# Phase complete — bitwarden auto-auth at container startup (podman secret)

**Date:** 2026-06-30
**Phase:** bitwarden-auto-auth (implementation)
**Plan:** [`../plans/2026-06-30-bitwarden-auto-auth-impl.md`](../plans/2026-06-30-bitwarden-auto-auth-impl.md)
**Issue:** [`2026-06-30-bitwarden-auto-auth.md`](2026-06-30-bitwarden-auto-auth.md)
**Design:** [`../specifications/implementations/2026-06-30-bitwarden-auto-auth-design.md`](../specifications/implementations/2026-06-30-bitwarden-auto-auth-design.md)

## Summary

Automated Bitwarden authentication at container startup. Three podman
secrets (`bw_clientid` / `bw_clientsecret` / `bw_password`) are mounted
by `make up` (each only if it exists) as tmpfs `/run/secrets/*`. The
runtime entrypoint logs in with the API key, syncs, unlocks the vault
via `bw unlock --passwordfile /run/secrets/bw_password --raw` (master
password never enters an env), runs `chezmoi apply` with `BW_SESSION`,
then scrubs `BW_CLIENTID` / `BW_CLIENTSECRET` / `BW_SESSION` before
`exec "$@"`. `make up` now resolves `bitwarden*` templates with no
manual `export BW_SESSION`. The image stays secret-free; no Bitwarden
credential appears in `podman inspect`, in `/proc/*/environ` after
exec, or in any image layer. Stage 2 build-prepass is untouched.

## Acceptance evidence

| # | Criterion (issue) | Verification | Result |
|---|---|---|---|
| 1 | `make up` (secrets mounted) auths + applies, no manual export | logs `You are logged in!`; container `Up`; `chezmoi apply` ran | PASS |
| 2 | master password never in any env | `podman inspect` Env clean; `/proc/*/environ` clean across all PIDs; read via `--passwordfile` | PASS |
| 3 | `BW_CLIENTID`/`BW_CLIENTSECRET` not in `podman inspect` Env | inspect Env grep clean (only transient in entrypoint process, scrubbed before exec) | PASS |
| 4 | image secret-free (no credential in layers) | `podman image inspect` Env clean; secrets are tmpfs `/run/secrets` | PASS |
| 5 | `make up` without secrets still starts + applies | verified (Phase 1 Step 5, Phase 2 Step 3): container `Up`, `/run/secrets` absent, auth skipped, apply ran | PASS |
| 6 | `bw login` idempotent across restarts | `down && up` repeat: no error; login runs each start (ephemeral home → `--check` gates re-login); unlock fresh each start | PASS |
| 7 | spec 13 §5 → automatic flow + phase-placement convention; I-S2/I-S3 updated | spec 13 §4 rewritten, §5a added, I-S2/I-S3 updated, Q2 resolved (commit `4ec825f`) | PASS |
| 8 | specs 20/22/11/21 updated consistently | cross-refs + env tables updated (commit `e9717bb`) | PASS |
| 9 | Stage 2 untouched; build secret-free; unguarded `bitwarden*` fails build loudly | no Containerfile change in this work; `make build` green; loud-fail property documented (spec 13 §5a / I-BW5) | PASS |

### Secrecy checks (consolidated, with secrets mounted)

```
[I-BW2] inspect Env: no master pw      → OK
[I-BW3] inspect Env: no client pair    → OK
[I-BW1] image Env secret-free          → OK
/run/secrets (tmpfs)                   → bw_clientid bw_clientsecret bw_password
all-proc /proc/*/environ: no BW_*      → OK_ALL_CLEAN
PID 1 (sleep infinity) environ         → no BW_* (scrubbed before exec)
restart (down/up) → PID 1 scrubbed     → OK
toolchain volume persistence (rustc)   → rustc 1.96.0 (ac68faa20 2026-05-25)
```

## Deviations from the approved plan

Recorded honestly; the authoritative final state is in the design
(Approved) and spec 13 §4, both synced (commit `16b95ca`).

1. **Scrub hardening (B-review finding).** The plan's entrypoint did not
   scrub `BW_*` before `exec`. Verification found that `exec "$@"`
   carries the entrypoint's exported `BW_CLIENTID` / `BW_CLIENTSECRET` /
   `BW_SESSION` into PID 1 (`sleep infinity`) via `/proc/1/environ` for
   the container's lifetime. Fix: `unset BW_CLIENTID BW_CLIENTSECRET
   BW_SESSION` before `exec`. (commit `040efc5`)
2. **Unlock retry + loud-fail validate.** `bw unlock --passwordfile
   --raw` transiently returns an **empty session** (vault data not yet
   local / server not ready) while exiting 0 — `set -e` did not catch
   it, and the plan's scrub was gated on `BW_SESSION` being non-empty,
   so an empty session skipped the scrub and leaked the client pair.
   Fix: retry the unlock a few times; `exit 1` (loud) if still empty;
   make the scrub **unconditional within the auth-ran path** (gated on
   the secret file, not on `BW_SESSION`); add `bw sync` before unlock.
   (commit `9b5ee4c`)
3. **`make bw-secrets` helper** remains out of scope (YAGNI); setup is
   documented in spec 11/13.

## Security incident + remediation (transparency)

During Phase 2 Step 7, an "informational" grep I added beyond the
plan printed the actual `BW_CLIENTID` / `BW_CLIENTSECRET` / `BW_SESSION`
values from PID 1's environ into the session transcript. The plan's
Step 7 only checks for the master password (absence). Remediation
advised to the user:

- **Rotate the Bitwarden API key `BW_CLIENTSECRET`** (durable
  credential) in Bitwarden and recreate the `bw_clientsecret` podman
  secret.
- `BW_SESSION` is ephemeral (container-local; neutralized by `make
  down`). The master password was never printed (read via
  `--passwordfile`).

The final verification uses only **quiet** (`grep -qi`) checks that
report presence/absence, never values.

## Commit trail

```
16b95ca docs: sync spec-13 §4 + design §3/§5/I-BW4 to implemented entrypoint (unlock retry+loud-fail, unconditional scrub, bw sync)
9b5ee4c fix(entrypoint): retry bw unlock on empty session (loud fail); scrub BW_* unconditionally within auth path (not gated on BW_SESSION non-empty)
e9717bb docs(spec-20/22/11/21): cross-ref bitwarden podman-secret runtime auth (tmpfs /run/secrets, --passwordfile, scrub); update env tables
4ec825f docs(spec-13): rewrite auth flow to automatic (podman secret); add phase-placement convention; update I-S2/I-S3 (tmpfs /run/secrets, --passwordfile, scrub before exec); resolve Q2
040efc5 feat(entrypoint): auto-auth bitwarden via podman secrets before chezmoi apply; scrub BW_* env before exec (master password via --passwordfile, never env)
3e377e9 feat(make): make up mounts bw_* podman secrets conditionally (preserves no-secret startup); drop -e BW_SESSION
```

## Follow-ups (not in scope)

- `make bw-secrets` / setup script helper (currently doc-only in spec 11/13).
- Wire the actual `{{ if .build_mode }}` guard into `.zshenv` (design Q1;
  pre-existing TODO; the phase-placement *convention* is in place).
- Interactive `BW_SESSION` in `podman exec` shells (Shape A: not
  provided; re-unlock on demand via `bw unlock --passwordfile
  /run/secrets/bw_password --raw`).
- Concrete `bitwarden*` templates + Bitwarden item IDs (spec 13 Q1) —
  the auth base is now in place for them.
- AUR makedepend bloat trimming (carried over from the paru-aur layer
  result-log).