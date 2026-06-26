import sys, os, json, winreg

CONFIG_FILE = "config.json"

def get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_FILE)

DEFAULT_CONFIG = {
    "hotkey": {"ctrl": False, "alt": True, "shift": False, "vk": 0x20},
    "window_width": 420, "window_height": 480,
    "title": "Run Launcher",
    "categories": [{"name": "默认", "items": []}]
}

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "RunLauncher"

def get_auto_start_cmd():
    if getattr(sys, 'frozen', False):
        return sys.executable
    pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
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
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
    if enabled:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, get_auto_start_cmd())
    else:
        try:
            winreg.DeleteValue(key, REG_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

def load_config():
    cfg_path = get_config_path()
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"hotkey": DEFAULT_CONFIG["hotkey"], "categories": [{"name": "默认", "items": data}]}
                if "categories" not in data and "items" in data:
                    data["categories"] = [{"name": "默认", "items": data.pop("items")}]
                return data
        except:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(config, categories):
    config["categories"] = categories
    cfg_path = get_config_path()
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass
