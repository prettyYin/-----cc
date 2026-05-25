"""抚摸手动效：像素画卡通手在桌宠头顶上下浮动 1.5 秒后销毁。"""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from src.core.paths import icon_path
from src.ui.pixel_art import dewhite_pixmap, render_pattern


_HAND_SIZE = 72
_DURATION_MS = 1500
_BOB_HEIGHT_PX = 16
_BOB_COUNT = 4


_HAND_PATTERN = [
    ".XXX.XX.",
    "XSSSXSSX",
    "XSSSXSSX",
    "XSSSXSSX",
    "XSSSSSSX",
    "XSSSSSSX",
    "XXSSSSSX",
    ".XSSSSXX",
    ".XSSSSX.",
    "..XXXX..",
]
_HAND_PALETTE = {
    "X": "#5C4221",
    "S": "#FFD9B3",
}


def _make_hand_pixmap(size: int = _HAND_SIZE) -> QPixmap:
    png = icon_path("hand.png")
    if png.exists():
        pm = QPixmap(str(png))
        if not pm.isNull():
            pm = dewhite_pixmap(pm)
            return pm.scaled(
                size, size,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )
    scale = max(2, size // 11)
    return render_pattern(_HAND_PATTERN, _HAND_PALETTE, scale=scale, canvas_size=(size, size))


_hand_cache: QPixmap | None = None


def _hand_pixmap() -> QPixmap:
    global _hand_cache
    if _hand_cache is None:
        _hand_cache = _make_hand_pixmap()
    return _hand_cache


class PettingHand(QObject):
    def __init__(self, head_center_x: int, head_top_y: int) -> None:
        super().__init__()
        self._window = QWidget(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput,
        )
        self._window.setAttribute(Qt.WA_TranslucentBackground, True)
        self._window.setAttribute(Qt.WA_NoSystemBackground, True)
        self._window.setFixedSize(_HAND_SIZE, _HAND_SIZE)

        label = QLabel(self._window)
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        label.setGeometry(0, 0, _HAND_SIZE, _HAND_SIZE)
        label.setPixmap(_hand_pixmap())

        start_x = head_center_x - _HAND_SIZE // 2
        start_y = head_top_y - _HAND_SIZE - 4
        self._window.move(start_x, start_y)
        self._window.show()

        self._anim = QPropertyAnimation(self._window, b"pos", self)
        self._anim.setDuration(_DURATION_MS)
        steps = _BOB_COUNT * 2
        for i in range(steps + 1):
            t = i / steps
            y_offset = _BOB_HEIGHT_PX if i % 2 == 1 else 0
            self._anim.setKeyValueAt(t, QPoint(start_x, start_y + y_offset))
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

        QTimer.singleShot(_DURATION_MS + 80, self._cleanup)

    def _cleanup(self) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if self._window is not None:
            self._window.close()
            self._window.deleteLater()
            self._window = None
        self.deleteLater()
