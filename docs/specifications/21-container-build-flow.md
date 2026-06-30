# 21 — Container build flow

> Spec status: **active**. Normative spec for the Containerfile stage / layer
> ordering. The implementation lives in
> [`../../container/Containerfile`](../../container/Containerfile). 

## Stage (Layer) ordering

The Containerfile is a multi-stage build. Each `FROM ... AS <stage>` is a
stage; within a stage, numbered **sub-layers** (`Layer N-M`) group related
`RUN` / `ARG` / `USER` directives. The table below reflects the file as of
2026-06-30.

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
| `aur` (`FROM toolchain`) | 4-1 | `git clone` paru PKGBUILD + `makepkg -si` (sources `/tmp/build-home/.zshenv`; cache mounts on `~/.cache/paru` + `/var/cache/pacman/pkg` + `$CARGO_HOME/{registry,git}`) | Bootstrap `paru` from the AUR as non-root `${USERNAME}`. | AUR `paru` PKGBUILD, Layer 1-4 sudoers |
| `aur` (`FROM toolchain`) | 4-2 | `paru -S --noconfirm --needed` | Install the Layer 4 AUR package set from the generated list (`manager = "paru"` entries only). | `dependencies/layer_4/paru.txt` |
| `runtime` (`FROM aur`) | 5-1 | `rm -rf` scratch; `chown` home; `install -d /run/user/$UID` | Strip Stage 2/3/4 scratch artifacts; bake XDG runtime dir. | - |
| `runtime` (`FROM aur`) | 5-2 | `COPY entrypoint.sh` | Install the runtime chezmoi-apply entrypoint (authenticates `bw` from the mounted `bw_*` podman secrets → `BW_SESSION` → `chezmoi apply`, then scrubs BW_* env before `exec`; see [`13-secret-management.md`](13-secret-management.md) §4). | `container/bind/layer_5_files/entrypoint.sh` |
| `runtime` (`FROM aur`) | 5-3 | `USER`/`WORKDIR`/`ENTRYPOINT`/`CMD` | Final image: entrypoint re-applies chezmoi against the host bind. | - |

### Notes on the current state

- The image is fully implemented across 5 stages. `no-config-base`
  is retired.
- `base` Layer 1-5 provisions XDG-compliant directories so the three
  Podman named volumes (cargo / rustup / mise) and the host bind for
  the chezmoi source root attach without overlay-hiding image content.
- The `aur` stage (Layer 4) bootstraps `paru` from the AUR via
  `makepkg -si` as non-root `${USERNAME}`, then installs the Layer 4
  AUR package set from `dependencies/layer_4/paru.txt`. `paru` itself is
  declared with `manager = "custom"` (doc-only) so it is NOT in the
  `paru -S` list — re-submitting an already-bootstrapped AUR helper as a
  `paru -S` target breaks paru's resolver. The paru/AUR cache
  (`~/.cache/paru`) and the pacman package cache are backed by
  `--mount=type=cache`; the cargo registry/git caches are also mounted
  because `paru` (and any Rust AUR package) needs `$CARGO_HOME` writable
  to fetch crates. The bootstrap clone (`/tmp/paru-build`) is removed
  before the stage ends (I-AUR4).
- The build-prepass scratch (`/tmp/chezmoi-src`, `/tmp/build-home`) and
  the build-time `~/.config/chezmoi` are deleted in Stage 5 before the
  final image layer is finalized.

## Acceptance criteria

A new stage may land only when:

1. its name appears in this spec under "Stage (Layer) ordering"
2. its `dependencies/layer_<N>/<manager>.txt` is generated, not hand-written
3. the corresponding [`02-installed-programs.md`](02-installed-programs.md) entries are reachable from `packages.toml`
4. invariants I6–I8 in [`20-container-rules.md`](20-container-rules.md) hold after the change
5. The final image has no `/tmp/chezmoi-src`, `/tmp/build-home`, or
   `~/.config/chezmoi` directory (Stage 4 scratch removal asserted).
6. After `make up`, `podman exec <container> zsh -ic 'echo $CARGO_HOME'`
   outputs `~/.local/share/cargo` (XDG-compliant). The toolchain PATH/HOMEs
   are now **split across phases**: `.zshenv` carries them only at build
   time (`build_mode = true`, sourced by Stage 3 against `/tmp/build-home`);
   at runtime the entrypoint re-applies chezmoi with `build_mode = false`,
   so `.zshenv` omits the block and `~/.config/zsh/.zshrc` re-establishes
   `CARGO_HOME` / `RUSTUP_HOME` / `MISE_DATA_DIR` + the toolchain PATH
   entries for **interactive** shells. `.zshenv` sets
   `ZDOTDIR=$XDG_CONFIG_HOME/zsh`, which is what makes zsh find
   `~/.config/zsh/.zshrc` in the first place (zsh's default `.zshrc` lookup
   is `$ZDOTDIR/.zshrc`, defaulting to `$HOME/.zshrc`; without `ZDOTDIR` the
   XDG `.zshrc` would never be sourced). Verify via `podman exec` with an
   *interactive* zsh (`zsh -ic`): `.zshrc` is interactive-only, so
   `zsh -lc` (login, non-interactive) and `zsh -c` will NOT see
   `CARGO_HOME`. Do not use an ephemeral `podman run`, which neither runs
   the entrypoint nor sources the dotfiles.
7. After `make up`, `~/.local/share/chezmoi/.git` is visible inside the
   container (host bind verified).
8. `make down && make up` preserves toolchain binaries (named-volume
   persistence verified).
9. After `make up`, `podman exec <container> paru --version` prints a
   paru version string as `${USERNAME}` (AUR bootstrap succeeded);
   `nvim --version` (or whatever AUR package is listed in
   `layer_4/paru.txt`) is likewise installed.
10. `podman build --target aur` succeeds in isolation and the resulting
    image has `paru` on PATH.
11. Every `aur`-stage `RUN` carries `--mount=type=cache` on both
    `/var/cache/pacman/pkg` and `/home/${USERNAME}/.cache/paru` (AUR +
    pacman cache reuse, resolving Q1); the bootstrap RUN also mounts the
    cargo registry/git caches (paru is a Rust package).

## Open questions

- Q1: Resolved. AUR builds happen in a dedicated `aur` stage (Layer 4,
  `FROM toolchain AS aur`) positioned between `toolchain` and
  `runtime`. `paru` is bootstrapped via `makepkg -si` as non-root
  `${USERNAME}` (Layer 4-1), then the Layer 4 AUR package set is
  installed from `dependencies/layer_4/paru.txt` (Layer 4-2). `paru` is
  declared `manager = "custom"` (doc-only) so it is bootstrapped once
  and never re-submitted as a `paru -S` target. Both the paru/AUR cache
  (`~/.cache/paru`) and the pacman package cache are backed by
  `--mount=type=cache`; the cargo caches are also mounted for Rust AUR
  packages. See
  [`implementations/2026-06-30-paru-aur-layer-design.md`](implementations/2026-06-30-paru-aur-layer-design.md).
- Q2: `.dockerignore` policy. The repo-root `.dockerignore` currently
  excludes `.git`, `docs`, `.env`, and `container/bind/home_dir`.
  Additional paths to exclude from the `srcroot` build context (large
  untracked subtrees, editor swap files, etc.) need a convention.
