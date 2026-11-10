# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# RUNLAUNCHER_SLIM=1 creates a separate lean build; the default stays full-size.
slim = os.environ.get('RUNLAUNCHER_SLIM') == '1'

datas = []
datas += collect_data_files('pypinyin')


a = Analysis(
    [str(Path(SPECPATH) / 'main.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PyQt5.QtWinExtras', 'win32timezone'] + (['_sha2'] if slim else []),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Cache hashes use CPython's built-in SHA implementation, not OpenSSL.
    excludes=['_hashlib', '_ssl', 'ssl'] if slim else [],
    noarchive=False,
    optimize=0,
)

if slim:
    # This app uses raster QWidget painting, not QML, WebGL, or OpenGL widgets.
    qt_dlls = {'qt5core.dll', 'qt5gui.dll', 'qt5widgets.dll', 'qt5winextras.dll',
               'msvcp140.dll', 'msvcp140_1.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}
    qt_plugins = {'qwindows.dll', 'qoffscreen.dll', 'qjpeg.dll', 'qico.dll',
                  'qwindowsvistastyle.dll'}
    openssl_dlls = {'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
                    'libcrypto-1_1.dll', 'libssl-1_1.dll'}

    def keep_binary(entry):
        name = entry[0].replace('\\', '/').lower()
        leaf = name.rsplit('/', 1)[-1]
        if name.startswith('pyqt5/qt5/plugins/'):
            return leaf in qt_plugins
        if name.startswith('pyqt5/qt5/bin/'):
            return leaf in qt_dlls
        return leaf not in openssl_dlls

    removed = [entry[0] for entry in a.binaries if not keep_binary(entry)]
    a.binaries = [entry for entry in a.binaries if keep_binary(entry)]
    # Translations are unused: the application's text is supplied in Chinese.
    a.datas = [entry for entry in a.datas
               if '/translations/' not in entry[0].replace('\\', '/').lower()]
    print('Slim build removed %d optional binaries:' % len(removed))
    for name in removed:
        print('  ' + name)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Launcher-slim' if slim else 'Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
