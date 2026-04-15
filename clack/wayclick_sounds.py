#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from clack.config import load_config

DEFAULT_ZIP_URL = (
    "https://github.com/dusklinux/wayclick_soundpacks/archive/refs/heads/main.zip"
)
DEFAULT_PACK = "audio_pack_1"


def _get_default_pack() -> str:
    config = load_config()
    pack = config.get("wayclick_sound_pack", DEFAULT_PACK)
    if not isinstance(pack, str) or not pack.strip():
        return DEFAULT_PACK
    return pack.strip()


def _find_extracted_root(base_dir: Path) -> Path:
    candidates = list(base_dir.glob("wayclick_soundpacks-*/"))
    if not candidates:
        raise FileNotFoundError("Extracted soundpack directory not found in archive.")
    return candidates[0]


def install_soundpack(
    pack_name: str,
    url: str = DEFAULT_ZIP_URL,
    target_dir: Path | None = None,
    force: bool = False,
) -> Path:
    target_base = (target_dir or Path.home() / ".config" / "wayclick").expanduser()
    target_base.mkdir(parents=True, exist_ok=True)
    target_pack = target_base / pack_name

    if target_pack.exists():
        if not force:
            print(f"Soundpack already installed at {target_pack}")
            return target_pack
        shutil.rmtree(target_pack)

    tmp_dir = Path(tempfile.mkdtemp(prefix="clack-wayclick-"))
    try:
        zip_path = tmp_dir / "soundpacks.zip"
        with urllib.request.urlopen(url) as response, open(zip_path, "wb") as handle:
            handle.write(response.read())

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        extracted_root = _find_extracted_root(tmp_dir)
        source_pack = extracted_root / pack_name
        if not source_pack.is_dir():
            raise FileNotFoundError(
                f"Soundpack '{pack_name}' not found in {extracted_root}."
            )

        shutil.copytree(source_pack, target_pack)
        print(f"Installed {pack_name} to {target_pack}")
        return target_pack
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install WayClick soundpacks for Clack."
    )
    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser("install", help="Install a soundpack")
    install_parser.add_argument(
        "--pack",
        default=_get_default_pack(),
        help="Soundpack directory name (default: config value or audio_pack_1)",
    )
    install_parser.add_argument(
        "--url",
        default=DEFAULT_ZIP_URL,
        help="Soundpack ZIP URL",
    )
    install_parser.add_argument(
        "--target-dir",
        default=str(Path.home() / ".config" / "wayclick"),
        help="Install base directory",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing pack if present",
    )

    args = parser.parse_args()
    command = args.command or "install"

    if command == "install":
        install_soundpack(
            pack_name=args.pack,
            url=args.url,
            target_dir=Path(args.target_dir),
            force=args.force,
        )
        return

    parser.error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
