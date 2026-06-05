"""PRISM Part1 reader — extracts daily grid-cell values from PRISM zip archives.

Scans the PRISM data directory for zip files, extracts the contained TIF to a
cache directory, reads raster values at grid cells referenced by the C3 weight
table, and returns a long-format DataFrame for consumption by ``gridded``
linkage pattern.

Expected directory structure:
    <exposure.file>/<var>/daily/<year>/prism_<var>_us_30s_YYYYMMDD.zip

Each zip contains a GeoTIFF with the same name (minus .zip + .tif).

Output schema (consumed by gridded_linkage with date_col="date"):
    grid_id (int64), date (datetime64[ns]), <var> (float64)
"""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import os
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from spacescans.pipeline.registry import register_reader


_PRISM_VARS = ["ppt", "tmax", "tmin", "tmean", "tdmean", "vpdmin", "vpdmax"]


def _unzip_prism_tif(zip_path: str, cache_dir: str) -> str:
    """Extract the .tif from a PRISM zip into a cache directory. Returns tif path."""
    stem = os.path.splitext(os.path.basename(zip_path))[0]
    tif_name = stem + ".tif"

    var_match = re.search(r"/(ppt|tmax|tmin|tmean|tdmean|vpdmin|vpdmax)/", zip_path)
    yr_match = re.search(r"/(20\d{2})/", zip_path)
    var = var_match.group(1) if var_match else "unknown"
    yr = yr_match.group(1) if yr_match else "unknown"

    dest_dir = os.path.join(cache_dir, var, yr)
    os.makedirs(dest_dir, exist_ok=True)
    dest_tif = os.path.join(dest_dir, tif_name)

    if not os.path.exists(dest_tif):
        with zipfile.ZipFile(zip_path, "r") as zf:
            tif_members = [n for n in zf.namelist() if n.lower().endswith(".tif")]
            if not tif_members:
                raise RuntimeError(f"No .tif inside: {zip_path}")
            exact = [n for n in tif_members if tif_name in n]
            member = exact[0] if exact else tif_members[0]
            with zf.open(member) as src, open(dest_tif, "wb") as dst:
                dst.write(src.read())

    return dest_tif


def _parse_date_from_zip(zip_path: str) -> pd.Timestamp:
    """Extract date from filename containing YYYYMMDD."""
    m = re.search(r"(\d{8})", os.path.basename(zip_path))
    if m is None:
        raise ValueError(f"Cannot parse date from: {zip_path}")
    return pd.Timestamp(m.group(1))


def _list_var_year_zips(prism_root: str, var: str, year: int) -> list[str]:
    """List zip files for a given variable and year."""
    canonical_dir = os.path.join(prism_root, var, "daily", str(year))
    if os.path.isdir(canonical_dir):
        zips = sorted([
            os.path.join(canonical_dir, f)
            for f in os.listdir(canonical_dir)
            if f.endswith(".zip")
        ])
        if zips:
            return zips
    # Fallback: walk the variable directory
    var_root = os.path.join(prism_root, var)
    if not os.path.isdir(var_root):
        return []
    all_zips = []
    for root, _, files in os.walk(var_root):
        for f in files:
            if f.endswith(".zip") and str(year) in f:
                all_zips.append(os.path.join(root, f))
    return sorted(all_zips)


def _read_one_daily_tif(
    zip_path: str, var_name: str, keep_ids: list[int], cache_dir: str,
) -> pd.DataFrame:
    """Read one day's raster values at the specified grid cells."""
    import rasterio

    tif_path = _unzip_prism_tif(zip_path, cache_dir)
    with rasterio.open(tif_path) as src:
        nodata = src.nodata
        n_cells = src.width * src.height
        ncols = src.width
        valid_ids = [i for i in keep_ids if 0 <= i < n_cells]
        if not valid_ids:
            return pd.DataFrame(
                {"date": pd.Series(dtype="datetime64[ns]"),
                 "grid_id": pd.Series(dtype=int),
                 var_name: pd.Series(dtype=float)}
            )

        data = src.read(1)
        rows = [i // ncols for i in valid_ids]
        cols = [i % ncols for i in valid_ids]
        vals = [float(data[r, c]) for r, c in zip(rows, cols)]

    date = _parse_date_from_zip(zip_path)
    df = pd.DataFrame({
        "date": date,
        "grid_id": [int(i) for i in valid_ids],
        var_name: vals,
    })
    if nodata is not None:
        df.loc[df[var_name] == nodata, var_name] = np.nan
    df.loc[df[var_name] <= -9999, var_name] = np.nan
    df = df.dropna(subset=[var_name])
    return df


@register_reader("prism_part1")
class PRISMPart1ExposureSource:
    """Read raw PRISM zip archives and extract daily grid-cell values.

    For each requested variable and year, scans the PRISM data directory for
    zip files, extracts the contained GeoTIFF, and reads values at grid cells
    referenced by the C3 weight table.

    Returns a wide DataFrame with columns:
        grid_id (int64), date (datetime64[ns]), plus one column per variable.
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame:
        from spacescans.io.readers import read_table

        # Load weights to determine which grid cells to extract
        weights = read_table(self.config.source.file)
        keep_ids = sorted(weights["grid_id"].dropna().astype(int).unique().tolist())

        # Resolve paths
        prism_root = str(self.config.exposure.file)
        value_cols = list(self.config.exposure.value_cols)
        requested_vars = [v for v in value_cols if v in _PRISM_VARS]
        if not requested_vars:
            requested_vars = _PRISM_VARS

        # Cache directory: alongside the output
        cache_dir = os.path.join(
            os.path.dirname(self.config.output.path), "prism_cache"
        )
        # Also check v1 cache
        v1_cache = "output/python/270m/PRISM/C4/part1/prism_cache"
        if os.path.isdir(v1_cache):
            cache_dir = v1_cache

        os.makedirs(cache_dir, exist_ok=True)
        requested_years = years if years else [2013]

        print(f"[prism_part1] vars={requested_vars}, years={requested_years}, "
              f"grid_cells={len(keep_ids)}")

        # Collect per-variable DataFrames
        var_frames: dict[str, list[pd.DataFrame]] = {v: [] for v in requested_vars}

        for var in requested_vars:
            for yr in requested_years:
                zips = _list_var_year_zips(prism_root, var, yr)
                if not zips:
                    print(f"  [prism_part1] No zips for {var}/{yr}")
                    continue

                print(f"  [prism_part1] {var}/{yr}: {len(zips)} files")
                for idx, z in enumerate(zips, 1):
                    if idx % 50 == 0 or idx == len(zips):
                        print(f"    {idx}/{len(zips)}")
                    df = _read_one_daily_tif(z, var, keep_ids, cache_dir)
                    if not df.empty:
                        var_frames[var].append(df)

        # Build wide table: outer-join all variables on (grid_id, date)
        var_dfs: list[pd.DataFrame] = []
        for var in requested_vars:
            parts = var_frames[var]
            if not parts:
                continue
            vdf = pd.concat(parts, ignore_index=True)
            var_dfs.append(vdf.set_index(["grid_id", "date"]))

        if not var_dfs:
            raise RuntimeError(
                f"No PRISM data loaded for vars={requested_vars}, years={requested_years}"
            )

        wide = var_dfs[0]
        for other in var_dfs[1:]:
            wide = wide.join(other, how="outer")

        wide = wide.reset_index()
        wide["grid_id"] = wide["grid_id"].astype("int64")
        wide["date"] = pd.to_datetime(wide["date"])
        return wide
