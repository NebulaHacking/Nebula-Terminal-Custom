"""Commandes réseau (M3) — scan, iptracker, ping.

Portage des branches de l'ancien main.py : scan (1189-1290), iptracker (1144-1156),
ping (937-938). Les moteurs sont dans Tools/portscan.py et Tools/iptracker.py ;
ce module ne fait que l'adaptation CLI (flags, arguments).
"""
import requests

from terminal.registry import REGISTRY
from Tools.portscan import scan_ports
from Tools.iptracker import live_ip_tracker, show_map_with_positions


SCAN_HELP = """ -- Scan v1.1 --

Syntaxe :
   scan [IP] [min] [max]  : ports 1-1024 (ou la plage donnée)
   -f [IP] [min] [max]    : analyse rapide
   -a [IP]                : tous les ports (1-65535, ~1 à 2 minutes)
   -s [IP]                : analyse discrète (lente : une connexion à la fois)

Ctrl+C arrête le scan.
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


IPT_HELP = """ -- IPTracker v1.1 --

   iptracker <IP ou domaine>  : pays, ville, fournisseur, proxy/VPN, hébergeur
   iptracker -c <IP>          : suivi continu (Ctrl+C pour arrêter)
   iptracker -m <IP>          : carte « moi / cible » (fichier HTML)

Position approximative (base publique ip-api.com) : ville au mieux, jamais une adresse.
"""

@REGISTRY.register("iptracker", help_text=IPT_HELP, summary="Infos publiques d'une IP : pays, fournisseur, proxy (-c continu, -m carte)")
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
        from terminal.blocks import print_blocks
        from Tools.iptracker import ip_blocks
        print_blocks(ip_blocks(argv[1]))


@REGISTRY.register("ping", help_text="ping <ip/url>    - Ping d'une IP ou URL")
def _ping(ctx, argv, raw):
    from Tools.ping.ping import run_ping_command
    from terminal import events
    # Dashboard ou Nebula IA : personne ne peut faire Ctrl+C, donc pas de ping infini.
    if getattr(events.local, "quiet", False) and not {"-c", "--count"} & set(argv):
        raw += " -c 4"
    run_ping_command(raw)