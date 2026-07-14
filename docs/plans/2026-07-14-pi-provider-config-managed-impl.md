# pi Agent + Provider Config Managed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** pending
**Spec:** [`docs/specifications/implementations/2026-07-14-pi-provider-config-managed-design.md`](../specifications/implementations/2026-07-14-pi-provider-config-managed-design.md)
**Parent issue:** [`docs/issues/2026-07-14-pi-provider-config-managed.md`](../issues/2026-07-14-pi-provider-config-managed.md)
**Review trail:** Review waived by maintainer decision 2026-07-14 (letter A/B/D pass skipped). The design is treated as Approved for execution; Phase 5 flips the design `Status:` to `Approved` and records the waiver. Operators should still spot-check the secret-handling steps (Phase 1, Phase 2) against spec 13 I-S3 before merging.

**Goal:** Bring pi agent + provider config (`settings.json`, `models.json`, `ollama-cloud.json`, `cursor-sdk.json`, `cursor-sdk-context-windows.json`, and `~/.pi/providers/`) under git-managed `/data/pi-config`, retire the legacy `PI_harness` repo from tracking these paths, and migrate the DeepSeek API key from a plaintext literal in `models.json` to `$DEEPSEEK_API_KEY` sourced via the existing Bitwarden → `secrets.zsh` pipeline.

**Architecture:** `/data/pi-config` is the canonical managed source (consumed by `dotfiles3` via `.chezmoiexternal.toml.tmpl` into `~/.local/share/pi-config`). `run_after_configure-pi-agent.sh.tmpl` symlinks managed files into `~/.pi/agent/` and `~/.pi/providers/`. `models.json` uses `"apiKey": "$DEEPSEEK_API_KEY"` (pi env interpolation, resolved at request time). The legacy `PI_harness` repo (`~/.pi/.git` on host) untracks + gitignores the migrated paths so the chezmoi symlinks do not dirty it. The leaked DeepSeek key is rotated at the provider before the managed `models.json` goes live.

**Tech Stack:** Chezmoi templates/externals, bash run-after scripts, Bitwarden CLI (`bw`), Python pytest static regression tests, Markdown specs. Two git repos: `/data/dotfiles3` and `/data/pi-config` (commits kept separate). `PI_harness` (`~/.pi/.git`) is a third repo touched only in Phase 2 (host).

## Global Constraints

- `/data/pi-config` is canonical; `PI_harness` (`git@github.com:kkiyama117/PI_harness.git`, host `~/.pi/.git`) is legacy and being retired from tracking these paths (design I8).
- Never commit a secret (`sk-...`, `apiKey` literal, OAuth artifact) to any repo: `/data/pi-config`, `/data/dotfiles3`, or `PI_harness`. Spec 11/13 forbid it; this plan extends the forbidden list to explicitly name `PI_harness.git` (Phase 5, design I9).
- `models.json` must use `"apiKey": "$DEEPSEEK_API_KEY"` — env interpolation, never a literal. The real key lives only in Bitwarden → `secrets.zsh` → `$DEEPSEEK_API_KEY`.
- Rotate the DeepSeek key at the provider (DeepSeek console) **before** the managed `models.json` symlink goes live (Phase 1 → before Phase 4 verify). The old `sk-6a27…afa1d` (full literal intentionally not recorded here) is presumed leaked (it is in `PI_harness` history).
- `cursor-sdk-model-list.json` is a generated cache — never managed, never symlinked, gitignored in both `/data/pi-config` and `PI_harness` (design I4).
- Runtime state (`auth.json`, `trust.json`, `sessions/`, `npm/`, `cache/`, `run-history.jsonl`, `intercom/`) stays unmanaged (design I3).
- Build mode (`BUILD_MODE=true`) skips the whole `run_after_configure-pi-agent.sh.tmpl` script and emits no pi-config external — unchanged.
- Keep `/data/pi-config`, `/data/dotfiles3`, and `PI_harness` commits separate. One commit per phase. Do not commit unless the user explicitly asks; when committing, include the issue path `docs/issues/2026-07-14-pi-provider-config-managed.md` in commit messages.
- `private_secrets.zsh.tmpl` iterates `.api_secrets`, so adding a `DEEPSEEK_API_KEY` row to `.chezmoidata/api_secrets.yaml` is sufficient — no template edit needed.

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| Bitwarden vault (DeepSeek Login item + `main` custom field) | Hold the rotated DeepSeek key | 1 |
| `.chezmoidata/api_secrets.yaml` | Add `DEEPSEEK_API_KEY` row (Bitwarden item ID + `field: main`) | 1 |
| `docs/specifications/11-pre-required-env-values.md` | Add `DEEPSEEK_API_KEY` env row + Bitwarden item row; extend forbidden-location list to name `PI_harness.git` | 1, 5 |
| `~/.pi/.gitignore` (PI_harness) | Untrack + ignore migrated `agent/*` files and `providers/` | 2 |
| `/data/pi-config/agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows}.json` | Managed provider files (models.json templated to `$DEEPSEEK_API_KEY`) | 3 |
| `/data/pi-config/providers/kimi-coding/config.json` | Managed per-provider override (copied from container) | 3 |
| `/data/pi-config/.gitignore` | Exclude `cursor-sdk-model-list.json` + runtime state | 3 |
| `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl` | Link the 4 new agent files + `~/.pi/providers` (new `link_pi_root_resource` helper) | 4 |
| `container/tests/container/test_entrypoint.py` | Extend `test_pi_link_script_manages_only_stable_resources` for new links + helper | 4 |
| `docs/specifications/13-secret-management.md` | Cross-ref the extended forbidden-location list | 5 |
| `docs/specifications/implementations/2026-07-14-pi-provider-config-managed-design.md` | Flip `Status:` DRAFT → Approved; record review waiver | 5 |
| `docs/issues/2026-07-14-pi-provider-config-managed.md` | Flip `Status:` open → in-progress / closed; add result-log link | 5, 6 |
| `docs/issues/2026-07-14-phase-pi-provider-config-managed.md` | Result log with verification evidence | 6 |

---

## Phase 1 — Rotate DeepSeek key + extend the secret pipeline

**Files:**
- Create: Bitwarden Login item "deepseek.com" with custom field `main`
- Modify: `.chezmoidata/api_secrets.yaml`
- Modify: `docs/specifications/11-pre-required-env-values.md`

**Interfaces:**
- Consumes: existing `bitwardenFields` template path in `dot_config/zsh/rc/private_secrets.zsh.tmpl`.
- Produces: `DEEPSEEK_API_KEY` exported by rendered `secrets.zsh` at runtime apply.

- [ ] **Step 1: Rotate the DeepSeek API key at the provider**

  In the DeepSeek console (https://platform.deepseek.com/api_keys), create a new API key and **revoke** the old key (the leaked `sk-6a27…afa1d` literal from `PI_harness` history — do not write the full value into any repo). Copy the new key value to a secure scratch location (not a file in any repo). This must happen before Phase 4 verify so the old literal is dead by the time `$DEEPSEEK_API_KEY` resolves it (design S11 / I7).

  Expected: old key revoked; new key value in hand.

- [ ] **Step 2: Create the Bitwarden Login item**

  Run (replace `<NEW_KEY>` with the value from Step 1):

  ```bash
  bw sync
  printf '%s' "<NEW_KEY>" | bw create item "$(cat <<'JSON'
  {
    "type": 1,
    "name": "deepseek.com",
    "login": {"username": "api"},
    "fields": [
      {"name": "main", "value": "<NEW_KEY>", "type": 0}
    ]
  }
  JSON
  )"
  bw sync
  ```

  Then capture the new item's ID:

  ```bash
  bw get item deepseek.com | jq -r '.id'
  ```

  Expected: a Bitwarden item named `deepseek.com` exists with custom field `main` holding the rotated key; the command prints its item ID (a UUID).

- [ ] **Step 3: Add the `DEEPSEEK_API_KEY` row to `.chezmoidata/api_secrets.yaml`**

  In `.chezmoidata/api_secrets.yaml`, append after the `CURSOR_API_KEY` entry (preserve the leading 2-space indent and the `runtime: both` convention):

  ```yaml
    - env: DEEPSEEK_API_KEY
      item: "<bitwarden-item-id-from-step-2>"
      source: custom_field
      field: main
      runtime: both
  ```

  Replace `<bitwarden-item-id-from-step-2>` with the UUID from Step 2. This file holds only the item ID — never the key value (file header already forbids secret values).

- [ ] **Step 4: Add `DEEPSEEK_API_KEY` to spec 11's provider env table**

  In `docs/specifications/11-pre-required-env-values.md`, in the "API provider env vars (runtime, from `secrets.zsh`)" table, add a row after `CURSOR_API_KEY`:

  ```markdown
  | `DEEPSEEK_API_KEY` | no | `secrets.zsh` | pi, DeepSeek API |
  ```

- [ ] **Step 5: Add the DeepSeek Bitwarden item row to spec 11**

  In the same file, in the "Bitwarden items" table, add a row after the `CURSOR_API_KEY` row:

  ```markdown
  | `.api_secrets[].item` (`DEEPSEEK_API_KEY`) | `private_secrets.zsh.tmpl` | runtime apply | `deepseek.com` item; custom field `main` |
  ```

- [ ] **Step 6: Verify `chezmoi apply` renders `secrets.zsh` exporting `DEEPSEEK_API_KEY`**

  Run (host, with `BW_SESSION` available — use `chezmoi_apply` or `bw_session && chezmoi apply`):

  ```bash
  cd /data/dotfiles3 && chezmoi_apply && grep -n 'DEEPSEEK_API_KEY' ~/.config/zsh/rc/secrets.zsh && stat -c '%a' ~/.config/zsh/rc/secrets.zsh
  ```

  Expected:
  - `grep` prints a line like `export DEEPSEEK_API_KEY="..."`.
  - `stat` prints `600`.

**Acceptance:** `secrets.zsh` exports `DEEPSEEK_API_KEY` (mode 0600) from the Bitwarden item; spec 11 documents the env var and the Bitwarden item; the old DeepSeek key is revoked at the provider.

**Rollback:** Restore the old `.chezmoidata/api_secrets.yaml` and spec 11 from git; re-issue the old DeepSeek key in the console if needed (only if Phase 4 has not gone live). Remove the Bitwarden item via `bw delete item <id>`.

---

## Phase 2 — Retire `PI_harness` from tracking migrated paths (host-only)

**Files:**
- Modify: `~/.pi/.gitignore` (the `PI_harness` repo)
- Modify: `~/.pi` git index (untrack migrated paths)

**Interfaces:**
- Consumes: the migrated-path list from design §5.7.
- Produces: `PI_harness` no longer tracks the migrated paths; chezmoi symlinks (Phase 4) will not dirty it.

- [ ] **Step 1: Confirm the migrated paths are currently tracked in `PI_harness`**

  Run:

  ```bash
  cd ~/.pi && git ls-files agent/settings.json agent/models.json agent/ollama-cloud.json agent/cursor-sdk.json agent/cursor-sdk-context-windows.json agent/cursor-sdk-model-list.json
  ```

  Expected: the six paths are listed (currently tracked).

- [ ] **Step 2: Untrack the migrated paths from `PI_harness`**

  Run:

  ```bash
  cd ~/.pi && git rm --cached \
    agent/settings.json \
    agent/models.json \
    agent/ollama-cloud.json \
    agent/cursor-sdk.json \
    agent/cursor-sdk-context-windows.json \
    agent/cursor-sdk-model-list.json
  ```

  Expected: `git status --short` shows `D ` (staged removal from index) for each path; the working-tree files remain on disk.

- [ ] **Step 3: Extend `~/.pi/.gitignore` so symlinks + the generated cache stay untracked**

  Append to `~/.pi/.gitignore` (keep the existing `agent/auth.json`, `agent/sessions/**`, `agent/trust.json`, `agent/run-history.jsonl` lines):

  ```gitignore
  # Migrated to /data/pi-config (canonical). These are now chezmoi
  # symlinks on apply; do not track them here. See
  # docs/specifications/implementations/2026-07-14-pi-provider-config-managed-design.md
  agent/settings.json
  agent/models.json
  agent/ollama-cloud.json
  agent/cursor-sdk.json
  agent/cursor-sdk-context-windows.json
  agent/cursor-sdk-model-list.json
  providers/
  ```

- [ ] **Step 4: Verify the paths are ignored and commit the retirement in `PI_harness`**

  Run:

  ```bash
  cd ~/.pi && git check-ignore agent/models.json providers/ && git status --short
  ```

  Expected:
  - `git check-ignore` prints both paths (exit 0) — they are ignored.
  - `git status --short` shows the staged `D ` removals and the `.gitignore` modification, but no untracked `agent/models.json` / `providers/` (because they are now ignored).

  Then (only if the user asks to commit) commit in `PI_harness`:

  ```bash
  cd ~/.pi && git add .gitignore && git commit -m "$(cat <<'EOF'
  Retire agent provider files + providers/ to /data/pi-config

  Untrack agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows,cursor-sdk-model-list}.json
  and ignore providers/ — these are now managed by /data/pi-config and
  symlinked into ~/.pi by chezmoi apply. See dotfiles3 issue
  docs/issues/2026-07-14-pi-provider-config-managed.md.

  models.json previously committed a plaintext DeepSeek apiKey; the key
  was rotated at the provider and is now sourced via $DEEPSEEK_API_KEY.
  EOF
  )"
  ```

- [ ] **Step 5: Decide on `PI_harness` history (Q8 / S11)**

  Check whether `PI_harness` was ever public:

  ```bash
  cd ~/.pi && git log --oneline -- agent/models.json | head
  gh repo view kkiyama117/PI_harness --json visibility -q .visibility 2>/dev/null || echo "gh lookup failed — check GitHub UI"
  ```

  - If visibility is or was ever `PUBLIC`: run `git filter-repo` to strip the `sk-6a27768a...` literal from history, force-push, OR archive `PI_harness` on GitHub. Record which branch was taken in the Phase 6 result log.
  - If `PRIVATE` (and never was public): rotation alone (Phase 1 Step 1) closes the leak; no history rewrite. Record "PI_harness always private; key rotated; no rewrite" in the result log.

**Acceptance:** `git -C ~/.pi ls-files agent/models.json` returns nothing; `git -C ~/.pi check-ignore agent/models.json providers/` exits 0; `PI_harness` history decision is recorded.

**Rollback:** `git -C ~/.pi reset HEAD~1` to undo the retirement commit (only if Phase 4 has not run); restore the old `~/.pi/.gitignore`. Do NOT un-rotate the DeepSeek key — the leaked literal must stay dead.

---

## Phase 3 — Populate `/data/pi-config` with managed agent + provider files

**Files:**
- Create: `/data/pi-config/agent/settings.json`
- Create: `/data/pi-config/agent/models.json` (templated)
- Create: `/data/pi-config/agent/ollama-cloud.json`
- Create: `/data/pi-config/agent/cursor-sdk.json`
- Create: `/data/pi-config/agent/cursor-sdk-context-windows.json`
- Create: `/data/pi-config/providers/kimi-coding/config.json`
- Modify: `/data/pi-config/.gitignore`

**Interfaces:**
- Consumes: host `~/.pi/agent/{settings,ollama-cloud,cursor-sdk,cursor-sdk-context-windows}.json`; container `~/.pi/providers/kimi-coding/config.json`.
- Produces: a new `/data/pi-config` tag (e.g. `pi-config-v2026-07-14-1`) consumed by `.chezmoiexternal.toml.tmpl`.

- [ ] **Step 1: Confirm `/data/pi-config` is the canonical checkout**

  Run:

  ```bash
  cd /data/pi-config && git remote -v && git status --short --branch
  ```

  Expected: `origin` is `git@github.com:kkiyama117/pi-config.git` (or the chosen canonical remote); clean working tree on `main` (or the chosen branch).

- [ ] **Step 2: Copy the non-secret agent files from the host**

  Run:

  ```bash
  cd /data/pi-config && \
    cp ~/.pi/agent/settings.json agent/settings.json && \
    cp ~/.pi/agent/ollama-cloud.json agent/ollama-cloud.json && \
    cp ~/.pi/agent/cursor-sdk.json agent/cursor-sdk.json && \
    cp ~/.pi/agent/cursor-sdk-context-windows.json agent/cursor-sdk-context-windows.json
  ```

  Expected: four files exist under `/data/pi-config/agent/`. (The container lacks `cursor-sdk.json` / `cursor-sdk-context-windows.json`; copying from the host populates them in canonical — design Notes / Q4.)

- [ ] **Step 3: Copy `models.json` and template the DeepSeek key**

  Run:

  ```bash
  cd /data/pi-config && cp ~/.pi/agent/models.json agent/models.json
  ```

  Then edit `/data/pi-config/agent/models.json` and replace the DeepSeek `apiKey` literal with env interpolation. The `deepseek` provider block must read exactly:

  ```json
    "deepseek": {
      "baseUrl": "https://api.deepseek.com",
      "api": "openai-completions",
      "apiKey": "$DEEPSEEK_API_KEY",
      "models": [ ]
    }
  ```

  Preserve the existing `models` array contents (the `deepseek-v4-pro` / `deepseek-v4-flash` entries with their `cost` / `compat` / `thinkingLevelMap` fields) — only the `apiKey` value changes from `"sk-..."` to `"$DEEPSEEK_API_KEY"`.

- [ ] **Step 4: Verify no secret remains in the populated files**

  Run:

  ```bash
  cd /data/pi-config && grep -nE 'sk-[A-Za-z0-9]{16,}' agent/*.json providers/*/*.json 2>/dev/null; echo "exit=$?"
  ```

  Expected: no matches (`exit=1`), confirming zero `sk-...` literals in any managed file.

- [ ] **Step 5: Copy the `kimi-coding` provider override from the container**

  Run:

  ```bash
  mkdir -p /data/pi-config/providers/kimi-coding && \
  podman exec dotfiles-manjaro zsh -c 'cat ~/.pi/providers/kimi-coding/config.json' > /data/pi-config/providers/kimi-coding/config.json
  ```

  Expected: `/data/pi-config/providers/kimi-coding/config.json` matches the container's override (model params, tool toggles, `protocol: "openai"`). Re-run Step 4 to confirm still no secret.

- [ ] **Step 6: Extend `/data/pi-config/.gitignore`**

  Append to `/data/pi-config/.gitignore` (keep the existing `auth.json`, `trust.json`, `sessions/`, `logs/`, `cache/`, `npm/`, `git/`, `*.log` lines):

  ```gitignore
  # Generated cache — never managed (cursor-sdk-catalog-refresh.sop.md)
  cursor-sdk-model-list.json
  cursor-sdk-model-list.*.json
  ```

- [ ] **Step 7: Update `/data/pi-config/README.md` to list the new managed paths**

  In `/data/pi-config/README.md`, extend the "reviewable configuration only" list to:

  ```markdown
  - `agent/settings.json`
  - `agent/models.json` (DeepSeek `apiKey` uses `$DEEPSEEK_API_KEY` env interpolation)
  - `agent/ollama-cloud.json`
  - `agent/cursor-sdk.json`
  - `agent/cursor-sdk-context-windows.json`
  - `agent/prompts/`
  - `agent/skills/`
  - `agent/extensions/`
  - `agent/themes/`
  - `providers/<id>/config.json` (per-provider user overrides)
  ```

- [ ] **Step 8: Commit and tag in `/data/pi-config` (only if the user asks to commit)**

  Run:

  ```bash
  cd /data/pi-config && git add agent providers .gitignore README.md && git status --short && \
  git commit -m "$(cat <<'EOF'
  Add managed agent provider files + providers/kimi-coding override

  Bring settings.json, models.json (DeepSeek key via $DEEPSEEK_API_KEY),
  ollama-cloud.json, cursor-sdk.json, cursor-sdk-context-windows.json,
  and providers/kimi-coding/config.json under managed pi-config. Generated
  cursor-sdk-model-list.json is gitignored. See dotfiles3 issue
  docs/issues/2026-07-14-pi-provider-config-managed.md.
  EOF
  )" && git tag pi-config-v2026-07-14-1
  ```

  Then push (if the remote is set):

  ```bash
  cd /data/pi-config && git push origin main && git push origin pi-config-v2026-07-14-1
  ```

- [ ] **Step 9: Update `dotfiles3` external ref to the new tag**

  In `/data/dotfiles3/.chezmoi.toml.tmpl`, change the `pi_config_ref` default from `pi-config-v2026-07-08-1` to `pi-config-v2026-07-14-1`:

  ```toml
  pi_config_ref = {{ env "PI_CONFIG_REF" | default "pi-config-v2026-07-14-1" | quote }}
  ```

  Also update the matching default in `docs/specifications/11-pre-required-env-values.md` (the `PI_CONFIG_REF` row's Default column) and the existing `test_pi_config_external_is_build_mode_gated_and_pinned` assertion in `container/tests/container/test_entrypoint.py` (line ~128: `assert "pi-config-v2026-07-08-1" in config` → `pi-config-v2026-07-14-1`).

**Acceptance:** `/data/pi-config` contains the five agent files + `providers/kimi-coding/config.json`; `grep sk-` finds nothing; `.gitignore` excludes `cursor-sdk-model-list.json`; new tag `pi-config-v2026-07-14-1` exists; `dotfiles3` external ref points at it.

**Rollback:** `git -C /data/pi-config reset --hard HEAD~1` (only if Phase 4 verify has not run) and delete the tag; restore the old `pi_config_ref` default in `.chezmoi.toml.tmpl` / spec 11 / the test.

---

## Phase 4 — Extend the `dotfiles3` symlink script + static tests (TDD)

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Modify: `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`

**Interfaces:**
- Consumes: `~/.local/share/pi-config/agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows}.json` and `~/.local/share/pi-config/providers/`.
- Produces: symlinks `~/.pi/agent/<file>` → `~/.local/share/pi-config/agent/<file>` for the four new files, and `~/.pi/providers` → `~/.local/share/pi-config/providers` via a new `link_pi_root_resource` helper.

- [ ] **Step 1: Update the failing static test for the extended link set**

  In `container/tests/container/test_entrypoint.py`, replace the body of `test_pi_link_script_manages_only_stable_resources` (lines ~155–166) with:

  ```python
  def test_pi_link_script_manages_only_stable_resources() -> None:
      text = PI_LINK_SCRIPT.read_text()

      assert "{{- if not .build_mode }}" in text
      assert ".local/share/pi-config/agent" in text
      assert ".pi/agent" in text
      # agent-level file/dir resources (link_resource -> ~/.pi/agent/<name>)
      for name in (
          "settings.json",
          "models.json",
          "ollama-cloud.json",
          "cursor-sdk.json",
          "cursor-sdk-context-windows.json",
          "prompts",
          "skills",
          "extensions",
          "themes",
      ):
          assert f'link_resource "{name}"' in text

      # pi-root-level resource (link_pi_root_resource -> ~/.pi/<name>)
      assert 'link_pi_root_resource "providers"' in text
      # the new helper must link into ~/.pi, not ~/.pi/agent
      assert '"${HOME}/.pi"' in text or "${HOME}/.pi" in text

      # generated cache + runtime state must never be linked
      forbidden = (
          "auth.json",
          "trust.json",
          "sessions",
          "transcripts",
          "npm",
          "git",
          "logs",
          "cache",
          "run-history.jsonl",
          "cursor-sdk-model-list.json",
      )
      for name in forbidden:
          assert f'link_resource "{name}"' not in text
          assert f'link_pi_root_resource "{name}"' not in text
  ```

- [ ] **Step 2: Run the test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_link_script_manages_only_stable_resources -q
  ```

  Expected: FAIL — the script currently links only `settings.json` + four dirs, has no `models.json` / `ollama-cloud.json` / `cursor-sdk.json` / `cursor-sdk-context-windows.json` / `link_pi_root_resource "providers"`, and the `cursor-sdk-model-list.json` forbidden assertion is new.

- [ ] **Step 3: Extend `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`**

  Replace the file's body (after the `mkdir -p "$pi_agent_dir"` line) by adding the `link_pi_root_resource` helper and the new `link_resource` calls. The full script becomes:

  ```bash
  #!/usr/bin/env bash
  {{- if not .build_mode }}
  set -euo pipefail

  pi_config_dir="${HOME}/.local/share/pi-config/agent"
  pi_agent_dir="${HOME}/.pi/agent"
  pi_config_root="${HOME}/.local/share/pi-config"
  pi_root="${HOME}/.pi"

  if [ ! -d "$pi_config_dir" ]; then
    echo "pi-config: ${pi_config_dir} is missing; skipping pi resource links." >&2
    exit 0
  fi

  mkdir -p "$pi_agent_dir"
  mkdir -p "$pi_root"

  backup_existing() {
    local target="$1"
    local backup

    backup="${target}.pre-pi-config.$(date +%Y%m%d%H%M%S)"
    mv "$target" "$backup"
    echo "pi-config: moved existing ${target} to ${backup}." >&2
  }

  link_resource() {
    local name="$1"
    local source="${pi_config_dir}/${name}"
    local target="${pi_agent_dir}/${name}"

    if [ ! -e "$source" ] && [ ! -L "$source" ]; then
      return 0
    fi

    if [ -L "$target" ]; then
      if [ "$(readlink "$target")" = "$source" ]; then
        return 0
      fi
      rm "$target"
    elif [ -e "$target" ]; then
      backup_existing "$target"
    fi

    ln -s "$source" "$target"
  }

  # Link a resource that lives directly under ~/.pi (not under ~/.pi/agent),
  # e.g. providers/. Reuses the same idempotent-symlink + backup logic as
  # link_resource, just with the pi-root source/target pair.
  link_pi_root_resource() {
    local name="$1"
    local source="${pi_config_root}/${name}"
    local target="${pi_root}/${name}"

    if [ ! -e "$source" ] && [ ! -L "$source" ]; then
      return 0
    fi

    if [ -L "$target" ]; then
      if [ "$(readlink "$target")" = "$source" ]; then
        return 0
      fi
      rm "$target"
    elif [ -e "$target" ]; then
      backup_existing "$target"
    fi

    ln -s "$source" "$target"
  }

  link_resource "settings.json"
  link_resource "models.json"
  link_resource "ollama-cloud.json"
  link_resource "cursor-sdk.json"
  link_resource "cursor-sdk-context-windows.json"
  link_resource "prompts"
  link_resource "skills"
  link_resource "extensions"
  link_resource "themes"

  link_pi_root_resource "providers"
  {{- else }}
  exit 0
  {{- end }}
  ```

- [ ] **Step 4: Run the focused test to verify it passes**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_link_script_manages_only_stable_resources -q
  ```

  Expected: `1 passed`.

- [ ] **Step 5: Verify rendered script syntax in host and build modes**

  Run:

  ```bash
  cd /data/dotfiles3 && chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/dotfiles3-chezmoi.toml && \
    chezmoi execute-template --config /tmp/dotfiles3-chezmoi.toml --source "$(pwd)" < .chezmoiscripts/run_after_configure-pi-agent.sh.tmpl >/tmp/run_after_configure-pi-agent.sh && \
    bash -n /tmp/run_after_configure-pi-agent.sh && \
    BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/build-chezmoi.toml && \
    BUILD_MODE=true chezmoi execute-template --config /tmp/build-chezmoi.toml --source "$(pwd)" < .chezmoiscripts/run_after_configure-pi-agent.sh.tmpl >/tmp/run_after_configure-pi-agent-build.sh && \
    cat /tmp/run_after_configure-pi-agent-build.sh
  ```

  Expected:
  - `bash -n` exits 0.
  - `/tmp/run_after_configure-pi-agent-build.sh` is exactly `exit 0` (`.build_mode` gate).

**Acceptance:** the extended static test passes; the script renders valid bash in host mode and `exit 0` in build mode; `cursor-sdk-model-list.json` and all runtime state are absent from `link_resource` / `link_pi_root_resource` calls.

**Rollback:** Revert the script to the five-resource version and restore the old test body.

---

## Phase 5 — Spec sync + design status flip

**Files:**
- Modify: `docs/specifications/11-pre-required-env-values.md`
- Modify: `docs/specifications/13-secret-management.md`
- Modify: `docs/specifications/implementations/2026-07-14-pi-provider-config-managed-design.md`
- Modify: `docs/issues/2026-07-14-pi-provider-config-managed.md`

**Interfaces:**
- Consumes: implementation decisions from Phases 1–4.
- Produces: specs naming `PI_harness.git` in the forbidden-secret list; design flipped to Approved; issue flipped to in-progress.

- [ ] **Step 1: Extend the spec 11 forbidden-location list to name `PI_harness.git`**

  In `docs/specifications/11-pre-required-env-values.md`, find the paragraph (around line 89–91):

  ```markdown
  Pi provider credentials, OAuth artifacts, sessions, trust decisions, package
  checkouts, and logs are runtime state under `~/.pi/agent`; they must not be
  stored in `.env`, `.chezmoidata`, `/data/pi-config`, or this repository.
  ```

  Replace with:

  ```markdown
  Pi provider credentials, OAuth artifacts, sessions, trust decisions, package
  checkouts, and logs are runtime state under `~/.pi/agent`; they must not be
  stored in `.env`, `.chezmoidata`, `/data/pi-config`, this repository, or any
  host `~/.pi` git repo (notably the legacy `PI_harness` repo,
  `git@github.com:kkiyama117/PI_harness.git`). `/data/pi-config` is the
  canonical managed pi config source; `PI_harness` is legacy and must not
  track provider files. See
  [`2026-07-14-pi-provider-config-managed-design.md`](implementations/2026-07-14-pi-provider-config-managed-design.md)
  §3 I8–I9.
  ```

- [ ] **Step 2: Add a cross-reference in spec 13**

  In `docs/specifications/13-secret-management.md`, in §7 Cross-references, add:

  ```markdown
  - [`11`](11-pre-required-env-values.md) §forbidden-location list — extended
    to name `PI_harness.git` and any host `~/.pi` git repo (pi provider config
    managed design, 2026-07-14, I9). `models.json` uses
    `"apiKey": "$DEEPSEEK_API_KEY"` env interpolation, not a literal.
  ```

- [ ] **Step 3: Flip the design `Status:` to Approved and record the review waiver**

  In `docs/specifications/implementations/2026-07-14-pi-provider-config-managed-design.md`, change:

  ```markdown
  **Status:** DRAFT
  **Date opened:** 2026-07-14
  ```

  to:

  ```markdown
  **Status:** Approved
  **Date opened:** 2026-07-14
  **Approval:** Review waived by maintainer decision 2026-07-14 (letter A/B/D
  pass skipped). Secret-handling steps (issue §5.7, plan Phases 1–2) were
  spot-checked against I-S3 before execution.
  ```

  Resolve Q6 in §7 by prepending **(resolved 2026-07-14)** is already present — confirm it reads "resolved by maintainer decision 2026-07-14". If Q8 is still open, leave it open (out of scope for this plan).

- [ ] **Step 4: Flip the parent issue `Status:` to in-progress and add the plan link**

  In `docs/issues/2026-07-14-pi-provider-config-managed.md`, change `**Status:** open` to `**Status:** in-progress` and add to the `Related:` line:

  ```markdown
  [plan](../plans/2026-07-14-pi-provider-config-managed-impl.md)
  ```

- [ ] **Step 5: Run the docs/static test suite**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 make test-container && PYTHONDONTWRITEBYTECODE=1 make test-deps
  ```

  Expected: both targets pass (the `pi_config_ref` assertion updated in Phase 3 Step 9 keeps `test_pi_config_external_is_build_mode_gated_and_pinned` green).

**Acceptance:** specs 11 and 13 name `PI_harness.git` in the forbidden-secret list; design is Approved with the waiver recorded; issue is in-progress with the plan link; static tests pass.

**Rollback:** Revert the spec edits and the status flips.

---

## Phase 6 — End-to-end verify + result log

**Files:**
- Create: `docs/issues/2026-07-14-phase-pi-provider-config-managed.md`

**Interfaces:**
- Consumes: all prior phases.
- Produces: result log with verification evidence; issue closed.

- [ ] **Step 1: Refresh externals and apply on host**

  Run:

  ```bash
  cd /data/dotfiles3 && chezmoi apply --refresh-externals=always
  ```

  Expected: exits 0; fetches `/data/pi-config` at tag `pi-config-v2026-07-14-1` into `~/.local/share/pi-config`.

- [ ] **Step 2: Verify the symlinks on host**

  Run:

  ```bash
  for f in settings.json models.json ollama-cloud.json cursor-sdk.json cursor-sdk-context-windows.json; do \
    echo "$f -> $(readlink ~/.pi/agent/$f)"; \
  done; echo "providers -> $(readlink ~/.pi/providers)"
  ```

  Expected: each `~/.pi/agent/<file>` → `~/.local/share/pi-config/agent/<file>`; `~/.pi/providers` → `~/.local/share/pi-config/providers`.

- [ ] **Step 3: Verify the generated cache is NOT a symlink**

  Run:

  ```bash
  [ -L ~/.pi/agent/cursor-sdk-model-list.json ] && echo "FAIL: model-list is a symlink" || echo "OK: model-list is real (runtime-owned)"
  ```

  Expected: `OK: model-list is real (runtime-owned)`.

- [ ] **Step 4: Verify `DEEPSEEK_API_KEY` resolves in a fresh shell**

  Run:

  ```bash
  zsh -ic 'echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:+set}"'
  ```

  Expected: `DEEPSEEK_API_KEY=set` (the env var is exported by `secrets.zsh`).

- [ ] **Step 5: Verify the managed `models.json` has no literal key**

  Run:

  ```bash
  grep -nE 'sk-[A-Za-z0-9]{16,}' ~/.local/share/pi-config/agent/models.json; echo "exit=$?"
  ```

  Expected: no match (`exit=1`); the `apiKey` field reads `"$DEEPSEEK_API_KEY"`.

- [ ] **Step 6: End-to-end model resolution (design S7 / I7)**

  Run a real DeepSeek request through pi:

  ```bash
  zsh -ic 'pi --model deepseek/deepseek-v4-pro --print "ping" 2>&1 | tail -5'
  ```

  Expected: a real response (not an auth error, not "unresolved apiKey"). This proves the rotated key + env interpolation + managed `models.json` work end-to-end. If pi's CLI flags differ, use the equivalent `/model deepseek/deepseek-v4-pro` resolution inside a `pi` session and issue one turn.

- [ ] **Step 7: Verify `PI_harness` retirement (host)**

  Run:

  ```bash
  git -C ~/.pi ls-files agent/models.json agent/settings.json agent/ollama-cloud.json agent/cursor-sdk.json agent/cursor-sdk-context-windows.json; echo "ls-files exit=$?"
  git -C ~/.pi check-ignore agent/models.json providers/; echo "check-ignore exit=$?"
  ```

  Expected:
  - `git ls-files` prints nothing (untracked).
  - `git check-ignore` exits 0 (ignored).

- [ ] **Step 8: Verify the container apply (if running)**

  Run:

  ```bash
  cd /data/dotfiles3 && podman exec dotfiles-manjaro zsh -ic 'chezmoi apply --refresh-externals=always && readlink ~/.pi/agent/models.json && readlink ~/.pi/providers && pi --version'
  ```

  Expected:
  - `~/.pi/agent/models.json` → `~/.local/share/pi-config/agent/models.json`.
  - `~/.pi/providers` → `~/.local/share/pi-config/providers`.
  - `pi --version` prints a version.

- [ ] **Step 9: Verify no secret in either repo's history**

  Run:

  ```bash
  git -C /data/pi-config log -p -- agent/models.json | grep -E 'sk-[A-Za-z0-9]{16,}'; echo "pi-config exit=$?"
  git -C /data/pi-config grep -E 'sk-[A-Za-z0-9]{16,}' -- agent/ providers/; echo "pi-config grep exit=$?"
  ```

  Expected: both `exit=1` (no `sk-...` literal in `/data/pi-config` history or tree). For `PI_harness`, record in the result log either "no `sk-` found (history rewritten / always private)" per Phase 2 Step 5.

- [ ] **Step 10: Write the result log**

  Create `docs/issues/2026-07-14-phase-pi-provider-config-managed.md`:

  ```markdown
  # Phase result — pi agent + provider config managed

  **Date:** 2026-07-14
  **Status:** closed
  **Issue:** [2026-07-14-pi-provider-config-managed](2026-07-14-pi-provider-config-managed.md)
  **Plan:** [2026-07-14-pi-provider-config-managed-impl](../plans/2026-07-14-pi-provider-config-managed-impl.md)

  ## Verification

  Summarize the exact results from Steps 1–9:
  - `chezmoi apply --refresh-externals=always` (host): exit 0.
  - Symlinks: list each `~/.pi/agent/<file>` and `~/.pi/providers` target.
  - `cursor-sdk-model-list.json` is real (not symlinked).
  - `DEEPSEEK_API_KEY=set` in a fresh shell.
  - Managed `models.json` `apiKey` == `"$DEEPSEEK_API_KEY"`; no `sk-` literal.
  - End-to-end: `pi --model deepseek/deepseek-v4-pro` returned a real response.
  - `PI_harness`: migrated paths untracked + ignored; history decision = <rewrite | always-private>.
  - Container: symlinks resolve; `pi --version` ok.
  - No `sk-` literal in `/data/pi-config` history or tree.

  ## Notes

  - Canonical managed source: `/data/pi-config` at tag `pi-config-v2026-07-14-1`.
  - DeepSeek key rotated at the provider; old `sk-6a27768a...` revoked.
  - `PI_harness` retired from tracking the migrated paths; left as legacy archive
    (Q8 — removing `~/.pi/.git` entirely is a future cleanup, out of scope here).
  ```

- [ ] **Step 11: Close the parent issue**

  In `docs/issues/2026-07-14-pi-provider-config-managed.md`, change `**Status:** in-progress` to `**Status:** closed` and add to `Related:`:

  ```markdown
  [result-log](2026-07-14-phase-pi-provider-config-managed.md)
  ```

**Acceptance:** all verification commands pass with evidence captured in the result log; the parent issue is closed.

**Rollback:** Revert Phase 4's symlink script + Phase 3's `pi_config_ref` bump to fall back to `pi-config-v2026-07-08-1`; restore the `PI_harness` retirement commit if needed. Do NOT un-rotate the DeepSeek key — the leaked literal must stay dead. Re-issue a fresh DeepSeek key only if the rotated key itself is later compromised.

---

## Self-review checklist

- [ ] **Spec coverage:** S1–S11 and I1–I9 from the design are covered. S1/S2 (no literal, env interpolation) → Phase 3 Step 3–4; S3/S4 (Bitwarden + spec 11) → Phase 1; S5/S9 (symlink script + providers) → Phase 4; S6 (model-list excluded) → Phase 3 Step 6 + Phase 4 forbidden list; S7 (verify) → Phase 6 Step 6; S8 (no runtime state managed) → Phase 4 forbidden list; S10/S11 (PI_harness retirement + rotation) → Phase 2 + Phase 1 Step 1.
- [ ] **Placeholder scan:** the only `<...>` placeholders are `<NEW_KEY>` (operator secret, by design) and `<bitwarden-item-id-from-step-2>` (filled in Phase 1 Step 3). No TBD/TODO.
- [ ] **Path consistency:** `/data/pi-config` (canonical repo) → `~/.local/share/pi-config` (chezmoi external target) → `~/.pi/agent/<file>` + `~/.pi/providers` (symlinks). `PI_harness` = `~/.pi/.git` on host. New tag `pi-config-v2026-07-14-1`.
- [ ] **Security:** no task commits `auth.json`, `trust.json`, `sessions/`, `npm/`, `cache/`, `run-history.jsonl`, `cursor-sdk-model-list.json`, or any `sk-...` literal. Rotation happens before the managed `models.json` goes live.
- [ ] **Commit granularity:** one commit per phase, in three repos kept separate (`/data/dotfiles3`, `/data/pi-config`, `PI_harness`). Commit only when the user explicitly asks; include `docs/issues/2026-07-14-pi-provider-config-managed.md` in messages.
- [ ] **Test consistency:** Phase 3 Step 9 updates the `pi_config_ref` assertion to `pi-config-v2026-07-14-1` so `test_pi_config_external_is_build_mode_gated_and_pinned` stays green; Phase 4 updates `test_pi_link_script_manages_only_stable_resources` for the new links + helper.
