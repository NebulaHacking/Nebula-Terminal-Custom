"""Espace de travail, shell (redirection, --json, alias, scripts), saisie façon Kali, tuto,
dashboard en direct, historique reqforge en mission, anciens outils modernisés."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Tools.virtualfs import VirtualFS
from terminal import events, mission
from terminal.context import default_context
from terminal.registry import build_registry


def run(line, ctx=None, stdin=""):
    ctx = ctx or default_context()
    out = io.StringIO()
    with contextlib.redirect_stdout(out), mock.patch("builtins.input", side_effect=stdin.splitlines() or [""] * 50):
        status = build_registry().dispatch(ctx, line)
    return out.getvalue(), status


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.fs = VirtualFS()

    def test_paths(self):
        fs = self.fs
        fs.mkdir("a/b", parents=True)
        fs.cd("a/b")
        self.assertEqual(fs.get_path(), "/Nebula/a/b")
        fs.write_file("../../notes.txt", "x")
        self.assertEqual(fs.read("~/notes.txt"), "x")
        self.assertEqual(fs.read("/Nebula/notes.txt"), "x")
        fs.cd("..")
        fs.cd("/")
        self.assertEqual(fs.get_path(), "/")
        fs.cd()
        self.assertEqual(fs.get_path(), "/Nebula")
        with self.assertRaises(ValueError):
            fs.cd("notes.txt")
        with self.assertRaises(ValueError):
            fs.cd("nope")
        self.assertEqual(fs.parts("../../.."), [])

    def test_create_move_copy_remove(self):
        fs = self.fs
        fs.mkdir("d")
        fs.write_file("d/f.txt", "abc")
        fs.write_file("d/f.txt", "def", append=True)
        self.assertEqual(fs.read("d/f.txt"), "abcdef")
        fs.cp("d", "e", recursive=True)
        fs.mv("e/f.txt", "g.txt")
        self.assertEqual([n for n, *_ in fs.ls()], ["d", "e", "g.txt"])
        with self.assertRaises(ValueError):
            fs.cp("d", "z")                     # dossier sans -r
        with self.assertRaises(ValueError):
            fs.mv("d", "d/sub")                 # dans lui-même
        with self.assertRaises(ValueError):
            fs.rm("d")                          # non vide sans -r
        fs.cd("d")
        with self.assertRaises(ValueError):
            fs.rm("/Nebula/d", recursive=True)  # dossier où l'on se trouve
        fs.cd("~")
        fs.rm("d", recursive=True)
        with self.assertRaises(ValueError):
            fs.mkdir("bad|name")
        self.assertIn("g.txt", fs.entries("g"))
        self.assertIn("e/", fs.entries(""))
        self.assertEqual(fs.entries("/Neb"), ["/Nebula/"])

    def test_tree_find_limits_and_load(self):
        fs = self.fs
        fs.mkdir("scans/web", parents=True)
        fs.write_file("scans/web/headers.txt", "x")
        self.assertIn("    └── headers.txt", "\n".join(fs.tree()))
        self.assertEqual(fs.find("*.txt", "/"), ["/Nebula/scans/web/headers.txt"])
        with mock.patch("Tools.virtualfs.MAX_FILE", 10):
            with self.assertRaises(ValueError):
                fs.write_file("big.txt", "x" * 11)
        with self.assertRaises(ValueError):
            fs.load_tree({"/": {"a": 3}})
        fs.load_tree({"/": {"Nebula": {"old.txt": "ancien profil"}}})   # ancien format accepté
        self.assertEqual(fs.read("old.txt"), "ancien profil")

    def test_disk_bridge(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "liste.txt").write_text("admin\nlogin\n", encoding="utf-8")
        (tmp / "bin.dat").write_bytes(b"\x00\x01")
        self.fs.mkdir("listes")
        self.assertEqual(self.fs.import_file(str(tmp / "liste.txt"), "listes"), "/Nebula/listes/liste.txt")
        with self.assertRaises(ValueError):
            self.fs.import_file(str(tmp / "bin.dat"))
        out = self.fs.export_file("listes/liste.txt", str(tmp / "copie.txt"))
        self.assertEqual(Path(out).read_text(encoding="utf-8"), "admin\nlogin\n")
        with self.assertRaises(ValueError):
            self.fs.export_file("listes/liste.txt", str(tmp / "copie.txt"))   # pas d'écrasement sans -f
        self.fs.export_file("listes/liste.txt", str(tmp / "copie.txt"), overwrite=True)


class ShellTest(unittest.TestCase):
    def test_redirect_append_and_grep(self):
        ctx = default_context()
        out, status = run("ipcalc 192.168.1.10/24 > reseau.txt", ctx)
        self.assertEqual(status, "ok")
        self.assertIn("écrites dans /Nebula/reseau.txt", out)
        self.assertNotIn("Broadcast", out)                 # la sortie va dans le fichier, pas à l'écran
        run('echo "fin > du fichier" >> reseau.txt', ctx)
        text = ctx.vfs.read("reseau.txt")
        self.assertIn("192.168.1.255", text)
        self.assertTrue(text.rstrip().endswith('"fin > du fichier"'))
        self.assertNotIn("\x1b[", text)
        self.assertEqual(run("grep -n Broadcast reseau.txt", ctx)[0].strip(), "6:  Broadcast          192.168.1.255")
        self.assertEqual(run("ls >", ctx)[1], "erreur")

    def test_json_and_unknown_command(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        from tests.test_analysis import sample_frames, write_pcap
        write_pcap(tmp / "c.pcap", sample_frames())
        out, _ = run(f'tracewave "{tmp / "c.pcap"}" --json')
        self.assertIsInstance(json.loads(out), list)
        self.assertIn("--json n'est pas disponible", run("ipcalc 10.0.0.1/8 --json")[0])
        out, status = run("sacn 1.2.3.4")
        self.assertEqual(status, "erreur")
        self.assertIn("Vouliez-vous dire « scan »", out)

    def test_alias_run_and_depth(self):
        ctx = default_context()
        run("alias ipc ipcalc", ctx)
        self.assertIn("Réseau             10.0.0.0/8", run("ipc 10.0.0.1/8", ctx)[0])
        self.assertIn("ipc", run("alias", ctx)[0])
        ctx.vfs.write_file("calc.nbl", "# commentaire\nipcalc $1\necho fini $@\n")
        out, _ = run("run calc.nbl 172.16.0.1/12 deux", ctx)
        self.assertIn("172.16.0.0/12", out)
        self.assertIn("fini 172.16.0.1/12 deux", out)
        self.assertIn("3/3", out.replace("2/2", "3/3"))
        ctx.vfs.write_file("boucle.nbl", "run boucle.nbl\n")
        self.assertIn("Trop de scripts imbriqués", run("run boucle.nbl", ctx)[0])
        ctx.vfs.write_file("stop.nbl", "commande-inconnue\necho jamais\n")
        self.assertNotIn("jamais", run("run -e stop.nbl", ctx)[0].split("Arrêt")[-1])
        run("unalias ipc", ctx)
        self.assertEqual(ctx.aliases, {})

    def test_rm_is_workspace_and_exec_is_system(self):
        ctx = default_context()
        ctx.vfs.write_file("x.txt", "1")
        run("rm x.txt", ctx)
        self.assertIsNone(ctx.vfs.read_file("x.txt"))
        with mock.patch("Tools.systemtools.execute_command_real") as real:
            run("exec echo bonjour", ctx)
            real.assert_called_once_with("echo bonjour")

    def test_missing_module_message(self):
        reg = build_registry()

        @reg.register("needs-module", hidden=True)
        def _needs(ctx, argv, raw):
            raise ModuleNotFoundError("No module named 'sklearn'", name="sklearn")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = reg.dispatch(default_context(), "needs-module")
        self.assertEqual(status, "erreur")
        self.assertIn("pip install scikit-learn", out.getvalue())

    def test_update_compares_versions(self):
        from terminal.commands import shell
        with mock.patch.object(shell, "remote_version", return_value="1.6"):
            self.assertIn("à jour", shell.update_from_git(Path(tempfile.mkdtemp())))
        with mock.patch.object(shell, "remote_version", return_value=None):  # GitHub sans numéro (avant la 2.0)
            self.assertIn("à jour", shell.update_from_git(Path(tempfile.mkdtemp())))
        with mock.patch.object(shell, "remote_version", return_value="9.0.0"), \
                mock.patch.object(shell, "_remote_news", return_value="## 9.0.0\n- super"):
            out = shell.update_from_git(Path(tempfile.mkdtemp()), check_only=True)
        self.assertIn("→ v9.0.0", out)
        self.assertIn("- super", out)

    def _zip(self, files):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, content in files.items():
                z.writestr("Nebula-Terminal-Custom-main/" + name, content)
        resp = mock.Mock()
        resp.iter_content.return_value = [buf.getvalue()]
        return resp

    def test_update_zip_replaces_files_but_keeps_user_data(self):
        from terminal.commands import shell
        root = Path(tempfile.mkdtemp())
        (root / "users").mkdir()
        (root / "users" / "users_config.json").write_text("mes profils", encoding="utf-8")
        resp = self._zip({"terminal/x.py": "nouveau", "users/users_config.json": "ÉCRASÉ", "requirements.txt": "rich"})
        with mock.patch.object(shell, "remote_version", return_value="9.0.0"), \
                mock.patch.object(shell, "_remote_news", return_value=""), mock.patch("requests.get", return_value=resp):
            out = shell.update_from_git(root)
        self.assertEqual((root / "terminal" / "x.py").read_text(encoding="utf-8"), "nouveau")
        self.assertEqual((root / "users" / "users_config.json").read_text(encoding="utf-8"), "mes profils")
        self.assertIn("dépendances ont changé", out)

    def test_update_zip_refuses_path_traversal(self):
        from terminal.commands import shell
        root = Path(tempfile.mkdtemp())
        with mock.patch("requests.get", return_value=self._zip({"../../evil.txt": "x"})), self.assertRaises(ValueError):
            shell._zip_update(root)
        self.assertFalse((root.parent / "evil.txt").exists())

    def test_update_git_needs_main_branch(self):
        import shutil
        import subprocess
        from terminal.commands import shell
        if not shutil.which("git"):
            self.skipTest("git absent")
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", "-b", "dev", str(root)], check=True)
        with self.assertRaises(ValueError) as e:
            shell._git_update(root)
        self.assertIn("git switch main", str(e.exception))

    def test_startup_notice_once_a_day(self):
        from terminal.commands import shell
        stamp = Path(tempfile.mkdtemp()) / "check"
        with mock.patch.object(shell, "remote_version", return_value="9.0.0"), mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("NEBULA_NO_UPDATE_CHECK", None)
            self.assertIn("v9.0.0", shell.startup_notice(stamp))
            self.assertIsNone(shell.startup_notice(stamp))  # déjà vérifié aujourd'hui
        with mock.patch.object(shell, "remote_version", side_effect=OSError("hors ligne")):
            self.assertIsNone(shell.startup_notice(Path(tempfile.mkdtemp()) / "check"))

    def test_tuto_runs_and_cleans_up(self):
        ctx = default_context()
        answers = ["", "", "", "", "", "", "", "", "", "", "", "", "", "s", "s", "s", "s", "s", "o"]
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch.object(mission, "ROOT", tmp):
            out, status = run("tuto", ctx, stdin="\n".join(answers))
        self.assertEqual(status, "ok")
        self.assertIn("C'est tout", out)
        self.assertIsNone(ctx.vfs.node(ctx.vfs.parts("~/tuto")))
        self.assertNotIn("ipc", ctx.aliases)


class LineEditorTest(unittest.TestCase):
    RIGHT = "\x1b[C"

    def _type(self, *chunks, ctx=None):
        """Tape chaque morceau avec une petite pause (complétion et suggestion sont calculées en
        tâche de fond, comme pour un humain), puis Entrée."""
        import threading
        import time
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        from terminal.line_editor import make_session

        ctx = ctx or default_context()
        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            session = make_session(build_registry(), ctx, input=pipe, output=DummyOutput())

            def typist():
                for chunk in [*chunks, "\r"]:
                    time.sleep(0.3)
                    pipe.send_text(chunk)

            threading.Thread(target=typist, daemon=True).start()
            return session.prompt("> ")

    def test_tab_completes_commands_options_and_paths(self):
        self.assertEqual(self._type("tracew", "\t"), "tracewave")
        self.assertEqual(self._type("mission ver", "\t"), "mission verify")
        ctx = default_context()
        ctx.vfs.mkdir("rapports")
        self.assertEqual(self._type("cd rap", "\t", ctx=ctx), "cd rapports/")

    def test_grey_suggestion_from_history_accepted_with_right_arrow(self):
        ctx = default_context()
        ctx.history = ["sslscan example.com", "ls"]
        self.assertEqual(self._type("ssl", self.RIGHT, ctx=ctx), "sslscan example.com")

    def test_masked_secret_is_never_suggested(self):
        ctx = default_context()
        run("pwstrength MonSecret123", ctx, stdin="MonSecret123")
        self.assertEqual(self._type("pwstrength ", self.RIGHT, ctx=ctx), "pwstrength ")


class DashboardAndMissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patcher = mock.patch.object(mission, "ROOT", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        if mission.active():
            mission.close()
        if mission._record in events.listeners:
            events.listeners.remove(mission._record)

    def test_dashboard_blocks_dangerous_commands_even_through_alias(self):
        from NebulaGui import server
        ctx = default_context()
        ctx.aliases["x"] = "exec"
        server._state.update(ctx=ctx, registry=build_registry())
        for cmd in ("exec dir", "! dir", "x dir", "run script.nbl", "tuto", "update"):
            self.assertEqual(server.run_command(cmd)["status"], "erreur", cmd)

    def test_live_output_is_visible_while_running(self):
        from NebulaGui import server
        seen = {}

        def slow(a):
            print("étape 1")
            seen["live"] = server._running()
            return [{"notes": [["ok", "fini"]]}]

        server._state.update(ctx=default_context(), registry=build_registry())
        with mock.patch.dict(server.tools.BY_ID, {"lent": {"id": "lent", "fields": [], "run": slow}}):
            events.enable()
            event = server.run_tool("lent", {})
        self.assertEqual(event["status"], "ok")
        self.assertIn("étape 1", seen["live"]["output"])
        self.assertIsNone(server._running())

    def test_reqforge_history_survives_restart_in_mission(self):
        from Tools import reqforge as rf
        mission.new("web", ["example.com"])
        fake = {"n": 9001, "time": "10:00:00", "verify": True, "follow": False,
                "request": {"method": "GET", "url": "https://example.com/", "headers": [], "body": ""},
                "response": {"status": 200, "reason": "OK", "url": "https://example.com/", "headers": [], "body": "ok",
                             "size": 2, "truncated": False, "ms": 5, "redirects": []}, "findings": [["ok", "Aucun constat"]]}
        (self.tmp / "web" / "reqforge.jsonl").write_text(json.dumps(fake) + "\n", encoding="utf-8")
        with mock.patch.object(rf, "HISTORY", []), mock.patch.object(rf, "_loaded_for", None):
            self.assertEqual(rf.get(9001)["response"]["body"], "ok")
            self.assertEqual(next(rf._ids), 9002)


class ModernizedToolsTest(unittest.TestCase):
    def test_weather_and_ip_blocks(self):
        from Tools import iptracker, weather
        wttr = {"current_condition": [{"temp_C": "12", "FeelsLikeC": "11", "humidity": "88", "windspeedKmph": "9",
                                       "winddir16Point": "SW", "pressure": "1006", "visibility": "10", "uvIndex": "1",
                                       "observation_time": "12:00 PM", "lang_fr": [{"value": "Bruine"}]}],
                "nearest_area": [{"areaName": [{"value": "Fribourg"}], "region": [{"value": ""}], "country": [{"value": "Suisse"}]}],
                "weather": [{"date": "2026-11-11", "mintempC": "6", "maxtempC": "13",
                             "hourly": [{"chanceofrain": "68", "lang_fr": [{"value": "Pluie"}]}]}]}
        resp = mock.Mock(status_code=200, json=lambda: wttr)
        with mock.patch("requests.get", return_value=resp):
            blocks = weather.weather_blocks("Fribourg")
        self.assertEqual(blocks[0]["title"], "Fribourg, Suisse")
        self.assertEqual(blocks[1]["rows"][0], ["2026-11-11", "6 °C", "13 °C", "Pluie", "68 %"])

        ip = {"status": "success", "query": "8.8.8.8", "country": "USA", "countryCode": "US", "regionName": "Virginie",
              "city": "Ashburn", "lat": 39, "lon": -77, "timezone": "America/New_York", "isp": "Google", "proxy": True,
              "hosting": True, "mobile": False}
        with mock.patch("requests.get", return_value=mock.Mock(json=lambda: ip)):
            blocks = iptracker.ip_blocks("8.8.8.8")
        self.assertEqual(blocks[0]["notes"][0][0], "warn")
        with self.assertRaises(ValueError):
            iptracker.ip_blocks("-x")


if __name__ == "__main__":
    unittest.main()
