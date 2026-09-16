#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Orchestrateur central gérant l'exécution séquentielle et sécurisée des modules.
"""

import sys
import importlib
from rich.console import Console
from core.database import CoffreBase

console = Console()

class Orchestrator:
    def __init__(self, target: str, args):
        self.target = target
        self.args = args
        self.coffre = CoffreBase(target)
        
        # Mapping des étapes et de leurs fichiers correspondants
        self.all_modules = {
            "step1_llama": "modules.step1_llama_web",
            "step2_darkweb": "modules.step2_darkweb",
            "step3_shodan": "modules.step3_shodan",
            "step4_custom_list": "modules.step4_custom_list",
            "step5_holehe": "modules.step5_holehe"
        }

    def determine_modules_to_run(self) -> dict:
        """Filtre les modules à exécuter en fonction des options de ligne de commande."""
        modules_to_run = self.all_modules.copy()

        # Option --only (Un seul module)
        if self.args.only:
            target_key = f"step5_holehe" if self.args.only == "holehe" else f"step_{self.args.only}"
            # On cherche la clé exacte correspondante dans notre dictionnaire
            matched_key = next((k for k in self.all_modules.keys() if self.args.only in k), None)
            if matched_key:
                return {matched_key: self.all_modules[matched_key]}
            else:
                console.print(f"[bold red][!] Module spécifié invalide : {self.args.only}[/bold red]")
                sys.exit(1)

        # Option --fast (On zappe les modules lourds / lents comme Tor ou LLM)
        if self.args.fast:
            console.print("[yellow][!] Mode rapide activé : exclusion des modules lents (LLM & Dark Web)...[/yellow]")
            modules_to_run.pop("step1_llama", None)
            modules_to_run.pop("step2_darkweb", None)

        # Option --exclude (Exclusion manuelle de modules)
        if self.args.exclude:
            excluded = [x.strip() for x in self.args.exclude.split(",")]
            for exc in excluded:
                matched_key = next((k for k in self.all_modules.keys() if exc in k), None)
                if matched_key:
                    modules_to_run.pop(matched_key, None)
                    console.print(f"[yellow][!] Module exclu : {matched_key}[/yellow]")

        return modules_to_run

    def run(self):
        """Lance l'exécution de la collecte."""
        modules_to_execute = self.determine_modules_to_run()
        
        console.print(f"\n[bold cyan][*] Lancement de la collecte d'informations ({len(modules_to_execute)} modules actifs)...[/bold cyan]")

        for step_name, module_path in modules_to_execute.items():
            console.print(f"┌── [bold yellow]Exécution : {step_name.replace('_', ' ').title()}[/bold yellow]...")
            
            # Mise à jour du statut dans le coffre : en cours
            self.coffre.update_step(step_name, "running", {})

            try:
                # Importation dynamique du module ciblé
                module = importlib.import_module(module_path)
                
                # Chaque module doit exposer une fonction standard : run_module(target)
                if hasattr(module, "run_module"):
                    result_data = module.run_module(self.target)
                    
                    # Sauvegarde des résultats réussis dans le coffre
                    self.coffre.update_step(step_name, "success", result_data)
                    console.print(f"└── [bold green][✔] {step_name.replace('_', ' ').title()} complété avec succès ![/bold green]\n")
                else:
                    raise AttributeError(f"Le module {module_path} n'implémente pas la fonction obligatoire 'run_module'")

            except Exception as e:
                # Si un module plante, l'orchestrateur capture l'erreur et continue
                error_msg = f"Erreur critique lors de l'exécution : {str(e)}"
                self.coffre.update_step(step_name, "failed", {"error": error_msg})
                console.print(f"└── [bold red][✘] {step_name.replace('_', ' ').title()} a échoué ![/bold red] (Erreur loggée dans le coffre)\n")

        # Finalisation globale de la session de recherche
        self.coffre.finalize("completed")
        console.print("[bold green][✔] Session de collecte terminée. Données centralisées dans le coffre.[/bold green]\n")