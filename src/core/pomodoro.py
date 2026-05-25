"""学习陪伴：一次性专注计时；倒计时归零后自动 stop（emit IDLE）。"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from src.core import config


STATE_IDLE = "idle"
STATE_FOCUS = "focus"

TICK_INTERVAL_MS = 1000


def _cfg() -> dict:
    return config.get("pomodoro", {}) or {}


class PomodoroController(QObject):
    """状态变化时 emit (state, remaining_seconds)；focus 归零后 emit IDLE 收尾。"""

    state_changed = Signal(str, int)

    def __init__(self) -> None:
        super().__init__()
        self._state = STATE_IDLE
        self._remaining_s = 0

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    # --- public API -----------------------------------------------------

    def state(self) -> str:
        return self._state

    def remaining_seconds(self) -> int:
        return self._remaining_s

    def is_running(self) -> bool:
        return self._state != STATE_IDLE

    def start(self) -> None:
        if self.is_running():
            return
        self._enter_focus()

    def stop(self) -> None:
        if not self.is_running():
            return
        self._timer.stop()
        self._state = STATE_IDLE
        self._remaining_s = 0
        self.state_changed.emit(STATE_IDLE, 0)

    # --- internals ------------------------------------------------------

    def _enter_focus(self) -> None:
        minutes = int(_cfg().get("focus_minutes", 25) or 25)
        self._state = STATE_FOCUS
        self._remaining_s = max(1, minutes) * 60
        self.state_changed.emit(self._state, self._remaining_s)
        self._timer.start()

    def _tick(self) -> None:
        if self._state == STATE_IDLE:
            self._timer.stop()
            return
        self._remaining_s -= 1
        if self._remaining_s > 0:
            self.state_changed.emit(self._state, self._remaining_s)
            return
        self.stop()
