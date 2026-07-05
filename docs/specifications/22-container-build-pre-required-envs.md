# 22 — Container build pre-required envs

> Spec status: **DRAFT**. Normative spec for environment variables required
> by `make build`. The general (host-side) pre-required envs are in
> [`11-pre-required-env-values.md`](11-pre-required-env-values.md);
> this file covers only build-time envs.

## Required build-time envs

| Variable | Source | Required | Default | Notes |
|---|---|---|---|---|
| `HOST_UID` | `id -u` (Makefile resolves) | yes | — | passed as `--build-arg`; used by `Containerfile` to remap the `builder` user (see the `base` stage, sub-layers 1-3 / 1-4, in [`21-container-build-flow.md`](21-container-build-flow.md); the non-root-account rule is I7 in [`20-container-rules.md`](20-container-rules.md)) |
| `HOST_GID` | `id -g` (Makefile resolves) | yes | — | same as above |
| `USERNAME` | `.env` (gitignored, repo-root) | yes (build, up) | — | passed as `--build-arg`. The `Containerfile` renames the base image's `builder` account to this name and sets `/home/$USERNAME` as the home dir; `make up` bind-mounts the repo root (chezmoi source) at `/home/$USERNAME/.local/share/chezmoi` and mounts the `dotfiles_cargo`/`dotfiles_rustup`/`dotfiles_mise`/`dotfiles_gnupg`/`dotfiles_ssh` named volumes at `~/.local/share/{cargo,rustup,mise,gnupg}` and `~/.ssh`. `dotfiles_gnupg` persists the GPG keyring at `GNUPGHOME` (`~/.local/share/gnupg`, set by `dot_zshenv.tmpl`); `dotfiles_ssh` persists the SSH client keyring at `~/.ssh`; no key material is baked into the image (see spec 20 I-GPG1/I-GPG4 and I-SSH1/I-SSH3). `make build` and `make up` fail fast with `"USERNAME is not set"` if absent. |
| `JOBS`     | env, overridable by `make JOBS=N` | no | `1` | `podman build --jobs` |

### `.env` contract

`Makefile` reads `.env` at the repository root via `-include .env`. The
file is gitignored, per-machine, and uses `KEY=VALUE` shell syntax.

```sh
# .env (example; do not commit)
USERNAME=kiyama
```

`.env` MUST NOT carry secrets — runtime auth material is provided as
**podman secrets** (`bw_clientid` / `bw_clientsecret` / `bw_password`),
mounted by `make up` (each only if it exists) as tmpfs
`/run/secrets/*`; the master password is consumed via
`bw unlock --passwordfile` and never enters an env. See
[`13-secret-management.md`](13-secret-management.md) §4. Build-time envs
(`HOST_UID` / `HOST_GID` / `USERNAME` / `JOBS`) are unchanged and remain
the only envs `make build` consumes.

### Runtime podman secrets (optional)

| Secret name | Required | Notes |
|---|---|---|
| `bw_clientid` | no (auth) | `BW_CLIENTID` source for `bw login --apikey` |
| `bw_clientsecret` | no (auth) | `BW_CLIENTSECRET` source for `bw login --apikey` |
| `bw_password` | no (auth) | master password, read via `bw unlock --passwordfile` |

All three are optional: `make up` starts without them and the
entrypoint skips `bw` auth (no-secret startup). Create them once on the
host (`printf '%s' "$VAL" | podman secret create <name> -`); they
persist in the podman store across restarts.

## Removed: `BW_ID` build-time mechanism

The previous `BW_ID` build-time BuildKit-secret mechanism (mounting a
Bitwarden item-ID file at `/run/secrets/bitwarden_id`) has been
**removed**. `chezmoi apply` now runs at runtime, authenticating `bw`
from the mounted `bw_*` podman secrets and deriving `BW_SESSION` in the
entrypoint process (then scrubbing it before `exec`); the image is
secret-free. See
[`13-secret-management.md`](13-secret-management.md) §5 and the Makefile
(`BW_ID` / `BW_SECRET` skeleton deleted).

## Related

- General pre-required envs (host side, not build): [`11-pre-required-env-values.md`](11-pre-required-env-values.md)
- Container rules: [`20-container-rules.md`](20-container-rules.md)
- Build flow / stage invariants: [`21-container-build-flow.md`](21-container-build-flow.md)
- Make target contract: [`03-makefile.md`](03-makefile.md)
