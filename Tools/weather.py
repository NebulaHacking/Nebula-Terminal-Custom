"""Météo via wttr.in — conditions actuelles et prévisions sur 3 jours, en blocs.

`weather_blocks(ville)` : ville vide = position estimée d'après ta connexion.
"""
from urllib.parse import quote

import requests


def weather_data(city: str = "") -> dict:
    city = (city or "").strip()
    if len(city) > 80:
        raise ValueError("Nom de ville trop long")
    r = requests.get(f"https://wttr.in/{quote(city)}?format=j1&lang=fr", timeout=15,
                     headers={"User-Agent": "curl/8 (Nebula weather)"})  # wttr.in répond en JSON aux clients « curl »
    if r.status_code != 200:
        raise ValueError(f"Météo indisponible pour « {city or 'ta position'} » (HTTP {r.status_code})")
    try:
        return r.json()
    except ValueError as e:
        raise ValueError("Réponse météo illisible (ville inconnue ?)") from e


def _desc(item) -> str:
    for key in ("lang_fr", "weatherDesc"):
        if item.get(key):
            return item[key][0]["value"].strip()
    return ""


def weather_blocks(city: str = "") -> list[dict]:
    data = weather_data(city)
    now = data["current_condition"][0]
    area = (data.get("nearest_area") or [{}])[0]
    place = ", ".join(x[0]["value"] for x in (area.get("areaName"), area.get("region"), area.get("country")) if x and x[0]["value"])
    days = []
    for day in data.get("weather", [])[:3]:
        hours = day.get("hourly") or []
        midday = hours[len(hours) // 2] if hours else {}
        rain = max((int(h.get("chanceofrain", 0)) for h in hours), default=0)
        days.append([day["date"], f"{day['mintempC']} °C", f"{day['maxtempC']} °C", _desc(midday), f"{rain} %"])
    return [
        {"title": place or city or "Météo", "kv": [
            ["Conditions", _desc(now)], ["Température", f"{now['temp_C']} °C (ressenti {now['FeelsLikeC']} °C)"],
            ["Humidité", f"{now['humidity']} %"], ["Vent", f"{now['windspeedKmph']} km/h {now['winddir16Point']}"],
            ["Pression", f"{now['pressure']} hPa"], ["Visibilité", f"{now['visibility']} km"], ["Indice UV", now.get("uvIndex", "")],
            ["Observé à", now.get("observation_time", "") + " UTC"]]},
        {"title": "Prévisions", "cols": ["Date", "Min", "Max", "Temps (midi)", "Pluie"], "rows": days},
    ]


def cmd_weather(ville: str | None = None) -> None:
    """Compatibilité : affichage texte dans le terminal."""
    from terminal.blocks import print_blocks
    print_blocks(weather_blocks(ville or ""))
