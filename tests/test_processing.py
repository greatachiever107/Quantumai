import hashlib

import numpy as np
import pandas as pd
import pytest

from datalab import processing as proc


# ---------------------------------------------------------------- statistics
def test_summary_statistics_known_values():
    df = pd.DataFrame({"v": [1, 2, 3, 4, 5]})
    row = proc.summary_statistics(df, ["v"], [50]).loc["v"]
    assert row["count"] == 5
    assert row["mean"] == 3
    assert row["median"] == 3
    assert row["min"] == 1 and row["max"] == 5
    assert row["std"] == pytest.approx(np.std([1, 2, 3, 4, 5], ddof=1))
    assert row["p50"] == 3


def test_group_statistics():
    df = pd.DataFrame({"g": ["a", "a", "b"], "v": [1.0, 3.0, 10.0]})
    out = proc.group_statistics(df, "g", "v")
    assert out.loc["a", "mean"] == 2.0
    assert out.loc["b", "count"] == 1


def test_correlation_perfect_and_not_applicable():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8], "const": [1, 1, 1, 1]})
    corr = proc.correlation_matrix(df, ["x", "y", "const"])
    assert corr.loc["x", "y"] == pytest.approx(1.0)
    assert "const" not in corr.columns  # constant column is skipped
    assert proc.correlation_matrix(df, ["x"]) is None


def test_outliers_reported_not_removed():
    df = pd.DataFrame({"v": [10, 11, 12, 11, 10, 12, 11, 500]})
    before = df.copy()
    result = proc.detect_outliers(df, ["v"])
    assert result["v"]["count"] == 1
    assert result["v"]["example_row_indexes"] == [7]
    pd.testing.assert_frame_equal(df, before)  # data untouched


# ------------------------------------------------------------ missing values
def test_missing_values_median_strategy(small_df):
    cleaned, actions = proc.clean_data(small_df, missing_numeric_strategy="median")
    assert cleaned["b"].isna().sum() == 0
    assert cleaned.loc[2, "b"] == 30.0  # median of 10,20,40,50
    assert cleaned.loc[2, "cat"] == "Unknown"
    assert actions["numeric_missing_filled_with_median"] == {"b": 1}


def test_missing_values_keep_and_drop(small_df):
    kept, _ = proc.clean_data(small_df, missing_numeric_strategy="keep")
    assert kept["b"].isna().sum() == 1
    dropped, actions = proc.clean_data(small_df, missing_numeric_strategy="drop")
    assert len(dropped) == 4 and actions["rows_dropped_for_missing_numeric"] == 1


def test_clean_does_not_modify_input(small_df):
    original = small_df.copy()
    proc.clean_data(small_df)
    pd.testing.assert_frame_equal(small_df, original)


def test_invalid_strategy_rejected(small_df):
    with pytest.raises(ValueError):
        proc.clean_data(small_df, missing_numeric_strategy="guess")


# ---------------------------------------------------------------- duplicates
def test_duplicate_detection_and_removal():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    assert proc.validate_data(df)["duplicate_rows"] == 1
    cleaned, actions = proc.clean_data(df)
    assert len(cleaned) == 2 and actions["duplicates_removed"] == 1


def test_invalid_numeric_and_negative_detection():
    df = pd.DataFrame({"price": ["1", "2", "abc", "4", "5", "6", "7", "8", "9", "10"], "qty": [1, -2, 3, 4, 5, 6, 7, 8, 9, 10]})
    findings = proc.validate_data(df, non_negative_columns=["qty", "price"])
    assert findings["invalid_numeric_values"] == {"price": 1}
    assert findings["negative_values"] == {"qty": 1}
    cleaned, _ = proc.clean_data(df, non_negative_columns=["qty"], missing_numeric_strategy="keep")
    assert cleaned["price"].isna().sum() == 1 and cleaned["qty"].isna().sum() == 1


def test_missing_required_columns_reported():
    findings = proc.validate_data(pd.DataFrame({"a": [1]}), required_columns=["a", "zzz"])
    assert findings["missing_required_columns"] == ["zzz"]


def test_monthly_trend_needs_enough_data():
    df = pd.DataFrame({"d": ["2025-01-05", "2025-02-05"], "v": [1, 2]})
    assert proc.monthly_trend(df, "d", "v") is None
    df = pd.DataFrame({"d": ["2025-01-05", "2025-02-05", "2025-03-05"], "v": [10, 20, 30]})
    trend = proc.monthly_trend(df, "d", "v")
    assert trend["direction"] == "higher" and trend["months_covered"] == 3


# ------------------------------------------------------------- invalid files
def test_load_missing_file(tmp_path):
    with pytest.raises(proc.DataLoadError):
        proc.load_csv(tmp_path / "nope.csv")


def test_load_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("")
    with pytest.raises(proc.DataLoadError):
        proc.load_csv(p)


def test_load_header_only_file(tmp_path):
    p = tmp_path / "header.csv"
    p.write_text("a,b,c\n")
    with pytest.raises(proc.DataLoadError):
        proc.load_csv(p)


def test_load_binary_garbage(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_bytes(bytes(range(256)) * 20)
    with pytest.raises(proc.DataLoadError):
        proc.load_csv(p)


def test_load_too_large(tmp_path):
    p = tmp_path / "big.csv"
    p.write_text("a\n1\n")
    with pytest.raises(proc.DataLoadError):
        proc.load_csv(p, max_file_mb=0.000001)


def test_load_valid_file_reads_in_chunks(tmp_path):
    p = tmp_path / "ok.csv"
    pd.DataFrame({"a": range(25)}).to_csv(p, index=False)
    assert len(proc.load_csv(p, chunk_rows=10)) == 25
