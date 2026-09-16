#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 4 : Recherche automatisée sur une liste personnalisée de sources (list.txt).
"""

import os
import requests
import urllib.parse
import re

def get_or_create_custom_list() -> list:
    """
    Récupère les URLs depuis config/list.txt.
    Si le fichier n'existe pas, il le génère avec des exemples par défaut.
    """
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    list_path = os.path.join(config_dir, "list.txt")
    
    os.makedirs(config_dir, exist_ok=True)
    
    # Si le fichier n'existe pas, on crée un template de base
    if not os.path.exists(list_path):
        default_content = """# NOSINT - Liste de sources OSINT personnalisées
# Ajoutez vos URLs ici. Utilisez la balise {target} là où la cible doit être insérée.
# Les lignes commençant par # sont ignorées.

https://github.com/{target}
https://en.wikipedia.org/wiki/{target}
https://pastebin.com/search?q={target}
"""
        with open(list_path, "w", encoding="utf-8") as f:
            f.write(default_content)
        
    # Lecture et nettoyage de la liste
    urls = []
    with open(list_path, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()
            if clean_line and not clean_line.startswith("#"):
                urls.append(clean_line)
                
    return urls

def extract_title(html_content: str) -> str:
    """
    Extrait le titre de la page web avec une simple regex pour donner du contexte.
    """
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Titre inconnu"

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    Itère sur chaque site de la liste pour chercher la cible.
    """
    urls_to_check = get_or_create_custom_list()
    
    if not urls_to_check:
        return {
            "status": "skipped",
            "reason": "Le fichier config/list.txt est vide."
        }

    encoded_target = urllib.parse.quote(target)
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

    for template_url in urls_to_check:
        # On remplace la balise {target} par la cible encodée (pour les espaces et caractères spéciaux)
        target_url = template_url.replace("{target}", encoded_target)
        
        try:
            # Requête avec timeout court pour éviter de bloquer sur un site lent
            response = requests.get(target_url, headers=headers, timeout=5)
            
            # Si on reçoit un code 200 (OK), on considère que c'est un résultat potentiel
            if response.status_code == 200:
                page_title = extract_title(response.text)
                
                # Petit filtre anti-faux positifs (si la page renvoie 200 mais dit "non trouvé")
                if "not found" not in page_title.lower() and "404" not in page_title:
                    results.append({
                        "url": target_url,
                        "status_code": 200,
                        "page_title": page_title
                    })
            else:
                # On enregistre aussi les accès refusés (403), car cela peut signifier que la page existe
                if response.status_code in [401, 403]:
                     results.append({
                        "url": target_url,
                        "status_code": response.status_code,
                        "page_title": "Accès restreint / Protégé"
                    })
                     
        except requests.exceptions.RequestException:
            # On ignore silencieusement les sites qui ne répondent pas (timeout, erreur DNS)
            continue

    return {
        "sources_checked": len(urls_to_check),
        "hits_found": len(results),
        "data": results
    }