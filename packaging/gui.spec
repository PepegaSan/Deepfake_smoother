# -*- mode: python ; coding: utf-8 -*-
"""One-file windowed build. Run from repo root: pyinstaller packaging/gui.spec"""
import os

from PyInstaller.utils.hooks import collect_all

_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

_tkdnd_datas, _tkdnd_bins, _tkdnd_hidden = collect_all("tkinterdnd2")

a = Analysis(
    [os.path.join(_root, "gui.py")],
    pathex=[_root],
    binaries=_tkdnd_bins,
    datas=_tkdnd_datas,
    hiddenimports=["theme_palette", *_tkdnd_hidden],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="gui",
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
