"""Commandes terminal internes (M1) — exit, clear, help, history, rand, time, color, nebula_ascii.

Portage des branches de l'ancien main.py : exit (704), clear (709), help (718),
time (962), rand (1082), history (1090), color (1019-1038), nebula_ascii (1057).
"""
import os
import random
import time

from terminal.registry import REGISTRY

# ---------------------------------------------------------------------
# Sortie / effacement
# ---------------------------------------------------------------------
@REGISTRY.register(
    "exit",
    aliases=("quit",),
    help_text="exit          - Quitter le terminal",
)
def _exit(ctx, argv, raw):
    ctx.should_exit = True


@REGISTRY.register("clear", help_text="clear         - Effacer l'écran")
def _clear(ctx, argv, raw):
    os.system("cls" if os.name == "nt" else "clear")


# ---------------------------------------------------------------------
# Aide
# ---------------------------------------------------------------------
# Catégories affichées dans le tableau `help`, déduites du module source de chaque handler.
_HELP_CATEGORIES = (
    ("terminal.commands.builtins",    "Noyau",        "cyan"),
    ("terminal.commands.filesystem",  "Fichiers",     "green"),
    ("terminal.commands.network",     "Réseau",       "magenta"),
    ("terminal.commands.system",      "Système",      "yellow"),
    ("terminal.commands.misc",        "Utilitaires",  "blue"),
    ("terminal.commands.external",    "Outils",       "red"),
)


def _describe(cmd) -> str:
    """Description courte d'une commande : summary explicite, sinon la première
    ligne utile de son help_text (on saute les titres du type `-- x v1.0 --`)."""
    if cmd.summary:
        return cmd.summary
    for line in cmd.help_text.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        return line
    return cmd.help_text.strip()


@REGISTRY.register("help", help_text="help          - Liste des commandes disponibles",
                   summary="Affiche la liste des commandes en tableau")
def _help(ctx, argv, raw):
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        # Fallback : liste simple (rich absent)
        for cmd in REGISTRY.commands():
            print(f"  {cmd.name:<16} {_describe(cmd)}")
        return

    # Ordre stable des catégories (défaut en fin de tableau)
    order = {mod: i for i, (mod, _, _) in enumerate(_HELP_CATEGORIES)}
    mods = {mod for mod, _, _ in _HELP_CATEGORIES}

    def sort_key(c):
        return (order.get(c.func.__module__, len(mods)), c.name)

    console = Console()
    tbl = Table(title="Nebula — Commandes disponibles", border_style="bright_blue",
                header_style="bold", show_lines=False, pad_edge=False)
    tbl.add_column("Commande", style="bold green", no_wrap=True, min_width=18)
    tbl.add_column("Description", style="white")

    current = None
    for cmd in sorted(REGISTRY.commands(), key=sort_key):
        label, style = next(
            ((lab, st) for mod, lab, st in _HELP_CATEGORIES if mod == cmd.func.__module__),
            ("Divers", "white"),
        )
        if label != current:
            current = label
            tbl.add_row(f"[{style} bold]── {label} ──[/]", "", style=f"{style} dim")
        tbl.add_row(cmd.name, _describe(cmd))

    console.print(tbl)
    console.print("[dim]<cmd>.help pour l'aide détaillée d'un outil[/]")


# ---------------------------------------------------------------------
# Utilitaires d'affichage
# ---------------------------------------------------------------------
@REGISTRY.register("history", help_text="history        - Afficher l'historique des commandes")
def _history(ctx, argv, raw):
    # ctx.history contient déjà `raw` (append par le dispatcher) — parité avec l'original.
    print(ctx.history)


@REGISTRY.register("time", aliases=("heure",), help_text="time           - Afficher l'heure actuelle en ASCII")
def _time_cmd(ctx, argv, raw):
    heure = time.strftime("%H:%M:%S")
    try:
        import pyfiglet
        ascii_heure = pyfiglet.figlet_format(heure)
    except ImportError:
        print(heure)
        return
    print(ascii_heure, end="")


@REGISTRY.register("nebula_ascii", aliases=("ascii",), help_text="nebula_ascii   - Afficher l'ASCII art Nebula")
def _nebula_ascii(ctx, argv, raw):
    from terminal.banner import affichage_nebula
    affichage_nebula()


# ---------------------------------------------------------------------
# Couleurs console Windows
# ---------------------------------------------------------------------
@REGISTRY.register("color", help_text="color <n>      - Changer la couleur (0=reset, 2=vert, 3=cyan, 4=rouge, Windows)")
def _color(ctx, argv, raw):
    from Tools.systemtools import set_console_color

    if os.name != "nt":
        print("color est réservé à Windows (cmd.exe).")
        return
    try:
        set_console_color(argv[1] if len(argv) > 1 else "")
    except ValueError:
        print("Usage : color 0 | 2 | 3 | 4")


# ---------------------------------------------------------------------
# Nombre aléatoire
# ---------------------------------------------------------------------
@REGISTRY.register("rand", help_text="rand <a> <b>   - Générer un nombre aléatoire entre a et b")
def _rand(ctx, argv, raw):
    try:
        min_val = int(argv[1])
        max_val = int(argv[2])
        print(random.randint(min_val, max_val))
    except (ValueError, IndexError):
        print("Usage : rand <min> <max>")