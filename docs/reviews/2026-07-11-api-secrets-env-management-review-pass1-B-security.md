# api-secrets-env-management — Review pass-1 (Letter B: security)

**Date:** 2026-07-12
**Reviewer:** pi-subagent reviewer (Letter B)
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve with conditions.** The secret-handling boundaries (inspect scrub, `bitwarden*`-only
resolution, build-mode guard, master-password-via-`--passwordfile`, no-secret-in-git)
are correct and evidence-backed. B-F1/B-F2/B-F3 are **RESOLVED** in `e6b01db`:
source renamed to `private_secrets.zsh.tmpl` with `private_` prefix; inert mode
comment removed; static test asserts `private_` source. Runtime `stat` and
`podman inspect` checks remain operator-deferred.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| B-F1 | HIGH | RESOLVED | `dot_config/zsh/rc/private_secrets.zsh.tmpl`, commit `e6b01db` | `private_` prefix enforces `0600` on rendered `secrets.zsh` (S4/I4 met at source level) |
| B-F2 | MEDIUM | RESOLVED | `container/tests/container/test_api_secrets.py`, commit `e6b01db` | `test_secrets_template_uses_private_source_for_mode_0600` asserts `private_` prefix; legacy path must not exist |
| B-F3 | LOW | RESOLVED | commit `e6b01db` | Inert `# chezmoi:mode=600` line removed |
| B-F4 | LOW | open | `dot_config/zsh/rc/functions/bw_session.zsh:15` | Host fallback `export BW_SESSION="$(bw unlock --raw)"` exports an empty session on unlock failure (command-substitution swallows non-zero); robustness only, not a leak |

### B-F1 details

**Resolution (commit `e6b01db`):** Source renamed to
`dot_config/zsh/rc/private_secrets.zsh.tmpl`. Chezmoi's `private_` prefix clears
group/world permissions on the target `~/.config/zsh/rc/secrets.zsh` → `0600`.
Inert `# chezmoi:mode=600` removed.

**Remaining verification (operator-deferred):**

```
stat -c '%a' ~/.config/zsh/rc/secrets.zsh   # expect 600 after runtime apply
```

### B-F2 details

**Resolution (commit `e6b01db`):** Replaced inert comment assertion with
`test_secrets_template_uses_private_source_for_mode_0600`, which asserts
`private_secrets.zsh.tmpl` exists, name starts with `private_`, and legacy
`secrets.zsh.tmpl` does not exist. Result-log updated accordingly.

### B-F3 details

**Resolution (commit `e6b01db`):** Inert `# chezmoi:mode=600` line removed with
source rename.

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
- **P3 (I-S5, templates never shell out to `bw`):** `private_secrets.zsh.tmpl` resolves
  values only via `bitwardenFields` / `bitwarden` template functions; `bw_session.zsh`
  is a non-template interactive `.zsh` helper, outside the I-S5 template scope.
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

- **Q1:** After B-F1 fix, is `~/.config/zsh/rc/` guaranteed non-traversable
  by other UIDs on the host (design §10.5 host apply path)? A `0600` file under a
  `0755` directory is still readable by anyone who can `stat`/open it if they know
  the path; confirm the host threat model treats `$HOME` as single-user, or set
  the directory `private_` too.
- **Q2 (NOTE, operability):** With no `enabled` flag (D4), a single unfilled
  placeholder among the four entries fails the **entire** `chezmoi apply` (not
  just the secrets shard), blocking all runtime dotfiles until every item ID is
  filled. This is the intended fail-loud contract, but the all-or-nothing blast
  radius should be documented for operators.
