"""喂食流程：在桌宠附近落下骨头，桌宠走过去吃掉后切 happy；支持用户操作打断时立即清理。"""
from __future__ import annotations

import random
from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from src.core.paths import icon_path
from src.ui.pixel_art import dewhite_pixmap, render_pattern


_BONE_SIZE = 60
_NEAR_OFFSET_MIN = 10
_NEAR_OFFSET_MAX = 50
_FALL_HEIGHT_PX = 120
_FALL_DURATION_MS = 500


_BONE_PATTERN = [
    "XX.....XX..",
    "XOX...XOX..",
    "XOOXXXOOX..",
    ".XOOOOOOX..",
    "XOOXXXOOX..",
    "XOX...XOX..",
    "XX.....XX..",
]
_BONE_PALETTE = {
    "X": "#5C4221",
    "O": "#FFF1CC",
}


def _make_bone_pixmap(size: int = _BONE_SIZE) -> QPixmap:
    png = icon_path("bone.png")
    if png.exists():
        pm = QPixmap(str(png))
        if not pm.isNull():
            pm = dewhite_pixmap(pm)
            return pm.scaled(
                size, size,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )
    scale = max(2, size // 12)
    return render_pattern(_BONE_PATTERN, _BONE_PALETTE, scale=scale, canvas_size=(size, size))


class BoneWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedSize(_BONE_SIZE, _BONE_SIZE)

        label = QLabel(self)
        label.setGeometry(0, 0, _BONE_SIZE, _BONE_SIZE)
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        label.setPixmap(_make_bone_pixmap())


class FeedingController(QObject):
    """单次喂食流程的协调者：创建骨头、驱动桌宠走过去、吃掉，并支持用户中断时立即清理。"""

    def __init__(
        self,
        *,
        pet_size: int,
        behavior,
        state_machine,
        on_arrive_sound: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._pet_size = pet_size
        self._behavior = behavior
        self._sm = state_machine
        self._on_arrive_sound = on_arrive_sound
        self._bone: BoneWindow | None = None
        self._fall_anim: QPropertyAnimation | None = None
        self._cancelled = False

    def start(self, pet_x: int, pet_y: int) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        side = random.choice([-1, 1])
        offset = random.randint(_NEAR_OFFSET_MIN, _NEAR_OFFSET_MAX)
        bone_x = pet_x + self._pet_size // 2 + side * (self._pet_size // 2 + offset) - _BONE_SIZE // 2
        bone_x = max(geo.left() + 20, min(geo.right() - _BONE_SIZE - 20, bone_x))

        bone_landing_y = pet_y + self._pet_size - _BONE_SIZE - 5
        bone_landing_y = max(
            geo.top() + 20,
            min(geo.bottom() - _BONE_SIZE - 10, bone_landing_y),
        )
        bone_start_y = bone_landing_y - _FALL_HEIGHT_PX

        self._bone = BoneWindow()
        self._bone.move(bone_x, bone_start_y)
        self._bone.show()

        self._fall_anim = QPropertyAnimation(self._bone, b"pos", self)
        self._fall_anim.setDuration(_FALL_DURATION_MS)
        self._fall_anim.setStartValue(QPoint(bone_x, bone_start_y))
        self._fall_anim.setEndValue(QPoint(bone_x, bone_landing_y))
        self._fall_anim.setEasingCurve(QEasingCurve.OutBounce)
        self._fall_anim.finished.connect(lambda: self._on_bone_landed(bone_x, bone_landing_y))
        self._fall_anim.start()

    def _on_bone_landed(self, bone_x: int, bone_top_y: int) -> None:
        if self._cancelled:
            return
        target_pet_x = bone_x + _BONE_SIZE // 2 - self._pet_size // 2
        target_pet_y = bone_top_y + _BONE_SIZE - self._pet_size + 10
        self._behavior.walk_to(
            target_pet_x,
            target_pet_y,
            self._on_pet_arrived,
            on_cancel=self._on_walk_cancelled,
        )

    def _on_pet_arrived(self) -> None:
        if self._cancelled:
            return
        self._cleanup_bone()
        if self._on_arrive_sound is not None:
            self._on_arrive_sound()
        self._sm.transition("happy", force=True)
        self.deleteLater()

    def _on_walk_cancelled(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        self._cleanup_bone()
        self.deleteLater()

    def cancel(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        if self._fall_anim is not None:
            self._fall_anim.stop()
            self._fall_anim = None
        self._cleanup_bone()
        self._behavior.cancel_walk_to()
        self.deleteLater()

    def _cleanup_bone(self) -> None:
        if self._bone is not None:
            self._bone.close()
            self._bone.deleteLater()
            self._bone = None
