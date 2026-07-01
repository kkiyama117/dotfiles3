# git config setup (chezmoi-managed `~/.config/git/{config,ignore}` + delta + GPG signing) — Design

**Status:** DRAFT
**Date opened:** 2026-07-01
**Issue:** [`../../issues/2026-07-01-git-config-setup.md`](../../issues/2026-07-01-git-config-setup.md)
**Author:** kiyama

## §1 Context & success criteria

See the [issue](../../issues/2026-07-01-git-config-setup.md) for the full
context. In short: the host runs `~/.config/git/config` (997 B) +
`~/.config/git/ignore` (709 lines, generic); neither is chezmoi-managed
here. Commit `2d8836a` seeded `.chezmoidata/git_config.yaml`
(`git.identity_default.{name,email,signingkey=TODO}` + empty
`git.identities`). `delta` is host-installed but not in `packages.toml`;
`credential.helper=libsecret` needs a keyring daemon the container lacks;
the repo has no host/container flag (`build_mode` is build-time vs
runtime only).

Success criteria (labeled for review cross-reference; mirror the issue):

- **S1** `signingkey` filled with `A1E4E20240EA5BAA` (public).
- **S2** `dot_config/git/config.tmpl` ports the full host config; `[user]`
  from data; `gpg.format = openpgp` explicit; `credential.helper` gated.
- **S3** `dot_config/git/ignore` = verbatim host global gitignore (generic).
- **S4** dead `!.config/git/gitignore` exception removed from
  `.chezmoiignore`.
- **S5** `.chezmoi.toml.tmpl` `runtime` data var + `entrypoint.sh`
  `DOTFILES_RUNTIME=container`.
- **S6** `git-delta` in `packages.toml` Layer 1; `make gen-deps` regen;
  generator tests pass.
- **S7** container: no `credential.helper`; signing settings + delta
  present + `delta --version` works.
- **S8** host-mode render has `credential.helper=libsecret`; container-mode
  render omits it; both keep `user.signingkey`.
- **S9** `chezmoi managed -S .` lists `.config/git/{config,ignore}`.
- **S10** specs 01/02/20 updated; spec 13 confirmed.
- **S11** signing not gated off in container; host test commit signs OK.

## §2 Alternatives considered

- **Scope (Q1).** A minimal (templates only) / B templates + divergence
  handling / C B + signing run-script. Chosen **B**: it is the smallest
  scope that makes the config actually work in both host and container
  (adds `delta`, gates `libsecret`), without pulling in the secret-touching
  run-scripts (gh-hosts/git-credentials/ssh-keys) which belong to the
  deferred Bitwarden/SSH-key work. A leaves `delta`/`libsecret` as broken
  container references; C widens scope into secret transport prematurely.
- **`credential.helper` (Q2).** A graceful no-op (write it everywhere; in
  the container it errors and git falls back) / B explicit `runtime` flag /
  C container uses `store`/`cache`. Chosen **B**: the user's scope-B intent
  was "container omits libsecret", which requires gating, which requires a
  host/container signal — `build_mode` alone cannot provide it (it is
  build-time vs runtime, and both host and container run with
  `build_mode=false`). The `runtime` flag is a clean, explicit, reusable
  primitive. A leaves a broken reference in the container config (contrary
  to the chosen scope); C bakes a plaintext credential store into the
  container (a new secret-adjacent surface, against the secret-free
  direction).
- **Signing method (Q3).** A GPG / B SSH / C both (template switch). Chosen
  **A (GPG)**: the host already signs with GPG (`commit.gpgsign=true`,
  `user.signingkey=A1E4E20240EA5BAA`, openpgp), and the just-completed
  gnupg container setup (`dotfiles_gnupg` named volume + deferred
  Bitwarden key import) was built for exactly this. SSH signing would
  orphan the gnupg work and require a separate SSH-key runtime injection
  (the deferred `run_after_install-ssh-keys.sh.tmpl`). C adds template
  complexity for no current need (YAGNI).

## §3 Architecture / Invariants

- **I-GIT1** — `~/.config/git/config` is rendered from
  `dot_config/git/config.tmpl` by chezmoi; `[user] name/email/signingkey`
  are injected from `.chezmoidata/git_config.yaml`
  (`{{ .git.identity_default.* }}`). The data file is the single source of
  identity; the template is the single source of the *structure*.
- **I-GIT2** — `~/.config/git/ignore` is a static chezmoi-managed file
  (`dot_config/git/ignore`, no template): it is a verbatim port of the host
  global gitignore, which contains only generic toptal patterns (no
  personal/secret entries — verified). It is read by git via the XDG
  default `core.excludesFile` (`$XDG_CONFIG_HOME/git/ignore`, host has
  `core.excludesFile` unset → XDG default).
- **I-GIT3** — `credential.helper = libsecret` is gated to **host runtime
  only** by `{{ if and (not .build_mode) (eq .runtime "host") }}`. The
  container has no keyring daemon (spec 20 I-GPG9); writing the line there
  would be a broken reference. Build-time prepass (`build_mode=true`) also
  omits it (the image never carries `libsecret` as a credential helper).
- **I-GIT4** — `commit.gpgsign = true`, `gpg.format = openpgp`, and
  `user.signingkey` are rendered in **all modes** (build + host runtime +
  container runtime). Signing is **not** gated by `runtime`: once the GPG
  key is imported into the container's `dotfiles_gnupg` volume (deferred
  Bitwarden issue), the container signs automatically. Gating signing off
  in the container would silently disable it even after the key arrives.
- **I-GIT5** — No secret is baked into any image layer. `user.email` and
  `user.signingkey` (a public key ID) are acceptable plain text (spec 13);
  they are already public in the committed `.chezmoidata/git_config.yaml`.
  The GPG *secret* key is never baked (it lives only in the runtime
  `dotfiles_gnupg` volume — spec 20 I-GPG4). This extends spec 20 I4 / spec
  13 I-S4.
- **I-GIT6** — `delta` is provided by the `git-delta` Arch `extra` package,
  declared in `packages.toml` Layer 1, so `core.pager=delta` /
  `pager.*=delta` work identically in host and container. No gating needed
  for delta.
- **I-GIT7** — The `runtime` chezmoi data var (`host` | `container`,
  default `host`) is driven by the `DOTFILES_RUNTIME` env var in
  `.chezmoi.toml.tmpl`. Only `entrypoint.sh` sets it (to `container`); the
  build prepass does not need to (build_mode=true already suppresses the
  gated line). The host never sets it (defaults to `host`).

## §4 Scope / staging breakdown

Six mechanical change areas, each independently reviewable (one commit
each, doc-mgmt §6.5):

1. **`.chezmoidata/git_config.yaml`** — fill `signingkey: A1E4E20240EA5BAA`.
2. **`dot_config/git/config.tmpl`** (create) — port the host config; inject
   `[user]` from data; add `gpg.format = openpgp`; gate
   `credential.helper`. **`dot_config/git/ignore`** (create) — verbatim
   host global gitignore.
3. **`.chezmoiignore`** — remove the dead `!.config/git/gitignore`
   exception. **`.chezmoi.toml.tmpl`** — add the `runtime` data var.
   **`entrypoint.sh`** — export `DOTFILES_RUNTIME=container`.
4. **`dependencies/packages.toml`** — add `git-delta` (Layer 1 pacman);
   `make gen-deps` regenerates `layer_1/pacman.txt` + spec 02 AUTO-GEN.
5. **Spec sync** — spec 01 (tree), spec 20 (`DOTFILES_RUNTIME` note),
   spec 13 (signingkey/email confirmation); spec 02 is AUTO-GEN by Task 4.
6. **End-to-end smoke gate + result-log + close issue.**

## §5 Implementation detail

### §5.1 `.chezmoidata/git_config.yaml`

Change only the `signingkey` value (`TODO` → the real public subkey ID):
```yaml
git:
    identity_default:
        name: kkiyama117
        email: k.kiyama117@gmail.com
        signingkey: A1E4E20240EA5BAA
    identities: {}
```
The file's leading `# TODO: make template ...` comment is kept (it scopes
the future per-user templating, which is out of scope here).

### §5.2 `dot_config/git/config.tmpl`

Port the host `~/.config/git/config` verbatim (the `;`-comment lines, the
`[delta]` theming, the worktree aliases), with three changes:

- `[user]` values come from data;
- a new explicit `[gpg] format = openpgp` block;
- the `credential.helper = libsecret` block wrapped in the host-runtime gate.

```ini
; main
[core]
  editor = nvim
  pager = delta
  quotepath = false
  autocrlf = input
[user]
  name = {{ .git.identity_default.name }}
  email = {{ .git.identity_default.email }}
  signingkey = {{ .git.identity_default.signingkey }}

[init]
  defaultBranch = main
[commit]
  verbose = true
  gpgsign = true
[gpg]
  format = openpgp
[pull]
  rebase = false
  ff = only
[push]
  default=current

; worktree shortcuts (used by /branch-out flow + manual ops)
[alias]
  wt = worktree
  wtl = worktree list
  wta = worktree add -b

{{ if and (not .build_mode) (eq .runtime "host") }}
; cred — libsecret (host has a keyring daemon; the container does not, so
; this section is host-runtime only; see I-GIT3)
[credential]
  helper = libsecret
{{ end }}
; pager
[diff]
  colorMoved = default
[merge]
  conflictStyle = diff3
  ff = false
[pager]
  blame = delta
  diff = delta
; log = delta
  reflog = delta
  show = delta
[interactive]
  diffFilter = delta --color-only
[delta]
  keep-plus-minus-markers = true
  plus-style = syntax "#012800"
  minus-style = normal "#340001"
  syntax-theme = "Monokai Extended"
  hunk-header-style = omit
  diff-so-fancy = true
  line-numbers = true
  side-by-side = true
  navigate = true
  hyperlinks = true
  dark = true
```

Trailing whitespace from the host file (e.g. after `plus-style`/`minus-style`
values) is trimmed — cosmetic; the functional content is identical.

### §5.3 `dot_config/git/ignore`

Static file, no template. Created by copying the host file and verifying
it is generic:
```bash
cp ~/.config/git/ignore dot_config/git/ignore
test "$(wc -l < dot_config/git/ignore)" -eq 709
! grep -niE 'kiyama|/home/|/data/|@[a-z]+\.[a-z]+|token|secret' dot_config/git/ignore
```
(The host file is 709 lines, all toptal-generated generic patterns; the
grep must find nothing.)

### §5.4 `.chezmoiignore`

Remove the dead exception line `!.config/git/gitignore` from the
"Git-related files" block. `~/.config/git/ignore` is not matched by any
ignore pattern (`**/.gitignore` matches `.gitignore` files, not `ignore`),
so it is managed by default — no exception is needed, and the existing
line targets a non-existent `~/.config/git/gitignore` (a no-op).

### §5.5 `.chezmoi.toml.tmpl` + `entrypoint.sh`

`.chezmoi.toml.tmpl` `[data]`:
```toml
[data]
build_mode = {{ if eq (env "BUILD_MODE" | default "false") "true" }}true{{ else }}false{{ end }}
runtime = {{ env "DOTFILES_RUNTIME" | default "host" | quote }}
```
(`quote` renders `runtime = "host"` / `runtime = "container"`.)

`entrypoint.sh`, immediately before the `chezmoi execute-template --init`
call that renders the runtime chezmoi config:
```bash
# Mark this chezmoi apply as running inside the container. build_mode is
# already false here (BUILD_MODE unset at runtime); DOTFILES_RUNTIME
# distinguishes container runtime from host runtime for settings that must
# not appear in the container (e.g. credential.helper=libsecret — the
# container has no keyring daemon; see dot_config/git/config.tmpl I-GIT3).
export DOTFILES_RUNTIME=container
```
No `Containerfile` change: the build prepass runs with `build_mode=true`,
which already suppresses the gated line (the `and (not .build_mode) ...`
short-circuits).

### §5.6 `packages.toml`

Insert `git-delta` in the Layer 1 alphabetical position (between `git` and
`gnupg`):
```toml
[[tool]]
name = "git-delta"
manager = "pacman"
layer = 1
has_configs = false
description = "git-delta — syntax-highlighting pager for git diff/blame/log (core.pager/pager.* in ~/.config/git/config)"
```
`has_configs = false`: delta is configured entirely through the git config
(`[delta]` block), not its own config file.

### §5.7 Verification

- `make gen-deps` → `layer_1/pacman.txt` contains `git-delta`; spec 02
  AUTO-GEN lists it; `python3 -m pytest -q` in `programs/generate_deps`
  passes (15 tests).
- `chezmoi managed -S .` lists `.config/git/config` and `.config/git/ignore`.
- Host-mode render (no apply, no clobber of the real home):
  `chezmoi execute-template --init < .chezmoi.toml.tmpl > /tmp/c.toml` then
  `chezmoi execute-template --config /tmp/c.toml --source . <
  dot_config/git/config.tmpl` → contains `credential.helper = libsecret`
  and `user.signingkey = A1E4E20240EA5BAA`.
- Container-mode render: `DOTFILES_RUNTIME=container chezmoi
  execute-template --init < .chezmoi.toml.tmpl > /tmp/cc.toml` then render
  with `--config /tmp/cc.toml` → **no** `credential.helper` line, still has
  `user.signingkey`.
- `make build && make up` →
  `podman exec dotfiles-manjaro zsh -c 'git config --get credential.helper; git config --get user.signingkey; git config --get gpg.format; delta --version'`
  → empty / `A1E4E20240EA5BAA` / `openpgp` / `delta 0.19.x`.
- Host signing: `git -c user.email=t@t -c user.name=t commit --allow-empty
  -m t --gpg-sign` in a scratch repo signs OK.

## §6 Open questions

- **Q1 (scope)** — Resolved: **B** (templates + divergence handling), no
  run-scripts.
- **Q2 (credential.helper)** — Resolved: **B** (`runtime` flag), not
  graceful no-op and not a container `store`/`cache`.
- **Q3 (signing method)** — Resolved: **A** (GPG), reusing the gnupg
  container setup; SSH signing and the `identities` per-host map deferred.
- **Q4 (bake identity into image?)** — Resolved: yes, acceptable. Email +
  public signingkey are already public in the committed data file (spec 13
  permits plain text); baking them into the image adds no new exposure, and
  the GPG *secret* key is never baked (I-GIT5). The alternative (gate
  `[user]` to runtime-only so the image is identity-free) adds template
  complexity for no secrecy benefit, since the data file is already in the
  public repo.