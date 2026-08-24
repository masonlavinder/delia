#!/usr/bin/env python3
"""Generate assets/snoopy.gif — an original pixel-art beagle asleep on the roof
of his red doghouse, breathing slowly, with Zs drifting up. Regenerate:
    python3 tools/make_snoopy_gif.py

Drawn from primitives rather than a source image: at 128x64 every pixel counts,
and the shapes are the only thing that survives at this size. Most of the panel
stays black (unlit) — only the house and the dog draw current.
"""
import math
import os

from PIL import Image, ImageDraw

W, H, N = 128, 64, 48
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "snoopy.gif")
)

WHITE = (255, 255, 255)
INK = (0, 0, 0)               # his markings: black on a black panel = unlit
ROOF = (210, 30, 30)
WALL = (170, 20, 20)
DOOR = (0, 0, 0)

# House. The peak is flattened into a shelf wide enough for the whole dog to lie
# on it: every black marking he has (nose, eye, ear) needs LIT pixels behind it,
# or it disappears into the panel.
RIDGE_Y, EAVE_Y, FLOOR_Y = 30, 44, 63
RIDGE_L, RIDGE_R = 34, 90
EAVE_L, EAVE_R = 26, 102
WALL_L, WALL_R = 34, 94


# A 3x6 pixel font — only the letters the house needs. Same reason as the Z
# below: a real font has nothing legible to give at this size. Six rows, not
# five, because lowercase needs somewhere to put the descenders on p and y.
GLYPHS = {
    "d": ("..#", "..#", "###", "#.#", "###", "..."),
    "o": ("...", "...", "###", "#.#", "###", "..."),
    "p": ("...", "...", "###", "#.#", "###", "#.."),
    "y": ("...", "...", "#.#", "#.#", ".##", "##."),
}
WORD = "doopy"


def draw_word(d, word, x, y, scale, fill):
    """Blit WORD at `scale`, one glyph box per letter plus a 1px gap."""
    for ch in word:
        for r, row in enumerate(GLYPHS[ch]):
            for c, on in enumerate(row):
                if on == "#":
                    d.rectangle([x + c * scale, y + r * scale,
                                 x + (c + 1) * scale - 1, y + (r + 1) * scale - 1], fill=fill)
        x += 4 * scale


def draw_house(d):
    d.rectangle([WALL_L, EAVE_Y, WALL_R, FLOOR_Y], fill=WALL)
    d.polygon([(RIDGE_L, RIDGE_Y), (RIDGE_R, RIDGE_Y),
               (EAVE_R, EAVE_Y), (EAVE_L, EAVE_Y)], fill=ROOF)
    # nameplate, centred on the front: 5 letters at scale 2 = 38px wide, so it
    # starts 19px left of the house's centre line.
    draw_word(d, WORD, (WALL_L + WALL_R) // 2 - 19, 50, 2, INK)


def draw_dog(d, lift):
    """On his back on the roof, head left, legs in the air — the pose everyone
    knows. `lift` is the breathing offset (0 or 1 px) on the torso alone; the
    head, legs and tail stay put, so it reads as a ribcage rather than the whole
    dog twitching.

    Shapes are left a pixel apart wherever two white ones meet. The panel is
    black, so that gap IS the line between them — it is the whole reason he
    doesn't read as one long blob.
    """
    base = RIDGE_Y + 1                 # a pixel into the roof: no gap under him

    # The body is a run of four sections along the roof, roughly to these
    # proportions (h x w): neck 10x5, belly 20x20 domed, leg 10x10, foot 20x5.
    # Every one of them stands ON the roof, so the foot reaches the base like
    # the rest of him rather than floating at the end.
    d.rectangle([45, 23, 53, base], fill=WHITE)                   # neck: low, narrow
    d.ellipse([53, 15 - lift, 73, base], fill=WHITE)              # belly: domed, the
                                                                  # part that breathes
    d.rectangle([53, 23, 73, base], fill=WHITE)                   # ...on a square base:
    # an ellipse narrows at the bottom, which would leave a red notch either
    # side where the belly meets the neck and the leg.
    d.rectangle([73, 23, 83, base], fill=WHITE)                   # leg: back down
    d.rectangle([83, 18, 87, base], fill=WHITE)                   # foot: tall, narrow
    d.ellipse([83, 14, 87, 22], fill=WHITE)                       # rounded off on top

    # head: a circle, with the muzzle as a smaller circle offset UP off it —
    # he is on his back, so the muzzle is the one part aimed at the sky.
    d.ellipse([33, 13, 51, 31], fill=WHITE)                      # head
    d.ellipse([39, 5, 49, 17], fill=WHITE)                       # muzzle
    d.ellipse([42, 6, 47, 11], fill=INK)                         # nose, at its tip
    d.line([(40, 20), (40, 24)], fill=INK)                       # eye, a shut vertical slit

    # ear: droops off the back of his head onto the red roof, which is what
    # gives it a lit background to be seen against
    d.ellipse([41, 26, 49, 40], fill=INK)

# A Z, as a bitmap — a font would be illegible at this size.
Z_GLYPH = ("11111", "...1.", "..1..", ".1...", "11111")


def draw_z(img, x, y, scale, level):
    col = (int(120 * level), int(140 * level), int(220 * level))
    if max(col) < 12:
        return
    for r, row in enumerate(Z_GLYPH):
        for c, on in enumerate(row):
            if on == "1":
                for dy in range(scale):
                    for dx in range(scale):
                        px, py = x + c * scale + dx, y + r * scale + dy
                        if 0 <= px < W and 0 <= py < H:
                            img.putpixel((px, py), col)


frames = []
for f in range(N):
    t = f / N
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_house(d)
    draw_dog(d, 1 if math.sin(2 * math.pi * t) > 0 else 0)
    # Zs on one shared cycle, half a phase apart -> a steady stream that loops
    # seamlessly (each is a pure function of its own phase). They rise and grow,
    # and stay left of his head, which is the only clear sky on the panel.
    for i in range(2):
        p = (t + i / 2) % 1.0
        draw_z(img, 5 + int(13 * p), 13 - int(13 * p),
               2 if p > 0.5 else 1, math.sin(math.pi * p) ** 0.6)
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=125, loop=0)
print(f"wrote {OUT} ({N} frames)")
