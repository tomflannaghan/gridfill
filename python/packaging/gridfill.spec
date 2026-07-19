# PyInstaller spec for the standalone gridfill CLI executable.
#
# Build (from the repo root, with the "build" extra installed):
#   pyinstaller packaging/gridfill.spec
#
# Output lands in dist/gridfill(.exe).

import os

block_cipher = None

repo_root = os.path.dirname(os.path.abspath(SPEC))
repo_root = os.path.dirname(repo_root)

a = Analysis(
    [os.path.join(repo_root, "packaging", "gui_main.py")],
    pathex=[repo_root, os.path.join(repo_root, "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="gridfill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
