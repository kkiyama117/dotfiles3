# Steal List: pi-workflows → pi (dotfiles3) and DSH

> **Status:** IDEA MEMO (not an implementation plan). Naming deviates from
> `00-document-management.md` (`-impl.md` reserved for mechanical checklists);
> if any item is adopted, file an issue + design doc under
> `docs/specifications/implementations/` first.
>
> **Source:** [osolmaz/pi-workflows](https://github.com/osolmaz/pi-workflows)
> v0.11.2 (2026-08-21 checkout), announced in
> [@onusoz tweet 2090167392878117288](https://x.com/onusoz/status/2090167392878117288).
> License MIT, WIP. Verified locally: engine + `piw` TUI build & run.
>
> **Applicability targets:** `pi` = this repo's agent workflow (AGENTS.md +
> docs/specifications + superpowers skills). `DSH` = `~/.dsh` Deepseek harness
> (profiles: dsh-tui/headless/web; skills: implement-task, ponytail, …).

## Already covered — do NOT steal

| Feature in pi-workflows | pi equivalent | DSH equivalent |
| --- | --- | --- |
| Plan → execute flow | superpowers `writing-plans` + `docs/plans/` | `implement-task` skill |
| Review loop (request/receive) | superpowers `requesting-code-review` / `receiving-code-review` + `09-review.md` | — |
| Verification before done | superpowers `verification-before-completion` | — |
| Subagent-driven execution | superpowers `subagent-driven-development` | — |

Stealing here would be re-inventing what already works. Only the **bounded-loop
rules** (below) are new.

## Candidate steals (sorted by value / effort)

| # | Idea | What it does (source) | pi applicability | DSH applicability | Effort |
| --- | --- | --- | --- | --- | --- |
| 1 | **P2/P3 stop rule** | Review rounds record P0–P2. P0/P1 → must re-review; P2-only → fix + verify WITHOUT re-review; P3 untracked. `docs/WORKFLOW_COMPOSITION.md` | Add to `09-review.md`: stop condition so the loop cannot chase issues ad infinitum | Same rule in harness AGENTS.md | S |
| 2 | **Approval gate (autoplan)** | Model builds plan, human approves (or rejects) before execution; pings a channel (Telegram) | Currently no gate between `docs/plans` and execution — add a "plan → approve → start" convention | Add gate to `implement-task` | S |
| 3 | **Bounded CI watch** | One watch ≤ 5 min, per-PR isolation, run local tests while pending, never invent ETA. `docs/workflows.md` | Container build / dependency checks (`make build`, `make gen-deps`) get timeboxed reporting | — | M |
| 4 | **Monitor loop** | Periodic (`everyMinutes`) check → one concise report → continue / repair (if authorized) / stop | Could watch container freshness / secret expiry (08-automations.md) | `task-board` periodic jobs | M |
| 5 | **Run bundle / session capture** | Self-contained replay dir: `trace.ndjson` source of truth + `state.json` projection + `session/events.ndjson` + `capture.json` integrity, 0700/0600 | docs/reviews + result-log become machine-checkable; large outputs externalized (sha256 artifacts) | `~/.dsh/sessions` gets replayable event journal | L |
| 6 | **piw viewer + live replay protocol** | ratatui TUI: browse / follow / replay; `piw serve` (WebSocket, loopback-only) + `piw connect`; Herdr plugin (Ctrl+Shift+R piw) | Direct win: we already run Herdr; install `pi-workflows` → view runs | `dsh-tui` profile could gain session viewer | M (install) / L (port) |
| 7 | **Command batches** | Bounded parallel commands, stable IDs, per-command timeout + output cap, results in input order | `programs/generate_deps` parallelize w/o scatter | Parallel tool execution in harness | M |
| 8 | **Checkpoint / parking** | Run pauses at `waiting`; resume with a new attempt; immutable bundle while waiting | Human-in-the-loop for risky changes (e.g., container rebuild) | Same | M |
| 9 | **Decision records** | request/answer/resolution fences, digest-bound, redeliverable; rejected/expired sealed | Formalize approval artifacts under `docs/issues/` | Same | L |
| 10 | **Security posture** | Private perms by default, loopback-only server, no PATH search for host, size caps (4 MiB) | Apply to any future web/WS surface (also DSH `web` profile) | Same | S |
| 11 | **Parity/golden fixtures** | TS ↔ Rust renderers pinned by fixtures; `npm run fixtures` regenerates | Generalize: fixture tests for `generate_deps` outputs | — | M |
| 12 | **Herdr plugin** | Native plugin: `/piw` command, pane placement, run title tracking | Free if #6 adopted | — | 0 (comes with #6) |

## Do NOT steal (YAGNI for us)

- The full graph engine (`defineWorkflow`, controllers, composition): dotfiles
  repo + personal harness do not need multi-repo orchestration; skills already
  approximate the flow at far lower cost.
- Telegram decision channels / digests / redacted receipts: only pays off with
  many human decisions per day.
- TS/Rust renderer parity machinery: #11 generalizes instead.

## Recommended first moves

1. **pi**: adopt #1 (edit `09-review.md`) and #2 (one paragraph in AGENTS.md or
   `00-document-management.md`) — zero new dependencies.
2. **pi**: `cargo install pi-workflows` (already done in this session) + Herdr
   integration → see runs of future workflows.
3. **DSH**: discuss with maintainer where the approval gate + P2 rule live
   (`AGENTS.md` vs skill), then patch the skill.

## Open questions

- Does DSH want a replayable session format at all (is `~/.dsh/sessions`
  already stable enough)?
- Who approves autoplan plans in our usage — Telegram (new dependency) or
  plain terminal prompt (pi's existing intercom ask)?
