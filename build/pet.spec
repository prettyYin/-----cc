# -*- mode: python ; coding: utf-8 -*-
"""小喜桌宠 PyInstaller spec。

打包（项目根目录运行，不是 build/ 下）：
    pyinstaller --clean build/pet.spec --distpath build/dist --workpath build/build
"""
from pathlib import Path


block_cipher = None
project_root = Path.cwd()
assets = project_root / "src" / "assets"

# 资源：sprites / data / icons 全打；fonts 只挂 zh_hans（省 ~27MB，其他语言字体从未被加载）
datas = [
    (str(assets / "sprites"), "src/assets/sprites"),
    (str(assets / "data"),    "src/assets/data"),
    (str(assets / "icons"),   "src/assets/icons"),
    (
        str(assets / "fonts" / "fusion-pixel-12px-monospaced-zh_hans.ttf"),
        "src/assets/fonts",
    ),
]

# keyring Windows 后端 + pywin32-ctypes（PyInstaller 追不到 entry_points 注册的后端）
hiddenimports = [
    "keyring.backends",
    "keyring.backends.Windows",
    "win32ctypes",
    "win32ctypes.pywin32",
    "win32ctypes.pywin32.pywintypes",
    "win32ctypes.core",
    "openai",
]

# 用不到的 PySide6 模块，瘦身
excludes = [
    "tkinter",
    "PySide6.Qt3D",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtBluetooth",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPositioning",
    "PySide6.QtNfc",
    "PySide6.QtRemoteObjects",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtTest",
    "PySide6.QtDataVisualization",
    "PySide6.QtCharts",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQml",
]


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
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
    name="XiLeDi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets / "icons" / "xiledi.ico"),
)
