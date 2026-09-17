"""Ponts vers les outils externes (M5) — dirb, shadowviper, nexariescan, netstorm,
browser, nebulers, nebulaGui, nebula_ia, blackledger, filmux.

Portage des branches de l'ancien main.py. Tous les imports sont LAZY (dans les
handlers) : chaque module externe peut être lourd (keyboard, PyQt5, sounddevice…)
ou manquer — le terminal démarre et fonctionne sans eux.

Outils supprimés au refactor (approuvé « supprimer le reste ») :
    - blacknova (100% simulé)  — hook absent ici
    - k3d (stub)               — hook absent ici
"""
from terminal.registry import REGISTRY


DIRB_HELP = """ -- Dirb v1.0 --

Hotkeys :
   q        - Stop scan
   r        - Stats restantes

Options :
   dirb <url>              - scan avec la wordlist intégrée (~100 mots)
   dirb <url> <wordlist>   - scan avec un fichier wordlist externe
   dirb -m <url>           - mode minimal (10 mots testés)
   dirb -w <url> <wordlist> - scan avec wordlist externe

Exemples :
   dirb https://example.com
   dirb https://example.com DirbWordListe/baseWord.txt
   dirb -w https://example.com DirbWordListe/mots.txt
"""

SV_HELP = """ShadowViper v1.0
By Ma4g

Usage :
   shadowviper [paramètre] <cible>

Notes :
   ShadowViper est un outil avancé de collecte d'informations et d'analyse de vulnérabilités.
   Utilisation responsable recommandée.

Hotkeys :
   q        - Quitter
   h        - Help
   r        - Stats restantes
   s        - Sauvegarder les stats

Options :
   (à remplir selon les fonctionnalités ajoutées)

Exemples :
   shadowviper -scan 192.168.0.1
"""


@REGISTRY.register("dirb", help_text=DIRB_HELP,
                   summary="Bruteforce de répertoires (-w wordlist, -m minimal)")
def _dirb(ctx, argv, raw):
    from Tools.dirb import dirb

    if len(argv) == 1:
        # Message exact de l'original (typo volontairement conservée)
        print("lunch dirb.help for having help")
        return
    if argv[1] == "-w":
        url = argv[2]
        wordlist = argv[3]
        dirb(url, wordlist=wordlist, minimal=False)
    elif argv[1] == "-m":
        url = argv[2]
        dirb(url, wordlist=None, minimal=True)
    else:
        url = argv[1]
        dirb(url)


@REGISTRY.register("shadowviper", help_text=SV_HELP,
                   summary="Collecte d'infos et analyse de vulnérabilités")
def _shadowviper(ctx, argv, raw):
    from Tools.shadowviper import run_shadowviper

    if len(argv) > 1:
        run_shadowviper(argv[1])
    else:
        user_input = input("shadowviper > Entrez une IP, domaine, URL, ASN ou email : ").strip()
        run_shadowviper(user_input)


@REGISTRY.register("nexariescan", help_text="nexariescan - Lancer le scan Nexari (XSS & liens)")
def _nexariescan(ctx, argv, raw):
    from Tools.nexariescan import run_scan

    target = input("URL cible (ex: https://example.com) : ").strip()
    delay = input("Delay entre requêtes (default 0.5s) : ").strip()
    delay = float(delay) if delay else 0.5

    print(f"Lancement du scan Nexari sur {target}...")
    results = run_scan(target, delay=delay, verbose=True, safe_only=True)

    print("\n=== Résumé du scan ===")
    print("Liens trouvés :", results.get('links_found'))
    print("Tests de liens effectués :", results.get('tested_links_count'))
    print("Tests de formulaires effectués :", results.get('tested_forms_count'))
    print("XSS détectés dans les liens :", len(results.get('xss_in_links', [])))
    for l in results.get('xss_in_links', []):
        print(" ->", l)
    print("XSS détectés dans les formulaires :", len(results.get('xss_in_forms', [])))
    for f in results.get('xss_in_forms', []):
        print(" -> page:", f['page'], " action:", f['form_action'])


@REGISTRY.register("netstorm", help_text="netstorm <IP> [PORT] [DUREE] [THREADS] - Attaque réseau (légal requis)")
def _netstorm(ctx, argv, raw):
    from ToolsFunction import netstorm

    demande = input("Cet outil peut être dangereux voulez vous continuer (y/n) ? ")
    if demande != "y":
        return
    if len(argv) >= 2:
        ip = argv[1]
        port = int(argv[2]) if len(argv) >= 3 else 80
        duration = int(argv[3]) if len(argv) >= 4 else 10
        threads = int(argv[4]) if len(argv) >= 5 else 50
        netstorm.run(ip, port, duration, threads)
    else:
        print("Utilisation : netstorm <IP> [PORT] [DUREE] [THREADS]")


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


@REGISTRY.register("nebulaGui", help_text="nebulaGui - Lancer l'interface graphique Nebula")
def _nebula_gui(ctx, argv, raw):
    import NebulaGui.Gui
    NebulaGui.Gui.launch_nebula_gui()


@REGISTRY.register("nebula_ia", help_text="nebula_ia - L'IA du NTC (EN COURS DE DEVELOPPEMENT !!!)")
def _nebula_ia(ctx, argv, raw):
    import Nebula_IA.main as nebula_module
    print("Lancement de Nebula IA...")
    nebula_module.launch()


@REGISTRY.register("nebula_ia_install", help_text="nebula_ia_install - Install Nebula IA")
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