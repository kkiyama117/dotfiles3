# Kakehashi container install result

**Date:** 2026-07-16
**Status:** executed
**Plan:** [../plans/2026-07-16-kakehashi-container-install-impl.md](../plans/2026-07-16-kakehashi-container-install-impl.md)

## Acceptance evidence

| Criterion | Status | Evidence |
|---|---|---|
| Custom Layer 3 inventory | PASS | `make gen-deps` output: `generate_deps: layers=[-1, 0, 1, 3, 4, 6] txt_written=0 doc_updated=False`; second run produced identical output and no diff |
| Static contracts | PASS | `make test-deps`: 38 passed; `make test-container`: 28 passed; `make test-zsh` exited 0; `git diff --check` produced no output |
| Image build | PASS | `make build` completed all stages and `COMMIT localhost/dotfiles-manjaro:latest`; Layer 3-8 printed `kakehashi 0.8.0` |
| Runtime path/version | PASS | `podman exec dotfiles-manjaro zsh -ic 'command -v kakehashi; kakehashi --version'` → `/home/kiyama/.local/bin/kakehashi` and `kakehashi 0.8.0` |
| Mode and ownership | PASS | `podman exec dotfiles-manjaro zsh -ic 'stat -c "%a %U:%G" "$HOME/.local/bin/kakehashi"'` → `755 kiyama:kiyama` |
| Entrypoint boundary | PASS | `! rg -n 'kakehashi' container/bind/layer_5_files/entrypoint.sh` exited 0; no match in entrypoint |
| Specs synchronized | PASS | `programs/generate_deps/tests/test_kakehashi_container_install.py` passes; spec 20 contains I-KAKEHASHI1–6; spec 21 contains Layer 3-8 and acceptance #26 |

## Command outputs

### Offline checks

```bash
$ make gen-deps
python3 programs/generate_deps/main.py
generate_deps: layers=[-1, 0, 1, 3, 4, 6] txt_written=0 doc_updated=False

$ make gen-deps  # idempotency check
python3 programs/generate_deps/main.py
generate_deps: layers=[-1, 0, 1, 3, 4, 6] txt_written=0 doc_updated=False

$ make test-deps
python3 -m pytest programs/generate_deps/tests/ -q
......................................                                   [100%]
38 passed in 0.53s

$ make test-container
python3 -m pytest container/tests/container/ -q
............................                                           [100%]
28 passed in 0.52s

$ make test-zsh
zsh container/tests/zsh/zoxide_zi_test.zsh

$ git diff --check
# no output
```

### Image build and startup

```bash
$ make build
...
[3/5] STEP 11/11: RUN zsh -c 'set -eo pipefail; ...'
kakehashi 0.8.0
...
[5/5] STEP 10/10: CMD ["zsh"]
[5/5] COMMIT localhost/dotfiles-manjaro:latest
--> 062675717872
Successfully tagged localhost/dotfiles-manjaro:latest
0626757178729c436fd87850e2c4a8358326af80580c824db5279c9e2d411191

$ make up
podman run -d --replace --name dotfiles-manjaro ...
make: waiting for entrypoint's chezmoi apply to finish (timeout 120s)...
make: container ready (chezmoi apply finished).
```

### Runtime verification

```bash
$ podman exec dotfiles-manjaro zsh -ic 'command -v kakehashi; kakehashi --version'
/home/kiyama/.local/bin/kakehashi
kakehashi 0.8.0

$ podman exec dotfiles-manjaro zsh -ic 'stat -c "%a %U:%G" "$HOME/.local/bin/kakehashi"'
755 kiyama:kiyama

$ ! rg -n 'kakehashi' container/bind/layer_5_files/entrypoint.sh
# exit status 0, no matches
```

## Notes

- The first `make build` attempt exceeded the 900-second tool timeout while
  copying `entrypoint.sh` near the end of the runtime stage, but the image
  layers up to that point were cached. A second `make build` run completed
  successfully and produced the final image.
- All prior Task 1–3 changes remain uncommitted and unstaged as required.
