# api-secrets-env-management — Review pass-1 (Letter B: security)

**Date:** 2026-07-12
**Reviewer:** pi-subagent reviewer (Letter B)
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

**Request changes.** The secret-handling boundaries (inspect scrub, `bitwarden*`-only
resolution, build-mode guard, master-password-via-`--passwordfile`, no-secret-in-git)
are correct and evidence-backed. One HIGH leak-path finding blocks approval: the
rendered `~/.config/zsh/rc/secrets.zsh` is **not** enforced to `0600` — the
`# chezmoi:mode=600` comment on line 1 is not a chezmoi mechanism, so the file
renders at the default `0644` and defeats success criterion **S4** / invariant
**I4** and the SSH-key trust-model parity the design relies on. A supporting
MEDIUM finding: the static test that "passes" for mode only asserts the presence
of that inert comment string, producing false assurance.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| B-F1 | HIGH | open | `dot_config/zsh/rc/secrets.zsh.tmpl:1`; design §6, §3 I4; S4 | `# chezmoi:mode=600` is not a valid chezmoi mode mechanism; rendered `secrets.zsh` gets default `0644` → plaintext API keys group/world-readable on disk |
| B-F2 | MEDIUM | open | `container/tests/container/test_api_secrets.py:24-33`; result-log line 23 | Mode test asserts only the literal string `# chezmoi:mode=600`, not the applied mode → false "PASS" for S4 |
| B-F3 | LOW | open | `dot_config/zsh/rc/secrets.zsh.tmpl:1` | Inert `# chezmoi:mode=600` line is emitted verbatim into the rendered target (merged with the next comment via `{{-` trim); cosmetic, confirms the directive is non-functional |
| B-F4 | LOW | open | `dot_config/zsh/rc/functions/bw_session.zsh:15` | Host fallback `export BW_SESSION="$(bw unlock --raw)"` exports an empty session on unlock failure (command-substitution swallows non-zero); robustness only, not a leak |

### B-F1 details

`secrets.zsh.tmpl` relies on line 1 to set the target file mode:

```1:2:dot_config/zsh/rc/secrets.zsh.tmpl
# chezmoi:mode=600
{{- if not .build_mode -}}
```

chezmoi determines a target file's mode **only** from source-state filename
attributes (`private_`, `readonly_`, `executable_`) or `.chattr`/rename — never
from an in-file comment directive (chezmoi *Target types* / *source-state
attributes*: `private_` "clears all group and world permissions" → `0600`;
permission comment directives do not exist). The source file is named
`secrets.zsh.tmpl` with **no `private_` prefix**, so:

1. The `# chezmoi:mode=600` line is treated as ordinary file content and rendered
   verbatim into `~/.config/zsh/rc/secrets.zsh` (see B-F3).
2. The target is written at the default file mode `0644 &^ umask` — i.e.
   group/world **readable** on any host or container where `umask` is the common
   `022`.

Impact: after runtime `chezmoi apply` resolves real vault items, the file holds
plaintext `export GH_TOKEN=…`, `export OPENROUTER_API_KEY=…`, etc. On a
multi-user host (design §10.5 host path: `BW_SESSION=… chezmoi apply`), any other
local UID that can traverse `~/.config/zsh/rc/` can read every provider key. This
violates **S4** ("Rendered `secrets.zsh` is `0600`") and **I4** ("Permissions
must be `0600`").

The design's own trust model (§3 I4) claims parity with "SSH private keys in
`dotfiles_ssh`" — but that precedent enforces mode **explicitly**:

```44:46:.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl
  bw get attachment "$attachment" --itemid "$item" --session "$BW_SESSION" --raw > "$tmp"
  chmod "$mode" "$tmp"
  mv "$tmp" "$destination"
```

with `fetch_attachment_file … 600` for private keys and a `0700` `~/.ssh`
directory. `secrets.zsh` gets neither an explicit `chmod` nor a `private_` prefix,
so the parity claim is currently false.

**Suggested fix (pick one):**

- Rename the source to `private_secrets.zsh.tmpl` (target stays
  `~/.config/zsh/rc/secrets.zsh`; chezmoi then clears group/world → `0600`). This
  is the idiomatic chezmoi mechanism and removes the inert comment line.
- Or add a `run_after_chmod-secrets-zsh.sh.tmpl` post-step (the fallback the
  design §6 itself anticipates: "If chezmoi `mode` on a `.tmpl` is insufficient…").

Prefer the `private_` rename. Also confirm the parent directory
`~/.config/zsh/rc/` is not group/world traversable if the host is multi-user.

**Verification steps:**

```
# after fix + runtime apply with a real vault item:
stat -c '%a' ~/.config/zsh/rc/secrets.zsh   # expect 600
# source-attribute proof at the source:
ls dot_config/zsh/rc/ | grep -x 'private_secrets.zsh.tmpl'
```

### B-F2 details

The test asserted as the S4 gate only checks a substring:

```24:26:container/tests/container/test_api_secrets.py
def test_secrets_template_build_mode_guard() -> None:
    text = SECRETS_TMPL.read_text()
    assert "# chezmoi:mode=600" in text
```

Because the asserted string is the exact inert directive from B-F1, this test
passes while the applied mode is wrong. The result-log records
`` `# chezmoi:mode=600` in template | PASS (static test) `` (line 23), which
misrepresents S4 as covered when the real `0600` check is separately DEFERRED
(result-log line 24). After B-F1's fix, replace this assertion with a
source-attribute check (e.g. assert the source file is named `private_…`), so the
static suite actually gates the permission invariant.

### B-F3 details

With the leading `{{-` trim, chezmoi emits `# chezmoi:mode=600` merged onto the
first rendered comment line of the target file. Harmless to `zsh source` (it stays
a `#` comment) and secret-free in build mode, but it confirms the directive is
non-functional and leaves a misleading line in every rendered `secrets.zsh`.
Removing it falls out naturally from the `private_` rename in B-F1.

### B-F4 details

```9:17:dot_config/zsh/rc/functions/bw_session.zsh
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

If `bw unlock` fails, `$( … )` yields empty and the helper exports an empty
`BW_SESSION`, masking failure until a later `bitwarden*` call errors. No secret is
exposed (master password stays in `--passwordfile`; no keyring persistence — spec
13 §8 Q2 honored), so this is a robustness nit, not a leak. Optional: guard the
assignment and `unset`/return non-zero on empty.

## Verified premises

- **P1 (scrub boundary unchanged, I5 / S2 §10.4):** `entrypoint.sh` scrubs
  exactly `BW_CLIENTID BW_CLIENTSECRET BW_SESSION`, gated on the presence of
  `/run/secrets/bw_password` (not on a non-empty session), and the provider env
  vars are **not** added to the scrub list — matching spec 13 §4 and the design's
  intent that provider vars stay durable for the session.

```178:180:container/bind/layer_5_files/entrypoint.sh
if [ -f /run/secrets/bw_password ]; then
  unset BW_CLIENTID BW_CLIENTSECRET BW_SESSION
fi
```

- **P2 (no inspect leak):** `BW_CLIENTID`/`BW_CLIENTSECRET` are `export`ed only
  inside the entrypoint process (read from `/run/secrets/*`, never image `Env` /
  `-e`), so they are absent from `podman inspect`; the master password enters no
  env (`bw unlock --passwordfile`, entrypoint.sh:147). Provider keys live only in
  the interactive shell's env (sourced by sheldon), never in PID 1 / image `Env`,
  so they are absent from `podman inspect` too.
- **P3 (I-S5, templates never shell out to `bw`):** `secrets.zsh.tmpl` resolves
  values only via `bitwardenFields` / `bitwarden` template functions
  (lines 10, 13, 15); `bw_session.zsh` is a non-template interactive `.zsh`
  helper, outside the I-S5 template scope.
- **P4 (I-S6 / build_mode fail-loud):** every resolution path is wrapped in
  `{{- if not .build_mode -}} … {{- end -}}` (lines 2, 19). The build-time
  pre-pass (`build_mode = true`) renders secret-free output and never invokes
  `bw`; a forgotten guard would make the Stage-2 apply call `bw` unauthenticated
  and fail the build loudly (spec 13 §5a safety property).
- **P5 (no secret-in-git):** `.chezmoidata/api_secrets.yaml` carries only env
  names, `source`/`field` selectors, and `REPLACE_WITH_BITWARDEN_ITEM_ID`
  placeholders; the template holds no key material. Repo-wide scan for common key
  shapes (`sk-…`, `ghp_…`, `sk-or-v1-…`, `AKIA…`) returned no matches. Item IDs,
  when filled, are public per spec 11.
- **P6 (placeholder fail-loud, S3 / D4):** an unresolved
  `REPLACE_WITH_BITWARDEN_ITEM_ID` makes `bitwardenFields "item" "…"` fail (item
  not found) → template error → `chezmoi apply` fails → entrypoint `set -euo
  pipefail` exits non-zero → `make up` surfaces the failure. No silent empty
  export path exists (a missing `api_key` field also errors at
  `(index $fields .field).value`).

## Open questions

- **Q1:** After B-F1 is fixed, is `~/.config/zsh/rc/` guaranteed non-traversable
  by other UIDs on the host (design §10.5 host apply path)? A `0600` file under a
  `0755` directory is still readable by anyone who can `stat`/open it if they know
  the path; confirm the host threat model treats `$HOME` as single-user, or set
  the directory `private_` too.
- **Q2 (NOTE, operability):** With no `enabled` flag (D4), a single unfilled
  placeholder among the four entries fails the **entire** `chezmoi apply` (not
  just the secrets shard), blocking all runtime dotfiles until every item ID is
  filled. This is the intended fail-loud contract, but the all-or-nothing blast
  radius should be documented for operators.
