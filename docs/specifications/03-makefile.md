# 03 — Makefile

> Spec status: **DRAFT**. Normative contract for `Makefile` target
> naming and behaviour. The Makefile itself is the SoT for actual commands;
> this spec governs **what targets are allowed and what they must guarantee**.

## Current targets

| Target | Class | Must do |
|---|---|---|
| `help`  | meta | print one-line summary of every target. Default target. |
| `build` | container | build the container image for the current host uid/gid via rootless Podman. Requires `$(USERNAME)`. Tags the image as `$(IMAGE)`. |
| `build_container` | container | alias of `build`. |
| `up`    | container | start a detached container named `$(CONTAINER)` with `$(HOME_DIR)` bind-mounted at `/home/$(USERNAME)`. Uses `--userns=keep-id` per [`20-container-rules.md`](20-container-rules.md) I2. Requires `$(USERNAME)`. |
| `exec`  | container | open an interactive shell inside `$(CONTAINER)`. |
| `down`  | container | stop and remove `$(CONTAINER)`. Errors during stop/rm are ignored so the target is idempotent. |

## Optional / planned targets

| Target | Class | Status | Acceptance criteria |
|---|---|---|---|
| `gen-deps` | codegen | planned (see [`01-automations.md`](01-automations.md)) | regenerates `dependencies/layer_<N>.txt` and the AUTO-GEN block in [`02-installed-programs.md`](02-installed-programs.md) from `dependencies/packages.toml`. Idempotent. |

## Contract

- Every target appearing in `make help` must be `.PHONY` unless it produces a tracked output file.
- Targets that mutate the host (secrets, bind mounts, podman state) must list the side effects in `make help` output.
- `make build` is the only target authorised to call `podman build` directly.
- Targets that depend on `$(USERNAME)` MUST gate on the `_require_username` helper (or equivalent) so the failure mode is "`USERNAME is not set`" rather than an obscure podman error.
- `down` MUST be idempotent — running it against an already-stopped or absent container MUST exit 0.
- New targets require a `01-automations.md` entry or a `12-quickstart.md` reference; orphaned targets are forbidden.

## Variables surfaced via `make` invocation

| Variable | Type | Default | Notes |
|---|---|---|---|
| `JOBS`      | int  | `1` | `--jobs` for `podman build` |
| `HOST_UID`  | int  | `$(id -u)` | passed as `--build-arg` |
| `HOST_GID`  | int  | `$(id -g)` | passed as `--build-arg` |
| `USERNAME`  | str  | — (required; sourced from `.env`) | passed as `--build-arg`; also drives the `up` bind target `/home/$(USERNAME)`. See [`11-pre-required-env-values.md`](11-pre-required-env-values.md). |
| `BW_ID`     | path | `TEST` | mounted as BuildKit secret `bitwarden_id` when the file exists. See [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md). |
| `IMAGE`     | str  | `localhost/dotfiles-manjaro:latest` | image tag. Matches `LABEL org.opencontainers.image.title` in `Containerfile`. |
| `CONTAINER` | str  | `dotfiles-manjaro` | container name used by `up`/`exec`/`down`. |

## `.env` contract

`Makefile` reads `.env` via `-include .env` (silent if missing). The file is
gitignored; per-machine. Currently it must define:

```sh
USERNAME=<your container username>
```

`.env` MUST NOT carry secrets — secrets travel via `$(BW_ID)` file + BuildKit
secret mount only. See [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
