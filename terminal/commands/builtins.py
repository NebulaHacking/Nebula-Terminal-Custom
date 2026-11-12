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
    ("terminal.commands.ia",          "Nebula IA",    "bright_magenta"),
    ("terminal.commands.mission",     "Mission",      "bright_yellow"),
    ("terminal.commands.analysis",    "Analyse",      "bright_cyan"),
    ("terminal.commands.recon",       "Reconnaissance", "bright_magenta"),
    ("terminal.commands.crypto",      "Crypto",       "bright_green"),
    ("terminal.commands.shell",       "Shell",        "white"),
    ("terminal.commands.system",      "Système",      "yellow"),
    ("terminal.commands.misc",        "Utilitaires",  "blue"),
    ("terminal.commands.external",    "Outils",       "red"),
)


def _plain(text: str) -> str:
    """Minuscules sans accents, pour que `help reseau` trouve « Réseau »."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


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


@REGISTRY.register("help", help_text="help          - Liste des commandes disponibles\nhelp <mot>    - Seulement une catégorie ou les commandes contenant ce mot (ex : help crypto)",
                   summary="Affiche la liste des commandes en tableau")
def _help(ctx, argv, raw):
    from terminal.theme import get_rich_style

    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        # Fallback : liste simple (rich absent)
        for cmd in REGISTRY.commands():
            print(f"  {cmd.name:<16} {_describe(cmd)}")
        return

    # Récupère les styles du thème
    theme_styles = get_rich_style()
    border_style = theme_styles["border_style"]
    title_style = theme_styles["title_style"]

    # Ordre stable des catégories (défaut en fin de tableau)
    order = {mod: i for i, (mod, _, _) in enumerate(_HELP_CATEGORIES)}
    mods = {mod for mod, _, _ in _HELP_CATEGORIES}

    def sort_key(c):
        return (order.get(c.func.__module__, len(mods)), c.name)

    console = Console()
    tbl = Table(title="Nebula — Commandes disponibles", border_style=border_style,
                header_style=title_style, show_lines=False, pad_edge=False)
    tbl.add_column("Commande", style="bold", no_wrap=True, min_width=18)
    tbl.add_column("Description", style="white")

    # `help <mot>` : ne garde que les lignes dont la catégorie ou le nom contient le mot.
    wanted = argv[1].lower() if len(argv) > 1 else ""
    current = None
    for cmd in sorted(REGISTRY.commands(), key=sort_key):
        label, style = next(
            ((lab, st) for mod, lab, st in _HELP_CATEGORIES if mod == cmd.func.__module__),
            ("Divers", "white"),
        )
        if wanted and wanted not in _plain(label) and wanted not in cmd.name.lower():
            continue
        if label != current:
            current = label
            tbl.add_row(f"[{style} bold]── {label} ──[/]", "", style=f"{style} dim")
        tbl.add_row(cmd.name, _describe(cmd))

    if wanted and current is None:
        console.print(f"Aucune commande ni catégorie ne contient '{wanted}'.")
        return
    console.print(tbl)
    console.print("[dim]<cmd>.help : aide détaillée d'un outil  |  help <mot> : filtrer (ex : help crypto)[/]")


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
# Thème
# ---------------------------------------------------------------------
@REGISTRY.register("theme", help_text="theme <nom>     - Changer le thème actif (ex: micha, redark)")
def _theme(ctx, argv, raw):
    from terminal.theme import _load_themes, get_theme_name, paint, set_theme, swatch

    themes = _load_themes()
    if len(argv) < 2:  # aperçu : une barre de couleurs par thème, le thème actif marqué
        current = get_theme_name()
        print()
        for name, t in themes.items():
            mark = "*" if name == current else " "
            print(f"  {mark} {name:<10} {swatch(name)}  {t.get('description', '')}")
        print("\n  Usage : theme <nom>   (theme random = au hasard)\n")
        return

    name = argv[1].lower()
    if name == "random":
        name = random.choice([n for n in themes if n != get_theme_name()] or list(themes))
    if not set_theme(name):
        print(f"Échec : le thème '{name}' n'existe pas. Tapez  theme  pour voir la liste.")
        return
    print(paint("  _  _     _         _\n | \\| |___| |__ _  _| |__ _\n | .` / -_) '_ \\ || | / _` |\n |_|\\_\\___|_.__/\\_,_|_\\__,_|"))
    print(f"  Thème « {themes[name].get('name', name)} » appliqué (sauvegardé avec votre profil).")



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