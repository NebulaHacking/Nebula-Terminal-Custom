"""Commandes système (M4) — rm, clean, tools.

Portage des branches de l'ancien main.py : rm (1131-1138), clean (864-869),
tools (967-990). Moteurs dans Tools/systemtools.py et Tools/toolstxt.py.
"""
from terminal.registry import REGISTRY


@REGISTRY.register(
    "rm",
    aliases=("exec",),
    help_text=(
        "rm <commande>    - Exécuter une commande SYSTÈME RÉELLE (alias : exec)\n"
        "\n"
        "⚠  Ce n'est PAS 'remove' : la commande est passée telle quelle au shell\n"
        "   (cmd.exe / sh). Exemple : rm dir C:\\Users\n"
        "   Pour supprimer un fichier VIRTUEL, utilisez le FS virtuel à la place."
    ),
)
def _rm(ctx, argv, raw):
    from Tools.systemtools import execute_command_real

    if len(argv) < 2:
        print("Syntaxe => rm 'commande'  (ou exec 'commande')")
        return
    print("Passage en mode réel")
    commande = " ".join(argv[1:])  # recolle tout ce qui vient après 'rm'
    execute_command_real(commande)


@REGISTRY.register("clean", help_text="clean            - netoie le system")
def _clean(ctx, argv, raw):
    from Tools.systemtools import clean_pycache
    clean_pycache()


@REGISTRY.register("tools", help_text="tools            - Liste des outils disponibles")
def _tools(ctx, argv, raw):
    from Tools.toolstxt import lire_tools_txt
    print(lire_tools_txt())