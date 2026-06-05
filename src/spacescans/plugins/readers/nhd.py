"""NHD blue-space proximity reader.

Loads the intermediate ``proximity_blue_by_category_m.pkl`` (geoid-level static
distances to NHD flowlines, waterbodies, areal water, and coastline) and returns
it as a standard exposure DataFrame for consumption by the
``precomputed_static`` linkage pattern.

The pkl schema is:
    geoid (int32),
    dist_flow_m, dist_water_m, dist_area_m, dist_coast_m, dist_blue_m (float64)

The reader tries the canonical v1 output path first, then falls back to the
modularized output path so the pipeline works regardless of which run produced
the intermediate file.
"""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import os
from pathlib import Path

import numpy as np
import pandas as pd

from spacescans.pipeline.registry import register_reader

_CANDIDATES = [
    "output/python/NHD/proximity_blue_by_category_m.pkl",
    "output/Python/NHD/proximity_blue_by_category_m.pkl",
    "output_modularized/NHD/proximity_blue_by_category_m.pkl",
]


def _find_pkl(repo_root: Path) -> Path:
    for rel in _CANDIDATES:
        p = repo_root / rel
        if p.exists():
            return p
    raise FileNotFoundError(
        f"NHD proximity_blue_by_category_m.pkl not found. Tried:\n"
        + "\n".join(f"  {repo_root / r}" for r in _CANDIDATES)
    )


@register_reader("nhd")
class NHDExposureSource:
    """Load ``proximity_blue_by_category_m.pkl`` for the precomputed_static pattern.

    Returns a DataFrame with columns:
        geoid (int64),
        dist_flow_m, dist_water_m, dist_area_m, dist_coast_m, dist_blue_m (float64)

    The dist_coast_m column has NaN filled with 99999 to match v1 behaviour.
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years=None) -> pd.DataFrame:
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
        df["geoid"] = df["geoid"].astype("int64")

        # Note: dist_coast_m NaN values are left as NaN here so the TWA
        # correctly skips them.  The 99999 fill (v1 behaviour) is applied
        # AFTER patient-level aggregation by the linkage pattern.

        value_cols = ["dist_flow_m", "dist_water_m", "dist_area_m", "dist_coast_m", "dist_blue_m"]
        keep = ["geoid"] + [c for c in value_cols if c in df.columns]
        return df[keep].reset_index(drop=True)
