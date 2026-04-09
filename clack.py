#!/usr/bin/env python3
"""
Clack - Mechanical Keyboard Click Sound App
Run in background to play click sounds on keypress
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler("/tmp/clack.log"), logging.StreamHandler()],
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clack.app import ClackApp


def main():
    app = ClackApp()
    app.run()


if __name__ == "__main__":
    main()
