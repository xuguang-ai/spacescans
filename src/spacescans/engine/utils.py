"""Engine utilities — weight normalization and validation."""
from __future__ import annotations
import pandas as pd

def normalize_weights(data: pd.DataFrame, *, group_by: str, weight_col: str = "weight") -> pd.DataFrame:
    df = data.copy()
    totals = df.groupby(group_by)[weight_col].transform("sum")
    df[weight_col] = df[weight_col] / totals
    return df

def validate_group_weight_sums(data: pd.DataFrame, *, group_by: str, weight_col: str = "weight", tol: float = 1e-6) -> float:
    sums = data.groupby(group_by)[weight_col].sum()
    deviations = (sums - 1.0).abs()
    max_dev = deviations.max()
    if pd.isna(max_dev):
        max_dev = 0.0
    assert max_dev < tol, f"Weight sums deviate by {max_dev:.8f} (tol={tol})"
    return float(max_dev)
