"""Tracker IP — portage des lignes 78-198 de l'ancien main.py.

- `get_ip_info(ip)`            : infos complètes via ip-api.com
- `live_ip_tracker(ip, delai)` : traçage continu (interruptible par 'q')
- `show_map_with_positions`    : carte folium "Moi vs Cible" (Macron/segments)

Les imports lourds (folium, keyboard) sont chargés à l'intérieur des fonctions
pour que le terminal démarre vite même si ces dépendances manquent.
"""
import time

from colorama import Fore, Style

import requests

_IP_API = "http://ip-api.com/json/{ip}"
_FIELDS = "status,message,query,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting"


def _tc():
    from terminal.theme import get_prompt_colors
    return get_prompt_colors()


def ip_blocks(target: str) -> list[dict]:
    """Infos publiques d'une IP ou d'un domaine (ip-api.com), en blocs."""
    from Tools.recon import clean_host
    target = clean_host(target)
    res = requests.get(f"{_IP_API.format(ip=target)}?fields={_FIELDS}&lang=fr", timeout=10).json()
    if res.get("status") != "success":
        raise ValueError(f"Aucune information pour {target} : {res.get('message', 'inconnue')}")
    oui = lambda v: "oui" if v else "non"  # noqa: E731
    notes = []
    if res.get("proxy"):
        notes.append(["warn", "Adresse de proxy, VPN ou Tor : la vraie origine est masquée"])
    if res.get("hosting"):
        notes.append(["info", "Adresse d'hébergeur (serveur, cloud) plutôt que d'un particulier"])
    if res.get("mobile"):
        notes.append(["info", "Réseau mobile : la position est très approximative"])
    return [{"notes": notes or [["ok", "Adresse résidentielle ou d'entreprise, sans proxy détecté"]]},
            {"title": f"Adresse {res['query']}", "kv": [
                ["Nom inverse", res.get("reverse") or "—"], ["Pays", f"{res['country']} ({res['countryCode']})"],
                ["Région / ville", f"{res['regionName']} / {res['city']} {res.get('zip', '')}".strip()],
                ["Coordonnées", f"{res['lat']}, {res['lon']} (approximatives)"], ["Fuseau", res["timezone"]],
                ["Fournisseur", res["isp"]], ["Organisation", res.get("org") or "—"],
                ["Système autonome", f"{res.get('as', '')} {res.get('asname', '')}".strip() or "—"],
                ["Proxy / VPN", oui(res.get("proxy"))], ["Hébergeur", oui(res.get("hosting"))], ["Mobile", oui(res.get("mobile"))]]}]


def get_ip_info(ip: str) -> dict | None:
    """Retourne les infos ip-api.com de `ip`, None en cas d'erreur (parité)."""
    try:
        res = requests.get(_IP_API.format(ip=ip)).json()
        if res["status"] == "success":
            return res
        print(Fore.RED + f"Erreur avec l'IP {ip} : {res.get('message', 'Inconnue')}")
    except Exception as e:
        print(Fore.RED + f"Erreur de requête : {e}")
    return None


def show_map_with_positions(my_ip: str, target_ip: str) -> None:
    """Compare les positions de `my_ip` et `target_ip` sur une carte folium."""
    my_info = get_ip_info(my_ip)
    target_info = get_ip_info(target_ip)

    if not my_info or not target_info:
        print(Fore.RED + "Impossible de récupérer les infos pour une ou plusieurs IP.")
        return

    def print_info(label: str, info: dict) -> None:
        print(Style.BRIGHT + _tc()["primary"] + f"\n=== Infos {label} ===")
        print(_tc()["accent"] + f"IP : {info['query']}")
        print(_tc()["accent"] + f"Pays : {info['country']} ({info['countryCode']})")
        print(_tc()["accent"] + f"Région : {info['regionName']} ({info['region']})")
        print(_tc()["accent"] + f"Ville : {info['city']}")
        print(_tc()["accent"] + f"Code postal : {info['zip']}")
        print(_tc()["accent"] + f"Fournisseur ISP : {info['isp']}")
        print(_tc()["accent"] + f"Organisation : {info.get('org', 'N/A')}")
        print(_tc()["accent"] + f"AS : {info.get('as', 'N/A')}")
        print(_tc()["accent"] + f"Latitude : {info['lat']}")
        print(_tc()["accent"] + f"Longitude : {info['lon']}")
        print(_tc()["accent"] + f"Fuseau horaire : {info.get('timezone', 'N/A')}")

    print_info("Utilisateur (Moi)", my_info)
    print_info("Cible", target_info)

    avg_lat = (my_info['lat'] + target_info['lat']) / 2
    avg_lon = (my_info['lon'] + target_info['lon']) / 2

    import folium
    map_world = folium.Map(location=[avg_lat, avg_lon], zoom_start=2)

    folium.Marker(
        location=[my_info['lat'], my_info['lon']],
        popup=f"Moi : {my_info['query']}\n{my_info['city']}, {my_info['country']}",
        icon=folium.Icon(color="blue", icon="user")
    ).add_to(map_world)

    folium.Marker(
        location=[target_info['lat'], target_info['lon']],
        popup=f"Cible : {target_info['query']}\n{target_info['city']}, {target_info['country']}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(map_world)

    folium.PolyLine(
        locations=[[my_info['lat'], my_info['lon']],
                   [target_info['lat'], target_info['lon']]],
        color="green", weight=2.5, opacity=0.8
    ).add_to(map_world)

    map_world.save("ip_positions_map.html")
    print(Fore.YELLOW + "\nCarte interactive sauvegardée sous 'ip_positions_map.html'. "
                        "Ouvre ce fichier dans un navigateur pour voir la carte.")


def live_ip_tracker(ip: str, refresh_delay: int | None = None) -> None:
    """Trace `ip` une fois (refresh_delay=None) ou en continu (refresh_delay en s)."""
    while True:
        try:
            data = requests.get(_IP_API.format(ip=ip)).json()
            if data["status"] == "fail":
                print(Fore.RED + "IP introuvable.")
                break

            print(Style.BRIGHT + _tc()["primary"] + f"\n=== Trace IP {ip} ===")
            print(_tc()["accent"] + f"Pays : {data['country']}")
            print(_tc()["accent"] + f"Région : {data['regionName']}")
            print(_tc()["accent"] + f"Ville : {data['city']}")
            print(_tc()["accent"] + f"Fournisseur : {data['isp']}")
            print(_tc()["accent"] + f"Latitude : {data['lat']}, Longitude : {data['lon']}")

            if refresh_delay is None:
                # Pas de refresh, on sort de la boucle après la première requête
                break

            print(Fore.YELLOW + f"(Actualisation dans {refresh_delay}s... Ctrl+C pour arrêter)")
            time.sleep(refresh_delay)

        except KeyboardInterrupt:
            print(Fore.RED + "\nTraceur interrompu.")
            break