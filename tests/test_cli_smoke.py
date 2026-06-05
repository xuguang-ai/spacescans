"""CLI entry points return 0 + correct text."""
import subprocess
import sys


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "spacescans.cli", *args],
        capture_output=True, text=True,
    )


def test_help_returns_zero():
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "spacescans" in r.stdout.lower()
    # Subcommands should be listed
    assert "run" in r.stdout


def test_run_help_returns_zero():
    r = _run_cli("run", "--help")
    assert r.returncode == 0
    assert "data-dir" in r.stdout
    assert "output-dir" in r.stdout


def test_run_missing_config_returns_nonzero():
    r = _run_cli("run", "/tmp/nonexistent_config_does_not_exist.yaml")
    assert r.returncode != 0
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower()
