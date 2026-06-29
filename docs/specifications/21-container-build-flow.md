# 21 — Container build flow

> Spec status: **DRAFT (stub)**. Normative spec for the Containerfile layer
> ordering. The implementation lives in
> [`../../container/Containerfile`](../../container/Containerfile).

## Stage (Layer) ordering

| Stage (`FROM ... AS`) | Layer | Purpose | Inputs |
|---|---|---|---|
| `base`            | 0 | minimum packages required for `chezmoi apply` (base-devel, sudo, curl, git). | `manjarolinux/base:latest`, `dependencies/layer_1.txt` |
| `no-config-base`  | 1 | remap the `builder` user to host uid/gid for bind-mount ownership. | `HOST_UID`, `HOST_GID` build-args |
| _(planned)_ `chezmoi-apply` | 2 | run `chezmoi apply` once with secrets injected via BuildKit `--secret` mounts. | `BW_ID` secret, `/var/lib/chezmoi-source` bind |
| _(planned)_ `tooling` | 3+ | install per-layer tool sets (`paru`, `nix`, `mise`, `uv`) per `dependencies/layer_<N>.txt`. | layer txt files |

## Acceptance criteria

A new stage may land only when:

1. its name appears in this spec under "Stage ordering"
2. its `dependencies/layer_<N>.txt` is generated, not hand-written
3. the corresponding [`02-installed-programs.md`](02-installed-programs.md) entries are reachable from `packages.toml`
4. invariants I6–I8 hold after the change

## Open questions

- Q1: how are AUR packages installed without an interactive sudo password inside the build? `--mount=type=bind,from=...` of a pacman cache, or `makepkg --noconfirm`?
