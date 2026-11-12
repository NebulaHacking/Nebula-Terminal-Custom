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
    from terminal import mission
    if mission.active():  # rappel permanent : les commandes sont limitées et enregistrées
        path_display += f"{primary}]-[{reset}mission:{mission.active()['name']}"

    # Dernière commande : en rouge si elle a échoué, durée si elle a été lente.
    status = ""
    if ctx.last_status != "ok":
        status += f"{primary}-[{reset}\033[91m{ctx.last_status}{reset}{primary}]{reset}"
    if ctx.last_duration >= 2:
        status += f"{primary}-[{reset}{colors['accent']}{ctx.last_duration:.1f}s{reset}{primary}]{reset}"

    # Format Kali ASCII-only pour compatibilité Windows
    line1 = f"{primary}[{reset}{secondary}{user}@nebula{reset}{primary}]-[{reset}{path_display}{primary}]{reset}{status}"
    line2 = f"{primary}$ {reset}"
    return f"{line1}\n{line2}"

