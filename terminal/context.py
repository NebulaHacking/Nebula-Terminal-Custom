"""État global du terminal — un contexte explicite par session, plus de `global`.

Chaque handler reçoit ce Context. Il porte le système de fichiers virtuel,
l'historique des commandes et l'historique du navigateur.
"""
from dataclasses import dataclass, field

from Tools.virtualfs import VirtualFS


@dataclass
class Context:
    """État partagé entre toutes les commandes du terminal."""

    vfs: VirtualFS = field(default_factory=VirtualFS)
    history: list[str] = field(default_factory=list)
    browser_history: list[str] = field(default_factory=list)
    should_exit: bool = False  # posé par la commande `exit` ; le REPL break dessus


def default_context() -> Context:
    return Context()