# Host `main` SSH key into container — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this plan step-by-step. This plan is an operator runtime seed procedure, not a code change; do not commit key material or relay it through the repository.

**Status:** pending

**Goal:** Seed the host machine's existing `~/.ssh/main` key pair into the container's persisted `dotfiles_ssh` named volume so the container can use it as an SSH file key without baking secrets into the image or bind-mounting host `~/.ssh`.

**Architecture:** Use the delivered SSH plumbing from `docs/specifications/25-container-ssh-management.md`: the container has an empty, persisted `~/.ssh` backed by the `dotfiles_ssh` Podman named volume. The host key is copied directly into the running container with `podman cp`, permissions are fixed inside the container, and verification compares public-key fingerprints plus volume persistence across `make down && make up`. No Makefile, Containerfile, chezmoi source, or image layer is modified.

**Tech Stack:** Podman, OpenSSH, zsh, existing `dotfiles-manjaro` container target.

## Global Constraints

- Secret material must never enter the repository, chezmoi source tree, docs, terminal snippets committed to git, image layers, or `.env`.
- Do not bind-mount host `~/.ssh`; use the existing `dotfiles_ssh` named volume.
- Do not use `make clean` during this procedure; it removes `dotfiles_ssh` and other persisted volumes. Use `make down && make up` for persistence checks.
- The source key pair is assumed to be `~/.ssh/main` and `~/.ssh/main.pub` on the host.
- The destination key pair is `~/.ssh/main` and `~/.ssh/main.pub` inside the container.
- If `~/.ssh/main` already exists inside the container, stop and decide whether to back it up or remove it before copying.

**Spec:** [`docs/specifications/25-container-ssh-management.md`](../specifications/25-container-ssh-management.md)
**Parent issue:** [`docs/issues/2026-07-03-ssh-container-setup.md`](../issues/2026-07-03-ssh-container-setup.md)
**Review trail:** Existing SSH plumbing review trail is linked from the parent issue; this runtime seed plan does not introduce a new design.

---

## Phases

### Phase 1 — Preconditions

1. Confirm the host key pair exists and is not being read from inside the repository:

   ```bash
   test -f "$HOME/.ssh/main"
   test -f "$HOME/.ssh/main.pub"
   pwd
   ```

   Expected: both `test` commands exit 0; `pwd` may be `/data/dotfiles3`, but the key paths are under `$HOME/.ssh`, not under the repo.

2. Record the host public-key fingerprint in operator notes outside the repo:

   ```bash
   ssh-keygen -lf "$HOME/.ssh/main.pub"
   ```

   Expected: prints one fingerprint line. Do not paste the output into repository docs unless intentionally documenting only a public key fingerprint.

3. Start or reuse the container:

   ```bash
   make up
   ```

   Expected: `dotfiles-manjaro` is running.

4. Confirm the destination does not already contain a `main` key:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'test ! -e ~/.ssh/main && test ! -e ~/.ssh/main.pub'
   ```

   Expected: exit 0. If it fails, inspect with `podman exec dotfiles-manjaro zsh -lc 'ls -la ~/.ssh'` and decide whether to keep, rename, or remove the existing container key.

**Acceptance:** Host key pair exists; container is running; no destination `~/.ssh/main` collision exists.

**Rollback:** No changes have been made. Stop the container with `make down` if desired.

### Phase 2 — Runtime Copy

1. Copy the host key pair directly into the running container's volume-backed `~/.ssh`:

   ```bash
   podman cp "$HOME/.ssh/main" dotfiles-manjaro:.ssh/main
   podman cp "$HOME/.ssh/main.pub" dotfiles-manjaro:.ssh/main.pub
   ```

   Expected: both commands exit 0.

2. Fix OpenSSH permissions inside the container:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/main && chmod 644 ~/.ssh/main.pub'
   ```

   Expected: command exits 0.

3. Verify destination file modes:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'stat -c "%a %n" ~/.ssh ~/.ssh/main ~/.ssh/main.pub'
   ```

   Expected:

   ```text
   700 /home/<user>/.ssh
   600 /home/<user>/.ssh/main
   644 /home/<user>/.ssh/main.pub
   ```

**Acceptance:** `main` and `main.pub` exist in container `~/.ssh` with strict permissions.

**Rollback:** Remove only the copied key files:

```bash
podman exec dotfiles-manjaro zsh -lc 'rm -f ~/.ssh/main ~/.ssh/main.pub'
```

### Phase 3 — Verification

1. Compare the container public-key fingerprint with the host fingerprint from Phase 1:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'ssh-keygen -lf ~/.ssh/main.pub'
   ```

   Expected: fingerprint matches the host `~/.ssh/main.pub` fingerprint.

2. Verify the private key is acceptable to OpenSSH without initiating a network connection:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'ssh-keygen -y -f ~/.ssh/main >/tmp/main.pub.check && cmp -s /tmp/main.pub.check ~/.ssh/main.pub && rm -f /tmp/main.pub.check'
   ```

   Expected: command exits 0. If the key is passphrase-protected, `ssh-keygen` may prompt for the passphrase.

3. Verify named-volume persistence:

   ```bash
   make down
   make up
   podman exec dotfiles-manjaro zsh -lc 'test -f ~/.ssh/main && test -f ~/.ssh/main.pub && stat -c "%a %n" ~/.ssh/main ~/.ssh/main.pub'
   ```

   Expected: files survive restart; modes remain `600` and `644`.

4. Optional network smoke test, only if the operator supplies a reachable host:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'ssh -i ~/.ssh/main -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 user@host true'
   ```

   Expected: exits 0 for a reachable host that accepts the public key. Replace `user@host` outside the repository.

**Acceptance:** Fingerprint matches, OpenSSH can derive the public key from the private key, and the key pair persists across `make down && make up`.

**Rollback:** Remove the copied files with the Phase 2 rollback command.

### Phase 4 — Optional Usage Config

1. For immediate use without a managed `~/.ssh/config`, call SSH with the key explicitly:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'ssh -i ~/.ssh/main -o IdentitiesOnly=yes user@host'
   ```

2. If a temporary container-local SSH config is needed before the deferred chezmoi-managed config issue lands, create it only in the volume:

   ```bash
   podman exec dotfiles-manjaro zsh -lc 'cat > ~/.ssh/config <<'"'"'EOF'"'"'
Host example-main
  HostName example.com
  User git
  IdentityFile ~/.ssh/main
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config'
   ```

   Replace `example-main`, `example.com`, and `git` with real values outside committed docs if they reveal private infrastructure.

**Acceptance:** SSH commands can reference `~/.ssh/main` either explicitly or through a volume-local config.

**Rollback:** Remove the temporary config if it should not persist:

```bash
podman exec dotfiles-manjaro zsh -lc 'rm -f ~/.ssh/config'
```

---

## Completion Evidence

When executed, record only non-secret evidence in a result-log if this needs project traceability:

- Commands run: `make up`, `podman cp`, permission fix, fingerprint comparison, persistence check.
- Status: pass/fail for each phase.
- Do not record private key material, full private hostnames, usernames for private infrastructure, passphrases, or terminal output that contains secrets.

