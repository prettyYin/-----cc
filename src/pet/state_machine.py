"""桌宠状态机：定义合法转移、最小停留时长、状态变更信号。"""
from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QObject, Signal


STATES = ("idle", "walk", "sit", "sleep", "happy", "dizzy")


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "idle":  {"walk", "sit", "sleep", "happy", "dizzy"},
    "walk":  {"idle", "happy", "dizzy"},
    "sit":   {"idle", "happy", "dizzy"},
    "sleep": {"idle", "dizzy"},
    "happy": {"idle", "dizzy"},
    "dizzy": {"idle"},
}


_MIN_DURATION_MS: dict[str, int] = {
    "idle":  300,
    "walk":  500,
    "sit":   500,
    "sleep": 1000,
    "happy": 500,
    "dizzy": 500,
}


class StateMachine(QObject):
    state_changed = Signal(str, str)

    def __init__(self, initial: str = "idle") -> None:
        super().__init__()
        if initial not in STATES:
            raise ValueError(f"未知状态：{initial}")
        self._state = initial
        self._entered_at = QElapsedTimer()
        self._entered_at.start()

    def state(self) -> str:
        return self._state

    def elapsed_ms(self) -> int:
        return self._entered_at.elapsed()

    def can_transition(self, new_state: str) -> bool:
        if new_state == self._state:
            return False
        if new_state not in STATES:
            return False
        if new_state not in _VALID_TRANSITIONS.get(self._state, set()):
            return False
        if self._entered_at.elapsed() < _MIN_DURATION_MS.get(self._state, 0):
            return False
        return True

    def transition(self, new_state: str, force: bool = False) -> bool:
        if new_state == self._state:
            return False
        if not force and not self.can_transition(new_state):
            return False
        old = self._state
        self._state = new_state
        self._entered_at.restart()
        self.state_changed.emit(old, new_state)
        return True
