#!/usr/bin/env python3
"""Generate assets/aurora.gif — slow teal/green/violet ribbons flowing across the
upper panel, fading to black below (so the bottom half stays dark -> lower
current). Regenerate:
    python3 tools/make_aurora_gif.py
"""
import math
import os

from PIL import Image, ImageChops

W, H, N = 128, 64, 120
TOP = 44          # ribbons live in the top rows; below is black
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "aurora.gif")
)

# Each ribbon is a horizontal band whose center undulates (two sines -> organic,
# seamless over one t cycle) and whose intensity falls off with vertical distance.
RIBBONS = [
    {"base": 16, "amp": 7, "k1": 26, "k2": 40, "spread": 6, "color": (40, 230, 140)},
    {"base": 24, "amp": 9, "k1": 34, "k2": 22, "spread": 8, "color": (30, 180, 210)},
    {"base": 12, "amp": 5, "k1": 20, "k2": 50, "spread": 5, "color": (120, 90, 220)},
]

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for x in range(W):
        for rb in RIBBONS:
            yc = (rb["base"]
                  + rb["amp"] * math.sin(x / rb["k1"] + t)
                  + rb["amp"] * 0.6 * math.sin(x / rb["k2"] - t))
            for y in range(TOP):
                d = y - yc
                inten = math.exp(-(d * d) / (2 * rb["spread"] ** 2))
                inten *= max(0.0, 1 - y / TOP)   # global top-to-bottom fade to black
                if inten <= 0.02:
                    continue
                orr, og, ob = px[x, y]
                px[x, y] = (
                    min(orr + int(rb["color"][0] * inten), 255),
                    min(og + int(rb["color"][1] * inten), 255),
                    min(ob + int(rb["color"][2] * inten), 255),
                )
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
comp = frames[0].copy()
for fr in frames[1:]:
    comp = ImageChops.lighter(comp, fr)
pal = comp.quantize(colors=256, dither=Image.Dither.NONE)
pframes = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
pframes[0].save(OUT, save_all=True, append_images=pframes[1:], duration=70, loop=0)
print(f"wrote {OUT} ({N} frames, {len(RIBBONS)} ribbons)")
