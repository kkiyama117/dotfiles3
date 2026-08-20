# yazi wrapper: launch yazi, and on exit jump to the directory yazi was in.
# Uses zoxide's own cd (`__zoxide_cd` — the same function `z`/`zi` call
# internally) instead of `builtin cd`, so the frecency DB is updated through
# the chpwd hook. `z <abspath>` would query the DB and can miss dirs not yet
# tracked; `__zoxide_cd` cds to the exact path and registers it.
# Based on the official yazi wrapper (https://yazi-rs.github.io/docs/quick-start).
function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	yazi "$@" --cwd-file="$tmp"
	if cwd="$(command cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
		__zoxide_cd "$cwd"
	fi
	rm -f -- "$tmp"
}