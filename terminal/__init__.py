"""Nebula Terminal Custom — couche CLI (Phase 2).

Package terminal : REPL, registre de commandes, état (Context), prompt et
bannière. Les moteurs métier vivent dans Tools/.
"""
__version__ = "2.0.0"

from terminal.core import main

__all__ = ["main"]