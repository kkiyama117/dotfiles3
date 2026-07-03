# Import SSH file keys from Bitwarden at container startup — Design

**Status:** DRAFT
**Date opened:** 2026-07-03
**Issue:** [`../../issues/2026-07-03-ssh-bitwarden-import.md`](../../issues/2026-07-03-ssh-bitwarden-import.md)
**Author:** kiyama
**Review required:** letter A + B + D (touches secret material, auth flow, and cross-spec consistency; see [`../09-review.md`](../09-review.md) §2.2)

## §1 Context & success criteria

### Context

The delivered SSH plumbing gives the container a persisted but initially empty
`~/.ssh` backed by the `dotfiles_ssh` Podman named volume
([`../25-container-ssh-management.md`](../25-container-ssh-management.md)).
Today the operator seeds file keys manually with `podman cp`. That keeps the
image secret-free, but it is not reproducible after `make clean` destroys the
volume.

The project secret source is Bitwarden via `bw`
([`../13-secret-management.md`](../13-secret-management.md)). The runtime
entrypoint authenticates and unlocks Bitwarden from Podman secrets before
running `chezmoi apply`; Bitwarden-bound templates must be wrapped in
`{{ if not .build_mode }}` so the build-time pre-pass never resolves secret
material.

This design automates only the file-key seed path. It does not add
`ssh-agent`, GPG-agent SSH auth, or a managed `~/.ssh/config`; those remain
with the SSH config / agent follow-up issue.

### Success criteria

- **S1:** On a fresh `dotfiles_ssh` volume, `make up` with Bitwarden secrets
  mounted imports the configured SSH key files into container `~/.ssh`.
- **S2:** Import is runtime-only: no private key, public key, passphrase, or
  temporary key artifact is written to the repository, `.env`, Podman image
  layers, or `podman inspect` environment.
- **S3:** Import is idempotent and non-destructive: an existing destination
  private key is never overwritten by default.
- **S4:** Imported file modes are OpenSSH-compatible: `~/.ssh` is `0700`,
  private keys are `0600`, and public keys are `0644`.
- **S5:** `make down && make up` preserves already-imported files because they
  live in `dotfiles_ssh`; `make clean` may delete them, after which Bitwarden
  import can restore them.
- **S6:** `make up` without Bitwarden Podman secrets still starts in the
  existing no-secret mode and leaves `dotfiles_ssh` empty unless the operator
  has manually seeded it.
- **S7:** The implementation updates the relevant docs: specs 11 / 25 and the
  parent issue acceptance notes gain the Bitwarden item contract and runtime
  import behavior.

## §2 Alternatives considered

- **A1 — Keep manual `podman cp` only.** Rejected for the target workflow:
  it is secure but not reproducible after `make clean` and does not answer the
  operator request to manage the key like other Bitwarden-backed secrets.
- **A2 — Host `~/.ssh` bind mount.** Rejected by the baseline SSH design:
  it couples host and container permissions / lock files / socket state and
  violates the named-volume independence invariant.
- **A3 — Bitwarden attachments materialized by a chezmoi `run_after` script
  (chosen).** The private key and public key live as Bitwarden attachments;
  a runtime-only chezmoi script writes them directly to the volume-backed
  `~/.ssh`, fixes modes, and skips existing keys. This matches spec 13's
  Bitwarden template model and keeps the image secret-free.
- **A4 — Shell out to `bw` in a standalone entrypoint helper.** Rejected for
  this phase: spec 13 makes chezmoi's native `bitwarden*` template functions
  the integration path. A shell helper would duplicate auth/session handling
  and make build-mode guards harder to audit.
- **A5 — Use a hosted SSH-agent product instead of file keys.** Deferred:
  agent-backed signing is a different runtime contract. File keys remain
  needed for hosts that expect `IdentityFile` / `ssh -i` behavior.

## §3 Architecture / Invariants

### Bitwarden item shape

Each managed SSH key is represented by non-secret metadata in the chezmoi
source and secret bytes in Bitwarden:

- `name`: destination basename under `~/.ssh`, for example `main`.
- `item`: Bitwarden item ID or stable item name. Item IDs are allowed in the
  repository per [`../11-pre-required-env-values.md`](../11-pre-required-env-values.md);
  secret values are not.
- `private_attachment`: attachment name containing the private OpenSSH key.
- `public_attachment`: optional attachment name containing the public key. If
  omitted, the script derives `name.pub` from the private key with
  `ssh-keygen -y`.

The recommended first item is the host's `main` key pair:

```yaml
ssh_keys:
  - name: main
    item: "bitwarden-item-id-or-stable-name"
    private_attachment: "main"
    public_attachment: "main.pub"
```

The placeholder above is illustrative. The implementation plan must replace it
with either a documented operator-edit step or a real non-secret item ID
approved by the maintainer; it must never include key material.

### Runtime materialization flow

`chezmoi apply` evaluates a new script template:

`./.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`

The template is fully gated. In build mode, or in runtime without a
`BW_SESSION`, it renders a no-op script and does not evaluate any Bitwarden
attachment:

```gotemplate
#!/usr/bin/env bash
{{ if and (not .build_mode) (env "BW_SESSION") }}
# Runtime-only Bitwarden attachment materialization.
{{ else }}
exit 0
{{ end }}
```

At runtime, for each configured key:

1. If `~/.ssh/<name>` already exists, skip that key and print a short
   non-secret status line.
2. Create `~/.ssh` if needed and set it to `0700`.
3. Write the private attachment to a temporary file under `~/.ssh` in the
   same filesystem, then atomically move it to `~/.ssh/<name>`.
4. Write the public attachment to `~/.ssh/<name>.pub`, or derive it with
   `ssh-keygen -y -f ~/.ssh/<name>`.
5. Set private/public permissions to `0600` / `0644`.
6. Verify the private key can derive the same public key when a public key is
   present.
7. Remove temporary files on both success and failure.

### Invariants

- **I-SH-BW1:** Import is runtime-only and must be guarded by both
  `{{ if not .build_mode }}` and a non-empty `BW_SESSION`. A build-time
  pre-pass, or a no-secret runtime start, must never evaluate a Bitwarden
  attachment.
- **I-SH-BW2:** The `dotfiles_ssh` named volume is the only destination for
  imported SSH file keys. The repository and image remain key-free.
- **I-SH-BW3:** The script never overwrites an existing private key unless a
  later design explicitly adds an opt-in force mode. Default behavior is
  skip-and-report.
- **I-SH-BW4:** Temporary files must stay outside the chezmoi source bind
  mount and must be removed with a trap. No temporary export path under the
  repository is allowed.
- **I-SH-BW5:** Public keys are treated as volume-owned alongside private
  keys. They may be regenerated from private keys, but they are not committed
  merely because they are public.
- **I-SH-BW6:** No SSH agent state is introduced. Consumers use explicit
  `ssh -i ~/.ssh/<name>` or a future managed `~/.ssh/config`.

## §4 Scope / staging breakdown

1. **Configuration data** — add a small chezmoi data file for SSH key import
   metadata. It contains item IDs / names and attachment names only, never
   secret bytes.
2. **Runtime script** — add
   `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`, with attachment
   evaluation guarded by `{{ if and (not .build_mode) (env "BW_SESSION") }}`,
   using `bitwardenAttachment` / `bitwardenAttachmentByRef` to materialize
   attachments.
3. **Documentation sync** — update specs 11 and 25 to describe the Bitwarden
   item contract and runtime import lifecycle; update the deferred issue with
   the design / plan / result-log links as work progresses.
4. **Verification** — run build-time and runtime checks proving the script is
   skipped in build mode, imports on a fresh volume, skips on a populated
   volume, and preserves keys across `make down && make up`.

Explicitly out of scope:

- Adding or changing `openssh` packages.
- Changing `Containerfile` or `Makefile` volume plumbing.
- Managing `~/.ssh/config` or `known_hosts`.
- Agent forwarding, `ssh-agent`, or GPG-agent SSH auth.
- Importing host `~/.ssh` directly.

## §5 Implementation detail

### §5.1 Chezmoi data

Create a dedicated data file, for example:

`./.chezmoidata/ssh_keys.yaml`

It should contain only non-secret metadata:

```yaml
ssh_keys:
  - name: main
    item: "bitwarden-item-id-or-stable-name"
    private_attachment: "main"
    public_attachment: "main.pub"
```

If `.chezmoidata/` does not exist yet in the working tree, the implementation
creates it. This matches the documented repository layout in
[`../01-file-structures.md`](../01-file-structures.md).

### §5.2 Script template contract

The script template is created at:

`./.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`

Template-level requirements:

- Wrap the Bitwarden attachment calls in
  `{{ if and (not .build_mode) (env "BW_SESSION") }}`.
- Render one shell block per configured key from `.ssh_keys`.
- Use chezmoi Bitwarden template functions to inline attachment bytes into
  shell-safe here-documents at apply time.
- Set `umask 077` before writing private material.
- Use `mktemp` under `~/.ssh`, not `/tmp`, so the final `mv` stays on the
  target filesystem.
- Register a `trap` to delete temporary files.
- Print only key names and status; never print key contents or passphrases.

The implementation plan must choose the exact template function variant after
checking the installed chezmoi version's `bitwardenAttachment` return shape.
The design requires native chezmoi Bitwarden functions and forbids direct
`bw` subprocess calls from the script.

### §5.3 Verification commands

Build-mode guard:

```bash
make build
```

Expected: build succeeds without consulting Bitwarden for SSH attachments.

Fresh-volume import:

```bash
podman volume rm dotfiles_ssh
make up
podman exec dotfiles-manjaro zsh -lc 'test -f ~/.ssh/main && test -f ~/.ssh/main.pub'
podman exec dotfiles-manjaro zsh -lc 'stat -c "%a %n" ~/.ssh ~/.ssh/main ~/.ssh/main.pub'
```

Expected: `~/.ssh` is `700`, `main` is `600`, and `main.pub` is `644`.

Idempotence:

```bash
make down
make up
podman exec dotfiles-manjaro zsh -lc 'test -f ~/.ssh/main && test -f ~/.ssh/main.pub'
```

Expected: the second run skips the existing key and leaves the same files in
place.

Key consistency:

```bash
podman exec dotfiles-manjaro zsh -lc 'ssh-keygen -y -f ~/.ssh/main > /tmp/main.pub.check && cmp -s /tmp/main.pub.check ~/.ssh/main.pub && rm -f /tmp/main.pub.check'
```

Expected: command exits 0. If the key is passphrase-protected, this may prompt
for the passphrase; unattended passphrase handling is out of scope unless a
later design explicitly adds it.

## §6 Failure behavior / rollback

- Missing Bitwarden secrets: preserve the existing no-secret startup path.
  The script renders as a no-op when `BW_SESSION` is absent, so no Bitwarden
  attachment is evaluated and `~/.ssh` stays empty unless the operator has
  manually seeded it.
- Missing Bitwarden item or attachment: `chezmoi apply` fails loudly. Silent
  partial import is not allowed.
- Destination collision: skip that key and leave the existing file untouched.
- Public/private mismatch: remove the newly written files for that key and
  fail the script.
- Rollback for imported files:

  ```bash
  podman exec dotfiles-manjaro zsh -lc 'rm -f ~/.ssh/main ~/.ssh/main.pub'
  ```

- Full SSH keyring reset:

  ```bash
  make down
  podman volume rm dotfiles_ssh
  ```

  Do not use `make clean` for a targeted SSH rollback; it also removes other
  persisted volumes.

## §7 Open questions

- **Q1:** Which exact Bitwarden item ID / stable item name should the initial
  `main` key use? This must be supplied by the maintainer outside this design
  or added as a non-secret data value during implementation.
- **Q2:** Should the public key be stored as a Bitwarden attachment, or should
  the script always derive it from the private key? Recommended default:
  allow both, prefer attachment when present, derive when omitted.
- **Q3:** Are passphrase-protected private keys required to verify
  non-interactively during startup? Recommended default: no; import bytes and
  permissions only, leave authentication prompts to normal SSH use.
- **Q4:** Should future work add an explicit force-refresh mode for key
  rotation? Recommended default: no for the first implementation; rotation is
  manual remove-then-reimport.

## Related

- Runtime SSH key lifecycle:
  [`../25-container-ssh-management.md`](../25-container-ssh-management.md)
- Secret source / Bitwarden runtime auth:
  [`../13-secret-management.md`](../13-secret-management.md)
- Pre-required Bitwarden values:
  [`../11-pre-required-env-values.md`](../11-pre-required-env-values.md)
- Container invariants:
  [`../20-container-rules.md`](../20-container-rules.md)
- Deferred issue:
  [`../../issues/2026-07-03-ssh-bitwarden-import.md`](../../issues/2026-07-03-ssh-bitwarden-import.md)
