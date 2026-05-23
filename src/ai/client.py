"""AI 流式客户端：QThread 包装 openai SDK，避免阻塞 UI；测试连接同步函数。"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class ChatWorker(QThread):
    chunk_received = Signal(str)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(
        self,
        messages: list[dict[str, str]],
        ai_config: dict[str, str],
    ) -> None:
        super().__init__()
        self._messages = messages
        self._cfg = ai_config

    def run(self) -> None:
        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=self._cfg.get("base_url") or None,
                api_key=self._cfg.get("api_key") or "EMPTY",
                timeout=60,
            )
            stream = client.chat.completions.create(
                model=self._cfg.get("model") or "gpt-4o-mini",
                messages=self._messages,
                stream=True,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content or ""
                except (AttributeError, IndexError):
                    delta = ""
                if delta:
                    self.chunk_received.emit(delta)
            self.finished_ok.emit()
        except Exception as exc:
            self.failed.emit(_format_error(exc))


def test_connection(ai_config: dict[str, str]) -> tuple[bool, str]:
    """同步发一条 hi，返回 (success, message)。仅供"测试连接"按钮使用。"""
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=ai_config.get("base_url") or None,
            api_key=ai_config.get("api_key") or "EMPTY",
            timeout=15,
        )
        resp = client.chat.completions.create(
            model=ai_config.get("model") or "gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=8,
        )
        content = resp.choices[0].message.content or "(empty)"
        return True, f"连接成功！模型回复：{content.strip()[:40]}"
    except Exception as exc:
        return False, _format_error(exc)


def _format_error(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = str(exc)
    if not msg:
        return name
    if len(msg) > 300:
        msg = msg[:300] + "…"
    return f"{name}: {msg}"
