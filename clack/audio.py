import logging
import os
import subprocess
import threading
from pathlib import Path
from shutil import which

from clack.config import get_sounds_dir

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class AudioEngine:
    def __init__(self):
        self._sounds = {}
        self._modifier_sounds = {}
        self._mouse_sounds = {}
        self._volume = 0.7
        self._sounds_dir = get_sounds_dir()
        self._player = self._detect_player()
        self._load_sounds()
        logger.info(f"AudioEngine initialized")

    def _load_sounds(self):
        profiles = ["clicky", "tactile", "linear"]

        for profile in profiles:
            profile_dir = self._sounds_dir / profile
            if not profile_dir.exists():
                logger.warning(f"Profile dir not found: {profile_dir}")
                continue
            default_file = profile_dir / "default.wav"
            if default_file.exists():
                self._sounds[profile] = str(default_file)
                logger.debug(f"Loaded {profile}: {default_file}")

        mod_dir = self._sounds_dir / "modifier"
        if mod_dir.exists():
            default_mod = mod_dir / "default.wav"
            if default_mod.exists():
                self._modifier_sounds["default"] = str(default_mod)

        mouse_dir = self._sounds_dir / "mouse"
        if mouse_dir.exists():
            left = mouse_dir / "left.wav"
            right = mouse_dir / "right.wav"
            middle = mouse_dir / "middle.wav"
            default_mouse = mouse_dir / "default.wav"
            if left.exists():
                self._mouse_sounds["left"] = str(left)
            if right.exists():
                self._mouse_sounds["right"] = str(right)
            if middle.exists():
                self._mouse_sounds["middle"] = str(middle)
            if default_mouse.exists():
                self._mouse_sounds["default"] = str(default_mouse)

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to {self._volume}")

    def play_click(self, key_name: str, profile: str, is_modifier: bool = False):
        logger.debug(
            f"play_click: {key_name}, profile={profile}, modifier={is_modifier}"
        )

        if is_modifier and self._modifier_sounds:
            sound_file = self._modifier_sounds.get("default")
            vol = self._volume * 0.5
        else:
            sound_file = self._sounds.get(profile)
            vol = self._volume

        if sound_file:
            try:
                threading.Thread(
                    target=self._play_sound, args=(sound_file, vol), daemon=True
                ).start()
                logger.debug(f"Playing: {sound_file}")
            except Exception as e:
                logger.error(f"Failed to play: {e}")
        else:
            logger.warning(f"No sound file for profile={profile}")

    def play_mouse(self, button: str):
        if not self._mouse_sounds:
            return

        sound_file = self._mouse_sounds.get(button) or self._mouse_sounds.get(
            "default"
        )
        if not sound_file:
            return

        try:
            threading.Thread(
                target=self._play_sound, args=(sound_file, self._volume), daemon=True
            ).start()
            logger.debug(f"Playing mouse: {sound_file}")
        except Exception as e:
            logger.error(f"Failed to play mouse: {e}")

    def _detect_player(self):
        if which("paplay"):
            return "paplay"
        if which("pw-play"):
            return "pw-play"
        if which("aplay"):
            return "aplay"
        logger.error(
            "No audio playback tool found. Install pulseaudio-utils or pipewire."
        )
        return None

    def _play_sound(self, sound_file: str, volume: float):
        if not self._player:
            return

        try:
            if self._player == "paplay":
                vol_int = int(volume * 65536)
                cmd = ["paplay", f"--volume={vol_int}", sound_file]
            elif self._player == "pw-play":
                cmd = ["pw-play", "--volume", f"{volume:.3f}", sound_file]
            else:
                cmd = ["aplay", sound_file]

            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as e:
            logger.error(f"{self._player} failed: {e}")

    def has_sounds(self) -> bool:
        return bool(self._sounds)
