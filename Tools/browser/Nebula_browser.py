# nebula_browser_ultimate.py
import sys
import tempfile
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineSettings,
)

# --- CONFIGURATION ---
ALLOWED_SCHEMES = {"http", "https"}  # refuser tout le reste
DOMAIN_ALLOWLIST = None               # None = pas de restriction, sinon ex: {"example.com"}
# ----------------------

def is_domain_allowed(url: QUrl) -> bool:
    if DOMAIN_ALLOWLIST is None:
        return True
    host = url.host().lower()
    return any(host == d or host.endswith("." + d) for d in DOMAIN_ALLOWLIST)

# --- Page sécurisée avec JS site-par-site ---
class SecurePage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.allowed_js_sites = set()  # sites pour lesquels JS est activé

    def acceptNavigationRequest(self, qurl, nav_type, isMainFrame):
        # Bloquer les schémas non autorisés
        scheme = qurl.scheme().lower()
        if scheme not in ALLOWED_SCHEMES:
            print(f"[Nebula] Bloqué scheme: {scheme} ({qurl.toString()})")
            return False

        # Vérifier allowlist
        if not is_domain_allowed(qurl):
            print(f"[Nebula] Domaine non autorisé: {qurl.toString()}")
            return False

        host = qurl.host().lower()
        # Demande pour activer JS si pas déjà autorisé
        if host not in self.allowed_js_sites:
            reply = QMessageBox.question(None, "Enable JavaScript?",
                                         f"Activer JavaScript pour {host} ?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                self.allowed_js_sites.add(host)
            else:
                self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, False)

        return super().acceptNavigationRequest(qurl, nav_type, isMainFrame)

    # Refuse les certificats invalides par défaut
    def certificateError(self, certError):
        print(f"[Nebula] Certificat non vérifié pour {certError.url().toString()}")
        return False

# --- Navigateur Nebula ---
class NebulaBrowser:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Profil éphémère
        self.profile = QWebEngineProfile(parent=self.app)
        self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        try:
            self.profile.setPersistentStoragePath("")
            self.profile.setCachePath(tempfile.gettempdir())
        except Exception:
            pass

        # Page et vue
        self.page = SecurePage(self.profile)
        self.view = QWebEngineView()
        self.view.setPage(self.page)

        # Paramètres globaux de sécurité
        wsettings = self.view.settings()
        wsettings.setAttribute(QWebEngineSettings.JavascriptEnabled, False)
        wsettings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        wsettings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
        wsettings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        try:
            wsettings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        except Exception:
            pass

        self.profile.setHttpUserAgent("NebulaBrowser/Ultimate/1.0 (+privacy)")

        # Téléchargements bloqués par défaut
        self.profile.downloadRequested.connect(self._on_download_requested)

    def _on_download_requested(self, download_item):
        print("[Nebula] Téléchargement bloqué par défaut :", download_item.url().toString())
        download_item.cancel()

    def browse(self, url):
        if not url.startswith("http"):
            url = "http://" + url
        qurl = QUrl(url)
        if not is_domain_allowed(qurl):
            print("[Nebula] Domaine non autorisé, ouverture annulée.")
            return
        self.view.setWindowTitle("Nebula Browser — Navigation sécurisée")
        self.view.resize(1200, 800)
        self.view.show()
        self.view.load(QUrl(url))
        self.app.exec_()

# --- Fonction pratique pour importer depuis un autre script ---
def browse(url):
    nb = NebulaBrowser()
    nb.browse(url)

# --- Test rapide ---
if __name__ == "__main__":
    browse("https://www.google.com")
