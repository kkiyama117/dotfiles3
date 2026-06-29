# 22 — Container build pre-required envs

> Spec status: **DRAFT**. Normative spec for environment variables required
> by `make build`. The general (host-side) pre-required envs are in
> [`11-pre-required-env-values.md`](11-pre-required-env-values.md);
> this file covers only build-time envs.

## Required build-time envs

| Variable | Source | Required | Default | Notes |
|---|---|---|---|---|
| `HOST_UID` | `id -u` (Makefile resolves) | yes | — | passed as `--build-arg`; used by `Containerfile` to remap the `builder` user (see the `no-config-base` stage in [`21-container-build-flow.md`](21-container-build-flow.md); the non-root-account rule is I7 in [`20-container-rules.md`](20-container-rules.md)) |
| `HOST_GID` | `id -g` (Makefile resolves) | yes | — | same as above |
| `USERNAME` | `.env` (gitignored, repo-root) | yes (build, up) | — | passed as `--build-arg`. The `Containerfile` renames the base image's `builder` account to this name and sets `/home/$USERNAME` as the home dir; `make up` bind-mounts `container/bind/home_dir/` at the same path. `make build` and `make up` fail fast with `"USERNAME is not set"` if absent. |
| `JOBS`     | env, overridable by `make JOBS=N` | no | `1` | `podman build --jobs` |
| `BW_ID`    | path to a file containing the Bitwarden item ID | conditional | `TEST` (placeholder) | When the file at `$BW_ID` exists, it is mounted as the BuildKit secret `bitwarden_id`. When it does not exist, the build still succeeds but any layer that consumes `bitwarden_id` will fail. |

### `.env` contract

`Makefile` reads `.env` at the repository root via `-include .env`. The
file is gitignored, per-machine, and uses `KEY=VALUE` shell syntax.

```sh
# .env (example; do not commit)
USERNAME=kiyama
```

`.env` MUST NOT carry secrets — secrets travel via `$(BW_ID)` file + BuildKit
secret mount only.

## `BW_ID` contract

- The variable holds a **path**, not the ID itself. The contents of the
  file are mounted at `/run/secrets/bitwarden_id` inside the build.
- The contents must be a single Bitwarden item ID. Newlines are
  trimmed; no surrounding whitespace.
- File permissions: 0400 (BuildKit accepts 0600 but consumers in this
  repo assume 0400).
- Never commit a real `BW_ID` file. Default value `TEST` is intentionally
  invalid so a missing file path is harmless.

## Related

- General pre-required envs (host side, not build): [`11-pre-required-env-values.md`](11-pre-required-env-values.md)
- Container rules: [`20-container-rules.md`](20-container-rules.md)
- Build flow / stage invariants: [`21-container-build-flow.md`](21-container-build-flow.md)
- Make target contract: [`03-makefile.md`](03-makefile.md)
