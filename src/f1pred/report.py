"""Render a prediction payload as one self-contained HTML page (no external assets)."""
import json
import re
import sys
from html import escape

import pandas as pd

from .config import EVALUATION, OUTCOMES, PREDICTIONS, REPORTS, RESULTS_CSV

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap" rel="stylesheet">'
)

# Team color (stripe) and card color (dark shade that keeps white text readable),
# both from formula1.com: the team logos on /en/results/2026/team and the driver
# cards on /en/drivers. Order matters: "racing bulls" before "red bull".
TEAM_COLORS = [
    ("racing bulls", "#6692FF", "#0038C2"), ("rb f1", "#6692FF", "#0038C2"),
    ("red bull", "#3671C6", "#142948"), ("mercedes", "#27F4D2", "#067E6A"),
    ("ferrari", "#E8002D", "#5C0012"), ("mclaren", "#FF8000", "#804000"),
    ("aston martin", "#229971", "#0F4331"), ("alpine", "#00A1E8", "#004E70"),
    ("audi", "#FF2D00", "#751500"), ("cadillac", "#AAAAAD", "#58585B"),
    ("williams", "#1868DB", "#082145"), ("haas", "#DEE1E2", "#667175"),
]

CSS = """
:root{--red:#E10600;--red-deep:#CA0500;--red-tint:#F6B4B2;
--bg:#15151E;--surface:#26262B;--surface-2:#303037;--rule:#47464C;
--text:#FFFFFF;--muted:#AAAAAA;--tag:var(--red-tint);--chrome-lo:#8A8A92;--chrome-hi:#FFFFFF;--chrome-edge:rgba(255,255,255,.18);
--display:"Formula1","Titillium Web",system-ui,sans-serif;--body:"Titillium Web",system-ui,sans-serif}
@media (prefers-color-scheme:light){:root{--bg:#F7F4F1;--surface:#FFFFFF;--surface-2:#E0DEDC;--rule:#CDCDCD;
--text:#15151E;--muted:#606066;--tag:var(--red-deep);--chrome-lo:#15151E;--chrome-hi:#5A5A62;--chrome-edge:rgba(0,0,0,.12)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:600 14px/16px var(--body)}
::selection{background:var(--red);color:#FFFFFF}
:focus-visible{outline:2px solid var(--text);outline-offset:2px}
main{max-width:973px;margin:0 auto;padding:24px 16px 48px}
@media(min-width:735px){main{padding:32px 24px 64px}}
@media(min-width:1069px){main{padding:32px 32px 64px}}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:0 0 32px;
padding-bottom:12px;border-bottom:1px solid var(--rule)}
.brand{font:900 16px/22px var(--display);text-transform:uppercase;letter-spacing:.5px;margin:0}
.back{color:var(--text);text-decoration:none;border:1px solid var(--rule);border-radius:4px;padding:4px 12px;
font:600 14px/20px var(--body);transition:background-color .15s cubic-bezier(.4,0,.2,1)}
.back:hover{background:var(--surface-2)}
.brand a{color:inherit;text-decoration:none}
.brand a:hover{text-decoration:underline;text-underline-offset:4px}
h1{font:900 32px/38px var(--display);text-transform:uppercase;text-wrap:balance;margin:0 0 12px}
@media(min-width:735px){h1{font-size:40px;line-height:44px}}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;color:var(--muted);margin:0 0 16px}
.tag{border:1px solid var(--tag);color:var(--tag);border-radius:4px;padding:2px 8px;
font:500 12px/16px var(--display);text-transform:uppercase;letter-spacing:.5px}
.tag.back{border-color:var(--muted);color:var(--muted)}
.claim{font:400 16px/24px var(--body);max-width:68ch;margin:0 0 32px}
.summary{font:600 16px/24px var(--body);margin:0 0 16px}
.label{font:500 12px/16px var(--display);text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 12px}
.podium{display:grid;grid-template-columns:1fr;gap:12px;margin-bottom:48px}
@media(min-width:735px){.podium{grid-template-columns:repeat(3,1fr)}}
.card{background:var(--card-bg,var(--surface-2));color:var(--on,var(--text));border-radius:8px;padding:16px;
display:grid;grid-template-columns:1fr auto;gap:12px 16px}
@media(min-width:735px){.card{display:flex;flex-direction:column;min-height:256px}}
.pick{font:500 12px/16px var(--display);text-transform:uppercase;letter-spacing:.5px;margin:0 0 8px}
.first{font:400 20px/24px var(--display);margin:0}
.last{font:700 28px/32px var(--display);margin:0;overflow-wrap:anywhere}
@media(min-width:735px){.last{font-size:32px;line-height:36px}}
.team{font:600 14px/16px var(--body);margin:8px 0 0}
.score{align-self:end;text-align:right}
@media(min-width:735px){.score{align-self:stretch;margin-top:auto;padding-top:16px;text-align:left}}
.pct{font:700 36px/40px var(--body);margin:0;font-variant-numeric:tabular-nums}
.sub{font:600 14px/16px var(--body);margin:0}
.outcome{grid-column:1/-1;margin:0;display:flex;align-items:center;gap:8px;font:600 16px/20px var(--body)}
.why{grid-column:1/-1;margin:0;padding:0;list-style:none;font:600 14px/20px var(--body)}
.why b{display:inline-block;width:12px;font-weight:400}
.mark{display:inline-block;padding:0 6px;border:1px solid currentColor;border-radius:4px;
font:500 12px/18px var(--display);letter-spacing:.5px;text-transform:uppercase}
.mark.miss{border-style:dashed}
td .mark.miss{border-color:var(--muted);color:var(--muted)}
td .mark{border-color:var(--text)}
table{width:100%;border-collapse:collapse}
.scroll{overflow-x:auto;scrollbar-color:var(--rule) transparent}
th,td{padding:12px 6px;text-align:left;border-bottom:1px solid var(--rule)}
th{font:500 12px/16px var(--display);text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding-bottom:8px}
td{height:44px;transition:background-color .15s cubic-bezier(.4,0,.2,1)}
tbody tr:hover td{background:var(--surface-2)}
.num{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.fin{white-space:nowrap}
.cell{display:flex;align-items:center;gap:12px;font:500 16px/22px var(--display);text-transform:uppercase}
.sv{flex:none;width:4px;height:24px;background:var(--team);box-shadow:inset 0 0 0 1px var(--rule)}
.unmapped .sv{background:transparent;box-shadow:inset 0 0 0 1px var(--muted)}
.team-col{display:none;color:var(--muted)}
@media(min-width:735px){.team-col{display:table-cell}th,td{padding:12px 8px}}
.pb{display:flex;align-items:center;gap:8px}
@media(min-width:735px){.pb{gap:12px}}
.bar{flex:1;height:8px;background:var(--surface-2);border-radius:4px;min-width:32px}
@media(min-width:735px){.bar{min-width:120px}}
.bar i{display:block;height:100%;min-width:2px;background:var(--red);border-radius:4px;
animation:grow .3s cubic-bezier(.4,0,.2,1) both;animation-delay:calc(var(--i)*30ms)}
@keyframes grow{from{width:0}}
.pv{flex:none;width:48px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.made{margin:48px 0 0;padding-top:16px;border-top:1px solid var(--rule);color:var(--muted);font:600 14px/20px var(--body)}
.made a{color:var(--text);font-weight:700;text-decoration:underline;text-decoration-color:var(--muted);text-underline-offset:3px}
@supports (background-clip:text) or (-webkit-background-clip:text){
.made a{background:repeating-linear-gradient(105deg,var(--chrome-lo) 0,var(--chrome-hi) 9px,var(--chrome-lo) 18px) 0 0/300% 100%;
-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent;
font:900 17px/20px var(--body);transition:background-position .8s cubic-bezier(.4,0,.2,1);
filter:drop-shadow(0 1px 0 var(--chrome-edge))}
.made a:hover,.made a:focus-visible{background-position:-9px 0}}
.races{list-style:none;margin:0 0 16px;padding:0}
.races a{display:grid;grid-template-columns:1fr auto;gap:4px 16px;padding:16px 8px;border-bottom:1px solid var(--rule);
color:var(--text);text-decoration:none;transition:background-color .15s cubic-bezier(.4,0,.2,1)}
.races a:hover{background:var(--surface-2)}
.races .ev{font:700 20px/24px var(--display);text-transform:uppercase}
.races .meta2{color:var(--muted);font:600 14px/20px var(--body);margin:0}
.races .when{color:var(--muted);font:500 12px/16px var(--display);text-transform:uppercase;letter-spacing:.5px;text-align:right}
.method{margin-top:64px;max-width:68ch}
.method h3{font:700 20px/24px var(--body);margin:32px 0 8px}
.method p,.method li{font:400 16px/24px var(--body);margin:0 0 12px}
.method ul{margin:0 0 12px;padding-left:20px}
.method li{margin-bottom:8px}
.method .scroll{margin:16px 0;max-width:none}
.method caption{caption-side:top;text-align:left;color:var(--muted);font:600 14px/20px var(--body);padding-bottom:8px}
.note{color:var(--muted);font:400 14px/20px var(--body);max-width:68ch;margin:32px 0 0}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

FINISHED = re.compile(r"Finished|Lap")

# Vercel Web Analytics for plain HTML. The script is served by Vercel itself, so it
# does nothing (and fails quietly) when a page is opened from disk.
ANALYTICS = ('<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script>'
             '<script defer src="/_vercel/insights/script.js"></script>')

BRAND = ('<p class="brand"><a href="https://github.com/ceejt/SlipStream" target="_blank" rel="noopener noreferrer" '
         'aria-label="SlipStream, source code on GitHub (opens in a new tab)">SlipStream</a></p>')

def _top(back=False):
    """Top bar: wordmark on the left, and on race pages a button back to the index."""
    link = '<a class="back" href="index.html">Back to all races</a>' if back else ""
    return f'<header class="top">{BRAND}{link}</header>'


CREDIT = ('<footer class="made">Made by <a href="https://ceejt-portfolio.vercel.app/" '
          'target="_blank" rel="noopener noreferrer">ceejt</a></footer>')


def _ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _team_info(team):
    """(stripe color, card color) for a team, or None if no verified color is on file."""
    name = str(team).lower()
    return next(((c, card) for key, c, card in TEAM_COLORS if key in name), None)


def _team_style(team):
    """Inline style and class for the table stripe. Unknown teams get a hollow stripe."""
    info = _team_info(team)
    return (f' style="--team:{info[0]}"', "") if info else ("", " unmapped")


def _card_style(team):
    """Card colors: F1's dark team shade with white text, or the neutral surface."""
    info = _team_info(team)
    return f' style="--card-bg:{info[1]};--on:#FFFFFF"' if info else ""


def _names(code, names):
    """(first, last) for a driver code, falling back to the code itself."""
    first, last = (names or {}).get(code, ("", ""))
    return (escape(first), escape(last)) if last else ("", escape(code))


def _reason_text(feature, value):
    """Plain wording for a model feature and its value."""
    v = value
    if v is None:
        return escape(feature.replace("_", " "))
    text = {
        "grid": lambda: f"Starts {_ordinal(v)}",
        "quali_pos": lambda: f"Qualified {_ordinal(v)}",
        "quali_gap_s": lambda: "Set the pole time" if v < 0.0005 else f"{v:.3f} s off pole",
        "driver_form_pos": lambda: f"Recent average finish of {v:.1f}",
        "driver_dnf_rate": lambda: f"Retires in {v * 100:.0f}% of races",
        "team_form_pts": lambda: f"Team averages {v:.0f} points a race lately",
        "team_dnf_rate": lambda: f"Team cars retire in {v * 100:.0f}% of starts",
        "circuit_dnf_rate": lambda: f"{v * 100:.0f}% of cars retire at this circuit",
        "circuit_pos_gain": lambda: f"Drivers move {v:.1f} places here on average",
        "altitude_m": lambda: f"Altitude {v:.0f} m",
        "is_street": lambda: "Street circuit" if v >= 0.5 else "Permanent circuit",
    }.get(feature)
    return escape(text()) if text else escape(f"{feature.replace('_', ' ')} = {v}")


def _reasons(rs):
    items = []
    for r in rs:
        sign = "+" if r["shap"] > 0 else "-"
        items.append(f'<li><b>{sign}</b> {_reason_text(r["feature"], r["value"])}</li>')
    return "<ul class='why' aria-label='Reasons, strongest first'>" + "".join(items) + "</ul>"


def _beats(ev):
    """True if the model beats both grid baselines on every key metric, False if not, None if unknown."""
    try:
        m = ev["models"]
        x, g, o = m["xgboost"], m["grid logistic"], m["grid order"]
        return bool(x["brier"] < g["brier"] and x["logloss"] < g["logloss"]
                    and x["top3_overlap"] > o["top3_overlap"])
    except (KeyError, TypeError):
        return None


def _baseline_line(ev):
    """One sentence on how the model compares with grid baselines, from the saved evaluation."""
    beat = _beats(ev)
    if beat is None:
        return ""
    span = f'{ev["races"]} races through {ev["through"]["year"]} round {ev["through"]["round"]}'
    verdict = ("Has beaten a grid-order baseline on Brier score, log loss and top-3 overlap"
               if beat else "Has not yet beaten a grid-order baseline")
    return f"{verdict} ({span})."


def _method_table(ev):
    """Small comparison table from the saved evaluation, or empty text if there is none."""
    if _beats(ev) is None:
        return ""
    rows = ""
    for key, label in (("grid order", "First three on the grid"), ("grid logistic", "Formula on grid position only"),
                       ("xgboost", "SlipStream model")):
        m = ev["models"][key]
        pct = lambda v: "n/a" if v is None else f"{v * 100:.1f}%"
        num = lambda v: "n/a" if v is None else f"{v:.3f}"
        rows += (f'<tr><td>{label}</td><td class="num">{pct(m["top3_overlap"])}</td><td class="num">{pct(m["exact_podium"])}</td>'
                 f'<td class="num">{num(m["brier"])}</td><td class="num">{num(m["logloss"])}</td></tr>')
    span = f'{ev["races"]} races, through {ev["through"]["year"]} round {ev["through"]["round"]}'
    return (f'<div class="scroll"><table><caption>{span}</caption><thead><tr><th scope="col">Method</th>'
            '<th scope="col" class="num">Top-3 overlap</th><th scope="col" class="num">Exact podium</th>'
            '<th scope="col" class="num">Brier score</th><th scope="col" class="num">Log loss</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _method_html(ev):
    """The "How it works" section, in plain words. Numbers come from the saved evaluation."""
    beat = _beats(ev)
    verdict = ""
    if beat is True:
        verdict = "<p>On every one of these measures the model does better than both simple guesses.</p>"
    elif beat is False:
        verdict = ("<p>So far the model has not clearly beaten the two simple guesses, so treat its picks with care. "
                   "That is why the top of each page says so.</p>")
    return f"""<section class="method" aria-labelledby="how">
<h2 class="label" id="how">How it works</h2>
<h3>What the model looks at</h3>
<p>For every driver in a race, the model gets a short list of facts that were known before the start:</p>
<ul>
<li>Where the driver starts, where they qualified, and how far they were from the pole time.</li>
<li>How they finished in their last five races, and how often they retire.</li>
<li>How many points their team has scored lately, and how often the team's cars retire.</li>
<li>How often cars retire at this circuit, how many places drivers usually gain or lose there, whether it is a street circuit, and its altitude.</li>
</ul>
<p>Nothing from the race itself is ever used. That is the one rule the project is built around: a prediction for a race only uses what was known before that race.</p>
<h3>How it turns facts into a percentage</h3>
<p>The model is XGBoost. It builds many small decision trees. Each tree asks simple questions, like "does this driver start in the top three?" or "has this team been scoring well?", and nudges the answer a little. Together, the trees settle on one number.</p>
<p>To learn, the model looks at every earlier race. For each driver it sees the facts above and whether they finished on the podium (the top three). Over time it learns which combinations of facts usually lead to a podium. For a new race, it gives each driver a number from 0% to 100%: how likely that driver is to finish in the top three, judging by how similar drivers did before. It is not a simulation of the race.</p>
<p>Each driver gets their own number, and a podium has three places, so across the whole field the numbers add up to around 300%, not 100%. A driver at 80% is not "80% to win". It means the model thinks a podium is very likely.</p>
<h3>Why each pick has reasons</h3>
<p>Under each of the three picks you see the three facts that moved the number most. They come from a method called SHAP. A plus sign means the fact raised the driver's chance. A minus sign means it lowered it. The strongest comes first.</p>
<h3>How it is checked</h3>
<p>A model can look clever by accident if it has already seen the answers. So every race is tested like this: pretend it is the day before that race, teach the model only with earlier races, make the predictions, then compare them with what really happened. This is called walk-forward testing, and it is repeated for every race after the first five.</p>
<p>The model is also compared with two simple guesses. One says the first three on the grid will finish on the podium. The other is a basic formula that only looks at starting position. If the model cannot beat these, it has not added anything useful.</p>
{_method_table(ev)}
<p>Top-3 overlap is the share of the real podium drivers that were in the model's top three picks. Exact podium counts the races where all three picks were right. Brier score and log loss judge the percentages themselves. For both of those, lower is better.</p>
{verdict}<h3>What it does not know</h3>
<p>It does not know about grid penalties, because it uses the qualifying order. It also knows nothing about weather, tyre choices, safety cars or car upgrades, and it has only a few seasons of results, so some circuits have little history. The percentages are raw model output. They have not been checked for calibration, so a "70%" may not come true seven times in ten.</p>
<p>Treat the numbers as a ranking of who looks strongest, not as a promise. Results and qualifying come from the Jolpica F1 API.</p>
</section>"""


def _outcome(d):
    """Finished text for a driver in a backtest: ('DNF' | ordinal | None)."""
    status, pos = d.get("status"), d.get("actual_position")
    if status is not None and not FINISHED.search(status):
        return "DNF"
    return None if pos is None else _ordinal(pos)


def _load_outcome(p):
    """The saved result for a prediction, or None if the race has not been scored yet."""
    f = OUTCOMES / f'{p["year"]}_R{p["round"]:02d}.json'
    return json.loads(f.read_text()) if f.exists() else None


def _apply_outcome(p, o):
    """A copy of the prediction with the real result filled in. The saved prediction is never changed."""
    if not o:
        return p
    drivers = []
    for d in p["drivers"]:
        got = o["drivers"].get(d["driver"], {})
        drivers.append(dict(d, actual_position=got.get("position"), status=got.get("status")))
    return dict(p, mode="scored", outcome_utc=o["created_utc"], drivers=drivers)


def _is_hit(d):
    return _outcome(d) not in (None, "DNF") and d["actual_position"] <= 3


def render(p: dict, evaluation=None, names=None) -> str:
    drivers = p["drivers"]
    picks = drivers[:3]
    backtest = p["mode"] in ("backtest", "scored")
    evaluation = p.get("evaluation") or evaluation

    cards = ""
    for i, d in enumerate(picks):
        grid = f'starts {_ordinal(d["grid"])}' if d["grid"] is not None else "grid unknown"
        first, last = _names(d["driver"], names)
        out = ""
        if backtest:
            res = _outcome(d)
            text = {"DNF": "Did not finish", None: "Result missing"}.get(res, f"Finished {res}")
            mark = '<span class="mark">Hit</span>' if _is_hit(d) else '<span class="mark miss">Miss</span>'
            out = f'<p class="outcome">{mark} {text}</p>'
        cards += (
            f'<article class="card"{_card_style(d["team"])}><div><p class="pick">Pick {i + 1}</p>'
            + (f'<p class="first">{first}</p>' if first else "")
            + f'<p class="last">{last}</p><p class="team">{escape(str(d["team"]))} · {grid}</p></div>'
            f'<div class="score"><p class="pct">{d["p_podium"] * 100:.1f}%</p><p class="sub">podium probability</p></div>'
            f'{out}{_reasons(d["reasons"])}</article>')

    summary = ""
    if backtest:
        hits = sum(_is_hit(d) for d in picks)
        missed = sorted((d for d in drivers[3:] if _is_hit(d)), key=lambda d: d["actual_position"])
        summary = f"{hits} of 3 picks finished on the podium."
        if missed:
            summary += " On the podium but not picked: " + ", ".join(
                f'{escape(d["driver"])} ({_ordinal(d["actual_position"])})' for d in missed) + "."
        summary = f'<p class="summary">{summary}</p>'

    pick_codes = {d["driver"] for d in picks}
    rows = ""
    for i, d in enumerate(drivers):
        style, cls = _team_style(d["team"])
        extra = ""
        if backtest:
            res = _outcome(d)
            call = ""
            if d["driver"] in pick_codes:
                call = '<span class="mark">Hit</span> ' if _is_hit(d) else '<span class="mark miss">Miss</span> '
            extra = f'<td class="num fin">{call}{"n/a" if res is None else res}</td>'
        grid = d["grid"] if d["grid"] is not None else "-"
        rows += (
            f'<tr class="{cls.strip()}"{style}><td class="num">{i + 1}</td>'
            f'<td><div class="cell"><span class="sv"></span>{escape(d["driver"])}</div></td>'
            f'<td class="team-col">{escape(str(d["team"]))}</td><td class="num">{grid}</td>'
            f'<td><div class="pb"><div class="bar" aria-hidden="true">'
            f'<i style="width:{min(d["p_podium"], 1) * 100:.1f}%;--i:{i}"></i></div>'
            f'<span class="pv">{d["p_podium"] * 100:.1f}%</span></div></td>{extra}</tr>')
    extra_th = '<th scope="col" class="num">Finished</th>' if backtest else ""

    made = escape(p["created_utc"][:16].replace("T", " ")) + " UTC"
    result_added = (f'<span>Result added {escape(p["outcome_utc"][:16].replace("T", " "))} UTC</span>'
                    if p.get("outcome_utc") else "")
    tag = f'<span class="tag{" back" if backtest else ""}">{escape(p["mode"])}</span>'
    claim = " ".join(s for s in (
        "Raw model output, not calibrated.", _baseline_line(evaluation),
        "Grid is the qualifying order, so penalties are not included.") if s)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SlipStream {p['year']} {escape(p['event'])}</title>{FONT_LINK}{ANALYTICS}<style>{CSS}</style></head><body><main>
{_top(True)}
<h1>{escape(p['event'])}</h1>
<p class="meta">{tag}<span>Round {p['round']}, {p['year']}</span><span>Trained on {p['trained_on_races']} earlier races</span><span>Made {made}</span>{result_added}</p>
<p class="claim">{escape(claim)}</p>
{summary}<h2 class="label">Highest podium probability</h2>
<section class="podium">{cards}</section>
<h2 class="label">Full field</h2>
<div class="scroll"><table><thead><tr><th scope="col" class="num">Rank</th><th scope="col">Driver</th><th scope="col" class="team-col">Team</th>
<th scope="col" class="num">Grid</th><th scope="col">Podium probability</th>{extra_th}</tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="note">Probabilities are independent for each driver, so they do not add up to 100%. Reasons are the three features that moved a pick's score most, strongest first: + raised it, - lowered it.</p>
{_method_html(evaluation)}
{CREDIT}
</main></body></html>"""


def _name_lookup():
    """Driver code -> (given, family), taken from the latest rows of results.csv."""
    if not RESULTS_CSV.exists():
        return {}
    df = pd.read_csv(RESULTS_CSV)
    if "FamilyName" not in df.columns:
        return {}
    latest = df.sort_values(["year", "round"]).drop_duplicates("Abbreviation", keep="last")
    return {r.Abbreviation: (str(r.GivenName) if pd.notna(r.GivenName) else "", str(r.FamilyName))
            for r in latest.itertuples() if pd.notna(r.FamilyName)}


def render_index(items, evaluation=None, names=None):
    """Landing page: one row per saved prediction, newest first."""
    rows = ""
    for p in items:
        top = p["drivers"][0]
        first, last = _names(top["driver"], names)
        who = f"{first} {last}".strip()
        backtest = p["mode"] in ("backtest", "scored")
        hits = sum(_is_hit(d) for d in p["drivers"][:3])
        detail = f'Top pick {who}, {top["p_podium"] * 100:.1f}% podium probability'
        status = f"{hits} of 3 picks on the podium" if backtest else "Waiting for the race"
        rows += (f'<li><a href="{p["year"]}_R{p["round"]:02d}.html"><span><span class="ev">{escape(p["event"])}</span>'
                 f'<p class="meta2">{detail}</p></span><span class="when">Round {p["round"]}, {p["year"]}<br>{status}</span></a></li>')
    if not rows:
        rows = '<li><p class="meta2" style="padding:16px 8px">No predictions yet.</p></li>'
    claim = " ".join(s for s in ("Raw model output, not calibrated.", _baseline_line(evaluation)) if s)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SlipStream</title>{FONT_LINK}{ANALYTICS}<style>{CSS}</style></head><body><main>
{_top()}
<h1>Formula 1 podium predictions</h1>
<p class="claim">Made after qualifying and saved before the race, then compared with the result. {escape(claim)}</p>
<h2 class="label">Races</h2>
<ul class="races">{rows}</ul>
{_method_html(evaluation)}
{CREDIT}
</main></body></html>"""


def write_index(fallback=None, names=None):
    items = [json.loads(f.read_text()) for f in PREDICTIONS.glob("*.json")]
    items = [_apply_outcome(p, _load_outcome(p)) for p in items]
    items.sort(key=lambda p: (p["year"], p["round"]), reverse=True)
    ev = (items[0].get("evaluation") if items else None) or fallback
    path = REPORTS / "index.html"
    path.write_text(render_index(items, ev, names))
    return path


def write_report(payload: dict):
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = _apply_outcome(payload, _load_outcome(payload))
    fallback = json.loads(EVALUATION.read_text()) if EVALUATION.exists() else None
    names = _name_lookup()
    path = REPORTS / f"{payload['year']}_R{payload['round']:02d}.html"
    path.write_text(render(payload, fallback, names))
    write_index(fallback, names)
    return path


if __name__ == "__main__":
    print(write_report(json.load(open(sys.argv[1]))))
