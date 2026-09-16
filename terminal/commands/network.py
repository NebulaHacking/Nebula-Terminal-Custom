"""Commandes réseau (M3) — scan, iptracker, ping.

Portage des branches de l'ancien main.py : scan (1189-1290), iptracker (1144-1156),
ping (937-938). Les moteurs sont dans Tools/portscan.py et Tools/iptracker.py ;
ce module ne fait que l'adaptation CLI (flags, arguments).
"""
import requests

from terminal.registry import REGISTRY
from Tools.portscan import scan_ports
from Tools.iptracker import live_ip_tracker, show_map_with_positions


SCAN_HELP = """ -- Scan v1.0 --

Syntaxe :
   -f [IP]  : analyse rapide des ports
   -a [IP]  : analyse de tous les ports
   -s [IP]  : analyse discrète des ports

Hotkeys :
   q        - Stop scan
   r        - Statistiques restantes
"""

@REGISTRY.register("scan", help_text=SCAN_HELP, summary="Analyse des ports ouverts (-f rapide, -a tous, -s discret)")
def _scan(ctx, argv, raw):
    from terminal.banner import affichage_scan
    affichage_scan()

    if len(argv) < 2:
        return  # "scan" seul : bannière seulement (parité avec l'original)

    if argv[1] == "-f":  # scan rapide
        port_min = int(argv[3]) if len(argv) > 3 else None
        port_max = int(argv[4]) if len(argv) > 4 else None
        scan_ports(argv[2], mode="fast",
                   port_min=port_min, port_max=port_max)
    elif argv[1] == "-a":  # scan de tous les ports
        scan_ports(argv[2], mode="all")
    elif argv[1] == "-s":  # scan discret, 4 passes de 256 ports
        scan_ports(argv[2], mode="stealth")
    else:  # scan normal
        port_min = int(argv[2]) if len(argv) > 2 else None
        port_max = int(argv[3]) if len(argv) > 3 else None
        scan_ports(argv[1], mode="normal",
                   port_min=port_min, port_max=port_max)


IPT_HELP = """ -- IPTracker v1.0 --

Hotkeys :
   q        - Stop track

Options :
   -c [IP]  : scan continu
   -m [IP]  : affiche une carte avec infos IP cible et utilisateur
"""

@REGISTRY.register("iptracker", help_text=IPT_HELP, summary="Tracker IP (-c continu, -m carte folium)")
def _iptracker(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : iptracker -m <IP_cible>")
        return

    if argv[1] == "-c":
        live_ip_tracker(argv[2], 3)
    elif argv[1] == "-m":
        target_ip = argv[2]
        my_ip = requests.get("https://api.ipify.org").text
        show_map_with_positions(my_ip, target_ip)
    else:
        live_ip_tracker(argv[1])


@REGISTRY.register("ping", help_text="ping <ip/url>    - Ping d'une IP ou URL")
def _ping(ctx, argv, raw):
    from Tools.ping.ping import run_ping_command
    run_ping_command(raw)