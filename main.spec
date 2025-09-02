# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('../Setup_files/acasmart_template.db', '.'),
        ('../Setup_files/.env', '.'),
        ('../black_background_icon.ico', '.'),
        ('../white_background_icon.ico', '.'),
        ('../black_background_icon.png', '.'),
        ('../white_background_icon.png', '.'),
        *collect_data_files('dotenv'),
        *collect_data_files('openpyxl'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'shiboken6',
        'sqlite3',
        'pandas',
        'numpy',
        'jdatetime',
        'openpyxl',
        'requests',
        'dotenv',
        'et_xmlfile',
        'cachetools'
    ],
    hookspath=[],
    runtime_hooks=[
        'src/custom_runtime_hook.py'
    ],
    excludes=[
        'matplotlib', 'scipy', 'IPython', 'jupyter', 'notebook','pytest', 'nbconvert',
        'sphinx', 'setuptools', 'distutils', 'tkinter', 'PIL', 'pillow', 'cv2',
        'opencv', 'tensorflow', 'torch', 'sklearn', 'scikit_learn', 'pkg_resources'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AcaSmart',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='../black_background_icon.ico'  # Default icon (will be changed dynamically)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AcaSmart'
)
