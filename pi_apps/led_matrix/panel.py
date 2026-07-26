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

    # 'adafruit-hat' -- REQUIRES the library patch that puts the E address line
    # on GPIO 24 (see led-matrix-setup.md "THE CRITICAL FIX"). The bonnet wires
    # E to GPIO 24; stock hzeller must be edited to match, or you get the
    # 16-on/16-off banding. Solder-wise, E is bridged to the "8" pad (HUB75 pin).
    options.hardware_mapping = 'adafruit-hat'

    # Known-good config (see led-matrix-setup.md). These are library defaults,
    # kept explicit for clarity. FM6126A init is NOT needed once E is on GPIO 24.
    options.multiplexing = 0
    options.row_address_type = 0

    # Pi 3-class board. 2 is a good start; raise toward 4 if you see
    # glitches/tearing, drop to 1 if rock-solid.
    options.gpio_slowdown = 2

    # 0-100. KEEP THIS LOW at first. Full white at high brightness pulls a lot
    # of current from your 5V supply.
    options.brightness = brightness

    options.drop_privileges = False
    return RGBMatrix(options=options)
