"""Commandes du système de fichiers virtuel (M2) — ls, mkdir, cd, kcat, save, load, knano.

Portage des branches de l'ancien main.py : ls (999), mkdir (1004), cd (1009/1014),
kcat (940), save (852), load (856), knano (933).
"""
import os

from terminal.registry import REGISTRY

SAVES_DIR = "saves"


# ---------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------
@REGISTRY.register("ls", help_text="ls               - Lister le contenu du dossier actuel")
def _ls(ctx, argv, raw):
    items = ctx.vfs.ls()
    if not items:
        print("Dossier vide.")
        return
    ref = ctx.vfs.get_current_dir()
    try:
        from rich.console import Console
        console = Console()
        for item in items:
            if isinstance(ref.get(item), dict):  # dossier -> bleu gras
                console.print(f"[bold blue]{item}[/]")
            else:  # fichier -> blanc
                console.print(item)
        return
    except ImportError:
        for item in items:
            print(item)


@REGISTRY.register("mkdir", help_text="mkdir <nom>      - Créer un dossier")
def _mkdir(ctx, argv, raw):
    if len(argv) < 2:
        print("Commande inconnue : mkdir. Tapez 'help' pour voir les commandes.")
        return
    ctx.vfs.mkdir(argv[1])


@REGISTRY.register("cd", help_text="cd <nom> | ..    - Changer de dossier virtuel")
def _cd(ctx, argv, raw):
    if len(argv) < 2:
        print("Commande inconnue : cd. Tapez 'help' pour voir les commandes.")
        return
    ctx.vfs.cd(argv[1])


@REGISTRY.register("kcat", help_text="kcat <fichier>   - Afficher le contenu d'un fichier du FS virtuel")
def _kcat(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage: kcat <fichier>")
        return
    content = ctx.vfs.read_file(argv[1])
    if content is not None:
        print(content)
    else:
        print(f"Erreur : le fichier '{argv[1]}' n'existe pas.")


# ---------------------------------------------------------------------
# Persistance
# ---------------------------------------------------------------------
@REGISTRY.register("save", help_text="save             - Sauvegarder le système de fichiers virtuel")
def _save(ctx, argv, raw):
    filename = input("Nom du fichier pour sauvegarde (sans extension): ").strip()
    if not filename:
        filename = "filesystem_save"
    try:
        filepath = ctx.vfs.save_to(filename, SAVES_DIR)
        print(f"FS sauvegardé dans '{filepath}' !")
    except Exception as e:
        print("Erreur lors de la sauvegarde :", e)


@REGISTRY.register("load", help_text="load             - Charger un système de fichiers sauvegardé")
def _load(ctx, argv, raw):
    files = ctx.vfs.list_saves(SAVES_DIR)
    if not files:
        print("Aucun fichier disponible dans 'saves'.")
        return

    print("Fichiers disponibles :")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f}")

    choix = input("Numéro du fichier à charger : ").strip()
    try:
        index = int(choix) - 1
        filepath = ctx.vfs.load_from(index, SAVES_DIR)
        if filepath is not None:
            print(f"FS rechargé depuis '{filepath}' !")
        else:
            print("Choix invalide.")
    except ValueError:
        print("Veuillez entrer un numéro valide.")
    except Exception as e:
        print("Erreur lors du chargement :", e)


# ---------------------------------------------------------------------
# Éditeur
# ---------------------------------------------------------------------
@REGISTRY.register(
    "knano",
    summary="Mini éditeur de texte pour le FS virtuel",
    help_text="""knano - Mini éditeur pour FS virtuel

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