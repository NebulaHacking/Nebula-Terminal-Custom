"""Ponts vers les outils externes (M5) — dirb, shadowviper, nexariescan,
browser, nebulers, nebulaGui, blackledger, filmux.

Portage des branches de l'ancien main.py. Tous les imports sont LAZY (dans les
handlers) : chaque module externe peut être lourd (keyboard, PyQt5…)
ou manquer — le terminal démarre et fonctionne sans eux.

Outils supprimés au refactor (approuvé « supprimer le reste ») :
    - blacknova (100% simulé)  — hook absent ici
    - k3d (stub)               — hook absent ici
"""
from terminal.registry import REGISTRY


DIRB_HELP = """ -- Dirb v1.1 --

Cherche les dossiers et fichiers cachés d'un site (20 requêtes en parallèle).
Ctrl+C arrête le scan.

Options :
   dirb <url>               - wordlist par défaut (DirbWordListe/baseWord.txt)
   dirb <url> <wordlist>    - avec un fichier wordlist
   dirb -m <url>            - mode minimal (10 mots testés)
   dirb -w <url> <wordlist> - identique à dirb <url> <wordlist>

Seuls les chemins qui existent sont affichés (200, redirections, 401/403...).

Exemples :
   dirb https://example.com
   dirb https://example.com mots.txt
"""

SV_HELP = """shadowviper <cible>

Collecte d'informations sur une IP, un domaine, une URL, un ASN (AS15169) ou une adresse e-mail :
géolocalisation, fournisseur, système autonome, WHOIS, DNS, ports courants, ping et traceroute,
puis avis du modèle local (scikit-learn, facultatif : python launch.py --full).

Exemple :
   shadowviper example.com
   shadowviper 8.8.8.8 --json
"""


@REGISTRY.register("dirb", help_text=DIRB_HELP,
                   summary="Bruteforce de répertoires (-w wordlist, -m minimal)")
def _dirb(ctx, argv, raw):
    from Tools.dirb import dirb

    if len(argv) == 1:
        # Message exact de l'original (typo volontairement conservée)
        print("lunch dirb.help for having help")
        return
    from terminal.banner import tool_banner
    tool_banner("DIRB", "Bruteforce de répertoires web")
    if argv[1] == "-w":
        url = argv[2]
        wordlist = argv[3]
        dirb(url, wordlist=wordlist, minimal=False)
    elif argv[1] == "-m":
        url = argv[2]
        dirb(url, wordlist=None, minimal=True)
    else:
        dirb(argv[1], wordlist=argv[2] if len(argv) > 2 else None)


@REGISTRY.register("shadowviper", help_text=SV_HELP,
                   summary="Collecte d'infos et analyse de vulnérabilités")
def _shadowviper(ctx, argv, raw):
    from terminal.blocks import local, print_blocks
    from Tools.shadowviper import affichage_viper, investigate

    if len(argv) < 2:
        print("Usage : shadowviper <IP | domaine | URL | ASN | e-mail>   (shadowviper.help)")
        return
    if not getattr(local, "json", False):
        affichage_viper()
    print_blocks(investigate(argv[1]))


@REGISTRY.register("nexariescan", help_text=(
    "nexariescan <url> [--delay 0.5] [--pages 50] [--post]\n"
    "\n"
    "Parcourt le site (même domaine) puis cherche les XSS réfléchis : paramètres d'URL et formulaires.\n"
    "  --delay   pause entre deux requêtes, en secondes (défaut 0.5)\n"
    "  --pages   nombre maximal de pages parcourues (défaut 50)\n"
    "  --post    teste aussi les formulaires POST (par défaut : GET seulement, moins intrusif)\n"
    "\n"
    "Uniquement sur un site que vous êtes autorisé à tester (mission ouverte = périmètre appliqué)."),
    summary="XSS réfléchis : paramètres d'URL et formulaires (--json)")
def _nexariescan(ctx, argv, raw):
    from terminal.blocks import print_blocks
    from Tools.nexariescan import scan_blocks

    args, opts = [], {"--delay": "0.5", "--pages": "50"}
    it = iter(argv[1:])
    for a in it:
        if a in opts:
            opts[a] = next(it, opts[a])
        elif a != "--post":
            args.append(a)
    if not args:
        print("Usage : nexariescan <url> [--delay 0.5] [--pages 50] [--post]   (nexariescan.help)")
        return
    from terminal.banner import tool_banner
    tool_banner("NEXARIE", "XSS réfléchis · paramètres d'URL et formulaires")
    print_blocks(scan_blocks(args[0], float(opts["--delay"]), int(opts["--pages"]), "--post" in argv))


@REGISTRY.register("browser", help_text="browser - navigateur web nebula sécurisé (run as non root)")
def _browser(ctx, argv, raw):
    from Tools.browser.Nebula_browser import browse

    print("==== Nebula Secure Browser ====")
    print("========= Version 1.0 =========")
    print("")
    url_choice = input("URL : ")
    ctx.browser_history.append(url_choice)
    try:
        browse(url_choice)
    except Exception:
        print("url invalide")


@REGISTRY.register("browser.history", help_text="browser.history - Historique du navigateur")
def _browser_history(ctx, argv, raw):
    print(ctx.browser_history)


@REGISTRY.register("nebulers", help_text="nebulers - Lancer le jeu Nebulers")
def _nebulers(ctx, argv, raw):
    from Tools.games.nebulers import Menu_Principale
    Menu_Principale()


@REGISTRY.register("nebulaGui", aliases=("dashboard", "gui"), help_text=(
    "nebulaGui        - Ouvre le dashboard web de Nebula dans le navigateur (alias : dashboard, gui)\n"
    "\n"
    "Activité du terminal en direct, console, recon en un clic, palette de commandes (Ctrl+K).\n"
    "Le dashboard n'est accessible que depuis ce PC (127.0.0.1) et s'arrête avec le terminal."),
    summary="Dashboard web en direct (s'ouvre dans le navigateur)")
def _nebula_gui(ctx, argv, raw):
    import webbrowser
    from NebulaGui import server

    url = server.start(ctx, REGISTRY)
    print(f"Dashboard Nebula : {url}")
    webbrowser.open(url)


@REGISTRY.register("nebula_ia_install", help_text="nebula_ia_install - Installe Ollama et un modèle local pour Nebula IA (commande ia)")
def _nebula_ia_install(ctx, argv, raw):
    from Nebula_IA.install import main
    main()


@REGISTRY.register("blackledger", help_text="blackledger - Créateur de wordslist grace a ia")
def _blackledger(ctx, argv, raw):
    from Tools.BlackLedger.BlackLedger import interactive_generate
    interactive_generate()


@REGISTRY.register("filmux", help_text="filmux - Permet de regarder des films gratuitement dans une interface GUI")
def _filmux(ctx, argv, raw):
    from Tools.filmux.filmux_gui import main
    main()