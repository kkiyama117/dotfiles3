# `paru` (AUR) Install Layer — Design

**Status:** DRAFT
**Date opened:** 2026-06-30
**Issue:** [`docs/issues/2026-06-30-paru-aur-layer.md`](../../issues/2026-06-30-paru-aur-layer.md)
**Author:** kiyama

## §1 Context & success criteria

The container build (see [spec 21](../21-container-build-flow.md)) has
stages `base → build-prepass → toolchain → runtime` and installs from
`pacman` (Layer 1) and `cargo` (Layer 3) but has no AUR path. `paru` is
itself an AUR package, so it must be bootstrapped via `makepkg` before it
can install anything. Layer 1-4 already provisions the non-root
`${USERNAME}` + NOPASSWD sudoers for exactly this purpose, but no stage
consumes it.

- **S1:** AUR packages can be declared in `dependencies/packages.toml`
  with `manager = "paru"`, regenerated into
  `dependencies/layer_4/paru.txt` by `make gen-deps`, and installed in
  the container build with no manual intervention.
- **S2:** `paru` is bootstrapped inside a dedicated build stage as the
  non-root `${USERNAME}`; `makepkg` / `paru` never run as root (spec 20
  I7).
- **S3:** The `paru` / AUR clone+build cache is backed by BuildKit
  `--mount=type=cache`, so cache-miss rebuilds reuse AUR clones / built
  packages instead of re-fetching + rebuilding.
- **S4:** The final image has `paru` on PATH and every package listed in
  `layer_4/paru.txt` installed.
- **S5:** spec 21 Q1 (AUR scheduling + cache) and spec 20 Q2 (paru
  policy) are resolved and point at this design.

## §2 Alternatives considered

- **A1 — Layer 1-6 (sub-layer inside `base`).** Rejected: `build-prepass`
  (Stage 2) is `FROM base` and only does a secret-free chezmoi scratch
  render, so it would inherit the full AUR build bloat for every
  prepass rebuild even though AUR packages are runtime-only. Also
  violates the conceptual role of Layer 1 ("minimum installation only
  for chezmoi apply").
- **A2 — Fold AUR installs into the `toolchain` stage (Layer 3).**
  Rejected: `toolchain` is conceptually "rustup / mise / cargo" (user
  toolchain under XDG paths). AUR packages are system packages installed
  to `/usr`, a different concern. Mixing them obscures the build flow
  and forces `toolchain` to carry AUR build weight it does not need.
- **A3 — New dedicated stage `aur` between `toolchain` and `runtime`
  (chosen).** Keeps each build concern in its own stage (consistent with
  the existing rustup / mise / cargo split), keeps `base` / `prepass` /
  `toolchain` lean, allows a dedicated `--mount=type=cache` for the
  paru/AUR cache, and gives a clean single `FROM aur AS runtime` handoff
  to the final image.
- **A4 — Bootstrap `paru` via a prebuilt binary / static download.**
  Rejected: `paru` does not publish official static binaries; the
  supported install path is the AUR PKGBUILD. Bootstrapping via
  `makepkg -si` from the AUR clone is the canonical method and reuses
  `base-devel` (already in Layer 1).
- **A5 — Declare `paru` in `packages.toml` vs. treat it as build-only
  tooling.** Chose to declare it (with `manager = "paru"`, `layer = 4`)
  so invariant I5 ("all packages originate from `packages.toml`") holds
  and the AUTO-GEN block in spec 02 records it.

## §3 Architecture / Invariants

### Stage chain

```
base (Layer 1) → build-prepass (Layer 2) → toolchain (Layer 3)
                                              ↓
                                  aur (Layer 4) ← NEW
                                              ↓
                                  runtime (Layer 5)   [was Layer 4]
```

- `aur` is `FROM toolchain AS aur`; `runtime` becomes `FROM aur AS
  runtime`.
- `aur` inherits `USER ${USERNAME}` from `toolchain` (which inherits it
  from `base` Layer 1-4 / 1-5). `makepkg` and `paru` therefore run
  non-root; root escalation for `pacman` happens only via the Layer 1-4
  NOPASSWD sudoers entry → spec 20 I7 holds.
- `toolchain` and `aur` are independent in content (cargo = user
  toolchain under `$XDG_DATA_HOME`; AUR = system packages under `/usr`)
  but linearly chained so the final `runtime` image inherits both.

### New invariants

- **I-AUR1:** `paru` is bootstrapped exactly once, in the `aur` stage,
  via `makepkg -si` against the AUR `paru` PKGBUILD clone. No other
  stage runs `makepkg`.
- **I-AUR2:** Every AUR package installed in the image is listed in
  `dependencies/layer_4/paru.txt` (generated from `packages.toml`).
  Ad-hoc `paru -S` / `makepkg -si` for packages not in `packages.toml`
  is forbidden (extends I5 to the `paru` manager).
- **I-AUR3:** The `paru` / AUR clone+build cache
  (`/home/${USERNAME}/.cache/paru`) and the pacman package cache
  (`/var/cache/pacman/pkg`) are backed by `--mount=type=cache` in every
  `aur`-stage `RUN` that fetches or builds. The cache mounts are not
  written to image layers (no bloat).
- **I-AUR4:** The `aur` stage's bootstrap clone (`/tmp/paru-build`) is
  removed before the stage ends (either in the bootstrap `RUN` itself or
  in the runtime scratch-removal step) so it cannot ride into the final
  image.

### Layer renumbering

Inserting `aur` as Layer 4 pushes `runtime` from Layer 4 to Layer 5.
To keep "numeric layer order == build-chain order" (a spec 21
convention), the runtime sub-layer comments (`# Layer 4-1/4-2/4-3` →
`# Layer 5-1/5-2/5-3`) and the bind directory
`container/bind/layer_4_files/` → `container/bind/layer_5_files/` are
renamed in the same change. Cross-references updated: `container/.gitignore`
(`!bind/layer_4_files/entrypoint.sh` → `layer_5_files`), spec 01 tree,
spec 21 stage table + inputs column.

## §4 Scope / staging breakdown

1. **Generator** — add `(4, "paru")` to `EXPECTED_EMPTY_FILES` so
   `layer_4/paru.txt` is always emitted; add a unit test.
2. **SoT** — add a `Layer 4` marker + the seed `paru` `[[tool]]` entry
   to `dependencies/packages.toml`; run `make gen-deps` to emit
   `dependencies/layer_4/paru.txt`.
3. **Containerfile** — add the `aur` stage (bootstrap + bulk install
   with cache mounts); renumber `runtime` to Layer 5 and rename
   `layer_4_files` → `layer_5_files`.
4. **Specs** — update spec 21 (stage table, notes, acceptance
   criteria, resolve Q1), spec 20 (resolve Q2, add I-AUR invariants),
   spec 02 (paru manager rules already present — verify AUTO-GEN block
   gains the Layer 4 table), spec 01 (tree: `layer_4/paru.txt` +
   `layer_5_files/entrypoint.sh`).
5. **Smoke gate** — end-to-end `make build` + `paru --version` in the
   running container.

## §5 `aur` stage detail

```dockerfile
# ---------------------------------------------------------------------------
# Stage 4: aur
#
# Bootstrap paru from the AUR (paru is itself an AUR package and cannot
# be installed via pacman), then install the Layer 4 AUR package set from
# dependencies/layer_4/paru.txt. Runs as non-root ${USERNAME}; root
# escalation for pacman happens only via the Layer 1-4 NOPASSWD sudoers.
# BuildKit cache mounts keep the AUR clone/build cache and the pacman
# package cache across rebuilds without bloating image layers.
# ---------------------------------------------------------------------------
FROM toolchain AS aur

# Layer 4-1: bootstrap paru via makepkg (non-root).
RUN --mount=type=cache,target=/var/cache/pacman/pkg \
    --mount=type=cache,target=/home/${USERNAME}/.cache/paru,uid=${HOST_UID},gid=${HOST_GID} \
    set -e; \
    sudo pacman -Sy --noconfirm; \
    git clone https://aur.archlinux.org/paru.git /tmp/paru-build; \
    cd /tmp/paru-build && makepkg -si --noconfirm --needed; \
    rm -rf /tmp/paru-build

# Layer 4-2: install the AUR package set from the generated list.
COPY --from=deps layer_4/paru.txt /tmp/paru_deps.txt
RUN --mount=type=cache,target=/var/cache/pacman/pkg \
    --mount=type=cache,target=/home/${USERNAME}/.cache/paru,uid=${HOST_UID},gid=${HOST_GID} \
    set -e; \
    pkgs=$(sed 's/#.*//' /tmp/paru_deps.txt | xargs); \
    if [ -n "$pkgs" ]; then \
      paru -S --noconfirm --needed $pkgs; \
    else \
      echo "aur: paru install list is empty -- skipping"; \
    fi
```

Notes:

- `sudo pacman -Sy` refreshes the sync DB so `makepkg -si`'s dependency
  resolution via pacman succeeds; it does **not** `-u` (no full upgrade)
  — Layer 1-2 already ran `pacman -Syu`.
- `makepkg -si --noconfirm --needed` installs `paru` + its repo deps
  (all already satisfied by `base-devel` / Layer 1).
- The bulk install reads the whole `paru.txt`, including the `paru` line
  itself; `paru -S --needed paru` is a no-op once paru is bootstrapped,
  which exercises the install-list path without rebuilding paru.
- `/tmp/paru-build` is removed at the end of Layer 4-1 (I-AUR4) so it
  never enters the layer.

## §6 `packages.toml` seed entry

```toml
# Layer 4: paru-installed tools (AUR); Containerfile `aur` stage.
# paru itself is bootstrapped via makepkg in the `aur` stage, then used
# to install the rest of this list. Add `[[tool]]` entries with
# `manager = "paru"` and `layer = 4`. Run `make gen-deps` to regenerate
# `dependencies/layer_4/paru.txt`.
[[tool]]
name = "paru"
manager = "paru"
layer = 4
has_configs = false
description = "AUR helper; bootstrapped via makepkg, then installs the rest of layer 4"

[[tool]]
name = "neovim-git"
manager = "paru"
layer = 4
has_configs = false
description = "neovim built from upstream git master (AUR); first concrete AUR package"
```

Initial list = `{ paru, neovim-git }`. `paru` is the bootstrap tool
(declared so I5 holds); `neovim-git` is the first concrete AUR package
and exercises the full clone/build/install path. `neovim-git` compiles
neovim from source, so its `aur`-stage build is slow (minutes); the
`~/.cache/paru` cache mount makes repeat builds reuse the clone. Its
makedepends (cmake/ninja/gettext/...) are pulled in automatically by
`makepkg -si` as transient build deps — not declared in `packages.toml`
because they are dependencies, not packages we explicitly install.

## §7 Generator change

In `programs/generate_deps/main.py`:

```python
EXPECTED_EMPTY_FILES: tuple[tuple[int, str], ...] = ((3, "cargo"), (4, "paru"))
```

Rationale: the Containerfile `COPY --from=deps layer_4/paru.txt` is
unconditional, so the file must exist even with zero entries. Keeping it
generator-owned satisfies spec 02 §9 criterion #10 (never hand-edited).
No schema bump (additive).

## §8 Spec edits

- **spec 21** — stage table: add `aur` (`FROM toolchain`) row at Layer 4
  with sub-layers 4-1 (bootstrap) / 4-2 (bulk install); change
  `runtime` row to Layer 5 with sub-layers 5-1/5-2/5-3 and inputs
  `container/bind/layer_5_files/entrypoint.sh`. Notes: add an `aur`
  bullet. Acceptance criteria: add items for `paru --version`, AUR
  cache mount, non-root bootstrap. Open questions: mark Q1 Resolved
  with a pointer here.
- **spec 20** — Open questions: mark Q2 Resolved. Build invariants: add
  I-AUR1..I-AUR4 (or fold into prose under a new "AUR / paru" note).
- **spec 02** — `paru` is already in the allowed-managers contract and
  manager-rules bullet; no contract change. The AUTO-GEN block
  regenerates (via `make gen-deps`) to add a "Layer 4 — install list"
  table once the `paru` entry lands.
- **spec 01** — tree: replace `container/bind/layer_4_files/` with
  `layer_5_files/entrypoint.sh`; add `dependencies/layer_4/paru.txt`.

## §9 Acceptance / verification

- `make gen-deps` is idempotent and emits `dependencies/layer_4/paru.txt`
  with the `paru` line (and the AUTO-GEN Layer 4 table in spec 02).
- `make build` succeeds end-to-end across the 5 stages.
- In the running container (`make up` then `podman exec`):
  `paru --version` prints a version string as `${USERNAME}`.
- `podman build --target aur` succeeds in isolation and the resulting
  image has `paru` on PATH.
- Re-running `make build` after a no-op change reuses the
  `~/.cache/paru` cache mount (second build's `aur` step is faster / a
  cache hit for the clone).
- spec 21 Q1 and spec 20 Q2 read "Resolved" with a pointer to this
  design.

## §10 Open questions

- **Q1:** Should the `aur` stage also run `paru -Syu` (full system
  upgrade) instead of just `pacman -Sy`? Current design: no — Layer 1-2
  already ran `pacman -Syu`, and a mid-build full upgrade risks
  destabilizing the toolchain stage's pinned binaries. Deferred to a
  follow-up if drift becomes a problem.
- **Q2:** Should concrete AUR packages (the user's intended set) be
  added in this change or a follow-up? Current design: follow-up, to
  land infrastructure first (mirrors the cargo precedent). The user is
  asked at plan handoff whether to seed a concrete list now.
- **Q3:** GPG key import for AUR packages that sign sources. `paru`
  handles this interactively by default; with `--noconfirm` it may fail
  on signed sources whose key is not in the keyring. Deferred until the
  first such package is added to `paru.txt`.