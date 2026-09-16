"""Bannières ASCII de Nebula + infos système (extrait de main.py 547-655).

`show_nebula()` = bannière d'accueil avec panneau d'infos système.
`affichage_nebula()` / `affichage_scan()` = art ASCII standalone (commandes).
"""
import getpass
import os
import platform
import socket

from colorama import Fore

from Tools.sysinfo import get_gpu, get_packages, get_resolution, get_uptime

from terminal.prompt import BLUE, GREEN, RESET


def show_nebula() -> None:
    """Logo N + panneau d'infos système (portage identique de l'original)."""
    nebula_logo = [
        f"",
        f"",
        f"{GREEN} /$$   /$${RESET}          ",
        f"{GREEN}| $$$ | $${RESET}          ",
        f"{GREEN}| $$$$| $${RESET}          ",
        f"{GREEN}| $$ $$ $${RESET}          ",
        f"{GREEN}| $$  $$$${RESET}          ",
        f"{GREEN}| $$\\  $$${RESET}          ",
        f"{GREEN}| $$ \\  $${RESET}          ",
        f"{GREEN}|__/  \\__/ebula{RESET}     ",
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
        "User:", "OS:", "Kernel:", "Uptime:", "Packages:",
        "Shell:", "Resolution:", "Terminal:", "CPU:", "GPU:", "Memory:"
    ]
    info_values = [
        f"{user}@{host}", os_info, kernel, uptime, packages,
        shell, resolution, terminal, cpu, gpu, memory
    ]

    max_lines = max(len(nebula_logo), len(info_labels))
    while len(nebula_logo) < max_lines:
        nebula_logo.append("")
    while len(info_labels) < max_lines:
        info_labels.append("")
    while len(info_values) < max_lines:
        info_values.append("")

    for i in range(max_lines):
        print(f"{nebula_logo[i]:<20} {BLUE}{info_labels[i]:<12}{RESET} {GREEN}{info_values[i]}{RESET}")


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
    print(Fore.LIGHTRED_EX + nebula_ascii)


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
    print(Fore.WHITE + scan_ascii)