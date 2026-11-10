"""
execute_cmd_IA — Pont IA → Terminal Nebula.

Exécute une liste de commandes via le registre du terminal, sans boucle
interactive ni bannière. Pas encore branché sur le chat IA : à relier quand
l'IA proposera des commandes (prévoir une confirmation : `rm`/`exec` lance
de vraies commandes système).
"""
from colorama import Fore, Style


def execute(commands, ctx=None):
    """Exécute chaque commande Nebula de `commands` dans `ctx` (nouveau contexte si None)."""
    from terminal.context import default_context
    from terminal.registry import build_registry

    ctx = ctx or default_context()
    reg = build_registry()
    for cmd in commands:
        print(f"{Fore.CYAN}> {cmd}{Style.RESET_ALL}")
        reg.dispatch(ctx, cmd)  # dispatch capture déjà les erreurs des commandes
    return ctx
