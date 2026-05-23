"""自主行为调度：8 方向移动、概率切状态、定点行走（喂食）、外部 pause/cancel 支持。"""
from __future__ import annotations

import math
import random
from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from src.pet.animator import Animator
from src.pet.state_machine import StateMachine


SPEED_PX_PER_S = 42
TICK_INTERVAL_MS = 40
WALK_TO_ARRIVE_PX = 6


_WALK_DIRECTIONS: list[tuple[int, int]] = [
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (1, -1), (-1, 1), (1, 1),
]


def _idle_duration_ms() -> int:
    return random.randint(5000, 12000)


def _walk_duration_ms() -> int:
    return random.randint(4000, 8000)


def _sit_duration_ms() -> int:
    return random.randint(3000, 6000)


def _sleep_duration_ms() -> int:
    return random.randint(10000, 18000)


class Behavior(QObject):
    position_changed = Signal(int, int)

    def __init__(
        self,
        state_machine: StateMachine,
        animator: Animator,
        pet_size: int = 180,
    ) -> None:
        super().__init__()
        self._sm = state_machine
        self._animator = animator
        self._pet_size = pet_size

        self._dir_x = -1
        self._dir_y = 0
        self._paused = False
        self._current_pos = QPoint(0, 0)
        self._screen_geo: QRect | None = None

        self._mode = "auto"
        self._target_x: int | None = None
        self._on_arrive: Callable[[], None] | None = None
        self._on_cancel: Callable[[], None] | None = None

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(TICK_INTERVAL_MS)
        self._move_timer.timeout.connect(self._on_move_tick)

        self._next_transition_timer = QTimer(self)
        self._next_transition_timer.setSingleShot(True)
        self._next_transition_timer.timeout.connect(self._on_auto_transition)

        self._animator.animation_finished.connect(self._on_animation_finished)

    # --- public API -----------------------------------------------------

    def set_initial_position(self, x: int, y: int) -> None:
        self._current_pos = QPoint(x, y)

    def sync_position(self, x: int, y: int) -> None:
        self._current_pos = QPoint(x, y)

    def start(self) -> None:
        self._refresh_screen_geo()
        self._move_timer.start()
        self._schedule_next_transition()

    def stop(self) -> None:
        self._move_timer.stop()
        self._next_transition_timer.stop()

    def pause(self) -> None:
        if self._paused:
            return
        self._paused = True
        self._next_transition_timer.stop()
        if self._mode == "walk_to":
            cancel_cb = self._on_cancel
            self._mode = "auto"
            self._target_x = None
            self._on_arrive = None
            self._on_cancel = None
            if cancel_cb is not None:
                cancel_cb()

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        self._refresh_screen_geo()
        self._schedule_next_transition()

    def is_paused(self) -> bool:
        return self._paused

    def mode(self) -> str:
        return self._mode

    def walk_to(
        self,
        target_x: int,
        _target_y: int,
        on_arrive: Callable[[], None],
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        if self._paused:
            if on_cancel is not None:
                on_cancel()
            return
        self._next_transition_timer.stop()
        self._mode = "walk_to"
        self._target_x = target_x
        self._on_arrive = on_arrive
        self._on_cancel = on_cancel
        direction = 1 if target_x > self._current_pos.x() else -1
        self._dir_x = direction
        self._dir_y = 0
        self._animator.set_direction(direction)
        self._sm.transition("walk", force=True)

    def cancel_walk_to(self) -> None:
        if self._mode != "walk_to":
            return
        self._mode = "auto"
        self._target_x = None
        self._on_arrive = None
        self._on_cancel = None
        if not self._paused:
            self._schedule_next_transition()

    # --- internals ------------------------------------------------------

    def _refresh_screen_geo(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            self._screen_geo = screen.availableGeometry()

    def _on_move_tick(self) -> None:
        if self._paused:
            return
        if self._sm.state() != "walk":
            return
        if self._screen_geo is None:
            self._refresh_screen_geo()
            if self._screen_geo is None:
                return

        norm = math.sqrt(self._dir_x ** 2 + self._dir_y ** 2)
        if norm == 0:
            return

        dt_s = TICK_INTERVAL_MS / 1000.0
        vx = SPEED_PX_PER_S * self._dir_x / norm
        vy = SPEED_PX_PER_S * self._dir_y / norm
        dx = int(vx * dt_s)
        dy = int(vy * dt_s)
        if dx == 0 and self._dir_x != 0:
            dx = self._dir_x
        if dy == 0 and self._dir_y != 0:
            dy = self._dir_y

        new_x = self._current_pos.x() + dx
        new_y = self._current_pos.y() + dy

        if self._mode == "walk_to" and self._target_x is not None:
            crossed = (
                (self._dir_x > 0 and new_x >= self._target_x)
                or (self._dir_x < 0 and new_x <= self._target_x)
            )
            if crossed or abs(new_x - self._target_x) <= WALK_TO_ARRIVE_PX:
                new_x = self._target_x
                self._current_pos.setX(new_x)
                self.position_changed.emit(new_x, self._current_pos.y())
                self._complete_walk_to()
                return

        min_x = self._screen_geo.left()
        max_x = self._screen_geo.right() - self._pet_size
        min_y = self._screen_geo.top()
        max_y = self._screen_geo.bottom() - self._pet_size

        if new_x < min_x:
            new_x = min_x
            self._dir_x = -self._dir_x
            self._update_sprite_direction()
        elif new_x > max_x:
            new_x = max_x
            self._dir_x = -self._dir_x
            self._update_sprite_direction()

        if new_y < min_y:
            new_y = min_y
            self._dir_y = -self._dir_y
        elif new_y > max_y:
            new_y = max_y
            self._dir_y = -self._dir_y

        if new_x != self._current_pos.x() or new_y != self._current_pos.y():
            self._current_pos.setX(new_x)
            self._current_pos.setY(new_y)
            self.position_changed.emit(new_x, new_y)

    def _update_sprite_direction(self) -> None:
        if self._dir_x > 0:
            self._animator.set_direction(1)
        elif self._dir_x < 0:
            self._animator.set_direction(-1)

    def _complete_walk_to(self) -> None:
        cb = self._on_arrive
        self._on_arrive = None
        self._on_cancel = None
        self._target_x = None
        self._mode = "auto"
        if cb is not None:
            cb()
        self._schedule_next_transition()

    def _schedule_next_transition(self) -> None:
        if self._mode == "walk_to" or self._paused:
            return
        state = self._sm.state()
        if state == "idle":
            ms = _idle_duration_ms()
        elif state == "walk":
            ms = _walk_duration_ms()
        elif state == "sit":
            ms = _sit_duration_ms()
        elif state == "sleep":
            ms = _sleep_duration_ms()
        else:
            ms = 2500
        self._next_transition_timer.start(ms)

    def _on_auto_transition(self) -> None:
        if self._paused or self._mode == "walk_to":
            return
        state = self._sm.state()
        if state == "idle":
            roll = random.random()
            if roll < 0.3:
                self._dir_x, self._dir_y = random.choice(_WALK_DIRECTIONS)
                self._update_sprite_direction()
                self._sm.transition("walk")
            elif roll < 0.7:
                self._sm.transition("sit")
            else:
                self._sm.transition("sleep")
        else:
            self._sm.transition("idle")
        self._schedule_next_transition()

    def _on_animation_finished(self, state: str) -> None:
        if state == "dizzy":
            self._sm.transition("idle", force=True)
            if self._paused:
                self.resume()
