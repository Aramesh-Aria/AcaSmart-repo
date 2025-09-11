# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# ===== Paths (نسبت به محل همین فایل mac.spec) =====
BASE = Path(__file__).resolve().parent                          # .../AcaSmart-repo
PROJ = BASE.parent                                              # .../AcaSmart
SRC_DIR = BASE / 'src'                                          # .../AcaSmart-repo/src
STATIC_DIR = PROJ / 'static'                                    # .../AcaSmart/static
SETUP_DIR = PROJ / 'Setup_files'                                # .../AcaSmart/Setup_files

ICON_ICNS = str((STATIC_DIR / 'AppIcon.icns').resolve())        # آیکن مک

block_cipher = None

# فقط دیتاهای لازم؛ آیکن را در datas نمی‌گذاریم چون با پارامتر icon کپی می‌شود
datas = [
    (str((SETUP_DIR / 'acasmart_template.db').resolve()), '.'),
    (str((SETUP_DIR / '.env').resolve()), '.'),
    *collect_data_files('dotenv'),
    *collect_data_files('openpyxl'),
]

hiddenimports = [
    'PySide6.QtCore','PySide6.QtWidgets','PySide6.QtGui','shiboken6',
    'sqlite3','pandas','numpy','jdatetime','openpyxl','requests',
    'dotenv','et_xmlfile','cachetools',
]

a = Analysis(
    [str((SRC_DIR / 'main.py').resolve())],
    pathex=[str(BASE.resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[str((SRC_DIR / 'custom_runtime_hook.py').resolve())],
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
    icon=ICON_ICNS,   # ← برای اطمینان اینجا هم ست می‌کنیم
)

app = BUNDLE(
    exe,
    name='AcaSmart.app',
    icon=ICON_ICNS,   # ← آیکن باندل مک
    bundle_identifier='com.acasmart.app',
    info_plist={
        'CFBundleName': 'AcaSmart',
        'CFBundleDisplayName': 'AcaSmart',
        'CFBundleIconFile': 'AppIcon.icns',  # نام فایلی که در Resources خواهد بود
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'NSHighResolutionCapable': True,
    },
)
