"""Shared helpers for every scene: build the RGBMatrix, load bundled fonts.

Working config for the Adafruit 128x64 2mm panel on the RGB Matrix Bonnet + Pi 3 A+.
See ../led-matrix-setup.md. Do NOT add FM6126A or a custom multiplexing value --
that was a dead end. Stock 'adafruit-hat' (E on GPIO 24, jumper soldered) is correct.
"""
import os
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics


def build_matrix(brightness=50):
    o = RGBMatrixOptions()
    o.rows = 64
    o.cols = 128
    o.chain_length = 1
    o.parallel = 1
    o.hardware_mapping = "adafruit-hat"   # E on GPIO 24 (stock); bonnet "8" pad soldered
    o.multiplexing = 0
    o.row_address_type = 0
    o.gpio_slowdown = 2                    # raise toward 4 if glitchy, drop to 1 if solid
    o.brightness = brightness             # keep modest; full white pulls a lot of current
    o.drop_privileges = False
    return RGBMatrix(options=o)


def _fonts_dir():
    """Locate the fonts bundled with rpi-rgb-led-matrix, even when run under sudo."""
    user = os.environ.get("SUDO_USER") or ""
    home = os.path.expanduser("~" + user)
    return os.path.join(home, "rpi-rgb-led-matrix", "fonts")


def load_font(name="7x13.bdf"):
    """Load a BDF font by filename, e.g. load_font('10x20.bdf')."""
    f = graphics.Font()
    f.LoadFont(os.path.join(_fonts_dir(), name))
    return f
