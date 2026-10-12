#!/usr/bin/env python3
"""Generate assets/leaves.gif — autumn leaves drifting slowly down a black
panel, swaying and tumbling, with a few settled on the ground. Regenerate:
    python3 tools/make_leaves_gif.py

Seamless loop: each leaf falls the whole drop (H + margin) an integer number of
times per loop, wrapping from the bottom back to the top, and its sway and spin
use integer frequencies -> every leaf is back where it started at f=N.
Two depths: far leaves are small, dim, and fall once per loop; near leaves are
bigger, brighter, and fall twice — cheap parallax.
"""
import math
import os
import random

from PIL import Image, ImageDraw

W, H, N = 128, 64, 240
MARGIN = 10               # leaves start/end fully off-panel
DROP = H + MARGIN * 2
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "leaves.gif")
)

COLORS = [
    (220, 50, 10),    # red
    (240, 100, 0),    # orange
    (245, 160, 0),    # gold
    (200, 120, 10),   # amber
    (140, 60, 15),    # brown
    (180, 30, 20),    # crimson
]

random.seed(7)
leaves = []
for i in range(16):
    near = i % 3 == 0
    leaves.append({
        "x0": random.uniform(6, W - 6),
        "y0": random.uniform(0, DROP),
        "laps": 2 if near else 1,          # falls per loop
        "size": random.uniform(4.5, 5.5) if near else random.uniform(2.8, 3.6),
        "dim": 1.0 if near else 0.6,
        "sway": random.uniform(5, 10),
        "sf": random.choice([2, 3, 4]),    # sway cycles per loop
        "sp": random.uniform(0, 2 * math.pi),
        "spin": random.choice([1, 2, 3]),  # tumble cycles per loop
        "color": random.choice(COLORS),
    })

# A low drift of settled leaves along the bottom edge (static).
random.seed(3)
pile = [(random.uniform(2, W - 2), random.uniform(H - 3, H - 0.5),
         random.uniform(0, math.pi), random.choice(COLORS)) for _ in range(28)]


def leaf_poly(cx, cy, size, angle, squash):
    """A pointed oval (two arcs meeting at the tips), rotated by `angle` and
    squashed across its width by `squash` to fake turning edge-on."""
    pts = []
    steps = 6
    for side in (1, -1):
        for k in range(steps + 1):
            u = k / steps                      # 0..1 tip to tip
            along = (u - 0.5) * 2 * size
            across = side * math.sin(math.pi * u) * size * 0.55 * squash
            if side == -1:
                along = -along
            ca, sa = math.cos(angle), math.sin(angle)
            pts.append((cx + along * ca - across * sa, cy + along * sa + across * ca))
    return pts


def scale(c, s):
    return tuple(int(v * s) for v in c)


frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for x, y, a, c in pile:
        d.polygon(leaf_poly(x, y, 3, a, 0.7), fill=scale(c, 0.45))
    # Far leaves first so near ones pass in front of them.
    for lf in sorted(leaves, key=lambda l: l["laps"]):
        y = (lf["y0"] + DROP * lf["laps"] * f / N) % DROP - MARGIN
        sway = math.sin(lf["sf"] * t + lf["sp"])
        x = (lf["x0"] + lf["sway"] * sway) % W
        # Tilt follows the sway (a leaf leans into its swing); the squash comes
        # from a separate spin so it occasionally flips edge-on.
        angle = 0.9 * math.cos(lf["sf"] * t + lf["sp"]) + 0.4
        squash = 0.35 + 0.65 * abs(math.cos(lf["spin"] * t + lf["sp"]))
        col = scale(lf["color"], lf["dim"])
        poly = leaf_poly(x, y, lf["size"], angle, squash)
        d.polygon(poly, fill=col)
        if lf["laps"] == 2:   # a midrib on the near leaves only — too small to read on far ones
            ca, sa = math.cos(angle), math.sin(angle)
            s = lf["size"]
            d.line([(x - s * ca, y - s * sa), (x + s * ca, y + s * sa)], fill=scale(col, 0.55))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=80, loop=0)
print(f"wrote {OUT} ({N} frames, {len(leaves)} leaves)")
