"""MODIS NDVI Part3 reader.

Loads the merged + interpolated NDVI pkl produced by Part1/Part2
(``modis_ndvi_MOD13Q1_MYD13Q1_all_years_interp.pkl``) and returns it as a
standard gridded exposure DataFrame for the ``gridded`` linkage pattern.

Input pkl schema:
    grid_id (int64), startDate (datetime64), endDate (datetime64),
    ndvi (float64), is_interp (bool)

Output schema (consumed by gridded_linkage):
    grid_id (int64), start_date (datetime64[ns]),
    end_date (datetime64[ns]), ndvi (float64)

Candidate paths are searched in order:
  1. output_modularized/…/modis_ndvi_*_all_years_interp.pkl
  2. output/Python/…/modis_ndvi_*_all_years_interp.pkl
  3. output/python/…/modis_ndvi_*_all_years_interp.pkl
"""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import os
from pathlib import Path

import pandas as pd

from spacescans.pipeline.registry import register_reader

_SUBPATH = (
    "270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi"
    "/MERGED_MOD13Q1_MYD13Q1"
    "/modis_ndvi_MOD13Q1_MYD13Q1_all_years_interp.pkl"
)

_CANDIDATES = [
    f"output_modularized/{_SUBPATH}",
    f"output/Python/{_SUBPATH}",
    f"output/python/{_SUBPATH}",
]

# Date bounds matching v1 script
_DATE_MIN = pd.Timestamp("2012-01-01")
_DATE_MAX = pd.Timestamp("2019-12-31")


def _find_pkl(repo_root: Path) -> Path:
    for rel in _CANDIDATES:
        p = repo_root / rel
        if p.exists():
            return p
    raise FileNotFoundError(
        f"MODIS NDVI interp pkl not found. Tried:\n"
        + "\n".join(f"  {repo_root / r}" for r in _CANDIDATES)
    )


@register_reader("modis_ndvi")
class MODISNDVIExposureSource:
    """Load the merged+interpolated MODIS NDVI pkl for the gridded pattern.

    Returns a DataFrame with columns:
        grid_id (int64), start_date (datetime64[ns]),
        end_date (datetime64[ns]), ndvi (float64)
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame:
        repo_root = Path(os.getcwd())

        # Allow config to point directly to the pkl or to a directory
        exposure_path = Path(self.config.exposure.file)
        if exposure_path.suffix == ".pkl" and exposure_path.exists():
            pkl_path = exposure_path
        else:
            pkl_path = _find_pkl(repo_root)

        df = pd.read_pickle(str(pkl_path))

        # Rename date columns to match gridded_linkage expectations
        df = df.rename(columns={"startDate": "start_date", "endDate": "end_date"})
        df["start_date"] = pd.to_datetime(df["start_date"])
        df["end_date"] = pd.to_datetime(df["end_date"])

        # Apply global date bounds (matches v1)
        df = df[(df["start_date"] <= _DATE_MAX) & (df["end_date"] >= _DATE_MIN)].copy()

        # Keep only interpolated records (is_interp == True means we KEEP them in v1)
        # v1 KEEP_INTERP_ONLY=True means keep all rows (interp + observed)
        # The column name is 'is_interp'; v1 logic: if KEEP_INTERP_ONLY=False, drop interp rows
        # Default is True → keep all
        keep_interp_only = True
        if not keep_interp_only and "is_interp" in df.columns:
            df = df[~df["is_interp"]].copy()

        df["grid_id"] = df["grid_id"].astype("int64")
        df["ndvi"] = df["ndvi"].astype("float64")

        # Filter to requested years if specified
        if years:
            mask = df["start_date"].dt.year.isin(years) | df["end_date"].dt.year.isin(years)
            df = df[mask].copy()

        return df[["grid_id", "start_date", "end_date", "ndvi"]].reset_index(drop=True)
