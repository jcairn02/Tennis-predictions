"""Report section for Stage A of "rating systems against Elo": the systems, their frozen constants, the tuning years'
log loss against Elo, how flat each tuning surface is, and the checks and probes.

Contract: SECTION and render(study_dir) -> {"html", "data", "script"}; every number from stageA_summary.json and
summary_results.json in study_dir (data/studies/rating_systems/).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": "A", "id": "stage-a", "title": "The rating systems, tuned and frozen"}
TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
PARAM_WORDS = {"rd0": "RD0", "sigma0": "σ", "tau": "τ", "gamma": "γ", "rho": "ρ", "window": "window (weeks)", "w": "surface weight"}
WHAT = {
    "glicko2": "Glickman's Glicko-2, a tournament week as the rating period: a player's games of the week scored together",
    "glicko1": "The same with the volatility fixed (Glicko-1)",
    "glicko2m": "Glicko-2 match by match: each round a rating period; the deviation grows with the time since the last match",
    "glicko1m": "The same with the volatility fixed",
    "trueskill": "TrueSkill for two players, no draws; its variance grows per match (τ) and per year (γ)",
    "glicko_cs": "A skill per surface, correlated ρ, updated by Glicko's step match by match",
    "trueskill_cs": "A skill per surface, correlated ρ, updated by TrueSkill's step",
    "ttt": "TrueSkill Through Time, causal: after each week, the last weeks' results re-scored against the current estimates",
    "ttt_hold": "The same at the same constants, with two-week events joining the model only two weeks after they start "
                "(a sensitivity, not tuned)",
}


def esc(x) -> str:
    return html.escape(str(x))


def mm(x, d=2) -> str:
    if x is None:
        return "–"
    s = f"{abs(x):.{d}f}"
    return ("−" if x < 0 and s.strip("0.") else "+") + s


def val(p, v) -> str:
    if p == "window":
        return f"{v:.0f}"
    if p == "rd0":
        return f"{v:.0f}"
    return f"{v:g}"


def render(study_dir: Path) -> dict:
    A = json.loads((Path(study_dir) / "stageA_summary.json").read_text(encoding="utf-8"))
    S = json.loads((Path(study_dir) / "summary_results.json").read_text(encoding="utf-8"))
    systems, names = S["systems"], S["names"]
    parts = ['''    <div class="prose">
      <p>Each system was built from wins and losses alone, over every singles match from 2010 at every level, under the
      earlier studies' time rule. Its constants were chosen on the log loss of the overall rating over the evaluation
      matches of 2013–2018, exactly as Stage 1 tuned Elo; the weight of the surface rating was chosen next. Where a best
      value lay on an edge of its grid, the grid was widened past it. Everything was then frozen.</p>
    </div>''']
    # constants and the tuning years
    rows = []
    for s in systems:
        cells = [f'<td><b>{esc(names[s])}</b><br><small class="muted">{esc(WHAT.get(s, ""))}</small></td>']
        for t in TOUR:
            c = S["constants"][f"{s}|{t}"]
            cs = ", ".join(f"{PARAM_WORDS.get(p, p)} {val(p, v)}" for p, v in c.items() if p != "w")
            if c.get("w"):
                cs += f"; surface weight {c['w']:.2f}"
            ll = S["tuning_log_loss"][t][s]
            cells.append(f'<td>{esc(cs)}</td><td class="r">{ll:.5f}<br><small class="muted">{mm(1000 * (S["tuning_log_loss"][t]["elo"] - ll))} vs Elo</small></td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    elo_row = "".join(f'<td>Stage 1\'s frozen K and surface weight</td><td class="r">{S["tuning_log_loss"][t]["elo"]:.5f}</td>'
                      for t in TOUR)
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>The frozen constants and the tuning years</h3><p>Log loss of each system's frozen
      forecast, evaluation matches of 2013–2018; "vs Elo" is milli-log-loss better (+) than surface Elo there</p></div>
      <div class="table-wrap"><table class="wide"><thead><tr><th>System</th><th>Men: constants</th><th class="r">Men, 2013–18</th>
        <th>Women: constants</th><th class="r">Women, 2013–18</th></tr></thead><tbody>
        <tr><td><b>Surface Elo</b></td>{elo_row}</tr>{"".join(rows)}</tbody></table></div>
      <p class="note-small" style="margin:10px 0 0">RD0 is a newcomer's Glicko deviation (rating points); σ the weekly drift
      (Glicko) or a newcomer's skill deviation (TrueSkill, whose performance noise β is 1); τ the volatility's
      volatility (Glicko-2) or a per-match drift (TrueSkill); γ the drift per square-root year; ρ the surfaces'
      correlation; the window the weeks TrueSkill Through Time re-scores after each week.</p>
    </div>''')
    # flatness
    fl_rows = []
    for s in systems:
        for t in TOUR:
            if f"{s}|{t}" not in A["flatness"]:
                continue
            f = A["flatness"][f"{s}|{t}"]
            by = "; ".join(f"{PARAM_WORDS.get(p, p)}: " + ", ".join(f"{k} {'+' if v > 0 else ''}{v:.2f}" for k, v in d.items())
                           for p, d in f["best_by_value"].items())
            fl_rows.append(f'<tr><td>{esc(names[s])}</td><td>{TOUR[t].split(" ")[0]}</td><td class="r">{f["settings"]}</td>'
                           f'<td class="r">{f["within_1_milli"]}</td><td><small>{esc(by)}</small></td></tr>')
    parts.append(f'''    <details class="twin"><summary>How flat each tuning surface is</summary>
      <p class="note-small">For each constant, the best log loss at each value tried (the others free), in milli-log-loss
      above the system's best; settings tried, and how many came within 1 milli-log-loss of the best.</p>
      <div class="table-wrap"><table class="wide"><thead><tr><th>System</th><th>Tour</th><th class="r">Settings</th>
      <th class="r">Within 1</th><th>Best by value</th></tr></thead><tbody>{"".join(fl_rows)}</tbody></table></div>
    </details>''')
    # checks
    ck = S["checks"]
    pr = ck["probes"]
    top = A.get("top10_end", {})
    tops = "".join(f'<li><b>{esc(names.get(s, s))}, {TOUR[t].split(" ")[0]}:</b> '
                   f'{esc(", ".join(p["name"] for p in v[t]))}</li>' for s, v in top.items() for t in TOUR if t in v)
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>Checks</h3></div>
      <ul class="plain">
        <li><b>The time rule.</b> A probe cut by date, event and round redrew every result each cut may not see and re-ran
        the pass ({pr["real_cuts"]} cuts over {len(pr["systems_probed"])} systems): {pr["protected_changed"]:,} of
        {pr["protected_checked"]:,} protected pre-match values moved. A deliberately leaky pass moved {pr["leaky_changed"]:,}.</li>
        <li><b>Tuning against the frozen pass.</b> Every tuning pass equals the frozen full pass's first rows (largest
        difference {ck["prefix_checks_max_abs"]:g}).</li>
        <li><b>The formulas</b> (<code>test/rating_systems/</code>): Glickman's worked Glicko-2 example and his Glicko-1 example, TrueSkill's update
        against the exact posterior integrated numerically, Landfried and Mocskos's published TrueSkill Through Time
        example, the correlated-surface model reducing to TrueSkill and to Glicko-1 at ρ = 1, and every pre-match value of
        random histories against a fresh pass over only what the rule lets it see.</li>
        <li><b>The ten highest-rated players at the end of the table</b> (a sanity check of the scale; players with at
        least 30 rated matches): <ul class="plain">{tops}</ul></li>
      </ul>
    </div>''')
    return {"html": "\n".join(parts), "data": {}, "script": ""}
