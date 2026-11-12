"""Noyau du REPL : `main()` construit le contexte + registre, `run()` boucle.

Remplace `terminal_custom()` (ancien main.py 688-1302) et gère le
KeyboardInterrupt qui était capturé par la boucle `while True` externe.
"""
import sys
import time

from colorama import init

from terminal import events, mission
from terminal.banner import show_nebula
from terminal.context import Context, default_context
from terminal.prompt import get_prompt
from terminal.registry import CommandRegistry, build_registry
from terminal.theme import get_theme_name, set_theme
from terminal.user_manager import (
    get_available_users, user_exists, create_user, get_user_theme, get_user_vfs, get_user_aliases,
    save_user_theme, save_user_history, save_user_vfs, save_user_aliases, get_user_history
)


def select_or_create_user() -> str:
    """Demande à l'utilisateur de sélectionner ou créer un compte."""
    print("\n" + "="*50)
    print("[*] NEBULA TERMINAL CUSTOM - Selection Utilisateur")
    print("="*50)

    users = get_available_users()

    if users:
        print("\n[*] Utilisateurs existants :")
        for i, user in enumerate(users, 1):
            print(f"  {i}. {user}")

        print(f"  {len(users) + 1}. Creer un nouvel utilisateur")
        print(f"  {len(users) + 2}. Quitter")

        while True:
            try:
                choice = input(f"\nChoisissez une option (Entree = {users[0]}) : ").strip()
                choice_num = int(choice) if choice else 1

                if 1 <= choice_num <= len(users):
                    return users[choice_num - 1]
                elif choice_num == len(users) + 1:
                    break
                elif choice_num == len(users) + 2:
                    print("Au revoir !")
                    sys.exit(0)
                else:
                    print("Option invalide.")
            except ValueError:
                print("Option invalide.")
            except (EOFError, KeyboardInterrupt):
                sys.exit(0)
    else:
        print("\n[-] Aucun utilisateur trouve. Creez-en un nouveau.\n")

    # === Création d'un nouvel utilisateur ===
    print("\n[+] Creer un nouvel utilisateur")
    while True:
        try:
            username = input("Nom d'utilisateur : ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

        if not username:
            print("[-] Le nom ne peut pas etre vide.")
            continue

        if user_exists(username):
            print(f"[-] L'utilisateur '{username}' existe deja.")
            continue

        if create_user(username):
            print(f"[+] Utilisateur '{username}' cree avec succes !")
            return username
        else:
            print(f"[-] Erreur lors de la creation de '{username}'.")


def run(ctx: Context, reg: CommandRegistry) -> None:
    """Boucle principale du REPL. Ctrl+C efface la ligne (comme sous Kali) ; exit ou Ctrl+D quitte."""
    from terminal.line_editor import LineReader

    show_nebula()
    reader = LineReader(reg, ctx)
    while not ctx.should_exit:
        try:
            cmd = reader.read(get_prompt(ctx)).strip()
        except KeyboardInterrupt:
            if reader.session is None:  # saisie simple : pas de ligne à effacer, on quitte comme avant
                print("\n\nFermeture de Nebula...")
                break
            continue
        except EOFError:
            print("\n\nFermeture de Nebula...")
            break
        if cmd:
            started = time.time()
            ctx.last_status = reg.dispatch(ctx, cmd)
            ctx.last_duration = time.time() - started


def main() -> None:
    init(autoreset=True)

    username = select_or_create_user()
    print(f"\n[+] Connecte en tant que : {username}\n")

    # Restaure le profil : thème, historique, FS virtuel.
    set_theme(get_user_theme(username))
    ctx = default_context()
    ctx.current_user = username
    ctx.history = get_user_history(username).copy()
    ctx.aliases = dict(get_user_aliases(username))
    saved_vfs, vfs_broken = get_user_vfs(username), False
    if saved_vfs:
        try:
            ctx.vfs.load_tree(saved_vfs)
        except ValueError as e:
            print(f"[!] Espace de travail du profil illisible ({e}) : un espace vide est utilisé, l'ancien n'est pas effacé.")
            vfs_broken = True
    if not ctx.history:
        print("[*] Première fois ? Tape  tuto  pour une visite guidée de 5 minutes.")

    from terminal.commands.shell import startup_notice
    notice = startup_notice()
    if notice:
        print(notice)
    events.enable()  # garde la sortie des commandes : ia ? explique la dernière
    mission.restore()
    if mission.active():
        print(f"[*] Mission ouverte : {mission.active()['name']} (périmètre : {', '.join(mission.active()['scope'])})")

    run(ctx, build_registry())

    print("\n[*] Sauvegarde des donnees utilisateur...")
    save_user_history(username, ctx.history)
    save_user_theme(username, get_theme_name())

    save_user_aliases(username, ctx.aliases)
    # L'espace de travail est sauvegardé automatiquement, sauf s'il n'a pas pu être relu au démarrage
    # (on ne remplace jamais un ancien espace illisible par un espace vide).
    if not vfs_broken:
        save_user_vfs(username, ctx.vfs.root)

    print(f"[+] Donnees sauvegardees pour '{username}'.")
    print("[*] Merci d'avoir utilise Nebula !")
