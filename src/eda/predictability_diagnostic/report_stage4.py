"""Report section for Stage 4, "The rundown": every row of the approved candidate list (a candidate in one form, per
tour) scored three ways (alone, given surface Elo, given the closing odds), walk-forward by season, beside its null band
of shuffled copies and the family-wide line; where the leading rows gain, by era and by level; and the leak checks.

Every number comes from stage4_results.json (render_report.py assembles the page).
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": 4, "id": "rundown", "title": "The rundown"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "ATP (men)", "wta": "WTA (women)"}
ERAS = ("2013-16", "2017-19", "2020-21", "2022-26")
ERA_WORDS = {"2013-16": "2013–16", "2017-19": "2017–19", "2020-21": "2020–21", "2022-26": "2022–26"}
LEVELS = [("GS", "Grand Slams"), ("FIN", "Tour Finals"), ("T1000", "1000s"), ("T500", "500s"), ("T250", "250s"),
          ("GSQ", "Grand Slam qualifying"), ("TQ", "Tour qualifying"), ("CH", "Challenger / WTA 125"),
          ("CHQ", "Challenger / 125 qualifying")]
FORM_WORDS = {"career": "career", "52 weeks": "52 weeks", "decayed": "decayed", "surface": "surface",
              "adjusted": "opponent-adjusted", "single": "–"}
READING_ORDER = ["finding", "possible", "no sign", "worse", "no information (constant)", "not scored"]
LEADERS = 10                                     # leading rows per tour offered in the era-and-level chart


def esc(x) -> str:
    return html.escape(str(x))


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def f2(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:.2f}".replace("-0.00", "0.00").replace("-", "−")


def f3(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:.3f}".replace("-0.000", "0.000").replace("-", "−")


def f1(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:.1f}".replace("-0.0", "0.0").replace("-", "−")


def n0(x) -> str:
    v = num(x)
    return "–" if v is None else f"{int(round(v)):,}"


def pct(x, d=1) -> str:
    v = num(x)
    return "–" if v is None else f"{100 * v:.{d}f}%"


def better(milli) -> str:
    """'1.23 better' / '0.40 worse' for an improvement in milli-log-loss (positive = better)."""
    v = num(milli)
    if v is None:
        return "–"
    return f"{abs(v):.2f} {'better' if v >= 0 else 'worse'}"


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div>'
            f'<div class="note">{note}</div></div>')


def label_of(r: dict) -> str:
    return r["name"] + ("" if r["form"] == "single" else f" ({FORM_WORDS[r['form']]})")


def render(study_dir: Path) -> dict:
    res = load(study_dir, "stage4_results.json")
    rank = res["ranking"]
    by_tour = {t: [r for r in rank if r["tour"] == t] for t in TOUR}
    lines = res["lines"]
    probe = res["probe"]
    leak = res.get("leak_checks", res.get("leak_lag", []))
    cov = res["coverage_vs_plan"]
    plan = res["plan"]
    ec = res["event_country"]
    grp = {}
    for g in res["by_group"]:
        grp.setdefault((g["tour"], g["id"], g["form"], g["score"]), {})[g["group_name"]] = g

    def top(t, key="elo_imp", k=1):
        rows = [r for r in by_tour[t] if num(r.get(key)) is not None and not r["constant"]]
        return sorted(rows, key=lambda r: -r[key])[:k]

    count = {t: {k: sum(1 for r in by_tour[t] if r["reading"] == k) for k in READING_ORDER} for t in TOUR}
    line_clear = {t: sum(1 for r in by_tour[t] if r.get("elo_clears_line")) for t in TOUR}
    best_elo = {t: top(t)[0] for t in TOUR}
    best_mkt = {t: top(t, "market_imp")[0] for t in TOUR}
    rec, pl = probe["variants"]["recorded_format"], probe["variants"]["plan"]
    lag = [x for x in leak if x.get("check") == "one match later" and num(x.get("original_elo")) is not None]
    fmt = [x for x in leak if x.get("check") == "format recorded"]
    parts = []

    # ------------------------------------------------------------------ intro and tiles
    nrows = {t: len(by_tour[t]) for t in TOUR}
    parts.append(f'''    <div class="prose">
      <p>Stage 4 scores every row of the approved candidate list: a candidate statistic or feature in one form, for each
      tour ({nrows["atp"]} rows for the men, {nrows["wta"]} for the women). Each row is fitted walk-forward, season by
      season, by a logistic regression without an intercept, and scored three ways on the matches where it exists: alone
      against a coin, added to surface Elo, and added to the closing odds. Beside every score stand 20 copies of the same
      feature shuffled within each season, which carry no information about who won: they show what chance alone gives a
      row of that kind. The plan (<code>candidates.md</code>, approved as written; SHA-256 <code>{esc(plan["sha256"][:16])}…</code>)
      fixed all of this before anything was compared with results.</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("Rows that clear the family-wide line given Elo", f"{line_clear['atp']}", f"{line_clear['wta']}",
                 f"of {nrows['atp']} and {nrows['wta']}; findings (the line, and better than Elo in three eras or more): "
                 f"{count['atp']['finding']} and {count['wta']['finding']}")}
      {pair_tile("Largest gain on surface Elo (milli-log-loss)", f2(best_elo["atp"]["elo_imp"]), f2(best_elo["wta"]["elo_imp"]),
                 f"{esc(label_of(best_elo['atp']))}; {esc(label_of(best_elo['wta']))}")}
      {pair_tile("Largest gain on the closing odds (milli-log-loss)", f2(best_mkt["atp"]["market_imp"]), f2(best_mkt["wta"]["market_imp"]),
                 f"{esc(label_of(best_mkt['atp']))} (95% range {f2(best_mkt['atp']['market_lo'])} to {f2(best_mkt['atp']['market_hi'])}); "
                 f"{esc(label_of(best_mkt['wta']))} ({f2(best_mkt['wta']['market_lo'])} to {f2(best_mkt['wta']['market_hi'])})")}
      <div class="tile" role="listitem"><div class="label">Leak probe: protected matches whose features moved</div>
        <div class="value">{n0(rec["protected_changed"])} of {n0(probe["protected_checked"])}</div>
        <div class="note">format from the source's record; a deliberately leaky control moved at {n0(rec["control_protected_changed"])}
        (section "Leak checks")</div></div>
    </div>''')

    # ------------------------------------------------------------------ terms
    parts.append(f'''    <div class="sub">
      <h3>Terms used in this section</h3>
      <dl class="terms">
        <dt>Row</dt><dd>A candidate in one form (career, last 52 weeks, decayed, this surface, opponent-adjusted; or the one
        form a single feature has), for one tour.</dd>
        <dt>Walk-forward</dt><dd>For each season from 2013 (the women's box-score rows from 2019): fitted on the
        evaluation-level matches of 2010 to the season before, scored on that season. A season whose training set holds
        fewer than {res["settings"]["min_train"]} matches, or fewer than {res["settings"]["min_train"]} on which the
        feature is not zero, is not scored.</dd>
        <dt>Improvement</dt><dd>The baseline's log loss minus the row's model's, per match, in milli-log-loss (thousandths;
        a coin scores 693): positive is better. <i>Alone</i>: against a coin. <i>Given Elo</i>: surface Elo plus the
        feature against surface Elo alone, refitted on the same matches. <i>Given the market</i>: the same with the closing
        odds, on the main-tour matches that have them. The 95% range comes from the per-match differences.</dd>
        <dt>Null band</dt><dd>The range of the improvements of 20 copies of the feature shuffled within each season. Every
        match carries 20 random keys shared by every row, so the copies keep the rows' links to one another.</dd>
        <dt>Family-wide line</dt><dd>Per tour and score, each row's improvement is put on a common scale (minus its copies'
        mean, over their standard deviation). Each copy's largest value over all rows is the best that useless features as
        correlated as these reach; the line is the largest of the 20. Given Elo it is {f1(lines["atp|elo"]["line"])} (men)
        and {f1(lines["wta|elo"]["line"])} (women) standard deviations.</dd>
        <dt>Reading</dt><dd>Fixed in the plan. <b>Finding</b>: clears the line given Elo, and its improvement given Elo is
        positive in at least three eras. <b>Possible</b>: above its own band, not the line. <b>No sign</b>: inside its band.
        <b>Worse</b>: below it. A row whose feature never varies carries <b>no information</b>; a row with no season that
        passes the training minimum is <b>not scored</b>.</dd>
        <dt>Coverage</dt><dd>The share of the tour's evaluation matches of the row's scored seasons on which it was scored
        (it exists for both players and its season was fitted).</dd>
        <dt>Directional</dt><dd>A group of fewer than 300 matches: its result shows a direction only.</dd>
      </dl>
    </div>''')

    # ------------------------------------------------------------------ the ranking (sortable)
    def rows_for(t):
        out = []
        for r in sorted(by_tour[t], key=lambda r: r["rank_given_elo"] if num(r.get("rank_given_elo")) is not None else 1e9):
            out.append({"rank": num(r.get("rank_given_elo")), "label": label_of(r), "id": r["id"], "form": r["form"],
                        "cov": num(r.get("elo_coverage")), "elo": num(r.get("elo_imp")), "lo": num(r.get("elo_lo")),
                        "hi": num(r.get("elo_hi")), "bmax": num(r.get("elo_band_max")), "z": num(r.get("elo_z")),
                        "line": bool(r.get("elo_clears_line")), "eras": r.get("eras_positive"), "eras_n": r.get("eras_scored"),
                        "e19": num(r.get("elo_2019-2026")), "e22": num(r.get("elo_2022-2026")),
                        "alone": num(r.get("alone_imp")), "mkt": num(r.get("market_imp")), "mlo": num(r.get("market_lo")),
                        "mhi": num(r.get("market_hi")), "mband": bool(r.get("market_above_band")),
                        "reading": r.get("reading") or "–", "exp": r.get("elo_expected") or "–",
                        "obs": r.get("elo_observed") or "–", "sep": (r.get("elo_separated_real") or 0)})
        return out
    table_data = {t: rows_for(t) for t in TOUR}
    parts.append(f'''    <div class="sub">
      <h3>The ranking</h3>
      <div class="prose">
        <p>Every row, ranked by its improvement given surface Elo over all its scored seasons. Click a column's name to sort
        by it. The plan's reading and its expectation (set before anything was scored) stand beside each row, so surprises
        show.</p>
      </div>
      <div class="panel">
        <div class="controls"><span>Tour:</span><div class="seg" role="group" aria-label="Tour">
          <button type="button" data-s4tour="atp" aria-pressed="true">ATP (men)</button>
          <button type="button" data-s4tour="wta" aria-pressed="false">WTA (women)</button></div>
          <span>Show:</span><div class="seg" role="group" aria-label="Rows shown">
          <button type="button" data-s4show="all" aria-pressed="true">All rows</button>
          <button type="button" data-s4show="above" aria-pressed="false">Above their band given Elo</button></div></div>
        <div class="table-wrap" style="max-height:34rem;overflow-y:auto"><table class="num wide" id="s4-rank">
          <thead><tr></tr></thead><tbody></tbody></table></div>
        <p class="note-small">Milli-log-loss, positive = better. "Band max" is the best of the 20 shuffled copies given Elo;
        "Line" marks a row above the family-wide line given Elo; "Eras +" counts the eras in which the improvement given
        Elo is positive, of those scored. Every group and score is in <code>stage4_results.csv</code>; this table is
        <code>stage4_ranking.csv</code>.</p>
      </div>
    </div>''')

    # ------------------------------------------------------------------ the leading rows, by era and level
    leaders = []
    for t in TOUR:
        for r in top(t, k=LEADERS):
            key = (r["id"], r["form"])
            if key not in [(x["id"], x["form"]) for x in leaders]:
                leaders.append({"id": r["id"], "form": r["form"], "label": label_of(r)})
    chart = {}
    for L in leaders:
        cell = {}
        for t in TOUR:
            for s in ("elo", "market"):
                g = grp.get((t, L["id"], L["form"], s), {})
                cell[f"{t}|{s}"] = [{"g": name, "kind": kind, "n": g[name]["n"], "imp": num(g[name]["imp"]),
                                     "lo": num(g[name]["lo"]), "hi": num(g[name]["hi"]), "bmin": num(g[name]["band_min"]),
                                     "bmax": num(g[name]["band_max"]), "dir": bool(g[name]["directional"])}
                                    for kind, names in (("era", ERAS), ("level", [c for c, _ in LEVELS]))
                                    for name in names if name in g]
        chart[f"{L['id']}|{L['form']}"] = cell
    parts.append(f'''    <div class="sub">
      <h3>Where the leading rows gain</h3>
      <div class="prose">
        <p>For the {LEADERS} rows with the largest improvement given Elo on each tour: the walk-forward improvement inside
        each era and each level group (dots, with 95% ranges), against the range of the shuffled copies in the same group
        (the grey band). A hollow dot is a group of fewer than 300 matches, directional only.</p>
      </div>
      <div class="panel">
        <div class="controls">
          <label for="s4-lead">Row:</label>
          <select id="s4-lead" style="font:inherit;font-size:.88rem;padding:3px 6px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink)">
            {"".join(f'<option value="{esc(L["id"])}|{esc(L["form"])}">{esc(L["label"])}</option>' for L in leaders)}</select>
          <div class="seg" role="group" aria-label="Score">
            <button type="button" data-s4score="elo" aria-pressed="true">Given Elo</button>
            <button type="button" data-s4score="market" aria-pressed="false">Given the market</button></div>
        </div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-1);border-radius:6px"></span>Improvement (95% range)</span>
          <span class="key"><span class="sw-band"></span>Shuffled copies' range</span>
        </div>
        <div class="chart-pair" id="s4-lead-chart"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide" id="s4-lead-table">
          <thead><tr><th>Tour</th><th>Group</th><th class="r">Matches</th><th class="r">Improvement</th><th class="r">95% range</th>
          <th class="r">Copies' range</th></tr></thead><tbody></tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ the readings, and the best form per statistic
    rtab = "".join(f'<tr><td>{esc(k)}</td><td class="r">{count["atp"][k]}</td><td class="r">{count["wta"][k]}</td></tr>'
                   for k in READING_ORDER if count["atp"][k] or count["wta"][k])
    stats = []
    for r in rank:
        if r["form"] != "single" and (r["id"], r["name"]) not in stats:
            stats.append((r["id"], r["name"]))
    ftab = []
    for cid, name in stats:
        cells = []
        for t in TOUR:
            rows = [r for r in by_tour[t] if r["id"] == cid and num(r.get("elo_imp")) is not None]
            if not rows:
                cells.append('<td>–</td><td class="r">–</td>')
                continue
            b = max(rows, key=lambda r: r["elo_imp"])
            cells.append(f'<td>{esc(FORM_WORDS[b["form"]])}</td><td class="r">{f2(b["elo_imp"])}</td>')
        exp_form = next((r["form_expected_best"] for r in rank if r["id"] == cid), "")
        ftab.append(f'<tr><td>{esc(name)}</td><td>{esc(exp_form or "–")}</td>{"".join(cells)}</tr>')
    parts.append(f'''    <div class="sub">
      <h3>The readings, and which form did best</h3>
      <div class="panel">
        <div class="panel-head"><h3>Rows by reading</h3><p>The plan's reading rule, given Elo</p></div>
        <div class="table-wrap"><table class="num"><thead><tr><th>Reading</th><th class="r">ATP</th><th class="r">WTA</th></tr></thead>
          <tbody>{rtab}</tbody></table></div>
        <details class="twin"><summary>The form that did best given Elo, statistic by statistic</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Statistic or matchup</th><th>Form the plan expected to do best</th><th>ATP: best form</th><th class="r">Given Elo</th>
          <th>WTA: best form</th><th class="r">Given Elo</th></tr></thead><tbody>{"".join(ftab)}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ the warm-up seasons, season by season
    warm_ids = [("rank", "single"), ("rank_points", "single"), ("recent_level", "single")]
    warm = {}
    for t in TOUR:
        for cid, form in warm_ids:
            g = grp.get((t, cid, form, "elo"), {})
            pts = sorted(((int(k.split()[1]), v) for k, v in g.items() if k.startswith("season ")), key=lambda x: x[0])
            warm.setdefault(t, []).append({"id": cid, "label": label_of(next(r for r in rank if r["id"] == cid and r["form"] == form)),
                                           "pts": [[y, num(v["imp"]), num(v["lo"]), num(v["hi"]), v["n"]] for y, v in pts]})
    wr = {t: {x["id"]: x for x in warm[t]} for t in TOUR}

    def season_val(t, cid, y):
        return next((p[1] for p in wr[t][cid]["pts"] if p[0] == y), None)

    def walk_val(t, cid, y, key):
        return grp.get((t, cid, "single", "elo"), {}).get(f"season {y}", {}).get(key)
    w_mid = [season_val("wta", "rank", y) for y in range(2014, 2023)]
    w_below = "all" if all(v is not None and v < 0 for v in w_mid) else str(sum(1 for v in w_mid if v is not None and v < 0))
    parts.append(f'''    <div class="sub">
      <h3>Why the ranking looks worse than it is</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>Added to surface Elo, the ranking, ranking points and the level played over the last
        52 weeks score <i>worse</i> than Elo alone over all their seasons. Season by season (the chart), the loss sits in the
        early seasons and fades: the men's ranking scores {f2(season_val("atp", "rank", 2013))} in 2013 and
        {f2(season_val("atp", "rank", 2026))} in 2026; the women's {f2(season_val("wta", "rank", 2013))} in 2013, below
        zero in {w_below} of the seasons 2014–2022 and {f2(season_val("wta", "rank", 2026))} in 2026. The walk-forward fit
        for 2013, trained on 2010–2012, weights the men's ranking
        {f2(walk_val("atp", "rank", 2013, "walk_coef"))} per standard deviation and Elo's log-odds
        {f2(walk_val("atp", "rank", 2013, "walk_base_in_model"))}, against {f2(walk_val("atp", "rank", 2013, "walk_base_alone"))}
        for Elo alone; the fit for 2026 weights them {f2(walk_val("atp", "rank", 2026, "walk_coef"))} and
        {f2(walk_val("atp", "rank", 2026, "walk_base_in_model"))}, against {f2(walk_val("atp", "rank", 2026, "walk_base_alone"))}.</p>
        <p><span class="kind">Inferred</span>The walk-forward fits begin on 2010–2012, the seasons in which Elo is still warming up
        from 1,500 for every player. There a ranking corrects an immature rating, so the first fits weight it heavily and Elo
        lightly; each later fit still carries those seasons, so the weights change only slowly. The plan fixes this window, so
        the full-period ranking understates every feature that stands in for strength; their 2022–2026 values are the fairer
        reading.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Given Elo, season by season</h3><p>Milli-log-loss better (+) or worse (−) than surface Elo alone;
        each season fitted on every earlier one from 2010</p></div>
        <div class="legend" aria-hidden="true">
          {"".join(f'<span class="key"><span class="sw-line" style="background:var(--series-{i + 1})"></span>{esc(x["label"])}</span>' for i, x in enumerate(warm["atp"]))}
        </div>
        <div class="chart-pair" id="s4-warm"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Feature</th>{"".join(f"<th class='r'>{y}</th>" for y in range(2013, 2027))}</tr></thead>
          <tbody>{"".join(f'<tr><td>{TOUR[t]}</td><td>{esc(x["label"])}</td>' + "".join(f'<td class="r">{f2(season_val(t, x["id"], y))}</td>' for y in range(2013, 2027)) + "</tr>" for t in TOUR for x in warm[t])}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ leak checks
    lag_rows = "".join(
        f'<tr><td>{TOUR[x["tour"]]}</td><td>{esc(next((label_of(r) for r in rank if r["tour"] == x["tour"] and r["id"] == x["id"] and r["form"] == x["form"]), x["id"]))}</td>'
        f'<td class="r">{f2(x.get("feature_corr"))}</td><td class="r">{f2(x.get("original_elo"))}</td><td class="r">{f2(x.get("rebuilt_elo"))}</td>'
        f'<td class="r">{f2(x.get("original_market"))}</td><td class="r">{f2(x.get("rebuilt_market"))}</td><td class="r">{n0(x.get("n_elo"))}</td></tr>'
        for x in lag)
    fmt_d = [abs(num(x.get("rebuilt_elo")) - num(x.get("original_elo"))) for x in fmt
             if num(x.get("rebuilt_elo")) is not None and num(x.get("original_elo")) is not None]
    fmt_m = [abs(num(x.get("rebuilt_market")) - num(x.get("original_market"))) for x in fmt
             if num(x.get("rebuilt_market")) is not None and num(x.get("original_market")) is not None]
    fmt_n = max((x.get("values_differ") or 0) for x in fmt) if fmt else 0
    fmt_most = max(fmt, key=lambda x: x.get("values_differ") or 0) if fmt else {}
    fmt_cols = sorted(pl["changed_by_column"])
    picked = [x for x in leak if x.get("check") == "one match later"]
    n_top = sum(1 for x in picked if x.get("why") == "ten strongest given Elo")
    n_big = sum(1 for x in picked if x.get("why") == "clear gain over the closing odds")
    n_line = sum(1 for x in picked if x.get("why") == "clears the family-wide line given the closing odds")
    parts.append(f'''    <div class="sub">
      <h3>Leak checks</h3>
      <div class="prose">
        <p><span class="kind">Observed</span><b>The probe cut by date, event and round.</b> On the matches of 2025–2026 (both
        tours, history inside that slice), {probe["cuts"]} cut matches were chosen in 2026. At each, what was played in
        every match the time rule does not let the cut see (its own round and later rounds of its event, the week's other
        events, later weeks) was redrawn: results, box scores, scores, minutes, statuses and the point-by-point values; so
        were the pre-match values (rankings, ages, ratings) of every later match. Every feature was rebuilt, the weighted
        Elos rerun. With the match format taken from the source's record, {n0(rec["protected_changed"])} of
        {n0(probe["protected_checked"])} protected matches moved in any of the {probe["columns"]} feature columns (largest
        difference {rec["largest_protected_difference"]:.1e}, rounding), while a deliberately leaky control (career wins
        counted with the match itself) moved at {n0(rec["control_protected_changed"])}. With the format as the plan reads
        it, from the match's own score, {n0(pl["protected_changed"])} protected matches moved, all in the {len(fmt_cols)}
        columns that use the format (the matchups through the iid model, the ratings through it, match length).</p>
        <p><span class="kind">Observed</span><b>The format, read from the source's record instead.</b> The plan reads best
        of five from the score, as Stage 2 did; the score then tells the format, not who won. Rebuilt from the record
        alone (the Next Gen Finals' short sets kept), the {len(fmt)} format rows change on at most {n0(fmt_n)} matches
        (by event and round: {esc(fmt_most.get("differ_by_event") or "–")}; by season: {esc(fmt_most.get("differ_by_season") or "–")}),
        and their improvements move by at most {f3(max(fmt_d) if fmt_d else None)} milli-log-loss given Elo and
        {f3(max(fmt_m) if fmt_m else None)} given the market.</p>
        <p><span class="kind">Observed</span><b>One match later.</b> The {n_top} strongest rows given Elo (ten per tour)
        were rebuilt with each player's history read as it stood at their previous match of that history, and scored again
        on the matches where both versions exist: a real feature changes a little, a leak would collapse. No row gains
        {n0(res["settings"]["large_market_gain"])} milli-log-loss or more on the closing odds (the plan's "clear", the size
        that would make it a suspected leak), so {"no row was" if n_big == 0 else f"{n_big} rows were"} checked on that
        ground; as a precaution, the {n_line} other rows that clear the family-wide line given the market were rebuilt
        too.</p>
        <p><span class="kind">Inferred</span>No check points to a leak. For the features about the latest matches (sets
        and minutes over 7 or 14 days, days since the last match), the version one match later is a different quantity,
        the load before the previous match (see the correlation column), so this check cannot tell a leak from recency for
        them; the probe can, and found none.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>One match later</h3><p>Milli-log-loss on the matches where both versions exist</p></div>
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Row</th><th class="r">Correlation of the two</th><th class="r">Given Elo</th><th class="r">One match later</th>
          <th class="r">Given the market</th><th class="r">One match later</th><th class="r">Matches</th></tr></thead>
          <tbody>{lag_rows}</tbody></table></div>
        <p class="note-small">Every check, with 95% ranges, is in <code>stage4_leak_checks.csv</code>; the probe is in
        <code>stage4_features_summary.json</code>.</p>
      </div>
    </div>''')

    # ------------------------------------------------------------------ how it was built
    exact = sum(1 for c in cov if c["exists_here"] == c["plan_present"])
    home_gap = sum(c["plan_present"] - c["exists_here"] for c in cov if c["id"] == "home" and c["tour"] == "atp")
    k_new = {(c["stat"], c["tour"]): c for c in res["constants"] if c["kind"] == "shrinkage K"}
    parts.append(f'''    <div class="sub">
      <h3>How Stage 4 was built and checked</h3>
      <ul class="plain">
        <li><b>Data.</b> {n0(res["pool"]["atp"])} men's and {n0(res["pool"]["wta"])} women's evaluation-level matches of
        2010–2026 (completed or retired); {n0(res["pool_evaluation"]["atp"])} and {n0(res["pool_evaluation"]["wta"])} of them are
        evaluation matches (2013–2026). Features read every singles match from 2010 as history.</li>
        <li><b>One chronological pass.</b> Every history goes through the study's as-of helper and Stage 3's look-back sums,
        never a per-row look-back. Stage 3's constants, ratings and Stage 1's Elo are used as they are.</li>
        <li><b>The plan reproduced.</b> For {exact} of {len(cov)} rows, the matches on which a feature exists equal the plan's
        own coverage counts; the one difference is the men's home country, {n0(home_gap)} matches fewer: the
        {n0(ec["matches_without_country"]["atp"])} matches of the Kingston events of 2026, whose country the name cannot
        place, less those already without a player's country.</li>
        <li><b>Constants set in Stage 4</b> (before any score; <code>stage4_constants.csv</code>), by Stage 3's method on
        2010–2018: match wins {n0((k_new.get(("win", "atp")) or {}).get("value"))} matches (men) and
        {n0((k_new.get(("win", "wta")) or {}).get("value"))} (women); break points above expectation: no spread between the men's
        seasons (every man gets the average), so that statistic carries nothing for the men by construction.</li>
        <li><b>The tournament's country.</b> A hand-made table (<code>stage4_event_country.csv</code>) from the city in each
        event's name. It agrees with tennis-data.co.uk's location on {n0(ec["tennis_data"]["agree"])} of
        {n0(ec["tennis_data"]["linked_matches"])} linked matches, with the country code of the WTA's 2013–2015 tournament ids
        on {ec["wta_ids"]["agree"]} of {ec["wta_ids"]["events"]} events, and with the WTA calendar on {ec["wta_calendar"]["agree"]} of
        {ec["wta_calendar"]["events"]}; every disagreement is listed in <code>stage4_event_country_check.csv</code>.</li>
        <li><b>Tests</b> (<code>test/predictability_diagnostic/test_stage4.py</code>): every feature family on hand-made
        histories against a row-by-row reading of the time rule; the Newton fits against scikit-learn's; walk-forward never
        seeing the season it scores; the copies staying inside their season; the family-wide line.</li>
      </ul>
    </div>''')

    data = {"tours": [[t, TOUR_LONG[t]] for t in TOUR], "table": table_data, "chart": chart,
            "eraWords": ERA_WORDS, "levelWords": dict(LEVELS), "warm": warm}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["rundown"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const f2 = v => v == null ? "–" : (v < 0 && Math.abs(v).toFixed(2) !== "0.00" ? "−" : "") + Math.abs(v).toFixed(2);
  const pc = v => v == null ? "–" : (100 * v).toFixed(1) + "%";
  const fmtN = v => v == null ? "–" : Math.round(v).toLocaleString("en-US");
  const tip = (node, rows) => window.reportTip.bind(node, rows);
  const seg = (attr, fn) => document.querySelectorAll(`#rundown [${attr}]`).forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(`#rundown [${attr}]`).forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    fn(b.getAttribute(attr));
  }));

  // ---------------------------------------------------------------- the sortable ranking
  (function ranking() {
    const tbl = document.getElementById("s4-rank");
    const cols = [
      { k: "rank", t: "#", num: true, f: v => v == null ? "–" : String(v) },
      { k: "label", t: "Candidate (form)" },
      { k: "cov", t: "Coverage", num: true, f: pc },
      { k: "elo", t: "Given Elo", num: true, f: (v, r) => f2(v) + " (" + f2(r.lo) + " to " + f2(r.hi) + ")" },
      { k: "bmax", t: "Band max", num: true, f: f2 },
      { k: "line", t: "Line", f: v => v ? "clears" : "" },
      { k: "eras", t: "Eras +", num: true, f: (v, r) => v == null ? "–" : v + " of " + r.eras_n },
      { k: "e19", t: "2019–26", num: true, f: f2 },
      { k: "e22", t: "2022–26", num: true, f: f2 },
      { k: "alone", t: "Alone", num: true, f: f2 },
      { k: "mkt", t: "Given market", num: true, f: (v, r) => f2(v) + (r.mband ? " ▲" : "") },
      { k: "reading", t: "Reading" },
      { k: "exp", t: "Expected → seen", f: (v, r) => v + " → " + r.obs },
    ];
    let tour = "atp", key = "rank", dir = 1, show = "all";
    const head = tbl.querySelector("thead tr");
    cols.forEach(c => {
      const th = el("th", c.num ? "r" : null);
      const b = el("button", null, c.t);
      b.type = "button";
      b.style.cssText = "font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer;text-transform:inherit;letter-spacing:inherit";
      b.addEventListener("click", () => { if (key === c.k) dir = -dir; else { key = c.k; dir = c.num && c.k !== "rank" ? -1 : 1; } draw(); });
      th.appendChild(b); th.dataset.k = c.k; head.appendChild(th);
    });
    function draw() {
      head.querySelectorAll("th").forEach(th => th.setAttribute("aria-sort", th.dataset.k === key ? (dir > 0 ? "ascending" : "descending") : "none"));
      const rows = D.table[tour].filter(r => show === "all" || (r.elo != null && r.bmax != null && r.elo > r.bmax));
      rows.sort((a, b) => {
        const x = a[key], y = b[key];
        if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
        return (typeof x === "string" ? x.localeCompare(y) : (x - y)) * dir;
      });
      const body = tbl.querySelector("tbody");
      body.replaceChildren();
      rows.forEach(r => {
        const tr = el("tr");
        cols.forEach(c => {
          const td = el("td", c.num ? "r" : null, c.f ? c.f(r[c.k], r) : (r[c.k] == null ? "–" : String(r[c.k])));
          if (c.k === "reading" && r.reading === "finding") td.style.fontWeight = "650";
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }
    seg("data-s4tour", v => { tour = v; draw(); });
    seg("data-s4show", v => { show = v; draw(); });
    draw();
  })();

  // ---------------------------------------------------------------- the leading rows by era and level
  (function leaders() {
    const host = document.getElementById("s4-lead-chart");
    const pick = document.getElementById("s4-lead");
    const tbody = document.querySelector("#s4-lead-table tbody");
    let score = "elo";
    function draw() {
      host.replaceChildren(); tbody.replaceChildren();
      const cell = D.chart[pick.value];
      let lo = 0, hi = 0;
      D.tours.forEach(([t]) => (cell[t + "|" + score] || []).forEach(g => {
        [g.lo, g.hi, g.bmin, g.bmax].forEach(v => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
      }));
      const span = Math.max(hi - lo, 0.5);
      const step = span <= 2 ? 0.5 : span <= 5 ? 1 : span <= 12 ? 2 : span <= 30 ? 5 : 10;
      lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
      D.tours.forEach(([t, name]) => {
        const rows = cell[t + "|" + score] || [];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        if (!rows.length) { box.appendChild(el("p", "note-small", "Not scored on this tour.")); host.appendChild(box); return; }
        const W = 460, L = 190, R = 14, T = 8, B = 32, rowH = 22, gapH = 12;
        const H = T + rows.length * rowH + gapH + B;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": improvement by era and level group with 95% ranges and the shuffled copies' range; the table below holds the numbers" });
        const x = v => L + (W - L - R) * (v - lo) / (hi - lo);
        for (let v = lo; v <= hi + 1e-9; v += step) {
          const vv = Math.round(v * 100) / 100;
          S("line", { x1: x(vv), x2: x(vv), y1: T, y2: H - B, class: vv === 0 ? "ref" : "grid" }, svg);
          S("text", { x: x(vv), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = (vv < 0 ? "−" : "") + Math.abs(vv);
        }
        S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "milli-log-loss better (+) or worse (−)";
        let yy = T;
        rows.forEach((g, i) => {
          if (i > 0 && g.kind !== rows[i - 1].kind) yy += gapH;
          const yc = yy + rowH / 2;
          const lab = g.kind === "era" ? D.eraWords[g.g] : D.levelWords[g.g];
          S("text", { x: L - 8, y: yc + 4, "text-anchor": "end", class: "lab" }, svg).textContent = lab;
          if (g.bmin != null && g.bmax != null) S("rect", { x: x(g.bmin), y: yc - 6, width: Math.max(1, x(g.bmax) - x(g.bmin)), height: 12, class: "band", rx: 2 }, svg);
          if (g.lo != null && g.hi != null) S("line", { x1: x(g.lo), x2: x(g.hi), y1: yc, y2: yc, stroke: "var(--ink-2)", "stroke-width": 1 }, svg);
          const dot = S("circle", { cx: x(g.imp), cy: yc, r: 4.5, fill: g.dir ? "var(--surface)" : "var(--series-1)",
            stroke: g.dir ? "var(--series-1)" : "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          const hit = S("rect", { x: 0, y: yy, width: W, height: rowH, class: "hit" }, svg);
          const rowsFn = () => [f2(g.imp) + " milli-log-loss", lab + " · " + name, "95% range " + f2(g.lo) + " to " + f2(g.hi),
            "copies " + f2(g.bmin) + " to " + f2(g.bmax) + " · " + fmtN(g.n) + " matches" + (g.dir ? " · directional only" : "")];
          tip(hit, rowsFn); tip(dot, rowsFn);
          const tr = el("tr");
          [name, lab, fmtN(g.n) + (g.dir ? " *" : ""), f2(g.imp), f2(g.lo) + " to " + f2(g.hi), f2(g.bmin) + " to " + f2(g.bmax)]
            .forEach((v, j) => tr.appendChild(el("td", j >= 2 ? "r" : null, v)));
          tbody.appendChild(tr);
          yy += rowH;
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    pick.addEventListener("change", draw);
    seg("data-s4score", v => { score = v; draw(); });
    draw();
  })();

  // ---------------------------------------------------------------- the warm-up seasons
  (function warm() {
    const host = document.getElementById("s4-warm");
    let lo = 0, hi = 0;
    D.tours.forEach(([t]) => D.warm[t].forEach(s => s.pts.forEach(p => { if (p[1] != null) { lo = Math.min(lo, p[1]); hi = Math.max(hi, p[1]); } })));
    const step = (hi - lo) <= 6 ? 1 : 2;
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    D.tours.forEach(([t, name]) => {
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, H = 250, L = 40, R = 14, T = 10, B = 34;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": improvement given Elo season by season for the ranking, ranking points and recent level; the table below holds the numbers" });
      const x0 = 2013, x1 = 2026;
      const x = v => L + (W - L - R) * (v - x0) / (x1 - x0);
      const y = v => T + (H - T - B) * (hi - v) / (hi - lo);
      for (let v = lo; v <= hi + 1e-9; v += step) {
        S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: v === 0 ? "ref" : "grid" }, svg);
        S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = (v < 0 ? "−" : "") + Math.abs(v);
      }
      [2013, 2016, 2019, 2022, 2026].forEach(v => { S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v; });
      S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "season";
      D.warm[t].forEach((s, i) => {
        const color = "var(--series-" + (i + 1) + ")";
        const pts = s.pts.filter(p => p[1] != null);
        if (pts.length > 1) S("path", { d: pts.map((p, j) => (j ? "L" : "M") + x(p[0]).toFixed(1) + "," + y(p[1]).toFixed(1)).join(" "),
          fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
        pts.forEach(p => {
          const dot = S("circle", { cx: x(p[0]), cy: y(p[1]), r: 4, fill: color, stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          const hit = S("circle", { cx: x(p[0]), cy: y(p[1]), r: 12, class: "hit" }, svg);
          const rowsFn = () => [f2(p[1]) + " milli-log-loss", s.label + " · " + p[0] + " · " + name, "95% range " + f2(p[2]) + " to " + f2(p[3]) + " · " + fmtN(p[4]) + " matches"];
          tip(hit, rowsFn); tip(dot, rowsFn);
        });
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();
})();
"""
