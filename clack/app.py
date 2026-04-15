import sys
import threading
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor

from clack.config import load_config, save_config, get_sounds_dir
from clack.audio import AudioEngine
from clack.keyboard import KeyboardListener


class Signals(QObject):
    key_pressed = pyqtSignal(str, bool)
    toggle_requested = pyqtSignal()
    mouse_clicked = pyqtSignal(str)


class ClackApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = load_config()
        self.audio = AudioEngine(self.config)
        self.audio.set_volume(self.config["volume"] / 100)

        self.signals = Signals()
        self.listener = None
        self._last_hotkey_time = 0.0

        self._setup_tray()
        self.signals.toggle_requested.connect(self.toggle)
        self.signals.mouse_clicked.connect(self._play_mouse)
        self._start_listening()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon()
        self._update_icon()
        self.tray.activated.connect(self._on_tray_activated)

        self.menu = QMenu()

        self.toggle_action = QAction(
            "Enable" if not self.config["enabled"] else "Disable"
        )
        self.toggle_action.triggered.connect(self.toggle)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        volume_label = QAction("Volume")
        volume_label.setEnabled(False)
        self.menu.addAction(volume_label)
        self.volume_actions = {}
        for v in [30, 50, 70, 100]:
            action = QAction(
                f"{v}%", checkable=True, checked=v == self.config["volume"]
            )
            action.triggered.connect(lambda checked, vol=v: self._set_volume(vol))
            self.volume_actions[v] = action
            self.menu.addAction(action)

        self.menu.addSeparator()
        profile_label = QAction("Sound Profile")
        profile_label.setEnabled(False)
        self.menu.addAction(profile_label)
        profiles = ["clicky", "tactile", "linear"]
        self.profile_actions = {}
        for profile in profiles:
            action = QAction(
                profile.capitalize(),
                checkable=True,
                checked=profile == self.config["sound_profile"],
            )
            action.triggered.connect(lambda checked, p=profile: self._set_profile(p))
            self.profile_actions[profile] = action
            self.menu.addAction(action)

        self.menu.addSeparator()
        self.mouse_action = QAction(
            "Mouse clicks",
            checkable=True,
            checked=self.config.get("play_mouse", True),
        )
        self.mouse_action.triggered.connect(self._set_mouse_clicks)
        self.menu.addAction(self.mouse_action)

        self.menu.addSeparator()

        settings_action = QAction("Settings")
        settings_action.triggered.connect(self._show_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

    def _update_icon(self):
        enabled = self.config["enabled"]
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if enabled:
            color = QColor("#00ff00")
            painter.setBrush(color)
            painter.setPen(QColor("#00aa00"))
        else:
            color = QColor("#888888")
            painter.setBrush(color)
            painter.setPen(QColor("#666666"))

        for i in range(4):
            x = 8 + (i % 2) * 28
            y = 10 + (i // 2) * 26
            painter.drawRoundedRect(x, y, 18, 20, 3, 3)

        painter.end()
        icon = QIcon(pixmap)
        self.tray.setIcon(icon)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle()

    def toggle(self):
        self.config["enabled"] = not self.config["enabled"]
        save_config(self.config)

        self._update_icon()
        self.toggle_action.setText("Disable" if self.config["enabled"] else "Enable")

    def _start_listening(self):
        if self.listener:
            return

        pressed_mouse = set()

        def on_key(key_name, is_modifier, event_value=1):
            mouse_button = self._mouse_button_from_key(key_name)
            if mouse_button:
                if event_value == 0:
                    pressed_mouse.discard(mouse_button)
                    return
                if event_value in (1, 2):
                    if mouse_button in pressed_mouse:
                        return
                    pressed_mouse.add(mouse_button)
                    if self.config["enabled"] and self.config.get("play_mouse", True):
                        self._handle_mouse_click(mouse_button)
                return

            if event_value != 1:
                return
            if self._is_hotkey(key_name):
                now = time.monotonic()
                if now - self._last_hotkey_time > 0.5:
                    self._last_hotkey_time = now
                    self.signals.toggle_requested.emit()
                return

            if self.config["enabled"]:
                self.signals.key_pressed.emit(key_name, is_modifier)

        self.listener = KeyboardListener(on_key, self.config)
        self.signals.key_pressed.connect(self._play_sound)
        self.listener.start()

    def _stop_listening(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _play_sound(self, key_name: str, is_modifier: bool):
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(f"Key pressed: {key_name}, modifier={is_modifier}")

        if is_modifier and not self.config["play_modifiers"]:
            return
        profile = self.config["sound_profile"]
        logger.debug(f"Playing with profile: {profile}")
        self.audio.play_click(key_name, profile, is_modifier)

    def _play_mouse(self, button: str):
        if not self.config["enabled"] or not self.config.get("play_mouse", True):
            return
        self.audio.play_mouse(button)

    def _handle_mouse_click(self, button: str):
        if button in ("left", "right"):
            self.signals.mouse_clicked.emit(button)

    @staticmethod
    def _normalize_key(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _is_hotkey(self, key_name: str) -> bool:
        hotkey = self.config.get("hotkey", "F12")
        return self._normalize_key(hotkey) == self._normalize_key(key_name)

    @staticmethod
    def _mouse_button_from_key(key_name: str):
        if key_name.startswith("mouse_"):
            return key_name.split("_", 1)[1]
        return None

    def _set_volume(self, volume: int):
        self.config["volume"] = volume
        self.audio.set_volume(volume / 100)
        save_config(self.config)

        for v, action in self.volume_actions.items():
            action.setChecked(v == volume)

    def _set_profile(self, profile: str):
        self.config["sound_profile"] = profile
        save_config(self.config)

        for key, action in self.profile_actions.items():
            action.setChecked(key == profile)

    def _set_mouse_clicks(self, enabled: bool):
        self.config["play_mouse"] = enabled
        save_config(self.config)

    def _show_settings(self):
        msg = QMessageBox()
        msg.setWindowTitle("Clack Settings")
        excluded = self.config.get("excluded_device_keywords", [])
        if isinstance(excluded, str):
            excluded = [v.strip() for v in excluded.split(",") if v.strip()]

        use_wayclick = self.config.get("use_wayclick_sounds", False)
        wayclick_pack = self.config.get("wayclick_sound_pack", "audio_pack_1")

        msg.setText(
            f"Current Settings:\n\n"
            f"Enabled: {'Yes' if self.config['enabled'] else 'No'}\n"
            f"Volume: {self.config['volume']}%\n"
            f"Sound: {self.config['sound_profile']}\n"
            f"WayClick sounds: {'Yes' if use_wayclick else 'No'}\n"
            f"WayClick pack: {wayclick_pack}\n"
            f"Hotkey: {self.config['hotkey']}\n"
            f"Mouse clicks: {'Yes' if self.config.get('play_mouse', True) else 'No'}\n"
            f"Trackpad sounds: {'Yes' if self.config.get('enable_trackpad_sounds', False) else 'No'}\n"
            f"Auto-detect trackpads: {'Yes' if self.config.get('auto_detect_trackpads', True) else 'No'}\n"
            f"Hotplug poll: {self.config.get('hotplug_poll_seconds', 1.0)}s\n"
            f"Excluded keywords: {', '.join(excluded)}\n"
            f"Auto-start: {'Yes' if self.config['startup'] else 'No'}"
        )
        msg.exec()

    def run(self):
        self.app.exec()

    def quit(self):
        self._stop_listening()
        self.app.quit()
