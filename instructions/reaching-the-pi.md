# Reaching the Pi

The Pi answers to **`delia.local`** (mDNS — no IP to remember). It was
`delia-pi.local` until the rename; if that is still what answers, run
*Renaming it* below.

## Is it alive?

Run these in order. The first one that fails tells you where the problem is.

```bash
ping -c 3 delia.local                          # 1. on the network?
ssh mlavinder@delia.local                      # 2. can I get a shell?
./deploy.sh status                             # 3. are both services up?
curl -sI http://delia.local:8080 | head -1     # 4. is the web UI serving?
```

## Renaming it

`delia.local` is just avahi publishing the Pi's hostname over mDNS. The catch is
that **this image is cloud-init managed**, so `/etc/hostname` and `/etc/hosts`
are both *generated*, not authoritative — `/etc/cloud/cloud.cfg` has
`preserve_hostname: false`, the user-data sets `manage_etc_hosts: true`, and
cloud-init rewrites both from the boot partition on every boot. Rename it with
`hostnamectl` alone and the old name can come back at the next reboot.

The source of truth is one line in **`user-data` on the boot partition** — which
is `/boot/firmware/user-data` on the running Pi, and `bootfs/user-data` when the
card is mounted on a laptop.

```bash
ssh mlavinder@delia.local                            # or the OLD name, pre-rename
sudo cp /boot/firmware/user-data /boot/firmware/user-data.bak
sudo sed -i 's/^hostname: .*/hostname: delia/' /boot/firmware/user-data
sudo hostnamectl set-hostname delia                  # takes effect now, without a reboot
sudo sed -i 's/\bdelia-pi\b/delia/g' /etc/hosts     # keeps THIS session consistent;
                                                     # cloud-init regenerates it on boot
sudo systemctl restart avahi-daemon                  # republish <hostname>.local
```

With the card out of the Pi and mounted on a laptop, the same rename is the
`user-data` line alone, and it needs no sudo — that partition is vfat, mounted
`uid=1000`. `/etc/hostname` and `/etc/hosts` on the ext4 side do need root, but
cloud-init will fix both on the next boot anyway.

Then, from the laptop:

```bash
ping -c 3 delia.local                          # answers within a few seconds
```

- Both names may answer for a minute while the old mDNS record ages out. The old
  one stops working after that — that is the rename taking effect, not a fault.
- SSH will ask you to confirm a host key the first time you use the new name.
  It is the same machine and the same key; `known_hosts` is keyed by name.
- The web UI moves with it: `http://delia.local:8080`.
- Nothing on the Pi refers to the hostname (the services bind `0.0.0.0` and the
  socket is a path), so no service needs restarting. In this repo the name is
  only a default — `PI_HOST` for `deploy.sh` and `apply-wifi.sh`, `PANEL_API`
  for the Vite dev proxy.
- `instance_id` in `meta-data` is what decides whether cloud-init treats the card
  as a new instance. Leave it alone: changing it re-runs first-boot setup.
