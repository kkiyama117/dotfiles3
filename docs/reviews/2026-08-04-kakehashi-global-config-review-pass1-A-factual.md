# kakehashi-global-config — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-08-04
**Reviewer:** Reviewer-A
**Subject:** [Global kakehashi configuration design](../specifications/implementations/2026-08-04-kakehashi-global-config-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Request changes.** The config loads and the pyright bridge runs, and the
documented kakehashi merge/Neovim `keep` behavior is correct. However, the
claimed nvim-lspconfig parity, eight-server host readiness, and spec 24
justification are not factually satisfied.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | HIGH | open | Design §5.1, lines 125–141; `dot_config/kakehashi/kakehashi.toml:70-128` | Four `workspaceMarkers` entries do not mirror the cited nvim-lspconfig root behavior. |
| F2 | HIGH | open | Design §1 S1/S2/S4 and §5.4, lines 24–61, 174–185 | The eight-server “installed” inventory is not currently resolvable, and the verification plan exercises only pyright. |
| F3 | HIGH | open | Design §2 alternative C, lines 70–75 | The official `extra` package does not satisfy spec 24 §2's “AUR prebuilt” criterion; spec 24 instead puts it out of scope. |
| F4 | MEDIUM | open | Design §7, lines 198–203 | The claim that rustup creates proxies only for installed components contradicts the observed stale proxy with no installed rust-analyzer component. |
| F5 | MEDIUM | open | Design §5.1, line 134; `dot_config/kakehashi/kakehashi.toml:119-128` | The clangd language list omits two cited nvim-lspconfig filetypes without documenting why. |
| F6 | LOW | open | Design S2/§5.3, lines 45–47 and 158–164 | The repository mise file already contains the listed additions and is unchanged from `HEAD`; they are not currently “uncommitted” source changes. |

### F1 details

The upstream kakehashi reference says `workspaceMarkers` entries are tried in
list order, while a nested array is one equal-priority group
(`/tmp/kakehashi/docs/README.md:474-483`). The proposed conversions change the
cited Neovim behavior:

- `tombi.lua:10-12` has one flat `root_markers` list containing
  `tombi.toml`, `pyproject.toml`, and `.git` in priority order; the proposal
  changes the first two into an equal-priority nearest-match group.
- `pyright.lua:37-47` and `clangd.lua:66-76` likewise use flat lists, but the
  proposal changes every non-git marker from ordered priority into one
  equal-priority nearest-match group. `.git` remains the final fallback in
  both representations.
- `rust_analyzer.lua:88-132` is not equivalent to
  `["Cargo.toml", ".git"]`: it also recognizes `rust-project.json` and resolves
  a Cargo manifest through `cargo metadata` to the Cargo workspace root.

The denols, vtsls, and emmylua groupings do preserve the marker-group shapes
shown in `denols.lua:107-125`, `vtsls.lua:82-105`, and
`emmylua_ls.lua:54-74`; gopls's ordered list accurately represents the
`go.work` → `go.mod` → `.git` chain in `gopls.lua:86-113`.

Suggested fix: either reproduce the cited static marker semantics exactly
(keep flat nvim-lspconfig lists flat), or explicitly document each intentional
divergence. For rust-analyzer, state that
`workspaceMarkers` is only an approximation and add `rust-project.json` if that
project form must work; kakehashi markers alone cannot reproduce the
`cargo metadata` workspace-root calculation.

Verification: construct nested directories with a nearer `.git` and a farther
language-specific marker, then compare the root selected by Neovim and
kakehashi for each server.

### F2 details

With `~/.local/share/mise/shims` prepended to `PATH`, command lookup found
deno, gopls, pyright-langserver, tombi, vtsls, and clangd, but not
`lua-language-server`. `mise which lua-language-server` reported that it is not
a mise bin; `mise ls --current` instead showed
`cargo:emmylua_ls 0.24.0 (missing)` in the applied host config. rust-analyzer
resolved only to the broken rustup proxy and exited with “Unknown binary
'rust-analyzer'”.

The required CLI diagnostic still passed because the sample invokes pyright
only:

```text
$ printf '# Check\n\n```python\nx: int = 1\n```\n' | PATH="$HOME/.local/share/mise/shims:$PATH" kakehashi --config-file dot_config/kakehashi/kakehashi.toml diagnose --stdin-filename review-python-fence.md
0 diagnostics in 1 file
```

That proves deserialization and the pyright path, not eight-server readiness.
The design includes a host install step for rust-analyzer but no host
`mise install` plus per-command resolution check after applying the changed
mise config.

Suggested fix: add `chezmoi apply`, `mise install`, and a loop that resolves
and smoke-tests all eight `cmd[0]` values. Keep the Python-fence diagnostic as
the end-to-end bridge test. Define the proposed config-sync test as a
provisioning mapping (mise-managed union system-managed), because exact key
equality among the three files is neither true nor intended.

Verification: after installation, run `command -v` and a version/help command
for every declared executable, then rerun the diagnostic.

### F3 details

Spec 24 §1 says packages that do not depend on the Rust toolchain use ordinary
pacman/paru selection and are out of scope
(`docs/specifications/24-rust-packages-rule.md:10-15`). Its §2 paru branch is
specifically “AUR prebuilt” and requires a stable prebuilt AUR binary
(`docs/specifications/24-rust-packages-rule.md:17-29`).

`pacman -Si rust-analyzer` confirms repository `extra`, version `20260608-1`,
dependencies `gcc-libs rust-src`, and no `rust`/`rustup` dependency. This
supports installing the package through paru, but not the design's claim that
an official-repository package satisfies spec 24's AUR criterion.

Suggested fix: justify `manager = "paru", layer = 4` under the repository's
ordinary system-package/layer convention and state that spec 24 is
inapplicable because this package does not pull a Rust toolchain. If spec 24
is intended to govern official repository prebuilt packages too, revise that
spec first.

Verification: retain the `pacman -Si rust-analyzer` metadata in the result log
and cite the actual non-Rust package rule that authorizes Layer 4.

### F4 details

Observed commands:

```text
$ readlink ~/.local/share/cargo/bin/rust-analyzer
rustup
$ rustup show profile
minimal
$ rustup component list --installed
cargo-x86_64-unknown-linux-gnu
rust-std-x86_64-unknown-linux-gnu
rustc-x86_64-unknown-linux-gnu
```

Thus the important premise is verified: the path is a rustup symlink, the
rust-analyzer component is absent, and invoking the proxy fails. But that same
state disproves “rustup recreates proxies only for installed components.”
Current state also cannot prove the historical assertion “component never
installed.”

Suggested fix: describe rustup's proxy as component-independent host state,
remove the unprovable history, and make the acceptance check simply ensure the
proxy no longer shadows `/usr/bin/rust-analyzer`. The rollback text should
distinguish restoring the old broken proxy from installing the rustup
component, which changes the selected installation strategy.

Verification: after the planned removal/install, check `command -v
rust-analyzer`, `readlink -f "$(command -v rust-analyzer)"`, and
`rust-analyzer --version`.

### F5 details

The proposed clangd languages are `c`, `cpp`, `objc`, `objcpp`, and `cuda`.
The cited `clangd.lua:66-68` additionally lists `c.doxygen` and `cpp.doxygen`.
Since clangd is intentionally outside the Neovim `bridged_servers` contract,
“languages mirror the nvim bridge contract” does not define its source.

Suggested fix: either include the two filetypes/language identifiers or state
that they are intentionally excluded and identify the authoritative
kakehashi language IDs for clangd.

Verification: inspect `kakehashi language list` and test a Doxygen buffer if
those identifiers are supported.

### F6 details

`git status --short` listed only the issue, prompt, design, and
`dot_config/kakehashi/` as untracked. It reported no change to
`dot_config/mise/config.toml`; that tracked file already contains the gopls,
pyright, vtsls, LuaLS, tombi, and StyLua entries at lines 70–77.

Suggested fix: describe the mise entries as already present in repository
state, unless another pending patch is expected and can be cited.

Verification: `git diff HEAD -- dot_config/mise/config.toml` should show the
intended delta, or the design should remove that claimed delta.

## Verified premises

- P1: The four kakehashi layers and later-source/deep-per-key merge are
  documented in `/tmp/kakehashi/docs/architecture-decisions/configuration-merging-strategy.md:60-81,142-230`.
- P2: kakehashi's marker semantics are flat list = ordered priority and nested
  list = equal-priority group (`/tmp/kakehashi/docs/README.md:474-483`).
- P3: Neovim calls `bridge.inherit(..., 'keep')`
  (`~/.config/nvim/lua/hooks/kakehashi.nvim.dpp:49-54`), and
  `vim.tbl_extend` receives the effective/global server entry first
  (`~/.config/nvim/lua/vimrc/kakehashi_bridge.lua:144-165`). Therefore existing
  keys win and global `emmylua_ls.cmd = ["lua-language-server"]` survives.
- P4: The global `languages` host bridge, Markdown injection priorities, and
  rmd/quarto bases match the non-dpp portions of
  `~/.config/nvim/lua/vimrc/kakehashi_config.lua:20-31,93-174`; dpp is
  explicitly Neovim-local.
- P5: `has_configs` only affects validation and the generated spec-02
  `configs` cell in `programs/generate_deps/main.py:87-108,139-169`; it does
  not alter install-list generation. The exact-dictionary expectation in
  `programs/generate_deps/tests/test_kakehashi_container_install.py:13-26`
  must change from `False` to `True`. No generator implementation change is
  required for that flip.
- P6: `pacman -Si rust-analyzer` confirms the design's quoted version
  `20260608-1` and dependencies `gcc-libs` plus `rust-src`.
- P7: The stale rust-analyzer proxy and missing component are real:
  `readlink -f ~/.local/share/cargo/bin/rust-analyzer` resolves to rustup,
  the installed component list omits rust-analyzer, and invocation fails.
- P8: The explicit config loads and its Python-fence pyright diagnostic exits
  0 with “0 diagnostics in 1 file.”
- P9: No files were staged during this review (`git diff --cached --name-only`
  produced no output).

## Open questions

- Q1: Should tombi, pyright, and clangd retain the nvim-lspconfig marker
  priority order, or is the proposed equal-priority grouping of their
  non-git markers an intentional divergence?
- Q2: What is the intended approximation for rust-analyzer projects using
  `rust-project.json` or Cargo workspaces whose workspace root differs from
  the nearest `Cargo.toml`?
- Q3: Should clangd support `c.doxygen` and `cpp.doxygen`, and if not, which
  kakehashi language-ID constraint justifies excluding them?
- Q4: Will the implementation explicitly run `mise install` on the host and
  verify all eight commands, rather than treating the pyright-only diagnostic
  as inventory validation?
