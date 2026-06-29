# Pre-required Environment Values

> Spec status: **DRAFT** — this is the SoT for "secrets and config the user
> must have before `chezmoi apply` or `make build` will succeed". The
> concrete secret-name list lives in this file; container-build-specific
> envs are split into [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md);
> the secret-management design (two-tier principle, `bw` auth flow,
> runtime-not-build application) lives in [`13-secret-management.md`](13-secret-management.md).

## Required toolchain

| Tool | Purpose | Where used |
|---|---|---|
| `chezmoi` | applies dotfiles | host + container |
| Bitwarden CLI (`bw`) | secret source used by chezmoi templates | host + container |
| `git`     | chezmoi source operations | host + container |

> The CLI is **`bw`** (package `bitwarden-cli`, Arch `Extra`), installed
> in container Layer 1 (see [`02-installed-programs.md`](02-installed-programs.md)).
> `rbw` is not used. The secret-management design — two-tier principle,
> API-key auth flow, runtime (not build) application — lives in
> [`13-secret-management.md`](13-secret-management.md).

## Required accounts / vault state

- **Bitwarden account** — required as the only secret source. Before any
  chezmoi template that calls `bitwarden` functions will render, `bw`
  must be authenticated (`bw login --apikey`) and unlocked (`bw unlock`)
  with `BW_SESSION` set in the shell env. See
  [`13-secret-management.md`](13-secret-management.md) §4 for the full
  auth flow.
- The Bitwarden item IDs consumed by templates are listed in this file
  under [§ Bitwarden items](#bitwarden-items). Do not embed actual secret
  values in this repository; only item IDs are public.

## Bitwarden items

> TODO: enumerate the item ID → consumer mapping. Until the host secret
> survey under `host_config_list.md` is reconciled with `dot_zshenv`, this
> stays a TBD list. Acceptance criterion: every chezmoi template invocation
> of `bitwarden*` resolves to one of the entries in this table. See
> [`13-secret-management.md`](13-secret-management.md) §3 for the template
> functions.

| Item ID env / template var | Consumer | Required at | Notes |
|---|---|---|---|
| _(TBD)_ | _(TBD)_ | apply / build | _(TBD)_ |

## Local environment variables

| Variable | Required | Default | Used by |
|---|---|---|---|
| `XDG_CONFIG_HOME` | no | `~/.config` | chezmoi, Bitwarden CLI |
| `XDG_STATE_HOME`  | no | `~/.local/state` | Bitwarden CLI session cache |
| `BW_CLIENTID`     | yes (apply) | — | `bw login --apikey` (base key; Tier 1) |
| `BW_CLIENTSECRET` | yes (apply) | — | `bw login --apikey` (base key; Tier 1) |
| `BW_SESSION`      | yes (apply) | — | `bw get` from chezmoi templates |

> The `BW_*` variables are **runtime shell env only** — never in `.env`,
> the repo, or the image. See [`13`](13-secret-management.md) §2 (two-tier)
> and §6 I-S2/I-S3.

## Container-build envs

Container-build envs (`USERNAME`, `HOST_UID`, `HOST_GID`, `JOBS`) and
the `.env` contract are the canonical responsibility of
[`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
This spec lists them for completeness but does not duplicate the contract.

Of these, **`USERNAME`** is the only one a user must set by hand before
`make build` / `make up` will run; the rest are auto-resolved or have safe
defaults. See [`22-container-build-pre-required-envs.md` § `.env` contract](22-container-build-pre-required-envs.md#env-contract).
