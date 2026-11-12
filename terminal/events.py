"""Journal d'activité en direct — alimente le dashboard web (NebulaGui/server.py).

Chaque commande passée par `dispatch` devient un événement (commande, sortie, durée, statut).
N'importe quel module peut publier le sien avec `emit()` : c'est le point d'entrée prévu pour
Nebula IA (source="ia") quand elle appellera des outils.
Inactif tant que le dashboard n'est pas lancé : coût nul pour le terminal seul.
"""
import builtins
import itertools
import re
import sys
import threading
import time
from collections import deque

EVENTS: deque = deque(maxlen=300)
enabled = False
listeners: list = []  # fonctions appelées avec chaque événement (ex. registre de mission)
local = threading.local()  # .buf = sortie en cours de capture ; .quiet = thread du dashboard
_ids = itertools.count(1)
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_MAX_OUTPUT = 20000


def emit(source: str, title: str, detail: str = "", status: str = "ok", duration: float = 0.0,
         blocks: list | None = None) -> dict:
    """Publie un événement. source : "terminal", "dashboard", "ia"… status : ok / erreur / info."""
    event = {"id": next(_ids), "time": time.time(), "source": source, "title": title,
             "detail": _ANSI.sub("", detail)[-_MAX_OUTPUT:], "status": status,
             "duration": round(duration, 2)}
    if blocks is not None:
        event["blocks"] = blocks
    EVENTS.append(event)
    for listener in listeners:
        listener(event)
    return event


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def since(last_id: int) -> list[dict]:
    return [e for e in list(EVENTS) if e["id"] > last_id]


class _Router:
    """Remplace sys.stdout : recopie la sortie dans le tampon du thread courant.
    Le thread du dashboard (quiet) n'écrit PAS dans le vrai terminal."""

    def __init__(self, real):
        self.real = real

    def write(self, s):
        buf = getattr(local, "buf", None)
        if buf is not None:
            buf.append(s)
        live = getattr(local, "live", None)  # sortie en direct d'une commande lancée depuis le dashboard
        if live is not None:
            live.append(s)
        if not getattr(local, "quiet", False):
            self.real.write(s)
        return len(s)

    def isatty(self):
        return not getattr(local, "quiet", False) and self.real.isatty()

    def __getattr__(self, name):
        return getattr(self.real, name)


def enable() -> None:
    """Active la capture (appelé une fois par le serveur du dashboard)."""
    global enabled
    if enabled:
        return
    enabled = True
    sys.stdout = _Router(sys.stdout)
    real_input = builtins.input

    def guarded_input(prompt=""):
        if getattr(local, "quiet", False):  # personne ne peut répondre depuis le navigateur
            raise EOFError("commande interactive : lancez-la directement dans le terminal, sans redirection")
        return real_input(prompt)

    builtins.input = guarded_input


def begin() -> float:
    """Ouvre une capture. Les captures s'imbriquent (une commande lancée par un script)."""
    if enabled:
        if not hasattr(local, "stack"):
            local.stack = []
        local.stack.append(getattr(local, "buf", None))
        local.buf = []
    return time.time()


def finish(started: float, title: str, status: str, extra: str = "", propagate: bool = True) -> None:
    """Ferme la capture et publie l'événement. La sortie remonte à la capture englobante
    (sauf si elle a été redirigée vers un fichier)."""
    if not enabled:
        return
    detail = "".join(getattr(local, "buf", None) or []) + extra
    parent = local.stack.pop() if getattr(local, "stack", None) else None
    if parent is not None and propagate:
        parent.append(detail)
    local.buf = parent
    # local.source : posé par Nebula IA pour que ses commandes portent la source « ia » (journal + registre).
    emit(getattr(local, "source", None) or ("dashboard" if getattr(local, "quiet", False) else "terminal"),
         title, detail, status, time.time() - started)
