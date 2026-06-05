"""MODIS Part1 reader — loads per-product-per-year pkl files from v1 Part1 output.

Expected pkl schema: grid_id (int64), date (datetime64), ndvi (float64)

The reader discovers pkl files under the MODIS output directories for both
MOD13Q1 and MYD13Q1 products, concatenates them, and returns a long-format
DataFrame for consumption by the ``gridded`` linkage pattern.

Candidate paths searched:
    output/Python/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi/{product}/
    output/python/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi/{product}/
    output_modularized/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi/{product}/
"""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import os
import re
from pathlib import Path

import pandas as pd

from spacescans.pipeline.registry import register_reader


_PRODUCTS = ["MOD13Q1", "MYD13Q1"]
_PKL_PATTERN = re.compile(r"^(?P<product>[a-z0-9]+)_(?P<year>\d{4})\.pkl$", re.IGNORECASE)

_BASE_DIRS = [
    "output/Python/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi",
    "output/python/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi",
    "output_modularized/270m/MOD13Q1_MYD13Q1_061/C4/modis_ndvi",
]


def _discover_part1_pkls(years: set[int] | None = None) -> list[Path]:
    """Find per-product-per-year pkl files across candidate directories.

    Deduplicates by (product, year) key — first directory found wins.
    """
    seen: dict[tuple[str, int], Path] = {}
    for base in _BASE_DIRS:
        for product in _PRODUCTS:
            prod_dir = Path(base) / product
            if not prod_dir.is_dir():
                continue
            for p in sorted(prod_dir.glob("*.pkl")):
                m = _PKL_PATTERN.match(p.name)
                if m:
                    yr = int(m.group("year"))
                    if years is not None and yr not in years:
                        continue
                    key = (m.group("product").upper(), yr)
                    if key not in seen:
                        seen[key] = p
    return sorted(seen.values())


@register_reader("modis_part1")
class MODISPart1ExposureSource:
    """Load MODIS Part1 per-product-per-year pkl files.

    Returns a DataFrame with columns:
        grid_id (int64), date (datetime64[ns]), ndvi (float64)
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame:
        requested_years = set(years) if years else None
        pkls = _discover_part1_pkls(requested_years)

        if not pkls:
            raise FileNotFoundError(
                f"No MODIS Part1 pkl files found for years={years}. "
                f"Searched: {_BASE_DIRS}"
            )

        frames = []
        for p in pkls:
            print(f"[modis_part1] Loading {p}")
            df = pd.read_pickle(str(p))
            df["grid_id"] = df["grid_id"].astype("int64")
            df["date"] = pd.to_datetime(df["date"])
            df["ndvi"] = df["ndvi"].astype("float64")
            frames.append(df[["grid_id", "date", "ndvi"]])

        result = pd.concat(frames, ignore_index=True)
        print(f"[modis_part1] Loaded {len(result)} rows from {len(pkls)} files")
        return result
