"""Registre de commandes — remplace la chaîne if/elif de 49 branches.

Un handler = une fonction `(ctx, argv, raw)` décorée `@REGISTRY.register(...)`.
`argv` = ligne découpée (argv[0] = nom de la commande), `raw` = ligne brute.
Le registre gère aussi les alias et la résolution automatique de `<cmd>.help`.

`Keep` riche et coloré : `.help` affiche un encadré, erreurs/inconnues en rouge.
Les retours colorés ont un fallback simple si `rich` manque.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from terminal.context import Context

Handler = Callable[[Context, list[str], str], None]


@dataclass
class Command:
    name: str
    func: Handler
    help_text: str = ""
    summary: str = ""  # description courte pour le tableau `help` (sinon dérivée)
    hidden: bool = False


def _panel_title(name: str) -> str:
    return f"[bold cyan]{name}[/] — Aide"


def _print_cmd_help(cmd: "Command") -> None:
    """Affiche l'aide d'une commande : encadré coloré si rich dispo, sinon brut."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(cmd.help_text, title=_panel_title(cmd.name),
                              border_style="cyan"))
    except ImportError:
        print(cmd.help_text)


class CommandRegistry:
    """Collection de commandes + dispatcher."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self.aliases: dict[str, str] = {}

    def register(
        self,
        name: Optional[str] = None,
        *,
        aliases: tuple[str, ...] = (),
        help_text: str = "",
        summary: str = "",
        hidden: bool = False,
    ) -> Callable[[Handler], Handler]:
        """Decorateur. `name` défaut = nom de la fonction. Les alias pointent vers `name`."""
        def deco(fn: Handler) -> Handler:
            key = name or fn.__name__
            self._commands[key] = Command(key, fn, help_text, summary, hidden)
            for a in aliases:
                self.aliases[a] = key
            return fn
        return deco

    def get(self, raw_name: str) -> Optional[Command]:
        """Résout un alias puis retourne la commande (ou None)."""
        key = self.aliases.get(raw_name, raw_name)
        return self._commands.get(key)

    def commands(self) -> list[Command]:
        """Commandes visibles (non cachées), triées par nom."""
        return [c for c in self._commands.values() if not c.hidden]

    def dispatch(self, ctx: Context, raw: str) -> bool:
        """Traite une ligne de commande. Retourne True si gérée (no-op pour inconnue)."""
        raw = raw.strip()
        if not raw:
            return True
        # Parité avec l'original : la commande brute entre dans l'historique AVANT traitement.
        ctx.history.append(raw)
        argv = raw.split()
        head = argv[0]

        # `foo.help` -> affiche l'aide de la commande `foo`
        if head.endswith(".help"):
            cmd = self.get(head[:-5])
            if cmd is not None:
                _print_cmd_help(cmd)
                return True

        cmd = self.get(head)
        if cmd is None:
            self._warn(f"Commande inconnue : {raw}. Tapez 'help' pour voir les commandes.")
            return True

        try:
            cmd.func(ctx, argv, raw)
        except KeyboardInterrupt:
            print("\nInterrompu (Ctrl-C).")
        except Exception as e:
            # L'ancien code s'appuyait sur un try global ; ici on affiche l'erreur
            # en rouge et on continue la boucle (comportement pro, pas de crash).
            self._warn(f"Erreur : {e}")
        return True

    @staticmethod
    def _warn(message: str) -> None:
        try:
            from rich.console import Console
            Console().print(f"[bold red]{message}[/]")
        except ImportError:
            print(message)


# Registre unique partagé par tous les modules de commandes.
REGISTRY = CommandRegistry()


def build_registry() -> CommandRegistry:
    """Importe les modules de commandes (effet de bord : @register) puis retourne le registre."""
    import terminal.commands  # noqa: F401
    return REGISTRY