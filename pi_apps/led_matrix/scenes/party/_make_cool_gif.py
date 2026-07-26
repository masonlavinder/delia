#!/usr/bin/env python3
"""Generate cool.gif — a seamlessly-looping purple plasma.

Not a scene (leading `_` hides it from `display`). Regenerate with:
    python3 scenes/party/_make_cool_gif.py
"""
import math
import os
from PIL import Image

W, H, N = 128, 64, 40          # frames; t completes one full 2*pi cycle -> seamless loop
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cool.gif")

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            v = (
                math.sin(x / 16.0 + t)
                + math.sin(y / 12.0 - t)
                + math.sin((x + y) / 20.0 + t)
                + math.sin(math.hypot(x - W / 2, y - H / 2) / 12.0 - t)
            )
            n = (v + 4) / 8.0                      # normalize -4..4 -> 0..1
            n = 0.5 + (n - 0.5) * 1.9              # steepen contrast (more drastic dark<->light)
            n = 0.0 if n < 0 else 1.0 if n > 1 else n
            r = min(255, int(6 + 116 * n))         # dark ~(6,0,12)  bright ~(122,30,152)
            g = min(255, int(0 + 30 * n * n))      # keep green low so it stays purple
            b = min(255, int(12 + 140 * n))
            px[x, y] = (r, g, b)
    frames.append(img)

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=100, loop=0)
print(f"wrote {OUT} ({N} frames)")
