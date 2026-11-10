import subprocess
import json
import colorama
from datetime import datetime
import os
import sys
import re
import requests
import tempfile
import platform
import threading
import time

# ===================== CONFIG =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "nebula_saves.json")

DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_MODE = "local"
DEFAULT_VOCAL = "OFF"  # Défault vocal ON
DEFAULT_TTS = "local"  # Défault TTS ElevenLabs
RESPONSE_TIMEOUT = 120  # secondes (le 1er chargement d'un modèle 8B peut être long)
MAX_RETRIES = 2
ONLINE_MODEL = "gpt-4o-mini"

# ==================================================

# ---------------- STATE --------------------------
def save_state(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(colorama.Fore.RED + f"[!] Impossible de sauvegarder l'état : {e}" + colorama.Fore.RESET)

def load_state():
    if not os.path.exists(SAVE_FILE):
        return {
            "history": [],
            "system_prompt": "",
            "mode": DEFAULT_MODE,
            "vocal": DEFAULT_VOCAL,
            "tts": DEFAULT_TTS,
            "model": DEFAULT_MODEL,
            "stats": {"count": 0}
        }
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["history"] = data.get("history", [])
            data["system_prompt"] = data.get("system_prompt", "")
            data["mode"] = data.get("mode", DEFAULT_MODE)
            data["vocal"] = data.get("vocal", DEFAULT_VOCAL)
            data["tts"] = data.get("tts", DEFAULT_TTS)
            data["model"] = data.get("model", DEFAULT_MODEL)
            data["stats"] = data.get("stats", {"count": 0})
            return data
    except Exception as e:
        print(colorama.Fore.RED + f"[!] Erreur lecture sauvegarde : {e}, réinitialisation de l'état." + colorama.Fore.RESET)
        return {
            "history": [], "system_prompt": "", "mode": DEFAULT_MODE,
            "vocal": DEFAULT_VOCAL, "tts": DEFAULT_TTS,
            "model": DEFAULT_MODEL, "stats": {"count": 0}
        }

# ---------------- SYSTEM INFO --------------------
def print_system_info():
    try:
        print(f"User:        {os.getlogin()}")
        print(f"OS:          {platform.system()} {platform.release()}")
        print(f"Kernel:      {platform.version()}")
        print(f"CPU:         {platform.processor()}")
        try:
            import psutil
            mem = round(psutil.virtual_memory().total / (1024**3))
            print(f"Memory:      {mem} GB")
        except ImportError:
            print("Memory:      Unknown (psutil non installé)")
    except Exception as e:
        print(f"[!] Impossible de récupérer les infos système : {e}")

def _fail(msg):
    print(colorama.Fore.RED + msg + colorama.Fore.RESET)
    return msg

# ============== TTS ENGINES =======================
def speak_local(tts, text):
    if tts is None:
        return
    try:
        tts.say(text)
        tts.runAndWait()
    except Exception as e:
        print(colorama.Fore.RED + f"[!] Erreur TTS local : {e}" + colorama.Fore.RESET)

ELEVENLABS_VOICES = {
    "Alloy": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "Erxq0VzmQq5EdP9vDKmQ",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Antoni": "pNInz6obpgDQGcFmaJgB",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
}

CURRENT_VOICE_ID = ELEVENLABS_VOICES["Alloy"]

def speak_elevenlabs(text, voice_id=None):
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if not API_KEY:
        print(colorama.Fore.RED + "[!] Clé ELEVENLABS_API_KEY manquante." + colorama.Fore.RESET)
        return
    voice_id = voice_id or CURRENT_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability":0.65,"similarity_boost":0.75}}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(r.content)
                temp = f.name
            import sounddevice as sd
            import soundfile as sf
            data_audio, fs = sf.read(temp, dtype='float32')
            threading.Thread(target=lambda: (sd.play(data_audio, fs), sd.wait(), os.remove(temp)), daemon=True).start()
        else:
            print(colorama.Fore.RED + f"[!] Erreur ElevenLabs ({r.status_code}): {r.text}" + colorama.Fore.RESET)
    except Exception as e:
        print(colorama.Fore.RED + f"[!] Erreur réseau ElevenLabs : {e}" + colorama.Fore.RESET)

# -------- MENU pour changer de voix --------
def change_voice():
    global CURRENT_VOICE_ID
    print("\n--- Voix disponibles ---")
    for i, name in enumerate(ELEVENLABS_VOICES.keys(), start=1):
        print(f"{i} - {name}")
    choice = input("Choisis une voix (numéro) : ")
    try:
        choice = int(choice)
        if 1 <= choice <= len(ELEVENLABS_VOICES):
            CURRENT_VOICE_ID = list(ELEVENLABS_VOICES.values())[choice-1]
            print(colorama.Fore.GREEN + f"[+] Voix changée sur {list(ELEVENLABS_VOICES.keys())[choice-1]}" + colorama.Fore.RESET)
        else:
            print(colorama.Fore.RED + "[!] Choix invalide." + colorama.Fore.RESET)
    except ValueError:
        print(colorama.Fore.RED + "[!] Entrée invalide." + colorama.Fore.RESET)

# ================= IA CLASS ========================
class NebulaIA:
    def __init__(self, model=None):
        self.model = model or DEFAULT_MODEL
        self.history = []
        try:
            base_json = os.path.join(BASE_DIR, "base.json")
            if os.path.exists(base_json):
                with open(base_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.system_prompt = data.get("system_prompt", "")
            else:
                self.system_prompt = ""
        except Exception as e:
            print(colorama.Fore.RED + f"[!] Erreur lecture base.json : {e}" + colorama.Fore.RESET)
            self.system_prompt = ""

    # ---- LOCAL OLLAMA ----
    def ask_local(self, prompt):
        """Une requête Ollama, relancée au plus MAX_RETRIES fois (avant : récursion infinie)."""
        for attempt in range(1, MAX_RETRIES + 1):
            print(colorama.Fore.YELLOW + "thinking...")
            try:
                p = subprocess.run(
                    ["ollama", "run", self.model], input=prompt + "\n",
                    capture_output=True, text=True, encoding="utf-8", timeout=RESPONSE_TIMEOUT,
                )
            except FileNotFoundError:
                return _fail("[!] Ollama non trouvé. Installer avec 'nebula_ia_install'.")
            except subprocess.TimeoutExpired:  # subprocess.run tue le process lui-même
                print(colorama.Fore.RED + f"[!] Timeout local ({attempt}/{MAX_RETRIES})" + colorama.Fore.RESET)
                continue
            output = p.stdout.strip()
            if output:
                print(colorama.Fore.GREEN + output + colorama.Fore.RESET)
                return output
            err = p.stderr.strip()
            print(colorama.Fore.RED + f"[!] Réponse vide ({attempt}/{MAX_RETRIES}) {err[:200]}" + colorama.Fore.RESET)
        return _fail("[!] Pas de réponse d'Ollama.")

    # ---- ONLINE OPENAI ----
    def ask_online(self, prompt):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return _fail("[!] Aucune clé OPENAI_API_KEY trouvée.")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {"model": ONLINE_MODEL, "messages": [{"role": "user", "content": prompt}]}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.post("https://api.openai.com/v1/chat/completions",
                                  headers=headers, json=data, timeout=RESPONSE_TIMEOUT)
            except requests.RequestException as e:
                print(colorama.Fore.RED + f"[!] Erreur réseau ({attempt}/{MAX_RETRIES}) : {e}" + colorama.Fore.RESET)
                continue
            if r.status_code != 200:  # clé invalide, quota… : inutile de réessayer
                return _fail(f"[!] Erreur OpenAI ({r.status_code}) : {r.text[:200]}")
            response = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if response:
                print(colorama.Fore.CYAN + response + colorama.Fore.RESET)
                return response
        return _fail("[!] Pas de réponse d'OpenAI.")

    def ask(self, text, mode):
        self.history.append({"user": text})
        full = self.system_prompt + "\n\n"
        for m in self.history[-20:]:
            if "user" in m: full += f"User: {m['user']}\n"
            if "nebula" in m: full += f"Nebula: {m['nebula']}\n"
        full += "Nebula:"
        if mode == "online":
            r = self.ask_online(full)
        else:
            r = self.ask_local(full)
        self.history[-1]["nebula"] = r
        return r

# ================= INTERFACE =======================
def launch():
    colorama.init(autoreset=True)
    print_system_info()

    state = load_state()
    nebula = NebulaIA(state["model"])
    nebula.history = state["history"]

    try:
        import pyttsx3
        tts = pyttsx3.init()
        tts.setProperty("rate", 220)
    except Exception as e:  # pas de moteur vocal : le chat texte reste utilisable
        print(colorama.Fore.RED + f"[!] TTS local indisponible : {e}" + colorama.Fore.RESET)
        tts = None

    print(colorama.Fore.MAGENTA + "\n=== NEBULA AI  ===\n")
    print("")
    print(colorama.Fore.MAGENTA + "\n(This version of Nebula is restricted for security reasons.)\n")

    while True:
        print(colorama.Fore.BLUE + f"\nMode: {state['mode']} | Vocal: {state['vocal']} | TTS: {state['tts']} | Model: {state['model']}\n")
        print(colorama.Fore.BLUE + "Settings rapides: 'settings', Quit: 'exit' ou 'quit'\n")
        user = input(colorama.Fore.YELLOW + "You : " + colorama.Fore.RESET)

        if user.lower() in ["exit", "quit"]:
            break

        if user.lower() == "settings":
            while True:
                print("\n--- SETTINGS ---")
                print("1 - ON/OFF Vocal")
                print("2 - TTS Engine (local/elevenlabs)")
                print("3 - Mode IA (local/online)")
                print("4 - Changer modèle")
                print("5 - Reset historique")
                print("6 - Stats")
                print("7 - Changer voix ElevenLabs")
                print("8 - Retour")
                c = input(">>> ")
                if c == "1":
                    state["vocal"] = "ON" if state["vocal"] == "OFF" else "OFF"
                elif c == "2":
                    state["tts"] = "elevenlabs" if state["tts"] == "local" else "local"
                elif c == "3":
                    state["mode"] = "online" if state["mode"] == "local" else "local"
                elif c == "4":
                    new = input("Nouveau modèle: ")
                    state["model"] = new
                    nebula.model = new
                elif c == "5":
                    nebula.history = []
                    print("Historique vidé.")
                    try:
                        os.remove(SAVE_FILE)
                    except FileNotFoundError:
                        pass
                elif c == "6":
                    print("Messages générés:", state["stats"]["count"])
                elif c == "7":
                    change_voice()
                elif c == "8":
                    break
                save_state(state)
            continue

        response = nebula.ask(user, state["mode"])

        if state["vocal"] == "ON":
            if state["tts"] == "elevenlabs":
                threading.Thread(target=speak_elevenlabs, args=(response,), daemon=True).start()
            else:
                threading.Thread(target=speak_local, args=(tts, response), daemon=True).start()

        state["history"] = nebula.history
        state["stats"]["count"] += 1
        save_state(state)

if __name__ == "__main__":
    launch()
