#!/usr/bin/env python3
"""Generate assets/pumpkin.gif — a jack-o'-lantern on black whose carved face
flickers like a candle, with a faint warm glow spilling onto the ground.
Regenerate:
    python3 tools/make_pumpkin_gif.py

The body is drawn once and reused; only the face and the ground glow change per
frame. The flicker is a sum of sines at integer multiples of the loop frequency,
so it looks irregular but returns exactly to its start at f=N -> seamless.
"""
import math
import os

from PIL import Image, ImageDraw

W, H, N = 128, 64, 120
CX, CY = 64, 36            # pumpkin center
RX, RY = 30, 22            # pumpkin half-width / half-height
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "pumpkin.gif")
)

ORANGE = (235, 110, 10)
RIB = (150, 55, 0)         # darker orange for the rib lines and outline
CUT = (70, 20, 0)          # the carved edge of each opening
STEM = (70, 120, 25)
STEM_DARK = (40, 75, 15)


def draw_body():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    # Five overlapping lobes read as a ribbed pumpkin; drawn outer-first so the
    # middle lobe sits on top.
    lobes = [(-18, 14), (18, 14), (-9, 17), (9, 17), (0, 18)]
    for dx, hw in lobes:
        d.ellipse((CX + dx - hw, CY - RY, CX + dx + hw, CY + RY), fill=ORANGE, outline=RIB)
    # Stem: a short, slightly leaning block with a darker side.
    d.polygon([(CX - 3, CY - RY + 2), (CX + 3, CY - RY + 2), (CX + 5, CY - RY - 7),
               (CX, CY - RY - 8)], fill=STEM)
    d.line([(CX + 3, CY - RY + 2), (CX + 5, CY - RY - 7)], fill=STEM_DARK)
    # A curl of vine off the stem.
    d.arc((CX + 4, CY - RY - 8, CX + 14, CY - RY + 1), 180, 330, fill=STEM)
    return img


def face_polys():
    """Carved openings: two triangle eyes, a triangle nose, a jagged grin."""
    eye_y = CY - 8
    left = [(CX - 17, eye_y + 6), (CX - 6, eye_y + 6), (CX - 11, eye_y - 3)]
    right = [(CX + 6, eye_y + 6), (CX + 17, eye_y + 6), (CX + 11, eye_y - 3)]
    nose = [(CX - 3, CY + 4), (CX + 3, CY + 4), (CX, CY)]
    my = CY + 8
    mouth = [(CX - 20, my), (CX - 14, my + 2), (CX - 11, my - 1), (CX - 7, my + 3),
             (CX - 3, my), (CX + 1, my + 3), (CX + 5, my), (CX + 9, my + 3),
             (CX + 12, my - 1), (CX + 15, my + 2), (CX + 20, my),
             (CX + 15, my + 9), (CX + 8, my + 7), (CX + 4, my + 10),
             (CX - 1, my + 7), (CX - 6, my + 10), (CX - 10, my + 7), (CX - 15, my + 9)]
    return [left, right, nose, mouth]


def flicker(t):
    """Candle brightness in ~[0.55, 1.0]: integer harmonics -> loops at t=2pi."""
    v = (0.5 * math.sin(3 * t) + 0.3 * math.sin(7 * t + 1.3)
         + 0.2 * math.sin(13 * t + 2.1))
    return 0.775 + 0.225 * v


body = draw_body()
faces = face_polys()

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    b = flicker(t)
    img = body.copy()
    d = ImageDraw.Draw(img)
    # Inner glow: a deep-orange rim with a bright yellow core, both scaled by the
    # flicker, so the openings look lit from inside rather than painted.
    rim = (int(255 * b), int(175 * b), int(20 * b))
    core = (255, int(245 * b), int(150 * b))
    for poly in faces:   # dark cut edge keeps the glow from blending into the rind
        d.polygon(poly, fill=rim, outline=CUT)
    for poly in faces[:3]:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        d.polygon([(cx + (x - cx) * 0.5, cy + (y - cy) * 0.5) for x, y in poly], fill=core)
    d.line([(CX - 13, CY + 12), (CX + 13, CY + 12)], fill=core)   # bright seam in the grin
    # Ground glow: a dim warm smear under the pumpkin, breathing with the candle.
    gy = CY + RY + 1
    for x in range(CX - RX - 6, CX + RX + 7):
        fall = max(0.0, 1 - abs(x - CX) / (RX + 6)) ** 1.5
        for y in range(gy, min(gy + 3, H)):
            g = fall * b * (1 - (y - gy) / 3) * 0.45
            if g > 0.03:
                img.putpixel((x, y), (int(200 * g), int(80 * g), 0))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=70, loop=0)
print(f"wrote {OUT} ({N} frames)")
