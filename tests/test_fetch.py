import math

from f1pred.fetch import _seconds, season_rows


def _race(rnd, rows):
    return {"round": str(rnd), "raceName": f"GP{rnd}", "date": "2025-03-16",
            "Circuit": {"Location": {"locality": "Monza"}}, "Results": rows}


def _res(code, pos, grid):
    return {"Driver": {"code": code, "familyName": "X"}, "Constructor": {"name": "T"},
            "grid": str(grid), "position": str(pos), "status": "Finished", "points": "25"}


def test_seconds_parses_lap_times_and_blanks():
    assert _seconds("1:15.096") == 75.096
    assert math.isnan(_seconds(""))
    assert math.isnan(_seconds(None))


def test_season_rows_uses_best_quali_session_and_handles_missing():
    results = {1: _race(1, [_res("AAA", 1, 2), _res("BBB", 2, 1)])}
    quali = {1: {"QualifyingResults": [
        {"Driver": {"code": "AAA"}, "position": "2", "Q1": "1:20.000", "Q2": "1:19.000", "Q3": "1:18.500"},
        {"Driver": {"code": "BBB"}, "position": "1", "Q1": "1:20.000", "Q2": "1:19.000", "Q3": ""}]}}
    rows, races = season_rows(2025, results, quali)
    assert [r["quali_time_s"] for r in rows] == [78.5, 79.0]
    assert races == [{"year": 2025, "round": 1, "event": "GP1", "location": "Monza", "date": "2025-03-16"}]
    # a race with no qualifying data still yields rows
    rows, _ = season_rows(2025, results, {})
    assert all(math.isnan(r["quali_time_s"]) for r in rows)
