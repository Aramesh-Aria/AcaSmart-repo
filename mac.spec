# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ('../Setup_files/acasmart_template.db', '.'),
    ('../Setup_files/.env', '.'),
    ('../static/white_background_icon.icns', '.'),
    ('../static/white_background_icon.png', '.'),
    *collect_data_files('dotenv'),
    *collect_data_files('openpyxl'),
]

hiddenimports = [
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
    'cachetools',
]

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=['src/custom_runtime_hook.py'],
    excludes=[
        'matplotlib','scipy','IPython','jupyter','notebook','pytest','nbconvert',
        'sphinx','setuptools','distutils','tkinter','PIL','pillow','cv2',
        'opencv','tensorflow','torch','sklearn','scikit_learn','pkg_resources'
    ],
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
    runtime_tmpdir=None,
    console=False,
)

app = BUNDLE(
    exe,
    name='AcaSmart.app',
    icon='../static/white_background_icon.icns',  # آیکن مک از پوشه Setup_files
    bundle_identifier='com.acasmart.app',
    info_plist={
        'NSHighResolutionCapable': True,
    },
)
