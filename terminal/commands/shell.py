"""Commandes du shell — alias, unalias, run (scripts), update, tuto."""
import re
import shlex
import subprocess
from pathlib import Path

from terminal.registry import REGISTRY

ROOT = Path(__file__).resolve().parent.parent.parent
MAX_DEPTH = 5
_ALIAS = re.compile(r"^[A-Za-z0-9_.-]{1,30}$")
_depth = 0


# ---------------------------------------------------------------------
# Alias
# ---------------------------------------------------------------------
@REGISTRY.register("alias", help_text=(
    "alias                    - Liste tes alias\n"
    "alias <nom> <commande>   - Crée un raccourci (sauvegardé avec ton profil)\n"
    "Exemples : alias s scan -f    puis    s 192.168.1.1\n"
    "           alias recon run recon.nbl"), summary="Créer des raccourcis de commandes")
def _alias(ctx, argv, raw):
    if len(argv) == 1:
        if not ctx.aliases:
            print("Aucun alias. Exemple : alias s scan -f")
        for name, value in sorted(ctx.aliases.items()):
            print(f"  {name:<12} = {value}")
        return
    if len(argv) < 3:
        raise ValueError("Usage : alias <nom> <commande>")
    name, value = argv[1], raw.split(None, 2)[2].strip()
    if not _ALIAS.match(name):
        raise ValueError("Nom d'alias : lettres, chiffres, _ . - (30 max)")
    if name in ("alias", "unalias"):
        raise ValueError(f"« {name} » ne peut pas être redéfini")
    if REGISTRY.get(name) is not None:
        print(f"[!] « {name} » est aussi une commande Nebula : ton alias la remplacera.")
    ctx.aliases[name] = value
    print(f"[+] {name} = {value}")


@REGISTRY.register("unalias", help_text="unalias <nom>    - Supprimer un alias", summary="Supprimer un alias")
def _unalias(ctx, argv, raw):
    if len(argv) != 2 or argv[1] not in ctx.aliases:
        raise ValueError("Usage : unalias <nom>  (alias pour la liste)")
    del ctx.aliases[argv[1]]
    print(f"[+] Alias {argv[1]} supprimé")


# ---------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------
RUN_HELP = """run <script> [arguments...]   - Exécute une liste de commandes Nebula, une par ligne

Le script est cherché dans l'espace de travail, puis sur le disque.
Dans le script : # = commentaire, $1 $2 ... = arguments, $@ = tous les arguments.
Option -e : s'arrêter à la première commande en erreur ou refusée.

Exemple (fichier recon.nbl) :
   # reconnaissance de base
   dns $1
   whois $1
   headers $1 > headers-$1.txt
   sslscan $1
Puis : run recon.nbl example.com"""


def _load_script(ctx, name):
    try:
        return ctx.vfs.read(name), f"espace de travail : {name}"
    except ValueError:
        disk = Path(name.strip('"')).expanduser()
        if disk.is_file():
            return disk.read_text(encoding="utf-8", errors="replace"), str(disk)
    raise ValueError(f"Script introuvable : {name} (ni dans l'espace de travail, ni sur le disque)")


@REGISTRY.register("run", help_text=RUN_HELP, summary="Exécuter un script de commandes Nebula")
def _run(ctx, argv, raw):
    global _depth
    words = shlex.split(raw, posix=False)[1:]
    stop = "-e" in words
    words = [w for w in words if w != "-e"]
    if not words:
        raise ValueError("Usage : run <script> [arguments...]")
    text, where = _load_script(ctx, words[0])
    args = [w.strip('"') for w in words[1:]]
    if _depth >= MAX_DEPTH:
        raise ValueError(f"Trop de scripts imbriqués (max {MAX_DEPTH}) : un script s'appelle-t-il lui-même ?")

    def substitute(line):
        line = line.replace("$@", " ".join(args))
        return re.sub(r"\$(\d)", lambda m: args[int(m.group(1)) - 1] if 0 < int(m.group(1)) <= len(args) else "", line)

    lines = [substitute(l.strip()) for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    print(f"[*] Script {where} : {len(lines)} commandes")
    _depth += 1
    done = 0
    try:
        for line in lines:
            print(f"\n▶ {line}")
            status = REGISTRY.dispatch(ctx, line)
            done += 1
            if stop and status in ("erreur", "refusé"):
                print(f"[!] Arrêt du script (option -e) : « {line} » → {status}")
                break
            if ctx.should_exit:
                break
    finally:
        _depth -= 1
    print(f"\n[*] Script terminé : {done}/{len(lines)} commandes exécutées")


# ---------------------------------------------------------------------
# Mise à jour
# ---------------------------------------------------------------------
REPO, BRANCH = "NebulaHacking/Nebula-Terminal-Custom", "main"
_RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
_ZIP = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.zip"
# Jamais écrasés par une mise à jour ZIP (données de l'utilisateur ; de toute façon absents du dépôt).
_KEEP = {".git", "venv", ".venv", "users", "missions", "saves", ".env", "Mind-NTC"}
_MAX_ZIP = 200 * 2**20
_REQ_NOTE = "\nLes dépendances ont changé : elles seront installées au prochain lancement (python launch.py)."


def _vtuple(version: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def remote_version(timeout: float = 10) -> str | None:
    """Numéro de version publié sur GitHub (branche main). None si le fichier n'en contient pas."""
    import requests

    r = requests.get(_RAW + "terminal/__init__.py", timeout=timeout)
    r.raise_for_status()
    m = re.search(r'__version__ = "(.+?)"', r.text)
    return m.group(1) if m else None


def _remote_news(version: str) -> str:
    """La section du CHANGELOG publié qui correspond à `version` (vide si introuvable)."""
    import requests

    try:
        text = requests.get(_RAW + "CHANGELOG.md", timeout=10).text
    except requests.RequestException:
        return ""
    m = re.search(rf"^## {re.escape(version)}\b.*?(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(0).strip()[:3000] if m else ""


def _git_update(root: Path) -> str:
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, timeout=120)  # noqa: E731
    try:
        branch = run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    except FileNotFoundError as e:
        raise ValueError("git n'est pas installé sur ce PC") from e
    if branch != BRANCH:
        raise ValueError(f"Tu es sur la branche « {branch} » : les versions publiées sont sur « {BRANCH} ». "
                         f"Passe dessus avec :  git switch {BRANCH}   puis relance update.")
    if run("status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ValueError("Des fichiers du projet ont été modifiés : commit ou annule-les avant de mettre à jour")
    before = run("rev-parse", "HEAD").stdout.strip()
    pulled = run("pull", "--ff-only", f"https://github.com/{REPO}.git", BRANCH)
    if pulled.returncode != 0:
        raise ValueError("Mise à jour impossible : " + (pulled.stderr.strip() or pulled.stdout.strip())[:300])
    changed = run("diff", "--name-only", before, "HEAD").stdout.split()
    return f"Récupérée avec git ({len(changed)} fichiers modifiés)." + \
        (_REQ_NOTE if {"requirements.txt", "requirements-full.txt"} & set(changed) else "")


def _zip_update(root: Path) -> str:
    """Projet téléchargé sans git : on récupère l'archive de GitHub et on remplace les fichiers du dépôt."""
    import io
    import zipfile

    import requests

    r = requests.get(_ZIP, timeout=120, stream=True)
    r.raise_for_status()
    data = io.BytesIO()
    for chunk in r.iter_content(1 << 16):
        data.write(chunk)
        if data.tell() > _MAX_ZIP:
            raise ValueError("Archive anormalement grosse : mise à jour annulée")
    root, written, req_changed = root.resolve(), 0, False
    with zipfile.ZipFile(data) as z:
        for info in z.infolist():
            rel = Path(*Path(info.filename).parts[1:])  # retire le dossier « Nebula-Terminal-Custom-main/ »
            if info.is_dir() or not rel.parts or rel.parts[0] in _KEEP:
                continue
            target = (root / rel).resolve()
            if not target.is_relative_to(root):  # chemin piégé (« ../ ») : refusé
                raise ValueError(f"Chemin refusé dans l'archive : {info.filename}")
            content = z.read(info)
            if target.exists() and target.read_bytes() == content:
                continue
            req_changed |= rel.name in ("requirements.txt", "requirements-full.txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            written += 1
    # shortcut: les fichiers supprimés sur GitHub restent sur le disque ; sans effet tant qu'aucun module ne les importe.
    return f"Téléchargée depuis GitHub ({written} fichiers remplacés)." + (_REQ_NOTE if req_changed else "")


def update_from_git(root: Path = ROOT, check_only: bool = False) -> str:
    """Compare la version locale à celle publiée sur GitHub et l'installe si elle est plus récente."""
    import requests
    from terminal import __version__ as local

    try:
        remote = remote_version()
    except requests.RequestException as e:
        raise ValueError(f"GitHub injoignable, vérifie ta connexion ({type(e).__name__})") from e
    if remote is None or _vtuple(remote) <= _vtuple(local):
        return f"Nebula est à jour (v{local})." + (f" Version publiée sur GitHub : v{remote}." if remote else "")
    news = _remote_news(remote)
    head = f"Nouvelle version disponible : v{local} → v{remote}" + (f"\n\n{news}" if news else "")
    if check_only:
        return f"{head}\n\nTape  update  pour l'installer."
    detail = _git_update(root) if (root / ".git").exists() else _zip_update(root)
    return f"{head}\n\n[+] {detail}\nRelance Nebula pour utiliser la v{remote}."


def startup_notice(stamp: Path = ROOT / "saves" / ".update_check") -> str | None:
    """Au démarrage : une vérification par jour au plus, 2 s maximum, silencieuse si hors ligne."""
    import os
    import time

    if os.getenv("NEBULA_NO_UPDATE_CHECK") or (stamp.exists() and time.time() - stamp.stat().st_mtime < 86400):
        return None
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        remote = remote_version(timeout=2)
    except Exception:  # hors ligne, GitHub lent, disque en lecture seule : on n'embête pas l'utilisateur
        return None
    from terminal import __version__ as local
    if remote and _vtuple(remote) > _vtuple(local):
        return f"[*] Nouvelle version v{remote} disponible sur GitHub (tu as la v{local}) : tape  update"
    return None


@REGISTRY.register("update", help_text=(
    "update           - Regarde sur GitHub s'il existe une version plus récente et l'installe\n"
    "update --check   - Regarde seulement, sans rien installer\n"
    "\n"
    "Compare ta version à celle publiée sur GitHub (branche main) et affiche les nouveautés.\n"
    "Projet cloné avec git : git pull. Projet téléchargé en ZIP : l'archive est téléchargée et les\n"
    "fichiers remplacés ; tes profils, missions, .env et venv ne sont jamais touchés.\n"
    "Nebula vérifie aussi au démarrage, une fois par jour (désactivable : NEBULA_NO_UPDATE_CHECK=1)."),
    summary="Mettre Nebula à jour depuis GitHub")
def _update(ctx, argv, raw):
    print(update_from_git(check_only="--check" in argv))


# ---------------------------------------------------------------------
# Tutoriel
# ---------------------------------------------------------------------
def _steps(mission_name):
    return [
        ("Bienvenue", "Nebula regroupe plus de 60 commandes. « help » les liste, « help <mot> » filtre "
                      "(crypto, recon, mission…), et « <commande>.help » donne l'aide détaillée.", ["help crypto"]),
        ("Autocomplétion", "Tape le début d'une commande puis Tab pour la compléter.\n"
                           "Quand une commande déjà tapée commence pareil, Nebula te la propose en gris : "
                           "flèche → pour l'accepter.\n↑ et ↓ parcourent l'historique.", ["encode b64 Bonjour Nebula"]),
        ("Ton espace de travail", "Nebula a son propre système de fichiers, sauvegardé avec ton profil. "
                                  "Les commandes sont celles de Linux : mkdir, cd, ls, cat, rm, mv, cp, tree, find…",
         ["mkdir -p ~/tuto", "cd ~/tuto", "echo Mes premières notes > notes.txt", "ls -l", "cat notes.txt"]),
        ("Garder un résultat", "« > fichier » enregistre la sortie d'une commande (>> ajoute à la fin), "
                               "et grep y cherche un texte.", ["ipcalc 192.168.1.10/24 > reseau.txt", "grep Broadcast reseau.txt"]),
        ("Raccourcis", "Un alias remplace une commande longue. Il est sauvegardé avec ton profil.",
         ["alias ipc ipcalc", "ipc 10.0.0.1/8"]),
        ("Scripts", "« run » exécute un fichier de commandes. $1, $2… sont remplacés par les arguments.",
         ["echo ipcalc $1 > calcul.nbl", "run calcul.nbl 172.16.0.1/12"]),
        ("Mode mission", "Une mission fixe le périmètre autorisé : toute cible en dehors est refusée avant "
                         "le moindre envoi, et tout est enregistré comme preuve. Ici, le périmètre est example.com : "
                         "la 2ᵉ commande sera refusée.", [f"mission new {mission_name} example.com", "scan -f 8.8.8.8",
                                                          "mission report", "mission close"]),
        ("Le dashboard", "« nebulaGui » ouvre le tableau de bord dans ton navigateur : tous les outils avec des "
                         "formulaires, le journal en direct et une console. (s pour passer cette étape)", ["nebulaGui"]),
    ]


@REGISTRY.register("tuto", help_text="tuto    - Visite guidée de Nebula (environ 5 minutes)",
                   summary="Visite guidée de Nebula")
def _tuto(ctx, argv, raw):
    import time

    mission_name = f"tuto-{time.strftime('%H%M%S')}"
    steps = _steps(mission_name)
    print("\n=== Visite guidée de Nebula ===")
    print("Entrée = lancer la commande proposée   s = passer   q = quitter le tuto\n")
    for i, (title, text, commands) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {title}\n{text}\n")
        for command in commands:
            answer = input(f"  → {command}   [Entrée/s/q] ").strip().lower()
            if answer == "q":
                print("Tuto interrompu. Relance-le quand tu veux avec : tuto")
                return
            if answer == "s":
                continue
            REGISTRY.dispatch(ctx, command)
    print("\n=== C'est tout ! ===")
    if input("Supprimer les fichiers du tuto (~/tuto) et l'alias ipc ? [o/N] ").strip().lower() in ("o", "oui", "y"):
        ctx.vfs.cd("~")
        if ctx.vfs.node(ctx.vfs.parts("~/tuto")) is not None:
            ctx.vfs.rm("~/tuto", recursive=True)
        ctx.aliases.pop("ipc", None)
        print("[+] Nettoyé.")
    print("Pour aller plus loin : help, <commande>.help, et le dashboard (nebulaGui).")
