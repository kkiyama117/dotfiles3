# Add a `paru` (AUR) install layer to the container build

**Date:** 2026-06-30
**Status:** open
**Related:** [design](../specifications/implementations/2026-06-30-paru-aur-layer-design.md), [plan](../plans/2026-06-30-paru-aur-layer-impl.md), [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [spec 02](../specifications/02-installed-programs.md)

## Context

The container image currently installs packages only from the official
repos via `pacman` (Layer 1) and from crates.io via `cargo` (Layer 3).
There is no mechanism to install **AUR** packages. spec 21 carries an
explicit Open Question (Q1) about AUR / `paru` build scheduling and
cache mounts, and spec 20 carries Q2 about the `paru` / AUR policy inside
the non-root user namespace. The infrastructure to resolve them is
missing:

- `paru` itself is an AUR package, so it must be bootstrapped via
  `makepkg` (non-root) before it can install anything else.
- `dependencies/packages.toml` already allows `manager = "paru"` and the
  generator (`programs/generate_deps/main.py`) already lists `paru` in
  `LIST_MANAGERS`, but no `layer_N/paru.txt` is emitted or consumed.
- Layer 1-4 already provisions the non-root `${USERNAME}` + NOPASSWD
  sudoers specifically so `paru` / `makepkg` can run non-interactively,
  but no later stage actually uses it.

## Problem

We need a dedicated, spec-blessed place to install AUR packages in the
container build, with (a) a bootstrap path for `paru` itself, (b) a
generated install list fed from `dependencies/packages.toml` (invariant
I5/I8), and (c) a BuildKit `--mount=type=cache` for the `paru` / AUR
clone+build cache (resolving spec 21 Q1 (a) and (b)).

Putting it in Layer 1 (`base` stage, e.g. as a new sub-layer 1-6) is
wrong: `build-prepass` (Stage 2) is `FROM base` and only does a
secret-free chezmoi scratch render, so it would inherit all AUR build
bloat unnecessarily.

## Acceptance criteria

1. A new container stage `aur` exists, positioned between `toolchain`
   and `runtime` in the build chain (`base → build-prepass → toolchain →
   aur → runtime`), and is documented in spec 21's stage table.
2. `paru` is bootstrapped inside `aur` via `makepkg -si` as the non-root
   `${USERNAME}` (I7 holds); NOPASSWD sudoers from Layer 1-4 is the only
   root-escalation path.
3. AUR packages are installed from a generated
   `dependencies/layer_4/paru.txt` via `paru -S --noconfirm --needed`,
   sourced from `dependencies/packages.toml` (I5/I8 hold).
4. `dependencies/layer_4/paru.txt` is generator-owned and emitted even
   when empty (added to `EXPECTED_EMPTY_FILES`), so the unconditional
   `COPY --from=deps layer_4/paru.txt` never breaks the build.
5. The `paru` / AUR clone+build cache (`~/.cache/paru`) and the pacman
   package cache are backed by `--mount=type=cache` (resolves spec 21 Q1
   and spec 20 Q2).
6. The final image contains `paru` on PATH (`paru --version` succeeds as
   `${USERNAME}`).
7. spec 21 Q1 and spec 20 Q2 are marked Resolved with a pointer to the
   `aur` stage.
8. The runtime stage is renumbered Layer 4 → Layer 5 (and
   `container/bind/layer_4_files/` → `layer_5_files/`) so numeric layer
   order stays equal to build-chain order; all cross-references (spec 01
   tree, spec 21 inputs, `container/.gitignore`) are updated in the same
   change.

## Notes

- Initial `paru.txt` content = `{ paru, neovim-git }` (infrastructure
  bootstrap + one concrete AUR package to exercise the full clone/build
  path). `paru` is the bootstrap tool (declared so I5 holds);
  `neovim-git` compiles neovim from upstream git master, so the `aur`
  stage build is slow (minutes) — the `~/.cache/paru` cache mount makes
  repeat builds reuse the clone. Additional AUR packages are follow-up
  commits.
- No schema bump in `packages.toml` (additive: `paru` manager and
  layer-4 entries are already allowed by the existing schema).
- This change is secret-free (I4 unaffected): the `aur` stage installs
  only system packages, never consults Bitwarden.