# -*- coding: utf-8 -*-
import sys, os, json, subprocess, ctypes, ctypes.wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QMenu, QListWidget, QListWidgetItem, QFileIconProvider,
                             QListView, QTabBar, QMessageBox,
                             QSystemTrayIcon, QDialog, QFormLayout, QLineEdit, QSpinBox,
                             QPushButton)
from PyQt5.QtCore import Qt, QAbstractNativeEventFilter, QTimer, QSize, QFileInfo
from PyQt5.QtGui import QIcon, QCursor, QPixmap, QPainter, QColor
import win32gui, win32api

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "hotkey": {"ctrl": False, "alt": True, "shift": False, "vk": 0x20},
    "window_width": 420, "window_height": 480,
    "title": "Launcher",
    "categories": [{"name": "\u9ed8\u8ba4", "items": []}]
}

class WinEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            if msg.message == 0x0311:
                self.callback()
                return True, 0
        return False, 0

class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.drag_pos = None
        self.config = self.load_config()
        self.categories = self.config.get("categories", [{"name": "\u9ed8\u8ba4", "items": []}])
        self.current_cat = 0
        self.init_ui()
        self.setup_tray()
        QTimer.singleShot(500, self.setup_hotkey)

    def setup_tray(self):
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setBrush(QColor(100, 150, 255))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 2, 12, 12, 3, 3)
        p.end()
        icon = QIcon(pix)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip(self.config.get("title", "Launcher") + " (Alt+Space)")
        tray_menu = QMenu()
        a1 = tray_menu.addAction("\u663e\u793a/\u9690\u85cf")
        a1.triggered.connect(self.toggle)
        tray_menu.addSeparator()
        a2 = tray_menu.addAction("\u8bbe\u7f6e")
        a2.triggered.connect(self.show_settings)
        tray_menu.addSeparator()
        a3 = tray_menu.addAction("\u9000\u51fa")
        a3.triggered.connect(self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_click)
        self.tray.show()

    def tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle()

    def quit_app(self):
        self.save_config()
        QApplication.instance().quit()

    def show_settings(self):
        w = self.config.get("window_width", 420)
        h = self.config.get("window_height", 480)
        t = self.config.get("title", "Launcher")
        dialog = QDialog(self)
        dialog.setWindowTitle("\u8bbe\u7f6e")
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        form = QFormLayout(dialog)
        de_title = QLineEdit(t)
        de_title.setStyleSheet("background: #555; color: white; border: 1px solid #777; padding: 4px;")
        sb_w = QSpinBox()
        sb_w.setRange(200, 2000); sb_w.setValue(w)
        sb_w.setStyleSheet("background: #555; color: white; border: 1px solid #777;")
        sb_h = QSpinBox()
        sb_h.setRange(200, 2000); sb_h.setValue(h)
        sb_h.setStyleSheet("background: #555; color: white; border: 1px solid #777;")
        form.addRow("\u6807\u9898:", de_title)
        form.addRow("\u5bbd\u5ea6:", sb_w)
        form.addRow("\u9ad8\u5ea6:", sb_h)
        btn = QPushButton("\u786e\u5b9a")
        btn.setStyleSheet("background: #555; color: white; border: 1px solid #777; padding: 6px;")
        btn.clicked.connect(lambda: self._apply_settings(de_title.text(), sb_w.value(), sb_h.value(), dialog))
        form.addRow(btn)
        dialog.exec_()

    def _apply_settings(self, title, width, height, dialog):
        self.config["title"] = title
        self.config["window_width"] = width
        self.config["window_height"] = height
        self.save_config()
        dialog.accept()
        self.setFixedSize(width, height)
        self.title_label.setText("  " + title)
        self.tray.setToolTip(title + " (Alt+Space)")

    def setup_hotkey(self):
        hk = self.config.get("hotkey", DEFAULT_CONFIG["hotkey"])
        mod = 0
        if hk.get("ctrl"): mod |= 0x0002
        if hk.get("alt"): mod |= 0x0001
        if hk.get("shift"): mod |= 0x0004
        vk = hk.get("vk", 0xC0)
        HWND = int(self.winId())
        ctypes.windll.user32.RegisterHotKey(HWND, 1, mod, vk)

    def init_ui(self):
        w = self.config.get("window_width", 420)
        h = self.config.get("window_height", 480)
        self.setFixedSize(w, h)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        bg = QWidget()
        bg.setStyleSheet("background: rgba(30,30,40,220); border-radius: 10px;")
        bg_layout = QVBoxLayout(bg)
        bg_layout.setSpacing(6)

        title_text = self.config.get("title", "Launcher")
        self.title_label = QLabel("  " + title_text)
        self.title_label.setStyleSheet("color: white; font: bold 14px; padding: 4px 0;")
        self.title_label.setFixedHeight(28)

        self.tabs = QTabBar()
        self.tabs.setStyleSheet("""
            QTabBar { background: transparent; }
            QTabBar::tab { color: #ccc; padding: 4px 14px; margin: 2px; border-radius: 4px; }
            QTabBar::tab:hover { background: rgba(255,255,255,0.1); color: white; }
            QTabBar::tab:selected { background: rgba(255,255,255,0.2); color: white; }
        """)
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(self.switch_category)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_menu)
        self.refresh_tabs()

        self.list = QListWidget()
        self.list.setAcceptDrops(True)
        self.list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: white; }
            QListWidget::item { padding: 4px; border-radius: 6px; color: white; }
            QListWidget::item:hover { background: rgba(255,255,255,0.15); color: white; }
            QListWidget::item:selected { background: rgba(255,255,255,0.1); color: white; }
        """)
        self.list.setViewMode(QListView.IconMode)
        self.list.setIconSize(QSize(44, 44))
        self.list.setGridSize(QSize(72, 80))
        self.list.setWrapping(True)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setMovement(QListView.Snap)
        self.list.setWordWrap(True)
        self.list.setSpacing(4)
        self.list.itemDoubleClicked.connect(self.launch_item)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.item_menu)

        self.list.dragEnterEvent = self.list_drag_enter
        self.list.dragMoveEvent = self.list_drag_move
        self.list.dropEvent = self.list_drop

        self.refresh_list()

        bg_layout.addWidget(self.title_label)
        bg_layout.addWidget(self.tabs)
        bg_layout.addWidget(self.list)
        layout.addWidget(bg)
        self.setLayout(layout)

    def refresh_tabs(self):
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for cat in self.categories:
            self.tabs.addTab(cat["name"])
        if self.tabs.count() > 0:
            self.tabs.setCurrentIndex(min(self.current_cat, self.tabs.count() - 1))
        self.tabs.blockSignals(False)

    def switch_category(self, index):
        self.current_cat = index
        self.refresh_list()

    @property
    def current_items(self):
        if 0 <= self.current_cat < len(self.categories):
            return self.categories[self.current_cat]["items"]
        return []

    def tab_menu(self, pos):
        menu = QMenu()
        act = menu.addAction("\u6dfb\u52a0\u5206\u7c7b")
        act.triggered.connect(self.add_category)
        tab_idx = self.tabs.tabAt(pos)
        if tab_idx >= 0:
            act2 = menu.addAction("\u91cd\u547d\u540d")
            act2.triggered.connect(lambda: self.rename_category(tab_idx))
            if len(self.categories) > 1:
                act3 = menu.addAction("\u5220\u9664")
                act3.triggered.connect(lambda: self.delete_category(tab_idx))
        menu.exec_(self.tabs.mapToGlobal(pos))

    def add_category(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Category")
        dlg.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        dlg.setStyleSheet("QDialog { background: #333; } QLabel { color: white; font: 9pt 'Microsoft YaHei'; } QLineEdit { background: #555; color: white; border: 1px solid #777; padding: 4px; font: 9pt 'Microsoft YaHei'; } QPushButton { background: #555; color: white; border: 1px solid #777; padding: 6px 20px; font: 9pt 'Microsoft YaHei'; } QPushButton:hover { background: #666; }")
        dlg.setFixedWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("\u5206\u7c7b\u540d\u79f0:"))
        ed = QLineEdit()
        layout.addWidget(ed)
        btn = QPushButton("\u786e\u5b9a")
        btn.clicked.connect(lambda: dlg.accept())
        layout.addWidget(btn)
        if dlg.exec_() == QDialog.Accepted and ed.text().strip():
            name = ed.text().strip()
            self.categories.append({"name": name, "items": []})
            self.refresh_tabs()
            self.tabs.setCurrentIndex(len(self.categories) - 1)
            self.save_config()

    def rename_category(self, idx):
        dlg = QDialog(self)
        dlg.setWindowTitle("Rename")
        dlg.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        dlg.setStyleSheet("QDialog { background: #333; } QLabel { color: white; font: 9pt 'Microsoft YaHei'; } QLineEdit { background: #555; color: white; border: 1px solid #777; padding: 4px; font: 9pt 'Microsoft YaHei'; } QPushButton { background: #555; color: white; border: 1px solid #777; padding: 6px 20px; font: 9pt 'Microsoft YaHei'; } QPushButton:hover { background: #666; }")
        dlg.setFixedWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("\u65b0\u540d\u79f0:"))
        ed = QLineEdit(self.categories[idx]["name"])
        layout.addWidget(ed)
        btn = QPushButton("\u786e\u5b9a")
        btn.clicked.connect(lambda: dlg.accept())
        layout.addWidget(btn)
        if dlg.exec_() == QDialog.Accepted and ed.text().strip():
            self.categories[idx]["name"] = ed.text().strip()
            self.refresh_tabs()
            self.save_config()

    def delete_category(self, idx):
        self.categories.pop(idx)
        if self.current_cat >= len(self.categories):
            self.current_cat = len(self.categories) - 1
        self.refresh_tabs()
        self.refresh_list()
        self.save_config()

    def list_drag_enter(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def list_drag_move(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def list_drop(self, e):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.exists(path):
                name = os.path.splitext(os.path.basename(path))[0]
                self.categories[self.current_cat]["items"].append({"name": name, "path": path})
        self.save_config()
        self.refresh_list()

    def launch_item(self, item):
        data = item.data(Qt.UserRole)
        if data:
            try:
                subprocess.Popen(data["path"], shell=True)
            except:
                pass
            self.hide()

    def item_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        menu = QMenu()
        act = menu.addAction("\u5220\u9664")
        act.triggered.connect(lambda: self.delete_item(data))
        menu.exec_(self.list.mapToGlobal(pos))

    def delete_item(self, data):
        items = self.current_items
        if data in items:
            items.remove(data)
            self.save_config()
            self.refresh_list()

    def refresh_list(self):
        self.list.clear()
        for item in self.current_items:
            li = QListWidgetItem(item["name"])
            li.setData(Qt.UserRole, item)
            li.setTextAlignment(Qt.AlignCenter)
            if os.path.exists(item["path"]):
                icon = self.extract_icon(item["path"])
                if icon:
                    li.setIcon(icon)
            self.list.addItem(li)

    def extract_icon(self, path):
        try:
            icon = QFileIconProvider().icon(QFileInfo(path))
            if icon and not icon.isNull():
                return icon
        except:
            pass
        return None

    def mousePressEvent(self, e):
        self.drag_pos = e.globalPos() - self.pos()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(e.globalPos() - self.drag_pos)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            cursor = QCursor.pos()
            w = self.config.get("window_width", 420)
            self.move(cursor.x() - w // 2, cursor.y() - 20)
            self.show()
            self.raise_()
            self.activateWindow()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"hotkey": DEFAULT_CONFIG["hotkey"], "categories": [{"name": "\u9ed8\u8ba4", "items": data}]}
                if "categories" not in data and "items" in data:
                    data["categories"] = [{"name": "\u9ed8\u8ba4", "items": data.pop("items")}]
                return data
        return dict(DEFAULT_CONFIG)

    def save_config(self):
        self.config["categories"] = self.categories
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    

    window = LauncherWindow()
    window.hide()

    event_filter = WinEventFilter(window.toggle)
    app.installNativeEventFilter(event_filter)

    hotkey_state = {"pressed": False}
    hk = window.config.get("hotkey", DEFAULT_CONFIG["hotkey"])
    mod_vks = []
    if hk.get("ctrl"): mod_vks.append(0x11)
    if hk.get("alt"): mod_vks.append(0x12)
    if hk.get("shift"): mod_vks.append(0x10)
    target_vk = hk.get("vk", 0xC0)

    def poll_hotkey():
        all_down = all(win32api.GetAsyncKeyState(vk) & 0x8000 for vk in mod_vks)
        target_down = win32api.GetAsyncKeyState(target_vk) & 0x8000
        if all_down and target_down and not hotkey_state["pressed"]:
            hotkey_state["pressed"] = True
            window.toggle()
        elif not (all_down and target_down):
            hotkey_state["pressed"] = False

    poll_timer = QTimer()
    poll_timer.timeout.connect(poll_hotkey)
    poll_timer.start(150)

    sys.exit(app.exec_())
