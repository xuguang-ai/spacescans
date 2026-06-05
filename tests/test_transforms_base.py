"""filter/recode/derive should work without [geo]."""
import pandas as pd
from spacescans.transforms.filter import filter_features
from spacescans.transforms.recode import recode_columns
from spacescans.transforms.derive import derive_variable


def test_filter_basic():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": ["a", "b", "a", "c"]})
    out = filter_features(df, column="y", values=["a", "c"])
    assert len(out) == 3
