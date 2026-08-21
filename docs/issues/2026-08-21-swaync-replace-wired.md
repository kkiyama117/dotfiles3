# Replace wired with SwayNC; waybar module left of sound

**Date:** 2026-08-21
**Status:** in-progress
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
- Waybar `custom/notification` first on `modules-right`; `exec: swaync-client -swb`.
- Delete wired source: packages.toml entry, generated layer list, systemd unit, `wired.ron`.
- No custom `dot_config/swaync/` theme unless defaults look wrong (ponytail).

## Acceptance criteria

- [x] `modules-right` starts with `custom/notification` then `pulseaudio`.
- [x] Click toggles the SwayNC panel; right-click toggles DND (waybar `on-click` / `on-click-right`).
- [x] `wired` gone from `packages.toml` / `layer_4/paru.txt` / 02 AUTO-GEN (`make gen-deps` 2026-08-21).
- [x] `dot_config/wired/` and `wired.service` removed from chezmoi source.
- [ ] Host: install `swaync` (sudo required; not done this session), stop `wired.service`, start `swaync`, `chezmoi apply`, reload waybar. `wired` is still `active` on the host as of 2026-08-21 09:28 JST.

## Host leftover (run locally)

```sh
sudo pacman -S --needed swaync
systemctl --user disable --now wired.service
# dest files are not removed by deleting chezmoi source:
rm -f ~/.config/systemd/user/wired.service
# optional: paru -Rns wired
swaync &
pkill -SIGUSR2 waybar
```

## Notes

- Design doc skipped (same as the waybar issue: GUI config, not a spec change).
- Host leftover after `chezmoi apply`: `~/.config/wired/` and the enabled user
  unit are not auto-deleted by chezmoi. Disable/stop the unit and `paru -Rns wired`.
