# launch.py (remplace ton fichier)
import os
import sys
import subprocess
import venv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / "venv"
REQ_FILE = BASE_DIR / "requirements.txt"
MAIN_FILE = BASE_DIR / "main.py"

def run(cmd, **kwargs):
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[ERR] Command returned {result.returncode}")
        sys.exit(result.returncode)

def create_venv(python_exe=None):
    if VENV_DIR.exists():
        print("[*] venv déjà présent.")
        return
    print("[*] Création de l'environnement virtuel (venv)...")
    # Utilise le python courant si pas fourni
    python_to_use = python_exe or sys.executable
    # Crée le venv en appelant python -m venv pour compatibilité
    run([python_to_use, "-m", "venv", str(VENV_DIR)])
    print("[*] venv créé.")

def get_venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def main():
    # 1) Crée venv si nécessaire
    create_venv()

    python_bin = str(get_venv_python())
    if not Path(python_bin).exists():
        print(f"[!] Impossible de localiser le python du venv ({python_bin}).")
        print("[!] Vérifie la création du venv ou utilise --python / path_to_python")
        sys.exit(1)

    # 2) Installer requirements si présent
    if REQ_FILE.exists():
        print("[*] Installation des dépendances (depuis requirements.txt)...")
        # Toujours appeler pip via python -m pip (plus fiable cross-platform)
        run([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
        run([python_bin, "-m", "pip", "install", "-r", str(REQ_FILE)])
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
