"""Prompt style Kali (extrait de main.py lignes 465-481 et 456-461)."""
from terminal.context import Context
from terminal.theme import get_prompt_colors


def get_prompt(ctx: Context) -> str:
    """
    Prompt style Kali colorisé avec support des thèmes dynamiques.
    Format : [user@nebula]-[path] compatible Windows
    """
    colors = get_prompt_colors()
    primary = colors["primary"]
    secondary = colors["secondary"]
    reset = colors["reset"]

    user = ctx.current_user
    path_display = ctx.vfs.get_path()

    # Format Kali ASCII-only pour compatibilité Windows
    line1 = f"{primary}[{reset}{secondary}{user}@nebula{reset}{primary}]-[{reset}{path_display}{primary}]{reset}"
    line2 = f"{primary}$ {reset}"
    return f"{line1}\n{line2}"

