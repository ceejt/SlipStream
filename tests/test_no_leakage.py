import numpy as np
import pandas as pd

from f1pred.features import build


def _fake(n_races=8, n_drivers=6):
    rows, races = [], []
    for r in range(1, n_races + 1):
        for d in range(n_drivers):
            rows.append(dict(year=2024, round=r, Abbreviation=f"D{d}", TeamName=f"T{d // 2}",
                             GridPosition=d + 1, Position=d + 1, Status="Finished" if d else "Retired",
                             Points=max(0, 10 - d), quali_pos=d + 1, quali_time_s=80 + d * 0.1,
                             event=f"E{r}", location="Monza"))
        races.append(dict(year=2024, round=r, air_temp=25, track_temp=35, humidity=50,
                          rain_frac=0.0, safety_car=r % 2))
    circuits = pd.DataFrame([dict(location="Monza", lat=0, lon=0, altitude_m=162, is_street=0)])
    return pd.DataFrame(rows), pd.DataFrame(races), circuits


def test_first_race_has_no_history():
    df = build(*_fake())
    first = df[df["round"] == 1]
    assert first["driver_form_pos"].isna().all()
    assert first["circuit_dnf_rate"].isna().all()


def test_features_ignore_current_race_outcome():
    res, races, circuits = _fake()
    base = build(res, races, circuits)
    res2 = res.copy()
    last = res2["round"] == res2["round"].max()
    res2.loc[last, ["Position", "Status", "Points"]] = [20, "Retired", 0]
    changed = build(res2, races, circuits)
    cols = ["driver_form_pos", "driver_dnf_rate", "team_form_pts", "circuit_dnf_rate", "circuit_sc_rate"]
    a = base[base["round"] == base["round"].max()][cols].reset_index(drop=True)
    b = changed[changed["round"] == changed["round"].max()][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
