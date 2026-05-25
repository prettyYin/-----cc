"""像素画工具：把 ASCII 字符画模式渲染成清晰的 QPixmap（无抗锯齿、整像素块）。"""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap


def render_pattern(
    pattern: list[str],
    palette: dict[str, QColor | str],
    scale: int = 3,
    canvas_size: tuple[int, int] | None = None,
    offset: tuple[int, int] | None = None,
) -> QPixmap:
    """把字符画模式渲染成像素 QPixmap。

    pattern: 每个字符代表一个逻辑像素，行 = y，列 = x。
    palette: 字符到颜色的映射；不在映射中的字符（空格、点等）视为透明。
    scale: 每个逻辑像素放大成 scale × scale 的实际像素块。
    canvas_size: 最终画布大小（像素）。None 时按 pattern 宽高 × scale 自动算。
    offset: 内容在画布上的偏移（实际像素，不是逻辑像素）。None 时居中。
    """
    if not pattern:
        return QPixmap(1, 1)
    rows = len(pattern)
    cols = max(len(row) for row in pattern)

    if canvas_size is None:
        canvas_w, canvas_h = cols * scale, rows * scale
    else:
        canvas_w, canvas_h = canvas_size

    if offset is None:
        ox = (canvas_w - cols * scale) // 2
        oy = (canvas_h - rows * scale) // 2
    else:
        ox, oy = offset

    pm = QPixmap(canvas_w, canvas_h)
    pm.fill(Qt.transparent)

    palette_q: dict[str, QColor] = {
        ch: (col if isinstance(col, QColor) else QColor(col))
        for ch, col in palette.items()
    }

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            color = palette_q.get(ch)
            if color is None:
                continue
            p.fillRect(ox + x * scale, oy + y * scale, scale, scale, color)
    p.end()
    return pm


PixelPalette = dict[str, QColor | str]


def dewhite_pixmap(pm: QPixmap, tol: int = 16) -> QPixmap:
    """边缘泛洪去白底：从四角 BFS 把"接近白色（每通道≥255-tol）+ 与边界连通"的像素 alpha 设为 0。

    胸口白毛被棕色描边包围、不与边界连通，不会被误伤。
    若图像已透明（四角 alpha=0），BFS 立刻终止，等同 no-op。
    """
    if pm.isNull():
        return pm
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    if w == 0 or h == 0:
        return pm

    threshold = 255 - tol
    transparent_rgba = QColor(0, 0, 0, 0).rgba()

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        queue.append((sx, sy))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        c = QColor(img.pixel(x, y))
        if c.alpha() == 0:
            continue
        if c.red() < threshold or c.green() < threshold or c.blue() < threshold:
            continue
        img.setPixel(x, y, transparent_rgba)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                queue.append((nx, ny))

    return QPixmap.fromImage(img)
