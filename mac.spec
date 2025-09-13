from pathlib import Path
import inspect
from PyInstaller.utils.hooks import collect_data_files

SPEC_PATH = Path(inspect.getframeinfo(inspect.currentframe()).filename).resolve()
BASE = SPEC_PATH.parent                          # .../AcaSmart-repo
PROJ = BASE.parent                               # .../AcaSmart
SRC_DIR = BASE / 'src'
STATIC_DIR = PROJ / 'static'
SETUP_DIR = PROJ / 'Setup_files'                # .../AcaSmart/Setup_files

block_cipher = None

# فقط دیتاهای لازم؛ آیکن را در datas نمی‌گذاریم چون با پارامتر icon کپی می‌شود
datas = [
    ('../Setup_files/acasmart_template.db', '.'),
    ('../Setup_files/.env', '.'),
    *collect_data_files('dotenv'),
    *collect_data_files('openpyxl'),
]

hiddenimports = [
    'PySide6.QtCore','PySide6.QtWidgets','PySide6.QtGui','shiboken6',
    'sqlite3','pandas','numpy','jdatetime','openpyxl','requests',
    'dotenv','et_xmlfile','cachetools','jinja2'
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
    icon='../static/AppIcon.icns',
)

app = BUNDLE(
    exe,
    name='AcaSmart.app',
    icon='../static/AppIcon.icns',
    bundle_identifier='ir.aramesh.AcaSmart',
    info_plist={
        'CFBundleIdentifier' : 'ir.aramesh.AcaSmart',
        'CFBundleName': 'AcaSmart',
        'CFBundleDisplayName': 'AcaSmart',
        'CFBundleIconFile': 'AppIcon.icns',
        'CFBundleShortVersionString': '1.1.08',
        'CFBundleVersion': '1108',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'NSRequiresAquaSystemAppearance': False,  # پشتیبانی از Dark Mode
    

    },
)
