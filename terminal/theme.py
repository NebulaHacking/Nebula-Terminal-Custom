"""
Systeme de themes charge depuis themes.json

Usage:
    from terminal.theme import get_theme, set_theme, is_redark

    set_theme("redark")   # Active le theme redark
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


def _load_config() -> Dict[str, Any]:
    """Charge la config complete (version, default, etc.)."""
    try:
        with open(_THEME_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "default": "micha", "themes": {}}


def get_theme() -> Dict[str, Any]:
    """Retourne la configuration du theme courant."""
    themes = _load_themes()
    return themes.get(_current_theme, themes.get("micha", {})) or {}


def set_theme(theme_name: str) -> bool:
    """
    Change le theme courant.

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


def get_prompt_colors() -> Dict[str, str]:
    """Retourne les couleurs ANSI pour le prompt selon le theme."""
    theme = get_theme()
    prompt = theme.get("prompt", {})
    return {
        "primary": prompt.get("primary", "[92m"),
        "secondary": prompt.get("secondary", "[94m"),
        "accent": prompt.get("accent", "[96m"),
        "reset": prompt.get("reset", "[0m")
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


# Alias pour compatibilite
def get_border_style() -> str:
    return get_rich_style()["border_style"]


def get_title_style() -> str:
    return get_rich_style()["title_style"]


# Constantes
MICHA = "micha"
REDARK = "redark"