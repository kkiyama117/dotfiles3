# 20 — Container rules

> Spec status: **DRAFT (stub)**. Normative spec for the container's runtime
> contract. Build-flow specifics are split into
> [`21-container-build-flow.md`](21-container-build-flow.md); build-time envs
> live in [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).

## Invariants

Invariants are grouped by the phase they bind: **Runtime** (host &
`podman run`), **Secrets** (cross-cutting), and **Build** (`Containerfile`).
IDs are stable across the spec set, so cross-references use these `I<n>`
labels directly.

### Runtime (host & `podman run`)

- I1: **Rootless Podman only.** The container is never built or run as root on the host.
- I2: **`--userns=keep-id` is required** for any run that bind-mounts host files. The host UID/GID survive the user-namespace remap so bind-mount ownership (chezmoi-source, home dir) is preserved.
- I3: **No `:U` volume flag.** It recursively `chown`s the host directory, which is destructive.
- I-RUN1: **`make up` uses Podman `--init`.** The runtime command is a
  long-lived keepalive (`sleep infinity`), which must not be PID 1 because
  PID 1 ignores default `SIGTERM` handling. Podman's init process forwards
  stop signals so `make up --replace`, `podman stop`, and `make down` exit
  cleanly without falling back to `SIGKILL`.
- I-RUN2: **`make up` does not return until the entrypoint's `chezmoi apply`
  has finished.** Because `make up` is `podman run -d` (detached) and the
  entrypoint runs `chezmoi apply --no-tty --force` before `exec sleep
  infinity`, an immediate `make exec` would race the apply and start a
  zsh that sees the I10 baked `~/.zshenv` but **no** `~/.zshrc` /
  `~/.config/sheldon/plugins.toml` / `~/.config/starship.toml` — i.e.
  sheldon and starship never load on that first shell. To close the race,
  the entrypoint writes a readiness sentinel at `/tmp/chezmoi-applied`
  (`rm -f` at start so a container restart cannot satisfy the wait with a
  stale flag; `touch` only after `chezmoi apply` succeeds, so a failed
  apply never publishes readiness — `set -e` exits before the `touch`).
  Before publishing readiness, the entrypoint also seeds zoxide with
  `~/.local/share/chezmoi` so the first interactive `zi` invocation has
  the source bind available. The custom `zi` wrapper prepends `$HOME`
  directly to its no-argument picker because zoxide itself does not store
  the home directory,
  and `make up` polls `podman exec $(CONTAINER) test -f /tmp/chezmoi-applied`
  once per second up to `UP_WAIT_TIMEOUT` (default 120 s, covering Bitwarden
  auth + apply). If the container exits before the sentinel appears (apply
  failed) or the timeout elapses, `make up` exits non-zero and tails
  `podman logs` so the operator sees the apply error. The sentinel lives
  in `/tmp` (ephemeral per container, fresh on each `make up --replace`,
  not the chezmoi bind mount, not a named volume). The fix is a runtime
  readiness signal, NOT baking more files into the image — I10's
  "`~/.zshenv` only" policy is unchanged. See
  [`docs/issues/2026-07-06-make-up-races-chezmoi-apply.md`](../issues/2026-07-06-make-up-races-chezmoi-apply.md).
- I-RUN3: **`make up` refuses to run a stale image.** The readiness-sentinel
  wait loop (I-RUN2) only works if the running image's entrypoint actually
  contains the sentinel logic — an image built before an entrypoint edit
  would never write `/tmp/chezmoi-applied`, so `make up` would always hit
  `UP_WAIT_TIMEOUT` and report a misleading "chezmoi apply timed out". To
  close that foot-gun, `make up` depends on a `_verify_image_fresh` target
  that compares the SHA-256 of the source
  `container/bind/layer_5_files/entrypoint.sh` to the entrypoint inside the
  image (`podman run --rm --entrypoint /usr/bin/sha256sum $(IMAGE)
  /usr/local/bin/entrypoint.sh` — a throwaway container, no volumes, no
  entrypoint script, no `--userns`, ~1–2 s). On mismatch or missing image,
  `make up` exits non-zero with `run \`make build\` then re-run \`make up\``
  before starting the real container. The check is byte-hash based, so it
  catches ANY entrypoint drift, not just the sentinel. See
  [`docs/issues/2026-07-06-make-up-races-chezmoi-apply.md`](../issues/2026-07-06-make-up-races-chezmoi-apply.md).

### Secrets (build-time & runtime)

- I4: The image is secret-free in both phases. The build-time `chezmoi apply` pre-pass (Containerfile Stage 2) uses `build_mode = true`, which guards every Bitwarden-bound template; the scratch destination is deleted in Stage 5 (after the minimum `.zshenv` is copied out — see I10). The runtime `chezmoi apply` (entrypoint) authenticates `bw` from **podman secrets** (`podman secret create` + `podman run --secret`) mounted as tmpfs `/run/secrets/*`; the master password is consumed via `bw unlock --passwordfile` and **never** placed in an environment variable, and the client pair / `BW_SESSION` are `export`-ed only inside the entrypoint process and **scrubbed before `exec`** — so no Bitwarden credential appears in `podman inspect` `Env`, in `/proc/*/environ` after exec, or in any image layer. See [`13-secret-management.md`](13-secret-management.md) §4 / §5a.

> NOTE: `libsecret` arrives in the image only as a hard dependency of
> the `pinentry` package (library, not the `gnome-keyring` service). No
> secret-store daemon is installed or started; the Bitwarden-only
> secret model ([`13-secret-management.md`](13-secret-management.md)
> §2 Tier 1) is preserved. See I-GPG1..I-GPG5 below.

### Build (`Containerfile`)

- I5: **All packages must originate from `dependencies/packages.toml`.** Ad-hoc `pacman -S` / `paru -S` calls in the Containerfile are forbidden once `gen-deps` is wired.
- I6: **Every stage is built from a named `AS <stage>`** so downstream stages can `COPY --from=<stage>` without coupling to a layer ordinal.
- I7: **`builder` (remapped to `${USERNAME}`) is the only non-root account** inside the image; `USER` is set before any installation step that does not require root.
- I8: **Each `layer_<N>/<manager>.txt` is regenerated by `make gen-deps`** from `dependencies/packages.toml`; hand-editing layer txt files is forbidden.
- I9: **`/run/user/${HOST_UID}` is baked at Stage 5 (Layer 5-2)** (root `install -d -m 0700 -o ${HOST_UID} -g ${HOST_GID}`). The container has no `pam_systemd` to create the XDG runtime dir, but `/run` is rootfs (not tmpfs) under `podman run --userns=keep-id`, so the build-time dir persists and is writable at runtime. This lets the shared `.zshenv` line `export XDG_RUNTIME_DIR=/run/user/$UID` work identically on host (systemd creates it) and container, so tools that `MkdirAll($XDG_RUNTIME_DIR)` (e.g. `chezmoi cd`) don't fail with `mkdir /run/user/<uid>: permission denied`.
- I10: **The final image bakes a minimum `$HOME`** (`~/.zshenv` only — **NOT** `~/.config/chezmoi/chezmoi.toml`), copied in Stage 5 (Layer 5-2) from the Stage 2 `build-prepass` render before the scratch tree is dropped (Layer 5-3). The build-prepass `chezmoi.toml` (`build_mode = true`, rendered from `.chezmoi.toml.tmpl` by `chezmoi execute-template --init` with `BUILD_MODE=true`, USERNAME-owned) rides the Stage chain into the runtime image and is **stripped** in Layer 5-3; the runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is **re-rendered from the same `.chezmoi.toml.tmpl` by the entrypoint** (`BUILD_MODE` unset) as `${USERNAME}` before `chezmoi apply`. `BUILD_MODE` is inline in the Stage 2 `RUN` (not `ENV`), so it never appears in image `Env` / `podman inspect`. This makes the image boot into a **wizard-free, PATH-equipped, shell-usable state independent of the runtime entrypoint** (the shell is usable without the entrypoint, but `chezmoi apply` requires the entrypoint or a manually-created config) — covering (a) `make exec` racing the entrypoint's `chezmoi apply` (an exec'd interactive `zsh` would otherwise find no zsh startup file in `$HOME` and the `zsh/newuser` module would source `/usr/share/zsh/scripts/newuser`, launching the first-run `zsh-newuser-install` wizard; a single `~/.zshenv` suppresses it), and (b) the container being exec'd with the entrypoint bypassed (e.g. `podman run --entrypoint ...`). Safe because `dot_zshenv.tmpl` has no chezmoi template directives and no `build_mode` branch, so the Stage 2 render is byte-identical to the runtime `chezmoi apply --force` output (idempotent overwrite). See spec 21 acceptance #5a.
- I11: **No `/etc/skel` bash remnants in `$HOME`** (`.bashrc`, `.bash_profile`, `.bash_logout`, `.profile`). Stage 5 removes the files that Layer 1-3's `usermod -l ... -d /home/${USERNAME} -m builder` moves out of the base image's `builder` home; these are not chezmoi-managed, so `chezmoi apply` would never remove them. See spec 21 acceptance #5b.
- I12: **Container locales match `.zshenv` exactly.** Layer 1-2 generates only `ja_JP.UTF-8` and `en_US.UTF-8`, matching `LANG` / `LC_CTYPE` in `dot_zshenv.tmpl`; detailed build-flow behavior and verification live in spec 21 acceptance #7.
- I-GPG1: The GPG keyring is persisted via the Podman named volume
  `dotfiles_gnupg` mounted at `~/.local/share/gnupg` (= `GNUPGHOME`
  from `dot_zshenv.tmpl`), the same pattern as `dotfiles_cargo` /
  `dotfiles_rustup` / `dotfiles_mise`. The image carries no key
  material (extends I4 / [`13-secret-management.md`](13-secret-management.md)
  I-S4: the keyring lives only in the runtime volume).
- I-GPG2: `~/.local/share/gnupg` is baked owner-correct at `0700` in
  Containerfile Layer 1-6 (extension of the Layer 1-5 XDG-directory
  provisioning). `0700` is mandatory for `GNUPGHOME` (gpg strict
  permissions); the owner-correct provisioning prevents Podman from
  root-creating an absent mountpoint (the `/home` re-own failure mode,
  Layer 5-2).
- I-GPG3: `gpg-agent` / `pinentry` are runtime, on-demand only. No
  agent is baked into the image entrypoint; gpg auto-starts
  `gpg-agent` on first use, which uses the default `/usr/bin/pinentry`
  wrapper. No `gpg.conf` / `gpg-agent.conf` is chezmoi-managed in this
  phase (gpg runs on defaults).
- I-GPG4: No GPG key material is baked into any image layer. The
  build-time pre-pass (Stage 2, `build_mode = true`) never touches
  `gnupg` (the Layer 1-6 directory is empty at build time); the runtime
  keyring lives only in the `dotfiles_gnupg` named volume, never in an
  image layer or `podman inspect`.
- I-GPG5: `.chezmoiignore` lists `.local/share/gnupg` so chezmoi never
  manages the keyring (consistent with the `cargo` / `rustup` / `mise` /
  `chezmoi` ignore entries).

- I-CARGO2: `.chezmoiignore` excludes everything under
  `~/.local/share/cargo/` except `~/.local/share/cargo/config.toml` and `~/.local/share/cargo/binstall.toml`
  Chezmoi manages only the non-secret Cargo config; `$CARGO_HOME/bin`,
  registry data, and git cache are volume-owned and never touched by
  chezmoi. The build-prepass renders this config to
  `/tmp/build-home/.local/share/cargo/(filename).toml`, and the toolchain
  stage copies it under `$CARGO_HOME/` before Rust/cargo/AUR work.

- I-SSH1: The SSH client keyring is persisted via the Podman named volume
  `dotfiles_ssh` mounted at `~/.ssh`, the same pattern as `dotfiles_gnupg`
  (different path, same mechanics). The image carries no key material
  (extends I4 / [`13-secret-management.md`](13-secret-management.md)
  I-S4: keys live only in the runtime volume). No host `~/.ssh` bind mount.
- I-SSH2: `~/.ssh` is baked owner-correct at `0700` in Containerfile
  Layer 1-7 (extension of the Layer 1 XDG-directory provisioning,
  parallel to Layer 1-6 for gnupg). Owner-correct provisioning prevents
  Podman from root-creating an absent mountpoint (the `/home` re-own
  failure mode, Layer 5-2).
- I-SSH3: No SSH private key material is baked into any image layer. The
  build-time pre-pass (Stage 2, `build_mode = true`) never touches
  `~/.ssh` (the Layer 1-7 directory is empty at build time); runtime keys
  live only in the `dotfiles_ssh` named volume, never in an image layer or
  `podman inspect`.
- I-SSH4: `.chezmoiignore` excludes **everything under `~/.ssh/` except
  `~/.ssh/config`** (`.ssh/*` then `!.ssh/config`). Chezmoi manages only
  `~/.ssh/config`; all other entries (private/public keys, `known_hosts`,
  `config.d/*`) are volume-owned and never touched by chezmoi. This is a
  stricter, single-managed-file policy than the earlier conventional-key-name
  pattern list (I-GPG5 ignores the whole GPG keyring tree; SSH inverts it —
  ignore the tree, re-include the one non-secret config file).
- I-SSH5: `make clean` removes `dotfiles_ssh` alongside the other named
  volumes. Targeted reset and rollout safety live in spec 21 acceptance
  #22.
- I-SSH6: Plumbing phase wires **no** `ssh-agent` in the entrypoint or
  `dot_zshenv.tmpl`. File keys are used directly via `IdentityFile` /
  `ssh -i`. Agent wiring (`SSH_AUTH_SOCK`, gpg-agent SSH socket) is
  deferred to the config issue.

> NOTE: `openssh` is already declared in `dependencies/packages.toml`
> (`layer = 1`, `has_configs = true`). The `has_configs` flag is
> structurally accurate, but config sources are unrealized until the
> deferred config issue populates spec 25 §4+.

- I-GIT1: `~/.config/git/config` is rendered by chezmoi from
  `dot_config/git/config.tmpl`; `[user] name/email/signingkey` are injected
  from `.chezmoidata/git_config.yaml` (`{{ .git.identity_default.* }}`).
  The data file is the single source of identity; the template is the
  single source of the config structure.
- I-GIT2: `~/.config/git/ignore` is a static chezmoi-managed file
  (`dot_config/git/ignore`, no template): a verbatim port of the host
  global gitignore, which contains only generic toptal patterns (no
  personal/secret entries — verified). Read by git via the XDG default
  `core.excludesFile` (`$XDG_CONFIG_HOME/git/ignore`).
- I-GIT3: `credential.helper = libsecret` is gated to host runtime only
  by `{{ if and (not .build_mode) (eq .runtime "host") }}`. The container
  has no keyring daemon (I-GPG9); writing the line there would be a broken
  reference. The build-time pre-pass (`build_mode = true`) also omits it.
- I-GIT4: `commit.gpgsign = true`, `gpg.format = ssh`, and
  `user.signingkey = ~/.ssh/main` render in all modes (build + host runtime
  + container runtime). Signing is NOT gated by `runtime`; the host and
  container use the same Git configuration and their independently
  persisted copies of the same SSH file key.
- I-GIT5: No secret is baked into any image layer. `user.email` and
  `user.signingkey` (a path, not key material) are acceptable plain text.
  The SSH private key is never baked; the container obtains it at runtime
  in `dotfiles_ssh` (I-SSH1/I-SSH3). Extends I4 / spec 13 I-S4.
- I-GIT6: `delta` is provided by the `git-delta` Arch `extra` package
  (Layer 1, `packages.toml`), so `core.pager=delta` / `pager.*=delta` work
  identically in host and container. No gating needed for delta.
- I-GIT7: The `runtime` chezmoi data var (`host` | `container`, default
  `host`) is driven by the `DOTFILES_RUNTIME` env var in
  `.chezmoi.toml.tmpl`. Only `entrypoint.sh` sets it (to `container`); the
  build prepass does not need to (`build_mode = true` already suppresses
  the gated line). The host never sets it (defaults to `host`). This is the
  repo's host/container signal — `build_mode` alone is build-time vs
  runtime only (both host and container run with `build_mode = false`).

- I-AUR1: `paru` is bootstrapped exactly once, in the `aur` stage, via
  `makepkg -si` against the AUR `paru` PKGBUILD clone. No other stage
  runs `makepkg`.
- I-AUR2: Every AUR package installed in the image is listed in
  `dependencies/layer_4/paru.txt` (generated from `packages.toml`).
  Ad-hoc `paru -S` / `makepkg -si` for packages not in `packages.toml`
  is forbidden (extends I5 to the `paru` manager). `paru` itself is
  declared `manager = "custom"` (doc-only) — it appears in the spec 02
  AUTO-GEN block but is NOT in `paru.txt`, so its sole install path is
  the `aur`-stage bootstrap.
- I-AUR3: The paru/AUR clone+build cache (`~/.cache/paru`) and the
  pacman package cache (`/var/cache/pacman/pkg`) are backed by
  `--mount=type=cache` in every `aur`-stage `RUN` that fetches or
  builds. The cargo registry/git caches are also mounted (paru is a
  Rust package). The cache mounts are not written to image layers.
- I-AUR4: The `aur` stage's bootstrap clone (`/tmp/paru-build`) is
  removed before the stage ends so it cannot ride into the final image.
- I-MAKEPKG1: `/etc/makepkg.conf` is image-owned, not chezmoi-managed.
  The build-time `COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf`
  (Layer 1-2, before the first `pacman -Syu`) embeds the curated AUR/pacman
  compression (`PKGEXT`), `COMPRESSZST`, `MAKEFLAGS`, and build flags so
  every `paru -S` / `makepkg -si` in the `aur` stage and at runtime uses
  the host's preferred settings. `makepkg` still sources
  `/etc/makepkg.conf.d/*.conf` after the curated file; current base-image
  drop-ins (`fortran.conf`, `rust.conf`) are comment-only and do not
  override curated variables. To
  switch compression (e.g. xz → zstd), edit the bind file's `PKGEXT` line
  and re-run `make build` — no Containerfile edit required.
- I-INFRA1: **Toolchain installer binaries are infrastructure, not
  `packages.toml` entries.** A tool whose sole purpose is to
  install/manage other tools (an installer-of-installers) and which
  ships an official prebuilt binary is curl-bootstrapped in the
  Containerfile and is NOT declared in `packages.toml`. Instances:
  `rustup` (Layer 3-3), `cargo-binstall` (Layer 3-6). (`mise` is now a
  regular `pacman` package at Layer 1, not curl-bootstrapped infra; mise-managed
  languages install at Layer 3-4 from `dot_config/mise/config.toml`.)
  This is the formal carve-out from I5 for installer infra (the
  `paru` `manager = "custom"` doc-only mechanism is a separate,
  package-specific carve-out via I-AUR2).
- I-CARGO1: **`cargo-binstall` is the cargo instance of I-INFRA1.** It is
  bootstrapped at Layer 3-6 from a version-pinned (v1.20.1) + SHA256-gated
  (`f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e`)
  prebuilt musl tarball, extracted single-file to `$CARGO_HOME/bin`. Build-time
  cargo tools (`layer = 3`) install via `cargo binstall --only-signed -y`
  (signed prebuilt only — see [`24-rust-packages-rule.md`](24-rust-packages-rule.md)
  §3). `cargo-binstall` has no persistent download cache (per-run tempdir in
  `$CARGO_HOME`), so there is no BuildKit cache mount for binstall downloads.
- I-HERDR1: **`herdr` is installed only through mise.** It is declared as
  `"aqua:ogulcancelik/herdr" = "latest"` in `dot_config/mise/config.toml`
  (explicit aqua backend required by `disable_default_registry = true`). Layer
  3-4 installs it under `$MISE_DATA_DIR` during the build via `mise install
  --yes`. There is no `packages.toml` entry, no Containerfile curl bootstrap,
  and no `herdr update` or image-rebuild path for routine upgrades — operators
  use `mise upgrade aqua:ogulcancelik/herdr` on host or inside the container.
  The `"latest"` policy matches other mise-managed globals: the exact version
  resolved at install/upgrade time is intentionally non-reproducible at the
  config layer.
- I-HERDR2: **`herdr` is on PATH via mise shims, persisted in
  `dotfiles_mise`.** `dot_zshenv.tmpl` activates mise shims; `which herdr`
  resolves under `$MISE_DATA_DIR/shims`, not `~/.local/bin/herdr`. Layer 3-4
  installs `herdr` into `$MISE_DATA_DIR` inside the image. On the **first**
  `make up` with an empty `dotfiles_mise` volume, Podman copy-on-first-mount
  seeds the volume from the image tree (same pattern as spec 21 acceptance
  #14). If `dotfiles_mise` already exists from before this migration, it will
  **not** gain the aqua install on `make up` alone — operators must run a
  one-time `podman volume rm dotfiles_mise` (see spec 21 acceptance #25;
  `make clean` is broader and also removes the image and other volumes).
  After the aqua install is present, `make down && make up` preserves `herdr`
  across restarts via the named volume.
- I-HERDR3: **No herdr runtime state in the image; chezmoi owns config with
  update checks disabled.** The build never launches a herdr server or
  client; runtime state (sockets, logs, `session.json`, `sessions/`,
  release-note cache) is created at runtime only. Config files under
  `~/.config/herdr/` remain chezmoi's domain (runtime `chezmoi apply`,
  `dot_config/herdr/`); the `[update]` section sets `channel = "stable"`,
  `version_check = false`, and `manifest_check = false` so Herdr does not
  prompt for or apply self-updates. Extends the spec 20 I4 secret-free
  property trivially (herdr ships no credentials).

> NOTE on `git safe.directory`: an earlier draft mandated registering
> `/var/lib/chezmoi-source` via `git config --global --add safe.directory`.
> That invariant was dropped because I2 (`--userns=keep-id`) already keeps
> the host UID inside the container, so git's "dubious ownership" check
> never fires in the supported run mode. See
> [`../references/2026-06-25-chezmoi-in-containers.md`](../references/2026-06-25-chezmoi-in-containers.md)
> for context.


## Delegated rules

| Topic | File |
|---|---|
| Containerfile stage breakdown, layer ordering, acceptance criteria | [`21-container-build-flow.md`](21-container-build-flow.md) |
| Build-time env vars (`HOST_UID`, `HOST_GID`, `JOBS`) | [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md) |
| GPG key runtime lifecycle (import flow, posture, persistence, gpgsign, future automation) | [`23-container-gnupg-management.md`](23-container-gnupg-management.md) |
| Rust packages rule (paru vs cargo-binstall vs cargo-install; layer 3 vs layer 6) | [`24-rust-packages-rule.md`](24-rust-packages-rule.md) |
| Container SSH management (named volume, manual import, persistence, future config/automation) | [`25-container-ssh-management.md`](25-container-ssh-management.md) |
| Host pre-requirements (Bitwarden `bw`, chezmoi) | [`11-pre-required-env-values.md`](11-pre-required-env-values.md) |
| Make target contract | [`03-makefile.md`](03-makefile.md) |
| Chezmoi-in-container gotchas (safe.directory, UID remap) | [`../references/2026-06-25-chezmoi-in-containers.md`](../references/2026-06-25-chezmoi-in-containers.md) |
| Podman conventions used in this repo | [`../references/podman_defact_standard.md`](../references/podman_defact_standard.md) |

## Open questions

- Q1: Resolved. Chezmoi apply runs in two phases — a build-time pre-pass in Stage 2 (`build_mode = true`, scratch destination) and a runtime apply via the entrypoint. See [`13-secret-management.md`](13-secret-management.md) §5 for the contract.
- Q2: Resolved. `paru` / AUR builds run in the dedicated `aur` stage
  (Layer 4) as non-root `${USERNAME}`; root escalation for `pacman`
  happens only via the Layer 1-4 NOPASSWD sudoers (I7 holds). `paru` is
  declared `manager = "custom"` (doc-only) and bootstrapped once via
  `makepkg -si`; all other AUR packages come from the generated
  `layer_4/paru.txt` via `paru -S --noconfirm --needed`. See
  [`21-container-build-flow.md`](21-container-build-flow.md) and
  [`implementations/2026-06-30-paru-aur-layer-design.md`](implementations/2026-06-30-paru-aur-layer-design.md).
