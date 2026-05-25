"""API Key 安全存储：优先 Windows 凭据管理器（keyring），失败回退 config.json。"""
from __future__ import annotations

from src.core import config

SERVICE = "XiLeDi"
USER = "openai_api_key"

try:
    import keyring
    _KEYRING_OK = True
except ImportError:
    keyring = None
    _KEYRING_OK = False


def is_keyring_available() -> bool:
    return _KEYRING_OK


def get_api_key() -> str:
    if _KEYRING_OK:
        try:
            v = keyring.get_password(SERVICE, USER) or ""
            if v:
                return v
        except Exception as exc:
            print(f"[secrets] keyring 读取失败：{exc}")
    return (config.get("ai", {}) or {}).get("api_key", "")


def set_api_key(value: str) -> None:
    ai = dict(config.get("ai", {}) or {})
    ai["api_key"] = ""
    config.update({"ai": ai})
    if not _KEYRING_OK:
        ai["api_key"] = value
        config.update({"ai": ai})
        return
    try:
        if value:
            keyring.set_password(SERVICE, USER, value)
        else:
            try:
                keyring.delete_password(SERVICE, USER)
            except Exception:
                pass
    except Exception as exc:
        print(f"[secrets] keyring 写入失败，回退 config：{exc}")
        ai["api_key"] = value
        config.update({"ai": ai})


def migrate_from_config() -> None:
    if not _KEYRING_OK:
        return
    ai = dict(config.get("ai", {}) or {})
    legacy = ai.get("api_key", "")
    if not legacy:
        return
    try:
        keyring.set_password(SERVICE, USER, legacy)
        ai["api_key"] = ""
        config.update({"ai": ai})
        print("[secrets] 已把明文 Key 迁移到 Windows 凭据管理器")
    except Exception as exc:
        print(f"[secrets] 迁移失败（保留 config 里的旧值）：{exc}")
