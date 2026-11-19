# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


PROJECT_ROOT = Path(SPECPATH)
ICON_FILE = PROJECT_ROOT / "assets" / "gestione_turni.ico"
VERSION_FILE = PROJECT_ROOT / "version_info.txt"


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(ICON_FILE), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt 6 on Windows uses the operating system's ICU implementation. An unrelated
# ICU (e.g. from Poppler/Conda on PATH) exports version-suffixed symbols and makes
# QtCore fail at startup when PyInstaller accidentally bundles it.
if sys.platform == "win32":
    a.binaries = [
        entry for entry in a.binaries
        if Path(entry[0]).name.lower() not in {"icuuc.dll", "icuin.dll"}
        and not Path(entry[0]).name.lower().startswith("icudt")
    ]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GestioneTurni",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE),
    version=str(VERSION_FILE),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestioneTurni",
)
