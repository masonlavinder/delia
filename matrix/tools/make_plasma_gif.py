#!/usr/bin/env python3
"""Generate assets/plasma.gif — a seamlessly-looping, smoothly-gradated purple
plasma. Regenerate:  python3 tools/make_plasma_gif.py
"""
import math
import os

from PIL import Image

W, H, N = 128, 64, 60   # more frames -> smoother motion; t does one 2*pi cycle -> seamless loop
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "plasma.gif")
)

frames = []
for f in range(N):
    t = 2 * math.pi * f / N
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            # broad wavelengths -> smooth, gradated field (no harsh transitions)
            v = (
                math.sin(x / 22.0 + t)
                + math.sin(y / 18.0 - t)
                + math.sin((x + y) / 30.0 + t)
                + math.sin(math.hypot(x - W / 2, y - H / 2) / 18.0 - t)
            )
            n = (v + 4) / 8.0        # 0..1, smooth field
            # Dim regions fall to TRUE black (fewer lit pixels -> less current ->
            # less power-sag), with a smooth ramp so there's no hard edge.
            g0 = max(0.0, (n - 0.4) / 0.6)   # 0 below 0.4, 0..1 above
            glow = g0 * g0                   # ease in -> smooth glow, ~40%+ black
            r = int(210 * glow)
            g = int(60 * glow * n)           # keep green low -> stays purple
            b = int(230 * glow)
            px[x, y] = (min(r, 255), min(g, 255), min(b, 255))
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
# GIF is limited to 256 colors. Use ONE shared palette (from a frame; every
# frame uses the same purple ramp) and NO dithering, so the pattern is stable
# frame-to-frame -> no "dither crawl" flicker. 256 levels is plenty for this ramp.
pal = frames[0].quantize(colors=256, dither=Image.Dither.NONE)
pframes = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
pframes[0].save(OUT, save_all=True, append_images=pframes[1:], duration=90, loop=0)
print(f"wrote {OUT} ({N} frames, stable palette)")
