import json
from datetime import datetime
import os

SAVE_FILE = "nebula_save.json"

def save_state(conversation_history, system_prompt, preferences, self_improvement_data):
    data = {
        "conversation_history": conversation_history,
        "system_prompt": system_prompt,
        "preferences": preferences,
        "self_improvement_data": self_improvement_data
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print("✅ Nebula AI state saved.")

def load_state():
    if not os.path.exists(SAVE_FILE):
        return [], "", {}, {"generation_count": 0, "last_update": None}
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return (data.get("conversation_history", []),
            data.get("system_prompt", ""),
            data.get("preferences", {}),
            data.get("self_improvement_data", {"generation_count": 0, "last_update": None}))

# Exemple d'utilisation
conversation_history, system_prompt, preferences, self_improvement_data = load_state()

# Ajouter un nouveau message
conversation_history.append({"user": "Salut", "nebula": "Hello! How can I help today?"})

# Mettre à jour les données self-improvement
self_improvement_data["generation_count"] += 1
self_improvement_data["last_update"] = datetime.now().isoformat()

save_state(conversation_history, system_prompt, preferences, self_improvement_data)
