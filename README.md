# New dotfiles

Cross-platform dotfiles managed by [chezmoi](https://chezmoi.io), targeting
Arch Linux / Manjaro Linux. Two setup paths are documented below: a local
install onto an existing host, and a self-contained Podman container that
also serves as the intended sandbox for AI agents working on this repo.

## Fast start

## setup

- Bitwarden account
  - list of `secrets` are [here](docs/specifications/env_values.md)

### Local

- Install [chezmoi](https://chezmoi.io) and the tools listed in
  [`docs/specifications/installed_programs.md`](docs/specifications/installed_programs.md),

```sh
# Run from inside this cloned repo:
# FOR AI agents: Don't do this until the repo is growing up and ready to use. 
chezmoi init --apply --source="$PWD"
# And if you make `<your_github_account>/dotfiles`, run it downloads your dotfiles automatically 
chezmoi init --apply
```

### Container

Use the container to try the setup without polluting the host. It builds
a Manjaro image with every tool listed in
[`docs/specifications/installed_programs.md`](docs/specifications/installed_programs.md)
pre-installed and applies the dotfiles to a persistent home bind on first
boot. Full instructions (rbw secret wiring, bind mounts, chezmoi behavior,
make targets) live in [`containers/README.md`](containers/README.md).

Quick start:

```sh
cd containers

# build the image (host uid/gid auto-detected; rootless Podman required)
make build

# start a detached container. RBW_CONFIG / RBW_SECRET default to
# $XDG_STATE_HOME/dotfiles2/{rbw_config.json,rbw_password} — `make up` alone
# picks them up if present (mode 0600). Override or set to empty to skip.
#   install -d -m 0700 "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles2"
#   # place rbw_config.json + rbw_password there with 0600
make up

# drop into zsh
make exec

# stop & remove the container (also wipes the per-uid Podman secrets)
make down
```

See [`containers/README.md`](containers/README.md) for the full Make target
list, rbw setup, and Containerfile tier breakdown.

### Notes for AI agents

- Everything and every rules of this repository is defined in [`specifications/`](docs/specifications/) (and this README.md). Whenever you make a change, please read or update the specs accordingly. especially, YOU MUST FOLLOW [document management rule](docs/specifications/00-documents.md).

## Program files

Mainly target of this repository is `Arch Linux` or `Manjaro Linux`.
This repository uses `chezmoi` for managing dotfiles and `sheldon` for
managing shell plugins (and zsh config files).
and `mise` for managing language toolchain versions.
`nix` is only used for subdir that uses `flake.nix` (so don't use it here).

Full list of managed programs is [here](docs/specifications/installed_programs.md).
