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
| `USERNAME` | `.env` (gitignored, repo-root) | yes (build, up) | — | passed as `--build-arg`. The `Containerfile` renames the base image's `builder` account to this name and sets `/home/$USERNAME` as the home dir; `make up` bind-mounts `container/bind/home_dir/` at the same path. `make build` and `make up` fail fast with `"USERNAME is not set"` if absent. |
| `JOBS`     | env, overridable by `make JOBS=N` | no | `1` | `podman build --jobs` |

### `.env` contract

`Makefile` reads `.env` at the repository root via `-include .env`. The
file is gitignored, per-machine, and uses `KEY=VALUE` shell syntax.

```sh
# .env (example; do not commit)
USERNAME=kiyama
```

`.env` MUST NOT carry secrets — runtime secrets (`BW_CLIENTID`,
`BW_CLIENTSECRET`, `BW_SESSION`) live in the interactive shell env only;
see [`13-secret-management.md`](13-secret-management.md).

## Removed: `BW_ID` build-time mechanism

The previous `BW_ID` build-time BuildKit-secret mechanism (mounting a
Bitwarden item-ID file at `/run/secrets/bitwarden_id`) has been
**removed**. `chezmoi apply` now runs at runtime with `BW_SESSION` set in
the interactive shell; the image is secret-free. See
[`13-secret-management.md`](13-secret-management.md) §5 and the Makefile
(`BW_ID` / `BW_SECRET` skeleton deleted).

## Related

- General pre-required envs (host side, not build): [`11-pre-required-env-values.md`](11-pre-required-env-values.md)
- Container rules: [`20-container-rules.md`](20-container-rules.md)
- Build flow / stage invariants: [`21-container-build-flow.md`](21-container-build-flow.md)
- Make target contract: [`03-makefile.md`](03-makefile.md)
