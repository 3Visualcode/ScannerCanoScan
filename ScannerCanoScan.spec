# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['scanner_app.py'],
    pathex=[],
    binaries=[],
    datas=[('sane-win64', 'sane-win64')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PIL.ImageQt', 'numpy', 'tkinter.test'],
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
    name='ScannerCanoScan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX is off on purpose: packed executables are a frequent source of
    # antivirus false positives, which is exactly what code signing is meant
    # to avoid. The size saving is not worth the extra SmartScreen friction.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,     # macOS only; Windows signing is done in build.ps1
    entitlements_file=None,
    version='version_info.txt',
)
