

def execute(commands):

    import os, sys

    # Ajouter le dossier parent au chemin d'import
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Importer la fonction
    from main import nebula_terminal
    for cmd in commands:
        print(f"{cmd}")
        try:
            nebula_terminal(cmd=cmd, is_ia=True)  # appel direct
        except Exception as e:
            print(f"[Erreur exécution] {e}")