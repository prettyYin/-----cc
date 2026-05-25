"""番茄钟进度环：48×48 像素风圆环，作为 PetWindow 的 child widget，右上角内侧显示倒计时。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.core import fonts


RING_SIZE = 48

_BG_COLOR = QColor("#FFF8EC")
_BORDER_COLOR = QColor("#5C4221")
_TEXT_COLOR = QColor("#3B2A1A")

_STATE_COLORS = {
    "focus": QColor("#E45550"),
}


class ProgressRing(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(RING_SIZE, RING_SIZE)
        self._state = "focus"
        self._remaining_s = 0
        self._total_s = 1
        self.hide()

    def set_progress(self, state: str, remaining_s: int, total_s: int) -> None:
        self._state = state
        self._remaining_s = max(0, remaining_s)
        self._total_s = max(1, total_s)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = QRectF(2, 2, RING_SIZE - 4, RING_SIZE - 4)

        painter.setBrush(_BG_COLOR)
        painter.setPen(QPen(_BORDER_COLOR, 2))
        painter.drawEllipse(rect)

        ratio = self._remaining_s / self._total_s if self._total_s > 0 else 0
        span_deg = int(360 * ratio)
        arc_color = _STATE_COLORS.get(self._state, _STATE_COLORS["focus"])
        arc_pen = QPen(arc_color, 4)
        arc_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.NoBrush)
        arc_rect = QRectF(4, 4, RING_SIZE - 8, RING_SIZE - 8)
        # Qt 角度单位 1/16 度；起点 90° 朝正上方，顺时针走 → span 取负
        painter.drawArc(arc_rect, 90 * 16, -span_deg * 16)

        mins, secs = divmod(self._remaining_s, 60)
        text = f"{mins:02d}:{secs:02d}"
        painter.setPen(_TEXT_COLOR)
        painter.setFont(fonts.pixel_font(8))
        painter.drawText(self.rect(), Qt.AlignCenter, text)
