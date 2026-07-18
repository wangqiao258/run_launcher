import sys
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QAbstractNativeEventFilter
import config
from window import LauncherWindow


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
HOTKEY_ID = 1

_user32 = ctypes.windll.user32
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.UnregisterHotKey.restype = wintypes.BOOL


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._cb()
                    return True, 0
        except Exception as e:
            config.log_msg(f"nativeEventFilter error: {e}")
        return False, 0


def _build_modifiers(hk):
    mods = MOD_NOREPEAT
    if hk.get("alt"): mods |= MOD_ALT
    if hk.get("ctrl"): mods |= MOD_CONTROL
    if hk.get("shift"): mods |= MOD_SHIFT
    return mods


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    config.log_msg(f"Launcher started, frozen={getattr(sys,'frozen',False)}, exe={sys.executable}")
    config.log_msg(f"auto_start_cmd={config.get_auto_start_cmd()}")
    config.log_msg(f"auto_start_enabled={config.is_auto_start_enabled()}")
    config.log_msg(f"config_path={config.get_config_path()}")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = LauncherWindow()
    window.hide()

    hk = window.config_data.get("hotkey", config.DEFAULT_CONFIG["hotkey"])
    mods = _build_modifiers(hk)
    vk = hk.get("vk", 0x20)

    hotkey_filter = HotkeyFilter(window.toggle)
    app.installNativeEventFilter(hotkey_filter)

    if not _user32.RegisterHotKey(None, HOTKEY_ID, mods, vk):
        err = ctypes.get_last_error()
        config.log_msg(f"RegisterHotKey failed: err={err} mods={mods:#x} vk={vk:#x}")
    else:
        config.log_msg(f"RegisterHotKey OK: mods={mods:#x} vk={vk:#x}")

    def _cleanup():
        try:
            _user32.UnregisterHotKey(None, HOTKEY_ID)
        except Exception as e:
            config.log_msg(f"UnregisterHotKey error: {e}")
        try:
            config.flush_save_now()
        except Exception as e:
            config.log_msg(f"flush_save_now error: {e}")

    app.aboutToQuit.connect(_cleanup)

    sys.exit(app.exec_())
