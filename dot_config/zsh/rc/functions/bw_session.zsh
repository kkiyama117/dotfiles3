# Interactive Bitwarden session helper.
#
# Entrypoint auth (spec 13 §4) already unlocks bw for runtime chezmoi apply.
# Use bw_session() only when you need BW_SESSION in the current shell
# (e.g. podman exec, manual chezmoi apply, debugging).
#
# Does NOT persist BW_SESSION to a keyring.

bw_session() {
  if [[ -r /run/secrets/bw_password ]]; then
    export BW_SESSION="$(
      bw unlock --passwordfile /run/secrets/bw_password --raw
    )"
  else
    export BW_SESSION="$(bw unlock --raw)"
  fi
}
