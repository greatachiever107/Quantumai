"""Report writing (Markdown for people, JSON for programs).

LEARNING NOTES
--------------
* JSON can't store NumPy numbers or pandas objects directly, so ``to_jsonable`` converts
  them into plain Python types first.
* Reports are TIMESTAMPED so each run keeps its own file and nothing is overwritten.
* The report only repeats numbers that were computed from the data. It never adds
  interpretation the data doesn't support.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def to_jsonable(obj):
    """Recursively convert NumPy / pandas values to JSON-safe Python values."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return to_jsonable(obj.to_dict(orient="index"))
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime, Path)):
        return str(obj)
    if obj is pd.NaT:
        return None
    return obj


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(c) for c in row) + " |")
    return lines


def render_markdown(report: dict) -> str:
    lines = [
        "# Data Analysis Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Status: **{report['status']}**",
        f"- Execution duration: {report['execution_seconds']:.2f} seconds",
        f"- Datasets analysed: {len(report['datasets'])}",
        "",
    ]
    for ds in report["datasets"]:
        lines += [f"## Dataset: {ds['name']}", ""]
        if ds.get("errors"):
            lines += ["**This dataset could not be analysed.**", ""]
            lines += [f"- Error: {e}" for e in ds["errors"]] + [""]
            continue
        lines += [
            f"- Rows loaded: {ds['rows_loaded']}",
            f"- Rows after cleaning: {ds['rows_after_cleaning']}",
            "",
            "### Data quality findings",
            "",
        ]
        issues = ds["quality"]["issues"]
        lines += [f"- {i}" for i in issues] if issues else ["- No quality issues detected by the configured checks."]
        lines += ["", "Cleaning actions applied (to a copy; the original file is untouched):", ""]
        for key, val in ds["cleaning_actions"].items():
            lines.append(f"- {key}: {val}")
        lines += ["", "### Summary statistics", ""]
        stats = ds["summary_statistics"]
        if stats:
            cols = list(next(iter(stats.values())).keys())
            lines += _table(["column"] + cols, [[c] + [v.get(k) for k in cols] for c, v in stats.items()])
        else:
            lines.append("No numeric columns found.")
        lines += ["", "### Trends and correlations", ""]
        trend = ds.get("trend")
        if trend:
            lines.append(
                f"- Monthly mean of `{trend['target_column']}` went from {_fmt(trend['first_month_mean'])} "
                f"({trend['first_month']}) to {_fmt(trend['last_month_mean'])} ({trend['last_month']}) over "
                f"{trend['months_covered']} months: {trend['direction']}"
                + (f", change {_fmt(trend['change_percent_first_to_last'])}%." if trend["change_percent_first_to_last"] is not None else ".")
            )
            lines.append("- This describes the numbers only; it does not explain the cause.")
        else:
            lines.append("- Not enough dated data to describe a trend.")
        corr = ds.get("strong_correlations", [])
        if corr:
            for p in corr:
                lines.append(f"- `{p['column_a']}` vs `{p['column_b']}`: r = {p['correlation']:.2f} (correlation is not causation).")
        else:
            lines.append("- No column pairs met the correlation threshold (or correlation was not applicable).")
        lines += ["", "### Potential outliers (reported, not removed)", ""]
        outliers = ds.get("outliers", {})
        rows = [[c, o["count"], o["percent_of_values"], o["lower_fence"], o["upper_fence"]] for c, o in outliers.items() if o["count"]]
        lines += _table(["column", "count", "% of values", "lower fence", "upper fence"], rows) if rows else ["No outliers flagged by the IQR rule."]
        lines += ["", "### Group statistics", ""]
        if ds.get("group_statistics"):
            for gname in ds["group_statistics"]:
                lines.append(f"- Grouped by `{gname}`: see `{ds['group_statistics'][gname]}`")
        else:
            lines.append("No grouping columns available.")
        lines += ["", "### Output files", ""]
        lines += [f"- Chart: `{c}`" for c in ds["charts"]] or ["- No charts generated."]
        lines += [f"- Processed: `{p}`" for p in ds["processed_files"]]
        if ds.get("warnings"):
            lines += ["", "### Warnings", ""] + [f"- {w}" for w in ds["warnings"]]
        lines.append("")
    lines += ["## Errors and warnings (run level)", ""]
    run_msgs = [f"ERROR: {e}" for e in report["errors"]] + [f"WARNING: {w}" for w in report["warnings"]]
    lines += [f"- {m}" for m in run_msgs] or ["- None."]
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict, reports_dir: Path, when: datetime | None = None) -> tuple[Path, Path]:
    """Write report_<timestamp>.md and .json. Returns both paths."""
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    base = reports_dir / f"report_{stamp}"
    counter = 1
    while base.with_suffix(".md").exists() or base.with_suffix(".json").exists():
        base = reports_dir / f"report_{stamp}_{counter}"
        counter += 1
    md_path, json_path = base.with_suffix(".md"), base.with_suffix(".json")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(to_jsonable(report), indent=2), encoding="utf-8")
    return md_path, json_path
