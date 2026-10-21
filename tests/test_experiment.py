import json

import pytest

from datalab.config import ConfigError, load_config
from datalab.experiment import ExperimentRunner, data_fingerprint


class FakeClock:
    """Time only moves when sleep() is called, so tests finish instantly."""

    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def make_runner(run_fn, fp_fn, clock, duration=3600, interval=900, force=1800, log_path=None):
    return ExperimentRunner(run_fn, fp_fn, duration, interval, force, run_log_path=log_path,
                            clock=clock.now, sleep=clock.sleep, tick_seconds=60)


def test_stops_automatically_at_duration_and_reports_elapsed():
    clock = FakeClock()
    runs = []
    runner = make_runner(lambda: runs.append(clock.t), lambda: ("same",), clock)
    summary = runner.run()
    assert summary["stop_reason"] == "duration_elapsed"
    assert summary["reached_planned_duration"] is True
    assert summary["elapsed_seconds"] == pytest.approx(3600)
    # checks at t=0,900,1800,2700; run at 0 and forced at 1800
    assert summary["runs_succeeded"] == 2
    assert summary["checks_skipped_unchanged"] == 2


def test_unchanged_data_skips_heavy_work():
    clock = FakeClock()
    calls = []
    runner = make_runner(lambda: calls.append(1), lambda: ("same",), clock, duration=1700, force=99999)
    summary = runner.run()
    assert len(calls) == 1 and summary["checks_skipped_unchanged"] == 1


def test_changed_data_triggers_rerun():
    clock = FakeClock()
    state = {"fp": 0}
    calls = []

    def run():
        calls.append(clock.t)

    def fp():
        state["fp"] += 1  # looks different every check
        return (state["fp"],)

    summary = make_runner(run, fp, clock, duration=1800, force=99999).run()
    assert len(calls) == summary["runs_succeeded"] == 2


def test_failed_run_is_logged_and_retried_without_stopping(tmp_path):
    clock = FakeClock()
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("temporary glitch")

    log_path = tmp_path / "runs.jsonl"
    summary = make_runner(flaky, lambda: ("same",), clock, duration=1700, force=99999, log_path=log_path).run()
    assert summary["runs_failed"] == 1 and summary["runs_succeeded"] == 1
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    failed = [e for e in entries if e.get("status") == "failed"]
    assert failed and "temporary glitch" in failed[0]["error"]
    assert all("timestamp" in e for e in entries)
    assert entries[-1]["event"] == "experiment_end"


def test_ctrl_c_stops_safely_and_does_not_claim_full_duration():
    clock = FakeClock()

    def interrupting_sleep(seconds):
        clock.sleep(seconds)
        if clock.t >= 300:
            raise KeyboardInterrupt

    runner = ExperimentRunner(lambda: None, lambda: ("x",), 3600, 900, 1800, clock=clock.now, sleep=interrupting_sleep, tick_seconds=60)
    summary = runner.run()
    assert summary["stop_reason"] == "keyboard_interrupt"
    assert summary["reached_planned_duration"] is False
    assert summary["elapsed_seconds"] < 3600


def test_stop_requested_flag_ends_loop():
    clock = FakeClock()
    runner = make_runner(lambda: None, lambda: ("x",), clock)
    orig_sleep = runner.sleep

    def sleep_then_stop(s):
        orig_sleep(s)
        runner.stop_requested = True

    runner.sleep = sleep_then_stop
    summary = runner.run()
    assert summary["stop_reason"] == "stop_requested"
    assert summary["elapsed_seconds"] < 3600


def test_data_fingerprint_changes_when_file_changes(tmp_path):
    assert data_fingerprint(tmp_path / "missing") == ()
    f = tmp_path / "a.csv"
    f.write_text("x\n1\n")
    first = data_fingerprint(tmp_path)
    f.write_text("x\n1\n2\n")
    assert data_fingerprint(tmp_path) != first


def test_default_config_is_six_hours_and_fifteen_minutes(tmp_path):
    cfg = load_config(base_dir=tmp_path)
    assert cfg["experiment"]["duration_hours"] == 6
    assert cfg["experiment"]["interval_minutes"] == 15


def test_invalid_config_values_rejected(tmp_path):
    bad = tmp_path / "config.json"
    bad.write_text(json.dumps({"experiment": {"duration_hours": -1}}))
    with pytest.raises(ConfigError):
        load_config(bad, tmp_path)
    bad.write_text("{not json")
    with pytest.raises(ConfigError):
        load_config(bad, tmp_path)
