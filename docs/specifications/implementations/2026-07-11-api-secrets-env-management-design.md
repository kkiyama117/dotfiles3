# API provider secrets as environment variables — Design

**Status:** Approved
**Date opened:** 2026-07-11
**Issue:** [`../../issues/2026-07-11-api-secrets-env-management.md`](../../issues/2026-07-11-api-secrets-env-management.md)
**Author:** kiyama
**Review required:** letter A + B + D (touches secret material, auth flow,
and cross-spec consistency; see [`../09-review.md`](../09-review.md) §2.2)

## §1 Context & success criteria

### Context

The host runs `~/.config/zsh/rc/secrets.zsh` to export API keys for
GitHub CLI and AI providers (OpenRouter, Kimi, Ollama, etc.). The host
inventory flags this file as confidential and requires a chezmoi +
Bitwarden template port (`docs/references/host_config_list.md` §1, §18).

The new repository already defines:

- Bitwarden as the sole secret source (`bw`, spec 13 I-S1).
- Tier-1 credentials as podman secrets with entrypoint auto-auth
  (approved design `2026-06-30-bitwarden-auto-auth-design.md`).
- Runtime-only `bitwarden*` template guards (`{{ if not .build_mode }}`,
  spec 13 I-S6).
- sheldon deferred loading for `options.zsh` via `my_conf_defered`
  (`dot_config/sheldon/plugins.toml`).

What is missing is the **Tier-1-adjacent vault-item path**: API keys stored
as Bitwarden login/custom-field items, resolved at `chezmoi apply`, and
exported as durable shell env vars for the interactive session. Provider
keys are **not** Tier-1 base credentials; they are vault items retrieved
through the existing `BW_SESSION` contract and intentionally **not**
scrubbed by the entrypoint (spec 13 §4 scrubs only `BW_CLIENTID` /
`BW_CLIENTSECRET` / `BW_SESSION`).

### Success criteria

- **S1:** On host and container runtime apply (with `BW_SESSION`), chezmoi
  renders `~/.config/zsh/rc/secrets.zsh` exporting every entry in
  `.chezmoidata/api_secrets.yaml`.
- **S2:** No API key value is committed, written to `.env`, baked into
  image layers, or visible in `podman inspect` environment.
- **S3:** Build-time pre-pass (`build_mode = true`) never calls `bw`;
  unguarded `bitwarden*` in the template fails the build loudly (I-S6).
- **S4:** Rendered `secrets.zsh` is `0600`, owned by `${USERNAME}`.
- **S5:** sheldon sources `secrets.zsh` **synchronously** before the first
  prompt so subprocesses (`gh`, pi, curl, etc.) inherit provider env vars.
- **S6:** `.chezmoidata/api_secrets.yaml` contains only non-secret metadata
  (Bitwarden item IDs/names, env var names, field selectors). Spec 11
  §Bitwarden items gains one row per provider.
- **S7:** `dot_config/zsh/rc/functions/bw_session.zsh` ships as a
  non-secret helper for interactive `bw unlock` inside `podman exec`
  shells (spec 13 §4 recipe); it does not replace entrypoint auth.
- **S8:** Relevant specs (`11`, `08`, `host_config_list`) are updated in
  the implementation phase.

## §2 Alternatives considered

- **A1 — Flat `dot_config/zsh/secrets.zsh` beside `options.zsh` (rejected
  for path parity).** Matches the current `my_conf_defered` glob
  (`use=["{options}.zsh"]`) with no sheldon change, but diverges from the
  host layout (`rc/secrets.zsh`) and splits confidential exports away from
  other `rc/` shards the inventory documents.
- **A2 — `run_after_install-api-secrets.sh.tmpl` writing a credentials
  file (rejected).** Mirrors SSH attachment materialization but adds a
  second delivery path and shell `bw` calls in scripts. Spec 13 I-S5
  prefers chezmoi `bitwarden*` functions for value resolution; scripts
  are reserved for non-export materialization (SSH keys, gh hosts).
- **A3 — Provider keys in `dot_zshenv.tmpl` (rejected).** Would make keys
  visible to every zsh invocation including non-interactive `zsh -c`, and
  conflicts with the existing comment that Tier-1 credentials must not live
  in the image-bound zshenv tree. API keys belong in the interactive rc
  shard the host already uses.
- **A4 — `dot_config/zsh/rc/secrets.zsh.tmpl` + `.chezmoidata/api_secrets.yaml`
  + synchronous sheldon plugin (chosen).** Matches host path, follows SSH
  data-file precedent, uses `bitwardenFields` / `bitwarden` per item
  shape, and keeps load order explicit.

## §3 Architecture / Invariants

### Data flow

```text
Bitwarden vault items (API keys)
        │
        ▼  chezmoi apply (runtime, BW_SESSION set)
dot_config/zsh/rc/secrets.zsh.tmpl
        │  bitwardenFields / bitwarden (guarded)
        ▼
~/.config/zsh/rc/secrets.zsh  (mode 0600, plain exports)
        │
        ▼  sheldon [plugins.my_secrets] apply=source
interactive zsh env  →  gh / pi / curl / …
```

### Design invariants

- **I1:** API keys are vault items, not podman secrets. No new
  `podman secret create` entries for providers.
- **I2:** Every `bitwarden*` call in `secrets.zsh.tmpl` is wrapped in
  `{{ if not .build_mode }}…{{ end }}` (I-S6). Optional per-entry
  `runtime: host|container|both` filtering uses the `.runtime` chezmoi
  data flag (same compound-guard pattern as `dot_config/git/config.tmpl`).
- **I3:** Chezmoi templates resolve secrets only via `bitwarden*`
  functions (I-S5). No `bw` subprocess from `.tmpl` files.
- **I4:** Rendered `secrets.zsh` may contain resolved key values on disk
  in `$HOME` (same trust model as SSH private keys in `dotfiles_ssh`).
  Permissions must be `0600`; the file must never enter image layers
  (runtime apply only).
- **I5:** Entrypoint `BW_*` scrub list is unchanged. Provider env vars
  exported by `secrets.zsh` are intentionally durable for the shell
  session and must not be added to the scrub block.
- **I6:** `.chezmoidata/api_secrets.yaml` stores item IDs/names only,
  never key material (mirrors `.chezmoidata/ssh_keys.yaml`).

### Bitwarden item shape (operator contract)

Each provider entry maps to one Bitwarden **Login** or **Secure Note**
item. The template supports three value sources (first match wins per
entry configuration):

| `source` value | chezmoi expression | Typical use |
|---|---|---|
| `custom_field` | `(bitwardenFields "item" "<id>").<field>.value` | `api_key`, `token`, provider-specific names |
| `password` | `(bitwarden "item" "<id>").login.password` | legacy login-item pattern |
| `notes` | `(bitwarden "item" "<id>").notes` | rare; prefer `custom_field` |

The operator creates items in Bitwarden and records the item ID (or stable
name) plus field name in `.chezmoidata/api_secrets.yaml`. Item IDs are
public in the repository per spec 11. **v1 operator contract:** every
provider item stores the key in a custom field named `api_key`.

### Initial provider set (v1)

Each env var uses the **provider's default** name (what upstream CLIs/SDKs
read without extra configuration):

| Env var | Consumer | Default Bitwarden item name (illustrative) | `source` / field |
|---|---|---|---|
| `GH_TOKEN` | `gh`, GitHub API | `github-api-token` | `custom_field` / `api_key` |
| `OPENROUTER_API_KEY` | pi, OpenRouter HTTP clients | `openrouter` | `custom_field` / `api_key` |
| `MOONSHOT_API_KEY` | pi, Kimi / Moonshot API | `kimi` | `custom_field` / `api_key` |
| `OLLAMA_API_KEY` | pi, Ollama Cloud API | `ollama-cloud` | `custom_field` / `api_key` |

Additional providers (Anthropic, OpenAI, Groq, etc.) are added by appending
rows to `api_secrets.yaml` without template logic changes.

## §4 Scope / staging breakdown

### In scope (this design)

- `.chezmoidata/api_secrets.yaml` schema and seed entries (placeholder item
  IDs — operator replaces with real vault IDs).
- `dot_config/zsh/rc/secrets.zsh.tmpl` generator loop over the data file.
- `dot_config/sheldon/plugins.toml` — new `[plugins.my_secrets]` block.
- `dot_config/zsh/rc/functions/bw_session.zsh` — interactive unlock helper.
- Spec 11 / 08 / `host_config_list` updates (implementation phase).
- `container/tests/` extension for `0600` perm and build-mode guard smoke.

### Out of scope

- Host-side automatic `BW_SESSION` (host keeps manual unlock per spec 12).
- `run_after_install-gh-hosts.sh.tmpl` (separate gh OAuth hosts file).
- Pi `~/.pi/agent` runtime state, pi-config content, provider model routing.
- New podman secrets per provider.
- Secret rotation automation, CI/CD secret injection.

## §5 Implementation detail — data file

Add `.chezmoidata/api_secrets.yaml`:

```yaml
# Non-secret metadata only. Replace item IDs with your vault IDs.
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

Fields:

- `env` — shell variable name to export (provider default).
- `item` — Bitwarden item ID or stable name (public).
- `source` — `custom_field` | `password` | `notes` (v1 uses `custom_field`).
- `field` — required when `source: custom_field` (v1: always `api_key`).
- `runtime` — `host` | `container` | `both` (default `both`).

There is **no `enabled` flag**. Whether secrets resolve is controlled solely
by the template-level `{{ if not .build_mode }}` guard (I-S6): build-time
apply renders an empty file; runtime apply resolves every listed entry.

## §6 Implementation detail — `secrets.zsh.tmpl`

Source path: `dot_config/zsh/rc/secrets.zsh.tmpl`
Target path: `~/.config/zsh/rc/secrets.zsh`

Template skeleton:

```gotemplate
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

Data access follows the same chezmoi rule as `.chezmoidata/ssh_keys.yaml`:
the file root key `api_secrets` becomes template var `.api_secrets` (see
`{{- range .ssh_keys }}` in `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`).

Chezmoi template attributes on the source file (implementation plan):

```yaml
# .chezmoi.yaml.tmpl or file-level directive
dot_config/zsh/rc/secrets.zsh.tmpl:
  mode: 0600
```

If chezmoi `mode` on a `.tmpl` is insufficient in practice, add a
`run_after_chmod-secrets-zsh.sh.tmpl` post-step (same pattern as SSH key
mode fix) — prefer native `mode` first.

Build-time behavior: outer `{{ if not .build_mode }}` renders an empty
file (or a comment-only stub) so the build pre-pass never invokes `bw`.

## §7 Implementation detail — sheldon wiring

Add to `dot_config/sheldon/plugins.toml` **after** `my_conf_defered` and
**before** `my_functions` so options load first, secrets second, hooks last:

```toml
# API provider env (synchronous — child processes must inherit exports)
[plugins.my_secrets]
local = "~/.config/zsh/rc"
use = ["secrets.zsh"]
apply = ["source"]
```

Rationale: deferred loading (`my_conf_defered` default) delays env exports
until the first prompt, breaking tools spawned early in shell startup and
any `zsh -c` paths that source the sheldon cache before defer fires.
Synchronous `source` matches the security-sensitive nature of env injection.

`dot_config/zsh/dot_zshrc` stays unchanged (sheldon cache regeneration
picks up the new plugin automatically).

## §8 Implementation detail — `bw_session.zsh`

Port `~/.config/zsh/rc/functions/bw_session.zsh` as a **non-template**
zsh function file loaded by existing `[plugins.my_functions]`.

Responsibilities:

- Define `bw_session()` that runs `bw unlock --raw` interactively on the
  host, or `bw unlock --passwordfile /run/secrets/bw_password --raw` when
  `/run/secrets/bw_password` exists (container `podman exec`).
- Export `BW_SESSION` in the **current shell only** for follow-up
  `chezmoi apply` or debugging — not for replacing entrypoint auth.
- Document in a header comment that entrypoint auth (spec 13 §4) already
  unlocks for runtime apply; this helper is for interactive re-entry.

Do **not** persist `BW_SESSION` to a keyring (spec 13 §8 Q2).

## §9 Spec and doc updates (implementation phase)

| Document | Change |
|---|---|
| [`11-pre-required-env-values.md`](../11-pre-required-env-values.md) | Add Bitwarden-items rows for each `api_secrets` entry; add provider env subsection |
| [`13-secret-management.md`](../13-secret-management.md) | Note `bitwardenFields` consumer (`secrets.zsh.tmpl`) in §3; no invariant change |
| [`08-automations.md`](../08-automations.md) | Map API provider env → Bitwarden item → `secrets.zsh` |
| [`host_config_list.md`](../../references/host_config_list.md) | Mark `secrets.zsh` / `bw_session.zsh` port complete |
| [`01-file-structures.md`](../01-file-structures.md) | Add new paths to inventory |

## §10 Verification contract

Implementation must demonstrate:

1. **Build secret-free:** `make build` succeeds; Stage 2 pre-pass does not
   call `bw` (existing invariant; guarded template stays empty).
2. **Runtime render:** `make up` with podman secrets →
   `~/.config/zsh/rc/secrets.zsh` exists, mode `0600`, contains `export`
   lines for all configured providers.
3. **Env visibility:** Interactive `podman exec` shell →
   `printenv GH_TOKEN` (and other configured vars) non-empty when vault
   items exist.
4. **No inspect leak:** `podman inspect` env lacks provider API keys and
   lacks `BW_*` after entrypoint scrub.
5. **Host path:** `BW_SESSION=… chezmoi apply` on host renders the same
   file (manual unlock per spec 12).
6. **Tests:** Extend `container/tests/` with at least build-mode empty
   render and `0600` mode assertions.

## §11 Decisions (operator-approved 2026-07-11)

- **D1 — Env var names:** Use each provider's default env var:
  `GH_TOKEN`, `OPENROUTER_API_KEY`, `MOONSHOT_API_KEY`, `OLLAMA_API_KEY`.
- **D2 — Bitwarden field:** All v1 items use custom field `api_key`.
- **D3 — Ollama:** Ollama Cloud API key only (`OLLAMA_API_KEY`). No
  `OLLAMA_HOST` export.
- **D4 — No `enabled` flag:** Activation is solely via `build_mode`;
  runtime apply exports every entry in `api_secrets.yaml`. Operator must
  fill real Bitwarden item IDs before runtime apply (missing items fail
  loudly at template resolution).

## §12 Review trail

**Pass 1 prompt:** [`../../reviews/2026-07-11-api-secrets-env-management-review-prompt-pass1.md`](../../reviews/2026-07-11-api-secrets-env-management-review-prompt-pass1.md)

Required letters (09-review §2.2):

- Pass 1-A — correctness / regressions (build-mode guard, sheldon order).
  [`../../reviews/2026-07-11-api-secrets-env-management-review-pass1-A-factual.md`](../../reviews/2026-07-11-api-secrets-env-management-review-pass1-A-factual.md)
- Pass 1-B — security (file perms, no inspect leak, scrub boundary).
  [`../../reviews/2026-07-11-api-secrets-env-management-review-pass1-B-security.md`](../../reviews/2026-07-11-api-secrets-env-management-review-pass1-B-security.md)
- Pass 1-D — cross-spec consistency (11, 13, host inventory).
  [`../../reviews/2026-07-11-api-secrets-env-management-review-pass1-D-consistency.md`](../../reviews/2026-07-11-api-secrets-env-management-review-pass1-D-consistency.md)
- Aggregate: [`../../reviews/2026-07-11-api-secrets-env-management-review-pass1.md`](../../reviews/2026-07-11-api-secrets-env-management-review-pass1.md)

> Implementation landed on `develop` before pass-1 reviews completed;
> reviewers evaluated both design and committed artifacts. Pass 1 closed
> 2026-07-12 after AB-F1 fix (`e6b01db`); runtime verification deferred.

## §13 Meta-prompt for implementation planner

```
Implement approved design:
docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md

Deliverables:
1. .chezmoidata/api_secrets.yaml (operator fills item IDs; no enabled flag)
2. dot_config/zsh/rc/secrets.zsh.tmpl with I-S6 guard + loop
3. dot_config/sheldon/plugins.toml [plugins.my_secrets]
4. dot_config/zsh/rc/functions/bw_session.zsh
5. Spec updates per design §9
6. container/tests extensions per design §10

Constraints: I-S1..I-S6, no new podman secrets, no bw calls from templates,
entrypoint scrub list unchanged, single commit per plan phase.
```
