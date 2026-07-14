# pi-config direct-clone design

**Date:** 2026-07-14
**Status:** DRAFT
**Supersedes:** [2026-07-14-pi-provider-config-managed-design.md](./2026-07-14-pi-provider-config-managed-design.md) (the symlink layer introduced there is removed by this design)
**Oracle review:** claude-code oracle session 2026-07-14 (R1-R7 findings incorporated)

## §1 Context

`/data/pi-config` was brought under chezmoi management in the pi-provider-config-managed change (commit `c3421af`). That design used a clone-to-intermediate + symlink approach: chezmoi clones pi-config into `~/.local/share/pi-config`, then `run_after_configure-pi-agent.sh.tmpl` symlinks individual files into `~/.pi/agent/` and `~/.pi/providers/`.

`/data/nvim_config` uses a simpler approach: chezmoi clones directly into `~/.config/nvim`. No symlink script. Runtime state lives alongside managed files, gitignored by the repo's `.gitignore`.

The pi-config repo structure already maps 1:1 to `~/.pi/` (top-level `agent/` and `providers/` directories), so the intermediate layer is unnecessary. This design removes it.

## §2 Key risks (oracle findings)

### R1 (CRITICAL): Host `~/.pi` is a PI_harness checkout

The host's `/home/kiyama/.pi` is a git checkout of `git@github.com:kkiyama117/PI_harness.git`. If `.chezmoiexternal.toml.tmpl` targets `[".pi"]` unconditionally, chezmoi on the host would `git pull` PI_harness (not clone pi-config) — silently operating on the wrong repo.

**Decision A:** Gate the external to container runtime only. The host's `~/.pi` remains PI_harness-managed.

### R2 (CRITICAL): `.chezmoiignore` has `.pi`

The current `.chezmoiignore` contains `.pi`, which causes chezmoi to silently skip the `[".pi"]` external — no error, no clone, nothing happens.

**Mitigation:** Make the `.chezmoiignore` entry conditional: ignore `.pi` except when `runtime == "container"`. `.chezmoiignore` supports template syntax.

### R3 (HIGH): Existing non-empty `~/.pi` blocks clone

Chezmoi's git-repo external does NOT overwrite an existing non-empty non-git directory. The container's `~/.pi` has auth.json, sessions, symlinks, etc. — chezmoi will no-op.

**Decision B:** In-place migration: manually clone pi-config's `.git` into `~/.pi`, checkout, then remove the old `~/.local/share/pi-config`. Also update the Dockerfile for fresh builds.

### R4 (HIGH): `programs/chezmoi_pi_commit.sh` fallback path

The script has a fallback: `$HOME/.local/share/pi-config/agent/prompts/commit.md`. After direct clone, the path becomes `$HOME/.pi/agent/prompts/commit.md`. The test `test_pi_commit_hook_uses_external_prompt_precedence` asserts the old path.

**Mitigation:** Remove the fallback (the external is always present for container runtime). Update the test.

### R5 (MEDIUM): Structural fragility

If pi runs before chezmoi apply, `~/.pi` is created as a non-git directory, and subsequent chezmoi clone becomes a permanent no-op. nvim_config avoids this because nvim doesn't create `~/.config/nvim` before chezmoi runs.

**Mitigation:** Document in the entrypoint that chezmoi apply must precede pi invocation. Consider a lightweight run_after guard that detects the condition and warns.

### R6 (LOW): Missing gitignore entries

`/data/pi-config/.gitignore` needs: `run-history.jsonl`, `intercom/`, `.pi-subagents/`, `*.pre-pi-config.*`. The `cursor-sdk-model-list.*.json` glob is correct (not `..json`).

### R7 (LOW): Tag change doesn't trigger re-clone

Git-repo external pull doesn't follow tag changes. Same known limitation as nvim_config. Fresh clones get the new tag; existing clones need manual intervention or `--refresh-externals=always`.

## §3 Design

### §3.1 `.chezmoiexternal.toml.tmpl`

```toml
{{- /* pi config external — container runtime only (host ~/.pi is PI_harness). */ -}}
{{- if and (not .build_mode) (eq .runtime "container") }}
[".pi"]
type = "git-repo"
url = "{{ .pi_config_url }}"
refreshPeriod = "0"
clone.args = ["--branch", "{{ .pi_config_ref }}", "--depth", "1", "--no-single-branch"]
pull.args = ["--ff-only"]
{{- end }}
```

### §3.2 `.chezmoiignore`

Change the `.pi` entry from unconditional to runtime-conditional:

```
{{ if not (eq .runtime "container") }}.pi{{ end }}
```

### §3.3 `run_after_configure-pi-agent.sh.tmpl`

**Deleted.** The symlink layer is removed. The file is deleted from the dotfiles3 tree.

### §3.4 `/data/pi-config/.gitignore`

Add:
```
run-history.jsonl
intercom/
.pi-subagents/
*.pre-pi-config.*
```

### §3.5 `programs/chezmoi_pi_commit.sh`

Remove the `$HOME/.local/share/pi-config/agent/prompts/commit.md` fallback. The primary path `$HOME/.pi/agent/prompts/commit.md` is always present for container runtime.

### §3.6 Tests

- **Delete** `test_pi_link_script_manages_only_stable_resources` + `PI_LINK_SCRIPT` constant
- **Update** `test_chezmoi_toml_config_has_pi_config`: assert `pi-config-v2026-07-14-2`
- **Update** `test_chezmoi_external_has_pi_config`: assert `[".pi"]`, runtime gate, remove `file:///data/pi-config` assertion
- **Update** `test_pi_commit_hook_uses_external_prompt_precedence`: assert `$HOME/.pi/agent/prompts/commit.md`, assert old path NOT present

### §3.7 Spec 11

Bump `PI_CONFIG_REF` default to `pi-config-v2026-07-14-2`.

### §3.8 `.chezmoi.toml.tmpl`

Bump `pi_config_ref` default to `pi-config-v2026-07-14-2`.

### §3.9 Dockerfile

Update any `~/.local/share/pi-config` references. The external now populates `~/.pi` directly; no intermediate directory needed.

### §3.10 PI_harness `.gitignore` comment

Update the comment in `~/.pi/.gitignore` that says agent files are symlinked from pi-config. After this change, the host's `~/.pi` is still PI_harness (container-only external), but the comment should reflect the current state.

## §4 Invariants

- **I1**: pi-config is cloned directly into `~/.pi` on container runtime only
- **I2**: Host `~/.pi` remains PI_harness-managed (unchanged)
- **I3**: No symlink script exists in the dotfiles3 tree
- **I4**: `/data/pi-config/.gitignore` covers all `~/.pi` runtime state
- **I5**: No secrets in any repo (spec 11/13)
- **I6**: `pi_config_ref` points to `pi-config-v2026-07-14-2`

## §5 Success criteria

- **S1**: `run_after_configure-pi-agent.sh.tmpl` deleted from dotfiles3
- **S2**: `.chezmoiexternal.toml.tmpl` targets `[".pi"]` with container runtime gate
- **S3**: `.chezmoiignore` allows `.pi` external for container runtime only
- **S4**: `/data/pi-config/.gitignore` covers all runtime state
- **S5**: pi-config tagged `pi-config-v2026-07-14-2` and pushed
- **S6**: All tests pass with updated paths
- **S7**: Container in-place migration succeeds; `pi --model deepseek/deepseek-v4-flash --print` returns OK
- **S8**: Dockerfile updated; fresh container build works
- **S9**: PI_harness `.gitignore` comment updated
