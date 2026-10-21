"""The analysis pipeline: load -> validate -> clean -> analyse -> chart -> report.

LEARNING NOTES
--------------
``run_analysis`` is the one function both "single run" and "experiment mode" call.
Each dataset is wrapped in ``try/except`` so one bad file cannot stop the others.
The ``data/`` folder is only ever READ. Everything we write goes under ``output/``.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import processing as proc
from . import visuals
from .reports import to_jsonable, write_report

log = logging.getLogger("datalab")


def list_datasets(data_dir: Path) -> list[Path]:
    data_dir = Path(data_dir)
    return sorted(p for p in data_dir.glob("*.csv") if p.is_file()) if data_dir.is_dir() else []


def _analyse_one(path: Path, cfg: dict) -> dict:
    a = cfg["analysis"]
    paths = cfg["resolved_paths"]
    stem = path.stem
    ds: dict = {"name": path.name, "charts": [], "processed_files": [], "warnings": [], "errors": [], "group_statistics": {}}

    raw = proc.load_csv(path, a["max_file_mb"], a["chunk_rows"])
    ds["rows_loaded"] = int(len(raw))
    exclude = a["exclude_numeric_columns"]
    ds["quality"] = proc.validate_data(raw, a["required_columns"], a["non_negative_columns"], exclude)
    if ds["quality"]["missing_required_columns"]:
        ds["warnings"].append("Some required columns are missing; related analysis may be skipped.")

    cleaned, actions = proc.clean_data(raw, exclude, a["non_negative_columns"], a["date_column"], a["missing_numeric_strategy"])
    ds["cleaning_actions"] = actions
    ds["rows_after_cleaning"] = int(len(cleaned))
    del raw  # free memory early

    numeric_cols = proc.find_numeric_columns(cleaned, exclude=exclude)
    target = a["target_column"] if a["target_column"] in numeric_cols else (numeric_cols[0] if numeric_cols else None)
    if target and target != a["target_column"]:
        ds["warnings"].append(f"Target column '{a['target_column']}' not found; using '{target}' instead.")
    group_cols = [g for g in a["group_by"] if g in cleaned.columns]
    if not group_cols:  # fall back to low-cardinality text columns
        group_cols = [c for c in cleaned.columns if c not in numeric_cols and not pd.api.types.is_datetime64_any_dtype(cleaned[c])
                      and 1 < cleaned[c].nunique() <= 20][:2]

    stats = proc.summary_statistics(cleaned, numeric_cols, a["percentiles"])
    ds["summary_statistics"] = to_jsonable(stats)
    corr = proc.correlation_matrix(cleaned, numeric_cols)
    ds["strong_correlations"] = proc.strong_correlations(corr, a["correlation_threshold"])
    ds["outliers"] = proc.detect_outliers(cleaned, numeric_cols, a["outlier_iqr_multiplier"])
    ds["trend"] = proc.monthly_trend(cleaned, a["date_column"], target)

    # ---- save processed data (never into data/) ----
    pdir = Path(paths["processed_dir"]); pdir.mkdir(parents=True, exist_ok=True)
    files = {f"{stem}_cleaned.csv": cleaned, f"{stem}_summary_statistics.csv": stats}
    if corr is not None:
        files[f"{stem}_correlations.csv"] = corr
    for g in group_cols:
        if target:
            name = f"{stem}_group_{target}_by_{g}.csv"
            files[name] = proc.group_statistics(cleaned, g, target)
            ds["group_statistics"][g] = name
    flagged = sorted({i for o in ds["outliers"].values() for i in o["example_row_indexes"]})
    if flagged:
        files[f"{stem}_outlier_examples.csv"] = cleaned.loc[flagged]
    for name, frame in files.items():
        frame.to_csv(pdir / name, index=name.endswith(("statistics.csv", "correlations.csv")) or "_group_" in name)
        ds["processed_files"].append(name)

    # ---- charts ----
    cdir, dpi = Path(paths["charts_dir"]), a["chart_dpi"]
    try:
        for col in numeric_cols[:3]:
            ds["charts"].append(visuals.histogram(cleaned, col, cdir, stem, dpi))
        if target:
            for g in group_cols[:1]:
                ds["charts"].append(visuals.bar_chart(cleaned, g, target, cdir, stem, dpi))
            for g in group_cols[-1:]:
                ds["charts"].append(visuals.box_plot(cleaned, g, target, cdir, stem, dpi))
        if ds["trend"]:
            ds["charts"].append(visuals.line_chart(ds["trend"]["monthly_means"], target, cdir, stem, dpi))
        if corr is not None and len(corr) >= 3:
            ds["charts"].append(visuals.correlation_heatmap(corr, cdir, stem, dpi))
    except Exception as exc:  # charts are optional; don't lose the rest of the analysis
        ds["warnings"].append(f"Chart generation problem: {exc}")
        log.warning("Chart generation problem for %s: %s", path.name, exc)
    return ds


def run_analysis(cfg: dict) -> dict:
    """Analyse every CSV in data_dir. Returns the full report dict (also written to disk)."""
    start = time.perf_counter()
    paths = cfg["resolved_paths"]
    report: dict = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "success",
        "datasets": [],
        "warnings": [],
        "errors": [],
    }
    files = list_datasets(paths["data_dir"])
    if not files:
        report["errors"].append(f"No CSV files found in {paths['data_dir']}")
    for path in files:
        log.info("Analysing %s", path.name)
        try:
            report["datasets"].append(_analyse_one(path, cfg))
        except proc.DataLoadError as exc:
            log.error("Skipping %s: %s", path.name, exc)
            report["datasets"].append({"name": path.name, "errors": [str(exc)]})
            report["errors"].append(f"{path.name}: {exc}")
        except Exception as exc:  # unexpected problem: record it and continue
            log.exception("Unexpected error analysing %s", path.name)
            report["datasets"].append({"name": path.name, "errors": [f"Unexpected error: {exc}"]})
            report["errors"].append(f"{path.name}: unexpected error: {exc}")
    ok = [d for d in report["datasets"] if not d.get("errors")]
    report["status"] = "success" if ok and len(ok) == len(report["datasets"]) else ("partial" if ok else "failed")
    for d in ok:
        report["warnings"] += [f"{d['name']}: {w}" for w in d["warnings"]]
    report["execution_seconds"] = time.perf_counter() - start
    md_path, json_path = write_report(report, paths["reports_dir"])
    report["report_files"] = [md_path.name, json_path.name]
    log.info("Report written: %s (status=%s, %.2fs)", md_path.name, report["status"], report["execution_seconds"])
    return report
