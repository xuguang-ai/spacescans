"""[geo]-gated modules should raise MissingExtraError if geopandas missing."""
import importlib
import pytest
from spacescans._extras import MissingExtraError


@pytest.mark.geo  # passes when [geo] installed
def test_can_import_boundary_overlap_when_geo_installed():
    mod = importlib.import_module("spacescans.linkage.boundary_overlap_fast_linkage")
    assert mod is not None


@pytest.mark.geo
def test_init_registers_boundary_overlap_fast():
    from spacescans.pipeline.registry import init, get_pattern
    init()
    fn = get_pattern("boundary_overlap_fast")
    assert callable(fn)
