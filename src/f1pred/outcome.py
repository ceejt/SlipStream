"""Add the real result next to a saved prediction. The prediction itself is never changed.

Usage: python -m f1pred.outcome            # every unscored prediction whose race is now in results.csv
       python -m f1pred.outcome 2026 18    # one race
Run `python -m f1pred.fetch` first so results.csv has the race.
"""
import json
import sys
from datetime import datetime, timezone

import pandas as pd

from .config import OUTCOMES, PREDICTIONS, RESULTS_CSV
from .report import write_report

MIN_DRIVERS = 10  # fewer rows than this means the result is not fully in yet


def build_outcome(results, year, rnd):
    """Finishing position and status per driver, or None if the race is not in the data yet."""
    race = results[(results["year"] == year) & (results["round"] == rnd)]
    if len(race) < MIN_DRIVERS:
        return None
    return {"year": year, "round": rnd,
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "drivers": {r.Abbreviation: {"position": int(r.Position) if pd.notna(r.Position) else None,
                                         "status": str(r.Status)} for r in race.itertuples()}}


def run(year=None, rnd=None):
    results = pd.read_csv(RESULTS_CSV)
    OUTCOMES.mkdir(parents=True, exist_ok=True)
    added = 0
    for f in sorted(PREDICTIONS.glob("*.json")):
        p = json.loads(f.read_text())
        if p["mode"] != "upcoming" or (year is not None and (p["year"], p["round"]) != (year, rnd)):
            continue
        target = OUTCOMES / f.name
        if target.exists():
            continue  # already scored; keep the first result
        o = build_outcome(results, p["year"], p["round"])
        if o is None:
            print(f"{f.stem}: result not in results.csv yet (run fetch, or wait for Jolpica)")
            continue
        target.write_text(json.dumps(o, indent=2))
        print(f"{f.stem}: saved {target.name}, rebuilt {write_report(p).name}")
        added += 1
    if not added:
        print("nothing to add")


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]]
    run(*args) if len(args) == 2 else run()
