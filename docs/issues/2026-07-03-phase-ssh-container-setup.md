# Phase complete — SSH file keys in the container (plumbing)

**Date:** 2026-07-03
**Phase:** ssh-container-setup (4 phases — plumbing / spec sync / verify / SDD gate)
**Issue:** [`2026-07-03-ssh-container-setup.md`](2026-07-03-ssh-container-setup.md) → closed
**Plan:** [`../plans/2026-07-03-ssh-container-setup-impl.md`](../plans/2026-07-03-ssh-container-setup-impl.md)
**Design:** [`../specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Review trail:** pass-1 A–E ([aggregate](../reviews/2026-07-03-ssh-container-setup-review-pass1.md)); plan review (4 findings, fixed); implementation task review (Phase 1-2, Approved, no Critical/Important, 3 Minor — 2 fixed, 1 left as improvement).

## Summary

The container now has a persisted SSH client keyring via the Podman named
volume `dotfiles_ssh` mounted at `~/.ssh`. The Containerfile `base` stage bakes
the `~/.ssh` mountpoint owner-correct at `0700` (Layer 1-7, mirroring the GPG
Layer 1-6 block), so Podman does not root-create an absent mountpoint at
`make up`. The Makefile wires `SSH_VOLUME := dotfiles_ssh` into `up` (mount)
and `clean` (remove). `.chezmoiignore` excludes everything under `~/.ssh/`
except `~/.ssh/config` (`.ssh/*` + `!.ssh/config`) — chezmoi manages only
the config file; keys, `known_hosts`, `config.d/*` are volume-owned (I-SSH4).
No SSH private key is baked into any image layer (I-SSH3); the
keyring lives only in the runtime named volume. No `ssh-agent` /
`SSH_AUTH_SOCK` wiring is added this phase (I-SSH6 — deferred to the config
issue). Spec 25 (Container SSH key management) is created with §1-3 normative
(manual import flow) and §4+ deferred to `2026-07-03-ssh-container-config-setup`.
Specs 03/20/21/22 are synced. `openssh` was already installed (Layer 1 pacman);
`packages.toml` is unchanged.

## Acceptance evidence

| # | Criterion (issue / spec 21) | Verification | Result |
|---|---|---|---|
| 18 | After `make up`, `ssh -V` succeeds | `podman exec dotfiles-manjaro zsh -ic 'ssh -V'` → `OpenSSH_10.3p1, OpenSSL 3.6.3` | PASS |
| 19 | After `make up`, `stat ~/.ssh` prints `0700` and is `${USERNAME}`-owned | image inspect: `stat -c '%a %U:%G' ~/.ssh` → `700 kiyama:kiyama`; runtime: same | PASS |
| 20 | `make down && make up` preserves key material in `dotfiles_ssh` (test key) | imported test ed25519 via `podman cp` → `ssh-keygen -l -f` → fingerprint `SHA256:U82lzOPMAE3e047ms1LbkDa2Ady8fa3ZLuKQ0jqT4yk`; after `make down && make up` the same fingerprint resolves | PASS |
| 21 | Rollout: existing deployments run `make build` (Layer 1-7) before first `make up`; reset SSH keys only via `podman volume rm dotfiles_ssh` (NOT `make clean`) | `make build` re-ran (Layer 1-7 new); first `make up` created `dotfiles_ssh` fresh; GPG key in `dotfiles_gnupg` survived (targeted reset not needed this phase — volume was new) | PASS |

## Invariant evidence (I-SSH1..I-SSH6)

| Invariant | Verification | Result |
|---|---|---|
| I-SSH1 | `dotfiles_ssh` named volume mounted at `~/.ssh` by `up` (no bind mount) | `Makefile:22,75` | PASS |
| I-SSH2 | Layer 1-7 pre-creates `~/.ssh` at `0700` owner-correct (`-o ${HOST_UID} -g ${HOST_GID}`) | `Containerfile:121-127`; image inspect `700 kiyama:kiyama` | PASS |
| I-SSH3 | No SSH private key baked into any image layer | image inspect `ls -A ~/.ssh | wc -l` → `0` (empty at build time) | PASS |
| I-SSH4 | `.chezmoiignore` excludes everything under `~/.ssh/` except `~/.ssh/config` (`.ssh/*` + `!.ssh/config`); keys / `known_hosts` / `config.d/*` volume-owned, never chezmoi-managed | `.chezmoiignore:46-50`; only `config` re-included | PASS |
| I-SSH5 | `make clean` removes `dotfiles_ssh` (backup warning documented in spec 25) | `Makefile:86`; spec 25 §2 notes the wipe | PASS |
| I-SSH6 | No `ssh-agent` / `SSH_AUTH_SOCK` wiring this phase | no entrypoint/zshenv change; entrypoint.sh untouched | PASS |

## Representative command output

### Image inspection (Layer 1-7 mountpoint, before any volume)

```
$ podman run --entrypoint bash --rm localhost/dotfiles-manjaro:latest -lc \
    "stat -c '%a %U:%G' /home/kiyama/.ssh && ls -A /home/kiyama/.ssh | wc -l"
700 kiyama:kiyama
0
```

The mountpoint exists at `0700` owner-correct and is empty — no key baked
(I-SSH3). `--entrypoint bash` is required because the default entrypoint exits
without the chezmoi source bind (plan-review fix).

### Smoke (acceptance #18 / #19)

```
$ podman exec dotfiles-manjaro zsh -ic 'ssh -V'
OpenSSH_10.3p1, OpenSSL 3.6.3 9 Jun 2026
$ podman exec dotfiles-manjaro zsh -c 'stat -c "%a %U:%G" ~/.ssh'
700 kiyama:kiyama
$ podman exec dotfiles-manjaro zsh -c 'ls -A ~/.ssh | wc -l'
0
```

### Manual import + persistence (acceptance #20)

```
$ ssh-keygen -t ed25519 -f /tmp/ssh_test_key -N "" -C "container-ssh-setup-test"
$ podman cp /tmp/ssh_test_key dotfiles-manjaro:/home/kiyama/.ssh/id_ed25519_test
$ podman exec dotfiles-manjaro zsh -c 'chmod 600 ~/.ssh/id_ed25519_test'
$ podman exec dotfiles-manjaro zsh -ic 'ssh-keygen -l -f ~/.ssh/id_ed25519_test'
256 SHA256:U82lzOPMAE3e047ms1LbkDa2Ady8fa3ZLuKQ0jqT4yk container-ssh-setup-test (ED25519)
$ make down && make up
$ podman exec dotfiles-manjaro zsh -ic 'ssh-keygen -l -f ~/.ssh/id_ed25519_test'
256 SHA256:U82lzOPMAE3e047ms1LbkDa2Ady8fa3ZLuKQ0jqT4yk container-ssh-setup-test (ED25519)
```

The test key survives `make down && make up` (same fingerprint) — the
`dotfiles_ssh` named volume persists across container recreation. The test
key was removed after verification.

### GPG regression (dotfiles_gnupg preserved)

```
$ podman exec dotfiles-manjaro zsh -ic 'gpg --list-secret-keys --keyid-format=long | grep -q D131EE0BBB05F21E && echo "GPG key present (preserved)"'
GPG key present (preserved)
```

The GPG key from the 2026-07-02 host-key import survives — no regression from
the new SSH volume plumbing.

## Deviations / caveats

1. **Plan-review fixes applied before implementation.** The plan's original
   `podman run <image> stat ...` image-inspection command would fail because
   the image entrypoint exits without the chezmoi source bind; fixed to
   `podman run --entrypoint bash --rm <image> -lc '...'`. The issue's
   `ssh-add -l` acceptance was also stale (contradicts the no-agent scope,
   I-SSH6) and was replaced with `ssh-keygen -l -f` / permission checks.
2. **Task-review Minor 1-2 fixed** (commit `e0d38e5`): stale Makefile `##`
   recipe annotations ("toolchain volumes" → "named volumes (cargo, rustup,
   mise, gnupg, ssh)") and spec 03 `up` row XDG phrasing (`~/.ssh` is not an
   XDG path — rephrased to "XDG data paths (...) and at ~/.ssh"). Minor 3
   (spec 25 I-SH-GM placement in §5 instead of the plan's §3) was left: it
   mirrors spec 23 §8 precedent and is an improvement.
3. **First `make up` created `dotfiles_ssh` fresh** (the volume did not exist
   before this phase), so the `podman volume rm dotfiles_ssh || true` in the
   verification was a no-op (expected). On existing deployments the rollout
   requires `make build` first (Layer 1-7 is new) per acceptance #21.
4. **No `make clean` used** in verification — it would wipe `dotfiles_gnupg`
   (the GPG key), `dotfiles_cargo`, `dotfiles_mise`, and `dotfiles_rustup`.
   Targeted `podman volume rm dotfiles_ssh` is the safe reset path (spec 21
   #21, spec 25 §2).
5. **PR review 1 tightened the `.chezmoiignore` policy.** The initial
   implementation excluded only OpenSSH conventional secret-key filename
   patterns (`id_*`, `*_ed25519`, …). PR review 1 revised this to a stricter
   single-managed-file policy: exclude everything under `~/.ssh/` except
   `~/.ssh/config` (`.ssh/*` + `!.ssh/config`). The Phase 3 build / smoke /
   persistence evidence above remains valid because no `dot_ssh/config.tmpl`
   source exists yet in either policy, so the runtime behavior (empty volume,
   no key baked, keys persist) is identical; only the declarative chezmoiignore
   scope changed. The I-SSH4 evidence row and summary were updated to the final
   policy; spec 20 I-SSH4, spec 25 §2/F1, and the deferred config issue were
   updated to the single-file model (no `config.d/chezmoi/*.conf` fragments).

## Secrecy invariants (unchanged)

- No SSH private key is baked into any image layer. The Layer 1-7 mountpoint is
  empty at build time; the keyring lives only in the runtime `dotfiles_ssh`
  named volume. The manual import flow (spec 25 §3 / design §6) uses
  `podman cp` from the host — no credential in any `RUN` (extends I4 / spec 13
  I-S4).
- The test key used for the persistence check was a throwaway ed25519
  (`container-ssh-setup-test`) generated in `/tmp` and removed from the
  container after verification. No real host key was copied.
- The `dotfiles_gnupg` named volume was preserved (no `make clean`); the GPG
  key survives.

## Deferred (separate issues)

- [`2026-07-03-ssh-container-config-setup.md`](2026-07-03-ssh-container-config-setup.md) —
  chezmoi-managed `~/.ssh/config` (Include + fragments, no YAML manifest —
  YAGNI per architect review) + GPG `[A]` SSH auth via `gpg-agent`.
- [`2026-07-03-ssh-bitwarden-import.md`](2026-07-03-ssh-bitwarden-import.md) —
  `run_after_install-ssh-keys.sh.tmpl` + `bitwardenAttachment` for automated
  file-key seeding (mirrors the GPG Bitwarden import pattern).
