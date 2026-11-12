"""Modules de commandes — importés pour leur effet de bord (enregistrement).

`terminal/registry.build_registry()` importe ce package pour peupler REGISTRY.
"""
from terminal.commands import builtins  # noqa: F401
from terminal.commands import filesystem  # noqa: F401
from terminal.commands import network  # noqa: F401
from terminal.commands import system  # noqa: F401
from terminal.commands import misc  # noqa: F401
from terminal.commands import external  # noqa: F401
from terminal.commands import crypto  # noqa: F401
from terminal.commands import recon  # noqa: F401
from terminal.commands import mission  # noqa: F401
from terminal.commands import analysis  # noqa: F401
from terminal.commands import shell  # noqa: F401
from terminal.commands import ia  # noqa: F401
