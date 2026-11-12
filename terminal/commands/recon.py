"""Commandes de reconnaissance — dns, whois, headers, banner, sslscan, subdomain, hostscan.

Moteurs dans Tools/recon.py (import lazy : `requests` / `whois` ne ralentissent pas le démarrage).
À n'utiliser que sur des cibles que vous possédez ou êtes autorisé à tester.
"""
import os
import time

from terminal.registry import REGISTRY


def _table(rows) -> None:
    rows = [(k, v) for k, v in rows]
    if not rows:
        return
    width = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {str(k):<{width}}  {v}")


def _port(text: str) -> int:
    port = int(text)
    if not 1 <= port <= 65535:
        raise ValueError("Port entre 1 et 65535")
    return port


# ---------------------------------------------------------------------
# DNS / WHOIS
# ---------------------------------------------------------------------
@REGISTRY.register("dns", help_text=(
    "dns <domaine>          - Adresses A/AAAA + MX, NS et TXT\n"
    "dns <domaine> <type>   - Un seul type : A, AAAA, MX, TXT, NS, CNAME, SOA, PTR, SRV, CAA\n"
    "Exemples : dns example.com   |   dns example.com mx   |   dns 8.8.8.8 ptr"),
    summary="Enregistrements DNS d'un domaine (A, MX, TXT, NS…)")
def _dns(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 2:
        print("Usage : dns <domaine> [type]")
        return
    host = recon.clean_host(argv[1])
    types = [argv[2].upper()] if len(argv) > 2 else ["A", "MX", "NS", "TXT"]
    for rtype in types:
        if rtype in ("A", "AAAA") and len(argv) <= 2:
            addrs = recon.dns_addresses(host)
            lines = [f"{k:<5} {ip}" for k, ips in addrs.items() for ip in ips]
        else:
            lines = recon.dns_query(host, rtype)
        print(f"--- {rtype if len(argv) > 2 else ('A / AAAA' if rtype == 'A' else rtype)} ---")
        print("\n".join(f"  {l}" for l in lines) if lines else "  (aucun enregistrement)")


@REGISTRY.register("whois", help_text="whois <domaine>   - Registrar, dates, serveurs DNS et propriétaire d'un domaine",
                   summary="WHOIS d'un domaine (registrar, dates, DNS)")
def _whois(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 2:
        print("Usage : whois <domaine>")
        return
    info = recon.whois_lookup(recon.clean_host(argv[1]))
    if info:
        _table(info.items())
    else:
        print("Aucune information WHOIS (domaine inexistant ou registre muet).")


# ---------------------------------------------------------------------
# HTTP / services / TLS
# ---------------------------------------------------------------------
@REGISTRY.register("headers", help_text=(
    "headers <url>      - En-têtes HTTP + audit sécurité (HSTS, CSP, cookies, fuites de version)\n"
    "headers <url> -a   - Affiche aussi tous les en-têtes bruts\n"
    "Sans http:// ou https://, HTTPS est utilisé."),
    summary="En-têtes HTTP + audit des en-têtes de sécurité")
def _headers(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 2:
        print("Usage : headers <url> [-a]")
        return
    res = recon.http_headers(argv[1])
    for hop in res["redirects"]:
        print(f"  -> {hop}")
    print(f"  {res['status']} {res['url']}\n")
    if "-a" in argv[2:]:
        _table(res["headers"].items())
        print()
    for name, value in res["present"].items():
        print(f"  [+] {name}: {value[:90]}")
    for name in res["missing"]:
        print(f"  [-] {name} absent  ({recon.SECURITY_HEADERS[name]})")
    for name, value in res["leaks"].items():
        print(f"  [!] {name}: {value}  (révèle la technologie utilisée)")
    for name, missing in res["cookies"]:
        if missing:
            print(f"  [!] cookie {name} sans {', '.join(missing)}")
    total = len(recon.SECURITY_HEADERS)
    print(f"\n  Score : {total - len(res['missing'])}/{total} en-têtes de sécurité")


@REGISTRY.register("banner", help_text=(
    "banner <hôte> <port> [port...]   - Bannière des services (nom + version)\n"
    "Exemple : banner 192.168.1.1 21 22 80 443"),
    summary="Bannière d'un service TCP (identifie service + version)")
def _banner(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 3:
        print("Usage : banner <hôte> <port> [port...]")
        return
    host = recon.clean_host(argv[1])
    for port in (_port(p) for p in argv[2:]):
        try:
            text = recon.grab_banner(host, port)
        except OSError as e:
            print(f"[{port}] fermé ou injoignable ({e})")
            continue
        print(f"[{port}] " + (text.replace("\r", "").replace("\n", "\n      ") if text else "ouvert, aucune bannière"))


@REGISTRY.register("sslscan", help_text=(
    "sslscan <hôte> [port]   - Versions TLS acceptées, chiffrement, certificat et problèmes (défaut : 443)"),
    summary="Audit TLS : protocoles, chiffrement, certificat")
def _sslscan(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 2:
        print("Usage : sslscan <hôte> [port]")
        return
    res = recon.tls_scan(recon.clean_host(argv[1]), _port(argv[2]) if len(argv) > 2 else 443)
    print("  Protocoles : " + "  ".join(f"{p} {'oui' if ok else 'non'}" for p, ok in res["protocols"].items()))
    sans = res["sans"]
    _table([
        ("Négocié", f"{res['negotiated']} — {res['cipher']}"),
        ("Sujet", res["subject"]),
        ("Émetteur", res["issuer"]),
        ("Valide du", res["not_before"]),
        ("Expire le", f"{res['not_after']}  ({res['days_left']} jours)"),
        ("Noms (SAN)", ", ".join(sans[:8]) + (f" … (+{len(sans) - 8})" if len(sans) > 8 else "")),
        ("Confiance", "certificat valide" if res["trusted"] else "NON VALIDE"),
    ])
    for issue in res["issues"]:
        print(f"  [!] {issue}")
    if not res["issues"]:
        print("  [+] Aucun problème détecté")


# ---------------------------------------------------------------------
# Énumération
# ---------------------------------------------------------------------
@REGISTRY.register("subdomain", help_text=(
    "subdomain <domaine>              - Cherche les sous-domaines courants (liste intégrée)\n"
    "subdomain <domaine> <wordlist>   - Avec votre fichier (un mot par ligne)\n"
    "Résolution DNS uniquement : aucun paquet n'est envoyé aux serveurs trouvés."),
    summary="Énumération de sous-domaines par wordlist (DNS)")
def _subdomain(ctx, argv, raw):
    from Tools import recon

    if len(argv) < 2:
        print("Usage : subdomain <domaine> [wordlist]")
        return
    domain = recon.clean_host(argv[1])
    words = None
    if len(argv) > 2:
        path = os.path.expanduser(raw.split(None, 2)[2].strip().strip('"'))
        with open(path, encoding="utf-8", errors="ignore") as f:
            words = [l for l in f if l.strip() and not l.startswith("#")]
    start = time.time()
    res = recon.enum_subdomains(domain, words,
                                on_found=lambda name, ips: print(f"  [+] {name:<40} {', '.join(ips)}"))
    if res["wildcard"]:
        print(f"  [!] DNS wildcard détecté (*.{domain} -> {', '.join(res['wildcard'])}) : ces IP sont ignorées")
    print(f"[*] {len(res['found'])} sous-domaines trouvés sur {res['tested']} testés en {time.time() - start:.1f}s")


@REGISTRY.register("hostscan", help_text=(
    "hostscan            - Machines actives sur votre réseau local (/24 détecté automatiquement)\n"
    "hostscan <cidr>     - Sur le réseau donné (ex : hostscan 192.168.1.0/24, max 4096 adresses)\n"
    "Balayage par ping : une machine qui bloque le ping n'apparaît pas."),
    summary="Découverte des machines actives d'un réseau (ping sweep)")
def _hostscan(ctx, argv, raw):
    from Tools import recon

    network = argv[1] if len(argv) > 1 else recon.local_network()
    print(f"Balayage de {network}...")
    start = time.time()
    alive = recon.host_sweep(network, on_found=lambda ip, name: print(f"  [+] {ip:<16} {name}"))
    print(f"[*] {len(alive)} machines actives en {time.time() - start:.1f}s")
