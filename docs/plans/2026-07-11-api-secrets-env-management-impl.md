# API provider secrets as environment variables — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task.
> Dispatch **one fresh subagent per Phase**; parent reviews between phases.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** executing
**Spec:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md) (DRAFT — operator-approved decisions §11)
**Parent issue:** [`docs/issues/2026-07-11-api-secrets-env-management.md`](../issues/2026-07-11-api-secrets-env-management.md)
**Review trail:** design §12 plans letters A + B + D before implementation.
Security-touching (09-review §2.2 → A + B + D required).

**Goal:** Render GitHub and AI-provider API keys from Bitwarden vault items
into `~/.config/zsh/rc/secrets.zsh` at runtime `chezmoi apply`, load them
synchronously via sheldon, and expose them as shell env vars
(`GH_TOKEN`, `OPENROUTER_API_KEY`, `MOONSHOT_API_KEY`, `OLLAMA_API_KEY`)
without baking secrets into image layers or the repository.

**Architecture:** Non-secret metadata in `.chezmoidata/api_secrets.yaml`
maps env var names to Bitwarden item IDs and field selectors. A chezmoi
template `dot_config/zsh/rc/secrets.zsh.tmpl` loops over `.api_secrets`,
resolving values via `bitwardenFields` / `bitwarden` behind a
`{{ if not .build_mode }}` guard. sheldon plugin `[plugins.my_secrets]`
sources the rendered file synchronously. `bw_session.zsh` provides
interactive re-unlock only.

**Tech Stack:** chezmoi (`bitwarden*` templates), Bitwarden CLI (`bw`),
zsh, sheldon, pytest (static repo tests).

## Global Constraints

- **I-S1** — `bw` is the sole secret source; no new podman secrets for API keys.
- **I-S5** — templates resolve secrets only via `bitwarden*` functions; no `bw`
  subprocess from `.tmpl` files.
- **I-S6** — every `bitwarden*` call wrapped in `{{ if not .build_mode }}`.
- **D1** — env vars: `GH_TOKEN`, `OPENROUTER_API_KEY`, `MOONSHOT_API_KEY`,
  `OLLAMA_API_KEY` (provider defaults).
- **D2** — Bitwarden custom field name: `api_key` for all v1 providers.
- **D3** — Ollama Cloud API key only; no `OLLAMA_HOST`.
- **D4** — no `enabled` flag; `build_mode` is the sole activation gate.
- **I-S4 / spec 20 I4** — image stays secret-free; API keys appear only on
  runtime apply into `$HOME`, never in image layers or `podman inspect` env.
- **entrypoint scrub** — do not modify the `BW_*` scrub list in
  `container/bind/layer_5_files/entrypoint.sh`.
- **00-doc-mgmt** — one commit per Phase; no secret values in git or docs.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `.chezmoidata/api_secrets.yaml` | create | Non-secret item ID → env var mapping |
| `dot_config/zsh/rc/secrets.zsh.tmpl` | create | Runtime Bitwarden → export loop |
| `dot_config/sheldon/plugins.toml` | modify | `[plugins.my_secrets]` sync source |
| `dot_config/zsh/rc/functions/bw_session.zsh` | create | Interactive `bw unlock` helper |
| `container/tests/container/test_api_secrets.py` | create | Static guard / wiring / mode tests |
| `container/tests/container/test_entrypoint.py` | modify | Import shared `ROOT` if needed |
| `docs/specifications/11-pre-required-env-values.md` | modify | Bitwarden-items rows + provider envs |
| `docs/specifications/13-secret-management.md` | modify | Note `secrets.zsh.tmpl` consumer |
| `docs/specifications/08-automations.md` | modify | Automation inventory row |
| `docs/specifications/01-file-structures.md` | modify | New path inventory |
| `docs/references/host_config_list.md` | modify | Mark port complete |
| `docs/issues/2026-07-11-phase-api-secrets-env-management.md` | create | Phase result-log (Phase 4) |

**Operator prerequisite (before runtime verify):** fill real Bitwarden item
IDs in `.chezmoidata/api_secrets.yaml`. Each item must have custom field
`api_key`. Discover IDs with `bw get item <name> --raw | jq .id`.

---

## Phase 1 — Data file + secrets template + mode 0600

**Subagent role:** `worker` — implement files only; no spec updates yet.

**Files:**
- Create: `.chezmoidata/api_secrets.yaml`
- Create: `dot_config/zsh/rc/secrets.zsh.tmpl`

**Interfaces:**
- Consumes: chezmoi data merge (`.chezmoidata/api_secrets.yaml` root key
  `api_secrets` → template var `.api_secrets`, same rule as `.ssh_keys`).
- Produces: guarded template that renders empty at `build_mode=true` and
  `export` lines at runtime.

- [ ] **Step 1: Create `.chezmoidata/api_secrets.yaml`**

```yaml
# API provider secret metadata for chezmoi templates.
#
# This file may contain Bitwarden item IDs / stable item names only.
# Never store API keys, tokens, or other secret values here.
#
# Operator: replace item values with your vault item IDs or stable names.
# Each Bitwarden item must have custom field "api_key".
api_secrets:
  - env: GH_TOKEN
    item: "REPLACE_WITH_BITWARDEN_ITEM_ID"
    source: custom_field
    field: api_key
    runtime: both

  - env: OPENROUTER_API_KEY
    item: "REPLACE_WITH_BITWARDEN_ITEM_ID"
    source: custom_field
    field: api_key
    runtime: both

  - env: MOONSHOT_API_KEY
    item: "REPLACE_WITH_BITWARDEN_ITEM_ID"
    source: custom_field
    field: api_key
    runtime: both

  - env: OLLAMA_API_KEY
    item: "REPLACE_WITH_BITWARDEN_ITEM_ID"
    source: custom_field
    field: api_key
    runtime: both
```

- [ ] **Step 2: Create `dot_config/zsh/rc/secrets.zsh.tmpl`**

```gotemplate
# chezmoi:mode=600
{{- if not .build_mode -}}
# API provider env (Bitwarden-sourced, runtime apply only).
# Generated from .chezmoidata/api_secrets.yaml — do not edit rendered file.
{{- range .api_secrets }}
{{- $rt := default "both" .runtime }}
{{- $rtOk := or (eq $rt "both") (eq $rt $.runtime) }}
{{- if $rtOk }}
{{- if eq .source "custom_field" }}
{{- $fields := bitwardenFields "item" .item }}
export {{ .env }}={{ (index $fields .field).value | quote }}
{{- else if eq .source "password" }}
export {{ .env }}={{ (bitwarden "item" .item).login.password | quote }}
{{- else if eq .source "notes" }}
export {{ .env }}={{ (bitwarden "item" .item).notes | quote }}
{{- end }}
{{- end }}
{{- end }}
{{- end -}}
```

- [ ] **Step 3: Verify build-mode render is secret-free (static)**

```bash
cd /data/dotfiles3
grep -q '{{ if not .build_mode }}' dot_config/zsh/rc/secrets.zsh.tmpl
grep -q 'chezmoi:mode=600' dot_config/zsh/rc/secrets.zsh.tmpl
grep -q 'bitwardenFields' dot_config/zsh/rc/secrets.zsh.tmpl
# bitwarden* must be inside the build_mode guard — no bare calls outside
python3 - <<'PY'
from pathlib import Path
text = Path("dot_config/zsh/rc/secrets.zsh.tmpl").read_text()
guard_start = text.index("{{- if not .build_mode")
guard_end = text.index("{{- end -}}")
body = text[guard_start:guard_end]
assert "bitwardenFields" in body
assert "bitwarden " not in text[guard_end:]
print("guard OK")
PY
```

Expected: `guard OK`; no `bitwarden` calls after the closing `{{- end -}}`.

- [ ] **Step 4: Verify build-mode chezmoi render (optional, needs chezmoi)**

```bash
cd /data/dotfiles3
BUILD_MODE=true chezmoi execute-template < dot_config/zsh/rc/secrets.zsh.tmpl
```

Expected: empty output (or whitespace only).

- [ ] **Step 5: Commit**

```bash
git add .chezmoidata/api_secrets.yaml dot_config/zsh/rc/secrets.zsh.tmpl
git commit -m "$(cat <<'EOF'
Add api_secrets data and secrets.zsh chezmoi template.

Refs docs/issues/2026-07-11-api-secrets-env-management.md
EOF
)"
```

**Acceptance:** `api_secrets.yaml` and `secrets.zsh.tmpl` exist; template has
`chezmoi:mode=600`, `{{ if not .build_mode }}` guard, and loops `.api_secrets`
with `bitwardenFields` for `api_key` field.

**Rollback:** `git revert HEAD`.

---

## Phase 2 — sheldon wiring + bw_session helper

**Subagent role:** `worker`

**Files:**
- Modify: `dot_config/sheldon/plugins.toml`
- Create: `dot_config/zsh/rc/functions/bw_session.zsh`

**Interfaces:**
- Consumes: rendered `~/.config/zsh/rc/secrets.zsh` from Phase 1.
- Produces: synchronous sheldon source of `secrets.zsh`; `bw_session()`
  function for interactive unlock.

- [ ] **Step 1: Add `[plugins.my_secrets]` to sheldon manifest**

Insert in `dot_config/sheldon/plugins.toml` after `[plugins.my_conf_defered]`
(block ending `apply = ['defer']`) and before `[plugins.my_functions]`:

```toml
# API provider env (synchronous — child processes must inherit exports)
[plugins.my_secrets]
local = "~/.config/zsh/rc"
use = ["secrets.zsh"]
apply = ["source"]
```

- [ ] **Step 2: Create `dot_config/zsh/rc/functions/bw_session.zsh`**

```zsh
# Interactive Bitwarden session helper.
#
# Entrypoint auth (spec 13 §4) already unlocks bw for runtime chezmoi apply.
# Use bw_session() only when you need BW_SESSION in the current shell
# (e.g. podman exec, manual chezmoi apply, debugging).
#
# Does NOT persist BW_SESSION to a keyring.

bw_session() {
  if [[ -r /run/secrets/bw_password ]]; then
    export BW_SESSION="$(
      bw unlock --passwordfile /run/secrets/bw_password --raw
    )"
  else
    export BW_SESSION="$(bw unlock --raw)"
  fi
}
```

- [ ] **Step 3: Verify sheldon wiring (static)**

```bash
cd /data/dotfiles3
grep -A4 '\[plugins.my_secrets\]' dot_config/sheldon/plugins.toml
grep -q 'apply = \["source"\]' dot_config/sheldon/plugins.toml
grep -q 'bw_session()' dot_config/zsh/rc/functions/bw_session.zsh
```

Expected: `my_secrets` uses `secrets.zsh` with `apply = ["source"]`; not
`defer`. `bw_session` function defined.

- [ ] **Step 4: Verify plugin order**

```bash
python3 - <<'PY'
from pathlib import Path
text = Path("dot_config/sheldon/plugins.toml").read_text()
defer_idx = text.index("[plugins.my_conf_defered]")
secrets_idx = text.index("[plugins.my_secrets]")
funcs_idx = text.index("[plugins.my_functions]")
assert defer_idx < secrets_idx < funcs_idx
print("order OK")
PY
```

Expected: `order OK`.

- [ ] **Step 5: Commit**

```bash
git add dot_config/sheldon/plugins.toml dot_config/zsh/rc/functions/bw_session.zsh
git commit -m "$(cat <<'EOF'
Wire secrets.zsh into sheldon and add bw_session helper.

Refs docs/issues/2026-07-11-api-secrets-env-management.md
EOF
)"
```

**Acceptance:** sheldon loads `secrets.zsh` synchronously; `bw_session.zsh`
exists and is picked up by existing `[plugins.my_functions]`.

**Rollback:** `git revert HEAD`.

---

## Phase 3 — Static tests

**Subagent role:** `worker`

**Files:**
- Create: `container/tests/container/test_api_secrets.py`

**Interfaces:**
- Consumes: Phase 1–2 files on disk.
- Produces: pytest module run by `make test-container`.

- [ ] **Step 1: Write failing tests first**

Create `container/tests/container/test_api_secrets.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_SECRETS_DATA = ROOT / ".chezmoidata" / "api_secrets.yaml"
SECRETS_TMPL = ROOT / "dot_config" / "zsh" / "rc" / "secrets.zsh.tmpl"
SHELDON = ROOT / "dot_config" / "sheldon" / "plugins.toml"
BW_SESSION = ROOT / "dot_config" / "zsh" / "rc" / "functions" / "bw_session.zsh"


def test_api_secrets_data_lists_v1_providers() -> None:
    text = API_SECRETS_DATA.read_text()
    for env in (
        "GH_TOKEN",
        "OPENROUTER_API_KEY",
        "MOONSHOT_API_KEY",
        "OLLAMA_API_KEY",
    ):
        assert f"env: {env}" in text
    assert "field: api_key" in text
    assert "enabled:" not in text
    assert "OLLAMA_HOST" not in text


def test_secrets_template_build_mode_guard() -> None:
    text = SECRETS_TMPL.read_text()
    assert "# chezmoi:mode=600" in text
    assert "{{- if not .build_mode -}}" in text
    guard_start = text.index("{{- if not .build_mode")
    guard_end = text.index("{{- end -}}")
    body = text[guard_start:guard_end]
    assert "bitwardenFields" in body
    tail = text[guard_end + len("{{- end -}}") :]
    assert "bitwarden" not in tail


def test_secrets_template_exports_all_data_entries() -> None:
    text = SECRETS_TMPL.read_text()
    assert "{{- range .api_secrets }}" in text
    assert 'export {{ .env }}=' in text
    assert '(index $fields .field).value' in text


def test_sheldon_my_secrets_plugin_is_synchronous() -> None:
    text = SHELDON.read_text()
    block_start = text.index("[plugins.my_secrets]")
    block_end = text.index("[plugins.my_functions]", block_start)
    block = text[block_start:block_end]
    assert 'use = ["secrets.zsh"]' in block
    assert 'apply = ["source"]' in block
    assert "defer" not in block


def test_sheldon_plugin_order_secrets_before_functions() -> None:
    text = SHELDON.read_text()
    defer_idx = text.index("[plugins.my_conf_defered]")
    secrets_idx = text.index("[plugins.my_secrets]")
    funcs_idx = text.index("[plugins.my_functions]")
    assert defer_idx < secrets_idx < funcs_idx


def test_bw_session_helper_exists() -> None:
    text = BW_SESSION.read_text()
    assert "bw_session()" in text
    assert "/run/secrets/bw_password" in text
    assert "bw unlock --raw" in text
```

- [ ] **Step 2: Run tests — expect FAIL before Phase 1–2 land**

```bash
cd /data/dotfiles3
make test-container
```

Expected: PASS (after Phases 1–2 are committed).

- [ ] **Step 3: Commit**

```bash
git add container/tests/container/test_api_secrets.py
git commit -m "$(cat <<'EOF'
Add static tests for API secrets env management.

Refs docs/issues/2026-07-11-api-secrets-env-management.md
EOF
)"
```

**Acceptance:** `make test-container` passes including new tests.

**Rollback:** `git revert HEAD`.

---

## Phase 4 — Spec/doc updates + runtime verification + result-log

**Subagent role:** `worker` for docs; parent or operator for runtime verify.

**Files:**
- Modify: `docs/specifications/11-pre-required-env-values.md`
- Modify: `docs/specifications/13-secret-management.md`
- Modify: `docs/specifications/08-automations.md`
- Modify: `docs/specifications/01-file-structures.md`
- Modify: `docs/references/host_config_list.md`
- Create: `docs/issues/2026-07-11-phase-api-secrets-env-management.md`

- [ ] **Step 1: Update spec 11 Bitwarden items table**

In `docs/specifications/11-pre-required-env-values.md`, replace the `_(TBD)_`
row and add four rows:

```markdown
| `.api_secrets[].item` in `.chezmoidata/api_secrets.yaml` (`GH_TOKEN`) | `dot_config/zsh/rc/secrets.zsh.tmpl` | runtime apply (host + container) | Bitwarden custom field `api_key` on login/secure-note item |
| `.api_secrets[].item` (`OPENROUTER_API_KEY`) | `secrets.zsh.tmpl` | runtime apply | custom field `api_key` |
| `.api_secrets[].item` (`MOONSHOT_API_KEY`) | `secrets.zsh.tmpl` | runtime apply | custom field `api_key` |
| `.api_secrets[].item` (`OLLAMA_API_KEY`) | `secrets.zsh.tmpl` | runtime apply | Ollama Cloud API key; custom field `api_key` |
```

Add provider env subsection under Local environment variables:

```markdown
### API provider env vars (runtime, from `secrets.zsh`)

| Variable | Required | Source | Used by |
|---|---|---|---|
| `GH_TOKEN` | no (derived at shell startup) | `~/.config/zsh/rc/secrets.zsh` | `gh`, GitHub API |
| `OPENROUTER_API_KEY` | no | `secrets.zsh` | pi, OpenRouter clients |
| `MOONSHOT_API_KEY` | no | `secrets.zsh` | pi, Kimi / Moonshot API |
| `OLLAMA_API_KEY` | no | `secrets.zsh` | pi, Ollama Cloud API |

> Values are resolved at `chezmoi apply` from Bitwarden and written to
> `secrets.zsh` (mode 0600). They are not in `podman inspect` env.
```

- [ ] **Step 2: Update spec 13 §3 consumer list**

In `docs/specifications/13-secret-management.md`, add to the template
consumer inventory (§3 or equivalent):

```markdown
- `dot_config/zsh/rc/secrets.zsh.tmpl` — `bitwardenFields` / `bitwarden`
  for API provider env exports (`.chezmoidata/api_secrets.yaml`).
```

- [ ] **Step 3: Update spec 08 automations inventory**

Add row to `docs/specifications/08-automations.md`:

```markdown
| API provider env export | active | runtime `chezmoi apply` + interactive zsh | Bitwarden items in `.chezmoidata/api_secrets.yaml` + `BW_SESSION` | `~/.config/zsh/rc/secrets.zsh` → shell env via sheldon |
```

- [ ] **Step 4: Update file-structure inventory**

In `docs/specifications/01-file-structures.md`, add under chezmoi source:

```markdown
- `.chezmoidata/api_secrets.yaml` — API provider Bitwarden item metadata
- `dot_config/zsh/rc/secrets.zsh.tmpl` — runtime API key env exports
- `dot_config/zsh/rc/functions/bw_session.zsh` — interactive bw unlock helper
```

- [ ] **Step 5: Update host_config_list port status**

In `docs/references/host_config_list.md`, update `secrets.zsh` and
`bw_session.zsh` entries to note chezmoi port target paths
(`dot_config/zsh/rc/secrets.zsh.tmpl`, `dot_config/zsh/rc/functions/bw_session.zsh`).

- [ ] **Step 6: Operator fills Bitwarden item IDs**

Replace `REPLACE_WITH_BITWARDEN_ITEM_ID` in `.chezmoidata/api_secrets.yaml`
with real vault IDs. Verify field names:

```bash
bw get item <item-id> --raw | jq '.fields[] | select(.name=="api_key")'
```

- [ ] **Step 7: Runtime verification (container)**

```bash
cd /data/dotfiles3
make build
make up
# wait for entrypoint chezmoi apply
podman exec -it dotfiles-manjaro zsh -lic 'stat -c "%a %n" ~/.config/zsh/rc/secrets.zsh'
podman exec -it dotfiles-manjaro zsh -lic 'grep -c "^export GH_TOKEN=" ~/.config/zsh/rc/secrets.zsh'
podman exec -it dotfiles-manjaro zsh -lic 'printenv GH_TOKEN | wc -c'
podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'GH_TOKEN|OPENROUTER|MOONSHOT|OLLAMA|BW_' || true
make test-container
```

Expected:
- `secrets.zsh` mode `600`
- `export` lines present
- `printenv GH_TOKEN` non-empty in interactive shell
- `podman inspect` shows no provider keys or `BW_*` env

- [ ] **Step 8: Runtime verification (host, optional)**

```bash
export BW_SESSION="$(bw unlock --raw)"
chezmoi apply --source /data/dotfiles3
stat -c '%a' ~/.config/zsh/rc/secrets.zsh   # expect 600
grep '^export OPENROUTER_API_KEY=' ~/.config/zsh/rc/secrets.zsh
```

- [ ] **Step 9: Write result-log**

Create `docs/issues/2026-07-11-phase-api-secrets-env-management.md`:

```markdown
# Phase result-log — API secrets env management

**Date:** 2026-07-11
**Plan:** docs/plans/2026-07-11-api-secrets-env-management-impl.md
**Issue:** docs/issues/2026-07-11-api-secrets-env-management.md

## Evidence

| Check | Result |
|---|---|
| `make test-container` | PASS |
| `secrets.zsh` mode 0600 | PASS |
| `podman inspect` no API keys | PASS |
| Interactive `printenv GH_TOKEN` | PASS (when items configured) |

## Notes

<paste command output snippets>
```

- [ ] **Step 10: Commit**

```bash
git add docs/specifications/11-pre-required-env-values.md \
  docs/specifications/13-secret-management.md \
  docs/specifications/08-automations.md \
  docs/specifications/01-file-structures.md \
  docs/references/host_config_list.md \
  docs/issues/2026-07-11-phase-api-secrets-env-management.md
git commit -m "$(cat <<'EOF'
Document API secrets env management and record phase result-log.

Refs docs/issues/2026-07-11-api-secrets-env-management.md
EOF
)"
```

**Acceptance:** design §9 docs updated; design §10 verification checks pass;
result-log written; issue acceptance A1–A6 satisfied.

**Rollback:** `git revert HEAD`; remove rendered `~/.config/zsh/rc/secrets.zsh`
on host if applied.

---

## Subagent execution map

| Phase | Subagent | Context | Review after |
|---|---|---|---|
| 1 | `worker` | fresh | parent: build-mode guard + data schema |
| 2 | `worker` | fresh | parent: sheldon order + bw_session |
| 3 | `worker` | fresh | parent: `make test-container` output |
| 4 | `worker` | fresh | parent: spec cross-refs + result-log |

Parent orchestration pattern (pi-subagents):

```typescript
// Per phase after plan approval:
subagent({
  agent: "worker",
  task: "Implement Phase N of docs/plans/2026-07-11-api-secrets-env-management-impl.md only. ...",
  async: true,
  context: "fresh",
  acceptance: { level: "checked", evidence: ["commands-run", "changed-files"] }
})
```

After all phases: run review letters A + B + D per design §12 before
marking plan `executed` and closing the issue.

---

## Self-review (plan vs spec)

| Spec requirement | Plan task |
|---|---|
| S1 runtime render all entries | Phase 1 template + Phase 4 verify |
| S2 no secrets in git/image/inspect | Global constraints + Phase 4 inspect check |
| S3 build_mode guard | Phase 1 + Phase 3 tests |
| S4 mode 0600 | `# chezmoi:mode=600` + Phase 4 stat |
| S5 sheldon sync load | Phase 2 + Phase 3 tests |
| S6 api_secrets.yaml metadata | Phase 1 |
| S7 bw_session helper | Phase 2 |
| S8 spec updates | Phase 4 |
| D1–D4 operator decisions | Global constraints + data file |

No TBD placeholders remain in task steps.
