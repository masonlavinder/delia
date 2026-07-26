#!/usr/bin/env python3
"""Generate assets/matrix.gif — green "digital rain": bright heads falling down
thin columns with fading green tails. Thin columns keep the lit-pixel count (and
current) modest. Regenerate:
    python3 tools/make_matrix_gif.py
"""
import os
import random

from PIL import Image, ImageChops

W, H, N = 128, 64, 90
STEP = 4          # column spacing (px)
TAIL = 14         # max trailing length
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "matrix.gif")
)

FALL = H + TAIL   # a drop travels top -> off the bottom, plus its tail
random.seed(3)
cols = []
for cx in range(0, W, STEP):
    if random.random() < 0.35:
        continue  # leave some columns empty -> less coverage, less power
    cols.append({
        "x": cx,
        "loops": random.choice([1, 2, 2, 3]),   # whole falls per loop -> seamless
        "phase": random.uniform(0, FALL),
        "tail": random.randint(8, TAIL),
    })

frames = []
for f in range(N):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for c in cols:
        head = (c["phase"] + c["loops"] * FALL * f / N) % FALL
        for k in range(c["tail"]):
            y = int(head - k)          # tail trails ABOVE the falling head
            if 0 <= y < H:
                if k == 0:
                    px[c["x"], y] = (200, 255, 200)   # bright white-green head
                else:
                    frac = 1 - k / c["tail"]
                    px[c["x"], y] = (int(20 * frac), int(40 + 180 * frac), int(30 * frac))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
comp = frames[0].copy()
for fr in frames[1:]:
    comp = ImageChops.lighter(comp, fr)
pal = comp.quantize(colors=256, dither=Image.Dither.NONE)
pframes = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
pframes[0].save(OUT, save_all=True, append_images=pframes[1:], duration=70, loop=0)
print(f"wrote {OUT} ({N} frames, {len(cols)} columns)")
