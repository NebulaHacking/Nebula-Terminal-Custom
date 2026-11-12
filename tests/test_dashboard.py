"""Dashboard web : jeton obligatoire, état, exécution de commandes, capture de la sortie."""
import contextlib
import io
import json
import unittest
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from NebulaGui import server
from terminal import events
from terminal.context import default_context
from terminal.registry import build_registry


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = default_context()
        cls.reg = build_registry()
        url = urlsplit(server.start(cls.ctx, cls.reg))
        cls.base = f"http://{url.netloc}"
        cls.token = url.query.split("=", 1)[1]

    def call(self, path, body=None, token=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body else None,
                                     headers={"X-Nebula-Token": self.token if token is None else token})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def test_token_is_required(self):
        for path, body in (("/api/state", None), ("/api/run", {"cmd": "uuid"})):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                self.call(path, body, token="faux")
            self.assertEqual(cm.exception.code, 403)

    def test_fonts_route_cannot_leave_its_folder(self):
        for path in ("/fonts/..%2Fserver.py", "/fonts/../server.py", "/fonts/absent.woff2"):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(self.base + path, timeout=10)
            self.assertEqual(cm.exception.code, 404)

    def test_page_and_state(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as r:
            self.assertTrue(b"<title>Nebula</title>" in r.read())
        state = self.call("/api/state?full=1")
        self.assertEqual(state["user"], self.ctx.current_user)
        self.assertIn("hashid", {c["name"] for c in state["commands"]})
        self.assertIn("cpu", state["sys"])

    def test_run_captures_output_without_touching_terminal(self):
        real = io.StringIO()
        with contextlib.redirect_stdout(events._Router(real)):
            event = self.call("/api/run", {"cmd": "calc 6*7"})
        self.assertIn("42", event["detail"])
        self.assertEqual((event["source"], event["status"]), ("dashboard", "ok"))
        self.assertEqual(real.getvalue(), "")
        self.assertIn(event["id"], [e["id"] for e in self.call("/api/state")["events"]])

    def test_interactive_and_blocked_commands_fail_cleanly(self):
        self.assertIn("interactive", self.call("/api/run", {"cmd": "calc"})["detail"])  # input() refusé
        blocked = self.call("/api/run", {"cmd": "exit"})
        self.assertEqual(blocked["status"], "erreur")
        self.assertFalse(self.ctx.should_exit)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.call("/api/run", {"nope": 1})
        self.assertEqual(cm.exception.code, 400)

    def test_tools_return_structured_results(self):
        state = self.call("/api/state?full=1")
        ids = {t["id"] for t in state["tools"]}
        self.assertTrue({"dns", "sslscan", "scan", "hashid", "fileinfo"} <= ids)
        self.assertNotIn("run", state["tools"][0])

        event = self.call("/api/tool", {"id": "ipcalc", "args": {"spec": "192.168.1.10/24"}})
        self.assertEqual(event["status"], "ok")
        self.assertIn(["Réseau", "192.168.1.0/24"], event["blocks"][0]["kv"])

        missing = self.call("/api/tool", {"id": "ipcalc", "args": {}})
        self.assertEqual(missing["status"], "erreur")
        bad = self.call("/api/tool", {"id": "ipcalc", "args": {"spec": "999.1.1.1/24"}})
        self.assertEqual((bad["status"], bad["blocks"][0]["notes"][0][0]), ("erreur", "bad"))
        self.assertEqual(self.call("/api/tool", {"id": "nope", "args": {}})["status"], "erreur")

        via_cmd = self.call("/api/tool", {"id": "ping", "args": {"target": ""}})  # outil « commande »
        self.assertEqual(via_cmd["status"], "erreur")

    def test_secret_fields_never_reach_the_journal(self):
        event = self.call("/api/tool", {"id": "pwstrength", "args": {"password": "MonSecret123"}})
        self.assertEqual(event["title"], "pwstrength")
        self.assertNotIn("MonSecret123", json.dumps(self.call("/api/state")["events"]))
        self.assertNotIn("MonSecret123", " ".join(self.ctx.history))

    def test_every_tool_field_is_wired(self):
        from NebulaGui import tools
        for tool in tools.TOOLS:
            self.assertTrue(("run" in tool) != ("cmd" in tool), tool["id"])
            if "cmd" in tool:
                tool["cmd"].format(**{f["name"]: "x" for f in tool["fields"]})
                self.assertIsNotNone(self.reg.get(tool["cmd"].split()[0]), tool["id"])

    def test_terminal_commands_appear_in_feed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.reg.dispatch(self.ctx, "encode hex Nebula")
        last = events.EVENTS[-1]
        self.assertEqual((last["source"], last["title"]), ("terminal", "encode hex Nebula"))


if __name__ == "__main__":
    unittest.main()
