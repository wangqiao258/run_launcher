from PyQt5.QtWidgets import (QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QCheckBox, QFileDialog, QWidget)
from PyQt5.QtCore import Qt, QEvent, QAbstractNativeEventFilter
from PyQt5.QtGui import QDesktopServices, QKeyEvent
from PyQt5.QtCore import QUrl
import ctypes
from ctypes import wintypes, CFUNCTYPE, c_int, Structure
import config
from utils import hotkey_to_keyseq

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0
VK_MENU = 0x12
LLKHF_ALTDOWN = 0x0020

_user32 = ctypes.windll.user32
_user32.SetWindowsHookExW.argtypes = [c_int, CFUNCTYPE(c_int, c_int, wintypes.WPARAM, wintypes.LPARAM), wintypes.HINSTANCE, wintypes.DWORD]
_user32.SetWindowsHookExW.restype = wintypes.HHOOK
_user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
_user32.UnhookWindowsHookEx.restype = wintypes.BOOL
_user32.CallNextHookEx.argtypes = [wintypes.HHOOK, c_int, wintypes.WPARAM, wintypes.LPARAM]
_user32.CallNextHookEx.restype = c_int


class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [('vkCode', wintypes.DWORD),
                ('scanCode', wintypes.DWORD),
                ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]


_VK_TO_QT = {
    0x20: Qt.Key_Space, 0x0D: Qt.Key_Return, 0x1B: Qt.Key_Escape,
    0x09: Qt.Key_Tab, 0x08: Qt.Key_Backspace, 0x2E: Qt.Key_Delete,
    0x2D: Qt.Key_Insert, 0x26: Qt.Key_Up, 0x28: Qt.Key_Down,
    0x25: Qt.Key_Left, 0x27: Qt.Key_Right, 0x21: Qt.Key_PageUp,
    0x22: Qt.Key_PageDown, 0x24: Qt.Key_Home, 0x23: Qt.Key_End,
    0x70: Qt.Key_F1, 0x71: Qt.Key_F2, 0x72: Qt.Key_F3, 0x73: Qt.Key_F4,
    0x74: Qt.Key_F5, 0x75: Qt.Key_F6, 0x76: Qt.Key_F7, 0x77: Qt.Key_F8,
    0x78: Qt.Key_F9, 0x79: Qt.Key_F10, 0x7A: Qt.Key_F11, 0x7B: Qt.Key_F12,
}
for c in range(ord('A'), ord('Z') + 1):
    _VK_TO_QT[c] = c
for c in range(ord('0'), ord('9') + 1):
    _VK_TO_QT[c] = c

STYLE_DLG = """
QDialog { background: #333; }
QLabel { color: white; }
QLineEdit { background: #555; color: white; border: 1px solid #777; padding: 4px; }
QPushButton { background: #555; color: white; border: 1px solid #777; padding: 6px 20px; }
QPushButton:hover { background: #666; }
QCheckBox { color: white; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #777; border-radius: 3px; background: #555; }
QCheckBox::indicator:checked { background: #4a9eff; border-color: #4a9eff; }
QCheckBox::indicator:hover { border-color: #aaa; }
"""
STYLE_INPUT = "background: #555; color: white; border: 1px solid #777; padding: 4px;"
STYLE_BTN = "background: #555; color: white; border: 1px solid #777; padding: 6px;"

_KEY_NAMES = {
    Qt.Key_Space: 'Space', Qt.Key_Return: 'Enter', Qt.Key_Enter: 'Enter',
    Qt.Key_Escape: 'Esc', Qt.Key_Tab: 'Tab', Qt.Key_Backspace: 'Backspace',
    Qt.Key_Delete: 'Delete', Qt.Key_Insert: 'Insert',
    Qt.Key_Up: 'Up', Qt.Key_Down: 'Down', Qt.Key_Left: 'Left', Qt.Key_Right: 'Right',
    Qt.Key_PageUp: 'PageUp', Qt.Key_PageDown: 'PageDown',
    Qt.Key_Home: 'Home', Qt.Key_End: 'End',
    Qt.Key_CapsLock: 'CapsLock', Qt.Key_NumLock: 'NumLock',
    Qt.Key_F1: 'F1', Qt.Key_F2: 'F2', Qt.Key_F3: 'F3', Qt.Key_F4: 'F4',
    Qt.Key_F5: 'F5', Qt.Key_F6: 'F6', Qt.Key_F7: 'F7', Qt.Key_F8: 'F8',
    Qt.Key_F9: 'F9', Qt.Key_F10: 'F10', Qt.Key_F11: 'F11', Qt.Key_F12: 'F12',
    Qt.Key_F13: 'F13', Qt.Key_F14: 'F14', Qt.Key_F15: 'F15', Qt.Key_F16: 'F16',
    Qt.Key_F17: 'F17', Qt.Key_F18: 'F18', Qt.Key_F19: 'F19', Qt.Key_F20: 'F20',
    Qt.Key_F21: 'F21', Qt.Key_F22: 'F22', Qt.Key_F23: 'F23', Qt.Key_F24: 'F24',
    Qt.Key_Minus: '-', Qt.Key_Equal: '=', Qt.Key_BracketLeft: '[',
    Qt.Key_BracketRight: ']', Qt.Key_Backslash: '\\', Qt.Key_Semicolon: ';',
    Qt.Key_Apostrophe: "'", Qt.Key_QuoteLeft: '`', Qt.Key_Comma: ',',
    Qt.Key_Period: '.', Qt.Key_Slash: '/',
}
_MOD_KEYS = {Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta, Qt.Key_AltGr}


STYLE_INPUT_RECORDING = "background: #444; color: #4a9eff; border: 2px solid #4a9eff; padding: 4px;"

class ShortcutEdit(QLineEdit):
    """Capture keyboard shortcuts. Uses event filter + low-level hook for Alt combos."""

    _hook = None
    _cb = None
    _target = None

    @classmethod
    def _hook_proc(cls, nCode, wParam, lParam):
        if nCode == HC_ACTION and cls._target and cls._target.hasFocus():
            kbd = KBDLLHOOKSTRUCT.from_address(lParam)
            alt_held = bool(kbd.flags & LLKHF_ALTDOWN)
            if alt_held and wParam == WM_SYSKEYDOWN and kbd.vkCode != VK_MENU:
                qt_key = _VK_TO_QT.get(kbd.vkCode, kbd.vkCode)
                from PyQt5.QtCore import QTimer
                name = _KEY_NAMES.get(qt_key, chr(kbd.vkCode) if 0x30 <= kbd.vkCode <= 0x7A else f'0x{kbd.vkCode:02X}')
                QTimer.singleShot(0, lambda n=name: cls._target.setText(f'Alt+{n}') if cls._target else None)
                return 1
        return _user32.CallNextHookEx(cls._hook, nCode, wParam, lParam)

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setReadOnly(True)
        self.installEventFilter(self)
        self.setStyleSheet(STYLE_INPUT)
        self._normal_style = STYLE_INPUT
        self._recording_style = STYLE_INPUT_RECORDING

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.setStyleSheet(self._recording_style)
        self.setPlaceholderText("请按快捷键...")
        if not ShortcutEdit._hook:
            ShortcutEdit._target = self
            ShortcutEdit._cb = CFUNCTYPE(c_int, c_int, wintypes.WPARAM, wintypes.LPARAM)(ShortcutEdit._hook_proc)
            ShortcutEdit._hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, ShortcutEdit._cb, None, 0)

    def focusOutEvent(self, e):
        if ShortcutEdit._hook:
            _user32.UnhookWindowsHookEx(ShortcutEdit._hook)
            ShortcutEdit._hook = None
            ShortcutEdit._cb = None
            ShortcutEdit._target = None
        self.setStyleSheet(self._normal_style)
        self.setPlaceholderText("")
        super().focusOutEvent(e)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            mods = int(event.modifiers())
            if key == Qt.Key_Escape:
                self.clear()
                return True
            if key == 0 and mods == 0:
                return True
            # Only accept if there is at least one non-modifier key
            if key in _MOD_KEYS:
                return True  # consume the event but don't record yet
            parts = []
            if mods & Qt.ControlModifier:  parts.append('Ctrl')
            if mods & Qt.AltModifier:     parts.append('Alt')
            if mods & Qt.ShiftModifier:   parts.append('Shift')
            if mods & Qt.MetaModifier:    parts.append('Meta')
            name = _KEY_NAMES.get(key)
            if name is None:
                if 0x41 <= key <= 0x5A:   name = chr(key)
                elif 0x30 <= key <= 0x39:  name = chr(key)
                else: name = f'0x{key:02X}'
            parts.append(name)
            self.setText('+'.join(parts))
            return True
        return False


class SettingsDialog(QDialog):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.resize(320, 260)
        self.setStyleSheet(STYLE_DLG)

        form = QFormLayout(self)
        self.de_title = QLineEdit(config_data.get("title", "Run Launcher"))
        self.de_title.setStyleSheet(STYLE_INPUT)

        hk_str = config_data.get('hotkey', config.DEFAULT_CONFIG['hotkey'])
        self.hotkey_edit = ShortcutEdit(hk_str)
        self.hotkey_edit.setFixedHeight(28)

        self.cb_autostart = QCheckBox("开机自启动")
        self.cb_autostart.setChecked(config.is_auto_start_enabled())

        form.addRow("标题:", self.de_title)
        form.addRow("呼出热键:", self.hotkey_edit)
        form.addRow("", self.cb_autostart)

        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def get_values(self):
        hotkey = self.hotkey_edit.text().strip()
        if not hotkey:
            hotkey = self.config_data.get('hotkey', config.DEFAULT_CONFIG['hotkey'])
        return {
            "title": self.de_title.text(),
            "hotkey": hotkey,
            "autostart": self.cb_autostart.isChecked(),
        }


class InputDialog(QDialog):
    def __init__(self, parent, title, label, default=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.ed = QLineEdit(default)
        self.ed.setStyleSheet(STYLE_INPUT)
        layout.addWidget(self.ed)
        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_text(self):
        return self.ed.text().strip() if self.result() == QDialog.Accepted else None


class EditItemDialog(QDialog):
    def __init__(self, parent, name, path, icon_path=""):
        super().__init__(parent)
        self.setWindowTitle("编辑")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(420)
        form = QFormLayout(self)
        self.ed_name = QLineEdit(name)
        self.ed_name.setStyleSheet(STYLE_INPUT)
        self.ed_path = QLineEdit(path)
        self.ed_path.setStyleSheet(STYLE_INPUT)
        self.ed_icon = QLineEdit(icon_path or "")
        self.ed_icon.setStyleSheet(STYLE_INPUT)
        self.ed_icon.setPlaceholderText("留空则自动提取；支持 .ico .png .exe .dll")
        icon_row = QWidget()
        icon_row_layout = QHBoxLayout(icon_row)
        icon_row_layout.setContentsMargins(0, 0, 0, 0)
        icon_row_layout.addWidget(self.ed_icon, 1)
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet(STYLE_BTN)
        btn_browse.clicked.connect(self._pick_icon)
        btn_clear = QPushButton("清空")
        btn_clear.setStyleSheet(STYLE_BTN)
        btn_clear.clicked.connect(lambda: self.ed_icon.setText(""))
        icon_row_layout.addWidget(btn_browse)
        icon_row_layout.addWidget(btn_clear)
        form.addRow("名称:", self.ed_name)
        form.addRow("路径:", self.ed_path)
        form.addRow("图标:", icon_row)
        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def _pick_icon(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择图标",
            self.ed_icon.text() or "",
            "图标文件 (*.ico *.png *.jpg *.jpeg *.bmp *.exe *.dll);;所有文件 (*.*)")
        if f:
            self.ed_icon.setText(f)

    def get_values(self):
        import os
        name = self.ed_name.text().strip()
        path = self.ed_path.text().strip()
        icon_path = self.ed_icon.text().strip()
        if name and path and os.path.exists(path):
            result = {"name": name, "path": path}
            if icon_path and os.path.exists(icon_path):
                result["icon_path"] = icon_path
            return result
        return None


class AboutDialog(QDialog):
    def __init__(self, parent, config_data=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Run Launcher")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"版本 v{config.VERSION}")
        ver.setStyleSheet("color: #ccc;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        hk_str = (config_data or {}).get('hotkey', config.DEFAULT_CONFIG['hotkey'])
        desc = QLabel(f"Windows 快速启动器\n{hk_str} 全局呼出")
        desc.setStyleSheet("color: #aaa;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        row = QHBoxLayout()
        btn_github = QPushButton("GitHub")
        btn_github.setStyleSheet(STYLE_BTN)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{config.GITHUB_REPO}")))
        btn_update = QPushButton("检查更新")
        btn_update.setStyleSheet(STYLE_BTN)
        btn_update.clicked.connect(lambda: (self.accept(), parent.check_update(silent=False)))
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(STYLE_BTN)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_github)
        row.addWidget(btn_update)
        row.addWidget(btn_close)
        layout.addLayout(row)
