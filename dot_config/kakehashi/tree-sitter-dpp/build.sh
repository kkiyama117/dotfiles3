#!/bin/sh
# Rebuild the tree-sitter-dpp parser shared library.
#
# Requires: tree-sitter-cli (>= 0.25, ABI 15) and a C compiler.
# Output: dpp.so (build artifact) — install it with:
#   cp dpp.so ../parser/dpp.so
#
# kakehashi loads the `tree_sitter_dpp` symbol from ../parser/dpp.so
# (see lua/vimrc/kakehashi_config.lua: languages.dpp.parser).
set -eu
cd "$(dirname "$0")"

tree-sitter generate
cc -shared -fPIC -O2 -I src -o dpp.so src/parser.c
echo "built dpp.so ($(nm -D dpp.so | grep tree_sitter_dpp))"
