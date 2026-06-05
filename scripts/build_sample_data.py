# scripts/build_sample_data.py
"""Generate tiny sample data (< 5 MB) for spacescans quickstart.

Run once during development:
    python scripts/build_sample_data.py

Outputs:
    src/spacescans/resources/data/sample_patients.parquet  (10 synthetic patients)
    src/spacescans/resources/data/sample_counties.shp + sidecars (Delaware, ~3 counties)
    src/spacescans/resources/data/sample_zcta5.shp + sidecars (Delaware ZCTAs)
"""
from __future__ import annotations
import random
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point

OUT = Path(__file__).parent.parent / "src" / "spacescans" / "resources" / "data"
OUT.mkdir(parents=True, exist_ok=True)

# --- 10 synthetic patients ---
random.seed(42)
np.random.seed(42)
# Delaware bounding box (approx): lon -75.78 to -75.05, lat 38.45 to 39.84
n = 10
df = pd.DataFrame({
    "PATID": [f"P{i:04d}" for i in range(n)],
    "long": np.random.uniform(-75.55, -75.15, n),  # within Sussex lon [-75.6, -75.1]
    "lat":  np.random.uniform(38.55, 38.95, n),    # within Sussex lat [38.5, 39.0]
    "start": pd.to_datetime("2013-01-01"),
    "end": pd.to_datetime("2019-12-31"),
    "bg_geoid": ["100010001001"] * n,  # placeholder; tied to a sample county
})
df.to_parquet(OUT / "sample_patients.parquet")
print(f"wrote {OUT / 'sample_patients.parquet'}  ({len(df)} patients)")

# --- 3 synthetic county polygons (rough rectangles in DE area) ---
counties = gpd.GeoDataFrame({
    "GEOID10": ["10001", "10003", "10005"],
    "NAME10": ["Kent", "New Castle", "Sussex"],
    "geometry": [
        Polygon([(-75.7, 39.0), (-75.4, 39.0), (-75.4, 39.3), (-75.7, 39.3)]),
        Polygon([(-75.7, 39.3), (-75.4, 39.3), (-75.4, 39.7), (-75.7, 39.7)]),
        Polygon([(-75.6, 38.5), (-75.1, 38.5), (-75.1, 39.0), (-75.6, 39.0)]),
    ],
}, crs="EPSG:4326")
counties.to_file(OUT / "sample_counties.shp", driver="ESRI Shapefile")
print(f"wrote {OUT / 'sample_counties.shp'}  ({len(counties)} polygons)")

# --- 6 synthetic ZCTA5 polygons (smaller, inside counties) ---
zctas = gpd.GeoDataFrame({
    "ZCTA5CE10": ["19901", "19902", "19720", "19711", "19958", "19966"],
    "geometry": [
        Polygon([(-75.65, 39.05), (-75.55, 39.05), (-75.55, 39.15), (-75.65, 39.15)]),
        Polygon([(-75.55, 39.05), (-75.45, 39.05), (-75.45, 39.15), (-75.55, 39.15)]),
        Polygon([(-75.65, 39.55), (-75.55, 39.55), (-75.55, 39.65), (-75.65, 39.65)]),
        Polygon([(-75.55, 39.55), (-75.45, 39.55), (-75.45, 39.65), (-75.55, 39.65)]),
        Polygon([(-75.45, 38.6), (-75.35, 38.6), (-75.35, 38.7), (-75.45, 38.7)]),
        Polygon([(-75.25, 38.7), (-75.15, 38.7), (-75.15, 38.8), (-75.25, 38.8)]),
    ],
}, crs="EPSG:4326")
zctas.to_file(OUT / "sample_zcta5.shp", driver="ESRI Shapefile")
print(f"wrote {OUT / 'sample_zcta5.shp'}  ({len(zctas)} polygons)")

# --- Size report ---
total = sum(p.stat().st_size for p in OUT.glob("*"))
print(f"\nTotal sample data: {total/1024:.1f} KB ({total/1024/1024:.2f} MB)")
assert total < 5 * 1024 * 1024, "Sample data exceeds 5 MB budget"
