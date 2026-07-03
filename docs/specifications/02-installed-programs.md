# 02 — Installed Programs

> Spec status: **active**. This is the single SoT spec for the tool
> inventory — both the **contract** for how tools are declared and the
> **list** itself (rendered into the AUTO-GEN block below by
> `programs/generate_deps/main.py` via `make gen-deps`).

## Source of truth

- Hand-edited SoT for tool definitions: [`../../dependencies/packages.toml`](../../dependencies/packages.toml)
- Generated artifacts (all derived from `packages.toml`):
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv`/`cargo`/`mise`)
  - The AUTO-GEN block at the end of this document

`packages.toml` schema is documented at the top of that file. New tool
entries belong there only — never edit the AUTO-GEN block by hand.

## Contract

| Field | Required | Allowed values |
|---|---|---|
| `name`        | yes | string |
| `manager`     | yes | `pacman` / `paru` / `nix` / `mise` / `uv` / `cargo` / `custom` |
| `layer`       | yes | integer ≥ 0; 1-5 = Containerfile stage index; 0 = already in the base image; 6 = runtime-manual reference (not build-installed, see [`24-rust-packages-rule.md`](24-rust-packages-rule.md)) |
| `has_configs` | yes | bool — true if config is templated under chezmoi |
| `description` | no  | string — used in the AUTO-GEN block |

## manager rules

- `pacman`: use to install packages to build container.
- `paru`: install all packages from AUR package, that isn't included in `pacman` installed list.
- `mise`: list-based manager for programming languages and tools except `Rust`. Emits `dependencies/layer_<N>/mise.txt` (one `<name>@latest` line per tool) and is installed in the `toolchain` stage (Layer 3-4). Bare `mise install <tool>` reads a `mise.toml` (not latest), so the generator appends `@latest`.
- `nix`: Now we use `nix` only for apply `flake.nix`
- `uv`: installed via `uv` (Python package manager)
- `cargo`: build-time cargo tools (`layer = 3`) are installed via
  `cargo binstall --only-signed -y` from `dependencies/layer_3/cargo.txt`
  in the `toolchain` stage (Layer 3-6); per spec 24 they MUST ship a
  signed prebuilt. `layer = 6` cargo tools are runtime-manual
  (declared for SoT, NOT build-installed; `layer_6/cargo.txt` is a
  reference list the Containerfile never reads). See
  [`24-rust-packages-rule.md`](24-rust-packages-rule.md). (The old
  `cargo install --locked` source-compile path + registry/git cache
  mounts are retired for the binstall path; `--mount=type=cache` on
  `$CARGO_HOME/{registry,git}` remains only on Layers 4-1/4-2 for
  `paru`/Rust AUR builds.)
- `custom`: doc-only. Declared in `packages.toml` (so it appears in the
  AUTO-GEN block below and satisfies I5) but NOT written to any
  `layer_<N>/<manager>.txt` install list. Use for packages with a
  bespoke install path in the Containerfile that cannot go through a
  generated list — e.g. `paru`, which is bootstrapped via `makepkg` and
  therefore cannot also be a `paru -S` target.

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
| `chezmoi` | pacman | yes | dotfiles manager |
| `curl` | pacman | no |  |
| `git` | pacman | yes |  |
| `git-delta` | pacman | no | git-delta — syntax-highlighting pager for git diff/blame/log (core.pager/pager.* in ~/.config/git/config) |
| `gnupg` | pacman | yes | GnuPG (`gpg` / `gpg-agent`); honors GNUPGHOME from .zshenv |
| `openssh` | pacman | yes |  |
| `pinentry` | pacman | no | pinentry frontends (tty/curses) + default wrapper; hard-deps libsecret (library only, no daemon) |
| `rsync` | pacman | no |  |
| `sheldon` | pacman | no | shell plugin/source manager |
| `sudo` | pacman | no |  |
| `zsh` | pacman | yes | user's login shell |

#### Layer 3 — install list

| name | manager | configs | description |
|---|---|---|---|
| `topgrade` | cargo | no | multi-package-manager updater; build-time cargo tool (signed prebuilt via cargo-binstall --only-signed) |
| `deno` | mise | no | Deno runtime (mise-managed, latest) |
| `go` | mise | no | Go programming language (mise-managed, latest) |
| `python` | mise | no | CPython (mise-managed, latest) |

#### Layer 4 — install list

| name | manager | configs | description |
|---|---|---|---|
| `paru` | custom | no | AUR helper; bootstrapped via makepkg in the aur stage (custom install path, not in paru.txt) |
| `neovim-git` | paru | no | neovim built from upstream git master (AUR); first concrete AUR package |
| `pueue` | paru | no | task queue daemon |
| `starship` | paru | no | zsh prompt theme manager |
| `tmux` | paru | no | tmux multiplexer |
| `wired` | paru | no | notification daemon |

#### Layer 6 — runtime-manual (not build-installed)

| name | manager | configs | description |
|---|---|---|---|
| `cargo-edit` | cargo | no | runtime-manual cargo tool; cargo-add/rm/set-version/upgrade |
| `cargo-expand` | cargo | no | runtime-manual cargo tool; pretty-print macro expansion |
| `cargo-outdated` | cargo | no | runtime-manual cargo tool; detect outdated crate deps |
| `cargo-zigbuild` | cargo | no | runtime-manual cargo tool; cross-compile via zig toolchain |
| `maturin` | cargo | no | runtime-manual cargo tool; build & publish Rust-Python extensions |
<!-- END AUTO-GEN: installed-programs -->
