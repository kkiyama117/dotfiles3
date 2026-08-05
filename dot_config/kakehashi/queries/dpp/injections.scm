; dpp -> lua injection.
;
; Every hook block's content is Lua: `lua_*` hooks are run as `:lua` by
; dpp.vim, and other blocks (`-- rust {{{` etc.) are Vimscript ftplugin
; keys whose content is wrapped in `lua << EOF` / `EOF` heredocs — still
; Lua.
; TODO: Treat `other blocks` as Vimscript, and set the config of `lua in
; Viml`
;
; Capture the WHOLE `hook_block` node (start marker + content + end marker)
; as ONE contiguous injection region per block:
;
;   - Contiguous is required by kakehashi for edit-carrying methods
;     (textDocument/completion, rename, inlayHint, codeAction, ...): the
;     previous per-line + `injection.combined` design merged all blocks into
;     ONE non-contiguous virtual document (markers/wrappers became gaps),
;     so kakehashi refused to bridge completion ("dpp source" = the ddc lsp
;     completion source produced nothing).
;   - The marker lines (`-- name {{{` / `-- }}}`) are valid Lua comments, so
;     they are harmless in the virtual document.
;   - One region per block also means kakehashi can map hover/completion/
;     diagnostics positions per block (marker line = virtual line 0).
;
; Downside: inside `-- rust {{{`-style blocks the `lua << EOF` / `EOF`
; wrapper lines are now part of the virtual document, so emmylua reports one
; spurious `expected '=' for assignment` diagnostic per wrapped block. This
; is the price of a contiguous region; the previous design traded away all
; edit-carrying LSP features to avoid it.
;
; NOTE (why the extra parens): tree-sitter parses each `(#set! ...)` as a
; STANDALONE pattern unless the whole thing is wrapped in one more pair of
; parentheses. Unwrapped, the `injection.language` property lands on an
; empty pattern, `extract_injection_language` finds nothing, and kakehashi
; resolves zero regions (no hover/completion/diagnostics at all — the
; "host bridging not opted in" fallthrough).

(
  (hook_block) @injection.content
  (#set! injection.language "lua")
  ; hook_block has named children (marker/content lines) that span the whole
  ; block; without include-children kakehashi computes the GAPS between them
  ; as the "included" ranges — zero-width here — so the virtual document
  ; would be EMPTY and emmylua would answer no completion/hover/diagnostics.
  (#set! injection.include-children)
)

