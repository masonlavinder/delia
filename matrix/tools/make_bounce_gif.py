#!/usr/bin/env python3
"""Generate assets/bounce.gif — the old screensaver: a solid block drifting
across a black panel, changing colour on every wall, never landing in a corner.
Regenerate:
    python3 tools/make_bounce_gif.py

Random physics and a seamless loop pull against each other: a random walk never
returns to where it started, so it cannot loop. The way out is to make the
"randomness" a pure function of the state rather than a stream of random
numbers. Speed and colour after a bounce come from a hash of (position,
velocity, colour), so the whole thing is a deterministic finite state machine —
and a finite state machine MUST eventually revisit a state.

So: simulate, watch for the first repeated state, and emit exactly the frames
between the two visits. That run is a true cycle, so the GIF loops with no seam
while the bouncing inside it never repeats.

With these constants the cycle is ~324 frames (about 27s at 12fps) and the block
takes a different angle off nearly every wall — at one unchanging speed. Change
SPEEDS or START and the cycle length moves wildly (60 frames for one nearby
setting, 3844 for another), so re-check the printed length after any edit.

The corner is safe for free here: reaching one needs a frame where the block is
flush against a vertical AND a horizontal wall, and the emitted cycle is checked
for that below.
"""
import math
import os

from PIL import Image, ImageDraw

W, H = 128, 64
BW, BH = 16, 10                     # the block
LX, LY = W - BW, H - BH
# A bounce swaps the axis speeds as a PAIR, never picks them independently.
# Drawing each axis separately allowed (1,1) and (3,3), i.e. |v| between 1.4 and
# 4.2 — the block visibly crawled, then raced. Swapping a fixed pair keeps
# |v| = sqrt(1^2 + 2^2) = 2.24 px/frame whatever direction it takes. At the 12fps
# the scene asks for, that is 27 px/s — half the old pace. Half the speed is
# split between a smaller step and a slower frame rate on purpose: dropping fps
# alone would leave 3.6px jumps, which read as stutter rather than slowness.
SPEEDS = ((1, 2), (2, 1))
START = (11, 3, 1, 2, 0)            # x, y, vx, vy, colour index — vx,vy from SPEEDS
LIMIT = 20000                       # give up if no cycle turns up by here

OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "bounce.gif")
)

PALETTE = [(255, 70, 70), (70, 230, 130), (90, 150, 255),
           (255, 210, 60), (220, 90, 255)]


def h32(*vals):
    """FNV-1a. Any cheap hash works; it only has to be deterministic, since it
    is what stands in for randomness."""
    h = 2166136261
    for v in vals:
        h = ((h ^ (int(v) & 0xffffffff)) * 16777619) & 0xffffffff
    return h


def simulate():
    """Walk the state machine until a state repeats; return the cycle."""
    x, y, vx, vy, ci = START
    seen, path = {}, []
    for i in range(LIMIT):
        state = (x, y, vx, vy, ci)
        if state in seen:
            return path[seen[state]:]
        seen[state] = i
        path.append(state)

        nx, ny = x + vx, y + vy
        bounced = False
        if not 0 <= nx <= LX:
            vx = -vx
            nx = x + vx
            bounced = True
        if not 0 <= ny <= LY:
            vy = -vy
            ny = y + vy
            bounced = True
        if bounced:
            # new speed and colour, both drawn from the state itself
            hh = h32(x, y, vx, vy, ci)
            mx, my = SPEEDS[hh % len(SPEEDS)]
            vx = (1 if vx > 0 else -1) * mx
            vy = (1 if vy > 0 else -1) * my
            ci = (ci + 1 + (hh >> 16) % (len(PALETTE) - 1)) % len(PALETTE)
        x, y = nx, ny
    raise RuntimeError(f"no cycle within {LIMIT} frames — change SPEEDS or START")


cycle = simulate()

corners = [(x, y) for x, y, *_ in cycle
           if x in (0, LX) and y in (0, LY)]
if corners:
    raise RuntimeError(f"the block lands in a corner at {corners} — that spoils the joke")

speeds = {round(math.hypot(vx, vy), 3) for _x, _y, vx, vy, _ci in cycle}
if len(speeds) != 1:
    raise RuntimeError(f"speed is not constant across the loop: {sorted(speeds)}")

frames = []
for x, y, _vx, _vy, ci in cycle:
    img = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(img).rectangle([x, y, x + BW - 1, y + BH - 1], fill=PALETTE[ci])
    frames.append(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=83, loop=0)
print(f"wrote {OUT} ({len(frames)} frames, {len(frames) * 83 / 1000:.1f}s at 12fps)")
