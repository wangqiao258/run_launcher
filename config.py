import sys, os, json, winreg, threading
from datetime import datetime

CONFIG_FILE = "config.json"

def get_config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "RunLauncher")
    os.makedirs(d, exist_ok=True)
    return d

def get_config_path():
    return os.path.join(get_config_dir(), CONFIG_FILE)

def log_path():
    return os.path.join(get_config_dir(), "startup.log")

def log_msg(msg):
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

def get_legacy_config_path():
    base = os.path.dirname(os.path.abspath(sys.executable))
    return os.path.join(base, CONFIG_FILE)

def _is_frozen():
    return getattr(sys, "frozen", False) or hasattr(sys, "nuitka")

def _detect_exe_path():
    if _is_frozen():
        return os.path.abspath(sys.executable)
    return os.path.abspath(sys.argv[0])

DEFAULT_CONFIG = {
    "hotkey": {"ctrl": False, "alt": True, "shift": False, "vk": 0x20},
    "window_width": 420, "window_height": 480,
    "title": "Run Launcher",
    "categories": [{"name": "默认", "items": []}]
}

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "RunLauncher"

def get_auto_start_cmd():
    exe = _detect_exe_path()
    return f'"{exe}"'

def is_auto_start_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return val == get_auto_start_cmd()
    except:
        return False

def set_auto_start(enabled):
    if enabled:
        cmd = get_auto_start_cmd()
        log_msg(f"set_auto_start(True): cmd={cmd}")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    if enabled:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, cmd)
        winreg.FlushKey(key)
        verified, _ = winreg.QueryValueEx(key, REG_NAME)
        if verified != cmd:
            log_msg(f"set_auto_start: verification FAILED: wrote={cmd}, read={verified}")
        else:
            log_msg(f"set_auto_start: verified OK")
    else:
        try:
            winreg.DeleteValue(key, REG_NAME)
            log_msg("set_auto_start(False): removed")
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

def load_config():
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
        return {"hotkey": DEFAULT_CONFIG["hotkey"], "categories": [{"name": "默认", "items": data}]}
    if "categories" not in data and "items" in data:
        data["categories"] = [{"name": "默认", "items": data.pop("items")}]
    return data

def save_config(config, categories):
    config["categories"] = categories
    _schedule_save(dict(config))


_save_lock = threading.Lock()
_save_pending = None
_save_timer = None


def _do_save(cfg_snapshot):
    cfg_path = get_config_path()
    try:
        tmp_path = cfg_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg_snapshot, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, cfg_path)
    except Exception as e:
        log_msg(f"save_config failed: {e}")


def _schedule_save(cfg_snapshot, delay=0.25):
    global _save_pending, _save_timer
    with _save_lock:
        _save_pending = cfg_snapshot
        if _save_timer is not None and _save_timer.is_alive():
            _save_timer.cancel()
        _save_timer = threading.Timer(delay, _flush_save)
        _save_timer.daemon = True
        _save_timer.start()


def _flush_save():
    global _save_pending
    with _save_lock:
        snapshot = _save_pending
        _save_pending = None
    if snapshot is not None:
        _do_save(snapshot)


def flush_save_now():
    global _save_timer
    with _save_lock:
        if _save_timer is not None and _save_timer.is_alive():
            _save_timer.cancel()
    _flush_save()
