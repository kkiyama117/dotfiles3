# SSH file keys in the container (named volume at `~/.ssh`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** pending

**Goal:** Give the container a working, persisted **file-based SSH client keyring** at `~/.ssh` via a Podman named volume (`dotfiles_ssh`), with owner-correct `0700` mountpoint provisioning, chezmoiignore patterns for secret key filenames, and normative spec coverage — without baking key material into image layers, without host `~/.ssh` bind mounts, and without GPG-agent SSH wiring or chezmoi-managed `~/.ssh/config` (deferred siblings).

**Architecture:** Mirrors the GPG plumbing precedent (`gnupg-container-setup` → manual import → deferred Bitwarden). `openssh` is already installed (Layer 1 pacman, `packages.toml`). Containerfile Layer **1-7** adds a sibling `install -d -m 0700` for `~/.ssh` (parallel to Layer 1-6 gnupg). The `Makefile` wires a fifth named volume `dotfiles_ssh` at `~/.ssh`. `.chezmoiignore` excludes **conventional secret key filename patterns** under `.ssh/` (not the whole tree — future config issue can chezmoi-manage non-secret files). **No ssh-agent** in entrypoint or `dot_zshenv.tmpl` (I-SSH6). Spec **25 §1–3** is created at plumbing close (GPG spec 23 precedent).

**Tech Stack:** Podman ≥ 4.0 / BuildKit, Manjaro base image, Arch `openssh` (already installed), chezmoi.

## Global Constraints

- **Secret-free image** (spec 13 / spec 20 I4): no SSH private key material in any image layer. Layer 1-7 directory is empty at build time; keys live only in the runtime `dotfiles_ssh` named volume.
- **No `packages.toml` / `make gen-deps` change** (design S1): `openssh` already declared at layer 1.
- **No host bind mount** of `~/.ssh` (design Alt-B rejected — agent socket / lock / permission coupling; spec 23 §3 analog).
- **No ssh-agent wiring** in plumbing phase (I-SSH6): file keys via `ssh -i` / volume-local `IdentityFile`; agent deferred to config issue.
- **Non-root, `--userns=keep-id`** (spec 20 I2/I7): Layer 1-7 directory is owner-correct (`HOST_UID:HOST_GID`) at `0700`.
- **`USERNAME` defined in `.env`** at repo root (existing). `make build` / `make up` abort when unset.
- **Rollout:** existing deployments must run **`make build`** (Layer 1-7) before the first `make up` after this change. To reset SSH keys only: `podman volume rm dotfiles_ssh` — **NOT** `make clean` (also wipes `dotfiles_gnupg` / cargo / mise / rustup — cargo/GPG precedent).
- **Manual import:** never relay keys through the chezmoi source bind-mount (spec 23 I-GM2 analog); use `podman cp` into the running container's volume-backed `~/.ssh`.
- Commits: one commit per Phase. Commit message references `docs/issues/2026-07-03-ssh-container-setup.md`.

**Spec:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Parent issue:** [`docs/issues/2026-07-03-ssh-container-setup.md`](../issues/2026-07-03-ssh-container-setup.md)
**Review trail:** [`pass1-A`](../reviews/2026-07-03-ssh-container-setup-review-pass1-A-factual.md) / [`B`](../reviews/2026-07-03-ssh-container-setup-review-pass1-B-security.md) / [`C`](../reviews/2026-07-03-ssh-container-setup-review-pass1-C-architecture.md) / [`D`](../reviews/2026-07-03-ssh-container-setup-review-pass1-D-consistency.md) / [`E`](../reviews/2026-07-03-ssh-container-setup-review-pass1-E-operability.md) / [`aggregate`](../reviews/2026-07-03-ssh-container-setup-review-pass1.md)

---

## File Structure

| Path | Action | Phase |
|---|---|---|
| `container/Containerfile` | modify | Layer 1-7 `~/.ssh` mountpoint; update Layer 1 header comment (six runtime mounts / five named volumes) | 1 |
| `Makefile` | modify | `SSH_VOLUME := dotfiles_ssh`; `up` mount; `clean` volume rm; refresh `help` text | 1 |
| `.chezmoiignore` | modify | Add secret key filename patterns under `.ssh/` (§5.4) | 1 |
| `docs/specifications/03-makefile.md` | modify | Add `SSH_VOLUME` + missing `GNUPG_VOLUME` rows; refresh `up`/`clean` descriptions | 2 |
| `docs/specifications/20-container-rules.md` | modify | Add I-SSH1..I-SSH6 under **Build (Containerfile)**; delegated-rules row → spec 25 | 2 |
| `docs/specifications/21-container-build-flow.md` | modify | Layer 1-7 row; Notes ("five named volumes" → six mounts / five named + ssh); acceptance **#18–#21** | 2 |
| `docs/specifications/22-container-build-pre-required-envs.md` | modify | Add `dotfiles_ssh` @ `~/.ssh` to USERNAME row | 2 |
| `docs/specifications/25-container-ssh-management.md` | create | §1–3 only (plumbing baseline — spec 23 precedent) | 2 |
| `docs/issues/2026-07-03-phase-ssh-container-setup.md` | create | Result-log with acceptance evidence | 3 |
| `docs/issues/2026-07-03-ssh-container-setup.md` | modify | Status → closed; link result-log | 3 |

---

## Phase 1 — Plumbing (Containerfile + Makefile + chezmoiignore)

**Files:**
- Modify: `container/Containerfile`
- Modify: `Makefile`
- Modify: `.chezmoiignore`

**Interfaces:**
- Consumes: `HOST_UID` / `HOST_GID` / `USERNAME` build-args (existing); Layer 1-6 gnupg block as insertion anchor.
- Produces: `/home/${USERNAME}/.ssh` exists, `0700`, owner `HOST_UID:HOST_GID` before runtime mount; `make up` mounts `dotfiles_ssh` there; `make clean` removes the volume.

- [ ] **Step 1.1: Insert Containerfile Layer 1-7**

After the Layer 1-6 gnupg `RUN` (still as `USER root`, before the closing `USER ${USERNAME}`), append:

```dockerfile
# Layer 1-7: ~/.ssh mountpoint (named volume dotfiles_ssh).
#
# 0700 is OpenSSH's expected mode for the directory. Kept as a separate RUN
# from the 0755 toolchain dirs and the gnupg dir so the mode is distinct.
# Owner-correct so Podman does not root-create an absent mountpoint at
# `make up`. Empty at build time; no key material baked (I-SSH3).
RUN install -d -o ${HOST_UID} -g ${HOST_GID} -m 0700 \
    /home/${USERNAME}/.ssh
```

Update the Layer 1-5 header comment (~lines 95–97):
- **"five runtime mounts"** → **"six runtime mounts"**
- **"four named volumes for cargo/rustup/mise/gnupg"** → **"five named volumes for cargo/rustup/mise/gnupg/ssh"** (and mention `~/.ssh` is the fifth named volume, outside `~/.local/share/`)

- [ ] **Step 1.2: Wire `SSH_VOLUME` in Makefile**

Add after `GNUPG_VOLUME`:

```makefile
SSH_VOLUME    := dotfiles_ssh
```

In `up`, add mount (after gnupg line):

```makefile
		-v $(SSH_VOLUME):/home/$(USERNAME)/.ssh \
```

In `clean`, extend volume rm:

```makefile
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME) $(GNUPG_VOLUME) $(SSH_VOLUME)
```

Update `help` strings — replace vague "toolchain volumes" with explicit list:

```
up    … chezmoi bind + named volumes (cargo, rustup, mise, gnupg, ssh)
clean … remove image and named volumes (cargo, rustup, mise, gnupg, ssh)
```

- [ ] **Step 1.3: Add `.chezmoiignore` secret key patterns**

Append (after the gnupg ignore block):

```
# SSH secret key material — volume-owned; conventional names only
.ssh/id_*
.ssh/*_ed25519
.ssh/*_rsa
.ssh/*_ecdsa
.ssh/*_ed25519_sk
.ssh/*_ecdsa_sk
```

Do **not** add a blanket `.ssh` ignore.

- [ ] **Step 1.4: Verify Layer 1-7 in isolation**

```bash
make build
USERNAME=$(grep '^USERNAME' .env | cut -d= -f2)
podman run --rm --entrypoint bash $(grep '^IMAGE' Makefile | head -1 | awk '{print $3}') \
  -lc "stat -c '%a %U:%G' /home/${USERNAME}/.ssh"
```

Expected: `700 <USERNAME>:<group>` (or numeric uid:gid matching host).

- [ ] **Step 1.5: Commit**

```bash
git add container/Containerfile Makefile .chezmoiignore
git commit -m "feat(container): dotfiles_ssh volume + Layer 1-7 ~/.ssh mountpoint (0700)

Named volume at ~/.ssh mirrors GPG plumbing; chezmoiignore excludes
conventional secret key filename patterns only.

Refs docs/issues/2026-07-03-ssh-container-setup.md"
```

---

## Phase 2 — Spec sync (03 / 20 / 21 / 22 / 25)

**Files:**
- Modify: `docs/specifications/03-makefile.md`
- Modify: `docs/specifications/20-container-rules.md`
- Modify: `docs/specifications/21-container-build-flow.md`
- Modify: `docs/specifications/22-container-build-pre-required-envs.md`
- Create: `docs/specifications/25-container-ssh-management.md`

- [ ] **Step 2.1: spec 03 — Makefile contract**

- Add `GNUPG_VOLUME` row (pre-existing drift — backfill).
- Add `SSH_VOLUME` row: `dotfiles_ssh` @ `~/.ssh`; removed by `clean`.
- Refresh `up` / `clean` target descriptions to list all five named volumes + ssh.

- [ ] **Step 2.2: spec 20 — I-SSH1..I-SSH6**

Under **`### Build (Containerfile)`** (parallel to I-GPG1..5), add:

- **I-SSH1:** `dotfiles_ssh` named volume @ `~/.ssh`; no host bind mount.
- **I-SSH2:** Layer 1-7 pre-creates `0700` owner-correct mountpoint.
- **I-SSH3:** No private key material in image layers.
- **I-SSH4:** `.chezmoiignore` excludes conventional secret key patterns under `.ssh/`; chezmoi never manages those keys. Whole `.ssh` tree is **not** ignored (future config issue).
- **I-SSH5:** `make clean` removes `dotfiles_ssh`; rollout safety in spec 21 #21.
- **I-SSH6:** No `ssh-agent` / `SSH_AUTH_SOCK` wiring in plumbing phase.

Add delegated-rules row: **Container SSH management → spec 25**.

Note: `openssh` `has_configs = true` in spec 02 is structurally accurate but config sources are unrealized until the config issue (spec 25 §4+).

- [ ] **Step 2.3: spec 21 — Layer table + acceptance**

Add Layer 1 table row **1-7**:

| Sub-layer | Action | Rationale |
|---|---|---|
| 1-7 | `install -d -m 0700` for `~/.ssh` | Owner-correct `0700` mountpoint for `dotfiles_ssh`; empty at build time. |

Update Notes paragraph: four named volumes → **five** (cargo/rustup/mise/gnupg/**ssh**); mention six runtime mounts (one bind + five named).

Add acceptance criteria **#18–#21**:

18. After `make up`, `podman exec <c> zsh -ic 'ssh -V'` succeeds.
19. `stat ~/.ssh` → `0700`, `${USERNAME}`-owned.
20. `make down && make up` preserves key material in `dotfiles_ssh` (test key).
21. **Rollout:** existing deployments must run **`make build`** before first `make up` after this change; SSH-only reset: `podman volume rm dotfiles_ssh` (NOT `make clean` — also wipes `dotfiles_gnupg`).

- [ ] **Step 2.4: spec 22 — USERNAME row**

Extend the `USERNAME` Notes cell: add `dotfiles_ssh` @ `~/.ssh`; no key material baked (I-SSH3).

- [ ] **Step 2.5: Create spec 25 §1–3 (plumbing baseline)**

Mirror spec 23 structure for §1–3 only:

| Section | Content |
|---|---|
| §1 | Scope / relationships (this issue vs config vs Bitwarden siblings) |
| §2 | Delivered baseline: I-SSH1..6, empty volume, `openssh` already installed |
| §3 | Manual copy-import + **I-SH-GM1..4** (runtime-only seeding, scrub, no chezmoi-bind relay, `make clean` destroys keys) — copy procedure from design §6 |

§4+ deferred to [`2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md).

- [ ] **Step 2.6: Commit**

```bash
git add docs/specifications/03-makefile.md \
  docs/specifications/20-container-rules.md \
  docs/specifications/21-container-build-flow.md \
  docs/specifications/22-container-build-pre-required-envs.md \
  docs/specifications/25-container-ssh-management.md
git commit -m "docs(spec-03/20/21/22/25): SSH volume invariants + spec 25 §1–3 baseline

I-SSH1..6, Layer 1-7 row, acceptance #18–21, Makefile contract backfill.

Refs docs/issues/2026-07-03-ssh-container-setup.md"
```

---

## Phase 3 — Build, smoke, persistence, result-log, close issue

**Files:**
- Create: `docs/issues/2026-07-03-phase-ssh-container-setup.md`
- Modify: `docs/issues/2026-07-03-ssh-container-setup.md`

- [ ] **Step 3.1: Full build + empty mountpoint smoke**

Start from a fresh SSH volume for the empty-volume smoke. This reset is
targeted and preserves `dotfiles_gnupg` / cargo / mise / rustup volumes.

```bash
make build
make down || true
podman volume rm dotfiles_ssh || true
make up
podman exec dotfiles-manjaro zsh -ic 'ssh -V'
podman exec dotfiles-manjaro zsh -c 'stat -c "%a %U:%G" ~/.ssh'
podman exec dotfiles-manjaro zsh -c 'ls -A ~/.ssh | wc -l'
```

Expected: `ssh` version string; `700 <USERNAME>:...`; `0` (empty before manual import).

- [ ] **Step 3.2: Manual test key import (design §6)**

```bash
ssh-keygen -t ed25519 -f /tmp/container_ssh_test -N ''
podman cp /tmp/container_ssh_test     dotfiles-manjaro:.ssh/id_ed25519
podman cp /tmp/container_ssh_test.pub dotfiles-manjaro:.ssh/id_ed25519.pub
podman exec dotfiles-manjaro zsh -c \
  'chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_ed25519 && chmod 644 ~/.ssh/id_ed25519.pub'
podman exec dotfiles-manjaro zsh -c 'ls -la ~/.ssh'
rm -f /tmp/container_ssh_test /tmp/container_ssh_test.pub
```

Expected: key files present with correct permissions. Optional: `ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes …` when operator supplies a reachable host.

- [ ] **Step 3.3: Persistence**

```bash
make down && make up
podman exec dotfiles-manjaro zsh -c 'test -f ~/.ssh/id_ed25519 && echo persisted'
```

Expected: `persisted`.

- [ ] **Step 3.4: GPG regression (targeted volume reset)**

```bash
make down
podman volume rm dotfiles_ssh
make up
# Confirm GPG key still present (dotfiles_gnupg untouched):
podman exec dotfiles-manjaro zsh -c 'gpg --list-secret-keys 2>/dev/null | head -3 || echo no-keys'
```

Expected: GPG keys still listed (if previously imported); `~/.ssh` empty again after volume rm.

- [ ] **Step 3.5: Write result-log**

Create `docs/issues/2026-07-03-phase-ssh-container-setup.md` with:
- S1–S10 acceptance evidence table (map to design success criteria)
- Representative command output
- Rollout note (`make build` required; `podman volume rm dotfiles_ssh` not `make clean`)
- Deviations (if any)
- Secrecy invariants confirmed

- [ ] **Step 3.6: Close issue**

Update `docs/issues/2026-07-03-ssh-container-setup.md`:
- Status → `closed (see result-log)`
- Status update section with link to result-log

- [ ] **Step 3.7: Commit**

```bash
git add docs/issues/2026-07-03-phase-ssh-container-setup.md \
  docs/issues/2026-07-03-ssh-container-setup.md
git commit -m "docs: close ssh-container-setup issue with result-log (volume green, persistence holds, GPG preserved)

Refs docs/issues/2026-07-03-ssh-container-setup.md"
```

---

## Phase 4 — Whole-branch review (SDD final gate)

- [ ] **Step 4.1: Generate review diff**

```bash
git merge-base develop HEAD
# Write .superpowers/sdd/review-<merge-base>..<HEAD>.diff
```

- [ ] **Step 4.2: Dispatch final reviewer** (`context: fresh`)

Scope: spec coherence (I-SSH* / Layer 1-7 / acceptance #18–#21 / spec 25 §1–3), implementation correctness, rollout safety, no secret baked.

- [ ] **Step 4.3: Address Important findings before merge** (if any)

---

## Out of scope (do not implement in this plan)

- `packages.toml` / `make gen-deps`
- Chezmoi `~/.ssh/config` / fragments → [`2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md)
- GPG `[A]` SSH auth → config issue
- Bitwarden `run_after_install-ssh-keys.sh.tmpl` → [`2026-07-03-ssh-bitwarden-import.md`](../issues/2026-07-03-ssh-bitwarden-import.md)
- `authorized_keys` / inbound `sshd`
- `ssh-agent` / `SSH_AUTH_SOCK` (I-SSH6)

---

## Verification checklist (controller)

| Check | Command / evidence |
|---|---|
| Layer 1-7 mode | `stat -c '%a' ~/.ssh` → `700` |
| Empty at first up | `ls -A ~/.ssh` empty before import |
| ssh client | `ssh -V` |
| Persistence | key survives `make down && make up` |
| GPG safe reset | `podman volume rm dotfiles_ssh` leaves `dotfiles_gnupg` |
| No secret in image | no `id_*` under `~/.ssh` in `podman run --rm --entrypoint bash ...` before volume |
| Tests | `make test-deps` → 28 passed (no generator change; regression guard) |
