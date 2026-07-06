from pathlib import Path


ENTRYPOINT = Path(__file__).parents[1] / "bind" / "layer_5_files" / "entrypoint.sh"
MAKEFILE = Path(__file__).parents[2] / "Makefile"


def test_entrypoint_forwards_stop_signal_during_startup_work() -> None:
    text = ENTRYPOINT.read_text()

    assert "trap terminate TERM INT" in text
    assert "run_interruptible chezmoi execute-template --init" in text
    assert "run_interruptible chezmoi apply --no-tty --force" in text


def test_make_up_uses_init_for_steady_state_signal_forwarding() -> None:
    text = MAKEFILE.read_text()

    up_target = text.split("up: _require_username", 1)[1].split("\nexec:", 1)[0]
    assert "--init" in up_target


def test_entrypoint_writes_readiness_sentinel_only_after_apply() -> None:
    """make up waits on /tmp/chezmoi-applied; it must be removed at start
    and touched only after `chezmoi apply` succeeds so a stale flag can
    never satisfy the wait and a failed apply never publishes readiness."""
    text = ENTRYPOINT.read_text()

    assert 'READINESS_SENTINEL="/tmp/chezmoi-applied"' in text
    rm_idx = text.index('rm -f "$READINESS_SENTINEL"')
    apply_idx = text.index("run_interruptible chezmoi apply --no-tty --force")
    touch_idx = text.index('touch "$READINESS_SENTINEL"')
    assert rm_idx < apply_idx < touch_idx


def test_make_up_waits_for_readiness_sentinel() -> None:
    """make up must poll for the sentinel and abort (with logs) if the
    container exits early or the timeout elapses."""
    text = MAKEFILE.read_text()

    up_target = text.split("up: _require_username", 1)[1].split("\nexec:", 1)[0]
    assert "UP_WAIT_TIMEOUT" in up_target
    assert "/tmp/chezmoi-applied" in up_target
    assert "podman logs" in up_target
    assert "exit 1" in up_target
