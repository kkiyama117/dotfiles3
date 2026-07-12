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

- **Tier 1 — base key (strict, Bitwarden-managed).** The credentials
  that authenticate and unlock the vault, transported as **podman
  secrets** (not env / `.env` / repo / image):
  `bw_clientid` / `bw_clientsecret` (personal API key → `bw login
  --apikey`) and `bw_password` (master password → `bw unlock`). These
  are the ONE strict secret set the user must provide (once, via
  `podman secret create`). `BW_SESSION` is derived at runtime from
  `bw unlock --passwordfile` and is process-local. Every other sensitive
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

**Template consumers (runtime Bitwarden-bound dotfiles):**

- `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl` — `bitwardenAttachment`
  for SSH key import (`.chezmoidata/ssh_keys.yaml`).
- `dot_config/zsh/rc/secrets.zsh.tmpl` — `bitwardenFields` / `bitwarden`
  for API provider env exports (`.chezmoidata/api_secrets.yaml`).

## §4 Authentication flow (runtime, automatic)

The runtime entrypoint authenticates `bw` automatically when the three
podman secrets are mounted by `make up`. No manual `export BW_SESSION`
is required.

1. `make up` mounts `bw_clientid` / `bw_clientsecret` / `bw_password`
   (each only if it exists — see the Makefile `BW_SECRETS` variable).
   Podman presents them as tmpfs files at `/run/secrets/<name>`; they
   are NOT written to image layers ([`20`](20-container-rules.md) I4).
2. The entrypoint exports `BW_CLIENTID` / `BW_CLIENTSECRET` (read from
   `/run/secrets/*`) **only inside its own process** — they are never
   on the image `Env` or `podman run -e` flags, so they are absent
   from `podman inspect`.
3. `bw login --check` gates `bw login --apikey` (idempotent: login
   state is ephemeral in the container home, so a fresh container
   re-logs in each `make up`; a still-logged-in state is a no-op).
   Then `bw sync` refreshes the local vault data.
4. `bw unlock --passwordfile /run/secrets/bw_password --raw` is retried
   (a few times) because it can **transiently return an empty session**
   if the vault data is not yet local / the server is not ready. The
   master password is read straight from the secret file by `bw` and
   **never enters an environment variable** (I-BW2). If the session is
   still empty after retries, the entrypoint **exits non-zero (loud
   failure)** rather than silently running with no session (which would
   leave `bitwarden*` templates unresolvable without warning).
5. `chezmoi apply` runs with `BW_SESSION` in the entrypoint process, so
   `bitwarden*` templates resolve.
6. Before `exec "$@"`, the entrypoint **scrubs** `BW_CLIENTID` /
   `BW_CLIENTSECRET` / `BW_SESSION` from its environment (`unset`),
   **unconditionally within the auth-ran path** (gated on the secret
   file, NOT on `BW_SESSION` being non-empty, so a transient empty
   session still gets the client pair scrubbed). This prevents the
   credentials from riding into PID 1 (e.g. `sleep infinity`) via
   `/proc/1/environ` for the container's lifetime. `BW_SESSION` was
   only needed for the apply (now done).

If `/run/secrets/bw_password` is absent (no secrets mounted), the auth
block is skipped and `chezmoi apply` runs without `BW_SESSION`
(no-secret startup; a `bitwarden*` template then fails loudly — the
operator's signal to mount the secrets).

One-time operator setup (host; see
[`11-pre-required-env-values.md`](11-pre-required-env-values.md)):

    printf '%s' "$BW_CLIENTID"     | podman secret create bw_clientid -
    printf '%s' "$BW_CLIENTSECRET"  | podman secret create bw_clientsecret -
    printf '%s' "$BW_MASTERPASS"    | podman secret create bw_password -

Rotate by `podman secret rm <name>` then the create above. A `make
bw-secrets` helper is a follow-up (not implemented).

## §5 — Apply phases

Chezmoi apply runs in two phases:

1. **Build-time pre-pass** (Containerfile Stage 2 `build-prepass`). Runs
   against a scratch destination (`/tmp/build-home`) with `build_mode = true`
   in the chezmoi data. Renders ENV-bearing dotfiles only; Bitwarden-bound
   templates are guarded by the in-template `{{ if not .build_mode }}`
   convention (I-S6) so the build never consults `bw`. The scratch
   destination is deleted in Stage 5 (after the minimum `.zshenv` is
   copied out — see spec 20 I10 / spec 21 acceptance #5a) before the
   final image layer is finalized.

2. **Runtime apply** (`container/bind/layer_5_files/entrypoint.sh`). Runs
   against the real `$HOME` against the host-bind chezmoi source at
   `~/.local/share/chezmoi`. Authenticates `bw` automatically from the
   mounted podman secrets (§4), then resolves Bitwarden templates with
   `BW_SESSION` in the entrypoint process, and scrubs the BW_* env
   before `exec "$@"`. The image layers stay secret-free because the
   credentials live only in tmpfs `/run/secrets` and the entrypoint
   process env (never in image `Env`, never in `podman inspect`, and
   scrubbed from PID 1 before exec).

## §5a Phase-placement convention (dotfiles ↔ build / runtime)

The `build_mode` data flag is the single switch. It is set in
`~/.config/chezmoi/chezmoi.toml`, which is rendered from a single
dotfiles-managed config template `.chezmoi.toml.tmpl` (chezmoi source
root) by `chezmoi execute-template --init`: the Containerfile Stage 2
build-prepass renders it with `BUILD_MODE=true` (inline in the `RUN`, not
`ENV`), the runtime entrypoint renders it with `BUILD_MODE` unset
(`false`). The template cannot read `[data]` it is generating, so
`build_mode` is read from the `BUILD_MODE` env var
(`{{ env "BUILD_MODE" | default "false" }}`). For any dotfile, ask:
**does Stage 3 need to source this to get the toolchain ENV?**

- **Yes → build-time block.** Wrap in `{{ if .build_mode }}…{{ end }}`
  (build-only); content MUST be secret-free (I-S4). Currently the
  `.zshenv` toolchain HOMEs/PATH block; the runtime counterpart is
  `.zshrc`. (Wiring the actual `{{ if .build_mode }}` guard into
  `.zshenv` is a pre-existing follow-up, not required here.)
- **No → runtime-only (default).** Every `bitwarden*` /
  `bitwardenFields` / `bitwardenAttachment` call MUST be wrapped in
  `{{ if not .build_mode }}…{{ end }}` inline — the in-template guard
  convention of I-S6 (self-contained, no separate ignore list).
- **Plain non-secret dotfiles** without a guard render in both phases;
  the scratch copy is discarded in Stage 5, so this is harmless.

**Safety property:** a forgotten `{{ if not .build_mode }}` guard
around a `bitwarden*` call makes the Stage 2 `chezmoi apply`
(`build_mode = true`) evaluate that call → invoke `bw` unauthenticated
→ **the build fails loudly**. A missing guard is a build error, not a
silent secret leak. This is what makes I-S4 / [`20`](20-container-rules.md)
I4 self-enforcing.

## §6 Invariants

- **I-S1:** `bw` (`bitwarden-cli`) is the sole secret CLI. `rbw` is not
  used. (Install list: [`02`](02-installed-programs.md).)
- **I-S2:** The base key = `BW_CLIENTID` / `BW_CLIENTSECRET` (login) +
  `BW_PASSWORD` (unlock), transported as podman secrets `bw_clientid` /
  `bw_clientsecret` / `bw_password` (created once via `podman secret
  create`). `BW_SESSION` is derived at runtime from `bw unlock
  --passwordfile` and is process-local (scrubbed before `exec`). This is
  the ONLY secret set the user must provide; all other secrets are vault
  items retrieved via chezmoi templates.
- **I-S3:** Secrets are never committed to the repo, never written to
  `.env`, never baked into image layers. (Refines
  [`20`](20-container-rules.md) I4: build-time = the Stage 2 pre-pass
  runs `build_mode = true` and never consults `bw` — no secret
  transport at all; runtime = podman `--secret` → tmpfs
  `/run/secrets/*`, master password consumed via `bw unlock
  --passwordfile` so it never enters an env, client pair `export`-ed
  only in the entrypoint process then scrubbed before `exec`.)
- **I-S4:** Image layers contain no resolved secret. The build-time
  pre-pass runs `chezmoi apply` only with `build_mode = true`, which
  excludes every Bitwarden-bound template. The runtime apply renders
  secrets only into the running container's `$HOME`, never back into
  image layers.
- **I-S5:** chezmoi templates consume secrets ONLY via the `bitwarden*`
  template functions. No `bw` subprocess calls from templates.
- **I-S6:** Phase-conditional chezmoi content uses the **in-template guard**
  convention — `{{ if .build_mode }} ... {{ end }}` for build-only content
  and `{{ if not .build_mode }} ... {{ end }}` for runtime-only content —
  not `.chezmoiignore` template rules. (Exact whitespace-trimming dash
  placement is chosen per file so a guard never merges a trailing comment
  line with the following code.) First non-secret use: the toolchain HOMEs
  block, build-only in `.zshenv` and runtime-only in `~/.config/zsh/.zshrc`
  (see [`21`](21-container-build-flow.md) acceptance #6). Bitwarden-bound
  dotfiles, when introduced, follow the same `{{ if not .build_mode }}`
  guard so the build-time pre-pass never consults `bw`.

## §7 Cross-references

- [`11`](11-pre-required-env-values.md) — host pre-required envs (`BW_CLIENTID`, etc.)
- [`20`](20-container-rules.md) I4 — build-time secret transport; runtime `BW_SESSION`
- [`21`](21-container-build-flow.md) — Stage 2 `build-prepass` stays secret-free (build-time apply is `build_mode = true` pre-pass; no secret baked into layers)
- [`22`](22-container-build-pre-required-envs.md) — `BW_ID` build-time mechanism removed (runtime auth instead)
- [`08`](08-automations.md) — `make apply` (planned) automation

## §8 Open questions

- **Q1:** Remaining host secret survey entries must be reconciled in
  [`11`](11-pre-required-env-values.md). API provider and SSH import
  consumers are enumerated; operator must fill Bitwarden item IDs in
  `.chezmoidata/api_secrets.yaml` before runtime apply succeeds.
- **Q2: Resolved.** `BW_SESSION` is **not** persisted in a keyring. It is
  ephemeral: re-derived each `make up` via `bw unlock --passwordfile
  /run/secrets/bw_password --raw`, used only for the entrypoint's
  `chezmoi apply`, then scrubbed before `exec "$@"`. The podman secrets
  (client id/secret/master password) persist in the podman store across
  restarts, so re-auth is automatic and non-interactive. Interactive
  re-unlock inside a `podman exec` shell, if ever needed, reuses the
  mounted secret: `bw unlock --passwordfile /run/secrets/bw_password
  --raw`.
- **Q3: Resolved (I-S6).** Phase-conditional chezmoi content uses the
  in-template `{{ if (not) .build_mode }}` guard convention, not
  `.chezmoiignore` template rules. First use is the non-secret toolchain
  HOMEs block (build-only `.zshenv` / runtime-only `~/.config/zsh/.zshrc`);
  Bitwarden-bound dotfiles will follow the same `{{ if not .build_mode }}`
  guard so the build-time pre-pass stays secret-free. See invariant I-S6
  and [`21`](21-container-build-flow.md) acceptance #6.
