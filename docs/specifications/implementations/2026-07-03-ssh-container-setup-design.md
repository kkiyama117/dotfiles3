# Set up SSH file keys in the container (named volume at `~/.ssh`) — Design

**Status:** DRAFT (revise after pass-1 review — **Approved**)
**Date opened:** 2026-07-03
**Issue:** [`../../issues/2026-07-03-ssh-container-setup.md`](../../issues/2026-07-03-ssh-container-setup.md)
**Author:** kiyama

## §1 Context & success criteria

`openssh` is already declared in `dependencies/packages.toml` (`manager =
"pacman"`, `layer = 1`, `has_configs = true`). After `make up`, `ssh -V`
works, but there is **no** persisted `~/.ssh` directory and **no** private
keys inside the container.

The container already persists toolchain and GPG state via Podman named
volumes (`dotfiles_cargo` / `dotfiles_rustup` / `dotfiles_mise` /
`dotfiles_gnupg`) mounted at XDG paths, with owner-correct mountpoints
pre-created in Containerfile Layer 1 (0755 for toolchain dirs; 0700 for
`GNUPGHOME` at Layer 1-6). `--userns=keep-id` (spec 20 I2) keeps the host
UID/GID inside the container.

The gap: `~/.ssh` is not provisioned, there is no named volume, and any
keys copied into the container die on `make down`. GPG signing for git is
already handled via `dotfiles_gnupg` (spec 23). **This design is file-key
SSH only** — no `gpg-agent` SSH support, no chezmoi-managed `~/.ssh/config`
(deferred to
[`../../issues/2026-07-03-ssh-container-config-setup.md`](../../issues/2026-07-03-ssh-container-config-setup.md)).

Success criteria (mirror the issue's acceptance, labeled for review
cross-reference):

- **S1** `openssh` already in `dependencies/packages.toml` (`layer = 1`);
  **no** `make gen-deps` change required (spec 20 I5 / I8 hold).
  `has_configs = true` is **realized only after** the config issue (spec 25
  §config); plumbing leaves spec 02 AUTO-GEN accurate structurally but config
  sources absent — note in spec 20 I-SSH block.
- **S2** Containerfile Layer **1-7** creates `/home/${USERNAME}/.ssh` with
  mode `0700`, owner `HOST_UID:HOST_GID`.
- **S3** `Makefile` defines `SSH_VOLUME := dotfiles_ssh`; `make up` mounts
  it at `~/.ssh`; `make clean` removes it.
- **S4** After `make up`, `${USERNAME}` can run `ssh -V`; `stat ~/.ssh`
  shows `0700` and `${USERNAME}` ownership.
- **S5** `make down && make up` preserves key material written into the
  volume (named-volume persistence; spec 21 acceptance #8 analog).
- **S6** `.chezmoiignore` excludes **secret key filename patterns** under
  `.ssh/` (see §5.4). The **entire** `.ssh` tree is **not** ignored (unlike
  `.local/share/gnupg`) so a future config issue can chezmoi-manage
  non-secret files under `.ssh/`.
- **S7** No SSH private key material baked into any image layer (spec 20 I4
  / spec 13 I-S4 hold); `~/.ssh` is empty at build time.
- **S8** Specs **03 / 20 / 21 / 22** updated to record the new volume, Layer
  1-7 directory, and invariants `I-SSH1..I-SSH6`.
- **S9** **Manual import path normative** in new spec **25 §1–3** (plumbing
  baseline: volume invariants + manual copy-import + no-bind-relay / scrub —
  mirrors spec 23 for GPG). Config / GPG SSH tier / fragment Include remain
  deferred to the config issue (spec 25 §4+).
- **S10** Rollout safety documented in spec 21 acceptance **#21**: targeted
  `podman volume rm dotfiles_ssh`; **NOT** `make clean`; existing deployments
  must **`make build` before first `make up`** after this change (Layer 1-7).

## §2 Alternatives considered

- **Alt-B — Host bind mount** of `~/.ssh` into the container. Rejected: couples
  the container to the host keyring's existence and permissions (`0700` dir,
  `0600` keys), risks `ssh-agent` socket / lock file contention between host
  and container (same rationale as spec 23 §3 for rejecting a host GPG bind
  mount), and breaks the project invariant that the container is
  self-contained w.r.t. persisted client state.
- **C — Ephemeral** (no persistence; re-import keys each run). Rejected for
  daily use: SSH client keys the operator uses regularly should survive
  `make down && make up`; re-importing every start is friction this issue
  does not need to solve.
- **D — Named volume + Bitwarden key import at startup.** The persistence
  base is exactly Approach A; the Bitwarden-import step is deferred to
  [`../../issues/2026-07-03-ssh-bitwarden-import.md`](../../issues/2026-07-03-ssh-bitwarden-import.md)
  (mirrors GPG → [`../../issues/2026-07-01-gnupg-bitwarden-import.md`](../../issues/2026-07-01-gnupg-bitwarden-import.md)).
- **E — Chezmoi-managed `~/.ssh/config` in this phase.** Rejected (YAGNI +
  scope split): deferred to
  [`../../issues/2026-07-03-ssh-container-config-setup.md`](../../issues/2026-07-03-ssh-container-config-setup.md).

## §3 Architecture / Invariants

All I-SSH* land under spec 20 **`### Build (Containerfile)`** (parallel to
I-GPG1..5 / I-CARGO1), not under Runtime — they describe volume wiring and
build-time mountpoint provisioning.

- **I-SSH1** — SSH client key persistence is a Podman named volume
  `dotfiles_ssh` mounted at `~/.ssh`, the same pattern as `dotfiles_gnupg`
  (different path, same mechanics). The volume is the sole home of file
  keys; the image carries none of them. No host bind mount.
- **I-SSH2** — `~/.ssh` is baked owner-correct at `0700` in Containerfile
  Layer 1-7 (extension of Layer 1 XDG provisioning, parallel to Layer 1-6
  for gnupg). Owner-correct provisioning prevents Podman from root-creating
  an absent mountpoint (the `/home` re-own failure mode).
- **I-SSH3** — No SSH private key material is baked into any image layer
  (extends spec 20 I4 / spec 13 I-S4). Runtime keys live only in the named
  volume.
- **I-SSH4** — `.chezmoiignore` excludes **OpenSSH conventional secret key
  filename patterns** under `.ssh/` (see §5.4). Chezmoi must not manage
  keys matching those patterns. **Non-conventional names** (custom PEM paths,
  arbitrary filenames) are **not** covered — the operator must add explicit
  ignore entries or keep such keys volume-only without placing them in the
  chezmoi source tree (spec 13 I-S3). Unlike GPG (I-GPG5 ignores the entire
  `.local/share/gnupg` tree), the whole `.ssh` directory is **not** ignored
  so a future issue can chezmoi-manage non-secret config under `.ssh/`.
- **I-SSH5** — `make clean` removes `dotfiles_ssh` alongside the other named
  volumes. Targeted reset and rollout safety live in spec 21 acceptance
  **#21** (not duplicated here — mirrors I-GPG1..5 vs spec 21 #16 pattern).
- **I-SSH6** — Plumbing phase wires **no** `ssh-agent` in entrypoint or
  `dot_zshenv.tmpl`. File keys are used directly via `IdentityFile` / `ssh -i`.
  Agent wiring (`SSH_AUTH_SOCK`, gpg-agent SSH socket) is deferred to the
  config issue.

## §4 Scope / staging breakdown

Five mechanical change areas, each independently reviewable:

1. **`container/Containerfile` Layer 1-7** — append (as `USER root`, before
   `USER ${USERNAME}`):
   `install -d -o ${HOST_UID} -g ${HOST_GID} -m 0700
   /home/${USERNAME}/.ssh`.
   Update the Layer 1 header comment (~lines 95–97): **"five runtime mounts"**
   → **"six"** (one bind + five named volumes); **"four named volumes"**
   → **"five"** (+ `dotfiles_ssh` at `~/.ssh`).
2. **`Makefile`** — add `SSH_VOLUME := dotfiles_ssh`; mount in `make up`;
   add to `make clean`. Update `help` / `clean` descriptions to name **all**
   persisted volumes (cargo / rustup / mise / gnupg / ssh), not "toolchain"
   only.
3. **`.chezmoiignore`** — add secret key patterns under `.ssh/` (§5.4); do
   **not** add a blanket `.ssh` ignore.
4. **Spec sync** — spec **03** (Makefile contract), **20** (I-SSH1..6),
   **21** (Layer 1-7 row + acceptance **#18–#21** + Notes paragraph),
   **22** (`dotfiles_ssh` in `.env` contract), **25** (new §1–3 baseline
   only — see §5.7).
5. **Verification** (implementation phase — **not in this design commit**):
   build, smoke, persistence, manual import smoke, result-log, close issue.

**Explicitly out of scope:**

- `packages.toml` / `make gen-deps` changes.
- Chezmoi `~/.ssh/config` / fragments → config issue (spec 25 §4+).
- GPG `[A]` SSH auth → config issue.
- Bitwarden `run_after_install-ssh-keys.sh.tmpl` → Bitwarden issue.
- `authorized_keys` / inbound `sshd`.

## §5 Implementation detail

### §5.1 `packages.toml`

**No change.** `openssh` already declared at layer 1, `has_configs = true`
(config sources deferred — see S1).

### §5.2 Containerfile Layer 1-7

After Layer 1-6 gnupg block (still as `USER root`):

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

Header comment update (Layer 1-5 block above): **six** runtime mounts (one
bind for chezmoi source, **five** named volumes for cargo/rustup/mise/gnupg/ssh).

### §5.3 Makefile

```makefile
SSH_VOLUME  := dotfiles_ssh
```

In `make up`:

```makefile
	-v $(SSH_VOLUME):/home/$(USERNAME)/.ssh \
```

In `make clean`:

```makefile
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME) $(GNUPG_VOLUME) $(SSH_VOLUME)
```

Example `help` wording (replace vague "toolchain volumes"):

```
up    … chezmoi bind + named volumes (cargo, rustup, mise, gnupg, ssh)
clean … remove image and named volumes (cargo, rustup, mise, gnupg, ssh)
```

### §5.4 `.chezmoiignore`

```
# SSH secret key material — volume-owned; conventional names only
.ssh/id_*
.ssh/*_ed25519
.ssh/*_rsa
.ssh/*_ecdsa
.ssh/*_ed25519_sk
.ssh/*_ecdsa_sk
```

**Side effect:** `.ssh/id_*` matches `id_ed25519.pub` as well as private
keys (`*` spans the dot). Public keys are therefore also chezmoi-unmanaged —
acceptable for this phase (volume-only `.pub` files). **Gap:** custom names
(e.g. `~/.ssh/my_vps_key`, `*.pem`) are **not** ignored; never place secret
keys in the chezmoi source tree (spec 13 I-S3 / spec 23 I-GM2 analog).

### §5.5 Spec edits (summary)

| Spec | Edit |
|------|------|
| 03 | Add `SSH_VOLUME` to Variables table; refresh `up`/`clean` descriptions; **also add missing `GNUPG_VOLUME` row** (pre-existing drift) |
| 20 | Add I-SSH1..I-SSH6 under **Build (Containerfile)**; note `openssh has_configs` unrealized until spec 25 §config |
| 21 | Layer 1 table row **1-7**; update Notes ("five named volumes" + ssh); acceptance **#18–#21** (see below) |
| 22 | USERNAME row: add `dotfiles_ssh` @ `~/.ssh` |
| 25 | **New** §1–3 only at plumbing close (§5.7) |

**spec 21 acceptance #18–#21 (draft):**

18. After `make up`, `podman exec <c> zsh -ic 'ssh -V'` succeeds.
19. `stat ~/.ssh` → `0700`, `${USERNAME}`-owned.
20. `make down && make up` preserves key material in `dotfiles_ssh` (test key).
21. **Rollout:** existing deployments must run **`make build`** (Layer 1-7) before
    the first `make up` after this change; to reset SSH keys only use
    `podman volume rm dotfiles_ssh` (NOT `make clean` — also wipes `dotfiles_gnupg`).

### §5.6 Verification plan (implementation phase)

- `make build` → `podman run --rm --entrypoint bash $(IMAGE) -lc "stat -c '%a' /home/${USERNAME}/.ssh"`
  → `700` (before any `make up` volume seed; entrypoint intentionally bypassed).
- `make up` → `ssh -V`; `stat ~/.ssh` per S4.
- Manual import (§6) → `ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes …` smoke
  (no ssh-agent required — I-SSH6).
- `make down && make up` → key still present (S5).
- GPG regression: targeted `podman volume rm dotfiles_ssh` leaves `dotfiles_gnupg` intact.

### §5.7 spec 25 baseline (plumbing only — GPG spec 23 precedent)

Create `docs/specifications/25-container-ssh-management.md` with **§1–3 only**
at plumbing result-log time:

| Section | Content |
|---------|---------|
| §1 | Scope / relationships (this issue vs config vs Bitwarden issues) |
| §2 | Delivered baseline: I-SSH1..6, empty volume, `openssh` already installed |
| §3 | Manual copy-import (§6 below) + **I-SH-GM1..4** mirroring spec 23 I-GM1..4 (runtime-only seeding, scrub, no chezmoi-bind relay, `make clean` destroys keys) |

§4+ (config fragments, GPG SSH tier, Bitwarden) deferred to sibling issues.
Config issue AC #7 becomes "extend spec 25 §4+" instead of "create spec 25".

## §6 Manual key import (operator procedure)

Mirrors the **manual copy-import flow** in spec 23 §3 (there labeled
"Approach B" — **unrelated** to this design's §2 **Alt-B** host bind mount,
which is rejected).

> **Do not relay keys through the chezmoi source bind-mount** (spec 23 I-GM2).
> Copy only into the container's volume-backed `~/.ssh`. Never `cp` keys into
> the repo root / `private_dot_ssh/` — that would violate spec 13 I-S3.

1. **Host staging** (outside the repo):
   ```bash
   ssh-keygen -t ed25519 -f /tmp/container_test -N ''
   ```
2. **Copy into the running container** (volume-backed `~/.ssh`):
   ```bash
   podman cp /tmp/container_test     dotfiles-manjaro:.ssh/id_ed25519
   podman cp /tmp/container_test.pub dotfiles-manjaro:.ssh/id_ed25519.pub
   ```
   (`podman cp` resolves the container user's `$HOME`.)
3. **Fix permissions** (OpenSSH is strict):
   ```bash
   podman exec dotfiles-manjaro zsh -c \
     'chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_ed25519 && chmod 644 ~/.ssh/id_ed25519.pub'
   ```
4. **Verify** (agent-free — I-SSH6):
   ```bash
   podman exec dotfiles-manjaro zsh -c 'ls -la ~/.ssh'
   # Optional smoke when operator supplies a reachable host:
   podman exec dotfiles-manjaro zsh -c \
     'ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes -o ConnectTimeout=5 user@host true'
   ```
5. **Persistence:** `make down && make up` → keys still present.
6. **Scrub** host temp files; confirm no key material under the chezmoi source
   tree (`git status` clean under `dot_ssh/` / `private_dot_ssh/` if present).

> **Why not bind-mount the host `~/.ssh`?** Same rationale as spec 23 §3.

> **Config note:** Hand-edit `~/.ssh/config` on the volume if needed; chezmoi
> config is deferred to the config issue.

## §7 Open questions

- **Q1 (ssh-agent)** — RESOLVED by I-SSH6: no agent in plumbing phase.
- **Q2 (known_hosts)** — Volume-local only; not chezmoi-managed in this phase.
- **Q3 (Bitwarden)** — Deferred to Bitwarden issue.
- **Q4 (spec 25 timing)** — RESOLVED: §1–3 at plumbing close; §4+ at config issue.

## Related

- Issue: [`../../issues/2026-07-03-ssh-container-setup.md`](../../issues/2026-07-03-ssh-container-setup.md)
- Deferred config: [`../../issues/2026-07-03-ssh-container-config-setup.md`](../../issues/2026-07-03-ssh-container-config-setup.md)
- Deferred Bitwarden: [`../../issues/2026-07-03-ssh-bitwarden-import.md`](../../issues/2026-07-03-ssh-bitwarden-import.md)
- GPG precedent: spec 23, gnupg-container-setup design
