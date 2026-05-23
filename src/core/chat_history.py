"""聊天历史持久化：保留最近 N 条消息到 %APPDATA%\\XiLeDi\\chat_history.json。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.core.paths import user_data_dir


HISTORY_FILE = "chat_history.json"
MAX_MESSAGES = 40


def _history_path():
    return user_data_dir() / HISTORY_FILE


def load() -> list[dict[str, str]]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
        msgs = data.get("messages", []) if isinstance(data, dict) else []
        return [m for m in msgs if isinstance(m, dict) and "role" in m and "content" in m]
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[chat_history] 加载失败：{exc}")
        return []


def save(messages: list[dict[str, str]]) -> None:
    trimmed = messages[-MAX_MESSAGES:]
    payload: dict[str, Any] = {
        "messages": trimmed,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        with open(_history_path(), "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[chat_history] 保存失败：{exc}")


def clear() -> None:
    save([])
