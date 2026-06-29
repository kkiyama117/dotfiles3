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

Steps 2–3 are run manually in the shell (`bw login --apikey`, then
`bw unlock --raw`). `make apply` (planned) will run `chezmoi apply`
assuming `BW_SESSION` is set (see
[`08-automations.md`](08-automations.md)).

## §5 — Apply phases

Chezmoi apply runs in two phases:

1. **Build-time pre-pass** (Containerfile Stage 2 `build-prepass`). Runs
   against a scratch destination (`/tmp/build-home`) with `build_mode = true`
   in the chezmoi data. Renders ENV-bearing dotfiles only; Bitwarden-bound
   templates are guarded by `{{- if not .build_mode -}}` (or excluded via
   `.chezmoiignore` templates) so the build never consults `bw`. The
   scratch destination is deleted in Stage 4 before the final image layer
   is finalized.

2. **Runtime apply** (`container/bind/layer_4_files/entrypoint.sh`). Runs
   against the real `$HOME` against the host-bind chezmoi source at
   `~/.local/share/chezmoi`. Resolves Bitwarden templates when the
   operator exported `BW_SESSION` before `make up`. The image layers stay
   secret-free because `BW_SESSION` lives only in the running container's
   process environment.

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
- **I-S4:** Image layers contain no resolved secret. The build-time
  pre-pass runs `chezmoi apply` only with `build_mode = true`, which
  excludes every Bitwarden-bound template. The runtime apply renders
  secrets only into the running container's `$HOME`, never back into
  image layers.
- **I-S5:** chezmoi templates consume secrets ONLY via the `bitwarden*`
  template functions. No `bw` subprocess calls from templates.

## §7 Cross-references

- [`11`](11-pre-required-env-values.md) — host pre-required envs (`BW_CLIENTID`, etc.)
- [`20`](20-container-rules.md) I4 — build-time secret transport; runtime `BW_SESSION`
- [`21`](21-container-build-flow.md) — Stage 2 `build-prepass` stays secret-free (build-time apply is `build_mode = true` pre-pass; no secret baked into layers)
- [`22`](22-container-build-pre-required-envs.md) — `BW_ID` build-time mechanism removed (runtime auth instead)
- [`08`](08-automations.md) — `make apply` (planned) automation

## §8 Open questions

- **Q1:** The exact Bitwarden item IDs consumed by templates must be
  enumerated in [`11`](11-pre-required-env-values.md) once the host secret
  survey is reconciled with the chezmoi source tree.
- **Q2:** Whether `BW_SESSION` is persisted in a keyring (chezmoi
  `secret keyring`) or requires re-auth each session. Deferred.
- **Q3:** Build-mode template guard convention. Whether Bitwarden-bound
  templates should be guarded with `{{- if not .build_mode -}}` inside
  the template or excluded via `.chezmoiignore` template-based rules is
  unresolved. Pick one before introducing the first Bitwarden-bound
  dotfile. (Tracked: design doc §10 item 6.)
