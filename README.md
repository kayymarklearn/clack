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

## Acknowledgements
Sound samples are derived from the **Klick** sound pack (MIT). See `THIRD_PARTY_NOTICES.txt`.
