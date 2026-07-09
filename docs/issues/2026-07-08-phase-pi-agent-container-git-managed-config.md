# Phase 7 Result Log: pi Agent Container + Git-Managed Config

**Date:** 2026-07-08
**Status:** done-with-concerns
**Plan:** [2026-07-08-pi-agent-container-git-managed-config-impl.md](../plans/2026-07-08-pi-agent-container-git-managed-config-impl.md)
**Design:** [2026-07-08-pi-agent-container-git-managed-config-design.md](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md)
**Parent issue:** [2026-07-08-pi-agent-container-git-managed-config.md](./2026-07-08-pi-agent-container-git-managed-config.md)

## Commit range summary

Phase 7 verifies the work committed through:

- `7fffc22` docs: sync pi agent container and external config specs (Phase 6)
- `0ef4e0d` docs: fix Phase 6 review findings before Phase 7
- Earlier implementation commits: `d2dae98`, `84cbbcb`, `5aec92f`, `bf09d37`

## Environment

- Host: pi-side workspace (`/data/dotfiles3`)
- Local pi-config checkout: `/data/pi-config`, tag `pi-config-v2026-07-08-1`
- GitHub remote `kkiyama117/pi-config` is **not yet published**.
- `.env` defines `USERNAME=kiyama`.
- Existing container `dotfiles-manjaro` has been running for ~2 hours.

## Verification results

| Step | Check | Exact command | Result | Notes |
|------|-------|---------------|--------|-------|
| 1 | Template/script syntax | `chezmoi execute-template --init < .chezmoi.toml.tmpl` + `.chezmoiexternal.toml.tmpl` + `.chezmoiscripts/run_after_configure-pi-agent.sh.tmpl` + `bash -n` | **PASS** exit 0 | Templates render; scripts parse. |
| 2a | Container tests | `PYTHONDONTWRITEBYTECODE=1 make test-container` | **PASS** | `12 passed in 0.55s` |
| 2b | Dependency tests | `PYTHONDONTWRITEBYTECODE=1 make test-deps` | **PASS** | `24 passed in 0.54s` |
| 2c | Zsh tests | `make test-zsh` | **PASS** | `zsh container/tests/zsh/zoxide_zi_test.zsh` exited 0 |
| 3 | Diff check | `git diff --check` | **PASS** exit 0 | No whitespace errors. |
| 4 | `make build` | NOT RUN | **INCONCLUSIVE** | Container was already running; build not executed this session. |
| 5 | `make up` with `PI_CONFIG_URL=file:///data/pi-config` | NOT RUN | **INCONCLUSIVE** | `Makefile` does not expose a way to pass arbitrary env such as `PI_CONFIG_URL` into `podman run`. Existing container lacks `/data/pi-config` mount, so runtime external fetch from local source is impossible without Makefile/compose changes or manual podman flags. |
| 6 | `pi --version` inside container | `podman exec dotfiles-manjaro zsh -ic 'pi --version'` | **PASS** | `0.80.3` returned, exit 0. |
| 7 | External prompt linkage | `podman exec dotfiles-manjaro zsh -ic 'test -r ~/.pi/agent/prompts/commit.md'` | **INCONCLUSIVE / FAIL** | `commit-prompt: missing`. External linkage was not verified because the running container does not have `/data/pi-config` mounted and `~/.local/share/pi-config` does not exist. |
| 8 | No sensitive pi runtime paths in git | `git ls-files` checks under `/data/dotfiles3` and `/data/pi-config` | **PASS** | No `auth.json`, `trust.json`, `sessions/`, `transcripts/`, `logs/`, `npm/`, `cache/` tracked in either repo. |
| 9 | No pi runtime secrets baked into image | `podman run --rm --entrypoint /usr/bin/test localhost/dotfiles-manjaro:latest ! -e /home/kiyama/.local/share/pi-config` | **PASS** exit 0 | `~/.local/share/pi-config` is not present in the image. |
| 10 | No sensitive files under `~/.pi/agent` at runtime | `podman exec dotfiles-manjaro zsh -ic 'test ! -e ~/.pi/agent/auth.json && test ! -d ~/.pi/agent/sessions'` | **FAIL** | `auth.json` and `sessions/` exist inside the container. These are unmanaged runtime state created by prior `pi` usage; they are not in either git repo and not in the image. |

## Observations

- The existing container was started before Phase 7 and still contains pi runtime state (`~/.pi/agent/auth.json`, `~/.pi/agent/sessions`, `~/.pi/agent/settings.json`).
- `~/.pi/agent/prompts/commit.md` is missing in the container, so the host-side chezmoi auto-commit hook would fall back to `~/.local/share/pi-config/agent/prompts/commit.md` or fail if neither is available.
- `~/.local/share/pi-config` is absent, so the external chezmoi consumer did not populate stable resources in this running container.
- `make up`/`make build` were not re-executed in this verification pass, so fresh-image behavior and runtime external-fetch behavior remain unverified.

## GitHub remote status

Push of `kkiyama117/pi-config` is **deferred**. Runtime verification therefore used `PI_CONFIG_URL=file:///data/pi-config` conceptually, but the Makefile does not currently wire that env into the container, so it could not be exercised end-to-end.

## Residual risks

1. **Runtime external fetch is unverified.** Without running `make build`/`make up`, we do not know that `PI_CONFIG_URL=file:///data/pi-config` will correctly fetch the external repo at runtime.
2. **Makefile env plumbing gap.** `Makefile` has no documented knob to pass `PI_CONFIG_URL`/`PI_CONFIG_REF` into `podman run`; this is a likely blocker for local override testing unless users invoke `podman run` manually.
3. **Existing container state masks verification.** The running container contains runtime `auth.json`/`sessions`, so checks expecting a clean `~/.pi/agent` are inconclusive. Future verification should start from a fresh image/volume.
4. **Prompt linkage not proven.** Because the prompt is missing, the host auto-commit hook path relying on `~/.pi/agent/prompts/commit.md` has not been validated end-to-end.
5. **GitHub remote not published.** Default source `https://github.com/kkiyama117/pi-config.git` cannot be fetched by anyone else until the remote is public and the tag is pushed.
