import sys, os, json, winreg
from datetime import datetime

CONFIG_FILE = "config.json"

def get_config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "RunLauncher")
    os.makedirs(d, exist_ok=True)
    return d

def get_legacy_config_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_FILE)

def get_config_path():
    return os.path.join(get_config_dir(), CONFIG_FILE)

DEFAULT_CONFIG = {
    "hotkey": {"ctrl": False, "alt": True, "shift": False, "vk": 0x20},
    "window_width": 420, "window_height": 480,
    "title": "Run Launcher",
    "categories": [{"name": "\u9ed8\u8ba4", "items": []}]
}

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "RunLauncher"

def get_auto_start_cmd():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.exists(pythonw):
        return f'"{pythonw}" "{os.path.abspath(__file__)}"'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def is_auto_start_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return val == get_auto_start_cmd()
    except:
        return False

def set_auto_start(enabled):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    if enabled:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, get_auto_start_cmd())
    else:
        try:
            winreg.DeleteValue(key, REG_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

def load_config():
    # try new path first, then legacy path
    cfg_path = get_config_path()
    if not os.path.exists(cfg_path):
        legacy = get_legacy_config_path()
        if os.path.exists(legacy):
            try:
                with open(legacy, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.remove(legacy)
                return _normalize_config(data)
            except:
                pass
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _normalize_config(data)
        except:
            pass
    return dict(DEFAULT_CONFIG)

def _normalize_config(data):
    if isinstance(data, list):
        return {"hotkey": DEFAULT_CONFIG["hotkey"], "categories": [{"name": "\u9ed8\u8ba4", "items": data}]}
    if "categories" not in data and "items" in data:
        data["categories"] = [{"name": "\u9ed8\u8ba4", "items": data.pop("items")}]
    return data

def save_config(config, categories):
    config["categories"] = categories
    cfg_path = get_config_path()
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
