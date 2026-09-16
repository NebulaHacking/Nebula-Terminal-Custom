
import os
import requests
import sys
import glob
import keyboard

# Mini wordlist si -m
mots_minimal = ["admin", "login", "dashboard", "config", "test", "server",
                "panel", "secret", "backup", "old"]

# Wordlist par défaut (fallback si baseWord.txt introuvable).
# Fusion de `mots_dirb_base`, liste morte de l'ancien main.py (lignes 54-67).
DEFAULT_WORDLIST = [
    "login", "dashboard", "config", "backup", "admin", "test", "uploads", "images",
    "js", "css", "includes", "api", "server-status", "data", "private", "tmp", "db",
    "old", "dev", "phpmyadmin", "console", "hidden", "auth", "cgi-bin", "panel",
    "webadmin", "setup", "install", "users", "register", "logout", "home", "index",
    "status", "bin", "core", "access", "files", "assets", "secure", "secret", "mail",
    "robots.txt", ".htaccess", ".htpasswd", "sitemap.xml", "logs", "downloads",
    "config.bak", "admin_old", "wordpress", "wp-login", "wp-admin", "site", "beta",
    "staging", "v1", "v2", "debug", "error", "signin", "signup", "rest", "json",
    "xml", "account", "contact", "form", "pay", "payment", "invoice", "api-docs",
    "monitor", "shell", "node_modules", "vendor", "lib", "static", "public", "portal",
    "client", "server", "manager", "sys", "env", "token", "session", "login.php",
    "index.php", "main", "core_old", "vulnerable", "exposed"
]

def dirb(url_base, minimal=False, wordlist=None):
    """
    Scan de répertoires basique.
    - minimal=True : utilise la mini-liste intégrée
    - wordlist=chemin_fichier : utilise un fichier wordlist spécifique
    - sinon : DirbWordListe/baseWord.txt, avec fallback DEFAULT_WORDLIST
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
        # Par défaut : baseWord.txt si trouvé, sinon DEFAULT_WORDLIST (anc. mots_dirb_base)
        mots = None
        fichiers_trouves = glob.glob(os.path.join(os.getcwd(), "**", "DirbWordListe", "baseWord.txt"), recursive=True)
        if fichiers_trouves:
            with open(fichiers_trouves[0], "r", encoding="utf-8") as f:
                mots = [ligne.strip() for ligne in f if ligne.strip()]
        if not mots:
            mots = list(DEFAULT_WORDLIST)

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
