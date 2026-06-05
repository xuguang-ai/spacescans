"""Base io: parquet/csv reading/writing works in base install (no extras)."""
import pandas as pd
from spacescans.io.readers import read_table
from spacescans.io.writers import write_table


def test_read_write_parquet_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    p = tmp_path / "x.parquet"
    df.to_parquet(p)
    loaded = read_table(p)
    assert loaded.equals(df)


def test_write_table_parquet(tmp_path):
    df = pd.DataFrame({"x": [1.0, 2.0]})
    out = tmp_path / "out.parquet"
    write_table(df, out)
    assert out.exists()
    assert pd.read_parquet(out).equals(df)
