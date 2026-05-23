"""桌宠主窗口：完整 M3 交互（右键、双击、抚摸、喂食、聊天、设置）+ 边缘吸附半隐藏。"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from src.core import audio, config
from src.pet.animator import Animator
from src.pet.behavior import Behavior
from src.pet.feeding import FeedingController
from src.pet.state_machine import StateMachine
from src.ui.bubble import ReminderBubble
from src.ui.chat_panel import ChatPanel
from src.ui.context_menu import build_pet_menu
from src.ui.heart_particles import HeartParticles
from src.ui.petting_hand import PettingHand
from src.ui.settings_dialog import SettingsDialog


PET_SIZE = 192

_CLICK_DRAG_THRESHOLD_PX = 3
_HEAD_RATIO = 0.4
_PET_DURATION_MS = 1500
_WAG_DURATION_MS = 500
_EDGE_SNAP_THRESHOLD_PX = 64
_EDGE_VISIBLE_PX = 54
_SLIDE_DURATION_MS = 320


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedSize(PET_SIZE, PET_SIZE)

        self._label = QLabel(self)
        self._label.setGeometry(0, 0, PET_SIZE, PET_SIZE)
        self._label.setAttribute(Qt.WA_TranslucentBackground, True)

        self._state_machine = StateMachine(initial="idle")
        self._animator = Animator(self._state_machine, pet_size=PET_SIZE)
        self._behavior = Behavior(self._state_machine, self._animator, pet_size=PET_SIZE)

        self._animator.frame_changed.connect(self._label.setPixmap)
        self._behavior.position_changed.connect(self._on_behavior_move)

        self._press_pos_global: QPoint | None = None
        self._press_pos_local: QPoint | None = None
        self._drag_offset: QPoint | None = None
        self._is_dragging = False
        self._is_petting = False
        self._pending_pet = False

        self._chat_panel: ChatPanel | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._feeding: FeedingController | None = None
        self._hearts: list[HeartParticles] = []
        self._petting_hands: list[PettingHand] = []
        self._bubbles: list[ReminderBubble] = []

        self._edge_hidden: str | None = None
        self._slide_anim: QPropertyAnimation | None = None

        self.apply_config()
        self._move_to_screen_corner()
        self._behavior.set_initial_position(self.x(), self.y())
        self._behavior.start()

    def apply_config(self) -> None:
        stay_on_top = bool(config.get("always_on_top", True))
        flags = self.windowFlags()
        if stay_on_top:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        if flags != self.windowFlags():
            was_visible = self.isVisible()
            self.setWindowFlags(flags)
            if was_visible:
                self.show()
        if self._chat_panel is not None and self._chat_panel.isVisible():
            self._chat_panel.refresh_after_settings_change()

    def _move_to_screen_corner(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.right() - PET_SIZE - 40
        y = geo.bottom() - PET_SIZE - 40
        self.move(x, y)

    def _on_behavior_move(self, x: int, y: int) -> None:
        if self._is_dragging or self._edge_hidden is not None:
            return
        self.move(x, y)

    # --- Mouse events ----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._cancel_feeding()
        self._press_pos_local = event.position().toPoint()
        self._press_pos_global = event.globalPosition().toPoint()
        self._drag_offset = self._press_pos_global - self.frameGeometry().topLeft()
        self._is_dragging = False
        self._is_petting = False
        if self._edge_hidden is not None:
            self._pending_pet = False
        else:
            self._pending_pet = self._press_pos_local.y() < int(PET_SIZE * _HEAD_RATIO)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._press_pos_global is None or self._drag_offset is None:
            return
        cur = event.globalPosition().toPoint()
        moved = (cur - self._press_pos_global).manhattanLength()
        if not self._is_dragging and not self._is_petting and moved >= _CLICK_DRAG_THRESHOLD_PX:
            if self._pending_pet and self._edge_hidden is None:
                self._is_petting = True
                self._trigger_pet()
            else:
                self._is_dragging = True
                self._behavior.pause()
                if self._slide_anim is not None:
                    self._slide_anim.stop()
                    self._slide_anim = None
                self._state_machine.transition("idle", force=True)
        if self._is_dragging:
            new_pos = cur - self._drag_offset
            self.move(new_pos)
            self._behavior.sync_position(new_pos.x(), new_pos.y())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        was_dragging = self._is_dragging
        was_petting = self._is_petting
        pending_pet = self._pending_pet
        was_edge_hidden = self._edge_hidden is not None
        self._press_pos_global = None
        self._press_pos_local = None
        self._drag_offset = None
        self._is_dragging = False
        self._is_petting = False
        self._pending_pet = False

        if was_dragging:
            self._behavior.sync_position(self.x(), self.y())
            if self._should_snap_to_edge():
                self._snap_to_edge()
            else:
                if was_edge_hidden:
                    self._unhide_from_edge()
                self._state_machine.transition("dizzy", force=True)
        elif was_edge_hidden:
            pass
        elif was_petting:
            pass
        elif pending_pet:
            self._trigger_pet()
        else:
            self._wag_tail()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._edge_hidden is None:
            self._open_chat()
            event.accept()

    def contextMenuEvent(self, event) -> None:
        self._behavior.pause()
        self._state_machine.transition("idle", force=True)
        menu = build_pet_menu(
            self,
            on_pet=self._trigger_pet,
            on_feed=self._trigger_feed,
            on_sleep=self._trigger_sleep,
            on_chat=self._open_chat,
            on_reminders=lambda: self._open_settings(initial_tab=2),
            on_settings=lambda: self._open_settings(initial_tab=0),
            on_quit=QApplication.quit,
        )
        menu.aboutToHide.connect(lambda: QTimer.singleShot(0, self._behavior.resume))
        menu.exec(event.globalPos())

    # --- Interaction actions --------------------------------------------

    def _trigger_pet(self) -> None:
        self._cancel_feeding()
        self._state_machine.transition("happy", force=True)
        head_x = self.x() + PET_SIZE // 2
        head_y = self.y() + int(PET_SIZE * 0.22)
        self._hearts.append(HeartParticles(head_x, head_y))
        self._petting_hands.append(PettingHand(head_x, head_y))
        QTimer.singleShot(_PET_DURATION_MS, self._return_to_idle_if_happy)

    def _wag_tail(self) -> None:
        self._state_machine.transition("happy", force=True)
        audio.play("bark")
        QTimer.singleShot(_WAG_DURATION_MS, self._return_to_idle_if_happy)

    def _return_to_idle_if_happy(self) -> None:
        if self._state_machine.state() == "happy":
            self._state_machine.transition("idle", force=True)

    def _trigger_sleep(self) -> None:
        self._cancel_feeding()
        self._state_machine.transition("sleep", force=True)

    def _trigger_feed(self) -> None:
        self._cancel_feeding()
        self._behavior.resume()
        self._feeding = FeedingController(
            pet_size=PET_SIZE,
            behavior=self._behavior,
            state_machine=self._state_machine,
            on_arrive_sound=lambda: audio.play("chew"),
        )
        self._feeding.destroyed.connect(self._on_feeding_done)
        self._feeding.start(self.x(), self.y())

    def _on_feeding_done(self, *_args) -> None:
        self._feeding = None

    def _cancel_feeding(self) -> None:
        if self._feeding is not None:
            self._feeding.cancel()
            self._feeding = None

    def _open_chat(self) -> None:
        self._cancel_feeding()
        if self._chat_panel is None:
            self._chat_panel = ChatPanel(self)
        self._chat_panel.show()
        self._chat_panel.raise_()
        self._chat_panel.activateWindow()

    def _open_settings(self, initial_tab: int = 0) -> None:
        self._cancel_feeding()
        if self._settings_dialog is not None:
            self._settings_dialog.close()
        self._settings_dialog = SettingsDialog(self, initial_tab=initial_tab)
        self._settings_dialog.settings_applied.connect(self.apply_config)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    # --- Edge snap (Bug 7) ----------------------------------------------

    def _should_snap_to_edge(self) -> bool:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return False
        geo = screen.availableGeometry()
        if self.x() < geo.left() + _EDGE_SNAP_THRESHOLD_PX:
            return True
        if self.x() + PET_SIZE > geo.right() - _EDGE_SNAP_THRESHOLD_PX:
            return True
        return False

    def _snap_to_edge(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        if self.x() < geo.left() + _EDGE_SNAP_THRESHOLD_PX:
            self._edge_hidden = "left"
            target_x = geo.left() - PET_SIZE + _EDGE_VISIBLE_PX
            self._animator.set_direction(1)
        else:
            self._edge_hidden = "right"
            target_x = geo.right() - _EDGE_VISIBLE_PX
            self._animator.set_direction(-1)
        target_y = self.y()
        target_y = max(geo.top(), min(geo.bottom() - PET_SIZE, target_y))

        self._behavior.pause()
        self._state_machine.transition("idle", force=True)

        if self._slide_anim is not None:
            self._slide_anim.stop()
        self._slide_anim = QPropertyAnimation(self, b"pos", self)
        self._slide_anim.setDuration(_SLIDE_DURATION_MS)
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(target_x, target_y))
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_anim.finished.connect(self._on_snap_finished)
        self._slide_anim.start()

    def _on_snap_finished(self) -> None:
        self._behavior.sync_position(self.x(), self.y())

    def _unhide_from_edge(self) -> None:
        self._edge_hidden = None
        self._behavior.resume()

    # --- Reminder bubble (M4) -------------------------------------------

    def show_reminder(self, title: str) -> None:
        self._bubbles.append(ReminderBubble(title, self.x(), self.y(), pet_size=PET_SIZE))
