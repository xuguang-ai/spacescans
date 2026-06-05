"""Shared test fixtures for spacescans tests."""
from __future__ import annotations
import os
import pytest
from pathlib import Path


@pytest.fixture
def clean_env(monkeypatch):
    """Unset SPACESCANS_* env vars so tests don't leak through local config."""
    for name in ("SPACESCANS_DATA_DIR", "SPACESCANS_OUTPUT_DIR"):
        monkeypatch.delenv(name, raising=False)
    yield
