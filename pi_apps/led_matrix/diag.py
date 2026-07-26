"""Panel geometry diagnostic. Draws a full-border rectangle + a big label so you
can find the correct multiplexing / row-address settings for your panel.

Usage:  sudo python3 diag.py <multiplexing> [row_addr_type]
The right setting is the one where the border is a single clean rectangle
touching all four edges and the label text is crisp and un-split.
"""
import sys
import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

mult = int(sys.argv[1]) if len(sys.argv) > 1 else 0
row_addr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
panel_type = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else ""
mode = sys.argv[4] if len(sys.argv) > 4 else "rainbow"
slowdown = int(sys.argv[5]) if len(sys.argv) > 5 else 2

opts = RGBMatrixOptions()
opts.rows = int(os.environ.get("ROWS", "64"))
opts.cols = int(os.environ.get("COLS", "128"))
opts.chain_length = int(os.environ.get("CHAIN", "1"))
opts.parallel = 1
opts.hardware_mapping = 'adafruit-hat'
opts.gpio_slowdown = slowdown
opts.brightness = 50
opts.multiplexing = mult
opts.row_address_type = row_addr
if panel_type:
    opts.panel_type = panel_type
opts.drop_privileges = False

m = RGBMatrix(options=opts)
canvas = m.CreateFrameCanvas()
font = graphics.Font()
font.LoadFont("/home/mlavinder/rpi-rgb-led-matrix/fonts/10x20.bdf")
white = graphics.Color(255, 255, 255)

if mode == "white":
    # Solid white fill: correct scan setting => WHOLE panel lights white.
    for y in range(m.height):
        for x in range(m.width):
            canvas.SetPixel(x, y, 180, 180, 180)
    # setting number in black at three heights so it reads wherever rows light
    lbl = "M%d" % mult
    for yy in (14, 34, 54):
        graphics.DrawText(canvas, font, 4, yy, graphics.Color(0, 0, 0), lbl)
else:
    # 8 stacked rainbow stripes, each 8 rows tall, labeled 0-7.
    # Correct panel reads top->bottom: red,orange,yellow,green,cyan,blue,magenta,white
    STRIPES = [
        (255, 0, 0),     # 0 red
        (255, 110, 0),   # 1 orange
        (255, 255, 0),   # 2 yellow
        (0, 255, 0),     # 3 green
        (0, 255, 255),   # 4 cyan
        (0, 0, 255),     # 5 blue
        (255, 0, 255),   # 6 magenta
        (255, 255, 255), # 7 white
    ]
    band = m.height // len(STRIPES)   # 8 rows per stripe on a 64-tall panel
    for i, (r, g, b) in enumerate(STRIPES):
        y0 = i * band
        for y in range(y0, y0 + band):
            for x in range(m.width):
                canvas.SetPixel(x, y, r, g, b)
        graphics.DrawText(canvas, font, 2, y0 + band - 1, graphics.Color(0, 0, 0), str(i))
m.SwapOnVSync(canvas)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    m.Clear()
