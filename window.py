import os, ctypes
from ctypes import wintypes, POINTER, byref, c_int, c_uint, c_ulong, Structure
import win32com.client
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu,
                             QListWidget, QListWidgetItem, QFileIconProvider,
                             QListView, QTabBar, QSystemTrayIcon, QApplication,
                             QLineEdit, QPushButton, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QSize, QFileInfo, QMimeData, QPoint, QEvent, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtGui import QIcon, QCursor, QPixmap, QPainter, QColor, QDrag, QImage
try:
    from PyQt5.QtWinExtras import QtWin
    _HAS_QTWIN = True
except Exception:
    _HAS_QTWIN = False
import config
from dialogs import SettingsDialog, InputDialog, EditItemDialog


class _SHFILEINFO(Structure):
    _fields_ = [("hIcon", wintypes.HICON),
                ("iIcon", c_int),
                ("dwAttributes", c_ulong),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]


_SHGFI_ICON = 0x100
_SHGFI_LARGEICON = 0x0

_shell32 = ctypes.windll.shell32
_user32 = ctypes.windll.user32
_shell32.SHGetFileInfoW.argtypes = [wintypes.LPCWSTR, c_ulong, POINTER(_SHFILEINFO), c_uint, c_uint]
_shell32.SHGetFileInfoW.restype = ctypes.c_ssize_t
_user32.DestroyIcon.argtypes = [wintypes.HICON]
_user32.DestroyIcon.restype = wintypes.BOOL


def _shell_system_qicon(path):
    if not _HAS_QTWIN:
        return None
    info = _SHFILEINFO()
    ret = _shell32.SHGetFileInfoW(path, 0, byref(info), ctypes.sizeof(info),
                                  _SHGFI_ICON | _SHGFI_LARGEICON)
    if not ret or not info.hIcon:
        return None
    try:
        pix = QtWin.fromHICON(info.hIcon)
    except Exception as e:
        config.log_msg(f"QtWin.fromHICON failed for {path}: {e}")
        pix = None
    try:
        _user32.DestroyIcon(info.hIcon)
    except Exception:
        pass
    if not pix or pix.isNull():
        return None
    return QIcon(pix)


_LNK_SHELL = None
def _resolve_lnk_target(path):
    global _LNK_SHELL
    try:
        if _LNK_SHELL is None:
            _LNK_SHELL = win32com.client.Dispatch("WScript.Shell")
        sc = _LNK_SHELL.CreateShortcut(path)
        t = sc.TargetPath
        if t and os.path.exists(t):
            return t
        if t and t.lower().endswith(".lnk") and os.path.exists(t):
            return _resolve_lnk_target(t)
    except Exception as e:
        config.log_msg(f"_resolve_lnk_target failed for {path}: {e}")
    return None


def _icon_has_content(icon):
    if not icon or icon.isNull():
        return False
    try:
        p = icon.pixmap(32, 32)
        return not p.isNull()
    except Exception:
        return False


RESIZE_MARGIN = 12
CORNER_MARGIN = 18
MIN_W, MIN_H = 320, 320
DRAG_MIME = "application/x-runlauncher-item"


class DragListWidget(QListWidget):
    def __init__(self, launcher):
        super().__init__(launcher)
        self._launcher = launcher
        self._press_pos = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton) or self._press_pos is None:
            return super().mouseMoveEvent(e)
        if (e.pos() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(e)
        item = self.itemAt(self._press_pos)
        if item is None:
            return super().mouseMoveEvent(e)
        data = item.data(Qt.UserRole)
        if not data:
            return super().mouseMoveEvent(e)
        cat = self._launcher._find_item_category(data)
        if cat is None:
            return super().mouseMoveEvent(e)
        src_cat_idx = self._launcher.categories.index(cat)
        src_item_idx = cat["items"].index(data)
        mime = QMimeData()
        mime.setData(DRAG_MIME, f"{src_cat_idx}:{src_item_idx}".encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        try:
            icon = item.icon()
            if not icon.isNull():
                drag.setPixmap(icon.pixmap(48, 48))
        except Exception:
            pass
        self._press_pos = None
        drag.exec_(Qt.MoveAction)


class DropTabBar(QTabBar):
    def __init__(self, launcher):
        super().__init__(launcher)
        self._launcher = launcher
        self.setAcceptDrops(True)
        self._hover_tab = -1

    def _tab_at_relaxed(self, pos):
        idx = self.tabAt(pos)
        if idx >= 0:
            return idx
        best_idx = -1
        best_dist = 10 ** 9
        for i in range(self.count()):
            r = self.tabRect(i)
            cx = r.center().x()
            cy = r.center().y()
            dx = abs(pos.x() - cx)
            dy = abs(pos.y() - cy)
            dist = dx + dy * 3
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _highlight(self, idx):
        if idx == self._hover_tab:
            return
        self._hover_tab = idx
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._hover_tab >= 0 and self._hover_tab < self.count():
            p = QPainter(self)
            r = self.tabRect(self._hover_tab)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(100, 150, 255, 90))
            p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 4, 4)
            p.end()

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(DRAG_MIME):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(DRAG_MIME):
            idx = self._tab_at_relaxed(e.pos())
            self._highlight(idx)
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dragLeaveEvent(self, e):
        self._highlight(-1)
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        self._highlight(-1)
        if not e.mimeData().hasFormat(DRAG_MIME):
            return super().dropEvent(e)
        try:
            payload = bytes(e.mimeData().data(DRAG_MIME)).decode("utf-8")
            src_cat, src_idx = map(int, payload.split(":"))
        except Exception as ex:
            config.log_msg(f"DropTabBar parse mime failed: {ex}")
            return
        dst_cat = self._tab_at_relaxed(e.pos())
        cats = self._launcher.categories
        if dst_cat < 0 or dst_cat >= len(cats) or dst_cat == src_cat:
            return
        if src_cat < 0 or src_cat >= len(cats):
            return
        try:
            it = cats[src_cat]["items"].pop(src_idx)
        except Exception:
            return
        cats[dst_cat]["items"].append(it)
        config.save_config(self._launcher.config_data, cats)
        self._launcher.refresh_list()
        e.acceptProposedAction()


class LauncherWindow(QWidget):
    _icon_ready = pyqtSignal(int, int, object, object)  # gen, idx, QIcon, cache_key

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.drag_pos = None
        self._drag_mode = None
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_gpos = None
        self._hover_edge = None
        self.config_data = config.load_config()
        self.categories = self.config_data.get("categories", [{"name": "默认", "items": []}])
        self.current_cat = 0
        self.filter_text = ""
        self._icon_cache = {}
        self._refresh_gen = 0
        self._icon_loader = ThreadPoolExecutor(max_workers=4)
        self.init_ui()
        self.setup_tray()
        QApplication.instance().installEventFilter(self)

    def _install_native_resize_frame(self):
        pass

    def _enable_mouse_tracking_recursive(self, widget):
        try:
            widget.setMouseTracking(True)
        except Exception:
            pass
        for child in widget.findChildren(QWidget):
            try:
                child.setMouseTracking(True)
            except Exception:
                pass

    def eventFilter(self, obj, ev):
        try:
            if not self.isVisible():
                return False
            if not (isinstance(obj, QWidget) and self.isAncestorOf(obj)) and obj is not self:
                return False
            et = ev.type()
            if et == QEvent.MouseMove:
                gpos = ev.globalPos()
                lpos = self.mapFromGlobal(gpos)
                if self._drag_mode == "resize":
                    self._perform_resize(gpos)
                    return True
                if self._drag_mode == "move":
                    if self.drag_pos is not None:
                        self.move(gpos - self.drag_pos)
                    return True
                edge = self._hit_test(lpos)
                if edge != self._hover_edge:
                    self._hover_edge = edge
                    self._set_edge_cursor(edge)
                if edge:
                    return True
            elif et == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                gpos = ev.globalPos()
                lpos = self.mapFromGlobal(gpos)
                edge = self._hit_test(lpos)
                if edge:
                    self._drag_mode = "resize"
                    self._resize_edge = edge
                    self._resize_start_geom = self.geometry()
                    self._resize_start_gpos = gpos
                    return True
                if obj is self or obj is self.title_label:
                    self._drag_mode = "move"
                    self.drag_pos = gpos - self.pos()
            elif et == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                if self._drag_mode == "resize":
                    self.config_data["window_width"] = self.width()
                    self.config_data["window_height"] = self.height()
                    config.save_config(self.config_data, self.categories)
                was_resize = self._drag_mode == "resize"
                self._drag_mode = None
                self._resize_edge = None
                self._resize_start_geom = None
                self._resize_start_gpos = None
                self.drag_pos = None
                if was_resize:
                    return True
        except Exception as e:
            config.log_msg(f"eventFilter error: {e}")
        return False

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
        self.tray.setToolTip(self.config_data.get("title", "Run Launcher") + " (Alt+Space)")
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
        self.config_data["window_width"] = self.width()
        self.config_data["window_height"] = self.height()
        config.save_config(self.config_data, self.categories)
        self.hide()

    def quit_app(self):
        self.config_data["window_width"] = self.width()
        self.config_data["window_height"] = self.height()
        config.save_config(self.config_data, self.categories)
        config.flush_save_now()
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
            self.resize(vals["width"], vals["height"])
            self.title_label.setText("  " + vals["title"])
            self.tray.setToolTip(vals["title"] + " (Alt+Space)")

    def init_ui(self):
        w = self.config_data.get("window_width", 420)
        h = self.config_data.get("window_height", 480)
        self.setMinimumSize(MIN_W, MIN_H)
        self.resize(max(w, MIN_W), max(h, MIN_H))
        layout = QVBoxLayout()
        layout.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        bg = QWidget()
        bg.setStyleSheet("background: rgba(30,30,40,220); border-radius: 10px;")
        bg_layout = QVBoxLayout(bg)
        bg_layout.setSpacing(6)

        title_text = self.config_data.get("title", "Run Launcher")
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

        self.tabs = DropTabBar(self)
        self.tabs.setStyleSheet("""
            QTabBar { background: transparent; }
            QTabBar::tab { color: #ccc; padding: 8px 16px; margin: 2px; border-radius: 4px; min-height: 20px; }
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

        self.list = DragListWidget(self)
        self.list.setAcceptDrops(True)
        self.list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: white; }
            QListWidget::item { padding: 4px; border-radius: 6px; color: white; }
            QListWidget::item:hover { background: rgba(255,255,255,0.15); color: white; }
            QListWidget::item:selected { background: rgba(255,255,255,0.1); color: white; }
        """)
        self.list.setViewMode(QListView.IconMode)
        self.list.setIconSize(QSize(32, 32))
        self.list.setGridSize(QSize(72, 72))
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

        self._icon_ready.connect(self._on_icon_ready)
        self.refresh_list()

        bg_layout.addLayout(title_bar)
        bg_layout.addWidget(self.search_box)
        bg_layout.addWidget(self.tabs)
        bg_layout.addWidget(self.list)

        layout.addWidget(bg)
        self.setLayout(layout)
        self._enable_mouse_tracking_recursive(self)

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
        if dlg.exec_() == QDialog.Accepted:
            name = dlg.get_text()
            if name:
                self.categories.append({"name": name, "items": []})
                self.refresh_tabs()
                self.tabs.setCurrentIndex(len(self.categories) - 1)
                config.save_config(self.config_data, self.categories)

    def rename_category(self, idx):
        dlg = InputDialog(self, "Rename", "新名称:", self.categories[idx]["name"])
        if dlg.exec_() == QDialog.Accepted:
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
        if not e.mimeData().hasUrls():
            return
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.exists(path):
                name = os.path.splitext(os.path.basename(path))[0]
                self.categories[self.current_cat]["items"].append({"name": name, "path": path})
        config.save_config(self.config_data, self.categories)
        self.refresh_list()

    def launch_item(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        path = data["path"]
        real = path
        if path.lower().endswith(".lnk"):
            t = _resolve_lnk_target(path)
            if t:
                real = t
        if not os.path.exists(real):
            config.log_msg(f"launch_item failed: path not found: {path} (resolved: {real})")
            QMessageBox.warning(self, "启动失败",
                f"找不到目标，可能已卸载或被移动：\n{path}\n\n解析路径：{real}")
            return
        try:
            os.startfile(path)
        except Exception as e:
            config.log_msg(f"launch_item exception: {path}: {e}")
            QMessageBox.warning(self, "启动失败", f"无法启动：\n{path}\n\n{e}")
            return
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

    def _find_item_category(self, data):
        for cat in self.categories:
            if data in cat["items"]:
                return cat
        return None

    def edit_item(self, data):
        cat = self._find_item_category(data)
        if cat is None:
            return
        idx = cat["items"].index(data)
        dlg = EditItemDialog(self, data["name"], data["path"], data.get("icon_path", ""))
        if dlg.exec_() != QDialog.Accepted:
            return
        vals = dlg.get_values()
        if vals:
            cat["items"][idx] = vals
            config.save_config(self.config_data, self.categories)
            self.refresh_list()

    def delete_item(self, data):
        cat = self._find_item_category(data)
        if cat is not None:
            cat["items"].remove(data)
            config.save_config(self.config_data, self.categories)
            self.refresh_list()

    def refresh_list(self):
        self._refresh_gen += 1
        gen = self._refresh_gen
        self.list.clear()
        if self.filter_text:
            items = []
            for cat in self.categories:
                items.extend(it for it in cat["items"] if self.filter_text in it["name"].lower())
        else:
            items = self.current_items
        for idx, item in enumerate(items):
            li = QListWidgetItem(item["name"])
            li.setData(Qt.UserRole, item)
            li.setTextAlignment(Qt.AlignCenter)
            key = self._icon_cache_key(item)
            if key and key in self._icon_cache:
                li.setIcon(self._icon_cache[key])
            else:
                self._icon_loader.submit(self._load_icon_async, gen, idx, item)
            self.list.addItem(li)

    @staticmethod
    def _icon_cache_key(item):
        icon_path = item.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            try:
                mtime = os.path.getmtime(icon_path)
            except Exception:
                mtime = 0
            return ("icon", icon_path, mtime)
        path = item.get("path", "")
        if path and os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0
            return ("path", os.path.realpath(path), mtime)
        return None

    def _on_icon_ready(self, gen, idx, icon, key):
        if gen != self._refresh_gen:
            return
        if key:
            self._icon_cache[key] = icon
        li = self.list.item(idx)
        if li is not None:
            li.setIcon(icon)

    def _load_icon_async(self, gen, idx, item):
        try:
            icon = self._extract_icon_for_item(item)
        except Exception as e:
            config.log_msg(f"_load_icon_async({idx}): {e}")
            return
        if not icon:
            return
        key = self._icon_cache_key(item)
        self._icon_ready.emit(gen, idx, icon, key)

    def _extract_icon_for_item(self, item):
        icon_path = item.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            icon = self._load_custom_icon(icon_path)
            if icon:
                return icon
        path = item.get("path", "")
        if os.path.exists(path):
            icon = self.extract_icon(path)
            if icon:
                return icon
        if path.lower().endswith(".lnk"):
            target = _resolve_lnk_target(path)
            if target and target != path and os.path.exists(target):
                icon = self.extract_icon(target)
                if icon:
                    return icon
        return None

    def extract_icon(self, path):
        icon = self._extract_icon_from_path(path)
        if icon:
            return icon
        if path.lower().endswith(".lnk"):
            target = _resolve_lnk_target(path)
            if target and target != path:
                icon = self._extract_icon_from_path(target)
                if icon:
                    return icon
        return None

    def _load_custom_icon(self, icon_path):
        try:
            ext = os.path.splitext(icon_path)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".bmp", ".ico"):
                pix = QPixmap(icon_path)
                if pix.isNull():
                    return None
                return QIcon(pix)
            return _shell_system_qicon(icon_path)
        except Exception as e:
            config.log_msg(f"_load_custom_icon failed for {icon_path}: {e}")
            return None

    def _extract_icon_from_path(self, path):
        if os.path.exists(path):
            icon = _shell_system_qicon(path)
            if _icon_has_content(icon):
                return icon
        try:
            icon = QFileIconProvider().icon(QFileInfo(path))
            if _icon_has_content(icon):
                return icon
        except Exception as e:
            config.log_msg(f"QFileIconProvider failed for {path}: {e}")
        ext = os.path.splitext(path)[1].lower()
        if ext in (".exe", ".dll", ".ico"):
            try:
                icon = QIcon(path)
                if _icon_has_content(icon):
                    return icon
            except Exception:
                pass
        return None

    def _hit_test(self, pos):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        m = RESIZE_MARGIN
        cm = CORNER_MARGIN
        c_left = x < cm
        c_right = x > w - cm
        c_top = y < cm
        c_bottom = y > h - cm
        if c_top and c_left: return "top_left"
        if c_top and c_right: return "top_right"
        if c_bottom and c_left: return "bottom_left"
        if c_bottom and c_right: return "bottom_right"
        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def _set_edge_cursor(self, edge):
        cursors = {
            "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
            "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
            "top_left": Qt.SizeFDiagCursor, "bottom_right": Qt.SizeFDiagCursor,
            "top_right": Qt.SizeBDiagCursor, "bottom_left": Qt.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(edge, Qt.ArrowCursor))

    def _perform_resize(self, gpos):
        dx = gpos.x() - self._resize_start_gpos.x()
        dy = gpos.y() - self._resize_start_gpos.y()
        g = self._resize_start_geom
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        edge = self._resize_edge or ""
        if "left" in edge:
            new_w = max(MIN_W, w - dx)
            x = x + (w - new_w)
            w = new_w
        if "right" in edge:
            w = max(MIN_W, w + dx)
        if "top" in edge:
            new_h = max(MIN_H, h - dy)
            y = y + (h - new_h)
            h = new_h
        if "bottom" in edge:
            h = max(MIN_H, h + dy)
        self.setGeometry(x, y, w, h)

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        pass

    def mouseReleaseEvent(self, e):
        pass

    def toggle(self):
        if self.isVisible():
            self.config_data["pos_x"], self.config_data["pos_y"] = self.pos().x(), self.pos().y()
            self.config_data["window_width"] = self.width()
            self.config_data["window_height"] = self.height()
            config.save_config(self.config_data, self.categories)
            self.hide()
        else:
            cursor = QCursor.pos()
            w = self.width()
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
