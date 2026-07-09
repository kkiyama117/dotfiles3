# nvim External Config via chezmoi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** pending
**Spec:** [`docs/specifications/implementations/2026-07-09-nvim-external-config-design.md`](../specifications/implementations/2026-07-09-nvim-external-config-design.md)
**Parent issue:** [`docs/issues/2026-07-09-nvim-external-config.md`](../issues/2026-07-09-nvim-external-config.md)
**Conversation:** [`docs/references/2026-07-09-nvim-external-config-conversation.md`](../references/2026-07-09-nvim-external-config-conversation.md)

**Goal:** Deploy Neovim config from independent repo `kkiyama117/nvim_config` to `~/.config/nvim` on host and container via chezmoi external, with build-mode gating and pinned ref.

**Architecture:** `/data/nvim_config` is the host authoring checkout; `dotfiles3` consumes `https://github.com/kkiyama117/nvim_config.git` through `.chezmoiexternal.toml.tmpl` with direct clone to `~/.config/nvim` (no symlinks). Config edits use normal git in the external checkout; dotfiles only stores URL/pin. Pi-config uses the same workflow but staging+symlinks layout — fix pi `clone.args` pinning in the same pass.

**Tech Stack:** Chezmoi templates/externals (v2.70+), bash/zsh, Podman container, Python pytest static regression tests, Markdown specs.

## Global Constraints

- `/data/nvim_config` is outside `/data/dotfiles3` and has its own git history.
- Default external source: `https://github.com/kkiyama117/nvim_config.git`; `file:///data/nvim_config` is local dev override only.
- Bootstrap immutable ref: `nvim-config-v2026-07-09-1` (update in plan if tag name changes at publish time).
- External target: `~/.config/nvim` (direct; git root = edit path).
- No `dot_config/nvim/` tree in `dotfiles3`; no `secrets.vim` overlay.
- `BUILD_MODE=true` must render **no** nvim (or pi) external blocks.
- `refreshPeriod = "0"`; explicit `chezmoi apply --refresh-externals=always` when pulling remote.
- `make build` must not fetch or bake nvim config into image layers.
- Lazy.nvim / plugin data under `~/.local/share/nvim` remains unmanaged.
- Do not commit unless the user explicitly asks. Keep `/data/nvim_config` and `/data/dotfiles3` commits separate.

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| `/data/nvim_config/.gitignore` | Exclude editor swap/backup artifacts | 1 |
| `/data/nvim_config/README.md` | Repo scope and edit workflow | 1 |
| `/data/nvim_config/{init.lua,lua/,…}` | Migrated nvim config from host | 1 |
| `.chezmoi.toml.tmpl` | Add `nvim_config_url` / `nvim_config_ref`; fix pi `clone.args` pinning | 2 |
| `.chezmoiexternal.toml.tmpl` | Add nvim external block; fix pi `clone.args` to use `pi_config_ref` | 2 |
| `docs/specifications/11-pre-required-env-values.md` | Document `NVIM_CONFIG_URL` / `NVIM_CONFIG_REF` | 3 |
| `docs/references/chezmoi_reference.md` | Document unified external edit workflow (pi + nvim) | 3 |
| `container/tests/container/test_entrypoint.py` | Static tests for nvim external + pi pinning fix | 2 |
| `docs/issues/2026-07-09-phase-nvim-external-config.md` | Result log after verification | 4 |

---

## Phase 1 — Bootstrap `/data/nvim_config` and publish

**Files:**
- Create: `/data/nvim_config/.gitignore`
- Create: `/data/nvim_config/README.md`
- Migrate: host `~/.config/nvim/*` → `/data/nvim_config/`

**Interfaces:**
- Consumes: existing host `~/.config/nvim` (legacy `miyake-ken/vimrc.git`).
- Produces: published git repo `kkiyama117/nvim_config` with tag `nvim-config-v2026-07-09-1`.

- [ ] **Step 1: Inspect host state**

  Run:

  ```bash
  ls -la /data/nvim_config
  git -C ~/.config/nvim remote -v 2>/dev/null || echo "no ~/.config/nvim git"
  test -f ~/.config/nvim/init.lua && echo "init.lua exists" || echo "no init.lua"
  ```

  Expected:
  - `/data/nvim_config` exists (may be empty).
  - `~/.config/nvim` remote is `miyake-ken/vimrc.git` or absent.

- [ ] **Step 2: Copy existing config to authoring checkout**

  Run:

  ```bash
  mkdir -p /data/nvim_config
  rsync -a --exclude='.git' ~/.config/nvim/ /data/nvim_config/
  ```

  Expected: config files present under `/data/nvim_config/` (e.g. `init.lua`).

- [ ] **Step 3: Write `/data/nvim_config/.gitignore`**

  Create `/data/nvim_config/.gitignore`:

  ```gitignore
  *.swp
  *.swo
  .netrwhist
  *.tmp
  *.bak
  ```

- [ ] **Step 4: Write `/data/nvim_config/README.md`**

  Create `/data/nvim_config/README.md`:

  ```markdown
  # nvim_config

  Neovim configuration consumed by dotfiles3 via chezmoi external.

  - Deployed to: `~/.config/nvim` (host + container)
  - Edit: here or at deployed path; commit with normal git (not `chezmoi add`)
  - Plugin/runtime state: `~/.local/share/nvim` (unmanaged)
  ```

- [ ] **Step 5: Initialize repo and push to GitHub**

  Run (requires `gh` auth and repo `kkiyama117/nvim_config` created):

  ```bash
  cd /data/nvim_config
  git init
  git add -A
  git commit -m "Initial nvim config migrated from host."
  git branch -M main
  git remote add origin https://github.com/kkiyama117/nvim_config.git
  git push -u origin main
  git tag nvim-config-v2026-07-09-1
  git push origin nvim-config-v2026-07-09-1
  ```

  Expected: tag `nvim-config-v2026-07-09-1` visible on GitHub.

- [ ] **Step 6: Commit in `/data/nvim_config` only when user asks**

  Do not commit from `dotfiles3` in this phase.

---

## Phase 2 — Chezmoi external consumer + pi pinning fix

**Files:**
- Modify: `.chezmoi.toml.tmpl`
- Modify: `.chezmoiexternal.toml.tmpl`
- Modify: `container/tests/container/test_entrypoint.py`

**Interfaces:**
- Consumes: tag `nvim-config-v2026-07-09-1` on GitHub.
- Produces: rendered externals with nvim block and pi `clone.args` using `pi_config_ref`.

- [ ] **Step 1: Write failing test for nvim external**

  Add to `container/tests/container/test_entrypoint.py`:

  ```python
  def test_nvim_config_external_is_build_mode_gated_and_pinned() -> None:
      config = CHEZMOI_CONFIG.read_text()
      external = CHEZMOI_EXTERNAL.read_text()

      assert "nvim_config_url" in config
      assert "NVIM_CONFIG_URL" in config
      assert "https://github.com/kkiyama117/nvim_config.git" in config
      assert "nvim_config_ref" in config
      assert "NVIM_CONFIG_REF" in config
      assert "nvim-config-v2026-07-09-1" in config

      assert '[".config/nvim"]' in external
      assert 'url = "{{ .nvim_config_url }}"' in external
      assert 'clone.args = ["--branch", "{{ .nvim_config_ref }}", "--depth", "1"]' in external
      assert "file:///data/nvim_config" not in external
  ```

  Note: `test_pi_config_external_is_build_mode_gated_and_pinned` already expects
  pinned `clone.args` for pi; current `.chezmoiexternal.toml.tmpl` is missing
  `--branch`. This phase fixes both.

- [ ] **Step 2: Run test to verify it fails**

  Run:

  ```bash
  cd /data/dotfiles3 && python -m pytest container/tests/container/test_entrypoint.py::test_nvim_config_external_is_build_mode_gated_and_pinned container/tests/container/test_entrypoint.py::test_pi_config_external_is_build_mode_gated_and_pinned -v
  ```

  Expected: FAIL (missing `nvim_config_*` in config; pi `clone.args` mismatch).

- [ ] **Step 3: Add nvim data to `.chezmoi.toml.tmpl`**

  After the `pi_config_ref` line, add:

  ```toml
  nvim_config_url = {{ env "NVIM_CONFIG_URL" | default "https://github.com/kkiyama117/nvim_config.git" | quote }}
  nvim_config_ref = {{ env "NVIM_CONFIG_REF" | default "nvim-config-v2026-07-09-1" | quote }}
  ```

- [ ] **Step 4: Update `.chezmoiexternal.toml.tmpl`**

  Replace file content with:

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

  {{- /* nvim config external. Build mode must not fetch user config into image layers. */ -}}
  {{- if not .build_mode }}
  [".config/nvim"]
  type = "git-repo"
  url = "{{ .nvim_config_url }}"
  refreshPeriod = "0"
  clone.args = ["--branch", "{{ .nvim_config_ref }}", "--depth", "1"]
  pull.args = ["--ff-only"]
  {{- end }}
  ```

- [ ] **Step 5: Run tests to verify they pass**

  Run:

  ```bash
  cd /data/dotfiles3 && python -m pytest container/tests/container/test_entrypoint.py::test_nvim_config_external_is_build_mode_gated_and_pinned container/tests/container/test_entrypoint.py::test_pi_config_external_is_build_mode_gated_and_pinned -v
  ```

  Expected: PASS

- [ ] **Step 6: Verify build-mode gating**

  Run:

  ```bash
  cd /data/dotfiles3
  BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl | rg -n 'config/nvim|pi-config' || echo "no externals in build mode"
  chezmoi execute-template --init < .chezmoi.toml.tmpl > /tmp/chezmoi-host.toml
  rg 'nvim_config_ref|pi_config_ref' /tmp/chezmoi-host.toml
  ```

  Expected:
  - Build mode: no external target lines (or only data vars, not external blocks).
  - Host mode: `nvim_config_ref` and `pi_config_ref` present in data.

- [ ] **Step 7: Commit dotfiles3 changes when user asks**

  ```bash
  git add .chezmoi.toml.tmpl .chezmoiexternal.toml.tmpl container/tests/container/test_entrypoint.py
  git commit -m "Add chezmoi external for nvim config and pin pi-config ref."
  ```

---

## Phase 3 — Documentation

**Files:**
- Modify: `docs/specifications/11-pre-required-env-values.md`
- Modify: `docs/references/chezmoi_reference.md` (if external workflow section exists)

**Interfaces:**
- Consumes: Phase 2 template data keys.
- Produces: documented env overrides and unified workflow.

- [ ] **Step 1: Add env vars to spec 11**

  In `docs/specifications/11-pre-required-env-values.md`, after `PI_CONFIG_REF` row, add:

  | `NVIM_CONFIG_URL` | no | `https://github.com/kkiyama117/nvim_config.git` | Optional chezmoi external source override for nvim config |
  | `NVIM_CONFIG_REF` | no | `nvim-config-v2026-07-09-1` | Optional chezmoi external ref override for nvim config |

  Add note:

  ```markdown
  `/data/nvim_config` is a local authoring checkout override via
  `NVIM_CONFIG_URL=file:///data/nvim_config` only.
  ```

- [ ] **Step 2: Document unified external workflow**

  Add subsection to `docs/references/chezmoi_reference.md` (or create short
  pointer to conversation log §3 and design §5.3):

  - pi: commit from `~/.local/share/pi-config` (edit via `~/.pi/agent` symlinks)
  - nvim: commit from `~/.config/nvim` (git root = edit path)
  - both: no `chezmoi add`; dotfiles commits only change URL/pin

- [ ] **Step 3: Commit docs when user asks**

  ```bash
  git add docs/specifications/11-pre-required-env-values.md docs/references/chezmoi_reference.md
  git commit -m "Document nvim external env overrides and unified workflow."
  ```

---

## Phase 4 — Host migration and verification

**Files:**
- Create: `docs/issues/2026-07-09-phase-nvim-external-config.md` (result log)

**Interfaces:**
- Consumes: Phase 1 published repo, Phase 2 chezmoi templates.
- Produces: working `~/.config/nvim` external on host and container.

- [ ] **Step 1: Backup and remove legacy deployed checkout**

  Run on host:

  ```bash
  mv ~/.config/nvim ~/.config/nvim.pre-external-backup
  ```

  Expected: `~/.config/nvim` no longer exists.

- [ ] **Step 2: Apply chezmoi external on host**

  Run:

  ```bash
  cd /data/dotfiles3
  chezmoi apply --refresh-externals=always
  test -d ~/.config/nvim/.git
  git -C ~/.config/nvim remote -v
  git -C ~/.config/nvim branch -vv
  ```

  Expected:
  - `~/.config/nvim/.git` exists
  - remote `kkiyama117/nvim_config`
  - on tag/branch matching `nvim-config-v2026-07-09-1`

- [ ] **Step 3: Verify build does not bake nvim config**

  Run:

  ```bash
  cd /data/dotfiles3 && make build
  podman run --rm localhost/dotfiles-manjaro:latest test ! -d /home/kiyama/.config/nvim/.git
  ```

  Expected: `make build` succeeds; runtime image has no nvim external checkout
  baked in (external fetched at runtime apply only).

- [ ] **Step 4: Verify container runtime apply**

  Run:

  ```bash
  cd /data/dotfiles3 && make up
  podman exec dotfiles-manjaro test -d /home/kiyama/.config/nvim/.git
  podman exec dotfiles-manjaro zsh -ic 'nvim --version'
  ```

  Expected:
  - `.git` under `~/.config/nvim` after runtime chezmoi apply
  - `nvim --version` exits 0

- [ ] **Step 5: Run full static test suite**

  Run:

  ```bash
  cd /data/dotfiles3 && python -m pytest container/tests/container/test_entrypoint.py -v
  ```

  Expected: all tests PASS

- [ ] **Step 6: Write result log**

  Create `docs/issues/2026-07-09-phase-nvim-external-config.md` with:
  - commands run and outcomes
  - pin tag used
  - migration backup path
  - link to parent issue; mark parent issue ready to close

- [ ] **Step 7: Commit result log when user asks**

  ```bash
  git add docs/issues/2026-07-09-phase-nvim-external-config.md
  git commit -m "Record nvim external config implementation verification."
  ```

---

## Spec Coverage Checklist

| Requirement | Task |
|---|---|
| S1 runtime `.git` at `~/.config/nvim` | Phase 4 Step 2, 4 |
| S2 host authoring `/data/nvim_config` | Phase 1 |
| S3 URL/pin + `file://` override | Phase 2, 3 |
| S4 build-mode gating | Phase 2 Step 6 |
| S5 runtime container fetch | Phase 4 Step 4 |
| S6 edit workflow documented | Phase 3 |
| S7 `make build` no bake | Phase 4 Step 3 |
| S8 verification | Phase 4 |
| pi `pi_config_ref` pinning fix | Phase 2 Step 4 |
| Unified workflow doc | Phase 3 |
| Host migration | Phase 1, 4 Step 1 |

## Residual Risks

- GitHub repo `kkiyama117/nvim_config` must exist and be public (or container fetch needs auth).
- Bootstrap tag name must match pushed tag exactly.
- Legacy `~/.config/nvim` backup must be kept until external apply verified.
- Container push from `~/.config/nvim` still needs git credentials (host preferred).

---

## Execution Handoff

Plan saved to `docs/plans/2026-07-09-nvim-external-config-impl.md`.

**Execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per phase, review between phases
2. **Inline Execution** — implement phases in this session with checkpoints

Which approach?
