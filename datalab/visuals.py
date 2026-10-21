"""Visualization engine (Matplotlib).

LEARNING NOTES
--------------
* ``matplotlib.use("Agg")`` selects a "no window" backend that only writes image files.
  That is lighter than opening GUI windows and is safe to run unattended.
* ``fig, ax = plt.subplots()`` creates a canvas (figure) and a drawing area (axes).
* We ALWAYS call ``plt.close(fig)`` after saving; otherwise memory grows with every
  chart, which would be a problem during a six-hour run on 8 GB RAM.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def _save(fig, path: Path, dpi: int) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path.name


def histogram(df: pd.DataFrame, column: str, out_dir: Path, stem: str, dpi: int = 150) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df[column].dropna(), bins=30, color="#4C78A8", edgecolor="white")
    ax.set_title(f"Distribution of {column} ({stem})")
    ax.set_xlabel(column)
    ax.set_ylabel("Number of rows")
    return _save(fig, out_dir / f"{stem}_histogram_{column}.png", dpi)


def bar_chart(df: pd.DataFrame, group_col: str, value_col: str, out_dir: Path, stem: str, dpi: int = 150) -> str:
    means = df.groupby(group_col)[value_col].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(means.index.astype(str), means.to_numpy(), color="#59A14F")
    ax.set_title(f"Average {value_col} by {group_col} ({stem})")
    ax.set_xlabel(group_col)
    ax.set_ylabel(f"Mean {value_col}")
    ax.tick_params(axis="x", rotation=30)
    return _save(fig, out_dir / f"{stem}_bar_{value_col}_by_{group_col}.png", dpi)


def line_chart(monthly_means: dict[str, float], value_col: str, out_dir: Path, stem: str, dpi: int = 150) -> str:
    labels = list(monthly_means.keys())
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(labels, list(monthly_means.values()), marker="o", color="#E15759")
    ax.set_title(f"Monthly mean of {value_col} ({stem})")
    ax.set_xlabel("Month")
    ax.set_ylabel(f"Mean {value_col}")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=0.3)
    return _save(fig, out_dir / f"{stem}_line_monthly_{value_col}.png", dpi)


def box_plot(df: pd.DataFrame, group_col: str, value_col: str, out_dir: Path, stem: str, dpi: int = 150) -> str:
    groups = [(str(name), g[value_col].dropna().to_numpy()) for name, g in df.groupby(group_col)]
    groups = [(n, v) for n, v in groups if len(v) > 0]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.boxplot([v for _, v in groups])
    ax.set_xticks(range(1, len(groups) + 1))
    ax.set_xticklabels([n for n, _ in groups], rotation=30)
    ax.set_title(f"Spread of {value_col} by {group_col} ({stem})")
    ax.set_xlabel(group_col)
    ax.set_ylabel(value_col)
    return _save(fig, out_dir / f"{stem}_box_{value_col}_by_{group_col}.png", dpi)


def correlation_heatmap(corr: pd.DataFrame, out_dir: Path, stem: str, dpi: int = 150) -> str:
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.columns)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Pearson correlation")
    ax.set_title(f"Correlation heatmap ({stem})")
    ax.set_xlabel("Numeric column")
    ax.set_ylabel("Numeric column")
    return _save(fig, out_dir / f"{stem}_correlation_heatmap.png", dpi)
