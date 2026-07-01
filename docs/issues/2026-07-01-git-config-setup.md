# git config setup (chezmoi-managed `~/.config/git/{config,ignore}` + delta + GPG signing)

**Date:** 2026-07-01
**Status:** open
**Related:** [design](../specifications/implementations/2026-07-01-git-config-setup-design.md), [plan](../plans/2026-07-01-git-config-setup-impl.md), deferred [gnupg-bitwarden-import](2026-07-01-gnupg-bitwarden-import.md)

## Context

The host already runs a working global git config at `~/.config/git/config`
(997 B, ~35 settings: delta pager, `credential.helper=libsecret`, GPG signing
with `user.signingkey=A1E4E20240EA5BAA`, nvim editor, worktree aliases,
pull/push/merge tuning) and a 709-line global gitignore at
`~/.config/git/ignore` (toptal-generated, purely generic — no personal
entries). Neither is managed by this repo yet.

The user has started the migration in commit `2d8836a`:

- added `.chezmoidata/git_config.yaml` with a data model
  `git.identity_default.{name,email,signingkey}` (`signingkey: TODO`) and an
  empty `git.identities: {}` (reserved for future per-host identities); the
  file comment reads "make template and manage per-each user, when this repo
  is shared";
- added `.chezmoidata/*.yaml` to `.chezmoiignore` (so the data dir is not
  applied as a target);
- the `.chezmoiignore` "Git-related files" block carries a
  `!.config/git/gitignore` exception, but the real global-ignore file is
  `~/.config/git/ignore` (no `git` prefix) and is not matched by any ignore
  pattern — so that exception is a dead no-op;
- `docs/references/host_config_list.md` §5 marks
  `~/.config/git/config` → `dot_config/git/config.tmpl` ("テンプレ化済み")
  and lists `.chezmoiscripts/run_after_install-{gh-hosts,git-credentials,
  gpg-signing,ssh-keys}.sh.tmpl` as "新リポジトリ側" — **but none of these
  files exist yet** (`dot_config/` has only `zsh/`; `.chezmoiscripts/` has
  only `.gitkeep`). The doc is aspirational; the templates are what this
  issue creates.

Two host/container divergence points exist:

- `core.pager = delta` / `pager.* = delta` reference the `delta` binary,
  which is installed on the host (`git-delta 0.19.2-2`, Arch `extra`) but
  **not declared in `dependencies/packages.toml`** — so the container would
  lack it.
- `credential.helper = libsecret` needs a secret-service daemon (the host
  has one; the container deliberately does not — see spec 20 I-GPG9 / the
  gnupg setup that pulled `libsecret` only as a `pinentry` library, no
  `gnome-keyring`). The repo has **no host/container flag** today:
  `build_mode` (in `.chezmoi.toml.tmpl`, driven by the `BUILD_MODE` env)
  distinguishes only build-time vs runtime, not host vs container (both
  run with `build_mode=false` at runtime).

Commit signing is orthogonal to `credential.helper` and already works on
the host (GPG, `commit.gpgsign=true`, `gpg.format` unset → openpgp default).
The gnupg container setup (named volume `dotfiles_gnupg`, deferred
Bitwarden key import) was built precisely for in-container signing.

## Problem

Bring `~/.config/git/config` and `~/.config/git/ignore` under chezmoi
management in this repo, wired to `.chezmoidata/git_config.yaml`, so the
config is reproducible across host and container — without baking any
secret into image layers, without leaving broken references (`delta` /
`libsecret`) in the container, and keeping commit signing via GPG (reusing
the gnupg work).

## Acceptance criteria

- **S1** `.chezmoidata/git_config.yaml` `signingkey` is filled with the
  real public GPG subkey ID `A1E4E20240EA5BAA` (public; spec 13 permits
  plain text).
- **S2** `dot_config/git/config.tmpl` exists, ports the full host config,
  injects `[user] name/email/signingkey` from `{{ .git.identity_default.* }}`,
  adds `gpg.format = openpgp` (explicit), and gates
  `credential.helper = libsecret` to host runtime only.
- **S3** `dot_config/git/ignore` exists and is a verbatim port of the host
  709-line global gitignore (verified generic — no personal entries).
- **S4** `.chezmoiignore`'s dead `!.config/git/gitignore` exception is
  removed (`~/.config/git/ignore` is managed by default; no exception
  needed).
- **S5** `.chezmoi.toml.tmpl` `[data]` gains
  `runtime = {{ env "DOTFILES_RUNTIME" | default "host" | quote }}`;
  `entrypoint.sh` exports `DOTFILES_RUNTIME=container` before rendering the
  runtime chezmoi config.
- **S6** `git-delta` is declared in `dependencies/packages.toml`
  (`manager = "pacman"`, `layer = 1`); `make gen-deps` regenerates
  `dependencies/layer_1/pacman.txt` and the spec 02 AUTO-GEN block; the
  generator test suite passes (no regression).
- **S7** In the container (`make up`): `git config --get credential.helper`
  is empty; `git config --get user.signingkey` = `A1E4E20240EA5BAA`;
  `commit.gpgsign` = `true`; `gpg.format` = `openpgg`;
  `git config --get core.pager` = `delta`; `delta --version` works
  (installed via Layer 1).
- **S8** A host-mode template render (via `chezmoi execute-template` with a
  freshly-rendered `runtime=host` config) yields
  `credential.helper = libsecret` and `user.signingkey = A1E4E20240EA5BAA`;
  a `runtime=container` render yields no `credential.helper` line but
  keeps `user.signingkey`.
- **S9** `chezmoi managed -S .` lists `.config/git/config` and
  `.config/git/ignore` (both managed; not ignored).
- **S10** spec 01 records `dot_config/git/{config.tmpl,ignore}` and
  `.chezmoidata/git_config.yaml`; spec 02 gains `git-delta` (AUTO-GEN);
  spec 20 records the `DOTFILES_RUNTIME` host/container flag; spec 13's
  signingkey/email plain-text allowance is confirmed (no change needed).
- **S11** GPG signing is not gated off in the container
  (`commit.gpgsign=true` everywhere): a test commit on the host signs OK;
  the container signs once the GPG key is imported (deferred Bitwarden
  issue) — until then it fails loudly (clear signal to import), not silently
  disabled.

## Notes

- Scope chosen (brainstorming 2026-07-01): **B** (templates + divergence
  handling) + **GPG signing** (Q3-A). Deferred: the
  `.chezmoiscripts/run_after_install-{gh-hosts,git-credentials,
  gpg-signing,ssh-keys}.sh.tmpl` run-scripts, the `identities` per-host
  map, and SSH signing.
- The host/container flag is a generally useful primitive (future
  host/container-divergent settings can reuse `.runtime`); `delta` needs
  no flag once the package is added.
- `git-credential-libsecret` ships with the `git` package itself
  (`/usr/lib/git-core/git-credential-libsecret`); `libsecret` the library
  arrives via `pinentry` (gnupg setup). Neither pulls a keyring daemon.