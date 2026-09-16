#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Modèle "Dieu" : Analyseur, corrélateur et moteur d'affichage final de nosint.
"""

import sys
import json
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()

class GodModel:
    def __init__(self, verbosity: str = "default"):
        """
        Initialise le modèle Dieu avec un niveau de verbosité défini.
        Niveaux acceptés : 'default', 'verbose', 'ultra_verbose'
        """
        self.verbosity = verbosity
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
        self.coffre_path = os.path.join(self.storage_dir, "coffre_base.json")

    def _load_coffre(self) -> dict:
        """Charge de manière sécurisée les données du coffre de base."""
        if not os.path.exists(self.coffre_path):
            console.print("[bold red][✘] Erreur : Le coffre de base est introuvable.[/bold red]")
            sys.exit(1)
        try:
            with open(self.coffre_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[bold red][✘] Erreur lors de la lecture du coffre : {e}[/bold red]")
            sys.exit(1)

    def generate_output(self):
        """Orchestre le rendu visuel final selon la verbosité configurée."""
        data = self._load_coffre()
        target = data.get("target", "Inconnue")
        metadata = data.get("metadata", {})

        # Entête du rapport final
        console.print("\n" + "="*60)
        console.print(f"[bold magenta]RAPPORT FINAL NOSINT - CIBLE : {target}[/bold magenta]")
        console.print(f"Statut : [green]{metadata.get('status', 'Inconnu')}[/green] | "
                      f"Durée : [cyan]{metadata.get('elapsed_time_seconds', 0)}s[/cyan]")
        console.print("="*60 + "\n")

        if self.verbosity == "ultra_verbose":
            self._render_ultra_verbose(data)
        elif self.verbosity == "verbose":
            self._render_verbose(data)
        else:
            self._render_default(data, target)

    def _render_default(self, data: dict, target: str):
        """Rendu par défaut : Synthèse condensée et ultra-propre."""
        console.print("[bold cyan]🔹 SYNTHÈSE DES DÉCOUVERTES MAJEURES[/bold cyan]\n")

        # Extraction des comptes trouvés (Holehe)
        holehe_data = data.get("step5_holehe", {}).get("data", {})
        registered = holehe_data.get("registered_accounts", [])
        
        # Extraction des ports ouverts (Shodan)
        shodan_data = data.get("step3_shodan", {}).get("data", {})
        ports = shodan_data.get("open_ports", [])
        
        if registered:
            console.print(f"[green][✔][/green] [bold]Comptes actifs détectés ({len(registered)}) :[/bold]")
            platforms = [x['platform'] for x in registered]
            console.print(f"    -> {', '.join(platforms)}")
        else:
            console.print("[yellow][!] Aucun compte social détecté via Holehe.[/yellow]")

        if ports:
            console.print(f"\n[green][✔][/green] [bold]Ports ouverts identifiés :[/bold] {', '.join(map(str, ports))}")
            if shodan_data.get("os") and shodan_data.get("os") != "Inconnu":
                console.print(f"    -> OS estimé : [cyan]{shodan_data.get('os')}[/cyan]")
        else:
            console.print("\n[yellow][!] Pas de ports ouverts ou d'infrastructure détectée sur Shodan.[/yellow]")

        # Custom List Hits
        custom_data = data.get("step4_custom_list", {}).get("data", {})
        hits = custom_data.get("data", [])
        if hits:
            console.print(f"\n[green][✔][/green] [bold]Présence sur vos listes personnalisées :[/bold] {len(hits)} correspondances trouvées.")
        
        console.print("\n[info]💡 Conseil : Utilisez l'option -v pour afficher les détails ou -V pour dumper le coffre brut.[/info]")

    def _render_verbose(self, data: dict):
        """Rendu détaillé : Tableaux structurés par module."""
        # 1. Détails Réseau / Shodan
        shodan_data = data.get("step3_shodan", {}).get("data", {})
        if shodan_data and "ip_scanned" in shodan_data:
            table = Table(title="💻 Analyse Réseau & Infrastructure (Shodan)", show_header=True, header_style="bold cyan")
            table.add_column("Propriété", style="dim")
            table.add_column("Valeur")
            table.add_row("IP Scannée", shodan_data.get("ip_scanned"))
            table.add_row("FAI / ISP", shodan_data.get("isp"))
            table.add_row("OS Détecté", shodan_data.get("os"))
            table.add_row("Ports Ouverts", str(shodan_data.get("open_ports")))
            console.print(table)
            console.print()

        # 2. Détails Comptes / Holehe
        holehe_data = data.get("step5_holehe", {}).get("data", {})
        registered = holehe_data.get("registered_accounts", [])
        if registered:
            table = Table(title="📧 Présence Numérique (Holehe)", show_header=True, header_style="bold green")
            table.add_column("Plateforme", style="bold")
            table.add_column("Récupération liée")
            for acc in registered:
                table.add_row(acc.get("platform"), acc.get("email_recovery") or "N/A")
            console.print(table)
            console.print()

        # 3. Résultats Custom List
        custom_data = data.get("step4_custom_list", {}).get("data", {})
        hits = custom_data.get("data", [])
        if hits:
            table = Table(title="📂 Correspondances Listes Personnalisées", show_header=True, header_style="bold yellow")
            table.add_column("URL Vérifiée")
            table.add_column("Code")
            table.add_column("Titre de page")
            for hit in hits:
                table.add_row(hit.get("url"), str(hit.get("status_code")), hit.get("page_title"))
            console.print(table)
            console.print()

    def _render_ultra_verbose(self, data: dict):
        """Rendu brut : Divulgue l'intégralité du coffre au format JSON coloré."""
        console.print("[bold red]🔓 [DIVULGATION DU COFFRE DE BASE - DONNÉES BRUTES][/bold red]\n")
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        console.print(syntax)