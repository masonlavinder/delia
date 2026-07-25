"""First light: cycle the whole panel through red, green, blue, white.

This is the "did I wire and configure everything right?" test. If you see the
colors fill the panel, you're good to move on to the other scenes.

Run:  cd ~/delia/pi_apps/led_matrix && sudo python3 hello.py
Stop: Ctrl-C
"""
import time
from panel import build_matrix

matrix = build_matrix(brightness=40)
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]

try:
    while True:
        for r, g, b in colors:
            matrix.Fill(r, g, b)
            time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()
