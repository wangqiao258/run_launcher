import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
import win32api
import config
from window import LauncherWindow

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

    hotkey_state = {"pressed": False}
    hk = window.config_data.get("hotkey", config.DEFAULT_CONFIG["hotkey"])
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
