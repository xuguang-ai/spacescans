"""[rda] gating: reading .Rda needs pyreadr."""
import pytest
from spacescans._extras import MissingExtraError


@pytest.mark.rda
def test_read_rda_works_with_rda_extra(tmp_path):
    """Smoke: when pyreadr present, reader doesn't raise MissingExtraError on .Rda call."""
    import pyreadr
    import pandas as pd
    df = pd.DataFrame({"x": [1, 2, 3]})
    fake = tmp_path / "fake.Rda"
    pyreadr.write_rdata(str(fake), df, df_name="mydata")
    from spacescans.io.readers import read_table
    loaded = read_table(fake)
    assert loaded is not None
