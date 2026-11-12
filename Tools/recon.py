"""Reconnaissance réseau — dns, whois, headers, banner, sslscan, subdomain, hostscan.

Stdlib + requests / python-whois (déjà dans requirements). Les fonctions renvoient des
données ; l'affichage est dans terminal/commands/recon.py.
À n'utiliser que sur des systèmes que vous possédez ou êtes autorisé à tester.
"""
import ipaddress
import os
import re
import secrets
import socket
import ssl
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

_HOST_RE = re.compile(r"^(?!-)[A-Za-z0-9._:-]{1,253}$")


def console_text(raw: bytes) -> str:
    """Sortie d'un programme console (ping, tracert, nslookup…). Sous Windows elle est dans la page de code
    de la console (souvent cp850), pas en UTF-8 ni en cp1252 : sinon « requˆte » au lieu de « requête »."""
    if os.name != "nt":
        return raw.decode("utf-8", "replace")
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetConsoleOutputCP()
    except (AttributeError, OSError):
        cp = 0
    try:
        return raw.decode(f"cp{cp}" if cp else "oem", "replace")
    except LookupError:
        return raw.decode("oem", "replace")


def clean_host(target: str) -> str:
    """`https://ex.com:8443/x` → `ex.com`. Refuse tout ce qui n'est pas un nom d'hôte ou une IP."""
    target = target.strip()
    host = urlparse(target if "://" in target else "//" + target).hostname or ""
    if not _HOST_RE.match(host):
        raise ValueError(f"Cible invalide : {target!r}")
    return host


# ---------------------------------------------------------------------
# DNS
# ---------------------------------------------------------------------
DNS_TYPES = ("A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA", "PTR", "SRV", "CAA")


def dns_addresses(host: str) -> dict[str, list[str]]:
    """A et AAAA via le résolveur du système."""
    out = {"A": [], "AAAA": []}
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return out
    for family, *_rest, sockaddr in infos:
        key = "A" if family == socket.AF_INET else "AAAA"
        if sockaddr[0] not in out[key]:
            out[key].append(sockaddr[0])
    return out


def dns_query(host: str, rtype: str) -> list[str]:
    """Enregistrements `rtype` via `nslookup` (résolveur du système : marche aussi en réseau interne).

    shortcut: on affiche la réponse brute de nslookup, à remplacer par dnspython si on a
    besoin de résultats structurés (JSON, transfert de zone).
    """
    rtype = rtype.upper()
    if rtype not in DNS_TYPES:
        raise ValueError(f"Type inconnu. Types : {', '.join(DNS_TYPES)}")
    try:
        p = subprocess.run(["nslookup", f"-type={rtype}", host],
                           capture_output=True, timeout=15)
    except FileNotFoundError as e:
        raise RuntimeError("nslookup introuvable sur ce système") from e
    text = console_text(p.stdout) if p.stdout else ""
    # Le 1er bloc (avant la ligne vide) décrit le serveur DNS interrogé : on le saute.
    body = re.split(r"\r?\n\s*\r?\n", text, maxsplit=1)
    lines = []
    for l in (body[1] if len(body) > 1 else "").splitlines():
        l = l.strip()
        if not l:
            continue
        if lines and lines[-1].endswith("="):  # nslookup met la valeur des TXT sur la ligne suivante
            lines[-1] += " " + l
        else:
            lines.append(l)
    return [l for l in lines if not l.lower().startswith(("authoritative answers", "non-authoritative"))
            and "ne fait pas autorit" not in l.lower()]


# ---------------------------------------------------------------------
# WHOIS
# ---------------------------------------------------------------------
def whois_lookup(domain: str) -> dict[str, str]:
    import whois  # python-whois (lazy : import lent)

    def one(v):
        if isinstance(v, (list, tuple, set)):
            v = sorted({str(x) for x in v if x}, key=str.lower)
            return ", ".join(v[:6])
        return "" if v is None else str(v)

    w = whois.whois(domain)
    fields = (("Domaine", "domain_name"), ("Registrar", "registrar"), ("Créé le", "creation_date"),
              ("Expire le", "expiration_date"), ("Modifié le", "updated_date"),
              ("Serveurs DNS", "name_servers"), ("Statut", "status"), ("Organisation", "org"),
              ("Pays", "country"), ("E-mails", "emails"), ("DNSSEC", "dnssec"))
    return {label: one(w.get(key)) for label, key in fields if one(w.get(key))}


# ---------------------------------------------------------------------
# En-têtes HTTP
# ---------------------------------------------------------------------
SECURITY_HEADERS = {
    "Strict-Transport-Security": "force HTTPS (HSTS)",
    "Content-Security-Policy": "limite les scripts chargés (anti-XSS)",
    "X-Frame-Options": "empêche l'affichage dans une iframe (clickjacking)",
    "X-Content-Type-Options": "bloque le MIME sniffing",
    "Referrer-Policy": "limite les fuites d'URL via Referer",
    "Permissions-Policy": "restreint caméra, micro, géolocalisation…",
}
_LEAK_HEADERS = ("Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version", "X-Generator", "Via")


def http_headers(url: str, timeout: float = 10) -> dict:
    import requests

    if "://" not in url:
        url = "https://" + url
    r = requests.get(url, timeout=timeout, allow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 (Nebula headers)"}, stream=True)
    r.close()  # on ne veut que les en-têtes
    h = r.headers
    present = {k: h[k] for k in SECURITY_HEADERS if k in h}
    if not r.url.startswith("https://"):
        present.pop("Strict-Transport-Security", None)  # HSTS n'a aucun effet en HTTP
    cookies = []
    for c in r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw.headers, "getlist") else []:
        low = c.lower()
        missing = [flag for flag, token in (("Secure", "secure"), ("HttpOnly", "httponly"),
                                            ("SameSite", "samesite")) if token not in low]
        cookies.append((c.split("=", 1)[0], missing))
    return {
        "url": r.url,
        "status": r.status_code,
        "redirects": [f"{x.status_code} {x.url}" for x in r.history],
        "headers": dict(h),
        "present": present,
        "missing": [k for k in SECURITY_HEADERS if k not in present],
        "leaks": {k: h[k] for k in _LEAK_HEADERS if k in h},
        "cookies": cookies,
    }


# ---------------------------------------------------------------------
# Bannières de service
# ---------------------------------------------------------------------
_TLS_PORTS = {443, 465, 636, 853, 993, 995, 8443}


def _unverified_ctx() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # voulu : on inspecte la cible, on ne lui confie rien
    return ctx


def grab_banner(host: str, port: int, timeout: float = 3) -> str:
    """Bannière d'un service TCP. Si le service ne parle pas le premier, on envoie une requête HTTP."""
    with socket.create_connection((host, port), timeout=timeout) as raw:
        sock = _unverified_ctx().wrap_socket(raw, server_hostname=host) if port in _TLS_PORTS else raw
        sock.settimeout(timeout)
        try:
            data = sock.recv(2048)
        except (socket.timeout, TimeoutError):
            data = b""
        if not data:
            sock.sendall(f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
            try:
                data = sock.recv(2048)
            except (socket.timeout, TimeoutError):
                data = b""
    return data.decode("utf-8", "replace").strip()


# ---------------------------------------------------------------------
# TLS
# ---------------------------------------------------------------------
_TLS_VERSIONS = (("TLS 1.0", ssl.TLSVersion.TLSv1), ("TLS 1.1", ssl.TLSVersion.TLSv1_1),
                 ("TLS 1.2", ssl.TLSVersion.TLSv1_2), ("TLS 1.3", ssl.TLSVersion.TLSv1_3))
_WEAK_TLS = ("TLS 1.0", "TLS 1.1")


def _trusted_ctx() -> ssl.SSLContext:
    """Contexte qui vérifie le certificat. Sous Windows, le magasin système ne contient que les
    autorités déjà rencontrées → faux « non valide » ; on prend donc la liste de certifi (livrée avec requests)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _decode_der(der: bytes) -> dict:
    """Certificat DER → dict, même quand il n'est pas validé (auto-signé, expiré…).

    shortcut: passe par l'API privée ssl._ssl._test_decode_cert, à remplacer par le
    paquet `cryptography` si CPython la retire.
    """
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(ssl.DER_cert_to_PEM_cert(der))
        return ssl._ssl._test_decode_cert(path)
    finally:
        os.remove(path)


def _tls_accepts(host: str, port: int, version, timeout: float) -> bool:
    ctx = _unverified_ctx()
    try:
        ctx.set_ciphers("ALL:@SECLEVEL=0")  # sinon OpenSSL refuse lui-même les vieux protocoles
        ctx.minimum_version = ctx.maximum_version = version
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host):
                return True
    except (ssl.SSLError, OSError, ValueError):
        return False


def tls_scan(host: str, port: int = 443, timeout: float = 5) -> dict:
    """Protocoles acceptés, chiffrement négocié, certificat et problèmes détectés."""
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with _unverified_ctx().wrap_socket(raw, server_hostname=host) as s:
            negotiated, cipher = s.version(), s.cipher()
            cert = _decode_der(s.getpeercert(binary_form=True))

    trust_error = ""
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with _trusted_ctx().wrap_socket(raw, server_hostname=host):
                pass
    except ssl.SSLCertVerificationError as e:
        trust_error = e.verify_message or str(e)
    except (ssl.SSLError, OSError) as e:
        trust_error = str(e)

    with ThreadPoolExecutor(len(_TLS_VERSIONS)) as pool:
        accepted = list(pool.map(lambda v: _tls_accepts(host, port, v[1], timeout), _TLS_VERSIONS))
    protocols = {name: ok for (name, _), ok in zip(_TLS_VERSIONS, accepted)}

    def name(field):
        return ", ".join(v for rdn in cert.get(field, ()) for k, v in rdn if k in ("commonName", "organizationName"))

    expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), timezone.utc)
    days_left = (expires - datetime.now(timezone.utc)).days

    issues = []
    if trust_error:
        issues.append(f"certificat non valide : {trust_error}")
    if days_left < 0:
        issues.append(f"certificat expiré depuis {-days_left} jours")
    elif days_left < 30:
        issues.append(f"certificat expire dans {days_left} jours")
    issues += [f"{p} accepté (protocole obsolète)" for p in _WEAK_TLS if protocols.get(p)]
    if not protocols.get("TLS 1.3"):
        issues.append("TLS 1.3 non supporté")
    if cipher and cipher[2] and cipher[2] < 128:
        issues.append(f"chiffrement faible ({cipher[2]} bits)")

    return {
        "protocols": protocols,
        "negotiated": negotiated,
        "cipher": f"{cipher[0]} ({cipher[2]} bits)" if cipher else "?",
        "subject": name("subject"),
        "issuer": name("issuer"),
        "sans": [v for k, v in cert.get("subjectAltName", ()) if k == "DNS"],
        "not_before": cert.get("notBefore", ""),
        "not_after": cert.get("notAfter", ""),
        "days_left": days_left,
        "trusted": not trust_error,
        "issues": issues,
    }


# ---------------------------------------------------------------------
# Sous-domaines
# ---------------------------------------------------------------------
SUBDOMAINS = (
    "www mail webmail smtp pop pop3 imap mx mx1 mx2 ns ns1 ns2 ns3 dns dns1 dns2 ftp sftp ssh vpn "
    "remote rdp gateway gw proxy fw firewall router admin administrator panel cpanel whm plesk "
    "portal intranet extranet internal corp office login sso auth id accounts account my secure "
    "api api2 apis graphql rest ws app apps mobile m web web1 web2 www1 www2 www3 dev devel "
    "development test testing qa uat stage staging preprod pre prod production demo beta alpha "
    "sandbox lab labs old new legacy backup backups bak db database sql mysql postgres mongo redis "
    "elastic kibana grafana prometheus monitor monitoring status stats metrics logs log nagios zabbix "
    "git gitlab github svn repo ci cd jenkins build docker registry k8s kube cloud aws azure s3 "
    "cdn static assets img images media video files file upload uploads download downloads storage "
    "blog news shop store boutique pay payment billing invoice crm erp hr support help helpdesk "
    "desk ticket tickets docs doc wiki kb forum community chat meet video conf zoom jira confluence "
    "mail1 mail2 email exchange owa autodiscover lyncdiscover sip voip pbx tel calendar "
    "search share sharepoint drive data analytics track tracking ads marketing newsletter "
    "smtp1 smtp2 relay ldap ad dc dc1 dc2 nas san backup1 srv srv1 srv2 server host host1 vps "
    "en fr de es it us uk eu ch ca"
).split()


def _resolve(name: str) -> tuple[str, list[str]]:
    try:
        return name, sorted(set(socket.gethostbyname_ex(name)[2]))
    except (socket.gaierror, UnicodeError):
        return name, []


def enum_subdomains(domain: str, words=None, workers: int = 40, on_found=None) -> dict:
    """Sous-domaines qui résolvent en DNS. Détecte le DNS « wildcard » pour éviter les faux positifs."""
    words = list(dict.fromkeys(w.strip().lower() for w in (words or SUBDOMAINS) if w.strip()))
    # Un nom aléatoire qui résout = wildcard (*.domaine) : ses IP ne prouvent rien.
    wildcard = set(_resolve(f"nebula-{secrets.token_hex(6)}.{domain}")[1])
    found = []
    with ThreadPoolExecutor(workers) as pool:
        for name, ips in pool.map(_resolve, (f"{w}.{domain}" for w in words)):
            if ips and not set(ips) <= wildcard:
                found.append((name, ips))
                if on_found:
                    on_found(name, ips)
    return {"found": found, "wildcard": sorted(wildcard), "tested": len(words)}


# ---------------------------------------------------------------------
# Découverte d'hôtes
# ---------------------------------------------------------------------
MAX_SWEEP_HOSTS = 4096


def local_network() -> str:
    """Réseau /24 de l'interface qui sort vers Internet (aucun paquet n'est envoyé)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 80))  # adresse de documentation : sert juste à choisir l'interface
        ip = s.getsockname()[0]
    finally:
        s.close()
    return str(ipaddress.ip_network(ip + "/24", strict=False))


def _probe_host(ip: str, timeout_ms: int):
    """(ip, nom) si l'hôte répond, sinon None. Le nom est cherché dans le même thread (DNS inverse lent)."""
    return (ip, _name_of(ip)) if _ping(ip, timeout_ms) else None


def _ping(ip: str, timeout_ms: int) -> bool:
    cmd = (["ping", "-n", "1", "-w", str(timeout_ms), ip] if os.name == "nt"
           else ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip])
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout_ms / 1000 + 3, creationflags=flags)
    except (subprocess.TimeoutExpired, OSError):
        return False
    # Windows renvoie 0 aussi pour « hôte inaccessible » : on exige une vraie réponse (TTL=).
    return p.returncode == 0 and (os.name != "nt" or b"TTL=" in p.stdout.upper())


def _name_of(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return ""


def host_sweep(network: str, timeout_ms: int = 700, workers: int = 64, on_found=None) -> list[tuple[str, str]]:
    """Ping de chaque adresse de `network` (CIDR). Renvoie [(ip, nom)] des hôtes qui répondent."""
    net = ipaddress.ip_network(network, strict=False)
    if net.num_addresses > MAX_SWEEP_HOSTS:
        raise ValueError(f"Réseau trop grand ({net.num_addresses} adresses, max {MAX_SWEEP_HOSTS}). Utilisez un /20 ou plus petit.")
    ips = [str(ip) for ip in (net.hosts() if net.num_addresses > 2 else net)]
    alive = []
    with ThreadPoolExecutor(workers) as pool:
        for entry in pool.map(lambda i: _probe_host(i, timeout_ms), ips):
            if entry:
                alive.append(entry)
                if on_found:
                    on_found(*entry)
    return alive
