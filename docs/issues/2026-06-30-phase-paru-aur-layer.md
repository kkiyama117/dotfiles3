# Phase complete — paru (AUR) install layer

**Date:** 2026-06-30
**Phase:** paru-aur-layer (implementation)
**Plan:** [`../plans/2026-06-30-paru-aur-layer-impl.md`](../plans/2026-06-30-paru-aur-layer-impl.md)
**Issue:** [`2026-06-30-paru-aur-layer.md`](2026-06-30-paru-aur-layer.md)
**Design:** [`../specifications/implementations/2026-06-30-paru-aur-layer-design.md`](../specifications/implementations/2026-06-30-paru-aur-layer-design.md)

## Summary

Added a dedicated `aur` stage (Layer 4) to `container/Containerfile`
between `toolchain` and `runtime`; `runtime` was renumbered Layer 4 →
Layer 5 (`FROM aur AS runtime`) and `container/bind/layer_4_files/` →
`layer_5_files/`. The `aur` stage bootstraps `paru` from the AUR via
`makepkg -si` (non-root `${USERNAME}`) and installs the Layer 4 AUR
package set from the generated `dependencies/layer_4/paru.txt`. A new
`custom` doc-only manager was added to the generator so `paru` can be
declared in `dependencies/packages.toml` (satisfying I5) without being
a `paru -S` target. First concrete AUR package: `neovim-git`.

## Acceptance evidence

| Criterion (issue / spec 21) | Verification | Result |
|---|---|---|
| 1. `aur` stage exists between `toolchain` and `runtime`; in spec 21 table | spec 21 stage table updated (commits `07caea8`, `7395c7b`) | PASS |
| 2. `paru` bootstrapped via `makepkg` as non-root; sudoers-only escalation | `id -u` in `aur` image = 1000; `makepkg`/`paru` ran as `${USERNAME}` | PASS |
| 3. AUR pkgs from generated `layer_4/paru.txt` via `paru -S --noconfirm --needed` | `paru.txt` = `{ neovim-git }` (generated) | PASS |
| 4. `layer_4/paru.txt` generator-owned, emitted even if empty | `(4, "paru")` in `EXPECTED_EMPTY_FILES`; pytest `test_paru_layer.py` (15 passed) | PASS |
| 5. `~/.cache/paru` + `/var/cache/pacman/pkg` (+ cargo) backed by `--mount=type=cache` | both `aur` RUNs carry the cache mounts (I-AUR3) | PASS |
| 6. final image has `paru` on PATH | `paru v2.1.0 - libalpm v16.0.1` | PASS |
| 7. spec 21 Q1 + spec 20 Q2 resolved | both read "Resolved" with design pointer (`07caea8`, `96fb4fd`) | PASS |
| 8. runtime renumbered Layer 5; `layer_5_files/`; cross-refs updated | spec 01 tree, `container/.gitignore`, Containerfile COPY all updated | PASS |

### Smoke-gate command output (representative)

```
$ podman run --rm --entrypoint bash localhost/dotfiles-manjaro:latest -c \
    "test ! -d /tmp/chezmoi-src && test ! -d /tmp/build-home && test ! -d /tmp/paru-build \
     && test ! -d /home/kiyama/.config/chezmoi && paru --version && nvim --version | head -1 && echo OK_ALL"
paru v2.1.0 - libalpm v16.0.1
NVIM v0.13.0-dev-868+gaa3823cca3
OK_ALL

$ podman exec dotfiles-manjaro zsh -ic 'echo $CARGO_HOME'
/home/kiyama/.local/share/cargo          # XDG-compliant (existing criterion #6 still holds)

$ podman exec dotfiles-manjaro zsh -lc 'rustc --version'   # after down/up
rustc 1.96.0 (ac68faa20 2026-05-25)       # named-volume persistence (criterion #8) holds
```

### Generator / idempotency

```
$ make gen-deps   # after all SoT changes
generate_deps: layers=[0, 1, 4] txt_written=0 doc_updated=False   # idempotent

$ python3 -m pytest -q (programs/generate_deps)
15 passed
```

## Deviations from the original plan

Recorded in the plan's "Deviation log" section. Key points:

1. Added a `custom` doc-only manager (generator + `DOC_ONLY_MANAGERS`).
   `paru` is `manager = "custom"` so it is in the spec 02 AUTO-GEN block
   (I5) but NOT in `paru.txt`. Reason: re-submitting an already-
   bootstrapped `paru` as a `paru -S` target breaks paru's resolver.
2. Both `aur` RUNs `source /tmp/build-home/.zshenv` and mount the cargo
   registry/git caches, because the toolchain stage re-roots
   `/home/${USERNAME}` to root and `paru` (Rust) needs a writable
   `$CARGO_HOME` (the XDG `~/.local/share/cargo`, not the default
   `~/.cargo` the user cannot create).
3. The intermediate "filter already-installed" hack was superseded by #1;
   the bulk install is the simple `paru -S --noconfirm --needed $pkgs`.
4. `neovim-git` (not stable `neovim`, which is a pacman-repo package)
   was confirmed by the user as the first concrete AUR package.

## Commit trail

```
c25b491 docs(spec-01/02): add 'custom' manager rules; tree: layer_4/paru.txt + layer_5_files
96fb4fd docs(spec-20): add I-AUR1..I-AUR4 invariants, resolve Q2 (paru/AUR policy)
07caea8 docs(spec-21): add aur stage (Layer 4), renumber runtime to Layer 5, resolve Q1
7395c7b feat(container): add aur stage (Layer 4) with paru bootstrap + neovim-git; renumber runtime to Layer 5
30bf95d refactor(deps): declare paru as manager=custom (doc-only); paru.txt now holds neovim-git only
a8e672c feat(generate_deps): add 'custom' doc-only manager (declared in packages.toml, no install list)
7d71610 refactor(container): rename layer_4_files bind dir to layer_5_files
1c596ce feat(deps): seed paru + neovim-git (layer 4) in packages.toml; regenerate layer_4/paru.txt
bb23450 feat(generate_deps): always emit layer_4/paru.txt (EXPECTED_EMPTY_FILES)
dfda56f docs: raise paru/AUR layer issue, design, and implementation plan
```

## Follow-ups (not in scope)

- Additional AUR packages: add `[[tool]]` with `manager = "paru"`,
  `layer = 4` to `packages.toml`, then `make gen-deps`.
- AUR makedepend bloat: `makepkg -si` keeps build-only deps (e.g. the
  `rust` pacman package pulled for paru's build) in the image. A future
  `makepkg -sri` / `paru --removemake` pass could trim them (design §10
  Q1).
- GPG-signed AUR sources: deferred until the first such package lands
  (design §10 Q3).