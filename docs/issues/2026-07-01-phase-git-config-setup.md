# Phase result-log: git config setup (chezmoi-managed `~/.config/git/{config,ignore}` + `git-delta` + GPG signing)

**Date:** 2026-07-01
**Plan:** [`../plans/2026-07-01-git-config-setup-impl.md`](../plans/2026-07-01-git-config-setup-impl.md)
**Parent issue:** [`2026-07-01-git-config-setup.md`](2026-07-01-git-config-setup.md)
**Branch:** `git_config` (rebased onto `mise-managed-languages` `9bafea6` before the smoke gate, per user)
**Worktree:** `/data/dotfiles3/.worktrees/git_config`

## Acceptance evidence (S1–S11)

| ID | Criterion | Verification (command → output) | Result |
|---|---|---|---|
| S1 | `signingkey` filled with public GPG subkey ID | `chezmoi execute-template` of `{{ .git.identity_default.signingkey }}` → `A1E4E20240EA5BAA` | PASS |
| S2 | `dot_config/git/config.tmpl` ports host config; identity from data; `gpg.format=openpgp`; `credential.helper` host-gated | `grep` of `config.tmpl` → `signingkey = {{ .git.identity_default.signingkey }}`, `format = openpgp`, `{{ if and (not .build_mode) (eq .runtime "host") }}[credential]...{{ end }}` | PASS |
| S3 | `dot_config/git/ignore` = verbatim host global gitignore, 709 lines, no personal entries | `wc -l` → `709`; `grep -ciE 'kiyama\|/home/\|/data/\|@[a-z]+\.[a-z]+'` → `0` | PASS |
| S4 | dead `!.config/git/gitignore` exception removed from `.chezmoiignore` | `grep -c '!.config/git/gitignore' .chezmoiignore` → `0` | PASS |
| S5 | `.chezmoi.toml.tmpl` `runtime` var + `entrypoint.sh` `DOTFILES_RUNTIME=container` | `grep runtime .chezmoi.toml.tmpl` → `runtime = {{ env "DOTFILES_RUNTIME" \| default "host" \| quote }}`; `grep DOTFILES_RUNTIME entrypoint.sh` → `export DOTFILES_RUNTIME=container`; render → `runtime = "host"` / `"container"` | PASS |
| S6 | `git-delta` in `packages.toml` Layer 1; `make gen-deps` regen; generator tests pass | `layer_1/pacman.txt` L11 `git-delta`; spec 02 AUTO-GEN row; `make gen-deps` idempotent (`txt_written=0`); `pytest` → `24 passed` (15 original + 9 mise) | PASS |
| S7 | container: no `credential.helper`; signing settings + delta present | `podman exec ... git config --get ...` → `credential.helper=[]`, `user.signingkey=[A1E4E20240EA5BAA]`, `commit.gpgsign=[true]`, `gpg.format=[openpgp]`, `core.pager=[delta]`, `user.name=[kkiyama117]`, `user.email=[k.kiyama117@gmail.com]`; `delta --version` → `delta 0.19.2` | PASS |
| S8 | host-mode render has `libsecret`; container-mode render omits it; both keep signingkey | host render → `helper = libsecret` + `signingkey = A1E4E20240EA5BAA`; container render → `grep -c credential` → `0` + `signingkey` present; in-container rendered file confirms `0` credential/libsecret lines | PASS |
| S9 | `chezmoi managed` lists both targets; container `~/.config/git/ignore` = 709 lines | `chezmoi managed -S .` → `.config/git/config`, `.config/git/ignore`; `podman exec wc -l ~/.config/git/ignore` → `709` | PASS |
| S10 | spec 01 records `dot_config/git` + `.chezmoidata`; spec 20 I-GIT1..7 + `DOTFILES_RUNTIME`; spec 02 AUTO-GEN `git-delta`; spec 13 verify-only | `grep` spec 01 → `config.tmpl`/`ignore`/`.chezmoidata/`; spec 20 → 7 `I-GIT` + `DOTFILES_RUNTIME`; spec 02 → `git-delta` row; spec 13 untouched | PASS |
| S11 | signing not gated off; host signs OK; container fails loud until key import | host `git commit --gpg-sign` → `gpg: ... 署名` (Good signature); container `git commit` → `CONTAINER_SIGN_FAILS_LOUD_OK` (no GPG key in `dotfiles_gnupg` volume yet) | PASS |

## No-regression (Task 6.9)

- `$CARGO_HOME` = `/home/kiyama/.local/share/cargo` (XDG, unchanged).
- `paru v2.1.0 - libalpm v16.0.1`; `NVIM v0.13.0-dev-885+g05d7040425`.
- `make down && make up` → `rustc 1.96.1` (cargo/rustup named volume persisted); `git config --get user.signingkey` = `A1E4E20240EA5BAA` (re-applied by entrypoint); `delta 0.19.2` still installed.

## Commit trail (post-rebase SHAs on `git_config`, base = `mise-managed-languages` `9bafea6`)

1. `7ff686b` — docs: file git-config-setup issue + design
2. `9975e5b` — docs: add git-config-setup implementation plan
3. `fff5285` — feat(chezmoi-data): fill git identity_default.signingkey (Task 1)
4. `77651b7` — feat(deps): add git-delta (layer 1) to packages.toml; regenerate (Task 2)
5. `f7095c3` — feat(chezmoi/container): add runtime data var (DOTFILES_RUNTIME) + wire entrypoint; drop dead .chezmoiignore gitignore exception (Task 3)
6. `1cdc72b` — feat(chezmoi): add managed ~/.config/git/{config.tmpl,ignore} (Task 4)
7. `0e2405f` — docs(spec-01/20): record dot_config/git templates + I-GIT invariants + DOTFILES_RUNTIME flag (Task 5)
8. `47ee87a` — fix(container): entrypoint source check accepts worktree .git (smoke-gate fix)

## Deviations from plan

1. **Rebased `git_config` onto `mise-managed-languages`** (`9bafea6`) before the smoke gate, per user. This pulls in the mise-managed-languages work (go/python/deno Layer 3, Containerfile Layer 3-5 mise, `.gitignore` rework). The rebase was clean (no conflicts — overlapping files `packages.toml`/spec 02 changed in different sections); `make gen-deps` confirmed idempotent and generator tests pass (24, was 15 + 9 mise).
2. **Entrypoint `.git`-check fix** (`47ee87a`) — the smoke gate is run from the `git_config` **worktree**, where `.git` is a *file* (gitdir pointer), not a directory. The entrypoint's `[[ ! -d "$CHEZMOI_SOURCE/.git" ]]` guard rejected it ("not a chezmoi source"). Changed `-d` → `-e` so both worktree (`.git` file) and normal repo (`.git` dir) sources are accepted. Small, strict improvement; enables worktree-based SDD smoke gates generally. Beyond the original plan scope; flagged for user review.
3. **Task ordering** — plan §"Plan adjustment" already noted the reorder (1 data → 2 packages → 3 plumbing → 4 templates → 5 specs → 6 smoke) vs the design staging, so Task 4's render verification had the filled `signingkey` (Task 1) and defined `runtime` (Task 3). No behavior change.
4. **Review gating** — Tasks 1, 2, 4 reviewed by the Claude Code subagent (herdr-driven, see below) with written review files (Spec ✅ + Quality ✅ → Approved). Tasks 3 and 5 (mechanical, fully behavior-verified by the controller: `runtime` renders host/container, exception removed, spec edits exact) were controller-gated; the final whole-branch review covers them.
5. **Subagent mechanism** — per user request, implementation/review was delegated to the Claude Code agent running in the herdr workspace (`w3:p8`, model `deepseek-v4-flash:cloud`), driven via the herdr socket API (`herdr pane run` to submit prompts, `herdr agent wait --status` to detect working/idle, `herdr agent read` / report files for results). Long prompts triggered Claude Code's paste-as-reference mode, requiring a follow-up Enter (`herdr pane run <pane> ''`) to submit.

## Secrecy invariants

- No GPG **secret** key is baked into any image layer. `user.signingkey` (`A1E4E20240EA5BAA`) is a **public** subkey ID; `user.email` is plain text — both acceptable under spec 13 §2 Tier 2 and already public in the committed `.chezmoidata/git_config.yaml`. The GPG secret key lives only in the runtime `dotfiles_gnupg` named volume (deferred Bitwarden import). Extends spec 20 I4 / I-GPG4 / I-GIT5.
- `credential.helper=libsecret` is host-runtime-only (the container has no keyring daemon, spec 20 I-GPG9); the in-container rendered config has zero `credential`/`libsecret` lines.
- The container's `commit.gpgsign=true` fails loudly on signing until the GPG key is imported (the deferred `2026-07-01-gnupg-bitwarden-import.md` issue) — signing is NOT silently disabled.

## Deferred (out of scope)

- GPG key import into the container (`docs/issues/2026-07-01-gnupg-bitwarden-import.md`).
- `.chezmoiscripts/run_after_install-{gh-hosts,git-credentials,gpg-signing,ssh-keys}.sh.tmpl` run-scripts.
- `identities` per-host/per-repo map; SSH signing.