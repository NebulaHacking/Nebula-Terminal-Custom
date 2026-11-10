"""Tests du noyau : registre, calculatrice, profils utilisateurs, lanceur.

Lancer : venv\\Scripts\\python -m unittest discover tests
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from terminal.context import default_context
from terminal.registry import CommandRegistry, build_registry


def _run(reg, ctx, line):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reg.dispatch(ctx, line)
    return buf.getvalue()


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.reg = CommandRegistry()
        self.ctx = default_context()

        @self.reg.register("boom", help_text="boom - explose")
        def _boom(ctx, argv, raw):
            raise ValueError("kaboom")

        @self.reg.register("quitter")
        def _quit(ctx, argv, raw):
            raise SystemExit(0)

        @self.reg.register("echo", aliases=("e",))
        def _echo(ctx, argv, raw):
            print(" ".join(argv[1:]))

    def test_alias_history_and_args(self):
        self.assertEqual(_run(self.reg, self.ctx, "e a b").strip(), "a b")
        self.assertEqual(self.ctx.history, ["e a b"])

    def test_errors_are_contained(self):
        self.assertIn("kaboom", _run(self.reg, self.ctx, "boom"))
        _run(self.reg, self.ctx, "quitter")   # sys.exit d'un outil ne tue pas le terminal
        self.assertFalse(self.ctx.should_exit)

    def test_unknown_with_markup_chars(self):
        self.assertIn("inconnue", _run(self.reg, self.ctx, "nope [x"))

    def test_help_suffix(self):
        self.assertIn("explose", _run(self.reg, self.ctx, "boom.help"))

    def test_real_registry_loads(self):
        names = {c.name for c in build_registry().commands()}
        self.assertTrue({"help", "ls", "calc", "theme", "scan", "nebulaGui"} <= names)


class CalculatorTest(unittest.TestCase):
    def test_math_and_sandbox(self):
        from Tools.calculator import calculer
        self.assertEqual(calculer("2**10"), 1024)
        for evil in ["__import__('os')", "().__class__", "open('x')"]:
            with self.assertRaises(Exception):
                calculer(evil)

    def test_calc_command_with_argument(self):
        out = _run(build_registry(), default_context(), "calc 6*7")
        self.assertIn("42", out)


class UserManagerTest(unittest.TestCase):
    def setUp(self):
        import terminal.user_manager as um
        self.um = um
        self.tmp = Path(tempfile.mkdtemp())
        p1 = mock.patch.object(um, "_USERS_DIR", self.tmp)
        p2 = mock.patch.object(um, "_USERS_CONFIG", self.tmp / "users_config.json")
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)

    def test_profile_roundtrip(self):
        um = self.um
        self.assertTrue(um.create_user("alice"))
        self.assertFalse(um.create_user("alice"))
        self.assertRegex(um.get_user_config("alice")["created_at"], r"^\d{4}-\d{2}-\d{2}T")
        um.save_user_theme("alice", "redark")
        um.save_user_history("alice", ["ls"])
        um.save_user_vfs("alice", {"/": {"Nebula": {"f": "x"}}})
        self.assertEqual(um.get_user_theme("alice"), "redark")
        self.assertEqual(um.get_user_history("alice"), ["ls"])
        self.assertEqual(um.get_user_vfs("alice")["/"]["Nebula"]["f"], "x")
        self.assertTrue(um.delete_user("alice"))
        self.assertEqual(um.get_available_users(), [])

    def test_corrupt_file_is_never_overwritten(self):
        cfg = self.tmp / "users_config.json"
        cfg.write_text("{pas du json", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(self.um.create_user("bob"))
        self.assertEqual(cfg.read_text(encoding="utf-8"), "{pas du json")


class LaunchTest(unittest.TestCase):
    def test_broken_venv_detected(self):
        import launch
        with mock.patch.object(launch, "get_venv_python", return_value=Path("Z:/nope/python.exe")):
            self.assertFalse(launch.venv_is_usable())


if __name__ == "__main__":
    unittest.main()
