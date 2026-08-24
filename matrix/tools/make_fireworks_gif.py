#!/usr/bin/env python3
"""Generate assets/fireworks.gif — shells that rise, burst, and fall dark.
Regenerate:
    python3 tools/make_fireworks_gif.py

Sparse by design: at any instant only one or two bursts are lit, so most of the
panel stays off and the current draw stays near the fireflies scene rather than
a full-panel animation.

Every shell is a pure function of its own phase `p` (0..1 across the loop), and
each phase is offset by a constant, so frame N lands exactly on frame 0 — the
loop closes with no seam and nothing carries state between frames.
"""
import colorsys
import math
import os
import random


from PIL import Image

W, H, N = 128, 64, 240
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fireworks.gif")
)

LAUNCH = 0.055       # fraction of a shell's cycle spent climbing
MAX_R = 21          # burst radius at full spread, px
GRAVITY = 14        # how far the sparks sag by the end, px

# Shells are generated rather than listed: a long sequence wants variety, and
# hand-writing twenty of them would be a wall of near-identical dicts. Seeded,
# so the same GIF comes out of every run — the loop repeats, and a burst that
# reshuffled every lap would strobe.
#
# Colour is a random hue at full saturation and value. Anything desaturated is
# grey mush on these LEDs, so only the hue is allowed to vary.
def make_shells(count=14, seed=7):
    rng = random.Random(seed)
    out = []
    for i in range(count):
        h = rng.random()
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        out.append({
            "x": rng.randint(14, W - 14),
            "apex": rng.randint(9, 27),
            "color": (int(r * 255), int(g * 255), int(b * 255)),
            # evenly spread around the loop, then jittered, so bursts do not
            # fall into a metronome rhythm
            "phase": (i / count + rng.uniform(-0.02, 0.02)) % 1.0,
            "n": rng.randint(14, 24),
            "seed": 100 + i,
        })
    return out


SHELLS = make_shells()


def spark_dirs(shell):
    """Fixed per-shell directions and speeds. Seeded, so the burst is the same
    shape every loop — a burst that reshuffled every lap would strobe."""
    rng = random.Random(shell["seed"])
    out = []
    for k in range(shell["n"]):
        a = 2 * math.pi * k / shell["n"] + rng.uniform(-0.12, 0.12)
        out.append((math.cos(a), math.sin(a), rng.uniform(0.40, 1.05)))
    return out


DIRS = {id(s): spark_dirs(s) for s in SHELLS}


def put(img, x, y, color, level):
    """Additive-ish plot: brighten toward `color` by `level`, never dim what is
    already lit (two sparks crossing should not cancel)."""
    if level <= 0.02:
        return
    xi, yi = int(x), int(y)
    if not (0 <= xi < W and 0 <= yi < H):
        return
    r0, g0, b0 = img.getpixel((xi, yi))
    img.putpixel((xi, yi), (max(r0, int(color[0] * level)),
                            max(g0, int(color[1] * level)),
                            max(b0, int(color[2] * level))))


frames = []
for f in range(N):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    t = f / N
    for shell in SHELLS:
        p = (t + shell["phase"]) % 1.0
        x0, apex, col = shell["x"], shell["apex"], shell["color"]

        if p < LAUNCH:
            # climbing: a bright head with a short tail, easing out as it tops
            u = p / LAUNCH
            y = (H - 1) - (u ** 0.75) * (H - 1 - apex)
            put(img, x0, y, (255, 240, 200), 1.0)
            for k in range(1, 5):
                put(img, x0, y + k, col, 0.45 - 0.09 * k)
            continue

        b = (p - LAUNCH) / (1 - LAUNCH)          # 0 at the burst, 1 when spent
        if b < 0.014:
            # the flash: a small solid ball before the sparks separate
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if dx * dx + dy * dy <= 4:
                        put(img, x0 + dx, apex + dy, (255, 255, 235), 1.0)
        spread = 1 - math.exp(-16.0 * b)          # fast out, then drifting
        fade = max(0.0, 1 - b / 0.16) ** 1.1
        for i, (cx, cy, speed) in enumerate(DIRS[id(shell)]):
            r = MAX_R * speed * spread
            x = x0 + cx * r
            y = apex + cy * r + GRAVITY * (b * 5) ** 2
            twinkle = 0.80 + 0.20 * math.sin(60 * math.pi * b + i)
            put(img, x, y, col, fade * twinkle)
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=66, loop=0)
print(f"wrote {OUT} ({N} frames)")
