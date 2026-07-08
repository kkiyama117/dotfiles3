#!/usr/bin/env zsh

set -eu
setopt pipefail

repo_root="${0:A:h:h:h}"
source "$repo_root/dot_config/zsh/sheldon_hooks/zoxide-zi.zsh"

function fail() {
    print -ru2 -- "FAIL: $*"
    exit 1
}

typeset -g cd_target=''

function zoxide() {
    [[ "$1" == "query" ]] || fail "expected zoxide query, got: $*"
    [[ "$2" == "-l" ]] || fail "expected zoxide query -l, got: $*"
    [[ "$3" == "--" ]] || fail "expected zoxide query -l --, got: $*"

    print -r -- "/tmp/zi target"
}

function sk() {
    local preview_seen=0
    local arg
    local line
    local -a candidates

    for arg in "$@"; do
        [[ "$arg" == "--preview=\command -p ls -F --color=always {}" ]] && preview_seen=1
    done

    (( preview_seen )) || fail "expected preview to use the selected path as a single quoted placeholder"

    # Consume stdin and simulate selecting a path containing a space.
    while IFS= read -r line; do
        candidates+=("$line")
    done

    (( ${#candidates[@]} == 1 )) || fail "expected one candidate, got ${#candidates[@]}"
    [[ "${candidates[1]}" == "/tmp/zi target" ]] || fail "expected plain path candidate, got: '${candidates[1]}'"

    print -r -- "${candidates[1]}"
}

function __zoxide_cd() {
    cd_target="$1"
}

__zoxide_zi

[[ "$cd_target" == "/tmp/zi target" ]] || fail "expected cd target '/tmp/zi target', got: '$cd_target'"
