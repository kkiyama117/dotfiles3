# Herdr mise migration — Implementation Plan

**Status:** executed
**Spec:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Parent issue:** [`docs/issues/2026-07-15-herdr-mise-management.md`](../issues/2026-07-15-herdr-mise-management.md)
**Review trail:** design [`pass-1`](../reviews/2026-07-15-herdr-mise-management-review-pass1.md); implementation [`pass-2`](../reviews/2026-07-15-herdr-mise-management-review-pass2.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan phase-by-phase. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Committing:** This session is **not** authorized to commit. Commands marked `(future commit)` are optional hand-off notes for the parent / next session.

## Goal

Migrate `herdr` from the bespoke Containerfile Layer 3-8 curl bootstrap into the existing mise-managed toolchain, making mise the sole install/version/update authority on host and container.

## Architecture

- Add `"aqua:ogulcancelik/herdr" = "latest"` to [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml).
- Remove the `herdr` entry from `dependencies/packages.toml` and run `make gen-deps` so the spec 02 AUTO-GEN block drops the Layer 3 `custom` row.
- Delete Containerfile Layer 3-8 (the `ARG HERDR_VERSION` / `ARG HERDR_SHA256` / curl + `sha256sum` + `install` block). Layer 3-4's existing `mise install --yes` will install `herdr` automatically once the config declares it.
- Set `[update] channel = "stable"`, `version_check = false`, `manifest_check = false` in both `dot_config/herdr/config.toml` and `dot_config/herdr/config.yml` (both files are TOML-formatted despite the `.yml` extension).
- Update specs 02, 20, and 21 to reflect the migration.
- Mark the old design `superseded` and the old plan `executed` with a forward link and a corrected Task 2 snippet.
- Preserve the closed container-install issue and result-log byte-identical.

## Global Constraints

- **mise is the sole authority** for `herdr` install, version, and upgrade.
- **No commits in this session.** Any commit commands are future optional hand-off notes.
- **Test-first:** add or update a repository policy test before changing implementation files.
- **One-time volume migration:** existing `dotfiles_mise` volumes must be removed once before `make up`; new deployments skip this step.
- **Rollback mirrors rollout:** restore files, rebuild, remove volume, restart.

---

## Phase 0 — Repository policy test (test-first)

**Files:**
- Create: `programs/generate_deps/tests/test_herdr_mise_migration.py`

**Goal:** Lock in the rule that `herdr` no longer appears in `packages.toml` and that the mise config declares the explicit aqua backend.

- [ ] **Step 0.1: Create the policy test file**

```python
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_herdr_not_in_packages_toml() -> None:
    """After migration herdr is managed by mise, not packages.toml."""
    repo_root = SCRIPT_DIR.parents[1]
    packages_path = repo_root / "dependencies" / "packages.toml"
    raw = packages_path.read_text()
    assert 'name = "herdr"' not in raw, "herdr must not be declared in dependencies/packages.toml"


def test_herdr_in_mise_config() -> None:
    """herdr is declared with the explicit aqua backend because disable_default_registry=true."""
    repo_root = SCRIPT_DIR.parents[1]
    mise_config_path = repo_root / "dot_config" / "mise" / "config.toml"
    raw = mise_config_path.read_text()
    assert '"aqua:ogulcancelik/herdr" = "latest"' in raw


def test_herdr_update_checks_disabled() -> None:
    """Both herdr config variants set stable channel and disabled checks."""
    repo_root = SCRIPT_DIR.parents[1]
    for name in ("config.toml", "config.yml"):
        cfg_path = repo_root / "dot_config" / "herdr" / name
        raw = cfg_path.read_text()
        assert 'channel = "stable"' in raw
        assert 'version_check = false' in raw
        assert 'manifest_check = false' in raw
```

- [ ] **Step 0.2: Run the new test and confirm it fails before implementation**

```bash
cd /data/dotfiles3
python3 -m pytest programs/generate_deps/tests/test_herdr_mise_migration.py -v
```

Expected: `test_herdr_not_in_packages_toml` fails (herdr still in packages.toml); the other two fail until Phase 2/3 edits.

**Acceptance:** New test exists and fails before implementation changes.
**Rollback:** Delete the test file.

---

## Phase 1 — Mise config and packages.toml migration

**Files:**
- Modify: [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml)
- Modify: `dependencies/packages.toml`

**Goal:** Declare `herdr` in mise config; remove it from packages.toml.

- [ ] **Step 1.1: Add herdr to mise config**

In [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml) `[tools]`, add after the existing `"npm:@earendil-works/pi-coding-agent"` entry:

```toml
"aqua:ogulcancelik/herdr" = "latest" # terminal workspace manager
```

- [ ] **Step 1.2: Remove herdr from packages.toml**

Delete the `[[tool]]` block:

```toml
[[tool]]
name = "herdr"
manager = "custom"
layer = 3
# `~/.config/herdr`
has_configs = true
description = "terminal workspace manager for AI coding agents (prebuilt binary, curl-bootstrapped in Layer 3-8)"
```

- [ ] **Step 1.3: Regenerate spec 02 AUTO-GEN block**

```bash
cd /data/dotfiles3
make gen-deps
```

Expected: `docs/specifications/02-installed-programs.md` AUTO-GEN block no longer contains `herdr` in the Layer 3 `custom` section.

- [ ] **Step 1.4: Verify idempotency**

```bash
cd /data/dotfiles3
make gen-deps
```

Expected: second run produces no diff.

- [ ] **Step 1.5: Run the policy test**

```bash
cd /data/dotfiles3
python3 -m pytest programs/generate_deps/tests/test_herdr_mise_migration.py -v
```

Expected: `test_herdr_not_in_packages_toml` and `test_herdr_in_mise_config` pass.

**Acceptance:**
- `dot_config/mise/config.toml` contains `"aqua:ogulcancelik/herdr" = "latest"`.
- `dependencies/packages.toml` has no `herdr` entry.
- `make gen-deps` is idempotent and removes `herdr` from spec 02 AUTO-GEN.
- Policy tests pass.

**Rollback:**
1. Restore `dependencies/packages.toml` herdr entry from git.
2. Remove `"aqua:ogulcancelik/herdr"` from mise config.
3. Re-run `make gen-deps`.

---

## Phase 2 — Containerfile migration

**Files:**
- Modify: [`container/Containerfile`](../../container/Containerfile)

**Goal:** Delete Layer 3-8 so `herdr` is installed only by Layer 3-4 `mise install --yes`.

- [ ] **Step 2.1: Locate and delete Layer 3-8**

Remove the entire block starting at the comment:

```dockerfile
# Layer 3-8: Install herdr (pinned prebuilt binary — packages.toml `custom`).
```

through the end of its `RUN` directive (including the trailing `RUN` that contains `ARG HERDR_VERSION`, `ARG HERDR_SHA256`, curl, `sha256sum -c`, `install -D`, and `"$HOME/.local/bin/herdr" --version`).

- [ ] **Step 2.2: Verify no HERDR references remain (static policy test)**

```bash
cd /data/dotfiles3
python3 -m pytest programs/generate_deps/tests/test_herdr_mise_migration.py::test_containerfile_has_no_bespoke_herdr_install -v
```

Expected: test passes (no `HERDR_VERSION`, `HERDR_SHA256`, `herdr-linux-x86_64`, or Layer 3-8 comment in `container/Containerfile`).

Supplemental grep check:

```bash
cd /data/dotfiles3
rg -i 'HERDR_VERSION|HERDR_SHA256|herdr-linux-x86_64' container/Containerfile || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 2.3: Defer Containerfile parse/build validation to Phase 5**

`podman build` has no `--dry-run` or `--check` flag (confirmed from `podman build --help`). Do **not** run a full image build in this phase. Real Containerfile parse/build validation is deferred to Phase 5 `make build`.

**Acceptance:**
- Layer 3-8 is removed.
- No `HERDR_*` references remain in the Containerfile.
- `test_containerfile_has_no_bespoke_herdr_install` passes.
- Full Containerfile build validation deferred to Phase 5 `make build`.

**Rollback:**
1. Restore Layer 3-8 from git history.
2. Re-run the static policy test from Step 2.2.

---

## Phase 3 — Herdr config update-check suppression

**Files:**
- Modify: [`dot_config/herdr/config.toml`](../../dot_config/herdr/config.toml)
- Modify: [`dot_config/herdr/config.yml`](../../dot_config/herdr/config.yml)

**Goal:** Disable Herdr's own update checks and set channel to `stable` in both managed variants.

- [ ] **Step 3.1: Update `dot_config/herdr/config.toml`**

Replace the existing `[update]` block with:

```toml
[update]
channel = "stable"
version_check = false
manifest_check = false
```

- [ ] **Step 3.2: Update `dot_config/herdr/config.yml`**

Replace the existing `[update]` block with the identical TOML block:

```toml
[update]
channel = "stable"
version_check = false
manifest_check = false
```

The file has a `.yml` extension but its body is TOML-formatted; do not invent YAML syntax.

- [ ] **Step 3.3: Run the policy test**

```bash
cd /data/dotfiles3
python3 -m pytest programs/generate_deps/tests/test_herdr_mise_migration.py -v
```

Expected: all four tests pass.

**Acceptance:**
- Both files contain `channel = "stable"`, `version_check = false`, `manifest_check = false`.
- Policy test `test_herdr_update_checks_disabled` passes.

**Rollback:**
1. Restore both herdr config files from git.

---

## Phase 4 — Spec and historical document sync

**Files:**
- Modify: [`docs/specifications/02-installed-programs.md`](../../docs/specifications/02-installed-programs.md) (prose + already regenerated AUTO-GEN)
- Modify: [`docs/specifications/20-container-rules.md`](../../docs/specifications/20-container-rules.md)
- Modify: [`docs/specifications/21-container-build-flow.md`](../../docs/specifications/21-container-build-flow.md)
- Modify: [`docs/specifications/implementations/2026-07-15-herdr-container-install-design.md`](../../docs/specifications/implementations/2026-07-15-herdr-container-install-design.md) (header only)
- Modify: [`docs/plans/2026-07-15-herdr-container-install-impl.md`](../../docs/plans/2026-07-15-herdr-container-install-impl.md) (header + Task 2 snippet correction)

**Goal:** Keep normative specs and historical docs consistent with the new design.

- [ ] **Step 4.1: Update spec 02 prose**

Add a sentence near the mise-config SoT paragraph stating that `herdr` is now managed via `dot_config/mise/config.toml` as an explicit aqua backend entry.

- [ ] **Step 4.2: Update spec 20**

Replace the existing I-HERDR1, I-HERDR2, and I-HERDR3 invariants (preserve
these stable IDs; do not renumber or drop any). Rewrite all three for mise-based
management mirroring design §3 I1–I7:

- **I-HERDR1** — sole mise/`latest` authority: explicit aqua backend in
  `dot_config/mise/config.toml`, Layer 3-4 install, `mise upgrade` path, no
  `packages.toml` / Containerfile curl bootstrap / `herdr update`.
- **I-HERDR2** — shim + `dotfiles_mise` semantics: PATH via mise shims under
  `$MISE_DATA_DIR/shims`; first-mount copy-on-first-mount seeding; one-time
  `podman volume rm dotfiles_mise` for existing volumes; persistence after
  install present.
- **I-HERDR3** — no runtime state baked; chezmoi-owned config with
  `[update]` checks disabled (`channel = "stable"`, `version_check = false`,
  `manifest_check = false`).

Example opening for I-HERDR1:

```markdown
- I-HERDR1: **`herdr` is installed only through mise.** It is declared as
  `"aqua:ogulcancelik/herdr" = "latest"` in `dot_config/mise/config.toml`
  (explicit aqua backend required by `disable_default_registry = true`).
  Layer 3-4 installs it under `$MISE_DATA_DIR` during the build. Herdr's own
  update checks are disabled in chezmoi-managed config; upgrades use
  `mise upgrade aqua:ogulcancelik/herdr`.
```

- [ ] **Step 4.3: Update spec 21**

1. Remove the Layer 3-8 row from the stage table.
2. Extend the Layer 3 summary row and Layer 3-4 row to include `herdr` (mise
   aqua install at 3-4, not a separate sub-layer).
3. **Replace acceptance criterion #25 in place** (keep stable number 25) with
   version-agnostic mise-shim checks (`herdr --version` exits 0; `which herdr`
   under `$MISE_DATA_DIR/shims`) plus the one-time `dotfiles_mise` volume
   migration note. Do not delete or renumber criterion #25.

- [ ] **Step 4.4: Mark old design superseded**

In [`docs/specifications/implementations/2026-07-15-herdr-container-install-design.md`](../../docs/specifications/implementations/2026-07-15-herdr-container-install-design.md) change the header to:

```markdown
**Status:** superseded
**Date opened:** 2026-07-15
**Issue:** [`../../issues/2026-07-15-herdr-container-install.md`](../../issues/2026-07-15-herdr-container-install.md)
**Superseded by:** [`2026-07-15-herdr-mise-management-design.md`](2026-07-15-herdr-mise-management-design.md)
```

Leave the body unchanged.

- [ ] **Step 4.5: Mark old plan executed and correct Task 2 snippet**

In [`docs/plans/2026-07-15-herdr-container-install-impl.md`](../../docs/plans/2026-07-15-herdr-container-install-impl.md):

1. Change status to `executed`.
2. Add a forward link to the new design in the header.
3. In Task 2, replace the rejected `source /tmp/build-home/.zshenv` + bare
   `herdr --version` snippet with the actually shipped form from
   `git show HEAD:container/Containerfile` (the closed container-install
   commit). The accepted historical snippet is:

```dockerfile
ARG HERDR_VERSION=0.7.3
ARG HERDR_SHA256=043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d
RUN zsh -c 'set -eo pipefail; \
      curl -L --proto "=https" --tlsv1.2 -sSf -o /tmp/herdr \
        https://github.com/ogulcancelik/herdr/releases/download/v${HERDR_VERSION}/herdr-linux-x86_64; \
      printf "%s  /tmp/herdr\n" "${HERDR_SHA256}" | sha256sum -c -; \
      install -D -m 0755 /tmp/herdr "$HOME/.local/bin/herdr"; \
      rm -f /tmp/herdr; \
      "$HOME/.local/bin/herdr" --version; \
    '
```

(No `source /tmp/build-home/.zshenv`; uses `install -D -m 0755`, `rm -f
/tmp/herdr`, and absolute-path `"$HOME/.local/bin/herdr" --version`.)

- [ ] **Step 4.6: Verify old issue/result-log bodies are byte-identical**

```bash
cd /data/dotfiles3
git diff -- docs/issues/2026-07-15-herdr-container-install.md docs/issues/2026-07-15-phase-herdr-container-install.md
```

Expected: no diff.

**Acceptance:**
- Spec 02, 20, 21 reflect mise-based herdr management.
- Old design is `superseded` with a forward link; body unchanged.
- Old plan is `executed` with a forward link and corrected Task 2 snippet; body otherwise unchanged.
- Closed issue and result-log bodies are byte-identical.

**Rollback:**
1. Restore the modified spec and historical doc files from git.

---

## Phase 5 — Build and rollout verification

**Files:** none (verification only)

**Goal:** Confirm the image builds, herdr resolves through mise shims, and the named-volume migration works.

- [ ] **Step 5.1: Build the image**

```bash
cd /data/dotfiles3
make build
```

Expected: build succeeds through all stages; no Layer 3-8 execution; Layer 3-4 installs `aqua:ogulcancelik/herdr`.

- [ ] **Step 5.2: Stop any running container and remove the existing mise volume**

```bash
cd /data/dotfiles3
make down
podman volume rm dotfiles_mise
```

> **One-time only.** New deployments skip this step.

- [ ] **Step 5.3: Start the container**

```bash
cd /data/dotfiles3
make up
```

Expected: container reaches ready state.

- [ ] **Step 5.4: Verify herdr version and shim path**

```bash
podman exec dotfiles-manjaro zsh -ic 'herdr --version'
podman exec dotfiles-manjaro zsh -ic 'which herdr'
```

Expected: `herdr <version>`; path under `$MISE_DATA_DIR/shims/herdr`.

- [ ] **Step 5.5: Verify old install path is gone**

```bash
podman exec dotfiles-manjaro zsh -ic 'test ! -x $HOME/.local/bin/herdr && echo OLD_PATH_GONE'
```

Expected: `OLD_PATH_GONE`.

- [ ] **Step 5.6: Verify herdr config update suppression**

```bash
podman exec dotfiles-manjaro zsh -c 'grep -E "channel|version_check|manifest_check" ~/.config/herdr/config.toml'
podman exec dotfiles-manjaro zsh -c 'grep -E "channel|version_check|manifest_check" ~/.config/herdr/config.yml'
```

Expected: `channel = "stable"` and both checks `false` in both files.

- [ ] **Step 5.7: Verify persistence across restart**

```bash
cd /data/dotfiles3
make down
make up
podman exec dotfiles-manjaro zsh -ic 'herdr --version'
```

Expected: still works.

- [ ] **Step 5.8: Regression checks**

```bash
podman exec dotfiles-manjaro zsh -ic 'go version; node --version; pi --version'
```

Expected: unaffected mise/npm tools still work.

**Acceptance:**
- `make build` succeeds.
- `herdr --version` works inside the container.
- `which herdr` resolves to a mise shim.
- Old `~/.local/bin/herdr` is absent.
- Both herdr config files show stable channel + disabled checks.
- Persistence across `make down && make up` works.
- Regression tools still work.

**Rollback:**
1. Revert all implementation file changes.
2. `make build && make down && podman volume rm dotfiles_mise && make up`.
3. Verify the old `~/.local/bin/herdr` path returns.

---

## Phase 6 — Result-log and issue closure

**Files:**
- Create: `docs/issues/2026-07-15-phase-herdr-mise-management.md`
- Modify: [`docs/issues/2026-07-15-herdr-mise-management.md`](../../docs/issues/2026-07-15-herdr-mise-management.md)

**Goal:** Record acceptance evidence and close the issue.

- [ ] **Step 6.1: Write the result-log**

Create `docs/issues/2026-07-15-phase-herdr-mise-management.md` per doc-management §6.6. Include:

- Commit trail (Phases 1–4 commits, if any).
- Acceptance evidence table matching Phase 5 checks.
- Any residual risks (E1/E2).

- [ ] **Step 6.2: Close the parent issue**

In [`docs/issues/2026-07-15-herdr-mise-management.md`](../../docs/issues/2026-07-15-herdr-mise-management.md), change:

```markdown
**Status:** open
```

to:

```markdown
**Status:** closed (see [result-log](2026-07-15-phase-herdr-mise-management.md))
```

- [ ] **Step 6.3: Mark this plan executed**

Change this plan's header status to `executed`.

**Acceptance:**
- Result-log exists with Phase 5 evidence.
- Parent issue is closed.
- Plan status is `executed`.

**Rollback:**
1. Delete or revert the result-log.
2. Re-open the issue.
3. Set plan status back to `pending`.

---

## Self-review (run after writing the plan, before execution)

- [ ] Every design success criterion (S1–S8) maps to at least one phase.
- [ ] No commit command is present unless explicitly marked `(future commit)`.
- [ ] Placeholder scan: no "TBD" / "implement later" / "similar to Phase N".
- [ ] Rollback per phase is specified.
- [ ] Acceptance criteria per phase are verifiable commands.
