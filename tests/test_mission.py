"""Mode mission : périmètre, refus hors périmètre, registre chaîné, diff, rapport."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from terminal import events, mission
from terminal.context import default_context
from terminal.registry import build_registry


class MissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(mission, "ROOT", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(self._close)
        self.ctx, self.reg = default_context(), build_registry()

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

    def test_scope_rules(self):
        scope = ["example.com", "10.0.0.0/24", "192.168.1.5/32"]
        for ok in ("example.com", "www.example.com", "https://api.example.com/x", "10.0.0.7", "10.0.0.0/28", "192.168.1.5"):
            self.assertTrue(mission.in_scope(ok, scope), ok)
        for bad in ("notexample.com", "example.com.evil.org", "10.0.1.7", "10.0.0.0/16", "192.168.1.6"):
            self.assertFalse(mission.in_scope(bad, scope), bad)
        # domaine non listé : accepté seulement si toutes ses adresses sont dans le périmètre
        addr = lambda *ips: [(0, 0, 0, "", (ip, 0)) for ip in ips]  # noqa: E731
        with mock.patch("socket.getaddrinfo", return_value=addr("10.0.0.9")):
            self.assertTrue(mission.in_scope("interne.test", scope))
        with mock.patch("socket.getaddrinfo", return_value=addr("10.0.0.9", "8.8.8.8")):
            self.assertFalse(mission.in_scope("mixte.test", scope))
        with self.assertRaises(ValueError):
            mission.new("../evil", ["example.com"])
        with self.assertRaises(ValueError):
            mission.new("vide", [])

    def test_out_of_scope_is_refused_and_nothing_runs(self):
        mission.new("audit", ["127.0.0.1"])
        with mock.patch("Tools.portscan.scan_ports") as scan, mock.patch("terminal.commands.network.scan_ports", scan):
            out = self.run_cmd("scan -f 8.8.8.8")
            scan.assert_not_called()
            self.assertIn("REFUSÉ", out)
            self.run_cmd("scan -f 127.0.0.1 1 2")
            scan.assert_called_once()
        last = mission.entries()
        self.assertEqual([e["status"] for e in last if e["command"].startswith("scan")], ["refusé", "ok"])
        self.assertNotIn("REFUSÉ", self.run_cmd("encode hex abc"))  # commandes locales : jamais limitées

        mission.close()
        with mock.patch("terminal.commands.network.scan_ports") as scan:
            self.run_cmd("scan -f 8.8.8.8")  # sans mission : aucun garde-fou
            scan.assert_called_once()

    def test_ledger_chain_detects_tampering(self):
        mission.new("preuves", ["example.com"])
        self.run_cmd("encode hex Nebula")
        self.run_cmd("mission note premier constat")
        ok, detail = mission.verify()
        self.assertTrue(ok, detail)
        items = mission.entries()
        self.assertIn("4e6562756c61", next(e["output"] for e in items if e["command"] == "encode hex Nebula"))

        ledger = self.tmp / "preuves" / "ledger.jsonl"
        original = ledger.read_text(encoding="utf-8")
        lines = original.splitlines()

        edited = json.loads(lines[1])
        edited["output"] = "falsifié"
        ledger.write_text("\n".join([lines[0], json.dumps(edited, ensure_ascii=False), *lines[2:]]) + "\n", encoding="utf-8")
        self.assertEqual(mission.verify()[0], False)
        self.assertIn("ligne 2", mission.verify()[1])

        ledger.write_text("\n".join(lines[:1] + lines[2:]) + "\n", encoding="utf-8")  # ligne supprimée
        self.assertFalse(mission.verify()[0])

        ledger.write_text(original, encoding="utf-8")
        self.assertTrue(mission.verify()[0])

    def test_diff_report_and_reopen(self):
        mission.new("suivi", ["example.com"], "robin")
        self.assertIsNone(mission.diff("ipcalc 10.0.0.1/24"))
        self.run_cmd("ts 1700000000")
        with mock.patch("Tools.cryptokit.ts_convert", return_value={"Timestamp": "1700000000", "Local": "CHANGÉ"}):
            self.run_cmd("ts 1700000000")
        changes = "\n".join(mission.diff("ts 1700000000"))
        self.assertIn("+  Local      CHANGÉ", changes)
        self.assertIn("-  UTC", changes)

        self.run_cmd("sslscan hors-perimetre.invalid")
        text = mission.report().read_text(encoding="utf-8")
        for expected in ("# Rapport de mission — suivi", "example.com", "intacte", "Tentatives hors périmètre", "ts 1700000000"):
            self.assertIn(expected, text)

        mission.close()
        self.assertIsNone(mission.active())
        mission.restore()            # rien d'ouvert : ne fait rien
        self.assertIsNone(mission.active())
        mission.open_("suivi")
        mission.close()
        (self.tmp / ".active").write_text("suivi", encoding="utf-8")
        mission.restore()            # rouverte au démarrage suivant
        self.assertEqual(mission.active()["name"], "suivi")
        self.assertIn("mission:suivi", __import__("terminal.prompt", fromlist=["x"]).get_prompt(self.ctx))

    def test_dashboard_tools_use_the_same_guard(self):
        from NebulaGui import server
        server._state.update(ctx=self.ctx, registry=self.reg)
        mission.new("web", ["example.com"])
        with mock.patch("Tools.recon.tls_scan") as tls:
            event = server.run_tool("sslscan", {"target": "autre.invalid"})
            tls.assert_not_called()
        self.assertEqual(event["status"], "refusé")
        ok = server.run_tool("ipcalc", {"spec": "10.0.0.1/24"})
        self.assertEqual(ok["status"], "ok")
        self.assertIn("Réseau", mission.entries()[-1]["output"])
        self.assertTrue(mission.verify()[0])


if __name__ == "__main__":
    unittest.main()
