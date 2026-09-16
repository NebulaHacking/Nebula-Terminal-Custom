"""Lecture de `txt.help.folder/Tools.txt` — portage des lignes 967-990 de l'ancien main.py.

Garde le double fix d'encodage exact (UTF-8 → Latin-1 → UTF-8) et la suppression
des accents, puis convertit les séquences `\\033` en vraies séquences ANSI.
"""
import unicodedata

TOOLS_TXT_PATH = "txt.help.folder/Tools.txt"


def enlever_accents(texte: str) -> str:
    """Supprime uniquement les accents (NFD + retrait des combining marks)."""
    texte = unicodedata.normalize("NFD", texte)
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def lire_tools_txt(path: str = TOOLS_TXT_PATH) -> str:
    """Renvoie le contenu nettoyé de Tools.txt (str, séquences ANSI actives)."""
    with open(path, "rb") as f:  # lecture binaire
        raw_bytes = f.read()

    try:
        # Essaye UTF-8 en premier
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Si ça plante, tente Latin-1 puis re-décode en UTF-8
        raw = raw_bytes.decode("latin-1").encode("utf-8").decode("utf-8")

    # Corrige les accents mal affichés (cas UTF8 lu en Latin-1)
    try:
        raw = raw.encode("latin-1").decode("utf-8")
    except UnicodeEncodeError:
        pass  # pas besoin si déjà correct

    # Enlève les accents si nécessaire
    raw = enlever_accents(raw)

    # Transforme les séquences \033 en vraies séquences ANSI
    return raw.replace("\\033", "\x1b")