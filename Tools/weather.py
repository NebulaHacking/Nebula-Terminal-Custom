"""Météo via wttr.in — portage des lignes 954-960 de l'ancien main.py.

`cmd_weather(ville)` demande la ville si non fournie (parité : l'ancien handler
faisait `input("Ville : ")`), puis affiche la version compacte `?0`.
"""
import requests


def cmd_weather(ville: str | None = None) -> None:
    if ville is None:
        ville = input("Ville : ").strip()
    url = f"https://wttr.in/{ville}?0"  # "?0" = version compacte
    try:
        print(requests.get(url).text)
    except Exception:
        print("Erreur : impossible de récupérer la météo.")