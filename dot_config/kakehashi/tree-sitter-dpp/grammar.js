// tree-sitter-dpp: grammar for dpp.vim hooks files (*.dpp).
//
// Mirrors dpp.vim's parseHooksFile() (denops/dpp/utils.ts):
//   - hook blocks are delimited by `-- name {{{` / `" name {{{` (start) and
//     `-- }}}` / `" }}}` (end) comment markers
//   - hook name charset: [0-9a-zA-Z_-]+ with whitespace before the marker
//   - end marker line ENDS with `}}}` (we additionally require the `--`/`"`
//     comment prefix; dpp tolerates any prefix, but hooks files use one)
//   - lines ending with `{{{` inside a block nest (we only nest on full
//     marker lines; dpp nests on any line ending `{{{`)
//
// Two start-marker node types split blocks by hook name, which determines
// the content language:
//   - lua_start_marker_line: `lua_*` hooks (content is Lua)
//   - viml_start_marker_line: everything else (`hook_*` hooks and
//     target-filetype blocks; content is Vimscript)
// Both accept the `--` (lua-style) and `"` (viml-style) comment prefixes.
// The lua_* rule is listed FIRST so the lexer's longest-match tie-break
// (first rule wins on equal length) assigns `lua_*` names to the lua type.
//
// Lexing trick: every marker/wrapper rule is ONE regex token that includes
// the trailing newline, so it is strictly LONGER than the content token
// (`[^\n]*`, which cannot span a newline). tree-sitter's lexer picks the
// longest match, so marker lines are recognized unambiguously even though
// content could otherwise swallow them. Consequence: marker lines have no
// sub-nodes (the hook name is not separately capturable) — fine for our
// queries, which distinguish the two block kinds by node type.
//
// The `lua << EOF` / `EOF` wrapper (user convention for viml blocks:
// valid Vimscript heredoc, parsed natively by the vim grammar) is modeled
// as distinct node types so injections can exclude them.
module.exports = grammar({
  name: 'dpp',

  // No implicit whitespace: all whitespace is explicit inside the tokens
  // (newline must never be skipped between tokens).
  extras: ($) => [],

  rules: {
    document: ($) =>
      repeat(
        choice(
          $.hook_block,
          $.line,
          // Safety nets for stray markers/wrappers outside a block
          // (unbalanced files must not hard-error).
          $.end_marker_line,
          $.wrapper_start_line,
          $.wrapper_end_line,
        ),
      ),

    // hook block: `-- name {{{` ... content ... `-- }}}` (nested blocks ok)
    hook_block: ($) =>
      seq(
        choice($.lua_start_marker_line, $.viml_start_marker_line),
        repeat(choice($.hook_block, $.hook_line)),
        $.end_marker_line,
      ),

    // -- lua_add {{{  /  " lua_add {{{  (lua_* hook: content is Lua)
    lua_start_marker_line: ($) => /[ \t]*(?:--|")[ \t]+lua_[0-9a-zA-Z_-]*[ \t]*\{\{\{[^\n]*\n/,

    // -- hook_add {{{  /  " go {{{  (hook_* or filetype: content is Vimscript)
    viml_start_marker_line: ($) => /[ \t]*(?:--|")[ \t]+[0-9a-zA-Z_-]+[ \t]*\{\{\{[^\n]*\n/,

    // -- }}}  /  " }}}  (line must end with }}}; we allow trailing whitespace)
    end_marker_line: ($) => /[ \t]*(?:--|")[ \t]*\}\}\}[ \t]*\n/,

    // content line (any line that is not a marker/wrapper)
    line: ($) => seq(/[^\n]*/, '\n'),

    // lua << EOF  (here-doc start; any terminator identifier accepted)
    wrapper_start_line: ($) => /[ \t]*lua[ \t]*<<[ \t]*[A-Za-z_][A-Za-z0-9_]*[ \t]*\n/,

    // EOF  (here-doc end; hardcoded to the user's convention)
    wrapper_end_line: ($) => /[ \t]*EOF[ \t]*\n/,

    // a line inside a hook block: content line or wrapper
    hook_line: ($) => choice($.line, $.wrapper_start_line, $.wrapper_end_line),
  },
});
