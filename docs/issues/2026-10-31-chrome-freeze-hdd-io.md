# Chrome freezes caused by HDD IO stalls

- Date: 2026-10-31
- Status: mitigated (cache only)

## Problem

Google Chrome intermittently freezes while CPU / memory / GPU are idle.

## Findings

- PSI: memory 0, CPU ~0, **IO `full` avg60 ≈ 21%**.
- `/home` (and `/data`, `/var`) are on HDD (`sdb`); `/` and swap are on NVMe.
- Chrome profile `~/.config/google-chrome` (11G) and cache
  `~/.cache/google-chrome` (5.7G) live on the HDD.
- Godot / adb were not significant IO sources at measurement time; a Godot
  test run from another agent session was a plausible burst source.

## Mitigation

- `dot_config/chrome-flags.conf.tmpl`: `--disk-cache-dir=/tmp/chrome-cache-<user>`
  (`/tmp` is on NVMe). Cache loss on reboot/cleanup is acceptable.

## Follow-up (not done)

- Move the profile (`~/.config/google-chrome`) to NVMe if freezes persist.
- Identify burst sources with `iotop -oPa` / `pidstat -d 1` during a freeze.
