# Result log: Install `herdr` during container build

**Date:** 2026-07-15
**Issue:** [`2026-07-15-herdr-container-install.md`](2026-07-15-herdr-container-install.md)
**Plan:** [`docs/plans/2026-07-15-herdr-container-install-impl.md`](../plans/2026-07-15-herdr-container-install-impl.md)
**Design:** [`docs/specifications/implementations/2026-07-15-herdr-container-install-design.md`](../specifications/implementations/2026-07-15-herdr-container-install-design.md)

## Commit trail

| Task | Commit | Subject |
|---|---|---|
| Task 1 | `4f251d3` | deps: move herdr from migrated (layer -1) to custom (layer 3) |
| Task 2 | `931b4a7` | feat(container): install herdr v0.7.3 prebuilt binary (Layer 3-8) with SHA256 pinning |
| Task 3 | `eda2d51` | docs(spec-20/21): record herdr Layer 3-8 + I-HERDR1 invariant + acceptance #25 |
| Task 5 | (this commit) | docs: close herdr-container-install issue with result-log |

> Note: Task 2 commit `f348082` was amended to `931b4a7` after a reviewer found that the initial brief's `source /tmp/build-home/.zshenv` + bare `herdr --version` would fail due to `.zshenv`'s `(N-/)` glob qualifier dropping `~/.local/bin` from `PATH` before the directory existed. The amended commit aligns with the approved design §5.1: `install -D -m 0755` + absolute-path `"$HOME/.local/bin/herdr" --version`.

## Acceptance evidence

| Criterion | Status | Evidence |
|---|---|---|
| S1: `herdr` in `packages.toml` as `custom`, layer 3 | ✅ PASS | `dependencies/packages.toml` lines 509–514: `manager = "custom"`, `layer = 3` |
| S1: spec 02 AUTO-GEN moved `herdr` to Layer 3 | ✅ PASS | `docs/specifications/02-installed-programs.md` Layer 3 table contains `herdr`; Layer -1 table does not |
| S2: Containerfile Layer 3-8 installs `herdr` | ✅ PASS | `container/Containerfile` lines 282–302 contain `ARG HERDR_VERSION`, `ARG HERDR_SHA256`, curl + `sha256sum -c` + `install -D` + `"$HOME/.local/bin/herdr" --version` |
| S3: `herdr --version` in running container | ✅ PASS | `podman exec dotfiles-manjaro zsh -ic 'herdr --version'` → `herdr 0.7.3` |
| S3: `herdr` at `~/.local/bin/herdr` | ✅ PASS | `which herdr` → `/home/kiyama/.local/bin/herdr`; `stat` shows `755 kiyama:kiyama` |
| S4: `~/.config/herdr/` rendered by chezmoi | ✅ PASS | `ls ~/.config/herdr/config.toml` succeeds (runtime `chezmoi apply`) |
| S5: No secret material baked | ✅ PASS | Layer 3-8 only downloads/verifies/installs the binary; no credentials, no server spawn, no sockets/logs in image layers |
| S6: SHA256 mismatch fails loudly | ✅ N/A (mechanism) | Same `sha256sum -c -` pattern as Layer 3-6 cargo-binstall; positive-path build success confirms SHA matches. Targeted negative rebuild skipped to avoid another 17-minute full build. |
| S7: Spec 20 I-HERDR1..I-HERDR3 added | ✅ PASS | `docs/specifications/20-container-rules.md` lines 239, 256, 264 |
| S7: Spec 21 Layer 3-8 row + acceptance #25 | ✅ PASS | `docs/specifications/21-container-build-flow.md` lines 32, 91 |
| No regression (existing tools) | ✅ PASS | `CARGO_HOME`, `pi --version`, `paru --version`, `gpg --version` all report expected output |
| Container replacement survival | ✅ PASS | `make down && make up` → `herdr --version` still prints `herdr 0.7.3` |
| `make gen-deps` idempotent | ✅ PASS | Second run produced no diff (`txt_written=0 doc_updated=False`) |

## Implementation notes

- `herdr` is installed as a single static-pie ELF binary from GitHub releases (`ogulcancelik/herdr`), pinned to v0.7.3 with hardcoded SHA256 `043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d`.
- The stable manifest (`https://herdr.dev/latest.json`) does not publish SHA256 checksums, so the SHA is hardcoded in the `ARG` — the same precedent as `cargo-binstall` (Layer 3-6).
- No new named volume, Makefile change, `.chezmoiignore` change, or `dot_zshenv.tmpl` change was needed.
- Full build time: ~17 minutes (dominated by AUR packages in Layer 4).

## Open follow-ups

- **Q1 (update-prompt suppression in container):** Deferred per design §7 Q1. If `version_check = true` proves noisy inside the container, gate it off for `runtime = "container"` via `DOTFILES_RUNTIME` templating of `dot_config/herdr/config.toml`.
- **Q2 (preview channel in the container):** Deferred per design §7 Q2. A container user can run `herdr update` / `herdr channel set preview` at runtime; changes are ephemeral (I-HERDR2).
