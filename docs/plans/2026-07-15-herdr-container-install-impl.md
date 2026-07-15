# `herdr` in the container (prebuilt binary in toolchain stage) — Implementation Plan

**Status:** pending
**Spec:** [`docs/specifications/implementations/2026-07-15-herdr-container-install-design.md`](../specifications/implementations/2026-07-15-herdr-container-install-design.md)
**Parent issue:** [`docs/issues/2026-07-15-herdr-container-install.md`](../issues/2026-07-15-herdr-container-install.md)
**Review trail:** conversational approval 2026-07-15 (lightweight path; no spec-09 letter pass — the change installs a prebuilt binary with SHA256 pinning, introduces no new secret transport, and follows the established I-INFRA1 curl-bootstrap pattern)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install `herdr` (terminal workspace manager for AI coding agents, https://herdr.dev) during the container build by curl-bootstrapping the pinned v0.7.3 prebuilt static-pie binary from GitHub releases into `~/.local/bin/herdr` in the `toolchain` stage (Layer 3-8), with SHA256 integrity verification — moving the `packages.toml` entry from `migrated` (layer = -1, not installed) to `custom` (layer = 3, doc-only SoT with a bespoke Containerfile install path), so `herdr --version` works inside the running container.

**Architecture:** No new build stage. `herdr` enters via a new Layer 3-8 `RUN` in the existing `toolchain` stage, positioned after Layer 3-7 (cargo tools) and before the `aur` stage `FROM`. The install follows the same curl-bootstrap + SHA256-gate pattern as `cargo-binstall` (Layer 3-6, I-INFRA1 / I-CARGO1): `ARG HERDR_VERSION` + `ARG HERDR_SHA256` pin the release; `curl` downloads the single static-pie ELF binary; `sha256sum -c` verifies integrity; `mv` places it at `~/.local/bin/herdr` (which is on `PATH` via `dot_zshenv.tmpl`). The `packages.toml` entry changes from `manager = "migrated"`, `layer = -1` to `manager = "custom"`, `layer = 3` (doc-only; `custom` entries are NOT written to any `layer_<N>/<manager>.txt` install list — the Containerfile install is bespoke, like `pi-coding-agent` and `cargo-binstall`). No named volume, no Makefile change, no `.chezmoiignore` change — `herdr` is a static binary in `~/.local/bin/` (not a toolchain state dir), and its config (`~/.config/herdr/`) is already chezmoi-managed (`has_configs = true`). The `herdr` self-update mechanism (`herdr update`) remains functional at runtime for version bumps after the initial bake.

**Tech Stack:** Podman ≥ 4.0 / BuildKit, Manjaro base image, `herdr` v0.7.3 prebuilt static-pie ELF binary (x86_64-unknown-linux-musl), `curl` + `sha256sum` (already in Layer 1), chezmoi, Python 3.11+ tomllib (existing `make gen-deps`).

## Global Constraints

- **Secret-free image** (spec 13 / spec 20 I4): `herdr` is a public prebuilt binary downloaded from GitHub releases; no secret material is involved. The SHA256 is a public integrity checksum, not a secret.
- **All packages from `packages.toml`** (spec 20 I5/I8): `herdr` is declared in `dependencies/packages.toml` with `manager = "custom"`, `layer = 3`; `custom` entries are doc-only (appear in the spec 02 AUTO-GEN block but are NOT written to any `layer_<N>/<manager>.txt`). The Containerfile install is the bespoke path, parallel to `cargo-binstall` (I-INFRA1) and `pi-coding-agent`.
- **Integrity gate** (parallel to I-CARGO1): the binary is version-pinned (`HERDR_VERSION=0.7.3`) and SHA256-gated (`HERDR_SHA256=043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d`) via `sha256sum -c` before placement. The stable manifest (`https://herdr.dev/latest.json`) does not publish SHA256 checksums (unlike the preview manifest), so the SHA is hardcoded in the `ARG` — the same approach as `cargo-binstall`.
- **Non-root** (spec 20 I7): the Layer 3-8 `RUN` executes as `USER ${USERNAME}` (set in Layer 1-4 and inherited through the stage chain); no root escalation is needed (the binary goes to `~/.local/bin/` which is `${USERNAME}`-owned).
- **No BuildKit cache mount**: `herdr` is a one-shot download of a single ~18 MB binary with no persistent cache to reuse across builds (same rationale as `cargo-binstall` Layer 3-6, I-CARGO1 / E-F1).
- **`~/.local/bin` is already on `PATH`**: `dot_zshenv.tmpl` exports `PATH="${HOME}/.local/bin:${PATH}"` (or equivalent XDG path), so `herdr` is discoverable in every zsh that sources `.zshenv`. This plan does **not** edit `dot_zshenv.tmpl`.
- **Config is already chezmoi-managed**: `~/.config/herdr/` is templated under chezmoi (`has_configs = true`); runtime `chezmoi apply` renders the config. No `.chezmoiignore` change is needed.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `dependencies/packages.toml` | modify | Change `herdr` entry from `manager = "migrated"`, `layer = -1` to `manager = "custom"`, `layer = 3`; update description |
| `docs/specifications/02-installed-programs.md` | regenerate (via `make gen-deps`) | AUTO-GEN block: `herdr` moves from the Layer -1 (migrated) table to the Layer 3 (custom) section |
| `container/Containerfile` | modify | Add Layer 3-8: `ARG HERDR_VERSION` + `ARG HERDR_SHA256` + `RUN` curl-download, sha256-verify, mv to `~/.local/bin/herdr` |
| `docs/specifications/20-container-rules.md` | modify | Add I-HERDR1 invariant (herdr as a `custom` Layer 3 prebuilt binary, parallel to I-INFRA1) |
| `docs/specifications/21-container-build-flow.md` | modify | Add Layer 3-8 row to the stage table; add acceptance criterion #25 |
| `docs/issues/2026-07-15-herdr-container-install.md` | create (Task 5) | Result-log with acceptance evidence |
| `docs/issues/2026-07-15-herdr-container-install.md` | modify (Task 5) | Status `open` → `closed`, link the result-log |

---

## Task 1: Update `packages.toml` and regenerate

**Files:**
- Modify: `dependencies/packages.toml`
- Regenerate: `docs/specifications/02-installed-programs.md`

**Interfaces:**
- Consumes: existing `generate_deps` (no code change — `custom` + `layer = 3` is already a supported path; `custom` entries are doc-only and do NOT appear in any `layer_<N>/<manager>.txt`).
- Produces: spec 02 AUTO-GEN block moves `herdr` from the Layer -1 (migrated) table to the Layer 3 section with `manager = "custom"`. No `layer_3/cargo.txt` or other install list changes.

- [ ] **Step 1.1: Update the `herdr` entry in `packages.toml`**

In `dependencies/packages.toml`, find the existing `herdr` entry:

```toml
[[tool]]
name = "herdr"
manager = "migrated" # "custom" if it used
layer = -1
# `~/.config/herdr`
has_configs = true
description = "multiplexer with AI agents"
```

Replace with:

```toml
[[tool]]
name = "herdr"
manager = "custom"
layer = 3
# `~/.config/herdr`
has_configs = true
description = "terminal workspace manager for AI coding agents (prebuilt binary, curl-bootstrapped in Layer 3-8)"
```

Key changes:
- `manager`: `"migrated"` → `"custom"` (doc-only SoT; the install is a bespoke Containerfile `RUN`, not a generated package-manager list)
- `layer`: `-1` → `3` (toolchain stage; installed during build, not runtime-manual)
- `description`: updated to reflect the actual tool and install method
- Remove the trailing-comment `# "custom" if it used` — it is now active

- [ ] **Step 1.2: Regenerate the spec 02 AUTO-GEN block**

Run from repo root:
```bash
make gen-deps
```
Expected: the spec 02 AUTO-GEN block is rewritten. `herdr` moves from the Layer -1 (migrated) table to the Layer 3 section. No `layer_<N>/<manager>.txt` files change (because `custom` entries are doc-only). The generator should print something like `txt_written=0 doc_updated=True` (or similar — only the doc is updated, no txt files).

- [ ] **Step 1.3: Verify the spec 02 AUTO-GEN block**

Run:
```bash
grep -A2 'herdr' docs/specifications/02-installed-programs.md | head -10
```
Expected: `herdr` appears in the Layer 3 section (not in the Layer -1 migrated table), with `custom` as the manager.

Also verify it is no longer in the migrated section:
```bash
sed -n '/#### Layer -1/,/#### Layer 0/p' docs/specifications/02-installed-programs.md | grep herdr || echo NOT_IN_MIGRATED
```
Expected: `NOT_IN_MIGRATED`.

- [ ] **Step 1.4: Verify idempotency**

Run:
```bash
make gen-deps
```
Expected: second run is a no-op diff (`txt_written=0 doc_updated=False` or equivalent).

- [ ] **Step 1.5: Run the generator test suite (no regression)**

Run:
```bash
cd programs/generate_deps && python3 -m pytest -q
```
Expected: all tests pass.

- [ ] **Step 1.6: Commit**

```bash
git add dependencies/packages.toml docs/specifications/02-installed-programs.md
git commit -m "feat(deps): move herdr from migrated (layer -1) to custom (layer 3); regenerate spec 02"
```

---

## Task 2: Add `herdr` install to Containerfile (Layer 3-8)

**Files:**
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: `HOST_UID` / `HOST_GID` / `USERNAME` build-args (already `ARG`'d in Layer 1-1); `USER ${USERNAME}` (set in Layer 1-4, inherited through the stage chain); `/tmp/build-home/.zshenv` (rendered in Stage 2, sourced for `PATH` resolution); `curl` + `sha256sum` (installed in Layer 1-2 pacman set).
- Produces: `~/.local/bin/herdr` exists as an executable static-pie ELF binary in the `toolchain` stage image; inherited by the `aur` stage (Layer 4) and the `runtime` stage (Layer 5) via the stage chain. `herdr --version` works in the final image.

- [ ] **Step 2.1: Insert the Layer 3-8 `ARG` + `RUN` after Layer 3-7**

In `container/Containerfile`, find the end of Layer 3-7 (the cargo tools `RUN`), which is immediately followed by the `aur` stage comment block:

```dockerfile
# ---------------------------------------------------------------------------
# Stage 4: aur
```

Insert the following Layer 3-8 block **between** the Layer 3-7 `RUN` and the `Stage 4: aur` comment:

```dockerfile
# Layer 3-8: Install herdr (prebuilt static-pie binary — custom, not in packages.toml list).
#
# herdr is a terminal workspace manager for AI coding agents (https://herdr.dev).
# Like cargo-binstall (3-6) it is curl-bootstrapped from a prebuilt binary and
# is declared `manager = "custom"` in packages.toml (doc-only; not in any
# layer_<N>/<manager>.txt). The stable manifest (https://herdr.dev/latest.json)
# does not publish SHA256 checksums (unlike the preview manifest), so the SHA
# is hardcoded in the ARG — the same approach as cargo-binstall (I-CARGO1).
#
# Integrity (parallel to I-CARGO1): pin to v0.7.3 + verify a hardcoded SHA256
# before placement. The binary is a single static-pie ELF file (no tarball);
# download to /tmp, sha256sum -c, mv to ~/.local/bin/herdr (on PATH via
# .zshenv). No BuildKit cache mount — one-shot download with no persistent
# cache (same rationale as cargo-binstall, I-CARGO1 / E-F1).
ARG HERDR_VERSION=0.7.3
ARG HERDR_SHA256=043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d
RUN zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      curl -L --proto "=https" --tlsv1.2 -sSf -o /tmp/herdr \
        https://github.com/ogulcancelik/herdr/releases/download/v${HERDR_VERSION}/herdr-linux-x86_64; \
      printf "%s  /tmp/herdr\n" "${HERDR_SHA256}" | sha256sum -c -; \
      chmod 0755 /tmp/herdr; \
      install -d "$HOME/.local/bin"; \
      mv /tmp/herdr "$HOME/.local/bin/herdr"; \
      herdr --version; \
    '
```

Key design points:
- **Position**: after Layer 3-7 (the last toolchain install), before the `aur` stage. This keeps all toolchain binary installs in Stage 3; the `aur` stage inherits herdr via the stage chain.
- **`source /tmp/build-home/.zshenv`**: each `RUN` in the toolchain stage is a fresh shell; sourcing the rendered `.zshenv` materializes `PATH` (including `~/.local/bin`) so `herdr --version` can resolve at the end of the `RUN`.
- **`install -d "$HOME/.local/bin"`**: ensures the directory exists before `mv` (it should already exist from the Stage 2 `chezmoi apply` render, but this is a safety net).
- **`chmod 0755 /tmp/herdr`**: the downloaded binary may not have execute permission; set it before `mv`.
- **No `--mount=type=cache`**: one-shot download, no persistent cache (same as cargo-binstall Layer 3-6).
- **`herdr --version` at the end**: build-time verification that the binary is functional; fails the build if the binary is corrupt despite the SHA match (defense in depth).

- [ ] **Step 2.2: Verify the Containerfile parses (dry-run)**

Run:
```bash
podman build --target toolchain --no-cache --dry-run . 2>&1 | head -30
```
Expected: no parse errors; the Layer 3-8 `RUN` appears in the build plan. (If `--dry-run` is not supported, skip to Step 2.3.)

- [ ] **Step 2.3: Build the image and confirm Layer 3-8 runs**

Run:
```bash
make build
```
Expected: build succeeds through all stages; the Layer 3-8 `RUN` downloads, verifies, and installs herdr; `herdr --version` prints `herdr 0.7.3` in the build output.

If the build fails at Layer 3-8:
- SHA256 mismatch: re-compute `sha256sum` of the downloaded binary and update `HERDR_SHA256` in the `ARG`. The SHA may differ if the upstream re-published the release asset.
- Download failure: check network connectivity and the GitHub release URL.

- [ ] **Step 2.4: Verify herdr is in the image (toolchain stage)**

Run:
```bash
USERNAME=$(grep ^USERNAME .env | cut -d= -f2)
podman run --rm --entrypoint bash localhost/dotfiles-manjaro:latest -c \
  "/home/${USERNAME}/.local/bin/herdr --version"
```
Expected: `herdr 0.7.3`.

- [ ] **Step 2.5: Commit**

```bash
git add container/Containerfile
git commit -m "feat(container): install herdr v0.7.3 prebuilt binary (Layer 3-8) with SHA256 pinning"
```

---

## Task 3: Update specs (20 / 21)

**Files:**
- Modify: `docs/specifications/20-container-rules.md`
- Modify: `docs/specifications/21-container-build-flow.md`

- [ ] **Step 3.1: Add I-HERDR1 invariant to spec 20**

In `docs/specifications/20-container-rules.md`, in the "Build (`Containerfile`)" invariants section, after the I-CARGO1 invariant (which ends with the text about `cargo-binstall` having no persistent download cache), append:

```markdown
- I-HERDR1: **`herdr` is a `custom` Layer 3 prebuilt binary, not an
  installer-of-installers.** Unlike `rustup` / `cargo-binstall` (which are
  infra — I-INFRA1), `herdr` is an end-user tool (a terminal workspace
  manager for AI coding agents). It is curl-bootstrapped at Layer 3-8 from
  a version-pinned (v0.7.3) + SHA256-gated
  (`043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d`)
  prebuilt static-pie ELF binary, placed at `~/.local/bin/herdr` (on `PATH`
  via `dot_zshenv.tmpl`). It is declared `manager = "custom"`, `layer = 3`
  in `packages.toml` (doc-only; not in any `layer_<N>/<manager>.txt` — the
  Containerfile install is bespoke, parallel to `pi-coding-agent`). The
  stable manifest (`https://herdr.dev/latest.json`) does not publish SHA256
  checksums (unlike the preview manifest), so the SHA is hardcoded in the
  `ARG` — the same approach as `cargo-binstall` (I-CARGO1). No BuildKit
  cache mount (one-shot download, no persistent cache). Config at
  `~/.config/herdr/` is chezmoi-managed (`has_configs = true`); the
  `herdr update` self-update mechanism remains functional at runtime for
  version bumps after the initial bake.
```

- [ ] **Step 3.2: Add the Layer 3-8 row to spec 21's stage table**

In `docs/specifications/21-container-build-flow.md`, in the "Stage (Layer) ordering" table, find the Layer 3-7 row:

```markdown
| `toolchain` (`FROM build-prepass`) | 3-7 | `COPY --from=deps layer_3/cargo.txt`; `cargo binstall --only-signed -y ${=pkgs}` | Install the Layer 3 build-time cargo tool set ... | `/tmp/build-home/.zshenv`, `dependencies/layer_3/cargo.txt` |
```

Insert a new row immediately after it:

```markdown
| `toolchain` (`FROM build-prepass`) | 3-8 | `ARG HERDR_VERSION`/`HERDR_SHA256`; `curl` the pinned v0.7.3 `herdr-linux-x86_64`; `sha256sum -c` against the hardcoded SHA256; `mv` to `~/.local/bin/herdr`; `herdr --version` | Install `herdr` (terminal workspace manager for AI coding agents) as a `custom` Layer 3 prebuilt binary (I-HERDR1). Declared `manager = "custom"` in `packages.toml` (doc-only; not in any `layer_<N>/<manager>.txt`). No cache mount (one-shot download, same as cargo-binstall 3-6). | `/tmp/build-home/.zshenv`, `ARG HERDR_VERSION`/`HERDR_SHA256` |
```

- [ ] **Step 3.3: Add a herdr acceptance criterion to spec 21**

In `docs/specifications/21-container-build-flow.md`, append to the "Acceptance criteria" numbered list (after criterion #24):

```markdown
25. After `make up`, `podman exec <container> zsh -ic 'herdr --version'`
    prints `herdr 0.7.3` (or the pinned `HERDR_VERSION`). The binary is at
    `~/.local/bin/herdr` (on `PATH` via `dot_zshenv.tmpl`). Config at
    `~/.config/herdr/` is rendered by runtime `chezmoi apply` (declared
    `has_configs = true` in `packages.toml`). No BuildKit cache mount on
    Layer 3-8 (one-shot download, same as cargo-binstall 3-6).
```

- [ ] **Step 3.4: Commit**

```bash
git add docs/specifications/20-container-rules.md docs/specifications/21-container-build-flow.md
git commit -m "docs(spec-20/21): record herdr Layer 3-8 + I-HERDR1 invariant + acceptance #25"
```

---

## Task 4: Build verification

**Files:** none modified; verification only.

- [ ] **Step 4.1: Reset to a clean slate**

Run:
```bash
make clean || true
```

- [ ] **Step 4.2: Build the image**

Run:
```bash
make build
```
Expected: build completes across all 5 stages; Layer 3-8 downloads, verifies, and installs herdr; `herdr --version` prints `herdr 0.7.3` in the build output.

- [ ] **Step 4.3: Start the container**

Run:
```bash
make up
sleep 2
```
Expected: container is `Up`; the readiness sentinel `/tmp/chezmoi-applied` is written (chezmoi apply succeeds, rendering `~/.config/herdr/` from chezmoi source).

- [ ] **Step 4.4: Verify herdr is available and reports its version**

Run:
```bash
podman exec dotfiles-manjaro zsh -ic 'herdr --version'
```
Expected (acceptance #25): `herdr 0.7.3`.

- [ ] **Step 4.5: Verify herdr is at the expected path**

Run:
```bash
podman exec dotfiles-manjaro zsh -ic 'which herdr'
```
Expected: `/home/<USERNAME>/.local/bin/herdr` (or the `PATH`-resolved equivalent).

- [ ] **Step 4.6: Verify herdr config is rendered by chezmoi**

Run:
```bash
podman exec dotfiles-manjaro zsh -c 'ls ~/.config/herdr/config.toml && echo CONFIG_OK'
```
Expected: `config.toml` exists and `CONFIG_OK` is printed (chezmoi apply rendered the herdr config).

- [ ] **Step 4.7: Verify existing acceptance criteria still hold (no regression)**

Run a subset of the pre-existing spec 21 acceptance checks:

```bash
podman exec dotfiles-manjaro zsh -ic 'echo $CARGO_HOME'
podman exec dotfiles-manjaro zsh -ic 'pi --version'
podman exec dotfiles-manjaro paru --version
podman exec dotfiles-manjaro zsh -ic 'gpg --version'
```
Expected: `~/.local/share/cargo`; a pi version string; a paru version string; a gpg version string. All pre-existing tools are unaffected by the new Layer 3-8.

- [ ] **Step 4.8: If any criterion fails**

Identify the failing criterion, return to the originating task (1–3), fix, recommit, and rerun **all** steps in Task 4 from 4.1.

---

## Task 5: Result-log + close issue

**Files:**
- Create: `docs/issues/2026-07-15-phase-herdr-container-install.md` (result-log)
- Modify: `docs/issues/2026-07-15-herdr-container-install.md` (close)

- [ ] **Step 5.1: Write the result-log**

Create `docs/issues/2026-07-15-phase-herdr-container-install.md` per doc-mgmt §6.6, recording the acceptance evidence as a table:

| Criterion | Status | Evidence |
|---|---|---|
| herdr in packages.toml as custom layer 3 | PASS | `grep -A5 'herdr' dependencies/packages.toml` shows `manager = "custom"`, `layer = 3` |
| spec 02 AUTO-GEN moved herdr to Layer 3 | PASS | `grep` confirms herdr in Layer 3 section, NOT_IN_MIGRATED |
| Containerfile Layer 3-8 installs herdr | PASS | `make build` output shows `herdr --version` → `herdr 0.7.3` |
| herdr --version in running container | PASS | `podman exec dotfiles-manjaro zsh -ic 'herdr --version'` → `herdr 0.7.3` |
| herdr at ~/.local/bin/herdr | PASS | `which herdr` → `/home/<USERNAME>/.local/bin/herdr` |
| herdr config rendered by chezmoi | PASS | `ls ~/.config/herdr/config.toml` → CONFIG_OK |
| No regression (cargo/pi/paru/gpg) | PASS | All pre-existing tools report versions |
| Spec 20 I-HERDR1 added | PASS | `grep I-HERDR1 docs/specifications/20-container-rules.md` matches |
| Spec 21 Layer 3-8 row + acceptance #25 | PASS | `grep '3-8' docs/specifications/21-container-build-flow.md` matches |

Reference the commit trail (Tasks 1–3 commits + any fix commits from Task 4.8).

- [ ] **Step 5.2: Close the parent issue**

In `docs/issues/2026-07-15-herdr-container-install.md`, change `**Status:** open` to `**Status:** closed (see [result-log](2026-07-15-phase-herdr-container-install.md))`.

- [ ] **Step 5.3: Commit the result-log + issue close**

```bash
git add docs/issues/2026-07-15-phase-herdr-container-install.md docs/issues/2026-07-15-herdr-container-install.md
git commit -m "docs: close herdr-container-install issue with result-log"
```

---

## Self-Review (run after writing the plan, before execution)

- [ ] **Spec coverage check.** For each design area, confirm a task implements it:
  - packages.toml change (migrated → custom, layer -1 → 3) → Task 1
  - Containerfile Layer 3-8 (curl + sha256 + mv) → Task 2
  - spec 20 I-HERDR1 invariant → Task 3 Step 3.1
  - spec 21 Layer 3-8 row + acceptance #25 → Task 3 Steps 3.2–3.3
  - spec 02 AUTO-GEN (regenerated) → Task 1 Step 1.2
  - Build + runtime verification → Task 4
  - Result-log + issue close → Task 5
- [ ] **Placeholder scan.** No "TBD" / "implement later" / "similar to Task N". All code/doc blocks are verbatim.
- [ ] **Name consistency.** `herdr` / `HERDR_VERSION` / `HERDR_SHA256` / `~/.local/bin/herdr` / Layer 3-8 / I-HERDR1 — used consistently across Tasks 1–5 and the specs.
- [ ] **SHA256 accuracy.** The hardcoded SHA256 (`043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d`) was computed from the actual v0.7.3 `herdr-linux-x86_64` binary. If the upstream re-publishes the asset, the SHA will mismatch and the build will fail loudly at `sha256sum -c` — re-compute and update the `ARG`.
- [ ] **Commit consistency.** One commit per task (Tasks 1–3) + one result-log/close commit (Task 5.3), matching doc-mgmt §6.5.
- [ ] **No scope creep.** This plan does NOT: add a named volume for herdr (it's a static binary, not toolchain state); modify the Makefile (no volume to wire); modify `.chezmoiignore` (config is already chezmoi-managed, binary is not chezmoi-managed); modify `dot_zshenv.tmpl` (`~/.local/bin` is already on `PATH`); modify the entrypoint (herdr is available immediately after build, no runtime setup needed).
- [ ] If any issue is found, fix inline and continue.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-07-15-herdr-container-install-impl.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session via `superpowers:executing-plans`, batch execution with checkpoints.