"""系统托盘：缺 ico 时用占位图，菜单含显示/隐藏 / 设置 / 退出。"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from src.core.paths import assets_dir
from src.pet.placeholder_art import make_placeholder_sheltie


class PetTrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_toggle_visibility: Callable[[], None],
        on_settings: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.setIcon(self._build_icon())
        self.setToolTip("小喜桌宠")

        menu = QMenu()

        toggle_action = QAction("显示 / 隐藏", self)
        toggle_action.triggered.connect(on_toggle_visibility)
        menu.addAction(toggle_action)

        settings_action = QAction("设置…", self)
        settings_action.triggered.connect(on_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("退出小喜", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self._on_toggle = on_toggle_visibility

    def _build_icon(self) -> QIcon:
        ico_path = assets_dir() / "icons" / "tray.ico"
        if ico_path.exists():
            return QIcon(str(ico_path))
        return QIcon(make_placeholder_sheltie(64, "idle"))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._on_toggle()
