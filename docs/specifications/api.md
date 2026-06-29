# API

API or commands for our dotfiles

## Manage dotfiles

We use `chezmoi` to manage the dotfiles. Below are the commands we use mainly.
For details, see the [chezmoi documentation](https://www.chezmoi.io/docs/).

| Command | Purpose |
| --- | --- |
| `chezmoi init <repo>` | Initialise the source directory from this repository. |
| `chezmoi apply` | Apply the managed dotfiles to `$HOME`. |
| `chezmoi diff` | Show the diff between the source state and the destination. |
| `chezmoi status` | List files whose state differs between source and destination. |
| `chezmoi add <path>` | Add an existing file under `$HOME` to the source directory. |
| `chezmoi edit <path>` | Edit a managed file via its source representation. |
| `chezmoi cd` | Open a shell in the source directory. |
| `chezmoi update` | `git pull` the source and `chezmoi apply` in one step. |

## container management

This repository has container definitions for managing the dotfiles with Podman.
Config files for the containers are stored in the `containers` directory.
And now we use `make` to manage the containers.

Run `make help` inside `containers/` for the canonical list. The main targets:

| Target | Purpose |
| --- | --- |
| `make build` | Build the image matching your host uid/gid. |
| `make rebuild` | Build with `--no-cache`. |
| `make run` | One-shot interactive ephemeral container (zsh). |
| `make up` | Start a detached, named container. |
| `make exec` (alias `shell`) | Drop into an interactive zsh in the running container. |
| `make down` | Stop & remove the named container (and its Podman secrets). |
| `make stop` | Stop the named container without removing it. |
| `make restart` | `down` then `up`. |
| `make logs` | Tail container logs. |
| `make ps` | Show container status. |
| `make verify` | Smoke-test the image (id, sudo, tools, bind-mount write). |
| `make history` | Show image layer history (secret leak audit). |
| `make clean` | Remove the named container and the built image. |

Common variables (override on the command line):

- `RBW_CONFIG=<path>` / `RBW_SECRET=<path>` — host files mounted as Podman
  secrets for `rbw` config and master password. Both are runtime-only; nothing
  is baked into the image.
- `MOUNT_SOURCE=1` — bind the host repo at `/var/lib/chezmoi-source` so
  `chezmoi cd` inside the container lands in a working tree you can commit
  back. Off by default; the baked image source stays usable standalone.
