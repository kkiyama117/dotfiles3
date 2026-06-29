# 21 — Container build flow

> Spec status: **active**. Normative spec for the Containerfile stage / layer
> ordering. The implementation lives in
> [`../../container/Containerfile`](../../container/Containerfile). 

## Stage (Layer) ordering

The Containerfile is a multi-stage build. Each `FROM ... AS <stage>` is a
stage; within a stage, numbered **sub-layers** (`Layer N-M`) group related
`RUN` / `ARG` / `USER` directives. The table below reflects the file as of
2026-06-29.

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

### Notes on the current state

- The image is fully implemented across 4 stages. `no-config-base`
  is retired.
- `base` Layer 1-5 provisions XDG-compliant directories so the three
  Podman named volumes (cargo / rustup / mise) and the host bind for
  the chezmoi source root attach without overlay-hiding image content.
- The build-prepass scratch (`/tmp/chezmoi-src`, `/tmp/build-home`) and
  the build-time `~/.config/chezmoi` are deleted in Stage 4 before the
  final image layer is finalized.

## Acceptance criteria

A new stage may land only when:

1. its name appears in this spec under "Stage (Layer) ordering"
2. its `dependencies/layer_<N>/<manager>.txt` is generated, not hand-written
3. the corresponding [`02-installed-programs.md`](02-installed-programs.md) entries are reachable from `packages.toml`
4. invariants I6–I8 in [`20-container-rules.md`](20-container-rules.md) hold after the change
5. The final image has no `/tmp/chezmoi-src`, `/tmp/build-home`, or
   `~/.config/chezmoi` directory (Stage 4 scratch removal asserted).
6. After `make up`, `podman exec <container> zsh -lc 'echo $CARGO_HOME'`
   outputs `~/.local/share/cargo` (XDG-compliant; the toolchain PATH/HOMEs
   live in `.zshenv`, rendered by the entrypoint at runtime, so verify via
   `podman exec` with a zsh login shell — not an ephemeral `podman run`
   with `bash -lc`, which neither runs the entrypoint nor sources
   `.zshenv`).
7. After `make up`, `~/.local/share/chezmoi/.git` is visible inside the
   container (host bind verified).
8. `make down && make up` preserves toolchain binaries (named-volume
   persistence verified).

## Open questions

- Q1: AUR / `paru` build scheduling and cache mount. Layer 1-4 provisions
  NOPASSWD sudoers so `paru` / `makepkg` can run non-interactively. Open
  parts: (a) whether AUR builds happen in a Stage 3-equivalent build
  stage or via a dedicated layer; (b) whether the `paru` / AUR cache is
  also backed by `--mount=type=cache` (the pacman cache already is).
- Q2: `.dockerignore` policy. The repo-root `.dockerignore` currently
  excludes `.git`, `docs`, `.env`, and `container/bind/home_dir`.
  Additional paths to exclude from the `srcroot` build context (large
  untracked subtrees, editor swap files, etc.) need a convention.
