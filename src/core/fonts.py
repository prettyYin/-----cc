"""像素字体注册：启动时调 init() 注册 src/assets/fonts/ 下的 .ttf，缺字体时回落系统默认。"""
from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase

from src.core.paths import assets_dir


_FAMILY: str | None = None
_FALLBACK_FAMILIES = ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC"]


_PREFERRED_FONT_FILES = (
    "fusion-pixel-12px-monospaced-zh_hans.ttf",
    "fusion-pixel-12px-monospaced.ttf",
    "fusion-pixel-12px-proportional-zh_hans.ttf",
    "ark-pixel-12px-monospaced-zh_hans.ttf",
    "pixel.ttf",
)


def init() -> str | None:
    """扫描 src/assets/fonts/ 注册第一个能找到的像素字体。返回字体 family 名（或 None）。"""
    global _FAMILY
    fonts_dir = assets_dir() / "fonts"
    if not fonts_dir.exists():
        return None

    for filename in _PREFERRED_FONT_FILES:
        path = fonts_dir / filename
        if not path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            print(f"[fonts] 加载失败：{filename}")
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            _FAMILY = families[0]
            print(f"[fonts] 已注册像素字体：{_FAMILY}（来自 {filename}）")
            return _FAMILY
    return None


def pixel_font(point_size: int = 11, bold: bool = False) -> QFont:
    """返回像素字体 QFont；如未注册则用系统中文 sans + 关闭抗锯齿。"""
    if _FAMILY:
        font = QFont(_FAMILY, point_size)
    else:
        font = QFont()
        for family in _FALLBACK_FAMILIES:
            font.setFamily(family)
            if QFontDatabase.families() and family in QFontDatabase.families():
                break
        font.setPointSize(point_size)
    font.setBold(bold)
    font.setStyleStrategy(QFont.NoAntialias)
    font.setHintingPreference(QFont.PreferFullHinting)
    return font


def family() -> str | None:
    return _FAMILY


def family_css() -> str:
    """给 QSS 用的 font-family 字符串（含 fallback）。"""
    if _FAMILY:
        return f'"{_FAMILY}", "Microsoft YaHei UI", "Microsoft YaHei", monospace'
    return '"Microsoft YaHei UI", "Microsoft YaHei", monospace'
