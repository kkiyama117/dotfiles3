# 08 — Automations

> Spec status: **DRAFT**. Normative spec for the project's automation
> pipelines. Concrete Make-target invocations are in [`03-makefile.md`](03-makefile.md);
> the underlying scripts live under `programs/` (e.g. `programs/generate_deps/`)
> and `container/`.

## Inventory of automations

| Name | Status | Trigger | Inputs | Outputs |
|---|---|---|---|---|
| dependency generation | active | `make gen-deps` | `dependencies/packages.toml` | `dependencies/layer_<N>/<manager>.txt` (layers >= 1; `pacman`/`paru`/`nix`/`uv`) + AUTO-GEN block in [`02-installed-programs.md`](02-installed-programs.md) |
| container build | active | `make build` | `Containerfile`, `dependencies/layer_<N>/<manager>.txt`, `HOST_UID`/`HOST_GID` | Podman image |
| bitwarden auth | planned | `make bw-login` | `BW_CLIENTID`/`BW_CLIENTSECRET` (shell env) | `BW_SESSION` in shell env |
| chezmoi deploy (host) | manual | `chezmoi apply` | repo source + Bitwarden secrets via `bw` | `~` files |
| chezmoi deploy (container) | planned | `make apply` (runtime, not build) | repo source + runtime `BW_SESSION` | `$HOME` files in bind mount (image secret-free) |

## Acceptance contracts

### dependency generation (`make gen-deps`)

Implemented by [`programs/generate_deps/main.py`](../../programs/generate_deps/main.py).

- MUST be idempotent — running twice in a row produces a no-op diff
- MUST fail fast on malformed `packages.toml` rather than emitting partial output
- MUST not call the network during generation
- Output files MUST carry a banner indicating they are generated and pointing back to `packages.toml`

### container build (`make build`)

See [`21-container-build-flow.md`](21-container-build-flow.md) for stage invariants and [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md) for the env contract.

### chezmoi deploy

- The host path is documented in [`12-quickstart.md` § Local](12-quickstart.md#local).
- The container path runs at runtime via `make apply` (not build); see [`13-secret-management.md`](13-secret-management.md) §5.

## Out of scope

- CI/CD pipelines (none yet).
- Secret rotation flows.
