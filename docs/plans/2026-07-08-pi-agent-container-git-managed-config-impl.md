# pi Agent Container Install + External Config - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** pending
**Spec:** [`docs/specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md`](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md)
**Parent issue:** [`docs/issues/2026-07-08-pi-agent-container-git-managed-config.md`](../issues/2026-07-08-pi-agent-container-git-managed-config.md)
**Review trail:** Not yet reviewed. This plan depends on resolving the DRAFT design's external-ref pinning question with tag `pi-config-v2026-07-08-1`.

**Goal:** Install the `pi` CLI in the container and move stable pi config resources into an external `/data/pi-config` git repository consumed by `dotfiles3` via `.chezmoiexternal.toml.tmpl`.

**Architecture:** Keep `/data/pi-config` as the independent authoring checkout and `https://github.com/kkiyama117/pi-config.git` as the default chezmoi external source. `dotfiles3` fetches that repo to `~/.local/share/pi-config`, then an idempotent chezmoi run-after script links only stable resources into `~/.pi/agent`; mutable pi runtime state remains unmanaged. The container installs the upstream npm package `@earendil-works/pi-coding-agent` after mise installs Node.

**Tech Stack:** Chezmoi templates and externals, bash/zsh run-after scripts, Podman/Containerfile, mise-managed Node/npm, npm package `@earendil-works/pi-coding-agent`, Python pytest static regression tests, Markdown specs.

## Global Constraints

- `/data/pi-config` is outside `/data/dotfiles3` and has its own git history.
- The committed default pi config source is `https://github.com/kkiyama117/pi-config.git`; `file:///data/pi-config` is for local development override only.
- The first immutable external ref is `pi-config-v2026-07-08-1`.
- `~/.local/share/pi-config` is the chezmoi external target; `~/.pi/agent` remains pi's runtime root.
- Never manage or commit `auth.json`, provider API keys, OAuth artifacts, `trust.json`, `sessions/`, transcripts, logs, npm/git package checkouts, or caches.
- `.pi` remains ignored as a normal chezmoi source target; do not add `dot_pi/` or `private_dot_pi/` source files in this implementation.
- Build mode must not fetch pi config externals or bake `~/.local/share/pi-config` / `~/.pi/agent` into the image.
- Install pi with lifecycle scripts disabled: `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`.
- Do not commit unless the user explicitly asks. If committing later, keep `/data/pi-config` and `/data/dotfiles3` commits separate.

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| `/data/pi-config/.gitignore` | Exclude pi runtime secrets, sessions, package clones, and logs from the external repo | 1 |
| `/data/pi-config/README.md` | Explain repo scope: stable pi resources only | 1 |
| `/data/pi-config/agent/prompts/commit.md` | Moved stable commit prompt currently tracked at `.pi/prompts/commit.md` | 1 |
| `/data/pi-config/agent/{skills,extensions,themes}/.gitkeep` | Preserve stable resource directories until populated | 1 |
| `.chezmoi.toml.tmpl` | Add `pi_config_url` / `pi_config_ref` data with env overrides | 2 |
| `.chezmoiexternal.toml.tmpl` | Fetch pinned external pi config to `~/.local/share/pi-config`, gated out of build mode | 2 |
| `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl` | Idempotently link stable external resources into `~/.pi/agent` | 3 |
| `programs/chezmoi_pi_commit.sh` | Read commit prompt from override, linked pi prompt, or external checkout | 4 |
| `.pi/prompts/commit.md` | Remove from `dotfiles3` after hook migration | 4 |
| `dependencies/packages.toml` | Add `pi-coding-agent` custom package inventory entry | 5 |
| `container/Containerfile` | Install pi CLI after Node is available from mise | 5 |
| `docs/specifications/02-installed-programs.md` | Document pi package and refreshed AUTO-GEN block | 6 |
| `docs/specifications/11-pre-required-env-values.md` | Document optional non-secret pi config env overrides and secret exclusions | 6 |
| `docs/specifications/21-container-build-flow.md` | Document pi install layer and external config runtime behavior | 6 |
| `docs/references/chezmoi_reference.md` | Update auto-commit prompt location | 6 |
| `container/tests/container/test_entrypoint.py` | Static regression tests for external gating, symlink script, hook prompt, and pi install | 2-5 |
| `docs/issues/2026-07-08-phase-pi-agent-container-git-managed-config.md` | Result log after implementation verification | 7 |

---

## Phase 1 - Bootstrap `/data/pi-config`

**Files:**
- Create: `/data/pi-config/.gitignore`
- Create: `/data/pi-config/README.md`
- Create: `/data/pi-config/agent/prompts/commit.md`
- Create: `/data/pi-config/agent/skills/.gitkeep`
- Create: `/data/pi-config/agent/extensions/.gitkeep`
- Create: `/data/pi-config/agent/themes/.gitkeep`

**Interfaces:**
- Consumes: `/data/dotfiles3/.pi/prompts/commit.md`.
- Produces: independent git repo `/data/pi-config` with tag `pi-config-v2026-07-08-1`.

- [ ] **Step 1: Confirm `/data` exists and inspect any existing pi config checkout**

  Run:

  ```bash
  cd /data/dotfiles3 && ls -la /data && if [ -e /data/pi-config ]; then git -C /data/pi-config status --short --branch; fi
  ```

  Expected:
  - `/data` exists.
  - If `/data/pi-config` already exists, it is either empty or a git repo the maintainer recognizes.

- [ ] **Step 2: Create the external repo skeleton**

  Run:

  ```bash
  cd /data/dotfiles3 && mkdir -p /data/pi-config/agent/prompts /data/pi-config/agent/skills /data/pi-config/agent/extensions /data/pi-config/agent/themes
  ```

  Expected: directories exist under `/data/pi-config/agent/`.

- [ ] **Step 3: Write `/data/pi-config/.gitignore`**

  Create `/data/pi-config/.gitignore`:

  ```gitignore
  # Mutable pi runtime state. Never commit credentials, sessions, package clones,
  # logs, or caches to this config repository.
  auth.json
  trust.json
  sessions/
  transcripts/
  logs/
  cache/
  npm/
  git/
  *.log
  ```

- [ ] **Step 4: Write `/data/pi-config/README.md`**

  Create `/data/pi-config/README.md`:

  ```markdown
  # pi-config

  Stable pi resources shared by dotfiles3.

  This repository contains reviewable configuration only:

  - `agent/settings.json`
  - `agent/prompts/`
  - `agent/skills/`
  - `agent/extensions/`
  - `agent/themes/`

  Do not commit pi runtime state such as auth files, trust decisions, sessions,
  logs, package checkouts, or caches. Those belong under `~/.pi/agent` at
  runtime and are intentionally unmanaged.
  ```

- [ ] **Step 5: Move the commit prompt into the external repo**

  Run:

  ```bash
  cd /data/dotfiles3 && cp .pi/prompts/commit.md /data/pi-config/agent/prompts/commit.md && touch /data/pi-config/agent/skills/.gitkeep /data/pi-config/agent/extensions/.gitkeep /data/pi-config/agent/themes/.gitkeep
  ```

  Expected: `/data/pi-config/agent/prompts/commit.md` matches the current tracked prompt.

- [ ] **Step 6: Initialize and tag the external repo**

  Run:

  ```bash
  cd /data/pi-config && git init -b main && git add README.md .gitignore agent && git commit -m "Add initial pi config resources." && git tag pi-config-v2026-07-08-1
  ```

  Expected:
  - Commit succeeds.
  - `git tag --list pi-config-v2026-07-08-1` prints `pi-config-v2026-07-08-1`.

- [ ] **Step 7: Publish remote when ready**

  If the GitHub repository exists, run:

  ```bash
  cd /data/pi-config && git remote add origin git@github.com:kkiyama117/pi-config.git && git push -u origin main && git push origin pi-config-v2026-07-08-1
  ```

  Expected:
  - Remote push succeeds.
  - The tag is visible on GitHub.

  If the GitHub repository does not exist yet, stop after the local tag and use `PI_CONFIG_URL=file:///data/pi-config` for Phase 2 verification.

**Acceptance:** `/data/pi-config` has a clean git status, contains the commit prompt and stable resource directories, and has tag `pi-config-v2026-07-08-1`.

**Rollback:** Delete `/data/pi-config` if it was newly created and remove the GitHub repository/tag if published only for this implementation attempt.

---

## Phase 2 - Add the chezmoi external consumer with tests

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Modify: `.chezmoi.toml.tmpl`
- Create: `.chezmoiexternal.toml.tmpl`

**Interfaces:**
- Consumes: `.build_mode` from `.chezmoi.toml.tmpl` data.
- Produces: `.pi_config_url` and `.pi_config_ref` template data; `.chezmoiexternal.toml.tmpl` external target `.local/share/pi-config`.

- [ ] **Step 1: Add failing static tests**

  In `container/tests/container/test_entrypoint.py`, add constants near the existing file constants:

  ```python
  CHEZMOI_CONFIG = ROOT / ".chezmoi.toml.tmpl"
  CHEZMOI_EXTERNAL = ROOT / ".chezmoiexternal.toml.tmpl"
  ```

  Add this test after `test_zshenv_owns_pnpm_bootstrap_env`:

  ```python
  def test_pi_config_external_is_build_mode_gated_and_pinned() -> None:
      config = CHEZMOI_CONFIG.read_text()
      external = CHEZMOI_EXTERNAL.read_text()

      assert "pi_config_url" in config
      assert "PI_CONFIG_URL" in config
      assert "https://github.com/kkiyama117/pi-config.git" in config
      assert "pi_config_ref" in config
      assert "PI_CONFIG_REF" in config
      assert "pi-config-v2026-07-08-1" in config

      assert "{{- if not .build_mode }}" in external
      assert '[".local/share/pi-config"]' in external
      assert 'type = "git-repo"' in external
      assert 'url = "{{ .pi_config_url }}"' in external
      assert 'refreshPeriod = "0"' in external
      assert 'clone.args = ["--branch", "{{ .pi_config_ref }}", "--depth", "1"]' in external
      assert "file:///data/pi-config" not in external
  ```

- [ ] **Step 2: Run the test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_config_external_is_build_mode_gated_and_pinned -q
  ```

  Expected: FAIL because `.chezmoiexternal.toml.tmpl` does not exist and the config data is absent.

- [ ] **Step 3: Add pi config data to `.chezmoi.toml.tmpl`**

  In `.chezmoi.toml.tmpl`, under the existing `[data]` keys, make the block:

  ```toml
  [data]
  build_mode = {{ if eq (env "BUILD_MODE" | default "false") "true" }}true{{ else }}false{{ end }}
  runtime = {{ env "DOTFILES_RUNTIME" | default "host" | quote }}
  pi_config_url = {{ env "PI_CONFIG_URL" | default "https://github.com/kkiyama117/pi-config.git" | quote }}
  pi_config_ref = {{ env "PI_CONFIG_REF" | default "pi-config-v2026-07-08-1" | quote }}
  ```

- [ ] **Step 4: Add `.chezmoiexternal.toml.tmpl`**

  Create `.chezmoiexternal.toml.tmpl`:

  ```toml
  {{- /* pi config external. Build mode must not fetch user config into image layers. */ -}}
  {{- if not .build_mode }}
  [".local/share/pi-config"]
  type = "git-repo"
  url = "{{ .pi_config_url }}"
  refreshPeriod = "0"
  clone.args = ["--branch", "{{ .pi_config_ref }}", "--depth", "1"]
  pull.args = ["--ff-only"]
  {{- end }}
  ```

  `refreshPeriod = "0"` keeps the pinned external stable unless the operator explicitly refreshes externals.

- [ ] **Step 5: Run the focused test**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_config_external_is_build_mode_gated_and_pinned -q
  ```

  Expected: `1 passed`.

- [ ] **Step 6: Verify template rendering in host and build modes**

  Run:

  ```bash
  cd /data/dotfiles3 && chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/dotfiles3-chezmoi.toml && BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/dotfiles3-chezmoi-build.toml && PI_CONFIG_URL=file:///data/pi-config chezmoi execute-template < .chezmoiexternal.toml.tmpl >/tmp/dotfiles3-externals.toml && BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/dotfiles3-build-config.toml
  ```

  Expected:
  - `/tmp/dotfiles3-chezmoi.toml` contains `pi_config_url` and `pi_config_ref`.
  - `/tmp/dotfiles3-externals.toml` contains `.local/share/pi-config`.
  - Build-mode config render exits 0.

**Acceptance:** focused test passes and templates render without errors. Build mode has the data available but the external template itself is gated by `.build_mode`.

**Rollback:** Remove `.chezmoiexternal.toml.tmpl`, remove `pi_config_url` / `pi_config_ref` from `.chezmoi.toml.tmpl`, and remove the new test.

---

## Phase 3 - Link stable pi resources after apply

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Create: `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`

**Interfaces:**
- Consumes: `~/.local/share/pi-config/agent`.
- Produces: symlinks under `~/.pi/agent` for `settings.json`, `prompts`, `skills`, `extensions`, and `themes`.

- [ ] **Step 1: Add failing static test for the run-after script**

  In `container/tests/container/test_entrypoint.py`, add:

  ```python
  PI_LINK_SCRIPT = ROOT / ".chezmoiscripts" / "run_after_configure-pi-agent.sh.tmpl"
  ```

  Add this test:

  ```python
  def test_pi_link_script_manages_only_stable_resources() -> None:
      text = PI_LINK_SCRIPT.read_text()

      assert "{{- if not .build_mode }}" in text
      assert '.local/share/pi-config/agent' in text
      assert '.pi/agent' in text
      for name in ("settings.json", "prompts", "skills", "extensions", "themes"):
          assert f'link_resource "{name}"' in text

      forbidden = ("auth.json", "trust.json", "sessions", "transcripts", "npm", "git", "logs", "cache")
      for name in forbidden:
          assert f'link_resource "{name}"' not in text
  ```

- [ ] **Step 2: Run the test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_link_script_manages_only_stable_resources -q
  ```

  Expected: FAIL because the script does not exist.

- [ ] **Step 3: Create `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`**

  Create `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`:

  ```bash
  #!/usr/bin/env bash
  {{- if not .build_mode }}
  set -euo pipefail

  pi_config_dir="${HOME}/.local/share/pi-config/agent"
  pi_agent_dir="${HOME}/.pi/agent"

  if [ ! -d "$pi_config_dir" ]; then
    echo "pi-config: ${pi_config_dir} is missing; skipping pi resource links." >&2
    exit 0
  fi

  mkdir -p "$pi_agent_dir"

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

  link_resource "settings.json"
  link_resource "prompts"
  link_resource "skills"
  link_resource "extensions"
  link_resource "themes"
  {{- else }}
  exit 0
  {{- end }}
  ```

- [ ] **Step 4: Run the focused test**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_link_script_manages_only_stable_resources -q
  ```

  Expected: `1 passed`.

- [ ] **Step 5: Verify rendered script syntax**

  Run:

  ```bash
  cd /data/dotfiles3 && chezmoi execute-template < .chezmoiscripts/run_after_configure-pi-agent.sh.tmpl >/tmp/run_after_configure-pi-agent.sh && bash -n /tmp/run_after_configure-pi-agent.sh && BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/build-chezmoi.toml
  ```

  Expected:
  - `bash -n` exits 0.
  - Build-mode config render exits 0.

**Acceptance:** the script is idempotent, build-mode gated, links only stable resources, and passes shell syntax validation.

**Rollback:** Delete `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl` and remove the test.

---

## Phase 4 - Migrate the host auto-commit prompt

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Modify: `programs/chezmoi_pi_commit.sh`
- Delete: `.pi/prompts/commit.md`

**Interfaces:**
- Consumes: `PI_COMMIT_PROMPT_FILE`, `~/.pi/agent/prompts/commit.md`, `~/.local/share/pi-config/agent/prompts/commit.md`.
- Produces: host commit hook independent of in-repo `.pi/prompts/commit.md`.

- [ ] **Step 1: Add failing test for prompt lookup precedence**

  In `container/tests/container/test_entrypoint.py`, add:

  ```python
  PI_COMMIT_HOOK = ROOT / "programs" / "chezmoi_pi_commit.sh"
  ```

  Add:

  ```python
  def test_pi_commit_hook_uses_external_prompt_precedence() -> None:
      text = PI_COMMIT_HOOK.read_text()

      assert "PI_COMMIT_PROMPT_FILE" in text
      assert "$HOME/.pi/agent/prompts/commit.md" in text
      assert "$HOME/.local/share/pi-config/agent/prompts/commit.md" in text
      assert '$src_dir/.pi/prompts/commit.md' not in text
  ```

- [ ] **Step 2: Run the test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_commit_hook_uses_external_prompt_precedence -q
  ```

  Expected: FAIL because the hook still reads `$src_dir/.pi/prompts/commit.md`.

- [ ] **Step 3: Update `programs/chezmoi_pi_commit.sh`**

  Replace:

  ```bash
  prompt_file="$src_dir/.pi/prompts/commit.md"
  if [ ! -f "$prompt_file" ]; then
    echo "chezmoi commit hook: missing $prompt_file — skipping auto-commit." >&2
    exit 0
  fi
  ```

  with:

  ```bash
  prompt_candidates=(
    "${PI_COMMIT_PROMPT_FILE:-}"
    "$HOME/.pi/agent/prompts/commit.md"
    "$HOME/.local/share/pi-config/agent/prompts/commit.md"
  )

  prompt_file=""
  for candidate in "${prompt_candidates[@]}"; do
    if [ -n "$candidate" ] && [ -f "$candidate" ]; then
      prompt_file="$candidate"
      break
    fi
  done

  if [ -z "$prompt_file" ]; then
    echo "chezmoi commit hook: missing pi commit prompt — skipping auto-commit." >&2
    exit 0
  fi
  ```

  Keep the existing frontmatter stripping:

  ```bash
  prompt="$(sed '/^---$/,/^---$/d' "$prompt_file")"
  ```

- [ ] **Step 4: Delete the tracked in-repo prompt**

  Run:

  ```bash
  cd /data/dotfiles3 && git rm .pi/prompts/commit.md
  ```

  Expected: `git status --short` shows `D  .pi/prompts/commit.md`.

- [ ] **Step 5: Run focused tests and shell syntax**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_commit_hook_uses_external_prompt_precedence -q && bash -n programs/chezmoi_pi_commit.sh
  ```

  Expected: test passes and `bash -n` exits 0.

**Acceptance:** the hook no longer depends on `.pi` inside `dotfiles3`, the external prompt is available in `/data/pi-config`, and the old tracked prompt is removed.

**Rollback:** Restore `.pi/prompts/commit.md` from git and restore the old `prompt_file="$src_dir/.pi/prompts/commit.md"` lookup.

---

## Phase 5 - Install pi CLI in the container

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Modify: `dependencies/packages.toml`
- Generated: `docs/specifications/02-installed-programs.md`
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: mise-managed Node/npm installed by Stage 3-4.
- Produces: `pi` executable on PATH in the running container.

- [ ] **Step 1: Add failing static tests for package inventory and Containerfile install**

  In `container/tests/container/test_entrypoint.py`, add:

  ```python
  PACKAGES = ROOT / "dependencies" / "packages.toml"
  CONTAINERFILE = ROOT / "container" / "Containerfile"
  ```

  Add:

  ```python
  def test_pi_coding_agent_inventory_and_container_install() -> None:
      packages = PACKAGES.read_text()
      containerfile = CONTAINERFILE.read_text()

      assert 'name = "pi-coding-agent"' in packages
      assert 'manager = "custom"' in packages
      assert "@earendil-works/pi-coding-agent" in packages
      assert "@earendil-works/pi-coding-agent" in containerfile
      assert "--ignore-scripts" in containerfile
      assert "pi --version" in containerfile
  ```

- [ ] **Step 2: Run the test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_coding_agent_inventory_and_container_install -q
  ```

  Expected: FAIL because package inventory and Containerfile install are absent.

- [ ] **Step 3: Add package inventory entry**

  In `dependencies/packages.toml`, add this entry in alphabetical order by `name`:

  ```toml
  [[tool]]
  name = "pi-coding-agent"
  manager = "custom"
  layer = 3
  # npm package: @earendil-works/pi-coding-agent
  has_configs = true
  description = "pi coding agent CLI (`@earendil-works/pi-coding-agent`); installed with npm --ignore-scripts after mise-managed Node"
  ```

- [ ] **Step 4: Regenerate dependency docs**

  Run:

  ```bash
  cd /data/dotfiles3 && make gen-deps
  ```

  Expected:
  - `docs/specifications/02-installed-programs.md` AUTO-GEN block includes `pi-coding-agent`.
  - No `dependencies/layer_3/custom.txt` is generated because `custom` is doc-only.

- [ ] **Step 5: Add Containerfile pi install layer**

  In `container/Containerfile`, insert this layer immediately after Layer 3-4 (`mise install --yes`) and before cargo-binstall:

  ```dockerfile
  # Layer 3-5: Install pi coding agent CLI with mise-managed Node/npm.
  #
  # The upstream install path is npm global with lifecycle scripts disabled.
  # Node and npm are available through the mise config installed in Layer 3-4.
  RUN --mount=type=cache,target=/home/${USERNAME}/.cache/npm,uid=${HOST_UID},gid=${HOST_GID} \
      zsh -c 'set -eo pipefail; \
        source /tmp/build-home/.zshenv; \
        mise exec node@latest -- npm install -g --ignore-scripts @earendil-works/pi-coding-agent; \
        pi --version; \
      '
  ```

  Then renumber the following Stage 3 comments:

  ```text
  3-6 cargo-binstall bootstrap
  3-7 cargo tools
  ```

  Also update the Stage 3 overview comment so it includes pi CLI installation.

- [ ] **Step 6: Run focused test**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest container/tests/container/test_entrypoint.py::test_pi_coding_agent_inventory_and_container_install -q
  ```

  Expected: `1 passed`.

**Acceptance:** package inventory records the pi CLI, Containerfile installs it with `--ignore-scripts`, and static tests pass.

**Rollback:** Remove the `pi-coding-agent` package entry, rerun `make gen-deps`, remove the Containerfile layer, and remove the test.

---

## Phase 6 - Documentation sync

**Files:**
- Modify: `docs/specifications/02-installed-programs.md`
- Modify: `docs/specifications/11-pre-required-env-values.md`
- Modify: `docs/specifications/21-container-build-flow.md`
- Modify: `docs/references/chezmoi_reference.md`
- Modify: `docs/issues/2026-07-08-pi-agent-container-git-managed-config.md`

**Interfaces:**
- Consumes: implementation decisions from Phases 1-5.
- Produces: synchronized specs and issue links.

- [ ] **Step 1: Update spec 02**

  In `docs/specifications/02-installed-programs.md`, ensure the generated AUTO-GEN block contains `pi-coding-agent` in Layer 3 with manager `custom`.

  Add a short manager note under `custom`:

  ```markdown
  `pi-coding-agent` is a `custom` Layer 3 entry because the package is installed
  by a bespoke npm command after mise-managed Node is available, not from a
  generated package-manager list.
  ```

- [ ] **Step 2: Update spec 11**

  In `docs/specifications/11-pre-required-env-values.md`, add local variables:

  ```markdown
  | `PI_CONFIG_URL` | no | `https://github.com/kkiyama117/pi-config.git` | Optional chezmoi external source override for stable pi config |
  | `PI_CONFIG_REF` | no | `pi-config-v2026-07-08-1` | Optional chezmoi external ref override for stable pi config |
  | `PI_COMMIT_PROMPT_FILE` | no | — | Optional host-only override for the chezmoi pi auto-commit prompt |
  ```

  Add this note near the local environment section:

  ```markdown
  Pi provider credentials, OAuth artifacts, sessions, trust decisions, package
  checkouts, and logs are runtime state under `~/.pi/agent`; they must not be
  stored in `.env`, `.chezmoidata`, `/data/pi-config`, or this repository.
  ```

- [ ] **Step 3: Update spec 21**

  In `docs/specifications/21-container-build-flow.md`:

  - Update the Stage 3 overview row to mention pi CLI installation.
  - Add a row for Layer 3-5 pi CLI install.
  - Renumber cargo-binstall and cargo tools rows to 3-6 and 3-7.
  - Add an acceptance criterion:

  ```markdown
  After `make up`, `podman exec dotfiles-manjaro zsh -ic 'pi --version'` exits 0.
  Build mode does not fetch `~/.local/share/pi-config` or bake pi runtime state;
  runtime `chezmoi apply` may fetch the pinned external config into
  `~/.local/share/pi-config` and link stable resources into `~/.pi/agent`.
  ```

- [ ] **Step 4: Update `docs/references/chezmoi_reference.md`**

  Replace the old prompt location text:

  ```markdown
  The commit prompt is in `.pi/prompts/commit.md` (repo-local, not deployed
  by chezmoi).
  ```

  with:

  ```markdown
  The commit prompt is managed by the external pi config repo. The hook checks
  `PI_COMMIT_PROMPT_FILE`, then `~/.pi/agent/prompts/commit.md`, then
  `~/.local/share/pi-config/agent/prompts/commit.md`.
  ```

- [ ] **Step 5: Update parent issue links**

  In `docs/issues/2026-07-08-pi-agent-container-git-managed-config.md`, update `Related` to include:

  ```markdown
  [design](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md), [plan](../plans/2026-07-08-pi-agent-container-git-managed-config-impl.md)
  ```

- [ ] **Step 6: Run docs/static tests**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 make test-container && PYTHONDONTWRITEBYTECODE=1 make test-deps
  ```

  Expected:
  - `make test-container` passes.
  - `make test-deps` passes.

**Acceptance:** specs and reference docs describe the same source, install, runtime, and secret-exclusion policy implemented in prior phases.

**Rollback:** Revert docs edits and parent issue link update.

---

## Phase 7 - End-to-end verification and result log

**Files:**
- Create: `docs/issues/2026-07-08-phase-pi-agent-container-git-managed-config.md`

**Interfaces:**
- Consumes: all prior phases.
- Produces: result log with verification evidence.

- [ ] **Step 1: Run template and script checks**

  Run:

  ```bash
  cd /data/dotfiles3 && chezmoi execute-template --init < .chezmoi.toml.tmpl >/tmp/dotfiles3-chezmoi.toml && PI_CONFIG_URL=file:///data/pi-config chezmoi execute-template < .chezmoiexternal.toml.tmpl >/tmp/dotfiles3-externals.toml && chezmoi execute-template < .chezmoiscripts/run_after_configure-pi-agent.sh.tmpl >/tmp/run_after_configure-pi-agent.sh && bash -n /tmp/run_after_configure-pi-agent.sh && bash -n programs/chezmoi_pi_commit.sh
  ```

  Expected: command exits 0.

- [ ] **Step 2: Run focused tests**

  Run:

  ```bash
  cd /data/dotfiles3 && PYTHONDONTWRITEBYTECODE=1 make test-container && PYTHONDONTWRITEBYTECODE=1 make test-deps && make test-zsh
  ```

  Expected: all three targets pass.

- [ ] **Step 3: Build and start container**

  Run:

  ```bash
  cd /data/dotfiles3 && make build && make up
  ```

  Expected:
  - `make build` exits 0.
  - `make up` exits 0 and prints `container ready`.

- [ ] **Step 4: Verify pi CLI and prompt inside container**

  Run:

  ```bash
  cd /data/dotfiles3 && podman exec dotfiles-manjaro zsh -ic 'pi --version' && podman exec dotfiles-manjaro zsh -ic 'test -r ~/.pi/agent/prompts/commit.md' && podman exec dotfiles-manjaro zsh -ic 'test ! -e ~/.pi/agent/auth.json && test ! -d ~/.pi/agent/sessions'
  ```

  Expected: command exits 0.

- [ ] **Step 5: Verify build image did not bake pi config external**

  Run:

  ```bash
  cd /data/dotfiles3 && podman run --rm --entrypoint /usr/bin/test localhost/dotfiles-manjaro:latest ! -e /home/${USERNAME}/.local/share/pi-config
  ```

  Expected: command exits 0.

- [ ] **Step 6: Verify tracked files exclude sensitive pi state**

  Run:

  ```bash
  cd /data/dotfiles3 && ! git ls-files | rg '(^|/)(auth\.json|trust\.json|sessions/|transcripts/|logs/|npm/|\.pi/agent/git/|cache/)' && cd /data/pi-config && ! git ls-files | rg '(^|/)(auth\.json|trust\.json|sessions/|transcripts/|logs/|npm/|git/|cache/)'
  ```

  Expected: command exits 0.

- [ ] **Step 7: Write result log**

  Create `docs/issues/2026-07-08-phase-pi-agent-container-git-managed-config.md`
  after the commands above have run. The file must include this header and
  the observed command outputs or concise pass/fail summaries from Steps 1-6:

  ```markdown
  # Phase result - pi agent container install and external config

  **Date:** 2026-07-08
  **Status:** closed
  **Issue:** [2026-07-08-pi-agent-container-git-managed-config](2026-07-08-pi-agent-container-git-managed-config.md)
  **Plan:** [2026-07-08-pi-agent-container-git-managed-config-impl](../plans/2026-07-08-pi-agent-container-git-managed-config-impl.md)

  ## Verification

  Summarize the exact results from:

  - template and script checks
  - `make test-container`
  - `make test-deps`
  - `make test-zsh`
  - `make build`
  - `make up`
  - `podman exec dotfiles-manjaro zsh -ic 'pi --version'`
  - sensitive pi path git checks

  ## Notes

  The stable pi config source is `/data/pi-config`, with default remote
  `https://github.com/kkiyama117/pi-config.git` and initial ref
  `pi-config-v2026-07-08-1`. Pi runtime state remains unmanaged under
  `~/.pi/agent`.
  ```

**Acceptance:** all verification commands either pass or have an explicit recorded blocker, and the result log captures the evidence.

**Rollback:** Revert implementation commits in reverse phase order; remove `/data/pi-config` only if it was created exclusively for this work and has no unpushed user changes.

---

## Self-review checklist

- [ ] **Spec coverage:** Phases cover S1-S9 and invariants I1-I9 from the design.
- [ ] **Placeholder scan:** Search this plan for common placeholder markers and unresolved stand-ins before execution.
- [ ] **Type/path consistency:** The external repo path is `/data/pi-config`; the external target is `~/.local/share/pi-config`; pi runtime root is `~/.pi/agent`; initial ref is `pi-config-v2026-07-08-1`.
- [ ] **Security:** No task commits auth, sessions, trust, logs, package checkouts, or caches.
- [ ] **Commit granularity:** If the user asks for commits during execution, use one commit per phase and include `docs/issues/2026-07-08-pi-agent-container-git-managed-config.md` in commit messages.
