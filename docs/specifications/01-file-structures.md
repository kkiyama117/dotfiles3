# 01 — File structures

> Spec status: **DRAFT (stub)**. Normative spec for the repository directory
> layout: what lives where, and what is hand-edited vs generated. Document
> lifecycle / naming rules live in
> [`00-document-management.md`](00-document-management.md); build-flow layout
> lives in [`21-container-build-flow.md`](21-container-build-flow.md).

## 1. Purpose

This repo is simultaneously:

1. a **chezmoi source directory** (manages `~/` files via `dot_*` entries), and
2. a **Podman build context** (self-contained container image), and
3. the **SoT for documentation** under `docs/`.

The three concerns must not leak into each other's directories. This spec is
the map of which top-level path serves which concern.

## 2. Top-level layout

```
/                       # chezmoi source root (also the repo root)
├── AGENTS.md           # top-level agent protocol; refs specifications/
├── README.md           # repo readme (user entry point)
├── Makefile            # build/up/exec/down + codegen targets (see 03-makefile.md)
├── dot_zshenv.tmpl     # chezmoi-managed ~/.zshenv (template; XDG/PATH/toolchain env)
├── dot_config/         # chezmoi-managed ~/.config/ (XDG configs)
│   ├── git/
│   │   ├── config.tmpl  # chezmoi-managed ~/.config/git/config (identity from .chezmoidata; credential.helper host-only via `runtime`; SSH signing)
│   │   └── ignore       # chezmoi-managed ~/.config/git/ignore (global gitignore; static, generic toptal patterns)
│   └── zsh/
│       ├── dot_zshrc        # chezmoi-managed ~/.config/zsh/.zshrc (sheldon boot; runtime toolchain block)
│       ├── dot_zprofile     # chezmoi-managed ~/.config/zsh/.zprofile (QT/browser env)
│       ├── dot_zfunc/       # chezmoi-managed ~/.config/zsh/.zfunc/ (fpath autoload completions: _chezmoi/_sheldon/_mise)
│       ├── rc/
│       │   ├── private_secrets.zsh.tmpl   # runtime API key env exports (Bitwarden; private_ → mode 0600)
│       │   └── functions/bw_session.zsh  # interactive bw unlock helper
│       └── sheldon_hooks/   # chezmoi-managed ~/.config/zsh/sheldon_hooks/ (sheldon hook scripts, e.g. skim-based zoxide `zi`)
├── dot_local/          # chezmoi-managed ~/.local/ (XDG data/state, rare static configs only)
│   ├── share/cargo/config.toml    # chezmoi-managed ~/.local/share/cargo/config.toml
│   └── share/cargo/binstall.toml  # chezmoi-managed ~/.local/share/cargo/binstall.toml 
├── (Other dotfiles)    # chezmoi-managed ~/(other dotfiles)
├── .chezmoiignore      # chezmoi ignore rules
├── .chezmoi.toml.tmpl  # chezmoi config template (build_mode via BUILD_MODE env; rendered by `chezmoi execute-template --init`)
├── .chezmoidata/       # chezmoi data dir (kept under VCS): git_config.yaml, ssh_keys.yaml, api_secrets.yaml
├── .chezmoiscripts/    # chezmoi run-once scripts dir (kept under VCS)
├── .containerignore    # srcroot build-context exclusions; applied to the `srcroot` named context in Makefile `build` (renamed from `.dockerignore`)
├── .env                # gitignored, per-machine (USERNAME=...); see 22-...md
├── .env.example        # committed example of .env
├── .gitignore
├── .gitmodules         # empty; reserved for future git submodules
│
├── container/          # Podman build context (BUILD_CTX in Makefile)
│   └── bind/           # bind-mounted sources/scripts (full rules: `20-container-rules.md`)
│       ├── layer_1_files/
│       │   ├── makepkg.conf       # Layer 1 makepkg.conf (Stage 1-2 → /etc/makepkg.conf; AUR/pacman compression)
│       │   └── pacman_mirrorlist  # Layer 1 pacman mirrorlist (Stage 1-2)
│       └── layer_5_files/
│           └── entrypoint.sh  # runtime chezmoi-apply entrypoint (Stage 5-4; see 21-...md)
│
├── dependencies/       # package SoT + generated layer manifests
│   ├── packages.toml   # HAND-EDITED SoT; consumed by `make gen-deps`
│   ├── layer_1/
│   │   └── pacman.txt  # GENERATED from packages.toml (do not hand-edit; I8)
│   ├── layer_3/
│   │   └── cargo.txt   # GENERATED (empty initial list; emitted by `make gen-deps`)
│   └── layer_4/
│       └── paru.txt    # GENERATED AUR install list (`manager = "paru"` entries only; I8)
│
├── programs/           # host-side tooling / codegen
│   └── generate_deps/  # implementation of `make gen-deps` (see 08-automations.md)
├── container/tests/    # host-side container/zsh regression tests, excluded from image build context
│
└── docs/               # documentation tree (placement: see [here](00-document-management.md))
│   └── ... delegate it to `00-document-management.md`
```

## 3. Invariants

- **I-FS1: `container/` is the only Podman build context.** Nothing outside
  `container/` is sent to `podman build` except via build-args / secrets. The
  Makefile sets `BUILD_CTX := $(CURDIR)/container`.
- **I-FS2: chezmoi source entries (`dot_*`, `.chezmoiignore`) live only at the
  repo root**, never inside `container/`, `dependencies/`, or `docs/`.
- **I-FS3: `dependencies/packages.toml` is the only hand-edited package
  manifest.** Everything under `dependencies/layer_*/` is generated
  (`make gen-deps`); hand-editing generated files violates I8 in
  [`20-container-rules.md`](20-container-rules.md).
- **I-FS4: secrets never live in the repo tree.** `.env` carries only
  non-secret machine config (`USERNAME`); secrets are sourced at runtime
  from Bitwarden via `bw` (`BW_SESSION` in the shell env) — never in the
  repo or image (I4 in [`20-container-rules.md`](20-container-rules.md),
  [`13-secret-management.md`](13-secret-management.md), and
  [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md)).
- **I-FS5: `docs/` is placement-governed by
  [`00-document-management.md`](00-document-management.md).** No ad-hoc files
  outside the documented subdirectories.
- **I-FS6: `dot_*` source entries may include static XDG data configs when the
  file is non-secret configuration rather than volume-owned tool data.** For
  example, `dot_local/share/cargo/config.toml` is managed because it is a
  static linker config, while `$CARGO_HOME/bin`, `registry/`, and `git/` are
  volume-owned and ignored via `.chezmoiignore`.

## 4. Open questions

- Q1: where do chezmoi-managed program config files that are large or
  third-party (e.g. sheldon plugins, nix flakes) live — inline `dot_*` at the
  repo root, or a dedicated subdir sourced via chezmoi `externals`? Currently
  only `dot_zshenv.tmpl` exists at the root (plus `dot_config/zsh/dot_zshrc.tmpl`
  under `dot_config/`).
- Q2: should `programs/` (host codegen) and `container/programs/` (per-program
  container install scripts) be merged or kept separate? They serve different
  run contexts today.
