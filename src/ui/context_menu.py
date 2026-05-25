"""桌宠右键菜单：构造 QMenu，回调通过参数注入。"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from src.core import fonts


def build_pet_menu(
    parent: QWidget,
    *,
    on_pet: Callable[[], None],
    on_feed: Callable[[], None],
    on_sleep: Callable[[], None],
    on_chat: Callable[[], None],
    on_reminders: Callable[[], None],
    on_settings: Callable[[], None],
    on_quit: Callable[[], None],
    on_pomodoro_toggle: Callable[[], None] | None = None,
    pomodoro_running: bool = False,
) -> QMenu:
    menu = QMenu(parent)
    menu.setFont(fonts.pixel_font(11))
    menu.setStyleSheet(_MENU_QSS_TEMPLATE.format(family=fonts.family_css()))

    def add(text: str, callback: Callable[[], None]) -> None:
        action = QAction(text, parent)
        action.triggered.connect(callback)
        menu.addAction(action)

    add("抚摸", on_pet)
    add("喂食", on_feed)
    add("睡觉", on_sleep)
    menu.addSeparator()
    add("聊天", on_chat)
    if on_pomodoro_toggle is not None:
        add("⏹ 结束学习陪伴" if pomodoro_running else "🍅 启动学习陪伴", on_pomodoro_toggle)
    add("提醒…", on_reminders)
    add("设置…", on_settings)
    menu.addSeparator()
    add("退出小喜", on_quit)

    return menu


_MENU_QSS_TEMPLATE = """
QMenu {{
    background: #FFF8EC;
    border: 2px solid #5C4221;
    padding: 4px;
    font-family: {family};
}}
QMenu::item {{
    padding: 6px 22px 6px 22px;
    color: #3B2A1A;
}}
QMenu::item:selected {{
    background: #F4C77B;
    color: #3B2A1A;
}}
QMenu::separator {{
    height: 2px;
    background: #5C4221;
    margin: 4px 4px;
}}
"""
