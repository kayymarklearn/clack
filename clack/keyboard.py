import logging
import os
import select
import sys
import threading
import time

logger = logging.getLogger(__name__)

MODIFIER_KEYS = {
    "shift",
    "ctrl",
    "alt",
    "enter",
    "space",
    "backspace",
    "tab",
    "caps_lock",
    "left shift",
    "right shift",
    "left ctrl",
    "right ctrl",
    "left alt",
    "right alt",
    "left",
    "right",
    "up",
    "down",
    "cmd",
    "super",
}

DEFAULT_EXCLUDED_KEYWORDS = (
    "touchpad",
    "trackpad",
    "glidepoint",
    "magic trackpad",
    "clickpad",
)


def _normalize_key_name(raw: str) -> str:
    name = raw.replace("KEY_", "").lower()
    name = name.replace("_", " ")
    aliases = {
        "leftshift": "left shift",
        "rightshift": "right shift",
        "leftctrl": "left ctrl",
        "rightctrl": "right ctrl",
        "leftalt": "left alt",
        "rightalt": "right alt",
        "capslock": "caps_lock",
        "numlock": "num_lock",
        "scrolllock": "scroll_lock",
        "btn left": "mouse_left",
        "btn right": "mouse_right",
        "btn middle": "mouse_middle",
    }
    return aliases.get(name, name)


class KeyboardListener(threading.Thread):
    def __init__(self, callback, config=None):
        super().__init__(daemon=True)
        self._callback = callback
        self._running = False
        self._devices = []
        self._backend = None
        self._config = config or {}

    def run(self):
        self._running = True
        backend = os.environ.get("CLACK_INPUT_BACKEND", "").strip().lower()

        try:
            if backend == "pynput":
                self._backend = "pynput"
                self._run_pynput()
            elif sys.platform.startswith("linux"):
                self._backend = "evdev"
                self._run_evdev()
            else:
                self._backend = "pynput"
                self._run_pynput()
        except Exception as e:
            logger.error(f"Keyboard listener error ({self._backend}): {e}")
            import traceback

            logger.error(traceback.format_exc())
            self._running = False

    def stop(self):
        self._running = False

    def _run_pynput(self):
        from pynput import keyboard as pynput_keyboard

        logger.info("Using pynput for key detection")
        pressed = set()

        def _get_key_name(key):
            try:
                key_name = (
                    key.char
                    if hasattr(key, "char") and key.char
                    else str(key).replace("Key.", "")
                )
            except Exception:
                key_name = str(key).replace("Key.", "")
            return key_name.lower()

        def on_press(key):
            key_name = _get_key_name(key)
            is_modifier = key_name in MODIFIER_KEYS or "Key." in str(key)
            if key_name in pressed:
                event_value = 2
            else:
                pressed.add(key_name)
                event_value = 1
            self._callback(key_name, is_modifier, event_value)

        def on_release(key):
            key_name = _get_key_name(key)
            pressed.discard(key_name)
            is_modifier = key_name in MODIFIER_KEYS or "Key." in str(key)
            self._callback(key_name, is_modifier, 0)

        listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        logger.info("pynput listener started, waiting for keypresses...")

        while self._running:
            threading.Event().wait(0.5)

        listener.stop()

    def _normalize_keywords(self, value):
        if isinstance(value, (list, tuple, set)):
            keywords = [str(k).strip().lower() for k in value if str(k).strip()]
        elif isinstance(value, str):
            keywords = [k.strip().lower() for k in value.split(",") if k.strip()]
        else:
            keywords = []
        return keywords

    def _as_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if value is None:
            return default
        return bool(value)

    def _get_hotplug_interval(self):
        value = self._config.get("hotplug_poll_seconds", 1.0)
        try:
            interval = float(value)
        except (TypeError, ValueError):
            interval = 1.0
        return max(0.1, interval)

    def _should_ignore_device(self, dev, caps, ecodes):
        if self._as_bool(self._config.get("enable_trackpad_sounds", False)):
            return False, None

        keywords = self._normalize_keywords(
            self._config.get("excluded_device_keywords", DEFAULT_EXCLUDED_KEYWORDS)
        )
        name_lower = (dev.name or "").lower()
        if keywords and any(keyword in name_lower for keyword in keywords):
            return True, "keyword"

        if self._as_bool(self._config.get("auto_detect_trackpads", True)):
            abs_codes = caps.get(ecodes.EV_ABS, [])
            key_codes = caps.get(ecodes.EV_KEY, [])
            has_mt = ecodes.ABS_MT_POSITION_X in abs_codes
            has_finger = ecodes.BTN_TOOL_FINGER in key_codes
            if has_mt or has_finger:
                return True, "touchpad"

        return False, None

    def _open_evdev_devices(self, paths, existing_paths, skipped_paths):
        from evdev import InputDevice, ecodes

        devices = []
        keyboard_markers = {
            ecodes.KEY_A,
            ecodes.KEY_Z,
            ecodes.KEY_SPACE,
            ecodes.KEY_ENTER,
        }
        mouse_markers = {
            ecodes.BTN_LEFT,
            ecodes.BTN_RIGHT,
            ecodes.BTN_MIDDLE,
        }

        for path in paths:
            if path in existing_paths or path in skipped_paths:
                continue
            try:
                dev = InputDevice(path)
                caps = dev.capabilities(absinfo=False)
                keys = caps.get(ecodes.EV_KEY, [])
                if not keys:
                    dev.close()
                    skipped_paths.add(path)
                    continue
                ignore, reason = self._should_ignore_device(dev, caps, ecodes)
                if ignore:
                    logger.info("Skipping %s (%s): %s", dev.name, dev.path, reason)
                    dev.close()
                    skipped_paths.add(path)
                    continue
                keyset = set(k for k in keys if isinstance(k, int))
                if not (
                    keyboard_markers.intersection(keyset)
                    or mouse_markers.intersection(keyset)
                ):
                    dev.close()
                    skipped_paths.add(path)
                    continue
                devices.append(dev)
                logger.info(f"Listening to {dev.path} ({dev.name})")
            except PermissionError:
                logger.warning(
                    "Permission denied for %s. Add user to input group or use udev rules.",
                    path,
                )
                skipped_paths.add(path)
            except OSError as e:
                logger.warning("Failed to open %s: %s", path, e)
                skipped_paths.add(path)

        return devices

    def _run_evdev(self):
        from evdev import ecodes, list_devices

        logger.info("Using evdev for key detection")
        devices = []
        device_paths = set()
        skipped_paths = set()
        hotplug_interval = self._get_hotplug_interval()
        last_scan = 0.0
        reported_no_devices = False

        while self._running:
            now = time.monotonic()
            if now - last_scan >= hotplug_interval:
                all_paths = list_devices()
                current_set = set(all_paths)
                skipped_paths &= current_set
                new_devices = self._open_evdev_devices(
                    all_paths, device_paths, skipped_paths
                )
                for dev in new_devices:
                    device_paths.add(dev.path)
                    devices.append(dev)
                last_scan = now
                if devices:
                    reported_no_devices = False

            if not devices:
                if not reported_no_devices:
                    logger.error(
                        "No accessible keyboard devices. Check /dev/input permissions."
                    )
                    reported_no_devices = True
                threading.Event().wait(min(0.5, hotplug_interval))
                continue

            self._devices = devices
            ready, _, _ = select.select(devices, [], [], 0.5)
            for dev in ready:
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.value not in (0, 1, 2):
                            continue
                        name_entry = ecodes.bytype[ecodes.EV_KEY].get(event.code)
                        if isinstance(name_entry, tuple):
                            key_name = name_entry[0]
                        elif isinstance(name_entry, str):
                            key_name = name_entry
                        else:
                            key_name = f"KEY_{event.code}"
                        if not (
                            key_name.startswith("KEY_")
                            or key_name in ("BTN_LEFT", "BTN_RIGHT", "BTN_MIDDLE")
                        ):
                            continue
                        key_name = _normalize_key_name(key_name)
                        is_modifier = key_name in MODIFIER_KEYS
                        self._callback(key_name, is_modifier, event.value)
                except OSError as e:
                    logger.warning("Input device disconnected: %s (%s)", dev.path, e)
                    try:
                        dev.close()
                    except OSError:
                        pass
                    devices = [d for d in devices if d is not dev]
                    device_paths.discard(dev.path)
                    self._devices = devices

        for dev in devices:
            try:
                dev.close()
            except OSError:
                pass
