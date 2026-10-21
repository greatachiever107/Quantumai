"""Copy the files the API serves into snapshot/ so they can be committed and deployed.

    python export_snapshot.py
Render's disk is wiped on every deploy, so the backend reads this committed
snapshot (PROJECT_DIR=.../snapshot). run_weekly.py runs this as its last step;
then commit and push the snapshot folder to publish the new numbers.
"""
import shutil
from pathlib import Path

OUT = Path("snapshot")
files = ["data/stocks.csv", "events/events.csv", "events/earnings.csv"]
files += [str(p).replace("\\", "/") for g in ("output/processed/*.csv", "output/tracking/*.csv") for p in Path(".").glob(g)]
shutil.rmtree(OUT, ignore_errors=True)
total = 0
for f in files:
    src = Path(f)
    if src.exists():
        dst = OUT / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        total += src.stat().st_size
        print(f"  copied {f}")
print(f"\nsnapshot/ ready: {len(list(OUT.rglob('*.csv')))} files, {total / 1e6:.1f} MB")
