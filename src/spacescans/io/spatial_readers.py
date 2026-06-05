# common_v2/io/spatial_readers.py
"""Spatial format reading — read only, no fix, no reproject."""

from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

from pathlib import Path

import geopandas as gpd
import numpy as np

from spacescans.models.raster_meta import RasterMeta


def read_vector(path: str | Path, *, layer: str | None = None) -> gpd.GeoDataFrame:
    """Read vector data (shp, gpkg, gdb, geojson)."""
    kwargs = {}
    if layer is not None:
        kwargs["layer"] = layer
    return gpd.read_file(str(path), **kwargs)


def read_raster_metadata(path: str | Path) -> RasterMeta:
    """Read raster metadata without loading pixel data."""
    import rasterio

    with rasterio.open(str(path)) as src:
        return RasterMeta(
            crs=str(src.crs) if src.crs else None,
            transform=tuple(src.transform)[:6],
            height=src.height,
            width=src.width,
            nodata=src.nodata,
            bounds=tuple(src.bounds),
        )


def read_raster_array(
    path: str | Path, *, band: int = 1,
) -> tuple[np.ndarray, RasterMeta]:
    """Read raster data as numpy array + metadata."""
    import rasterio

    with rasterio.open(str(path)) as src:
        arr = src.read(band).astype(np.float32)
        meta = RasterMeta(
            crs=str(src.crs) if src.crs else None,
            transform=tuple(src.transform)[:6],
            height=src.height,
            width=src.width,
            nodata=src.nodata,
            bounds=tuple(src.bounds),
        )
    return arr, meta


def read_hdf_array(
    path: str | Path, *, dataset: str | int = 0,
) -> tuple[np.ndarray, dict]:
    """Read HDF4/HDF5 dataset. Returns array + raw attributes dict."""
    from pyhdf.SD import SD, SDC

    hdf = SD(str(path), SDC.READ)
    ds_list = hdf.datasets()
    if isinstance(dataset, int):
        ds_name = list(ds_list.keys())[dataset]
    else:
        ds_name = dataset
    sds = hdf.select(ds_name)
    arr = sds[:].astype(np.float32)
    attrs = sds.attributes()
    sds.end()
    hdf.end()
    return arr, attrs


def read_netcdf_variable(path: str | Path, *, variable: str):
    """Read a single variable from a NetCDF file."""
    import xarray as xr

    ds = xr.open_dataset(str(path))
    return ds[variable]
