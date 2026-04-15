# Clack

Linux tray app that plays mechanical keyboard sounds on keypress. Inspired by the macOS app [Klick](https://github.com/champ3oy/Klick).

## Features
- Mechanical key sounds with three profiles: Clicky, Tactile, Linear
- Mouse click sounds (left + right click)
- Modifier key sound support
- Tray toggle + default hotkey (**F12**)
- Optional systemd user service

## Requirements
- Python 3.10+
- Audio playback: **paplay** (pulseaudio-utils) or **pw-play** (pipewire) or **aplay**
- Input access: user must be in the **input** group on Linux

## Install (Arch)
```bash
sudo pacman -S python python-pip pulseaudio-utils
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python clack.py
```

## WayClick soundpacks (optional)
Clack can use WayClick soundpacks stored in `~/.config/wayclick/<pack>`. To install
the default pack (`audio_pack_1`):
```bash
python -m clack.wayclick_sounds install
```

## Permissions (required)
```bash
sudo usermod -aG input $USER
```
Log out and back in after adding the group.

## Systemd user service
```bash
cp clack.service ~/.config/systemd/user/clack.service
```
Edit `ExecStart` if you use a virtualenv (point it to your `.venv/bin/python`).

```bash
systemctl --user daemon-reload
systemctl --user enable --now clack
```

## Configuration
Config lives at `~/.config/clack/config.json`.

Default hotkey: **F12**. Change `"hotkey"` in the config and restart the service/app.

Mouse clicks: toggle `"play_mouse"` in the config or via the tray menu.

Trackpad filtering (evdev backend):
- `"enable_trackpad_sounds"`: `false` (default) excludes touchpads/trackpads from sounds.
- `"auto_detect_trackpads"`: `true` uses device capabilities to detect unnamed touchpads.
- `"excluded_device_keywords"`: list of substrings matched against device names.
- `"hotplug_poll_seconds"`: device rescan interval to pick up newly connected devices.

WayClick soundpacks (optional):
- `"use_wayclick_sounds"`: `true` (default) will use `~/.config/wayclick/<pack>` if present.
- `"wayclick_sound_pack"`: pack directory name (default: `audio_pack_1`).

You can also switch packs from the tray menu via **WayClick Pack**.

## Acknowledgements
Sound samples are derived from the **Klick** sound pack (MIT). See `THIRD_PARTY_NOTICES.txt`.
