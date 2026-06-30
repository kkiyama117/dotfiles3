# `paru` (AUR) Install Layer — Design

**Status:** Approved (implemented & verified; see [result-log](../../issues/2026-06-30-phase-paru-aur-layer.md))
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
  tooling.** Chose to declare it, but with a **new `manager = "custom"`
  (doc-only)** enum rather than `manager = "paru"`. Rationale: `paru`
  must appear in `packages.toml` so invariant I5 ("all packages
  originate from `packages.toml`") holds and the spec 02 AUTO-GEN block
  records it, BUT it must NOT be a `paru -S` target — re-submitting an
  already-bootstrapped AUR helper as a `paru -S` target breaks paru's
  dependency resolver (observed during implementation). The `custom`
  manager (like `mise`) is rendered in the doc block but excluded from
  every `layer_<N>/<manager>.txt` install list, so the `aur`-stage
  bootstrap (`makepkg -si`) is its sole install path. This drove a
  generator extension (§7).

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
  is forbidden (extends I5 to the `paru` manager). `paru` itself is
  declared `manager = "custom"` (doc-only): it appears in the spec 02
  AUTO-GEN block but is NOT in `paru.txt`, so its sole install path is
  the `aur`-stage `makepkg -si` bootstrap (re-submitting it as a
  `paru -S` target breaks paru's resolver).
- **I-AUR3:** The `paru` / AUR clone+build cache
  (`/home/${USERNAME}/.cache/paru`) and the pacman package cache
  (`/var/cache/pacman/pkg`) are backed by `--mount=type=cache` in every
  `aur`-stage `RUN` that fetches or builds. The cargo registry/git
  caches are also mounted, because `paru` (and any Rust AUR package)
  needs `$CARGO_HOME` writable to fetch crates and the toolchain stage
  re-roots `/home/${USERNAME}` to root (the user cannot create the
  default `~/.cargo`). The cache mounts are not written to image layers
  (no bloat).
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
   `layer_4/paru.txt` is always emitted; add a unit test. Also add a
   **`custom` doc-only manager** (like `mise`) so packages with a
   bespoke install path can be declared in `packages.toml` (I5) without
   being written to any install list. Add a unit test for `custom`.
2. **SoT** — add a `Layer 4` marker + the seed entries to
   `dependencies/packages.toml`: `paru` with `manager = "custom"`
   (doc-only) and `neovim-git` with `manager = "paru"`; run
   `make gen-deps` to emit `dependencies/layer_4/paru.txt` (neovim-git
   only).
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
# BuildKit cache mounts keep the AUR clone/build cache, the pacman package
# cache, and the cargo registry/git caches across rebuilds without
# bloating image layers.
# ---------------------------------------------------------------------------
FROM toolchain AS aur

# Layer 4-1: bootstrap paru via makepkg (non-root).
RUN --mount=type=cache,target=/var/cache/pacman/pkg \
    --mount=type=cache,target=/home/${USERNAME}/.cache/paru,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/registry,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/git,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      sudo pacman -Sy --noconfirm; \
      git clone https://aur.archlinux.org/paru.git /tmp/paru-build; \
      cd /tmp/paru-build && makepkg -si --noconfirm --needed; \
      rm -rf /tmp/paru-build; \
    '

# Layer 4-2: install the AUR package set from the generated list.
COPY --from=deps layer_4/paru.txt /tmp/paru_deps.txt
RUN --mount=type=cache,target=/var/cache/pacman/pkg \
    --mount=type=cache,target=/home/${USERNAME}/.cache/paru,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/registry,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/git,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/paru_deps.txt | xargs); \
      if [ -n "$pkgs" ]; then \
        paru -S --noconfirm --needed $pkgs; \
      else \
        echo "aur: paru install list is empty -- skipping"; \
      fi; \
    '
```

Notes:

- `sudo pacman -Sy` refreshes the sync DB so `makepkg -si`'s dependency
  resolution via pacman succeeds; it does **not** `-u` (no full upgrade)
  — Layer 1-2 already ran `pacman -Syu`.
- Both RUNs `source /tmp/build-home/.zshenv` (the build-prepass scratch
  render, still present in the `aur` image — deleted only in Stage 5) so
  `CARGO_HOME` / `RUSTUP_HOME` resolve to the XDG paths pre-created with
  user ownership in Layer 1-5. This is required: the toolchain stage's
  cache mounts re-root `/home/${USERNAME}` to root, so the user cannot
  create the default `~/.cargo`; pointing cargo at the writable XDG
  `~/.local/share/cargo` (via the sourced `.zshenv`) is what lets
  `paru`'s Rust build fetch crates.
- `makepkg -si --noconfirm --needed` installs `paru` + its repo deps.
  The cargo registry/git cache mounts are mounted because `paru` is a
  Rust package; they also serve any future Rust AUR package in Layer 4.
- The bulk install reads `paru.txt`, which contains **only**
  `manager = "paru"` entries (currently `neovim-git`). `paru` is
  `manager = "custom"` (doc-only) and is therefore NOT in `paru.txt`, so
  the bootstrap above is its sole install path and the bulk call never
  re-submits it as a `paru -S` target (which would break paru's
  resolver — observed during implementation).
- `/tmp/paru-build` is removed at the end of Layer 4-1 (I-AUR4) so it
  never enters the layer.

## §6 `packages.toml` seed entries

```toml
# Layer 4: paru-installed tools (AUR); Containerfile `aur` stage.
# paru itself is bootstrapped via makepkg in the `aur` stage, so it is
# declared here with `manager = "custom"` (doc-only: it appears in the
# spec 02 AUTO-GEN block and satisfies I5, but is NOT written to
# `layer_4/paru.txt` -- re-submitting an already-bootstrapped AUR helper
# as a `paru -S` target breaks paru's resolver). Every other AUR package
# uses `manager = "paru"` and `layer = 4`; run `make gen-deps` to
# regenerate `dependencies/layer_4/paru.txt`.

[[tool]]
name = "paru"
manager = "custom"
layer = 4
has_configs = false
description = "AUR helper; bootstrapped via makepkg in the aur stage (custom install path, not in paru.txt)"

[[tool]]
name = "neovim-git"
manager = "paru"
layer = 4
has_configs = false
description = "neovim built from upstream git master (AUR); first concrete AUR package"
```

`paru.txt` (generated) = `{ neovim-git }`. `paru` (custom) appears only
in the doc block. `neovim-git` is the first concrete AUR package and
exercises the full clone/build/install path. `neovim-git` compiles
neovim from source, so its `aur`-stage build is slow (minutes); the
`~/.cache/paru` cache mount makes repeat builds reuse the clone. Its
makedepends (cmake/ninja/gettext/...) are pulled in automatically by
`makepkg` as transient build deps — not declared in `packages.toml`
because they are dependencies, not packages we explicitly install.

## §7 Generator change

In `programs/generate_deps/main.py`:

```python
LIST_MANAGERS = ("pacman", "paru", "nix", "uv", "cargo")
DOC_ONLY_MANAGERS = ("mise", "custom")
ALL_MANAGERS = LIST_MANAGERS + DOC_ONLY_MANAGERS

EXPECTED_EMPTY_FILES: tuple[tuple[int, str], ...] = ((3, "cargo"), (4, "paru"))
```

Rationale:
- `(4, "paru")` in `EXPECTED_EMPTY_FILES`: the Containerfile
  `COPY --from=deps layer_4/paru.txt` is unconditional, so the file must
  exist even with zero `paru`-manager entries. Generator-owned → spec 02
  §9 criterion #10 (never hand-edited).
- `"custom"` added to `DOC_ONLY_MANAGERS` (like `mise`): a `custom`
  entry is rendered in the AUTO-GEN doc block (so I5 holds and the
  package is traceable) but produces NO `layer_<N>/custom.txt` and is
  NOT merged into any other manager's list. This is the mechanism that
  lets `paru` be declared in `packages.toml` without becoming a
  `paru -S` target.

No schema bump (both changes are additive; existing entries unaffected).

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
- **spec 02** — add `custom` to the allowed-managers contract and a
  `custom` manager-rules bullet (doc-only, bespoke install path). `paru`
  was already in the contract / manager-rules. The AUTO-GEN block
  regenerates (via `make gen-deps`) to add a "Layer 4 — install list"
  table showing both `paru` (custom) and `neovim-git` (paru).
- **spec 01** — tree: replace `container/bind/layer_4_files/` with
  `layer_5_files/entrypoint.sh`; add `dependencies/layer_4/paru.txt`.

## §9 Acceptance / verification

- `make gen-deps` is idempotent and emits `dependencies/layer_4/paru.txt`
  containing only the `paru`-manager entries (currently `neovim-git`);
  the AUTO-GEN Layer 4 table in spec 02 shows `paru` (custom) +
  `neovim-git` (paru).
- `make build` succeeds end-to-end across the 5 stages.
- In the running container (`make up` then `podman exec`):
  `paru --version` and `nvim --version` print version strings as
  `${USERNAME}`.
- `podman build --target aur` succeeds in isolation and the resulting
  image has `paru` and `nvim` on PATH.
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
- **Q2:** Resolved. `neovim-git` was added in this change (the user
  confirmed at plan handoff) as the first concrete AUR package, landing
  alongside the infrastructure. Additional AUR packages are follow-up
  commits to `packages.toml` with `manager = "paru"`, `layer = 4`.
- **Q3:** GPG key import for AUR packages that sign sources. `paru`
  handles this interactively by default; with `--noconfirm` it may fail
  on signed sources whose key is not in the keyring. Deferred until the
  first such package is added to `paru.txt`.