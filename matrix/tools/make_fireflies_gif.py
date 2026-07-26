#!/usr/bin/env python3
"""Generate assets/fireflies.gif — a few soft warm glows drifting on black and
pulsing. Very sparse -> negligible current. Regenerate:
    python3 tools/make_fireflies_gif.py
"""
import math
import os
import random

from PIL import Image, ImageChops

W, H, N = 128, 64, 120
COUNT = 11
R = 3             # glow radius
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fireflies.gif")
)

random.seed(11)
# Each firefly drifts along a closed Lissajous path (integer freqs -> returns to
# start at f=N -> seamless) and pulses in brightness.
flies = []
for _ in range(COUNT):
    flies.append({
        "cx": random.uniform(12, W - 12), "cy": random.uniform(10, H - 10),
        "ax": random.uniform(6, 18), "ay": random.uniform(5, 14),
        "fx": random.choice([1, 1, 2]), "fy": random.choice([1, 2, 2]),
        "px": random.uniform(0, 2 * math.pi), "py": random.uniform(0, 2 * math.pi),
        "pulse": random.choice([1, 2, 3]), "pp": random.uniform(0, 2 * math.pi),
    })

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for fly in flies:
        x = fly["cx"] + fly["ax"] * math.sin(fly["fx"] * t + fly["px"])
        y = fly["cy"] + fly["ay"] * math.sin(fly["fy"] * t + fly["py"])
        b = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(fly["pulse"] * t + fly["pp"]))
        xi, yi = int(round(x)), int(round(y))
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                nx, ny = xi + dx, yi + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                dist = math.hypot(dx, dy)
                if dist > R:
                    continue
                g = (1 - dist / R) ** 2 * b       # soft radial falloff
                orr, og, ob = px[nx, ny]
                px[nx, ny] = (           # warm yellow-green
                    min(orr + int(200 * g), 255),
                    min(og + int(230 * g), 255),
                    min(ob + int(90 * g), 255),
                )
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
comp = frames[0].copy()
for fr in frames[1:]:
    comp = ImageChops.lighter(comp, fr)
pal = comp.quantize(colors=256, dither=Image.Dither.NONE)
pframes = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
pframes[0].save(OUT, save_all=True, append_images=pframes[1:], duration=70, loop=0)
print(f"wrote {OUT} ({N} frames, {COUNT} fireflies)")
