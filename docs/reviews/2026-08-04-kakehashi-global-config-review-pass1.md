# kakehashi-global-config — Review pass-1 (aggregate)

**Date:** 2026-08-04
**Subject:** [Global kakehashi configuration design](../specifications/implementations/2026-08-04-kakehashi-global-config-design.md)
**Per-letter reviews:**
[A-factual](2026-08-04-kakehashi-global-config-review-pass1-A-factual.md),
[D-consistency](2026-08-04-kakehashi-global-config-review-pass1-D-consistency.md)

## Verdict

**Approved.** Both reviewers returned "Request changes" with 11 findings
(A: 3 HIGH, 2 MEDIUM, 1 LOW; D: 1 HIGH, 3 MEDIUM, 1 LOW). All findings are
addressed in the revised design (§9 response table); no finding remains
`open` / `REGRESSION` / `blocked`. Two findings changed the deliverable
itself (workspaceMarkers transcription; emmylua_ls binary), both verified
at implementation time.

## Findings disposition

| ID | Severity | Status | Disposition |
|---|---|---|---|
| A-F1 | HIGH | addressed | workspaceMarkers transcribed as-is from lspconfig/`vim.fs.root`; rust_analyzer approximation documented |
| A-F2 | HIGH | addressed | full eight-server resolution + end-to-end LSP pull verification (§5.4); mapping-based sync test |
| A-F3 | HIGH | addressed | spec 02 Layer-4 `paru` rule cited; spec 24 declared inapplicable |
| A-F4 | MEDIUM | addressed | proxy described as observed host state; rollback split |
| A-F5 | MEDIUM | addressed | clangd doxygen exclusion documented |
| A-F6 | LOW | addressed | user commit `94f5556` recorded; delta re-scoped |
| D-F1 | HIGH | addressed | I-KC2 server→provider mapping contract |
| D-F2 | MEDIUM | addressed | same as A-F3 |
| D-F3 | MEDIUM | addressed | spec 20 I-KAKEHASHI6 narrowed to final-image property (user-approved) |
| D-F4 | MEDIUM | addressed | link conventions per spec 00 §7 |
| D-F5 | LOW | addressed | same as A-F6 |

## Verified premises (post-revision)

- P1: `vim.fs.root` source (`/usr/share/nvim/runtime/lua/vim/fs.lua`,
  `M.root`) confirms in-order top-level entries; kakehashi's
  `workspaceMarkers` semantics match — the transcription is faithful.
- P2: `cargo:emmylua_ls` (0.24.0) installs the `emmylua_ls` binary;
  end-to-end pull produced 2 errors + 1 hint on a broken Lua file.
- P3: `paru -S rust-analyzer` → `/usr/sbin/rust-analyzer` (extra repo
  `20260608-1`); stale rustup proxy removed; version check passes.
- P4: pytest suite `41 passed`; `make gen-deps` idempotent.
- P5: `chezmoi apply` installed `~/.config/kakehashi/kakehashi.toml`; all
  eight `cmd[0]` resolve.
- P6: spec 20 I-KAKEHASHI6 reworded; Containerfile pre-pass flow verified
  (scratch rendered into `/tmp/build-home`, removed in Stage 4).

## Open questions

None remaining for this design.
