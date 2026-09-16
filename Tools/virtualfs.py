"""Système de fichiers virtuel de Nebula.

Remplace les globaux `structure` / `current_path` de l'ancien main.py (lignes
70-72, 373-455, 940-949) par une classe testable. Aucun `global` : l'instance
vit dans `terminal/context.py` (Context.vfs) et circule via les handlers.
"""
import json
import os


class VirtualFS:
    """FS virtuel (dict imbriqué) + navigation/sauvegarde."""

    def __init__(self) -> None:
        # Racine virtuelle avec dossier Nebula (comportement identique à l'original)
        self.root: dict = {'/': {'Nebula': {}}}
        self.current_path: list[str] = ['/', 'Nebula']

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def get_current_dir(self) -> dict:
        """Retourne le dictionnaire du répertoire actuel."""
        dir_ref = self.root['/']
        for folder in self.current_path[1:]:
            dir_ref = dir_ref[folder]
        return dir_ref

    def get_path(self) -> str:
        """Chemin virtuel courant en string (ex: /Nebula/Pwned)."""
        path_display = "/".join(self.current_path[1:]) if len(self.current_path) > 1 else "/"
        if not path_display.startswith("/"):
            path_display = "/" + path_display
        return path_display

    def cd(self, arg: str) -> bool:
        """Change de dossier. `..` remonte. Retourne False en cas d'erreur."""
        if arg == "..":
            if len(self.current_path) > 1:
                self.current_path.pop()
            return True
        d = self.get_current_dir()
        if arg in d:
            if isinstance(d[arg], dict):
                self.current_path.append(arg)
                return True
            print(f"{arg} n'est pas un dossier.")
        else:
            print(f"Dossier '{arg}' introuvable.")
        return False

    def mkdir(self, arg: str) -> bool:
        """Crée un dossier virtuel dans le répertoire courant."""
        d = self.get_current_dir()
        if arg in d:
            print(f"Le dossier '{arg}' existe déjà.")
            return False
        d[arg] = {}
        return True

    def ls(self) -> list[str]:
        """Retourne les items du répertoire courant."""
        return list(self.get_current_dir().keys())

    # ------------------------------------------------------------------
    # Fichiers
    # ------------------------------------------------------------------
    def read_file(self, name: str) -> str | None:
        """Contenu d'un fichier virtuel, ou None si absent / non-fichier."""
        d = self.get_current_dir()
        if name in d and isinstance(d[name], str):
            return d[name]
        return None

    def write_file(self, name: str, content: str) -> None:
        """Écrit (ou écrase) un fichier virtuel."""
        self.get_current_dir()[name] = content

    def delete_file(self, name: str) -> bool:
        """Supprime `name` du répertoire courant. True si supprimé."""
        d = self.get_current_dir()
        if name in d:
            del d[name]
            return True
        return False

    # ------------------------------------------------------------------
    # Persistance (dossier `saves/`)
    # ------------------------------------------------------------------
    @staticmethod
    def list_saves(saves_dir: str = "saves") -> list[str]:
        """Liste les sauvegardes disponibles (*.txt) dans `saves_dir`."""
        if not os.path.isdir(saves_dir):
            return []
        return [f for f in os.listdir(saves_dir) if f.endswith(".txt")]

    def save_to(self, filename: str, saves_dir: str = "saves") -> str:
        """Sérialise le FS complet dans `saves_dir/<filename>.txt`. Retourne le chemin."""
        os.makedirs(saves_dir, exist_ok=True)
        filepath = os.path.join(saves_dir, filename + ".txt")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.root, f, indent=4)
        return filepath

    def load_from(self, index: int, saves_dir: str = "saves") -> str | None:
        """Recharge le FS depuis la sauvegarde `index`. Réinitialise le chemin courant."""
        files = self.list_saves(saves_dir)
        if not (0 <= index < len(files)):
            return None
        filepath = os.path.join(saves_dir, files[index])
        with open(filepath, "r", encoding="utf-8") as f:
            self.root = json.load(f)
        self.current_path = ['/', 'Nebula']
        return filepath