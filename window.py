import os, ctypes, ctypes.wintypes
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu,
                             QListWidget, QListWidgetItem, QFileIconProvider,
                             QListView, QTabBar, QSystemTrayIcon, QApplication,
                             QLineEdit, QPushButton)
from PyQt5.QtCore import Qt, QTimer, QSize, QFileInfo
from PyQt5.QtGui import QIcon, QCursor, QPixmap, QPainter, QColor
import config
from dialogs import SettingsDialog, InputDialog, EditItemDialog

class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.drag_pos = None
        self.config_data = config.load_config()
        self.categories = self.config_data.get("categories", [{"name": "默认", "items": []}])
        self.current_cat = 0
        self.filter_text = ""
        self.init_ui()
        self.setup_tray()

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
        self.tray.setToolTip(self.config_data.get("title", "Launcher") + " (Alt+Space)")
        tray_menu = QMenu()
        a1 = tray_menu.addAction("显示/隐藏")
        a1.triggered.connect(self.toggle)
        tray_menu.addSeparator()
        a2 = tray_menu.addAction("设置")
        a2.triggered.connect(self.show_settings)
        tray_menu.addSeparator()
        a3 = tray_menu.addAction("退出")
        a3.triggered.connect(self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_click)
        self.tray.show()

    def tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle()

    def hide_window(self):
        self.config_data["pos_x"], self.config_data["pos_y"] = self.pos().x(), self.pos().y()
        config.save_config(self.config_data, self.categories)
        self.hide()

    def quit_app(self):
        config.save_config(self.config_data, self.categories)
        QApplication.instance().quit()

    def show_settings(self):
        dlg = SettingsDialog(self, self.config_data)
        if dlg.exec_() == SettingsDialog.Accepted:
            vals = dlg.get_values()
            self.config_data["title"] = vals["title"]
            self.config_data["window_width"] = vals["width"]
            self.config_data["window_height"] = vals["height"]
            config.save_config(self.config_data, self.categories)
            config.set_auto_start(vals["autostart"])
            self.setFixedSize(vals["width"], vals["height"])
            self.title_label.setText("  " + vals["title"])
            self.tray.setToolTip(vals["title"] + " (Alt+Space)")

    def init_ui(self):
        w = self.config_data.get("window_width", 420)
        h = self.config_data.get("window_height", 480)
        self.setFixedSize(w, h)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        bg = QWidget()
        bg.setStyleSheet("background: rgba(30,30,40,220); border-radius: 10px;")
        bg_layout = QVBoxLayout(bg)
        bg_layout.setSpacing(6)

        title_text = self.config_data.get("title", "Launcher")
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("  " + title_text)
        self.title_label.setStyleSheet("color: white; font: bold 14px; padding: 4px 0;")
        self.title_label.setFixedHeight(28)
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #aaa; border: none; font: bold 16px; }
            QPushButton:hover { background: rgba(255,60,60,0.6); color: white; border-radius: 12px; }
        """)
        self.btn_close.clicked.connect(self.hide_window)
        title_bar.addWidget(self.title_label)
        title_bar.addStretch()
        title_bar.addWidget(self.btn_close)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索...")
        self.search_box.setStyleSheet("""
            QLineEdit { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2);
                        border-radius: 4px; padding: 4px 8px; }
            QLineEdit:focus { border: 1px solid rgba(100,150,255,0.6); }
        """)
        self.search_box.textChanged.connect(self.filter_items)
        self.search_box.setFixedHeight(28)

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

        bg_layout.addLayout(title_bar)
        bg_layout.addWidget(self.search_box)
        bg_layout.addWidget(self.tabs)
        bg_layout.addWidget(self.list)
        layout.addWidget(bg)
        self.setLayout(layout)

    def filter_items(self, text):
        self.filter_text = text.strip().lower()
        self.refresh_list()

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
        self.search_box.clear()
        self.refresh_list()

    @property
    def current_items(self):
        if 0 <= self.current_cat < len(self.categories):
            return self.categories[self.current_cat]["items"]
        return []

    def tab_menu(self, pos):
        menu = QMenu()
        act = menu.addAction("添加分类")
        act.triggered.connect(self.add_category)
        tab_idx = self.tabs.tabAt(pos)
        if tab_idx >= 0:
            act2 = menu.addAction("重命名")
            act2.triggered.connect(lambda: self.rename_category(tab_idx))
            if len(self.categories) > 1:
                act3 = menu.addAction("删除")
                act3.triggered.connect(lambda: self.delete_category(tab_idx))
        menu.exec_(self.tabs.mapToGlobal(pos))

    def add_category(self):
        dlg = InputDialog(self, "Add Category", "分类名称:")
        name = dlg.get_text()
        if name:
            self.categories.append({"name": name, "items": []})
            self.refresh_tabs()
            self.tabs.setCurrentIndex(len(self.categories) - 1)
            config.save_config(self.config_data, self.categories)

    def rename_category(self, idx):
        dlg = InputDialog(self, "Rename", "新名称:", self.categories[idx]["name"])
        name = dlg.get_text()
        if name:
            self.categories[idx]["name"] = name
            self.refresh_tabs()
            config.save_config(self.config_data, self.categories)

    def delete_category(self, idx):
        self.categories.pop(idx)
        if self.current_cat >= len(self.categories):
            self.current_cat = len(self.categories) - 1
        self.refresh_tabs()
        self.refresh_list()
        config.save_config(self.config_data, self.categories)

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
        config.save_config(self.config_data, self.categories)
        self.refresh_list()

    def launch_item(self, item):
        data = item.data(Qt.UserRole)
        if data:
            try:
                os.startfile(data["path"])
            except:
                pass
            self.hide()

    def item_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        menu = QMenu()
        act_del = menu.addAction("删除")
        act_del.triggered.connect(lambda: self.delete_item(data))
        act_edit = menu.addAction("编辑")
        act_edit.triggered.connect(lambda: self.edit_item(data))
        menu.exec_(self.list.mapToGlobal(pos))

    def edit_item(self, data):
        if data not in self.current_items:
            return
        idx = self.current_items.index(data)
        dlg = EditItemDialog(self, data["name"], data["path"])
        vals = dlg.get_values()
        if vals:
            self.categories[self.current_cat]["items"][idx] = vals
            config.save_config(self.config_data, self.categories)
            self.refresh_list()

    def delete_item(self, data):
        items = self.current_items
        if data in items:
            items.remove(data)
            config.save_config(self.config_data, self.categories)
            self.refresh_list()

    def refresh_list(self):
        self.list.clear()
        items = self.current_items
        if self.filter_text:
            items = [it for it in items if self.filter_text in it["name"].lower()]
        for item in items:
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
            self.config_data["pos_x"], self.config_data["pos_y"] = self.pos().x(), self.pos().y()
            config.save_config(self.config_data, self.categories)
            self.hide()
        else:
            cursor = QCursor.pos()
            w = self.config_data.get("window_width", 420)
            px = self.config_data.get("pos_x")
            py = self.config_data.get("pos_y")
            if px is not None and py is not None:
                self.move(px, py)
            else:
                self.move(cursor.x() - w // 2, cursor.y() - 20)
            self.show()
            self.raise_()
            self.activateWindow()
            self.search_box.setFocus()
