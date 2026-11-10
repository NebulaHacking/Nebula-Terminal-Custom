"""Noyau du REPL : `main()` construit le contexte + registre, `run()` boucle.

Remplace `terminal_custom()` (ancien main.py 688-1302) et gère le
KeyboardInterrupt qui était capturé par la boucle `while True` externe.
"""
import copy
import sys

from colorama import init

from terminal.banner import show_nebula
from terminal.context import Context, default_context
from terminal.prompt import get_prompt
from terminal.registry import CommandRegistry, build_registry
from terminal.theme import get_theme_name, set_theme
from terminal.user_manager import (
    get_available_users, user_exists, create_user, get_user_theme, get_user_vfs,
    save_user_theme, save_user_history, save_user_vfs, get_user_history
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
    """Boucle principale du REPL."""
    show_nebula()
    while not ctx.should_exit:
        try:
            cmd = input(get_prompt(ctx)).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nFermeture de Nebula...")
            break
        if cmd:
            reg.dispatch(ctx, cmd)


def main() -> None:
    init(autoreset=True)

    username = select_or_create_user()
    print(f"\n[+] Connecte en tant que : {username}\n")

    # Restaure le profil : thème, historique, FS virtuel.
    set_theme(get_user_theme(username))
    ctx = default_context()
    ctx.current_user = username
    ctx.history = get_user_history(username).copy()
    saved_vfs = get_user_vfs(username)
    if saved_vfs:
        ctx.vfs.root = saved_vfs
    vfs_before = copy.deepcopy(ctx.vfs.root)

    run(ctx, build_registry())

    print("\n[*] Sauvegarde des donnees utilisateur...")
    save_user_history(username, ctx.history)
    save_user_theme(username, get_theme_name())

    if ctx.vfs.root != vfs_before:
        try:
            response = input("Sauvegarder le systeme de fichiers virtuel ? (o/n) : ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "n"
        if response in ("o", "oui", "y", "yes"):
            save_user_vfs(username, ctx.vfs.root)
            print("[+] VFS sauvegarde.")
        else:
            print("[-] VFS non sauvegarde.")

    print(f"[+] Donnees sauvegardees pour '{username}'.")
    print("[*] Merci d'avoir utilise Nebula !")
