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
