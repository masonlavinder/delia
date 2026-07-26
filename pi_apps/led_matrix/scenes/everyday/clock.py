"""Digital clock: big HH:MM with AM/PM and the date below.
Uses the Pi's local time (timezone was set during setup).

Run:  ./run.sh everyday/clock        (Ctrl-C to stop)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from rgbmatrix import graphics
from core.panel import build_matrix, load_font

matrix = build_matrix(brightness=50)
canvas = matrix.CreateFrameCanvas()
big = load_font("10x20.bdf")
small = load_font("6x13.bdf")
cyan = graphics.Color(0, 200, 255)
grey = graphics.Color(130, 130, 130)

try:
    while True:
        now = time.localtime()
        hhmm = time.strftime("%-I:%M", now)   # 12-hour, no leading zero
        ampm = time.strftime("%p", now)
        date = time.strftime("%a %b %-d", now)
        canvas.Clear()
        graphics.DrawText(canvas, big, 6, 34, cyan, hhmm)
        graphics.DrawText(canvas, small, 96, 22, grey, ampm)
        graphics.DrawText(canvas, small, 6, 56, grey, date)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(10)
except KeyboardInterrupt:
    matrix.Clear()
