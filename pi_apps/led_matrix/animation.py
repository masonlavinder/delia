"""Play an animated GIF on the panel, scaled to fill the 128x64 display.

Drop a .gif into this folder, then pass its filename.

Run:  cd ~/delia/pi_apps/led_matrix && sudo python3 animation.py mygif.gif
Stop: Ctrl-C
"""
import sys
import time
from PIL import Image
from panel import build_matrix

path = sys.argv[1] if len(sys.argv) > 1 else "sample.gif"
matrix = build_matrix(brightness=50)
gif = Image.open(path)

# Pre-render every frame to the panel size so playback is smooth.
frames = []
try:
    while True:
        frame = gif.copy().convert("RGB").resize((matrix.width, matrix.height))
        frames.append(frame)
        gif.seek(gif.tell() + 1)
except EOFError:
    pass

print(f"Loaded {len(frames)} frames from {path}")

try:
    while True:
        for frame in frames:
            matrix.SetImage(frame)
            time.sleep(0.1)   # ~10 fps; tune to taste
except KeyboardInterrupt:
    matrix.Clear()
