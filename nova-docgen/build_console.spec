# -*- mode: python ; coding: utf-8 -*-
import os

datas = [
    ('templates', 'templates'),
    ('assets', 'assets'),
    ('forms.json', '.'),
    ('config.json', '.'),
    ('core/hwpxskill', 'core/hwpxskill'),
]

hiddenimports = [
    'win32com', 'win32com.client', 'win32timezone', 'pythoncom', 'pywintypes',
    'lxml._elementpath', 'PIL._tkinter_finder',
]

excludes = ['fitz', 'pymupdf', 'matplotlib', 'numpy', 'pandas', 'scipy', 'pytest']

a = Analysis(
    ['app.py'],
    pathex=['core'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='노바선임서류생성기',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)
