"""Shared helper: build the RGBMatrix object for our panel.

Hardware: Adafruit 128x64 RGB LED Matrix (HUB75, 2mm pitch) on the
Adafruit RGB Matrix Bonnet, driven from a Raspberry Pi 3 A+.

Every scene imports build_matrix() from here so the panel config lives in one place.
"""
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def build_matrix(brightness=50):
    options = RGBMatrixOptions()
    options.rows = 64            # panel is 64 pixels tall
    options.cols = 128           # panel is 128 pixels wide
    options.chain_length = 1     # a single panel
    options.parallel = 1

    # 'adafruit-hat' works with the Bonnet out of the box.
    # If you later solder the GPIO4<->GPIO18 jumper on the Bonnet (better,
    # flicker-free quality via hardware PWM), change this to 'adafruit-hat-pwm'.
    options.hardware_mapping = 'adafruit-hat'

    # Pi 3-class board. Start at 2; drop to 1 if rock-solid, raise if you see
    # glitches/tearing.
    options.gpio_slowdown = 2

    # 0-100. KEEP THIS LOW at first. Full white at high brightness pulls a lot
    # of current from your 5V supply.
    options.brightness = brightness

    options.drop_privileges = False
    return RGBMatrix(options=options)
