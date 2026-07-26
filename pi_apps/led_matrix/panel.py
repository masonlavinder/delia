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

    # 'adafruit-hat' expects the E address line on pin 8 -- matches the E->8
    # solder jumper required for this 64-tall ABCDE panel.
    # If you also solder the GPIO4<->GPIO18 jumper (optional, flicker-free
    # quality via hardware PWM), change this to 'adafruit-hat-pwm'.
    options.hardware_mapping = 'adafruit-hat'

    # Adafruit 6484 (128x64, 2mm) uses FM6126A driver chips -> needs the init
    # sequence or it shows garbage/split content.
    options.panel_type = 'FM6126A'
    # NOTE: this panel's scan mapping isn't fully solved yet. multiplexing=17
    # (FlippedStripe) gets closest to full coverage; still being dialed in.
    options.multiplexing = 17
    options.row_address_type = 0

    # Pi 3-class board. 2 is a good start; raise toward 4 if you see
    # glitches/tearing, drop to 1 if rock-solid.
    options.gpio_slowdown = 2

    # 0-100. KEEP THIS LOW at first. Full white at high brightness pulls a lot
    # of current from your 5V supply.
    options.brightness = brightness

    options.drop_privileges = False
    return RGBMatrix(options=options)
