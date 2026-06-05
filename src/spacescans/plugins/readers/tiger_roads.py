"""TIGER annual road proximity reader.

Loads the intermediate ``annual_proximity.pkl`` (geoid x year x distance
columns) and returns it as a standard exposure DataFrame for consumption by
the ``precomputed_areal`` linkage pattern.

The pkl schema is:
    geoid (int32), year (int64),
    dist_primary_m (float64), dist_secondary_m (float64),
    distance_prisec_m (float64)

The reader tries the canonical v1 output path first, then falls back to the
modularized output path so the pipeline works regardless of which run produced
the intermediate file.
"""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import os
from pathlib import Path

import pandas as pd

from spacescans.pipeline.registry import register_reader

# Candidate paths, searched in order
_CANDIDATES = [
    "output/python/TIGER/annual_proximity.pkl",
    "output/Python/TIGER/annual_proximity.pkl",
    "output_modularized/TIGER/annual_proximity.pkl",
]


def _find_pkl(repo_root: Path) -> Path:
    for rel in _CANDIDATES:
        p = repo_root / rel
        if p.exists():
            return p
    raise FileNotFoundError(
        f"TIGER annual_proximity.pkl not found. Tried:\n"
        + "\n".join(f"  {repo_root / r}" for r in _CANDIDATES)
    )


@register_reader("tiger_roads")
class TIGERRoadsExposureSource:
    """Load ``annual_proximity.pkl`` for the precomputed_areal pattern.

    Returns a DataFrame with columns:
        geoid (int64), year (int64),
        dist_primary_m, dist_secondary_m, distance_prisec_m (float64)
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame:
        # Resolve repo root relative to the config file's declared exposure path.
        repo_root = Path(os.getcwd())

        # Accept .pkl (v1) or .parquet (v2 C3 output); fall back to canonical path.
        exposure_path = Path(self.config.exposure.file)
        if exposure_path.exists() and exposure_path.suffix in (".pkl", ".parquet"):
            data_path = exposure_path
        else:
            data_path = _find_pkl(repo_root)

        if data_path.suffix == ".parquet":
            df = pd.read_parquet(str(data_path))
        else:
            df = pd.read_pickle(str(data_path))

        # Normalise column names — accept v1 (dist_primary_m / ...) or v2 (dist_pri / ...)
        df = df.rename(columns={"dist_primary_m": "dist_pri",
                                 "dist_secondary_m": "dist_sec",
                                 "distance_prisec_m": "dist_prisec"})
        df["geoid"] = df["geoid"].astype("int64")
        df["year"] = df["year"].astype("int64")

        # Filter to requested years if specified
        if years:
            df = df[df["year"].isin(years)]

        return df[["geoid", "year", "dist_pri", "dist_sec", "dist_prisec"]].reset_index(drop=True)
