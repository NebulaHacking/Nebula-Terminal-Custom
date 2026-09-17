"""
Filmux GUI — Interface minimaliste themee

Utilise les couleurs du theme actif (themes.json)
"""

import sys
import webbrowser
import urllib3
from urllib.parse import quote
from bs4 import BeautifulSoup

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame
)
from PyQt5.QtCore import Qt

VIDSRC_BASE_URL = "https://vidsrc.me/embed/movie/"
TMDB_SEARCH_URL = "https://www.themoviedb.org/search/movie"


def get_gui_colors():
    """Charge les couleurs GUI depuis le theme actif."""
    try:
        from terminal.theme import get_gui_colors, set_theme, get_theme_name
        colors = get_gui_colors()
        # Valeurs par defaut si theme non configure
        return colors if colors else {
            "background": "#121212",
            "primary": "#00d4ff",
            "secondary": "#1e1e1e",
            "text": "#e0e0e0",
            "input_bg": "#2d2d2d",
            "item_bg": "#1a1a1a",
            "item_selected": "#0078d4",
            "item_hover": "#2d2d2d"
        }
    except Exception:
        return {
            "background": "#121212",
            "primary": "#00d4ff",
            "secondary": "#1e1e1e",
            "text": "#e0e0e0",
            "input_bg": "#2d2d2d",
            "item_bg": "#1a1a1a",
            "item_selected": "#0078d4",
            "item_hover": "#2d2d2d"
        }


class FilmuxWindow(QMainWindow):
    """Fenetre principale themee"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Filmux 3.0")
        self.resize(900, 700)
        self.setMinimumSize(700, 500)

        self.colors = get_gui_colors()
        self.init_ui()

    def init_ui(self):
        """Interface centree avec les couleurs du theme"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(20)

        c = self.colors

        # Titre
        title = QLabel("FILMUX")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: bold;
            color: {c['primary']};
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel("Interface de streaming video")
        desc.setStyleSheet(f"font-size: 16px; color: #888;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(30)

        # Barre de recherche
        search_frame = QFrame()
        search_frame.setStyleSheet(f"background: {c['secondary']}; border-radius: 8px;")
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(40, 30, 40, 30)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un film...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 16px 20px;
                font-size: 18px;
                border: 2px solid #444;
                border-radius: 8px;
                background: {c['input_bg']};
                color: {c['text']};
                selection-background-color: {c['primary']};
            }}
            QLineEdit:focus {{
                border-color: {c['primary']};
            }}
        """)
        self.search_input.returnPressed.connect(self.search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("Rechercher")
        search_btn.setFixedHeight(50)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['primary']};
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                color: white;
            }}
            QPushButton:hover {{
                background: {c['item_selected']};
            }}
        """)
        search_btn.clicked.connect(self.search)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_frame)

        layout.addSpacing(30)

        # Resultats
        self.results_list = QListWidget()
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background: {c['item_bg']};
                color: {c['text']};
                border: 1px solid #333;
                border-radius: 8px;
                font-size: 16px;
            }}
            QListWidget::item {{
                padding: 16px 20px;
                border-bottom: 1px solid #2d2d2d;
            }}
            QListWidget::item:selected {{
                background: {c['item_selected']};
                color: white;
            }}
            QListWidget::item:hover {{
                background: {c['item_hover']};
            }}
        """)
        self.results_list.itemClicked.connect(self.open_movie)
        self.results_list.hide()
        layout.addWidget(self.results_list)

        layout.addStretch()

        # Status
        self.status_label = QLabel("Pret")
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.show()

    def search(self):
        """Recherche themoviedb.org"""
        query = self.search_input.text().strip()
        if not query:
            return

        self.status_label.setText(f"Recherche: '{query}'...")
        self.results_list.clear()

        USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        url = f"{TMDB_SEARCH_URL}?query={quote(query)}&page=1"

        try:
            http = urllib3.PoolManager()
            req = http.request("GET", url, headers={"User-Agent": USER_AGENT}, timeout=10.0)

            if req.status != 200:
                self.status_label.setText("Erreur de recherche")
                return

            soup = BeautifulSoup(req.data, 'html.parser')
            posters = soup.find_all('img', class_='poster')

            count = 0
            for poster in posters[:20]:
                title = poster.get('alt', '').strip()
                link = poster.find_parent('a', href=lambda x: x and x.startswith('/movie/'))
                if not link or not title:
                    continue

                href = link.get('href', '')
                tmdb_id = href.split('/')[-1].split('-')[0]

                if tmdb_id and title:
                    item = QListWidgetItem(title)
                    item.setData(Qt.UserRole, tmdb_id)
                    self.results_list.addItem(item)
                    count += 1

            if count > 0:
                self.results_list.show()
                self.status_label.setText(f"{count} resultats. Cliquez pour ouvrir.")
            else:
                self.status_label.setText("Aucun resultat")

        except Exception as e:
            self.status_label.setText(f"Erreur: {str(e)}")

    def open_movie(self, item):
        """Ouvre le film dans le navigateur externe"""
        tmdb_id = item.data(Qt.UserRole)
        url = f"{VIDSRC_BASE_URL}{tmdb_id}"
        webbrowser.open(url)
        self.status_label.setText(f"Ouverture: {item.text()}")


def run_gui():
    """Lance Filmux GUI"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setStyleSheet(f"""
        QMainWindow {{ background: {get_gui_colors()['background']}; }}
        QWidget {{ background: {get_gui_colors()['background']}; color: {get_gui_colors()['text']}; }}
    """)

    window = FilmuxWindow()
    sys.exit(app.exec_())


def main():
    run_gui()


if __name__ == "__main__":
    main()