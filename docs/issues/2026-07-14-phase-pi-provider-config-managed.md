# Phase 6 Result Log: pi Agent + Provider Config Managed

**Date:** 2026-07-14
**Status:** done (with deferred follow-ups)
**Plan:** [2026-07-14-pi-provider-config-managed-impl.md](../plans/2026-07-14-pi-provider-config-managed-impl.md)
**Design:** [2026-07-14-pi-provider-config-managed-design.md](../specifications/implementations/2026-07-14-pi-provider-config-managed-design.md)
**Parent issue:** [2026-07-14-pi-provider-config-managed.md](./2026-07-14-pi-provider-config-managed.md)

## Commit range summary

- `dotfiles3` (single rewrite commit at `develop` HEAD) — Bring pi agent + provider config under managed pi-config (10 files: `.chezmoi.toml.tmpl`, `.chezmoidata/api_secrets.yaml`, `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl`, `container/tests/container/test_entrypoint.py`, spec 11, spec 13, issue, plan, design, result log). Single commit (review-pass-1 rewrote the original 2 commits to purge a full DeepSeek key literal that had been committed into the docs — see F1 remediation below). Run `git log --oneline -1` on `develop` for the exact SHA.
- `/data/pi-config` `5a25bd9` — Add managed agent provider files + providers/kimi-coding override (tag `pi-config-v2026-07-14-1`, pushed to `origin/main`).
- `PI_harness` (`~/.pi/.git`) — retirement staged in working tree (6 `D ` removals + `.gitignore` M); **NOT committed** per "do not commit unless asked" — the operator should commit this separately when convenient. The 6 paths are untracked + gitignored so the chezmoi symlinks (host-side) will not dirty `PI_harness`.

## Environment

- Host: `/data/dotfiles3` (branch `develop`, base `a58e566` → single rewrite commit at HEAD; unpushed — 1 ahead of `origin/develop`).
- Container: `dotfiles-manjaro` (running, Up 38h+).
- `/data/pi-config`: `main` at `5a25bd9`, tag `pi-config-v2026-07-14-1`, pushed.
- Bitwarden item reused (no new item created): `https://deepseek.com/` (display "Deepseek"), id `9738dc0b-7166-4a4d-ac20-b25f00f36f04`, custom field `API`.

## Operator decisions (2026-07-14)

1. **Review waived** — letter A/B/D pass skipped; design treated as Approved for execution (review waiver recorded in design `Status:` + `Review trail:` lines).
2. **Key rotation DEFERRED** — the existing `https://deepseek.com/` Bitwarden item is reused; the leaked `sk-6a27768a...` literal in `PI_harness` history is NOT yet revoked at the provider. `PI_harness` is PRIVATE (always was, confirmed via `gh repo view`), so per design S11 no history rewrite is required — rotation alone (when it happens) closes the leak. **Follow-up required:** rotate the key in the DeepSeek console and update the Bitwarden item's `API` field.
3. **`PI_harness` retirement commit DEFERRED** — the 6 staged `D ` removals + `.gitignore` edit are left in `~/.pi`'s working tree for the operator to commit separately.

## Verification evidence

### Static (Phases 1–5)

- `grep -rnE 'sk-[A-Za-z0-9]{16,}' /data/pi-config/agent /data/pi-config/providers` → no matches (scan-exit=1). **No secret literal in managed pi-config.**
- `/data/pi-config/agent/models.json` line 6: `"apiKey": "$DEEPSEEK_API_KEY"` (env interpolation, resolved by pi at request time).
- `container/tests/container/test_entrypoint.py` — `15 passed in 0.51s` (includes the extended `test_pi_link_script_manages_only_stable_resources` asserting 9 `link_resource` + 1 `link_pi_root_resource "providers"` + `cursor-sdk-model-list.json` forbidden).
- `run_after_configure-pi-agent.sh.tmpl` — 10 link calls in correct order; `link_pi_root_resource` helper mirrors `link_resource` but targets `${pi_root}` (`~/.pi`) not `${pi_agent_dir}`.
- spec 11 names `PI_harness.git` + remote URL in the forbidden-location paragraph; spec 13 §2 cross-refs spec 11 + design §3 I9.
- design `Status:` = `Approved (review waived by maintainer decision 2026-07-14; see Review trail below)`; issue `Status:` = `in-progress` (flipped to `closed` by this result log).

### Runtime (Phase 6, container `dotfiles-manjaro`)

- `chezmoi init` regenerated `~/.config/chezmoi/chezmoi.toml` with `pi_config_ref = "pi-config-v2026-07-14-1"`.
- `chezmoi apply --refresh-externals=always --force` cloned `/data/pi-config` at `5a25bd9` / tag `pi-config-v2026-07-14-1` into `~/.local/share/pi-config`; the run-after script backed up the 4 pre-existing real files (`settings.json`, `models.json`, `ollama-cloud.json`, `providers/`) to `*.pre-pi-config.20260714032403` and created the symlinks.
- Symlinks verified (all 10):
  - `~/.pi/agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows}.json` → `~/.local/share/pi-config/agent/<name>`
  - `~/.pi/agent/{prompts,skills,extensions,themes}` → `~/.local/share/pi-config/agent/<name>`
  - `~/.pi/providers` → `~/.local/share/pi-config/providers`
- `~/.pi/agent/cursor-sdk-model-list.json` is a real 145471-byte file (generated cache, NOT a symlink — design I4 honored).
- `~/.config/zsh/rc/secrets.zsh` (mode 600) exports `DEEPSEEK_API_KEY` (len 35); sourcing it sets `${+DEEPSEEK_API_KEY}=1`.
- `grep apiKey ~/.pi/agent/models.json` → `"apiKey": "$DEEPSEEK_API_KEY"` (env interpolation reaches pi through the symlink).
- Secret scan in resolved external: `grep -rnE 'sk-[A-Za-z0-9]{16,}' ~/.local/share/pi-config/agent ~/.local/share/pi-config/providers` → no matches (scan-exit=1).
- **S7/I7 verify-before-commit gate (real pi request):**
  ```
  $ echo 'Reply with exactly the two characters: OK' | pi --model deepseek/deepseek-v4-flash --print
  OK
  pi-exit=0
  ```
  `pi` 0.80.6 resolved `$DEEPSEEK_API_KEY` from the env, read `models.json` through the symlink, and completed a real DeepSeek API round-trip. **The managed config end-to-end path is functional.**

### PI_harness retirement (host, Phase 2)

- `git -C ~/.pi ls-files agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows,cursor-sdk-model-list}.json` → empty (all 6 untracked).
- `git -C ~/.pi check-ignore agent/models.json providers/` → prints both, exit 0.
- `git -C ~/.pi status --short` → `M .gitignore` + 6 staged `D ` removals (working-tree files preserved).
- `PI_harness` visibility: **PRIVATE** (confirmed via `gh repo view kkiyama117/PI_harness --json visibility` → `PRIVATE / private=true`). Per design S11, **no history rewrite required**.

## Acceptance criteria status (parent issue #1–#11)

1. ✅ `/data/pi-config/agent/` contains the 5 files; `models.json` uses `$DEEPSEEK_API_KEY`; `providers/kimi-coding/config.json` present.
2. ✅ `DEEPSEEK_API_KEY` exported by `secrets.zsh` (mode 600) from the Bitwarden item.
3. ✅ `~/.pi/agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows}.json` are symlinks to the managed files (container).
4. ✅ `~/.pi/providers` is a symlink to `~/.local/share/pi-config/providers`; `kimi-coding/config.json` resolves through it.
5. ✅ `cursor-sdk-model-list.json` is NOT a symlink (generated cache stays unmanaged).
6. ✅ `link_pi_root_resource` helper present; `link_resource` extended for the 4 new agent files; static test `15 passed`.
7. ✅ Real `pi --model deepseek/deepseek-v4-flash` request succeeds (S7/I7).
8. ✅ No `sk-...` literal in `/data/pi-config` (scan-exit=1) or in the resolved external.
9. ✅ Override files contain no `apiKey`/secret (`kimi-coding/config.json` is secret-free).
10. ⚠️ `PI_harness` untracks + gitignores the migrated paths (verified) — **but the retirement commit is DEFERRED** (left staged in `~/.pi`). `PI_harness` is not yet "documented as legacy/superseded" in its own README; the dotfiles3 design doc + issue carry that documentation.
11. ⚠️ DeepSeek key rotation **DEFERRED** per operator decision. Spec 11/13 forbidden-location list extended to name `PI_harness.git` (design I9 done). Rotation + (optional, not needed since PRIVATE) history rewrite remain open.

## Deferred follow-ups (operator-owned)

1. **Rotate the DeepSeek key** in the DeepSeek console; update the Bitwarden `https://deepseek.com/` item's `API` field with the new key. Revoke the old leaked key (`sk-6a27…afa1d` — full literal not recorded here; recoverable from `PI_harness` history if needed). Until this happens, the leaked literal remains active.
2. **Commit the `PI_harness` retirement** in `~/.pi` (the 6 staged `D ` removals + `.gitignore` edit) with a message pointing at this issue + the new canonical location.
3. **Optionally remove `~/.pi/.git` entirely** (design Q8) so the host's `~/.pi` becomes a plain runtime dir like the container. Out of scope for this plan.
4. **`agent/extensions/` host-side untrack** — deferred in Phase 2 report. It is a real dir with contents; needs a backup-and-symlink procedure (not just `git rm --cached`) because Phase 4 symlinks `~/.pi/agent/extensions` → `~/.local/share/pi-config/agent/extensions`. Tracked for a later cleanup pass.

## Self-review

| Check | Result |
|---|---|
| No secret in `/data/pi-config` history (commit `5a25bd9`) | PASS |
| No secret in dotfiles3 rewrite commit | PASS (after review-pass-1 rewrite — see F1 remediation) |
| All 10 symlinks resolve (container) | PASS |
| `cursor-sdk-model-list.json` not symlinked | PASS |
| `secrets.zsh` exports `DEEPSEEK_API_KEY` (mode 600) | PASS |
| Real `pi` deepseek request succeeds | PASS |
| 15/15 static tests pass | PASS |
| `pi_config_ref` bumped in 3 places | PASS |
| spec 11/13 forbidden list names `PI_harness.git` | PASS |
| design `Status:` = Approved; issue closed | PASS |
| `PI_harness` retirement verified (untracked + ignored) | PASS |
| `PI_harness` retirement committed | DEFERRED |
| DeepSeek key rotated | DEFERRED |

## Review pass-1 remediation (2026-07-14)

A broad whole-branch review (letter A+B+D) flagged one CRITICAL blocker (F1): the full live DeepSeek key literal `sk-6a27…afa1d` had been committed verbatim into 3 lines of the plan + this result log (in the original 2 commits `75e6109` + `d45377a`), violating the very forbidden-location invariant (design I9 / spec 11 / spec 13 I-S3) this change introduces. F2 (LOW): the `test_pi_link_script_manages_only_stable_resources` assertion `'"${HOME}/.pi"' in text or "${HOME}/.pi" in text` was tautological — satisfied by `pi_agent_dir="${HOME}/.pi/agent"` as well as `pi_root="${HOME}/.pi"`.

Remediation applied (both commits were unpushed, so a clean rewrite was possible):

- **F1 (CRITICAL):** replaced all 3 full-literal occurrences with the non-recoverable prefix `sk-6a27…afa1d` (first 4 + last 4 of the 32-char key body; 24 chars unknown). Rewrote the 2 original commits into a single clean commit at `develop` HEAD; expired the reflog and ran `git gc --prune=now` to purge the dangling commits so the literal is no longer reachable from any ref locally. Confirmed: a full-literal grep against `HEAD` returns no matches; `git cat-file -e 75e6109`/`d45377a` → "Not a valid object name" (purged).
- **F2 (LOW):** replaced the tautological assertion with `'pi_root="${HOME}/.pi"' in text` + `'target="${pi_root}/${name}"' in text`, which actually verifies the helper targets `~/.pi` (not `~/.pi/agent`). `15 passed in 0.51s` after the fix.
- **F3 (LOW, already addressed):** design §5.5 example showed `field: main`; impl uses `field: API` (correct — matches the actual Bitwarden item). No change needed.

The rotation follow-up (#1 below) remains the only outstanding secret-safety item: until the old key is revoked at the DeepSeek console, it is still active (it lives in `PI_harness` history, which is PRIVATE). The literal no longer lives in `dotfiles3` or `/data/pi-config`.

## Conclusion

The managed pi-config path is live: `/data/pi-config` (tag `pi-config-v2026-07-14-1`) is canonical, `dotfiles3` consumes it via `.chezmoiexternal.toml.tmpl`, the run-after script symlinks all 10 resources into `~/.pi/agent` + `~/.pi/providers`, and a real DeepSeek request through `$DEEPSEEK_API_KEY` succeeds. The two deferred items (key rotation, `PI_harness` retirement commit) are operator-owned follow-ups that do not block the managed config functioning.
