"""Lightweight metadata container for raster data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RasterMeta:
    """Immutable raster metadata. CRS/transform/bounds may be None for raw HDF4 etc."""

    crs: str | None
    transform: tuple | None  # Affine 6-tuple (a, b, c, d, e, f)
    height: int
    width: int
    nodata: float | None
    bounds: tuple[float, float, float, float] | None  # (left, bottom, right, top)
