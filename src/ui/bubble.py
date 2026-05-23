"""提醒气泡：像素风方角云朵窗口，5 秒渐隐销毁。外部用列表持引用避免 GC。"""
from __future__ import annotations

from PySide6.QtCore import (
    QObject,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget


_PADDING_X = 16
_PADDING_Y = 12
_TAIL_HEIGHT = 14
_TAIL_BLOCK = 4
_MIN_WIDTH = 120
_MAX_WIDTH = 280
_DISPLAY_MS = 5000
_FADE_MS = 400
_OUTLINE_PX = 3


class _CloudBubble(QWidget):
    def __init__(self, text: str, tail_side: str) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._text = text
        self._tail_side = tail_side
        self._font = QFont()
        self._font.setPointSize(11)
        self._font.setStyleStrategy(QFont.NoAntialias)

        fm = QFontMetrics(self._font)
        text_w = min(_MAX_WIDTH, max(_MIN_WIDTH, fm.horizontalAdvance(text) + _PADDING_X * 2))
        rect = fm.boundingRect(0, 0, text_w - _PADDING_X * 2, 1000, Qt.TextWordWrap, text)
        body_h = rect.height() + _PADDING_Y * 2
        self._body_w = max(_MIN_WIDTH, text_w)
        self._body_h = max(44, body_h)
        self.setFixedSize(self._body_w, self._body_h + _TAIL_HEIGHT)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        fill = QColor("#FFF8EC")
        outline = QColor("#5C4221")

        body = QRectF(_OUTLINE_PX, _OUTLINE_PX,
                      self._body_w - _OUTLINE_PX * 2,
                      self._body_h - _OUTLINE_PX * 2)

        p.fillRect(body, QBrush(fill))
        pen = QPen(outline, _OUTLINE_PX)
        pen.setJoinStyle(Qt.MiterJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(body)

        tail_anchor_x = int(self._body_w * (0.30 if self._tail_side == "left" else 0.70))
        tail_top_y = int(body.bottom())
        steps = _TAIL_HEIGHT // _TAIL_BLOCK + 1
        for i in range(steps):
            block_y = tail_top_y + i * _TAIL_BLOCK
            block_half_w = max(_TAIL_BLOCK, (steps - i) * _TAIL_BLOCK)
            block_x = tail_anchor_x - block_half_w // 2
            p.fillRect(block_x, block_y, block_half_w, _TAIL_BLOCK, fill)
            p.fillRect(block_x - _OUTLINE_PX, block_y, _OUTLINE_PX, _TAIL_BLOCK, outline)
            p.fillRect(block_x + block_half_w, block_y, _OUTLINE_PX, _TAIL_BLOCK, outline)
        p.fillRect(
            tail_anchor_x - _OUTLINE_PX,
            tail_top_y - _OUTLINE_PX,
            _OUTLINE_PX * 2,
            _OUTLINE_PX,
            fill,
        )

        p.setPen(QColor("#3B2A1A"))
        p.setFont(self._font)
        text_rect = QRectF(
            _PADDING_X,
            _PADDING_Y,
            self._body_w - _PADDING_X * 2,
            self._body_h - _PADDING_Y * 2,
        )
        p.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self._text)


class ReminderBubble(QObject):
    """生命周期：构造时显示 → 5s 后 fadeOut → 销毁。外部用列表持有引用避免 GC。"""

    def __init__(self, text: str, pet_x: int, pet_y: int, pet_size: int = 192) -> None:
        super().__init__()
        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen is not None else None

        pet_center_x = pet_x + pet_size // 2
        tail_side = "left" if pet_center_x > (screen_geo.center().x() if screen_geo else 800) else "right"
        self._bubble = _CloudBubble(text, tail_side)

        bubble_x = pet_center_x - self._bubble.width() // 2
        bubble_y = pet_y - self._bubble.height() - 2

        if screen_geo is not None:
            bubble_x = max(screen_geo.left() + 4, min(screen_geo.right() - self._bubble.width() - 4, bubble_x))
            if bubble_y < screen_geo.top() + 4:
                bubble_y = pet_y + pet_size + 2

        self._bubble.move(bubble_x, bubble_y)
        self._bubble.setWindowOpacity(0.0)
        self._bubble.show()

        self._fade_in = QPropertyAnimation(self._bubble, b"windowOpacity", self)
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        QTimer.singleShot(_DISPLAY_MS, self._start_fade_out)

    def _start_fade_out(self) -> None:
        if self._bubble is None:
            return
        self._fade_out = QPropertyAnimation(self._bubble, b"windowOpacity", self)
        self._fade_out.setDuration(_FADE_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self._cleanup)
        self._fade_out.start()

    def _cleanup(self) -> None:
        if self._bubble is not None:
            self._bubble.close()
            self._bubble.deleteLater()
            self._bubble = None
        self.deleteLater()
