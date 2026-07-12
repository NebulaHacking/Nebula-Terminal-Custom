import os
import platform
import subprocess
import sys

def install_on_windows():
    # Vérifie si Scoop est installé
    scoop_check = subprocess.run("scoop --version", shell=True, capture_output=True, text=True)
    if scoop_check.returncode != 0:
        print("Scoop non trouvé, installation...")
        # Installe Scoop
        subprocess.run(
            'powershell -Command "Set-ExecutionPolicy RemoteSigned -scope CurrentUser; '
            'iwr -useb get.scoop.sh | iex"',
            shell=True
        )
    else:
        print("Scoop déjà installé.")

    # Ajout des buckets et installation de flix-cli
    subprocess.run("scoop bucket add extras", shell=True)
    subprocess.run("scoop bucket add flix-cli https://github.com/DemonKingSwarn/flix-cli-bucket.git", shell=True)
    subprocess.run("scoop install flix-cli", shell=True)

def install_on_linux():
    # Vérifie si pip est installé
    pip_check = subprocess.run("pip --version", shell=True, capture_output=True, text=True)
    if pip_check.returncode != 0:
        print("pip non trouvé, installation...")
        subprocess.run("sudo apt update && sudo apt install -y python3-pip", shell=True)
    
    # Installation de flix-cli
    subprocess.run("pip install flix-cli", shell=True)

def run_flix_cli():
    system = platform.system()
    if system == "Windows":
        # Ouvre un nouveau terminal et lance flix-cli
        subprocess.run('start powershell -NoExit -Command "flix-cli"', shell=True)
    elif system == "Linux":
        # Tente d'ouvrir gnome-terminal ou x-terminal-emulator
        try:
            subprocess.run("gnome-terminal -- flix-cli", shell=True)
        except:
            subprocess.run("x-terminal-emulator -e flix-cli", shell=True)

def main():
    system = platform.system()
    if system == "Windows":
        install_on_windows()
    elif system == "Linux":
        install_on_linux()
    else:
        print(f"Système non supporté : {system}")
        return
    
    run_flix_cli()

if __name__ == "__main__":
    main()
