# spacescans/io/readers.py
"""Unified table reading — dispatches by file suffix."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: str | Path, *, key: str | None = None) -> pd.DataFrame:
    """Read a table from any supported format. Dispatches by file suffix."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    if suffix in {".rds", ".rda"}:
        return _read_r_table(path, key=key)
    raise ValueError(f"Unsupported table format: {suffix} ({path})")


def read_tables_concat(
    paths: list[str | Path], *, key: str | None = None, **kwargs,
) -> pd.DataFrame:
    """Read multiple tables and vertically concatenate them."""
    frames = [read_table(p, key=key) for p in paths]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _read_r_table(path: Path, *, key: str | None = None) -> pd.DataFrame:
    """Read one table from an RDS/RData file using pyreadr."""
    from spacescans._extras import require
    require("rda", "pyreadr")
    import pyreadr

    result = pyreadr.read_r(str(path))
    if key is not None:
        return result[key]
    if None in result:
        return result[None]
    if len(result) == 1:
        return next(iter(result.values()))
    keys = ", ".join(str(k) for k in result.keys())
    raise KeyError(f"Multiple objects in {path}; specify key. Available: {keys}")
