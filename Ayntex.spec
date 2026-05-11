# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('C:/AynTex/libdjvulibre.dll', '.'), ('C:/AynTex/libdjvulibre-21.dll', '.'), ('C:/AynTex/libgcc_s_seh-1.dll', '.'), ('C:/AynTex/libjpeg.dll', '.'), ('C:/AynTex/libstdc++-6.dll', '.'), ('C:/AynTex/libtiff.dll', '.'), ('C:/AynTex/libwinpthread-1.dll', '.'), ('C:/AynTex/libz.dll', '.'), ('C:/AynTex/ddjvu.exe', '.'), ('C:/AynTex/djvused.exe', '.'), ('C:/AynTex/djvutxt.exe', '.')],
    datas=[('C:/AynTex/cwl', 'cwl'), ('C:/AynTex/plugins', 'plugins'), ('C:/AynTex/tips', 'tips'), ('C:/AynTex/icons', 'icons'), ('C:/AynTex/katex', 'katex'), ('C:/AynTex/D050000L.otf', '.'), ('C:/AynTex/FontAwesome.otf', '.'), ('C:/AynTex/STIXTwoMath-Regular.otf', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide2', 'PySide2.QtCore', 'PySide2.QtWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Ayntex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\AynTex\\AynTexlogo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Ayntex',
)
