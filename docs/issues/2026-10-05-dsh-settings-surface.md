# DSH settings surface retired upstream (0.2.1-alpha.1) + remote-web-ui pairing fence

**Date:** 2026-10-05
**Status:** in-progress
**Related:** [01-file-structures.md](../specifications/01-file-structures.md)

## Context

Observed on 2026-10-05 on the host (`boiled`), read-only checks only.

- Live harness: `/data/softwares/deepseek-harness-upgrade-master` (0.2.1-alpha.1).
  - systemd user unit `dsh-web-managed.service`: `node .../apps/cli/lib/bin.js web --port 3080 --no-open --trusted-host boiled.colobus-powan.ts.net`, `Environment=DSH_HOME=~/.dsh`, `WorkingDirectory=/data/softwares/deepseek-harness-upgrade-master`.
  - Listens on `127.0.0.1:3080`; Caddy fronts it as `https://boiled.local` (internal CA) and `https://boiled.colobus-powan.ts.net` (tailscale cert) — `~/.dsh/caddy/Caddyfile`.
- dotfiles3 managed `dot_dsh/settings.yaml` → `~/.dsh/settings.yaml` (spec 01 §2 tree, `.chezmoiignore`).
- Effective settings documents of the running instance:
  - `~/.dsh/profiles/web/cordis.patch.yml` — the active profile patch; the harness settings UI writes here (`profileContext.patchPath`).
  - `~/.dsh/cordis.patch.yml` — home-level patch applied *above* the profile patch; currently wires `session-persistence-jsonl` / `storage-json` / `attachment-local` to `~/.dsh-recovery-20261005` plus the `memory-kura` row.
- The pre-upgrade live document is preserved at `~/.dsh-recovery-20261005/settings.yaml` (`remote-web-ui.requirePairingForLan: false`, no `publicBaseUrl`).
- `~/.dsh/settings.yaml` does not exist right now (only `settings.yaml.bak-*` from 2026-09-13).

## Problem

### P1 — the managed surface is retired upstream

0.2.1-alpha.1 no longer reads a root `settings.yaml` as a settings source. `SettingsForms.importLegacyDocument()` reads `join(profile.home, 'settings.yaml')` (`profileContext.home` = `$DSH_HOME`), **renames it to `settings.yaml.imported`**, and merges its sections into the active profile patch — harness sources `packages/settings/settings/src/index.ts:238-258`, with the id remap table `LEGACY_SECTION_ENTRIES` (`ui-onboarding` → `ui-settings-general`, `agent-presets` → the preset registry entry, …).

Consequences for this repo:

- `dot_dsh/settings.yaml` is a **one-shot import seed**, not a settings source. Restoring it is actively harmful: the next DSH boot would import its stale sections over the current live values (e.g. `agent-default-model: ollama-cloud/deepseek-v4-pro:0813`, while the migration deliberately kept `openai-codex/gpt-6.1-sol/xhigh`), and `chezmoi apply` would recreate the file after every import.
- The managed file has also drifted from live: it carries `llm-cursor`, `kimi-coding`, `locale`, `pet`, `skin-background` and `publicBaseUrl`, none of which are in the live document, and it lacks live-only sections (`permission`, `dsh-better-sidebar`, `subagent-model-selection-settings`).

### P2 — live incident: the pairing fence blocks every non-loopback Web GUI

Opening the Web GUI from `https://boiled.local` or `https://boiled.colobus-powan.ts.net` renders the remote-web-ui blocking page `This device is not paired and cannot reach workspace data`, with no workspace or session data behind it.

- String origin: `@linxin666/dsh-remote-web-ui` 0.4.4, `fence.unpaired.title` (`lib/client.js:3376`, source `src/client/locales.ts:168`), rendered by `FenceNotice` when the gated `/remote` channel reports `unpaired`.
- Mechanism: the browser half reads the host-authoritative policy by fetching `api/pair/status` (`src/client/pair-api.ts::readPairGatePolicy`). That route is answered by the plugin's own `lanFence` (`src/routes.ts:583-620`), which trusts only loopback, live LAN literals, the configured `publicBaseUrl`, configured/env `trustedHosts`, and dynamically paired hosts. The Caddy/tailnet authorities are none of those, so the probe is refused, `readPairGatePolicy()` throws and the client **fails closed** (`hostPairingPolicy = true`, `src/client/index.ts:436-450`) → every `/api`, `/sidebar`, `/git`, `/pet` call is rewritten onto the gated `/remote` channel → no paired-device cookie (`deviceCount: 0`) → the fence.
- `requirePairingForLan: false` cannot break this loop: reading that value is itself behind the fence. The fence never learned the two Caddy origins because neither `publicBaseUrl` nor `trustedHosts` is set (only `requirePairingForLan: false` is).

Evidence (2026-10-05):

```console
$ curl -s http://127.0.0.1:3080/api/pair/status
{"ok":true,"paired":false,"requirePairingForLan":false,"phase":"lan-required","lanAvailable":false,"lanAddresses":[],"deviceCount":0,"onlineCount":0}

$ curl -s -H 'Host: boiled.colobus-powan.ts.net' http://127.0.0.1:3080/api/pair/status
{"ok":false,"code":"forbidden"}          # plugin lanFence, not the harness fence

$ curl -s -o /dev/null -w '%{http_code}\n' https://boiled.colobus-powan.ts.net/api/pair/status
403

$ dsh --profile web --dump-config | grep -A4 'id: remote-web-ui'
- id: remote-web-ui
  name: '@linxin666/dsh-remote-web-ui'
  config:
    requirePairingForLan: false          # no publicBaseUrl / trustedHosts
```

Data is intact — `~/.dsh-recovery-20261005/sessions/*/session.v4.jsonl.zstd` and `~/.dsh-recovery-20261005/storages/workspace.json` exist and are written by the running instance (12:16 JST boot; the harness token URL is in `journalctl --user -u dsh-web-managed.service`). Only the browser is fenced, so the fence copy ("cannot reach workspace data") is misleading.

## Acceptance criteria

- [x] spec 01 stops claiming a managed `~/.dsh` surface; `.chezmoiignore` ignores `.dsh` entirely.
- [x] `dot_dsh/settings.yaml` removed from the source tree (issue path cited in the commit message).
- [ ] Live fence cleared by an executor agent (see the handoff prompt below).
- [ ] `chezmoi status` reports no pending `~/.dsh` entries after the removal (needs an unlocked Bitwarden session; not runnable from a non-interactive agent session).

## Notes

- Design/review documents were skipped: this change is a doc line + an ignore rule (reversible, no container/build impact), the same precedent as [`2026-08-20-hyprland-waybar-topbar.md`](2026-08-20-hyprland-waybar-topbar.md). Escalate to a design if a future change wants chezmoi to *own* anything under `~/.dsh`.
- DSH runtime state stays unmanaged on purpose: the harness rewrites `cordis.patch.yml` from its own settings UI and from plugin installs (`dsh plugin --profile web …`), so managing it would fight the harness.
- Do **not** restore `~/.dsh/settings.yaml`: under 0.2.1-alpha.1 it is an import seed whose stale sections would overwrite live settings on the next boot (P1).
- The alternative to the live fix below is pairing the device, which needs either `publicBaseUrl` (built-in QR base) or the LAN-bind toggle (also a restart) — i.e. the same config edit is the enabler either way.

## Handoff prompt (executor agent)

```text
Fix the live DSH remote-access pairing fence on this machine (host `boiled`). Work only on the
live harness runtime; do not modify the dotfiles3 repo.

ENVIRONMENT (verified 2026-10-05)
- Live harness: /data/softwares/deepseek-harness-upgrade-master (0.2.1-alpha.1)
- systemd user unit: dsh-web-managed.service
    ExecStart=... node .../apps/cli/lib/bin.js web --port 3080 --no-open --trusted-host boiled.colobus-powan.ts.net
    Environment=DSH_HOME=~/.dsh
- Caddy fronts 127.0.0.1:3080 as https://boiled.local and https://boiled.colobus-powan.ts.net
- Active settings document: ~/.dsh/profiles/web/cordis.patch.yml (settings UI writes here)
- Home patch (DO NOT EDIT): ~/.dsh/cordis.patch.yml — it wires sessions/storages/attachments
  to ~/.dsh-recovery-20261005

SYMPTOM
A browser at https://boiled.colobus-powan.ts.net or https://boiled.local shows the
@linxin666/dsh-remote-web-ui fence page "This device is not paired and cannot reach workspace data",
with no sessions or workspaces.

ROOT CAUSE (verified)
The plugin fences its own policy probe. From a non-loopback origin the browser half fetches
`api/pair/status`; the plugin's lanFence trusts only loopback, live LAN literals, `publicBaseUrl`,
`trustedHosts`, and dynamically paired hosts. The Caddy/tailnet authorities are none of them and
`publicBaseUrl` is unset, so the probe is 403 → the client fails closed → all API traffic is rewritten
onto the gated /remote channel → no paired-device cookie (0 devices) → the fence.
`requirePairingForLan: false` alone cannot break the loop: reading it is behind the same fence.

TASK — make the plugin trust the Caddy-fronted origins.

Preferred path (no service restart; live DSH sessions survive)
1. Read the current loopback token:
     journalctl --user -u dsh-web-managed.service | grep 'dsh web: http' | tail -1
2. Open that http://127.0.0.1:3080/?token=... URL in a browser on this machine.
3. Settings → the remote-web-ui card (Remote access / リモートアクセス設定):
   - public address (公網アドレス / publicBaseUrl) = https://boiled.colobus-powan.ts.net
   - if https://boiled.local must be unfenced too: trustedHosts = ["boiled.local"]
   The host applies publicBaseUrl live (service.setPublicBaseUrl via the settings watch) and the
   fence re-reads per request, so no restart is needed.

Alternative path (needs a restart; kills the running DSH web sessions — the 2026-10-05
master-upgrade goal is awaiting a conversation resume, so confirm with the operator first)
1. cp ~/.dsh/profiles/web/cordis.patch.yml \
      ~/.dsh/profiles/web/cordis.patch.yml.bak-$(date +%Y%m%dT%H%M%S)
2. In that file's `- id: remote-web-ui` row set:
     config:
       requirePairingForLan: false
       publicBaseUrl: https://boiled.colobus-powan.ts.net
       trustedHosts: [boiled.local]
3. systemctl --user restart dsh-web-managed.service

ACCEPTANCE (paste raw output)
- dsh --profile web --dump-config | grep -A6 'id: remote-web-ui'   → shows publicBaseUrl (and trustedHosts)
- curl -s http://127.0.0.1:3080/api/pair/status                    → 200, requirePairingForLan:false
- curl -s -H 'Host: boiled.colobus-powan.ts.net' http://127.0.0.1:3080/api/pair/status
                                                                  → 200 (was 403 {"ok":false,"code":"forbidden"})
- curl -s -o /dev/null -w '%{http_code}\n' https://boiled.colobus-powan.ts.net/api/pair/status → 200
- Browser at each origin: Web GUI loads with no fence page; existing sessions/workspaces list and open
- Loopback GUI at 127.0.0.1:3080 still works; the harness browser-auth cookie is still required on the
  Caddy origins (pre-existing access path, unchanged by this fix)

DO NOT
- run `chezmoi apply` (it would recreate ~/.dsh/settings.yaml; the harness imports that file once and
  renames it, clobbering live settings)
- edit ~/.dsh/cordis.patch.yml, or anything under ~/.dsh-recovery-20261005
- delete or rewrite files under ~/.dsh-recovery-20261005/sessions

ROLLBACK
GUI path: clear/restore the public address field in the same card.
File path: mv cordis.patch.yml.bak-<ts> cordis.patch.yml && systemctl --user restart dsh-web-managed.service

REPORT
The effective --dump-config row, both curl results, the per-origin GUI result, and any residual fence
(e.g. `boiled.local` left untrusted).
```
