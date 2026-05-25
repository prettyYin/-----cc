"""路径工具：开发模式 / 打包模式都能正确找到 assets 目录。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def assets_dir() -> Path:
    return app_root() / "src" / "assets"


def sprites_dir() -> Path:
    return assets_dir() / "sprites"


def icons_dir() -> Path:
    return sprites_dir() / "icons"


def icon_path(name: str) -> Path:
    return icons_dir() / name


def user_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(base) / "XiLeDi"
    path.mkdir(parents=True, exist_ok=True)
    return path
