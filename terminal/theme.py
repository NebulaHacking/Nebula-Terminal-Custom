"""
Systeme de themes charge depuis themes.json

Usage:
    from terminal.theme import get_theme, set_theme, is_redark

    set_theme("redark")   # Active le theme (la persistance est faite par profil utilisateur, cf. core.main)
    theme = get_theme()   # Recupere la config du theme actif
"""
import json
from pathlib import Path
from typing import Dict, Any

# Chemins
_THEME_FILE = Path(__file__).parent / "themes.json"
_themes_cache: Dict[str, Dict[str, Any]] = {}
_current_theme: str = "micha"  # Defaut


def _load_themes() -> Dict[str, Dict[str, Any]]:
    """Charge les themes depuis le fichier JSON."""
    global _themes_cache
    if not _themes_cache:
        try:
            with open(_THEME_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _themes_cache = data.get("themes", {})
        except Exception:
            _themes_cache = {}
    return _themes_cache


def get_theme() -> Dict[str, Any]:
    """Retourne la configuration du theme courant."""
    themes = _load_themes()
    return themes.get(_current_theme, themes.get("micha", {})) or {}


def set_theme(theme_name: str) -> bool:
    """
    Change le theme courant (en mémoire). Sauvegardé dans le profil à la fermeture.

    Args:
        theme_name: Nom du theme ("micha", "redark", etc.)

    Returns:
        True si le theme existe, False sinon
    """
    themes = _load_themes()
    if theme_name in themes:
        global _current_theme
        _current_theme = theme_name
        return True
    return False


def get_theme_name() -> str:
    """Retourne le nom du theme courant."""
    return _current_theme


def get_available_themes() -> list[str]:
    """Liste des themes disponibles."""
    return list(_load_themes().keys())


def is_redark() -> bool:
    """True si le theme redark est actif."""
    return _current_theme == "redark"


def _to_ansi(color_code: str) -> str:
    """Convert a Rich-style tag (e.g., [92m) to a standard ANSI escape sequence (e.g., 033[92m)."""
    if color_code.startswith("[") and color_code.endswith("m"):
        return color_code.replace("[", "\033[")
    return color_code

def get_prompt_colors() -> Dict[str, str]:
    """Retourne les couleurs ANSI pour le prompt selon le theme."""
    theme = get_theme()
    prompt = theme.get("prompt", {})
    return {
        "primary": _to_ansi(prompt.get("primary", "[92m")),
        "secondary": _to_ansi(prompt.get("secondary", "[94m")),
        "accent": _to_ansi(prompt.get("accent", "[96m")),
        "reset": _to_ansi(prompt.get("reset", "[0m"))
    }



def get_rich_style() -> Dict[str, str]:
    """Retourne les styles pour Rich (panels, etc.)."""
    theme = get_theme()
    rich = theme.get("rich", {})
    return {
        "border_style": rich.get("border_style", "green"),
        "title_style": rich.get("title_style", "bold green")
    }


def get_gui_colors() -> Dict[str, str]:
    """Retourne les couleurs pour les interfaces GUI (PyQt5)."""
    theme = get_theme()
    return theme.get("gui", {})


def get_terminal_colors() -> Dict[str, str]:
    """Retourne les couleurs ANSI pour les éléments du terminal (banners, menus, erreurs)."""
    colors = get_prompt_colors()
    theme = get_theme()
    rich = theme.get("rich", {})

    return {
        "primary": colors["primary"],
        "secondary": colors["secondary"],
        "accent": colors.get("accent", colors["primary"]),
        "reset": colors["reset"],
        "border_style": rich.get("border_style", "green"),
        "title_style": rich.get("title_style", "bold green"),
    }



def banner_colors() -> list[str]:
    """Dégradé du thème (codes ANSI 256 couleurs), du haut vers le bas des bannières."""
    codes = get_theme().get("banner") or []
    return [f"\033[38;5;{c}m" for c in codes] or [get_prompt_colors()["primary"]]


def paint(text: str, theme_name: str | None = None) -> str:
    """Applique le dégradé vertical du thème à un texte multiligne (bannières ASCII des outils)."""
    if theme_name:
        codes = _load_themes().get(theme_name, {}).get("banner") or []
        colors = [f"\033[38;5;{c}m" for c in codes] or banner_colors()
    else:
        colors = banner_colors()
    lines = text.split("\n")
    step = len(colors) / max(len(lines), 1)
    return "\n".join(colors[min(int(i * step), len(colors) - 1)] + line for i, line in enumerate(lines)) + "\033[0m"


def swatch(theme_name: str) -> str:
    """Barre de couleurs du thème, pour l'aperçu de `theme`."""
    codes = _load_themes().get(theme_name, {}).get("banner") or []
    return "".join(f"\033[38;5;{c}m██" for c in codes) + "\033[0m"


# Alias pour compatibilite
def get_border_style() -> str:
    return get_rich_style()["border_style"]


def get_title_style() -> str:
    return get_rich_style()["title_style"]


# Constantes
MICHA = "micha"
REDARK = "redark"