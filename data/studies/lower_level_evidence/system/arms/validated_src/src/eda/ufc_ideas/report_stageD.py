"""Report section for Stage D: the individual-statistic profiles together against the odds (part 2, the lead), and the
best inputs of both studies together (part 1). Every number from stageD_profile_summary.json, stageD_summary.json and
the two rankings."""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": "D", "id": "stage-d", "title": "Together: the statistics profiles, and everything"}
TOUR_LONG = {"atp": "ATP (men)", "wta": "WTA (women)"}
TOURS = ("atp", "wta")


def esc(x) -> str:
    return html.escape(str(x))


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def f2(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:+.2f}"


def rng(lo, hi) -> str:
    a, b = num(lo), num(hi)
    return "" if a is None or b is None else f" ({a:+.2f} to {b:+.2f})"


def pc(x) -> str:
    v = num(x)
    return "–" if v is None else f"{100 * v:.0f}%"


def cell(h: dict, key: str, lo: str | None = None, hi: str | None = None, line: str | None = None) -> str:
    s = f2(h.get(key))
    if lo and hi:
        s += esc(rng(h.get(lo), h.get(hi)))
    if line and h.get(line):
        s += " ✓"
    return f'<td class="r">{s}</td>'


def render(study_dir: Path) -> dict:
    d = Path(study_dir)
    P = json.loads((d / "stageD_profile_summary.json").read_text(encoding="utf-8"))
    S = json.loads((d / "stageD_summary.json").read_text(encoding="utf-8"))
    ph, pm = P["headline"], {m["id"]: m for m in P["models"]}
    sh, sm, lad = S["headline"], {m["id"]: m for m in S["models"]}, S["ladder"]
    has_bt = S.get("has_bt", False)
    adj = {t: ph.get(f"{t}|profile_adjperf", {}) for t in TOURS}
    ev = {t: sh.get(f"{t}|everything", {}) for t in TOURS}
    tiles = f'''    <div class="tiles">
      <div class="tile"><div class="label">The adjperf profile of twelve individual statistics, given the closing odds</div><div class="pair">
        <div><small>ATP</small><div class="value">{f2(adj["atp"].get("market_imp"))}</div></div>
        <div><small>WTA</small><div class="value">{f2(adj["wta"].get("market_imp"))}</div></div></div>
        <div class="note">milli-log-loss better than the odds alone, all scored seasons; in 2022–2026 {f2(adj["atp"].get("market_2022-2026"))} (men) and {f2(adj["wta"].get("market_2022-2026"))} (women)</div></div>
      <div class="tile"><div class="label">The same profile, given Elo</div><div class="pair">
        <div><small>ATP</small><div class="value">{f2(adj["atp"].get("elo_imp"))}</div></div>
        <div><small>WTA</small><div class="value">{f2(adj["wta"].get("elo_imp"))}</div></div></div>
        <div class="note">as much as the points-won aggregates add, from statistics that alone are {f2(adj["atp"].get("alone_imp"))} / {f2(adj["wta"].get("alone_imp"))} better than a coin</div></div>
      <div class="tile"><div class="label">Everything together, given Elo and given the odds</div><div class="pair">
        <div><small>ATP</small><div class="value">{f2(ev["atp"].get("elo_imp"))}</div></div>
        <div><small>WTA</small><div class="value">{f2(ev["wta"].get("elo_imp"))}</div></div></div>
        <div class="note">given Elo; given the odds {f2(ev["atp"].get("market_imp"))} (men) and {f2(ev["wta"].get("market_imp"))} (women)</div></div>
      <div class="tile"><div class="label">Elo + everything on the ladder</div><div class="pair">
        <div><small>ATP</small><div class="value">{pc(lad["atp"].get("elo_plus_everything"))}</div></div>
        <div><small>WTA</small><div class="value">{pc(lad["wta"].get("elo_plus_everything"))}</div></div></div>
        <div class="note">of the way from a coin flip to the bookmakers on main-tour matches with odds, 2022–2026; Elo alone {pc(lad["atp"].get("elo_fit"))} / {pc(lad["wta"].get("elo_fit"))}</div></div>
    </div>'''

    # part 2: the profiles
    order = ["profile_adjperf", "profile_adjperf_52w", "profile_ios", "style_ios", "skill_ios", "profile_ios_products",
             "profile_both", "profile_both_products", "profile_plus_points", "points_only"]
    rows = []
    for mid in order:
        if mid not in pm:
            continue
        m = pm[mid]
        cells = []
        for t in TOURS:
            h = ph.get(f"{t}|{mid}", {})
            cells.append(cell(h, "market_imp", "market_lo", "market_hi", "market_clears_line") + cell(h, "market_2022-2026")
                         + cell(h, "elo_imp") + cell(h, "ratings_imp"))
        rows.append(f'<tr><td style="white-space:normal;min-width:16rem;max-width:26rem"><b>{esc(m["name"])}</b>'
                    f'<span style="display:block;color:var(--muted);font-size:.82rem;line-height:1.35;margin-top:2px">{esc(m["description"])}</span></td>'
                    f'{"".join(cells)}</tr>')
    profiles = f'''    <div class="sub">
      <h3>The individual statistics together, against the odds</h3>
      <p class="prose">Stage B scored each opponent-adjusted statistic one at a time. Here the whole profile enters one model:
      aces, double faults, first serves in, first- and second-serve points won, holds, break points saved, faced and
      converted, breaks and return points against each serve, as adjperf (2-week half-life or the last 52 weeks) and as IOS
      offence and defence. The points-won aggregates are kept out of the profiles and added back in one model. "Products" are
      the UFC weapon-times-liability interactions, each player's offence on a statistic times the opponent's lack of defence.
      Given the odds, the null band is what 20 shuffled copies of the same many-input model score, so "✓ clears the line"
      means better than a useless model of that size; read the gain and its range.</p>
      <div class="panel">
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th rowspan="2">Model</th><th colspan="4">Men</th><th colspan="4">Women</th></tr>
          <tr><th class="r">Given the odds (95% range)</th><th class="r">2022–26</th><th class="r">Given Elo</th><th class="r">Given the ratings</th>
              <th class="r">Given the odds (95% range)</th><th class="r">2022–26</th><th class="r">Given Elo</th><th class="r">Given the ratings</th></tr></thead>
          <tbody>{"".join(rows)}</tbody></table></div>
        <p class="note-small">milli-log-loss better than the baseline alone. "Given the ratings": added to the earlier study's serve-and-return
        ratings through the iid model. The women's rows are scored from 2019. Inputs per model are in <code>stageD_profile_catalog.json</code>.</p>
      </div>
    </div>'''

    # part 1: everything together
    rows = []
    for mid, m in sm.items():
        cells = []
        for t in TOURS:
            h = sh.get(f"{t}|{mid}", {})
            cells.append(cell(h, "elo_imp", "elo_lo", "elo_hi") + cell(h, "elo_2022-2026")
                         + cell(h, "market_imp", "market_lo", "market_hi", "market_clears_line")
                         + (cell(h, "bt_imp") if has_bt else "") + f'<td>{esc(h.get("reading", ""))}</td>')
        rows.append(f'<tr><td style="white-space:normal;min-width:16rem;max-width:26rem"><b>{esc(m["name"])}</b>'
                    f'<span style="display:block;color:var(--muted);font-size:.82rem;line-height:1.35;margin-top:2px">{esc(m["description"])}</span></td>'
                    f'{"".join(cells)}</tr>')
    bt_h = '<th class="r">Given BT</th>' if has_bt else ""
    together = f'''    <div class="sub">
      <h3>The best inputs of both studies together</h3>
      <div class="panel">
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th rowspan="2">Model</th><th colspan="{5 if has_bt else 4}">Men</th><th colspan="{5 if has_bt else 4}">Women</th></tr>
          <tr><th class="r">Given Elo (95% range)</th><th class="r">2022–26</th><th class="r">Given the odds</th>{bt_h}<th>Reading</th>
              <th class="r">Given Elo (95% range)</th><th class="r">2022–26</th><th class="r">Given the odds</th>{bt_h}<th>Reading</th></tr></thead>
          <tbody>{"".join(rows)}</tbody></table></div>
        <p class="note-small">Each model is a logistic regression on its inputs, every input at its own stage's frozen constants;
        nothing was tuned here. "Given BT" is the model added to Stage A's Bradley–Terry rating instead of Elo (for the models
        that do not already hold it). The women's rows are scored from 2019.</p>
      </div>
    </div>'''

    lrows = []
    keys = [("elo_raw", "Elo rating, as it is"), ("bt_raw", "Bradley–Terry rating, as it is"), ("elo_fit", "Elo refitted each season"),
            ("elo_plus_earlier_three", "Elo + the earlier study's three"), ("elo_plus_everything", "Elo + everything"),
            ("bt_plus_everything", "Bradley–Terry + everything"), ("market", "Bookmakers' closing prices")]
    for k, name in keys:
        if any(k in lad[t] for t in TOURS):
            lrows.append(f'<tr><td>{esc(name)}</td>' + "".join(f'<td class="r">{pc(lad[t].get(k))}</td>' for t in TOURS) + "</tr>")
    ladder = f'''    <div class="panel">
      <div class="panel-head"><h3>The ladder, from a coin flip (0%) to the bookmakers (100%)</h3><p>main-tour matches with closing odds, 2022–2026:
      {lad["atp"]["matches"]:,} men's and {lad["wta"]["matches"]:,} women's</p></div>
      <div class="table-wrap"><table class="num"><thead><tr><th>Forecast</th><th class="r">Men</th><th class="r">Women</th></tr></thead>
      <tbody>{"".join(lrows)}</tbody></table></div>
      <p class="note-small">The share is (coin − log loss) / (coin − the odds' log loss). "As it is" uses the rating's own probability; the fitted
      rows are the walk-forward models scored on these matches. Closing the ladder is not beating the odds: a model at 90% still trails them.</p>
    </div>'''
    return {"html": "\n".join([tiles, profiles, together, ladder]), "data": {"ladder": lad}, "script": ""}
