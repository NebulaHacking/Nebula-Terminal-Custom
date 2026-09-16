"""Sauvegarde d'état de Nebula IA (module utilitaire).

⚠ Refactoré : plus AUCUN effet de bord à l'import. Avant, importer ce module
réécrivait le fichier de sauvegarde et injectait un message codé en dur dans
l'historique. Les fonctions ne font désormais rien tant qu'on ne les appelle pas.

Le fichier est aligné sur celui de `Nebula_IA/main.py` (nebula_saves.json,
résolu depuis ce dossier et non depuis le CWD courant).
"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "nebula_saves.json")


def save_state(conversation_history, system_prompt, preferences, self_improvement_data):
    data = {
        "conversation_history": conversation_history,
        "system_prompt": system_prompt,
        "preferences": preferences,
        "self_improvement_data": self_improvement_data,
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("Nebula AI state saved ->", SAVE_FILE)


def load_state():
    """Charge l'état. Retourne les valeurs par défaut si absent ou corrompu."""
    if not os.path.exists(SAVE_FILE):
        return [], "", {}, {"generation_count": 0, "last_update": None}
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        # Fichier corrompu : on repart sur des valeurs par défaut au lieu de crasher.
        return [], "", {}, {"generation_count": 0, "last_update": None}
    return (
        data.get("conversation_history", []),
        data.get("system_prompt", ""),
        data.get("preferences", {}),
        data.get("self_improvement_data", {"generation_count": 0, "last_update": None}),
    )


if __name__ == "__main__":
    # Démo explicite : ne s'exécute QUE si on lance ce fichier directement.
    history, prompt, prefs, improve = load_state()
    history.append({"user": "Salut", "nebula": "Hello! How can I help today?"})
    improve["generation_count"] += 1
    improve["last_update"] = datetime.now().isoformat()
    save_state(history, prompt, prefs, improve)
