# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Paths: PyInstaller injects SPEC (path to this spec file); repo root is parent of packaging/
SPEC_PATH = Path(SPEC).resolve()
REPO_ROOT = SPEC_PATH.parent.parent        # .../AcaSmart-repo (repo root)

# Data files: (src, dest) 2-tuples; directories are collected recursively by PyInstaller
# Note: resource_path() expects resources at _MEIPASS/resources/, not _MEIPASS/acasmart/resources/
_datas = [
    (str(REPO_ROOT / 'acasmart' / 'resources' / 'acasmart_template.db'), 'resources'),
    (str(REPO_ROOT / 'acasmart' / 'resources' / 'fonts'), 'resources/fonts'),
    (str(REPO_ROOT / 'acasmart' / 'resources' / 'static'), 'resources/static'),
    *collect_data_files('dotenv'),
    *collect_data_files('openpyxl'),
]
if (REPO_ROOT / '.env').exists():
    _datas.append((str(REPO_ROOT / '.env'), '.'))

# Entry point is main.py at repo root; acasmart package is under repo root
a = Analysis(
    [str(REPO_ROOT / 'main.py')],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=_datas,
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
        'cachetools',
        'jinja2',
    ],
    hookspath=[],
    runtime_hooks=[str(REPO_ROOT / 'acasmart' / 'runtime' / 'custom_runtime_hook.py')],
    excludes=[
        'matplotlib', 'scipy', 'IPython', 'jupyter', 'notebook', 'pytest', 'nbconvert',
        'sphinx', 'setuptools', 'distutils', 'tkinter', 'PIL', 'pillow', 'cv2',
        'opencv', 'tensorflow', 'torch', 'sklearn', 'scikit_learn', 'pkg_resources',
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
    icon=str(REPO_ROOT / 'acasmart' / 'resources' / 'static' / 'AppIcon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AcaSmart',
)