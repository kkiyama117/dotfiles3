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
- [x] `dot_config/waybar/{config,style.css}` added (self-contained Catppuccin Mocha) with `hyprland/workspaces` + pulseaudio/network/clock/tray; replaces the shipped default (sway/workspaces, disabled on Hyprland). `packages.toml` still untouched (container has no GUI).
- [ ] (Later) more modules / reference parity (bluetooth, battery, custom/power→wlogout) when those tools are installed.

## Notes

- `hl.layer_rule` blur field confirmed against end-4/dots-hyprland: `hl.layer_rule({ match = { namespace = "..." }, blur = true })` (retrieved 2026-08-20).
- Scope kept minimal per user decision. A design doc ([`AGENTS.md`](../../AGENTS.md) §2) was skipped because the change is small (two config lines). Escalate to `docs/specifications/implementations/2026-08-20-hyprland-waybar-topbar-design.md` if module config or package wiring is added later.
- Reference config (fetched 2026-08-20): <https://github.com/ViegPhunt/Dotfiles/blob/main/.config/hypr/hyprland.conf>

## Remaining work (handoff to next agents)

Status bar (waybar) is live with `hyprland/workspaces` + pulseaudio/network/clock/tray. Deferred/optional work, prioritized.

### P1 — functional gaps
1. More modules for reference parity (the `(Later)` acceptance item): bluetooth (needs `blueman`), custom/power→`wlogout` (needs `wlogout`). battery is meaningless on this desktop (skip). After installing the tools on the GUI host, add module blocks to [`dot_config/waybar/config`](../../dot_config/waybar/config) + matching CSS in `style.css`.
2. Verify waybar auto-starts on a full Hyprland restart. [`custom/autostart.lua`](../../dot_config/hypr/custom/autostart.lua) runs `hl.exec_cmd("waybar")` on `hyprland.start`; only verified via a manual launch this session (PID 185151), not across a real restart.

### P2 — polish
3. Workspaces module: `format-icons` (app icons per workspace), `persistent-workspaces`, scroll-to-switch (currently `format="{name}"`, `disable-scroll=true`).
4. CSS polish: hover states, separators, per-module colors toward the reference `style.css` level.
5. CSS auto-reload: add `"reload_style_on_change": true` to the waybar config (CSS reloads on save; complements Super+Shift+B full reload).
6. Shared colorsheet: create `dot_config/colors/colors.css` (Catppuccin Mocha vars), `@import` from waybar style, reuse for cava/hyprland borders (currently inline-duplicated in waybar + cava).
7. Font parity: install `ttf-jetbrainsmono-nerd` (AUR) to match the reference's JetBrainsMono Nerd Font (currently NotoSansM Nerd Font; works but different typeface).

### P3 — ecosystem / closure
8. cava binary: `sudo pacman -S cava && chezmoi apply` (config in repo at `dot_config/cava/config`; binary not installed).
9. Close this issue when modules are done: set Status `closed`, write a result-log under `docs/issues/` ([`00-document-management.md`](../specifications/00-document-management.md) §4/§6.6).

### Environment notes (for the next agents)
- chezmoi source = `/home/kiyama/.local/share/chezmoi` → symlink `/data/dotfiles3` (repo IS the source; `chezmoi apply` materializes to home).
- Live Hyprland host: PID 102883, `WAYLAND_DISPLAY=wayland-1`, instance sig `efb50993780079460b0cbed1363e2166a2de1d9f_1787197845_721045847`. A detached shell lacks `WAYLAND_DISPLAY`/`HYPRLAND_INSTANCE_SIGNATURE` — inject them for `hyprctl`/waybar-launch. `hyprctl reload` works on this hyprlua build (re-binds keys; does not re-run the `hyprland.start` autostart event).
- waybar reload signal = SIGUSR2 (default reload per waybar(5)); `Super+Shift+B` sends it.
- Host-only tools (waybar/cava/fuzzel) are deliberately NOT in `dependencies/packages.toml` (container has no GUI/audio; the `migrated`/`custom` managers don't fit). Install on the GUI host directly.
- end-4's bar is Quickshell (QML); this repo chose waybar. Only the app launcher mirrors end-4 (fuzzel).
