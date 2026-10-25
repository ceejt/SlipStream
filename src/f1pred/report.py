"""Render a prediction payload as one self-contained HTML page (no external assets)."""
import json
import sys
from html import escape

from .config import REPORTS

CSS = """
:root{--bg:#f6f6f8;--card:#fff;--text:#14141c;--muted:#6b6b7b;--line:#e3e3ea;--accent:#e10600;
--gold:#c9961a;--silver:#8e9196;--bronze:#b36a2c}
@media (prefers-color-scheme:dark){:root{--bg:#0e0e14;--card:#17171f;--text:#eeeef6;--muted:#8a8a9c;--line:#2a2a36}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.5rem;margin:0}.sub{color:var(--muted);margin:4px 0 24px}
.podium{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;border-top:4px solid var(--c)}
.card .pos{font-weight:700;color:var(--c)}.card .name{font-size:1.25rem;font-weight:700}
.card .team{color:var(--muted);font-size:.85rem}.card .p{margin-top:8px;font-size:1.1rem}
.why{margin:8px 0 0;padding:0;list-style:none;font-size:.8rem;color:var(--muted)}
.up{color:#1a8f4c}.down{color:var(--accent)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);font-size:.9rem}
th{color:var(--muted);font-weight:600}tr:last-child td{border-bottom:0}
.bar{height:8px;background:var(--line);border-radius:4px;min-width:80px}.bar i{display:block;height:100%;background:var(--accent);border-radius:4px}
.note{color:var(--muted);font-size:.8rem;margin-top:16px}
@media(max-width:560px){.podium{grid-template-columns:1fr}}
"""


def _reasons(rs):
    items = []
    for r in rs:
        cls, sign = ("up", "+") if r["shap"] > 0 else ("down", "-")
        items.append(f'<li><span class="{cls}">{sign}</span> {escape(r["feature"])} = {r["value"]}</li>')
    return "<ul class='why'>" + "".join(items) + "</ul>"


def render(p: dict) -> str:
    drivers = p["drivers"]
    colors = ["var(--gold)", "var(--silver)", "var(--bronze)"]
    cards = "".join(
        f'<div class="card" style="--c:{colors[i]}"><div class="pos">P{i + 1}</div>'
        f'<div class="name">{escape(d["driver"])}</div><div class="team">{escape(str(d["team"]))}'
        f' · grid {d["grid"]}</div><div class="p">{d["p_podium"] * 100:.0f}% podium</div>'
        f'{_reasons(d["reasons"])}</div>' for i, d in enumerate(drivers[:3]))
    show_actual = p["mode"] == "backtest"
    rows = "".join(
        f'<tr><td>{i + 1}</td><td>{escape(d["driver"])}</td><td>{escape(str(d["team"]))}</td><td>{d["grid"]}</td>'
        f'<td><div class="bar"><i style="width:{min(d["p_podium"], 1) * 100:.0f}%"></i></div></td>'
        f'<td>{d["p_podium"] * 100:.1f}%</td>'
        + (f'<td>{d["actual_position"] if d["actual_position"] is not None else "DNF"}</td>' if show_actual else "")
        + "</tr>" for i, d in enumerate(drivers))
    extra_th = "<th>Actual</th>" if show_actual else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SlipStream {p['year']} {escape(p['event'])}</title><style>{CSS}</style></head><body><main>
<h1>{escape(p['event'])} {p['year']}</h1>
<p class="sub">Podium prediction · {escape(p['mode'])} · trained on {p['trained_on_races']} earlier races · made {escape(p['created_utc'])}</p>
<div class="podium">{cards}</div>
<table><thead><tr><th>#</th><th>Driver</th><th>Team</th><th>Grid</th><th>Probability</th><th></th>{extra_th}</tr></thead>
<tbody>{rows}</tbody></table>
<p class="note">Probabilities are raw model outputs, not calibrated. Reasons show the three features that moved each score most
(+ raises, - lowers). Grid is the qualifying order, so penalties are not included.</p>
</main></body></html>"""


def write_report(payload: dict):
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{payload['year']}_R{payload['round']:02d}.html"
    path.write_text(render(payload))
    return path


if __name__ == "__main__":
    print(write_report(json.load(open(sys.argv[1]))))
