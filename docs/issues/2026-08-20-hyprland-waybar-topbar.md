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
- [x] `custom/power` → `wlogout` (left of workspaces, same as ViegPhunt). Layout is Hyprland logout + suspend/reboot/shutdown; no lock (no locker installed) and no hibernate. Host: `paru -S wlogout` (AUR). Super+M opens the same menu. Logout action is `hyprctl dispatch 'hl.dsp.exit()'` — plain `dispatch exit` is rejected under Lua (`configProvider: lua`), same class of bug as waybar 0.15 `dispatch workspace N`.
- [x] P2 no-sudo polish (2026-08-21): `dot_config/colors/colors.css` + waybar `@import`; workspace persistent 1–10, scroll, numbered `{icon}`; hover CSS; `reload_style_on_change`.

## Notes

- `hl.layer_rule` blur field confirmed against end-4/dots-hyprland: `hl.layer_rule({ match = { namespace = "..." }, blur = true })` (retrieved 2026-08-20).
- Scope kept minimal per user decision. A design doc ([`AGENTS.md`](../../AGENTS.md) §2) was skipped because the change is small (two config lines). Escalate to `docs/specifications/implementations/2026-08-20-hyprland-waybar-topbar-design.md` if module config or package wiring is added later.
- Reference config (fetched 2026-08-20): <https://github.com/ViegPhunt/Dotfiles/blob/main/.config/hypr/hyprland.conf>

## Remaining work (handoff to next agents)

Status bar (waybar-git 0.15.0.r972.gd561b9d) is live with `custom/power` + `hyprland/workspaces` (persistent 1–10) + tray, notification, pulseaudio, bluetooth, network, **cpu** (system-wide `{usage}%`), **memory** (`{percentage}%`, tooltip used/total GiB), clock. CPU/memory added 2026-08-22 (built-in modules, no extra packages). `custom/power` click / Super+M → `wlogout -b 4 --protocol layer-shell`. Bluetooth click opens `kitty --class floatingterm -e bluetoothctl`. Polish on 2026-08-21: shared `dot_config/colors/colors.css`, hover CSS, `reload_style_on_change`. Host: `cava` 0.10.7 installed; Noto Nerd Font kept (user: working). Clock tooltip calendar is Mocha-colored month view; scroll shifts month, right-click toggles year.

### P1 — functional gaps
1. ~~More modules / wlogout leftover~~ done 2026-08-21 (`wlogout` installed; `custom/power` has no `exec-if` — that hid the button).
2. ~~Verify waybar auto-starts on a full Hyprland restart~~ done 2026-08-21 10:57 JST after logout (wlogout `hl.dsp.exit()`) + login. Fresh session: `start-hyprland` PID 388737 → Hyprland PID 388776 at **10:44:31**; waybar PID 388846 PPID 388776 at **10:44:32** (+1s). Same-second siblings from `hyprland.start`: swaync 388847, `wl-paste` 388850/388851; fcitx5 388853 (daemonized, PPID 1). Layers: `namespace: waybar` pid 388846 on **HDMI-A-1** (1920×30) and **DP-3** (2560×30); both monitors `reserved: 0 30 0 0`. Side note (not blocking this item): `hyprpolkitagent` was not running after this login.
2b. ~~`waybar-git` + restore `hyprland/workspaces`~~ done 2026-08-21 11:04 JST. Host `waybar-git` 0.15.0.r972.gd561b9d (replaces 0.15.0). Config back to `hyprland/workspaces` with `sort-by: number` and `persistent-workspaces: { "*": [1–10] }`. waybar-git `IPC::buildLuaDispatch` maps click to `hl.dsp.focus({ workspace = "N" })`. Reloaded as Hyprland child PID 415270; log: `Loading persistent workspaces from Waybar config`; layers on HDMI-A-1 + DP-3. `hyprctl dispatch 'hl.dsp.focus({ workspace = 5 })'` → workspace 5 (then restored to 1). User still needs to confirm a bar click.

### P2 — polish
3. ~~Workspaces: format-icons / persistent / scroll~~ numbered `{icon}` + persistent 1–10 restored 2026-08-21 with waybar-git (`hyprland/workspaces`). Scroll left enabled (`disable-scroll` omitted).
4. ~~CSS hover / per-module colors~~ done 2026-08-21 (padding as separators; no extra separator modules).
5. ~~`reload_style_on_change`~~ done 2026-08-21.
6. ~~Shared colorsheet~~ done 2026-08-21 (`dot_config/colors/colors.css`, waybar `@import`). Optional later: point cava/hypr at the same palette (cava is INI, cannot `@import`).
7. ~~Font parity~~ skipped 2026-08-21: user confirmed current Nerd Font is fine (NotoSansM / NotoMono Nerd Font in `style.css`; JetBrains Mono is also installed but not the Nerd variant).

### P3 — ecosystem / closure
8. ~~cava binary~~ already on host 2026-08-21 (`cava` 0.10.7-1; dest `~/.config/cava/config` present).
9. Close this issue when modules are done: set Status `closed`, write a result-log under `docs/issues/` ([`00-document-management.md`](../specifications/00-document-management.md) §4/§6.6).
### Incident 2026-09-06 — jsoncpp soname bump killed waybar (resolved same day)

Full system upgrade 2026-09-06 00:08 JST moved `jsoncpp` 1.9.6-3 → 1.9.8-1 (soname `libjsoncpp.so.26` → `.so.27`). Host `waybar-git` 0.15.0.r1004.g6d60c8e (built 2026-08-28, AUR/paru) still linked `.so.26`, so `waybar` died at exec (`error while loading shared libraries: libjsoncpp.so.26`) and the topbar silently vanished — `custom/autostart.lua` `hl.exec_cmd("waybar")` has no supervision/retry. Only waybar was affected (`/usr/bin` ldd scan; cmake/openxr already on `.so.27`). Fix: rebuilt the same revision in `~/.cache/paru/clone/waybar-git` (`makepkg -f`; build needs no root), installed with `sudo pacman -U` at 10:05 JST, relaunched compositor-side with `hyprctl dispatch "hl.dsp.exec_cmd('waybar')"`. Verified: waybar PID 126372, `libjsoncpp.so.27` linked, layers 1920×30 (HDMI-A-1) + 2560×30 (DP-3), both monitors `reserved: 0 30 0 0`. Lesson: a `pacman -Syu` soname bump requires `paru -S --rebuild` for locally built AUR packages; system upgrade never rebuilds them.

### Environment notes (for the next agents)
- chezmoi source = `/home/kiyama/.local/share/chezmoi` → symlink `/data/dotfiles3` (repo IS the source; `chezmoi apply` materializes to home).
- Live Hyprland host (post-restart 2026-08-21 10:44): PID 388776, `WAYLAND_DISPLAY=wayland-1`, instance sig `efb50993780079460b0cbed1363e2166a2de1d9f_1787276672_1286926770`. waybar-git child PID 415270 (relaunched 11:04 after package swap). Previous session's HIS dir (`…_1787237191_649501422`) can linger without `.socket.sock`; Cursor/agent env often still holds the old HIS — use `hyprctl -i <live HIS>`. `hyprctl reload` re-binds keys; it does not re-run `hyprland.start`. Replacing the waybar package does not restart the running bar — kill + `hl.exec_cmd("waybar")`.
- waybar reload signal = SIGUSR2 (default reload per waybar(5)); `Super+Shift+B` sends it. `"reload_style_on_change": true` watches `style.css` only — editing `colors/colors.css` still needs SIGUSR2.
- Host-only tools (waybar/cava/fuzzel) are deliberately NOT in `dependencies/packages.toml` (container has no GUI/audio; the `migrated`/`custom` managers don't fit). Install on the GUI host directly.
- end-4's bar is Quickshell (QML); this repo chose waybar. Only the app launcher mirrors end-4 (fuzzel).
