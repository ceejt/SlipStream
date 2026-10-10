# f1-podium-predictor

Podium prediction with one rule: a feature for race N only uses what is known before race N.

## Setup
    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

## Run
    .venv/bin/python -m f1pred.fetch 2022 2023 2024   # slow the first time, cached after
    .venv/bin/python -m f1pred.evaluate               # walk-forward vs baselines
    .venv/bin/pytest                                  # leakage tests

## Layout
- `src/f1pred/fetch.py`: FastF1 to `data/raw/` (results, quali, weather, safety car)
- `src/f1pred/features.py`: leak-free rolling driver, team and circuit features
- `src/f1pred/evaluate.py`: walk-forward split, baselines, metrics
- `data/circuits.csv`: static circuit attributes (starter rows, verify values, add the rest)

## Roadmap
1. Fetch 2018 to 2025 and read the first honest baseline numbers
2. Separate DNF model: P(podium) = P(finish) x P(top 3 | finish)
3. Weather forecast input (Open-Meteo) in place of observed race weather
4. FP2 long-run pace and tire degradation slope
5. Climate table per circuit and month; more circuit attributes
6. SHAP explanations, calibration, dashboard, public prediction log
