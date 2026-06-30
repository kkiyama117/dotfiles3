# Bitwarden auto-auth at container startup (podman secret) — Design

**Status:** Approved
**Date opened:** 2026-06-30
**Issue:** [`docs/issues/2026-06-30-bitwarden-auto-auth.md`](../../issues/2026-06-30-bitwarden-auto-auth.md)
**Author:** kiyama
**Review required:** letter A + B + D (touches secret / auth — 09-review §2.2) — self-reviewed in §10; user-approved 2026-06-30.
**Decisions:** Q1 = out of scope (follow-up); Q2 = (b) Makefile-conditional `--secret` (preserves S4); Q3 = Shape A confirmed.

## §1 Context & success criteria

### Context

- `bw` (`bitwarden-cli`) is installed at Layer 1. spec 13 §5 defines the
  auth flow but leaves it manual: the operator `export BW_SESSION` before
  `make up`, and `make up` forwards `-e BW_SESSION=$BW_SESSION`.
- The build-time `chezmoi apply` (Stage 2, `build_mode = true`) never
  calls `bw` (every `bitwarden*` call is guarded by `{{ if not
  .build_mode }}`, spec 13 I-S4/I-S6), so the image is secret-free
  (spec 20 I4). **This work touches the runtime entrypoint only.**
- Verified on host: Podman 5.8.3 (`podman secret create/exists/ls/rm` +
  `podman run --secret`); `bw unlock --passwordfile <path> --raw`;
  `bw login --apikey` (reads `BW_CLIENTID`/`BW_CLIENTSECRET` env).

### Success criteria

- **S1:** `make up` (with the three podman secrets mounted) authenticates
  `bw` and runs `chezmoi apply` with `BW_SESSION` set — no manual
  `export` by the operator.
- **S2:** The master password never enters any environment variable
  (read via `--passwordfile` from tmpfs `/run/secrets/bw_password`).
- **S3:** The image remains secret-free (spec 20 I4): credentials live
  only in the running container's `/run/secrets` tmpfs, never in image
  layers; `BW_CLIENTID`/`BW_CLIENTSECRET` are `export`-ed only inside the
  entrypoint process (absent from image `Env` and `podman run -e` flags,
  hence absent from `podman inspect`).
- **S4:** `make up` without the secrets still starts and runs
  `chezmoi apply` (skipping `bw` auth), preserving the current behavior.
- **S5:** `bw login` is idempotent across restarts (`bw login --check`
  gates re-login; login state is ephemeral in the container home).
- **S6:** The Stage 2 build-prepass is unmodified and the build remains
  secret-free; a future unguarded `bitwarden*` call fails the build
  loudly (no silent leak).
- **S7:** spec 13 §5 is rewritten to the automatic flow and gains a
  "phase-placement convention" section; specs 11/20/21/22 are updated
  consistently.

## §2 Alternatives considered

- **A1 — Environment variables (`-e BW_CLIENTID` / `BW_PASSWORD`).**
  Rejected: env vars are visible in `podman inspect` and `/proc/*/environ`,
  so the master password would leak. Also require per-shell `export`.
- **A2 — Podman secrets, all three as `type=env`.** Rejected for the
  master password: `type=env` injects it into the container env
  (`podman inspect`-visible). Keeps the client pair as env too. Weaker
  than the chosen design for the password.
- **A3 — Podman secrets, all three as files (`/run/secrets/<name>`), the
  entrypoint `export`s the client pair into its own process env and uses
  `--passwordfile` for the password (chosen).** The master password
  never enters any env; the client pair is env only inside the
  entrypoint (not declared on the image / `podman run -e`, so not in
  `podman inspect`); secrets are created once and persist in the podman
  store. Best secrecy + best UX.
- **A4 — `make apply` / `make auth` dedicated target instead of the
  entrypoint.** Rejected for now (YAGNI): re-applying after a dotfiles
  edit is `make down && make up` (toolchain volumes persist, apply is
  cheap). A separate target is an easy follow-up if iterative apply
  becomes friction.
- **A5 — Persist `bw` login state in a named volume so only `unlock`
  runs each start.** Rejected: saves a cheap network call (login) at the
  cost of a new volume + secret-state-at-rest. `bw unlock` is needed
  every start regardless (BW_SESSION is ephemeral by design). Not worth
  the volume.

## §3 Architecture / Invariants

### Credential transport

- Three podman secrets, created once by the operator (docs in spec 11):
  `bw_clientid`, `bw_clientsecret`, `bw_password`. `podman secret create
  <name> <file|->` stores them in the podman secret store (persists
  across container restarts; not in the image).
- `make up` mounts them: `podman run --secret bw_clientid --secret
  bw_clientsecret --secret bw_password …`. Podman mounts each as a tmpfs
  file at `/run/secrets/<name>` (default `type=mount`). They are NOT
  written to image layers.

### Entrypoint flow (`container/bind/layer_5_files/entrypoint.sh`)

```
# (after the existing build_mode=false chezmoi.toml render)

if [ -f /run/secrets/bw_password ]; then
  export BW_CLIENTID="$(cat /run/secrets/bw_clientid)"
  export BW_CLIENTSECRET="$(cat /run/secrets/bw_clientsecret)"
  if ! bw login --check >/dev/null 2>&1; then
    bw login --apikey
  fi
  bw sync >/dev/null 2>&1 || true
  for _ in 1 2 3; do
    BW_SESSION="$(bw unlock --passwordfile /run/secrets/bw_password --raw 2>/dev/null || true)"
    if [ -n "$BW_SESSION" ]; then break; fi
    sleep 2
  done
  if [ -z "$BW_SESSION" ]; then
    echo "entrypoint: bw unlock returned an empty session after retries." >&2
    exit 1
  fi
  export BW_SESSION
fi

chezmoi apply --no-tty --force

if [ -f /run/secrets/bw_password ]; then
  unset BW_CLIENTID BW_CLIENTSECRET BW_SESSION
fi

exec "$@"
```

- `BW_CLIENTID`/`BW_CLIENTSECRET` are `export`-ed only in this process
  (not on the image / `-e` flags → not in `podman inspect`).
- The master password is read by `bw` directly from
  `/run/secrets/bw_password` via `--passwordfile`; it is never `cat`-ed
  into any shell variable or env.
- `bw login --check` makes the login step idempotent; `bw sync` refreshes
  the local vault data before unlock.
- `bw unlock --passwordfile --raw` is **retried** because it can
  transiently return an empty session (vault data not yet local / server
  not ready). An empty session after retries is a **loud failure**
  (exit 1), not a silent degraded run.
- The scrub before `exec` is **unconditional within the auth-ran path**
  (gated on the secret file, not on `BW_SESSION` being non-empty), so a
  transient empty session still gets the client pair scrubbed and no BW_*
  rides into PID 1 (`/proc/1/environ`).
- `BW_SESSION` exists only for the `chezmoi apply` call; after `exec
  "$@"` it is gone (Shape A — interactive `podman exec` shells do not
  inherit it; see §6 for the rationale).

### New / updated invariants

- **I-BW1:** The image is secret-free. No Bitwarden credential is
  written to any image layer. All three credentials travel as podman
  secrets → tmpfs `/run/secrets/*` at runtime only (strengthens spec 20
  I4: transport moves from env to tmpfs files).
- **I-BW2:** The master password (`bw_password`) is consumed **only** via
  `bw unlock --passwordfile /run/secrets/bw_password`. It never appears
  in any environment variable, shell variable, or file written by the
  entrypoint.
- **I-BW3:** `BW_CLIENTID` / `BW_CLIENTSECRET` are `export`-ed **only**
  inside the entrypoint process (read from `/run/secrets/*`). They are
  never declared on the image `Env` or on `podman run -e` flags, so they
  are absent from `podman inspect`.
- **I-BW4:** The entrypoint auth block is **optional and tolerant**: if
  `/run/secrets/bw_password` is absent, the block is skipped and
  `chezmoi apply` still runs (preserves S4). If the secret IS mounted
  but `bw unlock` returns an empty session after retries, the entrypoint
  **exits non-zero (loud failure)** rather than silently running with no
  session. If a `bitwarden*` template is evaluated with no valid
  `BW_SESSION` (a BW-bound dotfile exists but auth was skipped/failed),
  `chezmoi apply` fails loudly — the operator's signal to mount/fix the
  secrets. The scrub before `exec` is unconditional within the auth-ran
  path, so no `BW_*` rides into PID 1 even on a transient empty session.
- **I-BW5 (phase placement, restates spec 13 I-S6 normatively):** Every
  `bitwarden*` / `bitwardenFields` / `bitwardenAttachment` call MUST be
  wrapped in `{{ if not .build_mode }}…{{ end }}` (inline) so the build
  never evaluates it. The build renders only the toolchain ENV block
  (`.zshenv` HOMEs/PATH). A forgotten guard makes the build-prepass
  `chezmoi apply` invoke `bw` unauthenticated and **fail the build** — a
  missing guard is a loud build error, not a silent leak.

### Phase-placement convention (for future dotfiles)

The `build_mode` data flag is the single switch. For any dotfile, ask:
**"Does Stage 3 need to source this to get toolchain ENV?"**

- **Yes → build-time block.** Wrap in `{{ if .build_mode }}…{{ end }}`
  (build-only); content MUST be secret-free (I-S4). Currently the
  `.zshenv` toolchain HOMEs/PATH block. The runtime counterpart is
  `.zshrc` (the structure the existing `.zshrc` header comment describes;
  wiring the actual `{{ if .build_mode }}` guard into `.zshenv` is a
  pre-existing follow-up, not introduced here — see Q1).
- **No → runtime-only (default).** Every `bitwarden*` call MUST be
  inline-guarded with `{{ if not .build_mode }}…{{ end }}` (primary,
  self-contained mechanism). A `.chezmoiignore` entry
  `{{ if .build_mode }}<file>{{ end }}` is the secondary mechanism for
  wholesale skipping (large files / files that don't template well) — the
  exception, not the default.
- **Plain non-secret dotfiles** without a guard render in both phases;
  the scratch copy is discarded in Stage 5, so this is harmless. Only
  add a `.chezmoiignore` build-gate when a whole file should be skipped
  at build.

## §4 Scope / staging breakdown

1. **entrypoint** — add the optional `bw` auth block (login-if-needed +
   `--passwordfile` unlock → `BW_SESSION`) before `chezmoi apply`.
2. **Makefile** — `make up`: remove `-e BW_SESSION=$BW_SESSION`, add
   `--secret bw_clientid --secret bw_clientsecret --secret bw_password`.
3. **specs** — rewrite spec 13 §5 (auto flow + phase-placement
   convention; update I-S2/I-S3 transport); spec 20 I4 (tmpfs transport);
   spec 22 (runtime podman-secret; build envs unchanged); spec 11 (host
   `podman secret create` setup); spec 21 (runtime entrypoint note).
4. **No build-time change** — Stage 2 untouched (S6).
5. **smoke gate** — create the three secrets, `make build && make up`,
   verify `chezmoi apply` runs with `BW_SESSION` set and the password is
   absent from env / inspect; also verify the no-secrets path still
   starts.

## §5 `entrypoint.sh` change (Layer 5)

Insert the auth block between the existing `chezmoi.toml`
(`build_mode = false`) render and `chezmoi apply`, and a scrub block
between `chezmoi apply` and `exec "$@"`. Both blocks are guarded by
`[ -f /run/secrets/bw_password ]` so absence is a no-op (I-BW4). No
change to the bind-check or `exec "$@"` tail. Under `set -euo pipefail`:
`bw login --check` is allowed to fail (gated by `if`); `bw sync` is
best-effort (`|| true`); `bw unlock` is wrapped in `$(... || true)` so
a non-zero unlock does not abort the retry loop; an **empty session
after retries** triggers an explicit `exit 1` (loud failure — the
password secret is present but unlock could not produce a session). The
scrub is unconditional within the auth-ran path so no `BW_*` rides into
PID 1 via `exec`. See §3 for the full code block.

## §6 `make up` change

```make
up: _require_username
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		--secret bw_clientid \
		--secret bw_clientsecret \
		--secret bw_password \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity
```

The `-e BW_SESSION=$$BW_SESSION` line is removed: `BW_SESSION` is now
derived inside the entrypoint. `podman run --secret <name>` errors if the
named secret does not exist, which would break S4 ("works without
secrets"). **Decision (Q2 = (b)):** the Makefile mounts each secret only
when it exists, via a `podman secret exists` probe, so `make up` without
the secrets still starts and the entrypoint skips auth (I-BW4):

```make
# Mount a podman secret only if it exists (preserves no-secret startup).
secret-opt = $(shell podman secret exists $(1) && printf -- '--secret %s' $(1))

up: _require_username
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		$(call secret-opt,bw_clientid) \
		$(call secret-opt,bw_clientsecret) \
		$(call secret-opt,bw_password) \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity
```

If all three are absent the `--secret` lines expand to empty and the
entrypoint's `[ -f /run/secrets/bw_password ]` guard is a no-op (S4).

## §7 Operator setup (one-time; documented in spec 11/13)

```
printf '%s' "$BW_CLIENTID"     | podman secret create bw_clientid -
printf '%s' "$BW_CLIENTSECRET"  | podman secret create bw_clientsecret -
printf '%s' "$BW_MASTERPASS"    | podman secret create bw_password -
podman secret ls                 # verify
```

Secrets persist in the podman store; re-creating is `podman secret rm
<name>` then the create above. Rotate by `rm` + `create`. A `make
bw-secrets` helper is out of scope (follow-up).

## §8 Spec edits

- **spec 13 §5** — rewrite the flow from manual to entrypoint-automatic
  (podman secret → `/run/secrets` → `bw login --apikey` / `bw unlock
  --passwordfile --raw` → `BW_SESSION` → `chezmoi apply`). Update I-S2
  (base key now incl. `BW_PASSWORD`) and I-S3 (transport: env → tmpfs
  `/run/secrets`, master password via `--passwordfile` never env). Add a
  **"Phase-placement convention"** section restating I-BW5. Note the
  Shape-A choice (BW_SESSION is entrypoint-process-local).
- **spec 20 I4** — note that runtime secret transport is now tmpfs
  `/run/secrets` (podman secret), stronger than the previous env path.
- **spec 22** — runtime section: add the three podman secrets (build-time
  envs unchanged).
- **spec 11** — add the one-time `podman secret create` setup and the
  Bitwarden account prereq wording.
- **spec 21** — runtime stage entrypoint note: the auth block runs
  before `chezmoi apply`.

## §9 Open questions (resolved at design approval, 2026-06-30)

- **Q1 — Resolved (out of scope):** This work does NOT wire the actual
  `{{ if .build_mode }}` guard into `.zshenv` (the structure the
  `.zshrc` header describes but that is not yet implemented). The
  existing "`.zshenv` renders in both phases, XDG-relative paths resolve
  in both" works and is a pre-existing TODO, tracked as a follow-up.
  This work adds only the runtime auth + the phase-placement
  *convention* (spec 13); it does not refactor existing templates.
- **Q2 — Resolved ((b)):** `make up` mounts each secret only when it
  exists (`$(call secret-opt,<name>)` via `podman secret exists`), so the
  no-secrets path still starts and the entrypoint skips auth (I-BW4 /
  S4 preserved). Acceptance criterion #5 (issue) is therefore unchanged.
- **Q3 — Resolved (Shape A):** `BW_SESSION` is entrypoint-process-local
  for the duration of `chezmoi apply`; it is NOT propagated to later
  `podman exec` interactive shells. Interactive re-unlock, if needed, is
  `bw unlock --passwordfile /run/secrets/bw_password --raw` (the secret
  stays mounted for the container's lifetime). Endorsed by the user.

## §10 Self-review (letters A / B / D; user-approved 2026-06-30)

- **A (architecture):** Stage 2 untouched; runtime change is additive
  and optional (I-BW4); the single switch is `build_mode`, already
  established. No new stages. Consistent with spec 13/20/21.
- **B (security):** Master password never in env (I-BW2); client pair
  env-only inside entrypoint, not in `podman inspect` (I-BW3); image
  secret-free (I-BW1); tmpfs `/run/secrets` not layer-bound; loud-fail
  on a forgotten `bitwarden*` guard (I-BW5). Residual: `BW_SESSION` is
  a session key in the entrypoint process env during apply — acceptable
  (it is a derived, revocable session token, not a base credential, and
  is process-local). Open: Q2 (no-secrets handling) — must not weaken
  I-BW4.
- **D (consistency):** spec 13 §5 rewrite + I-S2/I-S3 update + new
  phase-placement section; specs 11/20/21/22 cross-references updated in
  the same change. Naming `bitwarden-auto-auth` flows issue → design →
  plan → result-log (00-doc-mgmt §3.1). Q1/Q2/Q3 resolved at approval
  (§9); Q2=(b) keeps S4 consistent with issue acceptance #5 (no issue
  edit needed).