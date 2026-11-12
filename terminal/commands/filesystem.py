"""Commandes de l'espace de travail (système de fichiers virtuel).

ls, cd, pwd, mkdir, touch, cat, echo, grep, rm, mv, cp, tree, find, df,
import / export (pont avec le disque), save / load (instantanés), knano (éditeur).
Moteur dans Tools/virtualfs.py. Tout est sauvegardé avec ton profil à la fermeture.
"""
import re

from terminal.registry import REGISTRY
from Tools.virtualfs import MAX_TOTAL, SAVES_DIR


def _split(argv, flags):
    """(options présentes, arguments) — les options d'une lettre peuvent être groupées (-rf)."""
    found, rest = set(), []
    for a in argv[1:]:
        if a.startswith("-") and len(a) > 1 and set(a[1:]) <= set(flags):
            found |= set(a[1:])
        else:
            rest.append(a)
    return found, rest


def _need(rest, n, usage):
    if len(rest) < n:
        raise ValueError(f"Usage : {usage}")


def _size(n):
    return f"{n} o" if n < 1024 else f"{n / 1024:.1f} Ko" if n < 1048576 else f"{n / 1048576:.1f} Mo"


# ---------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------
@REGISTRY.register("ls", help_text=(
    "ls [chemin]      - Contenu d'un dossier (défaut : dossier actuel)\n"
    "ls -l [chemin]   - Avec le type et la taille"), summary="Lister un dossier (-l : détails)")
def _ls(ctx, argv, raw):
    flags, rest = _split(argv, "la")
    items = ctx.vfs.ls(rest[0] if rest else "")
    if not items:
        print("Dossier vide.")
        return
    try:
        from rich.console import Console
        con = Console(highlight=False)
        show = lambda name, is_dir: con.print(f"[bold blue]{name}/[/]" if is_dir else name, markup=is_dir)  # noqa: E731
    except ImportError:
        show = lambda name, is_dir: print(name + ("/" if is_dir else ""))  # noqa: E731
    for name, is_dir, size in items:
        if "l" in flags:
            print(f"{'d' if is_dir else '-'}  {_size(size):>9}  ", end="")
        show(name, is_dir)


@REGISTRY.register("cd", help_text="cd [chemin]      - Changer de dossier (cd seul ou cd ~ : dossier personnel, cd .. : remonter)",
                   summary="Changer de dossier")
def _cd(ctx, argv, raw):
    ctx.vfs.cd(argv[1] if len(argv) > 1 else "~")


@REGISTRY.register("pwd", help_text="pwd              - Afficher le dossier actuel", summary="Afficher le dossier actuel")
def _pwd(ctx, argv, raw):
    print(ctx.vfs.get_path())


@REGISTRY.register("tree", help_text="tree [chemin]    - Arborescence d'un dossier", summary="Arborescence d'un dossier")
def _tree(ctx, argv, raw):
    print("\n".join(ctx.vfs.tree(argv[1] if len(argv) > 1 else "")))


@REGISTRY.register("find", help_text="find <motif> [chemin]  - Chercher des fichiers par nom (ex : find *.txt, find scan)",
                   summary="Chercher des fichiers par nom")
def _find(ctx, argv, raw):
    _need(argv[1:], 1, "find <motif> [chemin]")
    found = ctx.vfs.find(argv[1], argv[2] if len(argv) > 2 else "/")
    print("\n".join(found) if found else "Aucun résultat.")


@REGISTRY.register("df", help_text="df               - Place utilisée dans l'espace de travail", summary="Place utilisée")
def _df(ctx, argv, raw):
    used = ctx.vfs.usage()
    print(f"Espace de travail : {_size(used)} / {_size(MAX_TOTAL)} ({used * 100 / MAX_TOTAL:.1f} %)")


# ---------------------------------------------------------------------
# Création / lecture
# ---------------------------------------------------------------------
@REGISTRY.register("mkdir", help_text="mkdir [-p] <dossier...>  - Créer des dossiers (-p : créer aussi les parents)",
                   summary="Créer un dossier")
def _mkdir(ctx, argv, raw):
    flags, rest = _split(argv, "p")
    _need(rest, 1, "mkdir [-p] <dossier...>")
    for path in rest:
        ctx.vfs.mkdir(path, parents="p" in flags)


@REGISTRY.register("touch", help_text="touch <fichier...>  - Créer des fichiers vides", summary="Créer un fichier vide")
def _touch(ctx, argv, raw):
    _need(argv[1:], 1, "touch <fichier...>")
    for path in argv[1:]:
        ctx.vfs.touch(path)


@REGISTRY.register("cat", aliases=("kcat",), help_text="cat <fichier...>  - Afficher le contenu de fichiers (alias : kcat)",
                   summary="Afficher un fichier")
def _cat(ctx, argv, raw):
    _need(argv[1:], 1, "cat <fichier...>")
    for path in argv[1:]:
        text = ctx.vfs.read(path)
        print(text, end="" if text.endswith("\n") else "\n")


@REGISTRY.register("echo", help_text=(
    "echo <texte>            - Afficher un texte\n"
    "echo <texte> > fichier  - L'écrire dans un fichier (>> pour ajouter à la fin)"),
    summary="Afficher un texte (ou l'écrire avec >)")
def _echo(ctx, argv, raw):
    print(raw.split(None, 1)[1] if len(argv) > 1 else "")


@REGISTRY.register("grep", help_text=(
    "grep [-i] [-n] <motif> <fichier...>  - Lignes qui contiennent le motif (expression régulière)\n"
    "Exemple : scan -f 192.168.1.1 > scan.txt   puis   grep ouvert scan.txt"),
    summary="Chercher un texte dans des fichiers")
def _grep(ctx, argv, raw):
    flags, rest = _split(argv, "in")
    _need(rest, 2, "grep [-i] [-n] <motif> <fichier...>")
    try:
        pattern = re.compile(rest[0], re.I if "i" in flags else 0)
    except re.error:
        pattern = re.compile(re.escape(rest[0]), re.I if "i" in flags else 0)
    files = rest[1:]
    for path in files:
        for i, line in enumerate(ctx.vfs.read(path).splitlines(), 1):
            if pattern.search(line):
                print(("" if len(files) == 1 else f"{path}:") + (f"{i}:" if "n" in flags else "") + line)


# ---------------------------------------------------------------------
# Suppression / déplacement
# ---------------------------------------------------------------------
@REGISTRY.register("rm", help_text=(
    "rm <chemin...>     - Supprimer des fichiers ou dossiers vides de l'espace de travail\n"
    "rm -r <dossier>    - Supprimer un dossier et tout son contenu\n"
    "(Pour lancer une commande système Windows/Linux, c'est désormais : exec <commande>)"),
    summary="Supprimer (espace de travail)")
def _rm(ctx, argv, raw):
    flags, rest = _split(argv, "rf")
    _need(rest, 1, "rm [-r] <chemin...>")
    for path in rest:
        ctx.vfs.rm(path, recursive="r" in flags)


@REGISTRY.register("mv", help_text="mv <source> <destination>  - Déplacer ou renommer", summary="Déplacer ou renommer")
def _mv(ctx, argv, raw):
    _need(argv[1:], 2, "mv <source> <destination>")
    ctx.vfs.mv(argv[1], argv[2])


@REGISTRY.register("cp", help_text="cp [-r] <source> <destination>  - Copier (-r pour un dossier)", summary="Copier")
def _cp(ctx, argv, raw):
    flags, rest = _split(argv, "r")
    _need(rest, 2, "cp [-r] <source> <destination>")
    ctx.vfs.cp(rest[0], rest[1], recursive="r" in flags)


# ---------------------------------------------------------------------
# Pont avec le disque
# ---------------------------------------------------------------------
def _disk_args(raw):
    """Arguments qui peuvent être des chemins Windows avec espaces (entre guillemets)."""
    import shlex
    out = []
    for token in shlex.split(raw, posix=False)[1:]:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
            token = token[1:-1]
        out.append(token)
    return out


@REGISTRY.register("import", help_text=(
    "import <fichier du disque> [chemin]  - Copier un fichier texte du disque dans l'espace de travail\n"
    'Exemple : import "C:\\wordlists\\mots.txt" listes/'), summary="Copier un fichier du disque vers l'espace de travail")
def _import(ctx, argv, raw):
    args = _disk_args(raw)
    _need(args, 1, "import <fichier du disque> [chemin]")
    print(f"[+] Importé dans {ctx.vfs.import_file(args[0], args[1] if len(args) > 1 else '')}")


@REGISTRY.register("export", help_text=(
    "export <fichier> <destination sur le disque> [-f]  - Copier un fichier de l'espace de travail sur le disque\n"
    "-f : écraser si le fichier existe déjà.  Exemple : export scan.txt C:\\Users\\moi\\Desktop"),
    summary="Copier un fichier vers le disque")
def _export(ctx, argv, raw):
    args = _disk_args(raw)
    force = "-f" in args
    args = [a for a in args if a != "-f"]
    _need(args, 2, "export <fichier> <destination> [-f]")
    print(f"[+] Exporté vers {ctx.vfs.export_file(args[0], args[1], overwrite=force)}")


# ---------------------------------------------------------------------
# Instantanés
# ---------------------------------------------------------------------
@REGISTRY.register("save", help_text=(
    "save <nom>   - Enregistrer un instantané de tout l'espace de travail (dossier saves/)\n"
    "L'espace de travail est déjà sauvegardé avec ton profil : save sert à garder des versions."),
    summary="Instantané de l'espace de travail")
def _save(ctx, argv, raw):
    name = argv[1] if len(argv) > 1 else input("Nom de l'instantané : ").strip() or "instantane"
    print(f"[+] Instantané enregistré : {ctx.vfs.save_to(name, SAVES_DIR)}")


@REGISTRY.register("load", help_text=(
    "load          - Liste les instantanés\n"
    "load <nom|n>  - Remplace l'espace de travail par un instantané"),
    summary="Recharger un instantané")
def _load(ctx, argv, raw):
    files = ctx.vfs.list_saves(SAVES_DIR)
    if len(argv) < 2:
        print("\n".join(f"  {i}. {f[:-4]}" for i, f in enumerate(files, 1)) or "Aucun instantané (save <nom> pour en créer un).")
        return
    choice = argv[1]
    index = int(choice) - 1 if choice.isdigit() else next((i for i, f in enumerate(files) if f[:-4] == choice), -1)
    path = ctx.vfs.load_from(index, SAVES_DIR)
    if path is None:
        raise ValueError(f"Instantané introuvable : {choice} (load pour la liste)")
    print(f"[+] Espace de travail rechargé depuis {path}")


# ---------------------------------------------------------------------
# Éditeur
# ---------------------------------------------------------------------
@REGISTRY.register(
    "knano",
    summary="Mini éditeur de texte pour l'espace de travail",
    help_text="""knano [fichier] - Mini éditeur pour l'espace de travail

Commandes :
   :w       - Sauvegarder
   :q       - Quitter (refuse si non sauvegardé)
   :wq      - Sauvegarder puis quitter
   :p       - Afficher contenu avec numéros de lignes
   :i N     - Insérer avant la ligne N
   :d N     - Supprimer la ligne N
   :h       - Afficher cette aide
   :r       - Renommer le fichier
""",
)
def _knano(ctx, argv, raw):
    from Tools.knano import knano_editor
    filename = argv[1] if len(argv) > 1 else None
    knano_editor(ctx.vfs, filename)
