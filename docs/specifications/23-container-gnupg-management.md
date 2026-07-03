# 23 — Container GPG key management

> Spec status: **active** (delivered baseline + manual flow); §7
> (future work) is **prospective** and tracks open/deferred issues.
> Normative spec for how a GPG key enters, lives in, and is used inside
> the container's `dotfiles_gnupg` named volume. Build-time wiring
> (package declaration, mountpoint, volume mount) is normative in
> [`20-container-rules.md`](20-container-rules.md) (I-GPG1..I-GPG5) and
> [`21-container-build-flow.md`](21-container-build-flow.md) (Layer
> 1-6); build-time envs live in
> [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).
> This file covers the **runtime key lifecycle** on top of that
> plumbing.

## 1. Scope & relationships

- **In scope:** the operator-driven flow for getting a GPG key into the
  container's persisted keyring; the primary-vs-subkey posture;
  persistence and backup lifecycle; the wiring between the keyring and
  git commit signing (`gpgsign`); and the open future-work items
  (automated Bitwarden/alternative import, real primary-key import).
- **Out of scope (normative elsewhere):** installing `gnupg` /
  `pinentry` ([`20-container-rules.md`](20-container-rules.md) I-GPG3,
  [`02-installed-programs.md`](02-installed-programs.md)); baking the
  `0700` mountpoint ([`21-container-build-flow.md`](21-container-build-flow.md)
  Layer 1-6); the `dotfiles_gnupg` volume wiring
  ([`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md),
  [`03-makefile.md`](03-makefile.md)); the secret-source model
  ([`13-secret-management.md`](13-secret-management.md)).
- **Cross-refs:** plumbing issue
  [`../issues/2026-07-01-gnupg-container-setup.md`](../issues/2026-07-01-gnupg-container-setup.md)
  (+ [result-log](../issues/2026-07-01-phase-gnupg-container-setup.md));
  manual host-key import issue
  [`../issues/2026-07-02-gnupg-host-key-import.md`](../issues/2026-07-02-gnupg-host-key-import.md)
  (+ [result-log](../issues/2026-07-02-phase-gnupg-host-key-import.md));
  deferred Bitwarden/alternative import issue
  [`../issues/2026-07-01-gnupg-bitwarden-import.md`](../issues/2026-07-01-gnupg-bitwarden-import.md);
  git signing invariants
  [`20-container-rules.md`](20-container-rules.md) I-GIT4/I-GIT5.

## 2. Delivered baseline

The plumbing issue delivered a working, persisted, **empty** keyring:

- `GNUPGHOME` resolves to `~/.local/share/gnupg` (`dot_zshenv.tmpl`),
  baked `0700` owner-correct (Layer 1-6, I-GPG2).
- The `dotfiles_gnupg` Podman named volume is mounted there at `make up`
  and removed by `make clean` (I-GPG1).
- `gpg` / `gpg-agent` / `pinentry` are installed (Layer 1); the agent
  starts on demand; gpg runs on defaults — no chezmoi-managed
  `gpg.conf` / `gpg-agent.conf` is baked in this phase (I-GPG3).
- No key material is baked into any image layer (I-GPG4); chezmoi never
  manages the keyring (I-GPG5).
- `.chezmoiignore` excludes `.local/share/gnupg`.

The keyring is therefore **seeded at runtime by the operator** (or, in
a future phase, by the Bitwarden/alternative automation — §7). The
image never carries a key.

## 3. Key import flow (manual — the current procedure)

The supported runtime seed path is **Approach B**: host export →
`podman cp` → container import. It touches no image layer, no Makefile,
no chezmoi source.

1. **Host export** (interactive; pinentry prompts for the primary's
   passphrase for `--export-secret-keys`):
   ```bash
   KEYID=<fingerprint or long keyid of the host key>
   gpg --armor --export-secret-keys "$KEYID" > /tmp/sec.asc
   gpg --export-ownertrust            > /tmp/otrust.txt
   # public-key file is OPTIONAL: importing sec.asc auto-derives the
   # public keyring. Only needed if you want to import a public ring
   # separately:
   # gpg --armor --export "$KEYID" > /tmp/pub.asc
   ```
2. **Transfer** to the container (do **not** relay through the repo
   source tree — it would land secret material in the bind-mounted
   chezmoi source):
   ```bash
   podman cp /tmp/sec.asc  dotfiles-manjaro:/tmp/sec.asc
   podman cp /tmp/otrust.txt dotfiles-manjaro:/tmp/otrust.txt
   ```
3. **Container import** (interactive; pinentry prompts for the
   passphrase):
   ```bash
   podman exec -it dotfiles-manjaro zsh -c \
     'gpg --import /tmp/sec.asc && gpg --import-ownertrust /tmp/otrust.txt'
   ```
4. **Verify:**
   ```bash
   podman exec dotfiles-manjaro zsh -c 'gpg --list-secret-keys --keyid-format=long'
   podman exec dotfiles-manjaro zsh -c 'gpg --list-public-keys  --keyid-format=long'
   ```
5. **Scrub** the temporary export artifacts from **both** sides:
   ```bash
   podman exec dotfiles-manjaro zsh -c 'rm -f /tmp/sec.asc /tmp/otrust.txt'
   rm -f /tmp/sec.asc /tmp/otrust.txt
   ```

> **Why not bind-mount the host `~/.local/share/gnupg`?** The design
> deliberately rejected it (plumbing issue, "without (b) coupling to
> the host's `~/.local/share/gnupg`"): a live bind mount breaks on
> `gpg-agent` socket conflicts (host agent vs container agent over the
> same socket files), host-specific `pinentry-auto.sh` /
> `gpg-agent.conf` that do not work in the container, and stale lock
> files (`.#lk*`). The named-volume + copy model keeps the two keyrings
> independent and the image secret-free.

## 4. Primary-vs-subkey posture

The container may hold:

- **Full secret key** (`sec`, no `#`): primary + subkeys all real. The
  container can then also perform primary-only operations (add/revoke
  UIDs, revoke, re-certify).
- **Subkeys-only** (`sec#`, primary a GNU-dummy stub): the three
  subkeys `[E]` / `[S]` / `[A]` are real; the primary secret is absent.
  This is the recommended **primary-offline** posture: daily
  signing/encryption/authentication work with subkeys; primary-only
  operations stay on the host (or an offline medium).

The 2026-07-02 manual import produced the **subkeys-only** state
(`sec#`), because the exported `sec.asc` carried the primary as a
GNU-dummy stub. This is fully functional for `gpgsign` (uses the `[S]`
subkey), encryption (`[E]`), and SSH-via-gpg auth (`[A]`). Whether the
automated import (§7) should bring the real primary or deliberately
keep this posture is an open decision (§7 Q2).

## 5. Persistence & backup lifecycle

- **`make down && make up`** preserves the keyring: `make down`
  stops/removes the container but does **not** touch the
  `dotfiles_gnupg` named volume; `make up` re-mounts it. Verified in
  the manual-import result-log (S3).
- **`make clean` destroys the keyring**: it runs `podman volume rm
  dotfiles_gnupg` (Makefile `clean`). **Before `make clean`, the
  operator MUST take a backup** (§5 I-GM3):
  ```bash
  podman exec dotfiles-manjaro zsh -c \
    'gpg --armor --export-secret-keys --export-options export-backups <KEYID>' \
    > ~/gpg-backup-$(date +%F).asc
  ```
  Store the backup outside the repo (and outside any path `make clean`
  touches), protected by the key passphrase.
- **Backup is the operator's responsibility.** The repo provides no
  key backup automation; the only secret source recognized is Bitwarden
  ([`13-secret-management.md`](13-secret-management.md) §2 Tier 1), and
  GPG key backup-to-Bitwarden is part of the deferred work (§7).

## 6. gpgsign wiring (current state)

Git commit signing is already wired structurally; it activates once the
key is present in the volume:

- [`20-container-rules.md`](20-container-rules.md) **I-GIT4** renders
  `commit.gpgsign = true`, `gpg.format = openpgp`, and
  `user.signingkey` in **all** modes (build + host runtime + container
  runtime) — signing is **not** gated by `runtime`, so the container
  signs automatically once the key is imported into `dotfiles_gnupg`.
- `user.signingkey` is the `[S]` subkey ID (a public value, spec 13 §2
  Tier 2), sourced from the chezmoi-managed `dot_config/git/config.tmpl`
  + `.chezmoidata/git_config.yaml` (I-GIT1). No secret is baked (I-GIT5).
- **Requirement for the container to actually sign:** the `[S]`
  subkey's secret material must be present in `dotfiles_gnupg` (the
  subkeys-only posture of §4 satisfies this). With the key imported,
  `git commit -S` in the container prompts via the default pinentry
  (`/usr/bin/pinentry`) for the key passphrase — or runs non-
  interactively if a loopback pinentry / cached passphrase is arranged
  (§7 Q3).

## 7. Future work (prospective — open/deferred issues)

Tracked in
[`../issues/2026-07-01-gnupg-bitwarden-import.md`](../issues/2026-07-01-gnupg-bitwarden-import.md)
(`open (deferred)`). Picking it up requires a design doc
(`docs/specifications/implementations/<slug>-design.md`) following the
[`13-secret-management.md`](13-secret-management.md) §5a phase-placement
convention (`{{ if not .build_mode }}` guard around every
`bitwarden*` / secret-consulting template call) and a review pass
(security touch: secrets + image — at least letters A/B/D per
[`09-review.md`](09-review.md) §2.2).

- **F1 — Automated runtime import.** Seed `dotfiles_gnupg` from the
  secret store at startup, **iff the volume is empty** (idempotent;
  never overwrites an operator-generated/imported key), keeping the
  image secret-free (I4 / I-GPG4 / spec 13 I-S3/I-S4 hold). The import
  runs in the runtime entrypoint, after `bw unlock` and before or as a
  dedicated post-`chezmoi apply` step; the passphrase is piped via
  `gpg --batch --pinentry-mode loopback --passphrase-fd` (or equivalent)
  inside the entrypoint process and scrubbed before `exec "$@"`
  (mirrors the `BW_*` scrub, spec 13 §4 step 6).
- **F2 — Secret transport: Bitwarden or an alternative.** The operator
  left the transport open (2026-07-02). The design decides whether the
  key + passphrase live as a Bitwarden item/attachment, a custom field,
  a separate attachment, or an alternative secret store. `make up`
  **without** the relevant podman secrets must still start the container
  and leave the keyring empty (no-secret startup preserved, spec 13 §4
  last paragraph).
- **F3 — Real primary-key import decision (Q2).** Decide whether the
  automated import brings the **real primary** (full `sec`) or
  deliberately keeps the **primary-offline / subkeys-only** posture
  (`sec#`) and documents it as such. The 2026-07-02 manual state is
  subkeys-only; see the
  [host-key-import result-log](../issues/2026-07-02-phase-gnupg-host-key-import.md).
- **F4 — gpgsign configuration ownership.** Confirm `user.signingkey`
  (the `[S]` subkey) and `commit.gpgsign` are owned by the chezmoi-
  managed `dot_config/git` (I-GIT1/I-GIT4) rather than by any GPG
  automation, so the signing config is one source of truth (already
  true today; this item closes the loop with F1).
- **F5 — Non-interactive pinentry for automation.** If F1 needs
  unattended import/signing, decide whether a `gpg-agent.conf`
  (`pinentry-program` / loopback) is baked by chezmoi — which would flip
  `gnupg` to `has_configs = true` in
  [`02-installed-programs.md`](02-installed-programs.md) (currently
  `false`, I-GPG3). Until then gpg runs on defaults and prompts via
  the default `/usr/bin/pinentry`.
- **F6 (optional, host-side) — Host `pubring.kbx` self-public-key
  anomaly.** The host `~/.local/share/gnupg/pubring.kbx` lacks the
  operator's own public-key record, so `gpg --export <fingerprint>` on
  the host falls back to deriving the public key from the secret key
  and prompts via pinentry. Optional host-side cleanup:
  `gpg --armor --export <long-keyid> | gpg --import`. Out of scope for
  the container but noted for completeness.

### Open questions (to resolve in the deferred design)

- **Q1:** Where does the key passphrase live — Bitwarden item password
  field, a custom field, or a separate attachment?
- **Q2:** Full secret key (real primary) vs. subkeys-only
  (primary-offline) for the automated import? (F3.)
- **Q3:** Does the automation need a baked `gpg-agent.conf` (loopback
  pinentry) for unattended operation, flipping `gnupg` to
  `has_configs = true`? (F5.)
- **Q4:** Is the secret transport Bitwarden or an alternative? (F2.)

## 8. Management invariants

Extends I-GPG1..I-GPG5 ([`20-container-rules.md`](20-container-rules.md)).

- **I-GM1:** Seeding `dotfiles_gnupg` is a **runtime-only** operation.
  No key import path may modify any image layer, the `Makefile`,
  `Containerfile`, `packages.toml`, or chezmoi source. (Extends I-GPG4
  / I4 / spec 13 I-S4.)
- **I-GM2:** Temporary export artifacts (`/tmp/*.asc`, ownertrust files)
  used by the manual flow MUST be scrubbed from **both** host and
  container after the transfer. Secret material must not linger on
  disk and must never be relayed through the chezmoi source bind-mount.
- **I-GM3:** `make clean` destroys the keyring (`podman volume rm
  dotfiles_gnupg`). The operator MUST take an encrypted backup (e.g.
  `gpg --armor --export-secret-keys --export-options export-backups`)
  to a location outside the repo before `make clean`. The repo provides
  no key-backup automation.
- **I-GM4:** The container's keyring is **independent** of the host's
  `~/.local/share/gnupg` (named volume, not a bind mount — I-GPG1).
  Bind-mounting the host live keyring is rejected (socket conflicts,
  host-specific pinentry/agent config, lock files; see §3 note).

## Related

- Container rules (I-GPG1..I-GPG5, I-GIT4/I-GIT5):
  [`20-container-rules.md`](20-container-rules.md)
- Build flow / Layer 1-6: [`21-container-build-flow.md`](21-container-build-flow.md)
- Build-time envs / `dotfiles_gnupg` volume note:
  [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md)
- Secret model: [`13-secret-management.md`](13-secret-management.md)
- Make target contract (`up`/`down`/`clean`/`exec`):
  [`03-makefile.md`](03-makefile.md)
- Manual import record:
  [`../issues/2026-07-02-gnupg-host-key-import.md`](../issues/2026-07-02-gnupg-host-key-import.md)
  (+ [result-log](../issues/2026-07-02-phase-gnupg-host-key-import.md))
- Deferred automation issue:
  [`../issues/2026-07-01-gnupg-bitwarden-import.md`](../issues/2026-07-01-gnupg-bitwarden-import.md)