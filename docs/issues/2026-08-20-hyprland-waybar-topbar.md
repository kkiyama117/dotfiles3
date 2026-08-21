# Hyprland topbar with waybar (host-only)

**Date:** 2026-08-20
**Status:** in-progress
**Related:** [swaync replace wired](2026-08-21-swaync-replace-wired.md)

## Context

- Hyprland config is Lua (end-4 hyprlua `hl.` API): [`dot_config/hypr/hyprland.lua`](../../dot_config/hypr/hyprland.lua) → `conf/*.lua` (portable) + `custom/*.lua` (machine).
- No topbar existed. [`custom/autostart.lua`](../../dot_config/hypr/custom/autostart.lua) launched only hyprpolkitagent / fcitx5 / cliphist.
- Reference: ViegPhunt/Dotfiles uses **waybar** — `exec-once = waybar`, `.config/waybar/{config,style.css}`, and `layerrule = blur on, match:namespace waybar` in `appearance.conf`.

## Problem

Add a topbar to Hyprland: pick the bar, wire launch + blur, and decide install handling.

## Decision

- **Bar:** waybar (matches the reference; JSON/CSS config, independent of the Lua hypr config, lowest setup cost).
- **Scope now:** launch + blur only. Waybar module config (`dot_config/waybar/`) is deferred — add when modules are chosen.
- **Install:** host-only. The container has **no GUI**, so waybar is deliberately NOT added to [`dependencies/packages.toml`](../../dependencies/packages.toml): the `migrated` manager assumes retained chezmoi config and `custom` assumes a Containerfile path, neither applies to a host-only GUI tool with no templated config. Install on the GUI host via the system package manager.

## Acceptance criteria

- [x] `custom/autostart.lua` launches waybar on `hyprland.start`.
- [x] `conf/appearance.lua` adds a `hl.layer_rule` blurring the `waybar` layer namespace.
- [x] Rationale (host-only, no container install) documented in config comments and this issue.
- [x] `conf/keybinding.lua` binds Super+Shift+B to reload waybar (`pkill -SIGUSR2 waybar`); SIGUSR2 is waybar's default reload signal (no config flag, no extra deps).
- [x] `dot_config/waybar/{config,style.css}` added (self-contained Catppuccin Mocha) with `hyprland/workspaces` + pulseaudio/bluetooth/network/clock/tray; replaces the shipped default (sway/workspaces, disabled on Hyprland). `packages.toml` still untouched (container has no GUI).
- [x] `custom/power` → `wlogout` (left of workspaces, same as ViegPhunt). Layout is Hyprland logout + suspend/reboot/shutdown; no lock (no locker installed) and no hibernate. Host: `paru -S wlogout` (AUR). Super+M opens the same menu.
- [x] P2 no-sudo polish (2026-08-21): `dot_config/colors/colors.css` + waybar `@import`; workspace persistent 1–10, scroll, numbered `{icon}`; hover CSS; `reload_style_on_change`.

## Notes

- `hl.layer_rule` blur field confirmed against end-4/dots-hyprland: `hl.layer_rule({ match = { namespace = "..." }, blur = true })` (retrieved 2026-08-20).
- Scope kept minimal per user decision. A design doc ([`AGENTS.md`](../../AGENTS.md) §2) was skipped because the change is small (two config lines). Escalate to `docs/specifications/implementations/2026-08-20-hyprland-waybar-topbar-design.md` if module config or package wiring is added later.
- Reference config (fetched 2026-08-20): <https://github.com/ViegPhunt/Dotfiles/blob/main/.config/hypr/hyprland.conf>

## Remaining work (handoff to next agents)

Status bar (waybar) is live with `custom/power` + `ext/workspaces` + tray, notification, pulseaudio, bluetooth, network, clock. `custom/power` click / Super+M → `wlogout -b 4 --protocol layer-shell`. Bluetooth click opens `kitty --class floatingterm -e bluetoothctl`. Polish on 2026-08-21: shared `dot_config/colors/colors.css`, hover CSS, `reload_style_on_change`. Workspaces switched to `ext/workspaces` + `on-click: activate` the same day: waybar 0.15.0 `hyprland/workspaces` sends `dispatch workspace N`, which Hyprland Lua (`configProvider: lua`) rejects (`hl.dispatch(workspace N)`). `ext/workspaces` uses ext-workspace-v1 (no IPC dispatch). Tradeoff: no `persistent-workspaces` (empty 1–10 stay hidden). Restore `hyprland/workspaces` after `paru -S waybar-git` (Lua dispatch fix).

### P1 — functional gaps
1. ~~More modules / wlogout leftover~~ done 2026-08-21 (`wlogout` installed; `custom/power` has no `exec-if` — that hid the button).
2. Verify waybar auto-starts on a full Hyprland restart. [`custom/autostart.lua`](../../dot_config/hypr/custom/autostart.lua) runs `hl.exec_cmd("waybar")` on `hyprland.start`; only verified via `hl.exec_cmd`, not a real logout/login.
2b. Optional: `paru -S waybar-git` then restore `hyprland/workspaces` (persistent 1–10 + Lua-safe click). Current `ext/workspaces` click is the 0.15.0 workaround.

### P2 — polish
3. ~~Workspaces: format-icons / persistent / scroll~~ numbered `{icon}` done; persistent dropped 2026-08-21 when moving to `ext/workspaces` so click-to-switch works on waybar 0.15.0 + Hyprland Lua. Re-add persistent after `waybar-git`.
4. ~~CSS hover / per-module colors~~ done 2026-08-21 (padding as separators; no extra separator modules).
5. ~~`reload_style_on_change`~~ done 2026-08-21.
6. ~~Shared colorsheet~~ done 2026-08-21 (`dot_config/colors/colors.css`, waybar `@import`). Optional later: point cava/hypr at the same palette (cava is INI, cannot `@import`).
7. Font parity: install `ttf-jetbrainsmono-nerd` (AUR) to match the reference's JetBrainsMono Nerd Font (currently NotoSansM Nerd Font; works but different typeface).

### P3 — ecosystem / closure
8. cava binary: `sudo pacman -S cava && chezmoi apply` (config in repo at `dot_config/cava/config`; binary not installed).
9. Close this issue when modules are done: set Status `closed`, write a result-log under `docs/issues/` ([`00-document-management.md`](../specifications/00-document-management.md) §4/§6.6).

### Environment notes (for the next agents)
- chezmoi source = `/home/kiyama/.local/share/chezmoi` → symlink `/data/dotfiles3` (repo IS the source; `chezmoi apply` materializes to home).
- Live Hyprland host: PID 102883, `WAYLAND_DISPLAY=wayland-1`, instance sig `efb50993780079460b0cbed1363e2166a2de1d9f_1787197845_721045847`. A detached shell lacks `WAYLAND_DISPLAY`/`HYPRLAND_INSTANCE_SIGNATURE` — inject them for `hyprctl`/waybar-launch. `hyprctl reload` works on this hyprlua build (re-binds keys; does not re-run the `hyprland.start` autostart event).
- waybar reload signal = SIGUSR2 (default reload per waybar(5)); `Super+Shift+B` sends it. `"reload_style_on_change": true` watches `style.css` only — editing `colors/colors.css` still needs SIGUSR2.
- Host-only tools (waybar/cava/fuzzel) are deliberately NOT in `dependencies/packages.toml` (container has no GUI/audio; the `migrated`/`custom` managers don't fit). Install on the GUI host directly.
- end-4's bar is Quickshell (QML); this repo chose waybar. Only the app launcher mirrors end-4 (fuzzel).
