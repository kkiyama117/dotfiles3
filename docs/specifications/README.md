# Specifications

Normative specs for `dotfiles3`. Conventions: see [`00-document-management.md`](00-document-management.md).
TODO: refactor and classify documents

## Index

### 0x — Repository-wide Rules

| Spec | Status | Summary |
|---|---|---|
| [`00-document-management.md`](00-document-management.md) | active | Document placement, naming, lifecycle. SoT for all docs. |
| [`01-file-structures.md`](01-file-structures.md) | DRAFT (stub) | Repository directory layout and what lives where. |
| [`02-installed-programs.md`](02-installed-programs.md) | active | Normative contract for tool inventory. |
| [`03-makefile.md`](03-makefile.md) | DRAFT | Target naming + dependency contract for `Makefile`. |
| [`08-automations.md`](08-automations.md) | DRAFT | Make targets and generators (`make gen-deps`, chezmoi deploy). |
| [`09-review.md`](09-review.md) | active | Rules for doing and receiving the review. |

### 1x — Common definition of the dotfiles 

| Spec | Status | Summary |
|---|---|---|
| [`11-pre-required-env-values.md`](11-pre-required-env-values.md) | DRAFT | Secrets, Bitwarden items, env vars required before apply/build. |
| [`12-quickstart.md`](12-quickstart.md) | DRAFT | User-facing quickstart (local + container). |
| [`13-secret-management.md`](13-secret-management.md) | DRAFT | Secret-management design: two-tier, `bw` auth, runtime apply. |

### 2x — Container

| Spec | Status | Summary |
|---|---|---|
| [`20-container-rules.md`](20-container-rules.md) | DRAFT (stub) | Rootless / userns / bind-mount invariants. |
| [`21-container-build-flow.md`](21-container-build-flow.md) | active | Containerfile layer breakdown and stage ordering. |
| [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md) | DRAFT | Build-time envs (`HOST_UID`, `HOST_GID`, `JOBS`). |
| [`23-container-gnupg-management.md`](23-container-gnupg-management.md) | active | GPG key lifecycle in the container's `dotfiles_gnupg` volume (baseline + manual flow; §7 prospective). |
| [`24-rust-packages-rule.md`](24-rust-packages-rule.md) | active | Install-manager selection for Rust-toolchain packages; build-time vs runtime-manual boundary. |
| [`25-container-ssh-management.md`](25-container-ssh-management.md) | active | SSH key lifecycle in the container's `dotfiles_ssh` volume (baseline + manual flow; §4+ deferred). |

## Status legend

- **active** — used in steady state
- **DRAFT** — has structure but content is incomplete; safe to read but cite with care
- **DRAFT (stub)** — section headers only; content TBD
- **empty (stub)** — placeholder file; nothing useful yet
