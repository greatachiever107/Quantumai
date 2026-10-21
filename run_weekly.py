"""One-command refresh: new prices, events, earnings, forecast, dashboard.

    python run_weekly.py            # about 2-3 min once downloads succeed
    python run_weekly.py --full     # also re-run the full model backtest
    python run_weekly.py --keep-cache   # reuse cached downloads (no fresh prices)
Run from the project folder. Stops at the first step that fails.
"""
import shutil, subprocess, sys

if "--keep-cache" not in sys.argv:           # caches never expire on their own
    for d in ("cache_prices", "cache_earnings"):
        shutil.rmtree(d, ignore_errors=True)
steps = ["fetch_stocks.py", "build_events.py", "fetch_earnings.py", "event_study.py",
         "volatility_chart.py", "track_forecasts.py", "build_dashboard.py", "export_snapshot.py"]
if "--full" in sys.argv:
    steps.insert(-2, "model_volatility_v3.py")
for s in steps:
    print(f"\n===== {s} =====", flush=True)
    if subprocess.run([sys.executable, s]).returncode != 0:
        sys.exit(f"\nStopped: {s} failed. Fix it (or wait and retry), then rerun.")
print("\nAll done. Open dashboard/index.html. To publish: git add snapshot && git commit -m update && git push")
