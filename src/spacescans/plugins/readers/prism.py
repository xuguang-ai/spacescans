"""PRISM Part3 reader — loads Part1/Part2 pkl files and returns wide grid-daily table."""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import re
from pathlib import Path

import pandas as pd

from spacescans.pipeline.registry import register_reader

# Pattern: {var}_{year}.pkl
_PKL_PATTERN = re.compile(r"^(?P<var>.+)_(?P<year>\d{4})\.pkl$")


def _discover_pkl_files(directories: list[Path]) -> dict[tuple[str, int], Path]:
    """Scan directories and return a mapping of (var, year) -> Path.

    Later directories take precedence over earlier ones (so part2 overrides part1
    for any overlapping variable/year combinations).
    """
    found: dict[tuple[str, int], Path] = {}
    for d in directories:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.pkl")):
            m = _PKL_PATTERN.match(p.name)
            if m:
                key = (m.group("var"), int(m.group("year")))
                found[key] = p
    return found


@register_reader("prism")
class PRISMExposureSource:
    """Load PRISM Part1/Part2 per-variable-per-year pkl files.

    Expected pkl schema: [date (datetime64), grid_id (int64), <var> (float64)]

    The reader concatenates all requested variable/year files and pivots to a
    wide table [grid_id, date, var1, var2, ...] for consumption by gridded_linkage.
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame:
        """Load all PRISM grid-daily values for the requested years.

        Parameters
        ----------
        years:
            Calendar years to load.  If None, all years found on disk are loaded.

        Returns
        -------
        pd.DataFrame
            Columns: grid_id (int64), date (datetime64[ns]), plus one column per
            variable (e.g. ppt, tmax, tmin, …).
        """
        value_cols = list(self.config.exposure.value_cols)

        # Resolve part1 and part2 directories
        # config.exposure.file points to part2 dir (or a base path); we infer part1
        part2_dir = Path(self.config.exposure.file)
        # Derive part1 by replacing "part2" with "part1" in the path
        part1_dir_str = str(part2_dir).replace("part2", "part1")
        part1_dir = Path(part1_dir_str)

        # Additional legacy fallbacks: try output/Python (capital P) variants
        legacy_dirs: list[Path] = []
        for base in (part1_dir, part2_dir):
            legacy = Path(str(base).replace("output/python", "output/Python"))
            if legacy != base:
                legacy_dirs.append(legacy)

        # part1 first, then part2 (part2 overrides part1 on key conflicts)
        search_dirs = [part1_dir, part2_dir] + legacy_dirs
        all_pkls = _discover_pkl_files(search_dirs)

        if not all_pkls:
            raise FileNotFoundError(
                f"No PRISM pkl files found in: {[str(d) for d in search_dirs]}"
            )

        # Filter to requested variables and years
        requested_years = set(years) if years else None
        frames_by_var: dict[str, list[pd.DataFrame]] = {v: [] for v in value_cols}

        for (var, year), path in sorted(all_pkls.items()):
            if var not in frames_by_var:
                continue
            if requested_years is not None and year not in requested_years:
                continue
            df = pd.read_pickle(str(path))
            df["date"] = pd.to_datetime(df["date"])
            df["grid_id"] = df["grid_id"].astype(int)
            # Keep only [grid_id, date, var]
            df = df[["grid_id", "date", var]].copy()
            frames_by_var[var].append(df)

        # Concatenate each variable across years into a single per-var frame
        var_dfs: list[pd.DataFrame] = []
        for var in value_cols:
            parts = frames_by_var[var]
            if not parts:
                continue
            var_df = pd.concat(parts, ignore_index=True)
            var_df = var_df.rename(columns={var: var})  # explicit (no-op, clarity)
            var_dfs.append(var_df.set_index(["grid_id", "date"]))

        if not var_dfs:
            raise RuntimeError(
                f"No PRISM data loaded for variables {value_cols} / years {years}"
            )

        # Outer-join all variables on (grid_id, date) to produce the wide table
        wide = var_dfs[0]
        for other in var_dfs[1:]:
            wide = wide.join(other, how="outer")

        wide = wide.reset_index()
        # Cast types to be explicit
        wide["grid_id"] = wide["grid_id"].astype("int64")
        wide["date"] = pd.to_datetime(wide["date"])

        return wide
