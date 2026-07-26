# LED Matrix Runbook — 128x64 P2 + Matrix Bonnet + Pi 3 A+

Working configuration and rebuild procedure. Keep this in the repo root
(`~/rpi-rgb-led-matrix/`) so it survives a reflash of the SD card.

---

## Hardware

| Item | Detail |
|---|---|
| Panel | Adafruit 128x64 RGB LED Matrix, 2mm pitch |
| Addressing | 5-address (ABCDE), 1:32 scan — **not** a 4-address panel |
| Adapter | Adafruit RGB Matrix Bonnet |
| Pi | Raspberry Pi 3 Model A+ (512MB RAM — matters, see Build) |
| E jumper | Center pad bridged to **8** (correct; selects HUB75 pin 8) |
| PWM mod | Not installed (no GPIO4→18 jumper) → use `adafruit-hat` |
| Power | Separate 5V supply, 4A minimum, into the bonnet's DC jack |

Bonnet GPIO map (per Adafruit):

```
A=22  B=26  C=27  D=20  E=24        (address lines)
R1=5  G1=13 B1=6  R2=12 G2=16 B2=23 (data lines)
OE=4  CLK=17 LAT=21                 (control)
```

---

## THE E-LINE (verify, don't blindly patch)

This 64-tall panel needs the 5th address line (E). The bonnet routes E through
the **address-E solder jumper → bridge the center pad to "8"** (HUB75 pin 8),
and on the Pi that lands on **GPIO 24**.

**Stock hzeller `adafruit-hat` already drives E on GPIO 24 — a fresh clone is
correct out of the box.** Verify it, don't assume it needs editing:

```bash
cd ~/rpi-rgb-led-matrix
grep -n -A11 '"adafruit-hat"' lib/hardware-mapping.c | grep '\.e '
# Expect:  .e  = GPIO_BIT(24),  /* Needs manual wiring, see README.md */
```

If — and only if — that reads `GPIO_BIT(8)` (e.g. from a bad local edit), the
address bus is only 4 bits, addresses 0–15 are reached, and the panel shows
**16 rows lit / 16 dark, repeating**. Restore it to 24 on both `adafruit-hat`
and `adafruit-hat-pwm` (leave `regular`=15 and `compute-module`=6 alone):

```bash
sed -i '/\.e /s/GPIO_BIT(8)/GPIO_BIT(24)/' lib/hardware-mapping.c   # only touches lines set to 8
sed -n '83p;107p' lib/hardware-mapping.c                            # both must read GPIO_BIT(24)
```

Confirm the library is actually driving all five lines with the included tool
(all of A–E should read `OUTPUT  levels seen: [0, 1]`):

```bash
sudo -E ./check-address-lines.py
```

---

## Build

Two Pi 3 A+ specific constraints:

- **Disable LTO.** The `g++ -shared -flto=2` link step re-optimizes every object
  at once. On 512MB it swaps for 5–15 minutes with no output and looks hung.
- **Cap parallelism at 2.** `-j4` will OOM.

```bash
cd ~/rpi-rgb-led-matrix
make LTO_FLAGS= -j2
```

Never Ctrl-C the link — make deletes `librgbmatrix.a` on interrupt and you
start over. If you do interrupt it, just re-run the same command.

Confirm a fresh binary:

```bash
ls -l examples-api-use/demo   # timestamp should be from just now
```

Optional extras:

```bash
sudo apt install libgraphicsmagick++-dev libwebp-dev   # enables led-image-viewer
```

---

## Known-good run command

```bash
cd ~/rpi-rgb-led-matrix/examples-api-use
sudo ./demo -D5 \
  --led-rows=64 --led-cols=128 --led-chain=1 \
  --led-gpio-mapping=adafruit-hat \
  --led-slowdown-gpio=2 --led-brightness=40
```

`--led-multiplexing=0`, `--led-row-addr-type=0`, and `--led-scan-mode=0` are all
defaults and can be omitted. Root is required for GPIO access.

Demos worth knowing: `-D0` rotating square, `-D3` plain square, `-D5` grayscale
block (best for spotting dark bands), `-D7` game of life.

---

## Tuning

Run `./tune-slowdown.sh` — it sweeps `--led-slowdown-gpio` 0 through 4, shows
the measured refresh rate for each, and reports the lowest clean value.

Lower slowdown = higher refresh. Start there, then if refresh is still low
(16,384 pixels on one chain is near the practical limit for a single chain):

| Flag | Effect |
|---|---|
| `--led-pwm-bits=8` | Fewer color steps, faster refresh (default 11) |
| `--led-pwm-lsb-nanoseconds=100` | Shortens the shortest PWM pulse |
| `--led-pwm-dither-bits=1` | Trades a little noise for speed |
| `--led-show-refresh` | Prints live refresh rate — use while tuning |

If brightness collapses or colors shift when a lot of the panel is lit, that's
the power supply, not the config. The panel can draw ~4A on its own.

---

## Diagnostics

### Symptom → cause

Address lines select one of 32 row-pairs (row *r* and *r+32* light together),
address = A·1 + B·2 + C·4 + D·8 + E·16. A dead bit blanks every row whose
address needs it, producing a fixed stripe period:

| Lit/dark band height | Dead line | GPIO | HUB75 pin |
|---|---|---|---|
| 1 on, 1 off | A | 22 | 9 |
| 2 on, 2 off | B | 26 | 10 |
| 4 on, 4 off | C | 27 | 11 |
| 8 on, 8 off | D | 20 | 12 |
| 16 on, 16 off | **E** | 24 | 8 |

Confirming check: dark bands in rows 0–31 should mirror rows 32–63 exactly.
If the halves differ, it's a data line (R2/G2/B2), not an address line.

Other patterns:

- Left 64 columns only, or image duplicated → try `--led-cols=64 --led-chain=2`
- Flicker, garbage, moving artifacts → raise `--led-slowdown-gpio`
- Dim / collapsing under load → power supply

### Is the library driving the address pins?

`./check-address-lines.py` dumps the GPIO function and observed levels for
A–E while the demo runs. All five should read `OUTPUT` with `levels seen:
[0, 1]`. An `INPUT` or a stuck `[0]` means the library isn't driving that pin —
that's the signature of the GPIO 8 vs 24 bug above.

### Is a pin electrically connected to the panel?

Run the panel as 32 rows (library uses A–D only, leaves E alone), then drive
GPIO 24 by hand. Content should jump 16 rows between HIGH and LOW:

```bash
cd ~/rpi-rgb-led-matrix/examples-api-use
sudo ./demo -D3 --led-rows=32 --led-cols=128 \
  --led-gpio-mapping=adafruit-hat --led-slowdown-gpio=2 --led-brightness=40 &
sleep 3
sudo python3 - <<'EOF'
from gpiozero import LED
import time
e = LED(24)
for _ in range(6):
    e.on();  print("E HIGH", flush=True); time.sleep(2)
    e.off(); print("E LOW ", flush=True); time.sleep(2)
e.off(); e.close()
EOF
sudo pkill -f "examples-api-use/demo"
```

Image moves → wiring is fine, problem is in software.
Image doesn't move → solder joint, ribbon, or wrong pad (try 16 instead of 8).

---

## Python bindings

```bash
python3 -m venv ~/rgbmatrix --system-site-packages
source ~/rgbmatrix/bin/activate
cd ~/rpi-rgb-led-matrix && make LTO_FLAGS= install-python
```

Run scripts with root while preserving the venv:

```bash
sudo -E env PATH=$PATH python3 yourscript.py
```

Minimal example:

```python
from rgbmatrix import RGBMatrix, RGBMatrixOptions

o = RGBMatrixOptions()
o.rows, o.cols = 64, 128
o.chain_length, o.parallel = 1, 1
o.hardware_mapping = 'adafruit-hat'
o.gpio_slowdown = 2
o.brightness = 40

m = RGBMatrix(options=o)
c = m.CreateFrameCanvas()
c.Fill(255, 255, 255)
m.SwapOnVSync(c)
```

Note the Python bindings link against the **built library**, so re-run
`make LTO_FLAGS= install-python` after any change to `hardware-mapping.c`.

---

## Environment gotchas

- **Audio must be off.** `dtparam=audio=off` in `/boot/firmware/config.txt`
  (already set). The library's PWM conflicts with `snd_bcm2835`.
- **1-Wire conflicts with GPIO 4 (OE).** If you ever enable it, relocate:
  `dtoverlay=w1-gpio gpiopin=19`.
- **Free GPIOs on the bonnet:** SCL, SDA, RX, TX, 25, MOSI, MISO, SCLK, CE0,
  CE1, 19. Plus 18 (no PWM mod). GPIO 24 is now in use for E.
- **Don't overclock.** Causes visual glitches on the matrix.
- **Bracketed paste** mangles multi-line pastes into this shell (`^[[200~`
  prefix, stray trailing `~`). Disable per session: `printf '\e[?2004l'`
- **Ribbon goes in the panel's INPUT connector** — arrows point INPUT → OUTPUT.

---

## What actually fixed it (history)

For the record, the panel is driven correctly by **stock** hzeller with
`--led-gpio-mapping=adafruit-hat` and all defaults — no library patch required.
The real requirements were:

1. **Solder** the address-E jumper (center pad → "8") so the 64-tall panel's
   E line reaches GPIO 24. Without it: only half the rows light.
2. **Build cleanly** on the 512MB Pi (LTO off, `-j2`, swap enabled). OOM-killed
   builds left broken/partial binaries that produced misleading symptoms.
3. **Match `panel.py` to the working config** (adafruit-hat, multiplexing 0,
   defaults). FM6126A init is NOT needed once E works.

The long detour through "multiplexing sweeps" was chasing a symptom created by
an incorrect local edit that set E to GPIO 8; reverting to the stock GPIO 24
plus a clean rebuild resolved it.
