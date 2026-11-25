# Phase result-log — Raspberry Pi 4 server setup (Phase 1–2.5)

**Date:** 2026-11-25
**Plan:** [2026-11-25-rpi4-server-setup-impl](../plans/2026-11-25-rpi4-server-setup-impl.md)
**Issue:** [2026-11-25-rpi4-server-setup](2026-11-25-rpi4-server-setup.md)

## Phase 1 — Flash SD card (host)

| Check | Result |
|---|---|
| tarball | `ArchLinuxARM-rpi-aarch64-latest.tar.gz` (850,215,189 B), md5 OK |
| tarball contents | `linux-aarch64` 7.1.6 + `uboot-raspberrypi` 2025.01, root via `PARTUUID` in `boot.txt`, no `cmdline.txt` |
| flash | `flash-alarm-sd.sh` completed; `/dev/sdc1` 512M vfat `ALARMBOOT`, `/dev/sdc2` 57.2G ext4 `ALARMROOT` |
| fstab | `/boot` → `UUID=3BCB-5FF4` |

## Phase 2 — First boot (wired)

Booted on the LAN of jump host `polaris` (`10.232.117.128/26`), not the host LAN.

| Check | Result |
|---|---|
| discovery | `ssh polaris 'bash -s' < find-pi.sh` → `10.232.117.143`, MAC `d8:3a:dd:13:3b:f2`, ssh open |
| SSH key login | OK with `-i ~/.ssh/main` (without `-i`: `Permission denied (publickey)`) |
| password SSH | rejected (`Permission denied (publickey)`) |
| hostname / IF | `colored` / `end0` (DHCP) |
| `pacman -Syu` | first attempt 404 on `linux-aarch64-7.3.6-1` via geo-redirect mirror; fixed by prepending `tw`/`tw2` mirrors (design §6) |
| after reboot | kernel `7.3.6-1-aarch64-ARCH`, `systemctl is-system-running` = `running`, no failed units |
| block device | SD was `mmcblk1` on 7.1.6, `mmcblk0` on 7.3.6; `/boot` mounted via UUID (I2 validated) |

## Phase 2.5 — Remote access

| Check | Result |
|---|---|
| packages | `tailscale` 1.104.7-1, `sudo` 1.9.17.p2-7 |
| `tailscaled` | enabled / active |
| tailnet | `100.68.63.72`; first registered as `colored-1` (stale 2023 node `colored` 100.79.84.136). Stale node removed, renamed to `colored`, key expiry disabled (admin console, user-confirmed) |
| `ssh colored` (tailnet) | OK |
| `ssh colored-lan` (ProxyJump polaris) | OK |
| ssh config | `Host colored` / `colored-lan` added; `private_dot_ssh/config.tmpl` re-synced with live `~/.ssh/config` (`chezmoi diff` empty) |

## Remaining

- (done) Tailscale admin console cleanup
- Phase 3 (Wi-Fi) not started
