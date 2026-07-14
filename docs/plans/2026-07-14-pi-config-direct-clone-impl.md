# pi-config direct-clone implementation plan

**Date:** 2026-07-14
**Design:** [2026-07-14-pi-config-direct-clone-design.md](../specifications/implementations/2026-07-14-pi-config-direct-clone-design.md)
**Issue:** [2026-07-14-pi-config-direct-clone.md](../issues/2026-07-14-pi-config-direct-clone.md)
**Oracle review:** claude-code oracle session 2026-07-14

## Phase 0 — Documents (parent-executed)

- [x] Issue created: `docs/issues/2026-07-14-pi-config-direct-clone.md`
- [x] Design created: `docs/specifications/implementations/2026-07-14-pi-config-direct-clone-design.md`
- [x] Plan created: this file

## Phase 1 — pi-config repo (`/data/pi-config`)

**Worker task:** Update `.gitignore`, commit, tag, push.

Steps:
1. Append to `.gitignore`: `run-history.jsonl`, `intercom/`, `.pi-subagents/`, `*.pre-pi-config.*`
2. Commit with message: "Extend .gitignore for direct ~/.pi clone (run-history.jsonl, intercom/, .pi-subagents/, *.pre-pi-config.*)"
3. Tag `pi-config-v2026-07-14-2`
4. Push to `origin/main` (with `--tags`)

## Phase 2 — dotfiles3 changes

**Worker task:** Modify 6 files, delete 1 file, update tests.

Files to change:
1. `.chezmoiignore` — make `.pi` entry conditional: `{{ if not (eq .runtime "container") }}.pi{{ end }}`
2. `.chezmoiexternal.toml.tmpl` — change `[".local/share/pi-config"]` to `[".pi"]`, gate with `{{ if and (not .build_mode) (eq .runtime "container") }}`
3. `.chezmoi.toml.tmpl` — bump `pi_config_ref` default to `pi-config-v2026-07-14-2`
4. `programs/chezmoi_pi_commit.sh` — remove `~/.local/share/pi-config` fallback path
5. `docs/specifications/11-pre-required-env-values.md` — bump `PI_CONFIG_REF` default
6. `container/tests/container/test_entrypoint.py`:
   - Delete `test_pi_link_script_manages_only_stable_resources` + `PI_LINK_SCRIPT` constant
   - Update `test_chezmoi_toml_config_has_pi_config`: assert `pi-config-v2026-07-14-2`
   - Update `test_chezmoi_external_has_pi_config`: assert `[".pi"]`, runtime gate, remove `file:///data/pi-config` assertion
   - Update `test_pi_commit_hook_uses_external_prompt_precedence`: assert `$HOME/.pi/agent/prompts/commit.md`, assert old path NOT present

File to delete:
7. `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`

Verification:
- `pytest container/tests/container/test_entrypoint.py` — all tests pass

## Phase 3 — Container in-place migration

**Parent-executed** (needs running container access).

Steps:
1. Remove old symlinks and backups from `~/.pi/agent/` and `~/.pi/providers`
2. `git clone --no-checkout --branch pi-config-v2026-07-14-2 --depth 1 https://github.com/kkiyama117/pi-config.git /tmp/pi-tmp`
3. `mv /tmp/pi-tmp/.git ~/.pi/.git`
4. `git -C ~/.pi checkout -f` (preserves untracked runtime state)
5. `rm -rf ~/.local/share/pi-config`
6. `chezmoi apply` → no-op (external already satisfied)
7. Verify: `pi --model deepseek/deepseek-v4-flash --print` returns OK
8. Verify: commit prompt works (`pi` reads `~/.pi/agent/prompts/commit.md`)

## Phase 4 — Dockerfile + PI_harness

**Worker task:** Update Dockerfile and PI_harness comment.

1. Dockerfile: remove any `~/.local/share/pi-config` references; ensure `~/.pi` is handled correctly for fresh builds
2. PI_harness `~/.pi/.gitignore`: update comment about agent files being symlinked

## Phase 5 — Commit + push

**Parent-executed** (requires explicit user authorization for push).

1. Commit all dotfiles3 changes with conventional commit message referencing the issue
2. Push to `origin/develop` (after user approval)
3. Close the issue
