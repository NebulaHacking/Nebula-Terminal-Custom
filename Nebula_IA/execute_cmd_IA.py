"""
execute_cmd_IA — Pont IA → Terminal Nebula.

Exécute une liste de commandes CLI via le REPL du terminal en mode monocmd
(utilise terminal.core.run avec le paramètre ia_line).

Refactoré pour coller à l'architecture terminal/ après le refactor 1.6.
"""


def execute(commands):
    """
    Exécute une liste de commandes Nebula en mode non-interactif.

    Args:
        commands: liste de strings de commandes exécutables dans le terminal
    """
    import os, sys
    from colorama import Fore, Style

    # Construit le contexte et le registre (identique à main.py)
    from terminal.registry import build_registry
    from terminal.context import default_context
    from terminal.core import run

    ctx = default_context()
    reg = build_registry()

    for cmd in commands:
        print(f"{Fore.CYAN}> {cmd}{Style.RESET_ALL}")
        try:
            # ia_line traite UNE commande puis retourne (pas de boucle interactive)
            run(ctx, reg, ia_line=cmd)
        except Exception as e:
            print(f"{Fore.RED}[Erreur exécution] {e}{Style.RESET_ALL}")
