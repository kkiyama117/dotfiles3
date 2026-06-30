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
| `build-prepass` (`FROM base`) | 2 | `COPY --from=srcroot`; `BUILD_MODE=true chezmoi execute-template --init < /tmp/chezmoi-src/.chezmoi.toml.tmpl > ~/.config/chezmoi/chezmoi.toml` (`build_mode = true`); `chezmoi apply --destination /tmp/build-home` | Scratch render of ENV-bearing dotfiles with `build_mode = true`; secret-free. | `srcroot` named build-context, `.chezmoi.toml.tmpl` |
| `toolchain` (`FROM build-prepass`) | 3 | `rustup-init`, mise installer, `cargo install`; cache mounts on `$CARGO_HOME/{registry,git}` | Install rustup/mise/cargo binaries under XDG-compliant paths. | `/tmp/build-home/.zshenv`, `dependencies/layer_3/cargo.txt` |
| `aur` (`FROM toolchain`) | 4-1 | `git clone` paru PKGBUILD + `makepkg -si` (sources `/tmp/build-home/.zshenv`; cache mounts on `~/.cache/paru` + `/var/cache/pacman/pkg` + `$CARGO_HOME/{registry,git}`) | Bootstrap `paru` from the AUR as non-root `${USERNAME}`. | AUR `paru` PKGBUILD, Layer 1-4 sudoers |
| `aur` (`FROM toolchain`) | 4-2 | `paru -S --noconfirm --needed` | Install the Layer 4 AUR package set from the generated list (`manager = "paru"` entries only). | `dependencies/layer_4/paru.txt` |
| `runtime` (`FROM aur`) | 5-1 | `FROM aur AS runtime` | Runtime stage base (inherits the `aur` image). | - |
| `runtime` (`FROM aur`) | 5-2 | bake minimum home: `cp /tmp/build-home/.zshenv` -> `~/.zshenv`; `install -d ~/.config/chezmoi`; `chown` home; `install -d /run/user/$UID` (as root) | Bake a wizard-free / PATH-equipped minimum `$HOME` so the image boots into a working shell independent of the runtime entrypoint (covers `make exec` racing the entrypoint apply, and entrypoint-bypassed `podman run`). Only `~/.zshenv` is baked — **no `chezmoi.toml` is baked** (the build-prepass toml is stripped in 5-3; the entrypoint creates it fresh). | `/tmp/build-home/.zshenv` (from Stage 2 render) |
| `runtime` (`FROM aur`) | 5-3 | strip build artifacts + `/etc/skel` bash remnants: `rm -rf /tmp/build-home /tmp/chezmoi-src`; `rm -f ~/.config/chezmoi/chezmoi.toml` (the root-owned build-prepass toml that rode the Stage chain); `rm -f ~/.{bashrc,bash_profile,bash_logout,profile}` (as root) | Drop Stage 2/3/4 scratch so neither tree rides the final layer (acceptance #5); strip the carried-forward build-prepass `chezmoi.toml` so the entrypoint (as `${USERNAME}`) can create the runtime one; remove the non-chezmoi-managed bash remnants. | - |
| `runtime` (`FROM aur`) | 5-4 | `COPY entrypoint.sh` + `chmod` + `USER`/`WORKDIR`/`ENTRYPOINT`/`CMD` | Install the runtime chezmoi-apply entrypoint (authenticates `bw` from the mounted `bw_*` podman secrets → `BW_SESSION` → `chezmoi apply`, then scrubs BW_* env before `exec`; see [`13-secret-management.md`](13-secret-management.md) §4) and set the final user/entrypoint. Final image: entrypoint re-applies chezmoi against the host bind. | `container/bind/layer_5_files/entrypoint.sh` |

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
- The build-prepass scratch (`/tmp/chezmoi-src`, `/tmp/build-home`) is
  deleted in Stage 5 (Layer 5-3) before the final image layer is
  finalized. The build-prepass `~/.config/chezmoi/chezmoi.toml`
  (`build_mode = true`, rendered from `.chezmoi.toml.tmpl` by
  `chezmoi execute-template --init` with `BUILD_MODE=true`, USERNAME-owned)
  rides the Stage chain (`toolchain` -> `aur` -> `runtime`) into the
  runtime image and is **stripped** in Layer 5-3 (not replaced); the
  runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is
  **re-rendered from the same `.chezmoi.toml.tmpl` by the entrypoint**
  (BUILD_MODE unset) as `${USERNAME}` before `chezmoi apply` (see
  acceptance #5a / invariant I10). The minimum `.zshenv` is copied out of `/tmp/build-home`
  (Layer 5-2) before that scratch tree is dropped (Layer 5-3).

## Acceptance criteria

A new stage may land only when:

1. its name appears in this spec under "Stage (Layer) ordering"
2. its `dependencies/layer_<N>/<manager>.txt` is generated, not hand-written
3. the corresponding [`02-installed-programs.md`](02-installed-programs.md) entries are reachable from `packages.toml`
4. invariants I6–I8 in [`20-container-rules.md`](20-container-rules.md) hold after the change
5. The final image has no `/tmp/chezmoi-src` or `/tmp/build-home`
   directory (Stage 5 scratch removal asserted).
5a. The final image bakes a **minimum `$HOME`** so it boots into a
    wizard-free, PATH-equipped, *shell-usable* state independent of the
    runtime entrypoint. Concretely the image carries `~/.zshenv` (copied
    from the Stage 2 `/tmp/build-home` render; `dot_zshenv.tmpl` has no
    template directives and no `build_mode` branch, so this is
    byte-identical to the runtime `chezmoi apply --force` output). It
    does **NOT** bake `~/.config/chezmoi/chezmoi.toml`: the build-prepass
    toml (`build_mode = true`, root-owned) is stripped in Layer 5-3, and
    the runtime entrypoint creates `~/.config/chezmoi/chezmoi.toml`
    (`build_mode = false`) fresh as `${USERNAME}` before `chezmoi apply`.
    So the baked shell is usable without the entrypoint, but
    `chezmoi apply` requires the entrypoint (or a manually-created
    config). This covers two failure modes: (a) `make exec` racing the
    entrypoint's `chezmoi apply` (an exec'd `zsh` would otherwise see a
    `$HOME` with no zsh startup file and trigger the `zsh/newuser`
    first-run wizard via `/usr/share/zsh/scripts/newuser`; with
    `~/.zshenv` baked, the module's "none of
    `.zshenv`/`.zprofile`/`.zshrc`/`.zlogin` exist" condition is never
    met); (b) the container being exec'd with the entrypoint bypassed
    (e.g. `podman run --entrypoint ...`) — the shell is usable, just not
    `chezmoi apply`-ready until the entrypoint (or a manual config) runs.
5b. The final image has no `/etc/skel` bash remnants in `$HOME`
    (`.bashrc`, `.bash_profile`, `.bash_logout`, `.profile`); Stage 5
    removes the files that Layer 1-3's `usermod -l ... -d
    /home/${USERNAME} -m builder` moved out of the base image's `builder`
    home (chezmoi does not manage them, so `chezmoi apply` never would).
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
   > **Known drift (out of scope of the minimum-home work):** criterion #6
   > describes the *intended* phase split, but the current
   > `dot_zshenv.tmpl` has **no `build_mode` branch and no chezmoi
   > template directives at all** — it always sets `CARGO_HOME` /
   > `RUSTUP_HOME` / `MISE_DATA_DIR` via `${VAR:-default}`. The outcome is
   > functionally equivalent (the `${VAR:-}` defaults land on the same
   > XDG paths), which is also why baking the Stage 2 render of `.zshenv`
   > into the image (acceptance #5a) is safe — build-time and runtime
   > renders are byte-identical. Re-introducing the `build_mode` branch
   > to actually omit the block at runtime is tracked separately.
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
