"""Saisie façon Kali (zsh) : Tab complète, et la commande déjà tapée qui commence pareil
s'affiche en gris — flèche → (ou Fin) pour l'accepter, ↑ ↓ pour l'historique.

Basé sur prompt_toolkit. Sans console interactive (script, tests) ou sans prompt_toolkit,
on retombe sur input() : rien ne casse.
"""
import sys

from terminal.context import Context

# Mots proposés après une commande (1er argument), en plus des chemins.
SUBCOMMANDS = {
    "mission": ["new", "open", "close", "list", "scope", "note", "log", "verify", "diff", "report"],
    "reqforge": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "raw", "list", "show", "replay", "diff", "curl", "python"],
    "tracewave": ["compare"],
    "scan": ["-f", "-a", "-s"],
    "decode": ["auto", "b64", "b32", "hex", "url", "rot13", "bin", "html"],
    "encode": ["b64", "b32", "hex", "url", "rot13", "bin", "html"],
    "hash": ["-f", "-c"],
    "ls": ["-l"], "mkdir": ["-p"], "rm": ["-r"], "cp": ["-r"], "grep": ["-i", "-n"],
    "iptracker": ["-c", "-m"],
}
WORKSPACE_PATHS = {"ls", "cd", "cat", "kcat", "rm", "mv", "cp", "tree", "mkdir", "touch", "grep", "knano", "export", "find", "run"}
DISK_PATHS = {"tracewave", "fileinfo", "strings", "import", "run"}


def _completer(registry, ctx: Context):
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.document import Document

    disk = PathCompleter(expanduser=True)

    class NebulaCompleter(Completer):
        def get_completions(self, document, event):
            text = document.text_before_cursor.lstrip()
            if " " not in text:  # 1er mot : commandes, alias Nebula, alias perso
                names = {c.name: c.summary or "" for c in registry.commands()}
                names.update({a: f"= {t}" for a, t in registry.aliases.items()})
                names.update({a: f"alias : {v}" for a, v in ctx.aliases.items()})
                for name in sorted(names, key=str.lower):
                    if name.lower().startswith(text.lower()):
                        yield Completion(name, -len(text), display_meta=names[name][:70])
                return
            words = text.split(" ")
            cmd, current = registry.aliases.get(words[0], words[0]), words[-1]
            position = len([w for w in words[1:-1] if w])  # index de l'argument en cours
            options = []
            if position == 0:
                options = list(SUBCOMMANDS.get(cmd, []))
                if cmd == "help":
                    from terminal.commands.builtins import _HELP_CATEGORIES, _plain
                    options = [_plain(label) for _, label, _ in _HELP_CATEGORIES]
                elif cmd == "theme":
                    from terminal.theme import get_available_themes
                    options = get_available_themes()
                elif cmd == "load":
                    options = [f[:-4] for f in ctx.vfs.list_saves()]
                elif cmd in ("unalias",):
                    options = sorted(ctx.aliases)
            elif cmd == "mission" and position == 1 and words[1] == "open":
                from terminal import mission
                options = mission.names()
            for option in options:
                if option.lower().startswith(current.lower()):
                    yield Completion(option, -len(current))
            if cmd in DISK_PATHS and not (cmd == "run" and position > 0):
                yield from disk.get_completions(Document(current), event)
            if cmd in WORKSPACE_PATHS and not (cmd == "export" and position > 0):
                for entry in ctx.vfs.entries(current):
                    yield Completion(entry, -len(current), display_meta="espace de travail")

    return NebulaCompleter()


def _history(ctx: Context):
    """Historique lu directement dans le profil (ctx.history) : un secret masqué après coup
    (pwstrength) n'est donc jamais proposé en suggestion."""
    from prompt_toolkit.history import History

    class ContextHistory(History):
        def load_history_strings(self):
            seen = set()
            for line in reversed(ctx.history[-3000:]):
                if line not in seen:
                    seen.add(line)
                    yield line

        async def load(self):
            for line in self.load_history_strings():
                yield line

        def get_strings(self):
            return list(self.load_history_strings())[::-1]

        def append_string(self, string):
            pass  # dispatch l'ajoute déjà à ctx.history

        def store_string(self, string):
            pass

    return ContextHistory()


def make_session(registry, ctx: Context, input=None, output=None):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style

    return PromptSession(history=_history(ctx), auto_suggest=AutoSuggestFromHistory(),
                         completer=_completer(registry, ctx), complete_while_typing=False,
                         style=Style.from_dict({"auto-suggestion": "#6c6c6c"}),
                         input=input, output=output)


class LineReader:
    """`read(prompt)` → la ligne tapée. KeyboardInterrupt = Ctrl+C, EOFError = Ctrl+D / fin d'entrée."""

    def __init__(self, registry, ctx: Context):
        self.session = None
        if sys.stdin.isatty() and sys.__stdout__.isatty():
            try:
                self.session = make_session(registry, ctx)
            except Exception:  # console non prise en charge : saisie simple
                self.session = None

    def read(self, prompt: str) -> str:
        if self.session is None:
            return input(prompt)
        from prompt_toolkit.formatted_text import ANSI
        return self.session.prompt(ANSI(prompt))
