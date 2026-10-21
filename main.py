"""Python-Data-Lab command-line entry point.

Usage (from the project folder, inside the virtual environment):
    python main.py run                 # one analysis of every CSV in data/
    python main.py experiment          # timed experiment (default 6 h, every 15 min)
    python main.py generate-sample     # (re)create data/sample_data.csv, refusing to overwrite
    python main.py --help

LEARNING NOTES
--------------
``argparse`` reads what you type after ``python main.py``. Each sub-command ("run",
"experiment", ...) calls one function. ``sys.exit(code)`` returns 0 for success and a
non-zero number for failure, which scripts can check.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datalab.config import ConfigError, load_config
from datalab.experiment import ExperimentRunner, data_fingerprint
from datalab.logging_setup import setup_logging
from datalab.pipeline import run_analysis
from datalab.sample_data import write_sample_csv


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Python-Data-Lab: local data analysis project")
    p.add_argument("--config", help="Path to a config.json (default: ./config.json)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run a single analysis")
    ex = sub.add_parser("experiment", help="Run the timed experiment")
    ex.add_argument("--hours", type=float, help="Override duration_hours from config.json")
    ex.add_argument("--interval-minutes", type=float, help="Override interval_minutes from config.json")
    sub.add_parser("generate-sample", help="Create data/sample_data.csv if it does not exist")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = Path(__file__).resolve().parent
    try:
        cfg = load_config(args.config, base)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    log = setup_logging(cfg["resolved_paths"]["logs_dir"])

    if args.command == "generate-sample":
        target = cfg["resolved_paths"]["data_dir"] / "sample_data.csv"
        if target.exists():
            log.warning("%s already exists; not overwriting it.", target)
            return 0
        write_sample_csv(target)
        log.info("Created %s", target)
        return 0

    if args.command == "run":
        report = run_analysis(cfg)
        log.info("Single run finished with status: %s", report["status"])
        print(f"\nReport files in {cfg['resolved_paths']['reports_dir']}: {', '.join(report.get('report_files', []))}")
        return 0 if report["status"] in ("success", "partial") else 1

    # experiment
    exp = cfg["experiment"]
    hours = args.hours if args.hours is not None else exp["duration_hours"]
    interval = args.interval_minutes if args.interval_minutes is not None else exp["interval_minutes"]
    if hours <= 0 or interval <= 0:
        print("Hours and interval must be positive numbers.", file=sys.stderr)
        return 2

    def one_run() -> dict:
        report = run_analysis(cfg)
        if report["status"] == "failed":
            raise RuntimeError("; ".join(report["errors"]) or "analysis failed")
        return report

    runner = ExperimentRunner(
        run_fn=one_run,
        fingerprint_fn=lambda: data_fingerprint(cfg["resolved_paths"]["data_dir"]),
        duration_seconds=hours * 3600,
        interval_seconds=interval * 60,
        force_reprocess_seconds=exp["force_reprocess_minutes"] * 60,
        run_log_path=cfg["resolved_paths"]["logs_dir"] / "experiment_runs.jsonl",
        logger=log,
        tick_seconds=exp["tick_seconds"],
    )
    print(f"Experiment starting: up to {hours:g} h, checking every {interval:g} min. Press Ctrl+C to stop safely.")
    summary = runner.run()
    print("\nExperiment summary (from measured clock, see logs/experiment_runs.jsonl):")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
