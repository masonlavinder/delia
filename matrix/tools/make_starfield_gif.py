#!/usr/bin/env python3
"""Generate assets/starfield.gif — twinkling stars drifting on pure black.

Sparse by design: only a few hundred lit pixels at once, so it draws almost no
current (no power-sag streaks even at full brightness). Regenerate:
    python3 tools/make_starfield_gif.py
"""
import math
import os
import random

from PIL import Image, ImageChops

W, H, N = 128, 64, 90
STARS = 80
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "starfield.gif")
)

random.seed(7)
# Each star: position, base brightness, twinkle phase, drift (whole panel-widths
# per loop -> seamless), whether it's a bright "sparkle" (+), and a faint tint.
stars = []
for _ in range(STARS):
    stars.append({
        "x": random.uniform(0, W),
        "y": random.uniform(0, H),
        "b": random.uniform(0.25, 1.0),
        "p": random.uniform(0, 2 * math.pi),
        "drift": random.choice([1, 1, 2]),
        "big": random.random() < 0.15,
        "tint": random.choice([(1.0, 1.0, 1.0), (0.8, 0.85, 1.0), (1.0, 0.95, 0.8)]),
    })

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for s in stars:
        x = int((s["x"] + s["drift"] * W * f / N) % W)   # seamless drift
        y = int(s["y"]) % H
        v = s["b"] * (0.55 + 0.45 * math.sin(t + s["p"]))  # twinkle
        if v <= 0.02:
            continue
        r, g, b = (int(255 * v * c) for c in s["tint"])
        px[x, y] = (min(r, 255), min(g, 255), min(b, 255))
        if s["big"] and v > 0.4:
            arm = int(120 * v)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    orr, og, ob = px[nx, ny]
                    px[nx, ny] = (min(orr + arm, 255), min(og + arm, 255), min(ob + arm, 255))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
# One shared palette (from the brightest-of-all composite) + no dither -> stable,
# no crawl. See make_plasma_gif.py for why.
comp = frames[0].copy()
for fr in frames[1:]:
    comp = ImageChops.lighter(comp, fr)
pal = comp.quantize(colors=256, dither=Image.Dither.NONE)
pframes = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
pframes[0].save(OUT, save_all=True, append_images=pframes[1:], duration=80, loop=0)
print(f"wrote {OUT} ({N} frames, {STARS} stars)")
