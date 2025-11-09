import ipaddress
from urllib.parse import urlparse
import re
import socket
import subprocess
import requests
import whois
import json
import math
from datetime import datetime
from colorama import Fore, Style, init
init(autoreset=True)
from Tools.SV_IA import start_phase_2




open_ports = []
global_data = {
    "domain": "",
    "avg_ttl": 0,
    "latitude": 0.0,
    "longitude": 0.0,
    "country": "",
    "region": "",
    "city": "",
    "isp": "",
    "org": "",
    "asn": "",
    "proxy": False,
    "hosting": False,
    "mobile": False,
    "timezone": "",
    "whois_data": {},
    "ip_api_data": {},
    "open_ports": [],
}



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
    print(Fore.LIGHTMAGENTA_EX + viper_ascii)

def phase_2(): #ia reflexion
    print("Passage la phase 2 --> analyse avce IA")
    print("IA en cours de reflexion...")
    print("==================== RESULTATS =====================")
    start_extraction_donnés()
    








def detect_input_type(value):
    try:
        ipaddress.ip_address(value)
        return "ip"
    except ValueError:
        pass
    
    try:
        result = urlparse(value)
        if result.scheme and result.netloc:
            return "url"
    except:
        pass

    if re.match(r"^AS\d+$", value, re.IGNORECASE):
        return "asn"
    
    if re.match(r"[^@]+@[^@]+\.[^@]+", value):
        return "email"

    if "." in value and " " not in value:
        return "domain"
    
    return "unknown"

# --- FONCTIONS DE COLLECTE ---

def get_ip_info(ip):
    print(f"\n{Style.BRIGHT}{Fore.GREEN}[+] Collecte infos IP: {ip}{Style.RESET_ALL}")

    # ip-api.com
    try:
        r1 = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query")
        data1 = r1.json()
        if data1.get("status") != "success":
            print(f"{Fore.RED}Erreur ip-api: {data1.get('message')}{Style.RESET_ALL}")
            return None
        print(f"{Fore.YELLOW}== ip-api.com ==")
        print(f"{Fore.CYAN}Pays : {Fore.WHITE}{data1.get('country')} ({data1.get('countryCode')})")
        print(f"{Fore.CYAN}Région : {Fore.WHITE}{data1.get('regionName')} ({data1.get('region')})")
        print(f"{Fore.CYAN}Ville : {Fore.WHITE}{data1.get('city')}, District : {Fore.WHITE}{data1.get('district')}, Code postal : {Fore.WHITE}{data1.get('zip')}")
        print(f"{Fore.CYAN}Latitude : {Fore.WHITE}{data1.get('lat')}, Longitude : {Fore.WHITE}{data1.get('lon')}")
        print(f"{Fore.CYAN}Fuseau horaire : {Fore.WHITE}{data1.get('timezone')}")
        print(f"{Fore.CYAN}Fournisseur (ISP) : {Fore.WHITE}{data1.get('isp')}")
        print(f"{Fore.CYAN}Organisation : {Fore.WHITE}{data1.get('org')}")
        print(f"{Fore.CYAN}AS : {Fore.WHITE}{data1.get('as')}")
        print(f"{Fore.CYAN}Mobile : {Fore.WHITE}{data1.get('mobile')}")
        print(f"{Fore.CYAN}Proxy : {Fore.WHITE}{data1.get('proxy')}")
        print(f"{Fore.CYAN}Hosting : {Fore.WHITE}{data1.get('hosting')}")
        global_data["country"] = data1.get('country', "")
        global_data["region"] = data1.get('regionName', "")
        global_data["city"] = data1.get('city', "")
        global_data["latitude"] = data1.get('lat', 0.0)
        global_data["longitude"] = data1.get('lon', 0.0)
        global_data["isp"] = data1.get('isp', "")
        global_data["org"] = data1.get('org', "")
        global_data["asn"] = data1.get('as', "")
        global_data["proxy"] = data1.get('proxy', False)
        global_data["hosting"] = data1.get('hosting', False)
        global_data["mobile"] = data1.get('mobile', False)
        global_data["timezone"] = data1.get('timezone', "")
    except Exception as e:
        print(f"{Fore.RED}Erreur API ip-api : {e}{Style.RESET_ALL}")

    # ipinfo.io
    try:
        r2 = requests.get(f"https://ipinfo.io/{ip}/json")
        data2 = r2.json()
        print(f"\n{Fore.YELLOW}== ipinfo.io ==")
        print(f"{Fore.CYAN}IP : {Fore.WHITE}{data2.get('ip')}")
        print(f"{Fore.CYAN}Hostname : {Fore.WHITE}{data2.get('hostname')}")
        print(f"{Fore.CYAN}Ville : {Fore.WHITE}{data2.get('city')}")
        print(f"{Fore.CYAN}Région : {Fore.WHITE}{data2.get('region')}")
        print(f"{Fore.CYAN}Pays : {Fore.WHITE}{data2.get('country')}")
        print(f"{Fore.CYAN}Loc (lat,long) : {Fore.WHITE}{data2.get('loc')}")
        print(f"{Fore.CYAN}Organisation : {Fore.WHITE}{data2.get('org')}")
        print(f"{Fore.CYAN}Timezone : {Fore.WHITE}{data2.get('timezone')}")
        print(f"{Fore.CYAN}Réservé aux entreprises : {Fore.WHITE}{'Oui' if data2.get('bogon') else 'Non'}")
    except Exception as e:
        print(f"{Fore.RED}Erreur API ipinfo.io : {e}{Style.RESET_ALL}")

    # BGPView API pour ASN détaillé
    try:
        asn = data1.get('as', '').split(' ')[0].replace('AS','')
        if asn.isdigit():
            r3 = requests.get(f"https://api.bgpview.io/asn/{asn}")
            data3 = r3.json()
            if data3.get('status') == 'ok':
                asndata = data3['data']
                print(f"\n{Fore.YELLOW}== Infos ASN détaillées (BGPView) ==")
                print(f"{Fore.CYAN}ASN : {Fore.WHITE}{asn}")
                print(f"{Fore.CYAN}Nom : {Fore.WHITE}{asndata.get('name')}")
                print(f"{Fore.CYAN}Organisation : {Fore.WHITE}{asndata.get('holder')}")
                print(f"{Fore.CYAN}Pays : {Fore.WHITE}{asndata.get('country_code')}")
                print(f"{Fore.CYAN}Date création : {Fore.WHITE}{asndata.get('created')}")
                print(f"{Fore.CYAN}Description : {Fore.WHITE}{asndata.get('description')}")
                print(f"{Fore.CYAN}Réseaux associés (count) : {Fore.WHITE}{len(asndata.get('prefixes', []))}")
                # Affiche quelques prefixes
                prefixes = asndata.get('prefixes', [])
                for p in prefixes[:5]:
                    print(f"  - {p.get('prefix')}")
            else:
                print(f"{Fore.RED}ASN info non disponible.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Erreur BGPView ASN : {e}{Style.RESET_ALL}")

    # Ping + Traceroute
    print(f"\n{Fore.YELLOW}== Ping et Traceroute ==")
    try:
        print(f"{Fore.GREEN}Ping 4 paquets...{Style.RESET_ALL}")
        cmd_ping = ["ping", "-c", "4", ip] if not subprocess.os.name == 'nt' else ["ping", "-n", "4", ip]
        ping_result = subprocess.run(cmd_ping, capture_output=True, text=True, timeout=15)
        print(ping_result.stdout)
    except Exception as e:
        print(f"{Fore.RED}Erreur ping : {e}{Style.RESET_ALL}")

    try:
        print(f"{Fore.GREEN}Traceroute...{Style.RESET_ALL}")
        cmd_traceroute = ["traceroute", ip] if not subprocess.os.name == 'nt' else ["tracert", ip]
        trace_result = subprocess.run(cmd_traceroute, capture_output=True, text=True, timeout=30)
        print(trace_result.stdout)
    except Exception as e:
        print(f"{Fore.RED}Erreur traceroute : {e}{Style.RESET_ALL}")

    # Whois IP complet
    try:
        w = whois.whois(ip)
        print(f"\n{Fore.YELLOW}== Whois IP complet ==")
        for k, v in w.items():
            if v and str(v) != "[]" and str(v) != "None":
                val_str = str(v)
                if len(val_str) > 200:
                    val_str = val_str[:200] + "..."
                print(f"{Fore.CYAN}{k.capitalize()}: {Fore.WHITE}{val_str}")
    except Exception as e:
        print(f"{Fore.RED}Erreur whois IP : {e}{Style.RESET_ALL}")

    # Scan ports basique (top ports)
    import socket
    print(f"\n{Fore.YELLOW}== Scan ports basique ==")
    common_ports = [21,22,23,25,53,80,110,143,443,445,3389]
    
    for port in common_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            res = sock.connect_ex((ip, port))
            if res == 0:
                print(f"{Fore.GREEN}Port {port} ouvert")
                open_ports.append(port)
        except:
            pass
        sock.close()
    if not open_ports:
        print(f"{Fore.RED}Aucun port ouvert détecté.{Style.RESET_ALL}")
    phase_2()
    


def scan_ports(ip, ports=None):
    if ports is None:
        ports = [21,22,23,25,53,80,110,143,443,445,3389]
    print(f"\n[+] Scan ports communs sur {ip} :")
    
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.7)
        try:
            result = sock.connect_ex((ip, port))
            if result == 0:
                print(f"Port {port} : Ouvert")
                open_ports.append(port)
        except Exception:
            pass
        sock.close()
    global_data["open_ports"] = open_ports.copy()
    if not open_ports:
        print("Aucun port ouvert détecté.")
    return open_ports


    

def get_whois_info(target):
    print(f"\n[+] Recherche WHOIS pour {target}")
    try:
        w = whois.whois(target)
        for k, v in w.items():
            # Affiche seulement les infos non vides et en limitant la longueur
            if v and str(v) != "[]" and str(v) != "None":
                val_str = str(v)
                if len(val_str) > 150:
                    val_str = val_str[:150] + "..."
                print(f"{k.capitalize()}: {val_str}")
        return w
        global_data["whois_data"] = w  # Le dict complet retourné par whois
    except Exception as e:
        print(f"Erreur whois: {e}")
        return None

def dns_lookup(domain):
    print(f"\n[+] Recherche DNS pour {domain}")
    try:
        result = subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=5)
        print(result.stdout.strip())
    except Exception as e:
        print(f"Erreur DNS lookup: {e}")

def get_asn_info(asn):
    print(f"\n[+] Collecte infos ASN: {asn}")
    try:
        r = requests.get(f"https://api.bgpview.io/asn/{asn[2:]}")
        data = r.json()
        if data.get("status") != "ok":
            print("ASN introuvable.")
            return None
        info = data.get("data", {})
        print(f"ASN : {asn}")
        print(f"Nom : {info.get('name')}")
        print(f"Organisation : {info.get('holder')}")
        print(f"Pays : {info.get('country_code')}")
        print(f"Date création : {info.get('created')}")
        return info
    except Exception as e:
        print(f"Erreur API ASN: {e}")
        return None

def search_email_osint(email):
    print(f"\n[+] Recherche passive OSINT pour email: {email}")
    # Simple démonstration, tu peux intégrer des APIs ou scrapers plus avancés
    domain = email.split("@")[-1]
    print(f"Domain associé : {domain}")
    print("Recherche WHOIS du domaine lié à l'email:")
    get_whois_info(domain)

# --- GESTION URL ---

def analyze_url(url):
    print(f"\n[+] Analyse URL : {url}")
    parsed = urlparse(url)
    domain = parsed.netloc
    print(f"Domaine extrait : {domain}")
    get_whois_info(domain)
    dns_lookup(domain)
    parsed = urlparse(url)
    domain = parsed.netloc
    global_data["domain"] = domain
    # Peut rajouter requêtes HTTP, headers, certificats SSL, robots.txt, sitemap, etc.

# --- MAIN ---

def run_shadowviper(input_value):
    
    affichage_viper()
    input_type = detect_input_type(input_value)
    print(f"Type détecté : {input_type}")

    if input_type == "ip":
        get_ip_info(input_value)
    elif input_type == "domain":
        ip = resolve_domain_to_ip(input_value)
        if ip:
            get_ip_info(ip)
        else:
            print("Impossible de résoudre l'IP du domaine.")
        get_whois_info(input_value)
        get_ip_info(input_value)
        scan_ports(input_value)
        dns_lookup(input_value)
    elif input_type == "url":
        analyze_url(input_value)
        get_ip_info(input_value)
    elif input_type == "asn":
        get_asn_info(input_value)
        get_ip_info(input_value)
    elif input_type == "email":
        search_email_osint(input_value)
        get_ip_info(input_value)
    else:
        print("Type non reconnu, veuillez réessayer.")

def resolve_domain_to_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None


def start_extraction_donnés():
    # On extrait les données depuis global_data
    domain = global_data.get("domain", "")
    avg_ttl = 0  # À calculer ou ajouter une méthode pour récupérer TTL moyen si possible

    features = []
    features.append(len(domain))
    features.append(avg_ttl)
    features.append(len(global_data.get("open_ports", [])))
    features.append(global_data.get("latitude", 0.0))
    features.append(global_data.get("longitude", 0.0))
    features.append(int(global_data.get("proxy", False)))
    features.append(int(global_data.get("hosting", False)))
    features.append(int(global_data.get("mobile", False)))
    features.append(len(global_data.get("country", "")))
    features.append(len(global_data.get("region", "")))
    features.append(len(global_data.get("city", "")))
    features.append(len(global_data.get("isp", "")))
    features.append(len(global_data.get("org", "")))
    features.append(len(global_data.get("asn", "")))
    features.append(len(global_data.get("timezone", "")))

    result_dict = {
        "domain": domain,
        "avg_ttl": avg_ttl,
        "open_ports": global_data.get("open_ports", []),
        "latitude": global_data.get("latitude", 0.0),
        "longitude": global_data.get("longitude", 0.0),
        "country": global_data.get("country", ""),
        "region": global_data.get("region", ""),
        "city": global_data.get("city", ""),
        "isp": global_data.get("isp", ""),
        "org": global_data.get("org", ""),
        "asn": global_data.get("asn", ""),
        "proxy": global_data.get("proxy", False),
        "hosting": global_data.get("hosting", False),
        "mobile": global_data.get("mobile", False),
        "timezone": global_data.get("timezone", ""),
        "features_vector": features,
    }
    print("[INFO] Dictionnaire construit pour la phase 2 :")
    print(json.dumps(result_dict, indent=2))
    start_phase_2(result_dict)


if __name__ == "__main__":
    val = input("shadowviper > Entrez une IP, domaine, URL, ASN ou email : ").strip()
    run_shadowviper(val)
