"""Commandes utilitaires diverses (M4) — calc, weather.

Portage des branches de l'ancien main.py : calc (929-931), weather (954-960).
random (rand) vit déjà dans builtins.py ; il reste ici groupé avec le reste
des utilitaires. Moteurs dans Tools/calculator.py et Tools/weather.py.
"""
from terminal.registry import REGISTRY


@REGISTRY.register("calc", help_text="calc [expr]      - Calcule expr (ex: calc 2**10), sans argument : mode interactif")
def _calc(ctx, argv, raw):
    from Tools.calculator import calculatrice, calculer
    expr = raw.split(None, 1)[1] if len(argv) > 1 else ""
    if expr:
        print("Résultat :", calculer(expr))
    else:
        calculatrice()


@REGISTRY.register("weather", aliases=("meteo",), help_text=(
    "weather [ville]   - Météo actuelle et prévisions sur 3 jours (sans ville : ta position estimée)\n"
    "Exemples : weather Fribourg   |   weather \"New York\""), summary="Météo et prévisions sur 3 jours")
def _weather(ctx, argv, raw):
    from terminal.blocks import print_blocks
    from Tools.weather import weather_blocks
    print_blocks(weather_blocks(raw.split(None, 1)[1].strip('"') if len(argv) > 1 else ""))