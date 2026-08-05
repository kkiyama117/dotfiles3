# tree-sitter-dpp

Grammar for dpp.vim hooks files (`*.dpp`): "almost Lua" files containing
hook blocks delimited by `-- name {{{` / `-- }}}` comment markers.

Used by [kakehashi](https://github.com/atusy/kakehashi) (the sole LSP client
in this nvim config) to parse dpp files and inject each block's content as
Lua (`queries/dpp/injections.scm`), which is then bridged to emmylua_ls —
the only path that reaches emmylua, since it keys documents by URI
extension (injected docs carry `kakehashi-virtual-uri-*.lua`).

## Layout

- `grammar.js` — grammar source (mirrors dpp.vim's `parseHooksFile()` rules)
- `tree-sitter.json` — CLI metadata (ABI 15)
- `src/` — generated parser C sources
- `dpp.so` — build artifact; the runtime copy lives at `../parser/dpp.so`
- `build.sh` — regenerate + compile (`tree-sitter generate` + `cc -shared`)

## Semantics (vs dpp.vim's parseHooksFile)

| dpp.vim | this grammar |
|---------|--------------|
| start: line containing `{{{` with `\s+name\s*` before it | `-- name {{{` (comment-prefixed only) |
| end: line ending with `}}}` | `-- }}}` (with optional trailing ws) |
| nesting: any line ending `{{{` inside a block | nested `-- name {{{` blocks |
| hook name charset | `[0-9a-zA-Z_-]+` |

Lexing note: marker/wrapper rules are single regex tokens that include the
trailing newline, making them strictly longer than the content token
(`[^\n]*`), so tree-sitter's longest-match lexer recognizes them
unambiguously. Consequence: marker lines have no sub-nodes (no separate
hook-name capture).

## Injection design

`queries/dpp/injections.scm` captures each content `line` inside
`hook_block` with `injection.combined`; kakehashi merges all captures of a
pattern (document-wide) into one virtual Lua document, with gaps (wrapper
lines `lua << EOF` / `EOF`, markers, nested blocks) becoming blank lines.
Diagnostics/hover map back to host positions per line. The wrapper lines
are deliberately excluded: `lua << EOF` is not valid Lua and would produce
a spurious emmylua error per block.
