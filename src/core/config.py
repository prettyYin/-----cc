"""配置读写：JSON 持久化到 %APPDATA%\\XiLeDi\\config.json。"""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from src.core.paths import user_data_dir


CONFIG_FILE = "config.json"


DEFAULTS: dict[str, Any] = {
    "always_on_top": True,
    "sound_enabled": True,
    "autostart": False,
    "pet_size": 180,
    "ai": {
        "provider": "",
        "base_url": "",
        "api_key": "",
        "model": "",
    },
    "reminders": [],
}


_cache: dict[str, Any] | None = None


def _config_path():
    return user_data_dir() / CONFIG_FILE


def _merge_defaults(loaded: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(DEFAULTS)
    for key, value in loaded.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def load() -> dict[str, Any]:
    global _cache
    path = _config_path()
    if not path.exists():
        _cache = deepcopy(DEFAULTS)
        save(_cache)
        return _cache
    try:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
        _cache = _merge_defaults(data) if isinstance(data, dict) else deepcopy(DEFAULTS)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[config] 解析失败，使用默认配置：{exc}")
        _cache = deepcopy(DEFAULTS)
    return _cache


def save(cfg: dict[str, Any] | None = None) -> None:
    global _cache
    if cfg is not None:
        _cache = cfg
    if _cache is None:
        _cache = deepcopy(DEFAULTS)
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(_cache, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[config] 写入失败：{exc}")


def get(key: str, default: Any = None) -> Any:
    if _cache is None:
        load()
    assert _cache is not None
    return _cache.get(key, default if default is not None else DEFAULTS.get(key))


def set_value(key: str, value: Any) -> None:
    if _cache is None:
        load()
    assert _cache is not None
    _cache[key] = value
    save()


def update(partial: dict[str, Any]) -> None:
    if _cache is None:
        load()
    assert _cache is not None
    for key, value in partial.items():
        if key in _cache and isinstance(_cache[key], dict) and isinstance(value, dict):
            _cache[key].update(value)
        else:
            _cache[key] = value
    save()
