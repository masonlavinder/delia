#!/usr/bin/env python3
"""Generate assets/rocket.gif — a rocket streaking left->right through a
deterministic starfield, flames flickering. Loops (rocket off-screen at both
ends). Regenerate:  python3 tools/make_rocket_gif.py
"""
import math
import os

from PIL import Image, ImageDraw

W, H, N = 128, 64, 64
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "rocket.gif"))


def _stars(n):
    seed, pts = 12345, []
    for _ in range(n):
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF; x = seed % W
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF; y = seed % H
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF; b = 70 + seed % 120
        pts.append((x, y, b))
    return pts


STARS = _stars(45)


def draw_rocket(d, nose, cy, flen):
    for i, col in enumerate([(255, 240, 120), (255, 150, 30), (220, 60, 20)]):
        w = 4 - i
        d.polygon([(nose - 20, cy - w), (nose - 20, cy + w), (nose - 20 - (flen - i * 3), cy)], fill=col)
    d.rectangle([nose - 20, cy - 4, nose - 7, cy + 4], fill=(215, 215, 225))
    d.polygon([(nose, cy), (nose - 7, cy - 4), (nose - 7, cy + 4)], fill=(230, 40, 40))
    d.ellipse([nose - 13, cy - 2, nose - 9, cy + 2], fill=(90, 200, 255))
    d.polygon([(nose - 16, cy - 4), (nose - 22, cy - 8), (nose - 16, cy - 8)], fill=(230, 40, 40))
    d.polygon([(nose - 16, cy + 4), (nose - 22, cy + 8), (nose - 16, cy + 8)], fill=(230, 40, 40))


frames = []
cy, span, start = H // 2, W + 90, -30
for f in range(N):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    scroll = (2 * f) % W
    for sx, sy, b in STARS:
        img.putpixel(((sx - scroll) % W, sy), (b, b, b))
    nose = start + int(span * f / N)
    flen = 8 + int(3 * math.sin(2 * math.pi * f / 8))
    draw_rocket(d, nose, cy, flen)
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=80, loop=0)
print(f"wrote {OUT} ({N} frames)")
