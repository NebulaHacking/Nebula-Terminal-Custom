"""Catalogue des outils du dashboard : un formulaire par outil, résultats structurés.

Chaque outil = des champs + une fonction `run(args)` qui renvoie des « blocs » affichables :
    {"title", "kv": [[clé, valeur]…]}            tableau clé / valeur
    {"title", "cols": […], "rows": [[…]…]}       tableau
    {"title", "text": "…"}                       texte brut
    {"notes": [[niveau, texte]…]}                constats (niveau : ok / warn / bad)
Les moteurs sont ceux du terminal (Tools/cryptokit, Tools/recon, Tools/portscan) : rien n'est dupliqué.
Pour ajouter un outil au dashboard : une entrée dans TOOLS.
"""
import socket
import uuid

from terminal.commands.crypto import _path, _read_capped
from Tools import cryptokit as ck
from Tools import reqforge as rf
from Tools import tracewave as tw
from Tools import recon


def _f(name, label, placeholder="", **extra):
    return {"name": name, "label": label, "placeholder": placeholder, **extra}


def _kv(title, mapping):
    return {"title": title, "kv": [[str(k), str(v)] for k, v in dict(mapping).items()]}


def _table(title, cols, rows):
    return {"title": title, "cols": cols, "rows": [[str(c) for c in r] for r in rows]}


def _int(value, default, low, high):
    n = int(value) if str(value).strip() else default
    if not low <= n <= high:
        raise ValueError(f"Valeur attendue entre {low} et {high}")
    return n


TARGET = _f("target", "Cible", "example.com", target=True, required=True)
FORMATS = list(ck.FORMATS)


# ---------------------------------------------------------------------
# Reconnaissance
# ---------------------------------------------------------------------
def _dns(a):
    host = recon.clean_host(a["target"])
    if a.get("type"):
        return [_table(a["type"], ["Enregistrement"], [[l] for l in recon.dns_query(host, a["type"])])]
    addrs = recon.dns_addresses(host)
    blocks = [_table("Adresses", ["Type", "Adresse"], [[k, ip] for k, ips in addrs.items() for ip in ips])]
    for rtype in ("MX", "NS", "TXT"):
        blocks.append(_table(rtype, ["Enregistrement"], [[l] for l in recon.dns_query(host, rtype)]))
    return blocks


def _whois(a):
    return [_kv("WHOIS", recon.whois_lookup(recon.clean_host(a["target"])))]


def _headers(a):
    r = recon.http_headers(a["target"])
    rows = [[h, "présent", r["present"][h][:120]] if h in r["present"] else [h, "absent", why]
            for h, why in recon.SECURITY_HEADERS.items()]
    notes = [["warn", f"{k}: {v} (révèle la technologie utilisée)"] for k, v in r["leaks"].items()]
    notes += [["warn", f"cookie {n} sans {', '.join(m)}"] for n, m in r["cookies"] if m]
    total = len(recon.SECURITY_HEADERS)
    score = total - len(r["missing"])
    notes.insert(0, ["ok" if score == total else "bad" if score < total / 2 else "warn",
                     f"{score}/{total} en-têtes de sécurité présents"])
    return [_kv("Réponse", {"URL": r["url"], "Statut": r["status"], "Redirections": " → ".join(r["redirects"]) or "aucune"}),
            {"notes": notes}, _table("En-têtes de sécurité", ["En-tête", "État", "Détail"], rows),
            _kv("Tous les en-têtes", r["headers"])]


def _banner(a):
    host, rows = recon.clean_host(a["target"]), []
    for port in (_int(p, 0, 1, 65535) for p in a["ports"].replace(",", " ").split()):
        try:
            rows.append([port, "ouvert", recon.grab_banner(host, port) or "(aucune bannière)"])
        except OSError as e:
            rows.append([port, "fermé", str(e)])
    return [_table("Services", ["Port", "État", "Bannière"], rows)]


def _sslscan(a):
    r = recon.tls_scan(recon.clean_host(a["target"]), _int(a.get("port", ""), 443, 1, 65535))
    return [{"notes": [["bad" if "non valide" in i or "expiré" in i else "warn", i] for i in r["issues"]]
             or [["ok", "Aucun problème détecté"]]},
            _table("Protocoles", ["Version", "Acceptée"], [[p, "oui" if ok else "non"] for p, ok in r["protocols"].items()]),
            _kv("Certificat", {"Sujet": r["subject"], "Émetteur": r["issuer"], "Valide du": r["not_before"],
                               "Expire le": f"{r['not_after']} ({r['days_left']} jours)",
                               "Noms (SAN)": ", ".join(r["sans"][:12]), "Négocié": f"{r['negotiated']} — {r['cipher']}",
                               "Confiance": "valide" if r["trusted"] else "NON VALIDE"})]


def _subdomain(a):
    words = None
    if a.get("wordlist"):
        with open(_path(a["wordlist"]), encoding="utf-8", errors="ignore") as f:
            words = [l for l in f if l.strip() and not l.startswith("#")]
    r = recon.enum_subdomains(recon.clean_host(a["target"]), words)
    notes = [["ok", f"{len(r['found'])} trouvés sur {r['tested']} testés"]]
    if r["wildcard"]:
        notes.append(["warn", f"DNS wildcard détecté ({', '.join(r['wildcard'])}) : ces adresses sont ignorées"])
    return [{"notes": notes}, _table("Sous-domaines", ["Nom", "Adresses"], [[n, ", ".join(ips)] for n, ips in r["found"]])]


def _hostscan(a):
    network = a.get("network") or recon.local_network()
    return [_table(f"Machines actives sur {network}", ["Adresse", "Nom"], recon.host_sweep(network))]


def _service(port):
    try:
        return socket.getservbyport(port)
    except OSError:
        return ""


def _scan(a):
    from Tools.portscan import scan_ports

    mode = a.get("mode") or "normal"
    pmin = _int(a["min"], 0, 1, 65535) if a.get("min") else None
    pmax = _int(a["max"], 0, 1, 65535) if a.get("max") else None
    ports = scan_ports(recon.clean_host(a["target"]), mode, pmin, pmax)
    return [{"notes": [["ok", f"{len(ports)} ports ouverts"]]},
            _table("Ports ouverts", ["Port", "Service habituel"], [[p, _service(p)] for p in ports])]


# ---------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------
def _decode(a):
    if a["format"] == "auto":
        return [_table("Formats reconnus", ["Format", "Texte"], ck.decode_auto(a["text"]))]
    return [{"title": "Résultat", "text": ck.decode(a["format"], a["text"])}]


def _hashid(a):
    kinds = ck.hashid(a["hash"])
    return [_table("Types probables", ["Du plus au moins courant"], [[k] for k in kinds])] if kinds \
        else [{"notes": [["warn", "Type inconnu"]]}]


def _jwt(a):
    import json

    r = ck.jwt_decode(a["token"])
    return [{"notes": [["bad" if "none" in w or "expiré" in w or "vide" in w else "ok", w] for w in r["warnings"]]},
            {"title": "Header", "text": json.dumps(r["header"], indent=2, ensure_ascii=False)},
            {"title": "Payload", "text": json.dumps(r["payload"], indent=2, ensure_ascii=False)}]


def _pwstrength(a):
    r = ck.pwstrength(a["password"])
    level = "bad" if r["bits"] < 50 else "warn" if r["bits"] < 70 else "ok"
    return [{"notes": [[level, f"{r['bits']} bits d'entropie : {r['verdict']}"]] + [["warn", n] for n in r["notes"]]}]


def _fileinfo(a):
    import os
    import time

    path = _path(a["path"])
    st, data = os.stat(path), _read_capped(path)
    ent = ck.entropy(data)
    stamp = lambda t: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))  # noqa: E731
    return [_kv("Fichier", {"Chemin": os.path.abspath(path), "Type": ck.file_type(data[:32]),
                            "Taille": f"{st.st_size} octets", "Modifié": stamp(st.st_mtime), "Créé": stamp(st.st_ctime),
                            "Entropie": f"{ent:.2f} / 8" + (" (chiffré ou compressé)" if ent > 7.5 else "")}),
            _kv("Empreintes", ck.hash_file(path))]


def _strings(a):
    found = ck.strings(_read_capped(_path(a["path"])), _int(a.get("min", ""), 4, 1, 100))
    return [{"notes": [["ok", f"{len(found)} chaînes trouvées" + (" (2000 affichées)" if len(found) > 2000 else "")]]},
            {"title": "Chaînes", "text": "\n".join(found[:2000])}]


def _reqforge(a):
    req = rf.build(a["method"], a["target"], a.get("headers", ""), a.get("body", ""))
    return rf.blocks(rf.send(req, verify=a.get("tls") != "ignorer", follow=a.get("redirects") == "suivre"))


def _reqforge_raw(a):
    req = rf.parse_raw(a["raw"], a.get("scheme") or "https")
    return rf.blocks(rf.send(req, verify=a.get("tls") != "ignorer"))


def _reqforge_replay(a):
    entry = rf.variant(rf.get(_int(a["n"], 0, 1, 10**9)), a.get("method") or None, a.get("url") or None,
                       a.get("headers", ""), a.get("body") or None)
    old = rf.get(_int(a["n"], 0, 1, 10**9))
    return rf.blocks(rf.send(entry, verify=old["verify"], follow=old["follow"]))


_TLS = _f("tls", "Certificat TLS", options=["vérifier", "ignorer"])
_FMT = _f("format", "Format", options=FORMATS)
_PATH = _f("path", "Fichier", r"C:\chemin\vers\fichier", required=True)

TOOLS = [
    # --- Reconnaissance ---
    dict(id="dns", cat="Reconnaissance", label="DNS", desc="Enregistrements DNS d'un domaine.",
         fields=[TARGET, _f("type", "Type", options=["", *recon.DNS_TYPES])], run=_dns),
    dict(id="whois", cat="Reconnaissance", label="WHOIS", desc="Registrar, dates et serveurs DNS d'un domaine.",
         fields=[TARGET], run=_whois),
    dict(id="headers", cat="Reconnaissance", label="En-têtes HTTP", desc="En-têtes d'un site et audit des en-têtes de sécurité.",
         fields=[TARGET], run=_headers),
    dict(id="sslscan", cat="Reconnaissance", label="Audit TLS", desc="Versions TLS acceptées, chiffrement et certificat.",
         fields=[TARGET, _f("port", "Port", "443")], run=_sslscan),
    dict(id="scan", cat="Reconnaissance", label="Ports", desc="Ports TCP ouverts. Le mode « all » teste les 65 535 ports (1 à 2 minutes).",
         fields=[TARGET, _f("mode", "Mode", options=["normal", "fast", "all", "stealth"]),
                 _f("min", "Port min", "1"), _f("max", "Port max", "1024")], run=_scan),
    dict(id="banner", cat="Reconnaissance", label="Bannières", desc="Nom et version des services sur des ports donnés.",
         fields=[TARGET, _f("ports", "Ports", "21 22 80 443", required=True)], run=_banner),
    dict(id="subdomain", cat="Reconnaissance", label="Sous-domaines", desc="Sous-domaines qui existent en DNS (liste intégrée ou wordlist).",
         fields=[TARGET, _f("wordlist", "Wordlist (optionnel)", "chemin d'un fichier")], run=_subdomain),
    dict(id="hostscan", cat="Reconnaissance", label="Machines du réseau", desc="Machines qui répondent au ping. Vide = votre réseau local.",
         fields=[_f("network", "Réseau (optionnel)", "192.168.1.0/24")], run=_hostscan),
    dict(id="dirb", cat="Reconnaissance", label="Répertoires web", desc="Dossiers et fichiers cachés d'un site (20 requêtes en parallèle).",
         fields=[TARGET, _f("wordlist", "Wordlist (optionnel)", "mots.txt")], cmd="dirb {target} {wordlist}"),
    dict(id="ping", cat="Reconnaissance", label="Ping", desc="Teste si une machine répond.",
         fields=[TARGET], cmd="ping {target}"),
    # --- Crypto ---
    dict(id="encode", cat="Crypto", label="Encoder", desc="Encode un texte.",
         fields=[_FMT, _f("text", "Texte", required=True, multiline=True)],
         run=lambda a: [{"title": "Résultat", "text": ck.encode(a["format"], a["text"])}]),
    dict(id="decode", cat="Crypto", label="Décoder", desc="Décode un texte. « auto » essaie tous les formats.",
         fields=[_f("format", "Format", options=["auto", *FORMATS]), _f("text", "Texte", required=True, multiline=True)], run=_decode),
    dict(id="hash", cat="Crypto", label="Empreintes", desc="MD5, SHA-1, SHA-256 et SHA-512 d'un texte.",
         fields=[_f("text", "Texte", required=True, multiline=True)], run=lambda a: [_kv("Empreintes", ck.hash_text(a["text"]))]),
    dict(id="hashid", cat="Crypto", label="Identifier un hash", desc="Devine le type d'un hash.",
         fields=[_f("hash", "Hash", required=True)], run=_hashid),
    dict(id="jwt", cat="Crypto", label="JWT", desc="Décode un token JWT. La signature n'est pas vérifiée.",
         fields=[_f("token", "Token", "eyJ…", required=True, multiline=True)], run=_jwt),
    dict(id="pwgen", cat="Crypto", label="Générer un mot de passe", desc="Mots de passe aléatoires forts.",
         fields=[_f("length", "Longueur", "20"), _f("count", "Nombre", "5")],
         run=lambda a: [_table("Mots de passe", ["Valeur"], [[ck.pwgen(_int(a.get("length", ""), 20, 8, 256))]
                                                              for _ in range(_int(a.get("count", ""), 5, 1, 100))])]),
    dict(id="pwstrength", cat="Crypto", label="Force d'un mot de passe", desc="Entropie estimée. Le mot de passe n'est ni affiché ni enregistré.",
         fields=[_f("password", "Mot de passe", required=True, secret=True)], run=_pwstrength),
    dict(id="ipcalc", cat="Crypto", label="Calcul IP", desc="Réseau, masque, broadcast et plage d'hôtes.",
         fields=[_f("spec", "Adresse / CIDR", "192.168.1.10/24", required=True)], run=lambda a: [_kv("Réseau", ck.ipcalc(a["spec"]))]),
    dict(id="ts", cat="Crypto", label="Timestamp", desc="Timestamp Unix ↔ date. Vide = maintenant.",
         fields=[_f("value", "Timestamp ou date", "1700000000 ou 2026-11-10 14:30")],
         run=lambda a: [_kv("Date", ck.ts_convert(a.get("value", "")))]),
    dict(id="uuid", cat="Crypto", label="UUID", desc="Identifiants UUID v4.",
         fields=[_f("count", "Nombre", "5")],
         run=lambda a: [_table("UUID", ["Valeur"], [[uuid.uuid4()] for _ in range(_int(a.get("count", ""), 5, 1, 1000))])]),
    # --- Fichiers ---
    dict(id="fileinfo", cat="Fichiers", label="Analyse de fichier", desc="Type réel, taille, dates, entropie et empreintes.",
         fields=[_PATH], run=_fileinfo),
    dict(id="strings", cat="Fichiers", label="Chaînes d'un binaire", desc="Chaînes lisibles d'un fichier (2000 lignes au plus).",
         fields=[_PATH, _f("min", "Longueur min", "4")], run=_strings),
]
TOOLS += [
    # --- Web ---
    dict(id="reqforge", cat="Web", label="Atelier HTTP",
         desc="Construit et envoie une requête HTTP, puis analyse la réponse (en-têtes, cookies, CORS, paramètres "
              "renvoyés, erreurs exposées). Chaque envoi reçoit un numéro pour le rejouer ou le comparer.",
         fields=[_f("method", "Méthode", options=list(rf.METHODS)), _f("target", "URL", "https://example.com/", target=True, required=True),
                 _TLS, _f("redirects", "Redirections", options=["ne pas suivre", "suivre"]),
                 _f("headers", "En-têtes (un par ligne)", "Cookie: session=abc", multiline=True),
                 _f("body", "Corps", "a=1&b=2", multiline=True)], run=_reqforge),
    dict(id="reqforge-raw", cat="Web", label="Requête brute",
         desc="Collez une requête copiée depuis les outils du navigateur (clic droit → Copier en tant que HTTP brut) ou depuis Burp.",
         fields=[_f("scheme", "Protocole", options=["https", "http"]), _TLS,
                 _f("raw", "Requête", "GET /chemin HTTP/1.1\nHost: example.com", required=True, multiline=True)], run=_reqforge_raw),
    dict(id="reqforge-replay", cat="Web", label="Rejouer une requête",
         desc="Renvoie une requête de l'historique en changeant ce que vous voulez. Les en-têtes donnés remplacent ceux du même nom.",
         fields=[_f("n", "N° de requête", "1", required=True), _f("method", "Méthode (optionnel)", "POST"),
                 _f("url", "URL (optionnel)", "https://example.com/autre"),
                 _f("headers", "En-têtes à changer", "Cookie: session=autre", multiline=True),
                 _f("body", "Nouveau corps (optionnel)", multiline=True)], run=_reqforge_replay),
    dict(id="reqforge-diff", cat="Web", label="Comparer deux réponses",
         desc="Statut, taille, temps, en-têtes et corps : ce qui change entre deux requêtes de l'historique.",
         fields=[_f("a", "N° A", "1", required=True), _f("b", "N° B", "2", required=True)],
         run=lambda a: rf.diff(rf.get(_int(a["a"], 0, 1, 10**9)), rf.get(_int(a["b"], 0, 1, 10**9)))),
    dict(id="reqforge-history", cat="Web", label="Historique HTTP", desc="Toutes les requêtes envoyées pendant cette session.",
         fields=[], run=lambda a: [{"title": "Historique", "cols": rf.HISTORY_COLS, "rows": rf.history_rows()}]),
    # --- Analyse ---
    dict(id="tracewave", cat="Analyse", label="Analyse de capture",
         desc="Analyse un fichier .pcap ou .pcapng : machines, conversations, services, domaines, sites HTTPS, "
              "et constats automatiques (protocoles en clair, identifiants visibles, balayages, conflits ARP).",
         fields=[_PATH, _f("focus", "Seulement cette IP (optionnel)", "192.168.1.10")],
         run=lambda a: tw.blocks(tw.analyze(_path(a["path"]), a.get("focus") or None))),
    dict(id="tracewave-compare", cat="Analyse", label="Comparer deux captures",
         desc="Ce qui est apparu ou a disparu entre deux captures (avant / après une modification du réseau, par ex.).",
         fields=[_f("a", "Capture « avant »", r"C:\captures\avant.pcapng", required=True),
                 _f("b", "Capture « après »", r"C:\captures\apres.pcapng", required=True)],
         run=lambda a: tw.compare(_path(a["a"]), _path(a["b"]))),
]
TOOLS += [
    dict(id="iptracker", cat="Reconnaissance", label="Infos d'une IP",
         desc="Pays, ville, fournisseur, système autonome, proxy/VPN et hébergeur d'une adresse IP ou d'un domaine (base publique).",
         fields=[TARGET], run=lambda a: __import__("Tools.iptracker", fromlist=["x"]).ip_blocks(a["target"])),
    dict(id="shadowviper", cat="Reconnaissance", label="ShadowViper",
         desc="Collecte d'informations sur une IP, un domaine, une URL, un ASN ou un e-mail : géolocalisation, WHOIS, DNS, ports, traceroute.",
         fields=[TARGET], run=lambda a: __import__("Tools.shadowviper", fromlist=["x"]).investigate(a["target"])),
    dict(id="nexariescan", cat="Web", label="XSS réfléchis",
         desc="Parcourt le site puis teste les paramètres d'URL et les formulaires (GET). Site autorisé uniquement.",
         fields=[_f("target", "URL", "https://example.com", target=True, required=True),
                 _f("pages", "Pages max", "50"), _f("post", "Formulaires POST", options=["non", "oui"])],
         run=lambda a: __import__("Tools.nexariescan", fromlist=["x"]).scan_blocks(
             a["target"], 0.5, _int(a.get("pages", ""), 50, 1, 500), a.get("post") == "oui")),
    dict(id="weather", cat="Utilitaires", label="Météo", desc="Conditions actuelles et prévisions sur 3 jours. Vide = ta position estimée.",
         fields=[_f("city", "Ville", "Fribourg")], run=lambda a: __import__("Tools.weather", fromlist=["x"]).weather_blocks(a.get("city", ""))),
]
BY_ID = {t["id"]: t for t in TOOLS}


def catalogue() -> list[dict]:
    """Le catalogue sans les fonctions (envoyé au navigateur)."""
    return [{k: v for k, v in t.items() if k not in ("run", "cmd")} for t in TOOLS]


def clean_args(tool: dict, args: dict) -> dict:
    """Ne garde que les champs déclarés, en texte ; vérifie les champs obligatoires et les listes."""
    out = {}
    for f in tool["fields"]:
        value = str(args.get(f["name"], "")).strip()
        if f.get("required") and not value:
            raise ValueError(f"Champ obligatoire : {f['label']}")
        if "options" in f and value not in f["options"]:
            value = f["options"][0]
        if len(value) > 20000:
            raise ValueError(f"{f['label']} : texte trop long")
        out[f["name"]] = value
    return out


def title_of(tool: dict, args: dict) -> str:
    """Titre affiché dans le journal : jamais les champs secrets, textes longs coupés."""
    shown = [args[f["name"]][:60] for f in tool["fields"]
             if args.get(f["name"]) and not f.get("secret") and not f.get("multiline")]
    return " ".join([tool["id"], *shown])
