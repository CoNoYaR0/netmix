# -*- mode: python ; coding: utf-8 -*-

# This is a PyInstaller spec file. It tells PyInstaller how to build the
# netmix.exe file. To use it, run `pyinstaller netmix.spec` from the terminal.

block_cipher = None

a = Analysis(
    ['netmix/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('netmix/ui/templates', 'netmix/ui/templates')
    ],
    hiddenimports=[
        'eventlet',  # Often needed for Flask-SocketIO
        'gevent',
        'engineio.async_drivers.eventlet',
        'sklearn.utils._typedefs', # Common hidden imports for scikit-learn
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._quad_tree',
        'sklearn.tree',
        'sklearn.tree._utils'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='netmix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='netmix',
)
