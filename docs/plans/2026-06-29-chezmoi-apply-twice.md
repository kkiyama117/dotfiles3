# Chezmoi Apply Twice — Container Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `container/Containerfile` and `Makefile` so `chezmoi apply` runs twice — once during build to seed XDG-compliant toolchain ENV and install rustup/mise/cargo binaries, once at container start to render the real dotfiles against a host-bind chezmoi source — keeping the image secret-free throughout.

**Architecture:** 5-stage Containerfile (`base` → `build-prepass` → `toolchain` → `runtime`); host bind for `~/.local/share/chezmoi`; named Podman volumes for `~/.local/share/{cargo,rustup,mise}` to survive image rebuilds and avoid overlay-hide of build-time tooling. Build-time apply uses `build_mode = true` chezmoi data flag and writes to scratch `/tmp/build-home`; runtime entrypoint re-renders `chezmoi.toml` with `build_mode = false` and applies for real.

**Tech Stack:** Podman ≥ 4.0 / BuildKit, chezmoi, zsh, rustup, mise, cargo, Python 3.11+ tomllib, Manjaro base image.

**Spec:** [`docs/specifications/implementations/2026-06-29-chezmoi-apply-twice-design.md`](../specifications/implementations/2026-06-29-chezmoi-apply-twice-design.md)

## Global Constraints

- **Secret-free image** (spec 13 / spec 20 I4): no Bitwarden secret may enter any image layer. Build-time `chezmoi apply` runs with `build_mode = true`; runtime `chezmoi apply` consumes `BW_SESSION` only via the host shell of the running container.
- **XDG-compliant paths** (host-equivalent test environment): `CARGO_HOME = $XDG_DATA_HOME/cargo`, `RUSTUP_HOME = $XDG_DATA_HOME/rustup`, `MISE_DATA_DIR = $XDG_DATA_HOME/mise`. No `/opt/dotfiles-tools`.
- **Podman ≥ 4.0** required for `uid=` / `gid=` parameters on `--mount=type=cache`. Verify with `podman --version` before starting Task 5.
- **`USERNAME` defined in `.env`** at repo root (existing). The Makefile aborts when unset.
- **Layer / source-of-truth invariants** (spec 20 I5/I8): `dependencies/layer_<N>/<manager>.txt` files are generated, never hand-edited. Sole source of truth: `dependencies/packages.toml`.
- **No interactive prompts in build** (spec 20 I7): all build-time installers use `--no-tty` / `-y` / equivalent.
- **Initial cargo install list = empty** (resolves spec §10 Open Item 1 — defer concrete list to a follow-up issue; land infrastructure first). Tasks treat the cargo install list as opt-in.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `dot_zshenv` | modify | Append `Toolchain HOMEs` block (CARGO_HOME / RUSTUP_HOME / MISE_DATA_DIR + PATH) |
| `.chezmoiignore` | modify | Add `.local/share/{cargo,rustup,mise,chezmoi}` |
| `dependencies/packages.toml` | modify | Register `cargo` manager note (empty list initially) |
| `programs/generate_deps/main.py` | modify | Accept `cargo` manager; write `dependencies/layer_3/cargo.txt` |
| `programs/generate_deps/tests/test_cargo_manager.py` | create | Unit tests for the cargo-manager extension |
| `dependencies/layer_3/cargo.txt` | create (via `make gen-deps`) | Generator-emitted install list — empty placeholder while no cargo entries exist (kept generated, never hand-edited; spec §9 criterion #10) |
| `container/Containerfile` | rewrite | 5-stage layout: base (+ Layer 1-5) → build-prepass → toolchain → runtime |
| `container/bind/layer_4_files/entrypoint.sh` | create | Runtime `chezmoi apply --no-tty --force` then exec CMD |
| `container/.gitignore` | modify | Drop `home_dir` entry (directory retired) |
| `Makefile` | modify | Add `--build-context srcroot=$(CURDIR)`, new `up` mounts, `clean` target, `.PHONY` |
| `.dockerignore` | create | Exclude `.git`, `docs`, `.env`, `container/bind/home_dir` from `srcroot` context |
| `docs/specifications/13-secret-management.md` | modify | §5 and I-S4 reword to scope "build pre-pass + runtime" |
| `docs/specifications/20-container-rules.md` | modify | I4 + Q1 reword |
| `docs/specifications/21-container-build-flow.md` | modify | Stage table replaced with 5-stage layout; acceptance criteria extended; Q2 added |
| `docs/specifications/02-installed-programs.md` | modify | `cargo` added to allowed managers + manager rules; AUTO-GEN block regenerated |
| `docs/specifications/01-file-structures.md` | modify | Add `layer_4_files/entrypoint.sh` and `dependencies/layer_3/cargo.txt` to tree diagram |

---

## Task 1: Append toolchain HOMEs to `dot_zshenv` and ignore mount targets

**Files:**
- Modify: `dot_zshenv` (append after line 76, the XDG section)
- Modify: `.chezmoiignore`

**Interfaces:**
- Consumes: existing XDG block in `dot_zshenv` (`$XDG_DATA_HOME`)
- Produces: env vars `CARGO_HOME` / `RUSTUP_HOME` / `MISE_DATA_DIR` and PATH entries used by Task 5/6/7 build-time installers and Task 7 runtime shell

- [ ] **Step 1.1: Verify current `dot_zshenv` ends at the XDG block**

Run: `tail -10 dot_zshenv`
Expected: last block is `: "XDG" && { ... export XDG_RUNTIME_DIR=... }`.

- [ ] **Step 1.2: Append the Toolchain HOMEs block to `dot_zshenv`**

Append exactly (after the closing `}` of the XDG block, with one blank line of separation):

```sh

################################################################################
# Toolchain HOMEs (XDG-compliant)
################################################################################
: "Toolchain HOMEs" && {
  export CARGO_HOME="${CARGO_HOME:-$XDG_DATA_HOME/cargo}"
  export RUSTUP_HOME="${RUSTUP_HOME:-$XDG_DATA_HOME/rustup}"
  export MISE_DATA_DIR="${MISE_DATA_DIR:-$XDG_DATA_HOME/mise}"
  path=($CARGO_HOME/bin(N-/) $MISE_DATA_DIR/shims(N-/) $path)
}
```

- [ ] **Step 1.3: Extend `.chezmoiignore`**

Append at the end of the file:

```
# Toolchain volume mountpoints — never managed by chezmoi
.local/share/cargo
.local/share/rustup
.local/share/mise

# Self bind-mount target (chezmoi source root) — chezmoi must not manage itself
.local/share/chezmoi
```

- [ ] **Step 1.4: Verify chezmoi parses the file (dry-run on host)**

Run: `chezmoi apply --dry-run --no-tty 2>&1 | head -20`
Expected: no syntax error, no mention of `.local/share/cargo` as a managed path. If `chezmoi` is not installed on host, skip this step and rely on Task 5 build-time verification.

- [ ] **Step 1.5: Commit**

```bash
git add dot_zshenv .chezmoiignore
git commit -m "feat: add toolchain HOMEs to dot_zshenv and ignore mountpoints"
```

---

## Task 2: Extend `generate_deps` to accept the `cargo` manager

**Files:**
- Modify: `programs/generate_deps/main.py`
- Create: `programs/generate_deps/tests/test_cargo_manager.py`
- Modify: `dependencies/packages.toml` (header comment update only — entries land in Task 3)

**Interfaces:**
- Consumes: existing `LIST_MANAGERS` / `validate()` / `write_txt_files()` in `main.py`
- Produces: `dependencies/layer_3/cargo.txt` (later, when cargo entries exist); the script accepts `manager = "cargo"` without raising

- [ ] **Step 2.1: Write the failing test**

Create `programs/generate_deps/tests/test_cargo_manager.py`:

```python
"""Tests for the cargo-manager extension in generate_deps."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_cargo_listed_in_list_managers() -> None:
    assert "cargo" in main.LIST_MANAGERS


def test_validate_accepts_cargo_manager() -> None:
    main.validate(
        {
            "name": "ripgrep",
            "manager": "cargo",
            "layer": 3,
            "has_configs": False,
        }
    )


def test_render_packages_txt_emits_cargo_entries() -> None:
    tools = [
        {"name": "ripgrep", "manager": "cargo", "layer": 3, "has_configs": False},
        {"name": "eza", "manager": "cargo", "layer": 3, "has_configs": False,
         "description": "modern ls"},
    ]
    out = main.render_packages_txt(3, "cargo", tools)
    assert "manager: cargo" in out
    assert "ripgrep" in out
    assert "eza  # modern ls" in out


def test_write_txt_files_creates_layer_3_cargo_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    by_layer = {
        3: [{"name": "ripgrep", "manager": "cargo", "layer": 3,
             "has_configs": False}],
    }
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "cargo.txt"
    assert n == 1
    assert out.is_file()
    assert "ripgrep" in out.read_text()


def test_write_txt_files_emits_empty_cargo_txt_when_no_entries(tmp_path, monkeypatch) -> None:
    """layer_3/cargo.txt must exist even with zero entries so the
    Containerfile `COPY --from=deps layer_3/cargo.txt` does not fail.
    Spec §9 criterion #10: never hand-edited."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    by_layer = {1: [{"name": "git", "manager": "pacman", "layer": 1,
                     "has_configs": False}]}
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "cargo.txt"
    assert out.is_file()
    body = out.read_text()
    assert "manager: cargo" in body
    assert "packages: 0" in body
```

- [ ] **Step 2.2: Run the tests and verify they fail**

Run: `cd programs/generate_deps && python3 -m pytest tests/test_cargo_manager.py -v`
Expected: 5 failures (e.g. `AssertionError: assert 'cargo' in ('pacman', 'paru', 'nix', 'uv')`).

- [ ] **Step 2.3: Add `cargo` to `LIST_MANAGERS` and emit an empty placeholder for `(layer=3, manager=cargo)`**

In `programs/generate_deps/main.py`, change:

```python
LIST_MANAGERS = ("pacman", "paru", "nix", "uv")
```

to:

```python
LIST_MANAGERS = ("pacman", "paru", "nix", "uv", "cargo")

# (layer, manager) pairs that always have a generated install list file,
# even when no entries exist. Required because the Containerfile COPYs
# `dependencies/layer_3/cargo.txt` unconditionally; a missing file breaks
# the build. Keeping the file generator-owned satisfies spec §9 criterion
# #10 (never hand-edited).
EXPECTED_EMPTY_FILES: tuple[tuple[int, str], ...] = ((3, "cargo"),)
```

Then in `write_txt_files`, after the existing per-layer loop and before the
`return written`, append:

```python
    # Emit empty install-list files for (layer, manager) pairs that the
    # build expects unconditionally (see EXPECTED_EMPTY_FILES above).
    for layer, mgr in EXPECTED_EMPTY_FILES:
        existing = [
            t for t in by_layer.get(layer, []) if t["manager"] == mgr
        ]
        if existing:
            continue  # already emitted by the main loop
        out = DEPS_DIR / f"layer_{layer}" / f"{mgr}.txt"
        if write_if_changed(out, render_packages_txt(layer, mgr, [])):
            written += 1
```

No schema bump (additive change; existing entries unaffected — resolves spec §10 Open Item 2).

- [ ] **Step 2.4: Run the tests and verify they pass**

Run: `cd programs/generate_deps && python3 -m pytest tests/test_cargo_manager.py -v`
Expected: 5 passed.

- [ ] **Step 2.5: Regenerate and confirm `layer_3/cargo.txt` is emitted empty**

Run from repo root: `make gen-deps`
Expected: prints `generate_deps: layers=[0, 1] txt_written=1` (the new empty `layer_3/cargo.txt`). The file now contains the AUTO-GEN header + `# manager: cargo | layer: 3 | packages: 0` and nothing else.

Run: `cat dependencies/layer_3/cargo.txt`
Expected: header lines + `# manager: cargo | layer: 3 | packages: 0` + blank line.

- [ ] **Step 2.6: Update `packages.toml` example comment**

In `dependencies/packages.toml`, find the example comment block ending with `description = "base meta-package: gcc, make, binutils, etc."`. Append below it (still as a comment):

```
#
# Allowed `manager` values: pacman, paru, nix, uv, cargo, mise.
# `cargo` entries land in layer 3 (Containerfile `toolchain` stage).
```

- [ ] **Step 2.7: Commit**

```bash
git add programs/generate_deps/main.py programs/generate_deps/tests/test_cargo_manager.py dependencies/packages.toml dependencies/layer_3/cargo.txt
git commit -m "feat(generate_deps): accept cargo manager, emit empty layer_3/cargo.txt"
```

---

## Task 3: Add layer-3 marker comment to `packages.toml`

**Files:**
- Modify: `dependencies/packages.toml` (comment marker only — no `[[tool]]` entries yet)

**Interfaces:**
- Consumes: `LIST_MANAGERS` from Task 2 (so adding cargo entries here would validate cleanly)
- Produces: nothing functional — documents maintainer intent; the actual layer_3/cargo.txt is owned by gen-deps (Task 2 Step 2.5 emitted it empty).

> **Note:** The cargo install list is intentionally empty at this stage (resolves spec §10 Open Item 1 per maintainer guidance to land infrastructure first). Adding entries is a follow-up commit, not part of this plan. Spec §9 criterion #10 is satisfied because `dependencies/layer_3/cargo.txt` is now owned by gen-deps (committed in Task 2).

- [ ] **Step 3.1: Add layer-3 marker comment to `packages.toml`**

Append at the end of `dependencies/packages.toml`:

```toml

# Layer 3: cargo-installed tools (Containerfile `toolchain` stage).
# Add `[[tool]]` entries with `manager = "cargo"` and `layer = 3`.
# Run `make gen-deps` to regenerate `dependencies/layer_3/cargo.txt`.
# (Currently empty — infrastructure-only landing per design spec §10 item 1.
# The empty cargo.txt is still generator-owned: see
# EXPECTED_EMPTY_FILES in programs/generate_deps/main.py.)
```

- [ ] **Step 3.2: Verify `make gen-deps` is idempotent**

Run from repo root: `make gen-deps`
Expected: `txt_written=0` (the empty placeholder already exists from Task 2 and matches what gen-deps would write — `write_if_changed` is a no-op).

- [ ] **Step 3.3: Commit**

```bash
git add dependencies/packages.toml
git commit -m "chore(deps): document layer 3 cargo entry slot"
```

---

## Task 4: Add Containerfile Layer 1-5 (provision XDG dirs)

**Files:**
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: `${HOST_UID}`, `${HOST_GID}`, `${USERNAME}` build-args (existing)
- Produces: owner-correct `/home/${USERNAME}/.local/share/{cargo,rustup,mise,chezmoi}` directories so runtime mounts attach cleanly (consumed by Task 8 `up`)

- [ ] **Step 4.1: Insert Layer 1-5 directly after the existing `USER ${USERNAME}` (Line 90)**

In `container/Containerfile`, between the existing `USER ${USERNAME}` (line 90) and the `# Layer 2 ...` comment block (line 92), insert:

```dockerfile

# Layer 1-5: XDG-compliant home subdirectories
#
# Owner-correct directories must exist so the four runtime mounts (one bind
# for chezmoi source, three named volumes for cargo/rustup/mise) attach to
# a properly-owned ~/.local/share/ parent. install -d as root, then return
# to ${USERNAME} so subsequent stages stay non-root.
USER root
RUN install -d -o ${HOST_UID} -g ${HOST_GID} -m 0755 \
    /home/${USERNAME}/.local \
    /home/${USERNAME}/.local/share \
    /home/${USERNAME}/.local/share/cargo \
    /home/${USERNAME}/.local/share/rustup \
    /home/${USERNAME}/.local/share/mise \
    /home/${USERNAME}/.local/share/chezmoi
USER ${USERNAME}
```

- [ ] **Step 4.2: Sanity-build the `base` stage in isolation**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman build --target base \
  --build-arg HOST_UID=$(id -u) \
  --build-arg HOST_GID=$(id -g) \
  --build-arg USERNAME=${USERNAME} \
  --build-context deps=$(pwd)/dependencies \
  -t dotfiles-base-test container/
```
Expected: build succeeds.

- [ ] **Step 4.3: Verify the XDG directories exist with correct ownership**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman run --rm dotfiles-base-test ls -lna /home/${USERNAME}/.local/share
```
Expected: `cargo`, `rustup`, `mise`, `chezmoi` directories listed; owner uid/gid match `id -u` / `id -g`.

- [ ] **Step 4.4: Clean up the test image**

Run: `podman rmi dotfiles-base-test`

- [ ] **Step 4.5: Commit**

```bash
git add container/Containerfile
git commit -m "feat(container): add Layer 1-5 XDG directory provisioning"
```

---

## Task 5: Replace `no-config-base` with Stage 2 `build-prepass`

**Files:**
- Modify: `container/Containerfile`
- Modify: `Makefile` (add `--build-context srcroot=$(CURDIR)` to `build`)

**Interfaces:**
- Consumes: `srcroot` named build-context (passed by Makefile), `${USERNAME}`, `${HOST_UID}`, `${HOST_GID}`
- Produces: `/tmp/build-home/.zshenv` inside the build-prepass image (consumed by Task 6 `source /tmp/build-home/.zshenv`)

- [ ] **Step 5.1: Verify Podman version supports BuildKit cache-mount uid/gid**

Run: `podman --version`
Expected: `podman version 4.x.x` or newer. If older, halt and report — Task 6 requires this.

- [ ] **Step 5.2: Replace the `no-config-base` stage with `build-prepass`**

In `container/Containerfile`, replace the existing `# Layer 2 ...` comment block (currently lines 92-101) and the trailing `FROM base AS no-config-base` (line 102) with:

```dockerfile

# ---------------------------------------------------------------------------
# Stage 2: build-prepass
#
# Run `chezmoi apply` with `build_mode = true` against a scratch destination
# so the resolved environment (CARGO_HOME, RUSTUP_HOME, MISE_DATA_DIR, PATH)
# becomes sourceable in Stage 3 without leaking secrets. The scratch
# destination is removed in Stage 4 before the final image layer.
# ---------------------------------------------------------------------------
FROM base AS build-prepass

COPY --from=srcroot --chown=${HOST_UID}:${HOST_GID} . /tmp/chezmoi-src

RUN mkdir -p /home/${USERNAME}/.config/chezmoi \
 && cat > /home/${USERNAME}/.config/chezmoi/chezmoi.toml <<'TOML'
[data]
build_mode = true
TOML

RUN chezmoi apply \
      --source /tmp/chezmoi-src \
      --destination /tmp/build-home \
      --no-tty \
      --force
```

- [ ] **Step 5.3: Add `srcroot` build-context to the Makefile `build` target**

In `Makefile`, find the existing line:

```makefile
	--build-context deps=$(CURDIR)/dependencies \
```

Add immediately after it (preserving the trailing backslash chain):

```makefile
	--build-context srcroot=$(CURDIR) \
```

- [ ] **Step 5.4: Build the build-prepass stage**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman build --target build-prepass \
  --build-arg HOST_UID=$(id -u) \
  --build-arg HOST_GID=$(id -g) \
  --build-arg USERNAME=${USERNAME} \
  --build-context deps=$(pwd)/dependencies \
  --build-context srcroot=$(pwd) \
  -t dotfiles-prepass-test container/
```
Expected: build succeeds; chezmoi apply prints managed paths and exits 0.

- [ ] **Step 5.5: Verify `.zshenv` was rendered to the scratch destination**

Run:
```bash
podman run --rm dotfiles-prepass-test bash -c \
  'test -f /tmp/build-home/.zshenv && grep -E "^export (CARGO_HOME|RUSTUP_HOME|MISE_DATA_DIR)" /tmp/build-home/.zshenv'
```
Expected: three matching `export` lines printed; exit 0.

- [ ] **Step 5.6: Clean up the test image**

Run: `podman rmi dotfiles-prepass-test`

- [ ] **Step 5.7: Commit**

```bash
git add container/Containerfile Makefile
git commit -m "feat(container): replace no-config-base with build-prepass stage"
```

---

## Task 6: Add Stage 3 `toolchain` — rustup, mise, and cargo install

**Files:**
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: `/tmp/build-home/.zshenv` from Stage 2; `dependencies/layer_3/cargo.txt` (Task 3) via `--from=deps`
- Produces: `$CARGO_HOME/bin/{rustup,cargo,rustc,...}`, `$MISE_DATA_DIR/...` populated; cargo-installed binaries (if any) under `$CARGO_HOME/bin/`

- [ ] **Step 6.1: Append Stage 3 to `Containerfile`**

After the Stage 2 `RUN chezmoi apply --destination /tmp/build-home ...` block, append:

```dockerfile

# ---------------------------------------------------------------------------
# Stage 3: toolchain
#
# Install rustup, mise, and cargo binaries with ENV inherited from the
# build-prepass scratch render. Each RUN is a fresh shell, so each must
# `source /tmp/build-home/.zshenv` to materialize CARGO_HOME / RUSTUP_HOME /
# MISE_DATA_DIR. BuildKit cache mounts (uid/gid require Podman >= 4.0) keep
# the cargo registry index / git checkouts across rebuilds without bloating
# image layers.
# ---------------------------------------------------------------------------
FROM build-prepass AS toolchain

RUN --mount=type=cache,target=/home/${USERNAME}/.cache/cargo-install,uid=${HOST_UID},gid=${HOST_GID} \
    bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --no-modify-path --default-toolchain stable --profile minimal; \
    '

RUN bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      curl https://mise.run | sh; \
    '

COPY --from=deps layer_3/cargo.txt /tmp/cargo_tools.txt

RUN --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/registry,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/git,uid=${HOST_UID},gid=${HOST_GID} \
    bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/cargo_tools.txt | xargs); \
      if [ -n "$pkgs" ]; then \
        cargo install --locked $pkgs; \
      else \
        echo "toolchain: cargo install list is empty -- skipping"; \
      fi; \
    '
```

- [ ] **Step 6.2: Build the toolchain stage**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman build --target toolchain \
  --build-arg HOST_UID=$(id -u) \
  --build-arg HOST_GID=$(id -g) \
  --build-arg USERNAME=${USERNAME} \
  --build-context deps=$(pwd)/dependencies \
  --build-context srcroot=$(pwd) \
  -t dotfiles-toolchain-test container/
```
Expected: build succeeds; rustup prints `Rust is installed now.`; mise prints its install banner; cargo step prints `cargo install list is empty -- skipping`.

- [ ] **Step 6.3: Verify rustc / cargo / mise are on PATH**

Run:
```bash
podman run --rm dotfiles-toolchain-test bash -lc \
  'source /tmp/build-home/.zshenv && rustc --version && cargo --version && mise --version'
```
Expected: three version strings printed (e.g. `rustc 1.x.x`, `cargo 1.x.x`, `mise 2024.x.x`).

- [ ] **Step 6.4: Clean up the test image**

Run: `podman rmi dotfiles-toolchain-test`

- [ ] **Step 6.5: Commit**

```bash
git add container/Containerfile
git commit -m "feat(container): add Stage 3 toolchain (rustup, mise, cargo)"
```

---

## Task 7: Create `entrypoint.sh` and add Stage 4 `runtime`

**Files:**
- Create: `container/bind/layer_4_files/entrypoint.sh`
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: `/tmp/build-home/.zshenv`, `/tmp/chezmoi-src`, `/home/${USERNAME}/.config/chezmoi/chezmoi.toml` from Stage 3 (all removed in Stage 4)
- Produces: final image with `ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]` and `CMD ["zsh"]`; entrypoint re-renders `chezmoi.toml` with `build_mode = false` and runs `chezmoi apply --no-tty --force` against the host-bound source root

- [ ] **Step 7.1: Create `container/bind/layer_4_files/entrypoint.sh`**

Create directory `container/bind/layer_4_files/` and file `entrypoint.sh` with content exactly:

```bash
#!/usr/bin/env bash
#
# Container entrypoint — runtime chezmoi apply against the host-bound source.
#
# The container is started by `make up` with the repo root bind-mounted at
# ~/.local/share/chezmoi. This script:
#   1. Verifies the bind is in place (the source root has .git).
#   2. Re-renders ~/.config/chezmoi/chezmoi.toml with build_mode = false
#      (the build-time toml was removed in Stage 4).
#   3. Runs `chezmoi apply --no-tty --force` so the real $HOME picks up the
#      latest dotfiles, optionally resolving Bitwarden secrets when the
#      operator exported BW_SESSION before `make up`.
#   4. Execs CMD.
set -euo pipefail

CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"
RUNTIME_CONFIG="${HOME}/.config/chezmoi/chezmoi.toml"

if [[ ! -d "$CHEZMOI_SOURCE/.git" ]]; then
  echo "entrypoint: $CHEZMOI_SOURCE is not a chezmoi source (no .git)." >&2
  echo "entrypoint: did make up bind the repo root into ~/.local/share/chezmoi?" >&2
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML

chezmoi apply --no-tty --force

exec "$@"
```

- [ ] **Step 7.2: Append Stage 4 to `Containerfile`**

After the Stage 3 cargo-install `RUN` block, append:

```dockerfile

# ---------------------------------------------------------------------------
# Stage 4: runtime (final)
#
# Strip Stage 2/3 scratch artifacts (so they cannot ride in the final layer),
# install the entrypoint that re-runs chezmoi apply at container start with
# build_mode = false, and set USER/WORKDIR/ENTRYPOINT/CMD.
# ---------------------------------------------------------------------------
FROM toolchain AS runtime

USER root
RUN rm -rf /tmp/chezmoi-src /tmp/build-home /home/${USERNAME}/.config/chezmoi
COPY --chown=root:root bind/layer_4_files/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

USER ${USERNAME}
WORKDIR /home/${USERNAME}
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["zsh"]
```

- [ ] **Step 7.3: Mark entrypoint.sh executable in the working tree**

Run: `chmod 0755 container/bind/layer_4_files/entrypoint.sh`

- [ ] **Step 7.4: Build the full image**

Run: `make build`
Expected: build succeeds end-to-end across all 4 stages.

- [ ] **Step 7.5: Verify scratch artifacts are gone in the final image**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman run --rm localhost/dotfiles-manjaro:latest bash -c \
  "test ! -d /tmp/chezmoi-src && test ! -d /tmp/build-home && test ! -d /home/${USERNAME}/.config/chezmoi"
```
Expected: exit 0 (all three removed).

- [ ] **Step 7.6: Commit**

```bash
git add container/bind/layer_4_files/entrypoint.sh container/Containerfile
git commit -m "feat(container): add Stage 4 runtime with chezmoi-apply entrypoint"
```

---

## Task 8: Update `Makefile` mounts (`up` + `clean`)

**Files:**
- Modify: `Makefile`

**Interfaces:**
- Consumes: `$(CURDIR)`, `$(IMAGE)`, `$(CONTAINER)`, `$(USERNAME)` (existing)
- Produces: `make up` mounts the repo as `~/.local/share/chezmoi` and three named volumes for cargo/rustup/mise; `make clean` removes them. The entrypoint added in Task 7 expects exactly this layout.

- [ ] **Step 8.1: Replace `HOME_DIR` block with named-volume variables**

In `Makefile`, replace the existing two lines (currently lines 15-16):

```makefile
# Bind mount for the container home directory
HOME_DIR := $(CURDIR)/container/bind/home_dir
```

with:

```makefile
# Named volumes for toolchain dirs (Podman copy-on-first-mount: build-time
# binaries under $CARGO_HOME / $RUSTUP_HOME / $MISE_DATA_DIR survive into
# the volume on the first `make up`; a host bind would hide them).
CARGO_VOLUME  := dotfiles_cargo
RUSTUP_VOLUME := dotfiles_rustup
MISE_VOLUME   := dotfiles_mise
```

- [ ] **Step 8.2: Update `.PHONY`**

In `Makefile`, replace the existing `.PHONY` line:

```makefile
.PHONY: help build build_container up exec down _require_username gen-deps
```

with:

```makefile
.PHONY: help build build_container up exec down clean _require_username gen-deps
```

- [ ] **Step 8.3: Add the `clean` line to the `help` target**

In the `help` target, insert after the line that echoes `"  down ..."`:

```makefile
	@echo "  clean           Stop container, remove image, and delete toolchain volumes"
```

- [ ] **Step 8.4: Rewrite the `up` target**

In `Makefile`, replace the existing `up:` target (currently lines 52-57):

```makefile
up: _require_username ## Start a detached container with the home bind mount
	@mkdir -p $(HOME_DIR)
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		-v $(HOME_DIR):/home/$(USERNAME) \
		$(IMAGE) sleep infinity
```

with:

```makefile
up: _require_username ## Start a detached container with chezmoi bind + toolchain volumes
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity
```

> Rationale: `sleep infinity` keeps the container alive; the `ENTRYPOINT` added in Task 7 still runs once (`podman run` invokes the entrypoint before CMD/args), executing the runtime `chezmoi apply` and then `exec sleep infinity` as the long-running PID 1.

- [ ] **Step 8.5: Add the `clean` target after `down`**

In `Makefile`, after the `down` target body, append:

```makefile

clean: down ## Full reset: stop container, remove image, and delete toolchain volumes
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME)
	-podman rmi $(IMAGE)
```

- [ ] **Step 8.6: Verify `make up` and a runtime apply succeed**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
make build
make up
sleep 2
podman exec dotfiles-manjaro test -f /home/${USERNAME}/.zshenv
echo "exit=$?"
```
Expected: `exit=0` (runtime apply rendered .zshenv into $HOME).

- [ ] **Step 8.7: Verify the host bind is rw and source root visible**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman exec dotfiles-manjaro ls /home/${USERNAME}/.local/share/chezmoi/.git
```
Expected: exit 0; `.git` directory listing printed.

- [ ] **Step 8.8: Verify `make clean` reset**

Run:
```bash
make clean
podman volume ls | grep -E 'dotfiles_(cargo|rustup|mise)' && echo "FAIL: volumes still present" || echo "OK: volumes gone"
podman image ls | grep dotfiles-manjaro && echo "FAIL: image still present" || echo "OK: image gone"
```
Expected: both lines print `OK: ...`.

- [ ] **Step 8.9: Commit**

```bash
git add Makefile
git commit -m "feat(make): bind chezmoi source, named toolchain volumes, clean target"
```

---

## Task 9: Add `.dockerignore` and clean up `container/.gitignore`

**Files:**
- Create: `.dockerignore` (repo root)
- Modify: `container/.gitignore` (drop `home_dir` entry if present)

**Interfaces:**
- Consumes: nothing
- Produces: smaller `srcroot` build-context (consumed by Task 5)

- [ ] **Step 9.1: Inspect the current state of `container/.gitignore`**

Run: `cat container/.gitignore 2>/dev/null || echo "(missing)"`
If a `home_dir` line exists, note it for Step 9.3. If the file does not exist, skip Step 9.3.

- [ ] **Step 9.2: Create `.dockerignore` at the repo root**

Create `.dockerignore` with content exactly:

```
# srcroot build-context exclusions (consumed by container/Containerfile
# Stage 2 via `--build-context srcroot=$(CURDIR)` in the Makefile).
# Excluding these keeps the chezmoi apply source tight and avoids
# accidentally baking host-only files into image layers.

.git
docs
.env
container/bind/home_dir
```

- [ ] **Step 9.3: If `container/.gitignore` lists `home_dir`, remove that line**

In `container/.gitignore`, remove any line equal to `home_dir` or `home_dir/`. Keep all other entries.

- [ ] **Step 9.4: Remove the now-unused bind directory**

Run: `rm -rf container/bind/home_dir`
(The directory may not exist on a clean checkout; `-rf` is idempotent.)

- [ ] **Step 9.5: Verify the build still succeeds**

Run: `make build`
Expected: build succeeds (no breakage from the trimmed context).

- [ ] **Step 9.6: Commit**

```bash
git add .dockerignore container/.gitignore
git rm -rf --ignore-unmatch container/bind/home_dir
git commit -m "chore(container): add .dockerignore, retire home_dir bind"
```

---

## Task 10: Run §9 acceptance criteria 1-8 (end-to-end smoke gate)

**Files:** none modified — verification only.

**Interfaces:** consumes the full Task 1-9 stack.

- [ ] **Step 10.1: Reset to a clean slate**

Run: `make clean || true`

- [ ] **Step 10.2: Build the image**

Run: `make build`
Expected (criterion #1): build completes without manual intervention.

- [ ] **Step 10.3: Verify scratch removed (criterion #2)**

Run: `podman run --rm localhost/dotfiles-manjaro:latest /bin/bash -c 'test ! -d /tmp/chezmoi-src && test ! -d /tmp/build-home'; echo $?`
Expected: `0`.

- [ ] **Step 10.4: Verify toolchain versions (criterion #3)**

Run: `podman run --rm localhost/dotfiles-manjaro:latest /bin/bash -lc 'rustc --version && cargo --version && mise --version'`
Expected: three version strings.

- [ ] **Step 10.5: Verify runtime apply succeeded (criterion #4)**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
make up
sleep 2
podman exec dotfiles-manjaro test -f /home/${USERNAME}/.zshenv; echo $?
```
Expected: `0`.

- [ ] **Step 10.6: Verify $CARGO_HOME is XDG-compliant (criterion #5)**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman exec dotfiles-manjaro bash -lc 'echo $CARGO_HOME'
```
Expected: `/home/${USERNAME}/.local/share/cargo`.

- [ ] **Step 10.7: Verify host bind visibility (criterion #6)**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman exec dotfiles-manjaro ls /home/${USERNAME}/.local/share/chezmoi/.git; echo $?
```
Expected: `0`.

- [ ] **Step 10.8: Verify volumes persist across `down`/`up` (criterion #7)**

Run:
```bash
make down
make up
sleep 2
podman exec dotfiles-manjaro bash -lc 'rustc --version'
```
Expected: same rustc version as Step 10.4 (volume preserved the toolchain).

- [ ] **Step 10.9: Verify `make clean` removes everything (criterion #8)**

Run:
```bash
make clean
podman volume ls | grep -E 'dotfiles_(cargo|rustup|mise)' && echo "FAIL" || echo "OK"
podman image ls | grep dotfiles-manjaro && echo "FAIL" || echo "OK"
```
Expected: both lines print `OK`.

- [ ] **Step 10.10: If any criterion fails**

Identify the failing criterion, return to the originating task (4-9), fix, recommit, and rerun **all** steps in Task 10 from 10.1.

- [ ] **Step 10.11: Commit (only if any code change was made in 10.10)**

```bash
git commit -m "fix(container): resolve acceptance-criteria failure in <area>"
```

If no changes, skip the commit and proceed to Task 11.

---

## Task 11: Spec edit — `13-secret-management.md` (§5 + I-S4)

**Files:**
- Modify: `docs/specifications/13-secret-management.md`

**Interfaces:**
- Consumes: none
- Produces: spec text consistent with implemented behavior. Spec §10 Open Item 6 (build_mode convention) is referenced as a future issue.

- [ ] **Step 11.1: Re-read the current §5 and find I-S4**

Run: `grep -n -E '^## §5|I-S4' docs/specifications/13-secret-management.md`
Note the line numbers; the wording you replace must say "chezmoi apply runs at runtime only" or similar.

- [ ] **Step 11.2: Reword §5**

Replace the current §5 body with text equivalent to:

```
## §5 — Apply phases

Chezmoi apply runs in two phases:

1. **Build-time pre-pass** (Containerfile Stage 2 `build-prepass`). Runs
   against a scratch destination (`/tmp/build-home`) with `build_mode = true`
   in the chezmoi data. Renders ENV-bearing dotfiles only; Bitwarden-bound
   templates are guarded by `{{- if not .build_mode -}}` (or excluded via
   `.chezmoiignore` templates) so the build never consults `bw`. The
   scratch destination is deleted in Stage 4 before the final image layer
   is finalized.

2. **Runtime apply** (`container/bind/layer_4_files/entrypoint.sh`). Runs
   against the real `$HOME` against the host-bind chezmoi source at
   `~/.local/share/chezmoi`. Resolves Bitwarden templates when the
   operator exported `BW_SESSION` before `make up`. The image layers stay
   secret-free because `BW_SESSION` lives only in the running container's
   process environment.
```

- [ ] **Step 11.3: Reword I-S4**

Replace the I-S4 invariant text with text equivalent to:

```
I-S4: Image layers contain no resolved secret. The build-time pre-pass
runs `chezmoi apply` only with `build_mode = true`, which excludes every
Bitwarden-bound template. The runtime apply renders secrets only into
the running container's `$HOME`, never back into image layers.
```

- [ ] **Step 11.4: Append §8 Q3 future-issue note**

At the end of the existing §8 ("Open questions") section, append:

```
- Q3: Build-mode template guard convention. Whether Bitwarden-bound
  templates should be guarded with `{{- if not .build_mode -}}` inside
  the template or excluded via `.chezmoiignore` template-based rules is
  unresolved. Pick one before introducing the first Bitwarden-bound
  dotfile. (Tracked: design doc §10 item 6.)
```

- [ ] **Step 11.5: Lint the file shape**

Run: `grep -c '^## ' docs/specifications/13-secret-management.md`
Expected: same number of `##` headings as before (you only edited content, not added/removed sections).

- [ ] **Step 11.6: Commit**

```bash
git add docs/specifications/13-secret-management.md
git commit -m "docs(spec-13): scope chezmoi apply to build-prepass + runtime"
```

---

## Task 12: Spec edit — `20-container-rules.md` (I4 + Q1)

**Files:**
- Modify: `docs/specifications/20-container-rules.md`

- [ ] **Step 12.1: Find I4**

Run: `grep -n -E 'I4|## §' docs/specifications/20-container-rules.md`
Note the line numbers.

- [ ] **Step 12.2: Reword I4**

Replace the I4 text with text equivalent to:

```
I4: The image is secret-free in both phases. The build-time `chezmoi
apply` pre-pass (Containerfile Stage 2) uses `build_mode = true`, which
guards every Bitwarden-bound template; the scratch destination is
deleted in Stage 4. The runtime `chezmoi apply` (entrypoint) consumes
`BW_SESSION` only into the running container's $HOME, never into image
layers.
```

- [ ] **Step 12.3: Refresh Q1 wording**

In the "Open questions" section of spec 20, find Q1 (which currently asserts that chezmoi apply runs only at runtime) and rewrite it to:

```
Q1: Resolved. Chezmoi apply runs in two phases — a build-time pre-pass
in Stage 2 (`build_mode = true`, scratch destination) and a runtime
apply via the entrypoint. See [`13-secret-management.md`](13-secret-management.md)
§5 for the contract.
```

- [ ] **Step 12.4: Commit**

```bash
git add docs/specifications/20-container-rules.md
git commit -m "docs(spec-20): I4 covers secret-free build pre-pass + runtime"
```

---

## Task 13: Spec edit — `21-container-build-flow.md` (stage table + acceptance + Q2)

**Files:**
- Modify: `docs/specifications/21-container-build-flow.md`

- [ ] **Step 13.1: Replace the Stage ordering table**

Find the table header `| Stage (\`FROM ... AS\`) | Sub-layer | ...` and replace from that header through the closing row (the `_(planned)_ tooling` row) with this new table:

```markdown
| Stage (`FROM ... AS`) | Sub-layer | Directive(s) | Purpose | Inputs |
|---|---|---|---|---|
| `manjarolinux/base:latest` | 0-1 | - | Base image | - |
| `base` | 1-1 | `ARG` | Receive build-args. | `HOST_UID`, `HOST_GID`, `USERNAME` |
| `base` | 1-2 | mirrorlist + `pacman -Sy` | Install Layer 1 pacman set with BuildKit cache. | `bind/layer_1_files/pacman_mirrorlist`, `dependencies/layer_1/pacman.txt` |
| `base` | 1-3 | `groupmod` / `usermod` | Remap builder -> ${USERNAME} with host uid/gid; set zsh login. | build-args |
| `base` | 1-4 | UID-collision fallback + sudoers + `USER ${USERNAME}` | Idempotent user provisioning; NOPASSWD sudoers; switch to non-root. | build-args |
| `base` | 1-5 | `install -d` for `~/.local/share/{cargo,rustup,mise,chezmoi}` | Owner-correct mountpoints for runtime binds/volumes. | build-args |
| `build-prepass` (`FROM base`) | 2 | `COPY --from=srcroot` + `chezmoi apply --destination /tmp/build-home` | Scratch render of ENV-bearing dotfiles with `build_mode = true`; secret-free. | `srcroot` named build-context |
| `toolchain` (`FROM build-prepass`) | 3 | `rustup-init`, mise installer, `cargo install`; cache mounts on `$CARGO_HOME/{registry,git}` | Install rustup/mise/cargo binaries under XDG-compliant paths. | `/tmp/build-home/.zshenv`, `dependencies/layer_3/cargo.txt` |
| `runtime` (`FROM toolchain`) | 4 | `rm -rf` scratch; `COPY entrypoint.sh`; `USER`/`WORKDIR`/`ENTRYPOINT`/`CMD` | Final image. Scratch artifacts removed; entrypoint runs runtime `chezmoi apply` against host bind. | `container/bind/layer_4_files/entrypoint.sh` |
```

- [ ] **Step 13.2: Update "Notes on the current state"**

Replace the existing bullet list under "Notes on the current state" with text equivalent to:

```
- The image is fully implemented across 4 stages. `no-config-base`
  is retired.
- `base` Layer 1-5 provisions XDG-compliant directories so the three
  Podman named volumes (cargo / rustup / mise) and the host bind for
  the chezmoi source root attach without overlay-hiding image content.
- The build-prepass scratch (`/tmp/chezmoi-src`, `/tmp/build-home`) and
  the build-time `~/.config/chezmoi` are deleted in Stage 4 before the
  final image layer is finalized.
```

- [ ] **Step 13.3: Extend the Acceptance criteria list**

Append items 5-8 to the existing numbered list:

```
5. The final image has no `/tmp/chezmoi-src`, `/tmp/build-home`, or
   `~/.config/chezmoi` directory (Stage 4 scratch removal asserted).
6. `podman run --rm <image> bash -lc 'echo $CARGO_HOME'` outputs
   `~/.local/share/cargo` (XDG-compliant).
7. After `make up`, `~/.local/share/chezmoi/.git` is visible inside the
   container (host bind verified).
8. `make down && make up` preserves toolchain binaries (named-volume
   persistence verified).
```

- [ ] **Step 13.4: Update Q1 partial-resolution note + add Q2**

In the "Open questions" section, replace the Q1 paragraph with:

```
- Q1: AUR / `paru` build scheduling and cache mount. Layer 1-4 provisions
  NOPASSWD sudoers so `paru` / `makepkg` can run non-interactively. Open
  parts: (a) whether AUR builds happen in a Stage 3-equivalent build
  stage or via a dedicated layer; (b) whether the `paru` / AUR cache is
  also backed by `--mount=type=cache` (the pacman cache already is).
```

Append after Q1:

```
- Q2: `.dockerignore` policy. The repo-root `.dockerignore` currently
  excludes `.git`, `docs`, `.env`, and `container/bind/home_dir`.
  Additional paths to exclude from the `srcroot` build context (large
  untracked subtrees, editor swap files, etc.) need a convention.
```

- [ ] **Step 13.5: Commit**

```bash
git add docs/specifications/21-container-build-flow.md
git commit -m "docs(spec-21): rewrite stage table for 5-stage layout"
```

---

## Task 14: Spec edit — `02-installed-programs.md` (cargo manager rules)

**Files:**
- Modify: `docs/specifications/02-installed-programs.md`

**Interfaces:**
- Consumes: the `cargo` manager added in Task 2
- Produces: spec text consistent with `LIST_MANAGERS`. AUTO-GEN block regenerates only when at least one cargo entry exists (currently zero, so the block is unchanged).

- [ ] **Step 14.1: Find the contract table**

Run: `grep -n '| `manager`' docs/specifications/02-installed-programs.md`
Expected: a row listing `pacman / paru / nix / mise / uv`.

- [ ] **Step 14.2: Add `cargo` to the manager allowed values**

Replace:

```
| `manager`     | yes | `pacman` / `paru` / `nix` / `mise` / `uv` |
```

with:

```
| `manager`     | yes | `pacman` / `paru` / `nix` / `mise` / `uv` / `cargo` |
```

- [ ] **Step 14.3: Add a cargo bullet to the "manager rules" section**

In the `## manager rules` section, after the existing `uv` bullet, append:

```
- `cargo`: installed via `cargo install --locked` from
  `dependencies/layer_3/cargo.txt`. Belongs to layer 3 (Containerfile
  `toolchain` stage); the registry index and git checkouts are backed
  by BuildKit `--mount=type=cache` and never copied into image layers.
```

- [ ] **Step 14.4: Update the "Source of truth" bullet**

Replace the existing list-managers bullet:

```
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv` only)
```

with:

```
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv`/`cargo`)
```

- [ ] **Step 14.5: Regenerate the AUTO-GEN block**

Run: `make gen-deps`
Expected: `txt_written=0 doc_updated=False` (no cargo entries to render). The doc is left unchanged for now.

- [ ] **Step 14.6: Commit**

```bash
git add docs/specifications/02-installed-programs.md
git commit -m "docs(spec-02): add cargo to allowed managers and manager rules"
```

---

## Task 15: Spec edit — `01-file-structures.md` (tree diagram extension)

**Files:**
- Modify: `docs/specifications/01-file-structures.md`

- [ ] **Step 15.1: Locate the tree diagram**

Run: `grep -n -E '└──|├──' docs/specifications/01-file-structures.md | head -40`
Expected: a directory tree showing `container/`, `dependencies/`, etc.

- [ ] **Step 15.2: Add `layer_4_files/entrypoint.sh` to the tree**

Inside the `container/bind/` subtree, add (preserving existing tree formatting):

```
│   └── layer_4_files/
│       └── entrypoint.sh
```

If a `home_dir/` entry exists in the same subtree, remove it (retired in Task 9).

- [ ] **Step 15.3: Add `layer_3/cargo.txt` to the tree**

Inside the `dependencies/` subtree, after `layer_1/pacman.txt`, add:

```
│   ├── layer_3/
│   │   └── cargo.txt
```

- [ ] **Step 15.4: Add `.dockerignore` at the repo root in the tree (if the tree shows root-level files)**

If the tree begins with the repo root and lists files like `.chezmoiignore`, `Makefile`, etc., add `.dockerignore` in alphabetical position. If the tree skips root-level dotfiles, skip this step.

- [ ] **Step 15.5: Commit**

```bash
git add docs/specifications/01-file-structures.md
git commit -m "docs(spec-01): add layer_4 entrypoint and layer_3 cargo to tree"
```

---

## Self-Review (run after Task 15)

Re-read the spec at `docs/specifications/implementations/2026-06-29-chezmoi-apply-twice-design.md` with fresh eyes and walk through this plan.

- [ ] **Spec coverage check.** For each spec section §3–§8, confirm at least one task implements it:
  - §3.1 Stage table → Task 4 (Layer 1-5), Task 5 (Stage 2), Task 6 (Stage 3), Task 7 (Stage 4), Task 13 (spec)
  - §3.2 Runtime mount strategy → Task 8
  - §3.3 XDG paths → Task 1 (zshenv), Task 4 (mountpoints)
  - §4 Containerfile changes → Tasks 4-7
  - §5 Chezmoi source-tree changes → Task 1 (zshenv/ignore), Task 9 (.dockerignore)
  - §6 Entrypoint → Task 7
  - §7 Makefile changes → Task 8
  - §8 Spec edits → Tasks 11-15
  - §9 Acceptance criterion #10 (cargo.txt generator-owned) → Task 2 (EXPECTED_EMPTY_FILES emits it; pytest test asserts the empty case)
- [ ] **§10 Open Items reconciliation.**
  - Item 1 (cargo list): resolved as "empty initial list" in Task 3.
  - Item 2 (schema bump): resolved as "no bump" in Task 2 (Step 2.3 rationale).
  - Item 3 (.dockerignore policy): minimum set landed in Task 9; broader policy = spec 21 Q2 (Task 13).
  - Item 4 (`make clean` scope): kept as "volumes + image" in Task 8.
  - Item 5 (runtime apply failure UX): kept as "fail-fast" in Task 7.
  - Item 6 (`build_mode` convention): future issue, captured in spec 13 §8 Q3 (Task 11).
  - Item 7 (AUR/paru scheduling): future issue, captured in spec 21 Q1 (Task 13).
- [ ] **Type consistency check.**
  - Volume names: `dotfiles_cargo` / `dotfiles_rustup` / `dotfiles_mise` (Makefile only; entrypoint references mountpoint paths, not names).
  - Stage names: `base`, `build-prepass`, `toolchain`, `runtime` (used consistently across Tasks 4-7 and spec 21 in Task 13).
  - chezmoi data flag: `build_mode` (Tasks 5 and 7 — same key).
  - File paths: `container/bind/layer_4_files/entrypoint.sh` (created in Task 7, referenced in Containerfile in Task 7, referenced in spec 01 in Task 15).
- [ ] If any issue is found, fix inline and continue.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-06-29-chezmoi-apply-twice.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session via `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
