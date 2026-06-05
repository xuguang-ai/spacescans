"""[hdf4] gating: TEMIS reader needs pyhdf."""
import importlib
import pytest


@pytest.mark.hdf4
def test_temis_reader_imports_with_hdf4_extra():
    mod = importlib.import_module("spacescans.plugins.readers.temis")
    assert mod is not None
