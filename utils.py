import os, time, ctypes, winreg
from ctypes import wintypes
import win32gui
import win32api
import win32com.client
import config
from PyQt5.QtCore import Qt

_user32 = ctypes.windll.user32
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.UnregisterHotKey.restype = wintypes.BOOL


# ---------------------------------------------------------------------------
# Windows shell icon extraction
# ---------------------------------------------------------------------------


def shell_hicon(path):
    """Extract a large-icon HICON for *path* via ExtractIconEx.

    Retries up to 3 times with a short delay to handle transient file-locking.
    Returns the HICON as an int, or 0 on failure.  The caller is responsible
    for calling ``win32gui.DestroyIcon(h)`` when done.
    """
    for attempt in range(3):
        try:
            icons = win32gui.ExtractIconEx(path, 0)
            if icons:
                large, small = icons
                chosen = large[0] if large else (small[0] if small else 0)
                for handle in set(large + small):
                    if handle and handle != chosen:
                        win32gui.DestroyIcon(handle)
                if chosen:
                    return chosen
        except Exception:
            pass
        if attempt < 2:
            time.sleep(0.02)
    return 0


# ---------------------------------------------------------------------------
# .lnk shortcut target resolution
# ---------------------------------------------------------------------------

def resolve_lnk_target(path):
    """Resolve a Windows ``.lnk`` shortcut to its target path.

    Returns the target path string if it exists on disk, otherwise ``None``.
    Recursively follows chained ``.lnk`` files (up to a reasonable depth).
    """
    try:
        # COM objects belong to their apartment; never share a shell across threads.
        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortcut(path)
        t = sc.TargetPath
        if t and os.path.exists(t):
            return t
        if t and t.lower().endswith(".lnk") and os.path.exists(t):
            return resolve_lnk_target(t)
    except Exception as e:
        config.log_msg(f"resolve_lnk_target failed for {path}: {e}")
    return None


_lnk_target_cache = {}

def resolve_lnk_target_cached(path):
    """Cached wrapper around :func:`resolve_lnk_target`."""
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0
    key = (path, mtime)
    if key in _lnk_target_cache:
        return _lnk_target_cache[key]
    t = resolve_lnk_target(path)
    if len(_lnk_target_cache) > 512:
        _lnk_target_cache.clear()
    _lnk_target_cache[key] = t
    return t


# ---------------------------------------------------------------------------
# Chinese pinyin initial extraction (for fuzzy search)
# ---------------------------------------------------------------------------
from pypinyin import pinyin, Style


def pinyin_initials(text):
    """Return the lowercase pinyin-initial string for *text*.

    Chinese characters are converted to their pinyin first letter;
    non-Chinese characters are passed through lowercase.
    Example: ``pinyin_initials("微信")`` → ``"wx"``.
    """
    out = []
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            initial = pinyin(ch, style=Style.FIRST_LETTER)
            out.append(initial[0][0])
        else:
            out.append(ch.lower())
    return ''.join(out)

# ---------------------------------------------------------------------------
# Mouse speed (SystemParametersInfo, range 1-20, 10 = Windows default)
# ---------------------------------------------------------------------------

SPI_GETMOUSESPEED = 0x00E8
SPI_SETMOUSESPEED = 0x0071
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002

_user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
_user32.SystemParametersInfoW.restype = wintypes.BOOL


def _reg_mouse_speed():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse") as k:
            v, _ = winreg.QueryValueEx(k, "MouseSensitivity")
        return max(1, min(20, int(v)))
    except Exception:
        return None


def get_mouse_speed():
    """Return the current system mouse speed (1-20); SPI first, registry fallback."""
    val = wintypes.UINT(0)
    if _user32.SystemParametersInfoW(SPI_GETMOUSESPEED, 0, ctypes.byref(val), 0) and val.value:
        return val.value
    speed = _reg_mouse_speed()
    if speed is None:
        config.log_msg(f"get_mouse_speed failed: err={ctypes.get_last_error()}")
        return 10
    return speed


def set_mouse_speed(speed):
    """Set the system mouse speed (clamped to 1-20), persisted like the OS slider."""
    speed = max(1, min(20, int(speed)))
    ok = _user32.SystemParametersInfoW(SPI_SETMOUSESPEED, 0, ctypes.c_void_p(speed),
                                       SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
    if not ok:
        config.log_msg(f"set_mouse_speed failed: err={ctypes.get_last_error()}")
    return speed


def next_mouse_speed(current, presets):
    """Next preset strictly greater than *current*, wrapping to the first preset."""
    ups = [p for p in presets if p > current]
    return ups[0] if ups else presets[0]


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

Qt_ControlModifier = 0x04000000
Qt_AltModifier    = 0x08000000
Qt_ShiftModifier  = 0x02000000
Qt_KeyCodeMask    = 0x01FFFFFF


def build_modifiers(hk):
    """Build Windows MOD_* bitmask from a hotkey dict."""
    mods = MOD_NOREPEAT
    if hk.get('alt'):   mods |= MOD_ALT
    if hk.get('ctrl'):  mods |= MOD_CONTROL
    if hk.get('shift'): mods |= MOD_SHIFT
    return mods


def keyseq_to_hotkey(seq_str):
    """Convert a QKeySequence string (e.g. 'Alt+Space') to a hotkey dict."""
    from PyQt5.QtGui import QKeySequence
    seq = QKeySequence(seq_str)
    if seq.isEmpty():
        return None
    combined = seq[0]  # PyQt5 returns int: key in lower bits, modifiers in upper bits
    qt_key = combined & Qt_KeyCodeMask
    qt_mods = combined & ~Qt_KeyCodeMask
    return {
        'ctrl': bool(qt_mods & Qt_ControlModifier),
        'alt': bool(qt_mods & Qt_AltModifier),
        'shift': bool(qt_mods & Qt_ShiftModifier),
        'vk': qt_key_to_vk(qt_key),
    }


def hotkey_to_keyseq(hk):
    """Convert a hotkey dict to a QKeySequence string."""
    parts = []
    if hk.get('ctrl'):  parts.append('Ctrl')
    if hk.get('alt'):   parts.append('Alt')
    if hk.get('shift'): parts.append('Shift')
    parts.append(vk_to_display(hk.get('vk', 0)))
    return '+'.join(parts)


# ---------------------------------------------------------------------------
# Hotkey helpers
# ---------------------------------------------------------------------------

# Qt key code → Windows VK code
_QT_TO_VK = {
    Qt.Key_Escape: 0x1B, Qt.Key_Tab: 0x09, Qt.Key_Backtab: 0x09,
    Qt.Key_Backspace: 0x08, Qt.Key_Return: 0x0D, Qt.Key_Enter: 0x0D,
    Qt.Key_Insert: 0x2D, Qt.Key_Delete: 0x2E, Qt.Key_Pause: 0x13,
    Qt.Key_Print: 0x2C, Qt.Key_SysReq: 0x2C,
    Qt.Key_Clear: 0x0C, Qt.Key_Home: 0x24, Qt.Key_End: 0x23,
    Qt.Key_Left: 0x25, Qt.Key_Up: 0x26, Qt.Key_Right: 0x27, Qt.Key_Down: 0x28,
    Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22,
    Qt.Key_Space: 0x20, Qt.Key_CapsLock: 0x14, Qt.Key_NumLock: 0x90, Qt.Key_ScrollLock: 0x91,
    Qt.Key_F1: 0x70, Qt.Key_F2: 0x71, Qt.Key_F3: 0x72, Qt.Key_F4: 0x73,
    Qt.Key_F5: 0x74, Qt.Key_F6: 0x75, Qt.Key_F7: 0x76, Qt.Key_F8: 0x77,
    Qt.Key_F9: 0x78, Qt.Key_F10: 0x79, Qt.Key_F11: 0x7A, Qt.Key_F12: 0x7B,
    Qt.Key_F13: 0x7C, Qt.Key_F14: 0x7D, Qt.Key_F15: 0x7E, Qt.Key_F16: 0x7F,
    Qt.Key_F17: 0x80, Qt.Key_F18: 0x81, Qt.Key_F19: 0x82, Qt.Key_F20: 0x83,
    Qt.Key_F21: 0x84, Qt.Key_F22: 0x85, Qt.Key_F23: 0x86, Qt.Key_F24: 0x87,
    Qt.Key_Multi_key: 0x15, Qt.Key_SingleCandidate: 0x16,
}

# Windows VK code → display name
_VK_DISPLAY = {
    0x1B: 'Esc', 0x09: 'Tab', 0x08: 'Backspace', 0x0D: 'Enter',
    0x2D: 'Insert', 0x2E: 'Delete', 0x13: 'Pause', 0x2C: 'PrintScreen',
    0x0C: 'Clear', 0x24: 'Home', 0x23: 'End', 0x20: 'Space',
    0x25: 'Left', 0x26: 'Up', 0x27: 'Right', 0x28: 'Down',
    0x21: 'PageUp', 0x22: 'PageDown',
    0x14: 'CapsLock', 0x90: 'NumLock', 0x91: 'ScrollLock',
}
for i in range(1, 25):
    _VK_DISPLAY[0x6F + i] = f'F{i}'  # F1=0x70 … F24=0x87


def qt_key_to_vk(qt_key):
    """Convert a Qt key code to a Windows VK code."""
    if qt_key in _QT_TO_VK:
        return _QT_TO_VK[qt_key]
    # Letters (Qt Key_A=0x41 … Key_Z=0x5A, same as ASCII/VK)
    if 0x41 <= qt_key <= 0x5A:
        return qt_key
    # Digits (Qt Key_0=0x30 … Key_9=0x39, same as ASCII/VK)
    if 0x30 <= qt_key <= 0x39:
        return qt_key
    return qt_key  # fallback: hope VK matches


def vk_to_display(vk):
    """Return a human-readable name for a Windows VK code."""
    if vk in _VK_DISPLAY:
        return _VK_DISPLAY[vk]
    if ord('A') <= vk <= ord('Z'):
        return chr(vk)
    if ord('0') <= vk <= ord('9'):
        return chr(vk)
    return f'0x{vk:02X}'


def hotkey_to_display(hk):
    """Return a display string like 'Ctrl + Alt + A' for a hotkey dict."""
    parts = []
    if hk.get('ctrl'):  parts.append('Ctrl')
    if hk.get('alt'):   parts.append('Alt')
    if hk.get('shift'): parts.append('Shift')
    parts.append(vk_to_display(hk.get('vk', 0)))
    return ' + '.join(parts)
