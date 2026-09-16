#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 2 : Recherche éthique sur le réseau Tor via Ahmia.
"""

import requests
import urllib.parse
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Configurations par défaut des proxies Tor locaux (SOCKS5)
TOR_PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

def search_ahmia_onion(query: str, use_tor_network: bool = True) -> list:
    """
    Interroge l'index public Ahmia pour trouver des mentions d'une cible sur des pages .onion.
    Parse RÉELLEMENT le HTML retourné (BeautifulSoup4) au lieu de renvoyer un faux résultat.
    """
    encoded_query = urllib.parse.quote_plus(query)

    # Si Tor est disponible, on utilise l'adresse .onion officielle d'Ahmia
    if use_tor_network:
        # URL de l'adresse v3 onion d'Ahmia
        url = f"http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={encoded_query}"
        proxies = TOR_PROXIES
    else:
        # Sinon, repli (Fallback) sur la version Web classique (Clearnet)
        url = f"https://ahmia.fi/search/?q={encoded_query}"
        proxies = None

    try:
        # Envoi de la requête avec un timeout pour ne pas bloquer indéfiniment
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0'}
        response = requests.get(url, proxies=proxies, headers=headers, timeout=12)
    except Exception as e:
        # En cas d'erreur de connexion au proxy SOCKS de Tor ou au serveur
        raise ConnectionError(f"Échec de la connexion à Ahmia ({'via Tor' if use_tor_network else 'Clearnet'}) : {str(e)}")

    if response.status_code != 200:
        return []

    if BeautifulSoup is None:
        # Sans BS4, on ne peut pas parser : on retourne vide plutôt qu'un faux résultat.
        return []

    results = []
    soup = BeautifulSoup(response.text, "html.parser")
    # Ahmia structure ses résultats en <li class="result"> (h4 > a + p.snippet)
    for block in soup.select("li.result"):
        link_el = block.select_one("h4 a")
        if not link_el:
            continue
        snippet_el = block.select_one("p")
        results.append({
            "title": link_el.get_text(strip=True),
            "onion_url": urljoin(url, link_el.get("href", "")),
            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
        })

    return results

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    Tente d'abord une connexion via le réseau Tor, sinon bascule sur le Clearnet.
    """
    results = []
    mode_used = "Tor network (onion v3)"

    try:
        # 1. Tentative d'interrogation en utilisant le proxy Tor local
        results = search_ahmia_onion(target, use_tor_network=True)
    except (ConnectionError, Exception):
        # 2. En cas d'échec de la connexion Tor, on tente via l'Internet classique (Clearnet)
        mode_used = "Clearnet fallback (ahmia.fi)"
        try:
            results = search_ahmia_onion(target, use_tor_network=False)
        except Exception as err:
            return {
                "status": "error",
                "error": f"Impossible d'interroger Ahmia (Tor et Clearnet inaccessibles) : {str(err)}",
                "results": []
            }

    return {
        "source": "Ahmia Search Engine",
        "mode": mode_used,
        "results": results
    }