# Quickstart

> Spec status: **DRAFT** — kept aligned with the current `Makefile` and
> `container/Containerfile`. Sections marked **(planned)** describe behaviour
> not yet implemented; do not assume it works yet.

## Common

Before either path below works, create a `.env` at the repository root:

```sh
# .env (gitignored, per-machine)
USERNAME=<your container username>   # e.g. USERNAME=kiyama
```

`USERNAME` is required by `make build` and `make up` — both fail fast with
`"USERNAME is not set"` if the file is missing or empty. The container
remaps the base image's `builder` account to this username; the home
bind is mounted at `/home/$USERNAME`. See
[`03-makefile.md`](03-makefile.md) and
[`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).

The Bitwarden CLI is `bw` (package `bitwarden-cli`); the per-item-ID secret
list is being enumerated in [`11-pre-required-env-values.md`](11-pre-required-env-values.md).
The secret-management design lives in [`13-secret-management.md`](13-secret-management.md).

## Local

Install [chezmoi](https://chezmoi.io) and the base packages listed in
[`02-installed-programs.md`](02-installed-programs.md) and
[`02-installed-programs.md`](02-installed-programs.md).

```sh
# Run from inside this cloned repo.
# NOTE for AI agents: do NOT run this against the host until the repo is
# verified to be ready. Use the container path below first.
chezmoi init --apply --source="$PWD"

# Or, if you publish this as <your_github_account>/dotfiles, the user-facing
# bootstrap is:
chezmoi init --apply <your_github_account>
```

See [`08-automations.md`](08-automations.md) for downstream automation
(dependency generation, deploy flow).

## Container

The container path lets you try the setup without touching the host.
It builds a Manjaro image and (once Layer 2 lands) applies dotfiles to a
persistent home bind on first boot.

Prerequisites: rootless Podman + BuildKit. See
[`20-container-rules.md`](20-container-rules.md) and
[`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).

Quick start:

```sh
# from the repository root
make help                  # list available targets

# build the image matching your host uid/gid; rootless Podman required.
# Requires USERNAME set in .env.
make build

# start a detached container; binds container/bind/home_dir to /home/$USERNAME
make up

# open an interactive shell (zsh) in the running container
make exec

# stop & remove the container (idempotent)
make down
```

### Make variable summary

| Variable | Source | Required | Note |
|---|---|---|---|
| `USERNAME`  | `.env`           | yes (build, up) | container account name; home bound at `/home/$USERNAME` |
| `HOST_UID`  | `id -u` (auto)   | yes              | passed as `--build-arg` |
| `HOST_GID`  | `id -g` (auto)   | yes              | passed as `--build-arg` |
| `JOBS`      | env (default `1`)| no               | parallel build jobs |
| `IMAGE`     | Makefile default | no               | `localhost/dotfiles-manjaro:latest` |
| `CONTAINER` | Makefile default | no               | `dotfiles-manjaro` |

### What is not yet implemented (planned)

- Layer 2 (`chezmoi apply` inside the build) — the current image is just the
  base + uid/gid remap. Until Layer 2 lands, `make up` gives you a container
  whose `/home/$USERNAME` is the host bind dir but with no dotfiles applied.
  See [`21-container-build-flow.md`](21-container-build-flow.md).
- `make gen-deps` — see [`08-automations.md`](08-automations.md).
- **Bitwarden auth + `chezmoi apply` at runtime** — `make up` currently
  only bind-mounts the home dir. The plan is to run `bw login --apikey` +
  `bw unlock` (setting `BW_SESSION`) then `chezmoi apply` inside the
  container at start, so chezmoi templates that call `bitwarden*` resolve
  at apply time. The image stays secret-free. See
  [`13-secret-management.md`](13-secret-management.md) and
  [`11-pre-required-env-values.md`](11-pre-required-env-values.md).
  Gated on Layer 2 / runtime-apply landing.

## Reference

- [`20-container-rules.md`](20-container-rules.md) — rootless / userns / bind-mount conventions
- [`21-container-build-flow.md`](21-container-build-flow.md) — Layer breakdown (Layer 1 / Layer 2 / …)
- [`../references/2026-06-25-chezmoi-in-containers.md`](../references/2026-06-25-chezmoi-in-containers.md) — chezmoi-in-container gotchas (safe.directory, UID remap)
