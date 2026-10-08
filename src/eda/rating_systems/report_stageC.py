"""Report section for Stage C of "rating systems against Elo": the feature-alpha audit's ladder with each rating as the
base, and the men's statistics profile against the closing line with each rating as an extra input.

Contract: SECTION and render(study_dir) -> {"html", "data", "script"}; every number from summary_results.json in
study_dir (data/studies/rating_systems/).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": "C", "id": "stage-c", "title": "Orthogonal to the promising features?"}
TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
STEP_WORDS = {"sr": "+ serve and return ratings", "sr_adjperf": "+ two-week adjusted points won",
              "sr_adjperf_ios": "+ short-memory IOS matchup", "sr_adjperf_ios_games": "+ games-weighted Elo",
              "full": "+ sets over 14 days, first matches on a surface, age"}
BASES = ["glicko_cs", "ttt", "glicko2m", "trueskill", "glicko2"]


def esc(x) -> str:
    return html.escape(str(x))


def mm(x, d=2) -> str:
    if x is None:
        return "–"
    s = f"{abs(x):.{d}f}"
    return ("−" if x < 0 and s.strip("0.") else "+") + s


def cell(r) -> str:
    if not r:
        return '<td class="r">–</td>'
    return f'<td class="r">{mm(r["gain"])}<br><small class="muted">{mm(r["lo"])} to {mm(r["hi"])}</small></td>'


def render(study_dir: Path) -> dict:
    S = json.loads((Path(study_dir) / "summary_results.json").read_text(encoding="utf-8"))
    names, orth, mk = S["names"], S["orthogonality"], S["market"]
    bases = [b for b in BASES if b in orth["atp"]["2022"]["bases"]]
    parts = ['''    <div class="prose">
      <p>If a new rating beats Elo only by carrying what the promising features carry, the features add less given it,
      and a full model gains nothing from the swap. If it is orthogonal to them, the features add as much and the full
      model keeps the rating's gain. Both are measured with the feature-alpha audit's ladder, imported unchanged: annual
      expanding logistic fits from 2013, scored from 2019, on the matches where every input exists, with intervals
      clustered by calendar week.</p>
    </div>''']
    for since in ("2022", "2019"):
        for t in TOUR:
            o = orth[t][since]
            head = "".join(f'<th class="r">{esc(names[b])}</th>' for b in bases)
            trs = [f'<tr><td>The base alone, against calibrated Elo</td>' + "".join(cell(o["bases"][b]["calibrated_vs_elo_calibrated"]) for b in bases) + "</tr>"]
            trs.append('<tr class="group"><td colspan="99">What each step adds given this base (given Elo in brackets)</td></tr>')
            for st, lab in STEP_WORDS.items():
                ge = o["steps_given_elo"].get(st)
                trs.append(f'<tr><td>{esc(lab)} <small class="muted">({mm(ge["gain"]) if ge else "–"} given Elo)</small></td>'
                           + "".join(cell(o["bases"][b]["steps_given_base"].get(st)) for b in bases) + "</tr>")
            trs.append('<tr class="group"><td colspan="99">The full model</td></tr>')
            trs.append('<tr><td>Against the full model with Elo</td>' + "".join(cell(o["bases"][b]["full_vs_elo_full"]) for b in bases) + "</tr>")
            trs.append('<tr><td>With both ratings, against the full model with Elo</td>' + "".join(cell(o["bases"][b]["both_full_vs_elo_full"]) for b in bases) + "</tr>")
            trs.append('<tr><td>Against the raw closing average (matches with odds)</td>' + "".join(cell(o["bases"][b]["full_vs_market"]) for b in bases) + "</tr>")
            ef, em = o["elo_full_vs_calibrated"], o["elo_full_vs_market"]
            title = f"{TOUR[t]}, scored {since}–2026"
            note = ""
            if ef:
                note = (f"{ef['n']:,} matches; with Elo as the base the full model gains {mm(ef['gain'])} on calibrated Elo "
                        f"and stands {mm(em['gain'] if em else None)} against the raw closing average on the matches with odds")
            table = (f'<div class="table-wrap"><table class="wide num"><thead><tr><th>milli-log-loss</th>{head}</tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table></div>')
            if since == "2022":
                parts.append(f'    <div class="panel"><div class="panel-head"><h3>{title}</h3><p>{note}</p></div>{table}</div>')
            else:
                parts.append(f'    <details class="twin"><summary>{title}</summary><p class="note-small">{note}</p>{table}</details>')
    # the closing line
    trs = []
    for window in ("2019-2026", "2022-2026", "2013-2026"):
        trs.append(f'<tr class="group"><td colspan="3">{window.replace("-", "–")}</td></tr>')
        rows = [("Surface Elo", "rating_elo", "calibrated_market")]
        rows += [(names[b], f"rating_{b}", "calibrated_market") for b in ("glicko_cs", "ttt", "glicko2m", "trueskill")]
        rows += [("The 16-input statistics profile", "profile", "calibrated_market")]
        rows += [(f"Profile + {'surface Elo' if b == 'elo' else names[b]}, against the profile", f"profile_rating_{b}", "profile")
                 for b in ("elo", "glicko_cs", "ttt", "glicko2m", "trueskill")]
        for lab, model, comp in rows:
            trs.append(f'<tr><td>{esc(lab)}</td>'
                       + "".join(cell(mk.get(m_, {}).get(window, {}).get(model, {}).get(comp)) for m_ in ("p_ps_a", "p_avg_a")) + "</tr>")
    n = mk.get("p_ps_a", {}).get("2019-2026", {}).get("profile", {}).get("calibrated_market", {}).get("n")
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>The men's closing line, with each rating as an input</h3><p>The audit's profile retest:
      market log-odds unpenalised, ridge on the rest from the two preceding seasons; {f"{n:,}" if n else "–"} matches
      2019–2026 with both prices</p></div>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>Gain over the calibrated closing price</th>
      <th class="r">Pinnacle</th><th class="r">Average of books</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
    </div>''')
    # the repaired cohort
    rep = S.get("repaired")
    if rep:
        lad = rep["ladder"]
        trs = []
        rows = [("The repairs' own Elo (dated history only), against calibrated Stage 1 Elo", "elo_repaired_vs_elo_calibrated", None),
                ("The full model with the repairs' Elo, against the full model with Stage 1 Elo", "elo_repaired_full_vs_elo_full", None)]
        for b in ("glicko_cs", "ttt", "glicko2m", "trueskill"):
            rows += [(f"{names[b]} alone, against calibrated Elo", b, "calibrated_vs_elo_calibrated"),
                     (f"{names[b]}: the full model, against the full model with Elo", b, "full_vs_elo_full"),
                     (f"{names[b]}: both ratings in the full model, against the full model with Elo", b, "both_full_vs_elo_full")]
        for lab, key, sub in rows:
            cells = ""
            for t in TOUR:
                for w in ("2019", "2022"):
                    rec = lad[t][w].get(key)
                    r = rec.get(sub) if (sub and rec) else (rec if not sub else None)
                    cells += cell(r)
            trs.append(f"<tr><td>{esc(lab)}</td>{cells}</tr>")
        mk_r = rep["market"]
        mtrs = []
        mrows = [("The 16-input statistics profile", "profile")]
        mrows += [(f"{'Surface Elo' if b == 'elo' else names[b]}", f"rating_{b}") for b in ("elo", "glicko_cs", "ttt", "glicko2m", "trueskill")]
        mrows += [(f"Profile + {'surface Elo' if b == 'elo' else names[b]}, against the profile", f"profile_rating_{b}_vs_profile")
                  for b in ("elo", "glicko_cs", "ttt")]
        for lab, key in mrows:
            mtrs.append(f"<tr><td>{esc(lab)}</td>" + "".join(cell(mk_r[m_][w].get(key)) for m_ in ("p_ps_a", "p_avg_a")
                                                             for w in ("2019", "2022")) + "</tr>")
        n_l = {t: (lad[t]["2019"]["ttt"]["calibrated_vs_elo_calibrated"] or {}).get("n") for t in TOUR}
        n_m = (mk_r["p_ps_a"]["2019"]["profile"] or {}).get("n")
        parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>On the audit's repaired cohort</h3><p>Main-tour matches with trusted match dates, every
      feature rebuilt in match-day order (the repairs of 2 Oct 2026); intervals clustered by four-week blocks</p></div>
      <p class="note-small" style="margin:0 0 10px">The ladder scored 2019–2026 on {n_l["atp"]:,} men's and {n_l["wta"]:,}
      women's matches (2022–2026 beside). The ratings come from the full history under the event-start rule; a filtering
      rating cannot pass an overlapping event's later rounds between players. The profile's gain over calibrated Pinnacle
      reproduces the repairs' published figure.</p>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>milli-log-loss</th><th class="r">Men 2019–26</th>
      <th class="r">Men 2022–26</th><th class="r">Women 2019–26</th><th class="r">Women 2022–26</th></tr></thead>
      <tbody>{"".join(trs)}</tbody></table></div>
      <h4 style="margin:14px 0 6px">The men's closing line on the repaired cohort ({f"{n_m:,}" if n_m else "–"} matches 2019–2026)</h4>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>Gain over the calibrated closing price</th>
      <th class="r">Pinnacle 2019–26</th><th class="r">Pinnacle 2022–26</th><th class="r">Average 2019–26</th>
      <th class="r">Average 2022–26</th></tr></thead><tbody>{"".join(mtrs)}</tbody></table></div>
    </div>''')
    return {"html": "\n".join(parts), "data": {}, "script": ""}
