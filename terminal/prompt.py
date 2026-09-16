"""Prompt style Kali (extrait de main.py lignes 465-481 et 456-461)."""
from terminal.context import Context

RESET = "\033[0m"
GREEN = "\033[92m"
BLUE = "\033[94m"


def get_prompt(ctx: Context) -> str:
    """
    Prompt style Kali colorisé :
    - Crochets / parenthèses en vert, host en bleu, chemin en vert.
    """
    host = "nebula"
    path_display = ctx.vfs.get_path()

    line1 = f"{GREEN}┌──[{RESET}{BLUE}{host}{RESET}{GREEN}]─[{path_display}{GREEN}]{RESET}"
    line2 = f"{GREEN}└──╼{RESET} $ "
    return f"{line1}\n{line2}"