# launch.py — Lanceur principal de Nebula Terminal Custom
import os
import sys
import hashlib
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / "venv"
REQ_FILE = BASE_DIR / "requirements.txt"
MAIN_FILE = BASE_DIR / "main.py"
ENV_FILE = BASE_DIR / ".env"
STAMP_FILE = VENV_DIR / ".requirements.sha256"  # hash du dernier requirements.txt installé

def load_env_file():
    """Charge le fichier .env (s'il existe) dans os.environ.

    Implémenté sans python-dotenv ici pour fonctionner même avant
    l'installation des dépendances. Respecte les variables déjà
    définies dans l'environnement (celles-ci ont la priorité).
    """
    if not ENV_FILE.exists():
        print("[*] Aucun fichier .env trouvé (les variables avancées ne sont pas définies).")
        print("[*] Copie .env.example vers .env pour activer les clés API.")
        return
    loaded = 0
    try:
        for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded += 1
        if loaded:
            print(f"[*] Fichier .env chargé ({loaded} variables).")
        else:
            print("[*] Fichier .env présent, aucune nouvelle variable chargée.")
    except OSError as e:
        print(f"[!] Impossible de lire {ENV_FILE} ({e}).")

def run(cmd, **kwargs):
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[ERR] Command returned {result.returncode}")
        sys.exit(result.returncode)

def venv_is_usable():
    """Le venv existe ET son python démarre (un venv copié d'un autre PC pointe vers un python absent)."""
    py = get_venv_python()
    if not py.exists():
        return False
    try:
        return subprocess.run([str(py), "-c", "pass"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def create_venv(python_exe=None):
    if VENV_DIR.exists():
        if venv_is_usable():
            print("[*] venv déjà présent.")
            return
        print("[!] venv inutilisable (créé sur une autre machine ?) -> recréation.")
        shutil.rmtree(VENV_DIR)
    print("[*] Création de l'environnement virtuel (venv)...")
    run([python_exe or sys.executable, "-m", "venv", str(VENV_DIR)])
    print("[*] venv créé.")

def get_venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def main():
    # 0) Charge les variables d'environnement depuis .env
    load_env_file()

    # 1) Crée venv si nécessaire
    create_venv()

    python_bin = str(get_venv_python())
    if not Path(python_bin).exists():
        print(f"[!] Impossible de localiser le python du venv ({python_bin}).")
        print("[!] Vérifie la création du venv ou utilise --python / path_to_python")
        sys.exit(1)

    # 2) Installer requirements seulement s'ils ont changé depuis la dernière installation
    if REQ_FILE.exists():
        req_hash = hashlib.sha256(REQ_FILE.read_bytes()).hexdigest()
        if STAMP_FILE.exists() and STAMP_FILE.read_text().strip() == req_hash:
            print("[*] Dépendances à jour.")
        else:
            print("[*] Installation des dépendances (depuis requirements.txt)...")
            run([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
            run([python_bin, "-m", "pip", "install", "-r", str(REQ_FILE)])
            STAMP_FILE.write_text(req_hash)
    else:
        print("[!] Pas de requirements.txt trouvé (skipped).")

    # 3) Lancer le main avec le python du venv
    if MAIN_FILE.exists():
        print("[*] Lancement du projet avec le venv...")
        run([python_bin, str(MAIN_FILE)])
    else:
        print(f"[!] Impossible de trouver {MAIN_FILE}")

if __name__ == "__main__":
    main()
