
import os
import requests
import sys
import glob
import keyboard

# Mini wordlist si -m
mots_minimal = ["admin", "login", "dashboard", "config", "test", "server",
                "panel", "secret", "backup", "old"]

def dirb(url_base, minimal=False, wordlist=None):
    """
    Scan de répertoires basique.
    - minimal=True : utilise la mini-liste intégrée
    - wordlist=chemin_fichier : utilise un fichier wordlist spécifique
    - sinon : utilise DirbWordListe/baseWord.txt
    """
    url_valide = []
    testés = 0
    trouvés = 0

    # Ajouter le http:// si absent
    if not url_base.startswith(("http://", "https://")):
        url_base = "http://" + url_base

    # Sélection de la liste de mots
    if minimal:
        mots = mots_minimal
    elif wordlist:
        mots = []
        # Vérifie si le fichier existe à l'emplacement donné
        if os.path.exists(wordlist):
            with open(wordlist, "r", encoding="utf-8") as f:
                mots = [ligne.strip() for ligne in f if ligne.strip()]
        else:
            # Recherche automatiquement dans tous les dossiers DirbWordListe
            fichiers_trouves = glob.glob(os.path.join(os.getcwd(), "**", "DirbWordListe", os.path.basename(wordlist)), recursive=True)
            if fichiers_trouves:
                wordlist = fichiers_trouves[0]  # On prend le premier trouvé
                with open(wordlist, "r", encoding="utf-8") as f:
                    mots = [ligne.strip() for ligne in f if ligne.strip()]
            else:
                print(f"Fichier introuvable : {wordlist}")
                return
    else:
        fichiers_trouves = glob.glob(os.path.join(os.getcwd(), "**", "DirbWordListe", "baseWord.txt"), recursive=True)
        if fichiers_trouves:
            fichier = fichiers_trouves[0]  # prend le premier trouvé
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                mots = [ligne.strip() for ligne in f if ligne.strip()]
        except FileNotFoundError:
            print(f"Fichier introuvable : {fichier}")
            return

    total = len(mots)
    print(f"--- Scan DIRB démarré sur {url_base} ---")
    print(f"Total de mots à tester : {total}\n")

    for mot in mots:
        # Vérifie si l'utilisateur appuie sur "q" pour quitter
        if keyboard.is_pressed("q"):
            print("\n\033[93mScan interrompu par l'utilisateur.\033[0m")
            break

        url = f"{url_base.rstrip('/')}/{mot}"
        testés += 1
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"\033[92m[200] Trouvé : {url}\033[0m")  # Vert
                url_valide.append(url)
                trouvés += 1
            elif r.status_code == 403:
                print(f"\033[91m[403] Accès refusé : {url}\033[0m")  # Rouge
            else:
                print(f"[{r.status_code}] {url}")
        except Exception:
            print(f"[!] Erreur de connexion avec {url}")

        # Afficher stats si l'utilisateur appuie sur "r"
        if keyboard.is_pressed("r"):
            print(f"\n\033[96m--- STATS DU SCAN ---")
            print(f"Testés   : {testés}/{total}")
            print(f"Trouvés  : {trouvés} -> {url_valide}")
            print(f"Restants : {total - testés}")
            print(f"---------------------\033[0m\n")

    print(f"\n--- Scan terminé : {trouvés} trouvés sur {testés} tests ---")
    if url_valide:
        print("URLs valides :", url_valide)

    return url_valide


def main():
    """
    Gestion des arguments en ligne de commande :
    -m : mini wordlist
    -w <fichier> : wordlist personnalisée
    <url> : site à scanner
    """
    minimal = False
    wordlist = None
    url = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "-m":
            minimal = True
            i += 1
        elif args[i] == "-w" and i + 1 < len(args):
            wordlist = args[i + 1]
            i += 2
        else:
            url = args[i]
            i += 1

    if not url:
        print("Usage: python dirb.py [-m] [-w wordlist] <url>")
        return

    dirb(url, minimal=minimal, wordlist=wordlist)


# Exécution si lancé directement
if __name__ == "__main__":
    main()
