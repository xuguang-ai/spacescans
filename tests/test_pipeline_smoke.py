"""init() runs and registers expected base patterns."""
import subprocess
import sys
import textwrap

import pytest

from spacescans.pipeline.registry import init, get_pattern


def test_init_succeeds_on_base_install():
    init()


def test_base_patterns_registered():
    init()
    for name in ("yearly_areal", "static_areal", "cbp_fallback", "faqsd_daily_areal",
                 "precomputed_areal", "precomputed_static"):
        assert callable(get_pattern(name)), f"{name} not registered"


def test_unknown_pattern_raises():
    init()
    with pytest.raises(KeyError):
        get_pattern("does_not_exist_pattern")


def test_base_modules_import_without_optional_extras():
    """Regression guard: base modules + registry.init() must work with ONLY base deps.

    The dev/CI [all] env has geopandas/rasterio/etc installed, which masks accidental
    module-top imports of optional packages in base code. We simulate a base-only
    interpreter in a subprocess by blocking those imports via a sys.meta_path finder,
    then import every base module and run registry.init(). Catches the class of bug
    where a [geo]-only package leaks into the base install path.
    """
    script = textwrap.dedent(
        """
        import sys
        from importlib.abc import MetaPathFinder

        _BLOCKED = {"geopandas", "rasterio", "shapely", "exactextract",
                    "pyreadr", "pyhdf", "xarray", "netCDF4"}

        class _Blocker(MetaPathFinder):
            def find_spec(self, name, path, target=None):
                if name.split(".")[0] in _BLOCKED:
                    raise ModuleNotFoundError(
                        f"No module named {name!r} (blocked for base-install test)")
                return None

        sys.meta_path.insert(0, _Blocker())

        # init() imports all base modules; optional modules are swallowed.
        from spacescans.pipeline.registry import init, get_pattern
        init()
        for name in ("yearly_areal", "static_areal", "cbp_fallback", "faqsd_daily_areal",
                     "precomputed_areal", "precomputed_static"):
            assert callable(get_pattern(name)), f"{name} not registered on base install"
        print("BASE_OK")
        """
    )
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert r.returncode == 0 and "BASE_OK" in r.stdout, (
        f"base-install import failed:\nstdout={r.stdout}\nstderr={r.stderr}"
    )
