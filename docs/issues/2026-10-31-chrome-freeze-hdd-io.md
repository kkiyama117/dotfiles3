# Chrome freezes caused by HDD IO stalls

- Date: 2026-10-31
- Status: mitigated (cache on NVMe + AV1 HW decode)

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

## Second cause: YouTube AV1 software decode

- 2026-11-01: with the HDD cache fixed, YouTube tabs were still heavy.
  Probe showed `dav1d-w*` threads (software AV1) at ~55% renderer CPU and
  NVDEC decoder 0%; `chrome://gpu` "Video Decode: Hardware accelerated" is
  not codec-specific and was misleading.
- Mitigation: `--enable-features=AcceleratedVideoDecodeLinuxGL,VaapiOnNvidiaGPUs`,
  `--ignore-gpu-blocklist`, `--use-gl=angle --use-angle=gl`
  (nvidia-vaapi-driver README, Chrome section; `LIBVA_DRIVER_NAME=nvidia` is
  already set in `dot_config/hypr/custom/environment.lua`).
- Result: `dav1d-w*` threads gone, GPU-process CPU 40% -> 6%.
  Experimental: remove these flags if video turns green / Chrome is unstable.
- Remaining: one renderer main thread at ~47% CPU (page JS, not decode).

## Follow-up (not done)

- Move the profile (`~/.config/google-chrome`) to NVMe if freezes persist.
- Identify burst sources with `iotop -oPa` / `pidstat -d 1` during a freeze.
