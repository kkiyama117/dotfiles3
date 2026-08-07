# Review prompt — kakehashi global config design (pass 1, letters A + D)

## Subject

- Design: `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md`
- Issue: `docs/issues/2026-08-04-kakehashi-global-config.md`

## Common output format

Follow spec 09 §3 (`docs/specifications/09-review.md`): header + Verdict +
Findings table (severity per finding) + Verified premises + Open questions.
Findings statuses: `open` / `RESOLVED` / `addressed` / `INCOMPLETE` /
`blocked`.

## Reviewer-A (factual / correctness)

Read: the design + issue, and these cited sources:

- `dot_config/kakehashi/kakehashi.toml` (the actual proposed file)
- `dot_config/mise/config.toml`
- `dependencies/packages.toml` (rust-analyzer entry, kakehashi entry)
- `/tmp/kakehashi/docs/README.md` (upstream config reference; also
  `/tmp/kakehashi/docs/architecture-decisions/configuration-merging-strategy.md`,
  `host-document-bridge.md`)
- nvim bridge contract: `~/.config/nvim/lua/vimrc/kakehashi_config.lua`
  and `lua/vimrc/kakehashi_bridge.lua` (referenced via `~/.config/nvim`)

Evaluate: every factual claim against the cited sources — the eight-server
inventory, bare-command `cmd`s, `workspaceMarkers` shape/semantics
(flat = priority order vs nested = equal group), merge `'keep'` behavior,
`has_configs` flip, spec 24 paru criteria for rust-analyzer, the stale
rustup-proxy claim. Flag false premises and logical gaps. Do NOT edit
files.

## Reviewer-D (consistency / cross-doc)

Read: the design + issue + ALL of `docs/specifications/` + the
`docs/specifications/implementations/2026-07-16-kakehashi-container-install-design.md`
and the docs listed for Reviewer-A.

Evaluate: naming, link paths (repo-relative, spec 00 §7), section-number
references, contradictions vs prior specs (02, 20, 21, 24), and whether
the stated non-changes (Containerfile/Makefile/specs 20-21/nvim config)
are truly non-changes given the inventory edits. Do NOT edit files.
