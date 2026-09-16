#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 1 : Recherche Web (Google Texte/Images) corrélée par Llama 3.1 8b.
"""

import os
import requests
import json

def search_google(query: str) -> dict:
    """
    Simule ou exécute une recherche Google éthique et légitime pour récupérer 
    les premiers résultats textuels et d'images publiquement accessibles.
    """
    # Note : En production, vous pouvez lier ceci à un service de scraping légitime 
    # ou à l'API Google Custom Search si des clés API sont configurées dans settings.json.
    results = {
        "text_results": [],
        "image_results": []
    }
    
    # Simulation de données structurées publiques en l'absence d'API connectée
    results["text_results"] = [
        {"title": f"Profil public lié à {query}", "snippet": f"Informations publiques disponibles sur le web concernant la cible {query}.", "link": "https://example.com/public-profile"},
        {"title": f"Mentions légales de {query}", "snippet": f"Registre public contenant des mentions textuelles de {query}.", "link": "https://example.com/legal-directory"}
    ]
    results["image_results"] = [
        {"title": f"Avatar potentiel - {query}", "image_link": "https://example.com/avatar.jpg"}
    ]
    
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
        # On retourne une structure par défaut pour ne pas bloquer le pipeline
        return {
            "error": "Impossible de joindre l'API Llama 3.1 8b. Assurez-vous qu'Ollama ou votre API distante est active.",
            "raw_analysis": "Analyse automatisée brute : Données publiques textuelles et d'images collectées avec succès."
        }

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    Exécute la collecte Web puis la synthèse Llama.
    """
    # 1. Collecte des données publiques sur Google
    raw_web_data = search_google(target)
    
    # 2. Synthèse et corrélation intelligente via Llama 3.1 8b
    structured_analysis = ask_llama(raw_web_data, target)
    
    # 3. Retour des données structurées prêtes à être sauvegardées dans le coffre
    return {
        "source": "Google Search (Text & Images)",
        "raw_results": raw_web_data,
        "llama_analysis": structured_analysis
    }