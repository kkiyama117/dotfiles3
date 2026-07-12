# Phase result-log — API secrets env management

**Date:** 2026-07-12
**Plan:** docs/plans/2026-07-11-api-secrets-env-management-impl.md
**Issue:** docs/issues/2026-07-11-api-secrets-env-management.md

## Commits

| Phase | SHA | Subject |
|---|---|---|
| 1 | fd7f4f3 | Add api_secrets data and secrets.zsh chezmoi template. |
| 2 | 83e1ade | Wire secrets.zsh into sheldon and add bw_session helper. |
| 3 | 7163b34 | Add static tests for API secrets env management. |
| 4 | (pending) | Document API secrets env management and record phase result-log. |

## Evidence

| Check | Result |
|---|---|
| `make test-container` | PASS (20 passed) |
| Build-mode guard in template | PASS (static test) |
| sheldon `[plugins.my_secrets]` sync source | PASS (static test) |
| `# chezmoi:mode=600` in template | PASS (static test) |
| Runtime `secrets.zsh` mode 0600 | DEFERRED — operator must fill Bitwarden item IDs and run `make up` |
| `podman inspect` no API keys | DEFERRED — requires container runtime verify |
| Interactive `printenv GH_TOKEN` | DEFERRED — requires real vault items |

## Notes

Static verification (2026-07-12):

```
$ make test-container
20 passed in 0.51s
```

Operator follow-up before runtime apply:

1. Replace `REPLACE_WITH_BITWARDEN_ITEM_ID` in `.chezmoidata/api_secrets.yaml`
   with real vault item IDs (each item needs custom field `api_key`).
2. Run container runtime checks from plan Phase 4 Step 7.
3. Complete review letters A + B + D per design §12 before closing issue.

Implementation plan brief Step 3 grep patterns omitted `{{-`/`-}}` dashes;
Phase 3 test initially failed on the same mismatch and was corrected to use
`{{- if not .build_mode`.
