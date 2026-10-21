import pandas as pd
import pytest

from datalab.config import load_config
from datalab.sample_data import generate_sample_data


@pytest.fixture
def project(tmp_path):
    """A throwaway project folder (inside pytest's temp dir) with a small synthetic dataset."""
    (tmp_path / "data").mkdir()
    generate_sample_data(n_rows=150, seed=1).to_csv(tmp_path / "data" / "sample.csv", index=False)
    cfg = load_config(base_dir=tmp_path)  # no config.json there -> defaults
    cfg["analysis"].update({
        "required_columns": ["order_id", "order_date", "region", "category", "units_sold", "unit_price", "revenue"],
        "non_negative_columns": ["units_sold", "unit_price", "revenue"],
        "chart_dpi": 50,
    })
    return tmp_path, cfg


@pytest.fixture
def small_df():
    return pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "b": [10.0, 20.0, None, 40.0, 50.0],
        "cat": ["x", "y", None, "x", "y"],
    })
