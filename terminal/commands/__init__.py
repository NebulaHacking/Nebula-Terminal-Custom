"""Modules de commandes — importés pour leur effet de bord (enregistrement).

`terminal/registry.build_registry()` importe ce package pour peupler REGISTRY.
"""
from terminal.commands import builtins  # noqa: F401
from terminal.commands import filesystem  # noqa: F401
from terminal.commands import network  # noqa: F401
from terminal.commands import system  # noqa: F401
from terminal.commands import misc  # noqa: F401
from terminal.commands import external  # noqa: F401