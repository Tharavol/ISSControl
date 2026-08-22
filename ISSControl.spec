# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone ISSControl.exe.

Points at isscontrol.pyw rather than the isscontrol package's own
__main__.py -- .pyw's absolute import (`from isscontrol.app import run`)
freezes cleanly, where __main__.py's relative import (`from .app import
run`) assumes a package context the frozen entry script doesn't have.
.pyw's own try/except-then-messagebox is a bonus here too: the same "show
a message box instead of vanishing" behavior it exists for under
pythonw.exe is exactly what a --windowed .exe needs on a startup failure,
since there's no console for a traceback to print to either way.

Verified locally before wiring this into CI (see #21): a frozen onefile
build renders the real window correctly, and -- the actual risk with
PyInstaller + keyring, which discovers its backend via package metadata
that freezing can break -- a set/get/delete round trip against Windows
Credential Manager works in a frozen build with no extra hidden-import
wiring needed.

Build with: pyinstaller ISSControl.spec
"""

import os

ROOT = os.path.abspath(SPECPATH)  # noqa: F821 -- injected by PyInstaller

a = Analysis(
    [os.path.join(ROOT, "isscontrol.pyw")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.datas,
    [],
    name="ISSControl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # .pyw's extension already implies this to PyInstaller's own analysis
    # (confirmed against the spec it generates for this exact entry file --
    # console=False came out even when --console was passed on the CLI);
    # set explicitly anyway so it isn't a fact a reader has to already know.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "isscontrol", "assets", "icon.ico"),
)
