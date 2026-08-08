; dpp -> lua / vim injection.
;
; Block kind is determined by the hook name (the grammar splits start
; markers into two node types):
;   - lua_* blocks (`-- lua_add {{{` / `" lua_add {{{`): content is Lua,
;     run as `:lua` by dpp.vim.
;   - hook_* and target-filetype blocks (`" hook_add {{{`, `-- go {{{`):
;     content is Vimscript (hook_add/hook_source run as Vimscript; ftplugin
;     keys are Vimscript too). The `lua << EOF` / `EOF` heredoc wrapper is
;     valid Vimscript, parsed natively by the vim grammar, which injects the
;     heredoc body as lua (vim's own injections).
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
;   - The marker lines are valid comments in both languages (`-- name {{{`
;     is a Lua comment, `" name {{{` a Vimscript comment), so they are
;     harmless in the virtual document.
;   - One region per block also means kakehashi can map hover/completion/
;     diagnostics positions per block (marker line = virtual line 0).
;
; NOTE (why the extra parens): tree-sitter parses each `(#set! ...)` as a
; STANDALONE pattern unless the whole thing is wrapped in one more pair of
; parentheses. Unwrapped, the `injection.language` property lands on an
; empty pattern, `extract_injection_language` finds nothing, and kakehashi
; resolves zero regions (no hover/completion/diagnostics at all — the
; "host bridging not opted in" fallthrough).

; lua_* blocks -> lua
(
  (hook_block
    (lua_start_marker_line)) @injection.content
  (#set! injection.language "lua")
  ; hook_block has named children (marker/content lines) that span the whole
  ; block; without include-children kakehashi computes the GAPS between them
  ; as the "included" ranges — zero-width here — so the virtual document
  ; would be EMPTY and emmylua would answer no completion/hover/diagnostics.
  (#set! injection.include-children)
)

; hook_* / target-filetype blocks -> vim
(
  (hook_block
    (viml_start_marker_line)) @injection.content
  (#set! injection.language "vim")
  (#set! injection.include-children)
)
