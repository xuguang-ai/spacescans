# tests/test_init_config.py
"""init-config copies templates to target dir."""
import subprocess
import sys
import yaml
from pathlib import Path


def test_init_config_creates_4_templates(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "spacescans.cli", "init-config", "--out", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr={r.stderr}"

    expected = [
        tmp_path / "c3" / "county.yaml",
        tmp_path / "c3" / "zcta5.yaml",
        tmp_path / "c4" / "zbp.yaml",
        tmp_path / "c4" / "cbp_fallback.yaml",
    ]
    for p in expected:
        assert p.is_file(), f"missing {p}"


def test_templates_parse_as_valid_yaml(tmp_path):
    subprocess.run(
        [sys.executable, "-m", "spacescans.cli", "init-config", "--out", str(tmp_path)],
        check=True,
    )
    for path in tmp_path.rglob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        assert "name" in data
        assert "linkage_pattern" in data


def test_templates_use_var_placeholders(tmp_path):
    """Templates must NOT contain hard-coded data_full/ or data/ paths."""
    subprocess.run(
        [sys.executable, "-m", "spacescans.cli", "init-config", "--out", str(tmp_path)],
        check=True,
    )
    for path in tmp_path.rglob("*.yaml"):
        content = path.read_text()
        assert "data_full/" not in content, f"{path}: hard-coded data_full/"
        # Either ${SPACESCANS_DATA_DIR}/ or an explicit base_dir block must be present
        assert "${SPACESCANS_DATA_DIR}" in content or "base_dir:" in content
