"""Patient buffer construction and CRS management."""
from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import geopandas as gpd
import pandas as pd

AEA_CRS = (
    "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 "
    "+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs +type=crs"
)


def build_buffers(
    points: gpd.GeoDataFrame,
    *,
    buffer_m: float = 270,
    buffer_resolution: int = 100,
    target_crs: str = AEA_CRS,
) -> gpd.GeoDataFrame:
    projected = points.to_crs(target_crs)
    projected["geometry"] = projected.geometry.buffer(buffer_m, resolution=buffer_resolution)
    return projected


def reproject(gdf: gpd.GeoDataFrame, *, target_crs: str) -> gpd.GeoDataFrame:
    return gdf.to_crs(target_crs)


def assign_by_intersection(
    points: gpd.GeoDataFrame,
    polygons: gpd.GeoDataFrame,
    *,
    attribute_col: str,
) -> pd.Series:
    joined = gpd.sjoin(
        points,
        polygons[[attribute_col, "geometry"]],
        how="left",
        predicate="intersects",
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined[attribute_col].reindex(points.index)
