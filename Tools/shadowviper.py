"""ShadowViper — collecte d'informations sur une IP, un domaine, une URL, un ASN ou un e-mail.

`investigate(valeur)` renvoie des blocs (terminal, dashboard, --json, Nebula IA).
Sources : ip-api.com, ipinfo.io, RIPEstat (ASN), WHOIS du domaine, DNS, ports courants, ping/traceroute,
puis le modèle local (Tools/SV_IA, scikit-learn) s'il est installé.
"""
import contextlib
import io
import ipaddress
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080]
TIMEOUT = 8


def affichage_viper():
    viper_ascii = r"""                                                  
    
                                                                                                                       
                                                                                          __
                                                                            ---_ ...... _/_ -
                                                                            /  .      ./ .'*\ \
                                                                            : '         /__-'   \.
                                                                            /                      )
                                                                        _/                  >   .'
                                                                        /   .   .       _.-" /  .'
                                                                        \           __/"     /.'/|
                                                                        \ '--  .-" /     //' |\|
                                                                        \|  \ | /     //_ _ |/|
                                                                            `.  \:     //|_ _ _|\|
                                                                            | \/.    //  | _ _ |/| 
                                                                            \_ | \/ /    \ _ _ \\\
                                                                                \__/      \ _ _ \|\
  .--.--.     ,---,                                                                                                     
 /  /    '. ,--.' |                     ,---,                              ,---.  ,--,   ,-.----.                          
|  :  /`. / |  |  :                   ,---.'|   ,---.           .---.     /__./|,--.'|   \    /  \             __  ,-. 
;  |  |--`  :  :  :                   |   | :  '   ,'\         /. ./|,---.;  ; ||  |,    |   :    |          ,' ,'/ /| 
|  :  ;_    :  |  |,--.  ,--.--.      |   | | /   /   |     .-'-. ' /___/ \  | |`--'_    |   | .\ :   ,---.  '  | |' | 
 \  \    `. |  :  '   | /       \   ,--.__| |.   ; ,. :    /___/ \: \   ;  \ ' |,' ,'|   .   : |: |  /     \ |  |   ,' 
  `----.   \|  |   /' :.--.  .-. | /   ,'   |'   | |: : .-'.. '   ' .\   \  \: |'  | |   |   |  \ : /    /  |'  :  /   
  __ \  \  |'  :  | | | \__\/: . ..   '  /  |'   | .; :/___/ \:     ' ;   \  ' .|  | :   |   : .  |.    ' / ||  | '    
 /  /`--'  /|  |  ' | : ," .--.; |'   ; |:  ||   :    |.   \  ' .\     \   \   ''  : |__ :     |`-''   ;   /|;  : |    
'--'.     / |  :  :_:,'/  /  ,.  ||   | '/  ' \   \  /  \   \   ' \ |   \   `  ;|  | '.'|:   : :   '   |  / ||  , ;    
  `--'---'  |  | ,'   ;  :   .'   \   :    :|  `----'    \   \  |--"     :   \ |;  :    ;|   | :   |   :    | ---'     
            `--''     |  ,     .-./\   \  /               \   \ |         '---" |  ,   / `---'.|    \   \  /           
                       `--`---'     `----'                 '---"                 ---`-'    `---`     `----'            
                                                                                                                       
                                                                                                                                                                                                                   
    """
    from terminal.theme import paint
    print(paint(viper_ascii))


def detect_input_type(value):
    try:
        ipaddress.ip_address(value)
        return "ip"
    except ValueError:
        pass
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        return "url"
    if re.match(r"^AS\d+$", value, re.IGNORECASE):
        return "asn"
    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        return "email"
    if "." in value and " " not in value:
        return "domain"
    return "unknown"


def _kv(title, mapping):
    return {"title": title, "kv": [[k, str(v)] for k, v in mapping.items() if v not in (None, "", [], {})]}


def _get_json(url):
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _whois(target):
    import whois

    rows = {}
    for k, v in whois.whois(target).items():
        if v and str(v) not in ("[]", "None"):
            text = str(v)
            rows[k.replace("_", " ").capitalize()] = text if len(text) <= 200 else text[:200] + "…"
    return rows


def _asn(number):
    # RIPEstat (gratuit, sans clé) ; BGPView, utilisé avant, a fermé.
    data = _get_json(f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{number}")
    d = data.get("data") or {}
    if data.get("status") != "ok" or not d.get("holder"):
        raise ValueError("ASN introuvable")
    block = d.get("block") or {}
    return {"ASN": f"AS{number}", "Titulaire": d.get("holder"), "Annoncé sur Internet": "oui" if d.get("announced") else "non",
            "Attribué par": block.get("desc")}


def _open_ports(ip):
    def probe(port):
        with socket.socket(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.7)
            return port if s.connect_ex((ip, port)) == 0 else None
    with ThreadPoolExecutor(len(COMMON_PORTS)) as pool:
        return [p for p in pool.map(probe, COMMON_PORTS) if p]


def _trace(ip):
    windows = subprocess.os.name == "nt"
    # ip vient de ipaddress : pas d'injection d'option possible
    from Tools.recon import console_text

    ping = subprocess.run(["ping", "-n" if windows else "-c", "4", ip], capture_output=True, timeout=20)
    trace = subprocess.run(["tracert", "-h", "15", "-d", ip] if windows else ["traceroute", "-m", "15", "-n", ip],
                           capture_output=True, timeout=60)
    return (console_text(ping.stdout) + "\n" + console_text(trace.stdout)).strip()


def _ml(geo, ports, domain):
    """Phase 2 : modèle local. Facultatif (scikit-learn)."""
    try:
        from Tools.SV_IA import start_phase_2
    except ModuleNotFoundError as e:
        return {"notes": [["info", f"Analyse par le modèle local ignorée : module « {e.name} » absent "
                                   "(python launch.py --full)"]]}
    data = {"domain": domain, "avg_ttl": 0, "open_ports": ports, "latitude": geo.get("lat", 0.0),
            "longitude": geo.get("lon", 0.0), "country": geo.get("country", ""), "region": geo.get("regionName", ""),
            "city": geo.get("city", ""), "isp": geo.get("isp", ""), "org": geo.get("org", ""), "asn": geo.get("as", ""),
            "proxy": geo.get("proxy", False), "hosting": geo.get("hosting", False), "mobile": geo.get("mobile", False),
            "timezone": geo.get("timezone", "")}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        start_phase_2(data)
    return {"title": "Analyse du modèle local (indicatif)", "text": out.getvalue().strip()}


def _ip_blocks(ip, domain=""):
    blocks, notes, geo = [], [], {}
    try:
        geo = _get_json(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,"
                        "zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query")
        if geo.get("status") != "success":
            raise ValueError(geo.get("message", "réponse invalide"))
        blocks.append(_kv("Géolocalisation (ip-api.com)", {
            "IP": geo.get("query"), "Pays": f"{geo.get('country')} ({geo.get('countryCode')})",
            "Région": geo.get("regionName"), "Ville": geo.get("city"), "Code postal": geo.get("zip"),
            "Coordonnées": f"{geo.get('lat')}, {geo.get('lon')}", "Fuseau": geo.get("timezone"),
            "Fournisseur": geo.get("isp"), "Organisation": geo.get("org"), "AS": geo.get("as"),
            "Mobile": "oui" if geo.get("mobile") else "non", "Proxy / VPN": "oui" if geo.get("proxy") else "non",
            "Hébergeur": "oui" if geo.get("hosting") else "non"}))
        if geo.get("proxy"):
            notes.append(["warn", "Adresse signalée comme proxy ou VPN"])
    except (requests.RequestException, ValueError) as e:
        notes.append(["warn", f"ip-api.com indisponible : {e}"])
    try:
        info = _get_json(f"https://ipinfo.io/{ip}/json")
        blocks.append(_kv("ipinfo.io", {"Nom d'hôte": info.get("hostname"), "Organisation": info.get("org"),
                                        "Localisation": info.get("loc"), "Adresse réservée": "oui" if info.get("bogon") else ""}))
    except (requests.RequestException, ValueError) as e:
        notes.append(["warn", f"ipinfo.io indisponible : {e}"])
    number = (geo.get("as") or "").split(" ")[0].upper().replace("AS", "")
    if number.isdigit():
        try:
            blocks.append(_kv("Système autonome (RIPEstat)", _asn(number)))
        except (requests.RequestException, ValueError) as e:
            notes.append(["info", f"RIPEstat indisponible : {e}"])
    # Pas de WHOIS d'adresse : python-whois renvoie celui du domaine (trompeur). ip-api/ipinfo/RIPEstat suffisent.
    ports = _open_ports(ip)
    blocks.append({"title": "Ports courants ouverts", "cols": ["Port", "Service"],
                   "rows": [[str(p), _service(p)] for p in ports]})
    risky = [p for p in ports if p in (21, 23, 445, 3389, 3306, 5432)]
    if risky:
        notes.append(["bad", f"Services sensibles exposés : {', '.join(map(str, risky))}"])
    try:
        blocks.append({"title": "Ping et traceroute", "text": _trace(ip)})
    except (OSError, subprocess.TimeoutExpired) as e:
        notes.append(["info", f"Ping / traceroute impossibles : {e}"])
    blocks.append(_ml(geo, ports, domain))
    return blocks, notes


def _service(port):
    try:
        return socket.getservbyport(port)
    except OSError:
        return "?"


def investigate(value):
    """Point d'entrée : renvoie la liste des blocs de résultat."""
    from Tools.recon import clean_host, dns_addresses

    value = value.strip()
    kind = detect_input_type(value)
    head = [_kv("Cible", {"Valeur": value, "Type détecté": kind})]
    if kind == "ip":
        blocks, notes = _ip_blocks(value)
    elif kind in ("domain", "url"):
        host = clean_host(urlparse(value).hostname if kind == "url" else value)
        try:
            ip = socket.gethostbyname(host)
        except OSError:
            return head + [{"notes": [["bad", f"Impossible de résoudre {host}"]]}]
        blocks, notes = _ip_blocks(ip, host)
        addrs = dns_addresses(host)
        blocks.insert(0, {"title": f"DNS de {host}", "cols": ["Type", "Adresse"],
                          "rows": [[k, a] for k, lst in addrs.items() for a in lst]})
        try:
            blocks.insert(1, _kv(f"WHOIS de {host}", _whois(host)))
        except Exception as e:
            notes.append(["info", f"WHOIS du domaine impossible : {e}"])
    elif kind == "asn":
        blocks, notes = [], []
        try:
            blocks.append(_kv("Système autonome (RIPEstat)", _asn(value[2:])))
        except (requests.RequestException, ValueError) as e:
            notes.append(["bad", f"ASN : {e}"])
    elif kind == "email":
        domain = value.split("@")[-1]
        blocks, notes = [], [["info", f"Domaine de l'adresse : {domain} (aucune recherche sur la personne)"]]
        try:
            blocks.append(_kv(f"WHOIS de {domain}", _whois(domain)))
        except Exception as e:
            notes.append(["info", f"WHOIS impossible : {e}"])
    else:
        return head + [{"notes": [["bad", "Type non reconnu : IP, domaine, URL, ASN (AS15169) ou e-mail"]]}]
    return head + ([{"notes": notes}] if notes else []) + blocks


def run_shadowviper(value):
    """Ancien point d'entrée (bannière + affichage)."""
    from terminal.blocks import print_blocks

    affichage_viper()
    print_blocks(investigate(value))
