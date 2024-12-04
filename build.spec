# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# GUI程序
gui = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'sshtunnel', 
        'pymysql',
        'paramiko',
        'cryptography',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets'
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

# 管理端程序
admin = Analysis(
    ['admin.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'sshtunnel', 
        'pymysql',
        'paramiko',
        'cryptography',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets'
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

gui_pyz = PYZ(gui.pure, gui.zipped_data, cipher=block_cipher)
admin_pyz = PYZ(admin.pure, admin.zipped_data, cipher=block_cipher)

# GUI程序
gui_exe = EXE(
    gui_pyz,
    gui.scripts,
    gui.binaries,
    gui.zipfiles,
    gui.datas,
    [],
    name='卡密验证',
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
    icon='icon.ico'
)

# 管理端程序
admin_exe = EXE(
    admin_pyz,
    admin.scripts,
    admin.binaries,
    admin.zipfiles,
    admin.datas,
    [],
    name='卡密管理',
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
    icon='icon.ico'
)

# 收集所有文件
coll = COLLECT(
    gui_exe,
    gui.binaries,
    gui.zipfiles,
    gui.datas,
    admin_exe,
    admin.binaries,
    admin.zipfiles,
    admin.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='卡密系统',
) 