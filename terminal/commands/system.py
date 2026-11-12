"""Commandes système (M4) — exec, clean, tools.

Portage des branches de l'ancien main.py : rm (1131-1138), clean (864-869),
tools (967-990). Moteurs dans Tools/systemtools.py et Tools/toolstxt.py.
"""
from terminal.registry import REGISTRY


@REGISTRY.register(
    "exec",
    aliases=("!",),
    summary="Lancer une vraie commande système (cmd.exe / sh)",
    help_text=(
        "exec <commande>    - Exécuter une commande SYSTÈME RÉELLE (alias : !)\n"
        "\n"
        "La commande est passée telle quelle au shell (cmd.exe sous Windows, sh sous Linux).\n"
        "Exemples : exec ipconfig    |    ! dir C:\\Users\n"
        "Pour supprimer un fichier de l'espace de travail Nebula : rm <fichier>"
    ),
)
def _exec(ctx, argv, raw):
    from Tools.systemtools import execute_command_real

    if len(argv) < 2:
        print("Usage : exec <commande système>")
        return
    execute_command_real(raw.split(None, 1)[1])


@REGISTRY.register("clean", help_text="clean            - netoie le system")
def _clean(ctx, argv, raw):
    from Tools.systemtools import clean_pycache
    clean_pycache()


@REGISTRY.register("tools", help_text="tools            - Liste des outils disponibles")
def _tools(ctx, argv, raw):
    from Tools.toolstxt import lire_tools_txt
    print(lire_tools_txt())