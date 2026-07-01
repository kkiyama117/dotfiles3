# Phase complete — gnupg in the container (named volume at `GNUPGHOME`)

**Date:** 2026-07-01
**Phase:** gnupg-container-setup (implementation)
**Plan:** [`../plans/2026-07-01-gnupg-container-setup-impl.md`](../plans/2026-07-01-gnupg-container-setup-impl.md)
**Issue:** [`2026-07-01-gnupg-container-setup.md`](2026-07-01-gnupg-container-setup.md) → closed
**Design:** [`../specifications/implementations/2026-07-01-gnupg-container-setup-design.md`](../specifications/implementations/2026-07-01-gnupg-container-setup-design.md)

## Summary

Installed `gnupg` + `pinentry` (Layer 1, pacman, declared in `packages.toml`),
baked `~/.local/share/gnupg` (`0700`, owner-correct) as a Layer 1-6
mountpoint, wired the `dotfiles_gnupg` Podman named volume there (Makefile
`make up` mount + `make clean` removal), and excluded `.local/share/gnupg`
from chezmoi. gpg runs on defaults (no chezmoi-managed `gpg.conf` /
`gpg-agent.conf` in this phase); `gpg-agent`/`pinentry` are runtime,
on-demand only. No GPG key material is baked into any image layer — the
keyring lives only in the runtime `dotfiles_gnupg` named volume (extends
spec 20 I4 / spec 13 I-S4). `libsecret` arrives only as a hard dependency
of `pinentry` (library, not the `gnome-keyring` daemon), preserving the
Bitwarden-only secret model (spec 13 §2 Tier 1).

## Acceptance evidence (S1–S10)

| # | Criterion | Verification | Result |
|---|---|---|---|
| S1 | `gnupg`+`pinentry` in `packages.toml` → `layer_1/pacman.txt` + spec 02 | `make gen-deps` idempotent (`txt_written=0 doc_updated=False`); `layer_1/pacman.txt` = 11 pkgs incl. `gnupg`/`pinentry`; spec 02 AUTO-GEN rows present; 15 generator tests pass | PASS |
| S2 | `~/.local/share/gnupg` `0700` owner-correct (Layer 1-6) | `stat -c '%a %U:%G'` → `700 kiyama:kiyama` (verified at `--target toolchain` and at `make up` runtime) | PASS |
| S3 | named volume `dotfiles_gnupg` wired in Makefile | `make -n up`/`make -n clean` include `dotfiles_gnupg`; runtime mount exercised by `make up` (key written into the volume, persisted) | PASS |
| S4 | `gpg --version` / `gpg-agent --version` / `$GNUPGHOME` after `make up` | `gpg (GnuPG) 2.4.9`; `gpg-agent (GnuPG) 2.4.9`; `GNUPGHOME=/home/kiyama/.local/share/gnupg` | PASS |
| S5 | `make down && make up` preserves a generated test key | generated `test@example.com` (`sec ed25519` + `ssb cv25519`); after `down && up`, `gpg --list-secret-keys` still lists `test@example.com` | PASS |
| S6 | `~/.local/share/gnupg` `0700` + `${USERNAME}`-owned at runtime | `stat` → `700 kiyama:kiyama` (not root-owned; gpg strict perms satisfied) | PASS |
| S7 | `.chezmoiignore` lists `.local/share/gnupg` | `chezmoi managed -S /data/dotfiles3` → `.local/share/gnupg` `NOT_MANAGED` (consistent with cargo/rustup/mise) | PASS |
| S8 | no key material baked into any image layer | `podman run --rm` (no volume) → `GNUPGHOME dir EMPTY in image (no key baked)` | PASS |
| S9 | no secret-store daemon | `gnome-keyring` NOT installed; `gnome-keyring-daemon` NOT PRESENT; `pinentry` `Depends On` = `glibc ncurses libassuan libsecret glib2` (libsecret = library only) | PASS |
| S10 | specs 01/02/20/21/22 updated | spec 20 I-GPG1..5 + libsecret NOTE; spec 21 Layer 1-6 row + acceptance #12; spec 22 volume note; spec 02 AUTO-GEN (gen-deps); spec 01 verified no-op (volumes are spec 22's domain) | PASS |

### No-regression (existing spec 21 acceptance 5–9)

```
$CARGO_HOME                 → /home/kiyama/.local/share/cargo   (XDG)
chezmoi source bind .git    → BIND_OK
paru --version              → paru v2.1.0 - libalpm v16.0.1
nvim --version (AUR)        → NVIM v0.13.0-dev-881+gc040f53dc1
rustc --version (after down/up) → rustc 1.96.1 (toolchain volumes persisted)
```

### Teardown (plan Step 6.9)

`make clean` removed the `dotfiles_gnupg` volume (`REMOVED`) and the image
(`IMAGE_REMOVED`) — the `make clean` volume-removal wiring is verified.

## Commit trail

1. `5baabc6` — docs: raise gnupg container setup issue + design + deferred Bitwarden-import issue
2. `d21e08c` — docs: add gnupg-container-setup implementation plan
3. `750fc0c` — feat(deps): add gnupg + pinentry (layer 1) to packages.toml; regenerate layer_1/pacman.txt
4. `4b7d0ca` — feat(container): bake 0700 GNUPGHOME mountpoint (Layer 1-6)
5. `44d13db` — feat(make): mount dotfiles_gnupg named volume; clean removes it
6. `61b6b39` — feat(chezmoi): ignore .local/share/gnupg (keyring never managed)
7. `5e06519` — docs(spec-20/21/22): record dotfiles_gnupg volume + Layer 1-6 + I-GPG invariants
8. `9404364` — docs: file paru/AUR resolution regression issue; annotate gnupg issue (plumbing done, runtime gate blocked)

(Hashes are post-rebase; the branch `gnupg_container` was rebased onto
`develop` to pick up the paru `${=pkgs}` word-split fix before the runtime
smoke gate was run.)

## Deviations from plan

1. **Spec 01 was verify-only (no edit).** The design §4 item 5 listed spec 01
   for a "named-volumes description" edit, but spec 01 governs the repo file
   structure and does not enumerate runtime named volumes or Layer 1-5/1-6
   directories (those live in spec 22 / spec 21). Corrected to verify-only;
   the design intent (record the new volume somewhere normative) is satisfied
   by the spec 22 edit. (Plan File Structure table noted this correction.)
2. **Plan Step 4.2 host `chezmoi managed` was the wrong chezmoi source.** The
   host's `chezmoi source-path` is `/home/kiyama/.local/share/chezmoi`
   (a separate directory, not this repo), so a bare `chezmoi managed`
   reflected the host's source, not this repo. Re-verified with
   `chezmoi managed -S /data/dotfiles3` (the source the container
   bind-mounts), which correctly showed `.local/share/gnupg` `NOT_MANAGED`.
3. **Task 6 ordering: Step 6.10 (no-regression) ran before Step 6.9 (teardown).**
   The plan placed `make clean` (6.9, which removes the image) before the
   no-regression `make up` checks (6.10), which would have required a
   needless rebuild. Ran 6.10 on the already-running container, then 6.9 as
   the final teardown. No acceptance impact.
4. **Runtime gate was blocked, then unblocked by a `develop` fix.** The
   initial `make build` (cache-bust from the Layer 1 gnupg/pinentry change)
   failed at the `aur` stage with `paru -S` reporting `could not find all
   required packages: neovim-git starship tmux (target)`. Root cause
   (fixed in `develop` commit `a115677` "word-split $pkgs"): zsh does not
   word-split a bare unquoted parameter, so `$pkgs` was passed to
   `paru -S` as one malformed target; the fix uses zsh's `${=pkgs}` split
   operator. After rebasing `gnupg_container` onto `develop`, the full build
   passed and the runtime smoke gate (S3/S5/S6) completed. The regression is
   tracked and closed in
   [`2026-07-01-paru-aur-resolution-regression.md`](2026-07-01-paru-aur-resolution-regression.md).

## Secrecy invariants (unchanged by this change)

- No GPG key material in any image layer (S8); the keyring lives only in the
  runtime `dotfiles_gnupg` named volume.
- No new secret transport introduced — keys are generated/imported at runtime
  only; the Bitwarden key-import automation is deferred to
  [`2026-07-01-gnupg-bitwarden-import.md`](2026-07-01-gnupg-bitwarden-import.md).
- No secret-store daemon (`gnome-keyring` / `libsecret` service) installed
  (S9).