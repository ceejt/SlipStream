import pandas as pd

from f1pred.outcome import build_outcome


def _results(n):
    return pd.DataFrame({"year": 2026, "round": 18, "Abbreviation": [f"D{i}" for i in range(n)],
                         "Position": [i + 1 for i in range(n)], "Status": ["Finished"] * n})


def test_outcome_needs_a_full_race_in_the_data():
    assert build_outcome(_results(3), 2026, 18) is None
    assert build_outcome(_results(20), 2026, 17) is None


def test_outcome_lists_position_and_status_per_driver():
    o = build_outcome(_results(20), 2026, 18)
    assert o["drivers"]["D0"] == {"position": 1, "status": "Finished"} and len(o["drivers"]) == 20
