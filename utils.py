import os, time, ctypes
from ctypes import wintypes, POINTER, byref, c_int, c_uint, c_ulong, Structure
import win32com.client
import config


# ---------------------------------------------------------------------------
# Windows shell icon extraction
# ---------------------------------------------------------------------------

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
_shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, c_int]
_shell32.ShellExecuteW.restype = wintypes.HINSTANCE
_user32.DestroyIcon.argtypes = [wintypes.HICON]
_user32.DestroyIcon.restype = wintypes.BOOL


def shell_hicon(path):
    """Extract a large-icon HICON for *path* via SHGetFileInfoW.

    Retries up to 3 times with a short delay to handle transient file-locking.
    Returns the HICON as an int, or 0 on failure.  The caller is responsible
    for calling ``_user32.DestroyIcon(h)`` when done.
    """
    for attempt in range(3):
        info = _SHFILEINFO()
        ret = _shell32.SHGetFileInfoW(path, 0, byref(info), ctypes.sizeof(info),
                                      _SHGFI_ICON | _SHGFI_LARGEICON)
        if ret and info.hIcon:
            return int(info.hIcon)
        if attempt < 2:
            time.sleep(0.02)
    return 0


# ---------------------------------------------------------------------------
# .lnk shortcut target resolution
# ---------------------------------------------------------------------------

_LNK_SHELL = None

def resolve_lnk_target(path):
    """Resolve a Windows ``.lnk`` shortcut to its target path.

    Returns the target path string if it exists on disk, otherwise ``None``.
    Recursively follows chained ``.lnk`` files (up to a reasonable depth).
    """
    global _LNK_SHELL
    try:
        if _LNK_SHELL is None:
            _LNK_SHELL = win32com.client.Dispatch("WScript.Shell")
        sc = _LNK_SHELL.CreateShortcut(path)
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

_GB2312_FIRST = [
    (0xB0A1, 0xB0C4, 'a'), (0xB0C5, 0xB2C0, 'b'), (0xB2C1, 0xB4ED, 'c'),
    (0xB4EE, 0xB6E9, 'd'), (0xB6EA, 0xB7A1, 'e'), (0xB7A2, 0xB8C0, 'f'),
    (0xB8C1, 0xB9FD, 'g'), (0xB9FE, 0xBBF6, 'h'), (0xBBF7, 0xBFA5, 'j'),
    (0xBFA6, 0xC0AB, 'k'), (0xC0AC, 0xC2E7, 'l'), (0xC2E8, 0xC4C2, 'm'),
    (0xC4C3, 0xC5B5, 'n'), (0xC5B6, 0xC5BD, 'o'), (0xC5BE, 0xC6D9, 'p'),
    (0xC6DA, 0xC8BA, 'q'), (0xC8BB, 0xC8F5, 'r'), (0xC8F6, 0xCBF9, 's'),
    (0xCBFA, 0xCDD9, 't'), (0xCDDA, 0xCEF3, 'w'), (0xCEF4, 0xD188, 'x'),
    (0xD1B9, 0xD4D0, 'y'), (0xD4D1, 0xD7F9, 'z'),
]

def pinyin_initials(text):
    """Return the lowercase pinyin-initial string for *text*.

    Chinese characters are converted to their GB-2312 first-letter
    approximation; non-Chinese characters are passed through lowercase.
    Example: ``pinyin_initials("微信")`` → ``"wx"``.
    """
    out = []
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            try:
                b = ch.encode('gb2312')
            except Exception:
                out.append(ch.lower())
                continue
            code = (b[0] << 8) | b[1]
            for lo, hi, letter in _GB2312_FIRST:
                if lo <= code <= hi:
                    out.append(letter)
                    break
            else:
                out.append(ch.lower())
        else:
            out.append(ch.lower())
    return ''.join(out)
