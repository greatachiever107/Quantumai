import hashlib
import json

import pytest

from datalab.pipeline import run_analysis
from datalab.reports import to_jsonable, write_report


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_run_creates_report_charts_and_processed_files(project):
    root, cfg = project
    original = root / "data" / "sample.csv"
    before = _sha(original)

    report = run_analysis(cfg)

    assert report["status"] == "success"
    md = list((root / "output" / "reports").glob("report_*.md"))
    js = list((root / "output" / "reports").glob("report_*.json"))
    assert len(md) == 1 and len(js) == 1
    data = json.loads(js[0].read_text(encoding="utf-8"))
    assert data["datasets"][0]["rows_loaded"] == report["datasets"][0]["rows_loaded"]
    assert data["execution_seconds"] >= 0
    text = md[0].read_text(encoding="utf-8")
    assert "Execution duration" in text and "Data quality findings" in text
    charts = list((root / "output" / "charts").glob("*.png"))
    assert len(charts) >= 5  # histograms, bar, box, line, heatmap
    for name in report["datasets"][0]["charts"]:
        assert (root / "output" / "charts" / name).is_file()
    assert (root / "output" / "processed" / "sample_cleaned.csv").is_file()
    assert _sha(original) == before  # original dataset untouched
    assert not list((root / "data").glob("*cleaned*"))  # nothing written into data/


def test_bad_file_is_reported_but_good_file_still_processed(project):
    root, cfg = project
    (root / "data" / "broken.csv").write_text("")
    report = run_analysis(cfg)
    assert report["status"] == "partial"
    assert any("broken.csv" in e for e in report["errors"])


def test_no_datasets_gives_failed_status(tmp_path):
    from datalab.config import load_config
    (tmp_path / "data").mkdir()
    report = run_analysis(load_config(base_dir=tmp_path))
    assert report["status"] == "failed"


def test_two_reports_in_same_second_do_not_overwrite(tmp_path):
    rep = {"generated_at": "t", "status": "success", "datasets": [], "warnings": [], "errors": [], "execution_seconds": 0.1}
    from datetime import datetime
    when = datetime(2026, 1, 1, 12, 0, 0)
    a = write_report(rep, tmp_path, when)
    b = write_report(rep, tmp_path, when)
    assert a[0] != b[0]


def test_to_jsonable_handles_numpy_and_nan():
    import numpy as np
    out = to_jsonable({"a": np.int64(3), "b": np.float64("nan"), "c": [np.float32(1.5)]})
    assert out == {"a": 3, "b": None, "c": [1.5]}
    json.dumps(out)
