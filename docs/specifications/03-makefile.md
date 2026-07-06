# 03 — Makefile

> Spec status: **DRAFT**. Normative contract for `Makefile` target
> naming and behaviour. The Makefile itself is the SoT for actual commands;
> this spec governs **what targets are allowed and what they must guarantee**.
It may be moved in `1x-` or `2x-` because it is not a rule of metadata or documents

## Current targets

| Target | Class | Must do |
|---|---|---|
| `help`  | meta | print one-line summary of every target. Default target. |
| `build` | container | build the container image for the current host uid/gid via rootless Podman. Requires `$(USERNAME)`. Tags the image as `$(IMAGE)`. |
| `build_container` | container | alias of `build`. |
| `up`    | container | start a detached container named `$(CONTAINER)`. Bind-mounts the repo root (chezmoi source) at `/home/$(USERNAME)/.local/share/chezmoi`, mounts the named volumes `dotfiles_cargo`/`dotfiles_rustup`/`dotfiles_mise`/`dotfiles_gnupg`/`dotfiles_ssh` at the XDG data paths (`$XDG_DATA_HOME/{cargo,rustup,mise,gnupg}`) and at `~/.ssh`, passes `BW_SESSION` through from the host shell, and uses `--userns=keep-id --replace` per [`20-container-rules.md`](20-container-rules.md) I2. The Stage 4 entrypoint runs `chezmoi apply --no-tty --force` at runtime, then `exec`s the passed command (`sleep infinity`). **Does not return until the entrypoint's `chezmoi apply` has finished** — polls the `/tmp/chezmoi-applied` readiness sentinel (see [`20-container-rules.md`](20-container-rules.md) I-RUN2) up to `UP_WAIT_TIMEOUT` seconds; on early container exit or timeout, exits non-zero and tails `podman logs` so a `make exec` immediately after always sees a fully applied `$HOME` (sheldon + starship load on the first interactive shell). **Refuses to start if the image's entrypoint differs from the source** (`_verify_image_fresh` prerequisite; see [`20-container-rules.md`](20-container-rules.md) I-RUN3) — fails fast with `run \`make build\`` instead of silently timing out against a stale entrypoint. Requires `$(USERNAME)`. |
| `exec`  | container | open an interactive shell inside `$(CONTAINER)`. |
| `down`  | container | stop and remove `$(CONTAINER)`. Errors during stop/rm are ignored so the target is idempotent. |
| `clean` | container | depends on `down`; removes the `dotfiles_cargo`/`dotfiles_rustup`/`dotfiles_mise`/`dotfiles_gnupg`/`dotfiles_ssh` named volumes and the image. Errors are ignored so the target is idempotent. |

## Optional / planned targets

| Target | Class | Status | Acceptance criteria |
|---|---|---|---|
| `gen-deps` | codegen | active (see [`08-automations.md`](08-automations.md)) | regenerates `dependencies/layer_<N>/<manager>.txt` and the AUTO-GEN block in [`02-installed-programs.md`](02-installed-programs.md) from `dependencies/packages.toml`. Idempotent. |
| `test-deps` | codegen | active (see [`08-automations.md`](08-automations.md)) | runs `python3 -m pytest programs/generate_deps/tests/ -q`. Exit 0. Does not touch the network or the container. |

## Contract

- Every target appearing in `make help` must be `.PHONY` unless it produces a tracked output file.
- Targets that mutate the host (secrets, bind mounts, podman state) must list the side effects in `make help` output.
- `make build` is the only target authorised to call `podman build` directly.
- Targets that depend on `$(USERNAME)` MUST gate on the `_require_username` helper (or equivalent) so the failure mode is "`USERNAME is not set`" rather than an obscure podman error.
- `down` MUST be idempotent — running it against an already-stopped or absent container MUST exit 0.
- `up` passes `BW_SESSION` through from the host shell via `-e BW_SESSION=$$BW_SESSION` (no hardcode). The operator MUST `export BW_SESSION=...` in the shell that runs `make up` for the Stage 4 entrypoint's `chezmoi apply` to resolve `bitwarden*` templates; a missing `BW_SESSION` is non-fatal (apply still runs, secret-dependent entries simply do not resolve). See [`13-secret-management.md`](13-secret-management.md).
- New targets require a `08-automations.md` entry or a `12-quickstart.md` reference; orphaned targets are forbidden.

## Variables surfaced via `make` invocation

| Variable | Type | Default | Notes |
|---|---|---|---|
| `JOBS`      | int  | `1` | `--jobs` for `podman build` |
| `UP_WAIT_TIMEOUT` | int | `120` | seconds `make up` waits for the entrypoint's `chezmoi apply` to finish (polls `/tmp/chezmoi-applied`) before returning; on timeout or early container exit, `make up` exits non-zero and tails `podman logs`. See [`20-container-rules.md`](20-container-rules.md) I-RUN2. |
| `HOST_UID`  | int  | `$(id -u)` | passed as `--build-arg` |
| `HOST_GID`  | int  | `$(id -g)` | passed as `--build-arg` |
| `USERNAME`  | str  | — (required; sourced from `.env`) | passed as `--build-arg`; also drives the `up` bind mount target `/home/$(USERNAME)/.local/share/chezmoi` (chezmoi source) and the toolchain volume mount points `/home/$(USERNAME)/.local/share/{cargo,rustup,mise}`. See [`11-pre-required-env-values.md`](11-pre-required-env-values.md). |
| `IMAGE`     | str  | `localhost/dotfiles-manjaro:latest` | image tag. Matches `LABEL org.opencontainers.image.title` in `Containerfile`. |
| `CONTAINER` | str  | `dotfiles-manjaro` | container name used by `up`/`exec`/`down`/`clean`. |
| `CARGO_VOLUME`  | str | `dotfiles_cargo`  | named volume mounted at `$XDG_DATA_HOME/cargo` by `up`; removed by `clean`. |
| `RUSTUP_VOLUME` | str | `dotfiles_rustup` | named volume mounted at `$XDG_DATA_HOME/rustup` by `up`; removed by `clean`. |
| `MISE_VOLUME`   | str | `dotfiles_mise`   | named volume mounted at `$XDG_DATA_HOME/mise` by `up`; removed by `clean`. |
| `GNUPG_VOLUME`  | str | `dotfiles_gnupg`  | named volume mounted at `$XDG_DATA_HOME/gnupg` (`GNUPGHOME`) by `up`; removed by `clean`. |
| `SSH_VOLUME`    | str | `dotfiles_ssh`    | named volume mounted at `~/.ssh` by `up`; removed by `clean`. |

## `.env` contract

`Makefile` reads `.env` via `-include .env` (silent if missing). The file is
gitignored; per-machine. Currently it must define:

```sh
USERNAME=<your container username>
```

`.env` MUST NOT carry secrets — runtime secrets (`BW_CLIENTID`,
`BW_CLIENTSECRET`, `BW_SESSION`) live in the interactive shell env only. See
[`13-secret-management.md`](13-secret-management.md) and
[`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
