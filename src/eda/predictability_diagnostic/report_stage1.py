"""Report section for Stage 1, "How predictable is tennis?": the baselines (coin, ranking, Elo, surface Elo,
closing odds) scored by log loss, by level, season and cell; how often favourites win; calibration; and the
room between Elo and the market.

Every number comes from stage1_results.json, stage1_baselines_summary.json and stage1_odds_summary.json
(render_report.py assembles the page).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": 1, "id": "how-predictable", "title": "How predictable is tennis?"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "ATP (men)", "wta": "WTA (women)"}
LEVEL_WORDS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
               "GSQ": "Grand Slam qualifying", "TQ": "Tour qualifying", "CH": "Challenger / WTA 125",
               "CHQ": "Challenger / 125 qualifying"}
TOUR_LEVEL = ("GS", "FIN", "T1000", "T500", "T250")
ERAS = ("2013-16", "2017-19", "2020-21", "2022-26")
ERA_WORDS = {"2013-16": "2013–16", "2017-19": "2017–19", "2020-21": "2020–21", "2022-26": "2022–26"}
HEAD = "2022-2026 (headline)"
GAP_BINS = [0, 5, 10, 15, 20, 25, 30]          # milli-log-loss; the last bin is open
ELO = "p_elo_surf_ret"                           # the Elo the charts show: surface-blended, retirements counted
BAR_KEYS = [("p_rank", "Ranking", "rank"), ("p_points", "Ranking points", "rank"), ("p_elo_ret", "Elo", "elo"),
            ("p_elo_surf_ret", "Surface Elo", "elo"), ("p_market", "Market (closing odds)", "market")]


def esc(x) -> str:
    return html.escape(str(x))


def n(x) -> str:
    return f"{int(round(x)):,}"


def ll3(x) -> str:
    return f"{x:.3f}"


def mm(x, signed=False) -> str:
    return f"{x:+.1f}" if signed else f"{x:.1f}"


def pct(x, d=1) -> str:
    return f"{x:.{d}f}%"


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div>'
            f'<div class="note">{note}</div></div>')


def better(milli: float) -> str:
    """'12.3 better' / '4.1 worse' for a difference a - b where lower is better (b is the comparison)."""
    return f"{abs(milli):.1f} {'worse' if milli > 0 else 'better'}"


def gap_bin(v: float) -> int:
    k = 0
    for i, edge in enumerate(GAP_BINS):
        if v >= edge:
            k = i
    return k


def render(study_dir: Path) -> dict:
    r = load(study_dir, "stage1_results.json")
    bs = load(study_dir, "stage1_baselines_summary.json")
    od = load(study_dir, "stage1_odds_summary.json")
    head = {(h["tour"], h["window"]): h for h in r["headline"]}
    H = {t: head[(t, HEAD)] for t in TOUR}
    ALL = {t: head[(t, "2013-2026")] for t in TOUR}
    coin = r["coin"]
    parts = []

    # ------------------------------------------------------------------ intro and tiles
    fav = {f["tour"]: f for f in r["favourites_headline"]}
    gapm = {t: H[t]["gaps_milli"][ELO] for t in TOUR}
    parts.append(f'''    <div class="prose">
      <p>Stage 1 asks how far the simplest predictors get. Each gives, before a match, a probability that one player
      wins: a coin, the players' rankings, an Elo rating built from every earlier result, and the bookmakers' closing odds.
      Each is scored on the {n(r["counts"]["atp"]["evaluation"])} men's and {n(r["counts"]["wta"]["evaluation"])} women's evaluation
      matches of 2013 to September 2026 by <b>log loss</b>: the average, over matches, of minus the natural log of the
      probability given to the player who won. A coin, always 50%, scores {coin:.3f}; lower is better, and a thousandth
      (0.001) is one <b>milli-log-loss</b>. The odds exist only for tour-level main draws, so every comparison with the
      market is made on the same matches. The headline window is 2022–2026.</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("Surface Elo, every evaluation match, 2022–2026", ll3(H["atp"][ELO]), ll3(H["wta"][ELO]),
                 f"coin {coin:.3f}; {n(H['atp']['n'])} and {n(H['wta']['n'])} matches, Challengers and qualifying included")}
      {pair_tile("Closing odds, 2022–2026", ll3(H["atp"]["market_subset"]["p_market"]), ll3(H["wta"]["market_subset"]["p_market"]),
                 f"tour-level main draws with odds: {n(H['atp']['market_subset']['n'])} and {n(H['wta']['market_subset']['n'])} matches")}
      {pair_tile("Room between Elo and the market", mm(gapm["atp"]["milli"]), mm(gapm["wta"]["milli"]),
                 "milli-log-loss by which surface Elo is worse than the closing odds on the same matches, 2022–2026")}
      {pair_tile("The market's favourite won", pct(fav["atp"]["p_market"]["favourite_won_pct"]), pct(fav["wta"]["p_market"]["favourite_won_pct"]),
                 "matches with odds, 2022–2026; the favourite is the player with the shorter odds")}
    </div>''')

    # ------------------------------------------------------------------ terms
    tuned = {(c["tour"], c["rule"]): c for c in bs["chosen"]}
    parts.append(f'''    <div class="sub">
      <h3>The baselines, in plain words</h3>
      <dl class="terms">
        <dt>Walk-forward</dt><dd>Every probability is made before the match, from earlier matches only (earlier weeks, and
        earlier rounds of the same event). Nothing is fitted on the match it predicts.</dd>
        <dt>Ranking</dt><dd>The ATP and WTA rankings order players by the points they earned over the last 52 weeks; ranking
        points are those points. Here, a one-input logistic regression turns the log of the ratio of the two ranks (and,
        separately, of the two players' points) into a probability, refitted each season on the seasons before it. A player
        with no ranking is given the rank just below the lowest seen on the tour in earlier seasons, and no points.</dd>
        <dt>Elo</dt><dd>A rating that rises when a player wins and falls when they lose, by more when the result was a surprise;
        the gap between two ratings gives the probability. It is run over every singles match since 2010, down to the ITF level,
        so newcomers arrive with a rating. A player's rating moves fast over their first matches and settles as they play more
        (the <i>K</i> factor shrinks with the number of matches).</dd>
        <dt>Surface Elo</dt><dd>Each player also has a separate rating on each surface (hard, clay, grass, carpet), moved only by
        matches on it. The prediction mixes the two: {pct(100 * (1 - tuned[("atp", "ret")]["w"]), 0)} overall and
        {pct(100 * tuned[("atp", "ret")]["w"], 0)} surface for the men, {pct(100 * (1 - tuned[("wta", "ret")]["w"]), 0)} and
        {pct(100 * tuned[("wta", "ret")]["w"], 0)} for the women.</dd>
        <dt>Closing odds</dt><dd>The last bookmaker prices before a match, as tennis-data.co.uk records them (its own words:
        "generally the most recent before play starts"): the average over bookmakers of each player's decimal odds. Decimal
        odds of 2.50 return 2.50 for each 1 staked, so 1/2.50 = 40% is the implied probability. The two players' implied
        probabilities add to a little more than one (the bookmakers' margin, or <b>overround</b>: median
        {od["quotes"]["avg"]["overround_quantiles"]["0.5"]:.3f}), so they are scaled to add to one.</dd>
        <dt>Favourite</dt><dd>The player a baseline gives more than 50%.</dd>
        <dt>Calibration</dt><dd>Whether favourites given 70% win about 70% of the time.</dd>
        <dt>Tuning years</dt><dd>Elo's few constants were chosen on 2013–2018 and then frozen, so later seasons are a fair test.</dd>
      </dl>
    </div>''')

    # ------------------------------------------------------------------ A. better than a coin
    bars, bars_n = {}, {}
    for t in TOUR:
        ms = H[t]["market_subset"]
        bars[t] = [{"key": k, "label": lab, "family": fam, "ll": ms[k], "milli": 1000 * (coin - ms[k])} for k, lab, fam in BAR_KEYS]
        bars_n[t] = ms["n"]
    twin = "".join(f'<tr><td>{esc(TOUR[t])}</td>' + "".join(f'<td class="r">{mm(b["milli"])}</td>' for b in bars[t])
                   + f'<td class="r">{n(bars_n[t])}</td></tr>' for t in TOUR)
    parts.append(f'''    <div class="sub">
      <h3>How far each baseline gets</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>On the tour-level matches with odds of 2022–2026, the ranking alone is
        {mm(bars["atp"][0]["milli"])} milli-log-loss better than a coin for the men and {mm(bars["wta"][0]["milli"])} for the women.
        Surface Elo is {mm(bars["atp"][3]["milli"])} and {mm(bars["wta"][3]["milli"])} better, and the closing odds
        {mm(bars["atp"][4]["milli"])} and {mm(bars["wta"][4]["milli"])}. So on these matches surface Elo covers
        {pct(100 * bars["atp"][3]["milli"] / bars["atp"][4]["milli"], 0)} (men) and {pct(100 * bars["wta"][3]["milli"] / bars["wta"][4]["milli"], 0)} (women)
        of the distance from a coin to the market, and the ranking {pct(100 * bars["atp"][0]["milli"] / bars["atp"][4]["milli"], 0)} and
        {pct(100 * bars["wta"][0]["milli"] / bars["wta"][4]["milli"], 0)}.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Better than a coin, by baseline</h3><p>Milli-log-loss below the coin's {coin:.3f}; tour-level main draws with odds, 2022–2026</p></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-3)"></span>Ranking-based</span>
          <span class="key"><span class="sw-rect" style="background:var(--series-1)"></span>Elo-based</span>
          <span class="key"><span class="sw-rect" style="background:var(--series-2)"></span>Market</span>
        </div>
        <div class="chart-pair" id="s1-bars"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Tour</th>{"".join(f'<th class="r">{esc(lab)}</th>' for _, lab, _ in BAR_KEYS)}<th class="r">Matches</th></tr></thead>
          <tbody>{twin}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ B. by season
    years_odds, years_all = {}, {}
    ym = r["margins"]["year"]["rows"]
    for t in TOUR:
        rows = sorted([x for x in ym if x["tour"] == t], key=lambda x: x["year"])
        years_odds[t] = {"rank": [[x["year"], x.get("p_rank__m"), x.get("n_market")] for x in rows],
                         "elo": [[x["year"], x.get(f"{ELO}__m"), x.get("n_market")] for x in rows],
                         "market": [[x["year"], x.get("p_market__m"), x.get("n_market")] for x in rows]}
        years_all[t] = {"rank": [[x["year"], x["p_rank"], x["n"]] for x in rows],
                        "elo": [[x["year"], x[ELO], x["n"]] for x in rows]}
    ytwin = []
    for t in TOUR:
        for x in sorted([x for x in ym if x["tour"] == t], key=lambda x: x["year"]):
            def c(v):
                return f'<td class="r">{ll3(v)}</td>' if v is not None else '<td class="r">–</td>'
            ytwin.append(f'<tr><td>{TOUR[t]}</td><td>{x["year"]}{" (tuning)" if x["year"] <= 2018 else ""}</td>'
                         f'<td class="r">{n(x["n"])}</td>{c(x["p_rank"])}{c(x[ELO])}'
                         f'<td class="r">{n(x["n_market"]) if x.get("n_market") else "–"}</td>{c(x.get("p_rank__m"))}'
                         f'{c(x.get(f"{ELO}__m"))}{c(x.get("p_market__m"))}</tr>')
    gy = {(g["tour"], g["year"]): g["gap_surf"] for g in r["margins"]["year"]["gaps"]}
    post = {t: [gy[k]["milli"] for k in gy if k[0] == t and k[1] >= 2019 and gy[k]["n"] >= r["directional_only_below"]] for t in TOUR}
    hold = r["order_holds_every_season"]
    if all(hold[t]["with_odds"] and hold[t]["all_evaluation_elo_below_rank"] for t in TOUR):
        order_text = ("In every season on both tours the order is the same: on the matches with odds the market is below surface Elo "
                      "and surface Elo below the ranking, and on all evaluation matches surface Elo is below the ranking.")
    else:
        bad = [f'{TOUR[o["tour"]]} {o["year"]}' for o in r["order_by_season"]
               if not o.get("market_below_elo_below_rank", True) or not o["all_elo_below_rank"]]
        order_text = "The order market, surface Elo, ranking holds in every season except " + ", ".join(bad) + "."
    tun = {t: head[(t, "2013-2018 (tuning)")]["gaps_milli"][ELO] for t in TOUR}
    aft = {t: head[(t, "2019-2026")]["gaps_milli"][ELO] for t in TOUR}
    ms_t = {t: head[(t, "2013-2018 (tuning)")]["market_subset"] for t in TOUR}
    ms_a = {t: head[(t, "2019-2026")]["market_subset"] for t in TOUR}
    gain = {d["tour"]: 1000 * (d["default_538"] - d["best"]) for d in bs["tuning_detail"] if d["rule"] == "ret"}

    def moved(t):
        return (f'the market from {ll3(ms_t[t]["p_market"])} to {ll3(ms_a[t]["p_market"])} and surface Elo from '
                f'{ll3(ms_t[t][ELO])} to {ll3(ms_a[t][ELO])}')
    parts.append(f'''    <div class="sub">
      <h3>Season by season</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>{order_text} The room between surface Elo and the market is
        {mm(tun["atp"]["milli"])} milli-log-loss (men) and {mm(tun["wta"]["milli"])} (women) over the tuning years 2013–2018, and
        {mm(aft["atp"]["milli"])} and {mm(aft["wta"]["milli"])} over 2019–2026, where a season's ranges from {mm(min(post["atp"]))} to
        {mm(max(post["atp"]))} for the men and {mm(min(post["wta"]))} to {mm(max(post["wta"]))} for the women. There are no men's odds for
        2018 (tennis-data.co.uk has no ATP 2018 file), and the 2026 odds stop on 3 August. From one period to the other, on the
        matches with odds, the men's log losses moved: {moved("atp")}; the women's: {moved("wta")}.
        <span class="kind">Inferred</span>Tuning improved Elo's 2013–2018 log loss by only {mm(gain["atp"])} (men) and {mm(gain["wta"])} (women)
        milli-log-loss over FiveThirtyEight's constants, so the tuning years flattering Elo explains little of the wider room after 2018;
        later seasons have been harder for a rating than for the market. The women's 2026 season is inflated by a Stage 0 problem
        described under the checks below.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Log loss by season</h3><p>Lower is better; the shaded seasons tuned Elo's constants</p></div>
        <div class="controls"><span>Matches:</span><div class="seg" role="group" aria-label="Which matches">
          <button type="button" data-mode="odds" aria-pressed="true">With closing odds</button>
          <button type="button" data-mode="all" aria-pressed="false">All evaluation matches (no odds)</button></div></div>
        <div class="legend" id="s1-years-legend"></div>
        <div class="chart-pair" id="s1-years"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Season</th><th class="r">Matches</th><th class="r">Ranking</th><th class="r">Surface Elo</th>
          <th class="r">With odds</th><th class="r">Ranking</th><th class="r">Surface Elo</th><th class="r">Market</th></tr></thead>
          <tbody>{"".join(ytwin)}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ C. by level
    lv = {(x["tour"], x["level_group"]): x for x in r["margins"]["level"]["rows"]}
    lg = {(g["tour"], g["level_group"]): g for g in r["margins"]["level"]["gaps"]}
    trs = []
    for t in TOUR:
        trs.append(f'<tr class="group"><td colspan="10">{TOUR_LONG[t]}</td></tr>')
        for code, _ in r["level_groups"]:
            x = lv.get((t, code))
            if not x:
                continue
            vals = [x["p_rank"], x["p_points"], x["p_elo_ret"], x[ELO]]
            best = min(vals)
            cells = "".join(f'<td class="r{" best" if v == best else ""}">{ll3(v)}</td>' for v in vals)
            g = lg.get((t, code))
            if g and x.get("n_market"):
                gg = g["gap_surf"]
                mk = (f'<td class="r">{n(x["n_market"])}</td><td class="r">{ll3(x[f"{ELO}__m"])}</td>'
                      f'<td class="r">{ll3(x["p_market__m"])}</td><td class="r">{mm(gg["milli"])}{"*" if gg["directional_only"] else ""}</td>')
            else:
                mk = '<td class="r">–</td><td class="r">–</td><td class="r">–</td><td class="r">–</td>'
            dir_mark = '<span class="tag">under 300</span>' if x["n"] < r["directional_only_below"] else ""
            trs.append(f'<tr><td>{esc(LEVEL_WORDS[code])}{dir_mark}</td><td class="r">{n(x["n"])}</td>{cells}{mk}</tr>')
    gs_bo = {(x["tour"], x["best_of"]): x for x in r["margins"]["best_of"]["rows"]}
    surf = {(x["tour"], x["surface"]): x for x in r["margins"]["surface"]["rows"]}
    era = {(x["tour"], x["era"]): x for x in r["margins"]["era"]["rows"]}

    def small_table(rows_by, keys, label_fn):
        out = []
        for t in TOUR:
            for k in keys:
                x = rows_by.get((t, k))
                if not x:
                    continue
                m_ = (f'<td class="r">{n(x["n_market"])}</td><td class="r">{ll3(x[f"{ELO}__m"])}</td><td class="r">{ll3(x["p_market__m"])}</td>'
                      if x.get("n_market") else '<td class="r">–</td><td class="r">–</td><td class="r">–</td>')
                out.append(f'<tr><td>{TOUR[t]}</td><td>{esc(label_fn(k))}</td><td class="r">{n(x["n"])}</td><td class="r">{ll3(x["p_rank"])}</td>'
                           f'<td class="r">{ll3(x["p_elo_ret"])}</td><td class="r">{ll3(x[ELO])}</td>{m_}</tr>')
        head_ = ('<thead><tr><th>Tour</th><th></th><th class="r">Matches</th><th class="r">Ranking</th><th class="r">Elo</th>'
                 '<th class="r">Surface Elo</th><th class="r">With odds</th><th class="r">Surface Elo</th><th class="r">Market</th></tr></thead>')
        return f'<div class="table-wrap"><table class="num wide">{head_}<tbody>{"".join(out)}</tbody></table></div>'

    best_level = {t: min(((code, lv[(t, code)][ELO]) for code, _ in r["level_groups"] if (t, code) in lv
                          and lv[(t, code)]["n"] >= r["directional_only_below"]), key=lambda z: z[1]) for t in TOUR}
    worst_level = {t: max(((code, lv[(t, code)][ELO]) for code, _ in r["level_groups"] if (t, code) in lv
                           and lv[(t, code)]["n"] >= r["directional_only_below"]), key=lambda z: z[1]) for t in TOUR}
    csg = {(c["tour"], c["best_of"], c["series"]): c for c in r["calibration_signed"]}
    e5 = csg[("atp", 5, "Surface Elo, matches with odds, 2013-2026")]["won_minus_given_points"]
    e3 = csg[("atp", 3, "Surface Elo, matches with odds, 2013-2026")]["won_minus_given_points"]
    k5 = csg[("atp", 5, "Market, matches with odds, 2013-2026")]["won_minus_given_points"]
    k3 = csg[("atp", 3, "Market, matches with odds, 2013-2026")]["won_minus_given_points"]
    bog = {(g["tour"], g["best_of"]): g for g in r["best_of_gaps"]}
    bo = {k: v for k, v in gs_bo.items()}

    def level_phrase(t):
        b, w = best_level[t], worst_level[t]
        return (f'best in {esc(LEVEL_WORDS[b[0]])} ({ll3(b[1])}) and worst in {esc(LEVEL_WORDS[w[0]])} ({ll3(w[1])})')

    parts.append(f'''    <div class="sub">
      <h3>By level</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>How predictable a match is depends on where it is played. Among levels with at least 300
        matches, surface Elo does {level_phrase("atp")} for the men, and {level_phrase("wta")} for the women. The men's Grand Slam main
        draws are the only best-of-five matches (the first to win three sets): there surface Elo scores {ll3(bo[("atp", 5)][ELO])}, against
        {ll3(bo[("atp", 3)][ELO])} at best of three.</p>
        <p><span class="kind">Inferred</span>A longer match gives the stronger player more room to prevail, but Elo gives the same probability
        whatever the length. <span class="kind">Observed</span>Over 2013–2026, on the men's matches with odds, surface Elo's favourites won
        {mm(abs(e5))} points {"more" if e5 > 0 else "less"} often than it said at best of five and {mm(abs(e3))} points {"more" if e3 > 0 else "less"} often at best of
        three (the market's: {mm(k5, True)} and {mm(k3, True)}), and the room between Elo and the market is {mm(bog[("atp", 5)]["milli"])} milli-log-loss
        at best of five against {mm(bog[("atp", 3)]["milli"])} at best of three.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Log loss by level, 2013–2026</h3><p>Lower is better; the best baseline in bold. The last four columns use only matches with odds.</p></div>
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th>Level</th><th class="r">Matches</th><th class="r">Ranking</th><th class="r">Points</th><th class="r">Elo</th>
          <th class="r">Surface Elo</th><th class="r">With odds</th><th class="r">Surface Elo</th><th class="r">Market</th><th class="r">Room</th></tr></thead>
          <tbody>{"".join(trs)}</tbody></table></div>
        <p class="note-small">Room: milli-log-loss by which surface Elo is worse than the market on the same matches. * under 300 matches with
        odds, directional only. Grand Slam, Challenger and all qualifying matches with no odds are scored by the other baselines only.</p>
        <details class="twin"><summary>By best of three or five sets</summary>{small_table(gs_bo, [3, 5], lambda k: f"Best of {k}")}</details>
        <details class="twin"><summary>By surface</summary>{small_table(surf, ["Hard", "Clay", "Grass", "Carpet", "unknown"], str)}</details>
        <details class="twin"><summary>By era</summary>{small_table(era, list(ERAS), lambda k: ERA_WORDS[k] + (" (tuning years)" if k == "2013-16" else " (tuning to 2018)" if k == "2017-19" else ""))}</details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ D. the room, by level and era
    le = {(g["tour"], g["level_group"], g["era"]): g["gap_surf"] for g in r["margins"]["level_era"]["gaps"]}
    heat = []
    for t in TOUR:
        rows_h = []
        for code in TOUR_LEVEL:
            cells = []
            for e in ERAS:
                g = le.get((t, code, e))
                if not g or not g.get("n"):
                    cells.append('<td class="v none">–</td>')
                    continue
                k = gap_bin(g["milli"])
                style = (f'background:var(--seq-{k});color:var(--seq-ink-{k})' if g["milli"] >= 0 else "")
                tip = "|".join([f'{mm(g["milli"], True)} milli-log-loss', f'{TOUR[t]} · {LEVEL_WORDS[code]} · {ERA_WORDS[e]}',
                                f'{n(g["n"])} matches with odds', f'95% range {mm(g["lo"], True)} to {mm(g["hi"], True)}'])
                cls = "v" + (" dir" if g["directional_only"] else "")
                cells.append(f'<td class="{cls}" style="{style}" tabindex="0" data-tip="{esc(tip)}">{mm(g["milli"])}{"*" if g["directional_only"] else ""}</td>')
            rows_h.append(f'<tr><td>{esc(LEVEL_WORDS[code])}</td>{"".join(cells)}</tr>')
        heat.append(f'''<div class="heat"><h4>{TOUR_LONG[t]}</h4><div class="table-wrap"><table class="heat">
          <thead><tr><th>Level</th>{"".join(f'<th class="r">{ERA_WORDS[e]}</th>' for e in ERAS)}</tr></thead>
          <tbody>{"".join(rows_h)}</tbody></table></div></div>''')
    scale = "".join(f'<span style="display:inline-flex;align-items:center;gap:4px"><span class="sw" style="background:var(--seq-{i})"></span>'
                    f'{GAP_BINS[i]}{"–" + str(GAP_BINS[i + 1]) if i + 1 < len(GAP_BINS) else "+"}</span>' for i in range(len(GAP_BINS)))
    parts.append(f'''    <div class="sub">
      <h3>The room between Elo and the market</h3>
      <div class="prose">
        <p>The gap between surface Elo and the closing odds on the same matches is the room a statistic added to a rating would
        have to fill to price matches as well as the market does. <span class="kind">Inferred</span>It is not a hard ceiling:
        the market is itself an estimate, and a statistic it underweights could in principle beat it; but it is the natural
        target. <span class="kind">Observed</span>Over 2013–2026 it is {mm(ALL["atp"]["gaps_milli"][ELO]["milli"])} milli-log-loss for the men
        (95% range {mm(ALL["atp"]["gaps_milli"][ELO]["lo"])}–{mm(ALL["atp"]["gaps_milli"][ELO]["hi"])}) and {mm(ALL["wta"]["gaps_milli"][ELO]["milli"])} for the women
        ({mm(ALL["wta"]["gaps_milli"][ELO]["lo"])}–{mm(ALL["wta"]["gaps_milli"][ELO]["hi"])}).</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Room between surface Elo and the market, by level and era</h3><p>Milli-log-loss, Elo worse than the market; hover a cell for its matches and range</p></div>
        <div class="scale" aria-hidden="true"><span class="lbl">Milli-log-loss:</span>{scale}<span style="display:inline-flex;align-items:center;gap:4px"><span class="sw none"></span>below 0: Elo better than the market</span><span>* under 300 matches with odds, directional only</span></div>
        <div class="chart-pair" id="s1-heat">{"".join(heat)}</div>
      </div>
    </div>''')

    # ------------------------------------------------------------------ E. calibration
    cal = {}
    for row in r["calibration"]:
        key = {"Surface Elo, matches with odds": "elo", "Market, matches with odds": "market"}.get(row["series"])
        if key and row["n"] > 0:
            cal.setdefault(row["tour"], {}).setdefault(key, []).append(
                {k: row[k] for k in ("bin", "n", "mean_p", "won", "won_lo", "won_hi")})
    ctwin = "".join(
        f'<tr><td>{TOUR[row["tour"]]}</td><td>{esc(row["series"])}</td><td>{esc(row["bin"])}</td><td class="r">{n(row["n"])}</td>'
        f'<td class="r">{pct(100 * row["mean_p"])}</td><td class="r">{pct(100 * row["won"])}</td></tr>'
        for row in r["calibration"] if row["n"] > 0)
    cal_err = {}
    for t in TOUR:
        for key in ("elo", "market"):
            pts = [p for p in cal[t][key] if p["n"] >= 100]
            cal_err[(t, key)] = max(abs(p["won"] - p["mean_p"]) for p in pts) * 100
    sg = {(c["tour"], c["series"]): c for c in r["calibration_signed"] if c["best_of"] == "all"}

    def lean(t, series):
        v = sg[(t, series)]["won_minus_given_points"]
        return f'{mm(abs(v))} points {"more" if v > 0 else "less"}'

    parts.append(f'''    <div class="sub">
      <h3>Are the probabilities honest?</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>On the matches with odds of 2022–2026, favourites won roughly as often as they were
        given. In every probability band with at least 100 matches, the share the favourite won is within
        {mm(cal_err[("atp", "elo")])} points of surface Elo's average probability for the men and {mm(cal_err[("wta", "elo")])} for the women,
        and within {mm(cal_err[("atp", "market")])} and {mm(cal_err[("wta", "market")])} points of the market's. Over all those matches, surface Elo's
        favourites won {lean("atp", "Surface Elo, matches with odds")} often than it said for the men and {lean("wta", "Surface Elo, matches with odds")}
        for the women; the market's favourites won {lean("atp", "Market, matches with odds")} and {lean("wta", "Market, matches with odds")} often than
        their price said.</p>
        <p><span class="kind">Inferred</span>Neither is far off the diagonal, so the market's lead comes mostly from telling likely
        winners from likely losers more sharply, not from Elo's probabilities being systematically too bold or too timid. The market's
        small lean is the direction of the well-known <i>favourite–longshot bias</i>: outsiders' odds a little too short, favourites'
        a little too long.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Calibration, 2022–2026</h3><p>Share of matches the favourite won, against the probability it was given; the diagonal is perfect calibration</p></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-line" style="background:var(--series-1)"></span>Surface Elo</span>
          <span class="key"><span class="sw-line" style="background:var(--series-2)"></span>Market</span>
          <span class="key"><span class="sw-line" style="background:var(--rule)"></span>Perfect calibration</span>
        </div>
        <div class="chart-pair" id="s1-cal"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Tour</th><th>Series</th><th>Probability band</th><th class="r">Matches</th><th class="r">Given</th><th class="r">Won</th></tr></thead>
          <tbody>{ctwin}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ F. favourites
    ftr = []
    for f in r["favourites"]:
        if f["level_group"] == "ALL":
            continue
        ms = f.get("market_subset") or {}
        mcell = (f'<td class="r">{pct(ms["p_market"]["favourite_won_pct"])}</td><td class="r">{n(ms["p_market"]["n"])}</td>'
                 if ms else '<td class="r">–</td><td class="r">–</td>')
        ftr.append(f'<tr><td>{TOUR[f["tour"]]}</td><td>{esc(LEVEL_WORDS[f["level_group"]])}</td>'
                   f'<td class="r">{pct(f["p_rank"]["favourite_won_pct"])}</td><td class="r">{pct(f[ELO]["favourite_won_pct"])}</td>'
                   f'<td class="r">{n(f[ELO]["n"])}</td>{mcell}</tr>')
    allf = {f["tour"]: f for f in r["favourites"] if f["level_group"] == "ALL"}
    parts.append(f'''    <div class="sub">
      <h3>How often the favourite won</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>Over all evaluation matches of 2013–2026, the better-ranked player won
        {pct(allf["atp"]["p_rank"]["favourite_won_pct"])} of men's and {pct(allf["wta"]["p_rank"]["favourite_won_pct"])} of women's matches, and surface Elo's
        favourite {pct(allf["atp"][ELO]["favourite_won_pct"])} and {pct(allf["wta"][ELO]["favourite_won_pct"])}. This is descriptive: how often a
        favourite wins says nothing about how well the probabilities were set, which is what log loss scores.</p>
      </div>
      <div class="panel"><div class="table-wrap"><table class="num wide">
        <thead><tr><th>Tour</th><th>Level</th><th class="r">Ranking's favourite won</th><th class="r">Surface Elo's</th>
        <th class="r">Matches</th><th class="r">Market's</th><th class="r">Matches with odds</th></tr></thead>
        <tbody>{"".join(ftr)}</tbody></table></div>
        <p class="note-small">A match whose two players a baseline cannot tell apart (both unranked, say) has no favourite and is left out of that baseline's share.</p>
      </div>
    </div>''')

    # ------------------------------------------------------------------ G. how it was built and checked
    det = {(d["tour"], d["rule"]): d for d in bs["tuning_detail"]}
    ktr = "".join(
        f'<tr><td>{TOUR[t]}</td><td>{esc(bs["rule_names"][rule])}</td><td class="r">{c["k0"]:g}</td><td class="r">{c["offset"]:g}</td>'
        f'<td class="r">{c["shape"]:g}</td><td class="r">{c["w"]:g}</td><td class="r">{det[(t, rule)]["best"]:.4f}</td>'
        f'<td class="r">{det[(t, rule)]["default_538"]:.4f}</td></tr>'
        for (t, rule), c in sorted(tuned.items()))
    ret = {t: head[(t, HEAD)]["noret_minus_ret_milli"] for t in TOUR}
    rets = {t: head[(t, HEAD)]["surf_noret_minus_ret_milli"] for t in TOUR}
    comp = {(c["tour"], c["window"]): c for c in r["completed_only"]}
    pin = {p["tour"]: p for p in r["pinnacle_check"]["by_tour"]}
    probes = bs["probe_by_round"]
    changed = sum(p["protected_matches_changed"] for p in probes.values())
    checked = sum(p["protected_matches_checked"] for p in probes.values())
    cuts = sum(p["cuts"] for p in probes.values())
    sp = od["scan_py_method"]
    cov = od["evaluation_tour_level_with_market_inside_coverage"]
    edge = [d for d in bs["tuning_detail"] if any(d["on_grid_edge"].values())]
    kat = {(d["tour"], d["rule"]): d["k_at_matches"] for d in bs["tuning_detail"]}
    k_range = {nm: (min(v[nm] for v in kat.values()), max(v[nm] for v in kat.values())) for nm in ("0", "10", "100", "500")}
    valley = (f'The best settings lie along a flat valley in which a larger k0 trades against a larger shape: K for a player with no rated '
              f'match ranges from {k_range["0"][0]:g} to {k_range["0"][1]:g} across the four choices, but after 10, 100 and 500 matches only from '
              f'{k_range["10"][0]:g} to {k_range["10"][1]:g}, {k_range["100"][0]:g} to {k_range["100"][1]:g} and {k_range["500"][0]:g} to {k_range["500"][1]:g} '
              f'(FiveThirtyEight\'s: {bs["default_k_at_matches"]["0"]:g}, {bs["default_k_at_matches"]["10"]:g}, {bs["default_k_at_matches"]["100"]:g}, '
              f'{bs["default_k_at_matches"]["500"]:g}).')
    if edge:
        valley += " " + "; ".join(
            f'{TOUR[d["tour"]]} with {bs["rule_names"][d["rule"]]} sits on the grid\'s edge, '
            f'{1000 * (d["best_inside_grid"]["log_loss"] - d["best"]):.2f} milli-log-loss from the best setting inside it'
            for d in edge) + "."
    si = {(s["tour"], s["window"]): s for s in r["split_identity_sensitivity"]}
    sw = r["split_identities"]["wta"]
    sa = r["split_identities"]["atp"]
    parts.append(f'''    <div class="sub">
      <h3>How the baselines were built and checked</h3>
      <ul class="plain">
        <li><b>Odds.</b> {n(od["td_rows_linked"])} of tennis-data.co.uk's {n(od["td_rows_2010_on"])} rows since 2010 ({pct(od["td_rows_linked_pct"], 2)}) were
        linked to a Stage 0 match: by the two names as merge-feasibility's <code>scan.py</code> reads them, then by one identical player
        with identical set scores, then with winner and loser exchanged. <code>scan.py</code>'s own method links {pct(sp["linked_pct_of_all_rows"], 2)} of the
        same rows and gives {n(sp["matches_taken_by_two_rows"])} matches two rows each. Inside the weeks tennis-data.co.uk covers, {pct(cov["atp"]["pct"])} of men's and
        {pct(cov["wta"]["pct"])} of women's tour-level evaluation matches have odds; the Next Gen ATP Finals never do. Pinnacle's odds stop in January 2026.</li>
        <li><b>Market average against Pinnacle.</b> Where both exist, the average is {better(pin["atp"]["milli"])} than Pinnacle for the men and
        {better(pin["wta"]["milli"])} for the women (milli-log-loss), so the average is a fair stand-in for the sharpest single bookmaker.</li>
        <li><b>Elo's constants</b>, chosen on 2013–2018 on a grid of {bs["tuning_detail"][0]["grid_points"]} settings per tour and frozen
        (K = k0 / (matches + offset)<sup>shape</sup>):
        <div class="table-wrap"><table class="num"><thead><tr><th>Tour</th><th>Retirements</th><th class="r">k0</th><th class="r">offset</th><th class="r">shape</th>
        <th class="r">surface weight</th><th class="r">log loss 2013–18</th><th class="r">FiveThirtyEight's K</th></tr></thead><tbody>{ktr}</tbody></table></div>
        {esc(valley)}</li>
        <li><b>Retirements</b> (a player who stops mid-match; the opponent advances). Skipping them rather than counting them makes surface Elo
        {better(rets["atp"]["milli"])} for the men and {better(rets["wta"]["milli"])} for the women in 2022–2026 (overall Elo:
        {better(ret["atp"]["milli"])} and {better(ret["wta"]["milli"])}), and overall Elo is {better(comp[("atp", HEAD)]["noret_minus_ret_milli"]["milli"])} and
        {better(comp[("wta", HEAD)]["noret_minus_ret_milli"]["milli"])} on completed matches alone. The charts count them, the default kept by the
        owner on 30 Sep 2026: Elo is an exploratory baseline, and its details are not to be worked further.</li>
        <li><b>No look-ahead.</b> The Elo pass equals the inherited <code>src/ratings/elo.py</code> wherever no two matches are simultaneous,
        and follows the Brief's time rule where they are (a round robin's matches never see each other, nor do two events of one week).
        A probe that scrambles every later result, cut by date, event and round ({cuts} cuts), changed {n(changed)} of {n(checked)} protected pre-match ratings.</li>
        <li><span class="flag">A Stage 0 problem.</span> In Tennis My Life's rows, which alone cover the weeks from 25 May 2026, {sw["player_ids"]}
        established women ({esc(", ".join(sw["examples"][:3]))} among them) carry a WTA id that Sackmann's rows never use, although
        the same name has one there; Elo meets each as a newcomer. They play in {sw["matches"]} matches, {si[("wta", HEAD)]["odds_matches_left_out"]} of them
        with odds. Without those, the women's room is {mm(si[("wta", "2026")]["gap_without"]["milli"])} rather than {mm(si[("wta", "2026")]["gap_all"]["milli"])} milli-log-loss
        in 2026 and {mm(si[("wta", HEAD)]["gap_without"]["milli"])} rather than {mm(si[("wta", HEAD)]["gap_all"]["milli"])} in 2022–2026. The men's equivalent (the audit's C2,
        {sa["player_ids"]} players in {sa["matches"]} matches) touches no match with odds. Reported, not fixed: see <code>stage1.md</code>.</li>
      </ul>
    </div>''')

    data = {"bars": bars, "bars_n": bars_n, "coin": coin,
            "years": {"odds": years_odds, "all": years_all}, "tuning": [2013, 2018],
            "cal": cal, "tours": [[t, TOUR_LONG[t]] for t in TOUR]}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["how-predictable"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const fmtN = v => Math.round(v).toLocaleString("en-US");
  const COLOR = { rank: "var(--series-3)", elo: "var(--series-1)", market: "var(--series-2)" };
  const LABEL = { rank: "Ranking", elo: "Surface Elo", market: "Market" };

  // ---------------------------------------------------------------- A. better than a coin
  (function bars() {
    const host = document.getElementById("s1-bars");
    const max = Math.max(...D.tours.map(([t]) => Math.max(...D.bars[t].map(b => b.milli))));
    const top = Math.ceil(max / 25) * 25;
    D.tours.forEach(([t, name]) => {
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, L = 130, R = 52, rowH = 34, barH = 18, T = 6, B = 26;
      const H = T + D.bars[t].length * rowH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": milli-log-loss better than a coin for each baseline; the table below holds the numbers" });
      const x = v => L + (W - L - R) * v / top;
      for (let v = 0; v <= top; v += 25) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
        S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v;
      }
      D.bars[t].forEach((b, i) => {
        const y = T + i * rowH + (rowH - barH) / 2, x0 = x(0), x1 = Math.max(x(b.milli), x0 + 1), r = Math.min(4, (x1 - x0) / 2);
        S("text", { x: L - 8, y: y + barH / 2 + 4, "text-anchor": "end", class: "lab" }, svg).textContent = b.label;
        const p = S("path", { d: `M${x0},${y} H${x1 - r} Q${x1},${y} ${x1},${y + r} V${y + barH - r} Q${x1},${y + barH} ${x1 - r},${y + barH} H${x0} Z`,
          fill: COLOR[b.family], class: "mark", tabindex: "0" }, svg);
        S("text", { x: x1 + 6, y: y + barH / 2 + 4, class: "val" }, svg).textContent = b.milli.toFixed(1);
        const hit = S("rect", { x: 0, y: T + i * rowH, width: W, height: rowH, class: "hit" }, svg);
        const rows = () => [b.milli.toFixed(1) + " milli-log-loss better than a coin", b.label + " · " + name,
          "log loss " + b.ll.toFixed(3) + " on " + fmtN(D.bars_n[t]) + " matches"];
        window.reportTip.bind(hit, rows); window.reportTip.bind(p, rows);
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();

  // ---------------------------------------------------------------- B. log loss by season
  (function years() {
    const host = document.getElementById("s1-years");
    const legend = document.getElementById("s1-years-legend");
    let mode = "odds";
    function draw() {
      host.replaceChildren(); legend.replaceChildren();
      const series = mode === "odds" ? ["rank", "elo", "market"] : ["rank", "elo"];
      series.forEach(k => { const s = el("span", "key"); const sw = el("span", "sw-line"); sw.style.background = COLOR[k]; s.append(sw, LABEL[k]); legend.appendChild(s); });
      const band = el("span", "key"); band.append(el("span", "sw-band"), "Tuning years (2013–2018)"); legend.appendChild(band);
      let lo = Infinity, hi = -Infinity;
      D.tours.forEach(([t]) => series.forEach(k => D.years[mode][t][k].forEach(([, v]) => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } })));
      lo = Math.floor(lo * 100) / 100; hi = Math.ceil(hi * 100) / 100;
      const years = D.years[mode][D.tours[0][0]].rank.map(d => d[0]);
      D.tours.forEach(([t, name]) => {
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        const W = 460, H = 250, L = 42, R = 74, T = 12, B = 26;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": log loss by season for " + series.map(k => LABEL[k]).join(", ") + "; the table below holds the numbers" });
        const x = yr => L + (W - L - R) * (yr - years[0]) / (years[years.length - 1] - years[0]);
        const y = v => T + (H - T - B) * (hi - v) / (hi - lo);
        S("rect", { x: x(D.tuning[0]) - 8, y: T, width: x(D.tuning[1]) - x(D.tuning[0]) + 16, height: H - T - B, class: "band" }, svg);
        for (let v = lo; v <= hi + 1e-9; v += 0.01) {
          S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }, svg);
          S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = v.toFixed(2);
        }
        years.forEach((yr, i) => { if (i % 2 === 0) S("text", { x: x(yr), y: H - 8, "text-anchor": "middle" }, svg).textContent = "'" + String(yr).slice(2); });
        const ends = [];
        series.forEach(k => {
          const pts = D.years[mode][t][k];
          let d = "", pen = false;
          pts.forEach(([yr, v]) => { if (v == null) { pen = false; return; } d += (pen ? " L" : " M") + x(yr).toFixed(1) + "," + y(v).toFixed(1); pen = true; });
          S("path", { d: d.trim(), fill: "none", stroke: COLOR[k], "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
          const last = [...pts].reverse().find(p => p[1] != null);
          if (last) {
            S("circle", { cx: x(last[0]), cy: y(last[1]), r: 4, fill: COLOR[k], stroke: "var(--surface)", "stroke-width": 2 }, svg);
            ends.push({ k, y: y(last[1]), x: x(last[0]) });
          }
        });
        ends.sort((a, b) => a.y - b.y);
        const clash = ends.some((e, i) => i > 0 && e.y - ends[i - 1].y < 13);
        if (!clash) ends.forEach(e => S("text", { x: e.x + 8, y: e.y + 4, class: "lab" }, svg).textContent = LABEL[e.k]);
        const cross = S("line", { x1: 0, x2: 0, y1: T, y2: H - B, class: "cross", visibility: "hidden" }, svg);
        const step = (W - L - R) / (years.length - 1);
        years.forEach((yr, i) => {
          const hit = S("rect", { x: x(yr) - step / 2, y: T, width: step, height: H - T - B, class: "hit", tabindex: "0" }, svg);
          const rows = () => {
            cross.setAttribute("x1", x(yr)); cross.setAttribute("x2", x(yr)); cross.setAttribute("visibility", "visible");
            const out = [String(yr) + (yr <= D.tuning[1] ? " (tuning years)" : "")];
            series.forEach(k => { const p = D.years[mode][t][k][i]; out.push((p && p[1] != null ? p[1].toFixed(3) : "no odds") + "  " + LABEL[k]); });
            const p = D.years[mode][t].rank[i]; if (p && p[2]) out.push(fmtN(p[2]) + " matches");
            return out;
          };
          window.reportTip.bind(hit, rows);
          hit.addEventListener("pointerleave", () => cross.setAttribute("visibility", "hidden"));
          hit.addEventListener("blur", () => cross.setAttribute("visibility", "hidden"));
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    document.querySelectorAll('#how-predictable .seg button').forEach(b => b.addEventListener("click", () => {
      mode = b.dataset.mode;
      document.querySelectorAll('#how-predictable .seg button').forEach(o => o.setAttribute("aria-pressed", String(o === b)));
      draw();
    }));
    draw();
  })();

  // ---------------------------------------------------------------- C. heat-table tooltips
  document.querySelectorAll("#s1-heat td[data-tip]").forEach(td => window.reportTip.bind(td, () => td.dataset.tip.split("|")));

  // ---------------------------------------------------------------- D. calibration
  (function cal() {
    const host = document.getElementById("s1-cal");
    D.tours.forEach(([t, name]) => {
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 400, H = 330, L = 44, R = 14, T = 10, B = 34;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": share of matches the favourite won against the probability it was given, surface Elo and market; the table below holds the numbers" });
      const x0 = 0.5, x1 = 1.0, y0 = 0.4, y1 = 1.0;
      const x = v => L + (W - L - R) * (v - x0) / (x1 - x0);
      const y = v => T + (H - T - B) * (y1 - v) / (y1 - y0);
      for (let v = 0.5; v <= 1.0001; v += 0.1) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: "grid" }, svg);
        S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = Math.round(v * 100) + "%";
      }
      for (let v = 0.4; v <= 1.0001; v += 0.1) {
        S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }, svg);
        S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = Math.round(v * 100) + "%";
      }
      S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "probability given to the favourite";
      S("line", { x1: x(0.5), y1: y(0.5), x2: x(1.0), y2: y(1.0), class: "ref" }, svg);
      ["elo", "market"].forEach(k => {
        const pts = (D.cal[t] || {})[k] || [];
        const d = pts.map((p, i) => (i ? "L" : "M") + x(p.mean_p).toFixed(1) + "," + y(p.won).toFixed(1)).join(" ");
        S("path", { d, fill: "none", stroke: COLOR[k], "stroke-width": 2, "stroke-linejoin": "round" }, svg);
        pts.forEach(p => {
          S("line", { x1: x(p.mean_p), x2: x(p.mean_p), y1: y(p.won_lo), y2: y(p.won_hi), stroke: COLOR[k], "stroke-width": 1.5, opacity: 0.6 }, svg);
          const dot = S("circle", { cx: x(p.mean_p), cy: y(p.won), r: 4, fill: COLOR[k], stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          const hit = S("circle", { cx: x(p.mean_p), cy: y(p.won), r: 12, class: "hit" }, svg);
          const rows = () => ["won " + (100 * p.won).toFixed(1) + "% (" + (100 * p.won_lo).toFixed(1) + "–" + (100 * p.won_hi).toFixed(1) + "%)",
            (k === "elo" ? "Surface Elo" : "Market") + " · " + name + " · band " + p.bin,
            "given " + (100 * p.mean_p).toFixed(1) + "% on average · " + fmtN(p.n) + " matches"];
          window.reportTip.bind(hit, rows); window.reportTip.bind(dot, rows);
        });
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();
})();
"""
