# Pre-required Environment Values

> Spec status: **DRAFT** — this is the SoT for "secrets and config the user
> must have before `chezmoi apply` or `make build` will succeed". The
> concrete secret-name list lives in this file; container-build-specific
> envs are split into [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).

## Required toolchain

| Tool | Purpose | Where used |
|---|---|---|
| `chezmoi` | applies dotfiles | host + container |
| Bitwarden CLI (`bw` or `rbw`) | secret source used by chezmoi templates | host + container |
| `git`     | chezmoi source operations | host + container |

> CLI choice is **not yet fixed**. Candidates: `bw` (official, supports
> `--apikey` / personal API key flow) and `rbw` (Rust client). The picked
> CLI must be the one chezmoi templates call, and must be the one
> referenced from `02-installed-programs.md` and the container Layer 1
> install list.

## Required accounts / vault state

- **Bitwarden account** — required as the only secret source. Before any
  chezmoi template that calls `bitwarden`/`bitwardenSecrets` functions
  will render, the chosen CLI (`bw` or `rbw`) must be authenticated and
  unlocked on the host. See [`../references/chezmoi_reference.md`](../references/chezmoi_reference.md).
- The Bitwarden item IDs consumed by templates are listed in this file
  under [§ Bitwarden items](#bitwarden-items). Do not embed actual secret
  values in this repository; only item IDs are public.

## Bitwarden items

> TODO: enumerate the item ID → consumer mapping. Until the host secret
> survey under `host_config_list.md` is reconciled with `dot_zshenv` and
> `dot_config/rbw/`, this stays a TBD list. Acceptance criterion: every
> chezmoi template invocation of `bitwarden*` resolves to one of the
> entries in this table.

| Item ID env / template var | Consumer | Required at | Notes |
|---|---|---|---|
| _(TBD)_ | _(TBD)_ | apply / build | _(TBD)_ |

## Local environment variables

| Variable | Required | Default | Used by |
|---|---|---|---|
| `XDG_CONFIG_HOME` | no | `~/.config` | chezmoi, Bitwarden CLI |
| `XDG_STATE_HOME`  | no | `~/.local/state` | Bitwarden CLI session cache |

## Container-build envs

Container-build envs (`USERNAME`, `HOST_UID`, `HOST_GID`, `BW_ID`, `JOBS`) and
the `.env` contract are the canonical responsibility of
[`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
This spec lists them for completeness but does not duplicate the contract.

Of these, **`USERNAME`** is the only one a user must set by hand before
`make build` / `make up` will run; the rest are auto-resolved or have safe
defaults. See [`22-container-build-pre-required-envs.md` § `.env` contract](22-container-build-pre-required-envs.md#env-contract).
