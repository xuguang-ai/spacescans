# src/spacescans/pipeline/runner.py
"""Pipeline runner — the main entry point."""
from __future__ import annotations
from pathlib import Path
from spacescans.engine.duckdb_engine import DuckDBEngine
from spacescans.models.config import DatasetConfig
from spacescans.pipeline.loader import load_config
from spacescans.pipeline.registry import get_pattern, init


class Pipeline:
    def __init__(self, config: DatasetConfig):
        self.config = config
        self.engine = self._build_engine()

    @classmethod
    def from_config(
        cls,
        path: str | Path,
        *,
        data_dir: str | None = None,
        output_dir: str | None = None,
    ) -> "Pipeline":
        init()
        config = load_config(path, data_dir=data_dir, output_dir=output_dir)
        return cls(config)

    def run(self) -> Path:
        pattern_fn = get_pattern(self.config.linkage_pattern.value)
        return pattern_fn(self.config, self.engine)

    def _build_engine(self):
        backend = self.config.engine.backend
        if backend == "duckdb":
            return DuckDBEngine()
        raise ValueError(f"Unknown engine backend: {backend}")
