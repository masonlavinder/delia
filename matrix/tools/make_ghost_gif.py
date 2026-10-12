#!/usr/bin/env python3
"""Generate assets/ghost.gif — a little ghost drifting left to right across a
black panel, bobbing as it goes, its hem rippling, under a few faint twinkling
stars. Regenerate:
    python3 tools/make_ghost_gif.py

Seamless loop: the ghost starts fully off the left edge and ends fully off the
right, so the wrap happens while it's out of sight; the bob, ripple, and twinkle
all use integer cycles per loop.
"""
import math
import os
import random

from PIL import Image, ImageDraw

W, H, N = 128, 64, 192
GW, GH = 22, 26           # ghost body size
TRAVEL = W + GW * 2       # off-left to off-right
BOBS = 4                  # bob cycles per crossing
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "ghost.gif")
)

BODY = (215, 225, 255)    # cool white
SHADE = (130, 145, 200)   # right-side shading, so it reads as round
FACE = (0, 0, 0)          # eyes and mouth are holes -> those LEDs stay off
CHEEK = (255, 120, 160)

random.seed(5)
stars = [(random.randrange(W), random.randrange(H - 6), random.randrange(1, 4),
          random.uniform(0, 2 * math.pi)) for _ in range(14)]


def draw_ghost(d, x, y, t):
    """Ghost with its top-left at (x, y). `t` drives the hem ripple and arms."""
    r = GW // 2
    d.ellipse((x, y, x + GW - 1, y + GW - 1), fill=BODY)                 # dome
    d.rectangle((x, y + r, x + GW - 1, y + GH - 5), fill=BODY)           # body
    # Shading: a crescent down the right side.
    d.arc((x, y, x + GW - 1, y + GW - 1), -60, 60, fill=SHADE)
    d.line([(x + GW - 1, y + r), (x + GW - 1, y + GH - 5)], fill=SHADE)
    # Hem: four scallops whose depth ripples along the hem over time.
    sw = GW / 4
    for i in range(4):
        depth = 3 + 2 * math.sin(t * 3 + i * 1.6)
        sx = x + i * sw
        d.ellipse((sx, y + GH - 5 - depth, sx + sw - 1, y + GH - 5 + depth), fill=BODY)
    # Little arms, waving slightly out of step with the bob.
    wave = round(1.5 * math.sin(t * 2))
    d.ellipse((x - 3, y + 11 + wave, x + 2, y + 15 + wave), fill=BODY)
    d.ellipse((x + GW - 3, y + 11 - wave, x + GW + 2, y + 15 - wave), fill=SHADE)
    # Face: oval eyes, a small "o" mouth, a hint of cheek.
    d.ellipse((x + 5, y + 7, x + 8, y + 12), fill=FACE)
    d.ellipse((x + 13, y + 7, x + 16, y + 12), fill=FACE)
    d.ellipse((x + 9, y + 14, x + 12, y + 18), fill=FACE)
    d.point([(x + 4, y + 13), (x + 17, y + 13)], fill=CHEEK)


frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for sx, sy, k, p in stars:
        b = 0.5 + 0.5 * math.sin(k * t + p)
        if b > 0.15:
            v = int(90 * b)
            d.point((sx, sy), fill=(v, v, int(v * 1.2)))
    gx = -GW - 3 + TRAVEL * f / N
    gy = (H - GH) / 2 + 9 * math.sin(BOBS * t)
    draw_ghost(d, round(gx), round(gy), BOBS * t)
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=70, loop=0)
print(f"wrote {OUT} ({N} frames)")
