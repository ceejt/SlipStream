"""Small client for the Jolpica F1 API (the Ergast successor). No login needed.

Limits are about 4 calls/s and 200 calls/h, so calls are spaced out and pages of
finished seasons are cached on disk. The current season is never cached.
"""
import hashlib
import json
import time
from datetime import date

import requests

from .config import CACHE

BASE = "https://api.jolpi.ca/ergast/f1"
PAGE = 100
_last_call = 0.0


def _fetch(url, params):
    global _last_call
    for attempt in range(4):
        wait = 0.3 - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429:
            delay = float(r.headers.get("Retry-After", 5 * (attempt + 1)))
            if delay > 120:
                raise RuntimeError(f"Jolpica rate limit hit, retry in {delay / 60:.0f} min")
            time.sleep(delay)
            continue
        r.raise_for_status()
        return r.json()["MRData"]
    raise RuntimeError(f"Jolpica kept returning 429 for {url}")


def get(path, year=None, **params):
    """GET one page and return its MRData dict."""
    url = f"{BASE}/{path}.json"
    cacheable = year is not None and year < date.today().year
    if cacheable:
        key = hashlib.md5(f"{url}{sorted(params.items())}".encode()).hexdigest()
        file = CACHE / "jolpica" / f"{key}.json"
        if file.exists():
            return json.loads(file.read_text())
    data = _fetch(url, params)
    if cacheable:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data))
    return data


def season(year, kind):
    """All races of a season from /results or /qualifying, keyed by round.

    A race can be split across pages, so rows are merged by round.
    """
    rows_key = "Results" if kind == "results" else "QualifyingResults"
    out, offset = {}, 0
    while True:
        m = get(f"{year}/{kind}", year, limit=PAGE, offset=offset)
        for race in m["RaceTable"]["Races"]:
            rnd = int(race["round"])
            if rnd in out:
                out[rnd][rows_key].extend(race[rows_key])
            else:
                out[rnd] = race
        offset += PAGE
        if offset >= int(m["total"]):
            return out
