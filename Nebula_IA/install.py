import subprocess
import sys
import os
import platform
import time

MODEL_NAME = "llama3.1:8b"

def install_ollama():
    """Installer Ollama via .exe et forcer le redémarrage du script"""
    system = platform.system()
    if system == "Windows":
        installer = os.path.join(os.path.dirname(__file__), "ModelSetup.exe")
        if os.path.exists(installer):
            print("[+] Lancement de l'installateur Ollama...")
            # On lance l'installateur et on attend qu'il se termine
            subprocess.run([installer], check=True)
            
            print("\n" + "="*50)
            print("[!] INSTALLATION TERMINEE")
            print("Pour que Windows reconnaisse la nouvelle commande 'ollama' :")
            print("1. Ferme cette fenêtre (le terminal).")
            print("2. Relance 'python install.py'.")
            print("="*50)
            
            # On quitte pour forcer l'utilisateur à relancer l'environnement
            sys.exit(0)
        else:
            print("👉 Télécharge Ollama ici : https://ollama.com/download/windows")
            print("Puis relance ce script après installation.")
            sys.exit(0)
    else:
        print("[!] Installation automatique uniquement pour Windows.")
        sys.exit(1)




from colorama import Fore, Style

def pull_model_user_folder():
    print("")
    print("Ouvrez un nouveau terminal et tapez :")
    print(Fore.RED + "ollama pull llama3.1:8b" + Style.RESET_ALL)
    print("")
    print("[+] Terminé ! Le terminal est maintenant en train de télécharger.")


def setup_openai():
    """Configure le mode online/OpenAI"""
    print("\n=== CONFIGURATION MODE ONLINE ===")
    key = input("Entre ta clé OPENAI_API_KEY (laisser vide pour ignorer) : ").strip()
    if key:
        os.environ["OPENAI_API_KEY"] = key
        print("[+] Clé enregistrée pour cette session.")
    else:
        print("[!] Mode online non configuré.")

def main():
    print("\n===== INSTALLATION NEBULA AI =====\n")
    print("Que veux-tu installer ?")
    print("1 - Mode LOCAL (Ollama + modèle)")
    print("2 - Mode ONLINE (OpenAI API uniquement)")
    print("3 - Quitter")

    choice = input("\nChoix : ").strip()
    if choice == "3":
        print("Installation annulée.")
        sys.exit(0)

    if choice == "1":
        # Vérification si ollama est déjà reconnu
        ollama_check = subprocess.run(["where", "ollama"], capture_output=True, text=True)
        
        if ollama_check.returncode != 0:
            ans = input("[?] Ollama n'est pas détecté. L'as-tu déjà installé ? (o/n) : ").lower()
            if ans == "n":
                ask_install = input("Veux-tu installer Ollama maintenant ? (o/n) : ").lower()
                if ask_install == "o":
                    install_ollama()
                    
                else:
                    print("[!] Impossible de continuer sans Ollama.")
                    sys.exit(1)
            else:
                sys.exit(1)

        # Si Ollama est trouvé, on lance le téléchargement
        pull_model_user_folder()
        print("\n[+] Installation locale terminée.")

    elif choice == "2":
        setup_openai()
        print("\n[+] Installation online terminée.")

    print("\nTu peux maintenant lancer Nebula avec :")
    print("    python main.py")

if __name__ == "__main__":
    main()