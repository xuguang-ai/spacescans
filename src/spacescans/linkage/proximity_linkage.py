# common_v2/linkage/proximity_linkage.py
from __future__ import annotations

from spacescans._extras import require
require("geo", "geopandas", "rasterio", "shapely", "exactextract")

from pathlib import Path
import geopandas as gpd
import pandas as pd
from spacescans.geometry.proximity import tile_and_compute
from spacescans.io.readers import read_table
from spacescans.io.spatial_readers import read_vector
from spacescans.io.writers import write_table
from spacescans.linkage.helpers import apply_transforms, load_patients, prepare_episodes
from spacescans.models.config import DatasetConfig
from spacescans.models.protocols import AggregationEngine
from spacescans.models.specs import DurationWeightedSpec
from spacescans.pipeline.registry import register_pattern


@register_pattern("proximity")
def run_proximity(config: DatasetConfig, engine: AggregationEngine) -> Path:
    patients = load_patients(config)
    patient_points = gpd.GeoDataFrame(
        patients,
        geometry=gpd.points_from_xy(
            patients[config.buffer.long_col],
            patients[config.buffer.lat_col],
        ),
        crs="EPSG:4326",
    ).to_crs(config.buffer.aea_crs)
    temporal_mode = config.time.temporal_mode if config.time else "static"
    periods = config.time.years if (config.time and temporal_mode == "yearly") else [None]
    category_col = config.source.category_col
    all_distances = []
    for period in periods:
        features = read_vector(config.source.file, layer=config.source.layer)
        features = features.to_crs(config.buffer.aea_crs)
        features = apply_transforms(features, config.transforms, target="source")
        distances = tile_and_compute(patient_points, features, category_col=category_col)
        if period is not None:
            distances["period_id"] = period
        all_distances.append(distances)
    distance_table = pd.concat(all_distances, ignore_index=True)
    episodes = prepare_episodes(patients)
    result = engine.duration_weighted(
        distance_table,
        episodes,
        DurationWeightedSpec(value_cols=["distance_m"]),
    )
    return write_table(result, config.output.path)
