"""开发期占位图：用 QPainter 临时画一只 Q 版喜乐蒂，正式美术到位后弃用。

提供两个公开函数：
- `make_placeholder_sheltie(size, mood)`：单帧基础图，按情绪变化
- `make_placeholder_frame(state, frame_idx, size)`：帧级占位图，同一状态内不同帧有细微差异
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap, QTransform


_MOOD_BY_STATE = {
    "idle": "idle",
    "walk": "idle",
    "sit": "idle",
    "sleep": "sleep",
    "happy": "happy",
    "dizzy": "idle",
}


def make_placeholder_sheltie(size: int = 180, mood: str = "idle") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    body_color = QColor("#F4C77B")
    chest_color = QColor("#FFF6E5")
    outline = QPen(QColor("#3B2A1A"), 3)
    p.setPen(outline)

    cx, cy = size / 2, size / 2 + 10

    p.setBrush(QBrush(body_color))
    p.drawEllipse(QPointF(cx, cy + 30), 55, 32)

    p.setBrush(QBrush(chest_color))
    p.drawEllipse(QPointF(cx, cy + 38), 24, 16)

    p.setBrush(QBrush(body_color))
    p.drawEllipse(QPointF(cx, cy - 10), 45, 42)

    p.setBrush(QBrush(chest_color))
    p.drawEllipse(QPointF(cx, cy + 3), 22, 18)

    p.setBrush(QBrush(body_color))
    p.drawPolygon([
        QPointF(cx - 38, cy - 30),
        QPointF(cx - 22, cy - 50),
        QPointF(cx - 18, cy - 22),
    ])
    p.drawPolygon([
        QPointF(cx + 38, cy - 30),
        QPointF(cx + 22, cy - 50),
        QPointF(cx + 18, cy - 22),
    ])

    p.setBrush(QBrush(QColor("#1A1A1A")))
    eye_y = cy - 8
    if mood == "sleep":
        pen2 = QPen(QColor("#1A1A1A"), 2)
        p.setPen(pen2)
        p.drawLine(QPointF(cx - 15, eye_y), QPointF(cx - 7, eye_y))
        p.drawLine(QPointF(cx + 7, eye_y), QPointF(cx + 15, eye_y))
        p.setPen(outline)
    else:
        p.drawEllipse(QPointF(cx - 11, eye_y), 3.5, 4.5)
        p.drawEllipse(QPointF(cx + 11, eye_y), 3.5, 4.5)

    p.setBrush(QBrush(QColor("#3B2A1A")))
    p.drawEllipse(QPointF(cx, cy + 4), 3, 2.5)

    if mood == "happy":
        pen3 = QPen(QColor("#3B2A1A"), 2)
        p.setPen(pen3)
        p.drawArc(QRectF(cx - 8, cy + 6, 16, 10), 0, -180 * 16)
        p.setPen(outline)

    p.setBrush(QBrush(body_color))
    tail_x = cx + 50
    tail_y = cy + 18
    p.drawEllipse(QPointF(tail_x, tail_y), 10, 18)

    p.end()
    return pm


def make_placeholder_frame(state: str, frame_idx: int, size: int = 180) -> QPixmap:
    """生成某状态某一帧的占位图。

    同一状态内不同 frame_idx 会有细微差异（位移 / 旋转 / 装饰），
    用于在缺少真实美术时验证动画系统是否真的在切帧。
    """
    mood = _MOOD_BY_STATE.get(state, "idle")
    base = make_placeholder_sheltie(size, mood)

    if state == "idle":
        return _y_offset(base, _breath_offset(frame_idx, 4, 2), size)

    if state == "walk":
        return _y_offset(base, _bob_offset(frame_idx, 6, 4), size)

    if state == "happy":
        return _y_offset(base, _bounce_offset(frame_idx, 5, 14), size)

    if state == "sleep":
        return _y_offset(base, _breath_offset(frame_idx, 3, 1), size)

    if state == "sit":
        return base

    if state == "dizzy":
        angle = (frame_idx - 1) * 8 - 12
        return _rotate(_add_stars(base, frame_idx, size), angle, size)

    return base


def _y_offset(src: QPixmap, dy: int, size: int) -> QPixmap:
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.drawPixmap(0, dy, src)
    p.end()
    return out


def _rotate(src: QPixmap, angle_deg: float, size: int) -> QPixmap:
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.translate(size / 2, size / 2)
    p.rotate(angle_deg)
    p.translate(-size / 2, -size / 2)
    p.drawPixmap(0, 0, src)
    p.end()
    return out


def _add_stars(src: QPixmap, frame_idx: int, size: int) -> QPixmap:
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, src)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#FFD700"), 2))
    p.setBrush(QBrush(QColor("#FFE066")))
    angle = (frame_idx - 1) * 90
    cx, cy = size / 2, 30
    for i in range(3):
        a = math.radians(angle + i * 120)
        x = cx + math.cos(a) * 22
        y = cy + math.sin(a) * 8
        p.drawEllipse(QPointF(x, y), 4, 4)
    p.end()
    return out


def _breath_offset(frame_idx: int, total: int, amp: int) -> int:
    return int(math.sin(frame_idx / total * math.pi * 2) * amp)


def _bob_offset(frame_idx: int, total: int, amp: int) -> int:
    return int(abs(math.sin(frame_idx / total * math.pi * 2)) * -amp)


def _bounce_offset(frame_idx: int, total: int, amp: int) -> int:
    return int(-abs(math.sin(frame_idx / total * math.pi)) * amp)
