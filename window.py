import os, ctypes, json
from collections import OrderedDict
from ctypes import wintypes
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu,
                             QListWidget, QListWidgetItem, QFileIconProvider,
                             QListView, QAbstractItemView, QTabBar, QSystemTrayIcon,
                             QApplication, QLineEdit, QPushButton, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QSize, QFileInfo, QMimeData, QPoint, QEvent, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtGui import QIcon, QCursor, QPixmap, QPainter, QColor, QPen, QDrag, QImage
try:
    from PyQt5.QtWinExtras import QtWin
    _HAS_QTWIN = True
except Exception:
    _HAS_QTWIN = False
import config
from utils import shell_hicon, resolve_lnk_target, resolve_lnk_target_cached, pinyin_initials
from utils import _shell32, _user32
from dialogs import SettingsDialog, InputDialog, EditItemDialog, AboutDialog



RESIZE_MARGIN = 15
CORNER_MARGIN = 6
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
        selected = self.selectedItems()
        if item not in selected:
            selected = [item]
        payload_items = []
        for it in selected:
            d = it.data(Qt.UserRole)
            if not d:
                continue
            cat = self._launcher._find_item_category(d)
            if cat is None:
                continue
            cat_idx = self._launcher.categories.index(cat)
            try:
                item_idx = cat["items"].index(d)
            except ValueError:
                continue
            payload_items.append({"cat": cat_idx, "idx": item_idx})
        if not payload_items:
            return super().mouseMoveEvent(e)
        mime = QMimeData()
        mime.setData(DRAG_MIME, json.dumps(payload_items).encode("utf-8"))
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

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self._launcher.delete_selected()
            return
        super().keyPressEvent(e)


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
            payload_items = json.loads(payload)
        except Exception as ex:
            config.log_msg(f"DropTabBar parse mime failed: {ex}")
            return
        dst_cat = self._tab_at_relaxed(e.pos())
        cats = self._launcher.categories
        if dst_cat < 0 or dst_cat >= len(cats):
            return
        moved = []
        by_cat = {}
        for it in payload_items:
            by_cat.setdefault(it["cat"], []).append(it["idx"])
        for cat_idx, idxs in by_cat.items():
            if cat_idx < 0 or cat_idx >= len(cats) or cat_idx == dst_cat:
                continue
            src = cats[cat_idx]["items"]
            for idx in sorted(idxs, reverse=True):
                if 0 <= idx < len(src):
                    moved.append(src.pop(idx))
        if not moved:
            return
        cats[dst_cat]["items"].extend(moved)
        config.save_config(self._launcher.config_data, cats)
        self._launcher.refresh_list()
        e.acceptProposedAction()



class CloseButton(QWidget):
    """Custom close button that draws a centered X with QPainter."""
    clicked = pyqtSignal()

    def __init__(self, parent=None, size=24):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._hovered = False
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hovered:
            p.setBrush(QColor(255, 60, 60, 150))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)
        pen = QPen(QColor(200, 200, 200) if self._hovered else QColor(170, 170, 170))
        pen.setWidth(2)
        p.setPen(pen)
        m = 7  # margin from edge
        p.drawLine(m, m, self.width() - m, self.height() - m)
        p.drawLine(self.width() - m, m, m, self.height() - m)
        p.end()


class LauncherWindow(QWidget):
    _icon_ready = pyqtSignal(int, int, object, object, object)  # gen, idx, payload_type, payload, cache_key
    _update_result = pyqtSignal(bool, str, str, str, bool)  # ok, latest, html_url, body, silent

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
        self._icon_cache = OrderedDict()  # LRU: max 500 entries
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
            et = ev.type()
            if self._drag_mode in ("resize", "move"):
                # Safety: if left button is no longer pressed, force-clear drag state
                if not (QApplication.mouseButtons() & Qt.LeftButton):
                    if self._drag_mode == "resize":
                        self._save_window_state()
                    self._drag_mode = None
                    self._resize_edge = None
                    self._resize_start_geom = None
                    self._resize_start_gpos = None
                    self.drag_pos = None
                    self.setCursor(Qt.ArrowCursor)
                elif et == QEvent.MouseMove:
                    gpos = ev.globalPos()
                    if self._drag_mode == "resize":
                        self._perform_resize(gpos)
                    elif self._drag_mode == "move" and self.drag_pos is not None:
                        self.move(gpos - self.drag_pos)
                    return False
                elif et == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                    if self._drag_mode == "resize":
                        self._save_window_state()
                    self._drag_mode = None
                    self._resize_edge = None
                    self._resize_start_geom = None
                    self._resize_start_gpos = None
                    self.drag_pos = None
                    return True
            if et == QEvent.MouseMove and self._drag_mode is None:
                lpos = self.mapFromGlobal(ev.globalPos())
                # Don't show resize cursor over child widgets (e.g. close button)
                child = self.childAt(lpos)
                if child and child is not self.bg:
                    edge = None
                else:
                    edge = self._hit_test(lpos)
                if edge != self._hover_edge:
                    self._hover_edge = edge
                    self._set_edge_cursor(edge)
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
        a_about = tray_menu.addAction("关于")
        a_about.triggered.connect(self.show_about)
        tray_menu.addSeparator()
        a3 = tray_menu.addAction("退出")
        a3.triggered.connect(self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_click)
        self.tray.show()

    def tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle()

    def _save_window_state(self):
        """Persist current window position and size to config."""
        self.config_data["pos_x"] = self.pos().x()
        self.config_data["pos_y"] = self.pos().y()
        self.config_data["window_width"] = self.width()
        self.config_data["window_height"] = self.height()
        config.save_config(self.config_data, self.categories)

    def hide_window(self):
        self._save_window_state()
        self.hide()

    def quit_app(self):
        self._save_window_state()
        config.flush_save_now()
        self._icon_loader.shutdown(wait=False)
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

    def show_about(self):
        AboutDialog(self).exec_()

    def check_update(self, silent=True):
        import threading as _th
        _th.Thread(target=self._do_check_update, args=(silent,), daemon=True).start()

    def _do_check_update(self, silent):
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest",
                headers={"User-Agent": "RunLauncher"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = _json.loads(r.read().decode("utf-8"))
            latest = str(data.get("tag_name", "")).lstrip("v")
            html_url = data.get("html_url", f"https://github.com/{config.GITHUB_REPO}/releases")
            body = data.get("body", "")
        except Exception as e:
            config.log_msg(f"check_update failed: {e}")
            self._update_result.emit(False, "", "", str(e), silent)
            return
        self._update_result.emit(True, latest, html_url, body, silent)

    def _on_update_result(self, ok, latest, html_url, body, silent):
        if not ok:
            if not silent:
                QMessageBox.warning(self, "检查更新", f"检查失败：{body}")
            return
        try:
            cur_parts = tuple(int(x) for x in config.VERSION.split("."))
            new_parts = tuple(int(x) for x in latest.split(".")) if latest else (0,)
        except Exception:
            cur_parts, new_parts = (0,), (0,)
        if new_parts > cur_parts:
            box = QMessageBox(self)
            box.setWindowTitle("发现新版本")
            box.setIcon(QMessageBox.Information)
            box.setText(f"当前版本 v{config.VERSION}\n最新版本 v{latest}")
            box.setInformativeText((body or "")[:500])
            box.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)
            box.button(QMessageBox.Open).setText("打开下载页")
            if box.exec_() == QMessageBox.Open:
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(html_url))
        elif not silent:
            QMessageBox.information(self, "检查更新", f"已是最新版本 v{config.VERSION}")

    def init_ui(self):
        w = self.config_data.get("window_width", 420)
        h = self.config_data.get("window_height", 480)
        self.setMinimumSize(MIN_W, MIN_H)
        self.resize(max(w, MIN_W), max(h, MIN_H))
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.bg = QWidget()
        self.bg.setStyleSheet("background: rgba(30,30,40,220); border-radius: 10px;")
        self.bg.setMouseTracking(True)
        bg_layout = QVBoxLayout(self.bg)
        bg_layout.setSpacing(6)

        title_text = self.config_data.get("title", "Run Launcher")
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("  " + title_text)
        self.title_label.setStyleSheet("color: white; font: bold 14px; padding: 4px 0;")
        self.title_label.setFixedHeight(28)
        self.btn_close = CloseButton(size=24)
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
        self.tabs.tabMoved.connect(self._on_tab_moved)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_menu)
        self.refresh_tabs()

        self.list = DragListWidget(self)
        self.list.setAcceptDrops(True)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
        self._update_result.connect(self._on_update_result)
        self.refresh_list()

        bg_layout.addLayout(title_bar)
        bg_layout.addWidget(self.search_box)
        bg_layout.addWidget(self.tabs)
        bg_layout.addWidget(self.list)

        layout.addWidget(self.bg)
        self.setLayout(layout)
        self._enable_mouse_tracking_recursive(self)

        self.bg.mousePressEvent = self._bg_mouse_press

    def _bg_mouse_press(self, e):
        if e.button() != Qt.LeftButton:
            return
        # Skip resize/move if clicking near a child widget (e.g. close button)
        child = self.childAt(e.pos())
        if child and child is not self.bg:
            return
        gpos = e.globalPos()
        lpos = self.mapFromGlobal(gpos)
        edge = self._hit_test(lpos)
        if edge:
            self._drag_mode = "resize"
            self._resize_edge = edge
            self._resize_start_geom = self.geometry()
            self._resize_start_gpos = gpos
            e.accept()
            return
        if e.pos().y() < 28:
            self._drag_mode = "move"
            self.drag_pos = gpos - self.pos()
            e.accept()

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

    def _on_tab_moved(self, from_idx, to_idx):
        if not (0 <= from_idx < len(self.categories) and 0 <= to_idx < len(self.categories)):
            return
        cat = self.categories.pop(from_idx)
        self.categories.insert(to_idx, cat)
        self.current_cat = to_idx
        config.save_config(self.config_data, self.categories)
        self.refresh_tabs()

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

    def launch_item(self, item, admin=False):
        data = item.data(Qt.UserRole)
        if not data:
            return
        path = data["path"]
        if not os.path.exists(path):
            real = path
            if path.lower().endswith(".lnk"):
                t = resolve_lnk_target(path)
                if t:
                    real = t
            if not os.path.exists(real):
                config.log_msg(f"launch_item failed: path not found: {path} (resolved: {real})")
                QMessageBox.warning(self, "启动失败",
                    f"找不到目标，可能已卸载或被移动：\n{path}\n\n解析路径：{real}")
                return
        self.hide()
        import threading as _th
        _th.Thread(target=self._startfile_bg, args=(path, admin), daemon=True).start()

    def _startfile_bg(self, path, admin=False):
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)
        except Exception:
            pass
        try:
            verb = "runas" if admin else "open"
            workdir = os.path.dirname(os.path.abspath(path))
            ret = _shell32.ShellExecuteW(None, verb, path, None, workdir, 1)
            if ret <= 32:
                config.log_msg(f"launch_item ShellExecuteW failed: {path}: verb={verb} ret={ret}")
                if not admin:
                    os.startfile(path)
        except Exception as e:
            config.log_msg(f"launch_item exception: {path}: {e}")
        try:
            ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass

    def item_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        menu = QMenu()
        selected = self.list.selectedItems()
        if data and item in selected and len(selected) > 1:
            act_del = menu.addAction(f"删除选中项 ({len(selected)})")
            act_del.triggered.connect(self.delete_selected)
        else:
            act_open = menu.addAction("打开路径")
            act_open.triggered.connect(lambda: self.open_item_path(data))
            act_admin = menu.addAction("以管理员身份运行")
            act_admin.triggered.connect(lambda: self.launch_item(item, admin=True))
            menu.addSeparator()
            act_edit = menu.addAction("编辑")
            act_edit.triggered.connect(lambda: self.edit_item(data))
            act_del = menu.addAction("删除")
            act_del.triggered.connect(lambda: self.delete_item(data))
        menu.exec_(self.list.mapToGlobal(pos))

    def open_item_path(self, data):
        path = data.get("path", "")
        if not path:
            return
        real = os.path.normpath(path)
        if path.lower().endswith(".lnk"):
            t = resolve_lnk_target(path)
            if t:
                real = os.path.normpath(t)
        folder = os.path.dirname(real)
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "打开路径失败",
                f"找不到文件夹：\n{folder}\n\n原路径：{path}")
            return
        try:
            import subprocess
            subprocess.Popen(["explorer", folder])
        except Exception as e:
            config.log_msg(f"open_item_path failed: {e}")
            QMessageBox.warning(self, "打开路径失败", str(e))

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

    def delete_selected(self):
        datas = [it.data(Qt.UserRole) for it in self.list.selectedItems() if it.data(Qt.UserRole)]
        if not datas:
            return
        for d in datas:
            cat = self._find_item_category(d)
            if cat is not None and d in cat["items"]:
                cat["items"].remove(d)
        config.save_config(self.config_data, self.categories)
        self.refresh_list()

    def _item_matches(self, item):
        text = self.filter_text
        if text in item["name"].lower():
            return True
        if text in pinyin_initials(item["name"]):
            return True
        path = item.get("path", "")
        if path and text in path.lower():
            return True
        if path and path.lower().endswith(".lnk"):
            t = resolve_lnk_target_cached(path)
            if t and text in t.lower():
                return True
        return False

    def refresh_list(self):
        self._refresh_gen += 1
        gen = self._refresh_gen
        self.list.clear()
        if self.filter_text:
            items = []
            for cat in self.categories:
                items.extend(it for it in cat["items"] if self._item_matches(it))
        else:
            items = self.current_items
        for idx, item in enumerate(items):
            li = QListWidgetItem(item["name"])
            li.setData(Qt.UserRole, item)
            li.setTextAlignment(Qt.AlignCenter)
            key = self._icon_cache_key(item)
            if key and key in self._icon_cache:
                self._icon_cache.move_to_end(key)
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

    def _on_icon_ready(self, gen, idx, payload_type, payload, key):
        if gen != self._refresh_gen:
            if payload_type == "hicon" and payload:
                try:
                    _user32.DestroyIcon(int(payload))
                except Exception:
                    pass
            return
        icon = None
        if payload_type == "hicon" and payload:
            h = int(payload)
            try:
                pix = QtWin.fromHICON(h)
                if pix and not pix.isNull():
                    icon = QIcon(pix)
            except Exception as e:
                config.log_msg(f"_on_icon_ready fromHICON failed: {e}")
            try:
                _user32.DestroyIcon(h)
            except Exception:
                pass
        elif payload_type == "image" and payload is not None:
            try:
                pix = QPixmap.fromImage(payload)
                if not pix.isNull():
                    icon = QIcon(pix)
            except Exception as e:
                config.log_msg(f"_on_icon_ready fromImage failed: {e}")
        elif payload_type == "qicon" and payload is not None:
            try:
                qic = payload
                if not qic.isNull():
                    icon = qic
            except Exception as e:
                config.log_msg(f"_on_icon_ready qicon failed: {e}")
        if icon is None:
            return
        if key:
            self._icon_cache[key] = icon
            self._icon_cache.move_to_end(key)
            while len(self._icon_cache) > 500:
                self._icon_cache.popitem(last=False)
        li = self.list.item(idx)
        if li is not None:
            li.setIcon(icon)

    def _load_icon_async(self, gen, idx, item):
        _co_init = False
        try:
            try:
                ctypes.windll.ole32.CoInitializeEx(None, 0x2)
                _co_init = True
            except Exception:
                pass
            payload_type, payload = self._extract_icon_payload(item)
        except Exception as e:
            config.log_msg(f"_load_icon_async({idx}): {e}")
            if _co_init:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass
            return
        if _co_init:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass
        if not payload:
            return
        key = self._icon_cache_key(item)
        self._icon_ready.emit(gen, idx, payload_type, payload, key)

    def _extract_icon_payload(self, item):
        icon_path = item.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            ext = os.path.splitext(icon_path)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".bmp", ".ico"):
                try:
                    img = QImage(icon_path)
                    if not img.isNull():
                        return "image", img
                except Exception:
                    pass
            h = shell_hicon(icon_path)
            if h:
                return "hicon", h
        path = item.get("path", "")
        if os.path.exists(path):
            h = shell_hicon(path)
            if h:
                return "hicon", h
        if path.lower().endswith(".lnk"):
            target = resolve_lnk_target(path)
            if target and target != path and os.path.exists(target):
                h = shell_hicon(target)
                if h:
                    return "hicon", h
        try:
            fb = QFileIconProvider().icon(QFileInfo(path))
            if not fb.isNull():
                return "qicon", fb
        except Exception as e:
            config.log_msg(f"_extract_icon_payload fallback failed for {path}: {e}")
        return None, None

    def _hit_test(self, pos):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        m = RESIZE_MARGIN
        cm = CORNER_MARGIN
        # Corners first (priority in the corner zones)
        c_left = x < cm
        c_right = x > w - cm
        c_top = y < cm
        c_bottom = y > h - cm
        if c_top and c_left: return "top_left"
        if c_top and c_right: return "top_right"
        if c_bottom and c_left: return "bottom_left"
        if c_bottom and c_right: return "bottom_right"
        # Edges (catches everything else along the border)
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
            self._save_window_state()
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
            self.list.viewport().update()
