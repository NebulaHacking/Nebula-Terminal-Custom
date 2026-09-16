"""Commandes utilitaires diverses (M4) — calc, weather.

Portage des branches de l'ancien main.py : calc (929-931), weather (954-960).
random (rand) vit déjà dans builtins.py ; il reste ici groupé avec le reste
des utilitaires. Moteurs dans Tools/calculator.py et Tools/weather.py.
"""
from terminal.registry import REGISTRY


@REGISTRY.register("calc", help_text="calc             - Lancer la calculatrice")
def _calc(ctx, argv, raw):
    from Tools.calculator import calculatrice
    calculatrice()


@REGISTRY.register("weather", help_text="weather [ville]   - Afficher la météo d'une ville (ex: weather Paris)")
def _weather(ctx, argv, raw):
    from Tools.weather import cmd_weather
    # Parité : le premier argument après "weather" est la ville.
    cmd_weather(argv[1] if len(argv) > 1 else None)