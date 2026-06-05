"""Noise TIF reader — reads 3 static rasters, extracts values at weighted grid cells."""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from spacescans.pipeline.registry import register_reader

# Canonical TIF filenames relative to the directory of the primary exposure file
_TIF_NAMES = {
    "l50dba_exi": "CONUS_L50dBA_sumDay_exi.tif",
    "l50dba_imp": "CONUS_sumDay_L50dBA_imp.tif",
    "l50dba_nat": "CONUS_sumDay_L50dBA_nat.tif",
}


def _grids_match(a, b, tol: float = 1e-9) -> bool:
    """Return True when two open rasterio datasets share the same spatial grid."""
    if a.crs != b.crs:
        return False
    if a.height != b.height or a.width != b.width:
        return False
    if any(abs(x - y) > tol for x, y in zip(a.res, b.res)):
        return False
    return not any(
        abs(x - y) > tol
        for x, y in zip(
            [a.bounds.left, a.bounds.right, a.bounds.bottom, a.bounds.top],
            [b.bounds.left, b.bounds.right, b.bounds.bottom, b.bounds.top],
        )
    )


@register_reader("noise")
class NoiseExposureSource:
    """Read the three Noise TIF rasters and return grid-cell-level exposure values.

    The returned DataFrame has columns [grid_id, l50dba_exi, l50dba_imp, l50dba_nat]
    where grid_id = row * raster_width + col.  Only grid cells present in the C3
    weights table are extracted (driven by config.source.file).
    """

    def __init__(self, config):
        self.config = config

    def load_exposure(self, *, years=None) -> pd.DataFrame:
        """Extract noise values at all grid_ids referenced by the weights table.

        Parameters
        ----------
        years:
            Ignored — Noise is a static dataset with no temporal dimension.

        Returns
        -------
        pd.DataFrame
            Columns: grid_id (int64), l50dba_exi (float64),
            l50dba_imp (float64), l50dba_nat (float64).
        """
        from spacescans.io.readers import read_table

        # Load weights to discover which grid cells we need
        weights = read_table(self.config.source.file)
        if "value" in weights.columns and "weight" not in weights.columns:
            weights = weights.rename(columns={"value": "weight"})
        keep_ids = sorted(weights["grid_id"].dropna().astype(int).unique())

        # Resolve TIF directory from the primary exposure file path
        primary_tif = Path(self.config.exposure.file)
        tif_dir = primary_tif.parent if not primary_tif.is_dir() else primary_tif

        tif_paths = {col: tif_dir / fname for col, fname in _TIF_NAMES.items()}
        for col, p in tif_paths.items():
            if not p.exists():
                raise FileNotFoundError(f"Noise TIF not found: {p}")

        # Open all three rasters and validate they share the same grid
        with (
            rasterio.open(str(tif_paths["l50dba_exi"])) as r_exi,
            rasterio.open(str(tif_paths["l50dba_imp"])) as r_imp,
            rasterio.open(str(tif_paths["l50dba_nat"])) as r_nat,
        ):
            if not (_grids_match(r_exi, r_imp) and _grids_match(r_exi, r_nat)):
                raise ValueError("Noise rasters do not share the same spatial grid.")

            n_cells = r_exi.width * r_exi.height
            ncols = r_exi.width
            nodata = r_exi.nodata

            valid_ids = [i for i in keep_ids if 0 <= i < n_cells]
            rows_idx = [i // ncols for i in valid_ids]
            cols_idx = [i % ncols for i in valid_ids]

            arr_exi = r_exi.read(1)
            arr_imp = r_imp.read(1)
            arr_nat = r_nat.read(1)

        vals_exi = [float(arr_exi[r, c]) for r, c in zip(rows_idx, cols_idx)]
        vals_imp = [float(arr_imp[r, c]) for r, c in zip(rows_idx, cols_idx)]
        vals_nat = [float(arr_nat[r, c]) for r, c in zip(rows_idx, cols_idx)]

        df = pd.DataFrame(
            {
                "grid_id": [int(i) for i in valid_ids],
                "l50dba_exi": vals_exi,
                "l50dba_imp": vals_imp,
                "l50dba_nat": vals_nat,
            }
        )

        # Replace nodata sentinel with NaN
        if nodata is not None:
            for col in ("l50dba_exi", "l50dba_imp", "l50dba_nat"):
                df.loc[df[col] == nodata, col] = np.nan

        return df
