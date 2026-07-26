#!/usr/bin/env python3
"""
Check whether the library is actually driving the A-E address lines.

Starts the demo, samples the BCM2835 GPIO registers directly, and reports the
function select and observed levels for each address pin.

    sudo ./check-address-lines.py

Healthy output: all five lines OUTPUT with levels [0, 1].

  A (GPIO 22): OUTPUT  levels seen: [0, 1]
  B (GPIO 26): OUTPUT  levels seen: [0, 1]
  C (GPIO 27): OUTPUT  levels seen: [0, 1]
  D (GPIO 20): OUTPUT  levels seen: [0, 1]
  E (GPIO 24): OUTPUT  levels seen: [0, 1]

An INPUT, or a pin stuck at [0], means the library never claims or never
asserts it. For E specifically that is the GPIO 8 vs GPIO 24 mapping bug --
see the CRITICAL FIX section of led-matrix-setup.md.

Pi 4 and earlier only; the Pi 5 uses a different GPIO controller (RP1).
"""

import mmap
import os
import struct
import subprocess
import sys
import time

FUNCS = {0: "INPUT", 1: "OUTPUT", 2: "ALT5", 3: "ALT4",
         4: "ALT0", 5: "ALT1", 6: "ALT2", 7: "ALT3"}

# Adafruit RGB Matrix Bonnet address lines
PINS = [("A", 22), ("B", 26), ("C", 27), ("D", 20), ("E", 24)]

# Resolve the demo relative to this script (works under plain `sudo`, where
# ~ would otherwise expand to /root).
_HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(_HERE, "examples-api-use", "demo")
if not os.path.isfile(DEMO):  # fall back to the invoking user's home
    _home = os.path.expanduser("~" + (os.environ.get("SUDO_USER") or ""))
    DEMO = os.path.join(_home, "rpi-rgb-led-matrix", "examples-api-use", "demo")
DEMO_ARGS = [
    "-D5",
    "--led-rows=64", "--led-cols=128", "--led-chain=1",
    "--led-gpio-mapping=adafruit-hat",
    "--led-slowdown-gpio=2", "--led-brightness=40",
]

GPLEV0 = 0x34   # pin level register
SAMPLES = 5000


def sample():
    """Sample levels many times, then read the function select registers."""
    fd = os.open("/dev/gpiomem", os.O_RDWR | os.O_SYNC)
    try:
        mem = mmap.mmap(fd, 4096, offset=0)
    finally:
        os.close(fd)

    def rd(off):
        return struct.unpack("<I", mem[off:off + 4])[0]

    seen = {name: set() for name, _ in PINS}
    for _ in range(SAMPLES):
        lev = rd(GPLEV0)
        for name, pin in PINS:
            seen[name].add((lev >> pin) & 1)

    modes = {}
    for name, pin in PINS:
        modes[name] = (rd((pin // 10) * 4) >> ((pin % 10) * 3)) & 7

    mem.close()
    return seen, modes


def main():
    if os.geteuid() != 0:
        sys.exit("Needs root:  sudo ./check-address-lines.py")

    if not os.path.isfile(DEMO):
        sys.exit(f"No demo binary at {DEMO}\n"
                 "Build it:  cd ~/rpi-rgb-led-matrix && make LTO_FLAGS= -j2")

    print("Starting demo...")
    proc = subprocess.Popen([DEMO] + DEMO_ARGS,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        if proc.poll() is not None:
            sys.exit("Demo exited early. Run it by hand to see the error.")

        print(f"Sampling {SAMPLES} times...\n")
        seen, modes = sample()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    problems = []
    for name, pin in PINS:
        mode = FUNCS[modes[name]]
        levels = sorted(seen[name])
        flag = ""
        if mode != "OUTPUT":
            flag = "  <-- not driven by the library"
            problems.append(name)
        elif levels != [0, 1]:
            flag = "  <-- never toggles"
            problems.append(name)
        print(f"  {name} (GPIO {pin:2d}): {mode:6s}  levels seen: {levels}{flag}")

    print()
    if not problems:
        print("All address lines healthy.")
    else:
        print(f"Problem lines: {', '.join(problems)}")
        if "E" in problems:
            print("\nE not driven is the classic 16-on/16-off stripe cause.")
            print("Check lib/hardware-mapping.c -- adafruit-hat needs")
            print("  .e = GPIO_BIT(24)   not   .e = GPIO_BIT(8)")


if __name__ == "__main__":
    main()
