# common_v2/models/protocols.py
"""Protocol interfaces — role-based, narrow, duck-typed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pandas as pd

if TYPE_CHECKING:
    # Only needed for the GeometrySource type annotation, which is a lazy string
    # under `from __future__ import annotations`. Importing at runtime would pull
    # geopandas into the base install (it belongs to the [geo] extra).
    import geopandas as gpd

from .specs import (
    DateRangeJoinSpec, DurationWeightedSpec, JoinSpec, SimpleAggSpec,
    TemporalAggSpec, WeightedAggSpec,
)


@runtime_checkable
class PatientSource(Protocol):
    def load_patients(self) -> pd.DataFrame: ...


@runtime_checkable
class WeightSource(Protocol):
    def load_weights(self) -> pd.DataFrame: ...


@runtime_checkable
class ExposureSource(Protocol):
    def load_exposure(self, *, years: list[int] | None = None) -> pd.DataFrame: ...


@runtime_checkable
class GeometrySource(Protocol):
    def load_geometries(self, *, year: int | None = None) -> gpd.GeoDataFrame: ...


@runtime_checkable
class AggregationEngine(Protocol):
    def join(self, left: pd.DataFrame, right: pd.DataFrame, spec: JoinSpec) -> pd.DataFrame: ...
    def weighted_aggregate(self, data: pd.DataFrame, spec: WeightedAggSpec) -> pd.DataFrame: ...
    def temporal_aggregate(self, data: pd.DataFrame, spec: TemporalAggSpec) -> pd.DataFrame: ...
    def date_range_join(self, exposure: pd.DataFrame, episodes: pd.DataFrame, spec: DateRangeJoinSpec) -> pd.DataFrame: ...
    def duration_weighted(self, values: pd.DataFrame, episodes: pd.DataFrame, spec: DurationWeightedSpec) -> pd.DataFrame: ...
    def simple_aggregate(self, data: pd.DataFrame, spec: SimpleAggSpec) -> pd.DataFrame: ...
