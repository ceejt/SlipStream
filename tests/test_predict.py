import pandas as pd

from f1pred.features import build
from f1pred.predict import predict_frame
from f1pred.report import render
from tests.test_no_leakage import _fake


def test_predict_uses_only_earlier_races_and_renders():
    df = build(*_fake(n_races=9))
    race_id = int(df["race_id"].max())
    out = predict_frame(df, race_id, min_train_races=3)
    assert len(out) == 6
    assert out["p_podium"].between(0, 1).all()
    assert out.iloc[0]["p_podium"] >= out.iloc[-1]["p_podium"]
    payload = {"year": 2024, "round": 9, "event": "<Test>", "mode": "backtest", "created_utc": "x",
               "trained_on_races": 8, "location": "Monza", "drivers": [
                   {"driver": r["Abbreviation"], "team": r["TeamName"], "grid": int(r["grid"]),
                    "p_podium": float(r["p_podium"]), "actual_position": int(r["position"]),
                    "reasons": r["reasons"]} for _, r in out.iterrows()]}
    html = render(payload)
    assert "&lt;Test&gt;" in html and "<Test>" not in html
