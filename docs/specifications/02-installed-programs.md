# 02 — Installed Programs

> Spec status: **active**. This is the single SoT spec for the tool
> inventory — both the **contract** for how tools are declared and the
> **list** itself (rendered into the AUTO-GEN block below by
> `programs/generate_deps/main.py` via `make gen-deps`).

## Source of truth

- Hand-edited SoT for tool definitions: [`../../dependencies/packages.toml`](../../dependencies/packages.toml)
- Generated artifacts (all derived from `packages.toml`):
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv` only)
  - The AUTO-GEN block at the end of this document

`packages.toml` schema is documented at the top of that file. New tool
entries belong there only — never edit the AUTO-GEN block by hand.

## Contract

| Field | Required | Allowed values |
|---|---|---|
| `name`        | yes | string |
| `manager`     | yes | `pacman` / `paru` / `nix` / `mise` / `uv` |
| `layer`       | yes | integer ≥ 1 (Containerfile layer index) |
| `has_configs` | yes | bool — true if config is templated under chezmoi |
| `description` | no  | string — used in the AUTO-GEN block |

## manager rules

- `pacman`: use to install packages to build container.
- `paru`: install all packages from AUR package, that isn't included in `pacman` installed list.
- `mise`: To install programming languages and tools excepts `Rust`.
- `nix`: Now we use `nix` only for apply `flake.nix`
- `uv`: installed via `uv` (Python package manager)

## Regeneration

Run `make gen-deps` (planned; tracked in [`08-automations.md`](08-automations.md))
to rewrite the AUTO-GEN block from `packages.toml`.

<!-- BEGIN AUTO-GEN: installed-programs -->
Rendered from [`../../dependencies/packages.toml`](../../dependencies/packages.toml) via `make gen-deps` (`programs/generate_deps/main.py`). Do not edit by hand.

#### Layer 0 — already in the base image

| name | manager | configs | description |
|---|---|---|---|
| `pacman` | pacman | yes |  |

#### Layer 1 — install list

| name | manager | configs | description |
|---|---|---|---|
| `base-devel` | pacman | no | base meta-package: gcc, make, binutils, etc. |
| `bitwarden-cli` | pacman | no | Bitwarden CLI (`bw`); secret backend for chezmoi templates |
| `chezmoi` | pacman | no | dotfiles manager |
| `curl` | pacman | no |  |
| `git` | pacman | no |  |
| `openssh` | pacman | no |  |
| `sudo` | pacman | no |  |
| `zsh` | pacman | no | user's login shell |
<!-- END AUTO-GEN: installed-programs -->
