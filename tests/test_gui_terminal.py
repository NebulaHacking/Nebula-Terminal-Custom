"""Le terminal de la GUI passe par le registre, y compris pour les commandes interactives."""
import os
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication
    from NebulaGui.Gui import NebulaImmersiveOS
except ImportError:  # PyQt5 absent : on saute ce test
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 non installé")
class GuiTerminalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _send(self, win, text):
        win.terminal_input.setText(text)
        win.execute_command()

    def _wait_idle(self, win, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            self.app.processEvents()
            if not win._busy:
                return
            time.sleep(0.02)
        self.fail("commande toujours en cours")

    def test_registry_command_and_interactive_input(self):
        win = NebulaImmersiveOS()
        out_before = sys.stdout
        self._send(win, "calc 6*7")
        self._wait_idle(win)
        self.assertIn("42", win.terminal_output.toPlainText())

        self._send(win, "calc")          # mode interactif : attend des input()
        time.sleep(0.2)
        self._send(win, "2+3")
        self._send(win, "exit")
        self._wait_idle(win)
        self.assertIn("Résultat : 5", win.terminal_output.toPlainText())
        self.assertIs(sys.stdout, out_before)  # stdout restauré après la commande

        self._send(win, "browser")       # ouvre sa propre fenêtre : refusé proprement
        self.assertIn("propre fenêtre", win.terminal_output.toPlainText())
        win.close()


if __name__ == "__main__":
    unittest.main()
