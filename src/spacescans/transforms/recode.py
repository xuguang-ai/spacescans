"""Rule-based column recoding engine."""
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from spacescans.models.config import RecodeRule


def recode_columns(df: pd.DataFrame, rules: list[RecodeRule]) -> pd.DataFrame:
    result = df.copy()
    for rule in rules:
        result[rule.output_col] = _apply_rule(result, rule)
    return result


def _apply_rule(df: pd.DataFrame, rule: RecodeRule) -> pd.Series:
    output = pd.Series(rule.default, index=df.index)
    for cond in reversed(rule.conditions):
        mask = _eval_condition(df, cond.when)
        output = output.where(~mask, cond.then)
    return output


def _eval_condition(df: pd.DataFrame, when: dict[str, Any]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col, val in when.items():
        if isinstance(val, dict):
            for op, threshold in val.items():
                if op == "gte":
                    mask = mask & (df[col] >= threshold)
                elif op == "gt":
                    mask = mask & (df[col] > threshold)
                elif op == "lte":
                    mask = mask & (df[col] <= threshold)
                elif op == "lt":
                    mask = mask & (df[col] < threshold)
                elif op == "eq":
                    mask = mask & (df[col] == threshold)
                elif op == "ne":
                    mask = mask & (df[col] != threshold)
                else:
                    raise ValueError(f"Unknown operator: {op}")
        else:
            mask = mask & (df[col] == val)
    return mask
