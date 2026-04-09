import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "clack"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "volume": 70,
    "sound_profile": "clicky",
    "hotkey": "F12",
    "play_modifiers": True,
    "startup": True,
}


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_sounds_dir() -> Path:
    return Path(__file__).parent / "sounds"
