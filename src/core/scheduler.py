"""提醒调度器：每 30 秒巡检一次启用的提醒，到点 emit triggered(title) 信号。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from src.core import reminders


CHECK_INTERVAL_MS = 30_000


class ReminderScheduler(QObject):
    triggered = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check)

        self._daily_fired_on: dict[str, date] = {}
        self._interval_last_fired: dict[str, datetime] = {}
        self._interval_baseline: dict[str, datetime] = {}

    def start(self) -> None:
        self._reset_interval_baseline()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def force_check(self) -> None:
        self._check()

    def _reset_interval_baseline(self) -> None:
        now = datetime.now()
        for r in reminders.load_all():
            if r.type == reminders.TYPE_INTERVAL and r.enabled:
                self._interval_baseline.setdefault(r.id, now)

    def _check(self) -> None:
        now = datetime.now()
        for r in reminders.load_all():
            if not r.enabled:
                continue
            if self._should_fire(r, now):
                self.triggered.emit(r.title)
                self._mark_fired(r, now)

    def _should_fire(self, r: reminders.Reminder, now: datetime) -> bool:
        if r.type == reminders.TYPE_DAILY:
            ok, _ = reminders.validate_schedule(r.type, r.schedule)
            if not ok:
                return False
            hh, mm = int(r.schedule[:2]), int(r.schedule[3:])
            target_today = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            already = self._daily_fired_on.get(r.id)
            if already == now.date():
                return False
            if now >= target_today and (now - target_today) < timedelta(minutes=2):
                return True
            return False
        if r.type == reminders.TYPE_INTERVAL:
            ok, _ = reminders.validate_schedule(r.type, r.schedule)
            if not ok:
                return False
            minutes = int(r.schedule)
            last = self._interval_last_fired.get(r.id)
            baseline = self._interval_baseline.setdefault(r.id, now)
            reference = last if last is not None else baseline
            return (now - reference) >= timedelta(minutes=minutes)
        return False

    def _mark_fired(self, r: reminders.Reminder, now: datetime) -> None:
        if r.type == reminders.TYPE_DAILY:
            self._daily_fired_on[r.id] = now.date()
        elif r.type == reminders.TYPE_INTERVAL:
            self._interval_last_fired[r.id] = now
