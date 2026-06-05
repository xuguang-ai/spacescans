"""Nearest distance computation — point to line/polygon features."""
from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import geopandas as gpd
import numpy as np
import pandas as pd


def compute_nearest_distance(
    points: gpd.GeoDataFrame,
    features: gpd.GeoDataFrame,
    *,
    category_col: str | None = None,
) -> pd.DataFrame:
    if category_col is not None:
        parts = []
        for cat, group in features.groupby(category_col):
            dists = _nearest_distances(points, group)
            df = pd.DataFrame({"geoid": points["geoid"].values, "category": cat, "distance_m": dists})
            parts.append(df)
        return pd.concat(parts, ignore_index=True)
    else:
        dists = _nearest_distances(points, features)
        return pd.DataFrame({"geoid": points["geoid"].values, "distance_m": dists})


def tile_and_compute(
    points: gpd.GeoDataFrame,
    features: gpd.GeoDataFrame,
    *,
    tile_size_deg: float = 0.5,
    category_col: str | None = None,
) -> pd.DataFrame:
    """Spatially tiled nearest-distance for large datasets."""
    pts_4326 = points.to_crs("EPSG:4326") if str(points.crs) != "EPSG:4326" else points
    feats_4326 = features.to_crs("EPSG:4326") if str(features.crs) != "EPSG:4326" else features
    bounds = pts_4326.total_bounds
    x_tiles = np.arange(bounds[0], bounds[2] + tile_size_deg, tile_size_deg)
    y_tiles = np.arange(bounds[1], bounds[3] + tile_size_deg, tile_size_deg)
    results = []
    for x in x_tiles[:-1]:
        for y in y_tiles[:-1]:
            tile_mask = (
                (pts_4326.geometry.x >= x) & (pts_4326.geometry.x < x + tile_size_deg) &
                (pts_4326.geometry.y >= y) & (pts_4326.geometry.y < y + tile_size_deg)
            )
            tile_pts = pts_4326[tile_mask]
            if tile_pts.empty:
                continue
            from shapely.geometry import box
            tile_box = box(x - tile_size_deg, y - tile_size_deg, x + 2 * tile_size_deg, y + 2 * tile_size_deg)
            tile_feats = feats_4326[feats_4326.intersects(tile_box)]
            if tile_feats.empty:
                continue
            local_crs = points.crs
            tile_pts_m = tile_pts.to_crs(local_crs)
            tile_feats_m = tile_feats.to_crs(local_crs)
            result = compute_nearest_distance(tile_pts_m, tile_feats_m, category_col=category_col)
            results.append(result)
    if not results:
        cols = ["geoid", "distance_m"] + (["category"] if category_col else [])
        return pd.DataFrame(columns=cols)
    return pd.concat(results, ignore_index=True)


def _nearest_distances(points: gpd.GeoDataFrame, features: gpd.GeoDataFrame) -> np.ndarray:
    if features.empty:
        return np.full(len(points), np.nan)
    union = features.geometry.union_all()
    return np.array([pt.distance(union) for pt in points.geometry])
