# tests/test_quickstart.py
"""Quickstart end-to-end against bundled data. Requires [geo]."""
import subprocess
import sys
import pytest
from pathlib import Path


@pytest.mark.geo
@pytest.mark.extras
def test_quickstart_runs_and_writes_output(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "spacescans.cli", "quickstart",
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "Quickstart complete" in r.stdout
    # At least one parquet produced
    outputs = list(tmp_path.rglob("*.parquet"))
    assert outputs, f"no parquet output produced; dir={list(tmp_path.iterdir())}"
