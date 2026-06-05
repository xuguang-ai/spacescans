"""Object-level spatial fixes — CRS assignment, nodata repair."""
from __future__ import annotations

import numpy as np

from spacescans.models.raster_meta import RasterMeta


def assign_crs(
    array: np.ndarray,
    meta: RasterMeta,
    *,
    crs: str,
    extent: tuple[float, float, float, float] | None = None,
) -> RasterMeta:
    """Assign CRS and optionally compute transform from extent.

    Args:
        array: The raster data (used for shape validation).
        meta: Existing raster metadata.
        crs: Target CRS string (e.g., 'EPSG:4326').
        extent: Optional (left, right, bottom, top) bounds.
                Will be reordered to bounds (left, bottom, right, top)
                and used to compute affine transform.

    Returns:
        New RasterMeta with assigned CRS, bounds, and transform.
    """
    if extent is not None:
        left, right, bottom, top = extent
        bounds = (left, bottom, right, top)
        pixel_w = (right - left) / meta.width
        pixel_h = (top - bottom) / meta.height
        transform = (pixel_w, 0.0, left, 0.0, -pixel_h, top)
    else:
        bounds = meta.bounds
        transform = meta.transform

    return RasterMeta(
        crs=crs,
        transform=transform,
        height=meta.height,
        width=meta.width,
        nodata=meta.nodata,
        bounds=bounds,
    )


def repair_nodata(
    array: np.ndarray,
    meta: RasterMeta,
    *,
    nodata_value: float,
) -> tuple[np.ndarray, RasterMeta]:
    """Replace specified nodata value with NaN and update metadata.

    Args:
        array: The raster data.
        meta: Existing raster metadata.
        nodata_value: Value to treat as nodata (will be replaced with NaN).

    Returns:
        Tuple of (new_array, new_meta) with nodata fixed.
    """
    new_arr = array.copy().astype(np.float32)
    new_arr[new_arr == nodata_value] = np.nan
    new_meta = RasterMeta(
        crs=meta.crs,
        transform=meta.transform,
        height=meta.height,
        width=meta.width,
        nodata=nodata_value,
        bounds=meta.bounds,
    )
    return new_arr, new_meta
