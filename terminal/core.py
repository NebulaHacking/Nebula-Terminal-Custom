"""Noyau du REPL : `main()` construit le contexte + registre, `run()` boucle.

Remplace `terminal_custom()` (ancien main.py 688-1302) et gère le
KeyboardInterrupt qui était capturé par la boucle `while True` externe.
"""
import os

from colorama import init

from terminal.banner import show_nebula
from terminal.context import Context, default_context
from terminal.prompt import get_prompt
from terminal.registry import CommandRegistry, build_registry


def run(ctx: Context, reg: CommandRegistry, ia_line: str | None = None) -> None:
    """Boucle principale. `ia_line` traite UNE commande puis retourne (mode IA)."""
    show_nebula()
    while True:
        try:
            if ia_line is not None:
                reg.dispatch(ctx, ia_line)
                return
            cmd = input(get_prompt(ctx)).strip()
        except KeyboardInterrupt:
            print("\nFermeture de Nebula...")
            break

        if not cmd.strip():
            continue

        reg.dispatch(ctx, cmd)

        if ctx.should_exit:
            break


def main() -> None:
    init(autoreset=True)
    # Dossier de sauvegarde du FS virtuel (parité avec l'ancien main.py, ligne 373).
    os.makedirs("saves", exist_ok=True)
    ctx = default_context()
    reg = build_registry()
    run(ctx, reg)