"""Nebula IA : politique des commandes, boucle d'agent (fournisseur simulé), mission, formats des fournisseurs."""
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Nebula_IA import agent, providers
from terminal import events, mission
from terminal.context import default_context
from terminal.registry import build_registry


def script(*replies):
    """Faux fournisseur : renvoie les réponses dans l'ordre et garde ce qu'il a reçu."""
    seen = []

    def chat(provider, model, system, history, tools, on_text=None):
        seen.append([dict(m) for m in history])
        return replies[len(seen) - 1]
    return chat, seen


def call(name, **args):
    return {"text": "", "calls": [{"id": f"c{name}{len(args)}", "name": name, "args": args}]}


class IaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for target, value in ((agent, "CONFIG"), (mission, "ROOT")):
            p = mock.patch.object(target, value, self.tmp / value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._close)
        self.ctx, self.reg = default_context(), build_registry()
        self.a = agent.Agent()

    @staticmethod
    def _close():
        if mission.active():
            mission.close()
        if mission._record in events.listeners:
            events.listeners.remove(mission._record)

    def ask(self, *replies, approve=lambda item: True):
        chat, seen = script(*replies)
        with mock.patch.object(providers, "chat", chat), contextlib.redirect_stdout(io.StringIO()):
            answer = self.a.ask("go", self.ctx, approve)
        return answer, seen

    def test_policy(self):
        p = lambda c, auto=False: agent.policy(c, self.ctx, self.reg, auto)[0]  # noqa: E731
        self.assertEqual(p("exec whoami"), "deny")
        self.assertEqual(p("! whoami"), "deny")
        self.ctx.aliases["x"] = "exec"
        self.assertEqual(p("x whoami"), "deny")          # un alias ne contourne pas l'interdiction
        self.assertEqual(p("mission scope add evil.com"), "deny")
        self.assertEqual(p("mission new a b.com"), "deny")
        self.assertEqual(p("mission log"), "ok")
        self.assertEqual(p("scan 10.0.0.1"), "ask")
        self.assertEqual(p("scan 10.0.0.1", auto=True), "ok")
        self.assertEqual(p("rf send https://x"), "ask")  # alias de reqforge
        self.assertEqual(p("rm notes.txt"), "ask")
        self.assertEqual(p("hash sha256 abc"), "ok")
        self.assertEqual(p("ls > out.txt"), "ok")

    def test_loop_runs_command_and_keeps_user_history(self):
        answer, seen = self.ask(call("run_command", command="pwd", why="voir"), {"text": "Fini.", "calls": []})
        self.assertEqual(answer, "Fini.")
        tool = seen[1][-1]
        self.assertEqual(tool["role"], "tool")
        self.assertIn("/", tool["result"])
        self.assertIn("<sortie_commande>", tool["result"])
        self.assertNotIn("pwd", self.ctx.history)
        self.assertTrue(any(e["source"] == "ia" and e["title"] == "pwd" for e in events.EVENTS))

    def test_forbidden_and_refused(self):
        _, seen = self.ask(call("run_command", command="exec whoami", why=""), call("run_command", command="scan 10.0.0.1", why=""),
                           {"text": "ok", "calls": []}, approve=lambda item: False)
        self.assertIn("BLOQUÉ", seen[1][-1]["result"])
        self.assertIn("refusé", seen[2][-1]["result"])

    def test_mission_scope_findings_and_report(self):
        mission.new("t", ["10.0.0.0/24"])
        self.a.configure(auto=True)
        self.ask(call("run_command", command="scan 10.9.9.9", why="hors périmètre"),
                 call("record_finding", severity="haute", title="Port 23 ouvert", evidence="scan", recommendation="fermer"),
                 {"text": "fin", "calls": []})
        items = mission.entries()
        self.assertTrue(any(e["source"] == "ia" and e["status"] == "refusé" for e in items))
        self.assertTrue(any(e["source"] == "constat" for e in items))
        self.assertTrue(mission.verify()[0])
        text = mission.report().read_text(encoding="utf-8")
        self.assertIn("## Constats", text)
        self.assertIn("Port 23 ouvert", text)
        self.assertIn("Port 23 ouvert", self.a.system_prompt(self.ctx, self.reg))  # mémoire de mission

    def test_autopilot_needs_mission(self):
        with self.assertRaises(ValueError):
            self.a.configure(auto=True)

    def test_repair_after_interruption(self):
        self.a.history = [{"role": "user", "text": "x"},
                          {"role": "assistant", "text": "", "calls": [{"id": "1", "name": "run_command", "args": {}}]}]
        self.a._repair()
        self.assertEqual(self.a.history[-1]["role"], "tool")

    def test_provider_formats(self):
        h = [{"role": "user", "text": "q"},
             {"role": "assistant", "text": "", "calls": [{"id": "a", "name": "run_command", "args": {"command": "ls"}},
                                                         {"id": "b", "name": "command_help", "args": {"name": "ls"}}]},
             {"role": "tool", "id": "a", "name": "run_command", "result": "r1"},
             {"role": "tool", "id": "b", "name": "command_help", "result": "r2"}]
        claude = providers._anthropic_messages(h)
        self.assertEqual([m["role"] for m in claude], ["user", "assistant", "user"])
        self.assertEqual(len(claude[2]["content"]), 2)  # résultats d'outils fusionnés
        gpt = providers._openai_messages("s", h)
        self.assertEqual(gpt[2]["tool_calls"][0]["function"]["arguments"], '{"command": "ls"}')
        self.assertEqual(gpt[3]["tool_call_id"], "a")
        gem = providers._gemini_contents(h)
        self.assertEqual([c["role"] for c in gem], ["user", "model", "user"])
        self.assertEqual(providers.resolve("Claude"), "anthropic")


if __name__ == "__main__":
    unittest.main()
