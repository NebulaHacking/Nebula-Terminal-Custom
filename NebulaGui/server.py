"""Nebula Dashboard — petit serveur web local (stdlib) qui montre le terminal en direct.

`start(ctx, registry)` démarre le serveur dans un thread et renvoie l'URL à ouvrir.
Sécurité : écoute uniquement sur 127.0.0.1 et chaque appel /api exige un jeton aléatoire
(le dashboard peut lancer des commandes, dont `rm`/`exec` = vraies commandes système :
sans jeton, n'importe quelle page web ouverte dans le navigateur pourrait en envoyer).
"""
import json
import platform
import secrets
import socket
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from NebulaGui import tools
from terminal import events, mission
from terminal.theme import get_gui_colors, get_theme_name

PORT = 7331
_PAGE = Path(__file__).resolve().parent / "dashboard.html"
# Commandes qui ouvrent une fenêtre, attendent le clavier ou ferment le terminal.
BLOCKED = {"exit", "quit", "clear", "nebulaGui", "browser", "filmux", "nebulers", "knano",
           "ia", "nebula_ia_install", "blackledger",
           # Jamais depuis le navigateur : commande système, scripts, tuto interactif, mise à jour.
           "exec", "run", "tuto", "update"}
_MAX_BODY = 65536

_state = {"url": None, "token": None, "ctx": None, "registry": None, "started": time.time()}
_run_lock = threading.Lock()
_net = {"t": 0.0, "up": 0, "down": 0}


def _system() -> dict:
    import psutil

    mem, io, now = psutil.virtual_memory(), psutil.net_io_counters(), time.time()
    dt = now - _net["t"] if _net["t"] else 0
    up = (io.bytes_sent - _net["up"]) / dt if dt else 0
    down = (io.bytes_recv - _net["down"]) / dt if dt else 0
    _net.update(t=now, up=io.bytes_sent, down=io.bytes_recv)
    return {"cpu": psutil.cpu_percent(None), "ram": mem.percent,
            "ram_used": round(mem.used / 2**30, 1), "ram_total": round(mem.total / 2**30, 1),
            "up": max(0, round(up)), "down": max(0, round(down)), "procs": len(psutil.pids())}


def _commands() -> list[dict]:
    from terminal.commands.builtins import _HELP_CATEGORIES, _describe

    cats = {mod: label for mod, label, _ in _HELP_CATEGORIES}
    return [{"name": c.name, "cat": cats.get(c.func.__module__, "Divers"), "summary": _describe(c),
             "help": c.help_text, "blocked": c.name in BLOCKED}
            for c in sorted(_state["registry"].commands(), key=lambda c: c.name)]


def snapshot(since: int = 0, full: bool = False) -> dict:
    ctx = _state["ctx"]
    names = [h.split()[0] for h in ctx.history if h.split()]
    data = {
        "user": ctx.current_user, "host": socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
        "theme": get_theme_name(), "accent": get_gui_colors().get("accent", ""),
        "path": ctx.vfs.get_path(), "uptime": int(time.time() - _state["started"]),
        "count": len(ctx.history), "top": Counter(names).most_common(6),
        "sys": _system(), "events": events.since(since),
        "mission": mission.active(),
        "running": _running(),
        "ia": _ia().get().public_state(),
        "playbooks": {k: v[0] for k, v in _ia().PLAYBOOKS.items()},
    }
    if full:
        data["commands"] = _commands()
        data["tools"] = tools.catalogue()
    return data


def _running() -> dict | None:
    """Commande du dashboard en cours, avec sa sortie jusqu'ici (affichée en direct par la page)."""
    run = _state.get("running")
    if not run:
        return None
    return {"title": run["title"], "elapsed": round(time.time() - run["started"]),
            "output": events.strip_ansi("".join(run["live"]))[-8000:]}


class _Live:
    """Le temps d'une commande : sa sortie est aussi copiée dans _state["running"]."""

    def __init__(self, title):
        self.title = title

    def __enter__(self):
        _state["running"] = {"title": self.title, "started": time.time(), "live": []}
        events.local.live = _state["running"]["live"]

    def __exit__(self, *exc):
        events.local.live = None
        _state["running"] = None


def run_command(cmd: str) -> dict:
    """Exécute `cmd` via le registre, sortie capturée (rien n'apparaît dans le terminal)."""
    from terminal.registry import expand_alias

    cmd = cmd.strip()
    expanded = expand_alias(_state["ctx"], cmd)  # un alias ne doit pas contourner BLOCKED
    head = expanded.split()[0] if expanded else ""
    target = _state["registry"].get(head[:-5] if head.endswith(".help") else head)
    if target is not None and target.name in BLOCKED and not head.endswith(".help"):
        return events.emit("dashboard", cmd, f"'{head}' est interactive ou ouvre une fenêtre : "
                           "lancez-la dans le terminal.", "erreur")
    with _run_lock, _Live(cmd):  # une commande du dashboard à la fois
        events.local.quiet = True
        try:
            _state["registry"].dispatch(_state["ctx"], cmd)
        finally:
            events.local.quiet = False
        return events.EVENTS[-1]


def run_tool(tool_id: str, args: dict) -> dict:
    """Lance un outil du catalogue. Renvoie l'événement du journal, avec ses blocs de résultat."""
    tool = tools.BY_ID.get(tool_id)
    if tool is None:
        return events.emit("dashboard", str(tool_id)[:40], "Outil inconnu", "erreur")
    try:
        args = tools.clean_args(tool, args)
    except ValueError as e:
        return events.emit("dashboard", tool_id, str(e), "erreur")
    for field in tool["fields"]:  # même garde-fou de périmètre que dans le terminal
        if field.get("target") or field["name"] == "network":
            value = args[field["name"]]
            if not value and tool_id == "hostscan" and mission.active():
                from Tools.recon import local_network
                value = local_network()
            refusal = mission.check(value) if value else None
            if refusal:
                return events.emit("dashboard", tools.title_of(tool, args), refusal, "refusé")
    if "cmd" in tool:  # outil sans résultat structuré : on passe par la commande du terminal
        return run_command(" ".join(tool["cmd"].format(**args).split()))

    started, status = time.time(), "ok"
    events.local.quiet, events.local.buf = True, []  # les print() des moteurs ne vont pas dans le terminal
    try:
        with _Live(tools.title_of(tool, args)):
            blocks = tool["run"](args)
    except PermissionError as e:  # refus du mode mission
        status, blocks = "refusé", [{"notes": [["bad", str(e)]]}]
    except Exception as e:  # une erreur d'outil devient un résultat lisible, jamais un 500
        status, blocks = "erreur", [{"notes": [["bad", str(e) or type(e).__name__]]}]
    finally:
        events.local.quiet, events.local.buf = False, None
    return events.emit("dashboard", tools.title_of(tool, args), "", status, time.time() - started, blocks)


def _ia():
    from Nebula_IA import agent
    return agent


def ia_action(path: str, body: dict) -> dict:
    """Nebula IA depuis le dashboard : message, accord d'une commande, réglages. Même agent que le terminal."""
    agent = _ia()
    a = agent.get()
    if path == "/api/ia":
        text = body.get("message")
        if isinstance(body.get("playbook"), str) and isinstance(body.get("target"), str):
            try:  # playbook : refusé sans mission ou hors périmètre
                text = agent.playbook_prompt(body["playbook"], body["target"].strip())
            except ValueError as e:
                return {"error": str(e)}
        if not isinstance(text, str) or not text.strip():
            raise ValueError
        if a.busy:
            return {"error": "Nebula IA est déjà en train de répondre"}

        def work():
            try:
                a.ask(text.strip()[:20000], _state["ctx"], a.web_approve)
            except RuntimeError:
                pass  # un tour lancé entre-temps depuis le terminal
        threading.Thread(target=work, daemon=True, name="nebula-ia").start()
        return {"ok": True}
    if path == "/api/ia/stop":
        a.stop()
        return {"ok": True}
    if path == "/api/ia/approve":
        return {"ok": a.resolve(str(body.get("id", "")), body.get("ok") is True)}
    try:  # /api/ia/config
        if body.get("reset"):
            a.reset()
        if body.get("key"):
            agent.save_key(body.get("provider") or a.provider, str(body["key"]))
        a.configure(provider=body.get("provider") or None, model=body.get("model") or None,
                    auto=body["auto"] if isinstance(body.get("auto"), bool) else None)
    except (ValueError, agent.providers.ProviderError) as e:
        return {"error": str(e)}
    return {"ok": True}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # pas de logs HTTP dans le terminal
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode())

    def _authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Nebula-Token", ""), _state["token"])

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":
            self._send(200, _PAGE.read_bytes(), "text/html")
        elif path.startswith("/fonts/"):
            # Polices locales facultatives (NebulaGui/fonts/*.woff2). `.name` interdit de sortir du dossier.
            font = _PAGE.parent / "fonts" / Path(path).name
            if font.suffix == ".woff2" and font.is_file():
                self._send(200, font.read_bytes(), "font/woff2")
            else:
                self._send(404, b"")
        elif path == "/api/state" and self._authorized():
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            since = int(params["since"]) if params.get("since", "").isdigit() else 0
            self._json(snapshot(since, params.get("full") == "1"))
        else:
            self._json({"error": "non autorisé"}, 403)

    def do_POST(self):
        if self.path not in ("/api/run", "/api/tool", "/api/ia", "/api/ia/approve", "/api/ia/config", "/api/ia/stop") or not self._authorized():
            self._json({"error": "non autorisé"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= _MAX_BODY:
                raise ValueError
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
            if self.path.startswith("/api/ia"):
                self._json(ia_action(self.path, body))
                return
            if self.path == "/api/run":
                cmd = body["cmd"]
                if not isinstance(cmd, str) or not cmd.strip():
                    raise ValueError
            elif not isinstance(body["id"], str) or not isinstance(body.get("args", {}), dict):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self._json({"error": "requête invalide"}, 400)
            return
        self._json(run_command(cmd) if self.path == "/api/run" else run_tool(body["id"], body.get("args", {})))


class _Server(ThreadingHTTPServer):
    # Sous Windows, la réutilisation d'adresse laisserait deux Nebula écouter sur le même port.
    allow_reuse_address = False
    daemon_threads = True


def start(ctx, registry) -> str:
    """Démarre le dashboard (une seule fois) et renvoie son URL, jeton inclus."""
    _state.update(ctx=ctx, registry=registry)
    if _state["url"]:
        return _state["url"]
    try:
        httpd = _Server(("127.0.0.1", PORT), _Handler)
    except OSError:  # port déjà pris : on laisse le système en choisir un libre
        httpd = _Server(("127.0.0.1", 0), _Handler)
    _state["token"] = secrets.token_urlsafe(24)
    _state["url"] = f"http://127.0.0.1:{httpd.server_address[1]}/?t={_state['token']}"
    import psutil
    psutil.cpu_percent(None)  # amorce : le premier appel ne mesure rien
    events.enable()
    events.emit("système", "Dashboard démarré", f"Session de {ctx.current_user}", "info")
    threading.Thread(target=httpd.serve_forever, daemon=True, name="nebula-dashboard").start()
    return _state["url"]
