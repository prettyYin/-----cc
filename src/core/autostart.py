"""开机自启：读写 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run，无需管理员权限。"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "XiLeDi"


def _command_to_run() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    project_root = Path(__file__).resolve().parents[2]
    bat = project_root / "启动小喜.bat"
    if bat.exists():
        return f'"{bat}"'
    return f'"{sys.executable}" "{project_root / "main.py"}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _APP_NAME)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError as exc:
        print(f"[autostart] 查询失败：{exc}")
        return False


def enable() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _command_to_run())
        return True
    except OSError as exc:
        print(f"[autostart] 启用失败：{exc}")
        return False


def disable() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError as exc:
        print(f"[autostart] 禁用失败：{exc}")
        return False


def apply(enabled: bool) -> bool:
    return enable() if enabled else disable()
