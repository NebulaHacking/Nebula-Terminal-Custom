"""Registre de commandes — remplace la chaîne if/elif de 49 branches.

Un handler = une fonction `(ctx, argv, raw)` décorée `@REGISTRY.register(...)`.
`argv` = ligne découpée (argv[0] = nom de la commande), `raw` = ligne brute.
Le registre gère aussi les alias et la résolution automatique de `<cmd>.help`.

`Keep` riche et coloré : `.help` affiche un encadré, erreurs/inconnues en rouge.
Les retours colorés ont un fallback simple si `rich` manque.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import contextlib
import io

from terminal import events, mission
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

    def dispatch(self, ctx: Context, raw: str) -> str:
        """Traite une ligne de commande. Renvoie le statut : ok, erreur, refusé, interrompu.

        Avant d'exécuter : alias de l'utilisateur, redirection `> fichier` / `>> fichier`
        (vers l'espace de travail) et option `--json`.
        """
        raw = raw.strip()
        if not raw:
            return "ok"
        # Parité avec l'original : la commande brute entre dans l'historique AVANT traitement.
        ctx.history.append(raw)
        try:
            line, target, append = split_redirect(raw)
            line, as_json = _strip_flag(line, "--json")
        except ValueError as e:
            self._warn(str(e))
            return "erreur"
        line = expand_alias(ctx, line)
        argv = line.split()
        if not argv:
            self._warn("Commande vide avant la redirection")
            return "erreur"
        head = argv[0]
        if target is None and not as_json:
            return self._run(ctx, line, argv, head)

        from terminal import blocks
        out = io.StringIO()
        blocks.local.json, blocks.local.json_used = as_json, False
        try:
            if target is not None:
                with contextlib.redirect_stdout(out):
                    # shortcut: redirect_stdout est global ; une commande lancée en même temps depuis le
                    # dashboard écrirait aussi dans ce fichier. À revoir si ça arrive en pratique.
                    status = self._run(ctx, line, argv, head, redirected=True)
            else:
                status = self._run(ctx, line, argv, head)
        finally:
            used = blocks.local.json_used
            blocks.local.json = False
        if as_json and not used:
            self._warn(f"--json n'est pas disponible pour « {head} » (sortie normale affichée)")
        if target is not None:
            text = events.strip_ansi(out.getvalue())
            try:
                path = ctx.vfs.write_file(target, text, append=append)
                print(f"[+] {len(text.splitlines())} lignes {'ajoutées à' if append else 'écrites dans'} {path}")
            except ValueError as e:
                self._warn(f"Redirection impossible : {e}")
                return "erreur"
        return status

    def _run(self, ctx: Context, raw: str, argv: list[str], head: str, redirected: bool = False) -> str:

        # `foo.help` -> affiche l'aide de la commande `foo`
        if head.endswith(".help"):
            cmd = self.get(head[:-5])
            if cmd is not None:
                _print_cmd_help(cmd)
                return "ok"

        started, status = events.begin(), "ok"
        try:
            cmd = self.get(head)
            if cmd is None:
                status = "erreur"
                hint = _closest(head, [c.name for c in self._commands.values()] + list(self.aliases))
                self._warn(f"Commande inconnue : {head}." + (f" Vouliez-vous dire « {hint} » ?" if hint else "")
                           + " Tapez 'help' pour voir les commandes.")
                return status
            refusal = mission.guard(cmd.name, argv)
            if refusal:  # mission ouverte et cible hors périmètre : rien n'est lancé
                status = "refusé"
                self._warn(refusal)
                return status
            cmd.func(ctx, argv, raw)
        except KeyboardInterrupt:
            status = "interrompu"
            print("\nInterrompu (Ctrl-C).")
        except PermissionError as e:  # refus du mode mission levé par un outil (ex. reqforge)
            status = "refusé"
            self._warn(str(e))
        except ModuleNotFoundError as e:
            status = "erreur"
            module = (e.name or "").split(".")[0]
            package = _PIP_NAMES.get(module, module)
            self._warn(f"Il manque le module « {module} » pour cette commande. Installez-le avec :\n"
                       f"   venv\\Scripts\\python -m pip install {package}\n"
                       f"(ou tous les outils optionnels d'un coup : python launch.py --full)")
        except SystemExit:
            pass  # un outil qui fait sys.exit() ne doit pas tuer le terminal (ni sauter la sauvegarde du profil)
        except Exception as e:
            # L'ancien code s'appuyait sur un try global ; ici on affiche l'erreur
            # en rouge et on continue la boucle (comportement pro, pas de crash).
            status = "erreur"
            self._warn(f"Erreur : {e}")
        finally:
            # ctx.history[-1] et pas `raw` : une commande peut avoir masqué un secret (pwstrength).
            events.finish(started, ctx.history[-1] if ctx.history else raw, status, propagate=not redirected)
        return status

    def run_quiet(self, ctx: Context, command: str, source: str) -> tuple[str, str, float]:
        """Lance une commande sans rien écrire dans le terminal ; renvoie (sortie, statut, durée).

        `source` marque l'événement et la ligne du registre de mission (« ia », « retest »).
        input() est refusé (personne ne peut répondre) et la commande ne va pas dans l'historique.
        """
        import time

        events.enable()
        local = events.local
        saved = getattr(local, "quiet", False), getattr(local, "source", None)
        local.quiet, local.source = True, source
        started = events.begin()
        try:
            status = self.dispatch(ctx, command)
        finally:
            output = events.strip_ansi("".join(local.buf or []))
            local.buf = local.stack.pop()
            local.quiet, local.source = saved
            if ctx.history and ctx.history[-1] == command:
                ctx.history.pop()  # l'historique (et l'autocomplétion) reste celui de l'utilisateur
        return output, status, round(time.time() - started, 1)

    @staticmethod
    def _warn(message: str) -> None:
        try:
            from rich.console import Console
            Console().print(message, style="bold red", markup=False)  # le texte peut contenir des [ ]
        except ImportError:
            print(message)


# Nom du paquet pip quand il diffère du module importé.
_PIP_NAMES = {"sklearn": "scikit-learn", "whois": "python-whois", "bs4": "beautifulsoup4", "PyQt5": "PyQt5 PyQtWebEngine",
              "yaml": "pyyaml", "dotenv": "python-dotenv", "socks": "pysocks", "prompt_toolkit": "prompt_toolkit"}


def _closest(word: str, names: list[str]) -> str | None:
    import difflib
    match = difflib.get_close_matches(word, names, n=1, cutoff=0.75)
    return match[0] if match else None


def _scan_quotes(text: str):
    """Positions des caractères hors guillemets."""
    quote = None
    for i, c in enumerate(text):
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        else:
            yield i, c


def split_redirect(raw: str) -> tuple[str, str | None, bool]:
    """`cmd args > fichier` → (cmd args, fichier, False) ; `>>` → ajout. Un > entre guillemets est ignoré."""
    positions = [i for i, c in _scan_quotes(raw) if c == ">"]
    if not positions:
        return raw, None, False
    first = positions[0]
    append = raw[first + 1:first + 2] == ">"
    if len(positions) > (2 if append else 1):
        raise ValueError("Une seule redirection par commande (mettez entre guillemets un > qui fait partie du texte)")
    target = raw[first + (2 if append else 1):].strip().strip("\"'")
    if not target:
        raise ValueError("Redirection sans fichier : commande > fichier.txt")
    return raw[:first].rstrip(), target, append


def _strip_flag(line: str, flag: str) -> tuple[str, bool]:
    words = line.split(" ")
    if flag in words:
        return " ".join(w for w in words if w != flag).strip(), True
    return line, False


def expand_alias(ctx: Context, line: str) -> str:
    """Remplace le 1er mot s'il s'agit d'un alias de l'utilisateur (une seule fois : pas de boucle)."""
    head, _, rest = line.partition(" ")
    expansion = getattr(ctx, "aliases", {}).get(head)
    return f"{expansion} {rest}".strip() if expansion else line


# Registre unique partagé par tous les modules de commandes.
REGISTRY = CommandRegistry()


def build_registry() -> CommandRegistry:
    """Importe les modules de commandes (effet de bord : @register) puis retourne le registre."""
    import terminal.commands  # noqa: F401
    return REGISTRY