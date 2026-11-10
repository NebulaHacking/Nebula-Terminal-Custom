"""
Système de gestion des utilisateurs Nebula.
Profils dans users/users_config.json : thème, historique, VFS.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

_USERS_DIR = Path(__file__).resolve().parent.parent / "users"
_USERS_CONFIG = _USERS_DIR / "users_config.json"
DEFAULT_THEME = "micha"


def _load() -> Dict[str, Any]:
    """Lit tous les profils. Fichier absent → {} ; fichier corrompu → erreur (on n'écrase jamais)."""
    if not _USERS_CONFIG.exists():
        return {}
    try:
        with open(_USERS_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Profils illisibles ({_USERS_CONFIG}) : {e}") from e


def _save(data: Dict[str, Any]) -> None:
    """Écriture atomique : un crash pendant l'écriture ne détruit pas les profils."""
    _USERS_DIR.mkdir(exist_ok=True)
    tmp = _USERS_CONFIG.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _USERS_CONFIG)


def _warn(msg: str) -> None:
    print(f"[!] {msg}")


def get_available_users() -> list[str]:
    try:
        return list(_load().keys())
    except RuntimeError as e:
        _warn(e)
        return []


def user_exists(username: str) -> bool:
    return username in get_available_users()


def create_user(username: str) -> bool:
    try:
        data = _load()
        if username in data:
            return False
        data[username] = {
            "username": username,
            "theme": DEFAULT_THEME,
            "history": [],
            "vfs_data": {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _save(data)
        return True
    except (RuntimeError, OSError) as e:
        _warn(e)
        return False


def get_user_config(username: str) -> Optional[Dict[str, Any]]:
    try:
        return _load().get(username)
    except RuntimeError as e:
        _warn(e)
        return None


def _update(username: str, key: str, value: Any) -> bool:
    try:
        data = _load()
        if username not in data:
            return False
        data[username][key] = value
        _save(data)
        return True
    except (RuntimeError, OSError) as e:
        _warn(e)
        return False


def save_user_theme(username: str, theme: str) -> bool:
    return _update(username, "theme", theme)


def save_user_history(username: str, history: list) -> bool:
    return _update(username, "history", history)


def save_user_vfs(username: str, vfs_data: Dict) -> bool:
    return _update(username, "vfs_data", vfs_data)


def get_user_theme(username: str) -> str:
    return (get_user_config(username) or {}).get("theme", DEFAULT_THEME)


def get_user_history(username: str) -> list:
    return (get_user_config(username) or {}).get("history", [])


def get_user_vfs(username: str) -> Dict:
    return (get_user_config(username) or {}).get("vfs_data", {})


def delete_user(username: str) -> bool:
    try:
        data = _load()
        if data.pop(username, None) is None:
            return False
        _save(data)
        return True
    except (RuntimeError, OSError) as e:
        _warn(e)
        return False
