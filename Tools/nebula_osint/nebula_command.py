#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Point d'entrée principal de la commande pour Nebula Terminal.
"""

import sys
import os
import argparse
import json
import importlib.util

# =====================================================================
# 1. VÉRIFICATION RIGOUREUSE DES DÉPENDANCES ET BIBLIOTHÈQUES SOUHAITÉES
# =====================================================================

REQUIRED_PACKAGES = {
    "rich": "rich",                      # Pour de superbes affichages console
    "requests": "requests",              # Pour les requêtes HTTP de base
    "holehe": "holehe",                  # Module pour l'OSINT d'emails (Étape 5)
    "trio": "trio",                      # Requis pour l'asynchronisme d'Holehe
    "httpx": "httpx"                     # Requis pour l'asynchronisme d'Holehe
}

MISSING_PACKAGES = []

for pkg_name, import_name in REQUIRED_PACKAGES.items():
    if importlib.util.find_spec(import_name) is None:
        MISSING_PACKAGES.append(pkg_name)

if MISSING_PACKAGES:
    print("\n\033[91m[ERREUR CATASTROPHIQUE - NOSINT]\033[0m")
    print("Certaines dépendances obligatoires ne sont pas installées sur votre système.")
    print("Veuillez les installer avant de lancer l'outil dans Nebula.")
    print("\nCommandes de résolution recommandées :")
    for pkg in MISSING_PACKAGES:
        print(f"  -> \033[92mpip install {pkg}\033[0m")
    print()
    sys.exit(1)

# Import de Rich après validation de sa présence
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

# Thème visuel personnalisé Nebula
nebula_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "accent": "bold magenta"
})
console = Console(theme=nebula_theme)

# Importations de notre architecture interne
try:
    from core.orchestrator import Orchestrator
    from models.god_model import GodModel
except ImportError as e:
    console.print(f"[bold red][✘] Erreur d'importation interne : {e}[/bold red]")
    console.print("[yellow]Assurez-vous que l'arborescence des dossiers (core/, modules/, models/) est correcte.[/yellow]")
    sys.exit(1)

# =====================================================================
# 2. CONFIGURATION DE L'ANALYSEUR D'ARGUMENTS (CLI)
# =====================================================================

def parse_arguments():
    """Configure et parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="[nosint] - Outil d'OSINT modulaire de pointe pour Nebula Terminal.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Argument cible obligatoire
    parser.add_argument(
        "target",
        help="La cible de l'enquête (Exemples: pseudo, email@domain.com, domaine.com, IP)"
    )

    # Options de verbosité (Le contrôle du modèle Dieu)
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mode Détaillé : Affiche un rapport structuré avec les corrélations majeures."
    )
    verbosity_group.add_argument(
        "-V", "--ultra-verbose",
        action="store_true",
        help="Mode Coffre Fort : Divulgue l'intégralité brute du coffre de base."
    )

    # Options de filtrage de modules
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--fast",
        action="store_true",
        help="Exécute uniquement les modules instantanés (ignore les étapes lentes comme Tor)."
    )
    filter_group.add_argument(
        "--only",
        metavar="MODULE",
        choices=["llama", "darkweb", "shodan", "custom", "holehe"],
        help="Force l'exécution d'un seul module précis (llama, darkweb, shodan, custom, holehe)."
    )
    filter_group.add_argument(
        "--exclude",
        metavar="MODULES",
        help="Exclut un ou plusieurs modules de la recherche (séparés par des virgules).\n"
             "Exemple: --exclude darkweb,llama"
    )

    # Option d'exportation
    parser.add_argument(
        "-o", "--output",
        metavar="FICHIER",
        help="Sauvegarde le contenu du coffre de base ou le rapport final dans un fichier externe."
    )

    return parser.parse_args()

# =====================================================================
# 3. INITIALISATION DU COFFRE DE BASE (BASE DE DONNÉES)
# =====================================================================

def initialize_storage(target):
    """Initialise un coffre de base propre et unifié en utilisant le gestionnaire de base de données."""
    from core.database import CoffreBase
    coffre = CoffreBase()
    coffre.initialize(target)
    return coffre.coffre_path

# =====================================================================
# 4. POINT D'ENTRÉE PRINCIPAL
# =====================================================================

# Modifie uniquement la fonction main() à la fin de ton nebula_command.py :

def main():
    args = parse_arguments()
    
    # Message de bienvenue élégant façon Nebula
    console.print(Panel(
        f"[accent]NOSINT[/accent] - [info]Nebula OSINT Orchestrator[/info]\n"
        f"Cible identifiée : [success]{args.target}[/success]",
        title="[accent]NEBULA ENGINE[/accent]",
        border_style="cyan"
    ))

    # Détermination du niveau de verbosité pour le modèle Dieu
    verbosity = "default"
    if args.verbose:
        verbosity = "verbose"
    elif args.ultra_verbose:
        verbosity = "ultra_verbose"

    # 1. Initialisation du coffre de base unifié
    console.print(f"[*] Initialisation du Coffre de Base pour : [info]{args.target}[/info]...")
    coffre_path = initialize_storage(args.target)
    console.print(f"[success][✔][/success] Coffre de base initialisé avec succès : {coffre_path}\n")

    # 2. Exécution de la collecte via l'Orchestrateur
    orchestrator = Orchestrator(args.target, args)
    orchestrator.run()
    
    # 3. Rendu final par le Modèle "Dieu" (avec passage correct de la verbosité)
    god = GodModel(verbosity)
    god.generate_output()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[error][!] Opération annulée par l'utilisateur (Ctrl+C).[/error]")
        sys.exit(0)


        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[error][!] Opération annulée par l'utilisateur (Ctrl+C).[/error]")
        sys.exit(0)