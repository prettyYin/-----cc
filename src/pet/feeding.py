"""喂食流程：支持骨头 / 狗粮两种食物，吃完进入 eat→happy→idle 三段链路；支持用户操作打断时立即清理。"""
from __future__ import annotations

import random
from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from src.core.paths import icon_path
from src.ui.pixel_art import dewhite_pixmap, render_pattern


_BONE_SIZE = 60
_DOGFOOD_SIZE = 70
_NEAR_OFFSET_MIN = 10
_NEAR_OFFSET_MAX = 50
_FALL_HEIGHT_PX = 120
_FALL_DURATION_MS = 500
_EAT_DURATION_MS = 3000
_HAPPY_DURATION_MS = 800


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


_DOGFOOD_PATTERN = [
    "...BBB...BBB....",
    "..BOBB.BBOBB....",
    ".BBOBBBBBOBBB...",
    "XXXXXXXXXXXXXX..",
    "X.OOOOOOOOOO.X..",
    "X.OBOBOBOBOO.X..",
    "X.OOOOOOOOOO.X..",
    ".XXXXXXXXXXXX...",
    "..XXXXXXXXXX....",
]
_DOGFOOD_PALETTE = {
    "X": "#5C4221",
    "O": "#FFF1CC",
    "B": "#A06030",
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


def _make_dogfood_pixmap(size: int = _DOGFOOD_SIZE) -> QPixmap:
    png = icon_path("dogfood.png")
    if png.exists():
        pm = QPixmap(str(png))
        if not pm.isNull():
            pm = dewhite_pixmap(pm)
            return pm.scaled(
                size, size,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )
    scale = max(2, size // 16)
    return render_pattern(_DOGFOOD_PATTERN, _DOGFOOD_PALETTE, scale=scale, canvas_size=(size, size))


class _FoodWindow(QWidget):
    def __init__(self, pixmap: QPixmap, size: int) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedSize(size, size)

        label = QLabel(self)
        label.setGeometry(0, 0, size, size)
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        label.setPixmap(pixmap)


class BoneWindow(_FoodWindow):
    def __init__(self) -> None:
        super().__init__(_make_bone_pixmap(), _BONE_SIZE)


class DogfoodWindow(_FoodWindow):
    def __init__(self) -> None:
        super().__init__(_make_dogfood_pixmap(), _DOGFOOD_SIZE)


class FeedingController(QObject):
    """单次喂食流程的协调者：按 food_type 分流，吃完走 eat/hold_bone→happy→idle 三段链路，并支持中断时立即清理。"""

    eating_finished = Signal(str)

    def __init__(
        self,
        *,
        pet_size: int,
        behavior,
        state_machine,
        animator,
        on_arrive_sound: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._pet_size = pet_size
        self._behavior = behavior
        self._sm = state_machine
        self._animator = animator
        self._on_arrive_sound = on_arrive_sound
        self._food: _FoodWindow | None = None
        self._food_size = _BONE_SIZE
        self._fall_anim: QPropertyAnimation | None = None
        self._eat_timer: QTimer | None = None
        self._happy_timer: QTimer | None = None
        self._cancelled = False
        self._food_type: str = "bone"

    def start(self, pet_x: int, pet_y: int, food_type: str = "bone") -> None:
        self._food_type = food_type
        if food_type == "dogfood":
            self._start_dogfood(pet_x, pet_y)
        else:
            self._start_bone(pet_x, pet_y)

    def _start_bone(self, pet_x: int, pet_y: int) -> None:
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

        self._food = BoneWindow()
        self._food_size = _BONE_SIZE
        self._food.move(bone_x, bone_start_y)
        self._food.show()

        self._fall_anim = QPropertyAnimation(self._food, b"pos", self)
        self._fall_anim.setDuration(_FALL_DURATION_MS)
        self._fall_anim.setStartValue(QPoint(bone_x, bone_start_y))
        self._fall_anim.setEndValue(QPoint(bone_x, bone_landing_y))
        self._fall_anim.setEasingCurve(QEasingCurve.OutBounce)
        self._fall_anim.finished.connect(lambda: self._on_bone_landed(bone_x, bone_landing_y))
        self._fall_anim.start()

    def _start_dogfood(self, pet_x: int, pet_y: int) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        side = 1 if self._animator.direction() > 0 else -1
        offset = random.randint(_NEAR_OFFSET_MIN, _NEAR_OFFSET_MAX)
        food_x = pet_x + self._pet_size // 2 + side * (self._pet_size // 2 + offset) - _DOGFOOD_SIZE // 2
        food_x = max(geo.left() + 20, min(geo.right() - _DOGFOOD_SIZE - 20, food_x))

        food_y = pet_y + self._pet_size - _DOGFOOD_SIZE - 5
        food_y = max(geo.top() + 20, min(geo.bottom() - _DOGFOOD_SIZE - 10, food_y))

        self._food = DogfoodWindow()
        self._food_size = _DOGFOOD_SIZE
        self._food.move(food_x, food_y)
        self._food.show()

        if self._on_arrive_sound is not None:
            self._on_arrive_sound()
        self._begin_eat()

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
        self._cleanup_food()
        if self._on_arrive_sound is not None:
            self._on_arrive_sound()
        self._begin_eat()

    def _begin_eat(self) -> None:
        if self._cancelled:
            return
        self._behavior.pause()
        target_state = "hold_bone" if self._food_type == "bone" else "eat"
        self._sm.transition(target_state, force=True)
        self._eat_timer = QTimer(self)
        self._eat_timer.setSingleShot(True)
        self._eat_timer.timeout.connect(self._on_eat_done)
        self._eat_timer.start(_EAT_DURATION_MS)

    def _on_eat_done(self) -> None:
        if self._cancelled:
            return
        self._sm.transition("happy", force=True)
        self._happy_timer = QTimer(self)
        self._happy_timer.setSingleShot(True)
        self._happy_timer.timeout.connect(self._on_happy_done)
        self._happy_timer.start(_HAPPY_DURATION_MS)

    def _on_happy_done(self) -> None:
        if self._cancelled:
            return
        self._sm.transition("idle", force=True)
        self._behavior.resume()
        self.eating_finished.emit(self._food_type)
        self.deleteLater()

    def _on_walk_cancelled(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        self._cleanup_food()
        self._behavior.resume()
        self.eating_finished.emit("")
        self.deleteLater()

    def cancel(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        if self._fall_anim is not None:
            self._fall_anim.stop()
            self._fall_anim = None
        if self._eat_timer is not None:
            self._eat_timer.stop()
            self._eat_timer = None
        if self._happy_timer is not None:
            self._happy_timer.stop()
            self._happy_timer = None
        self._cleanup_food()
        self._behavior.cancel_walk_to()
        self._behavior.resume()
        self.eating_finished.emit("")
        self.deleteLater()

    def _cleanup_food(self) -> None:
        if self._food is not None:
            self._food.close()
            self._food.deleteLater()
            self._food = None
