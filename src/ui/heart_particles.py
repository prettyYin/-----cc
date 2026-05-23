"""爱心粒子动效：在指定屏幕坐标附近向上飘起若干心形，约 1.5 秒后销毁。"""
from __future__ import annotations

import random

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from src.ui.pixel_art import render_pattern


_HEART_SIZE = 27
_HEART_COUNT = 6
_DURATION_MS = 1500


_HEART_PATTERN = [
    ".XX.XX.",
    "XOXXOXX",
    "XOOOOOX",
    ".XOOOX.",
    "..XOX..",
    "...X...",
]
_HEART_PALETTE = {
    "X": "#C73666",
    "O": "#FF6B9D",
}


def _make_heart_pixmap(size: int = _HEART_SIZE) -> QPixmap:
    scale = max(2, size // 9)
    return render_pattern(_HEART_PATTERN, _HEART_PALETTE, scale=scale, canvas_size=(size, size))


_heart_pixmap_cache: QPixmap | None = None


def _heart_pixmap() -> QPixmap:
    global _heart_pixmap_cache
    if _heart_pixmap_cache is None:
        _heart_pixmap_cache = _make_heart_pixmap()
    return _heart_pixmap_cache


class HeartParticles(QObject):
    """Owns a transparent borderless overlay window that animates hearts then destroys itself."""

    def __init__(self, center_x: int, center_y: int) -> None:
        super().__init__()
        width = 160
        height = 120

        self._overlay = QWidget(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput,
        )
        self._overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        self._overlay.setAttribute(Qt.WA_NoSystemBackground, True)
        self._overlay.setFixedSize(width, height)
        self._overlay.move(center_x - width // 2, center_y - height + 10)

        self._labels: list[QLabel] = []
        self._anims: list[QParallelAnimationGroup] = []

        pm = _heart_pixmap()
        for _ in range(_HEART_COUNT):
            label = QLabel(self._overlay)
            label.setPixmap(pm)
            label.setAttribute(Qt.WA_TranslucentBackground, True)
            label.setFixedSize(_HEART_SIZE, _HEART_SIZE)
            start_x = random.randint(20, width - 20 - _HEART_SIZE)
            label.move(start_x, height - _HEART_SIZE - 5)
            opacity = QGraphicsOpacityEffect(label)
            opacity.setOpacity(1.0)
            label.setGraphicsEffect(opacity)
            self._labels.append(label)
            self._anims.append(self._build_anim(label, opacity, start_x, height))

        self._overlay.show()
        for anim in self._anims:
            anim.start()

        QTimer.singleShot(_DURATION_MS + 200, self._cleanup)

    def _build_anim(
        self,
        label: QLabel,
        opacity: QGraphicsOpacityEffect,
        start_x: int,
        height: int,
    ) -> QParallelAnimationGroup:
        delay_ms = random.randint(0, 400)
        rise_dy = random.randint(60, 100)
        end_x = start_x + random.randint(-25, 25)

        move = QPropertyAnimation(label, b"pos")
        move.setDuration(_DURATION_MS - delay_ms)
        move.setStartValue(QPoint(start_x, height - _HEART_SIZE - 5))
        move.setEndValue(QPoint(end_x, height - _HEART_SIZE - 5 - rise_dy))
        move.setEasingCurve(QEasingCurve.OutQuad)

        fade = QPropertyAnimation(opacity, b"opacity")
        fade.setDuration(_DURATION_MS - delay_ms)
        fade.setStartValue(1.0)
        fade.setKeyValueAt(0.5, 1.0)
        fade.setEndValue(0.0)

        group = QParallelAnimationGroup()
        group.addAnimation(move)
        group.addAnimation(fade)

        if delay_ms > 0:
            wrapper = QTimer(self)
            wrapper.setSingleShot(True)
            wrapper.timeout.connect(group.start)
            wrapper.start(delay_ms)
            return group
        return group

    def _cleanup(self) -> None:
        for anim in self._anims:
            anim.stop()
        self._anims.clear()
        self._overlay.close()
        self._overlay.deleteLater()
        self.deleteLater()
