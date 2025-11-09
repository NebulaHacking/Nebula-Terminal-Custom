# nebula_os_bloc1.py

import sys, os, platform, socket, psutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QTextEdit, QVBoxLayout, QLabel,
    QHBoxLayout, QFileDialog, QMessageBox, QStackedWidget, QLineEdit, QStatusBar
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QLinearGradient, QBrush, QIcon
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

class NebulaImmersiveOS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nebula Immersive OS")
        self.setGeometry(50, 50, 1280, 720)
        self.setWindowIcon(QIcon("nebula_icon.png"))
        self.setStyleSheet("background-color: #1e1e1e; color: #00ffcc;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_top_bar()
        self.create_main_area()
        self.create_status_bar()
        self.setup_background_animation()

    def create_top_bar(self):
        self.top_bar = QLabel("🌌 Nebula OS - Simulated Environment")
        self.top_bar.setFont(QFont("Fira Sans", 16, QFont.Bold))
        self.top_bar.setStyleSheet("background-color: #2c2c2c; padding: 10px;")
        self.top_bar.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.top_bar)

    def create_main_area(self):
        self.main_area = QHBoxLayout()
        self.main_layout.addLayout(self.main_area)

        self.create_sidebar()
        self.create_content_area()

    def create_sidebar(self):
        self.sidebar = QVBoxLayout()
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setLayout(self.sidebar)
        self.sidebar_widget.setFixedWidth(180)
        self.sidebar_widget.setStyleSheet("background-color: #2c2c2c;")

        self.add_sidebar_button("🖥 Terminal", self.show_terminal)
        self.add_sidebar_button("📁 Fichiers", self.show_file_explorer)
        self.add_sidebar_button("ℹ️ Système", self.show_system_info)
        self.add_sidebar_button("🎨 Thèmes", self.show_theme_selector)

        self.main_area.addWidget(self.sidebar_widget)

    def add_sidebar_button(self, label, callback):
        btn = QPushButton(label)
        btn.setFixedHeight(50)
        btn.setFont(QFont("Fira Sans", 11))
        btn.setStyleSheet("QPushButton {color: #00ffcc; background-color: #1e1e1e; border-radius: 10px;}"
                          "QPushButton:hover {background-color: #00ffcc; color: #1e1e1e;}")
        btn.clicked.connect(callback)
        self.sidebar.addWidget(btn)

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

    def create_terminal(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("JetBrains Mono", 10))
        self.terminal_output.setStyleSheet("background-color: black; color: #00ffcc;")

        self.terminal_input = QLineEdit()
        self.terminal_input.setPlaceholderText("Tapez une commande...")
        self.terminal_input.returnPressed.connect(self.execute_command)

        layout.addWidget(self.terminal_output)
        layout.addWidget(self.terminal_input)
        return widget

    def execute_command(self):
        cmd = self.terminal_input.text()
        self.terminal_output.append(f"> {cmd}")
        self.terminal_input.clear()
        if cmd == "clear":
            self.terminal_output.clear()
        elif cmd == "info":
            self.show_system_info()
        elif cmd == "exit":
            self.close()
        else:
            self.terminal_output.append(f"Commande inconnue: {cmd}")

    def create_file_explorer(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.file_label = QLabel("📁 Explorateur de fichiers (simulé)")
        self.file_label.setFont(QFont("Fira Sans", 12))
        layout.addWidget(self.file_label)

        self.file_button = QPushButton("Parcourir...")
        self.file_button.clicked.connect(self.load_files)
        layout.addWidget(self.file_button)

        return widget

    def load_files(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.file_label.setText(f"📁 Dossier sélectionné : {folder}")

    def create_system_info(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel()
        info.setFont(QFont("Fira Sans", 11))
        info.setStyleSheet("padding: 10px;")
        layout.addWidget(info)

        try:
            user = os.getlogin()
        except:
            user = "Utilisateur"
        host = socket.gethostname()
        os_info = f"{platform.system()} {platform.release()}"
        kernel = platform.version()
        cpu = platform.processor()
        memory = f"{round(psutil.virtual_memory().total / (1024**3))} GB"

        info.setText(f"""
👤 Utilisateur : {user}@{host}
🖥 OS : {os_info}
🧠 Kernel : {kernel}
⚙️ CPU : {cpu}
💾 RAM : {memory}
        """)

        return widget

    def create_theme_selector(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_dark = QPushButton("🌑 Thème Sombre")
        btn_dark.clicked.connect(lambda: self.apply_theme("dark"))
        layout.addWidget(btn_dark)

        btn_light = QPushButton("🌕 Thème Clair")
        btn_light.clicked.connect(lambda: self.apply_theme("light"))
        layout.addWidget(btn_light)

        return widget

    def apply_theme(self, theme):
        if theme == "dark":
            self.setStyleSheet("background-color: #1e1e1e; color: #00ffcc;")
        elif theme == "light":
            self.setStyleSheet("background-color: #f0f0f0; color: #333333;")

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bienvenue dans Nebula OS")

    def setup_background_animation(self):
        self.gradient_position = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_background)
        self.timer.start(60)

    def animate_background(self):
        self.gradient_position = (self.gradient_position + 1) % 360
        color = QColor.fromHsv(self.gradient_position, 255, 80)
        palette = QPalette()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, QColor("#1e1e1e"))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

    def show_terminal(self): self.stack.setCurrentWidget(self.terminal_widget)
    def show_file_explorer(self): self.stack.setCurrentWidget(self.file_widget)
    def show_system_info(self): self.stack.setCurrentWidget(self.system_widget)
    def show_theme_selector(self): self.stack.setCurrentWidget(self.theme_widget)

# === Lancement ===
def launch_nebula_gui():
    app = QApplication(sys.argv)
    window = NebulaImmersiveOS()
    window.show()
    sys.exit(app.exec_())
    # === Notifications système ===
def show_notification(self, type, message):
    notif = QLabel(message, self)
    notif.setFont(QFont("Fira Sans", 10))
    notif.setFixedSize(300, 50)
    notif.setAlignment(Qt.AlignCenter)
    notif.setStyleSheet(f"""
        background-color: {'#00ffcc' if type == 'success' else '#ff4444' if type == 'error' else '#4444ff'};
        color: #1e1e1e;
        border-radius: 10px;
        padding: 10px;
    """)
    notif.move(self.width() - 320, self.height() - 100)
    notif.show()

    anim = QPropertyAnimation(notif, b"windowOpacity")
    anim.setDuration(4000)
    anim.setStartValue(1)
    anim.setEndValue(0)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    anim.start()
    anim.finished.connect(notif.deleteLater)

# === Gestionnaire de tâches simulé ===
def create_task_manager(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    label = QLabel("📊 Gestionnaire de tâches")
    label.setFont(QFont("Fira Sans", 12))
    layout.addWidget(label)

    self.task_list = QTextEdit()
    self.task_list.setReadOnly(True)
    self.task_list.setFont(QFont("JetBrains Mono", 10))
    self.task_list.setStyleSheet("background-color: black; color: #00ffcc;")
    layout.addWidget(self.task_list)

    btn_refresh = QPushButton("🔄 Actualiser")
    btn_refresh.clicked.connect(self.refresh_tasks)
    layout.addWidget(btn_refresh)

    return widget

def refresh_tasks(self):
    self.task_list.clear()
    self.task_list.append("PID   | Nom du processus     | CPU % | RAM %")
    for i in range(5):
        self.task_list.append(f"{1000+i} | Process_{i}           | {i*7}%  | {i*3}%")

# === Fenêtres internes ===
class FloatingWindow(QWidget):
    def __init__(self, title, content):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setStyleSheet("background-color: #2c2c2c; border: 2px solid #00ffcc; border-radius: 12px;")
        self.setFixedSize(400, 300)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        label = QLabel(title)
        label.setFont(QFont("Fira Sans", 12))
        label.setStyleSheet("color: #00ffcc; padding: 8px;")
        layout.addWidget(label)

        content_widget = QTextEdit()
        content_widget.setText(content)
        content_widget.setStyleSheet("background-color: black; color: #00ffcc;")
        layout.addWidget(content_widget)

        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

# === Lancer une fenêtre interne ===
def launch_floating_app(self, title, content):
    win = FloatingWindow(title, content)
    win.move(200, 200)
    win.show()
# === Personnalisation du fond d’écran ===
def set_wallpaper(self, image_path):
    pixmap = QPixmap(image_path).scaled(self.size(), Qt.KeepAspectRatioByExpanding)
    palette = self.palette()
    palette.setBrush(QPalette.Window, QBrush(pixmap))
    self.setPalette(palette)
    self.status_bar.showMessage(f"Fond d’écran appliqué : {os.path.basename(image_path)}")

def choose_wallpaper(self):
    path, _ = QFileDialog.getOpenFileName(self, "Choisir un fond d’écran", "", "Images (*.png *.jpg *.jpeg)")
    if path:
        self.set_wallpaper(path)

# === Session utilisateur ===
def load_user_profile(self):
    self.user_name = "NebulaUser"
    self.avatar_path = "avatar.png"
    self.status_bar.showMessage(f"Connecté en tant que {self.user_name}")

def show_user_profile(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    avatar = QLabel()
    avatar.setPixmap(QPixmap(self.avatar_path).scaled(100, 100))
    layout.addWidget(avatar)

    name_label = QLabel(f"👤 Utilisateur : {self.user_name}")
    name_label.setFont(QFont("Fira Sans", 12))
    layout.addWidget(name_label)

    logout_btn = QPushButton("🔓 Déconnexion")
    logout_btn.clicked.connect(lambda: self.status_bar.showMessage("Session terminée"))
    layout.addWidget(logout_btn)

    return widget

# === Navigateur fictif ===
def create_browser(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    self.address_bar = QLineEdit()
    self.address_bar.setPlaceholderText("nebula://home")
    self.address_bar.returnPressed.connect(self.load_page)
    layout.addWidget(self.address_bar)

    self.page_view = QTextEdit()
    self.page_view.setReadOnly(True)
    layout.addWidget(self.page_view)

    return widget

def load_page(self):
    url = self.address_bar.text()
    if url == "nebula://home":
        self.page_view.setText("Bienvenue sur la page d’accueil de Nebula OS.")
    elif url == "nebula://about":
        self.page_view.setText("Nebula OS est une interface graphique immersive simulée.")
    else:
        self.page_view.setText(f"Erreur 404 : {url} introuvable.")

# === Calendrier stylisé ===
def create_calendar(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    label = QLabel("📅 Calendrier - Septembre 2025")
    label.setFont(QFont("Fira Sans", 12))
    layout.addWidget(label)

    self.calendar_view = QTextEdit()
    self.calendar_view.setReadOnly(True)
    self.calendar_view.setText("""
Lun | Mar | Mer | Jeu | Ven | Sam | Dim
---------------------------------------
  1 |  2  |  3  |  4  |  5  |  6  |  7
  8 |  9  | 10  | 11  | 12  | 13  | 14
 15 | 16  | 17  | 18  | 19  | 20  | 21
 22 | 23  | 24  | 25  | 26  | 27  | 28
 29 | 30
    """)
    layout.addWidget(self.calendar_view)

    return widget

# === Gestionnaire d’apps ===
def create_app_launcher(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    label = QLabel("📦 Applications disponibles")
    label.setFont(QFont("Fira Sans", 12))
    layout.addWidget(label)

    apps = ["Terminal", "Navigateur", "Éditeur de texte", "Gestionnaire de tâches"]
    for app in apps:
        btn = QPushButton(f"🚀 Lancer {app}")
        btn.clicked.connect(lambda _, a=app: self.launch_floating_app(a, f"{a} lancé..."))
        layout.addWidget(btn)

    return widget
# === Éditeur de texte ===
def create_text_editor(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    self.text_area = QTextEdit()
    self.text_area.setFont(QFont("JetBrains Mono", 11))
    self.text_area.setStyleSheet("background-color: black; color: #00ffcc;")
    layout.addWidget(self.text_area)

    btn_save = QPushButton("💾 Sauvegarder")
    btn_save.clicked.connect(self.save_text_file)
    layout.addWidget(btn_save)

    btn_open = QPushButton("📂 Ouvrir fichier")
    btn_open.clicked.connect(self.open_text_file)
    layout.addWidget(btn_open)

    return widget

def save_text_file(self):
    path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder sous", "", "Text Files (*.txt)")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.text_area.toPlainText())
        self.status_bar.showMessage(f"Fichier sauvegardé : {os.path.basename(path)}")

def open_text_file(self):
    path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier", "", "Text Files (*.txt)")
    if path:
        with open(path, "r", encoding="utf-8") as f:
            self.text_area.setText(f.read())
        self.status_bar.showMessage(f"Fichier ouvert : {os.path.basename(path)}")

# === Assistant intégré ===
def create_assistant(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)

    self.chat_display = QTextEdit()
    self.chat_display.setReadOnly(True)
    layout.addWidget(self.chat_display)

    self.chat_input = QLineEdit()
    self.chat_input.setPlaceholderText("Posez une question...")
    self.chat_input.returnPressed.connect(self.respond_to_user)
    layout.addWidget(self.chat_input)

    return widget

def respond_to_user(self):
    user_msg = self.chat_input.text()
    self.chat_display.append(f"👤 Vous : {user_msg}")
    self.chat_input.clear()

    # Réponse simulée
    if "heure" in user_msg.lower():
        reply = f"🧠 Nebula : Il est actuellement {time.strftime('%H:%M')}."
    elif "qui es-tu" in user_msg.lower():
        reply = "🧠 Nebula : Je suis ton assistant virtuel intégré à Nebula OS."
    else:
        reply = "🧠 Nebula : Je ne suis pas sûr, mais je peux chercher pour toi."

    self.chat_display.append(reply)

# === Sauvegarde des préférences ===
def save_preferences(self):
    prefs = {
        "theme": "dark",
        "user": self.user_name,
        "avatar": self.avatar_path
    }
    with open("nebula_prefs.json", "w") as f:
        json.dump(prefs, f)

def load_preferences(self):
    try:
        with open("nebula_prefs.json", "r") as f:
            prefs = json.load(f)
            self.user_name = prefs.get("user", "NebulaUser")
            self.avatar_path = prefs.get("avatar", "avatar.png")
            self.apply_theme(prefs.get("theme", "dark"))
    except:
        self.user_name = "NebulaUser"
        self.avatar_path = "avatar.png"


if __name__ == "__main__":
    launch_nebula_gui()
