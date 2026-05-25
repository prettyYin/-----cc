"""精灵帧动画引擎：读 manifest 加载帧，QTimer 切帧，水平镜像支持，缺帧回落占位。"""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap, QTransform

from src.core.paths import sprites_dir
from src.pet.placeholder_art import make_placeholder_frame
from src.pet.state_machine import StateMachine
from src.ui.pixel_art import dewhite_pixmap


_DEFAULT_MANIFEST: dict[str, Any] = {
    "states": {
        "idle":  {"frames": 4, "fps": 3,  "loop": True},
        "walk":  {"frames": 6, "fps": 10, "loop": True},
        "sit":   {"frames": 2, "fps": 2,  "loop": True},
        "sleep": {"frames": 3, "fps": 3,  "loop": True},
        "happy": {"frames": 5, "fps": 12, "loop": True},
        "dizzy": {"frames": 4, "fps": 8,  "loop": True},
    }
}


class Animator(QObject):
    frame_changed = Signal(QPixmap)
    animation_finished = Signal(str)

    def __init__(self, state_machine: StateMachine, pet_size: int = 180) -> None:
        super().__init__()
        self._sm = state_machine
        self._size = pet_size

        self._manifest = self._load_manifest()
        self._frames: dict[str, list[QPixmap]] = {}
        self._mirrored: dict[str, list[QPixmap]] = {}
        self._load_all_frames()

        self._current_frame_idx = 0
        self._direction = -1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._sm.state_changed.connect(self._on_state_changed)
        self._start_timer_for(self._sm.state())
        self._emit_current()

    def set_direction(self, direction: int) -> None:
        if direction not in (-1, 1):
            return
        if self._direction == direction:
            return
        self._direction = direction
        self._emit_current()

    def direction(self) -> int:
        return self._direction

    def _load_manifest(self) -> dict[str, Any]:
        path = sprites_dir() / "manifest.json"
        if not path.exists():
            return _DEFAULT_MANIFEST
        try:
            with open(path, encoding="utf-8") as fp:
                data = json.load(fp)
            if "states" in data:
                return data
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[Animator] manifest 解析失败，使用默认值: {exc}")
        return _DEFAULT_MANIFEST

    def _load_all_frames(self) -> None:
        for state, conf in self._manifest["states"].items():
            n = int(conf.get("frames", 1))
            self._frames[state] = self._load_state_frames(state, n)
            self._mirrored[state] = [
                pm.transformed(QTransform().scale(-1, 1)) for pm in self._frames[state]
            ]

    def _load_state_frames(self, state: str, n_frames: int) -> list[QPixmap]:
        state_dir = sprites_dir() / state
        frames: list[QPixmap] = []
        for i in range(1, n_frames + 1):
            path = state_dir / f"frame_{i:02d}.png"
            if path.exists():
                pm = QPixmap(str(path))
                if pm.isNull():
                    pm = make_placeholder_frame(state, i, self._size)
                else:
                    pm = dewhite_pixmap(pm)
                    if pm.width() != self._size or pm.height() != self._size:
                        pm = pm.scaled(
                            self._size,
                            self._size,
                            Qt.KeepAspectRatio,
                            Qt.FastTransformation,
                        )
                frames.append(pm)
            else:
                frames.append(make_placeholder_frame(state, i, self._size))
        return frames

    def _start_timer_for(self, state: str) -> None:
        conf = self._manifest["states"].get(state, {})
        fps = max(1, int(conf.get("fps", 8)))
        self._timer.start(max(16, int(1000 / fps)))

    def _on_state_changed(self, _old: str, new: str) -> None:
        self._current_frame_idx = 0
        self._start_timer_for(new)
        self._emit_current()

    def _on_tick(self) -> None:
        state = self._sm.state()
        frames = self._frames.get(state, [])
        if not frames:
            return
        conf = self._manifest["states"].get(state, {})
        next_idx = self._current_frame_idx + 1
        if next_idx >= len(frames):
            if conf.get("loop", True):
                self._current_frame_idx = 0
                self._emit_current()
            else:
                self._current_frame_idx = len(frames) - 1
                self._timer.stop()
                self.animation_finished.emit(state)
        else:
            self._current_frame_idx = next_idx
            self._emit_current()

    def _emit_current(self) -> None:
        state = self._sm.state()
        bank = self._mirrored if self._direction > 0 else self._frames
        frames = bank.get(state, [])
        if not frames:
            return
        idx = min(self._current_frame_idx, len(frames) - 1)
        self.frame_changed.emit(frames[idx])
