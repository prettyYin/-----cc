"""桌宠主窗口：完整 M3 交互（右键、双击、抚摸、喂食、聊天、设置）+ 边缘吸附半隐藏。"""
from __future__ import annotations

import random

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from src.core import audio, config
from src.core.idle_chat import IdleChatter
from src.core.pomodoro import (
    PomodoroController,
    STATE_FOCUS,
    STATE_IDLE as POMO_IDLE,
)
from src.pet.animator import Animator
from src.pet.behavior import Behavior
from src.pet.feeding import FeedingController
from src.pet.state_machine import StateMachine
from src.ui.bubble import ReminderBubble
from src.ui.chat_panel import ChatPanel
from src.ui.context_menu import build_pet_menu
from src.ui.heart_particles import HeartParticles
from src.ui.petting_hand import PettingHand
from src.ui.progress_ring import ProgressRing
from src.ui.settings_dialog import SettingsDialog


PET_SIZE = 128

_CLICK_DRAG_THRESHOLD_PX = 3
_HEAD_RATIO = 0.4
_PET_DURATION_MS = 1500
_WAG_DURATION_MS = 500
_DRAG_RELEASE_FALL_MS = 350
_EDGE_SNAP_THRESHOLD_PX = 64
_EDGE_VISIBLE_PX = 90
_SLIDE_DURATION_MS = 320

_OVERSIZED_STATES = {"dizzy"}
_OVERSIZED_PET_SIZE = int(PET_SIZE * 1.4)  # 179
_OVERSIZED_OFFSET = (_OVERSIZED_PET_SIZE - PET_SIZE) // 2  # 25

_PEEK_WAVE_INTERVAL_MIN_MS = 18_000
_PEEK_WAVE_INTERVAL_MAX_MS = 35_000
_PEEK_WAVE_DURATION_MS = 1500

_FOCUS_ENCOURAGE_INTERVAL_MS = 5 * 60 * 1000
_FOCUS_ENCOURAGE_MIN_REMAIN_S = 360
_FOCUS_ENCOURAGEMENTS = (
    "小主继续加油哦~ 小喜在陪你 🐾",
    "再坚持一会，你超棒的 🌟",
    "小喜悄悄趴在这儿陪你学习~",
    "学习中的小主最帅啦！",
    "保持节奏~ 你做得超好",
    "认真的样子超可爱 🐾",
)


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

        self._chatter: IdleChatter | None = None
        self._pomodoro: PomodoroController | None = None
        self._progress_ring: ProgressRing | None = None
        self._pomo_total: int = 0
        self._focus_lock: bool = False
        self._focus_warned: bool = False
        self._focus_encourage_timer: QTimer | None = None
        self._peek_wave_timer: QTimer | None = None

        self._state_machine.state_changed.connect(self._on_state_changed_for_size)

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
        self._sync_bubble_positions()

    def _sync_bubble_positions(self) -> None:
        for b in list(self._bubbles):
            try:
                b.update_position(self.x(), self.y(), PET_SIZE)
            except RuntimeError:
                pass

    def _show_bubble(self, text: str) -> None:
        for b in list(self._bubbles):
            try:
                b.dismiss()
            except RuntimeError:
                pass
        bubble = ReminderBubble(text, self.x(), self.y(), pet_size=PET_SIZE)
        bubble.finished.connect(lambda b=bubble: self._bubbles.remove(b) if b in self._bubbles else None)
        self._bubbles.append(bubble)

    def _dismiss_all_bubbles(self) -> None:
        for b in list(self._bubbles):
            try:
                b.dismiss()
            except RuntimeError:
                pass

    def _cancel_overlays(self) -> None:
        for hand in list(self._petting_hands):
            try:
                hand.cancel()
            except RuntimeError:
                pass
        self._petting_hands.clear()
        for heart in list(self._hearts):
            try:
                heart.cancel()
            except RuntimeError:
                pass
        self._hearts.clear()

    # --- Mouse events ----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._notify_interaction()
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
                self._cancel_overlays()
                self._behavior.pause()
                if self._slide_anim is not None:
                    self._slide_anim.stop()
                    self._slide_anim = None
                self._state_machine.transition("dizzy", force=True)
        if self._is_dragging:
            new_pos = cur - self._drag_offset
            self.move(new_pos)
            self._behavior.sync_position(new_pos.x(), new_pos.y())
            self._sync_bubble_positions()
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
                self._state_machine.transition("fall", force=True)
                QTimer.singleShot(_DRAG_RELEASE_FALL_MS, self._return_to_idle_if_fall_or_dizzy)
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
            self._notify_interaction()
            self._open_chat()
            event.accept()

    def contextMenuEvent(self, event) -> None:
        self._notify_interaction()
        if self._edge_hidden is None:
            self._behavior.pause()
            self._cancel_feeding()
            self._state_machine.transition("idle", force=True)
        pomo_cfg = config.get("pomodoro", {}) or {}
        pomo_enabled = bool(pomo_cfg.get("enabled", False))
        pomo_running = self._pomodoro is not None and self._pomodoro.is_running()
        toggle_cb = self._toggle_pomodoro if (pomo_enabled and self._pomodoro is not None) else None
        menu = build_pet_menu(
            self,
            on_pet=self._trigger_pet,
            on_feed_bone=self._trigger_feed_bone,
            on_feed_dogfood=self._trigger_feed_dogfood,
            on_sleep=self._trigger_sleep,
            on_chat=self._open_chat,
            on_reminders=lambda: self._open_settings(initial_tab=3),
            on_settings=lambda: self._open_settings(initial_tab=0),
            on_quit=QApplication.quit,
            on_pomodoro_toggle=toggle_cb,
            pomodoro_running=pomo_running,
        )
        menu.aboutToHide.connect(lambda: QTimer.singleShot(0, self._resume_behavior_if_not_focused))
        menu.exec(event.globalPos())

    def _resume_behavior_if_not_focused(self) -> None:
        if self._edge_hidden is not None:
            return
        if self._focus_lock:
            self._state_machine.transition("sleep", force=True)
            return
        if self._state_machine.state() in ("eat", "hold_bone", "happy"):
            return
        self._behavior.resume()

    def _on_state_changed_for_size(self, old: str, new: str) -> None:
        """dizzy 帧用 1.4× 大画布显示（避免上下被裁），进出时同步缩放窗口 + label。"""
        new_oversized = new in _OVERSIZED_STATES
        old_oversized = old in _OVERSIZED_STATES
        if new_oversized == old_oversized:
            return
        if new_oversized:
            delta = -_OVERSIZED_OFFSET
            target_size = _OVERSIZED_PET_SIZE
        else:
            delta = _OVERSIZED_OFFSET
            target_size = PET_SIZE
        new_x = self.x() + delta
        new_y = self.y() + delta
        self.setFixedSize(target_size, target_size)
        self._label.setGeometry(0, 0, target_size, target_size)
        self.move(new_x, new_y)
        if self._drag_offset is not None:
            self._drag_offset = self._drag_offset - QPoint(delta, delta)
        self._behavior.sync_position(new_x, new_y)
        if self._progress_ring is not None:
            self._progress_ring.setGeometry(target_size - 56, 8, 48, 48)

    # --- Interaction actions --------------------------------------------

    def _trigger_pet(self) -> None:
        self._notify_interaction()
        if self._edge_hidden is not None:
            self._show_bubble("我躲在墙边啦~ 把我拖出来再摸嘛 🐾")
            return
        self._cancel_feeding()
        self._state_machine.transition("happy", force=True)
        head_x = self.x() + PET_SIZE // 2
        head_y = self.y() + int(PET_SIZE * 0.22)
        heart = HeartParticles(head_x, head_y)
        heart.finished.connect(lambda h=heart: self._hearts.remove(h) if h in self._hearts else None)
        self._hearts.append(heart)
        hand = PettingHand(head_x, head_y)
        hand.finished.connect(lambda h=hand: self._petting_hands.remove(h) if h in self._petting_hands else None)
        self._petting_hands.append(hand)
        QTimer.singleShot(_PET_DURATION_MS, self._return_to_idle_if_happy)

    def _wag_tail(self) -> None:
        self._state_machine.transition("happy", force=True)
        audio.play("bark")
        QTimer.singleShot(_WAG_DURATION_MS, self._return_to_idle_if_happy)

    def _return_to_idle_if_happy(self) -> None:
        if self._state_machine.state() == "happy":
            if self._focus_lock:
                self._state_machine.transition("sleep", force=True)
            else:
                self._state_machine.transition("idle", force=True)

    def _return_to_idle_if_dizzy(self) -> None:
        if self._state_machine.state() == "dizzy" and not self._is_dragging:
            if self._focus_lock:
                self._state_machine.transition("sleep", force=True)
            else:
                self._state_machine.transition("idle", force=True)
                if self._behavior.is_paused():
                    self._behavior.resume()

    def _return_to_idle_if_fall_or_dizzy(self) -> None:
        if self._state_machine.state() in ("fall", "dizzy") and not self._is_dragging:
            if self._focus_lock:
                self._state_machine.transition("sleep", force=True)
            else:
                self._state_machine.transition("idle", force=True)
                if self._behavior.is_paused():
                    self._behavior.resume()

    def _trigger_sleep(self) -> None:
        self._notify_interaction()
        if self._edge_hidden is not None:
            self._show_bubble("墙边不好睡觉~ 把我拽出来嘛 😴")
            return
        self._cancel_feeding()
        self._state_machine.transition("sleep", force=True)

    def _trigger_feed_bone(self) -> None:
        self._notify_interaction()
        if self._edge_hidden is not None:
            self._show_bubble("墙边吃不下骨头啦~ 先把我拽出来 🦴")
            return
        if self._focus_lock:
            self._show_bubble("学习中喂不下啦~ 等休息再吃 🦴")
            return
        self._start_feeding("bone")

    def _trigger_feed_dogfood(self) -> None:
        self._notify_interaction()
        if self._edge_hidden is not None:
            self._show_bubble("墙边放不下狗粮碗啦~ 先把我拽出来 🥣")
            return
        if self._focus_lock:
            self._show_bubble("学习中喂不下啦~ 等休息再吃 🥣")
            return
        self._start_feeding("dogfood")

    def _start_feeding(self, food_type: str) -> None:
        self._cancel_feeding()
        self._behavior.resume()
        controller = FeedingController(
            pet_size=PET_SIZE,
            behavior=self._behavior,
            state_machine=self._state_machine,
            animator=self._animator,
            on_arrive_sound=lambda: audio.play("chew"),
        )
        controller.destroyed.connect(
            lambda *_, ref=controller: self._on_feeding_destroyed(ref)
        )
        controller.eating_finished.connect(self._on_feeding_finished)
        self._feeding = controller
        controller.start(self.x(), self.y(), food_type=food_type)

    def _on_feeding_destroyed(self, ref) -> None:
        if self._feeding is ref:
            self._feeding = None

    def _on_feeding_finished(self, food_type: str) -> None:
        if not food_type:
            return
        if self._chatter is not None:
            self._chatter.say_event(f"after_feed_{food_type}")

    def _cancel_feeding(self) -> None:
        if self._feeding is not None:
            self._feeding.cancel()
            self._feeding = None

    def _open_chat(self) -> None:
        self._notify_interaction()
        if self._edge_hidden is not None:
            self._show_bubble("我躲在墙边呢~ 把我拽出来再聊嘛 💬")
            return
        self._cancel_feeding()
        if self._chat_panel is None:
            self._chat_panel = ChatPanel(self)
        self._chat_panel.show()
        self._chat_panel.raise_()
        self._chat_panel.activateWindow()

    def _open_settings(self, initial_tab: int = 0) -> None:
        self._cancel_feeding()
        self._dismiss_all_bubbles()
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

    def _logical_pos(self) -> tuple[int, int]:
        """dizzy 时窗口被向左上偏移 _OVERSIZED_OFFSET 像素，还原成逻辑（PET_SIZE 视角）位置。"""
        if self._state_machine.state() in _OVERSIZED_STATES:
            return self.x() + _OVERSIZED_OFFSET, self.y() + _OVERSIZED_OFFSET
        return self.x(), self.y()

    def _should_snap_to_edge(self) -> bool:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return False
        geo = screen.availableGeometry()
        lx, _ly = self._logical_pos()
        if lx < geo.left() + _EDGE_SNAP_THRESHOLD_PX:
            return True
        if lx + PET_SIZE > geo.right() - _EDGE_SNAP_THRESHOLD_PX:
            return True
        return False

    def _snap_to_edge(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        lx, ly = self._logical_pos()
        if lx < geo.left() + _EDGE_SNAP_THRESHOLD_PX:
            self._edge_hidden = "left"
            target_x = geo.left() - PET_SIZE + _EDGE_VISIBLE_PX
            self._animator.set_direction(-1)
        else:
            self._edge_hidden = "right"
            target_x = geo.right() - _EDGE_VISIBLE_PX
            self._animator.set_direction(1)
        target_y = max(geo.top(), min(geo.bottom() - PET_SIZE, ly))

        self._behavior.pause()
        self._state_machine.transition("peek", force=True)

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
        self._start_peek_wave_loop()

    def _unhide_from_edge(self) -> None:
        self._stop_peek_wave_loop()
        self._edge_hidden = None
        if self._state_machine.state() == "peek":
            self._state_machine.transition("idle", force=True)
        self._behavior.resume()

    # --- Peek wave (M4.9 四轮) ------------------------------------------

    def _start_peek_wave_loop(self) -> None:
        if self._peek_wave_timer is None:
            self._peek_wave_timer = QTimer(self)
            self._peek_wave_timer.setSingleShot(True)
            self._peek_wave_timer.timeout.connect(self._fire_peek_wave)
        self._schedule_next_peek_wave()

    def _schedule_next_peek_wave(self) -> None:
        if self._peek_wave_timer is None:
            return
        delay = random.randint(_PEEK_WAVE_INTERVAL_MIN_MS, _PEEK_WAVE_INTERVAL_MAX_MS)
        self._peek_wave_timer.start(delay)

    def _fire_peek_wave(self) -> None:
        if self._edge_hidden is None:
            return
        self._animator.play_peek_wave(_PEEK_WAVE_DURATION_MS)
        if self._chatter is not None:
            phrase = self._chatter.pick_phrase("peek_wave")
            if phrase:
                self._show_bubble(phrase)
        self._schedule_next_peek_wave()

    def _stop_peek_wave_loop(self) -> None:
        if self._peek_wave_timer is not None:
            self._peek_wave_timer.stop()

    # --- Reminder bubble (M4) -------------------------------------------

    def show_reminder(self, title: str) -> None:
        self._show_bubble(title)

    # --- Companion (M4.6) -----------------------------------------------

    def set_companion(
        self,
        chatter: IdleChatter,
        pomodoro: PomodoroController,
    ) -> None:
        self._chatter = chatter
        self._pomodoro = pomodoro
        chatter.set_visible(self.isVisible())
        chatter.phrase_ready.connect(self._on_idle_phrase)
        pomodoro.state_changed.connect(self._on_pomodoro_state_changed)
        if self._progress_ring is None:
            self._progress_ring = ProgressRing(self)
            self._progress_ring.setGeometry(PET_SIZE - 56, 8, 48, 48)
            self._progress_ring.hide()

    def _notify_interaction(self) -> None:
        if self._chatter is not None:
            self._chatter.notify_interaction()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._chatter is not None:
            self._chatter.set_visible(True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if self._chatter is not None:
            self._chatter.set_visible(False)

    def _on_idle_phrase(self, text: str) -> None:
        if not self.isVisible() or self._edge_hidden is not None:
            return
        self._show_bubble(text)

    def _toggle_pomodoro(self) -> None:
        if self._pomodoro is None:
            return
        if self._pomodoro.is_running():
            self._pomodoro.stop()
        else:
            self._pomodoro.start()

    def _focus_total_seconds(self) -> int:
        cfg = config.get("pomodoro", {}) or {}
        return max(1, int(cfg.get("focus_minutes", 25) or 25)) * 60

    def _start_focus_encourage_timer(self) -> None:
        if self._focus_encourage_timer is None:
            self._focus_encourage_timer = QTimer(self)
            self._focus_encourage_timer.timeout.connect(self._on_focus_encourage_tick)
        self._focus_encourage_timer.start(_FOCUS_ENCOURAGE_INTERVAL_MS)

    def _stop_focus_encourage_timer(self) -> None:
        if self._focus_encourage_timer is not None:
            self._focus_encourage_timer.stop()

    def _on_focus_encourage_tick(self) -> None:
        if not self._focus_lock or self._pomodoro is None:
            return
        if self._pomodoro.remaining_seconds() <= _FOCUS_ENCOURAGE_MIN_REMAIN_S:
            return
        self._show_bubble(random.choice(_FOCUS_ENCOURAGEMENTS))

    def _on_pomodoro_state_changed(self, state: str, remaining_s: int) -> None:
        if self._progress_ring is None:
            return
        if state == POMO_IDLE:
            self._progress_ring.hide()
            was_locked = self._focus_lock
            self._focus_lock = False
            self._focus_warned = False
            self._pomo_total = 0
            self._stop_focus_encourage_timer()
            if self._chatter is not None:
                self._chatter.resume()
            if was_locked:
                self._state_machine.transition("happy", force=True)
                self._show_bubble("学习结束啦~ 小主辛苦啦 🌟")
                if self._behavior.is_paused():
                    self._behavior.resume()
                QTimer.singleShot(_PET_DURATION_MS, self._return_to_idle_if_happy)
            elif self._behavior.is_paused():
                self._behavior.resume()
            return

        # FOCUS state
        if self._pomo_total == 0 or remaining_s > self._pomo_total:
            self._pomo_total = max(remaining_s, self._focus_total_seconds())

        self._progress_ring.set_progress(state, remaining_s, self._pomo_total)
        self._progress_ring.show()
        self._progress_ring.raise_()

        if remaining_s == self._pomo_total:
            # 状态首次进入：锁住小喜进入睡眠
            self._focus_lock = True
            self._focus_warned = False
            if self._chatter is not None:
                self._chatter.pause()
            self._cancel_feeding()
            self._cancel_overlays()
            self._behavior.pause()
            self._state_machine.transition("sleep", force=True)
            self._start_focus_encourage_timer()

        if not self._focus_warned and remaining_s <= 300 and remaining_s > 0:
            self._focus_warned = True
            self._show_bubble("小主，学习时间不足5分钟啦，不要偷偷看手机哦！")
