# Bring pi agent + provider config under managed pi-config

**Date:** 2026-07-14
**Status:** closed (Phases 1-6 done in the single rewrite commit at `develop` HEAD; runtime verify passed; see result log [2026-07-14-phase-pi-provider-config-managed.md](./2026-07-14-phase-pi-provider-config-managed.md)). Deferred follow-ups (operator-owned): (1) rotate DeepSeek key + update Bitwarden item, (2) commit `PI_harness` retirement in `~/.pi`, (3) optionally remove `~/.pi/.git` (design Q8), (4) `agent/extensions/` host-side untrack.
**Related:** [design](../specifications/implementations/2026-07-14-pi-provider-config-managed-design.md), [pi-config bootstrap issue](2026-07-08-pi-agent-container-git-managed-config.md), [api-secrets issue](2026-07-11-api-secrets-env-management.md), [spec 11](../specifications/11-pre-required-env-values.md), [spec 13](../specifications/13-secret-management.md), [SOP: pi-model-provider-swap](../../.pi/agent-sops/pi-model-provider-swap.sop.md), [SOP: cursor-sdk-catalog-refresh](../../.pi/agent-sops/cursor-sdk-catalog-refresh.sop.md)

## Context

- The pi-config bootstrap design
  (`docs/specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md`)
  landed `/data/pi-config` (remote `git@github.com:kkiyama117/pi-config.git`)
  consumed by `dotfiles3` via `.chezmoiexternal.toml.tmpl` into
  `~/.local/share/pi-config`. The `run_after_configure-pi-agent.sh.tmpl`
  script currently symlinks exactly five resources from there into
  `~/.pi/agent`: `settings.json`, `prompts`, `skills`, `extensions`,
  `themes`.
- The current `/data/pi-config` checkout contains only `agent/prompts/commit.md`
  and empty `skills/` `extensions/` `themes/` — **no `settings.json`, no
  provider files**. So today none of the live `~/.pi/agent` provider
  configuration is actually managed.
- The live `~/.pi/agent` directory also carries provider files that are
  stable enough to manage but are not yet in `/data/pi-config`:
  - `settings.json` (agent + subagent model selection, no secrets)
  - `models.json` (DeepSeek provider declaration) — **contains a plaintext
    DeepSeek `apiKey` (`sk-...`)**, which spec 11 §"API provider env vars"
    and spec 13 I-S3 forbid in `/data/pi-config`.
  - `ollama-cloud.json` (`{"webTools": false}`)
  - `cursor-sdk.json` (`{"fastDefaults": {}}`)
  - `cursor-sdk-context-windows.json` (hand-curated context-window
    overrides; governed by
    `~/.pi/agent-sops/cursor-sdk-catalog-refresh.sop.md`)
- The running container also carries a per-provider override directory
  **outside `agent/`**: `~/.pi/providers/kimi-coding/config.json`,
  overriding the built-in `kimi-coding` provider's model params, tool
  toggles, and protocol. It is secret-free and stable. The pi docs do
  not document `~/.pi/providers/` explicitly, but it is a real pi
  feature (verified against the running container and the `pi-ai`
  source `providers/kimi-coding.ts`). The host has no `~/.pi/providers/`
  because the host's `~/.pi` is the separate `PI_harness` authoring
  repo (see Notes).
- `~/.pi/agent/cursor-sdk-model-list.json` (145 KB, regenerated near-daily
  per the catalog-refresh SOP) is a generated cache and must not be
  managed.
- The DeepSeek key currently lives **only** as the inline literal in
  `models.json`. `DEEPSEEK_API_KEY` is not in `.chezmoidata/api_secrets.yaml`,
  not in spec 11's provider env table, and not exported by
  `~/.config/zsh/rc/secrets.zsh`. So the existing Bitwarden → `secrets.zsh`
  pipeline (approved in the 2026-07-11 api-secrets design) does not yet
  cover DeepSeek.
- Upstream pi (`docs/models.md` §"Value Resolution") supports three forms
  for the `apiKey` field: shell command (`"!cmd"`), env interpolation
  (`"$ENV_VAR"` / `"${ENV_VAR}"`, resolved at request time), and literal.
  `apiKey` is also optional — auth can come from `/login`/`auth.json` or
  `--api-key`. So `models.json` can be committed with
  `"apiKey": "$DEEPSEEK_API_KEY"` and resolve the real key at request time
  once the env var is exported.

## Problem

Bring the remaining stable pi agent + provider configuration under
git-managed `/data/pi-config` and the `dotfiles3` symlink flow, **without
committing any secret material**, and without regressing the
verify-before-commit discipline that `pi-model-provider-swap.sop.md` and
`cursor-sdk-catalog-refresh.sop.md` exist to enforce.

The design must decide, at minimum:

1. Which of the provider files (`settings.json`, `models.json`,
   `ollama-cloud.json`, `cursor-sdk.json`, `cursor-sdk-context-windows.json`)
   become managed + symlinked, and which stay runtime-only.
2. How `models.json`'s DeepSeek `apiKey` is replaced by an env-injected
   form (`"$DEEPSEEK_API_KEY"`) and how the env var enters the existing
   Bitwarden → `secrets.zsh` pipeline (a new `DEEPSEEK_API_KEY` row in
   `.chezmoidata/api_secrets.yaml` + a new Bitwarden Login item + a new
   row in spec 11's provider env table).
3. Whether each new managed file is symlinked (matches current
   `link_resource` pattern) or copied (avoids interactive `/settings` or
   `/model` edits dirtying `/data/pi-config`). Open question Q3 from the
   2026-07-08 design remains unresolved for `settings.json` and now
   applies to `models.json` as well.
4. How to verify, before any commit lands, that
   `deepseek/deepseek-v4-pro` still resolves end-to-end (env export →
   pi request) — the exact failure mode the model-provider-swap SOP was
   written to prevent.
5. Whether `cursor-sdk-model-list.json` is explicitly documented as
   excluded (generated cache, near-daily full rewrites), and whether
   `cursor-sdk-context-windows.json` is managed given it is
   SOP-governed and changes by hand.
6. Whether `~/.pi/providers/` (per-provider user overrides, e.g.
   `kimi-coding/config.json`) is managed too — it lives outside
   `~/.pi/agent/`, so the existing `link_resource` (which links only
   into `~/.pi/agent/`) must be extended with a second link target
   (`~/.pi/providers` → `~/.local/share/pi-config/providers`).

## Acceptance criteria

1. `/data/pi-config` contains the chosen managed provider files under
   `agent/`, with **no** `sk-...`/`apiKey` literal anywhere in its git
   history. `git -C /data/pi-config log -p -- agent/models.json` (and
   equivalent for any other file) shows no committed secret.
2. `models.json` in `/data/pi-config` uses
   `"apiKey": "$DEEPSEEK_API_KEY"` (env interpolation) for the DeepSeek
   provider; no other secret-bearing field is present.
3. `DEEPSEEK_API_KEY` is added to `.chezmoidata/api_secrets.yaml` with a
   Bitwarden item ID / stable item name and a `field` selector, matching
   the existing `OPENROUTER_API_KEY` / `MOONSHOT_API_KEY` / `OLLAMA_API_KEY`
   / `CURSOR_API_KEY` rows; a corresponding Bitwarden Login item with the
   named custom field is created in the user's vault.
4. Spec 11 §"API provider env vars" gains a `DEEPSEEK_API_KEY` row, and
   spec 11 §"Bitwarden items" gains the corresponding item row. Spec 13
   needs no new invariant but the design doc references I-S3 / I-S5.
5. `run_after_configure-pi-agent.sh.tmpl` is extended to `link_resource`
   each newly managed file under `~/.pi/agent/`, **and** to link
   `~/.pi/providers` → `~/.local/share/pi-config/providers` via a new
   `link_pi_root_resource` helper (since `providers/` lives outside
   `~/.pi/agent/`); build mode continues to skip the whole script
   (`{{ if not .build_mode }}` guard unchanged).
6. `cursor-sdk-model-list.json` is explicitly listed in the design as
   **not managed** (generated cache per
   `cursor-sdk-catalog-refresh.sop.md`); `/data/pi-config/.gitignore` is
   updated to defend against it (and any other generated cache) entering
   the repo accidentally.
7. Before the design moves from DRAFT to Approved, the verify-before-commit
   step from `pi-model-provider-swap.sop.md` is reproduced: with
   `DEEPSEEK_API_KEY` exported (via the rendered `secrets.zsh`) and
   `~/.pi/agent/models.json` symlinked to the managed file,
   `pi --model deepseek/deepseek-v4-pro` (or equivalent `/model`
   resolution) resolves and a real request succeeds. This evidence goes
   into the result-log.
8. No sensitive pi runtime path (`auth.json`, `trust.json`, `sessions/`,
   `npm/`, `cache/`, `run-history.jsonl`, `cursor-sdk-model-list.json`)
   becomes managed or enters `/data/pi-config` history.
9. `/data/pi-config/providers/` contains the managed per-provider
   overrides (e.g. `kimi-coding/config.json`); after apply,
   `~/.pi/providers` is a symlink to `~/.local/share/pi-config/providers`
   and the override files resolve through it. The override files contain
   no `apiKey`/secret.
10. The legacy `PI_harness` repo stops tracking the migrated paths
    (`agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows,cursor-sdk-model-list}.json`
    + `providers/`); those paths are gitignored in `PI_harness` so
    chezmoi symlinks do not dirty it. `PI_harness` is documented as
    legacy/superseded by `/data/pi-config`.
11. The DeepSeek key leaked into `PI_harness` history is **rotated** at
    the provider; the new key lives only in Bitwarden → `secrets.zsh` →
    `$DEEPSEEK_API_KEY`. If `PI_harness` was ever public, its history is
    rewritten or the repo archived after rotation. Spec 11 / spec 13's
    forbidden-secret-location list is extended to explicitly name
    `PI_harness.git` (and any host `~/.pi` git repo).

## Notes

- The 2026-07-08 design's open question **Q3** (symlink vs copy for
  `settings.json`, to avoid interactive edits dirtying the repo) is
  inherited here and extended to `models.json`. The design should pick
  one answer for all managed files and justify it, or split per file with
  a rule.
- The 2026-07-11 api-secrets design already established the Bitwarden →
  `secrets.zsh` pattern for `OPENROUTER_API_KEY` etc.; this issue is the
  natural extension for `DEEPSEEK_API_KEY` and should not invent a new
  pipeline.
- **Host vs container (resolved 2026-07-14):** `/data/pi-config` is the
  canonical managed source. `PI_harness`
  (`git@github.com:kkiyama117/PI_harness.git`, the host's `~/.pi/.git`)
  is the **legacy/current** config being grown out of and replaced — the
  goal is to grow `/data/pi-config` and replace the `PI_harness`-tracked
  config with it. The container already follows Model A (no `.git` in
  `~/.pi`, symlinks from `~/.local/share/pi-config/agent/*`); the host
  is being migrated to the same model. Two consequences: (a) `PI_harness`
  must stop tracking the migrated paths and gitignore them so the
  chezmoi symlinks do not dirty it (design §5.7); (b) the plaintext
  DeepSeek key already committed to `PI_harness` history must be
  **rotated** at the provider, and if `PI_harness` was ever public, its
  history rewritten or the repo archived (design S11 / §5.7 step 4).
- The container's `~/.pi/agent/{cursor-sdk.json,cursor-sdk-context-windows.json}`
  are **absent** (host has them); the design's `link_resource` no-ops on
  absent sources, so this is harmless, but the plan should decide whether
  to populate them in `/data/pi-config` (from the host's copies) or leave
  them unmanaged.
- Per AGENTS.md §2, this is a design-level change (touches the
  pi-config repo, the symlink script, the secret pipeline, and specs 11).
  Implementation must not start before the design reaches Approved and a
  plan exists in `docs/plans/`.
- Do not commit provider credentials, OAuth artifacts, API keys, sessions,
  transcripts, trust decisions, or downloaded package checkouts to either
  repository.
