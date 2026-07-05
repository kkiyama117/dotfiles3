# Cargo config container integration — Design

**Status:** DRAFT
**Date opened:** 2026-07-05
**Issue:** User request: add `dot_local/share/cargo/config.toml` to the container and copy it for the Rust dependency build/install layer
**Author:** kiyama

## §1 Context & success criteria

`dot_local/share/cargo/config.toml` already exists in the chezmoi source tree.
Because `dot_zshenv.tmpl` sets `CARGO_HOME=$XDG_DATA_HOME/cargo`, the file's
target path is `$CARGO_HOME/config.toml`, normally
`~/.local/share/cargo/config.toml`.

Today `.chezmoiignore` ignores `.local/share/cargo` as a volume-owned tree.
That protects `bin`, `registry`, and `git`, but it also prevents this one
non-secret Cargo config file from being rendered by the Stage 2 build-prepass
or maintained by runtime `chezmoi apply`.

- **S1:** Runtime `chezmoi apply` manages only
  `~/.local/share/cargo/config.toml` under `$CARGO_HOME`; cargo binaries,
  registry data, and git cache remain volume-owned and unmanaged.
- **S2:** The container build copies the rendered
  `/tmp/build-home/.local/share/cargo/config.toml` to
  `$CARGO_HOME/config.toml` before any Rust, cargo, or AUR step can compile
  Rust code.
- **S3:** Layer 1 generated pacman dependencies include the linker tools used
  by the Linux Cargo config: `clang`, `compiler-rt`, and `mold`.
- **S4:** The container docs describe the new Cargo config invariant, the
  Stage 3 copy step, and the managed `dot_local/share/cargo/` path.
- **S5:** Verification covers dependency generation, dependency generator
  tests, build through the AUR stage, and runtime presence of
  `$CARGO_HOME/config.toml`.

## §2 Alternatives considered

- **A1 — Manage runtime + build via chezmoi render path (chosen).** Carve out
  only `.local/share/cargo/config.toml` from `.chezmoiignore`, render it during
  the existing build-prepass, copy the rendered file into `$CARGO_HOME` early in
  the toolchain stage, and let runtime `chezmoi apply` maintain the same file in
  the cargo volume. This keeps build and runtime behavior consistent.
- **A2 — Build-only direct source copy (rejected).** Copy
  `dot_local/share/cargo/config.toml` directly from the source tree into the
  image. This is smaller, but it bypasses chezmoi, leaves runtime cargo volumes
  unmanaged, and creates two different paths for the same config.
- **A3 — Convert the config to a template or platform split (rejected for now).**
  The current file is static and contains no secrets. Cargo ignores irrelevant
  target sections, so Linux container builds do not need a Linux-only template
  yet.

## §3 Architecture / invariants

- **I1:** `$CARGO_HOME` remains a named-volume-backed toolchain directory.
  Chezmoi may manage only the static config file under that tree.
- **I2:** `.chezmoiignore` must use the same pattern as the SSH config carve-out:
  ignore the volume contents, then re-include the one managed config file.
- **I3:** The container build must consume the rendered file from
  `/tmp/build-home`, not the raw chezmoi source path. This preserves the
  build-prepass as the single render path if the Cargo config later becomes a
  template.
- **I4:** The Cargo config copy must happen before Stage 4 `paru` bootstrap and
  AUR installation, because those steps can compile Rust code and therefore may
  read `$CARGO_HOME/config.toml`.
- **I5:** No secret material is introduced. The Cargo config contains linker
  choices only.

## §4 Scope / staging breakdown

This change is one small container integration with three surfaces:

1. **Chezmoi surface:** allow `dot_local/share/cargo/config.toml` to render and
   apply while preserving the rest of `$CARGO_HOME` as volume-owned data.
2. **Container build surface:** copy the rendered Cargo config into the live
   build user's `$CARGO_HOME` before Rust dependency work.
3. **Documentation surface:** update specs that define file layout, container
   runtime/build invariants, and Stage 3 ordering.

The change does not alter the contents of `dot_local/share/cargo/config.toml`
and does not introduce host-specific or secret-backed templating.

## §5 Implementation detail

### §5.1 Chezmoi ignore carve-out

Update `.chezmoiignore` from an all-Cargo-tree ignore to a file-specific
carve-out:

```gitignore
# Cargo: chezmoi manages ONLY ~/.local/share/cargo/config.toml. Everything
# else under $CARGO_HOME (bin, registry, git cache) is volume-owned.
.local/share/cargo/*
!.local/share/cargo/config.toml
```

Keep `.local/share/rustup`, `.local/share/mise`, and keyring ignores unchanged.

### §5.2 Containerfile copy step

Add an early Stage 3 toolchain sub-layer before rustup and cargo work. The step
must source `/tmp/build-home/.zshenv`, validate the rendered config, create
`$CARGO_HOME`, and copy the config:

```sh
source /tmp/build-home/.zshenv
cargo_config=/tmp/build-home/.local/share/cargo/config.toml
if [ ! -s "$cargo_config" ]; then
  echo "toolchain: missing rendered cargo config: $cargo_config" >&2
  exit 1
fi
install -d "$CARGO_HOME"
cp "$cargo_config" "$CARGO_HOME/config.toml"
```

The sub-layer comments and `docs/specifications/21-container-build-flow.md`
must be updated together so Stage 3 ordering remains clear.

### §5.3 Dependency generation

`dependencies/packages.toml` already declares the Linux linker dependencies.
After implementation, run `make gen-deps` so these generated files reflect the
source of truth:

- `dependencies/layer_1/pacman.txt`
- `docs/specifications/02-installed-programs.md`

Do not hand-edit generated dependency outputs.

### §5.4 Spec updates

Update these hand-written specs:

- `docs/specifications/01-file-structures.md`: document
  `dot_local/share/cargo/config.toml` as a managed chezmoi source under
  `~/.local/share/cargo/`.
- `docs/specifications/20-container-rules.md`: add a Cargo config invariant
  parallel to the SSH config carve-out.
- `docs/specifications/21-container-build-flow.md`: add the new Stage 3
  sub-layer and acceptance criteria that `$CARGO_HOME/config.toml` exists
  before Rust/AUR work.

### §5.5 Rollout note

Existing `dotfiles_cargo` volumes will not be repopulated from the rebuilt
image. After the `.chezmoiignore` carve-out, runtime `chezmoi apply` should
create or update `config.toml` in the mounted volume. Tests that rely on
image-seeded cargo binaries still need the existing volume reset flow
(`make clean` or removing `dotfiles_cargo`) when validating first-run behavior.

## §6 Verification

Run these checks after implementation:

1. `make gen-deps`
   - Expected: `dependencies/layer_1/pacman.txt` includes `clang`,
     `compiler-rt`, and `mold`.
2. `make test-deps`
   - Expected: dependency generator tests pass.
3. `make build` or the equivalent `podman build --target aur` command from the
   `Makefile` build context.
   - Expected: build reaches the AUR stage with `$CARGO_HOME/config.toml`
     present before `paru` bootstrap.
4. `make up`, then:

   ```sh
   podman exec <container> zsh -ic 'test -s "$CARGO_HOME/config.toml" && cargo -V'
   ```

   Expected: command exits successfully and prints the Cargo version.

5. Optionally compare the runtime file with the source:

   ```sh
   podman exec <container> zsh -ic 'cat "$CARGO_HOME/config.toml"' > /tmp/container-cargo-config.toml
   diff -u dot_local/share/cargo/config.toml /tmp/container-cargo-config.toml
   rm /tmp/container-cargo-config.toml
   ```

   Expected: `diff` exits successfully because the managed runtime file
   matches the static chezmoi source file.

## §7 Open questions

- **Q1:** No open product or architecture questions remain. The selected scope
  is runtime plus build integration through the chezmoi render path.
