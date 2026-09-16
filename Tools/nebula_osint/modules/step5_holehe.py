#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 5 : Énumération de comptes enregistrés sur plus de 120 services via Holehe.
"""

import sys
import trio
import httpx
from rich.console import Console

# Importation des moteurs internes de holehe
try:
    from holehe import core
except ImportError:
    # Message d'erreur propre si holehe n'est pas installé sur la machine
    print("[!] Le module 'holehe' n'est pas installé. Veuillez lancer : pip install holehe")
    sys.exit(1)

console = Console()

async def async_run_holehe(email: str) -> list:
    """
    Exécute de manière asynchrone la collecte d'Holehe sur les 120+ plateformes.
    """
    results = []
    
    # 1. Chargement et importation dynamique de tous les sous-modules d'Holehe
    modules = core.import_submodules("holehe.modules")
    websites = core.get_functions(modules)
    
    # 2. Initialisation du client HTTP asynchrone requis par Holehe
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0, verify=True) as client:
        # Trio permet de lancer des tâches asynchrones en parallèle
        async with trio.open_nursery() as nursery:
            for website in websites:
                # Chaque fonction d'Holehe attend : (email, client, liste_de_retour)
                nursery.start_soon(website, email, client, results)
                
    return results

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    """
    # 1. Validation de base : Holehe requiert une adresse email
    if "@" not in target or "." not in target:
        return {
            "status": "skipped",
            "reason": f"La cible '{target}' n'est pas une adresse email valide. Holehe requiert un email."
        }
    
    console.print(f"[bold cyan]🔍 Lancement de l'analyse d'emails asynchrone sur 120+ sites pour : {target}...[/bold cyan]")
    
    # 2. Exécution de la boucle asynchrone Trio
    try:
        raw_results = trio.run(async_run_holehe, target)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Erreur lors de l'exécution asynchrone d'Holehe : {str(e)}"
        }
    
    # 3. Filtrage et nettoyage des résultats pour ne garder que l'essentiel
    # Holehe renvoie : {"name": "...", "exists": True/False, "rateLimit": True/False, ...}
    hits = []
    rate_limits = []
    
    for res in raw_results:
        if res.get("exists") is True:
            hits.append({
                "platform": res.get("name"),
                "email_recovery": res.get("emailrecovery"),
                "phone_number": res.get("phoneNumber"),
                "extra": res.get("others")
            })
        elif res.get("rateLimit") is True:
            rate_limits.append(res.get("name"))

    return {
        "email_scanned": target,
        "total_checked": len(raw_results),
        "accounts_found_count": len(hits),
        "rate_limited_count": len(rate_limits),
        "registered_accounts": hits,
        "rate_limited_platforms": rate_limits
    }