"""dirb — recherche de répertoires et fichiers cachés sur un site web (en parallèle).

À n'utiliser que sur des sites que vous possédez ou êtes autorisé à tester.
"""
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

WORDLIST_DIR = Path(__file__).resolve().parent.parent / "DirbWordListe"
WORKERS = 20
# Codes qui prouvent que le chemin existe (401/403 = existe mais protégé), avec leur couleur.
_INTERESTING = {200: "\033[92m", 204: "\033[92m", 301: "\033[96m", 302: "\033[96m", 307: "\033[96m",
                308: "\033[96m", 401: "\033[93m", 403: "\033[91m", 405: "\033[93m", 500: "\033[95m"}

# Mini wordlist si -m
mots_minimal = ["admin", "login", "dashboard", "config", "test", "server",
                "panel", "secret", "backup", "old"]

# Wordlist par défaut (fallback si baseWord.txt introuvable).
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


def _lire_wordlist(chemin) -> list[str]:
    with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def dirb(url_base, minimal=False, wordlist=None):
    """
    Scan de répertoires, WORKERS requêtes en parallèle. Ctrl+C pour arrêter.
    - minimal=True : utilise la mini-liste intégrée
    - wordlist=chemin_fichier : fichier donné (cherché aussi dans DirbWordListe/)
    - sinon : DirbWordListe/baseWord.txt, avec fallback DEFAULT_WORDLIST
    Renvoie la liste des URL trouvées (codes 200/204).
    """
    if not url_base.startswith(("http://", "https://")):
        url_base = "http://" + url_base
    url_base = url_base.rstrip("/")

    if minimal:
        mots = mots_minimal
    elif wordlist:
        chemin = next((c for c in (Path(wordlist), WORDLIST_DIR / Path(wordlist).name) if c.is_file()), None)
        if chemin is None:
            print(f"Fichier introuvable : {wordlist}")
            return []
        mots = _lire_wordlist(chemin)
    else:
        base = WORDLIST_DIR / "baseWord.txt"
        mots = (_lire_wordlist(base) if base.is_file() else []) or list(DEFAULT_WORDLIST)
    mots = list(dict.fromkeys(mots))  # sans doublons, ordre conservé

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Nebula dirb)"

    def tester(mot):
        try:
            r = session.get(f"{url_base}/{mot.lstrip('/')}", timeout=5, allow_redirects=False)
            return mot, r.status_code, len(r.content)
        except requests.RequestException:
            return mot, None, 0

    # Un chemin qui ne peut pas exister : s'il répond comme une vraie page, le site renvoie
    # la même chose pour tout (« soft 404 ») et on ignore les réponses de ce code.
    _, code_faux, _ = tester(f"nebula-{secrets.token_hex(8)}")
    if code_faux is None:
        print(f"[!] Impossible de joindre {url_base}")
        return []
    ignorer = code_faux if code_faux in _INTERESTING else None
    if ignorer:
        print(f"[!] Le site répond {ignorer} même pour une page inexistante : les réponses {ignorer} sont ignorées.")

    print(f"--- Scan DIRB démarré sur {url_base} ---")
    print(f"Total de mots à tester : {len(mots)}  ({WORKERS} requêtes en parallèle, Ctrl+C pour arrêter)\n")

    url_valide, testés, erreurs = [], 0, 0
    pool = ThreadPoolExecutor(WORKERS)
    try:
        for mot, code, taille in pool.map(tester, mots):
            testés += 1
            if code is None:
                erreurs += 1
            elif code in _INTERESTING and code != ignorer:
                print(f"{_INTERESTING[code]}[{code}] {url_base}/{mot}\033[0m  ({taille} octets)")
                if code in (200, 204):
                    url_valide.append(f"{url_base}/{mot}")
    except KeyboardInterrupt:
        print("\n\033[93mScan interrompu par l'utilisateur.\033[0m")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    print(f"\n--- Scan terminé : {len(url_valide)} trouvés sur {testés} tests"
          + (f", {erreurs} erreurs de connexion" if erreurs else "") + " ---")
    return url_valide


def main():
    """Ligne de commande : python dirb.py [-m] [-w wordlist] <url>"""
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


if __name__ == "__main__":
    main()
