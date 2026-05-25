"""AI 聊天面板：独立可拖动窗口，气泡列表 + 流式渲染 + 历史持久化 + 一键清空。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ai import persona
from src.ai.client import ChatWorker
from src.core import chat_history, config, fonts, secrets


_PANEL_QSS_TEMPLATE = """
QDialog {{
    background: #FFF8EC;
    font-family: {family};
}}
QScrollArea {{ border: 2px solid #5C4221; background: #FFFCF5; }}
QFrame#bubble_assistant {{
    background: #FFF1CC;
    border: 2px solid #5C4221;
    border-radius: 0px;
}}
QFrame#bubble_user {{
    background: #C8E4F5;
    border: 2px solid #5C4221;
    border-radius: 0px;
}}
QLabel {{
    color: #3B2A1A;
    font-family: {family};
}}
QLineEdit {{
    border: 2px solid #5C4221;
    border-radius: 0px;
    padding: 6px 10px;
    background: #FFFCF5;
    color: #3B2A1A;
    font-family: {family};
}}
QLineEdit:disabled {{
    background: #E8DDC6;
    color: #998877;
}}
QPushButton {{
    background: #F4C77B;
    border: 2px solid #5C4221;
    border-radius: 0px;
    padding: 6px 16px;
    color: #3B2A1A;
    font-family: {family};
}}
QPushButton:hover {{ background: #FFD89C; }}
QPushButton:pressed {{ background: #E0AC5C; }}
QPushButton:disabled {{ background: #E8DDC6; color: #998877; border-color: #998877; }}
QPushButton#clear_btn {{
    background: #FFFCF5;
    border: 2px solid #998877;
    padding: 4px 12px;
}}
QPushButton#clear_btn:hover {{ background: #FFE9B8; border-color: #5C4221; }}
QScrollBar:vertical {{
    background: #E8DDC6;
    border-left: 2px solid #5C4221;
    width: 14px;
}}
QScrollBar::handle:vertical {{
    background: #C9A66B;
    border: 2px solid #5C4221;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


_BUBBLE_MAX_WIDTH = 280


class MessageBubble(QFrame):
    def __init__(self, role: str, text: str = "") -> None:
        super().__init__()
        self.setObjectName(f"bubble_{role}")
        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self._label)
        self.setMaximumWidth(_BUBBLE_MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

    def append_text(self, chunk: str) -> None:
        self._label.setText(self._label.text() + chunk)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def text(self) -> str:
        return self._label.text()


class ChatPanel(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("和小喜聊天 🐾")
        self.setMinimumSize(380, 520)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_PANEL_QSS_TEMPLATE.format(family=fonts.family_css()))
        self.setFont(fonts.pixel_font(11))

        self._messages: list[dict[str, str]] = chat_history.load()
        self._current_assistant_bubble: MessageBubble | None = None
        self._worker: ChatWorker | None = None

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self._messages_layout = QVBoxLayout(scroll_content)
        self._messages_layout.setAlignment(Qt.AlignTop)
        self._messages_layout.setSpacing(8)
        self._messages_layout.setContentsMargins(6, 6, 6, 6)
        self._scroll.setWidget(scroll_content)

        self._input = QLineEdit()
        self._input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("发送")
        self._send_btn.setAutoDefault(False)
        self._send_btn.setDefault(False)
        self._send_btn.clicked.connect(self._on_send)

        input_row = QHBoxLayout()
        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._send_btn)

        self._clear_btn = QPushButton("清空历史")
        self._clear_btn.setObjectName("clear_btn")
        self._clear_btn.setAutoDefault(False)
        self._clear_btn.setDefault(False)
        self._clear_btn.clicked.connect(self._on_clear)
        hint = QLabel(f"保留最近 {chat_history.MAX_MESSAGES // 2} 轮，更早的会自动清掉")
        hint.setStyleSheet("color: #998877; font-size: 10px;")
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(hint)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self._clear_btn)

        self._status = QLabel()
        self._status.setStyleSheet("color: #C73666; font-size: 11px;")
        self._status.setWordWrap(True)
        self._status.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self._scroll, 1)
        layout.addWidget(self._status)
        layout.addLayout(input_row)
        layout.addLayout(bottom_row)

        self._render_history()
        self._update_input_enabled()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(50, self._scroll_to_bottom)
        if not self._has_api_key():
            self._show_status("还没填 API Key，去 设置→AI 配一下就能聊啦～")

    def refresh_after_settings_change(self) -> None:
        self._update_input_enabled()
        if self._has_api_key():
            self._hide_status()

    def _has_api_key(self) -> bool:
        return bool(secrets.get_api_key())

    def _update_input_enabled(self) -> None:
        has_key = self._has_api_key()
        is_streaming = self._worker is not None
        enabled = has_key and not is_streaming
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        if not has_key:
            self._input.setPlaceholderText("先去 设置→AI 填 API Key…")
        elif is_streaming:
            self._input.setPlaceholderText("小喜正在打字…")
        else:
            self._input.setPlaceholderText("跟小喜说点什么…")

    def _render_history(self) -> None:
        while self._messages_layout.count():
            item = self._messages_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if not self._messages:
            self._add_bubble("assistant", "汪~ 我是小喜！想聊点啥都可以 🐾")
        else:
            for m in self._messages:
                self._add_bubble(m["role"], m["content"])

    def _add_bubble(self, role: str, text: str) -> MessageBubble:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        bubble = MessageBubble(role, text)
        if role == "assistant":
            row_layout.addWidget(bubble)
            row_layout.addStretch(1)
        else:
            row_layout.addStretch(1)
            row_layout.addWidget(bubble)
        self._messages_layout.addWidget(row)
        QTimer.singleShot(0, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        if not self._has_api_key():
            self._show_status("还没填 API Key，去 设置→AI 配一下就能聊啦～")
            return
        if self._worker is not None:
            return
        self._input.clear()
        self._hide_status()

        self._messages.append({"role": "user", "content": text})
        self._add_bubble("user", text)
        self._current_assistant_bubble = self._add_bubble("assistant", "")

        ai_cfg = dict(config.get("ai", {}) or {})
        ai_cfg["api_key"] = secrets.get_api_key()
        full_messages: list[dict[str, str]] = [
            {"role": "system", "content": persona.build_system_prompt()}
        ]
        full_messages.extend(self._messages)

        self._worker = ChatWorker(full_messages, ai_cfg)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()
        self._update_input_enabled()

    def _on_chunk(self, chunk: str) -> None:
        if self._current_assistant_bubble is not None:
            self._current_assistant_bubble.append_text(chunk)
            self._scroll_to_bottom()

    def _on_finished(self) -> None:
        if self._current_assistant_bubble is not None:
            content = self._current_assistant_bubble.text()
            if content:
                self._messages.append({"role": "assistant", "content": content})
                chat_history.save(self._messages)
        self._cleanup_worker()

    def _on_failed(self, error: str) -> None:
        if self._current_assistant_bubble is not None and not self._current_assistant_bubble.text():
            self._current_assistant_bubble.set_text("呜…出问题了 😿")
        self._show_status(f"出错了：{error}")
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        self._current_assistant_bubble = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._update_input_enabled()

    def _on_clear(self) -> None:
        confirm = QMessageBox.question(
            self,
            "清空历史",
            "确认清空和小喜的全部聊天记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self._messages = []
        chat_history.clear()
        self._render_history()
        self._hide_status()

    def _show_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.show()

    def _hide_status(self) -> None:
        self._status.hide()
