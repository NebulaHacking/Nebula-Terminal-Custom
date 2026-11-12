"""Nouveautés 2.0 : streaming des fournisseurs, Stop, playbooks, retest, rapport HTML, constats, outils en blocs, thèmes."""
import contextlib
import io
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from Nebula_IA import agent, providers
from terminal import events, mission
from terminal.context import default_context
from terminal.registry import build_registry


class StreamingTest(unittest.TestCase):
    """Chaque protocole reconstruit le même résultat qu'en mode normal, et appelle on_text au fil de l'eau."""

    def run_stream(self, provider, chunks):
        got = []
        with mock.patch.object(providers, "_events", return_value=iter(chunks)), \
                mock.patch.dict("os.environ", {"OPENAI_API_KEY": "k", "ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "k"}):
            reply = providers.chat(provider, "m", "s", [{"role": "user", "text": "q"}], agent.TOOLS, got.append)
        return reply, "".join(got)

    def test_openai(self):
        reply, live = self.run_stream("openai", [
            {"choices": [{"delta": {"content": "Je "}}]}, {"choices": [{"delta": {"content": "lance."}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "run_command", "arguments": '{"comm'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'and": "ls", "why": "x"}'}}]}}]}])
        self.assertEqual((reply["text"], live), ("Je lance.", "Je lance."))
        self.assertEqual(reply["calls"], [{"id": "c1", "name": "run_command", "args": {"command": "ls", "why": "x"}}])

    def test_anthropic(self):
        reply, live = self.run_stream("anthropic", [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Ok"}},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "run_command", "input": {}}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"command": "pwd"'}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": ', "why": "y"}'}},
            {"type": "message_stop"}])
        self.assertEqual((reply["text"], live), ("Ok", "Ok"))
        self.assertEqual(reply["calls"][0]["args"], {"command": "pwd", "why": "y"})

    def test_gemini(self):
        reply, live = self.run_stream("gemini", [
            {"candidates": [{"content": {"parts": [{"text": "Sal"}]}}]},
            {"candidates": [{"content": {"parts": [{"text": "ut"}, {"functionCall": {"name": "command_help", "args": {"name": "ls"}},
                                                                    "thoughtSignature": "sig"}]}}]}])
        self.assertEqual((reply["text"], live), ("Salut", "Salut"))
        self.assertEqual(reply["calls"][0]["name"], "command_help")
        self.assertEqual(reply["raw"]["content"][-1]["thoughtSignature"], "sig")  # rejouée telle quelle

    def test_ollama(self):
        reply, live = self.run_stream("ollama", [
            {"message": {"content": "a"}}, {"message": {"content": "b", "tool_calls": [{"function": {"name": "run_command", "arguments": {"command": "ls"}}}]}},
            {"done": True}])
        self.assertEqual((reply["text"], live), ("ab", "ab"))
        self.assertEqual(reply["calls"][0]["args"], {"command": "ls"})

    def test_empty_tools_are_omitted(self):
        with mock.patch.object(providers, "_post", return_value={"choices": [{"message": {"content": "OK"}}]}) as post, \
                mock.patch.dict("os.environ", {"OPENAI_API_KEY": "k"}):
            providers.chat("openai", "m", "s", [{"role": "user", "text": "t"}], [])
        self.assertNotIn("tools", post.call_args[0][2])

    def test_provider_test_without_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(agent.test_providers(["openai"])[0][1], "—")


class MissionV2Test(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for target, value in ((agent, "CONFIG"), (mission, "ROOT")):
            p = mock.patch.object(target, value, self.tmp / value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._close)
        self.ctx, self.reg = default_context(), build_registry()
        mission.new("m", ["10.0.0.0/24", "example.com"])

    @staticmethod
    def _close():
        if mission.active():
            mission.close()
        if mission._record in events.listeners:
            events.listeners.remove(mission._record)

    def run_cmd(self, line):
        buf = io.StringIO()
        with contextlib.redirect_stdout(events._Router(buf)):
            self.reg.dispatch(self.ctx, line)
        return buf.getvalue()

    def test_retest_report_html_and_compliance(self):
        mission.finding("haute", "Bannière <script>", "echo", "corriger", "vulnerabilite", "echo version vulnerable", "vulnerable")
        mission.finding("moyenne", "Déjà corrigé", "echo", "rien", "chiffrement", "echo tout va bien", "faible")
        mission.finding("basse", "Sans preuve rejouable", "-", "-")
        out = self.run_cmd("mission retest")
        self.assertIn("toujours présent", out)
        states = {f["title"]: f["state"] for f in mission.findings()}
        self.assertEqual(states["Bannière <script>"], "toujours présent")
        self.assertEqual(states["Déjà corrigé"], "corrigé")
        self.assertEqual(states["Sans preuve rejouable"], "non revérifié")
        self.assertTrue(any(e["source"] == "retest" and e["command"] == "echo version vulnerable" for e in mission.entries()))
        self.assertTrue(mission.verify()[0])
        md = mission.report().read_text(encoding="utf-8")
        self.assertIn("## Conformité", md)
        self.assertIn("A.8.8", md)
        html = (self.tmp / "ROOT" / "m" / "rapport.html").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", html)   # le contenu venant de la cible est échappé
        self.assertNotIn("<script>", html)
        self.assertIn("toujours présent", html)

    def test_manual_finding(self):
        out = self.run_cmd('mission constat moyenne "HSTS absent" --cat chiffrement --cmd "headers example.com" --attendu "absent"')
        self.assertIn("inscrit", out)
        f = mission.findings()[0]
        self.assertEqual((f["category"], f["command"], f["expect"]), ("chiffrement", "headers example.com", "absent"))
        self.assertIn("Gravité inconnue", self.run_cmd('mission constat grave "x"'))

    def test_playbook_scope(self):
        self.assertIn("sslscan example.com", agent.playbook_prompt("web", "example.com"))
        with self.assertRaises(ValueError):
            agent.playbook_prompt("web", "10.9.9.9")  # hors périmètre
        with self.assertRaises(ValueError):
            agent.playbook_prompt("inconnu", "example.com")
        mission.close()
        with self.assertRaises(ValueError):
            agent.playbook_prompt("web", "example.com")  # sans mission

    def test_ai_cannot_retest(self):
        self.assertEqual(agent.policy("mission retest", self.ctx, self.reg, True)[0], "deny")
        self.assertEqual(agent.policy("mission constats", self.ctx, self.reg, False)[0], "ok")

    def test_stop(self):
        a = agent.Agent()

        def chat(provider, model, system, history, tools, on_text=None):
            a.stop()
            on_text("début")
            return {"text": "jamais", "calls": []}

        with mock.patch.object(providers, "chat", chat), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(a.ask("go", self.ctx, lambda i: True), "")
        self.assertEqual(a.log[-1]["text"], "Arrêté.")
        self.assertFalse(a.busy)


class _Reflect(BaseHTTPRequestHandler):
    """Faux site vulnérable : renvoie le paramètre q tel quel."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
        body = f'<a href="/search?q=test">recherche</a><p>{q}</p>'.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)


class ToolsV2Test(unittest.TestCase):
    def test_nexariescan_blocks(self):
        from Tools.nexariescan import scan_blocks

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Reflect)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            blocks = scan_blocks(f"http://127.0.0.1:{httpd.server_address[1]}/", delay=0, max_pages=5)
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(blocks[1]["notes"][0][0], "bad")
        self.assertEqual(len(blocks[2]["rows"]), 1)

    def test_shadowviper_offline(self):
        import requests
        from Tools import shadowviper as sv

        self.assertEqual([sv.detect_input_type(v) for v in ("8.8.8.8", "AS15169", "a@b.ch", "https://x.ch/", "x.ch", "?")],
                         ["ip", "asn", "email", "url", "domain", "unknown"])
        with mock.patch.object(sv.requests, "get", side_effect=requests.ConnectionError("hors ligne")), \
                mock.patch.object(sv, "_whois", side_effect=OSError("hors ligne")), \
                mock.patch.object(sv, "_trace", return_value="trace"), mock.patch.object(sv, "_open_ports", return_value=[23]):
            blocks = sv.investigate("127.0.0.1")
        notes = next(b["notes"] for b in blocks if "notes" in b)
        self.assertTrue(any(level == "bad" and "23" in text for level, text in notes))
        self.assertTrue(any(b.get("title") == "Ports courants ouverts" for b in blocks))

    def test_themes(self):
        from terminal import theme

        self.assertGreaterEqual(len(theme.get_available_themes()), 8)
        for name in theme.get_available_themes():
            self.assertTrue(theme._load_themes()[name].get("banner"), name)
        self.assertEqual(theme.paint("a\nb", "matrix").count("\033[38;5;"), 2)


if __name__ == "__main__":
    unittest.main()
