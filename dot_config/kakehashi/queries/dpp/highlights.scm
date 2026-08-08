; dpp host-level highlights. Injected lua/vim blocks are tokenized by the
; injection language's own highlights (kakehashi resolves injected regions
; against the injection language's queries), so no `; inherits: lua` /
; `; inherits: vim` is needed here.

(lua_start_marker_line) @comment
(viml_start_marker_line) @comment
(end_marker_line) @comment
(wrapper_start_line) @comment
(wrapper_end_line) @comment
