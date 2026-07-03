# ssh-container-setup — Review pass-1 (Aggregate)

**Date:** 2026-07-03
**Reviewer:** design author (aggregation of 5 subagent per-letter reviews)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** done (all findings acknowledged; design revised in same commit)

## Per-letter reviews

| Letter | Perspective | Verdict | File |
|---|---|---|---|
| A | factual / correctness | Approve with conditions | [`pass1-A-factual.md`](2026-07-03-ssh-container-setup-review-pass1-A-factual.md) |
| B | security | Approve with conditions | [`pass1-B-security.md`](2026-07-03-ssh-container-setup-review-pass1-B-security.md) |
| C | architecture / senior engineering | Approve with conditions | [`pass1-C-architecture.md`](2026-07-03-ssh-container-setup-review-pass1-C-architecture.md) |
| D | consistency / cross-doc | Approve with conditions | [`pass1-D-consistency.md`](2026-07-03-ssh-container-setup-review-pass1-D-consistency.md) |
| E | operability / runtime | Approve with conditions | [`pass1-E-operability.md`](2026-07-03-ssh-container-setup-review-pass1-E-operability.md) |

## Deduplicated findings (post-revise status)

| ID | Origin | Summary | Post-revise status |
|---|---|---|---|
| H1 | A-F1, D-F1 | spec 21 acceptance `#17–#20` collides with existing #17 | **RESOLVED** — **#18–#21** |
| M1 | A-F2, C-F8, E-F1 | Containerfile + spec 21 Notes still say "four/five" volumes | **RESOLVED** — six runtime mounts / five named volumes + Notes update |
| M2 | D-F2, C-F4 | I-SSH under "Runtime" vs actual I-GPG placement in Build section | **RESOLVED** — I-SSH* under Build (Containerfile); rollout in spec 21 #21 |
| M3 | D-F3, E-F3 | spec 03 not in sync list; GNUPG_VOLUME already missing | **RESOLVED** — spec 03 added; backfill GNUPG_VOLUME |
| M4 | B-F1, A-F4, C-F3 | chezmoiignore patterns + `.pub` side effect + custom names | **RESOLVED** — §5.4 explicit; I-SSH4 weakened to conventional names |
| M5 | B-F2, C-F1 | manual import lacks no-bind-relay; spec 25 fully deferred | **RESOLVED** — §6 callout; spec 25 §1–3 at plumbing close (S9) |
| M6 | D-F4 | §2 Alt-B vs spec 23 "Approach B" glyph clash | **RESOLVED** — §6 disambiguation note |
| M7 | E-F2 | `${USERNAME}` in podman cp paths | **RESOLVED** — `dotfiles-manjaro:.ssh/...` |
| M8 | C-F2, C-F5 | no I-SSH6 agent posture; ssh-add in verification | **RESOLVED** — I-SSH6; `ssh -i` smoke |
| M9 | E-F1 | rollout without rebuild on existing deploy | **RESOLVED** — spec 21 #21 requires `make build` first |
| L1 | A-F3 | install flag order §4 vs §5.2 | **RESOLVED** — aligned to Layer 1-6 order |
| L2 | D-F5, E-F4 | help/clean strings vague ("toolchain") | **RESOLVED** — lists all five volumes |
| L3 | C-F6 | openssh has_configs=true unrealized | **addressed** — S1 + spec 20 note |
| L4 | D-F6 | spec 00 implementation/ vs implementations/ | **INCOMPLETE (out of scope)** — pre-existing |

## Open questions resolved

| OQ | Resolution |
|---|---|
| Q-C1 / Q-B2 | spec 25 §1–3 normative at plumbing close (GPG spec 23 precedent) |
| Q-C2 | config hand-edit → volume migration deferred to config issue spec 25 §rollout |
| Q1 agent | I-SSH6: no agent in plumbing |

## Verdict

**Approve (ready for implementation plan)** — no Critical/High blockers after revise.
Next step: implementation plan (`docs/plans/2026-07-03-ssh-container-setup-impl.md`), then code — **not in this commit** (user requested stop before implementation).

## Prioritized actions applied in the revise

1. (H1) spec 21 acceptance **#18–#21**
2. (M1) Containerfile + spec 21 Notes volume counts
3. (M2) I-SSH* placement + I-SSH6 agent posture
4. (M3) spec 03 sync + GNUPG_VOLUME backfill
5. (M4–M5) §5.4 / §6 security + spec 25 §1–3 scope
6. (M6–M9) §6 procedure + rollout #21
