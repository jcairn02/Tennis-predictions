"""Report section for Stage 3, "Which statistics repeat": how much of each per-match statistic is the player and
how much is chance.

Reliability against sample size (split-half, Spearman-Brown), the reliability of a regular's season (the summary's
chart), the shrinkage constants, carry-over from season to season and across surfaces, the next-match forecasts, and
the serve and return ratings that adjust for the opponent. Whether a repeating statistic decides matches is Stage 2's
question; the summary combines the two.

Every number comes from stage3_results.json (render_report.py assembles the page).
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": 3, "id": "traits", "title": "Which statistics repeat"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "ATP (men)", "wta": "WTA (women)"}
SURF = [("all", "All surfaces"), ("Hard", "Hard"), ("Clay", "Clay"), ("Grass", "Grass")]
LABEL = {"spw": "Serve points won", "spw_adj": "Serve points won, opponent-adjusted", "rpw": "Return points won",
         "rpw_adj": "Return points won, opponent-adjusted", "tpw": "Total points won", "hold": "Service games held",
         "brk": "Return games won (breaks)", "ace": "Aces per serve point", "df": "Double faults per serve point",
         "first_in": "First serves in", "first_won": "First-serve points won", "second_won": "Second-serve points won",
         "bp_saved": "Break points saved", "bp_conv": "Break points converted",
         "bp_faced_pg": "Break points faced per service game", "tb_won": "Tiebreaks won", "sets_won": "Sets won",
         "games_won": "Games won"}
ADJ = ("spw_adj", "rpw_adj")
PER = {"serve points": "serve point", "return points": "return point", "points": "point", "service games": "service game",
       "return games": "return game", "first serves in": "first serve in", "second-serve points": "second-serve point",
       "break points faced": "break point faced", "break-point chances": "break-point chance", "tiebreaks": "tiebreak",
       "sets": "set", "games": "game"}
SELECT_STYLE = ("font:inherit;font-size:.88rem;padding:3px 6px;border:1px solid var(--rule);border-radius:6px;"
                "background:var(--surface);color:var(--ink)")
FORMS = [("career to date", "Career to date", "var(--series-1)"), ("last 52 weeks", "Last 52 weeks", "var(--series-2)"),
         ("decayed", "Decayed", "var(--series-3)"), ("serve and return ratings", "Serve and return ratings", "var(--ink)")]
WINDOW = "2019-2026"


def esc(x) -> str:
    return html.escape(str(x))


def n0(x) -> str:
    return f"{int(round(x)):,}"


def f2(x) -> str:
    return "–" if x is None or not math.isfinite(x) else f"{x:.2f}".replace("-0.00", "0.00").replace("-", "−")


def f1(x) -> str:
    return "–" if x is None or not math.isfinite(x) else f"{x:.1f}".replace("-", "−")


def pct(x, d=0) -> str:
    return "–" if x is None or not math.isfinite(x) else f"{100 * x:.{d}f}%"


def num(x) -> float | None:
    """A JSON number as a float, or None (the page draws nothing for it)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def kfmt(x) -> str:
    """A sample size: whole numbers from 10 on, one decimal below."""
    if x is None or not math.isfinite(x):
        return "no signal"
    return n0(x) if x >= 10 else f"{x:.1f}"


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div>'
            f'<div class="note">{note}</div></div>')


def render(study_dir: Path) -> dict:
    r = load(study_dir, "stage3_results.json")
    rt = r["ratings"]
    st = r["settings"]
    per = {(x["tour"], x["surface"], x["stat"]): x for x in r["persistence"]}
    shr = {(x["stat"], x["tour"], x["surface"], x["years"]): x for x in r["shrinkage"]["rows"]}
    change = {(x["stat"], x["tour"], x["surface"]): x for x in r["shrinkage"]["change"]}
    year = {(x["stat"], x["tour"], x["surface"]): x for x in r["carryover"]["year"]}
    cross = {(x["stat"], x["tour"], x["surfaces"]): x for x in r["carryover"]["surface"]}
    fc = {(x["stat"], x["tour"], x["window"], x["surface"], x["form"]): x for x in r["forecast"]["rows"]}
    fits = {(x["tour"], x["surface"], x["stat"], x["population"]): x for x in r["reliability"]["fits"]}
    half = r["forecast"]["half_life_weeks"]
    stats = [s["key"] for s in r["stats"]]
    raw_stats = [s for s in stats if s not in ADJ]
    main_pop = "at least 2n matches"
    fixed_pop = next(p for (_, _, _, p) in fits if p != main_pop)

    blank = {"reliability_typical": None, "reliability_typical_lo": None, "reliability_typical_hi": None, "verdict": None,
             "verdict_firm": True, "typical_matches": None, "typical_units": None, "unit": "", "k_matches": None,
             "k_units": None, "year_to_year_r": None}

    def P(t, s, surf="all"):
        return per.get((t, surf, s), blank)

    def F(s, t, form, surf="all", w=WINDOW):
        return fc.get((s, t, w, surf, form))

    def K(s, t, surf="all"):
        return shr[(s, t, surf, "2013-2018" if s in ADJ else "2010-2018")]

    # rows of the charts in one order: by the men's reliability over all surfaces, each adjusted rate under its raw one
    order = sorted(raw_stats, key=lambda s: -(num(P("atp", s)["reliability_typical"]) or 0))
    for a in ADJ:
        order.insert(order.index(a.replace("_adj", "")) + 1, a)
    parts = []

    # ------------------------------------------------------------------ intro and tiles
    typ = {t: P(t, "spw")["typical_matches"] for t in TOUR}
    parts.append(f'''    <div class="prose">
      <p>Stage 3 asks which of a player's per-match statistics are a property of the player, a <b>trait</b> (a skill) or a
      <b>style</b> (a way of playing), and which are mostly the luck of the matches they were measured on. It measures every
      rate in the Stage 0 table, for both tours and on every surface. It also builds <b>serve and return ratings</b> that
      adjust a match's serve rate for the opponent, and keeps their pre-match values for Stage 4. Whether a statistic
      that repeats also decides matches was Stage 2's question; the summary puts the two together.</p>
      <p>The measurements use completed matches at the evaluation levels (Grand Slams, Finals, 1000s, 500s, 250s,
      Challenger / WTA 125 and their qualifying), {n0(r["population"]["analysis_matches_2013_2026"]["atp"])} men's and
      {n0(r["population"]["analysis_matches_2013_2026"]["wta"])} women's from 2013 to 2026. Retirements are left out: their
      statistics cover part of a match.</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("Serve points won: reliability of a regular's season", f2(P("atp", "spw")["reliability_typical"]),
                 f2(P("wta", "spw")["reliability_typical"]),
                 f"share of the spread between players' season rates that is the player, not chance ({n0(typ['atp'])} and "
                 f"{n0(typ['wta'])} matches); adjusted for the opponent {f2(P('atp', 'spw_adj')['reliability_typical'])} and "
                 f"{f2(P('wta', 'spw_adj')['reliability_typical'])}")}
      {pair_tile("Tiebreaks won: the same measure", f2(P("atp", "tb_won")["reliability_typical"]),
                 f2(P("wta", "tb_won")["reliability_typical"]),
                 f"a season's tiebreak record is almost all chance; break points saved {f2(P('atp', 'bp_saved')['reliability_typical'])} "
                 f"and {f2(P('wta', 'bp_saved')['reliability_typical'])}")}
      {pair_tile("Matches before break points saved are half signal", kfmt(P("atp", "bp_saved")["k_matches"]),
                 kfmt(P("wta", "bp_saved")["k_matches"]),
                 f"aces {kfmt(P('atp', 'ace')['k_matches'])} and {kfmt(P('wta', 'ace')['k_matches'])}; serve points won "
                 f"{kfmt(P('atp', 'spw')['k_matches'])} and {kfmt(P('wta', 'spw')['k_matches'])}")}
      {pair_tile("Next match's serve points: share of what is not chance that a forecast gets",
                 pct(F("spw", "atp", "serve and return ratings")["share_of_non_chance"]),
                 pct(F("spw", "wta", "serve and return ratings")["share_of_non_chance"]),
                 f"from the serve and return ratings, which know the opponent; the player's own history alone "
                 f"{pct(F('spw', 'atp', 'career to date')['share_of_non_chance'])} and {pct(F('spw', 'wta', 'career to date')['share_of_non_chance'])} "
                 f"({WINDOW.replace('-', '–')})")}
    </div>''')

    # ------------------------------------------------------------------ terms
    parts.append(f'''    <div class="sub">
      <h3>Terms used in this section</h3>
      <dl class="terms">
        <dt>Rate</dt><dd>A per-match statistic as a share: serve points won of serve points played, aces per serve point,
        break points saved of break points faced, and so on. Its <i>units</i> are what it is counted in (serve points, break
        points faced, tiebreaks, sets, games).</dd>
        <dt>Reliability</dt><dd>Of a rate measured on a sample of matches: the share of its spread across players that
        is real difference between players, not chance. 1 is all player, 0 all chance.</dd>
        <dt>Split-half correlation</dt><dd>Two separate random sets of n matches from each player's season; the rate on
        each, correlated across players. It equals the reliability of a sample of n matches.</dd>
        <dt>Spearman–Brown curve</dt><dd>How reliability grows with the sample: r = n / (n + k). k is the sample at which
        reliability reaches 0.5, half signal and half noise. Twice the sample, two-thirds signal; four times, four-fifths.</dd>
        <dt>Regular, typical season</dt><dd>A regular plays at least {st["regular"]} evaluation-level matches in a season.
        A typical season is the median regular's: {n0(typ["atp"])} matches for the men and {n0(typ["wta"])} for the women
        over all surfaces (on one surface, the median of regulars who played on it).</dd>
        <dt>Shrinkage</dt><dd>Mixing the tour's average into a player's rate in proportion to how little the player's own
        sample says: (x + K × average) / (d + K), with x the player's count and d their units. K, the <i>shrinkage
        constant</i>, is chance variation per unit over the true spread between players; a player with d = K units gets half
        their own rate and half the average.</dd>
        <dt>Carry-over</dt><dd>The correlation of a player's shrunk rate in one season with the next, or on one surface with
        another in the same season. The <i>ceiling</i> is what it would be if the true rate never changed, given the
        samples' noise.</dd>
        <dt>Serve and return ratings</dt><dd>Each player's serve and return strength on the log-odds scale. The chance that
        a server wins a serve point is 1 / (1 + e<sup>−(μ + serve − return)</sup>), with μ the tour's average on the
        surface. They are updated match by match on the serve points each player won.</dd>
        <dt>Opponent-adjusted rate</dt><dd>A match's serve (or return) points won restated as against a typical returner
        (server), using the opponent's rating before the match.</dd>
        <dt>Log loss per point</dt><dd>As Stage 1's log loss, but scored on every point (or game, tiebreak...) of the next
        match with the forecast rate; milli-log-loss per point better than the tour's average for the surface.</dd>
      </dl>
    </div>''')

    # ------------------------------------------------------------------ 1. signal or noise in a season
    persist = {t: {s: [{"key": k, "label": LABEL[k], "adj": k in ADJ,
                        "rel": num(P(t, k, s)["reliability_typical"]), "lo": num(P(t, k, s)["reliability_typical_lo"]),
                        "hi": num(P(t, k, s)["reliability_typical_hi"]), "verdict": P(t, k, s)["verdict"] or "–",
                        "firm": P(t, k, s)["verdict_firm"], "m": num(P(t, k, s)["typical_matches"]),
                        "u": num(P(t, k, s)["typical_units"]), "unit": P(t, k, s)["unit"]}
                       for k in order] for s, _ in SURF} for t in TOUR}
    ptab = []
    for t in TOUR:
        for s, sname in SURF:
            for k in order:
                x = P(t, k, s)
                if x is blank:
                    continue
                ptab.append(f'<tr><td>{TOUR[t]}</td><td>{esc(sname)}</td><td>{esc(LABEL[k])}</td><td class="r">{n0(x["typical_matches"])}</td>'
                            f'<td class="r">{n0(x["typical_units"])} {esc(x["unit"])}</td><td class="r">{f2(num(x["reliability_typical"]))}</td>'
                            f'<td class="r">{f2(num(x["reliability_typical_lo"]))} to {f2(num(x["reliability_typical_hi"]))}</td>'
                            f'<td>{esc(x["verdict"] or "–")}{"" if x["verdict_firm"] else " (borderline)"}</td></tr>')
    rep = [k for k in raw_stats if P("atp", k)["verdict"] == "repeats" and P("wta", k)["verdict"] == "repeats"]
    weak = [k for k in raw_stats if {P("atp", k)["verdict"], P("wta", k)["verdict"]} == {"repeats weakly"}]
    noise = [k for k in raw_stats if P("atp", k)["verdict"] == "mostly noise" and P("wta", k)["verdict"] == "mostly noise"]
    border = [(t, k) for t in TOUR for k in raw_stats if not P(t, k)["verdict_firm"]]
    parts.append(f'''    <div class="sub">
      <h3>1. Signal or noise in a season</h3>
      <div class="prose">
        <p>For each rate, the reliability of a typical season's sample: the split-half correlation measured at half a
        season among the players who play one, stepped up to the whole season by the Spearman–Brown formula. The reading
        used for the verdict is fixed in advance: <b>repeats</b> when a season is at least half signal (0.5 or more),
        <b>repeats weakly</b> from 0.2, <b>mostly noise</b> below 0.2. It is <i>borderline</i> when the 95% range crosses a line.</p>
        <p><span class="kind">Observed</span>Over all surfaces, a season of matches is mostly signal for serve style (aces
        {f2(P("atp", "ace")["reliability_typical"])} and {f2(P("wta", "ace")["reliability_typical"])}, first serves in
        {f2(P("atp", "first_in")["reliability_typical"])} and {f2(P("wta", "first_in")["reliability_typical"])}, double faults
        {f2(P("atp", "df")["reliability_typical"])} and {f2(P("wta", "df")["reliability_typical"])}) and for serve and return
        skill (serve points won {f2(P("atp", "spw")["reliability_typical"])} and {f2(P("wta", "spw")["reliability_typical"])},
        return points won {f2(P("atp", "rpw")["reliability_typical"])} and {f2(P("wta", "rpw")["reliability_typical"])}, men
        first). Results are about half signal (games won {f2(P("atp", "games_won")["reliability_typical"])} and
        {f2(P("wta", "games_won")["reliability_typical"])}, sets won {f2(P("atp", "sets_won")["reliability_typical"])} and
        {f2(P("wta", "sets_won")["reliability_typical"])}). Break points are mostly chance (saved {f2(P("atp", "bp_saved")["reliability_typical"])}
        and {f2(P("wta", "bp_saved")["reliability_typical"])}, converted {f2(P("atp", "bp_conv")["reliability_typical"])} and
        {f2(P("wta", "bp_conv")["reliability_typical"])}), and tiebreaks are chance ({f2(P("atp", "tb_won")["reliability_typical"])}
        and {f2(P("wta", "tb_won")["reliability_typical"])}).</p>
        <p><span class="kind">Inferred</span>Repeats on both tours: {esc(", ".join(LABEL[k].lower() for k in rep))}. Repeats
        weakly: {esc(", ".join(LABEL[k].lower() for k in weak))}. Mostly noise: {esc(", ".join(LABEL[k].lower() for k in noise))}.
        Borderline: {esc("; ".join(f"{LABEL[k].lower()} ({TOUR[t]}, {f2(P(t, k)['reliability_typical'])})" for t, k in border))}.
        On one surface a season is a smaller sample, so every rate is less reliable there, grass most of all (a regular's
        grass season is {n0(P("atp", "spw", "Grass")["typical_matches"])} matches).</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Reliability of a regular's season, by statistic</h3><p>Share of the spread between
        players that is the player; bars to 0.5 and beyond repeat, below 0.2 mostly noise; whiskers are 95% ranges</p></div>
        <div class="controls"><span>Surface:</span><div class="seg" role="group" aria-label="Surface">
          {"".join(f'<button type="button" data-s3persist="{s}" aria-pressed="{str(s == "all").lower()}">{esc(n)}</button>' for s, n in SURF)}</div></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-1)"></span>Rate as measured</span>
          <span class="key"><span class="sw-rect" style="background:var(--series-2)"></span>Adjusted for the opponent</span>
        </div>
        <div class="chart-pair" id="s3-persist"></div>
        <p class="note-small">The typical season's sample is in the table (matches and the rate's own units). The summary's
        chart is to use this table: <code>stage3_persistence.csv</code>.</p>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Surface</th><th>Statistic</th><th class="r">Typical season</th><th class="r">In units</th>
          <th class="r">Reliability</th><th class="r">95% range</th><th>Verdict</th></tr></thead>
          <tbody>{"".join(ptab)}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 2. reliability against sample size
    rows = [x for x in r["reliability"]["rows"] if x["population"] == main_pop]
    curves = {t: {s: {} for s, _ in SURF} for t in TOUR}
    for x in rows:
        curves[x["tour"]][x["surface"]].setdefault(x["stat"], {"pts": []})["pts"].append(
            [x["n"], num(x["r"]), num(x["r_lo"]), num(x["r_hi"]), num(x["units_per_set"]), x["player_windows"], x["directional_only"]])
    for (t, s, k, pop), f in fits.items():
        if pop == main_pop and k in curves[t][s]:
            curves[t][s][k].update({"k": num(f["k_matches"]), "ku": num(f["k_units"])})
    ftab = []
    for t in TOUR:
        for s, sname in SURF:
            for k in order:
                f = fits.get((t, s, k, main_pop))
                if not f:
                    continue
                fx = fits.get((t, s, k, fixed_pop))
                ftab.append(f'<tr><td>{TOUR[t]}</td><td>{esc(sname)}</td><td>{esc(LABEL[k])}</td><td class="r">{kfmt(num(f["k_matches"]))}</td>'
                            f'<td class="r">{kfmt(num(f["k_units"]))} {esc(r["stats"][stats.index(k)]["unit"])}</td>'
                            f'<td class="r">{kfmt(num(fx["k_matches"])) if fx else "–"}</td><td class="r">{f2(num(f["fit_max_abs_resid"]))}</td>'
                            f'<td>{esc(f["fit_on"])}</td></tr>')
    sw = {t: P(t, "spw") for t in TOUR}
    max_miss = max(num(f["fit_max_abs_resid"]) or 0.0 for (t, s, k, pop), f in fits.items() if s == "all" and pop == main_pop)
    parts.append(f'''    <div class="sub">
      <h3>2. Reliability against sample size</h3>
      <div class="prose">
        <p>For each n, players with at least 2n matches in a window (a season; three seasons on grass, where a season is
        thin) give two separate random sets of n matches; the rate on each is correlated across players, averaged over
        {st["draws"]} random draws. The Spearman–Brown curve is fitted to the n's with at least {st["fit_units"]} player-windows,
        in matches and in the rate's units. <span class="kind">Observed</span>Serve points won reach half signal after
        {kfmt(sw["atp"]["k_matches"])} matches for the men ({kfmt(sw["atp"]["k_units"])} serve points) and
        {kfmt(sw["wta"]["k_matches"])} for the women; aces after {kfmt(P("atp", "ace")["k_matches"])} and {kfmt(P("wta", "ace")["k_matches"])};
        break points saved after {kfmt(P("atp", "bp_saved")["k_matches"])} and {kfmt(P("wta", "bp_saved")["k_matches"])}
        ({kfmt(P("atp", "bp_saved")["k_units"])} and {kfmt(P("wta", "bp_saved")["k_units"])} break points faced); tiebreaks won
        after about {kfmt(P("atp", "tb_won")["k_matches"])} and {kfmt(P("wta", "tb_won")["k_matches"])} matches, which no career reaches.</p>
        <p><span class="kind">Observed</span>Over all surfaces the curve misses the measured points by at most
        {f2(max_miss)}, the most for games and sets won, whose k creeps up with n: the players who play many matches are the
        ones who win, so they are more alike. On a fixed population
        (players with at least {2 * st["fixed_half"]} matches in the season, for every n) k is
        {kfmt(fits[("atp", "all", "games_won", fixed_pop)]["k_matches"])} matches for the men's games won against
        {kfmt(P("atp", "games_won")["k_matches"])}, and {kfmt(fits[("atp", "all", "spw", fixed_pop)]["k_matches"])} against
        {kfmt(sw["atp"]["k_matches"])} for serve points won. That is why the section's verdict reads the curve at a typical
        season among the players who play one.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Split-half correlation against the sample</h3><p>Dots: measured, with a 95% range (open:
        under 300 player-windows, directional only); line: the fitted Spearman–Brown curve; the marker is k, where reliability
        reaches 0.5</p></div>
        <div class="controls">
          <label for="s3-stat">Statistic:</label>
          <select id="s3-stat" style="{SELECT_STYLE}">{"".join(f'<option value="{k}"{" selected" if k == "spw" else ""}>{esc(LABEL[k])}</option>' for k in order)}</select>
          <div class="seg" role="group" aria-label="Surface">
            {"".join(f'<button type="button" data-s3curve="{s}" aria-pressed="{str(s == "all").lower()}">{esc(n)}</button>' for s, n in SURF)}</div>
          <div class="seg" role="group" aria-label="Sample counted in">
            <button type="button" data-s3unit="m" aria-pressed="true">Matches</button>
            <button type="button" data-s3unit="u" aria-pressed="false">Units</button></div>
        </div>
        <div class="chart-pair" id="s3-curve"></div>
        <details class="twin"><summary>Show the fitted samples as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Surface</th><th>Statistic</th><th class="r">k, matches</th><th class="r">k, units</th>
          <th class="r">k, fixed population</th><th class="r">Largest miss</th><th>Fitted on</th></tr></thead>
          <tbody>{"".join(ftab)}</tbody></table></div>
          <p class="note-small">Every split-half correlation, with its players and units, is in <code>stage3_reliability.csv</code>.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 3. shrinkage
    stab = []
    for k in order:
        cells = []
        for t in TOUR:
            x, c = K(k, t), change[(k, t, "all")]
            cells.append(f'<td class="r">{100 * x["mean"]:.1f}%</td><td class="r">{kfmt(num(x["K_units"]))}</td>'
                         f'<td class="r">{kfmt(num(x["K_matches"]))}</td><td class="r">{kfmt(num(x["K_binomial_units"]))}</td>'
                         f'<td class="r">{f2(num(c["K_ratio"]))}</td>')
        stab.append(f'<tr><td>{esc(LABEL[k])}</td><td>{esc(r["stats"][stats.index(k)]["unit"])}</td>{"".join(cells)}</tr>')
    sstab = []
    for t in TOUR:
        for s, sname in SURF[1:]:
            for k in order:
                x = K(k, t, s)
                sstab.append(f'<tr><td>{TOUR[t]}</td><td>{esc(sname)}</td><td>{esc(LABEL[k])}</td><td class="r">{100 * x["mean"]:.1f}%</td>'
                             f'<td class="r">{kfmt(num(x["K_units"]))}</td><td class="r">{kfmt(num(x["K_matches"]))}</td>'
                             f'<td class="r">{kfmt(num(x["K_units_lo"]))} to {kfmt(num(x["K_units_hi"]))}</td></tr>')
    ratios = sorted(v for v in (num(c["K_ratio"]) for c in r["shrinkage"]["change"] if c["surface"] == "all" and c["stat"] != "tb_won")
                    if v is not None)
    inside = sum(1 for c in r["shrinkage"]["change"] if c["inside_bootstrap_range"])
    parts.append(f'''    <div class="sub">
      <h3>3. How much of the tour average to mix in</h3>
      <div class="prose">
        <p>The shrinkage constant K is the chance variation of one unit over the true spread between players. Both are
        measured on player-seasons (three seasons on grass): the true spread is the spread of season rates less their
        chance part, and the chance part is measured from how much a player's matches vary within the season. That
        includes the points' own luck and the changing opponents, conditions and form. A binomial model (a beta-binomial's
        constant) counts the points' luck alone. The constants for Stage 4 are estimated on 2010–2018 only (the adjusted
        rates on 2013–2018, after the ratings' warm-up), so Stage 4 can use them without look-ahead.</p>
        <p><span class="kind">Observed</span>For serve points won K is {kfmt(K("spw", "atp")["K_units"])} serve points for the
        men ({kfmt(K("spw", "atp")["K_matches"])} matches) and {kfmt(K("spw", "wta")["K_units"])} for the women; binomial
        chance alone would give {kfmt(K("spw", "atp")["K_binomial_units"])} and {kfmt(K("spw", "wta")["K_binomial_units"])}: a
        match's serve rate varies {f1(K("spw", "atp")["overdispersion"])} and {f1(K("spw", "wta")["overdispersion"])} times
        as much as point luck explains. Break points behave almost like pure chance within a player (variation
        {f1(K("bp_saved", "atp")["overdispersion"])} and {f1(K("bp_saved", "wta")["overdispersion"])} times binomial).
        <span class="kind">Observed</span>With every year (2010–2026) the constants move little: the ratio to the
        2010–2018 constant has a median of {f2(ratios[len(ratios) // 2])} over all surfaces, from {f2(min(ratios))}
        to {f2(max(ratios))} (tiebreaks aside), and {inside} of {len(r["shrinkage"]["change"])} constants fall inside the
        2010–2018 bootstrap range.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Shrinkage constants, all surfaces, 2010–2018</h3><p>K in the rate's units and in matches;
        the ratio is the constant with every year over the one from 2010–2018</p></div>
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th rowspan="2">Statistic</th><th rowspan="2">Units</th><th class="r" colspan="5">ATP</th><th class="r" colspan="5">WTA</th></tr>
          <tr><th class="r">Average</th><th class="r">K</th><th class="r">K, matches</th><th class="r">Binomial K</th><th class="r">Ratio</th>
          <th class="r">Average</th><th class="r">K</th><th class="r">K, matches</th><th class="r">Binomial K</th><th class="r">Ratio</th></tr></thead>
          <tbody>{"".join(stab)}</tbody></table></div>
        <details class="twin"><summary>By surface</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Surface</th><th>Statistic</th><th class="r">Average</th><th class="r">K</th><th class="r">K, matches</th>
          <th class="r">Bootstrap 95% range of K</th></tr></thead><tbody>{"".join(sstab)}</tbody></table></div>
          <p class="note-small">Every constant, both year spans, the binomial version and the measured chance variation are in
          <code>stage3_shrinkage.csv</code>. "No signal" means no true spread between players was found.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 4. carry-over
    carry = {t: {s: [{"key": k, "label": LABEL[k], "adj": k in ADJ, "r": num(year[(k, t, s)].get("r")),
                      "lo": num(year[(k, t, s)].get("r_lo")), "hi": num(year[(k, t, s)].get("r_hi")),
                      "ceil": num(year[(k, t, s)].get("ceiling")), "pairs": year[(k, t, s)].get("pairs")}
                     for k in order] for s, _ in SURF} for t in TOUR}
    ctab = []
    for k in order:
        cells = []
        for t in TOUR:
            for pair in ("Hard-Clay", "Hard-Grass", "Clay-Grass"):
                x = cross.get((k, t, pair), {})
                cells.append(f'<td class="r">{f2(num(x.get("r")))} <span class="muted">/ {f2(num(x.get("ceiling")))}</span></td>')
        ctab.append(f'<tr><td>{esc(LABEL[k])}</td>{"".join(cells)}</tr>')
    yt = {k: {t: year[(k, t, "all")] for t in TOUR} for k in stats}
    parts.append(f'''    <div class="sub">
      <h3>4. Carry-over</h3>
      <div class="prose">
        <p>A player's shrunk rate in one season against the next (2013 to 2026, every pair of consecutive seasons), and on one
        surface against another in the same season. Beside each correlation, its ceiling: what it would be if the player's
        true rate never changed, given the noise of the two samples.</p>
        <p><span class="kind">Observed</span>Season to season, aces carry over at {f2(yt["ace"]["atp"]["r"])} (men) and
        {f2(yt["ace"]["wta"]["r"])} (women), against ceilings of {f2(yt["ace"]["atp"]["ceiling"])} and {f2(yt["ace"]["wta"]["ceiling"])};
        serve points won at {f2(yt["spw"]["atp"]["r"])} and {f2(yt["spw"]["wta"]["r"])}, and adjusted for the opponent at
        {f2(yt["spw_adj"]["atp"]["r"])} and {f2(yt["spw_adj"]["wta"]["r"])}; return points won at {f2(yt["rpw"]["atp"]["r"])}
        and {f2(yt["rpw"]["wta"]["r"])}, adjusted {f2(yt["rpw_adj"]["atp"]["r"])} and {f2(yt["rpw_adj"]["wta"]["r"])}; break
        points saved at {f2(yt["bp_saved"]["atp"]["r"])} and {f2(yt["bp_saved"]["wta"]["r"])}; tiebreaks at
        {f2(yt["tb_won"]["atp"]["r"])} and {f2(yt["tb_won"]["wta"]["r"])}.</p>
        <p><span class="kind">Inferred</span>Where the ceiling is high enough to read (0.3 or more), the adjusted serve and
        return rates and the ace rate carry nearly all they could ({f2(yt["spw_adj"]["atp"]["true_carry"])},
        {f2(yt["rpw_adj"]["atp"]["true_carry"])} and {f2(yt["ace"]["atp"]["true_carry"])} of their ceilings for the men). The
        rest of the serve style (first serves in {f2(yt["first_in"]["atp"]["true_carry"])}, double faults
        {f2(yt["df"]["atp"]["true_carry"])}) and the results (games won {f2(yt["games_won"]["atp"]["true_carry"])}) change more
        between seasons: players remodel a serve, and move between levels. Across surfaces, the ace rate is nearly the same
        trait everywhere; serve and return points won carry more once adjusted for the opponent, because a surface's opponents
        differ.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Season to the next: a player's shrunk rate</h3><p>Dots: the correlation, with a 95% range;
        ticks: the ceiling a rate that never changed would reach at these samples</p></div>
        <div class="controls"><span>Surface:</span><div class="seg" role="group" aria-label="Surface">
          {"".join(f'<button type="button" data-s3carry="{s}" aria-pressed="{str(s == "all").lower()}">{esc(n)}</button>' for s, n in SURF)}</div></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-1);border-radius:6px"></span>Rate as measured</span>
          <span class="key"><span class="sw-rect" style="background:var(--series-2);border-radius:6px"></span>Adjusted for the opponent</span>
          <span class="key"><span class="sw-line" style="background:var(--axis-ink);width:3px;height:12px"></span>Ceiling</span>
        </div>
        <div class="chart-pair" id="s3-carry"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Surface</th><th>Statistic</th><th class="r">Player pairs</th><th class="r">Correlation</th>
          <th class="r">95% range</th><th class="r">Ceiling</th></tr></thead>
          <tbody>{"".join(f'<tr><td>{TOUR[t]}</td><td>{esc(sn)}</td><td>{esc(LABEL[k])}</td><td class="r">{n0(year[(k, t, s)]["pairs"])}</td>'
                          f'<td class="r">{f2(num(year[(k, t, s)].get("r")))}</td><td class="r">{f2(num(year[(k, t, s)].get("r_lo")))} to {f2(num(year[(k, t, s)].get("r_hi")))}</td>'
                          f'<td class="r">{f2(num(year[(k, t, s)].get("ceiling")))}</td></tr>' for t in TOUR for s, sn in SURF for k in order)}</tbody></table></div></details>
        <details class="twin"><summary>Surface to surface, same season</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Statistic</th><th class="r">ATP hard–clay</th><th class="r">Hard–grass</th><th class="r">Clay–grass</th>
          <th class="r">WTA hard–clay</th><th class="r">Hard–grass</th><th class="r">Clay–grass</th></tr></thead>
          <tbody>{"".join(ctab)}</tbody></table></div>
          <p class="note-small">Each cell: the correlation / its ceiling. Grass is measured on short seasons and its constant on
          three-season windows, so its ceilings are rough; a correlation above its ceiling means the ceiling is too low there.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 5. the next match
    def unit_of(k):
        return r["stats"][stats.index(k)]["unit"]
    fcd = {t: [{"key": k, "label": LABEL[k],
                "v": {f: num((F(k, t, f) or {}).get("share_of_non_chance")) for f, _, _ in FORMS},
                "g": {f: num((F(k, t, f) or {}).get("better_milli_per_unit")) for f, _, _ in FORMS},
                "per": PER.get(unit_of(k), unit_of(k))} for k in order if k not in ADJ] for t in TOUR}
    fcols = FORMS + [("career to date, evaluation levels only", "Career, evaluation levels only", None),
                     ("last 52 weeks, not shrunk", "Last 52 weeks, not shrunk", None)]
    otab = []
    for t in TOUR:
        for k in order:
            if k in ADJ:
                continue
            cells = []
            for f, _, _ in fcols:
                x = F(k, t, f)
                cells.append(f'<td class="r">{f2(num(x["better_milli_per_unit"]))}</td>' if x else '<td class="r">–</td>')
            share = F(k, t, "career to date")
            otab.append(f'<tr><td>{TOUR[t]}</td><td>{esc(LABEL[k])}</td><td>{esc(PER.get(unit_of(k), unit_of(k)))}</td>'
                        f'{"".join(cells)}<td class="r">{pct(num(share["non_chance_part"]), 1)}</td><td class="r">{half.get(k, "–")}</td></tr>')
    sp = {t: {f: F("spw", t, f) for f, _, _ in FORMS} for t in TOUR}
    gw = {t: F("games_won", t, "career to date") for t in TOUR}
    gwe = {t: F("games_won", t, "career to date, evaluation levels only") for t in TOUR}
    swe = {t: F("sets_won", t, "career to date, evaluation levels only") for t in TOUR}
    sw_ = {t: F("sets_won", t, "career to date") for t in TOUR}
    tbr = {t: F("tb_won", t, "last 52 weeks, not shrunk") for t in TOUR}
    parts.append(f'''    <div class="sub">
      <h3>5. The next match from a player's history</h3>
      <div class="prose">
        <p>For every evaluation match from 2019 (the women's box-score rates are evaluated from 2019 on, as the Brief sets;
        the scores here are 2019–2026), the player's rate in that match is forecast from their earlier matches at every level
        from 2010, under the time rule. Three forms, each shrunk toward the tour's average on the match's surface with the
        2010–2018 constant: <b>career to date</b>; the <b>last 52 weeks</b>; and <b>decayed</b>, every earlier match weighted by
        half per half-life (chosen per statistic on the men's 2013–2018 matches from 13, 26, 52, 104 and 208 weeks). Each
        past match is measured against its own surface's average. For serve, return and total points won, the serve and
        return ratings also forecast them, knowing the opponent. The score is the log loss of the next match's points (or
        games, sets...) against the tour's average, and the share of the next match's variation beyond point luck that the
        forecast captures. The best forecast of a statistic is not necessarily the best predictor of who wins; Stage 4
        decides that.</p>
        <p><span class="kind">Observed</span>Serve points won: the player's history captures {pct(sp["atp"]["career to date"]["share_of_non_chance"])}
        (men) and {pct(sp["wta"]["career to date"]["share_of_non_chance"])} (women) of what is not point luck in the next match;
        the ratings, which also know the returner, {pct(sp["atp"]["serve and return ratings"]["share_of_non_chance"])} and
        {pct(sp["wta"]["serve and return ratings"]["share_of_non_chance"])} ({f2(sp["atp"]["serve and return ratings"]["better_milli_per_unit"])}
        and {f2(sp["wta"]["serve and return ratings"]["better_milli_per_unit"])} milli-log-loss per serve point better than the average,
        against {f2(sp["atp"]["career to date"]["better_milli_per_unit"])} and {f2(sp["wta"]["career to date"]["better_milli_per_unit"])}).
        The three forms are close for most rates; recency helps the serve style (the chosen half-lives are
        {half["ace"]} weeks for aces, {half["df"]} for double faults, {half["first_in"]} for first serves in) and not skill
        (serve points won {half["spw"]} weeks, the longest tried, which is nearly the whole career).</p>
        <p><span class="kind">Observed</span>Shrinkage matters most where events are rare: the unshrunk 52-week tiebreak record
        is {f1(-tbr["atp"]["better_milli_per_unit"])} and {f1(-tbr["wta"]["better_milli_per_unit"])} milli-log-loss per tiebreak
        worse than the average. Halving or doubling K moves the career forecast by a few hundredths of a milli-log-loss for
        most rates.</p>
        <p><span class="kind">Observed</span>For results, history from other levels misleads. Women's games won from the whole
        career scores {f2(gw["wta"]["better_milli_per_unit"])} milli-log-loss per game against the average, from evaluation-level
        matches only {f2(gwe["wta"]["better_milli_per_unit"])}; sets won {f2(sw_["wta"]["better_milli_per_unit"])} against
        {f2(swe["wta"]["better_milli_per_unit"])} (men {f2(sw_["atp"]["better_milli_per_unit"])} against {f2(swe["atp"]["better_milli_per_unit"])}).
        <span class="kind">Inferred</span>A player who won most of their games at ITF level wins fewer at the next level up:
        rates of results depend on the level of the opposition, and only the opponent-adjusted rates escape that.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Share of the next match's non-chance variation a forecast captures</h3><p>{WINDOW.replace("-", "–")},
        every surface; 0 is the tour's average; missing where the next match is 95% or more point luck</p></div>
        <div class="legend" aria-hidden="true">
          {"".join(f'<span class="key"><span class="sw-rect" style="background:{c};border-radius:6px"></span>{esc(n)}</span>' for _, n, c in FORMS)}
        </div>
        <div class="chart-pair" id="s3-fc"></div>
        <details class="twin"><summary>Show the log losses as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Statistic</th><th>Per</th>{"".join(f"<th class='r'>{esc(n)}</th>" for _, n, _ in fcols)}
          <th class="r">Beyond point luck</th><th class="r">Half-life, weeks</th></tr></thead>
          <tbody>{"".join(otab)}</tbody></table></div>
          <p class="note-small">Milli-log-loss per unit better than the tour's average on the surface (negative: worse).
          "Beyond point luck" is the share of the next match's squared error that is not the chance of its points. Every form,
          window and surface is in <code>stage3_forecast.csv</code>.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 6. the ratings and the adjustment
    ch = rt["chosen"]
    det = {d["tour"]: d for d in rt["tuning_detail"]}
    oos = {t: next(x for x in det[t]["scored"] if x["window"] == WINDOW) for t in TOUR}
    tun = {t: next(x for x in det[t]["scored"] if x["window"] == "2013-2018") for t in TOUR}
    probe = rt["probe_by_round"]
    spread = {x["tour"]: x for x in rt["spread_2022_2026"]}
    top = {}
    for x in rt["highest_2026"]:
        top.setdefault((x["tour"], x["kind"]), []).append(x)
    atab = []
    for k in ("spw", "rpw"):
        for t in TOUR:
            a, b = P(t, k), P(t, f"{k}_adj")
            ya, yb = year[(k, t, "all")], year[(f"{k}_adj", t, "all")]
            ca, cb = cross[(k, t, "Hard-Clay")], cross[(f"{k}_adj", t, "Hard-Clay")]
            atab.append(f'<tr><td>{esc(LABEL[k])}</td><td>{TOUR[t]}</td><td class="r">{f2(a["reliability_typical"])} → {f2(b["reliability_typical"])}</td>'
                        f'<td class="r">{kfmt(a["k_matches"])} → {kfmt(b["k_matches"])}</td>'
                        f'<td class="r">{kfmt(K(k, t)["K_matches"])} → {kfmt(K(k + "_adj", t)["K_matches"])}</td>'
                        f'<td class="r">{f2(ya["r"])} → {f2(yb["r"])}</td><td class="r">{f2(ca["r"])} → {f2(cb["r"])}</td></tr>')
    tops = []
    for t in TOUR:
        for kind in ("serve", "return"):
            names = ", ".join("{} {:+.2f}".format(x["name"], x["rating"]) for x in top[(t, kind)][:6])
            tops.append(f'<tr><td>{TOUR[t]}</td><td>{kind}</td><td>{esc(names)}</td></tr>')
    tops = "".join(tops)
    parts.append(f'''    <div class="sub">
      <h3>6. Serve and return ratings: adjusting for the opponent</h3>
      <div class="prose">
        <p>A match's serve rate depends on who returns. Subtracting the opponents' average rates does not fix that, because
        those averages depend in turn on whom the opponents played. The ratings instead explain every match's serve points
        at once: the chance that the server wins a point is 1 / (1 + e<sup>−(μ + serve − return)</sup>), with μ the tour's average on the
        surface. After a match each rating moves by the points won above expectation, times a step that is large while the
        rating is uncertain and small once it is well known. Time away widens the uncertainty again. It is Elo on serve points
        with a step that adapts, as Glickman's Glicko does for wins. A rating for a match holds only earlier events and the
        same event's earlier rounds (Stage 1's rule), so Stage 4 can use the pre-match values, which are saved for every
        match.</p>
        <p><span class="kind">Observed</span>Four constants were tuned on the serve points of 2013–2018 (2010–2012 warm up) and frozen:
        a newcomer's serve rating starts {f2(-ch["atp"]["start_serve"])} below their return rating for the men and
        {f2(-ch["wta"]["start_serve"])} for the women (newcomers serve worse against the pool they join), with variances of
        {"{:g} and {:g}".format(ch["atp"]["var_serve"], ch["atp"]["var_return"]) if (ch["atp"]["var_serve"], ch["atp"]["var_return"]) == (ch["wta"]["var_serve"], ch["wta"]["var_return"])
         else "{:g} and {:g} (men), {:g} and {:g} (women)".format(ch["atp"]["var_serve"], ch["atp"]["var_return"], ch["wta"]["var_serve"], ch["wta"]["var_return"])}
        (serve, return) on both tours, which widen by {ch["atp"]["drift"]:g} (men) and {ch["wta"]["drift"]:g} (women) for each week
        away. All lie inside the grid. On {WINDOW.replace("-", "–")}, out of sample, the ratings forecast serve points
        {f2(oos["atp"]["better_milli_per_point"])} (men) and {f2(oos["wta"]["better_milli_per_point"])} (women) milli-log-loss per
        point better than the surface's average ({f2(tun["atp"]["better_milli_per_point"])} and {f2(tun["wta"]["better_milli_per_point"])}
        in the tuning years). Among established players a serve rating's spread is {f2(spread["atp"]["sd_serve"])} and a return
        rating's {f2(spread["atp"]["sd_return"])} on the log-odds scale (men); serve and return correlate at
        {f2(spread["atp"]["corr_serve_return"])}.</p>
        <p><span class="kind">Inferred</span>Adjusted for the opponent, serve and return points won are more reliable, need
        fewer matches, carry over better between seasons and across surfaces (the table). The opponent mix, not the player,
        was a large part of the raw rates' noise.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Raw → adjusted</h3><p>All surfaces; carry-over across surfaces is hard to clay in the same season</p></div>
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th>Statistic</th><th>Tour</th><th class="r">Reliability of a season</th><th class="r">Matches for half signal</th>
          <th class="r">Shrinkage K, matches</th><th class="r">Season to season</th><th class="r">Hard to clay</th></tr></thead>
          <tbody>{"".join(atab)}</tbody></table></div>
        <details class="twin"><summary>The highest ratings in 2026 (a sanity check)</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Tour</th><th>Rating</th><th>Players (latest pre-match value)</th></tr></thead><tbody>{tops}</tbody></table></div>
          <p class="note-small">Players with 2,000 or more serve and return points rated who played in 2026. The ratings are
          relative to the pool; only differences matter.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ verdict table
    vtab = []
    for k in order:
        cells = []
        for t in TOUR:
            x = P(t, k)
            cells.append(f'<td>{esc(x["verdict"] or "–")}{"*" if not x["verdict_firm"] else ""}</td><td class="r">{f2(num(x["reliability_typical"]))}</td>'
                         f'<td class="r">{kfmt(num(x["k_matches"]))}</td><td class="r">{f2(num(x["year_to_year_r"]))}</td>')
        vtab.append(f'<tr><td>{esc(LABEL[k])}</td>{"".join(cells)}</tr>')
    parts.append(f'''    <div class="sub">
      <h3>The verdict, statistic by statistic</h3>
      <div class="prose"><p><span class="kind">Inferred</span>All surfaces. Evidence: the reliability of a regular's season,
      the matches for half signal, and the season-to-season carry-over. A rate that repeats can be a skill or a style; Stage 2
      measured which decide matches, and the summary sets the two side by side.</p></div>
      <div class="panel"><div class="table-wrap"><table class="num wide">
        <thead><tr><th rowspan="2">Statistic</th><th colspan="4">ATP</th><th colspan="4">WTA</th></tr>
        <tr><th>Verdict</th><th class="r">Season</th><th class="r">Half signal</th><th class="r">Carry-over</th>
        <th>Verdict</th><th class="r">Season</th><th class="r">Half signal</th><th class="r">Carry-over</th></tr></thead>
        <tbody>{"".join(vtab)}</tbody></table></div>
        <p class="note-small">* borderline: the 95% range of the season's reliability crosses 0.2 or 0.5.</p></div>
    </div>''')

    # ------------------------------------------------------------------ how it was built and checked
    pop = r["population"]
    parts.append(f'''    <div class="sub">
      <h3>How Stage 3 was built and checked</h3>
      <ul class="plain">
        <li><b>Data.</b> Stage 0's player rows. Measurements: completed matches in the standard format at the evaluation
        levels ({n0(pop["analysis_player_matches"]["atp"])} men's and {n0(pop["analysis_player_matches"]["wta"])} women's
        player-matches, 2010–2026). Forecast history: every completed singles match from 2010 at every level
        ({n0(pop["history_player_matches"]["atp"])} and {n0(pop["history_player_matches"]["wta"])} player-matches). A rate counts
        for a match where both its count and its denominator are written. One Tennis My Life box score (Prague 2026) has an
        unreadable break-point count, as Stage 2 reported; its hold, break and break-points-faced rates are left out.</li>
        <li><b>"All surfaces"</b> measures each match against the tour's 2010–2018 average on its surface, so a player's mix
        of surfaces does not count as a trait.</li>
        <li><b>The time rule.</b> The ratings and every forecast use only earlier events and earlier rounds of the same event.
        The tests check the rating pass against a plain match-by-match pass, a hand-made history and a fresh pass over only
        what the rule lets each match see, and the look-back sums (career, last 52 weeks, decayed) against a row-by-row reading
        of the rule. A probe on the real history redrew the serve points of every match a cut may not see: 0 of
        {n0(probe["atp"]["protected_matches_checked"] + probe["wta"]["protected_matches_checked"])} protected pre-match values moved, while
        {n0(probe["atp"]["later_matches_changed"] + probe["wta"]["later_matches_changed"])} later ones did.</li>
        <li><b>Known on simulated players.</b> The split-half correlation follows the Spearman–Brown curve and recovers k; the
        shrinkage constant is recovered, and the binomial-only constant is shown too small when matches vary beyond point luck;
        the carry-over ceiling gives about 1 for a rate that never changes; the ratings recover true serve and return strengths.</li>
      </ul>
    </div>''')

    data = {"tours": [[t, TOUR_LONG[t]] for t in TOUR], "persist": persist, "curves": curves, "carry": carry,
            "fc": fcd, "forms": [[f, n, c] for f, n, c in FORMS], "units": {k: r["stats"][stats.index(k)]["unit"] for k in stats},
            "labels": LABEL, "verdict": list(st["verdict_thresholds"])}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["traits"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const fmtN = v => Math.round(v).toLocaleString("en-US");
  const f2 = v => v == null ? "–" : (v < 0 ? "−" : "") + Math.abs(v).toFixed(2);
  const pc = v => v == null ? "–" : (v < 0 ? "−" : "") + Math.abs(100 * v).toFixed(0) + "%";
  const tick = v => String(Math.round(v * 100) / 100);
  const bar = (x0, x1, y, h, r) => {
    const right = x1 >= x0, len = Math.abs(x1 - x0), rr = Math.min(r, len / 2, h / 2);
    if (len < 0.5) return `M${x0},${y} H${x0 + (right ? 0.5 : -0.5)} V${y + h} H${x0} Z`;
    return right
      ? `M${x0},${y} H${x1 - rr} Q${x1},${y} ${x1},${y + rr} V${y + h - rr} Q${x1},${y + h} ${x1 - rr},${y + h} H${x0} Z`
      : `M${x0},${y} H${x1 + rr} Q${x1},${y} ${x1},${y + rr} V${y + h - rr} Q${x1},${y + h} ${x1 + rr},${y + h} H${x0} Z`;
  };
  const tip = (node, rows) => window.reportTip.bind(node, rows);
  const seg = (attr, fn) => document.querySelectorAll(`#traits [${attr}]`).forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(`#traits [${attr}]`).forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    fn(b.getAttribute(attr));
  }));

  // ---------------------------------------------------------------- 1. reliability of a regular's season
  (function persist() {
    const host = document.getElementById("s3-persist");
    let surface = "all";
    function draw() {
      host.replaceChildren();
      D.tours.forEach(([t, name]) => {
        const rows = D.persist[t][surface];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        const W = 460, L = 228, R = 40, T = 18, B = 26, rowH = 22, barH = 12;
        const H = T + rows.length * rowH + B;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": reliability of a regular's season for each statistic; the table below holds the numbers" });
        const x = v => L + (W - L - R) * Math.max(0, Math.min(1, v));
        [0, 0.25, 0.5, 0.75, 1].forEach(v => {
          S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
          S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = tick(v);
        });
        D.verdict.forEach(v => {
          S("line", { x1: x(v), x2: x(v), y1: T - 4, y2: H - B, class: "ref", "stroke-width": 1.5 }, svg);
        });
        S("text", { x: (x(D.verdict[0]) + x(1)) / 2, y: T - 6, "text-anchor": "middle" }, svg).textContent = "repeats";
        S("text", { x: (x(D.verdict[1]) + x(D.verdict[0])) / 2, y: T - 6, "text-anchor": "middle" }, svg).textContent = "weakly";
        S("text", { x: (x(0) + x(D.verdict[1])) / 2, y: T - 6, "text-anchor": "middle" }, svg).textContent = "noise";
        rows.forEach((c, i) => {
          const y0 = T + i * rowH + (rowH - barH) / 2;
          S("text", { x: L - 8, y: y0 + barH / 2 + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.label;
          if (c.rel == null) { S("text", { x: x(0) + 6, y: y0 + barH - 2, class: "val" }, svg).textContent = "–"; return; }
          const color = c.adj ? "var(--series-2)" : "var(--series-1)";
          const p = S("path", { d: bar(x(0), x(c.rel), y0, barH, 4), fill: color, class: "mark", tabindex: "0" }, svg);
          if (c.lo != null && c.hi != null) S("line", { x1: x(c.lo), x2: x(c.hi), y1: y0 + barH / 2, y2: y0 + barH / 2, stroke: "var(--ink-2)", "stroke-width": 1 }, svg);
          S("text", { x: x(Math.max(c.rel, c.hi || 0)) + 5, y: y0 + barH - 2, class: "val" }, svg).textContent = f2(c.rel);
          const hit = S("rect", { x: 0, y: T + i * rowH, width: W, height: rowH, class: "hit" }, svg);
          const rowsFn = () => [f2(c.rel) + " reliability · " + c.verdict + (c.firm ? "" : " (borderline)"), c.label + " · " + name,
            "95% range " + f2(c.lo) + " to " + f2(c.hi), "a typical season: " + fmtN(c.m) + " matches, " + fmtN(c.u) + " " + c.unit];
          tip(hit, rowsFn); tip(p, rowsFn);
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    seg("data-s3persist", v => { surface = v; draw(); });
    draw();
  })();

  // ---------------------------------------------------------------- 2. split-half correlation against the sample
  (function curve() {
    const host = document.getElementById("s3-curve");
    const pick = document.getElementById("s3-stat");
    let surface = "all", unit = "m";
    function draw() {
      host.replaceChildren();
      const stat = pick.value;
      let xmax = 0;
      D.tours.forEach(([t]) => { const c = D.curves[t][surface][stat]; if (c) c.pts.forEach(p => { xmax = Math.max(xmax, unit === "m" ? p[0] : p[4]); }); });
      const step = xmax <= 12 ? 2 : xmax <= 40 ? 5 : xmax <= 120 ? 20 : xmax <= 600 ? 100 : xmax <= 3000 ? 500 : 1000;
      const top = Math.ceil(xmax / step) * step || 1;
      D.tours.forEach(([t, name]) => {
        const c = D.curves[t][surface][stat];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        if (!c) { box.appendChild(el("p", "note-small", "Too few players for this statistic and surface.")); host.appendChild(box); return; }
        const W = 460, H = 270, L = 40, R = 14, T = 12, B = 36;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": split-half correlation of " + D.labels[stat] + " against the sample, with the fitted curve; the table below holds the fitted samples" });
        const x = v => L + (W - L - R) * v / top;
        const y = v => T + (H - T - B) * (1 - (Math.max(-0.1, Math.min(1, v)) + 0.1) / 1.1);
        for (let v = 0; v <= top + 1e-9; v += step) {
          S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
          S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = fmtN(v);
        }
        [0, 0.25, 0.5, 0.75, 1].forEach(v => {
          S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: v === 0.5 ? "ref" : (v === 0 ? "axis" : "grid") }, svg);
          S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = tick(v);
        });
        S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = unit === "m" ? "matches in each set" : D.units[stat] + " in each set";
        const k = unit === "m" ? c.k : c.ku;
        if (k != null && k > 0) {
          const pts = [];
          for (let i = 0; i <= 120; i++) { const v = top * i / 120; pts.push((i ? "L" : "M") + x(v).toFixed(1) + "," + y(v / (v + k)).toFixed(1)); }
          S("path", { d: pts.join(" "), fill: "none", stroke: "var(--series-1)", "stroke-width": 2, "stroke-linejoin": "round", opacity: 0.55 }, svg);
          if (k <= top) {
            S("line", { x1: x(k), x2: x(k), y1: y(0.5) - 6, y2: y(0.5) + 6, stroke: "var(--ink)", "stroke-width": 2 }, svg);
            S("text", { x: x(k) + 6, y: y(0.5) + 20, class: "val" }, svg).textContent = "k = " + (k >= 10 ? fmtN(k) : k.toFixed(1));
          }
        }
        c.pts.forEach(p => {
          const xv = unit === "m" ? p[0] : p[4];
          if (p[2] != null && p[3] != null) S("line", { x1: x(xv), x2: x(xv), y1: y(p[2]), y2: y(p[3]), stroke: "var(--series-1)", "stroke-width": 1.5 }, svg);
          const dot = S("circle", { cx: x(xv), cy: y(p[1]), r: 4.5, fill: p[6] ? "var(--surface)" : "var(--series-1)", stroke: p[6] ? "var(--series-1)" : "var(--surface)",
            "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          const hit = S("circle", { cx: x(xv), cy: y(p[1]), r: 12, class: "hit" }, svg);
          const rowsFn = () => ["r = " + f2(p[1]) + " (95% range " + f2(p[2]) + " to " + f2(p[3]) + ")", D.labels[stat] + " · " + name,
            p[0] + " matches in each set, about " + fmtN(p[4]) + " " + D.units[stat], fmtN(p[5]) + " player-windows" + (p[6] ? " · directional only" : "")];
          tip(hit, rowsFn); tip(dot, rowsFn);
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    pick.addEventListener("change", draw);
    seg("data-s3curve", v => { surface = v; draw(); });
    seg("data-s3unit", v => { unit = v; draw(); });
    draw();
  })();

  // ---------------------------------------------------------------- 4. season to season
  (function carry() {
    const host = document.getElementById("s3-carry");
    let surface = "all";
    function draw() {
      host.replaceChildren();
      D.tours.forEach(([t, name]) => {
        const rows = D.carry[t][surface];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        const W = 460, L = 228, R = 14, T = 6, B = 30, rowH = 22;
        const H = T + rows.length * rowH + B;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": season-to-season correlation of each statistic and its ceiling; the table below holds the numbers" });
        const lo = -0.1, hi = 1.0;
        const x = v => L + (W - L - R) * (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo);
        [0, 0.25, 0.5, 0.75, 1].forEach(v => {
          S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "ref" : "grid" }, svg);
          S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = tick(v);
        });
        S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "correlation, one season with the next";
        rows.forEach((c, i) => {
          const yc = T + i * rowH + rowH / 2;
          S("text", { x: L - 8, y: yc + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.label;
          if (c.r == null) { S("text", { x: x(0) + 6, y: yc + 4, class: "val" }, svg).textContent = "–"; return; }
          if (c.ceil != null) S("line", { x1: x(c.ceil), x2: x(c.ceil), y1: yc - 7, y2: yc + 7, stroke: "var(--axis-ink)", "stroke-width": 3, "stroke-linecap": "round" }, svg);
          if (c.lo != null) S("line", { x1: x(c.lo), x2: x(c.hi), y1: yc, y2: yc, stroke: "var(--ink-2)", "stroke-width": 1 }, svg);
          const color = c.adj ? "var(--series-2)" : "var(--series-1)";
          const dot = S("circle", { cx: x(c.r), cy: yc, r: 5, fill: color, stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          const hit = S("rect", { x: 0, y: yc - rowH / 2, width: W, height: rowH, class: "hit" }, svg);
          const rowsFn = () => ["r = " + f2(c.r) + " · ceiling " + f2(c.ceil), c.label + " · " + name,
            "95% range " + f2(c.lo) + " to " + f2(c.hi) + " · " + fmtN(c.pairs) + " player pairs"];
          tip(hit, rowsFn); tip(dot, rowsFn);
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    seg("data-s3carry", v => { surface = v; draw(); });
    draw();
  })();

  // ---------------------------------------------------------------- 5. the next match
  (function fc() {
    const host = document.getElementById("s3-fc");
    let lo = 0, hi = 0;
    D.tours.forEach(([t]) => D.fc[t].forEach(c => D.forms.forEach(([f]) => { const v = c.v[f]; if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } })));
    lo = Math.floor(lo * 10) / 10; hi = Math.ceil(hi * 10) / 10;
    D.tours.forEach(([t, name]) => {
      const rows = D.fc[t];
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, L = 228, R = 14, T = 6, B = 30, rowH = 34;
      const H = T + rows.length * rowH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": share of the next match's non-chance variation captured by each forecast form; the table below holds the log losses" });
      const x = v => L + (W - L - R) * (v - lo) / (hi - lo);
      for (let v = lo; v <= hi + 1e-9; v += 0.1) {
        const vv = Math.round(v * 10) / 10;
        S("line", { x1: x(vv), x2: x(vv), y1: T, y2: H - B, class: vv === 0 ? "ref" : "grid" }, svg);
        if (Math.round(vv * 10) % 2 === 0) S("text", { x: x(vv), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = Math.round(vv * 100) + "%";
      }
      S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "share captured, beyond the tour's average";
      rows.forEach((c, i) => {
        const yc = T + i * rowH + rowH / 2;
        S("text", { x: L - 8, y: yc + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.label;
        const any = D.forms.some(([f]) => c.v[f] != null);
        if (!any) { S("text", { x: x(0) + 6, y: yc + 4, class: "val" }, svg).textContent = "point luck only"; return; }
        D.forms.forEach(([f, fname, color], j) => {
          const v = c.v[f];
          if (v == null) return;
          const yy = yc + (j - 1.5) * 7;
          const mark = f === "serve and return ratings"
            ? S("path", { d: `M${x(v)},${yy - 6} L${x(v) + 6},${yy} L${x(v)},${yy + 6} L${x(v) - 6},${yy} Z`, fill: color, stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg)
            : S("circle", { cx: x(v), cy: yy, r: 4.5, fill: color, stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
          tip(mark, () => [pc(v) + " captured · " + f2(c.g[f]) + " milli-log-loss per " + c.per + " better", fname + " · " + c.label + " · " + name]);
        });
        const hit = S("rect", { x: 0, y: yc - rowH / 2, width: L, height: rowH, class: "hit" }, svg);
        tip(hit, () => [c.label + " · " + name].concat(D.forms.filter(([f]) => c.v[f] != null).map(([f, fname]) => pc(c.v[f]) + "  " + fname)));
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();
})();
"""
