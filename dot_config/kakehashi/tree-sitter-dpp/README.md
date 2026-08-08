# tree-sitter-dpp

Grammar for dpp.vim hooks files (`*.dpp`): hook blocks delimited by
`-- name {{{` / `" name {{{` and `-- }}}` / `" }}}` comment markers.

Used by [kakehashi](https://github.com/atusy/kakehashi) (the sole LSP client
in this nvim config) to parse dpp files and inject each block's content
(`queries/dpp/injections.scm`):
- `lua_*` blocks are injected as Lua, which is then bridged to emmylua_ls —
  the only path that reaches emmylua, since it keys documents by URI
  extension (injected docs carry `kakehashi-virtual-uri-*.lua`).
- `hook_*` and target-filetype blocks are injected as Vimscript (the
  `lua << EOF` heredoc wrapper is valid Vimscript, parsed natively by the
  vim grammar, which injects the body as lua for kakehashi's own features;
  no bridged server handles vim, so viml blocks get no LSP features).

## Layout

- `grammar.js` — grammar source (mirrors dpp.vim's `parseHooksFile()` rules)
- `tree-sitter.json` — CLI metadata (ABI 15)
- `src/` — generated parser C sources
- `dpp.so` — build artifact; the runtime copy lives at `../parser/dpp.so`
- `build.sh` — regenerate + compile (`tree-sitter generate` + `cc -shared`)

## Semantics (vs dpp.vim's parseHooksFile)

| dpp.vim | this grammar |
|---------|--------------|
| start: line containing `{{{` with `\s+name\s*` before it | `-- name {{{` / `" name {{{` (comment-prefixed only) |
| end: line ending with `}}}` | `-- }}}` / `" }}}` (with optional trailing ws) |
| nesting: any line ending `{{{` inside a block | nested marker blocks |
| hook name charset | `[0-9a-zA-Z_-]+` |

Two start-marker node types split blocks by hook name, which determines the
content language:
- `lua_start_marker_line` — `lua_*` hooks (content is Lua)
- `viml_start_marker_line` — everything else (`hook_*` hooks and
  target-filetype blocks; content is Vimscript)

Both accept the `--` (lua-style) and `"` (viml-style) comment prefixes. The
`lua_*` rule is listed first so the lexer's longest-match tie-break assigns
`lua_*` names to the lua type.

Lexing note: marker/wrapper rules are single regex tokens that include the
trailing newline, making them strictly longer than the content token
(`[^\n]*`), so tree-sitter's longest-match lexer recognizes them
unambiguously. Consequence: marker lines have no sub-nodes (no separate
hook-name capture) — the two block kinds are distinguished by node type.

## Injection design

`queries/dpp/injections.scm` captures each whole `hook_block` node (start
marker + content + end marker) as ONE contiguous injection region per
block, keyed by the start-marker node type. Contiguity is required by
kakehashi for edit-carrying methods (completion, rename, inlayHint,
codeAction): the previous per-line + `injection.combined` design merged all
blocks into one non-contiguous virtual document, so kakehashi refused to
bridge completion. The marker lines are valid comments in both languages
(`-- name {{{` is a Lua comment, `" name {{{` a Vimscript comment), so they
are harmless in the virtual document. One region per block also lets
kakehashi map hover/completion/diagnostics positions per block (marker line
= virtual line 0).
