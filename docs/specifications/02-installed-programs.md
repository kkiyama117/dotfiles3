# 02 — Installed Programs

> Spec status: **active**. This is the single SoT spec for the tool
> inventory — both the **contract** for how tools are declared and the
> **list** itself (rendered into the AUTO-GEN block below by
> `programs/generate_deps/main.py` via `make gen-deps`).

## Source of truth

- Hand-edited SoT for package-list and doc-only tool definitions: [`../../dependencies/packages.toml`](../../dependencies/packages.toml)
- Hand-edited SoT for mise language defaults: [`../../dot_config/mise/config.toml`](../../dot_config/mise/config.toml)
- Generated artifacts derived from `packages.toml`:
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv`/`cargo`)
  - The AUTO-GEN block at the end of this document

`packages.toml` schema is documented at the top of that file. New package-list
entries belong there only — never edit the AUTO-GEN block by hand. New global
mise language defaults belong in `dot_config/mise/config.toml`, not in
`packages.toml`.

## Contract

| Field | Required | Allowed values |
|---|---|---|
| `name`        | yes | string |
| `manager`     | yes | `pacman` / `paru` / `nix` / `uv` / `cargo` / `custom` |
| `layer`       | yes | integer ≥ 0; 1-5 = Containerfile stage index; 0 = already in the base image; 6 = runtime-manual reference (not build-installed, see [`24-rust-packages-rule.md`](24-rust-packages-rule.md)) |
| `has_configs` | yes | bool — true if config is templated under chezmoi |
| `description` | no  | string — used in the AUTO-GEN block |

## manager rules

- `pacman`: use to install packages to build container.
- `paru`: install all packages from AUR package, that isn't included in `pacman` installed list.
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
| `clang` | pacman | no |  |
| `compiler-rt` | pacman | no | Compiler runtime libraries for clang |
| `curl` | pacman | no |  |
| `git` | pacman | yes |  |
| `git-delta` | pacman | no | git-delta — syntax-highlighting pager for git diff/blame/log (core.pager/pager.* in ~/.config/git/config) |
| `gnupg` | pacman | yes | GnuPG (`gpg` / `gpg-agent`); honors GNUPGHOME from .zshenv |
| `mise` | pacman | yes | mise — language version manager |
| `mold` | pacman | no | Fast linker, mainly to compile Rust |
| `openssh` | pacman | yes |  |
| `pinentry` | pacman | no | pinentry frontends (tty/curses) + default wrapper; hard-deps libsecret (library only, no daemon) |
| `sheldon` | pacman | yes | shell plugin/source manager |
| `sudo` | pacman | no |  |
| `zsh` | pacman | yes | user's login shell |

#### Layer 3 — install list

| name | manager | configs | description |
|---|---|---|---|
| `cargo-edit` | cargo | no | provides cargo-add / cargo-rm / cargo-set-version / cargo-upgrade binaries (no cargo-edit binary by upstream design) |
| `cargo-outdated` | cargo | no | Detect outdated Rust crate dependencies |
| `topgrade` | cargo | no | multi-package-manager updater; build-time cargo tool (signed prebuilt via cargo-binstall --only-signed) |
| `cargo-binstall` | custom | no | Install binaries |

#### Layer 4 — install list

| name | manager | configs | description |
|---|---|---|---|
| `paru` | custom | no | AUR helper; bootstrapped via makepkg in the aur stage (custom install path, not in paru.txt) |
| `rsync` | pacman | no |  |
| `bat` | paru | no | Alternative `cat` |
| `lazygit` | paru | yes | TUI for git |
| `neovim-git` | paru | no | neovim built from upstream git master (AUR); first concrete AUR package |
| `pastel` | paru | no | color utility |
| `pueue` | paru | no | task queue daemon |
| `starship` | paru | yes | zsh prompt theme manager |
| `tmux` | paru | no | tmux multiplexer |
| `wired` | paru | no | notification daemon |

#### Layer 6 — runtime-manual (not build-installed)

| name | manager | configs | description |
|---|---|---|---|
| `cargo-audit` | cargo | no | Audit your dependencies for crates with security vulnerabilities reported to the RustSec Advisory Database. |
| `cargo-dist` | cargo | no | Rust version `goreleaser` |
| `cargo-expand` | cargo | no | runtime-manual cargo tool; pretty-print macro expansion |
| `cargo-make` | cargo | no | Rust task runner and build tool. |
| `cargo-zigbuild` | cargo | no | runtime-manual cargo tool; cross-compile via zig toolchain |
| `maturin` | cargo | no | runtime-manual cargo tool; build & publish Rust-Python extensions |
| `tre` | cargo | no | A modern alternative to the tree command |
<!-- END AUTO-GEN: installed-programs -->
