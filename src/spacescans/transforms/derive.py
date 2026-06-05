"""Derived variable computation — simple expressions + registered formulas."""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

_FORMULA_REGISTRY: dict[str, Callable] = {}

def register_formula(name: str):
    def decorator(fn: Callable) -> Callable:
        if name in _FORMULA_REGISTRY:
            raise ValueError(f"Formula already registered: {name}")
        _FORMULA_REGISTRY[name] = fn
        return fn
    return decorator

def derive_variable(df: pd.DataFrame, *, formula: str | None = None, registry_key: str | None = None, output_col: str, params: dict | None = None) -> pd.DataFrame:
    result = df.copy()
    if registry_key is not None:
        if registry_key not in _FORMULA_REGISTRY:
            raise KeyError(f"Unknown formula: {registry_key}. Registered: {list(_FORMULA_REGISTRY)}")
        fn = _FORMULA_REGISTRY[registry_key]
        result[output_col] = fn(result, **(params or {}))
    elif formula is not None:
        result[output_col] = result.eval(formula)
    else:
        raise ValueError("Provide either 'formula' or 'registry_key'")
    return result

# --- Built-in formulas ---

@register_formula("zfill_str")
def _zfill_str(df: pd.DataFrame, *, source_col: str, width: int = 5) -> pd.Series:
    """Cast numeric column to zero-padded string, e.g. 4760 → '04760' (width=5)."""
    return df[source_col].astype("Int64").astype(str).str.zfill(width)


@register_formula("relative_humidity_from_vpd")
def _rh_from_vpd(df: pd.DataFrame, *, t_col: str, vpd_col: str) -> pd.Series:
    es = 6.1078 * 10 ** (7.5 * df[t_col] / (237.3 + df[t_col]))
    return (100 * (1 - df[vpd_col] / es)).clip(0, 100)

@register_formula("relative_humidity_from_dewpoint")
def _rh_from_dewpoint(df: pd.DataFrame, *, t_col: str, td_col: str) -> pd.Series:
    es_t = 6.1078 * 10 ** (7.5 * df[t_col] / (237.3 + df[t_col]))
    es_td = 6.1078 * 10 ** (7.5 * df[td_col] / (237.3 + df[td_col]))
    return (100 * es_td / es_t).clip(0, 100)

@register_formula("heat_index_nws")
def _heat_index_nws(df: pd.DataFrame, *, t_col: str, rh_col: str) -> pd.Series:
    """NWS Rothfusz heat index (Fahrenheit input/output)."""
    t_f = df[t_col] * 9 / 5 + 32
    rh = df[rh_col]
    hi = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    mask_high = ((hi + t_f) / 2) >= 80
    c1, c2, c3, c4 = -42.379, 2.04901523, 10.14333127, -0.22475541
    c5, c6, c7, c8, c9 = -0.00683783, -0.05481717, 0.00122874, 0.00085282, -0.00000199
    hi_r = (c1 + c2 * t_f + c3 * rh + c4 * t_f * rh + c5 * t_f**2 + c6 * rh**2 + c7 * t_f**2 * rh + c8 * t_f * rh**2 + c9 * t_f**2 * rh**2)
    adj1 = np.where((rh < 13) & (t_f >= 80) & (t_f <= 112), -((13 - rh) / 4) * np.sqrt((17 - np.abs(t_f - 95)) / 17), 0)
    adj2 = np.where((rh > 85) & (t_f >= 80) & (t_f <= 87), ((rh - 85) / 10) * ((87 - t_f) / 5), 0)
    hi_full = hi_r + adj1 + adj2
    result = np.where(mask_high, hi_full, hi)
    return pd.Series((result - 32) * 5 / 9, index=df.index)
