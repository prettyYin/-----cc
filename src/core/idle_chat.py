"""主动搭话调度：用户长时间不互动时，桌宠按时段分类挑一句话冒气泡。"""
from __future__ import annotations

import json
import random
from datetime import datetime, time

from PySide6.QtCore import QObject, QTimer, Signal

from src.core import config
from src.core.paths import assets_dir


CHECK_INTERVAL_MS = 60_000
ENCOURAGE_PROB = 0.30


def _load_phrases() -> dict[str, list[str]]:
    path = assets_dir() / "data" / "idle_phrases.json"
    try:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[idle_chat] 语料加载失败：{exc}")
        return {"default": ["汪~"]}
    out: dict[str, list[str]] = {}
    for key in ("default", "morning", "evening", "night", "encourage",
                "after_feed_bone", "after_feed_dogfood", "peek_wave"):
        items = data.get(key)
        if isinstance(items, list) and items:
            out[key] = [str(s) for s in items if isinstance(s, str)]
    if "default" not in out:
        out["default"] = ["汪~"]
    return out


def _category_for_hour(hour: int) -> str:
    if 6 <= hour < 10:
        return "morning"
    if 17 <= hour < 20:
        return "evening"
    if hour >= 22 or hour < 6:
        return "night"
    return "default"


def _parse_hhmm(text: str, fallback: time) -> time:
    try:
        hh, mm = text.split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return fallback


def _in_quiet_hours(now: datetime, start: time, end: time) -> bool:
    cur = now.time()
    if start == end:
        return False
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


class IdleChatter(QObject):
    phrase_ready = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._phrases = _load_phrases()
        self._last_interact_at: datetime = datetime.now()
        self._paused = False
        self._visible = True

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._last_interact_at = datetime.now()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def notify_interaction(self) -> None:
        self._last_interact_at = datetime.now()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self._last_interact_at = datetime.now()

    def set_visible(self, visible: bool) -> None:
        self._visible = visible

    def say_event(self, category: str) -> None:
        bucket = self._phrases.get(category)
        if not bucket:
            return
        phrase = random.choice(bucket)
        self.phrase_ready.emit(phrase)
        self._last_interact_at = datetime.now()

    def pick_phrase(self, category: str) -> str | None:
        """从某类语料里直接挑一句，不走 phrase_ready 信号，由调用方决定怎么显示。"""
        bucket = self._phrases.get(category)
        if not bucket:
            return None
        return random.choice(bucket)

    def _tick(self) -> None:
        if self._paused or not self._visible:
            return
        cfg = config.get("idle_chat", {}) or {}
        if not cfg.get("enabled", True):
            return

        now = datetime.now()
        interval_min = int(cfg.get("interval_minutes", 15) or 15)
        if (now - self._last_interact_at).total_seconds() < interval_min * 60:
            return

        quiet_start = _parse_hhmm(cfg.get("quiet_start", "22:00"), time(22, 0))
        quiet_end = _parse_hhmm(cfg.get("quiet_end", "08:00"), time(8, 0))
        if cfg.get("quiet_enabled", False) and _in_quiet_hours(now, quiet_start, quiet_end):
            return

        phrase = self._pick_phrase(now.hour)
        if phrase is None:
            return
        self.phrase_ready.emit(phrase)
        self._last_interact_at = now

    def _pick_phrase(self, hour: int) -> str | None:
        if random.random() < ENCOURAGE_PROB and self._phrases.get("encourage"):
            return random.choice(self._phrases["encourage"])
        category = _category_for_hour(hour)
        bucket = self._phrases.get(category) or self._phrases.get("default")
        if not bucket:
            return None
        return random.choice(bucket)
