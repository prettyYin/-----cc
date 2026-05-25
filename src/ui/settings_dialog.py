"""设置面板：QTabWidget 三标签页（通用 / AI / 提醒），保存即写配置。"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, QTime, Signal
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from src.ai import client as ai_client
from src.ai.presets import DEFAULT_MODEL_PLACEHOLDER, MODEL_PLACEHOLDERS, PRESETS, PROVIDER_NAMES
from src.core import autostart, config, fonts, reminders, secrets
from src.core.paths import user_data_dir
from src.ui.pixel_art import render_pattern


def _ensure_check_icon_path() -> str:
    """生成 ✓ 像素 PNG 到 user_data_dir，返回 QSS 可用的正斜杠路径。"""
    path = user_data_dir() / "check_icon.png"
    if not path.exists():
        pattern = [
            ".......",
            "......X",
            ".....XX",
            "X...XX.",
            "XX.XX..",
            ".XXX...",
            "..X....",
        ]
        pm = render_pattern(pattern, {"X": "#FFF8EC"}, scale=2, canvas_size=(18, 18))
        pm.save(str(path), "PNG")
    return str(path).replace("\\", "/")


class _HelpHint(QLabel):
    """悬停时手动 QToolTip.showText 的小图标，比默认 QLabel tooltip 更稳定。"""

    def __init__(self, text: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._tooltip_text = tooltip
        self.setCursor(Qt.WhatsThisCursor)

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        QToolTip.showText(pos, self._tooltip_text, self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        QToolTip.hideText()
        super().leaveEvent(event)



_DIALOG_QSS_TEMPLATE = """
QDialog {{
    background: #FFF8EC;
    font-family: {family};
}}
QLabel {{ color: #3B2A1A; font-family: {family}; }}
QTabWidget::pane {{
    border: 2px solid #5C4221;
    background: #FFFCF5;
    top: -2px;
}}
QTabBar::tab {{
    background: #E8DDC6;
    border: 2px solid #5C4221;
    border-bottom: none;
    padding: 6px 18px;
    margin-right: 2px;
    color: #3B2A1A;
    font-family: {family};
}}
QTabBar::tab:selected {{ background: #F4C77B; }}
QTabBar::tab:hover {{ background: #FFE9B8; }}
QCheckBox {{ color: #3B2A1A; spacing: 8px; font-family: {family}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid #5C4221;
    background: #FFFCF5;
}}
QCheckBox::indicator:hover {{ border-color: #E45550; }}
QCheckBox::indicator:checked {{
    background: #5C4221;
    border: 2px solid #5C4221;
    image: url("{check_icon}");
}}
QLineEdit, QComboBox {{
    border: 2px solid #5C4221;
    border-radius: 0px;
    padding: 4px 8px;
    background: #FFFCF5;
    color: #3B2A1A;
    font-family: {family};
}}
QSpinBox, QTimeEdit {{
    border: 2px solid #5C4221;
    border-radius: 0px;
    padding: 4px 8px;
    background: #FFFCF5;
    color: #3B2A1A;
    font-family: {family};
}}
QSpinBox::up-button, QSpinBox::down-button,
QTimeEdit::up-button, QTimeEdit::down-button {{
    width: 16px;
    background: #F4C77B;
    border: 1px solid #5C4221;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{ background: #FFD89C; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #5C4221;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    border: 2px solid #5C4221;
    background: #FFFCF5;
    selection-background-color: #F4C77B;
    selection-color: #3B2A1A;
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
QTableWidget {{
    background: #FFFCF5;
    border: 2px solid #5C4221;
    gridline-color: #C9A66B;
    font-family: {family};
}}
QHeaderView::section {{
    background: #E8DDC6;
    border: 1px solid #5C4221;
    padding: 4px 8px;
    color: #3B2A1A;
    font-family: {family};
}}
QToolTip {{
    background: #FFFCF5;
    color: #3B2A1A;
    border: 2px solid #5C4221;
    padding: 4px 8px;
    font-family: {family};
}}
"""


class SettingsDialog(QDialog):
    settings_applied = Signal()

    def __init__(self, parent: QWidget | None = None, initial_tab: int = 0) -> None:
        super().__init__(parent)
        self.setWindowTitle("小喜设置")
        self.setMinimumSize(440, 380)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_DIALOG_QSS_TEMPLATE.format(family=fonts.family_css(), check_icon=_ensure_check_icon_path()))
        self.setFont(fonts.pixel_font(11))

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "通用")
        self._tabs.addTab(self._build_companion_tab(), "陪伴")
        self._tabs.addTab(self._build_ai_tab(), "AI")
        self._tabs.addTab(self._build_reminders_tab(), "提醒")
        self._tabs.setCurrentIndex(initial_tab)

        ok_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addLayout(btn_row)

    # --- 通用 tab -------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setLabelAlignment(Qt.AlignLeft)

        self._chk_top = QCheckBox("永远置顶")
        self._chk_top.setChecked(bool(config.get("always_on_top", True)))

        self._chk_sound = QCheckBox("启用音效")
        self._chk_sound.setChecked(bool(config.get("sound_enabled", True)))

        self._chk_autostart = QCheckBox("开机自动启动")
        self._chk_autostart.setChecked(bool(config.get("autostart", False)))

        form.addRow(self._chk_top)
        form.addRow(self._chk_sound)
        form.addRow(self._chk_autostart)
        form.addRow(QLabel("（保存后立即生效）"))

        return widget

    # --- 陪伴 tab -------------------------------------------------------

    def _build_companion_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        idle_cfg = config.get("idle_chat", {}) or {}
        pomo_cfg = config.get("pomodoro", {}) or {}

        # 主动搭话
        layout.addWidget(QLabel("主动搭话"))
        idle_form = QFormLayout()

        self._chk_idle_enabled = QCheckBox("启用主动搭话")
        self._chk_idle_enabled.setChecked(bool(idle_cfg.get("enabled", True)))

        self._spn_idle_interval = QSpinBox()
        self._spn_idle_interval.setRange(1, 240)
        self._spn_idle_interval.setSuffix(" 分钟未操作后")
        self._spn_idle_interval.setValue(int(idle_cfg.get("interval_minutes", 15) or 15))

        def _make_time_edit(text: str) -> QTimeEdit:
            tim = QTimeEdit()
            tim.setDisplayFormat("HH:mm")
            try:
                hh, mm = text.split(":")
                tim.setTime(QTime(int(hh), int(mm)))
            except (ValueError, AttributeError):
                tim.setTime(QTime(22, 0))
            return tim

        self._tim_quiet_start = _make_time_edit(str(idle_cfg.get("quiet_start", "22:00")))
        self._tim_quiet_end = _make_time_edit(str(idle_cfg.get("quiet_end", "08:00")))
        quiet_row = QHBoxLayout()
        quiet_row.addWidget(self._tim_quiet_start)
        quiet_row.addWidget(QLabel("–"))
        quiet_row.addWidget(self._tim_quiet_end)
        quiet_holder = QWidget()
        quiet_holder.setLayout(quiet_row)

        self._chk_quiet_enabled = QCheckBox("启用小喜休息时间")
        self._chk_quiet_enabled.setChecked(bool(idle_cfg.get("quiet_enabled", False)))

        def _sync_quiet_enabled(checked: bool) -> None:
            self._tim_quiet_start.setEnabled(checked)
            self._tim_quiet_end.setEnabled(checked)

        self._chk_quiet_enabled.toggled.connect(_sync_quiet_enabled)
        _sync_quiet_enabled(self._chk_quiet_enabled.isChecked())

        idle_form.addRow(self._chk_idle_enabled)
        idle_form.addRow("搭话时机", self._spn_idle_interval)
        idle_form.addRow(self._chk_quiet_enabled)
        idle_form.addRow("小喜休息时间", quiet_holder)
        layout.addLayout(idle_form)

        # 番茄钟
        layout.addSpacing(8)
        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.addWidget(QLabel("学习陪伴"))
        help_tip = _HelpHint("ⓘ", "专注 N 分钟后休息一会，要劳逸结合哦~")
        help_tip.setStyleSheet("color: #5C4221; padding: 0 4px;")
        heading_row.addWidget(help_tip)
        heading_row.addStretch(1)
        heading_holder = QWidget()
        heading_holder.setLayout(heading_row)
        layout.addWidget(heading_holder)
        pomo_form = QFormLayout()

        self._chk_pomo_enabled = QCheckBox("启用学习陪伴")
        self._chk_pomo_enabled.setChecked(bool(pomo_cfg.get("enabled", False)))

        self._spn_focus = QSpinBox()
        self._spn_focus.setRange(1, 120)
        self._spn_focus.setSuffix(" 分钟")
        self._spn_focus.setValue(int(pomo_cfg.get("focus_minutes", 25) or 25))

        pomo_form.addRow(self._chk_pomo_enabled)
        pomo_form.addRow("专注时长", self._spn_focus)
        layout.addLayout(pomo_form)

        layout.addStretch(1)
        return widget

    # --- AI tab ---------------------------------------------------------

    def _build_ai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()

        ai_cfg = config.get("ai", {}) or {}

        self._cmb_provider = QComboBox()
        self._cmb_provider.addItems(PROVIDER_NAMES)
        self._cmb_provider.addItem("自定义")
        current_provider = ai_cfg.get("provider") or ""
        if current_provider in PROVIDER_NAMES:
            self._cmb_provider.setCurrentText(current_provider)
        elif current_provider:
            self._cmb_provider.setCurrentText("自定义")

        self._edt_base_url = QLineEdit(ai_cfg.get("base_url", ""))
        self._edt_base_url.setPlaceholderText("https://api.example.com/v1")

        self._edt_api_key = QLineEdit(secrets.get_api_key())
        self._edt_api_key.setEchoMode(QLineEdit.Password)
        self._edt_api_key.setPlaceholderText("sk-...")

        self._edt_model = QLineEdit(ai_cfg.get("model", ""))
        self._edt_model.setPlaceholderText(DEFAULT_MODEL_PLACEHOLDER)

        self._cmb_provider.currentTextChanged.connect(self._on_provider_changed)
        self._apply_model_placeholder(self._cmb_provider.currentText())

        form.addRow("厂商", self._cmb_provider)
        form.addRow("Base URL", self._edt_base_url)
        form.addRow("API Key", self._edt_api_key)
        form.addRow("Model", self._edt_model)

        self._btn_test = QPushButton("测试连接")
        self._btn_test.clicked.connect(self._on_test_connection)

        layout.addLayout(form)
        layout.addWidget(self._btn_test)
        layout.addStretch(1)
        if secrets.is_keyring_available():
            layout.addWidget(QLabel(
                "Key 保存在 Windows 凭据管理器（服务名：XiLeDi），仅本机当前账户可读。"
            ))
        else:
            layout.addWidget(QLabel(
                "Key 仅保存在本机配置文件，不会上传（未启用凭据管理器）。"
            ))
        open_dir_btn = QPushButton("打开配置文件夹")
        open_dir_btn.setAutoDefault(False)
        open_dir_btn.setDefault(False)
        open_dir_btn.clicked.connect(self._on_open_config_dir)
        layout.addWidget(open_dir_btn)

        return widget

    def _on_open_config_dir(self) -> None:
        import os
        try:
            os.startfile(str(user_data_dir()))
        except OSError as exc:
            QMessageBox.warning(self, "打开配置文件夹", f"打开失败：{exc}")

    def _on_provider_changed(self, name: str) -> None:
        self._apply_model_placeholder(name)
        if name in PRESETS:
            preset = PRESETS[name]
            self._edt_base_url.setText(preset["base_url"])
            preset_models = {p["model"] for p in PRESETS.values() if p["model"]}
            current_model = self._edt_model.text().strip()
            if preset["model"] and (not current_model or current_model in preset_models):
                self._edt_model.setText(preset["model"])

    def _apply_model_placeholder(self, provider_name: str) -> None:
        placeholder = MODEL_PLACEHOLDERS.get(provider_name, DEFAULT_MODEL_PLACEHOLDER)
        self._edt_model.setPlaceholderText(placeholder)

    def _on_test_connection(self) -> None:
        cfg = {
            "base_url": self._edt_base_url.text().strip(),
            "api_key": self._edt_api_key.text().strip(),
            "model": self._edt_model.text().strip(),
        }
        if not cfg["api_key"]:
            QMessageBox.warning(self, "测试连接", "请先填 API Key")
            return
        self._btn_test.setEnabled(False)
        self._btn_test.setText("测试中…")
        ok, msg = ai_client.test_connection(cfg)
        self._btn_test.setEnabled(True)
        self._btn_test.setText("测试连接")
        if ok:
            QMessageBox.information(self, "测试连接", msg)
        else:
            QMessageBox.warning(self, "测试连接", msg)

    # --- 提醒 tab -------------------------------------------------------

    def _build_reminders_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._reminders: list[reminders.Reminder] = reminders.load_all()

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["启用", "调度", "提醒内容", "操作"])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._refresh_table()

        add_btn = QPushButton("＋ 添加提醒")
        add_btn.clicked.connect(self._on_add_reminder)

        layout.addWidget(self._table, 1)
        layout.addWidget(add_btn)

        return widget

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._reminders))
        for row, r in enumerate(self._reminders):
            chk = QCheckBox()
            chk.setChecked(r.enabled)
            chk.stateChanged.connect(lambda state, rid=r.id: self._on_toggle_enabled(rid, state))
            chk_holder = QWidget()
            h = QHBoxLayout(chk_holder)
            h.setContentsMargins(8, 0, 0, 0)
            h.addWidget(chk)
            h.addStretch(1)
            self._table.setCellWidget(row, 0, chk_holder)

            self._table.setItem(row, 1, QTableWidgetItem(reminders.describe(r)))
            self._table.setItem(row, 2, QTableWidgetItem(r.title))

            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda _=False, rid=r.id: self._on_edit_reminder(rid))
            del_btn = QPushButton("删除")
            del_btn.clicked.connect(lambda _=False, rid=r.id: self._on_delete_reminder(rid))
            op_holder = QWidget()
            oh = QHBoxLayout(op_holder)
            oh.setContentsMargins(0, 0, 0, 0)
            oh.addWidget(edit_btn)
            oh.addWidget(del_btn)
            self._table.setCellWidget(row, 3, op_holder)

    def _on_toggle_enabled(self, reminder_id: str, state: int) -> None:
        for r in self._reminders:
            if r.id == reminder_id:
                r.enabled = bool(state)
                return

    def _on_add_reminder(self) -> None:
        dialog = ReminderEditor(self)
        if dialog.exec() == QDialog.Accepted:
            new_r = dialog.reminder()
            if new_r is not None:
                self._reminders.append(new_r)
                self._refresh_table()

    def _on_edit_reminder(self, reminder_id: str) -> None:
        target = next((r for r in self._reminders if r.id == reminder_id), None)
        if target is None:
            return
        dialog = ReminderEditor(self, existing=target)
        if dialog.exec() == QDialog.Accepted:
            edited = dialog.reminder()
            if edited is not None:
                for i, r in enumerate(self._reminders):
                    if r.id == reminder_id:
                        self._reminders[i] = edited
                        break
                self._refresh_table()

    def _on_delete_reminder(self, reminder_id: str) -> None:
        confirm = QMessageBox.question(
            self,
            "删除提醒",
            "确认删除这条提醒吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self._reminders = [r for r in self._reminders if r.id != reminder_id]
        self._refresh_table()

    # --- 保存 ----------------------------------------------------------

    def _on_save(self) -> None:
        quiet_start = self._tim_quiet_start.time().toString("HH:mm")
        quiet_end = self._tim_quiet_end.time().toString("HH:mm")

        new_autostart = self._chk_autostart.isChecked()

        ai_payload = {
            "provider": self._cmb_provider.currentText() if self._cmb_provider.currentText() != "自定义" else "",
            "base_url": self._edt_base_url.text().strip(),
            "model": self._edt_model.text().strip(),
        }
        secrets.set_api_key(self._edt_api_key.text().strip())

        idle_payload = {
            "enabled": self._chk_idle_enabled.isChecked(),
            "interval_minutes": int(self._spn_idle_interval.value()),
            "quiet_enabled": self._chk_quiet_enabled.isChecked(),
            "quiet_start": quiet_start,
            "quiet_end": quiet_end,
        }

        pomodoro_payload = {
            "enabled": self._chk_pomo_enabled.isChecked(),
            "focus_minutes": int(self._spn_focus.value()),
        }

        config.update({
            "always_on_top": self._chk_top.isChecked(),
            "sound_enabled": self._chk_sound.isChecked(),
            "autostart": new_autostart,
            "ai": ai_payload,
            "idle_chat": idle_payload,
            "pomodoro": pomodoro_payload,
        })
        reminders.save_all(self._reminders)
        autostart.apply(new_autostart)
        self.settings_applied.emit()
        self.accept()


class ReminderEditor(QDialog):
    """添加/编辑单条提醒的小弹窗。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        existing: reminders.Reminder | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑提醒" if existing else "新建提醒")
        self.setMinimumSize(320, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_DIALOG_QSS_TEMPLATE.format(family=fonts.family_css(), check_icon=_ensure_check_icon_path()))
        self.setFont(fonts.pixel_font(11))

        self._reminder_id = existing.id if existing else reminders.new_id()
        self._enabled = existing.enabled if existing else True

        self._edt_title = QLineEdit(existing.title if existing else "")
        self._edt_title.setPlaceholderText("如：喝水时间到啦！")

        self._cmb_type = QComboBox()
        self._cmb_type.addItem("每天", reminders.TYPE_DAILY)
        self._cmb_type.addItem("每隔 N 分钟", reminders.TYPE_INTERVAL)
        if existing and existing.type == reminders.TYPE_INTERVAL:
            self._cmb_type.setCurrentIndex(1)

        self._edt_schedule = QLineEdit(existing.schedule if existing else "10:30")
        self._update_schedule_hint()
        self._cmb_type.currentIndexChanged.connect(self._update_schedule_hint)

        form = QFormLayout()
        form.addRow("提醒内容", self._edt_title)
        form.addRow("类型", self._cmb_type)
        form.addRow("时间", self._edt_schedule)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._result: reminders.Reminder | None = None

    def _current_type(self) -> str:
        return self._cmb_type.currentData()

    def _update_schedule_hint(self) -> None:
        if self._current_type() == reminders.TYPE_DAILY:
            self._edt_schedule.setPlaceholderText("HH:MM，例如 10:30")
        else:
            self._edt_schedule.setPlaceholderText("分钟数，例如 60")

    def _on_accept(self) -> None:
        title = self._edt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "提醒内容不能为空")
            return
        sched = self._edt_schedule.text().strip()
        rtype = self._current_type()
        ok, msg = reminders.validate_schedule(rtype, sched)
        if not ok:
            QMessageBox.warning(self, "时间格式", msg)
            return
        self._result = reminders.Reminder(
            id=self._reminder_id,
            title=title,
            type=rtype,
            schedule=sched,
            enabled=self._enabled,
        )
        self.accept()

    def reminder(self) -> reminders.Reminder | None:
        return self._result
