"""TIGER road proximity (C3-equivalent): per-(geoid × year) distance to nearest
primary (S1100) and secondary (S1200) road from local TIGER zip cache.

Output schema matches v1 annual_proximity.pkl (renamed for v2):
    geoid (int), year (int), dist_pri (float), dist_sec (float), dist_prisec (float)

Caching: per-(state, county, year) filtered roads → parquet on disk. The cache
is cohort-independent — any future cohort that touches the same county/year
gets a 100% hit on this step. Heavy lifting (sjoin_nearest with patients) is
cohort-specific and not cached.
"""
from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from spacescans.io.spatial_readers import read_vector
from spacescans.io.writers import write_table
from spacescans.linkage.helpers import load_patients
from spacescans.models.config import DatasetConfig
from spacescans.models.protocols import AggregationEngine
from spacescans.pipeline.registry import register_pattern

_CRS_METRIC = 5070  # NAD83 / Conus Albers (meters)
_MTFCC_KEEP = ("S1100", "S1200")


def _filtered_roads_path(cache_dir: Path, statefp: str, countyfp: str, year: int) -> Path:
    return cache_dir / f"{year}" / f"{statefp}{countyfp}.parquet"


def _get_county_roads(
    statefp: str,
    countyfp: str,
    year: int,
    raw_dir: Path,
    cache_dir: Path | None,
) -> gpd.GeoDataFrame | None:
    """Return S1100/S1200 roads for one (county, year). Cached as parquet."""
    if cache_dir is not None:
        cache_path = _filtered_roads_path(cache_dir, statefp, countyfp, year)
        if cache_path.exists():
            try:
                return gpd.read_parquet(cache_path)
            except Exception:
                pass  # corrupt cache → fall through

    zip_path = raw_dir / f"tiger{year}_roads" / f"tl_{year}_{statefp}{countyfp}_roads.zip"
    if not zip_path.exists():
        return None
    try:
        roads = gpd.read_file(f"/vsizip/{zip_path}")
    except Exception:
        return None

    roads = roads[roads["MTFCC"].isin(_MTFCC_KEEP)][["MTFCC", "geometry"]].copy()

    if cache_dir is not None:
        cache_path = _filtered_roads_path(cache_dir, statefp, countyfp, year)
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            roads.to_parquet(cache_path)
        except Exception:
            pass  # don't fail run on cache write error

    return roads


def _nearest_dist(pts_m: gpd.GeoDataFrame, roads_m: gpd.GeoDataFrame) -> np.ndarray:
    """Distance from each point to nearest road feature (meters)."""
    if roads_m is None or len(roads_m) == 0:
        return np.full(len(pts_m), np.nan)
    joined = gpd.sjoin_nearest(
        pts_m[["geometry"]].reset_index(drop=True),
        roads_m[["geometry"]].reset_index(drop=True),
        how="left",
        distance_col="_dist",
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined["_dist"].values.astype(float)


@register_pattern("tiger_proximity")
def run_tiger_proximity(config: DatasetConfig, engine: AggregationEngine) -> Path:
    """Compute (geoid, year) × distance to nearest primary/secondary road."""
    t_total = time.perf_counter()

    patients = load_patients(config)
    pts = gpd.GeoDataFrame(
        patients,
        geometry=gpd.points_from_xy(
            patients[config.buffer.long_col],
            patients[config.buffer.lat_col],
        ),
        crs="EPSG:4326",
    )
    pts_m = pts.to_crs(_CRS_METRIC)

    # 1) Determine which counties contain patients (one-time spatial join)
    t = time.perf_counter()
    if not config.source.county_file:
        raise ValueError(
            "tiger_proximity requires `source.county_file` (path to a county boundary "
            "shapefile) to determine which counties contain patients. Set it in the YAML, "
            "e.g. source.county_file: ${SPACESCANS_DATA_DIR}/County/tl_2010_us_county10.shp"
        )
    counties = read_vector(config.source.county_file).to_crs("EPSG:4326")
    pt_county = gpd.sjoin(
        pts[["geoid", "geometry"]],
        counties[["STATEFP10", "COUNTYFP10", "geometry"]],
        how="left",
        predicate="within",
    )
    pt_county = pt_county.dropna(subset=["STATEFP10", "COUNTYFP10"])
    unique_counties = pt_county[["STATEFP10", "COUNTYFP10"]].drop_duplicates().values.tolist()
    print(
        f"[tiger_proximity] {len(patients)} patients across "
        f"{len(unique_counties)} unique counties",
        flush=True,
    )
    t_county_resolve = time.perf_counter() - t

    # 2) For each year, gather per-county roads (cache-aware) + sjoin_nearest
    raw_dir = Path(config.source.file)
    cache_dir = Path(config.source.road_cache_dir) if config.source.road_cache_dir else None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"[tiger_proximity] road cache: {cache_dir}", flush=True)

    years = config.time.years if config.time else list(range(2013, 2020))

    timings = {"county_resolve": t_county_resolve, "load_filter": 0.0, "sjoin_nearest": 0.0, "concat": 0.0}
    cache_hits = 0
    cache_misses = 0

    records = []
    for year_idx, y in enumerate(years):
        t_year = time.perf_counter()
        county_roads = []
        for statefp, countyfp in unique_counties:
            t = time.perf_counter()
            cache_path = _filtered_roads_path(cache_dir, statefp, countyfp, y) if cache_dir else None
            was_hit = bool(cache_path and cache_path.exists())
            roads = _get_county_roads(statefp, countyfp, y, raw_dir, cache_dir)
            timings["load_filter"] += time.perf_counter() - t
            if was_hit:
                cache_hits += 1
            else:
                cache_misses += 1
            if roads is not None and len(roads) > 0:
                county_roads.append(roads)

        if not county_roads:
            print(f"[tiger_proximity] year {y}: no roads found, skipping", flush=True)
            continue

        t = time.perf_counter()
        roads_y = gpd.GeoDataFrame(pd.concat(county_roads, ignore_index=True), crs=county_roads[0].crs)
        roads_m = roads_y.to_crs(_CRS_METRIC)
        primary = roads_m[roads_m["MTFCC"] == "S1100"]
        secondary = roads_m[roads_m["MTFCC"] == "S1200"]
        d_pri = _nearest_dist(pts_m, primary)
        d_sec = _nearest_dist(pts_m, secondary)
        timings["sjoin_nearest"] += time.perf_counter() - t

        records.append(pd.DataFrame({
            "geoid": patients[config.buffer.geoid_col].values,
            "year": y,
            "dist_primary_m": d_pri,
            "dist_secondary_m": d_sec,
        }))
        print(
            f"[tiger_proximity] year {y} done in {(time.perf_counter() - t_year)/60:.2f}m  "
            f"(roads pri={len(primary)}, sec={len(secondary)})",
            flush=True,
        )

    # 3) Combine + derive prisec column
    t = time.perf_counter()
    annual = pd.concat(records, ignore_index=True)
    annual["distance_prisec_m"] = annual[["dist_primary_m", "dist_secondary_m"]].min(axis=1)
    annual.loc[np.isinf(annual["distance_prisec_m"]), "distance_prisec_m"] = np.nan
    annual = annual.rename(columns={
        "dist_primary_m": "dist_pri",
        "dist_secondary_m": "dist_sec",
        "distance_prisec_m": "dist_prisec",
    })
    timings["concat"] = time.perf_counter() - t

    out = write_table(annual, config.output.path)

    grand_total = time.perf_counter() - t_total
    measured = sum(timings.values())
    other_s = max(0.0, grand_total - measured)

    print("[tiger_proximity] === SUMMARY ===", flush=True)
    for k in sorted(timings.keys(), key=lambda x: -timings[x]):
        pct = 100 * timings[k] / grand_total if grand_total > 0 else 0
        print(f"[tiger_proximity]   {k:16s} {timings[k]/60:6.2f}m ({pct:5.1f}%)", flush=True)
    other_pct = 100 * other_s / grand_total if grand_total > 0 else 0
    print(f"[tiger_proximity]   {'other':16s} {other_s/60:6.2f}m ({other_pct:5.1f}%)", flush=True)
    print(f"[tiger_proximity]   {'total':16s} {grand_total/60:6.2f}m", flush=True)
    if cache_dir is not None:
        total = cache_hits + cache_misses
        rate = 100 * cache_hits / total if total > 0 else 0
        print(
            f"[tiger_proximity]   road cache: hits={cache_hits} misses={cache_misses} "
            f"hit_rate={rate:.1f}%",
            flush=True,
        )

    return out
