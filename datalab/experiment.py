"""Timed experiment mode.

LEARNING NOTES
--------------
* The runner repeats "check the data, maybe analyse" on a schedule until the configured
  duration has passed, or until you press Ctrl+C.
* To stay light on your laptop it sleeps in 1-second slices (cheap, and lets Ctrl+C work
  immediately) and only does heavy work when the files changed or the forced-reprocess
  interval has elapsed.
* ``clock`` and ``sleep`` are parameters so the tests can use a fake clock and finish
  instantly instead of waiting six real hours.
* Honesty rule: the final summary reports the ACTUAL measured elapsed time. It never
  assumes the planned duration was reached.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable


def data_fingerprint(data_dir: Path) -> tuple:
    """Cheap change detector: (name, size, modified-time) for each CSV. No file reading."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return ()
    items = []
    for p in sorted(data_dir.glob("*.csv")):
        try:
            st = p.stat()
            items.append((p.name, st.st_size, st.st_mtime_ns))
        except OSError:
            continue
    return tuple(items)


class ExperimentRunner:
    def __init__(
        self,
        run_fn: Callable[[], dict],
        fingerprint_fn: Callable[[], tuple],
        duration_seconds: float,
        interval_seconds: float,
        force_reprocess_seconds: float,
        run_log_path: Path | None = None,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        tick_seconds: float = 1.0,
    ):
        self.run_fn = run_fn
        self.fingerprint_fn = fingerprint_fn
        self.duration = duration_seconds
        self.interval = interval_seconds
        self.force_after = force_reprocess_seconds
        self.run_log_path = Path(run_log_path) if run_log_path else None
        self.log = logger or logging.getLogger("datalab")
        self.clock = clock
        self.sleep = sleep
        self.tick = tick_seconds
        self.stop_requested = False  # can be set to True to stop politely

    def _record(self, entry: dict) -> None:
        """Append one JSON line per scheduled check to the run log."""
        entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), **entry}
        if self.run_log_path:
            try:
                self.run_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.run_log_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
            except OSError as exc:
                self.log.warning("Could not write run log: %s", exc)

    def _wait_until(self, wake_at: float) -> None:
        while not self.stop_requested:
            remaining = wake_at - self.clock()
            if remaining <= 0:
                return
            self.sleep(min(self.tick, remaining))

    def run(self) -> dict:
        start = self.clock()
        deadline = start + self.duration
        counts = {"succeeded": 0, "failed": 0, "skipped": 0}
        last_fp = None
        last_success_at: float | None = None
        reason = "duration_elapsed"
        self.log.info(
            "Experiment started: planned duration %.0f s, check interval %.0f s",
            self.duration, self.interval,
        )
        try:
            while not self.stop_requested:
                now = self.clock()
                if now >= deadline:
                    break
                fp = self.fingerprint_fn()
                changed = fp != last_fp
                due = last_success_at is None or (now - last_success_at) >= self.force_after
                if changed or due:
                    why = "first run" if last_fp is None else ("data changed" if changed else "interval reached")
                    t0 = self.clock()
                    try:
                        self.run_fn()
                        status, error = "success", None
                        last_fp, last_success_at = fp, self.clock()
                        counts["succeeded"] += 1
                    except Exception as exc:  # temporary or data errors must not end the experiment
                        status, error = "failed", f"{type(exc).__name__}: {exc}"
                        last_fp = None  # force a retry at the next check
                        counts["failed"] += 1
                        self.log.error("Run failed (%s): %s", why, error)
                    self._record({"event": "run", "reason": why, "status": status,
                                  "duration_seconds": round(self.clock() - t0, 3), "error": error})
                    self.log.info("Run %s (%s)", status, why)
                else:
                    counts["skipped"] += 1
                    self._record({"event": "check", "status": "skipped_unchanged", "duration_seconds": 0, "error": None})
                    self.log.info("Check: data unchanged, heavy processing skipped")
                self._wait_until(min(now + self.interval, deadline))
            if self.stop_requested:
                reason = "stop_requested"
        except KeyboardInterrupt:
            reason = "keyboard_interrupt"
            self.log.info("Ctrl+C received: stopping safely")
        elapsed = self.clock() - start
        summary = {
            "stop_reason": reason,
            "planned_seconds": self.duration,
            "elapsed_seconds": round(elapsed, 2),
            "reached_planned_duration": reason == "duration_elapsed",
            "runs_succeeded": counts["succeeded"],
            "runs_failed": counts["failed"],
            "checks_skipped_unchanged": counts["skipped"],
        }
        self._record({"event": "experiment_end", **summary})
        self.log.info("Experiment ended (%s). Planned %.0f s, measured elapsed %.1f s.", reason, self.duration, elapsed)
        return summary
