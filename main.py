"""小喜桌宠 入口"""
from __future__ import annotations

import sys

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication

from src.core import autostart, config, fonts
from src.core.scheduler import ReminderScheduler
from src.pet.pet_window import PetWindow
from src.ui.tray import PetTrayIcon


SINGLE_INSTANCE_KEY = "XiLeDi_SingleInstance_v1"


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    shared_memory = QSharedMemory(SINGLE_INSTANCE_KEY)
    shared_memory.attach()
    shared_memory.detach()
    if not shared_memory.create(1):
        return 0

    config.load()
    autostart.apply(bool(config.get("autostart", False)))
    fonts.init()

    window = PetWindow()
    window.show()

    scheduler = ReminderScheduler()
    scheduler.triggered.connect(window.show_reminder)
    scheduler.start()

    def open_settings_from_tray() -> None:
        window._open_settings(initial_tab=0)

    tray = PetTrayIcon(
        on_toggle_visibility=window.toggle_visibility,
        on_settings=open_settings_from_tray,
    )
    tray.show()

    exit_code = app.exec()
    scheduler.stop()
    shared_memory.detach()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
