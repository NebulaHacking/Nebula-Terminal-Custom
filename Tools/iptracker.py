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
        print(Style.BRIGHT + Fore.GREEN + f"\n=== Infos {label} ===")
        print(Fore.CYAN + f"IP : {info['query']}")
        print(Fore.CYAN + f"Pays : {info['country']} ({info['countryCode']})")
        print(Fore.CYAN + f"Région : {info['regionName']} ({info['region']})")
        print(Fore.CYAN + f"Ville : {info['city']}")
        print(Fore.CYAN + f"Code postal : {info['zip']}")
        print(Fore.CYAN + f"Fournisseur ISP : {info['isp']}")
        print(Fore.CYAN + f"Organisation : {info.get('org', 'N/A')}")
        print(Fore.CYAN + f"AS : {info.get('as', 'N/A')}")
        print(Fore.CYAN + f"Latitude : {info['lat']}")
        print(Fore.CYAN + f"Longitude : {info['lon']}")
        print(Fore.CYAN + f"Fuseau horaire : {info.get('timezone', 'N/A')}")

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

            print(Style.BRIGHT + Fore.GREEN + f"\n=== Trace IP {ip} ===")
            print(Fore.CYAN + f"Pays : {data['country']}")
            print(Fore.CYAN + f"Région : {data['regionName']}")
            print(Fore.CYAN + f"Ville : {data['city']}")
            print(Fore.CYAN + f"Fournisseur : {data['isp']}")
            print(Fore.CYAN + f"Latitude : {data['lat']}, Longitude : {data['lon']}")

            if refresh_delay is None:
                # Pas de refresh, on sort de la boucle après la première requête
                break

            print(Fore.YELLOW + f"(Actualisation dans {refresh_delay}s...)")
            time.sleep(refresh_delay)

            import keyboard
            if keyboard.is_pressed("q"):
                print(Fore.RED + "\nTraceur interrompu par l'utilisateur (touche Q).")
                break

        except KeyboardInterrupt:
            print(Fore.RED + "\nTraceur interrompu.")
            break