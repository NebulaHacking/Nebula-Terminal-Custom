"""knano — mini-éditeur de texte pour le FS virtuel de Nebula.

Portage des lignes 202-369 de l'ancien main.py. Opère sur une instance
VirtualFS reçue en paramètre (plus de `get_current_dir()` global).
"""
from Tools.virtualfs import VirtualFS


def knano_editor(vfs: VirtualFS, filename_arg: str | None = None) -> None:
    """
    Usage:
    knano <filename>    -> ouvre/crée filename dans le répertoire courant (virtual FS)
    knano               -> demande un nom de fichier
    Édition:
    Tape du texte : chaque ligne est ajoutée.
    Les commandes commencent par ':' (ex: :w, :q, :wq, :p, :i 3, :d 2, :h)
    """
    # determine filename
    if filename_arg:
        filename = filename_arg.strip()
    else:
        filename = input("Nom du fichier (relative to current dir): ").strip()
        if not filename:
            print("Annulé.")
            return

    # référence au dossier courant dans le FS virtuel
    dir_ref = vfs.get_current_dir()

    # charge contenu existant si présent
    if filename in dir_ref and isinstance(dir_ref[filename], str):
        lines = dir_ref[filename].splitlines()
    else:
        lines = []

    modified = False

    def show_help():
        print("""knano - commandes :
: w        -> sauvegarder dans le FS virtuel
: q        -> quitter (refuse si modifs non sauvegardées)
: wq       -> sauvegarder puis quitter
: p        -> afficher le fichier avec numéros de lignes
: i N      -> insérer avant la ligne N (N est un entier, 1-based). Si N>len+1, ajoute à la fin.
: d N      -> supprimer la ligne N
: h        -> afficher cette aide
: r        -> renommer le fichier (demande nouveau nom)
: esc      -> taper exactement ":q" pour quitter (pas d'autre raccourci)
""")

    print(f"--- knano: édition de '{filename}' (tape ':h' pour aide) ---")
    # print current content initially (compact)
    if lines:
        print("[Contenu initial]")
        for i, l in enumerate(lines, 1):
            print(f"{i:3}: {l}")
    else:
        print("[Nouveau fichier vide]")

    while True:
        try:
            raw = input()  # lecture ligne par ligne
        except KeyboardInterrupt:
            print("\nInterrompu (Ctrl-C). Tape ':q' pour quitter ou ':wq' pour sauvegarder et quitter.")
            continue

        if raw.startswith(":"):  # commande spéciale
            parts = raw[1:].strip().split(" ", 1)
            cmd = parts[0].lower()

            if cmd == "w":  # sauvegarder
                try:
                    dir_ref[filename] = "\n".join(lines)
                    modified = False
                    print(f" -> '{filename}' sauvegardé.")
                except Exception as e:
                    print("Erreur sauvegarde :", e)

            elif cmd == "q":
                if modified:
                    confirm = input("Modifications non sauvegardées, quitter quand même ? (y/N): ").strip().lower()
                    if confirm == "y":
                        print("Quitte sans sauvegarder.")
                        return
                    else:
                        print("Annulé.")
                        continue
                else:
                    print("Quitte knano.")
                    return

            elif cmd == "wq":
                try:
                    dir_ref[filename] = "\n".join(lines)
                    print(f" -> '{filename}' sauvegardé. Quitte knano.")
                    return
                except Exception as e:
                    print("Erreur sauvegarde :", e)

            elif cmd == "p":  # print with numbers
                print("--- Contenu ---")
                if lines:
                    for i, l in enumerate(lines, 1):
                        print(f"{i:3}: {l}")
                else:
                    print("[fichier vide]")
                print("---------------")

            elif cmd == "i":  # insert before N
                if len(parts) < 2:
                    print("Usage : :i N   (insérer avant la ligne N)")
                    continue
                try:
                    n = int(parts[1].strip())
                    if n < 1:
                        n = 1
                    # ask for the line(s) to insert; allow multiple lines ended by a single '.' on a line
                    print("Entrez les lignes à insérer (une par ligne). Tapez une ligne contenant uniquement '.' pour finir.")
                    ins_lines = []
                    while True:
                        l = input()
                        if l == ".":
                            break
                        ins_lines.append(l)
                    idx = min(n-1, len(lines))
                    for offset, il in enumerate(ins_lines):
                        lines.insert(idx + offset, il)
                    modified = True
                    print(f"{len(ins_lines)} ligne(s) insérée(s) avant la ligne {n}.")
                except ValueError:
                    print("N doit être un entier.")

            elif cmd == "d":  # delete line N
                if len(parts) < 2:
                    print("Usage : :d N   (supprimer la ligne N)")
                    continue
                try:
                    n = int(parts[1].strip())
                    if 1 <= n <= len(lines):
                        removed = lines.pop(n-1)
                        modified = True
                        print(f"Ligne {n} supprimée : {removed}")
                    else:
                        print("Numéro de ligne invalide.")
                except ValueError:
                    print("N doit être un entier.")

            elif cmd == "r":  # rename
                new_name = input("Nouveau nom de fichier : ").strip()
                if not new_name:
                    print("Nom invalide.")
                    continue
                # move within current dir_ref
                if new_name in dir_ref:
                    print("Un fichier ou dossier existe déjà avec ce nom.")
                    continue
                # write current content to new key and delete old one if existed
                dir_ref[new_name] = "\n".join(lines)
                if filename in dir_ref:
                    try:
                        del dir_ref[filename]
                    except Exception:
                        pass
                filename = new_name
                print(f"Fichier renommé en '{filename}'. (En mémoire, n'oublie pas :w pour sauvegarder definitivement)")

            elif cmd == "h":
                show_help()

            else:
                print("Commande inconnue. Tape ':h' pour l'aide.")

        else:
            # insertion d'une ligne normale à la fin
            lines.append(raw)
            modified = True