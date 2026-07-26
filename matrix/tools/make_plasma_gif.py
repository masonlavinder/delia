#!/usr/bin/env python3
"""Generate assets/plasma.gif — a seamlessly-looping, smoothly-gradated purple
plasma. Regenerate:  python3 tools/make_plasma_gif.py
"""
import math
import os

from PIL import Image

W, H, N = 128, 64, 60   # more frames -> smoother motion; t does one 2*pi cycle -> seamless loop
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "plasma.gif")
)

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            # broad wavelengths -> smooth, gradated field (no harsh transitions)
            v = (
                math.sin(x / 22.0 + t)
                + math.sin(y / 18.0 - t)
                + math.sin((x + y) / 30.0 + t)
                + math.sin(math.hypot(x - W / 2, y - H / 2) / 18.0 - t)
            )
            n = (v + 4) / 8.0        # 0..1, NO contrast steepening -> smooth gradient
            # smooth purple ramp: deep indigo -> violet -> soft magenta
            r = int(18 + 150 * n)
            g = int(6 + 46 * n * n)  # keep green low so it stays purple
            b = int(45 + 165 * n)
            px[x, y] = (min(r, 255), min(g, 255), min(b, 255))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=90, loop=0)
print(f"wrote {OUT} ({N} frames)")
