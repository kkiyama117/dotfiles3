# 25 — Container SSH key management

> Spec status: **active** (delivered baseline + manual flow); §4+
> (future work) is **deferred** to
> [`../issues/2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md).
> Normative spec for how an SSH file key enters, lives in, and is used
> inside the container's `dotfiles_ssh` named volume. Build-time wiring
> (mountpoint, volume mount) is normative in
> [`20-container-rules.md`](20-container-rules.md) (I-SSH1..I-SSH6) and
> [`21-container-build-flow.md`](21-container-build-flow.md) (Layer
> 1-7); build-time envs live in
> [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
> This file covers the **runtime key lifecycle** on top of that
> plumbing.

## 1. Scope & relationships

- **In scope:** the operator-driven flow for getting SSH file keys into
  the container's persisted keyring; persistence and backup lifecycle;
  the wiring between the keyring and the SSH client (`ssh -i`,
  `IdentityFile`); and the deferred future-work items (chezmoi-managed
  `~/.ssh/config`, GPG-agent SSH auth, automated Bitwarden/alternative
  import).
- **Out of scope (normative elsewhere):** installing `openssh`
  ([`20-container-rules.md`](20-container-rules.md) I-SSH1,
  [`02-installed-programs.md`](02-installed-programs.md)); baking the
  `0700` mountpoint ([`21-container-build-flow.md`](21-container-build-flow.md)
  Layer 1-7); the `dotfiles_ssh` volume wiring
  ([`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md),
  [`03-makefile.md`](03-makefile.md)); the secret-source model
  ([`13-secret-management.md`](13-secret-management.md)).
- **Cross-refs:** plumbing issue
  [`../issues/2026-07-03-ssh-container-setup.md`](../issues/2026-07-03-ssh-container-setup.md)
  (+ result-log); deferred config issue
  [`../issues/2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md);
  deferred Bitwarden import issue
  [`../issues/2026-07-03-ssh-bitwarden-import.md`](../issues/2026-07-03-ssh-bitwarden-import.md);
  GPG precedent: spec 23.

## 2. Delivered baseline

The plumbing issue delivered a working, persisted, **empty** SSH keyring:

- `~/.ssh` is baked `0700` owner-correct (Layer 1-7, I-SSH2).
- The `dotfiles_ssh` Podman named volume is mounted there at `make up`
  and removed by `make clean` (I-SSH1).
- `openssh` is already installed (Layer 1); the client runs on defaults —
  no chezmoi-managed `~/.ssh/config` is baked in this phase (I-SSH6).
- No key material is baked into any image layer (I-SSH3);
  `.chezmoiignore` excludes everything under `~/.ssh/` except `~/.ssh/config`
  (I-SSH4) — chezmoi manages only the config file; keys, `known_hosts`, and
  `config.d/*` are volume-owned.
- No `ssh-agent` / `SSH_AUTH_SOCK` wiring is present in this phase
  (I-SSH6); keys are used directly via `ssh -i` / `IdentityFile`.

The keyring is therefore **seeded at runtime by the operator** (or, in
a future phase, by the Bitwarden/alternative automation — §4). The
image never carries a key.

## 3. Key import flow (manual — the current procedure)

The supported runtime seed path is **host export → `podman cp` →
container fix-permissions**. It touches no image layer, no Makefile, no
chezmoi source.

1. **Host staging** (outside the repo):
   ```bash
   ssh-keygen -t ed25519 -f /tmp/container_ssh_test -N ''
   ```
2. **Transfer** to the container (do **not** relay through the repo
   source tree — it would land secret material in the bind-mounted
   chezmoi source):
   ```bash
   podman cp /tmp/container_ssh_test     dotfiles-manjaro:.ssh/id_ed25519
   podman cp /tmp/container_ssh_test.pub dotfiles-manjaro:.ssh/id_ed25519.pub
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
5. **Scrub** the temporary export artifacts from **both** sides:
   ```bash
   rm -f /tmp/container_ssh_test /tmp/container_ssh_test.pub
   podman exec dotfiles-manjaro zsh -c 'rm -f /tmp/container_ssh_test /tmp/container_ssh_test.pub'
   ```

> **Why not bind-mount the host `~/.ssh`?** The design deliberately
> rejected it (plumbing issue, "without host `~/.ssh` bind mounts"): a
> live bind mount couples the container to the host keyring's existence
> and permissions, risks `ssh-agent` socket / lock file contention
> between host and container, and breaks the project invariant that the
> container is self-contained w.r.t. persisted client state. The named-
> volume + copy model keeps the two keyrings independent and the image
> secret-free.

## 4. Future work (deferred)

Tracked in
[`../issues/2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md)
(`open (deferred)`). Picking it up requires a design doc
(`docs/specifications/implementations/<slug>-design.md`) following the
[`13-secret-management.md`](13-secret-management.md) §5a phase-placement
convention and a review pass (security touch: secrets + image — at least
letters A/B/D per [`09-review.md`](09-review.md) §2.2).

- **F1 — Chezmoi-managed `~/.ssh/config` (single file).** Add
  `private_dot_ssh/config.tmpl` gated by `{{ if not .build_mode }}`. The
  operator chooses which Host blocks to manage by editing this one file —
  no `dot_ssh/config.d/*.tmpl` fragments (`config.d/*` is excluded by
  I-SSH4). A volume-only `~/.ssh/config.d/local/*` may still be
  `Include`d from `config.tmpl` for hand-edited / local-only Host blocks
  (never chezmoi-managed). This realizes the `openssh`
  `has_configs = true` declaration in
  [`02-installed-programs.md`](02-installed-programs.md) and is the
  natural home for `Host *`, `IdentityFile`, `AddKeysToAgent`, etc.
- **F2 — GPG-agent SSH auth.** Wire `SSH_AUTH_SOCK` to the gpg-agent
  `[A]` authentication subkey socket. Requires the config issue to decide
  whether to auto-add `export SSH_AUTH_SOCK=...` in `dot_zshenv.tmpl` /
  `dot_config/zsh/*.zshrc` and how to start `gpg-agent` with SSH support
  before the first `ssh` invocation.
- **F3 — Automated runtime import.** Seed `dotfiles_ssh` from the secret
  store at startup, **iff the volume is empty** (idempotent; never
  overwrites an operator-generated/imported key), keeping the image
  secret-free (I4 / I-SSH3 / spec 13 I-S3/I-S4 hold). The import runs in
  the runtime entrypoint, after `bw unlock` and before or as a dedicated
  post-`chezmoi apply` step; any passphrase is scrubbed before `exec
  "$@"` (mirrors the `BW_*` scrub, spec 13 §4 step 6).
- **F4 — Secret transport: Bitwarden or an alternative.** The operator
  left the transport open. The design decides whether the key +
  passphrase live as a Bitwarden item/attachment, a custom field, a
  separate attachment, or an alternative secret store. `make up`
  **without** the relevant podman secrets must still start the container
  and leave the keyring empty (no-secret startup preserved, spec 13 §4
  last paragraph).

### Open questions (to resolve in the deferred design)

- **Q1:** Where does the key passphrase live — Bitwarden item password
  field, a custom field, or a separate attachment?
- **Q2:** Should `~/.ssh/config` be a single file or fragment `Include`
  under `~/.ssh/config.d/`?
- **Q3:** Does the automation need an `ssh-agent` / gpg-agent SSH socket
  baked into the entrypoint or shell env?
- **Q4:** Is the secret transport Bitwarden or an alternative? (F4.)

## 5. Management invariants

Extends I-SSH1..I-SSH6 ([`20-container-rules.md`](20-container-rules.md)).

- **I-SH-GM1:** Seeding `dotfiles_ssh` is a **runtime-only** operation.
  No key import path may modify any image layer, the `Makefile`,
  `Containerfile`, `packages.toml`, or chezmoi source. (Extends I-SSH3 /
  I4 / spec 13 I-S4.)
- **I-SH-GM2:** Temporary export artifacts used by the manual flow MUST
  be scrubbed from **both** host and container after the transfer.
  Secret material must not linger on disk and must never be relayed
  through the chezmoi source bind-mount.
- **I-SH-GM3:** `make clean` destroys the keyring (`podman volume rm
  dotfiles_ssh`). The operator MUST take an encrypted backup (e.g. the
  original host key or a `gpg --armor --export-secret-keys` of the key)
  to a location outside the repo before `make clean`. The repo provides
  no key-backup automation.
- **I-SH-GM4:** The container's SSH keyring is **independent** of the
  host's `~/.ssh` (named volume, not a bind mount — I-SSH1). Bind-
  mounting the host live keyring is rejected (socket / lock / permission
  coupling; see §3 note).

## Related

- Container rules (I-SSH1..I-SSH6):
  [`20-container-rules.md`](20-container-rules.md)
- Build flow / Layer 1-7: [`21-container-build-flow.md`](21-container-build-flow.md)
- Build-time envs / `dotfiles_ssh` volume note:
  [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md)
- Make target contract (`up`/`down`/`clean`/`exec`):
  [`03-makefile.md`](03-makefile.md)
- Secret model: [`13-secret-management.md`](13-secret-management.md)
- GPG precedent: [`23-container-gnupg-management.md`](23-container-gnupg-management.md)
