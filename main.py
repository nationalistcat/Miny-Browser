"""
Miny Browser — Modern PySide6 Web Browser
"""
import sys, os, json, re, datetime, urllib.request, time, logging, threading, base64
from pathlib import Path
from functools import partial

from PySide6.QtCore import (Qt, QUrl, QSize, QPoint, QTimer, QEvent, Signal, QObject, QStandardPaths, QPropertyAnimation, QEasingCurve)
from PySide6.QtGui import (QIcon, QPixmap, QAction, QFont, QColor, QCursor, QKeySequence, QShortcut, QPainter, QPen)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTabBar, QLineEdit, QPushButton, QToolBar, QLabel,
    QStatusBar, QMenu, QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QMessageBox, QFileDialog, QComboBox,
    QCheckBox, QGroupBox, QFormLayout, QSplitter, QTextEdit,
    QProgressBar, QSizePolicy, QFrame, QStyle, QStyleOptionTab,
    QToolButton, QSpacerItem, QWidgetAction, QScrollArea, QGridLayout,
    QStackedWidget, QSpinBox, QButtonGroup, QRadioButton,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineDownloadRequest, QWebEngineUrlRequestInterceptor
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# EXE içinde dosyaları bulabilmek için yardımcı fonksiyon
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
APPDATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "MinyBrowser"
if not APPDATA_DIR.exists():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = APPDATA_DIR / "settings.json"
BOOKMARKS_FILE = APPDATA_DIR / "bookmarks.json"
HISTORY_FILE = APPDATA_DIR / "history.json"
SESSION_FILE = APPDATA_DIR / "session.json"
NEWTAB_PATH = resource_path("newtab.html")
LOGO_PATH = resource_path("logo.png")
ICO_PATH = resource_path("logo.ico")

# ── LOGGING SETUP ──
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(APPDATA_DIR / "miny.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.info("Miny Browser Başlatılıyor...")


# ── Default Settings ──
DEFAULT_SETTINGS = {
    "search_engine": "Google",
    "homepage": "newtab",
    "custom_homepage": "",
    "adblock_enabled": True,
    "language": "tr",
    "restore_session": True,
    "javascript_enabled": True,
    "webrtc_enabled": True,
    "do_not_track": False,
    "auto_clear_history": False,
    "default_zoom": 100,
    "font_size": 16,
    "smooth_scrolling": True,
    "hardware_acceleration": True,
    "developer_mode": False,
    "user_agent": "default",
    "proxy": "",
    "download_path": "",
}

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"JSON okuma hatasi ({path}): {e}")
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"JSON yazma hatasi ({path}): {e}")

def load_settings():
    s = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
    for k, v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v
    return s

def save_settings(s):
    save_json(SETTINGS_FILE, s)

def newtab_url(settings=None, is_private=False):
    if settings is None:
        settings = load_settings()
        
    if not is_private and settings.get("homepage") == "custom":
        custom = settings.get("custom_homepage", "").strip()
        if custom:
            if not custom.startswith(("http://", "https://", "ftp://", "file://")):
                custom = "https://" + custom
            return custom

    engine = settings.get("search_engine", "Google")
    lang = settings.get("language", "tr")
    path = resource_path("private_newtab.html") if is_private else NEWTAB_PATH
    return QUrl.fromLocalFile(str(path)).toString() + f"?engine={engine}&lang={lang}"

# ══════════════════════════════════════════════
#  DARK THEME QSS (MODERNIZED & MICRO-UI)
# ══════════════════════════════════════════════
DARK_QSS = """
/* ══ MINY BROWSER — DEEP AURORA PREMIUM (MODERNIZED) ══ */

/* ── Global ── */
QMainWindow { background: #06010f; }
QWidget {
    color: #FBFBFE;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* ── Tooltip ── */
QToolTip {
    background: rgba(20, 10, 35, 0.95);
    color: #ffffff;
    border: 1px solid rgba(123, 45, 255, 0.3);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Toolbar (Header) ── */
QToolBar {
    background: #06010f;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    padding: 10px 16px;
    spacing: 12px;
}
QToolBar QToolButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 6px;
    min-width: 36px;
    min-height: 36px;
    color: #FBFBFE;
    icon-size: 20px;
}
QToolBar QToolButton:hover { background: rgba(255, 255, 255, 0.08); }
QToolBar QToolButton:pressed { background: rgba(255, 255, 255, 0.12); }
QToolBar QToolButton:disabled { color: rgba(255, 255, 255, 0.2); }

/* ── URL Bar (Modern Capsule Center) ── */
QLineEdit#url_bar {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px; /* Perfect capsule */
    padding: 8px 24px;
    color: #FBFBFE;
    font-size: 14.5px;
    font-weight: 500;
    selection-background-color: rgba(254, 78, 0, 0.5); /* Miny Orange */
}
QLineEdit#url_bar:hover { 
    background: rgba(255, 255, 255, 0.09); 
    border: 1px solid rgba(255, 255, 255, 0.12);
}
QLineEdit#url_bar:focus {
    background: #06010f;
    border: 2px solid #7b2dff; /* Miny Purple */
    color: #ffffff;
    border-radius: 20px;
}
QLineEdit#url_bar[is_private="true"] {
    background: rgba(123, 45, 255, 0.12);
    border: 1px solid #7b2dff;
    color: #e9d5ff;
}
QLineEdit#url_bar[is_private="true"]:focus {
    background: #06010f;
    border: 2px solid #fe4e00;
    color: #ffffff;
}

/* ── Tabs (Modern Floating Style) ── */
QTabWidget::pane { border: none; background: #06010f; }
QTabBar {
    background: #06010f;
    border: none;
    qproperty-drawBase: 0;
    padding: 8px 10px 4px 10px;
}
QTabBar::tab {
    background: rgba(255, 255, 255, 0.03);
    color: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: rgba(123, 45, 255, 0.12); 
    border: 1px solid rgba(123, 45, 255, 0.3);
    border-bottom: 2px solid #7b2dff; /* Neon Purple Indicator */
    color: #ffffff;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background: rgba(255, 255, 255, 0.07);
    color: #FBFBFE;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* ── Status Bar Removed ── */

/* ── Menü ve Listeler ── */
QMenu {
    background: rgba(20, 10, 35, 0.95);
    border: 1px solid rgba(123, 45, 255, 0.3);
    border-radius: 8px;
    padding: 6px 0px;
}
QMenu::item { padding: 8px 36px 8px 16px; color: #FBFBFE; font-size: 13px; }
QMenu::item:selected { background: rgba(123, 45, 255, 0.3); color: #ffffff; }
QMenu::separator { height: 1px; background: rgba(255, 255, 255, 0.05); margin: 4px 8px; }

QListWidget { background: transparent; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 4px; outline: none; }
QListWidget::item { padding: 10px 14px; border-radius: 6px; color: rgba(255, 255, 255, 0.6); font-size: 13px; }
QListWidget::item:hover { background: rgba(255, 255, 255, 0.05); color: #FBFBFE; }
QListWidget::item:selected { background: rgba(254, 78, 0, 0.2); color: #fe4e00; }

/* ── Scrollbars ── */
QScrollBar:vertical { width: 12px; background: transparent; border-left: 1px solid rgba(255, 255, 255, 0.03); }
QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.15); border-radius: 5px; min-height: 40px; margin: 3px; }
QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.25); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
# ══════════════════════════════════════════════
#  ADBLOCK INTERCEPTOR
# ══════════════════════════════════════════════
class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocked_domains = set()
        self.enabled = True

    def load_hosts(self):
        hosts_path = BASE_DIR / "hosts_adblock.txt"
        if hosts_path.exists():
            try:
                with open(hosts_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split()
                            if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
                                domain = parts[1].strip()
                                if domain and domain != "localhost":
                                    self.blocked_domains.add(domain)
            except Exception:
                pass

    def download_hosts(self):
        def _task():
            url = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
            try:
                logging.info("Adblock: Hosts listesi indiriliyor...")
                req = urllib.request.Request(url, headers={"User-Agent": "MinyBrowser/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read().decode("utf-8", errors="ignore")
                hosts_path = BASE_DIR / "hosts_adblock.txt"
                with open(hosts_path, "w", encoding="utf-8") as f:
                    f.write(data)
                self.load_hosts()
                logging.info("Adblock: Hosts listesi guncellendi.")
            except Exception as e:
                logging.error(f"Adblock guncellemesi basarisiz oldu: {e}")
        
        threading.Thread(target=_task, daemon=True).start()

    def interceptRequest(self, info):
        if not self.enabled:
            return
        url = info.requestUrl().host()
        if url in self.blocked_domains:
            info.block(True)

# ══════════════════════════════════════════════
#  HISTORY MANAGER
# ══════════════════════════════════════════════
class HistoryManager:
    def __init__(self):
        self.entries = load_json(HISTORY_FILE, [])

    def add(self, url, title):
        if not url or "newtab.html" in url:
            return
        entry = {
            "url": url,
            "title": title or url,
            "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        self.entries.insert(0, entry)
        if len(self.entries) > 5000:
            self.entries = self.entries[:5000]
        self.save()

    def clear(self):
        # İndirmeler Paneli Eklentisi
        self.download_popup = DownloadPopup(self)
        self.download_popup.hide()
        self.download_popup.btn_more.clicked.connect(self._show_downloads_page)
        self.download_popup.btn_clear.clicked.connect(self._clear_downloads_popup)
        
        self._downloads = []
        self._restore_session()

    def save(self):
        save_json(HISTORY_FILE, self.entries)

# ══════════════════════════════════════════════
#  INTERNAL PAGE BASE (For Settings, History, etc)
# ══════════════════════════════════════════════
class InternalPage(QWidget):
    def __init__(self, title_text, internal_url, parent=None):
        super().__init__(parent)
        self.internal_title = title_text
        self.internal_url = internal_url
        self.setStyleSheet("""
            QWidget { background: #06010f; color: #ffffff; font-family: 'Segoe UI Variable Display', 'Inter', sans-serif; }
            QListWidget { background: transparent; border: none; padding: 16px; outline: none; }
            QListWidget::item { padding: 16px 20px; border-radius: 14px; margin-bottom: 8px; color: rgba(255,255,255,0.6); background: rgba(255,255,255,0.03); border: 1px solid transparent; font-size: 14px; font-weight: 500; }
            QListWidget::item:hover { background: rgba(255,255,255,0.07); color: #ffffff; border-color: rgba(255, 255, 255, 0.05); }
            QListWidget::item:selected { background: rgba(123, 45, 255, 0.15); color: #a78bfa; border-color: rgba(123, 45, 255, 0.3); font-weight: 600; }
            QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #ffffff; border-radius: 10px; padding: 10px 20px; font-weight: 600; font-size: 13px; }
            QPushButton:hover { background: rgba(255,255,255,0.1); border-color: rgba(255, 255, 255, 0.2); }
            QPushButton#danger_btn { background: transparent; border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; }
            QPushButton#danger_btn:hover { background: #ef4444; color: white; }
            QLabel#page_title { font-size: 32px; font-weight: 800; color: #ffffff; margin-bottom: 24px; letter-spacing: -1px; }
        """)
        
        self.base_lay = QVBoxLayout(self)
        self.base_lay.setContentsMargins(100, 40, 100, 40)
        
        header = QHBoxLayout()
        logo_lbl = QLabel()
        import os
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        logo_path = LOGO_PATH
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        header.addWidget(logo_lbl)
        
        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet("font-size: 28px; font-weight: 800; padding-left: 12px; color: white;")
        header.addWidget(title_lbl)
        header.addStretch()
        self.base_lay.addLayout(header)
        
        sep_line = QFrame()
        sep_line.setFixedHeight(1)
        sep_line.setStyleSheet("background: #1C1C24; margin: 24px 0;")
        self.base_lay.addWidget(sep_line)
        
        self.content_lay = QVBoxLayout()
        self.base_lay.addLayout(self.content_lay)

    def url(self): return QUrl(f"miny://{self.internal_url}")
    def title(self): return self.internal_title
    def icon(self): return QIcon()
    def history(self):
        class MockHistory:
            def canGoBack(self): return False
            def canGoForward(self): return False
        return MockHistory()
    def page(self): return None
    def load(self, url): pass
    def back(self): pass
    def forward(self): pass
    def reload(self): pass

class DownloadsPage(InternalPage):
    def __init__(self, parent=None):
        super().__init__("İndirmeler", "indirmeler", parent)
        self.download_list = QListWidget()
        self.content_lay.addWidget(self.download_list)
        self.items = {}

    def add_download(self, download):
        fname = download.downloadFileName()
        item = QListWidgetItem(f"{fname} — İndiriliyor...")
        self.download_list.insertItem(0, item)
        self.items[id(download)] = item

        download.receivedBytesChanged.connect(lambda: self._on_progress(download))
        download.isFinishedChanged.connect(lambda: self._on_finished(download))

    def _on_progress(self, dl):
        item = self.items.get(id(dl))
        if not item: return
        total = dl.totalBytes()
        received = dl.receivedBytes()
        fname = dl.downloadFileName()
        if total > 0:
            pct = int(received * 100 / total)
            mb_recv = received / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            item.setText(f"{fname} — {pct}% ({mb_recv:.1f}/{mb_total:.1f} MB)")
        else:
            item.setText(f"{fname} — {received / 1024:.0f} KB")

    def _on_finished(self, dl):
        item = self.items.get(id(dl))
        if item:
            item.setText(f"{dl.downloadFileName()} — Tamamlandı")

# ══════════════════════════════════════════════
#  FIND BAR (Ctrl+F)
# ══════════════════════════════════════════════
class FindBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background: #1e293b; border-top: 1px solid rgba(255, 255, 255, 0.1); }
            QLineEdit { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 6px 14px; color: #f8fafc; font-size: 13px; }
            QLineEdit:focus { border-color: #38bdf8; background: #0f172a; }
            QPushButton { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px 10px; color: #f8fafc; min-width: 24px; font-size: 12px; }
            QPushButton:hover { background: #334155; border-color: rgba(255, 255, 255, 0.2); }
            QPushButton:pressed { background: #475569; }
            QLabel { color: #94a3b8; font-size: 12px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Sayfada ara...")
        self.input.setFixedWidth(260)
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self.find_next)
        layout.addWidget(self.input)

        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

        btn_prev = QPushButton("▲")
        btn_prev.clicked.connect(self.find_prev)
        layout.addWidget(btn_prev)

        btn_next = QPushButton("▼")
        btn_next.clicked.connect(self.find_next)
        layout.addWidget(btn_next)

        layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.clicked.connect(self.close_bar)
        layout.addWidget(btn_close)

        self.setVisible(False)
        self._browser = None

    def set_browser(self, browser):
        self._browser = browser

    def open_bar(self):
        self.setVisible(True)
        self.input.setFocus()
        self.input.selectAll()

    def close_bar(self):
        self.setVisible(False)
        if self._browser:
            self._browser.findText("")

    def _on_text_changed(self, text):
        if self._browser and text:
            self._browser.findText(text)
        elif self._browser:
            self._browser.findText("")

    def find_next(self):
        if self._browser and self.input.text():
            self._browser.findText(self.input.text())

    def find_prev(self):
        if self._browser and self.input.text():
            self._browser.findText(self.input.text(), QWebEnginePage.FindFlag.FindBackward)

# ══════════════════════════════════════════════
#  BROWSER PAGE & VIEW
# ══════════════════════════════════════════════
class BrowserPage(QWebEnginePage):
    new_tab_requested = Signal(QUrl)

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def createWindow(self, wtype):
        page = BrowserPage(self.profile(), self)
        page.urlChanged.connect(lambda url: self.new_tab_requested.emit(url))
        return page

    def certificateError(self, error):
        return True

class BrowserView(QWebEngineView):
    new_tab_signal = Signal(QUrl)

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self._page = BrowserPage(profile, self)
        self.setPage(self._page)
        self._page.new_tab_requested.connect(self.new_tab_signal.emit)
        self.last_accessed = time.time()
        self.is_sleeping = False
        self.wake_url = None
        # Mouse gestures
        self._gesture_active = False
        self._gesture_pos = None
        self._gesture_done = False

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._gesture_active = True
            self._gesture_pos = event.globalPos()
            self._gesture_done = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._gesture_active:
            self._gesture_active = False
            if self._gesture_pos:
                delta = event.globalPos() - self._gesture_pos
                dx = delta.x()
                dy = delta.y()
                threshold = 40
                
                if abs(dx) > threshold or abs(dy) > threshold:
                    self._gesture_done = True
                    if abs(dx) > abs(dy):
                        if dx > 0 and self.history().canGoForward():
                            self.forward()
                        elif dx < 0 and self.history().canGoBack():
                            self.back()
                    else:
                        if dy > 0:
                            # Asagi kaydir: Yeni sekme
                            self.new_tab_signal.emit(QUrl(newtab_url()))
                        else:
                            # Yukari kaydir: Yenile
                            self.reload()
                    event.accept()
                    return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        if self._gesture_done:
            self._gesture_done = False
            return
        menu = QMenu(self)
        split_act = menu.addAction("Bu sayfayı Yanda Aç (Split View)")
        split_act.triggered.connect(lambda: self.window().open_split_view(self.url()))
        menu.addSeparator()
        back_act = menu.addAction("Geri")
        back_act.triggered.connect(self.back)
        back_act.setEnabled(self.history().canGoBack())
        fwd_act = menu.addAction("İleri")
        fwd_act.triggered.connect(self.forward)
        fwd_act.setEnabled(self.history().canGoForward())
        reload_act = menu.addAction("Yenile")
        reload_act.triggered.connect(self.reload)
        menu.addSeparator()
        src_act = menu.addAction("Sayfa kaynağını görüntüle")
        src_act.triggered.connect(lambda: self.new_tab_signal.emit(QUrl("view-source:" + self.url().toString())))
        menu.exec(event.globalPos())

# ══════════════════════════════════════════════
#  CUSTOM TAB BAR
# ══════════════════════════════════════════════
class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setExpanding(False)
        self.setElideMode(Qt.ElideRight)
        self.setDocumentMode(True)

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        widget = self.parent().widget(index)
        # Firefox tarzı kompakt sabitleme (Sadece ikon sığacak kadar)
        if getattr(widget, 'is_pinned', False):
            return QSize(44, 38)
            
        # Normal sekme genişlik sınırı
        return QSize(200, 38)

    def tabInserted(self, index):
        super().tabInserted(index)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.ArrowCursor)
        close_btn.setToolTip("Sekmeyi kapat")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; border-radius: 5px;
                color: rgba(255, 255, 255, 0.3); font-size: 11px; font-weight: 800; padding: 0;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.8); color: white; }
            QPushButton:pressed { background: #dc2626; color: white; }
        """)
        close_btn.clicked.connect(lambda _, b=close_btn: self._handle_close(b))
        self.setTabButton(index, QTabBar.RightSide, close_btn)

    def _handle_close(self, btn):
        for i in range(self.count()):
            if self.tabButton(i, QTabBar.RightSide) == btn:
                self.tabCloseRequested.emit(i)
                break

# ══════════════════════════════════════════════
#  NATIVE WINDOW CONTROLS (MICRO-UI SIZE)
# ══════════════════════════════════════════════
class NativeWindowButton(QPushButton):
    def __init__(self, btn_type, parent=None):
        super().__init__(parent)
        self.btn_type = btn_type
        # Daha kibar buton boyutları
        self.setFixedSize(36, 28)
        self.setStyleSheet("background: transparent; border: none;")
        self.setCursor(Qt.ArrowCursor)
        _tips = {"minimize": "Simge durumuna küçült", "maximize": "Ekranı kapla", "restore": "Önceki boyut", "close": "Kapat"}
        self.setToolTip(_tips.get(btn_type, ""))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Background hover/click
        if self.isDown():
            painter.fillRect(self.rect(), QColor("#ef4444" if self.btn_type == "close" else "#475569"))
        elif self.underMouse():
            painter.fillRect(self.rect(), QColor("#dc2626" if self.btn_type == "close" else "#334155"))
            
        color = QColor("white" if self.underMouse() and self.btn_type == "close" else "#94a3b8")
        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Draw custom vectors
        cx = self.width() // 2
        cy = self.height() // 2
        
        if self.btn_type == "minimize":
            painter.drawLine(cx - 4, cy, cx + 4, cy)
        elif self.btn_type == "maximize":
            painter.drawRect(cx - 4, cy - 4, 8, 8)
        elif self.btn_type == "restore":
            painter.drawRect(cx - 4, cy - 2, 6, 6)
            painter.drawLine(cx - 2, cy - 4, cx + 4, cy - 4)
            painter.drawLine(cx + 4, cy - 4, cx + 4, cy + 2)
            painter.drawLine(cx + 4, cy - 4, cx + 4, cy - 4) 
        elif self.btn_type == "close":
            painter.setRenderHint(QPainter.Antialiasing, True)
            v = 3
            painter.drawLine(cx - v, cy - v, cx + v, cy + v)
            painter.drawLine(cx + v, cy - v, cx - v, cy + v)

# ── İndirmeler Pop-up Paneli (Firefox Tarzı) ──
class DownloadPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setFixedSize(380, 480)
        self.setObjectName("download_popup")
        
        self.setStyleSheet("""
            QFrame#download_popup {
                background: #1a1c2e; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;
            }
            QLabel#popup_title { font-size: 16px; font-weight: 800; color: #ffffff; padding: 18px 20px; }
            QScrollArea { background: transparent; border: none; }
            QWidget#item_container { background: transparent; }
            
            /* Item Styling */
            QFrame#download_item { background: transparent; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QLabel#file_name { font-size: 13.5px; font-weight: 600; color: #ececf1; }
            QLabel#file_status { font-size: 11px; color: rgba(255,255,255,0.4); }
            
            /* Buttons */
            QPushButton#popup_action {
                background: rgba(255, 255, 255, 0.05); border: none; border-radius: 10px;
                color: #ffffff; padding: 10px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton#popup_action:hover { background: rgba(123, 45, 255, 0.2); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("İndirilenler")
        header.setObjectName("popup_title")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container.setObjectName("item_container")
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setContentsMargins(10, 0, 10, 0)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: rgba(0,0,0,0.1); border-top: 1px solid rgba(255,255,255,0.05);")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(16, 16, 16, 16)
        
        self.btn_clear = QPushButton("Temizle")
        self.btn_clear.setObjectName("popup_action")
        self.btn_more = QPushButton("Daha fazla göster")
        self.btn_more.setObjectName("popup_action")
        
        footer_lay.addWidget(self.btn_clear)
        footer_lay.addStretch()
        footer_lay.addWidget(self.btn_more)
        layout.addWidget(footer)

    def add_item(self, filename, status_text, download_obj=None):
        item = QFrame()
        item.setObjectName("download_item")
        item_lay = QHBoxLayout(item)
        item_lay.setContentsMargins(10, 12, 10, 12)
        
        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet("font-size: 20px; margin-right: 10px;")
        item_lay.addWidget(icon_lbl)
        
        info_lay = QVBoxLayout()
        name_lbl = QLabel(filename)
        name_lbl.setObjectName("file_name")
        status_lbl = QLabel(status_text)
        status_lbl.setObjectName("file_status")
        
        info_lay.addWidget(name_lbl)
        info_lay.addWidget(status_lbl)
        item_lay.addLayout(info_lay)
        item_lay.addStretch()
        
        # Klasörü Aç Butonu
        folder_btn = QPushButton("📁")
        folder_btn.setFixedSize(28, 28)
        folder_btn.setCursor(Qt.PointingHandCursor)
        folder_btn.setStyleSheet("background: transparent; border: none; font-size: 16px;")
        
        if download_obj:
            folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(download_obj.path()))))
        
        item_lay.addWidget(folder_btn)
        
        # Bu item'ı isimlendirelim (ileride güncellemek için)
        item.setProperty("filename", filename)
        item._status_label = status_lbl
        
        self.list_layout.insertWidget(0, item)
        return item

    def update_item_status(self, filename, status_text, color=None):
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget and widget.property("filename") == filename:
                widget._status_label.setText(status_text)
                if color:
                    widget._status_label.setStyleSheet(f"color: {color};")
                break

# ══════════════════════════════════════════════
#  MINY BROWSER — MAIN WINDOW
# ══════════════════════════════════════════════
class MinyBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.history_mgr = HistoryManager()
        self._is_fullscreen = False
        self._zoom_factor = 1.0

        # ── Profiles ──
        self.default_profile = QWebEngineProfile.defaultProfile()
        self.private_profile = QWebEngineProfile(self)  

        for prof in [self.default_profile, self.private_profile]:
            settings = prof.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            
            # --- Performans ve Kaydırma Optimizasyonu ---
            settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            # Zen-style smooth scrolling'in temel motor ayarı (Düzeltildi)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, self.settings.get("scroll_animator", True))
            # Gecikmeyi azaltan ayarlar
            settings.setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)

        # ── AdBlock ──
        self.adblock = AdBlockInterceptor(self)
        self.adblock.enabled = self.settings.get("adblock_enabled", True)
        self.adblock.load_hosts()
        self.default_profile.setUrlRequestInterceptor(self.adblock)

        # ── Downloads ──
        self.downloads_page = DownloadsPage(self)
        self.default_profile.downloadRequested.connect(self.on_download_requested)
        self.private_profile.downloadRequested.connect(self.on_download_requested)

        # ── Window Setup ──
        self.setWindowTitle("Miny Browser")
        self.setWindowIcon(QIcon(ICO_PATH))
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        # Siyah kareleri önlemek için boyama optimizasyonlarını daha stabil hale getir
        self.setAttribute(Qt.WA_OpaquePaintEvent, False) 
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#06010f"))
        self.setPalette(p)

        # ── Central Widget ──
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── Title Bar ──
        self._build_title_bar()

        # ── Toolbar ──
        self._build_toolbar()

        # ── Progress Bar ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # ── Splitter Base ──
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # ── Left Pane (Main Tabs) ──
        self.left_pane = QWidget()
        self.left_lay = QVBoxLayout(self.left_pane)
        self.left_lay.setContentsMargins(0, 0, 0, 0)
        self.left_lay.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabBar(CustomTabBar())
        self.tabs.setTabsClosable(True)

        # + (Yeni Sekme) Butonunu Sekmelerin En Sağına Taşı
        self.btn_new_tab = QToolButton()
        self.btn_new_tab.setText("+")
        self.btn_new_tab.setToolTip("Yeni Sekme (Ctrl+T)")
        self.btn_new_tab.setFixedSize(36, 30)
        self.btn_new_tab.setCursor(Qt.PointingHandCursor)
        self.btn_new_tab.setStyleSheet("""
            QToolButton { 
                background: rgba(255, 255, 255, 0.04); 
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-radius: 8px; 
                color: rgba(255, 255, 255, 0.5); 
                font-size: 22px; 
                font-weight: 300; 
                margin-right: 15px;
                padding-bottom: 2px;
            }
            QToolButton:hover { 
                background: rgba(123, 45, 255, 0.1); 
                border-color: #7b2dff; 
                color: #ffffff;
            }
            QToolButton:pressed {
                background: #7b2dff;
                color: white;
            }
        """)
        self.btn_new_tab.clicked.connect(lambda: self.add_tab())
        self.tabs.setCornerWidget(self.btn_new_tab, Qt.TopRightCorner) # En sağa sabitle

        # İndirmeler Paneli (Download Popup)
        self.download_popup = DownloadPopup(self)
        self.download_popup.hide()
        self.download_popup.btn_more.clicked.connect(self._show_downloads_page)
        self.download_popup.btn_clear.clicked.connect(self._clear_downloads_popup)

        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.left_lay.addWidget(self.tabs)

        self.find_bar = FindBar()
        self.left_lay.addWidget(self.find_bar)
        
        self.main_splitter.addWidget(self.left_pane)

        # ── Right Pane (Split View) ──
        self.right_pane = QWidget()
        self.right_pane.setVisible(False)
        self.right_lay = QVBoxLayout(self.right_pane)
        self.right_lay.setContentsMargins(0, 0, 0, 0)
        self.right_lay.setSpacing(0)

        right_header = QWidget()
        right_header.setStyleSheet("background: #1e293b; border-bottom: 1px solid rgba(255,255,255,0.1); border-left: 1px solid rgba(255,255,255,0.1);")
        right_header_lay = QHBoxLayout(right_header)
        right_header_lay.setContentsMargins(8, 4, 8, 4)

        self.right_url = QLineEdit()
        self.right_url.setStyleSheet("background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px; color: #94a3b8;")
        self.right_url.returnPressed.connect(lambda: self.right_view.load(QUrl.fromUserInput(self.right_url.text())))
        right_header_lay.addWidget(self.right_url)

        right_close = QToolButton()
        right_close.setText("✕")
        right_close.setStyleSheet("background:transparent; color:#ef4444; font-weight:bold; font-size:12px; border:none;")
        right_close.clicked.connect(lambda: self.right_pane.setVisible(False))
        right_header_lay.addWidget(right_close)

        self.right_lay.addWidget(right_header)
        self.right_view = BrowserView(self.default_profile)
        self.right_view.urlChanged.connect(lambda u: self.right_url.setText(u.toString()))
        self.right_lay.addWidget(self.right_view)
        
        self.main_splitter.addWidget(self.right_pane)
        self.main_splitter.setSizes([800, 400])

        # ── Keyboard Shortcuts ──
        self._setup_shortcuts()

        # ── Restore session or open new tab ──
        self._restore_session()

        # ── Drag ──
        self._drag_pos = None

        # ── Memory Saver Timer ──
        self._mem_timer = QTimer(self)
        self._mem_timer.timeout.connect(self._check_memory_saver)
        self._mem_timer.start(60000)

    def _toggle_downloads_popup(self):
        if self.download_popup.isVisible():
            self.download_popup.hide()
        else:
            # Butonun tam altına hizala
            btn_pos = self.btn_downloads.mapToGlobal(QPoint(0, 0))
            self.download_popup.move(btn_pos.x() - self.download_popup.width() + self.btn_downloads.width(), 
                                    btn_pos.y() + self.btn_downloads.height() + 10)
            self.download_popup.show()
            self.download_popup.raise_()

    def _show_downloads_page(self):
        self.download_popup.hide()
        self.add_tab("internal://downloads")

    def _clear_downloads_popup(self):
        while self.download_popup.list_layout.count():
            item = self.download_popup.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_download_requested(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", download.suggestedFileName())
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()
            
            filename = os.path.basename(path)
            # Pop-up'a ekle ve objeyi bağla
            self.download_popup.add_item(filename, "İndirme başlatıldı...", download)
            
            # Canlı İlerleme Takibi
            download.downloadProgress.connect(
                lambda received, total, fn=filename: self.download_popup.update_item_status(
                    fn, f"%{(received/total)*100:.1f} indirildi - {(received/1024/1024):.1f}MB" if total > 0 else "İndiriliyor..."
                )
            )
            
            download.finished.connect(lambda fn=filename: self.download_popup.update_item_status(fn, "İndirme tamamlandı", "#4ade80"))
            
            # Hata/İptal Takibi
            download.stateChanged.connect(
                lambda state, fn=filename: self._on_download_state_changed(state, fn)
            )

    def _on_download_state_changed(self, state, filename):
        if state == QWebEngineDownloadRequest.DownloadCancelled:
            self.download_popup.update_item_status(filename, "İptal Edildi", "#f87171")
        elif state == QWebEngineDownloadRequest.DownloadInterrupted:
            self.download_popup.update_item_status(filename, "Hata Oluştu", "#f87171")

    # ────────────────────────────────────
    #  TITLE BAR (Frameless)
    # ────────────────────────────────────
    def _build_title_bar(self):
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(34)
        self._title_bar.setStyleSheet("background: #06010f;")
        self._title_bar.installEventFilter(self)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        self._title_bar.setLayout(layout)

        # Title icon
        logo_label = QLabel()
        logo_path = os.path.join(BASE_DIR, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        
        layout.addWidget(logo_label)
        layout.addStretch()

        # Window controls
        self.btn_min = NativeWindowButton("minimize")
        self.btn_max = NativeWindowButton("maximize")
        self.btn_close = NativeWindowButton("close")
        
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            layout.addWidget(btn)

        self.main_layout.addWidget(self._title_bar)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.btn_type = "maximize"
        else:
            self.showMaximized()
            self.btn_max.btn_type = "restore"
        self.btn_max.update()
            
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMaximized():
                self.btn_max.btn_type = "restore"
            else:
                self.btn_max.btn_type = "maximize"
            self.btn_max.update()
        super().changeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self._title_bar:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            elif event.type() == QEvent.MouseMove and self._drag_pos:
                if self.isMaximized():
                    self.showNormal()
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._drag_pos = None
                return True
            elif event.type() == QEvent.MouseButtonDblClick:
                self._toggle_maximize()
                return True
        return super().eventFilter(obj, event)

    # ────────────────────────────────────
    #  TOOLBAR
    # ────────────────────────────────────
    def _build_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20)) # Daha büyük, kaliteli ikonlar
        self.main_layout.addWidget(toolbar)

        _fallback = {"back.svg": "❮", "forward.svg": "❯", "reload.svg": "⟳", "star.svg": "★"}

        def make_btn(icon_name, tooltip, callback):
            btn = QToolButton()
            icon_full_path = resource_path(icon_name)
            if os.path.exists(icon_full_path):
                btn.setIcon(QIcon(icon_full_path))
                if btn.icon().isNull():
                    btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
                    btn.setText(_fallback.get(icon_name, tooltip[0]))
                    btn.setStyleSheet("QToolButton { font-family: 'Segoe UI Symbol', sans-serif; font-size: 18px; font-weight: 800; color: #E4E4E7; min-width: 28px; min-height: 28px; padding: 2px; padding-bottom: 4px; }")
            else:
                btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
                btn.setText(_fallback.get(icon_name, tooltip[0]))
                btn.setStyleSheet("QToolButton { font-family: 'Segoe UI Symbol', sans-serif; font-size: 18px; font-weight: 800; color: #E4E4E7; min-width: 28px; min-height: 28px; padding: 2px; padding-bottom: 4px; }")
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            toolbar.addWidget(btn)
            return btn

        # Sol Butonlar
        self.btn_back = make_btn("back.svg", "Geri", self._nav_back)
        self.btn_forward = make_btn("forward.svg", "İleri", self._nav_forward)
        self.btn_reload = make_btn("reload.svg", "Yenile", self._nav_reload)

        # Esnek Boşluk (Sola yaslama)
        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer_left)

        # Ortalanmış SSL ve URL Çubuğu
        url_container = QWidget()
        url_container.setFixedWidth(700) # Kusursuz merkezleme için sabit genişlik
        url_lay = QHBoxLayout(url_container)
        url_lay.setContentsMargins(0, 0, 0, 0)
        url_lay.setSpacing(6)

        self.ssl_icon = QLabel("")
        self.ssl_icon.setFixedWidth(24)
        self.ssl_icon.setAlignment(Qt.AlignCenter)
        url_lay.addWidget(self.ssl_icon)

        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("url_bar")
        self.url_bar.setPlaceholderText("Arama yapın veya bir adres yazın...")
        self.url_bar.returnPressed.connect(self._navigate_to_url)
        
        # Yıldız (Yer imi) ikonunu URL çubuğunun direkt içine (sonuna) ekleme
        star_icon = QIcon(resource_path("star.svg"))
        star_action = self.url_bar.addAction(star_icon, QLineEdit.TrailingPosition)
        star_action.triggered.connect(self._toggle_bookmark)

        url_lay.addWidget(self.url_bar)
        toolbar.addWidget(url_container)

        # Esnek Boşluk (Sağa yaslama)
        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer_right)

        # İndirmeler Butonu (Görseldeki profesyonel SVG ikon ile)
        self.btn_downloads = QToolButton()
        self.btn_downloads.setToolTip("İndirilenler (Ctrl+J)")
        self.btn_downloads.setCursor(Qt.PointingHandCursor)
        
        # SVG İkon Tanımı
        def create_download_icon(color):
            svg_str = f"""
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            """
            from PySide6.QtGui import QPixmap, QPainter
            from PySide6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(svg_str.encode('utf-8'))
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)

        self.btn_downloads.setIcon(create_download_icon("#E4E4E7"))
        self.btn_downloads.setIconSize(QSize(20, 20))
        
        self.btn_downloads.setStyleSheet("""
            QToolButton { 
                background: transparent; border-radius: 8px;
                min-width: 34px; min-height: 34px;
            }
            QToolButton:hover { 
                background: rgba(255, 255, 255, 0.08); 
            }
        """)
        
        # Üzerine gelince ikonun mor olması için basit bir logic ekleyelim
        self.btn_downloads.installEventFilter(self) # Re-use window as filter if needed or keep it simple
        self.btn_downloads.clicked.connect(self._toggle_downloads_popup)
        toolbar.addWidget(self.btn_downloads)

        # Menü Butonu
        btn_menu = QToolButton()
        btn_menu.setText("⋮")
        btn_menu.setToolTip("Menü")
        btn_menu.setStyleSheet("""
            QToolButton { font-size: 22px; font-weight: 800; color: #E4E4E7; padding-bottom: 3px; min-width: 32px; min-height: 32px; }
            QToolButton::menu-indicator { image: none; }
        """)
        btn_menu.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(btn_menu)
        menu.addAction("İndirmeler\tCtrl+J", self._show_downloads)
        menu.addAction("Yer İmleri\tCtrl+B", self._show_bookmarks)
        menu.addAction("Geçmiş\tCtrl+H", self._show_history)
        menu.addSeparator()
        menu.addAction("Sayfada Ara\tCtrl+F", self._toggle_find)
        menu.addAction("Yazdır\tCtrl+P", self._print_page)
        menu.addSeparator()
        menu.addAction("Gizli Sekme\tCtrl+Shift+N", self._new_private_tab)
        menu.addAction("Tam Ekran\tF11", self._toggle_fullscreen)
        menu.addSeparator()
        menu.addAction("Ayarlar", self._show_settings)
        menu.addAction("Hakkında", self._show_about)
        btn_menu.setMenu(menu)
        toolbar.addWidget(btn_menu)

    # ────────────────────────────────────
    #  TAB MANAGEMENT
    # ────────────────────────────────────
    def add_tab(self, url=None, label="Yeni Sekme", is_private=False):
        profile = self.private_profile if is_private else self.default_profile
        view = BrowserView(profile, self)
        view.is_private = is_private
        view.is_pinned = False
        
        view.loadStarted.connect(lambda: self.progress_bar.setVisible(True))
        view.loadProgress.connect(self.progress_bar.setValue)
        view.loadFinished.connect(self._on_load_finished)
        view.urlChanged.connect(lambda u: self._update_url_bar(u, view))
        view.titleChanged.connect(lambda t: self._update_tab_title(t, view))
        view.iconChanged.connect(lambda i: self._update_tab_icon(i, view))
        view.new_tab_signal.connect(self.add_tab)

        if not url:
            label = "Gizli Sekme" if is_private else "Yeni Sekme"

        idx = self.tabs.addTab(view, label)
        self.tabs.setCurrentIndex(idx)
        
        if url:
            if isinstance(url, str):
                url = QUrl(url)
            view.load(url)
        else:
            view.load(QUrl(newtab_url(self.settings, is_private)))

        if not url or "newtab.html" in view.url().toString():
            self.url_bar.setFocus()
            self.url_bar.selectAll()

        return view

    def _open_internal_tab(self, widget, label, internal_url):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if getattr(w, 'internal_url', None) == internal_url:
                self.tabs.setCurrentIndex(i)
                return
        idx = self.tabs.addTab(widget, label)
        self.tabs.setCurrentIndex(idx)
        self._update_url_bar(widget.url(), widget)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            view = self.tabs.widget(index)
            self.tabs.removeTab(index)
            if not isinstance(view, InternalPage):
                view.deleteLater()
            elif getattr(view, 'internal_url', None) == 'ayarlar':
                view.deleteLater()
        else:
            self.tabs.currentWidget().load(QUrl(newtab_url(self.settings)))

    def _show_tab_context_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx == -1: return
        menu = QMenu(self)
        
        menu.addAction("Yeni Sekme Aç", lambda: self.add_tab())
        
        is_pinned = getattr(self.tabs.widget(idx), 'is_pinned', False)
        pin_text = "Sekmeyi Sabitlemeyi Kaldır" if is_pinned else "Sekmeyi Sabitle"
        menu.addAction(pin_text, lambda: self.toggle_pin_tab(idx))
        
        menu.addSeparator()
        
        menu.addAction("Yenile", lambda: self.tabs.widget(idx).reload() if hasattr(self.tabs.widget(idx), 'reload') else None)
        menu.addAction("Sekmeyi Çoğalt", lambda: self.add_tab(self.tabs.widget(idx).url().toString()) if hasattr(self.tabs.widget(idx), 'url') else None)
        
        menu.addSeparator()
        menu.addAction("Sekmeyi Kapat", lambda: self.close_tab(idx))
        
        def _close_others():
            for i in range(self.tabs.count()-1, -1, -1):
                if i != idx: self.close_tab(i)
        menu.addAction("Diğer Sekmeleri Kapat", _close_others)
        
        def _close_right():
            for i in range(self.tabs.count()-1, idx, -1):
                self.close_tab(i)
        menu.addAction("Sağdaki Sekmeleri Kapat", _close_right)
        
        menu.exec(self.tabs.mapToGlobal(pos))

    def toggle_pin_tab(self, index):
        view = self.tabs.widget(index)
        if not hasattr(view, 'is_pinned'): view.is_pinned = False
        
        view.is_pinned = not view.is_pinned
        
        if view.is_pinned:
            # Sabitlenenlerin yanına (en başa) taşı
            pinned_count = 0
            for i in range(self.tabs.count()):
                if getattr(self.tabs.widget(i), 'is_pinned', False) and i != index:
                    pinned_count += 1
            
            self.tabs.tabBar().moveTab(index, pinned_count)
            self.tabs.setTabText(pinned_count, "") # Yazıyı gizle
            self.tabs.tabBar().setTabButton(pinned_count, QTabBar.RightSide, None) # Kapatma butonunu kaldır
        else:
            # Sabitlemeyi kaldırınca eski kimliğine döner
            self.tabs.setTabText(index, view.title() if hasattr(view, 'title') else "Sekme")
            
            # Kapatma butonunu geri getir
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(18, 18)
            close_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 5px; color: rgba(255, 255, 255, 0.3); font-size: 11px; font-weight: 800; }
                QPushButton:hover { background: rgba(239, 68, 68, 0.8); color: white; }
            """)
            close_btn.clicked.connect(lambda _, b=close_btn: self.tabs.tabBar()._handle_close(b))
            self.tabs.tabBar().setTabButton(index, QTabBar.RightSide, close_btn)

        self.tabs.tabBar().updateGeometry()

    def _on_tab_changed(self, index):
        view = self.tabs.widget(index)
        if view:
            if getattr(view, 'is_sleeping', False):
                view.is_sleeping = False
                view.load(view.wake_url)
            
            if hasattr(view, 'last_accessed'):
                view.last_accessed = time.time()

            self._update_url_bar(view.url(), view)
            self.setWindowTitle(f"{view.title()} — Miny Browser")
            if hasattr(view, 'page') and view.page() is not None:
                self.find_bar.set_browser(view)
                # self._update_zoom_label()
            else:
                self.find_bar.close_bar()
            # self._update_ssl_indicator(view.url())
            self._update_nav_buttons()

    def _check_memory_saver(self):
        curr_view = self.tabs.currentWidget()
        now = time.time()
        for i in range(self.tabs.count()):
            v = self.tabs.widget(i)
            if hasattr(v, 'last_accessed') and v != curr_view and not getattr(v, 'is_sleeping', False):
                # 5 dakika sonra uykuya al (Görsel glitchleri önlemek için daha stabil süre)
                if now - v.last_accessed > 300: 
                    v.is_sleeping = True
                    v.wake_url = v.url()
                    v.setHtml("<style>body{background:#09090b;color:#a1a1aa;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;margin:0;} h2{font-weight:500;font-size:18px;}</style><body><h2>Sekme uykuya alındı. Uyanmak için tıklayın.</h2></body>")
                    self.tabs.setTabText(i, "💤 " + self.tabs.tabText(i))

    def open_split_view(self, url):
        self.right_pane.setVisible(True)
        self.right_view.load(url)
        self.main_splitter.setSizes([self.width() // 2, self.width() // 2])

    def _on_load_finished(self, ok):
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        view = self.sender()
        if view:
            self.history_mgr.add(view.url().toString(), view.title())
            self._update_nav_buttons()
            # self._update_ssl_indicator(view.url())

    # ────────────────────────────────────
    #  NAVIGATION & URL
    # ────────────────────────────────────
    def _navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text: return

        if "." in text and " " not in text:
            if not text.startswith(("http://", "https://", "ftp://", "file://", "view-source:")):
                text = "https://" + text
            url = QUrl(text)
        else:
            engine = self.settings.get("search_engine", "Google")
            if engine == "DuckDuckGo":
                url = QUrl(f"https://duckduckgo.com/?q={text}")
            elif engine == "Bing":
                url = QUrl(f"https://www.bing.com/search?q={text}")
            else:
                url = QUrl(f"https://www.google.com/search?q={text}")

        self.tabs.currentWidget().load(url)

    def _update_url_bar(self, url, view=None):
        if view == self.tabs.currentWidget():
            u_str = url.toString()
            if "newtab.html" in u_str:
                self.url_bar.setText("")
            else:
                self.url_bar.setText(u_str)
            self.url_bar.setCursorPosition(0)
            # self._update_ssl_indicator(url)
            self._update_nav_buttons()
            
            is_priv = getattr(view, 'is_private', False)
            self.url_bar.setProperty("is_private", is_priv)
            self.url_bar.style().unpolish(self.url_bar)
            self.url_bar.style().polish(self.url_bar)

    def _update_ssl_indicator(self, url):
        if url.scheme() == "https":
            self.ssl_icon.setText("")
            self.ssl_icon.setStyleSheet("font-size: 11px; padding: 0; color: #22c55e;")
            # self.ssl_status.setText("Güvenli Bağlantı")
        elif url.scheme() in ("http", "ftp"):
            self.ssl_icon.setText("")
            self.ssl_icon.setStyleSheet("font-size: 11px; padding: 0; color: #f59e0b;")
            # self.ssl_status.setText("Güvenli Değil")
        else:
            self.ssl_icon.setText("")

    def _update_tab_title(self, title, view):
        idx = self.tabs.indexOf(view)
        if idx != -1:
            if not title: title = "Yükleniyor..."
            # Clean up sleep icon if awake
            if not getattr(view, 'is_sleeping', False) and title.startswith("💤 "):
                title = title[3:]

            # Sabitlenmişse başlığı güncelleme (Sadece logo kalsın)
            if not getattr(view, 'is_pinned', False):
                self.tabs.setTabText(idx, title)
            else:
                self.tabs.setTabText(idx, "")
            
            self.tabs.setTabToolTip(idx, title)
            if view == self.tabs.currentWidget():
                if getattr(view, 'is_private', False):
                    self.setWindowTitle(f"{title} — Miny Browser (Gizli Mod)")
                else:
                    self.setWindowTitle(f"{title} — Miny Browser")

    def _update_tab_icon(self, icon, view):
        idx = self.tabs.indexOf(view)
        if idx != -1:
            self.tabs.setTabIcon(idx, icon)

    def _update_nav_buttons(self):
        view = self.tabs.currentWidget()
        if view:
            self.btn_back.setEnabled(view.history().canGoBack())
            self.btn_forward.setEnabled(view.history().canGoForward())

    def _nav_back(self): self.tabs.currentWidget().back()
    def _nav_forward(self): self.tabs.currentWidget().forward()
    def _nav_reload(self): self.tabs.currentWidget().reload()
    def _go_home(self): self.tabs.currentWidget().load(QUrl(newtab_url(self.settings)))

    # ────────────────────────────────────
    #  FEATURES & DIALOGS
    # ────────────────────────────────────
    def _toggle_bookmark(self):
        view = self.tabs.currentWidget()
        url = view.url().toString()
        title = view.title()
        marks = load_json(BOOKMARKS_FILE, [])
        exists = False
        for m in marks:
            if m['url'] == url:
                exists = True
                marks.remove(m)
                break
        if not exists:
            marks.append({"url": url, "title": title})
        save_json(BOOKMARKS_FILE, marks)

    def _on_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", download.downloadFileName())
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()
            
    def _show_downloads(self): 
        self._open_internal_tab(self.downloads_page, "İndirmeler", "indirmeler")
    
    def _show_bookmarks(self):
        marks = load_json(BOOKMARKS_FILE, [])
        page = InternalPage("Yer İmleri", "yerimleri", self)
        lst = QListWidget()
        for m in marks:
            title = m.get('title', 'İsimsiz')
            url = m.get('url', '')
            it = QListWidgetItem(f"☆  {title}\n   {url}")
            lst.addItem(it)
        lst.itemDoubleClicked.connect(lambda i: [self.add_tab(i.text().split('\n')[1].strip()), self.close_tab(self.tabs.indexOf(page))])
        page.content_lay.addWidget(lst)
        self._open_internal_tab(page, "Yer İmleri", "yerimleri")

    def _show_history(self):
        h = self.history_mgr.entries
        page = InternalPage("Tarama Geçmişi", "gecmis", self)
        lst = QListWidget()
        for e in h:
            it = QListWidgetItem(f"[{e['time']}] {e['title']}\n   {e['url']}")
            lst.addItem(it)
        lst.itemDoubleClicked.connect(lambda i: [self.add_tab(i.text().split('\n')[1].split(']')[-1].strip()), self.close_tab(self.tabs.indexOf(page))])
        page.content_lay.addWidget(lst)
        
        btn_clr = QPushButton("Tüm Geçmişi Temizle")
        btn_clr.setObjectName("danger_btn")
        btn_clr.clicked.connect(lambda: [self.history_mgr.clear(), lst.clear()])
        
        btn_wrap = QWidget()
        btn_lay = QHBoxLayout(btn_wrap)
        btn_lay.setContentsMargins(12, 4, 12, 12)
        btn_lay.addStretch()
        btn_lay.addWidget(btn_clr)
        page.content_lay.addWidget(btn_wrap)
        
        self._open_internal_tab(page, "Geçmiş", "gecmis")

    def _toggle_find(self): self.find_bar.open_bar()
    def _print_page(self): self.tabs.currentWidget().page().printToPdf(f"print_{int(datetime.datetime.now().timestamp())}.pdf")
    def _new_private_tab(self): self.add_tab(is_private=True)
    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._title_bar.setVisible(True)
        else:
            self.showFullScreen()
            self._title_bar.setVisible(False)
        self._is_fullscreen = not self._is_fullscreen

    def _show_settings(self):
        MODERN_SETTINGS_QSS = """
            QWidget#settings_page { background: #05060e; }
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 4px; background: transparent; }
            QScrollBar::handle:vertical { background: #5e20ff; border-radius: 2px; }
            
            /* Sidebar Navigation (Görseldeki gibi sade) */
            QListWidget#settings_sidebar {
                background: transparent; border: none;
                padding: 60px 40px; outline: 0;
            }
            QListWidget#settings_sidebar::item {
                padding: 10px 16px; border-radius: 8px; margin-bottom: 6px;
                color: #9fa1b5; font-size: 14px; font-weight: 500;
            }
            QListWidget#settings_sidebar::item:hover { color: #ffffff; }
            QListWidget#settings_sidebar::item:selected {
                background: transparent; color: #5e20ff;
                font-weight: 700;
            }
            
            /* Section Headers (Görseldeki Breadcrumb tarzı) */
            QLabel#card_title {
                font-size: 13px; font-weight: 700; color: #5e20ff;
                padding: 0px 0px 12px 10px;
            }
            
            /* Opera Style Dedicated Card */
            QFrame#setting_card {
                background: #1a1c2e; border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px; margin-bottom: 50px;
            }
            
            /* Setting Rows */
            QFrame#setting_row {
                background: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QLabel#setting_title { font-size: 15px; font-weight: 500; color: #ececf1; }
            QLabel#setting_desc { font-size: 13px; color: #9fa1b5; }
            
            /* Chrome/Opera Style Pill Controls */
            QComboBox, QSpinBox, QLineEdit {
                background: #0f101d; border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px; padding: 6px 12px; color: #ffffff;
            }
            QLineEdit#settings_search {
                background: #0f101d; border-radius: 18px; padding: 8px 24px; color: #ffffff;
            }
            
            QPushButton { 
                padding: 10px 32px; font-weight: 600; font-size: 13px;
                background: #5e20ff; color: #ffffff; border: none; border-radius: 20px;
            }
            QPushButton:hover { background: #713aff; }
            QPushButton#danger_btn { background: transparent; color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
            QPushButton#danger_btn:hover { background: #ef4444; color: #ffffff; }
            
            /* Custom Switch (Pill Toggle) */
            QCheckBox::indicator { width: 38px; height: 18px; border-radius: 9px; background: #35384d; }
            QCheckBox::indicator:checked { background: #5e20ff; }
        """
        page = InternalPage("Ayarlar", "ayarlar", self)
        page.setObjectName("settings_page")
        page.setStyleSheet(MODERN_SETTINGS_QSS)

        # Clear layout to use absolute horizontal flex
        for i in reversed(range(page.base_lay.count())): 
            item = page.base_lay.itemAt(i)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                for j in reversed(range(item.layout().count())):
                    w = item.layout().itemAt(j).widget()
                    if w: w.deleteLater()
            page.base_lay.removeItem(item)
        page.base_lay.setContentsMargins(0, 0, 0, 0)

        main_lay = QHBoxLayout()
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container.setStyleSheet("background: transparent;")
        sidebar_lay = QVBoxLayout(sidebar_container)
        sidebar_lay.setContentsMargins(0, 0, 0, 0)
        
        lbl_brand = QLabel(" AYARLAR")
        lbl_brand.setStyleSheet("font-size: 10px; font-weight: 800; color: rgba(255, 255, 255, 0.15); padding-left: 56px; margin-top: 50px; margin-bottom: 10px; letter-spacing: 2px;")
        sidebar_lay.addWidget(lbl_brand)
        
        sidebar = QListWidget()
        sidebar.setObjectName("settings_sidebar")
        categories = ["Genel", "Gizlilik ve Güvenlik", "Görünüm", "Performans ve Sistem", "Gelişmiş"]
        sidebar.addItems(categories)
        sidebar_lay.addWidget(sidebar)
        main_lay.addWidget(sidebar_container)

        # Content Main Setup
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_container = QWidget()
        content_lay = QVBoxLayout(content_container)
        content_lay.setContentsMargins(120, 80, 160, 100)
        content_lay.setSpacing(0)
        content_lay.setAlignment(Qt.AlignTop)
        
        # Search Bar
        search_box = QLineEdit()
        search_box.setObjectName("settings_search")
        search_box.setPlaceholderText("Ayarlarda ara")
        search_box.setFixedWidth(260)
        search_lay = QHBoxLayout()
        search_lay.addStretch()
        search_lay.addWidget(search_box)
        content_lay.addLayout(search_lay)
        content_lay.addSpacing(30)

        cards_data = [] 
        all_rows = []
        
        def auto_save(key, value):
            self.settings[key] = value
            save_settings(self.settings)

        def create_card(title):
            card = QFrame()
            card.setObjectName("setting_card")
            card.setFixedWidth(750) # Opera tarzı sabit ve dengeli genişlik
            lay = QVBoxLayout(card)
            lay.setContentsMargins(0, 10, 0, 10)
            lay.setSpacing(0)
            lbl = QLabel(title)
            lbl.setObjectName("card_title")
            lay.addWidget(lbl)
            content_lay.addWidget(card)
            cards_data.append(card)
            return lay

        def create_row(card_lay, title, description, widget):
            row = QFrame()
            row.setObjectName("setting_row")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(24, 22, 24, 22)
            text_lay = QVBoxLayout()
            text_lay.setSpacing(4)
            lbl_title = QLabel(title)
            lbl_title.setObjectName("setting_title")
            text_lay.addWidget(lbl_title)
            if description:
                lbl_desc = QLabel(description)
                lbl_desc.setObjectName("setting_desc")
                lbl_desc.setWordWrap(True)
                text_lay.addWidget(lbl_desc)
            row_lay.addLayout(text_lay, 1)
            row_lay.addWidget(widget)
            card_lay.addWidget(row)
            all_rows.append((row, title.lower() + " " + description.lower(), card_lay.parentWidget()))
            return row

        # 1. Genel
        c1 = create_card("Genel")
        engine_combo = QComboBox()
        engine_combo.addItems(["Google", "DuckDuckGo", "Bing", "Yandex"])
        engine_combo.setCurrentText(self.settings.get("search_engine", "Google"))
        engine_combo.currentTextChanged.connect(lambda v: auto_save("search_engine", v))
        create_row(c1, "Arama Motoru", "Varsayılan arama motorunuzu seçin.", engine_combo)

        lang_combo = QComboBox()
        lang_combo.addItems(["tr", "en", "de", "fr"])
        lang_combo.setCurrentText(self.settings.get("language", "tr"))
        lang_combo.currentTextChanged.connect(lambda v: auto_save("language", v))
        create_row(c1, "Arayüz Dili", "Tarayıcının iletişim dili.", lang_combo)

        restore_check = QCheckBox()
        restore_check.setChecked(self.settings.get("restore_session", True))
        restore_check.toggled.connect(lambda v: auto_save("restore_session", v))
        create_row(c1, "Başlangıçta Oturumu Koru", "Tarayıcı kapatıldığında açık olan sekmeleri korur.", restore_check)

        home_combo = QComboBox()
        home_combo.addItems(["newtab", "custom"])
        home_combo.setCurrentText(self.settings.get("homepage", "newtab"))
        home_combo.currentTextChanged.connect(lambda v: auto_save("homepage", v))
        create_row(c1, "Ana Sayfa Türü", "Yeni sekme açıldığında gösterilecek başlangıç ekranı.", home_combo)

        home_edit = QLineEdit()
        home_edit.setPlaceholderText("Örn: https://google.com")
        home_edit.setText(self.settings.get("custom_homepage", ""))
        home_edit.textChanged.connect(lambda v: auto_save("custom_homepage", v))
        create_row(c1, "Özel Ana Sayfa", "Özel bir URL seçtiyseniz buraya sayfa linkini girin.", home_edit)

        btn_dl_path = QPushButton("Klasör Seç")
        dl_widget = QWidget()
        dl_lay = QHBoxLayout(dl_widget)
        dl_lay.setContentsMargins(0,0,0,0)
        dl_path_edit = QLineEdit()
        dl_path_edit.setText(self.settings.get("download_path", ""))
        dl_path_edit.textChanged.connect(lambda v: auto_save("download_path", v))
        def _choose_dl_dir():
            d = QFileDialog.getExistingDirectory(self, "İndirme Klasörü Seç")
            if d: dl_path_edit.setText(d)
        btn_dl_path.clicked.connect(_choose_dl_dir)
        dl_lay.addWidget(dl_path_edit)
        dl_lay.addWidget(btn_dl_path)
        create_row(c1, "İndirme Konumu", "Dosyaların otomatik kaydedileceği cihaz konumu.", dl_widget)

        # 2. Gizlilik ve Güvenlik
        c2 = create_card("Gizlilik ve Güvenlik")
        adblock_check = QCheckBox()
        adblock_check.setChecked(self.settings.get("adblock_enabled", True))
        adblock_check.toggled.connect(lambda v: [auto_save("adblock_enabled", v), setattr(self.adblock, 'enabled', v)])
        create_row(c2, "Reklam Engelleyici", "Reklamları ve zararlı izleyicileri engeller.", adblock_check)

        dnt_check = QCheckBox()
        dnt_check.setChecked(self.settings.get("do_not_track", False))
        dnt_check.toggled.connect(lambda v: auto_save("do_not_track", v))
        create_row(c2, "Do Not Track (Beni İzleme)", "Tarama verilerinizin izlenmemesi için sitelere Header isteği yollar.", dnt_check)

        webrtc_check = QCheckBox()
        webrtc_check.setChecked(self.settings.get("webrtc_enabled", True))
        webrtc_check.toggled.connect(lambda v: auto_save("webrtc_enabled", v))
        create_row(c2, "WebRTC Paylaşımı", "IP sızıntısını engeller. Tam gizlilik için aktif tutulmalıdır.", webrtc_check)

        auto_clear_check = QCheckBox()
        auto_clear_check.setChecked(self.settings.get("auto_clear_history", False))
        auto_clear_check.toggled.connect(lambda v: auto_save("auto_clear_history", v))
        create_row(c2, "Çıkışta Geçmişi Temizle", "Tarayıcı her kapatıldığında geçmişi tamamen siler.", auto_clear_check)

        btn_clear_history = QPushButton("Geçmişi Temizle")
        btn_clear_history.clicked.connect(lambda: [self.history_mgr.clear(), btn_clear_history.setText("Temizlendi")])
        create_row(c2, "Tarama Geçmişi", "Şu ana kadar kaydedilmiş tüm geçmiş kayıtlarını anında sil.", btn_clear_history)

        # 3. Görünüm
        c3 = create_card("Görünüm")
        zoom_spin = QSpinBox()
        zoom_spin.setRange(25, 500)
        zoom_spin.setSuffix("%")
        zoom_spin.setSingleStep(10)
        zoom_spin.setValue(self.settings.get("default_zoom", 100))
        def zoom_changed(v):
            auto_save("default_zoom", v)
            self._zoom_factor = v / 100.0
            self._apply_zoom()
        zoom_spin.valueChanged.connect(zoom_changed)
        create_row(c3, "Yakınlaştırma", "Siteler için varsayılan büyüklük seviyesi.", zoom_spin)
        
        font_spin = QSpinBox()
        font_spin.setRange(10, 36)
        font_spin.setValue(self.settings.get("font_size", 16))
        font_spin.valueChanged.connect(lambda v: auto_save("font_size", v))
        create_row(c3, "Yazı Tipi Boyutu", "Sitelerdeki standart metin boyutu.", font_spin)

        smooth_check = QCheckBox()
        smooth_check.setChecked(self.settings.get("smooth_scrolling", True))
        smooth_check.toggled.connect(lambda v: auto_save("smooth_scrolling", v))
        create_row(c3, "Pürüzsüz Kaydırma", "Fare tekerleği ile sitelerde Opera tarzı akıcı kaydırma sağlar.", smooth_check)

        # 4. Performans ve Sistem
        c4 = create_card("Performans ve Sistem")
        hw_accel_check = QCheckBox()
        hw_accel_check.setChecked(self.settings.get("hardware_acceleration", True))
        hw_accel_check.toggled.connect(lambda v: auto_save("hardware_acceleration", v))
        create_row(c4, "Donanım Hızlandırma", "Optimum hız ve video kalitesi için ekran kartını devrede tutar.", hw_accel_check)

        memory_saver_check = QCheckBox()
        memory_saver_check.setChecked(True)
        create_row(c4, "Bellek Tasarrufu", "Kullanılmayan sekmeleri otomatik uykuya alıp belleği ferahlatır.", memory_saver_check)

        # 5. Gelişmiş
        c5 = create_card("Gelişmiş Seçenekler")
        proxy_edit = QLineEdit()
        proxy_edit.setPlaceholderText("Örn: http://proxy.sunucu:8080")
        proxy_edit.setText(self.settings.get("proxy", ""))
        proxy_edit.textChanged.connect(lambda v: auto_save("proxy", v))
        create_row(c5, "Proxy Sunucusu", "Ağ bağlantılarınızı bu proxy sunucusu üzerinden tüneller.", proxy_edit)

        ua_edit = QLineEdit()
        ua_edit.setPlaceholderText("Varsayılan")
        ua_edit.setText(self.settings.get("user_agent", "default"))
        ua_edit.textChanged.connect(lambda v: auto_save("user_agent", v))
        create_row(c5, "Özel User-Agent", "Tarayıcının kendini site altyapılarına nasıl tanıtacağını değiştirir.", ua_edit)

        dev_check = QCheckBox()
        dev_check.setChecked(self.settings.get("developer_mode", False))
        dev_check.toggled.connect(lambda v: auto_save("developer_mode", v))
        create_row(c5, "Geliştirici Araçları", "Sayfalar için Öğeyi İncele modunu sağ tık menüsünde aktif eder.", dev_check)

        btn_reset = QPushButton("Sıfırla")
        btn_reset.setObjectName("danger_btn")
        def _do_reset():
            for k, v in DEFAULT_SETTINGS.items(): self.settings[k] = v
            save_settings(self.settings)
            self.close_tab(self.tabs.indexOf(page))
            self._show_settings()
        btn_reset.clicked.connect(_do_reset)
        create_row(c5, "Fabrika Ayarlarına Dön", "Cihazınızdaki bu tarayıcının tüm ayarlarını Miny defautlarına sıfırlar.", btn_reset)

        content_lay.addStretch()
        scroll.setWidget(content_container)
        main_lay.addWidget(scroll)
        
        page.base_lay.addLayout(main_lay)

        def js_scroll(idx):
            if idx < len(cards_data):
                # Using QTimer to ensure layout is ready before calculating positions
                def scroll_to():
                    y = cards_data[idx].y() - 40 # slightly above
                    scroll.verticalScrollBar().setValue(max(0, y))
                QTimer.singleShot(50, scroll_to)
        sidebar.currentRowChanged.connect(js_scroll)
        
        def js_search(txt):
            txt = txt.lower()
            visible_cards = set()
            for row, text_content, card in all_rows:
                if txt in text_content:
                    row.setVisible(True)
                    visible_cards.add(card)
                else:
                    row.setVisible(False)
            
            for card in cards_data:
                if txt == "" or card in visible_cards:
                    card.setVisible(True)
                else:
                    card.setVisible(False)
        search_box.textChanged.connect(js_search)
        
        sidebar.setCurrentRow(0)
        self._open_internal_tab(page, "Ayarlar", "ayarlar")

    def _show_about(self):
        QMessageBox.about(self, "Miny Browser Hakkında", 
            "<h3>Miny Browser v1.0</h3>"
            "<p>Modern, hızlı ve güvenli PySide6 tabanlı web tarayıcısı.</p>"
            "<p>© 2026 Tüm hakları saklıdır.</p>")


    # ────────────────────────────────────
    #  SHORTCUTS & SESSION
    # ────────────────────────────────────
    def _setup_shortcuts(self):
        shortcuts = [
            ("Ctrl+T", lambda: self.add_tab()),
            ("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex())),
            ("Ctrl+L", self.url_bar.setFocus),
            ("Ctrl+R", self._nav_reload),
            ("F5", self._nav_reload),
            ("Ctrl+F", self._toggle_find),
            ("Ctrl+Shift+N", self._new_private_tab),
            ("Ctrl+H", self._show_history),
            ("Ctrl+B", self._show_bookmarks),
            ("Ctrl+J", self._show_downloads),
            ("F11", self._toggle_fullscreen),
            ("Ctrl+Plus", lambda: self._zoom(0.1)),
            ("Ctrl+Shift+Plus", lambda: self._zoom(0.1)),
            ("Ctrl+-", lambda: self._zoom(-0.1)),
            ("Ctrl+0", lambda: self._set_zoom(1.0)),

        ]
        for key, slot in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(slot)

    def _zoom(self, delta):
        self._zoom_factor = max(0.25, min(5.0, self._zoom_factor + delta))
        self._apply_zoom()

    def _set_zoom(self, val):
        self._zoom_factor = val
        self._apply_zoom()

    def _apply_zoom(self):
        view = self.tabs.currentWidget()
        if view:
            view.setZoomFactor(self._zoom_factor)
            # self._update_zoom_label()

    def _update_zoom_label(self):
        # self.zoom_label.setText(f"{int(self._zoom_factor * 100)}%")
        pass

    def _restore_session(self):
        if self.settings.get("restore_session", True) and SESSION_FILE.exists():
            urls = load_json(SESSION_FILE, [])
            if urls:
                for u in urls:
                    self.add_tab(u)
                return
        self.add_tab()

    def _save_session(self):
        urls = []
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            u = view.url().toString()
            if u and "newtab.html" not in u:
                urls.append(u)
        save_json(SESSION_FILE, urls)

    def closeEvent(self, event):
        self._save_session()
        super().closeEvent(event)

# ══════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    # Stabil Mod Bayrakları (Siyah kareleri önler)
    speed_flags = [
        "--use-angle=d3d11",
        "--disable-gpu-memory-buffer-video-frames",
        "--enable-parallel-downloading",
        "--enable-quic",
        "--ignore-gpu-blocklist",
        # "--enable-gpu-rasterization", # Siyah karelere sebep olduğu için kapatıldı
    ]
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(speed_flags)
    
    app = QApplication(sys.argv)
    # Gereksiz yerel nesne paylaşımını kapatarak RAM yükünü azaltır
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    app.setApplicationName("Miny Browser")
    app.setOrganizationName("MinySoft")
    app.setStyleSheet(DARK_QSS)
    
    window = MinyBrowser()
    window.show()
    
    sys.exit(app.exec())
