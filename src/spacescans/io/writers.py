# spacescans/io/writers.py
"""Unified output — Parquet primary, pkl for compat."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_table(
    df: pd.DataFrame, path: str | Path, *, format: str | None = None,
) -> Path:
    """Write a DataFrame. Format inferred from suffix or explicit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fmt = format or _infer_format(path)
    if fmt == "parquet":
        df.to_parquet(path, index=False)
    elif fmt in {"pkl", "pickle"}:
        df.to_pickle(path)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")
    return path


def write_geo(gdf, path: str | Path, *, driver: str = "GPKG") -> Path:
    """Write a GeoDataFrame, replacing any existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver=driver)
    return path


def _infer_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return "parquet"
    if suffix in {".pkl", ".pickle"}:
        return "pkl"
    raise ValueError(f"Cannot infer output format from suffix: {suffix}")
