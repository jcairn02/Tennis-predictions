"""Report section for Stage B of "rating systems against Elo": every system against surface Elo and the closing odds by
window, level and era; calibration; where the gain comes from; and the shared harness's rows.

Contract: SECTION and render(study_dir) -> {"html", "data", "script"}; every number from summary_results.json in
study_dir (data/studies/rating_systems/).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": "B", "id": "stage-b", "title": "Against Elo and the closing odds"}
TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
WIN = {"2013-2026": "2013–2026", "2013-2018 (tuning)": "2013–2018 (tuning)", "2019-2026": "2019–2026",
       "2022-2026 (headline)": "2022–2026"}
LEVELS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
          "GSQ": "Grand Slam qualifying", "TQ": "Tour qualifying", "CH": "Challenger / WTA 125", "CHQ": "Challenger / 125 qualifying"}
ERAS = {"2013-16": "2013–16", "2017-19": "2017–19", "2020-21": "2020–21", "2022-26": "2022–26"}
LEAD = ["glicko_cs", "ttt", "glicko2m", "trueskill"]
LEADER_NAMES = {"profile_adjperf": "The men's statistics profile (16 inputs)", "rating_matchup": "Serve and return ratings (iid model)",
                "ios_short": "Short-memory IOS points matchup", "adjperf_tpw": "Two-week adjusted total points won",
                "elo_games": "Games-weighted Elo", "mu_points": "Points matchup, 52 weeks", "sets_14d": "Sets over 14 days",
                "surface_first": "First matches on a surface", "age": "Age and age squared"}


def esc(x) -> str:
    return html.escape(str(x))


def mm(x, d=2) -> str:
    if x is None:
        return "–"
    s = f"{abs(x):.{d}f}"
    return ("−" if x < 0 and s.strip("0.") else "+") + s


def cell(v, lo=None, hi=None, star=False) -> str:
    sub = f'<br><small class="muted">{mm(lo)} to {mm(hi)}</small>' if lo is not None and hi is not None else ""
    return f'<td class="r">{mm(v)}{" ★" if star else ""}{sub}</td>'


def render(study_dir: Path) -> dict:
    S = json.loads((Path(study_dir) / "summary_results.json").read_text(encoding="utf-8"))
    systems, names, raw = S["systems"], S["names"], S["raw"]
    parts = ['''    <div class="prose">
      <p>Every system's frozen forecast against Stage 1's surface Elo on the same matches: raw log loss, so neither is
      refitted. "Better than Elo" is Elo's log loss minus the system's in milli-log-loss, with a 95% interval clustered by
      four-week calendar blocks. On the matches with odds (tour-level main draws) the closing prices' average is the
      market, and the share of the gap closed is (Elo − system) / (Elo − market).</p>
    </div>''']
    for t in TOUR:
        head = "".join(f'<th class="r">{esc(WIN[w])}</th>' for w in WIN)
        trs = []
        for s in systems:
            tds = "".join(cell(raw[t][w]["systems"][s]["better_than_elo"], raw[t][w]["systems"][s]["block_lo"],
                               raw[t][w]["systems"][s]["block_hi"]) for w in WIN)
            trs.append(f'<tr><td>{esc(names[s])}</td>{tds}</tr>')
        trs.append('<tr class="group"><td colspan="5">On the matches with odds</td></tr>')
        for s in systems:
            tds = ""
            for w in WIN:
                r = raw[t][w]["systems"][s]
                tds += (f'<td class="r">{mm(r["better_than_elo_odds"])}<br><small class="muted">{mm(r["odds_block_lo"])} to '
                        f'{mm(r["odds_block_hi"])} · gap {100 * r["gap_closed"]:+.0f}%</small></td>')
            trs.append(f'<tr><td>{esc(names[s])}</td>{tds}</tr>')
        ns = " · ".join(f'{esc(WIN[w])}: {raw[t][w]["n_all"]:,} ({raw[t][w]["n_odds"]:,} with odds; Elo {raw[t][w]["elo_ll"]:.4f}, '
                        f'market {raw[t][w]["market_ll"]:.4f})' for w in WIN)
        parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>{TOUR[t]}: better than surface Elo, milli-log-loss</h3></div>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>System</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>
      <p class="note-small" style="margin:10px 0 0">Matches: {ns}.</p>
    </div>''')
    # by level and era (the leading systems)
    for kind, key, words in (("level", "by_level", LEVELS), ("era", "by_era", ERAS)):
        head = "".join(f'<th class="r">{esc(names[s])}</th>' for s in LEAD)
        trs = []
        for t in TOUR:
            trs.append(f'<tr class="group"><td colspan="{len(LEAD) + 2}">{TOUR[t]}</td></tr>')
            for g, lab in words.items():
                rec = S[key][t].get(g)
                if not rec:
                    continue
                dr = ' <span class="tag">under 300</span>' if rec["n"] < 300 else ""
                trs.append(f'<tr><td>{esc(lab)}{dr}</td><td class="r">{rec["n"]:,}</td>'
                           + "".join(f'<td class="r">{mm(rec[s])}</td>' for s in LEAD) + "</tr>")
        parts.append(f'''    <details class="twin"><summary>Better than Elo by {kind}, 2013–2026, every evaluation match</summary>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>{kind.title()}</th><th class="r">Matches</th>{head}</tr></thead>
      <tbody>{"".join(trs)}</tbody></table></div></details>''')
    # calibration and where the gain comes from
    cal = S["calibration_slope_2019_2026"]
    ctr = "".join(f'<tr><td>{esc(names.get(k, "Surface Elo") if k != "elo" else "Surface Elo")}</td>'
                  + "".join(f'<td class="r">{cal[t][k]:.3f}</td>' for t in TOUR) + "</tr>" for k in ["elo"] + systems)
    parts.append(f'''    <details class="twin"><summary>Calibration, 2019–2026</summary>
      <p class="note-small">The slope from refitting the result on the forecast's log-odds: 1 is perfect, below 1 too
      confident, above 1 too timid.</p>
      <div class="table-wrap"><table class="num"><thead><tr><th>Forecast</th><th class="r">Men</th><th class="r">Women</th></tr></thead>
      <tbody>{ctr}</tbody></table></div></details>''')
    dg = S["diagnostics"]
    blocks = []
    for k, lab in (("fewest_prior_matches", "The less experienced player's rated matches before the match"),
                   ("longest_layoff_days", "The longer layoff of the two (days since the previous date played)")):
        trs = []
        for t in TOUR:
            trs.append(f'<tr class="group"><td colspan="{len(LEAD) + 1}">{TOUR[t]}</td></tr>')
            bins = list(dg[t][LEAD[0]][k])
            for b in bins:
                n = dg[t][LEAD[0]][k][b]["n"]
                if not n:
                    continue
                dr = ' <span class="tag">under 300</span>' if n < 300 else ""
                trs.append(f'<tr><td>{esc(b)} ({n:,}){dr}</td>' + "".join(f'<td class="r">{mm(dg[t][s][k][b]["milli"])}</td>' for s in LEAD) + "</tr>")
        head = "".join(f'<th class="r">{esc(names[s])}</th>' for s in LEAD)
        blocks.append(f'<h4 style="margin:12px 0 6px">{esc(lab)}</h4><div class="table-wrap"><table class="wide num"><thead><tr>'
                      f'<th>Group (matches)</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    parts.append(f'''    <details class="twin"><summary>Where the gain over Elo comes from</summary>
      <p class="note-small">Better than Elo (milli-log-loss), every evaluation match of 2013–2026, by the players' experience
      and layoffs.</p>{"".join(blocks)}</details>''')
    ov = S.get("weekly_overshoot") or {}
    if ov.get("atp"):
        trs = []
        for t in TOUR:
            trs.append(f'<tr class="group"><td colspan="4">{TOUR[t]}</td></tr>')
            for lab, rec in ov[t].items():
                cells = "".join(
                    f'<td class="r">{mm(rec[k]["milli"])}<br><small class="muted">{rec[k]["n"]:,} matches</small></td>'
                    if rec[k]["n"] else '<td class="r">–</td>' for k in ("all", "fewer_than_21_prior", "over_100_prior"))
                trs.append(f"<tr><td>{esc(lab)}</td>{cells}</tr>")
        parts.append(f'''    <details class="twin"><summary>Why Glicko-2 with weekly rating periods loses</summary>
      <p class="note-small">The weekly Glicko-2's log loss minus the match-by-match one (positive: the weekly version worse),
      every evaluation match of 2013–2026, by how many rated matches the players had already played in the match's week
      (the larger of the two), overall and for the less and the more experienced. A week's games scored together around
      the pre-week rating should cost most after several matches in the week by an uncertain player.</p>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>Earlier matches that week</th><th class="r">Every match</th>
      <th class="r">Less experienced player: 20 or fewer prior</th><th class="r">Both over 100 prior</th></tr></thead>
      <tbody>{"".join(trs)}</tbody></table></div></details>''')
    # the harness
    hs = S["harness"]
    trs = []
    for t in TOUR:
        trs.append(f'<tr class="group"><td colspan="4">{TOUR[t]}</td></tr>')
        for s in systems:
            g = hs[t]["systems"][s]
            ge, gm = g["given_elo"] or {}, g["given_market"] or {}
            trs.append(f'<tr><td>{esc(names[s])}</td>{cell(ge.get("imp"), ge.get("lo"), ge.get("hi"))}'
                       f'{cell(gm.get("imp"), gm.get("lo"), gm.get("hi"))}<td>{esc(S["harness_reading"][t].get(s, ""))}</td></tr>')
        for s in LEAD:
            g = hs[t]["elo_given"].get(s) or {}
            trs.append(f'<tr><td>Surface Elo, given {esc(names[s])}</td>{cell(g.get("imp"), g.get("lo"), g.get("hi"))}<td></td><td></td></tr>')
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>Through the shared test</h3><p>The earlier studies' walk-forward harness, 2013–2026: each
      rating added to a base refitted season by season; four-week intervals</p></div>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>Row</th><th class="r">Given Elo</th>
      <th class="r">Given the market</th><th>Reading</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
    </div>''')
    trs = []
    bases = ["elo"] + LEAD + ["market"]
    for t in TOUR:
        trs.append(f'<tr class="group"><td colspan="{len(bases) + 1}">{TOUR[t]}</td></tr>')
        for cid, lab in LEADER_NAMES.items():
            g = hs[t]["leaders"].get(cid)
            if not g or not any(g.values()):
                continue
            trs.append(f'<tr><td>{esc(lab)}</td>' + "".join(cell((g.get(b) or {}).get("imp")) for b in bases) + "</tr>")
    head = "".join(f'<th class="r">Given {esc("Elo" if b == "elo" else "the market" if b == "market" else names[b])}</th>' for b in bases)
    parts.append(f'''    <details class="twin" open><summary>The earlier leaders given Elo and given each new rating</summary>
      <p class="note-small">milli-log-loss each feature adds to the base; a feature that adds less given a new rating than
      given Elo shares information with that rating.</p>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>Feature</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>
    </details>''')
    return {"html": "\n".join(parts), "data": {}, "script": ""}
