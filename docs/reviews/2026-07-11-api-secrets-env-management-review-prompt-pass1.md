# API secrets env management — Review prompt (pass 1)

**Date:** 2026-07-12
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md)
**Issue:** [`docs/issues/2026-07-11-api-secrets-env-management.md`](../issues/2026-07-11-api-secrets-env-management.md)
**Plan:** [`docs/plans/2026-07-11-api-secrets-env-management-impl.md`](../plans/2026-07-11-api-secrets-env-management-impl.md)
**Result-log:** [`docs/issues/2026-07-11-phase-api-secrets-env-management.md`](../issues/2026-07-11-phase-api-secrets-env-management.md)
**Required letters:** A + B + D (09-review §2.2 — secret material, auth flow, cross-spec)

## Context for reviewers

Implementation phases 1–4 are committed on `develop` (`fd7f4f3` … `cdec48e`).
Static tests pass (`make test-container` → 20 passed). Runtime verification
and Bitwarden item IDs remain operator-deferred.

Review **both** the design and the landed implementation. Findings may
target the design doc, implementation files, or spec updates.

## Common output format

Each per-letter review MUST follow [`09-review.md`](../specifications/09-review.md) §3:

- Header (date, reviewer, subject, pass, status)
- Verdict (Approve / Approve with conditions / Request changes / Block)
- Findings table + per-finding details
- Verified premises
- Open questions

**Output paths (one file per letter):**

| Letter | Output file |
|---|---|
| A | `docs/reviews/2026-07-11-api-secrets-env-management-review-pass1-A-factual.md` |
| B | `docs/reviews/2026-07-11-api-secrets-env-management-review-pass1-B-security.md` |
| D | `docs/reviews/2026-07-11-api-secrets-env-management-review-pass1-D-consistency.md` |

After all three letters: author produces aggregate
`docs/reviews/2026-07-11-api-secrets-env-management-review-pass1.md`.

---

## Reviewer-A — factual / correctness

**Role:** Verify design claims match implementation and cited sources; catch
logical gaps in template loop, sheldon order, and build-mode behavior.

**Read:**

- Design §1–§8, §10–§11
- `.chezmoidata/api_secrets.yaml`
- `dot_config/zsh/rc/secrets.zsh.tmpl`
- `dot_config/sheldon/plugins.toml` (`[plugins.my_secrets]` block)
- `dot_config/zsh/rc/functions/bw_session.zsh`
- `container/tests/container/test_api_secrets.py`
- `.chezmoidata/ssh_keys.yaml` (data-access precedent)
- `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl` (guard precedent)

**Evaluate:**

1. **S1 / S3 / I-S6:** Does `secrets.zsh.tmpl` guard all `bitwarden*` calls
   behind `{{ if not .build_mode }}`? Does build-mode render produce no
   Bitwarden resolution?
2. **S5 / §7:** Is `[plugins.my_secrets]` synchronous (`apply = ["source"]`)?
   Plugin order: `my_conf_defered` → `my_secrets` → `my_functions`?
3. **D1–D4:** Env var names, `api_key` field, no `OLLAMA_HOST`, no `enabled`
   flag — reflected in data file and tests?
4. **Template loop:** Does `{{- range .api_secrets }}` + `bitwardenFields` /
   `(index $fields .field).value` match design §6 and SSH data-file pattern?
5. **Runtime filter:** Does `runtime: host|container|both` logic match design §6?
6. **bw_session:** Does helper match spec 13 §4 recipe without replacing
   entrypoint auth?
7. **Tests:** Do static tests cover the above? Any false negatives from
   dash-trimmed gotemplate (`{{-` / `-}}`)?

**Expected output:** Letter A review file per §3 schema. Flag any design §10
verification steps not yet evidenced in result-log.

---

## Reviewer-B — security

**Role:** OWASP-class review of secret handling, file permissions, privilege
boundaries, and leakage paths.

**Read:**

- Design §3 (I1–I6), §6, §8, §10
- `dot_config/zsh/rc/secrets.zsh.tmpl` (`# chezmoi:mode=600`)
- `container/bind/layer_5_files/entrypoint.sh` (BW_* scrub block — confirm
  unchanged)
- [`13-secret-management.md`](../specifications/13-secret-management.md) §2–§4, I-S1..I-S6
- [`20-container-rules.md`](../specifications/20-container-rules.md) I4 (image secret-free)
- Implementation commits and result-log deferred checks

**Evaluate:**

1. **I-S2 / S2 / S4:** Resolved keys on disk at `~/.config/zsh/rc/secrets.zsh`
   only at runtime apply; mode `0600`; never in git, `.env`, or image layers.
2. **Inspect leak (S2 / §10.4):** Provider keys and `BW_*` must not appear in
   `podman inspect` env after entrypoint scrub. Confirm scrub list was not
   extended to provider vars (I5).
3. **I-S5:** No `bw` subprocess from `.tmpl` files; only `bitwarden*` functions.
4. **I-S6 / build_mode:** Build pre-pass cannot invoke Bitwarden; unguarded
   template would fail loudly.
5. **bw_session:** Master password via `--passwordfile` only when secret
   exists; no keyring persistence; no password in env vars (I-BW2 boundary).
6. **Trust model (I4):** Plaintext exports on `$HOME` bind mount — acceptable
   per SSH key precedent? umask / ownership risks?
7. **Placeholder item IDs:** `REPLACE_WITH_BITWARDEN_ITEM_ID` — fail-loud
   behavior at template resolution vs silent empty exports?

**Expected output:** Letter B review file per §3 schema. CRITICAL/HIGH
findings on any secret-in-git, secret-in-image, or inspect-leak path.

---

## Reviewer-D — consistency / cross-doc

**Role:** Naming, link, section-number, and contradiction checks against
normative specs and neighboring designs.

**Read:**

- Design §9 (spec update table)
- [`11-pre-required-env-values.md`](../specifications/11-pre-required-env-values.md)
- [`13-secret-management.md`](../specifications/13-secret-management.md)
- [`08-automations.md`](../specifications/08-automations.md)
- [`01-file-structures.md`](../specifications/01-file-structures.md)
- [`host_config_list.md`](../references/host_config_list.md)
- Issue acceptance A1–A7 and result-log evidence table
- Plan global constraints vs design invariants

**Evaluate:**

1. **Spec 11:** Bitwarden-items table rows for all four providers; API provider
   env subsection; no contradiction with spec 13 two-tier model.
2. **Spec 13:** `secrets.zsh.tmpl` listed in template consumer inventory;
   invariants I-S1..I-S6 still accurate; Q1 resolution state.
3. **Spec 08 / 01 / host_config_list:** Entries match actual paths; port
   status notes cite correct chezmoi targets.
4. **Design vs implementation:** Any drift between design §5–§8 snippets and
   committed files (mode directive, sheldon block, bw_session)?
5. **Issue / plan / result-log:** Traceability — same slug, linked paths,
   phase commits recorded, deferred items explicit.
6. **Alternatives §2:** Chosen A4 still justified given landed sheldon wiring?
7. **A7:** Review letters A+B+D completed before issue close — process gap
   if implementation landed pre-approval?

**Expected output:** Letter D review file per §3 schema. List any spec
section still TBD or contradicting implementation.

---

## Pass-1 termination

Pass 1 closes when:

- Letters A, B, D are filed at the output paths above
- Aggregate review `…-review-pass1.md` summarizes cross-letter findings
- Every CRITICAL/HIGH finding is `RESOLVED` or explicitly `INCOMPLETE` with reason
- Design status advances toward `Approved` once findings are addressed
