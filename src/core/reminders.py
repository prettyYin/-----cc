"""提醒数据模型：简单两种类型（每日 / 间隔），持久化进 config.reminders。"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any

from src.core import config


TYPE_DAILY = "daily"
TYPE_INTERVAL = "interval"
VALID_TYPES = (TYPE_DAILY, TYPE_INTERVAL)


@dataclass
class Reminder:
    id: str
    title: str
    type: str
    schedule: str
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reminder":
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            title=str(data.get("title", "")),
            type=str(data.get("type", TYPE_DAILY)),
            schedule=str(data.get("schedule", "")),
            enabled=bool(data.get("enabled", True)),
        )


def new_id() -> str:
    return str(uuid.uuid4())


def load_all() -> list[Reminder]:
    raw = config.get("reminders", []) or []
    out: list[Reminder] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(Reminder.from_dict(item))
            except (TypeError, ValueError):
                continue
    return out


def save_all(reminders: list[Reminder]) -> None:
    config.set_value("reminders", [r.to_dict() for r in reminders])


def describe(r: Reminder) -> str:
    """人类可读的调度描述，给提醒列表用。"""
    if r.type == TYPE_DAILY:
        return f"每天 {r.schedule}"
    if r.type == TYPE_INTERVAL:
        return f"每隔 {r.schedule} 分钟"
    return r.type


def validate_schedule(reminder_type: str, schedule: str) -> tuple[bool, str]:
    schedule = schedule.strip()
    if reminder_type == TYPE_DAILY:
        if len(schedule) != 5 or schedule[2] != ":":
            return False, "格式：HH:MM（如 09:30）"
        try:
            hh, mm = int(schedule[:2]), int(schedule[3:])
        except ValueError:
            return False, "时分必须是数字"
        if not (0 <= hh < 24 and 0 <= mm < 60):
            return False, "小时 0-23，分钟 0-59"
        return True, ""
    if reminder_type == TYPE_INTERVAL:
        try:
            n = int(schedule)
        except ValueError:
            return False, "请填一个正整数（分钟数）"
        if n < 1:
            return False, "至少 1 分钟"
        return True, ""
    return False, "未知类型"
