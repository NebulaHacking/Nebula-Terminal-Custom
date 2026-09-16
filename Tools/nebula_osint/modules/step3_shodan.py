#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Étape 3 : Cartographie d'infrastructure réseau via l'API Shodan (avec invite interactive).
"""

import os
import json
import socket
import requests
from rich.console import Console

console = Console()

def get_or_ask_shodan_api_key() -> str:
    """
    Récupère la clé API Shodan, par ordre de priorité :
      1. Variable d'environnement SHODAN_API_KEY (recommandée — voir .env.example)
      2. Fichier local config/settings.json (config utilisateur, non versionnée)
      3. Saisie interactive (stockée UNIQUEMENT dans le fichier local, jamais versionné)
    """
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    config_path = os.path.join(config_dir, "settings.json")

    config_data = {}
    api_key = ""

    # 1. PRIORITÉ : variable d'environnement (méthode sûre et recommandée)
    api_key = os.environ.get("SHODAN_API_KEY", "").strip()

    # 2. Fallback : fichier de configuration local (s'il existe)
    if not api_key and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                api_key = config_data.get("api_keys", {}).get("shodan", "").strip()
        except Exception:
            # Si le JSON est corrompu, on repart sur un dictionnaire vide
            config_data = {}

    # 3. Si la clé est vide ou absente, on la demande de manière interactive
    if not api_key:
        console.print("\n[bold yellow][!] Clé API Shodan manquante (var. env SHODAN_API_KEY ou config locale).[/bold yellow]")
        try:
            # Demande de saisie à l'utilisateur
            user_input = input("🔑 Veuillez entrer votre clé API Shodan : ").strip()
            if user_input:
                api_key = user_input
                
                # Structure le dictionnaire de configuration
                if "api_keys" not in config_data:
                    config_data["api_keys"] = {}
                config_data["api_keys"]["shodan"] = api_key
                
                # Crée le dossier config s'il n'existe pas
                os.makedirs(config_dir, exist_ok=True)
                
                # Enregistre la nouvelle clé dans settings.json
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                
                console.print("[bold green][✔] Clé API enregistrée avec succès dans config/settings.json ![/bold green]\n")
            else:
                console.print("[bold red][✘] Aucune clé fournie. Passage à l'étape suivante.[/bold red]\n")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red][✘] Saisie annulée.[/bold red]\n")
            return ""

    return api_key

def resolve_to_ip(target: str) -> str:
    """
    Vérifie si la cible est une IP ou résout le domaine en IP.
    """
    try:
        socket.inet_aton(target)
        return target
    except socket.error:
        try:
            return socket.gethostbyname(target)
        except socket.gaierror:
            return None

def query_shodan(ip: str, api_key: str) -> dict:
    """
    Interroge l'API REST de Shodan pour une adresse IP spécifique.
    """
    url = f"https://api.shodan.io/shodan/host/{ip}?key={api_key}"
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        raise PermissionError("La clé API Shodan fournie est invalide.")
    elif response.status_code == 404:
        return {"message": "Aucune donnée trouvée sur Shodan pour cette IP."}
    else:
        raise Exception(f"Erreur API Shodan (Code {response.status_code})")

def run_module(target: str) -> dict:
    """
    Fonction standard requise par l'orchestrateur.
    """
    # 1. Récupération ou demande interactive de la clé API
    api_key = get_or_ask_shodan_api_key()
    if not api_key:
        return {
            "status": "skipped",
            "reason": "Clé API Shodan manquante (Saisie utilisateur ignorée)."
        }

    # 2. Résolution DNS de la cible
    target_ip = resolve_to_ip(target)
    if not target_ip:
        return {
            "status": "skipped",
            "reason": f"Impossible de résoudre '{target}' en adresse IP publique."
        }

    # 3. Requête Shodan
    try:
        shodan_data = query_shodan(target_ip, api_key)
        
        if "data" in shodan_data:
            return {
                "ip_scanned": target_ip,
                "isp": shodan_data.get("isp", "Inconnu"),
                "os": shodan_data.get("os", "Inconnu"),
                "hostnames": shodan_data.get("hostnames", []),
                "open_ports": shodan_data.get("ports", []),
                "vulnerabilities": shodan_data.get("vulns", [])
            }
        else:
             return {
                "ip_scanned": target_ip,
                "result": shodan_data.get("message", "Aucune donnée.")
            }

    except PermissionError as e:
        # En cas de mauvaise clé, on propose de la supprimer de la config
        return {
            "status": "error", 
            "error": f"{str(e)} (Vérifiez votre fichier config/settings.json)"
        }
    except Exception as e:
         return {"status": "error", "error": f"Échec de la connexion : {str(e)}"}