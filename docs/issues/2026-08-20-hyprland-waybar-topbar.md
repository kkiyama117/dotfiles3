# Hyprland topbar with waybar (host-only)

**Date:** 2026-08-20
**Status:** in-progress
**Related:** none yet (no design; change is small — see Notes)

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
- [ ] (Later) `dot_config/waybar/{config,style.css}` + module layout when modules are added; revisit `packages.toml` only if the container gains a GUI.

## Notes

- `hl.layer_rule` blur field confirmed against end-4/dots-hyprland: `hl.layer_rule({ match = { namespace = "..." }, blur = true })` (retrieved 2026-08-20).
- Scope kept minimal per user decision. A design doc ([`AGENTS.md`](../../AGENTS.md) §2) was skipped because the change is small (two config lines). Escalate to `docs/specifications/implementations/2026-08-20-hyprland-waybar-topbar-design.md` if module config or package wiring is added later.
- Reference config (fetched 2026-08-20): <https://github.com/ViegPhunt/Dotfiles/blob/main/.config/hypr/hyprland.conf>
