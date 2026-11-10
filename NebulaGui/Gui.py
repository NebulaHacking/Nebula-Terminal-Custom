"""
Nebula Immersive OS - Interface graphique professionnelle
Refactorisé pour être maintenable et professionnel.
"""
import sys
import os
import platform
import socket
import psutil
import time
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QTextEdit, QVBoxLayout,
    QHBoxLayout, QFileDialog, QMessageBox, QStackedWidget, QLineEdit, QStatusBar,
    QLabel
)
from PyQt5.QtGui import (
    QTextCursor, QFont, QPalette, QColor, QLinearGradient, QBrush, QIcon, QPixmap
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QObject, pyqtSignal
import io
import queue
import re
import threading

# Import du système de thème
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from terminal.theme import get_gui_colors, get_theme_name
from terminal.context import default_context
from terminal.registry import build_registry

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# Ces commandes ouvrent leur propre fenêtre Qt : impossible depuis le thread d'une commande.
GUI_BLOCKED = {"nebulaGui", "browser", "filmux"}


class _Bridge(QObject):
    """Transporte la sortie du thread de commande vers le thread Qt."""
    output = pyqtSignal(str)
    finished = pyqtSignal()


class _GuiStdout(io.TextIOBase):
    def __init__(self, bridge):
        self.bridge = bridge

    def write(self, s):
        if s:
            self.bridge.output.emit(_ANSI.sub("", s))
        return len(s)

    def isatty(self):
        return False


class _GuiStdin(io.TextIOBase):
    """input() des commandes lit ici ; la ligne de saisie de la GUI y dépose le texte."""
    def __init__(self):
        self.lines = queue.Queue()

    def readable(self):
        return True

    def readline(self, size=-1):
        line = self.lines.get()
        return "" if line is None else line + "\n"  # None → EOF (fermeture de la fenêtre)


class NebulaImmersiveOS(QMainWindow):
    """Fenêtre principale de Nebula OS."""

    def __init__(self, ctx=None):
        super().__init__()
        # Même contexte que le terminal texte quand la GUI est lancée depuis `nebulaGui`.
        self.ctx = ctx or default_context()
        self.registry = build_registry()
        self._busy = False
        self._saved_std = None
        self._stdin = _GuiStdin()
        self._bridge = _Bridge()
        self._bridge.output.connect(self._append_output)
        self._bridge.finished.connect(self._command_done)
        self._init_window()
        self._init_ui()
        self._init_theme()

    def _init_window(self):
        """Configuration de la fenêtre principale."""
        self.setWindowTitle("Nebula Immersive OS")
        self.setGeometry(50, 50, 1280, 720)
        self.setWindowIcon(QIcon(os.path.join(_ROOT, "Images", "Nebula_Logo.png")))

    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_top_bar()
        self.create_main_area()
        self.create_status_bar()
        self.setup_background_animation()

    def _init_theme(self):
        """Applique le thème actuel."""
        colors = get_gui_colors()
        self._apply_global_styles(colors)

    def _apply_global_styles(self, colors):
        """Applique les styles globaux basés sur le thème."""
        bg = colors.get('background', '#121212')
        fg = colors.get('text', '#e0e0e0')
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")

    # === Top Bar ===
    def create_top_bar(self):
        self.top_bar = QLabel("🌌 Nebula OS")
        self.top_bar.setFont(QFont("Fira Sans", 16, QFont.Bold))
        colors = get_gui_colors()
        self.top_bar.setStyleSheet(
            f"background-color: {colors.get('primary', '#00d4ff')};"
            f"padding: 10px; color: {colors.get('text', '#e0e0e0')};"
        )
        self.top_bar.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.top_bar)

    # === Main Area ===
    def create_main_area(self):
        self.main_area = QHBoxLayout()
        self.main_layout.addLayout(self.main_area)

        self.create_sidebar()
        self.create_content_area()

    # === Sidebar ===
    def create_sidebar(self):
        self.sidebar = QVBoxLayout()
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(self.sidebar)
        sidebar_widget.setFixedWidth(180)

        colors = get_gui_colors()
        sidebar_widget.setStyleSheet(
            f"background-color: {colors.get('secondary', '#1e1e1e')};"
            "border-radius: 10px;"
        )

        self.add_sidebar_button("🖥 Terminal", self.show_terminal)
        self.add_sidebar_button("📁 Fichiers", self.show_file_explorer)
        self.add_sidebar_button("ℹ️ Système", self.show_system_info)
        self.add_sidebar_button("🎨 Thèmes", self.show_theme_selector)

        self.main_area.addWidget(sidebar_widget)

    def add_sidebar_button(self, label, callback):
        """Crée un bouton de sidebar avec le style du thème."""
        colors = get_gui_colors()
        btn = QPushButton(label)
        btn.setFixedHeight(50)
        btn.setFont(QFont("Fira Sans", 11))

        btn_fg = colors.get('btn_fg', '#00ffcc')
        btn_bg = colors.get('btn_bg', '#1e1e1e')
        btn_hover_bg = colors.get('btn_hover_bg', '#00ffcc')
        btn_hover_fg = colors.get('btn_hover_fg', '#1e1e1e')

        btn.setStyleSheet(f"""
            QPushButton {{
                color: {btn_fg};
                background-color: {btn_bg};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                color: {btn_hover_fg};
            }}
        """)
        btn.clicked.connect(callback)
        self.sidebar.addWidget(btn)

    # === Content Area ===
    def create_content_area(self):
        self.stack = QStackedWidget()
        self.main_area.addWidget(self.stack)

        self.terminal_widget = self.create_terminal()
        self.file_widget = self.create_file_explorer()
        self.system_widget = self.create_system_info()
        self.theme_widget = self.create_theme_selector()

        self.stack.addWidget(self.terminal_widget)
        self.stack.addWidget(self.file_widget)
        self.stack.addWidget(self.system_widget)
        self.stack.addWidget(self.theme_widget)

    # === Terminal Panel ===
    def create_terminal(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        colors = get_gui_colors()

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("JetBrains Mono", 10))
        self.terminal_output.setStyleSheet(
            f"background-color: {colors.get('terminal_bg', '#0a0a0a')};"
            f"color: {colors.get('terminal_fg', '#00ffcc')};"
            "border-radius: 5px; padding: 5px;"
        )

        self.terminal_input = QLineEdit()
        self.terminal_input.setPlaceholderText("Tapez une commande Nebula...")
        self.terminal_input.setFont(QFont("JetBrains Mono", 10))
        self.terminal_input.setStyleSheet(
            f"background-color: {colors.get('input_bg', '#2d2d2d')};"
            f"color: {colors.get('text', '#e0e0e0')};"
            "border-radius: 5px; padding: 8px;"
        )
        self.terminal_input.returnPressed.connect(self.execute_command)

        layout.addWidget(self.terminal_output, 1)
        layout.addWidget(self.terminal_input)
        return widget

    def execute_command(self):
        """Exécute la saisie via le registre du terminal (toutes les commandes Nebula)."""
        text = self.terminal_input.text()
        self.terminal_input.clear()
        if self._busy:  # la commande en cours attend une saisie (input())
            self._append_output(text + "\n")
            self._stdin.lines.put(text)
            return
        cmd = text.strip()
        if not cmd:
            return
        self._append_output(f"$ {cmd}\n")
        head = cmd.split()[0]
        if head == "clear":
            self.terminal_output.clear()
            return
        if head in ("exit", "quit"):
            self.close()
            return
        if head in GUI_BLOCKED:
            self._append_output(f"'{head}' ouvre sa propre fenêtre : lancez-le depuis le terminal texte.\n")
            return
        self._busy = True
        self.terminal_input.setPlaceholderText("Commande en cours... (Entrée envoie la saisie à la commande)")
        threading.Thread(target=self._run_command, args=(cmd,), daemon=True).start()

    def _run_command(self, cmd):
        """Thread de commande : stdout/stdin redirigés vers le widget le temps de la commande."""
        self._saved_std = (sys.stdout, sys.stderr, sys.stdin)
        sys.stdout = sys.stderr = _GuiStdout(self._bridge)
        sys.stdin = self._stdin
        try:
            self.registry.dispatch(self.ctx, cmd)
        finally:
            self._restore_std()
            self._bridge.finished.emit()

    def _restore_std(self):
        if self._saved_std:
            sys.stdout, sys.stderr, sys.stdin = self._saved_std
            self._saved_std = None

    def _append_output(self, text):
        self.terminal_output.moveCursor(QTextCursor.End)
        self.terminal_output.insertPlainText(text)
        self.terminal_output.ensureCursorVisible()

    def _command_done(self):
        self._busy = False
        self.terminal_input.setPlaceholderText("Tapez une commande Nebula...")
        if self.ctx.should_exit:
            self.close()

    def closeEvent(self, event):
        if self._busy:
            self._stdin.lines.put(None)  # débloque un input() en attente
            self._restore_std()  # le terminal texte récupère sa sortie tout de suite
        super().closeEvent(event)

    # === File Explorer Panel ===
    def create_file_explorer(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        colors = get_gui_colors()

        title = QLabel("📁 Explorateur de fichiers")
        title.setFont(QFont("Fira Sans", 14, QFont.Bold))
        title.setStyleSheet(f"color: {colors.get('primary', '#00d4ff')};")
        layout.addWidget(title)

        self.file_browser = QTextEdit()
        self.file_browser.setReadOnly(True)
        self.file_browser.setFont(QFont("JetBrains Mono", 10))
        self.file_browser.setStyleSheet(
            f"background-color: {colors.get('item_bg', '#1a1a1a')};"
            f"color: {colors.get('text', '#e0e0e0')};"
        )
        layout.addWidget(self.file_browser, 1)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.refresh_file_browser)
        btn_layout.addWidget(btn_refresh)

        btn_browse = QPushButton("📂 Parcourir...")
        btn_browse.clicked.connect(self.browse_folder)
        btn_layout.addWidget(btn_browse)

        layout.addLayout(btn_layout)
        self.refresh_file_browser()
        return widget

    def refresh_file_browser(self):
        """Rafraîchit l'affichage du navigateur de fichiers."""
        try:
            current_path = os.getcwd() if os.name != 'nt' else os.path.expanduser("~")
            items = []
            try:
                items = os.listdir(current_path)
            except PermissionError:
                current_path = os.path.expanduser("~")
                items = os.listdir(current_path)

            folders = sorted([f for f in items if os.path.isdir(os.path.join(current_path, f))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(current_path, f))])

            html = f"<b>Dossier :</b> {current_path}<br><br>"
            html += "<b>📁 Dossiers :</b><br>"
            for f in folders[:10]:
                html += f"  📁 {f}<br>"
            if len(folders) > 10:
                html += f"  ... et {len(folders) - 10} autres<br>"

            html += "<br><b>📄 Fichiers :</b><br>"
            for f in files[:10]:
                size = os.path.getsize(os.path.join(current_path, f))
                html += f"  📄 {f} ({size:,} octets)<br>"
            if len(files) > 10:
                html += f"  ... et {len(files) - 10} autres<br>"

            self.file_browser.setHtml(html)
        except Exception as e:
            self.file_browser.setText(f"Erreur : {e}")

    def browse_folder(self):
        """Ouvre une boîte de dialogue pour choisir un dossier."""
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            try:
                os.chdir(folder)
                self.refresh_file_browser()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible d'accéder au dossier : {e}")

    # === System Info Panel ===
    def create_system_info(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        colors = get_gui_colors()

        title = QLabel("ℹ️ Informations système")
        title.setFont(QFont("Fira Sans", 14, QFont.Bold))
        title.setStyleSheet(f"color: {colors.get('primary', '#00d4ff')};")
        layout.addWidget(title)

        self.system_info = QTextEdit()
        self.system_info.setReadOnly(True)
        self.system_info.setFont(QFont("Fira Sans", 10))
        self.system_info.setStyleSheet(
            f"background-color: {colors.get('item_bg', '#1a1a1a')};"
            f"color: {colors.get('text', '#e0e0e0')};"
        )
        layout.addWidget(self.system_info, 1)

        self.update_system_info()
        return widget

    def update_system_info(self):
        """Met à jour les informations système."""
        try:
            user = os.getlogin()
        except:
            user = "Utilisateur"

        host = socket.gethostname()
        os_info = f"{platform.system()} {platform.release()}"
        kernel = platform.version()
        cpu = platform.processor()

        try:
            memory = psutil.virtual_memory()
            ram_total = f"{round(memory.total / (1024**3))} GB"
            ram_used = f"{round(memory.used / (1024**3))} GB"
            ram_percent = memory.percent
        except:
            ram_total = "N/A"
            ram_used = "N/A"
            ram_percent = "N/A"

        try:
            disk = psutil.disk_usage('/')
            disk_total = f"{round(disk.total / (1024**3))} GB"
            disk_used = f"{round(disk.used / (1024**3))} GB"
        except:
            disk_total = "N/A"
            disk_used = "N/A"

        info_text = f"""
<b>👤 Utilisateur :</b> {user}@{host}
<b>🖥 Système :</b> {os_info}
<b>🧠 Kernel :</b> {kernel}
<b>⚙️ Processeur :</b> {cpu}
<b>💾 Mémoire RAM :</b> {ram_used} / {ram_total} ({ram_percent}%)
<b>💿 Stockage :</b> {disk_used} / {disk_total}
<b>📡 Adresse IP :</b> {socket.gethostbyname(host)}
        """
        self.system_info.setText(info_text.strip())

    # === Theme Selector Panel ===
    def create_theme_selector(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        colors = get_gui_colors()

        title = QLabel("🎨 Sélecteur de thème")
        title.setFont(QFont("Fira Sans", 14, QFont.Bold))
        title.setStyleSheet(f"color: {colors.get('primary', '#00d4ff')};")
        layout.addWidget(title)

        current_theme = get_theme_name()
        current_label = QLabel(f"Thème actuel : <b>{current_theme.upper()}</b>")
        current_label.setFont(QFont("Fira Sans", 12))
        layout.addWidget(current_label)

        layout.addSpacing(20)

        btn_micha = QPushButton("🌿 Micha (Kali Style)")
        btn_micha.setFont(QFont("Fira Sans", 11))
        btn_micha.setFixedHeight(50)
        btn_micha.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #121212;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ffcc;
            }
        """)
        btn_micha.clicked.connect(lambda: self.apply_theme("micha"))
        layout.addWidget(btn_micha)

        btn_redark = QPushButton("🔥 Redark (BlackArch Style)")
        btn_redark.setFont(QFont("Fira Sans", 11))
        btn_redark.setFixedHeight(50)
        btn_redark.setStyleSheet("""
            QPushButton {
                background-color: #ff3333;
                color: #0a0a0a;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
        """)
        btn_redark.clicked.connect(lambda: self.apply_theme("redark"))
        layout.addWidget(btn_redark)

        layout.addStretch()
        return widget

    def apply_theme(self, theme_name):
        """Applique un thème et ferme la GUI pour forcer le rechargement."""
        from terminal.theme import set_theme
        if set_theme(theme_name):
            QMessageBox.information(
                self,
                "Thème appliqué",
                f"Le thème '{theme_name}' a été appliqué.\n"
                "Relancez Nebula pour voir les changements."
            )

    # === Status Bar ===
    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bienvenue dans Nebula OS")

    # === Background Animation ===
    def setup_background_animation(self):
        self.gradient_position = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_background)
        self.timer.start(60)

    def animate_background(self):
        self.gradient_position = (self.gradient_position + 1) % 360
        color = QColor.fromHsv(self.gradient_position, 200, 60)
        palette = QPalette()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, QColor("#0a0a0a"))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

    # === Navigation ===
    def show_terminal(self): self.stack.setCurrentWidget(self.terminal_widget)
    def show_file_explorer(self): self.stack.setCurrentWidget(self.file_widget)
    def show_system_info(self):
        self.update_system_info()
        self.stack.setCurrentWidget(self.system_widget)
    def show_theme_selector(self): self.stack.setCurrentWidget(self.theme_widget)


# === Lancement ===
def launch_nebula_gui(ctx=None):
    """Lance l'interface GUI Nebula (sans quitter le terminal à la fermeture)."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    window = NebulaImmersiveOS(ctx)
    window.show()
    app.exec_()


if __name__ == "__main__":
    launch_nebula_gui()