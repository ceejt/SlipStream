"""Fetch race results and qualifying from the Jolpica F1 API.

Usage: python -m f1pred.fetch 2024 2025 2026
Writes data/raw/results.csv (one row per driver per race) and data/raw/races.csv
(one row per race). Files are rewritten after each season, so a failure keeps
the seasons already fetched. Weather and safety car data are not fetched.
"""
import sys
from datetime import date

import pandas as pd

from . import jolpica
from .config import RACES_CSV, RAW, RESULTS_CSV


def _seconds(t):
    """'1:15.096' -> 75.096. Empty or missing -> NaN."""
    if not t:
        return float("nan")
    m, _, s = t.rpartition(":")
    return int(m or 0) * 60 + float(s)


def _code(driver):
    return driver.get("code") or driver["familyName"][:3].upper()


def season_rows(year, results, quali):
    """Turn Jolpica race dicts (keyed by round) into result rows and race rows."""
    rows, races = [], []
    for rnd, race in sorted(results.items()):
        q = {_code(x["Driver"]): x for x in quali.get(rnd, {}).get("QualifyingResults", [])}
        event = race["raceName"]
        location = race["Circuit"]["Location"]["locality"]
        for r in race["Results"]:
            code = _code(r["Driver"])
            qr = q.get(code, {})
            times = [_seconds(qr[k]) for k in ("Q3", "Q2", "Q1") if qr.get(k)]
            rows.append({
                "Abbreviation": code, "TeamName": r["Constructor"]["name"],
                "GridPosition": r["grid"], "Position": r["position"],
                "Status": r["status"], "Points": r["points"],
                "quali_pos": qr.get("position"),
                "quali_time_s": times[0] if times else float("nan"),
                "year": year, "round": rnd, "event": event, "location": location,
            })
        races.append({"year": year, "round": rnd, "event": event,
                      "location": location, "date": race["date"]})
    return rows, races


def main(years):
    RAW.mkdir(parents=True, exist_ok=True)
    all_rows, all_races = [], []
    for year in years:
        rows, races = season_rows(year, jolpica.season(year, "results"),
                                  jolpica.season(year, "qualifying"))
        all_rows += rows
        all_races += races
        pd.DataFrame(all_rows).to_csv(RESULTS_CSV, index=False)
        pd.DataFrame(all_races).to_csv(RACES_CSV, index=False)
        print(f"ok   {year}: {len(races)} races, {len(rows)} driver rows")


if __name__ == "__main__":
    this_year = date.today().year
    main([int(y) for y in sys.argv[1:]] or list(range(this_year - 3, this_year + 1)))
