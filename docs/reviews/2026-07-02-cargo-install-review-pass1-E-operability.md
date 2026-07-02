# cargo-install — Review pass-1 (Letter E: operability / runtime)

**Date:** 2026-07-02
**Reviewer:** pi subagent (operability reviewer)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../../specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

Approve with conditions. The build is **feasible**: both open questions
Q1 (cargo-binstall release asset) and Q2 (non-interactive binstall flag)
are concretely resolvable and **verified** against upstream sources, and
`topgrade` is in fact cargo-binstall-compatible (so Layer 3-6 will not
fail the build — no CRITICAL). However, the design's **I6 "cache reuse"
invariant is factually wrong** (cargo-binstall has no persistent download
cache at `~/.cache/cargo-binstall`), the named-volume migration for the
new `$CARGO_HOME/bin` binaries is not addressed (S1/S2 acceptance can
fail on an existing volume), the generator test target is still open
(Q3), and a couple of cache mounts / flags are dead weight. These are
MEDIUM/LOW and resolvable in the next revise without re-architecting.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | MEDIUM | open | design §3 I6, §5.2 Layer 3-5/3-6 | `~/.cache/cargo-binstall` cache mount caches nothing; binstall uses a per-run tempdir inside `$CARGO_HOME`, not `~/.cache/cargo-binstall`. I6 is factually incorrect. |
| F2 | MEDIUM | open | design §1 S1/S2/S6, §5.5 (rollout) | Named-volume migration not addressed: an existing `dotfiles_cargo` volume is NOT re-populated from the image on `make up`, so `cargo-binstall` / `topgrade` (new in `$CARGO_HOME/bin`) will be absent at runtime unless `make clean` runs first. |
| F3 | MEDIUM | open | design §6 (Q3), Makefile, `03-makefile.md` | No `test-deps`/`test` target exists in the Makefile; spec 03 §Contract requires new targets to have an `08-automations.md` entry. The test invocation must be pinned. |
| F4 | LOW | open | design §5.2 Layer 3-6 | `cargo binstall -y --no-confirm` is redundant: `-y` and `--no-confirm` are the same clap flag. Q2 resolves to `-y` alone. |
| F5 | LOW | open | design §5.2 Layer 3-6 | `--mount=type=cache,target=.../.local/share/cargo/registry` is ineffective for `cargo binstall` (binstall fetches crate metadata via the crates.io HTTP API, not the registry/git index). Dead weight. |
| F6 | LOW | open | design §4 (rollback) | Generator never deletes stale layer dirs; after a revert + `make gen-deps`, `dependencies/layer_6/cargo.txt` lingers on disk (not in `EXPECTED_EMPTY_FILES`). Rollback of tracked files is still clean; the stale artifact needs `git clean -fdx`. |

### F1 details
> **Quote (design §3 I6):** "the Layer 3-6 `RUN` carries a BuildKit
> `--mount=type=cache` on `~/.cache/cargo-binstall` (binstall's download
> cache) so rebuilds reuse downloaded prebuilt archives …"

**Evidence (verified against upstream source):** cargo-binstall creates
its per-run download/extract directory via
`tempfile::Builder::new().prefix("cargo-binstall").tempdir_in(&cargo_root)`
(`crates/bin/src/initialise.rs:138`), where `cargo_root` defaults to
`$CARGO_HOME` (`~/.local/share/cargo`). This is a RAII `TempDir` cleaned
up after each run. There is **no persistent download cache at
`~/.cache/cargo-binstall`** — that path is never written to by
cargo-binstall. Confirmed by inspecting `crates/bin/src/initialise.rs`,
`crates/binstalk/src/ops.rs` (`Options.temp_dir: PathBuf`), and
`crates/binstalk-downloader/src/download.rs` (`use tempfile::tempdir`).
`cargo-binstall --help` exposes no `--cache-dir` / `--temp-dir` flag
either (only `--no-cleanup` to retain the temp dir for debugging).

**Impact:** the `--mount=type=cache,target=/home/${USERNAME}/.cache/cargo-binstall`
mounts on Layers 3-5 and 3-6 cache an empty directory that nothing
writes to. Zero download reuse occurs across rebuilds; the I6 invariant
is false. The build still succeeds (the mount is harmless), but a future
maintainer reading I6 will expect cache reuse that does not exist.

**Suggested fix:**
1. Drop the `--mount=type=cache,target=.../.cache/cargo-binstall` mounts
   from Layers 3-5 and 3-6 (they cache nothing).
2. Rewrite I6 to: "cargo-binstall has no persistent download cache; it
   uses a per-run RAII tempdir inside `$CARGO_HOME` (cleaned up after
   each install). There is therefore no BuildKit cache mount for
   binstall downloads; rebuilds re-fetch prebuilt archives from GitHub."
3. If download reuse is actually desired, the only viable lever is
   mounting the parent `$CARGO_HOME` root — but that conflicts with the
   `dotfiles_cargo` named-volume copy-on-first-mount semantics, so it is
   not recommended. Accept re-fetch per rebuild.

**Verification steps:** run `strace -f -e trace=openat cargo binstall -y topgrade`
(or `cargo binstall --no-cleanup -y topgrade` and inspect the retained
temp dir); observe the temp dir is created under `$CARGO_HOME`, not
`~/.cache/cargo-binstall`. `ls ~/.cache/cargo-binstall` before/after
shows no writes.

### F2 details
> **Quote (design §1 S6):** "`make down && make up` preserves cargo /
> rustup toolchain binaries (the named volumes persist — regression
> check)."

**Evidence:** the Makefile `up` target mounts the named volume
`dotfiles_cargo` at `/home/$(USERNAME)/.local/share/cargo`. Podman
copy-on-first-mount populates the volume from the image's
`$CARGO_HOME` tree **only on the first `make up` against an empty
volume**. Once the volume is non-empty, subsequent `make up` does NOT
re-copy image content into it — the volume shadows the image's
`$CARGO_HOME/bin`. The design adds two new binaries to `$CARGO_HOME/bin`
(`cargo-binstall`, `topgrade`). On a host that already has a
`dotfiles_cargo` volume from a pre-design build, `make build && make up`
will mount the **old** volume content (no binstall/topgrade), so the S1
acceptance check `cargo binstall -V` and S2 `which topgrade` will FAIL
inside the container despite the build succeeding.

**Impact:** S1/S2 acceptance can fail in the real rollout path; the
build vs runtime gap is not documented. This is the same limitation as
the existing rustup/mise pattern, but the design introduces *new*
binaries in `$CARGO_HOME/bin` so the migration must be called out.

**Suggested fix:** add a "Rollout / migration" note to §4 or §5:
"Because `cargo-binstall` and `topgrade` are new entries in
`$CARGO_HOME/bin`, an existing `dotfiles_cargo` named volume (from a
prior build) will not pick them up on `make up` — Podman does not
re-populate a non-empty volume. Run `make clean` (or
`podman volume rm dotfiles_cargo`) before the first `make up` after this
change. Subsequent `make down && make up` then persists the new binaries
(S6)."

**Verification steps:** on a host with an existing `dotfiles_cargo`
volume: `make build && make up && podman exec dotfiles-manjaro zsh -ic
'which topgrade'` → fails; `make clean && make build && make up &&
podman exec dotfiles-manjaro zsh -ic 'which topgrade'` → succeeds.

### F3 details
> **Quote (design §6):** "`programs/generate_deps` tests green (`make
> test-deps` or `pytest programs/generate_deps/tests/` — confirm the
> exact target in the Makefile during implementation; open question
> Q3`)."

**Evidence:** `grep -nE "test|pytest|test-deps" Makefile` returns no
test target — the Makefile defines only `help build up exec down clean
gen-deps` (+ `_require_username`). `03-makefile.md` §Contract states
"New targets require a `08-automations.md` entry or a `12-quickstart.md`
reference; orphaned targets are forbidden." The existing tests are
pytest-based (`programs/generate_deps/tests/test_*.py`); running
`python3 -m pytest programs/generate_deps/tests/ -q` passes 24 tests
(baseline confirmed). So the invocation is concrete, but the design
leaves the target open.

**Impact:** S7 ("tests green") cannot be verified by a named Make
target today; CI / reviewers must know to invoke pytest directly. Not a
build blocker.

**Suggested fix:** either (a) add a `test-deps` target to the Makefile
(`pytest programs/generate_deps/tests/`) + an `08-automations.md` entry
(spec 03 requires it), or (b) pin the pytest invocation verbatim in §6
and drop the "`make test-deps`" alternative. Prefer (a) for
operability/CI.

**Verification steps:** `make test-deps` (after adding it) exits 0; or
`python3 -m pytest programs/generate_deps/tests/ -q` → `24 passed`.

### F4 details
> **Quote (design §5.2 Layer 3-6):** `cargo binstall -y --no-confirm ${=pkgs}`

**Evidence:** `cargo-binstall --help` (verified against the v1.20.1
binary fetched from the latest release) prints:
`-y, --no-confirm  Disable interactive mode / confirmation prompts`.
They are the **same** clap flag (short/long alias). Passing both is
harmless (clap deduplicates) but redundant. Q2 is resolved: `-y` alone
is the correct, sufficient non-interactive flag and works without a TTY
(build `RUN` is non-interactive; `-y` suppresses the prompt that would
otherwise require stdin).

**Suggested fix:** use `cargo binstall -y ${=pkgs}`; drop
`--no-confirm`. Close Q2 with "RESOLVED: `-y` (= `--no-confirm`) is the
single non-interactive flag; verified via `cargo-binstall --help`; works
without a TTY."

**Verification steps:** `cargo binstall --help | grep -A1 'no-confirm'`
shows `-y, --no-confirm` as one flag.

### F5 details
> **Quote (design §5.2 Layer 3-6):**
> `--mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/registry,uid=${HOST_UID},gid=${HOST_GID}`

**Evidence:** `cargo binstall` resolves crate metadata (Cargo.toml,
bin name, version) via the **crates.io HTTP API** and the GitHub
release-asset guess templates (`crates/binstalk-fetchers/src/gh_crate_meta/hosting.rs`),
not via the cargo registry/git index on disk. The
`~/.local/share/cargo/{registry,git}` cache mounts are relics of the
old `cargo install --locked` (source-compile) path that the design
replaces. They do not harm the build, but they cache directories
binstall does not populate/use.

**Suggested fix:** drop the `cargo/registry` and `cargo/git` cache
mounts from Layer 3-6 (the binstall path does not compile from source).
Keep them on Layer 4-1/4-2 (paru / Rust AUR packages still need them)
and on the binstall bootstrap's downstream — unchanged. If a
`cargo install --locked` fallback is ever re-enabled, re-add them.

**Verification steps:** `cargo binstall -y topgrade` with the registry
cache mount absent still succeeds (binstall never touches
`$CARGO_HOME/registry`).

### F6 details
> **Quote (design §4):** "all reversible" (rollback claim).

**Evidence:** `programs/generate_deps/main.py` `write_txt_files` only
**writes** files for layers with entries or for `EXPECTED_EMPTY_FILES`
pairs; it never deletes stale `layer_<N>/<manager>.txt` files or empty
layer directories. `EXPECTED_EMPTY_FILES = ((3,"cargo"), (4,"paru"),
(3,"mise"))` — `(6,"cargo")` is deliberately absent (the Containerfile
never COPYs layer 6). So after reverting `packages.toml` (removing the
layer-6 entries) and running `make gen-deps`, the file
`dependencies/layer_6/cargo.txt` and the `layer_6/` directory remain on
disk. Tracked-file rollback (Containerfile / packages.toml / main.py /
specs) is clean via `git revert`; only the generated artifact lingers.

**Impact:** minor — the lingering file is a generated artifact, removed
by `git clean -fdx dependencies/layer_6` or `rm -rf dependencies/layer_6`.
But the design's "all reversible" claim should acknowledge it.

**Suggested fix:** add to §4 (rollback): "Reverting the tracked changes
and running `make gen-deps` regenerates `layer_3/cargo.txt` to empty
and refreshes the spec 02 AUTO-GEN block; the generated
`dependencies/layer_6/cargo.txt` (and `layer_6/` dir) are not auto-removed
by the generator — run `git clean -fdx dependencies/layer_6` to purge."

**Verification steps:** after revert + `make gen-deps`,
`ls dependencies/layer_6/` still shows `cargo.txt`; `git clean -fdx
dependencies/layer_6` removes it.

## Verified premises

- **P1 (Q1 — cargo-binstall asset, RESOLVED):** the release asset
  `cargo-binstall-x86_64-unknown-linux-musl.tgz` exists at the latest
  release (v1.20.1) and is reachable at
  `https://github.com/cargo-bins/cargo-binstall/releases/latest/download/cargo-binstall-x86_64-unknown-linux-musl.tgz`
  (verified via the GitHub releases API + an actual download). The tgz
  contains a **single root-level `cargo-binstall` binary** (no directory
  prefix), so `tar -xz -C "$CARGO_HOME/bin"` places it correctly at
  `$CARGO_HOME/bin/cargo-binstall`. `cargo binstall -V` then resolves
  via the cargo-subcommand convention (`cargo-*` on PATH). The build
  will NOT block on Q1.
- **P2 (topgrade binstall-compatibility, RESOLVED — no HIGH/CRITICAL):**
  `topgrade` IS cargo-binstall-compatible. topgrade v17.6.2 ships
  GitHub release assets including
  `topgrade-v17.6.2-x86_64-unknown-linux-musl.tar.gz` (verified via the
  GitHub releases API + download; the tarball contains a single
  root-level `topgrade` binary). Although topgrade's `Cargo.toml` has
  no `[package.metadata.binstall]` block and no explicit `[[bin]]`
  (cargo auto-discovers `src/main.rs`), cargo-binstall's default
  gh-crate-meta fetcher tries multiple URL templates
  (`crates/binstalk-fetchers/src/gh_crate_meta/hosting.rs`) including
  `{repo}/releases/download/v{version}/{name}-v{version}-{target}{archive-suffix}`,
  which **matches topgrade's actual asset naming**. Layer 3-6
  (`cargo binstall -y topgrade`) will succeed. The design's §7 "Risk"
  assessment is correct.
- **P3 (Q2 — non-interactive flag, RESOLVED):** `cargo binstall -y`
  works in a non-interactive build (no TTY). `cargo-binstall --help`
  (v1.20.1) confirms `-y, --no-confirm  Disable interactive mode /
  confirmation prompts` is the single flag; with `-y`, binstall does
  not require stdin/TTY. Q2 resolves to `-y` alone (see F4).
- **P4 (`make gen-deps` exists and regenerates layer_3/cargo.txt +
  spec 02):** the Makefile defines `gen-deps` (`python3
  programs/generate_deps/main.py`). Running it on the current
  (pre-design) state is a no-op (`txt_written=0, doc_updated=False`),
  confirming the generator is idempotent. After the design's
  `packages.toml` change, it will emit `layer_3/cargo.txt` (topgrade)
  and `layer_6/cargo.txt` (the five runtime-manual tools). The
  generator emits `layer_<N>/<manager>.txt` for any `layer >= 1` with
  entries (`write_txt_files` main loop), so layer-6 emission needs
  **no functional generator change** — only the spec-02 heading
  special-case (design §5.3). Confirmed against
  `programs/generate_deps/main.py`.
- **P5 (empty `layer_3/cargo.txt` still builds):** `(3, "cargo")` is in
  `EXPECTED_EMPTY_FILES` (`main.py`), so `layer_3/cargo.txt` is always
  generated even with 0 entries; the Containerfile `COPY --from=deps
  layer_3/cargo.txt` never breaks. The Layer 3-6 `if [ -n "$pkgs" ]`
  guard skips the install when the list is empty. After adding
  `topgrade`, the file is non-empty but the guard handles both states.
  The design's I5 captures this correctly.
- **P6 (persistence / `dotfiles_cargo` volume wired):** the Makefile
  `up` target mounts `-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo`
  and `clean` runs `podman volume rm $(CARGO_VOLUME) …`. cargo binaries
  installed to `$CARGO_HOME/bin` (including the new `cargo-binstall`
  and `topgrade`) persist across `make down && make up` via the named
  volume — consistent with the existing rustup/mise pattern (spec 21
  acceptance #8/#13). S6 holds, **subject to the volume-migration
  caveat in F2**.
- **P7 (cache mount uid/gid convention):** all existing BuildKit
  `--mount=type=cache` directives under `/home/${USERNAME}/.cache/…`
  and `/home/${USERNAME}/.local/share/…` use
  `uid=${HOST_UID},gid=${HOST_GID}` (Containerfile Layers 3-2/3-4/3-5/
  4-1/4-2). The design's new cache mounts follow the same convention —
  consistent. (Whether the *paths* they mount are correct is F1/F5.)
- **P8 (generator tests green at baseline):** `python3 -m pytest
  programs/generate_deps/tests/ -q` → `24 passed`. The cargo-manager
  path is already covered by `test_cargo_manager.py`
  (`test_write_txt_files_emits_empty_cargo_txt_when_no_entries` etc.).
  The design's planned layer-6 tests are additive and the baseline is
  green.
- **P9 (sub-layer reorder is dependency-safe):** the design moves mise
  languages from 3-5 to 3-4 and cargo from 3-4 to 3-5/3-6. cargo-binstall
  (3-5) and `cargo binstall` (3-6) depend only on `cargo` (rustup 3-2),
  not on mise. mise languages (3-4) depend only on `mise` (3-3), not on
  cargo. The reorder introduces no cross-dependency; build order remains
  valid.
- **P10 (rollback of tracked files is clean):** all edits are in
  tracked files (`container/Containerfile`, `dependencies/packages.toml`,
  `programs/generate_deps/main.py`, specs) + one new generated file
  (`layer_6/cargo.txt`) + a regenerated `layer_3/cargo.txt`. `git
  revert` + `make gen-deps` restores the tracked state; only the
  generated layer-6 artifact lingers (F6). No irreversible host /
  Podman state is touched by the change itself (the volume-migration in
  F2 is a runtime, not code, concern).

## Open questions

- **Q-E1:** Should the design drop the ineffective
  `~/.cache/cargo-binstall` cache mounts entirely (recommended), or did
  the author intend a different cache strategy (e.g. mounting the
  `$CARGO_HOME` root)? This determines how I6 is rewritten. (addresses
  F1)
- **Q-E2:** Is the operator expected to run `make clean` (or
  `podman volume rm dotfiles_cargo`) before the first `make up` after
  this change? This rollout prerequisite must be documented for S1/S2
  to hold on existing hosts. (addresses F2)
- **Q-E3:** Will a `test-deps` Make target be added (with the
  `08-automations.md` entry that spec 03 §Contract requires), or is the
  pytest invocation pinned directly in §6? (addresses F3)