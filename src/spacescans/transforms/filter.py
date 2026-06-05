"""Attribute filtering — exact match or prefix match, with optional exclusion."""
from __future__ import annotations
import pandas as pd

def filter_features(df: pd.DataFrame, *, column: str, values: list | None = None, prefixes: list[str] | None = None, exclude: bool = False) -> pd.DataFrame:
    if values is not None:
        mask = df[column].isin(values)
    elif prefixes is not None:
        col_str = df[column].astype(str)
        mask = pd.Series(False, index=df.index)
        for prefix in prefixes:
            mask = mask | col_str.str.startswith(prefix)
    else:
        raise ValueError("Provide either 'values' or 'prefixes'")
    if exclude:
        mask = ~mask
    return df.loc[mask].reset_index(drop=True)
