"""[nc] gating: ACAG reader + linkage need xarray + netCDF4."""
import importlib
import pytest


@pytest.mark.nc
def test_acag_imports_with_nc_and_geo_extras():
    # Needs both [nc] (acag reader) and [geo] (acag_linkage). Marked only `nc` so the
    # geo-only CI job (which has no netCDF4) doesn't try to run it; the nc job installs
    # [nc,geo] together.
    importlib.import_module("spacescans.plugins.readers.acag")
    importlib.import_module("spacescans.linkage.acag_linkage")
