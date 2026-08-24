# Moving the Pi to a new WiFi network

Also covers a changed password on the network it's already on.

Two ways in, depending on whether you can still reach the Pi:

- **[The Pi is on a network](#the-pi-is-on-a-network)** — push over SSH. Do it
  this way whenever you can, *before* moving anything.
- **[Writing to the SD card](#writing-to-the-sd-card)** — for when it's already
  unreachable.

Either way, leave the old network in the config. The Pi keeps every network it
knows and joins whichever is in range, and with no ethernet port the old one is
your only way back in if the new one doesn't work.

## First, the config

Both paths read the same file.

```bash
cd matrix/raspberry_pi/pi-setup
cp wifi.conf.example wifi.conf     # first time only; it's gitignored
$EDITOR wifi.conf
```

One block per network. Add a block for the new one; edit `psk` in place for a
changed password.

```ini
[home]
ssid = OldNetwork
psk = old-password
priority = 5

[newplace]
ssid = NewNetwork
psk = new-password
priority = 10        # higher wins when both are in range
```

---

## The Pi is on a network

**1. Push it.** This only adds the profiles — your SSH session stays up.

```bash
./apply-wifi.sh          # prompts for the Pi's sudo password
```

**2. Switch over.** If you're moving the Pi somewhere new: power off, move,
power on. If it's staying put (new router, or just a new password), switch it
in place:

```bash
ssh user@delia.local 'sudo nmcli device wifi rescan; sudo nmcli connection up newplace'
```

Your SSH session dies as it switches off the network you're connected over.
That's normal — wait 30s and reconnect.

**3. Check it worked.**

```bash
ssh user@delia.local 'nmcli -f NAME,DEVICE,ACTIVE connection show'
./deploy.sh status
```

---

## Writing to the SD card

Before you pull anything apart: **set your phone's hotspot to the old SSID and
password.** The Pi joins it, you join it too, and you're back to the SSH path
above.

Otherwise, power off the Pi, pull the card, and put it in this laptop.

> **Don't reflash the card to fix WiFi.** It holds the whole working system —
> `~/delia`, the compiled `~/rpi-rgb-led-matrix`, the venv, and both units in
> `/etc/systemd/system`. Reflashing means rebuilding the library on a 512 MB
> Pi 3 A+ and walking the entire [setup runbook](../matrix/raspberry_pi/led-matrix-setup.md)
> again. Writing the profiles below takes a second and changes nothing else.

**1. Find the root partition.** The desktop mounts both partitions for you,
usually at `/media/$USER/rootfs` — you want `rootfs`, the big ext4 one, not the
small `bootfs`.

```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT
```

If it didn't mount itself: `sudo mount /dev/mmcblk0p2 /mnt` (use whatever
device `lsblk` showed) and use `/mnt` below.

**2. Write the profiles.** Use `sudo`, or the files land under the wrong owner
and the Pi ignores them.

```bash
cd matrix/raspberry_pi/pi-setup
sudo ./apply-wifi.sh --write-to /media/$USER/rootfs/etc/NetworkManager/system-connections
```

**3. Eject, put the card back, power on.** Give it a minute to join.

```bash
udisksctl unmount -b /dev/mmcblk0p2      # or `sudo umount /mnt` if you mounted it by hand
```

**4. Check it worked.**

```bash
ssh user@delia.local 'nmcli -f NAME,DEVICE,ACTIVE connection show'
./deploy.sh status
```

---

## When something's wrong

**`Could not resolve hostname delia.local`** — that's mDNS, not WiFi, and the
Pi may be perfectly fine. See [reaching-the-pi.md](reaching-the-pi.md).

**It joins nothing, and you're wondering why.** Look at the card before
theorizing — an *empty* profile directory means it has no credentials at all,
which is a different problem from wrong ones:

```bash
ls -l /media/$USER/rootfs/etc/NetworkManager/system-connections/
```

(This is exactly what happened on 2026-08-16: the directory was empty, so the Pi
had nothing to join with. Two profiles written, fixed.)

**Joins nothing at all** — WiFi is blocked until the country is set:
`sudo rfkill unblock wifi`, then `sudo raspi-config` → Localisation → WLAN
Country.

**Right password, still rejected** — check for a trailing space in `wifi.conf`
(quote it to keep one: `psk = "ends with space "`), and check the SSID's exact
capitalization.

**Nothing works and `systemctl is-active NetworkManager` says `inactive`** —
this Pi is older than Bookworm and uses `wpa_supplicant`; none of this applies.
