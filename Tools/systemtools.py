"""Outils système — portage de l'ancien main.py.

- `execute_command_real(cmd)` : exécute une vraie commande shell (anc. lignes 657-667)
- `clean_pycache()`           : purge récursive des __pycache__ (anc. lignes 864-869)
- `set_console_color(code)`   : couleur console Windows (anc. branche color, 1019-1038)
"""
import os
import shutil
import subprocess

_COLOR_ALLOWED = ("0", "2", "3", "4")  # 0=reset, 2=vert, 3=cyan, 4=rouge


def execute_command_real(cmd: str) -> None:
    """Exécute `cmd` dans le vrai shell et affiche stdout/stderr."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print("Erreur :", e)


def clean_pycache(root: str = ".") -> None:
    """Supprime tous les dossiers __pycache__ sous `root` (arborescance physique)."""
    for dirpath, dirs, files in os.walk(root, topdown=False):
        if "__pycache__" in dirs:
            path = os.path.join(dirpath, "__pycache__")
            shutil.rmtree(path)
            print(f"[CLEAN] Supprimé : {path}")


def set_console_color(color_code: str) -> None:
    """Change la couleur de la console Windows (cmd.exe).

    Lève `ValueError` si le code n'est pas dans _COLOR_ALLOWED.
    """
    if color_code not in _COLOR_ALLOWED:
        raise ValueError(f"code couleur invalide : {color_code!r}")
    if os.name == "nt":
        os.system(f"color {color_code}")