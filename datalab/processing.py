"""Data processing engine (pandas + NumPy).

LEARNING NOTES
--------------
* A pandas ``DataFrame`` is a table: rows are records, columns are fields.
* A ``Series`` is one column. NaN ("not a number") marks a missing value.
* Statistics here are descriptive: they summarise the data you have. They do not prove
  why something happened.
* Nothing in this module modifies the original file or the DataFrame you pass in:
  ``clean_data`` works on a ``.copy()``.

Key formulas
  mean   = sum(values) / count
  median = middle value after sorting (robust to extreme values)
  std    = sample standard deviation (ddof=1): how spread out values are
  IQR    = Q3 - Q1 (middle 50% range); outlier if outside [Q1 - k*IQR, Q3 + k*IQR]
  corr   = Pearson correlation, from -1 (opposite) through 0 (none) to +1 (together)
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


class DataLoadError(Exception):
    """Raised when a CSV cannot be read safely."""


# --------------------------------------------------------------------------- loading
def load_csv(path: str | Path, max_file_mb: float = 200, chunk_rows: int = 50_000) -> pd.DataFrame:
    """Read a CSV file in chunks (memory-conscious) and return one DataFrame.

    Reading in chunks means pandas never parses the whole file in one go. Files above
    ``max_file_mb`` are refused so a huge file cannot exhaust 8 GB of RAM.
    """
    path = Path(path)
    if not path.is_file():
        raise DataLoadError(f"File not found: {path}")
    size = path.stat().st_size
    if size == 0:
        raise DataLoadError(f"File is empty: {path.name}")
    if size / 1_048_576 > max_file_mb:
        raise DataLoadError(f"{path.name} is larger than the {max_file_mb} MB limit")
    try:
        df = pd.concat(pd.read_csv(path, chunksize=chunk_rows), ignore_index=True)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"No data found in {path.name}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise DataLoadError(f"Could not parse {path.name}: {exc}") from exc
    if df.shape[1] == 0 or df.empty:
        raise DataLoadError(f"{path.name} contains no rows")
    return df


# ------------------------------------------------------------------------- detection
def find_numeric_columns(df: pd.DataFrame, exclude: Iterable[str] = (), threshold: float = 0.8) -> list[str]:
    """Columns that are numeric, or text columns where >= `threshold` of values look numeric.

    The second case matters: one bad entry such as "abc" makes pandas store a whole
    column as text, and we still want to find (and report) that column.
    """
    excluded = set(exclude)
    found: list[str] = []
    for col in df.columns:
        if col in excluded:
            continue
        series = df[col]
        if pd.api.types.is_bool_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        if pd.api.types.is_numeric_dtype(series):
            found.append(col)
            continue
        non_null = series.dropna()
        if len(non_null) == 0:
            continue
        if pd.to_numeric(non_null, errors="coerce").notna().mean() >= threshold:
            found.append(col)
    return found


# ------------------------------------------------------------------------ validation
def validate_data(
    df: pd.DataFrame,
    required_columns: Iterable[str] = (),
    non_negative_columns: Iterable[str] = (),
    exclude_numeric: Iterable[str] = (),
) -> dict:
    """Inspect a DataFrame and describe its quality problems. Never changes the data."""
    findings: dict = {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "missing_required_columns": [c for c in required_columns if c not in df.columns],
        "unnamed_or_blank_columns": [str(c) for c in df.columns if str(c).strip() == "" or str(c).startswith("Unnamed:")],
        "duplicate_column_names": sorted({str(c) for c in df.columns[df.columns.duplicated()]}),
        "missing_values": {str(c): int(n) for c, n in df.isna().sum().items() if n > 0},
        "duplicate_rows": int(df.duplicated().sum()),
        "invalid_numeric_values": {},
        "negative_values": {},
    }
    for col in find_numeric_columns(df, exclude=exclude_numeric):
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            bad = int(np.isinf(series.to_numpy(dtype=float, na_value=np.nan)).sum())
        else:
            non_null = series.dropna()
            bad = int(pd.to_numeric(non_null, errors="coerce").isna().sum())
        if bad:
            findings["invalid_numeric_values"][str(col)] = bad
    for col in non_negative_columns:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            n_neg = int((values < 0).sum())
            if n_neg:
                findings["negative_values"][str(col)] = n_neg

    issues: list[str] = []
    if findings["missing_required_columns"]:
        issues.append(f"Missing required columns: {', '.join(findings['missing_required_columns'])}")
    if findings["duplicate_rows"]:
        issues.append(f"{findings['duplicate_rows']} exact duplicate row(s)")
    for col, n in findings["missing_values"].items():
        issues.append(f"{n} missing value(s) in '{col}'")
    for col, n in findings["invalid_numeric_values"].items():
        issues.append(f"{n} invalid numeric value(s) in '{col}'")
    for col, n in findings["negative_values"].items():
        issues.append(f"{n} negative value(s) in '{col}' (expected >= 0)")
    findings["issues"] = issues
    return findings


# ---------------------------------------------------------------------------- cleaning
def clean_data(
    df: pd.DataFrame,
    numeric_exclude: Iterable[str] = (),
    non_negative_columns: Iterable[str] = (),
    date_column: str | None = None,
    missing_numeric_strategy: str = "median",
) -> tuple[pd.DataFrame, dict]:
    """Return (cleaned_copy, actions). The input DataFrame is never modified.

    Steps: trim names/text -> invalid numbers become NaN -> negatives in
    non-negative columns become NaN -> remove exact duplicate rows -> handle
    missing numeric values (median / drop rows / keep) -> missing text = "Unknown".
    """
    if missing_numeric_strategy not in ("median", "drop", "keep"):
        raise ValueError("missing_numeric_strategy must be 'median', 'drop' or 'keep'")
    out = df.copy()  # <- the safety step: work on a copy
    actions: dict = {"strategy": missing_numeric_strategy}
    out.columns = [str(c).strip() for c in out.columns]

    text_cols = [c for c in out.columns if not pd.api.types.is_numeric_dtype(out[c])]
    for col in text_cols:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            continue
        out[col] = out[col].astype("object").where(out[col].isna(), out[col].astype(str).str.strip())

    numeric_cols = find_numeric_columns(out, exclude=numeric_exclude)
    invalid_to_nan: dict[str, int] = {}
    for col in numeric_cols:
        before = out[col].isna().sum()
        out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        changed = int(out[col].isna().sum() - before)
        if changed:
            invalid_to_nan[col] = changed
    actions["invalid_numeric_set_to_missing"] = invalid_to_nan

    negatives: dict[str, int] = {}
    for col in non_negative_columns:
        if col in numeric_cols:
            mask = out[col] < 0
            if mask.any():
                negatives[col] = int(mask.sum())
                out.loc[mask, col] = np.nan
    actions["negative_set_to_missing"] = negatives

    n_before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    actions["duplicates_removed"] = int(n_before - len(out))

    if date_column and date_column in out.columns:
        parsed = pd.to_datetime(out[date_column], errors="coerce")
        actions["invalid_dates_set_to_missing"] = int(parsed.isna().sum() - out[date_column].isna().sum())
        out[date_column] = parsed

    missing_before = {c: int(out[c].isna().sum()) for c in numeric_cols if out[c].isna().any()}
    if missing_numeric_strategy == "median":
        filled = {}
        for col in missing_before:
            median = out[col].median()
            if pd.notna(median):
                out[col] = out[col].fillna(median)
                filled[col] = missing_before[col]
        actions["numeric_missing_filled_with_median"] = filled
    elif missing_numeric_strategy == "drop":
        n = len(out)
        out = out.dropna(subset=list(missing_before)).reset_index(drop=True)
        actions["rows_dropped_for_missing_numeric"] = int(n - len(out))
    else:
        actions["numeric_missing_left_as_is"] = missing_before

    categorical_filled: dict[str, int] = {}
    for col in out.columns:
        if col in numeric_cols or col == date_column or pd.api.types.is_datetime64_any_dtype(out[col]):
            continue
        n_missing = int(out[col].isna().sum())
        if n_missing:
            out[col] = out[col].fillna("Unknown")
            categorical_filled[col] = n_missing
    actions["text_missing_filled_with_unknown"] = categorical_filled
    actions["rows_after_cleaning"] = int(len(out))
    return out, actions


# -------------------------------------------------------------------------- statistics
def summary_statistics(df: pd.DataFrame, numeric_cols: list[str], percentiles: Iterable[float] = (5, 25, 50, 75, 95)) -> pd.DataFrame:
    """count, mean, median, min, max, std and percentiles for each numeric column."""
    rows = {}
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        row = {
            "count": int(s.count()),
            "mean": s.mean() if len(s) else np.nan,
            "median": s.median() if len(s) else np.nan,
            "min": s.min() if len(s) else np.nan,
            "max": s.max() if len(s) else np.nan,
            "std": s.std(ddof=1) if len(s) > 1 else np.nan,
        }
        for p in percentiles:
            row[f"p{p:g}"] = float(np.percentile(s, p)) if len(s) else np.nan
        rows[col] = row
    return pd.DataFrame.from_dict(rows, orient="index")


def group_statistics(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    """Count/mean/median/min/max/std of `value_col` for each category in `group_col`."""
    grouped = df.groupby(group_col)[value_col].agg(["count", "mean", "median", "min", "max", "std"])
    return grouped.sort_values("mean", ascending=False)


def correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame | None:
    """Pearson correlation matrix, or None when it would not be meaningful (< 2 usable columns)."""
    usable = [c for c in numeric_cols if df[c].nunique(dropna=True) > 1]
    if len(usable) < 2 or len(df) < 3:
        return None
    return df[usable].corr(method="pearson")


def strong_correlations(corr: pd.DataFrame | None, threshold: float = 0.5) -> list[dict]:
    """List column pairs whose absolute correlation >= threshold (each pair once)."""
    if corr is None:
        return []
    pairs = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            if pd.notna(r) and abs(r) >= threshold:
                pairs.append({"column_a": a, "column_b": b, "correlation": round(float(r), 4)})
    return sorted(pairs, key=lambda p: -abs(p["correlation"]))


def detect_outliers(df: pd.DataFrame, numeric_cols: list[str], multiplier: float = 1.5, max_listed: int = 20) -> dict:
    """Flag values outside the IQR fences. Rows are REPORTED, never deleted."""
    result = {}
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        valid = s.dropna()
        if len(valid) < 4:
            continue
        q1, q3 = np.percentile(valid, [25, 75])
        iqr = q3 - q1
        lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
        mask = (s < lower) | (s > upper)
        count = int(mask.sum())
        result[col] = {
            "count": count,
            "percent_of_values": round(100 * count / len(valid), 2),
            "lower_fence": float(lower),
            "upper_fence": float(upper),
            "example_row_indexes": [int(i) for i in s.index[mask][:max_listed]],
        }
    return result


def monthly_trend(df: pd.DataFrame, date_col: str | None, target_col: str | None, min_months: int = 3) -> dict | None:
    """Describe how the monthly mean of `target_col` moved over time.

    Returns None if there is not enough data. The wording is deliberately descriptive:
    it states what the numbers did, not why.
    """
    if not date_col or not target_col or date_col not in df.columns or target_col not in df.columns:
        return None
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[target_col], errors="coerce")
    frame = pd.DataFrame({"month": dates.dt.to_period("M"), "value": values}).dropna()
    if frame.empty:
        return None
    monthly = frame.groupby("month")["value"].mean()
    if len(monthly) < min_months:
        return None
    first, last = float(monthly.iloc[0]), float(monthly.iloc[-1])
    slope = float(np.polyfit(np.arange(len(monthly)), monthly.to_numpy(dtype=float), 1)[0])
    change_pct = (last - first) / abs(first) * 100 if first else None
    if change_pct is None or abs(change_pct) < 5:
        direction = "roughly flat (first-to-last change under 5%)"
    else:
        direction = "higher" if change_pct > 0 else "lower"
    return {
        "target_column": target_col,
        "months_covered": int(len(monthly)),
        "first_month": str(monthly.index[0]),
        "last_month": str(monthly.index[-1]),
        "first_month_mean": round(first, 4),
        "last_month_mean": round(last, 4),
        "change_percent_first_to_last": None if change_pct is None else round(change_pct, 2),
        "linear_slope_per_month": round(slope, 4),
        "direction": direction,
        "monthly_means": {str(k): round(float(v), 4) for k, v in monthly.items()},
    }
