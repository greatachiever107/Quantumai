"""Configuration loading.

LEARNING NOTES
--------------
* JSON is a text format for settings. Python's built-in ``json`` module turns it
  into dictionaries (``dict``) and lists.
* We keep DEFAULTS in code and merge the user's config.json on top, so a missing
  setting never crashes the program.
* ``pathlib.Path`` is the modern way to handle file paths. It works the same on
  Windows (backslashes) and other systems.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULTS: dict = {
    "paths": {
        "data_dir": "data",
        "charts_dir": "output/charts",
        "reports_dir": "output/reports",
        "processed_dir": "output/processed",
        "logs_dir": "logs",
    },
    "analysis": {
        "target_column": "revenue",
        "date_column": "order_date",
        "group_by": ["region", "category"],
        "exclude_numeric_columns": ["order_id"],
        "required_columns": [],
        "non_negative_columns": [],
        "missing_numeric_strategy": "median",  # median | drop | keep
        "percentiles": [5, 25, 50, 75, 95],
        "outlier_iqr_multiplier": 1.5,
        "correlation_threshold": 0.5,
        "max_file_mb": 200,
        "chunk_rows": 50000,
        "chart_dpi": 150,
    },
    "experiment": {
        "duration_hours": 6,
        "interval_minutes": 15,
        "force_reprocess_minutes": 60,
        "tick_seconds": 1,
    },
}


class ConfigError(Exception):
    """Raised when config.json is unreadable or contains invalid values."""


def _merge(base: dict, override: dict) -> dict:
    """Recursively copy `override` values on top of `base` (without mutating either)."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(cfg: dict) -> None:
    """Check the values that would cause confusing failures later."""
    exp = cfg["experiment"]
    for key in ("duration_hours", "interval_minutes", "force_reprocess_minutes", "tick_seconds"):
        value = exp.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ConfigError(f"experiment.{key} must be a positive number, got {value!r}")
    if cfg["analysis"]["missing_numeric_strategy"] not in ("median", "drop", "keep"):
        raise ConfigError("analysis.missing_numeric_strategy must be 'median', 'drop' or 'keep'")
    pcts = cfg["analysis"]["percentiles"]
    if not pcts or any((not isinstance(p, (int, float)) or p < 0 or p > 100) for p in pcts):
        raise ConfigError("analysis.percentiles must be numbers between 0 and 100")
    if cfg["analysis"]["outlier_iqr_multiplier"] <= 0:
        raise ConfigError("analysis.outlier_iqr_multiplier must be positive")


def load_config(config_path: str | Path | None = None, base_dir: str | Path | None = None) -> dict:
    """Load config.json (if present), merge with defaults, resolve folders.

    Returns a dict with an extra key ``resolved_paths`` holding absolute Paths.
    """
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
    path = Path(config_path) if config_path else base / "config.json"
    user_cfg: dict = {}
    if path.exists():
        try:
            user_cfg = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ConfigError(f"Could not read {path}: {exc}") from exc
        if not isinstance(user_cfg, dict):
            raise ConfigError(f"{path} must contain a JSON object")
    cfg = _merge(DEFAULTS, user_cfg)
    validate_config(cfg)
    cfg["resolved_paths"] = {
        name: (base / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
        for name, rel in cfg["paths"].items()
    }
    cfg["base_dir"] = str(base)
    return cfg
