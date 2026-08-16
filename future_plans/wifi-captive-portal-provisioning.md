# WiFi provisioning over a captive portal

**Status:** planned, not started.
**Goal:** join the Pi to a new WiFi network the way a smart plug does — the Pi
raises its own access point, you join it from a phone, a setup page pops up,
you pick your network and type the password, the Pi joins it and the AP
disappears.

Today the equivalent is `matrix/raspberry_pi/pi-setup/apply-wifi.sh`: edit
`wifi.conf` on a laptop, push a NetworkManager keyfile over SSH — or, when the
Pi is already unreachable, shut down, pull the SD card, mount it, and
`--write-to` the card. That works and it should keep working. This adds a path
that needs neither a laptop nor the card.

---

## 1. Is it possible on this hardware?

Yes. The Pi 3 A+'s BCM43455 supports AP mode through `brcmfmac`/`nl80211`, and
NetworkManager — already running the show on this Pi — can drive both AP mode
and shared-IP mode natively.

The one radio is not a blocker, because the flow never needs AP and client at
the same time: **be an AP → collect credentials → become a client.** (The chip
can do concurrent AP+STA via virtual interfaces, but it's unreliable and
unnecessary here. Don't.)

Two consequences worth internalising up front:

- **The moment the AP comes up, SSH dies.** There is exactly one radio. Any
  testing of this feature disconnects you from the Pi. Section 7 is about
  surviving that.
- **The AP is invisible while the Pi is happily on WiFi.** So there has to be a
  deliberate way back into provisioning mode, not only the automatic one.

---

## 2. How a captive portal actually works

There is no protocol. The "login page pops up automatically" behaviour is a
client-side heuristic: on joining a network, phones fetch a known URL whose
response they already know, and if the answer is wrong they assume a portal is
intercepting traffic and open a browser.

| Client | Probe URL | Expects |
|---|---|---|
| iOS / macOS | `captive.apple.com/hotspot-detect.html` | body containing `Success` |
| Android | `connectivitycheck.gstatic.com/generate_204` | HTTP 204, empty |
| Windows | `www.msftconnecttest.com/connecttest.txt` | body `Microsoft Connect Test` |

So the portal needs two things:

1. **Wildcard DNS** — every name resolves to the Pi, so the probes reach us at
   all.
2. **A catch-all HTTP route** that answers those probes with a `302` to the
   setup page instead of what they expect.

That's the whole trick. Nothing more exotic is involved.

---

## 3. Build vs. adopt

| Option | What it is | Why not / why |
|---|---|---|
| **Comitup** | Debian package, NetworkManager-based, does exactly this | Least work. But it owns its own NM profiles and its own naming, which collides with `wifi.conf` being the source of truth. Two systems editing `/etc/NetworkManager/system-connections/` is how the Pi goes missing. |
| **balena wifi-connect** | Single Rust binary, NM-based, arm builds | Also little work, and it exits cleanly once connected. But it's an opaque dependency, upstream activity is thin, and the UI can't render on the LED matrix or match the panel UI. |
| **Roll our own** | ~1 systemd unit, a small Flask app, a keyfile writer | **Recommended.** Every piece already exists in this repo: keyfile rendering, a Flask app, a Unix-socket privilege boundary, an installed `panel.client` for drawing on the matrix. It stays consistent with "WiFi is config-driven, not hand-typed `nmcli`", and it can print the setup SSID *on the LED panel*, which is a better onboarding story than a smart plug gets. |

Adopt if this stalls; the plan below is for building.

---

## 4. Architecture

The existing trust boundary is reused rather than reinvented. Writing an NM
keyfile is a root operation; a web form is untrusted input; the current answer
to exactly that shape of problem is a root daemon behind a `0660 root:panel`
Unix socket that re-validates everything. Do the same.

```
phone joins "delia-setup" (WPA2)
      |
      |  NetworkManager AP profile, ipv4.method=shared
      |  -> NM's own dnsmasq: DHCP + wildcard DNS at 10.42.0.1
      v
portal (unprivileged, user mlavinder, group panel, :80)
      |  Flask: scan / form / catch-all probe redirect
      |
      |--- newline-JSON -> /run/panel/net.sock   (root:panel, 0660)
      |                          |
      |                    panel-netd (root)
      |                      validate (strict Pydantic)
      |                      render keyfile -> /etc/NetworkManager/...
      |                      nmcli connection reload / up
      |
      '--- panel.client -> /run/panel/panel.sock -> renderer
                                 draws the SSID + URL on the matrix
```

**`panel-netd` does exactly one thing** and accepts exactly one message:
`{label, ssid, psk, hidden, priority}`. It never takes a path, never takes a
command, never deletes a profile it did not create in this session. The
password travels inside the socket message and then inside a `0600` file — it
is never an `nmcli` argv, because argv is world-readable in `/proc` (the same
reason `apply-wifi.sh` scp's the file instead of passing `--ask`).

### Alternative considered: polkit instead of a root helper

Add `mlavinder` to a group with a polkit rule for
`org.freedesktop.NetworkManager.settings.modify.system`, and let the portal
talk to NM directly over D-Bus with no new root code at all. Genuinely
tempting, and fewer moving parts.

Rejected as the default because it widens the standing privileges of the
account that runs the web UI — that account currently cannot do a single
privileged thing, and that property is the security model. The root helper
keeps the blast radius at one 150-line program with one message type. Revisit
if `panel-netd` turns out to be more code than expected.

---

## 5. Layout

```
matrix/raspberry_pi/provisioning/
  netd.py              root helper: socket, strict schema, keyfile write, nmcli
  keyfile.py           render an NM keyfile from validated fields  (shared)
  portal.py            Flask: scan, form, probe catch-all, status
  supervisor.py        the state machine (section 6)
  nm.py                thin NetworkManager wrapper + a `mock` for off-Pi tests
  templates/setup.html one page, no build step, no JS framework
  tests/               runs off-Pi against nm.mock
  README.md

matrix/raspberry_pi/systemd/
  panel-netd.service        root, socket-activated or always-on
  panel-provision.service   the supervisor; After=NetworkManager.service

matrix/raspberry_pi/pi-setup/
  provision.conf.example    setup-AP SSID + WPA2 password, grace periods
  delia-setup.nmconnection  the AP profile (rendered, autoconnect=false)

instructions/
  wifi-captive-portal.md    how to use it, and how to recover when it fails
```

`nm.py` mirrors `matrix/panel/backends/` — a real implementation and a mock —
so the state machine and the portal are testable with
`PANEL_BACKEND=mock`-style discipline and no GPIO, no radio, no Pi.

**Note the duplication:** `keyfile.py` renders the same file `apply-wifi.sh`
renders in bash. Don't unify them — `apply-wifi.sh` must keep working from a
laptop with no Python environment and no Pi, including against a mounted SD
card. Instead add a test that renders a fixture through both and diffs the
output, so they can't drift silently.

---

## 6. The state machine

`panel-provision.service`, ordered `After=NetworkManager.service`:

1. **Wait** up to `GRACE` (default 45s) for NM to report a wifi device with an
   IPv4 address. If it connects — exit 0, do nothing else. On a normal boot at
   home this is the entire lifetime of the service.
2. **No connection** → bring up the `delia-setup` AP profile, start the portal,
   and push a scene to the renderer showing the SSID and `http://10.42.0.1`.
3. **Portal serves** a list of scanned SSIDs (NM can scan while in AP mode on
   this chip; if that proves flaky, scan *before* raising the AP in step 2 and
   serve the cached list, plus a free-text field for hidden networks).
4. **On submit** → hand to `panel-netd` → keyfile written → AP down →
   `nmcli connection up <label>`.
5. **Verify** within 45s: associated *and* has an IP. On success, write a
   success flag and exit 0.
6. **On failure** → delete the profile just created (only that one), raise the
   AP again, redisplay the form with the actual error (bad password vs. out of
   range vs. DHCP timeout — they need different fixes and the user can't guess).

### Wildcard DNS

NM's shared mode starts its own dnsmasq. Point everything at the Pi with a
drop-in — this is the bit that makes the portal auto-pop rather than requiring
the user to type an IP:

```
# /etc/NetworkManager/dnsmasq-shared.d/captive.conf
address=/#/10.42.0.1
```

### The AP profile

Ship it as a real keyfile rather than a one-shot `nmcli device wifi hotspot`,
for the same reason `wifi.conf` exists — config, not typed commands. Key
fields: `mode=ap`, `band=bg`, `channel=6`, `ipv4.method=shared`,
**`autoconnect=false`** (so it can never come up on its own later), WPA2 with a
password from `provision.conf`.

**2.4 GHz, not 5.** The chip can do a 5 GHz AP, but it's regdomain-dependent
and some phones won't list it. This is the one network that absolutely must be
joinable.

### Binding

The portal listens on `:80`, so it doesn't collide with `panel-api` on `:8080`.
Give the unit `AmbientCapabilities=CAP_NET_BIND_SERVICE` rather than running it
as root. Bind to `10.42.0.1` specifically, so it isn't also exposed on the home
network once provisioning is done.

---

## 7. Getting back in — the part that matters

The Pi has no ethernet and reflashing the card throws away the compiled
`rpi-rgb-led-matrix` and the whole install. Every mechanism here is about not
needing the card.

**Three ways into provisioning mode:**

1. **Automatic** — no connection within `GRACE` seconds of boot. Covers the
   real case: the Pi moved, or the router's password changed.
2. **From the panel UI** — a "Re-provision WiFi" action in the web app, for
   *before* you move it: you're on the network now, you know you're about to
   lose it. Must be a deliberate, confirmed action; it disconnects the Pi.
3. **Over SSH** — `sudo systemctl start panel-provision.service --force`,
   or a flag file the supervisor checks on boot.

**Dead-man's switch.** A `systemd` timer that, unless a success flag is written
within 10 minutes of provisioning starting, restores the previous state and
reboots. This is what makes the feature safe to test at all: the worst outcome
of a bad experiment becomes "wait ten minutes", not "find a monitor".

**Never delete existing profiles.** Same rule as `apply-wifi.sh` and for the
same reason — the old profile is the only way back in. New profiles get a
distinct label (`portal-<ssid>`) so `panel-netd` can identify and roll back
exactly what it created, and so hand-managed `wifi.conf` profiles are never
touched.

**For the first end-to-end test:** have a monitor and a USB keyboard on hand.
The Pi 3 A+ has full-size HDMI and one USB-A port. The GPIO header is under the
HUB75 bonnet, so a serial console is not the easy out it usually is.

---

## 8. Security

The current model is: the socket is the boundary, and there is no app-level
auth because a VPN/tunnel is the network boundary. A provisioning AP is
different in kind — it is, deliberately, an open door on the radio.

- **WPA2 on the setup AP**, password from `provision.conf` (gitignored — note
  that `.gitignore` already ignores `*.conf` and `*.nmconnection`, so both the
  filled-in config and any rendered profile stay out of git by default).
  Without this, anyone in radio range can join the Pi to *their* network and
  walk off with it.
- **The portal is an unauthenticated write to root-owned config** for the
  duration it's up. Keep that duration short: idle timeout, and it exits the
  moment provisioning succeeds.
- **Rate-limit** submissions; a failed attempt should cost seconds.
- **Never log the PSK** — not in the portal, not in `panel-netd`, not in a
  journal line, not in an error message rendered on the panel.
- Redact it in every dry-run/debug path, the way `apply-wifi.sh` already does.

---

## 9. Phases

Each phase is independently useful and independently testable; none of them
strands the Pi.

**Phase 1 — keyfile writer + root helper.** `keyfile.py`, `netd.py`,
`panel-netd.service`, tests off-Pi including the diff against `apply-wifi.sh`.
Verifiable entirely over SSH with the Pi on its normal network: feed the socket
a message, confirm the profile appears, `nmcli connection reload`, delete it.
No radio state is disturbed.

**Phase 2 — the AP profile.** Render and install `delia-setup.nmconnection`
with `autoconnect=false`. Bring it up manually from a console (this drops SSH),
confirm a phone can see and join it, get a DHCP lease, and reach `10.42.0.1`.
Bring it back down. Nothing is automated yet — this is purely "does the radio
do what we think".

**Phase 3 — the portal.** Flask app, scan list, form, probe catch-all, wildcard
DNS drop-in. Develop and test it off-Pi against `nm.mock` in a browser; the
captive-detection behaviour is the only part that needs the real AP.

**Phase 4 — the supervisor + dead-man's switch.** The state machine, the
timeout/rollback, `panel-provision.service`. Build the dead-man's switch
*before* the first unattended test, not after.

**Phase 5 — panel integration + UI trigger.** Draw the SSID and URL on the
matrix via `panel.client`; restore the previous scene afterwards. Add the
"Re-provision WiFi" action to the web app.

**Phase 6 — the runbook.** `instructions/wifi-captive-portal.md`, plus a row in
`instructions/README.md`, and a cross-reference from
`instructions/wifi-new-network.md` — with a clear statement of which method to
reach for when. Note the failure actually hit during phases 2–4; that's the
part not remembered in six months.

Also needed at the end: update `CLAUDE.md` (the WiFi bullet, and the "two
systemd services" claim, which becomes four), `deploy.sh` (a `provisioning`
target and the new units in the unit-comparison step), and
`matrix/raspberry_pi/`'s docs.

---

## 10. Open questions

- **Does `wifi.conf` stay the source of truth?** A network added through the
  portal exists only on the Pi; the laptop's `wifi.conf` won't know about it,
  and a later `apply-wifi.sh` run won't remove it (it only overwrites matching
  names) but the two views drift. Options: accept the drift and rely on the
  `portal-` label prefix to keep them distinguishable; or add a `--pull` mode
  to `apply-wifi.sh` that reads profiles back off the Pi. Leaning toward
  accepting the drift — the portal is the emergency path, `wifi.conf` is the
  planned path.
- **Should the portal also show diagnostics?** Signal strength, current IP,
  panel service status. Cheap to add and it's exactly when you want it. Risk of
  scope creep.
- **Is `panel-netd` a separate daemon or a second message type on the existing
  one?** Separate is cleaner (the renderer daemon should not grow a network
  API and should not need to be restarted to change WiFi code). Separate unless
  the process overhead on 512 MB proves to matter.
