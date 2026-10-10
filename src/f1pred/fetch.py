"""Fetch race results, qualifying and race-day weather/safety-car info via FastF1.

Usage: python -m f1pred.fetch 2022 2023 2024
Writes data/raw/results.csv (one row per driver per race) and data/raw/races.csv
(one row per race). Safe to re-run: FastF1 caches downloads in data/cache.
"""
import sys

import fastf1
import pandas as pd

from .config import CACHE, RACES_CSV, RAW, RESULTS_CSV


def _best_quali_time(row):
    times = [row.get(c) for c in ("Q3", "Q2", "Q1")]
    times = [t for t in times if pd.notna(t)]
    return times[0].total_seconds() if times else float("nan")


def fetch_race(year: int, rnd: int):
    race = fastf1.get_session(year, rnd, "R")
    race.load(laps=True, telemetry=False, weather=True, messages=False)
    quali = fastf1.get_session(year, rnd, "Q")
    quali.load(laps=False, telemetry=False, weather=False, messages=False)

    res = race.results[["Abbreviation", "TeamName", "GridPosition", "Position", "Status", "Points"]].copy()
    q = quali.results[["Abbreviation", "Position", "Q1", "Q2", "Q3"]].copy()
    q["quali_time_s"] = q.apply(_best_quali_time, axis=1)
    q = q.rename(columns={"Position": "quali_pos"})[["Abbreviation", "quali_pos", "quali_time_s"]]
    df = res.merge(q, on="Abbreviation", how="left")
    df["year"], df["round"] = year, rnd
    df["event"] = race.event["EventName"]
    df["location"] = race.event["Location"]

    w = race.weather_data
    ts = race.track_status
    sc = int(ts["Status"].astype(str).isin(["4"]).any()) if ts is not None and len(ts) else 0
    vsc = int(ts["Status"].astype(str).isin(["6"]).any()) if ts is not None and len(ts) else 0
    race_row = {
        "year": year, "round": rnd, "event": race.event["EventName"],
        "location": race.event["Location"], "date": race.event["EventDate"],
        "air_temp": w["AirTemp"].mean(), "track_temp": w["TrackTemp"].mean(),
        "humidity": w["Humidity"].mean(), "rain_frac": float(w["Rainfall"].mean()),
        "safety_car": sc, "vsc": vsc,
    }
    return df, race_row


def main(years):
    RAW.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE))
    all_rows, race_rows = [], []
    for year in years:
        sched = fastf1.get_event_schedule(year, include_testing=False)
        for rnd in sched["RoundNumber"]:
            if sched.loc[sched["RoundNumber"] == rnd, "EventDate"].iloc[0] > pd.Timestamp.now():
                continue
            try:
                df, rr = fetch_race(year, int(rnd))
            except Exception as e:
                print(f"skip {year} R{rnd}: {e}")
                continue
            all_rows.append(df)
            race_rows.append(rr)
            print(f"ok   {year} R{rnd} {rr['event']}")
    pd.concat(all_rows, ignore_index=True).to_csv(RESULTS_CSV, index=False)
    pd.DataFrame(race_rows).to_csv(RACES_CSV, index=False)


if __name__ == "__main__":
    main([int(y) for y in sys.argv[1:]] or [2023, 2024])
