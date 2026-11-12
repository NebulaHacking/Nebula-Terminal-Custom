"""Bannières ASCII de Nebula + infos système (extrait de main.py 547-655).

`show_nebula()` = bannière d'accueil avec panneau d'infos système.
`affichage_nebula()` / `affichage_scan()` = art ASCII standalone (commandes).
"""
import getpass
import os
import platform
import socket


from Tools.sysinfo import get_gpu, get_packages, get_resolution, get_uptime
from terminal import __version__
from terminal.theme import get_prompt_colors, paint, banner_colors


def show_nebula() -> None:
    """Logo N + panneau d'infos système avec thème dynamique bicolore."""
    colors = get_prompt_colors()
    primary = colors["primary"]
    secondary = colors["secondary"]
    reset = colors["reset"]

    nebula_logo = [
        f"",
        f"",
        f"{primary} /$$   /$${reset}          ",
        f"{primary}| $$$ | $${reset}          ",
        f"{primary}| $$$$| $${reset}          ",
        f"{primary}| $$ $$ $${reset}          ",
        f"{primary}| $$  $$$${reset}          ",
        f"{primary}| $$\\  $$${reset}          ",
        f"{primary}| $$ \\  $${reset}          ",
        f"{primary}|__/  \\__/ebula{reset}     ",
        f"",
        "",
        ""
    ]

    user = getpass.getuser()
    host = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    kernel = platform.version()
    uptime = get_uptime()
    packages = get_packages()
    shell = os.environ.get("SHELL") if platform.system() != "Windows" else os.environ.get("COMSPEC", "cmd.exe")
    resolution = get_resolution()
    terminal = os.environ.get("TERM", "Unknown") if platform.system() != "Windows" else "cmd.exe/PowerShell"
    cpu = platform.processor()
    gpu = get_gpu()
    try:
        import psutil
        memory = f"{round(psutil.virtual_memory().total / (1024**3))}GB"
    except Exception:
        memory = "N/A"

    info_labels = [
        "Nebula:", "User:", "OS:", "Kernel:", "Uptime:", "Packages:",
        "Shell:", "Resolution:", "Terminal:", "CPU:", "GPU:", "Memory:"
    ]
    info_values = [
        f"v{__version__}", f"{user}@{host}", os_info, kernel, uptime, packages,
        shell, resolution, terminal, cpu, gpu, memory
    ]

    max_lines = max(len(nebula_logo), len(info_labels))
    while len(nebula_logo) < max_lines:
        nebula_logo.append("")
    while len(info_labels) < max_lines:
        info_labels.append("")
    while len(info_values) < max_lines:
        info_values.append("")

    grad = banner_colors()  # le logo suit le dégradé du thème, ligne par ligne
    nebula_logo = [l.replace(primary, grad[min(i * len(grad) // max_lines, len(grad) - 1)]) for i, l in enumerate(nebula_logo)]
    for i in range(max_lines):
        print(f"{nebula_logo[i]:<20} {secondary}{info_labels[i]:<12}{reset} {primary}{info_values[i]}{reset}")


def affichage_nebula() -> None:
    nebula_ascii = r"""

            _____                    _____                    _____                    _____                    _____            _____
        /\    \                  /\    \                  /\    \                  /\    \                  /\    \          /\    \
        /::\____\                /::\    \                /::\    \                /::\____\                /::\____\        /::\    \
        /::::|   |               /::::\    \              /::::\    \              /:::/    /               /:::/    /       /::::\    \
        /:::::|   |              /::::::\    \            /::::::\    \            /:::/    /               /:::/    /       /::::::\    \
    /::::::|   |             /:::/\:::\    \          /:::/\:::\    \          /:::/    /               /:::/    /       /:::/\:::\    \
    /:::/|::|   |            /:::/__\:::\    \        /:::/__\:::\    \        /:::/    /               /:::/    /       /:::/__\:::\    \
    /:::/ |::|   |           /::::\   \:::\    \      /::::\   \:::\    \      /:::/    /               /:::/    /       /::::\   \:::\    \
    /:::/  |::|   | _____    /::::::\   \:::\    \    /::::::\   \:::\    \    /:::/    /      _____    /:::/    /       /::::::\   \:::\    \
/:::/   |::|   |/\    \  /:::/\:::\   \:::\    \  /:::/\:::\   \:::\ ___\  /:::/____/      /\    \  /:::/    /       /:::/\:::\   \:::\    \
/:: /    |::|   /::\____\/:::/__\:::\   \:::\____\/:::/__\:::\   \:::|    ||:::|    /      /::\____\/:::/____/       /:::/  \:::\   \:::\____\
\::/    /|::|  /:::/    /\:::\   \:::\   \::/    /\:::\   \:::\  /:::|____||:::|____\     /:::/    /\:::\    \       \::/    \:::\  /:::/    /
\/____/ |::| /:::/    /  \:::\   \:::\   \/____/  \:::\   \:::\/:::/    /  \:::\    \   /:::/    /  \:::\    \       \/____/ \:::\/:::/    /
        |::|/:::/    /    \:::\   \:::\    \       \:::\   \::::::/    /    \:::\    \ /:::/    /    \:::\    \               \::::::/    /
        |::::::/    /      \:::\   \:::\____\       \:::\   \::::/    /      \:::\    /:::/    /      \:::\    \               \::::/    /
        |:::::/    /        \:::\   \::/    /        \:::\  /:::/    /        \:::\__/:::/    /        \:::\    \              /:::/    /
        |::::/    /          \:::\   \/____/          \:::\/:::/    /          \::::::::/    /          \:::\    \            /:::/    /
        /:::/    /            \:::\    \               \::::::/    /            \::::::/    /            \:::\    \          /:::/    /
        /:::/    /              \:::\____\               \::::/    /              \::::/    /              \:::\____\        /:::/    /
        \::/    /                \::/    /                \::/____/                \::/____/                \::/    /        \::/    /
        \/____/                  \/____/                  ~~                       ~~                       \/____/          \/____/

    """
    print(paint(nebula_ascii))


def affichage_scan() -> None:
    scan_ascii = r"""
        ______        _____         _____  _____   ______
    ___|\     \   ___|\    \    ___|\    \|\    \ |\     \
    |    |\     \ /    /\    \  /    /\    \\\    \| \     \
    |    |/____/||    |  |    ||    |  |    |\|    \  \     |
___|    \|   | ||    |  |____||    |__|    | |     \  |    |
|    \    \___|/ |    |   ____ |    .--.    | |      \ |    |
|    |\     \    |    |  |    ||    |  |    | |    |\ \|    |
|\ ___\|_____|   |\ ___\/    /||____|  |____| |____||\_____/|
| |    |     |   | |   /____/ ||    |  |    | |    |/ \|   ||
\|____|_____|    \|___|    | /|____|  |____| |____|   |___|/
    \(    )/        \( |____|/   \(      )/     \(       )/
    '    '          '   )/       '      '       '       '
                        '
    """
    print(paint(scan_ascii))


# ---------------------------------------------------------------------
# Bannières des outils qui n'en avaient pas (police « ANSI Shadow »)
# ---------------------------------------------------------------------
_FONT = {
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "B": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "F": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "██║     ", "╚═╝     "],
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "Q": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║▄▄ ██║", "╚██████╔╝", " ╚══▀▀═╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "V": ["██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "],
    "W": ["██╗    ██╗", "██║    ██║", "██║ █╗ ██║", "██║███╗██║", "╚███╔███╔╝", " ╚══╝╚══╝ "],
    "X": ["██╗  ██╗", "╚██╗██╔╝", " ╚███╔╝ ", " ██╔██╗ ", "██╔╝ ██╗", "╚═╝  ╚═╝"],
    " ": ["   "] * 6,
}


def big(text: str) -> str:
    """`big("DIRB")` -> 6 lignes de grandes lettres (seules les lettres de _FONT existent)."""
    return "\n".join("".join(_FONT[c][row] for c in text.upper()) for row in range(6))


def tool_banner(word: str, subtitle: str = "") -> None:
    """Bannière d'un outil, au dégradé du thème. Rien avec --json, ni depuis le dashboard ou Nebula IA
    (sortie capturée : la bannière n'y servirait à rien). Console sans Unicode : texte simple."""
    from terminal import blocks, events

    if getattr(blocks.local, "json", False) or getattr(events.local, "quiet", False):
        return
    art = "\n" + big(word) + (f"\n  {subtitle}" if subtitle else "") + "\n"
    try:
        print(paint(art))
    except UnicodeEncodeError:
        print(f"== {word} ==" + (f"  {subtitle}" if subtitle else ""))
