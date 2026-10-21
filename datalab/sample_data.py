"""Synthetic sample data generator (no real or private data).

LEARNING NOTES
--------------
``numpy.random.default_rng(seed)`` makes random numbers that are the same every time
you use the same seed, so results are reproducible. We then deliberately inject a few
problems (duplicates, blanks, bad numbers, negatives, extreme values) so the validation
features have something to find. Revenue is computed BEFORE the problems are injected.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_data(n_rows: int = 520, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    regions = np.array(["North", "South", "East", "West"])
    categories = np.array(["Electronics", "Clothing", "Home", "Sports", "Books"])
    base_price = {"Electronics": 220.0, "Clothing": 45.0, "Home": 80.0, "Sports": 60.0, "Books": 18.0}

    dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n_rows), unit="D")
    category = rng.choice(categories, n_rows, p=[0.2, 0.25, 0.2, 0.15, 0.2])
    region = rng.choice(regions, n_rows)
    growth = 1 + 0.10 * (dates.dayofyear.to_numpy() / 365)  # mild upward price drift
    unit_price = np.round([base_price[c] for c in category] * growth * rng.normal(1, 0.08, n_rows), 2)
    units = rng.poisson(4, n_rows) + 1
    discount = rng.choice([0, 5, 10, 15, 20], n_rows, p=[0.5, 0.2, 0.15, 0.1, 0.05])
    revenue = np.round(units * unit_price * (1 - discount / 100), 2)
    df = pd.DataFrame({
        "order_id": [f"ORD-{i:05d}" for i in range(1, n_rows + 1)],
        "order_date": dates.strftime("%Y-%m-%d"),
        "region": region,
        "category": category,
        "units_sold": units,
        "unit_price": unit_price,
        "discount_pct": discount,
        "revenue": revenue,
        "customer_age": np.clip(rng.normal(38, 12, n_rows).round(), 18, 80).astype(int),
        "satisfaction_score": np.clip(rng.normal(4.0, 0.8, n_rows).round(1), 1, 5),
    })
    df = df.sort_values("order_date").reset_index(drop=True)
    df["unit_price"] = df["unit_price"].astype(object)

    # ---- injected data-quality problems (documented in data/DATA_DICTIONARY.md) ----
    idx = rng.permutation(n_rows)
    df.loc[idx[0:15], "customer_age"] = np.nan
    df.loc[idx[15:25], "satisfaction_score"] = np.nan
    df.loc[idx[25:30], "region"] = np.nan
    for i, bad in zip(idx[30:33], ["abc", "?", "twelve"]):
        df.loc[i, "unit_price"] = bad
    df.loc[idx[33:36], "units_sold"] = [-1, -2, -3]
    df.loc[idx[36:40], "units_sold"] = [60, 75, 80, 90]  # extreme but valid values
    df = pd.concat([df, df.iloc[idx[40:52]]], ignore_index=True)  # 12 exact duplicates
    return df


def write_sample_csv(path: str | Path, n_rows: int = 520, seed: int = 42) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_sample_data(n_rows, seed).to_csv(path, index=False)
    return path
