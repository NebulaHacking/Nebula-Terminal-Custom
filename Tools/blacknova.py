import random
import time
import os
import sys

# Gestion des couleurs (Windows/Unix)
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    RESET = colorama.Fore.RESET
except:
    GREEN = RED = YELLOW = RESET = ""

# Fonction pour afficher une barre de progression
def progress_bar(task, total=30, delay=0.05):
    for i in range(total + 1):
        percent = int((i / total) * 100)
        bar = "=" * i + " " * (total - i)
        print(f"{task}: [{bar}] {percent}%", end="\r")
        time.sleep(delay)
    print()

# Fonction principale BlackNova
def blacknova(cible, options=None, exploits=None):
    rapport = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    rapport.append(f"=== BlackNova v2.0 - Analyse de {cible} ({timestamp}) ===\n")
    print(f"\n=== BlackNova v2.0 - Analyse de {cible} ===\n")
    
    # Étape 1 : Scan réseau simulé
    scan_mode = "Standard"
    if options:
        if "-f" in options:
            scan_mode = "Rapide"
        elif "-a" in options:
            scan_mode = "Complet"
    print(f"-> Scan réseau ({scan_mode}) en cours...")
    rapport.append(f"Scan réseau ({scan_mode}) en cours...\n")
    
    ports = random.sample(range(20, 1025), 15)
    open_ports = []
    
    for port in ports:
        status = random.choice(["OUVERT", "FERMÉ"])
        color_status = GREEN + status + RESET if status=="OUVERT" else RED + status + RESET
        line = f"Port {port}: {color_status}"
        print(line)
        rapport.append(f"Port {port}: {status}")
        if status == "OUVERT":
            open_ports.append(port)
        time.sleep(0.1)
    
    progress_bar("Scan terminé", total=20, delay=0.03)
    
    # Étape 2 : Exploits simulés
    if exploits:
        print("\n-> Tentatives d'exploitation simulées...")
        rapport.append("\nTentatives d'exploitation simulées...")
        for exploit in exploits:
            print(f"  Exploit '{exploit}' en cours...")
            rapport.append(f"Exploit '{exploit}' en cours...")
            success = random.choice([True, False])
            time.sleep(0.5)
            if success:
                line = GREEN + f"  Exploit '{exploit}' réussi ! (simulation)" + RESET
                rapport.append(f"Exploit '{exploit}' réussi !")
            else:
                line = RED + f"  Exploit '{exploit}' échoué (simulation)" + RESET
                rapport.append(f"Exploit '{exploit}' échoué")
            print(line)
    
    # Étape 3 : Rapport visuel ASCII
    print("\n=== Rapport Visuel ===")
    rapport.append("\nRapport Visuel ASCII\n")
    ascii_art = [
        " ██████  ███    ██ ██████  ██   ██ ███    ██ ",
        "██       ████   ██ ██   ██ ██   ██ ████   ██ ",
        "██   ███ ██ ██  ██ ██████  ███████ ██ ██  ██ ",
        "██    ██ ██  ██ ██ ██      ██   ██ ██  ██ ██ ",
        " ██████  ██   ████ ██      ██   ██ ██   ████ "
    ]
    for line in ascii_art:
        print(YELLOW + line + RESET)
        rapport.append(line)
    
    vuln_score = random.randint(10, 100)
    line = f"\nScore de vulnérabilité (simulation) : {vuln_score}/100"
    print(line)
    rapport.append(line)
    
    if vuln_score > 70:
        alert = RED + "⚠️  Attention : Failles potentielles détectées !" + RESET
    else:
        alert = GREEN + "✅ Aucun problème critique détecté (simulation)." + RESET
    print(alert)
    rapport.append(alert)
    
    # Étape 4 : Hotkeys interactifs
    print("\nAppuyez sur 'q' pour quitter, 'r' pour rafraîchir, 's' pour sauvegarder le rapport.")
    while True:
        key = input("Hotkey > ").lower()
        if key == "q":
            print("Analyse terminée.")
            break
        elif key == "r":
            print("Rafraîchissement du rapport...")
            blacknova(cible, options, exploits)
            break
        elif key == "s":
            filename = f"rapport_blacknova_{cible.replace('.', '_')}.txt"
            with open(filename, "w") as f:
                f.write("\n".join(rapport))
            print(f"Rapport sauvegardé dans '{filename}'")
        else:
            print("Hotkey non reconnu. Utilisez 'q', 'r' ou 's'.")


