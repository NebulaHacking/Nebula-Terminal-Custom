#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nosint - Nebula OSINT Tool
Gestionnaire du "Coffre de Base" (Lecture/Écriture sécurisée des données de recherche).
"""

import os
import json
import time
from datetime import datetime

class CoffreBase:
    def __init__(self, target=None):
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
        self.coffre_path = os.path.join(self.storage_dir, "coffre_base.json")
        
        # Si le dossier de stockage n'existe pas, on le crée
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Si le fichier n'existe pas encore et qu'on a une cible, on l'initialise
        if not os.path.exists(self.coffre_path) and target:
            self.initialize(target)

    def initialize(self, target: str):
        """Crée un coffre de base propre et vide pour une nouvelle cible."""
        base_structure = {
            "target": target,
            "metadata": {
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "elapsed_time_seconds": 0
            },
            "step1_llama": {"status": "pending", "updated_at": None, "data": {}},
            "step2_darkweb": {"status": "pending", "updated_at": None, "data": {}},
            "step3_shodan": {"status": "pending", "updated_at": None, "data": {}},
            "step4_custom_list": {"status": "pending", "updated_at": None, "data": {}},
            "step5_holehe": {"status": "pending", "updated_at": None, "data": {}}
        }
        self._write(base_structure)

    def _read(self) -> dict:
        """Lit le contenu actuel du coffre de base."""
        if not os.path.exists(self.coffre_path):
            raise FileNotFoundError("Le coffre de base n'a pas encore été initialisé.")
        
        try:
            with open(self.coffre_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # En cas de corruption du JSON, on renvoie un dictionnaire vide ou gère l'erreur
            return {}

    def _write(self, data: dict):
        """Écrit de manière sécurisée les données dans le fichier JSON."""
        try:
            # Écriture temporaire puis renommage pour éviter de corrompre le fichier en cas de crash
            temp_path = self.coffre_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, self.coffre_path)
        except IOError as e:
            print(f"[ERREUR STOCKAGE] Impossible d'écrire dans le coffre : {e}")

    def update_step(self, step_name: str, status: str, data: dict):
        """
        Met à jour de façon isolée les résultats d'une étape spécifique.
        Exemple : update_step("step5_holehe", "success", {"accounts": [...]})
        """
        valid_steps = ["step1_llama", "step2_darkweb", "step3_shodan", "step4_custom_list", "step5_holehe"]
        if step_name not in valid_steps:
            raise ValueError(f"Étape inconnue : {step_name}")

        coffre_data = self._read()
        if not coffre_data:
            return

        coffre_data[step_name] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "data": data
        }
        self._write(coffre_data)

    def finalize(self, overall_status: str = "completed"):
        """Clôture la recherche et calcule les métadonnées de fin."""
        coffre_data = self._read()
        if not coffre_data:
            return

        start_time = datetime.fromisoformat(coffre_data["metadata"]["started_at"])
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        coffre_data["metadata"]["status"] = overall_status
        coffre_data["metadata"]["completed_at"] = end_time.isoformat()
        coffre_data["metadata"]["elapsed_time_seconds"] = round(elapsed, 2)
        
        self._write(coffre_data)

    def get_all_data(self) -> dict:
        """Récupère l'intégralité du coffre de base pour le modèle Dieu."""
        return self._read()