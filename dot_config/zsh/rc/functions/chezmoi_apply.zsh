# Runtime chezmoi apply with Bitwarden session.
#
# Entrypoint apply (make up) already unlocks bw once; use chezmoi_apply for
# manual apply in podman exec shells or on the host where BW_SESSION is absent.
# With podman secrets mounted, bw_session is non-interactive.

chezmoi_apply() {
  bw_session
  chezmoi apply "$@"
}
