"""Rocket flight: a little rocket streaks left-to-right across a starfield with
flickering flames trailing behind, over and over. Rendered live, loops forever.

Run:  display rocket        (Ctrl-C to stop)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
import random
from PIL import Image, ImageDraw
from core.panel import build_matrix

matrix = build_matrix(brightness=60)
W, H = matrix.width, matrix.height

# starfield: [x, y, brightness]
stars = [[random.randint(0, W - 1), random.randint(0, H - 1),
          random.choice([70, 120, 180])] for _ in range(45)]


def draw_rocket(d, nose, cy):
    # flames trail LEFT from the tail (flicker every frame)
    flen = random.randint(5, 12)
    for i, col in enumerate([(255, 240, 120), (255, 150, 30), (220, 60, 20)]):
        w = 4 - i
        d.polygon([(nose - 20, cy - w), (nose - 20, cy + w),
                   (nose - 20 - (flen - i * 3), cy)], fill=col)
    d.rectangle([nose - 20, cy - 4, nose - 7, cy + 4], fill=(215, 215, 225))  # body
    d.polygon([(nose, cy), (nose - 7, cy - 4), (nose - 7, cy + 4)], fill=(230, 40, 40))  # nose
    d.ellipse([nose - 13, cy - 2, nose - 9, cy + 2], fill=(90, 200, 255))     # window
    d.polygon([(nose - 16, cy - 4), (nose - 22, cy - 8), (nose - 16, cy - 4 - 4)], fill=(230, 40, 40))  # top fin
    d.polygon([(nose - 16, cy + 4), (nose - 22, cy + 8), (nose - 16, cy + 4 + 4)], fill=(230, 40, 40))  # bottom fin


canvas = matrix.CreateFrameCanvas()   # offscreen buffer -> no tearing
nose = -6            # start off the left edge
cy = H // 2
try:
    while True:
        img = Image.new("RGB", (W, H), (0, 0, 0))    # true black -> pixels fully off
        d = ImageDraw.Draw(img)
        for s in stars:                              # stars streak left (rocket flies right)
            s[0] = (s[0] - 2) % W
            b = s[2]
            img.putpixel((s[0], s[1]), (b, b, b))
        draw_rocket(d, nose, cy)
        canvas.SetImage(img)
        canvas = matrix.SwapOnVSync(canvas)          # flip between refreshes
        time.sleep(0.05)
        nose += 2
        if nose - 26 > W:                            # fully off the right -> relaunch from left
            nose = -6
            cy = random.randint(12, H - 12)
except KeyboardInterrupt:
    matrix.Clear()
