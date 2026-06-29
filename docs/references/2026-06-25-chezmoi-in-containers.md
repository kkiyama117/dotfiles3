# chezmoi inside containers — prior art and gotchas

## Summary

- chezmoi's official container story is Codespaces / VS Code devcontainers: clone repo to a non-default path, pin `sourceDir` in the config template to that path with `sourceDir = {{ .chezmoi.sourceDir | quote }}`; the `chezmoi docker` / `chezmoi podman` commands (merged Aug–Sep 2025) cover the ephemeral "install + apply + exec shell" pattern, not the bind-mount-and-edit pattern.
- The persistent state file (`chezmoistate.boltdb`) lives at `~/.config/chezmoi/chezmoistate.boltdb` by default — **not** inside `sourceDir` — so a bind mount does not cause the container to write state back into the host repo.
- A live `.git` tree in `sourceDir` activates git-dependent features: `autoCommit`/`autoPush`, `chezmoi update` (git pull), `chezmoi git …` pass-through, and the `working-tree` auto-detection walk; none of these fire when git is absent (as with the current baked image).
- Known gotchas with bind-mount + `.git`: git ≥ 2.35.2 will refuse operations inside the container if the mounted directory is owned by a different UID (`fatal: detected dubious ownership`); rootless Podman UID-mapping makes this nearly certain unless `--userns=keep-id` is set.

---

## What chezmoi docs say

### Containers and VMs page
<https://www.chezmoi.io/user-guide/machines/containers-and-vms/>

Covers Codespaces / VS Code Remote Containers only. Key requirement: when chezmoi is initialized with `--source=<non-default-path>`, the generated config **must** echo that path back:

```toml
# .chezmoi.toml.tmpl
sourceDir = {{ .chezmoi.sourceDir | quote }}
```

Without this line the source dir reverts to `~/.local/share/chezmoi` on next run, breaking `chezmoi cd` (see issue #3884 below).

### `chezmoi docker` / `chezmoi podman` commands (experimental, merged 2025-08)
<https://chezmoi.io/reference/commands/docker/>  
PRs: <https://github.com/twpayne/chezmoi/pull/4612> (podman+ssh), <https://github.com/twpayne/chezmoi/pull/4945> (podman alias for docker)

These commands bootstrap chezmoi *inside* a fresh or existing container by installing the binary, running `chezmoi init --apply <github-user>`, then exec-ing a shell. This is a **pull-from-GitHub** pattern, not a bind-mount pattern.

```bash
chezmoi podman run ubuntu:latest twpayne   # new container
chezmoi podman exec $CONTAINER_ID twpayne  # existing container
```

### Persistent state location
<https://www.chezmoi.io/reference/configuration-file/variables/>  
<https://chezmoi.io/reference/command-line-flags/global/>

| Variable | Default |
|---|---|
| `sourceDir` | `$HOME/.local/share/chezmoi` |
| `persistentState` | `$HOME/.config/chezmoi/chezmoistate.boltdb` |
| `workingTree` | same as `sourceDir` (git walk upward from there) |

`chezmoistate.boltdb` is separate from the source dir. chezmoi explicitly lists `chezmoistate.boltdb` as a `knownTargetFile` to warn if it appears inside the source tree  
(source: <https://github.com/twpayne/chezmoi/blob/master/internal/chezmoi/chezmoi.go>, `knownTargetFiles` set, line ~30).  
**Conclusion: bind-mounting sourceDir does not cause state to be written into the host repo.**

### `.chezmoiroot` file
<https://chezmoi.io/user-guide/advanced/customize-your-source-directory/>

A `.chezmoiroot` file in the root of the source dir redirects chezmoi to read source state from a subdirectory (e.g. `home/`). Useful if the repo root contains non-chezmoi files (README, CI scripts, etc.) that would otherwise pollute `$HOME`. Does live inside sourceDir; a bind mount carries it naturally.

### git auto-commit / auto-push
<https://www.chezmoi.io/user-guide/daily-operations>

```toml
[git]
    autoCommit = true
    autoPush   = true
```

Both options are **opt-in and off by default**. They only activate when the source dir is a git working tree. A baked image without `.git` silently skips them. With a bind-mounted source dir that has `.git`, they become active — which is desirable for the live-edit workflow but may surprise scripts that run `chezmoi apply` non-interactively.

### Container detection template pattern
<https://twpayne-chezmoi.mintlify.app/advanced/customize-chezmoi>

```toml
{{- $isContainer := or (stat "/run/.containerenv") (stat "/.dockerenv") -}}
{{- if $isContainer }}
pager = ""
verbose = false
{{- end }}
```

Useful for suppressing interactive prompts and pager output when running inside any OCI container.

---

## What people actually do (with links)

- **Codespaces / devcontainer install.sh pattern** — <https://github.com/twpayne/chezmoi/issues/760> — VS Code clones dotfiles repo to `~/.local/share/chezmoi`, `install.sh` runs `chezmoi init --apply --source=.`; the source dir becomes the cloned repo (with `.git`). Most common real-world container use of chezmoi.

- **VSCode remote-containers example (bind-mount of dotfiles into container)** — <https://github.com/ihommani/vscode_chezmoi_example> — configures `"dotfiles.targetPath": "~/.local/share/chezmoi"` in VS Code settings so the host dotfiles clone is bind-mounted to chezmoi's default sourceDir; `chezmoi cd` + `git commit` workflow from inside container explicitly documented.

- **DevContainer `postStartCommand` for safe.directory** — <https://www.kenmuse.com/blog/avoiding-dubious-ownership-in-dev-containers/> — canonical blog post on the git "dubious ownership" error in containers; recommends `"postStartCommand": "git config --global --add safe.directory ${containerWorkspaceFolder}"` in `devcontainer.json`.

- **Codespaces sourceDir bug (empty chezmoi cd)** — <https://github.com/twpayne/chezmoi/issues/3884> — user's `chezmoi cd` entered an empty non-git directory because `.chezmoi.toml.tmpl` lacked `sourceDir = {{ .chezmoi.sourceDir | quote }}`; fixed by PR #3890 adding explicit doc clarification.

- **chezmoi podman/docker experimental command** — <https://github.com/twpayne/chezmoi/pull/4612> — official first-party container workflow; downloads dotfiles from GitHub on each container start; no bind mount involved.

- **ray-manaloto/dotfiles — chezmoi in devcontainer with mise** — <https://github.com/ray-manaloto/dotfiles> — `chezmoi init` clones repo inside container; Python lifecycle hooks manage complex orchestration; baked pattern (no bind mount).

- **rezachegini.com blog — chezmoi in dev container step-by-step** — <https://rezachegini.com/2025/10/14/installing-and-using-chezmoi-in-a-dev-container/> — install script `chezmoi init --apply git@github.com:…/dotfiles.git` in `postCreateCommand`; pull pattern, not bind-mount.

---

## Known gotchas

- **git "dubious ownership" (CVE-2022-24765)** — <https://www.kenmuse.com/blog/avoiding-dubious-ownership-in-dev-containers/>; <https://github.com/containers/podman/discussions/27782> — git ≥ 2.35.2 refuses all operations if the bind-mounted directory UID does not match the running user; manifests as `fatal: detected dubious ownership in repository at '/var/lib/chezmoi-source'`; chezmoi's `autoCommit` and `chezmoi git …` calls will silently fail or error out. Fix: `git config --global --add safe.directory /var/lib/chezmoi-source` in the container entrypoint or Containerfile.

- **Rootless Podman UID mapping** — <https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md>; <https://github.com/containers/podman/discussions/28056> — in rootless mode, host UIDs are remapped through `/etc/subuid`; a file owned by UID 1000 on the host appears as a different UID inside the container unless `--userns=keep-id` is passed. Without it, every git and chezmoi write to the bind-mounted source dir will produce files owned by the wrong UID on the host. Use `--userns=keep-id` (or `userns_mode: "keep-id"` in compose). Avoid the `:U` volume flag — it recursively `chown`s the host directory to the remapped UID.

- **`sourceDir` config must be pinned explicitly** — <https://github.com/twpayne/chezmoi/issues/3884> — if `.chezmoi.toml.tmpl` does not contain `sourceDir = {{ .chezmoi.sourceDir | quote }}`, chezmoi regenerates config pointing at `~/.local/share/chezmoi` and `chezmoi cd` takes you there (empty directory) instead of the bind-mounted path.

- **`autoCommit` fires inside containers if `.git` is present** — <https://www.chezmoi.io/user-guide/daily-operations> — with a real `.git` in the bind-mounted sourceDir and `autoCommit = true` in config, every `chezmoi apply` (including the entrypoint run) will attempt a `git commit` inside the container. This writes to the host repo's git history. Either set `autoCommit = false` for container context or gate it with a template variable.

- **`.git/` scan performance** — no dedicated issue found, but chezmoi walks the source dir on every run to build the source state; a large `.git/` directory does not affect correctness but is traversed by `chezmoi doctor`'s `suspicious-entries` check. Not a correctness issue; potential slowness on very large repos.

- **Lock contention on `chezmoistate.boltdb`** — <https://chezmoi.io/user-guide/frequently-asked-questions/troubleshooting/> — only one writer at a time is allowed; running a second `chezmoi apply` (e.g. from a hook) while the entrypoint is still applying will timeout. Not container-specific, but more likely if the container entrypoint and an interactive shell both call chezmoi simultaneously.

- **`chezmoi podman`/`docker` commands vs. bind-mount** — <https://github.com/twpayne/chezmoi/pull/4612> — the official first-party `chezmoi podman` workflow is designed for ephemeral containers pulling from GitHub, not for persistent bind-mount dev environments; the two patterns are orthogonal.

---

## Recommended reading

- <https://www.chezmoi.io/user-guide/machines/containers-and-vms/> — official Codespaces/devcontainer guide; authoritative on `sourceDir` pinning requirement.
- <https://www.chezmoi.io/reference/configuration-file/variables/> — definitive table of `persistentState`, `sourceDir`, `workingTree` defaults and override keys.
- <https://chezmoi.io/reference/command-line-flags/global/> — `--persistent-state`, `--source`, `--working-tree` flag docs; useful for CLI-level overrides in entrypoints.
- <https://www.kenmuse.com/blog/avoiding-dubious-ownership-in-dev-containers/> — best single-page explainer of the git dubious-ownership error in containers and the `safe.directory` fix.
- <https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md> — Podman rootless UID mapping deep-dive; required reading before bind-mounting any repo in rootless Podman.
- <https://github.com/twpayne/chezmoi/pull/4612> — `chezmoi podman`/`ssh` PR; shows how the maintainer thinks about the container workflow (pull pattern); useful contrast to the bind-mount approach.
- <https://github.com/ihommani/vscode_chezmoi_example> — closest public prior art to the bind-mount-and-edit pattern; VS Code mounts host dotfiles clone to chezmoi's sourceDir and documents the `chezmoi cd` + commit workflow.
