# LED Matrix — Adafruit 128x64 RGB panel on a Pi 3 A+

Drive an Adafruit **128x64 RGB LED Matrix (HUB75, 2mm pitch)** from a
Raspberry Pi 3 A+ using the **Adafruit RGB Matrix Bonnet**. Starter scenes
included: a first-light test, a live weather display, and a GIF animation player.

---

## ⭐ READ THIS FIRST (so we never repeat the 4-hour debug)

**It works. This is the known-good state — don't "fix" what isn't broken.**

**Working config** (already in `core/panel.py`):
`hardware_mapping='adafruit-hat'`, `rows=64`, `cols=128`, `multiplexing=0`,
`row_address_type=0`, `gpio_slowdown=2`. **No FM6126A. No custom multiplexing.**
Stock `rpi-rgb-led-matrix` — the E address line is GPIO 24 out of the box (no
library patch on a fresh clone).

**The ONE hardware requirement:** the **address-E jumper must be soldered** on the
bonnet (center pad → `8`). That routes the 64-tall panel's E line to GPIO 24.

**If the panel bands / only lights part of the screen, in priority order:**
1. **It is the E line, NOT multiplexing.** Do **not** sweep multiplexing/row-addr
   values — that was a dead-end rabbit hole. Run `sudo -E ./check-address-lines.py`
   (in `~/rpi-rgb-led-matrix/`): all of A–E must show `OUTPUT levels [0,1]`.
   16-on/16-off banding = E dead → check the solder joint and that
   `lib/hardware-mapping.c` `adafruit-hat` reads `GPIO_BIT(24)`.
2. **A broken build looks like a panel bug.** On this 512MB Pi the build OOMs
   unless you enable swap and disable LTO — see the runbook. Rebuild cleanly
   before blaming the config.
3. **The Pi's files must match the repo.** After editing locally, copy over
   (`rsync -az … mlavinder@delia-pi.local:~/delia/pi_apps/led_matrix/`).

**Full build/repair procedure:** **[led-matrix-setup.md](led-matrix-setup.md)** —
read it before touching anything if the panel misbehaves or you reflash the card.

---

> Prerequisite: the Pi is set up and you can SSH into it. If not, do
> [`../bootstrap`](../bootstrap/README.md) first.

## Hardware checklist

- [x] Raspberry Pi 3 A+ (Raspberry Pi OS Lite)
- [x] Adafruit RGB Matrix Bonnet (snapped onto the Pi's 40-pin header)
- [x] 128x64 RGB LED matrix panel + its HUB75 ribbon cable
- [x] Separate **5V power supply, 4A minimum** (5A+ gives headroom)

### ⚠️ REQUIRED: solder the address-E jumper on the Bonnet

This panel (Adafruit 6484) is 64 pixels tall and uses a **non-standard 5-address
(ABCDE) multiplexing** scheme. The Bonnet does **not** connect the E address line
by default, so out of the box the panel can only drive half its rows — you get
banding / "every other row missing". You must:

- Flip the Bonnet over, find the **address-E solder jumper**: three pads labeled
  `8` — `E` (middle) — `16`.
- **Bridge the middle `E` pad to the `8` pad** with a blob of solder.
  (Adafruit panels use `8`; this matches `hardware_mapping='adafruit-hat'`.)

This is separate from (and unrelated to) the optional GPIO4↔GPIO18 PWM jumper.

Software side (already set in `panel.py`): `hardware_mapping='adafruit-hat'`
(stock hzeller drives E on **GPIO 24** — where the "8" solder pad lands),
rows=64, cols=128, multiplexing=0, row_address_type=0. No FM6126A init needed.

> ✅ **WORKING CONFIG CONFIRMED** — the full 128x64 panel lights cleanly.
> The authoritative build/repair procedure is **[led-matrix-setup.md](led-matrix-setup.md)**
> — read that if you ever reflash the SD card or the panel misbehaves.

### ⚠️ Power — read this first

- Plug the **5V supply into the Bonnet's screw terminals** (watch polarity: + and −).
  The Bonnet feeds 5V to **both the panel and the Pi** through the header, so with
  a beefy enough supply you may not need to plug the Pi's micro-USB in at all.
- **Use only ONE power source at a time.** Don't power the Pi from its micro-USB
  *and* the Bonnet simultaneously — pick one to avoid back-feeding.
- Connect the panel's **HUB75 ribbon** to the Bonnet's output, and the panel's
  **power leads to the Bonnet's screw terminals** too (per Adafruit's panel guide).
- Start scenes at **low brightness**. Full white on 8,192 LEDs is the peak current draw.

## Step 1 — Attach hardware (Pi powered OFF)

1. Seat the Bonnet firmly on all 40 GPIO pins.
2. Connect the panel's ribbon cable to the Bonnet (note the arrow / input side on the panel).
3. Wire the panel + Bonnet power to your 5V supply as above.

## Step 2 — Install the Adafruit RGB matrix library

SSH into the Pi, then:

```bash
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh >rgb-matrix.sh
sudo bash rgb-matrix.sh
```

The installer will ask a couple of questions:

- **Interface board type** → choose **Adafruit RGB Matrix Bonnet**.
- **Quality vs convenience** → for now choose the simple option that keeps you
  off the soldering iron. It will **disable the onboard sound** (required — the
  audio hardware conflicts with the panel's timing). That's expected.
  - If it mentions a **GPIO4↔GPIO18 solder jumper**: you can skip that today.
    Soldering it later + switching `hardware_mapping` to `'adafruit-hat-pwm'`
    in `panel.py` gives noticeably smoother, flicker-free output.

Let it build, then **reboot** when it asks:

```bash
sudo reboot
```

This installs the `rgbmatrix` Python module system-wide and clones the library
(with fonts + examples) into `~/rpi-rgb-led-matrix`.

## Step 3 — Install Python deps + get this code onto the Pi

```bash
sudo apt install -y git python3-pil python3-requests
git clone <your delia repo URL> ~/delia      # or copy the folder over
cd ~/delia/pi_apps/led_matrix
```

## Layout

```
led_matrix/
├── run.sh                  ← launcher: ./run.sh <scene> (handles sudo + paths)
├── config.example.py       ← copy to config.py (gitignored), set your location
├── core/
│   └── panel.py            ← build_matrix() + load_font(); the ONE place for panel config
├── scenes/
│   ├── everyday/           ← always-on info: weather, clock, …
│   │   ├── weather.py
│   │   └── clock.py
│   ├── party/              ← fun/animations
│   │   └── gif.py          ← plays a GIF (drop .gif files in this folder)
│   └── scratch/            ← experiments / WIP
│       └── hello.py        ← first-light color test
├── diagnostics/            ← troubleshooting tools (see led-matrix-setup.md)
│   ├── check-address-lines.py
│   ├── tune-slowdown.sh
│   └── diag.py
├── led-matrix-setup.md     ← the runbook (read if the panel ever misbehaves)
└── requirements.txt
```

## Running scenes

Use the launcher (it adds `sudo` + the right import paths):

```bash
cd ~/delia/pi_apps/led_matrix
./run.sh                     # lists all scenes
./run.sh scratch/hello       # first-light color test
./run.sh everyday/weather    # current temperature
./run.sh everyday/clock      # time + date
./run.sh party/gif cool.gif  # play scenes/party/cool.gif
```

`Ctrl-C` stops any scene. First time, set your location:

```bash
cp config.example.py config.py && nano config.py   # LAT / LON / units
```

**Adding a scene:** drop a `.py` in the matching `scenes/<group>/` folder,
start it with the 3-line header from any existing scene (it imports
`build_matrix`/`load_font` from `core.panel`), and run it with `./run.sh <group>/<name>`.

## Run a scene automatically on boot (optional, later)

Once a scene is the one you want always running, make a systemd service so it
starts on boot and restarts if it crashes. Ask and I'll generate the unit file.

## Troubleshooting

| Symptom | Try |
|---|---|
| Flicker / tearing | Solder the GPIO4↔GPIO18 jumper, set `hardware_mapping='adafruit-hat-pwm'`. Or raise `gpio_slowdown`. |
| Garbled / wrong pixels | In `panel.py` try `options.multiplexing = 1` (or 2), and/or `gpio_slowdown = 3`. |
| Random crashes / brownouts | Power problem — bigger 5V supply, and make sure you're not double-powering the Pi. |
| `ModuleNotFoundError: rgbmatrix` | The Adafruit installer (step 2) didn't finish, or you didn't reboot. |
| Colors look dim/washed | Raise `brightness` in the scene (watch current draw). |

Reference: Adafruit "RGB Matrix Bonnet" guide and the underlying
[hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) docs.
