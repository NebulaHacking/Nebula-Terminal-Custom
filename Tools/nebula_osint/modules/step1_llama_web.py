#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 1 : Recherche Web (Google Texte/Images) corrélée par Llama 3.1 8b.
"""

import os
import requests
import json
from urllib.parse import quote_plus

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def search_google(query: str) -> dict:
    """
    Recherche web RÉELLE (DuckDuckGo HTML, sans clé API) et retourne les
    premiers résultats textuels publiquement accessibles.

    Aucune donnée n'est inventée : si la requête échoue, on retourne une
    structure vide avec un champ 'error' explicite (jamais de faux résultats).
    """
    results = {"text_results": [], "image_results": [], "error": None}

    if BeautifulSoup is None:
        results["error"] = "BeautifulSoup4 manquant (pip install beautifulsoup4)."
        return results

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            results["error"] = f"DuckDuckGo a répondu avec le code {resp.status_code}."
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        for block in soup.select(".result")[:10]:
            title_el = block.select_one(".result__a")
            snippet_el = block.select_one(".result__snippet")
            if not title_el:
                continue
            results["text_results"].append({
                "title": title_el.get_text(strip=True),
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                "link": title_el.get("href", ""),
            })

        if not results["text_results"]:
            results["error"] = "Aucun résultat exploitable (page de consentement ou blocage)."
    except Exception as e:
        results["error"] = f"Échec de la recherche web : {e}"

    return results

def ask_llama(context: dict, target: str) -> dict:
    """
    Envoie les résultats bruts de la recherche Google à l'API Llama 3.1 8b 
    pour structurer, nettoyer et extraire les points clés.
    """
    # Exemple d'appel à une API compatible OpenAI (ou Ollama en local)
    # Dans Nebula, vous pouvez configurer l'URL locale ou distante dans config/settings.json
    api_url = "http://localhost:11434/api/chat" # Port par défaut d'Ollama si exécuté en local
    
    payload = {
        "model": "llama3.1:8b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es l'intelligence d'analyse de l'outil d'OSINT éthique nosint. "
                    "Ton but est d'extraire de manière structurée les faits réels, relations, "
                    "et données d'identification clés à partir des résultats de recherche fournis. "
                    "Réponds exclusivement au format JSON propre."
                )
            },
            {
                "role": "user",
                "content": f"Analyse ces données pour la cible '{target}' : {json.dumps(context)}"
            }
        ],
        "format": "json",
        "stream": False
    }

    try:
        # Envoi de la requête avec un timeout court pour ne pas bloquer le terminal
        response = requests.post(api_url, json=payload, timeout=15)
        if response.status_code == 200:
            result_json = response.json()
            # On tente de charger la réponse textuelle de Llama comme un dictionnaire
            content = result_json.get("message", {}).get("content", "{}")
            return json.loads(content)
    except Exception:
        # En cas d'échec de l'API Llama (par exemple si Ollama n'est pas lancé)
        # On signale honnêtement l'absence d'analyse, sans prétendre à un succès.
        return {
            "error": "Impossible de joindre l'API Llama 3.1 8b. Assurez-vous qu'Ollama ou votre API distante est active.",
            "raw_analysis": None,
        }

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    Exécute la collecte Web puis la synthèse Llama.
    """
    # 1. Collecte réelle des données publiques (DuckDuckGo HTML)
    raw_web_data = search_google(target)

    # 2. Synthèse et corrélation intelligente via Llama 3.1 8b
    structured_analysis = ask_llama(raw_web_data, target)

    # 3. Retour des données structurées prêtes à être sauvegardées dans le coffre
    return {
        "source": "DuckDuckGo HTML (Text & Images)",
        "raw_results": raw_web_data,
        "llama_analysis": structured_analysis
    }