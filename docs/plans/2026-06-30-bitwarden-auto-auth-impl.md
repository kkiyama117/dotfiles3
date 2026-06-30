# Bitwarden auto-auth at container startup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** pending
**Spec:** [`docs/specifications/implementations/2026-06-30-bitwarden-auto-auth-design.md`](../specifications/implementations/2026-06-30-bitwarden-auto-auth-design.md) (Approved)
**Parent issue:** [`docs/issues/2026-06-30-bitwarden-auto-auth.md`](../issues/2026-06-30-bitwarden-auto-auth.md)
**Review trail:** design self-reviewed letters A/B/D (§10); user-approved 2026-06-30. Security-touching (09-review §2.2 → A+B+D required); inline environment, so self-review + user review stand in for per-letter passes.

**Goal:** Automate Bitwarden (`bw`) authentication at container startup via podman secrets so `make up` resolves `bitwarden*` chezmoi templates without any manual `export BW_SESSION`, while keeping the image secret-free and the master password out of any environment variable.

**Architecture:** Three podman secrets (`bw_clientid`/`bw_clientsecret`/`bw_password`) are mounted into the container as tmpfs `/run/secrets/*` by `make up` (each only if it exists, preserving no-secret startup). The runtime entrypoint reads the client pair into its own process env, runs `bw login --apikey` if not already logged in, then `bw unlock --passwordfile /run/secrets/bw_password --raw` → `BW_SESSION`, and runs `chezmoi apply`. The master password never enters env. Stage 2 build-prepass is untouched (it never calls `bw`).

**Tech Stack:** Podman 5.8.3 (`podman secret`, `podman run --secret`), `bitwarden-cli` (`bw`), bash entrypoint, GNU Make, chezmoi, Manjaro base image.

## Global Constraints

- **spec 20 I4** — the image is secret-free in both phases; no credential is written to any image layer (credentials travel as podman secrets → tmpfs `/run/secrets` at runtime only).
- **spec 20 I7** — `builder`/`${USERNAME}` is the only non-root account; `USER` set before any install. (Unchanged by this work; the entrypoint already runs as `${USERNAME}`.)
- **I-BW2** — the master password is consumed ONLY via `bw unlock --passwordfile /run/secrets/bw_password`; it never appears in any environment variable or shell variable.
- **I-BW3** — `BW_CLIENTID` / `BW_CLIENTSECRET` are `export`-ed only inside the entrypoint process; never on image `Env` or `podman run -e` flags (so absent from `podman inspect`).
- **I-BW4** — the entrypoint auth block is optional/tolerant: if `/run/secrets/bw_password` is absent, it is skipped and `chezmoi apply` still runs (preserves S4 / issue acceptance #5).
- **S6 / issue #9** — Stage 2 build-prepass is NOT modified; the build stays secret-free.
- **00-doc-mgmt** — relative repo paths only; no secrets in docs; `bitwarden-auto-auth` slug flows issue → design → plan → result-log; one commit per Phase.
- `USERNAME=kiyama` in `.env`; working directory `/data/dotfiles3`; branch from `develop`.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `Makefile` | modify | `make up`: drop `-e BW_SESSION`, add `BW_SECRETS` foreach var that mounts each `--secret` only if it exists |
| `container/bind/layer_5_files/entrypoint.sh` | modify | insert optional `bw` auth block (login-if-needed + `--passwordfile` unlock → `BW_SESSION`) before `chezmoi apply` |
| `docs/specifications/13-secret-management.md` | modify | rewrite §5 flow to automatic; add "Phase-placement convention" section; update I-S2 / I-S3 transport |
| `docs/specifications/20-container-rules.md` | modify | I4: note runtime transport is now tmpfs `/run/secrets` (podman secret), stronger than env |
| `docs/specifications/22-container-build-pre-required-envs.md` | modify | runtime section: add the three podman secrets; build-time envs unchanged; drop stale `BW_SESSION` runtime-env wording |
| `docs/specifications/11-pre-required-env-values.md` | modify | add one-time `podman secret create` setup + Bitwarden account prereq wording |
| `docs/specifications/21-container-build-flow.md` | modify | runtime stage entrypoint note: auth block runs before `chezmoi apply` |
| `docs/issues/2026-06-30-phase-bitwarden-auto-auth.md` | create | result-log (Phase 5) |

No `packages.toml` / `layer_*.txt` / generator change (this work does not add packages — `bitwarden-cli` is already in Layer 1). No build-time Containerfile change.

---

## Phase 1 — `make up` mounts podman secrets conditionally

**Files:**
- Modify: `Makefile` (vars section ~L11-24; `up:` recipe ~L58-66)

**Interfaces:**
- Consumes: three podman secrets named `bw_clientid`, `bw_clientsecret`, `bw_password` (created by the operator in Phase 2's verification; existence is optional).
- Produces: a `make up` that mounts `--secret bw_*` iff each secret exists; with no secrets, expands to nothing (S4 preserved).

- [ ] **Step 1: add the `BW_SECRETS` variable**

Insert after the `MISE_VOLUME` block (after line `MISE_VOLUME   := dotfiles_mise`) and before `BUILD_CTX`:

```make
# Bitwarden credentials as podman secrets. Each is mounted only if it
# exists, so `make up` still starts when no secrets have been created
# (entrypoint skips auth when /run/secrets/bw_password is absent). The
# master password is read by `bw unlock --passwordfile` inside the
# container and never placed in an environment variable.
BW_SECRETS := $(foreach s,bw_clientid bw_clientsecret bw_password,$(shell podman secret exists $(s) 2>/dev/null && printf -- '--secret %s ' $(s))
```

- [ ] **Step 2: rewrite the `up:` recipe**

Replace the existing `up:` recipe (the block starting `up: _require_username ## Start a detached container…` through `$(IMAGE) sleep infinity`) with:

```make
up: _require_username ## Start a detached container with chezmoi bind + toolchain volumes
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		$(BW_SECRETS) \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity
```

(The `-e BW_SESSION=$$BW_SESSION` line is removed; `BW_SESSION` is derived inside the entrypoint in Phase 2.)

- [ ] **Step 3: dry-run verify — no secrets present**

First ensure no secrets exist yet (clean slate for this check):
```bash
podman secret rm bw_clientid bw_clientsecret bw_password 2>/dev/null; podman secret ls
```
Then:
```bash
make -n up
```
Expected: the printed `podman run` line has NO `--secret` token (the `$(BW_SECRETS)` expanded to empty). It must still contain `--userns=keep-id` and all four `-v` mounts and `$(IMAGE) sleep infinity`. There must be no leftover `-e BW_SESSION`.

- [ ] **Step 4: dry-run verify — with secrets present**

Create throwaway secrets (dummy values are fine for the dry-run; they will be re-created with real values in Phase 2):
```bash
printf 'dummy' | podman secret create bw_clientid -
printf 'dummy' | podman secret create bw_clientsecret -
printf 'dummy' | podman secret create bw_password -
make -n up
```
Expected: the `podman run` line contains `--secret bw_clientid --secret bw_clientsecret --secret bw_password` (in that order). Clean up:
```bash
podman secret rm bw_clientid bw_clientsecret bw_password
```

- [ ] **Step 5: real run verify — no-secret startup still works (S4)**

```bash
make down 2>/dev/null; make up
sleep 2; podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
```
Expected: `Up …` (container started with no secrets; the entrypoint skips auth). Then clean up:
```bash
make down
```

- [ ] **Step 6: commit**

```bash
git add Makefile
git commit -m "feat(make): make up mounts bw_* podman secrets conditionally (preserves no-secret startup); drop -e BW_SESSION"
```

**Acceptance:** `make -n up` shows `--secret bw_*` iff each secret exists; `make up` with no secrets starts the container; no `-e BW_SESSION` remains. `podman inspect` of the started container shows no Bitwarden credential in `Env` (the secrets are not mounted at all in this phase's no-secret run).
**Rollback:** `git revert HEAD` restores `-e BW_SESSION` and removes `BW_SECRETS`.

---

## Phase 2 — entrypoint `bw` auth block

**Files:**
- Modify: `container/bind/layer_5_files/entrypoint.sh`

**Interfaces:**
- Consumes: `/run/secrets/bw_clientid`, `/run/secrets/bw_clientsecret`, `/run/secrets/bw_password` (present iff `make up` mounted them).
- Produces: a running container whose entrypoint has run `chezmoi apply` with `BW_SESSION` set when the secrets were mounted; a no-op auth block otherwise.

- [ ] **Step 1: insert the auth block**

In `container/bind/layer_5_files/entrypoint.sh`, locate the block:
```
mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML

chezmoi apply --no-tty --force

exec "$@"
```
Insert the auth block between the `TOML` heredoc close and `chezmoi apply`, so it reads:
```
mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML

# Bitwarden auto-auth (optional). When the three podman secrets are
# mounted (make up mounts each only if it exists), log in with the API
# key and unlock the vault so `chezmoi apply` can resolve `bitwarden*`
# templates. The master password is read straight from
# /run/secrets/bw_password via `bw unlock --passwordfile` — it never
# enters an environment variable. BW_CLIENTID / BW_CLIENTSECRET are
# exported only in this process (not on the image / -e flags, so they do
# not appear in `podman inspect`). If the secrets are absent, skip auth
# and let `chezmoi apply` run without BW_SESSION (no-secret startup).
if [ -f /run/secrets/bw_password ]; then
  export BW_CLIENTID="$(cat /run/secrets/bw_clientid)"
  export BW_CLIENTSECRET="$(cat /run/secrets/bw_clientsecret)"
  if ! bw login --check >/dev/null 2>&1; then
    bw login --apikey
  fi
  export BW_SESSION="$(bw unlock --passwordfile /run/secrets/bw_password --raw)"
fi

chezmoi apply --no-tty --force

exec "$@"
```
Do NOT touch the bind-source check at the top or the `set -euo pipefail` line. Note: under `set -e`, a wrong `bw_password` makes the `bw unlock` command substitution fail, aborting the entrypoint — the container exits, which is the intended loud failure (a wrong credential must not be silently ignored).

- [ ] **Step 2: rebuild the image**

```bash
make build
```
Expected: build succeeds across all 5 stages (no change to Stage 2; the entrypoint is copied in Stage 5). Exit 0.

- [ ] **Step 3: verify no-secret path still applies (S4 / I-BW4)**

```bash
podman secret rm bw_clientid bw_clientsecret bw_password 2>/dev/null
make down 2>/dev/null; make up
sleep 3; podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
podman logs dotfiles-manjaro 2>&1 | tail -5
```
Expected: container `Up`; logs show the normal chezmoi-apply output with no `bw:` errors (auth skipped because `/run/secrets/bw_password` is absent).

- [ ] **Step 4: create the real secrets on the host**

Run interactively (the values are read from the operator's shell env; do NOT echo them into the plan or a committed file):
```bash
# Provide these in your shell first (do NOT commit them):
#   BW_CLIENTID=...      BW_CLIENTSECRET=...      BW_MASTERPASS=...
printf '%s' "$BW_CLIENTID"    | podman secret create bw_clientid -
printf '%s' "$BW_CLIENTSECRET" | podman secret create bw_clientsecret -
printf '%s' "$BW_MASTERPASS"   | podman secret create bw_password -
podman secret ls
```
Expected: three secrets listed (`bw_clientid`, `bw_clientsecret`, `bw_password`). If any already exists, `podman secret rm <name>` first.

- [ ] **Step 5: verify full auth + apply (S1)**

```bash
make down; make up
sleep 5; podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
podman logs dotfiles-manjaro 2>&1 | tail -8
```
Expected: container `Up`; logs show chezmoi apply ran with no `bitwarden*` template error. (If a `bitwarden*` template exists and fails, the error names the item — that is a template/item-ID issue, not an auth issue; auth itself succeeded if `bw login`/`unlock` produced no error in the logs. Today there are no `bitwarden*` templates committed, so apply succeeds trivially — this step confirms the auth block runs without aborting.)

- [ ] **Step 6: verify secrecy invariants (I-BW1 / I-BW2 / I-BW3)**

```bash
# Master password must NOT be in the container env or any process env:
podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_PASSWORD|BW_MASTERPASS|password' && echo FAIL_PASSWORD_ENV || echo OK_NO_PASSWORD_ENV
# BW_CLIENTID / BW_CLIENTSECRET must NOT be in the declared (inspect) env:
podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_CLIENTID|BW_CLIENTSECRET' && echo FAIL_CLIENT_ENV || echo OK_NO_CLIENT_ENV
# The secrets ARE mounted as tmpfs files inside the container:
podman exec dotfiles-manjaro ls -l /run/secrets/ 2>/dev/null
# No credential is baked into the image (inspect the image, not the container):
podman image inspect localhost/dotfiles-manjaro:latest --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_CLIENT|BW_PASSWORD|BW_SESSION' && echo FAIL_IMG_ENV || echo OK_IMG_SECRET_FREE
```
Expected: `OK_NO_PASSWORD_ENV`, `OK_NO_CLIENT_ENV`, the three files under `/run/secrets/`, and `OK_IMG_SECRET_FREE`.

- [ ] **Step 7: verify the master password is not in any live process env (I-BW2)**

```bash
# chezmoi apply has finished (sleep infinity is now PID 1's exec target);
# ensure no running process in the container carries the password:
for pid in $(podman exec dotfiles-manjaro sh -c 'ls /proc | grep -E "^[0-9]+$"'); do \
  podman exec dotfiles-manjaro sh -c "cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep -iE 'BW_PASSWORD|BW_MASTERPASS' && echo FOUND_IN_PID_$pid"; \
done; echo DONE
```
Expected: no `FOUND_IN_PID_*` line; only `DONE`. (BW_CLIENTID/BW_CLIENTSECRET are intentionally in the entrypoint's env only during the apply; after `exec "$@"` they are gone. This check targets the password, which must never be in env at all.)

- [ ] **Step 8: idempotent restart (S5)**

```bash
make down; make up
sleep 5; podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
podman logs dotfiles-manjaro 2>&1 | grep -iE 'already logged in|error|fail' | head
```
Expected: container `Up`; on the second start `bw login --check` short-circuits the login (no error; `bw login --apikey` is skipped). `bw unlock` runs fresh each start (BW_SESSION is ephemeral — by design).

- [ ] **Step 9: commit**

```bash
git add container/bind/layer_5_files/entrypoint.sh
git commit -m "feat(entrypoint): auto-auth bitwarden via podman secrets before chezmoi apply (master password via --passwordfile, never env)"
```

**Acceptance:** Phase 1 + Phase 2 together satisfy issue acceptance #1–#6: `make up` with secrets auths and applies (no manual export); master password not in env/inspect/process-environ; client pair not in inspect env; image secret-free; no-secret path still starts; login idempotent.
**Rollback:** `git revert HEAD` removes the auth block; re-add `-e BW_SESSION` (Phase 1 revert) to restore the manual flow. Remove the created secrets with `podman secret rm bw_clientid bw_clientsecret bw_password`.

---

## Phase 3 — spec 13 rewrite (core: flow + phase-placement + I-S2/I-S3)

**Files:**
- Modify: `docs/specifications/13-secret-management.md`

**Interfaces:**
- Consumes: the Approved design §3 (invariants I-BW1..5) and §"Phase-placement convention".
- Produces: normative spec text matching the implemented flow; the authoritative reference for Phases 4's cross-refs.

- [ ] **Step 1: rewrite §5 to the automatic flow**

Open `docs/specifications/13-secret-management.md`. Replace the current §5 content that describes the manual flow (`bw login --apikey` / `bw unlock --raw` run "manually in the shell", `make apply` "assuming BW_SESSION is set") with the automatic flow:

```markdown
## §5 Authentication flow (runtime, automatic)

The runtime entrypoint authenticates `bw` automatically when the three
podman secrets are mounted by `make up`:

1. `make up` mounts `bw_clientid` / `bw_clientsecret` / `bw_password`
   (each only if it exists — see the Makefile `BW_SECRETS` variable).
   Podman presents them as tmpfs files at `/run/secrets/<name>`; they
   are NOT written to image layers (I4).
2. The entrypoint exports `BW_CLIENTID` / `BW_CLIENTSECRET` (read from
   `/run/secrets/*`) **only inside its own process** — they are never
   on the image `Env` or `podman run -e` flags, so they are absent from
   `podman inspect`.
3. `bw login --check` gates `bw login --apikey` (idempotent across
   restarts; login state is ephemeral in the container home).
4. `BW_SESSION="$(bw unlock --passwordfile /run/secrets/bw_password
   --raw)"` — the master password is read straight from the secret
   file by `bw` and **never enters an environment variable** (I-BW2).
5. `chezmoi apply` runs with `BW_SESSION` in the entrypoint process, so
   `bitwarden*` templates resolve. `BW_SESSION` is process-local; after
   `exec "$@"` it is gone (interactive `podman exec` shells do not
   inherit it — re-unlock on demand with the same `--passwordfile`).

If `/run/secrets/bw_password` is absent (no secrets mounted), the
auth block is skipped and `chezmoi apply` runs without `BW_SESSION`
(no-secret startup; a `bitwarden*` template then fails loudly — the
operator's signal to mount the secrets).

One-time operator setup (host; see [`11-pre-required-env-values.md`](11-pre-required-env-values.md)):

    printf '%s' "$BW_CLIENTID"    | podman secret create bw_clientid -
    printf '%s' "$BW_CLIENTSECRET" | podman secret create bw_clientsecret -
    printf '%s' "$BW_MASTERPASS"   | podman secret create bw_password -
```

- [ ] **Step 2: add the "Phase-placement convention" section**

Add a new section (after the §5 flow, before the existing invariants section or at the end of the relevant block — place it adjacent to I-S4/I-S6):

```markdown
## Phase-placement convention (dotfiles ↔ build / runtime)

The `build_mode` data flag (set in `chezmoi.toml` by the Containerfile
Stage 2 / the runtime entrypoint) is the single switch. For any dotfile,
ask: **does Stage 3 need to source this to get the toolchain ENV?**

- **Yes → build-time block.** Wrap in `{{ if .build_mode }}…{{ end }}`
  (build-only); content MUST be secret-free (I-S4). Currently the
  `.zshenv` toolchain HOMEs/PATH block; the runtime counterpart is
  `.zshrc`. (Wiring the actual `{{ if .build_mode }}` guard into
  `.zshenv` is a pre-existing follow-up, not required here.)
- **No → runtime-only (default).** Every `bitwarden*` /
  `bitwardenFields` / `bitwardenAttachment` call MUST be wrapped in
  `{{ if not .build_mode }}…{{ end }}` (inline, primary mechanism —
  self-contained, no separate ignore list). A `.chezmoiignore` entry
  `{{ if .build_mode }}<file>{{ end }}` is the secondary mechanism for
  wholesale skipping (large files / files that don't template well) —
  the exception, not the default.
- **Plain non-secret dotfiles** without a guard render in both phases;
  the scratch copy is discarded in Stage 5, so this is harmless.

**Safety property:** a forgotten `{{ if not .build_mode }}` guard
around a `bitwarden*` call makes the Stage 2 `chezmoi apply`
(`build_mode = true`) evaluate that call → invoke `bw` unauthenticated
→ **the build fails loudly**. A missing guard is a build error, not a
silent secret leak. This is what makes I-S4 / I4 self-enforcing.
```

- [ ] **Step 3: update I-S2 and I-S3 transport wording**

Update the invariant bullets:
- **I-S2:** change "base key = `BW_CLIENTID` / `BW_CLIENTSECRET` + `BW_SESSION`" to include the master password as the unlock credential, transported as a podman secret: the automation base key = `BW_CLIENTID` / `BW_CLIENTSECRET` (login) + `BW_PASSWORD` (unlock), all as podman secrets (`bw_clientid` / `bw_clientsecret` / `bw_password`); `BW_SESSION` is derived at runtime from `bw unlock --passwordfile` and is process-local.
- **I-S3:** change the runtime transport from "env (`BW_SESSION` in the interactive shell)" to "tmpfs `/run/secrets/*` (podman `--secret`) → entrypoint; master password via `bw unlock --passwordfile`, never env; client pair env-only inside the entrypoint (absent from `podman inspect`); build-time transport unchanged (none — Stage 2 never consults `bw`)."

(Read the current I-S2 / I-S3 text in the file and edit in place; keep the `I-S2` / `I-S3` labels.)

- [ ] **Step 4: resolve spec 13 open Q2 (BW_SESSION persistence)**

If spec 13 has an open-question bullet about persisting `BW_SESSION` in a keyring, mark it **Resolved**: BW_SESSION is ephemeral by design (re-unlocked each `make up` via `--passwordfile`); no keyring persistence is added. Interactive re-unlock uses the mounted secret.

- [ ] **Step 5: verify**

```bash
cd /data/dotfiles3
rg -n 'podman secret|/run/secrets|--passwordfile|Phase-placement convention' docs/specifications/13-secret-management.md
make gen-deps   # must still be idempotent (no SoT change)
```
Expected: the new terms appear; `make gen-deps` prints `txt_written=0 doc_updated=False` (no doc change from gen-deps — spec 13 is not the AUTO-GEN file).

- [ ] **Step 6: commit**

```bash
git add docs/specifications/13-secret-management.md
git commit -m "docs(spec-13): rewrite auth flow to automatic (podman secret); add phase-placement convention; update I-S2/I-S3 transport"
```

**Acceptance:** spec 13 §5 describes the automatic flow; the phase-placement convention is normative; I-S2/I-S3 reflect tmpfs `/run/secrets` + `--passwordfile`; `make gen-deps` unaffected.
**Rollback:** `git revert HEAD`.

---

## Phase 4 — cross-reference specs (20 / 22 / 11 / 21)

**Files:**
- Modify: `docs/specifications/20-container-rules.md`, `docs/specifications/22-container-build-pre-required-envs.md`, `docs/specifications/11-pre-required-env-values.md`, `docs/specifications/21-container-build-flow.md`

**Interfaces:**
- Consumes: the Phase 3 spec 13 wording (link targets).
- Produces: all cross-references consistent (design §8 / self-review D).

- [ ] **Step 1: spec 20 I4 — strengthen the transport note**

In `docs/specifications/20-container-rules.md`, append to the I4 bullet (which currently says runtime apply consumes `BW_SESSION` only into the running container's `$HOME`, never into image layers):

```markdown
Runtime secret transport is **podman secrets** (`podman secret create` +
`podman run --secret`) → tmpfs `/run/secrets/*` in the running
container; the master password is consumed via `bw unlock --passwordfile`
and never placed in an environment variable. This strengthens the
secret-free-image guarantee: no Bitwarden credential appears in
`podman inspect` `Env` or in `/proc/*/environ`. See
[`13-secret-management.md`](13-secret-management.md) §5.
```

- [ ] **Step 2: spec 22 — runtime secrets, build envs unchanged**

In `docs/specifications/22-container-build-pre-required-envs.md`:
- In the `.env` contract section, the line that says runtime secrets
  (`BW_CLIENTID`, `BW_CLIENTSECRET`, `BW_SESSION`) live in the
  interactive shell env: update to say runtime auth material is provided
  as **podman secrets** (`bw_clientid` / `bw_clientsecret` /
  `bw_password`) mounted by `make up`; `.env` still MUST NOT carry
  secrets.
- Add a short "Runtime podman secrets" subsection listing the three
  secret names and noting they are optional (`make up` starts without
  them; the entrypoint skips auth). Build-time envs (`HOST_UID` /
  `HOST_GID` / `USERNAME` / `JOBS`) are unchanged.
- Remove/replace any stale `BW_SESSION` runtime-env wording that
  contradicts the new flow.

- [ ] **Step 3: spec 11 — host setup**

In `docs/specifications/11-pre-required-env-values.md`:
- Update the "Bitwarden account" prereq bullet to reference the one-time
  `podman secret create` setup (the three `printf | podman secret
  create` commands) and link to spec 13 §5.
- Note `BW_CLIENTID` / `BW_CLIENTSECRET` / `BW_MASTERPASS` are now
  consumed only to **create** the podman secrets (once); they are not
  needed in the shell at every `make up` (unlike the old per-shell
  `export BW_SESSION`).

- [ ] **Step 4: spec 21 — entrypoint note**

In `docs/specifications/21-container-build-flow.md`, in the runtime stage (Layer 5) description / acceptance criteria: add a note that the entrypoint runs the optional `bw` auth block (login-if-needed + `bw unlock --passwordfile` → `BW_SESSION`) **before** `chezmoi apply` when the podman secrets are mounted; otherwise it is skipped. Link to spec 13 §5.

- [ ] **Step 5: verify cross-refs resolve**

```bash
cd /data/dotfiles3
rg -n 'podman secret|/run/secrets|bw_password|--passwordfile' docs/specifications/20-container-rules.md docs/specifications/22-container-build-pre-required-envs.md docs/specifications/11-pre-required-env-values.md docs/specifications/21-container-build-flow.md
# links: ensure relative paths exist
rg -n '13-secret-management' docs/specifications/20-container-rules.md docs/specifications/22-container-build-pre-required-envs.md docs/specifications/11-pre-required-env-values.md docs/specifications/21-container-build-flow.md
```
Expected: each file mentions the new transport; each links to spec 13.

- [ ] **Step 6: commit**

```bash
git add docs/specifications/20-container-rules.md docs/specifications/22-container-build-pre-required-envs.md docs/specifications/11-pre-required-env-values.md docs/specifications/21-container-build-flow.md
git commit -m "docs(spec-20/22/11/21): cross-ref bitwarden podman-secret runtime auth (tmpfs /run/secrets, --passwordfile)"
```

**Acceptance:** specs 20/22/11/21 mention podman-secret/`/run/secrets`/`--passwordfile` and link spec 13; build-time envs described as unchanged; no stale "export BW_SESSION every shell" wording.
**Rollback:** `git revert HEAD`.

---

## Phase 5 — end-to-end smoke gate + result-log + close issue

**Files:**
- Create: `docs/issues/2026-06-30-phase-bitwarden-auto-auth.md`
- Modify: `docs/issues/2026-06-30-bitwarden-auto-auth.md` (Status → closed)

**Interfaces:**
- Consumes: all prior phases.
- Produces: the acceptance evidence (result-log) and a closed issue.

- [ ] **Step 1: full clean build + up (secrets present)**

```bash
cd /data/dotfiles3
make clean
make build
make up
sleep 6
podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
podman logs dotfiles-manjaro 2>&1 | tail -10
```
Expected: build 5 stages OK; container `Up`; logs show chezmoi apply ran with no abort.

- [ ] **Step 2: run the secrecy + behavior checks (reprise of Phase 2 Steps 6–8)**

```bash
podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_PASSWORD|BW_MASTERPASS' && echo FAIL_PASSWORD_ENV || echo OK_NO_PASSWORD_ENV
podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_CLIENTID|BW_CLIENTSECRET' && echo FAIL_CLIENT_ENV || echo OK_NO_CLIENT_ENV
podman image inspect localhost/dotfiles-manjaro:latest --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -iE 'BW_CLIENT|BW_PASSWORD|BW_SESSION' && echo FAIL_IMG_ENV || echo OK_IMG_SECRET_FREE
podman exec dotfiles-manjaro ls /run/secrets/
# down/up persistence of toolchain (existing acceptance) + idempotent re-auth:
make down; make up; sleep 6
podman exec dotfiles-manjaro zsh -lc 'rustc --version'
podman logs dotfiles-manjaro 2>&1 | grep -iE 'error|fail' | head
```
Expected: all `OK_*`; `/run/secrets/` lists the three files; `rustc` prints (toolchain volumes persist); no error lines.

- [ ] **Step 3: verify the no-secret path one more time (S4)**

```bash
make down
podman secret rm bw_clientid bw_clientsecret bw_password
make up; sleep 3
podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
podman logs dotfiles-manjaro 2>&1 | tail -3
make down
```
Expected: container `Up` with no secrets; apply runs (auth skipped). (Re-create the secrets only if you want to leave them for ongoing use — otherwise leave removed.)

- [ ] **Step 4: write the result-log**

Create `docs/issues/2026-06-30-phase-bitwarden-auto-auth.md` per 00-doc-mgmt §6.6: a Summary, an Acceptance-evidence table mapping issue criteria #1–#9 to the verification output above (paraphrase the `OK_*` results — do NOT paste any secret value), the commit trail, and a Follow-ups section (`make bw-secrets` helper; `.zshenv` `{{ if .build_mode }}` wiring; interactive `BW_SESSION` in `podman exec`; concrete `bitwarden*` templates + item IDs).

- [ ] **Step 5: close the issue**

In `docs/issues/2026-06-30-bitwarden-auto-auth.md`, change `**Status:** open` → `**Status:** closed (see [result-log](2026-06-30-phase-bitwarden-auto-auth.md))` and fill the `**Related:**` link to the result-log.

- [ ] **Step 6: commit**

```bash
git add docs/issues/2026-06-30-phase-bitwarden-auto-auth.md docs/issues/2026-06-30-bitwarden-auto-auth.md
git commit -m "docs: close bitwarden-auto-auth issue with result-log (podman-secret entrypoint auth verified)"
```

**Acceptance:** all issue acceptance criteria #1–#9 evidenced in the result-log; the secrecy invariants verified (`OK_NO_PASSWORD_ENV`, `OK_NO_CLIENT_ENV`, `OK_IMG_SECRET_FREE`); no-secret path verified; issue closed.
**Rollback:** `git revert HEAD` reopens the issue; the code reverts are Phase 1/2 reverts.

---

## Self-review (writing-plans)

- **Spec coverage:** issue criteria #1 (S1)→P2-S5; #2 (master pw not in env)→P2-S6/S7; #3 (client pair not in inspect)→P2-S6; #4 (image secret-free)→P2-S6; #5 (no-secret start)→P1-S5, P2-S3, P5-S3; #6 (idempotent login)→P2-S8; #7 (spec 13 rewrite+convention)→P3; #8 (specs 20/22/11/21)→P4; #9 (Stage 2 untouched, build secret-free)→P2-S2 (build succeeds, Stage 2 unchanged) + the convention's loud-fail property documented in P3-S2. All covered.
- **Placeholder scan:** no TBD/TODO; every code step shows the actual code; every verification step shows the actual command and expected output.
- **Type/naming consistency:** secret names `bw_clientid` / `bw_clientsecret` / `bw_password` used identically in Phase 1 (`BW_SECRETS`), Phase 2 (`/run/secrets/*`), Phase 3 (spec 13), Phase 4 (cross-refs), Phase 5 (checks). `BW_SESSION`, `BW_CLIENTID`, `BW_CLIENTSECRET` env names match across phases. The Makefile var is `BW_SECRETS` everywhere.
- **Risk note:** the `$(BW_SECRETS)` foreach expansion producing an empty token on a continued line is verified in Phase 1 Steps 3–5 (dry-run + real run) before commit; if a stray empty arg ever appeared, it would surface there, not in production.