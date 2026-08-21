# pi `fetch_content` hung until abort

**Date:** 2026-08-21
**Status:** closed
**Related:** [swaync swap](2026-08-21-swaync-replace-wired.md), [Cursor rule](../../.cursor/rules/pi-fetch-content.mdc)

## Context

During the waybar-notification / SwayNC session (Cursor transcript
`agent-dbda65d2-14c2-45d6-86c3-5355664f0c4e`, started 2026-08-21 08:54 JST),
`pi__fetch_content` was used twice:

1. **Completed, oversized:** `mode=raw` on
   `https://github.com/Toqozz/wired-notify/wiki/Useful-tools-to-help-you-do-things-with-Wired`
   plus a small GitHub raw waybar config. The wiki body was reported as
   **245320 chars**. Follow-up `get_search_content` was required to slice it.
2. **Aborted:** `mode=answer` on
   `https://raw.githubusercontent.com/ErikReider/SwayNotificationCenter/main/README.md`
   with prompt “extract the waybar module JSON”. Tool result:
   `Error: Page answer failed: Aborted`.

The user asked how long that second fetch ran.

## Problem

`fetch_content` `mode=answer` can block the session with no useful progress.
Agents then stall instead of using a bounded `curl` / known snippet.

## Timing (counted 2026-08-21)

Clock source: user timestamps in the Cursor transcript + jsonl mtime.
No per-tool duration field exists on that fetch, so this is wall-clock
bracketing, not a kernel timer.

| Mark | JST | Notes |
|------|-----|--------|
| Session start | 08:54 | first user_query timestamp |
| Last Cursor jsonl write | 09:06:01 | `agent-dbda65d2-….jsonl` mtime (25 lines; the aborted fetch is **not** in that file — it lived on the pi bridge) |
| User “how long are you fetching” | 09:27 | this abort / complaint |
| Counted | 09:28:37 | `date -Iseconds` when the duration was computed |

**Best estimate for the hung call:** **~21 minutes** (09:06 → 09:27), from last
recorded Cursor activity until abort. Could be shorter if the answer-mode
call started after 09:06; could be the whole remaining session.

**Whole session until complaint:** **33 minutes** (08:54 → 09:27). That includes
clarify/search work, not only the last fetch.

`/usr/bin/time` is not installed on this host (`そのようなファイルやディレクトリはありません`),
so a follow-up timed curl of the same README was not recorded.

## Acceptance criteria

- [x] Cursor agents treat `fetch_content` `mode=answer` as unsafe for docs: use
      `mode=raw` on a **small** URL, or `curl --max-time 8`, or skip the fetch.
      (`.cursor/rules/pi-fetch-content.mdc`, alwaysApply, 2026-08-21)
- [x] Wiki / GitHub HTML pages are not fetched whole when a raw file exists.
- [x] A hung fetch is aborted quickly; work continues from local knowledge.
      (policy: do not start `mode=answer`; use `curl --max-time 8`; do not wait
      on a silent fetch)

## Root cause (2026-08-21)

`pi-web-access` `fetch_content` HTTP extract times out around 30s
(`DEFAULT_TIMEOUT_MS`). `mode=answer` then calls `answerFromPage()`
(`page-query.ts`), a second LLM `complete()` on the current Pi model with
**no deadline** — only the caller abort `signal`. Abort surfaces as
`Error: Page answer failed: Aborted`. This repo does not own that package;
the standing fix for Cursor is `.cursor/rules/pi-fetch-content.mdc`
(alwaysApply). Do not put this incident in `AGENTS.md` (shared by non-Cursor agents).

## Notes

- Do **not** retry the aborted SwayNC README answer-mode fetch. The waybar
  module JSON is the well-known `swaync-client -swb` snippet.
- Pi wiki fetch earlier in the same session already demonstrated the failure
  mode: huge HTML, then `get_search_content` paging.
- Cursor standing copy: [`.cursor/rules/pi-fetch-content.mdc`](../../.cursor/rules/pi-fetch-content.mdc).
  Session chat is not loaded. `AGENTS.md` is shared with non-Cursor agents; keep incidents out of it.
