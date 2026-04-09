import logging
import os
import select
import sys
import threading

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
    def __init__(self, callback):
        super().__init__(daemon=True)
        self._callback = callback
        self._running = False
        self._devices = []
        self._backend = None

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

        def on_press(key):
            try:
                key_name = (
                    key.char
                    if hasattr(key, "char") and key.char
                    else str(key).replace("Key.", "")
                )
            except Exception:
                key_name = str(key).replace("Key.", "")

            key_name = key_name.lower()
            is_modifier = key_name in MODIFIER_KEYS or "Key." in str(key)
            self._callback(key_name, is_modifier, 1)

        listener = pynput_keyboard.Listener(on_press=on_press)
        listener.start()
        logger.info("pynput listener started, waiting for keypresses...")

        while self._running:
            threading.Event().wait(0.5)

        listener.stop()

    def _open_evdev_devices(self):
        from evdev import InputDevice, list_devices, ecodes

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

        for path in list_devices():
            try:
                dev = InputDevice(path)
                keys = dev.capabilities().get(ecodes.EV_KEY, [])
                if not keys:
                    dev.close()
                    continue
                keyset = set(k for k in keys if isinstance(k, int))
                if not (
                    keyboard_markers.intersection(keyset)
                    or mouse_markers.intersection(keyset)
                ):
                    dev.close()
                    continue
                devices.append(dev)
                logger.info(f"Listening to {dev.path} ({dev.name})")
            except PermissionError:
                logger.warning(
                    "Permission denied for %s. Add user to input group or use udev rules.",
                    path,
                )
            except OSError as e:
                logger.warning("Failed to open %s: %s", path, e)

        return devices

    def _run_evdev(self):
        from evdev import ecodes

        logger.info("Using evdev for key detection")
        devices = self._open_evdev_devices()

        if not devices:
            logger.error(
                "No accessible keyboard devices. Check /dev/input permissions."
            )
            self._running = False
            return

        self._devices = devices

        while self._running:
            if not devices:
                devices = self._open_evdev_devices()
                self._devices = devices
                threading.Event().wait(1.0)
                continue

            ready, _, _ = select.select(devices, [], [], 0.5)
            for dev in ready:
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.value not in (1, 2):
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
                    self._devices = devices

        for dev in devices:
            try:
                dev.close()
            except OSError:
                pass
