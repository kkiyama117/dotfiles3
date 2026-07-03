# Phase complete — host GPG key imported into the container `dotfiles_gnupg` volume

**Date:** 2026-07-02
**Phase:** gnupg-host-key-import (runtime-only operation; no build-time change)
**Issue:** [`2026-07-02-gnupg-host-key-import.md`](2026-07-02-gnupg-host-key-import.md) → closed
**Plumbing baseline:** [`2026-07-01-phase-gnupg-container-setup.md`](2026-07-01-phase-gnupg-container-setup.md) (delivered the empty persisted keyring)
**Deferred follow-up:** [`2026-07-01-gnupg-bitwarden-import.md`](2026-07-01-gnupg-bitwarden-import.md) (Bitwarden/alternative key-management + gpgsign + real primary-key import)

## Summary

Seeded the container's `dotfiles_gnupg` Podman named volume
(`~/.local/share/gnupg` = `GNUPGHOME`) with the operator's existing host
GPG key via the manual export→`podman cp`→import path (Approach B),
without any build-time change. The container now holds the host key's
three subkeys as real secret material (`[E]` / `[S]` / `[A]`) and the
primary as a stub (`sec#`). The public keyring was auto-populated from
the secret-key import (no separate public-key file was needed — the
initial `pub.asc` export was empty and turned out to be unnecessary).
The key persists across `make down && make up`. All temporary export
artifacts were removed from both host and container. No image layer,
`Makefile`, `Containerfile`, `packages.toml`, or chezmoi source was
modified — this is a pure runtime/volume operation layered on the
plumbing delivered by the closed plumbing issue.

## Acceptance evidence

| # | Criterion | Verification | Result |
|---|---|---|---|
| S1 | Container `$GNUPGHOME` holds the operator's key after manual export→`podman cp`→import | `podman exec dotfiles-manjaro zsh -c 'gpg --list-secret-keys --keyid-format=long'` (below) | PASS |
| S2 | Container public keyring lists the operator's public key + subkeys | `podman exec dotfiles-manjaro zsh -c 'gpg --list-public-keys --keyid-format=long'` (below) | PASS |
| S3 | Key persists across `make down && make up` | `make down && make up && sleep 2` then re-list secret keys (below) | PASS |
| S4 | No key material baked into any image layer | Unchanged from the plumbing issue; this task touched no image layer (runtime/volume only) | PASS (no-op) |
| S5 | Temp export artifacts removed from host and container | `ls /tmp/*.asc /tmp/otrust.txt` → no matches on both host and container (below) | PASS |
| S6 | No build-time / source change | `git status` after the operation — only the docs (this result-log + issue + the deferred-issue note) are new; no `Makefile` / `Containerfile` / `packages.toml` / chezmoi source touched | PASS |

## Representative command output

### S1 — secret keys in the container (after import)

```
$ podman exec dotfiles-manjaro zsh -c 'gpg --list-secret-keys --keyid-format=long'
/home/kiyama/.local/share/gnupg/pubring.kbx
-------------------------------------------
sec#  ed25519/D131EE0BBB05F21E 2022-01-04 [SC]
      D21F18DB23F99E621A5060E6D131EE0BBB05F21E
uid                 [ultimate] Kouhei Kiyama (Univ) <kiyama.kouhei.54v@st.kyoto-u.ac.jp>
uid                 [ultimate] kkiyama117 (boiled) <k.kiyama117@gmail.com>
ssb   cv25519/041375FB28B3D9F0 2022-01-04 [E]
ssb   ed25519/A1E4E20240EA5BAA 2026-02-19 [S] [expires: 2031-02-18]
ssb   ed25519/B5A785FC394EE442 2026-02-19 [A]
```

`sec#` (with `#`) = the primary secret key is a **stub** (GNU-dummy);
the three `ssb` subkeys are **real** secret material. See "Deviations /
caveats" below.

### S2 — public keys in the container (derived from the secret import)

```
$ podman exec dotfiles-manjaro zsh -c 'gpg --list-public-keys --keyid-format=long | head -12'
/home/kiyama/.local/share/gnupg/pubring.kbx
-------------------------------------------
pub   ed25519/D131EE0BBB05F21E 2022-01-04 [SC]
      D21F18DB23F99E621A5060E6D131EE0BBB05F21E
uid                 [ultimate] Kouhei Kiyama (Univ) <kiyama.kouhei.54v@st.kyoto-u.ac.jp>
uid                 [ultimate] kkiyama117 (boiled) <k.kiyama117@gmail.com>
sub   cv25519/041375FB28B3D9F0 2022-01-04 [E]
sub   ed25519/A1E4E20240EA5BAA 2026-02-19 [S] [expires: 2031-02-18]
sub   ed25519/B5A785FC394EE442 2026-02-19 [A]
```

The public key was **not** imported from a separate file — GnuPG
derived it from the secret-key import. (The `pub.asc` produced by the
first `gpg --armor --export` attempt was 0 bytes because the host
`pubring.kbx` lacks the operator's own public-key record; see
"Deviations / caveats". Importing `sec.asc` alone was sufficient.)

### S3 — persistence across `make down && make up`

```
$ make down && make up && sleep 2
$ podman exec dotfiles-manjaro zsh -c 'gpg --list-secret-keys --keyid-format=long'
/home/kiyama/.local/share/gnupg/pubring.kbx
-------------------------------------------
sec#  ed25519/D131EE0BBB05F21E 2022-01-04 [SC]
      D21F18DB23F99E621A5060E6D131EE0BBB05F21E
uid                 [ultimate] Kouhei Kiyama (Univ) <kiyama.kouhei.54v@st.kyoto-u.ac.jp>
uid                 [ultimate] kkiyama117 (boiled) <k.kiyama117@gmail.com>
ssb   cv25519/041375FB28B3D9F0 2022-01-04 [E]
ssb   ed25519/A1E4E20240EA5BAA 2026-02-19 [S] [expires: 2031-02-18]
ssb   ed25519/B5A785FC394EE442 2026-02-19 [A]
```

The `dotfiles_gnupg` named volume retained the keyring across the
restart (the volume is unmounted/remounted, not removed, by
`make down`/`make up`; `make clean` would remove it — by design).

### S5 — temporary artifacts removed

```
$ podman exec dotfiles-manjaro zsh -c 'rm -f /tmp/pub.asc /tmp/sec.asc /tmp/otrust.txt && ls /tmp/*.asc /tmp/otrust.txt'
zsh:1: no matches found: /tmp/*.asc
$ rm -f /tmp/pub.asc /tmp/sec.asc /tmp/otrust.txt   # host side
$ ls /tmp/*.asc /tmp/otrust.txt
ls: '/tmp/*.asc' にアクセスできません: そのようなファイルやディレクトリはありません
ls: '/tmp/otrust.txt' にアクセスできません: そのようなファイルやディレクトリはありません
```

## Procedure actually followed

1. **Host export** (interactive; pinentry prompted for the primary's
   passphrase):
   ```bash
   gpg --armor --export-secret-keys D21F18DB23F99E621A5060E6D131EE0BBB05F21E > /tmp/sec.asc
   gpg --export-ownertrust > /tmp/otrust.txt
   gpg --armor --export D21F18DB23F99E621A5060E6D131EE0BBB05F21E > /tmp/pub.asc   # → 0 bytes; not needed
   ```
2. **Transfer** (repo not used as a relay, to avoid secret material
   landing in the source tree):
   ```bash
   podman cp /tmp/sec.asc  dotfiles-manjaro:/tmp/sec.asc
   podman cp /tmp/otrust.txt dotfiles-manjaro:/tmp/otrust.txt
   ```
3. **Container import** (interactive; pinentry prompted for the
   passphrase):
   ```bash
   podman exec -it dotfiles-manjaro zsh -c 'gpg --import /tmp/sec.asc && gpg --import-ownertrust /tmp/otrust.txt'
   ```
4. **Verify + persistence** + **cleanup** as in S1–S5 above.

## Deviations / caveats

1. **Primary key imported as a stub (`sec#`).** The exported `sec.asc`
   carried the primary secret-key packet as a GNU-dummy stub
   (`plen=59`, S2K GNU-dummy) and only the subkey packets as real
   secret material — i.e. an `--export-secret-subkeys`-shaped export,
   not a full `--export-secret-keys` export. The container therefore
   has real `[E]` / `[S]` / `[A]` subkeys but **no real primary
   secret**. This is functional for all daily operations (signing,
   encryption, SSH-via-gpg auth) and matches the recommended
   "primary-offline" posture; primary-only operations (add/revoke
   UIDs, revoke, re-certify) remain host-side. **Importing the real
   primary is deferred** to the Bitwarden/alternative key-management +
   gpgsign setup (see the deferred follow-up issue), per operator
   decision 2026-07-02.
2. **`pub.asc` was empty (0 bytes) and unnecessary.** The host
   `~/.local/share/gnupg/pubring.kbx` does not contain the operator's
   own public-key record (only third-party public keys), so
   `gpg --armor --export <fingerprint>` on the host could not find a
   stored public key and — when the gpg-agent did not have the primary
   unlocked/cached — produced "nothing exported" / a 0-byte file. This
   was harmless: importing `sec.asc` alone auto-populated the public
   keyring (S2). The host `pubring.kbx` anomaly is a separate
   host-side cleanup, out of scope for this task (see the issue Notes).
3. **No design / plan / review pass.** This was a one-shot, runtime-only
   operational procedure with no build-time or source change, so the
   full spec-00 lifecycle (design → review → plan) did not apply — the
   plumbing issue already went through that lifecycle for the
   build-time wiring. This result-log exists for the same reason the
   plumbing issue's did: no-PR environment evidence retention (spec 00
   §6.6 / AGENTS.md). The secrecy invariants (no key in any image
   layer; no new secret transport) are unchanged from the plumbing
   baseline.

## Secrecy invariants (unchanged)

- No GPG key material is baked into any image layer (S4). The keyring
  lives only in the runtime `dotfiles_gnupg` named volume.
- No new secret transport was introduced — the manual export/import is
  operator-driven, one-time, and the export artifacts were scrubbed
  (S5). The Bitwarden key-import automation remains deferred.
- No secret-store daemon was added (unchanged from the plumbing issue;
  `gnome-keyring` / a `libsecret` service is still not installed).