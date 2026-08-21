# Replace wired with SwayNC; waybar module left of sound

**Date:** 2026-08-21
**Status:** closed
**Related:** [waybar topbar](2026-08-20-hyprland-waybar-topbar.md), [fetch hang](2026-08-21-pi-fetch-content-hang.md)

## Context

Waybar `modules-right` was `pulseaudio, network, clock, tray` with **no**
notification module. The notification daemon was **wired** (`packages.toml`
layer 4, `dot_config/wired/wired.ron`, `dot_config/systemd/user/wired.service`).
Wired has toasts + CLI (`--show`, `--dnd`) but no unread count and no control
center. SwayNC owns `org.freedesktop.Notifications` (cannot run beside wired)
and talks to waybar via `swaync-client -swb`.

User decisions (2026-08-21): switch to SwayNC for count + panel; delete wired
from the repo (package + unit + config). SwayNC is host-only like waybar (not
in `packages.toml`; container has no GUI).

## Problem

Put a live notification indicator immediately left of pulseaudio, with SwayNC’s
control center, and remove wired so the Notifications bus is free.

## Decision

- Host-install `swaync`. Do not add it to `packages.toml`.
- Autostart `swaync` from `custom/autostart.lua` (same pattern as waybar).
- Waybar `custom/notification` on `modules-right` immediately left of pulseaudio (`exec: swaync-client -swb`). Tray moved left of the bell 2026-08-21: `tray, custom/notification, pulseaudio, network, clock`.
- Delete wired source: packages.toml entry, generated layer list, systemd unit, `wired.ron`.
- No custom `dot_config/swaync/` theme unless defaults look wrong (ponytail).

## Acceptance criteria

- [x] `modules-right` is `tray, custom/notification, pulseaudio, network, clock` (tray left of the bell; bell left of pulseaudio). Updated 2026-08-21 after host leftover.
- [x] Click toggles the SwayNC panel; right-click toggles DND (waybar `on-click` / `on-click-right`).
- [x] `wired` gone from `packages.toml` / `layer_4/paru.txt` / 02 AUTO-GEN (`make gen-deps` 2026-08-21).
- [x] `dot_config/wired/` and `wired.service` removed from chezmoi source.
- [x] Host: `swaync` 0.12.6 running (`swaync.service` active, not enabled — autostart.lua owns launch). `wired` package gone. Notifications bus is SwayNotificationCenter. waybar `modules-right` is `tray, custom/notification, pulseaudio, network, clock`; SIGUSR2 reload 2026-08-21 10:00 JST. `swaync-client -swb` → `{"alt":"none",...}`.

## Host leftover (done 2026-08-21 09:57 JST)

```sh
# already true by then: pacman -Q swaync; wired package not installed
systemctl --user mask wired.service   # orphan /usr/lib/systemd/user/wired.service (no owning pkg)
rm -rf ~/.config/wired
kill -SIGUSR2 "$(pgrep -n waybar)"
```

Skipped: `paru -Rns wired` (package already absent). Mask kept because the unpackaged user unit file still sits under `/usr/lib/systemd/user/` and was colliding on `org.freedesktop.Notifications`. `sudo rm` that file if you want the mask gone too.

## Notes

- Design doc skipped (same as the waybar issue: GUI config, not a spec change).
- chezmoi does not delete dest leftovers; host cleanup is in **Host leftover** above.
