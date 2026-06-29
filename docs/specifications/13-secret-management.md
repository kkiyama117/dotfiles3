# 13 — Secret management

> Spec status: **DRAFT**. Normative spec for how secrets are sourced,
> authenticated, and consumed across host and container. Host-side
> pre-required envs live in [`11-pre-required-env-values.md`](11-pre-required-env-values.md);
> build-time envs in [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md);
> container rules in [`20-container-rules.md`](20-container-rules.md).

## §1 Purpose & scope

Define the single secret-management design for `dotfiles3`:

- which tool is the secret source (Bitwarden via `bw`),
- the two-tier principle (base key strict; other envs not picky),
- the authentication flow (API key → `BW_SESSION`),
- where chezmoi applies secrets (runtime, not build — the image stays
  secret-free).

Out of scope: secret rotation, CI/CD pipelines, Bitwarden Secrets Manager
(`bws`, a separate product).

## §2 The two-tier principle

Per the maintainer directive — *"base key of secret data must be managed
by bitwarden, but other envs are not picky"* — secrets split into two
tiers:

- **Tier 1 — base key (strict, Bitwarden-managed).** The credential that
  unlocks the vault: `BW_CLIENTID` / `BW_CLIENTSECRET` (personal API key)
  → `bw login --apikey` → `bw unlock` → `BW_SESSION`. This is the ONE
  strict secret the user must provide manually. Every other sensitive
  value is a vault item retrieved via chezmoi templates, never stored in
  the repo / `.env` / image.
- **Tier 2 — non-secret env (not picky).** `USERNAME`, `HOST_UID` /
  `HOST_GID`, `JOBS`, etc. These carry no secret value and live in
  `.env` (gitignored) or chezmoi data. Plain text is acceptable.

## §3 Secret source: Bitwarden CLI (`bw`)

- The chosen CLI is **`bw`** (package `bitwarden-cli`, Arch `Extra` repo).
  `rbw` is **not** used. This resolves the "CLI choice not yet fixed" note
  previously in [`11`](11-pre-required-env-values.md).
- `bw` is installed in **Layer 1** (see
  [`02-installed-programs.md`](02-installed-programs.md) and
  `dependencies/packages.toml`) so it is available to `chezmoi apply`.
- chezmoi's **native** Bitwarden template functions are the ONLY
  integration path; no shelling out to `bw` from templates:
  - `bitwarden "item" "<name-or-id>"` → `.login.username`, `.login.password`, `.notes`, …
  - `bitwardenFields "item" "<id>"` → custom fields (`.token.value`, …)
  - `bitwardenAttachment` / `bitwardenAttachmentByRef` → attachments (e.g. SSH keys)
- `bitwardenSecrets` (Bitwarden Secrets Manager / `bws`) is a **separate
  product** and is not used here.

## §4 Authentication flow (runtime, non-interactive)

1. Set `BW_CLIENTID` and `BW_CLIENTSECRET` in the shell env (host or
   container session). **Never** in `.env`, the repo, or the image.
2. `bw login --apikey` (reads the env vars; non-interactive).
3. `bw unlock --raw` → captures the session key; `export BW_SESSION="$(bw unlock --raw)"`.
4. `chezmoi apply` → chezmoi calls `bw get` inside templates; results
   are cached for the duration of the run.
5. On finish: `bw lock` (or `bw logout`) invalidates `BW_SESSION`.

`make bw-login` automates steps 2–3; `make apply` runs `chezmoi apply`
assuming `BW_SESSION` is set (see [`08-automations.md`](08-automations.md)).

## §5 Where secrets are applied: runtime, not build

- `chezmoi apply` runs at **container start / interactive session**,
  **never** during `make build`.
- The built image (`no-config-base` stage) is **secret-free**: no
  `BW_SESSION`, no rendered secret files baked into layers.
- Rationale: baking rendered secrets into image layers leaks them to
  anyone who can pull the image. Runtime application confines secrets to
  the bind-mounted `$HOME` only.
- This resolves [`20`](20-container-rules.md) Q1 (disposable vs
  persistent → runtime apply) and the "where `chezmoi apply` runs" part
  of [`21`](21-container-build-flow.md) Q1.

## §6 Invariants

- **I-S1:** `bw` (`bitwarden-cli`) is the sole secret CLI. `rbw` is not
  used. (Install list: [`02`](02-installed-programs.md).)
- **I-S2:** The base key = `BW_CLIENTID` / `BW_CLIENTSECRET` +
  `BW_SESSION`. It is the ONLY secret the user must provide manually;
  all other secrets are vault items retrieved via chezmoi templates.
- **I-S3:** Secrets are never committed to the repo, never written to
  `.env`, never baked into image layers. (Refines
  [`20`](20-container-rules.md) I4: build-time = BuildKit
  `--mount=type=secret`; runtime = `BW_SESSION` in the interactive shell
  only.)
- **I-S4:** `chezmoi apply` runs at runtime only. The built image
  contains no rendered secret.
- **I-S5:** chezmoi templates consume secrets ONLY via the `bitwarden*`
  template functions. No `bw` subprocess calls from templates.

## §7 Cross-references

- [`11`](11-pre-required-env-values.md) — host pre-required envs (`BW_CLIENTID`, etc.)
- [`20`](20-container-rules.md) I4 — build-time secret transport; runtime `BW_SESSION`
- [`21`](21-container-build-flow.md) — Layer 2 `no-config-base` stays secret-free (no build-time apply)
- [`22`](22-container-build-pre-required-envs.md) — `BW_ID` build-time mechanism removed (runtime auth instead)
- [`08`](08-automations.md) — `make bw-login` / `make apply` automations

## §8 Open questions

- **Q1:** The exact Bitwarden item IDs consumed by templates must be
  enumerated in [`11`](11-pre-required-env-values.md) once the host secret
  survey is reconciled with the chezmoi source tree.
- **Q2:** Whether `make bw-login` persists `BW_SESSION` in a keyring
  (chezmoi `secret keyring`) or requires re-auth each session. Deferred.