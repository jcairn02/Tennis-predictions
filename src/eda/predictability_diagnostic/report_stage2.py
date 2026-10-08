"""Report section for Stage 2, "Anatomy of a win": what decides a match, read from each match's own statistics.

Points to wins; break points and tiebreaks beyond the points share; the randomness floor against Elo and the
closing odds; whether over-performance persists; the components of the points edge; and every rate's match
impact. Each result is set beside the pure-luck replay (the same matches played again with independent points).

Every number comes from stage2_results.json (render_report.py assembles the page).
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": 2, "id": "anatomy", "title": "Anatomy of a win"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "ATP (men)", "wta": "WTA (women)"}
LEVEL_WORDS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
               "GSQ": "Grand Slam qualifying", "TQ": "Tour qualifying", "CH": "Challenger / WTA 125",
               "CHQ": "Challenger / 125 qualifying"}
LEVEL_ORDER = ["GS", "FIN", "T1000", "T500", "T250", "GSQ", "TQ", "CH", "CHQ"]
HEAD = "2022-2026"
CURVE_LO, CURVE_HI = 44, 56                 # the points-share range the curve shows (percent)
MEASURES = [("spw", "Serve points won"), ("rpw", "Return points won"), ("bp_saved_over", "Break points saved*"),
            ("bp_converted_over", "Break points converted*"), ("bp_both_over", "Break points, both ways*"),
            ("tb_over", "Tiebreaks won*")]
COMPONENTS = [("first_play", "First serves in play"), ("second_play", "Second serves in play"), ("ace", "Aces"),
              ("double_faults", "Double faults"), ("first_in", "First serves in"), ("serve_count", "Serve-point count")]
RATE_WORDS = {"sets_won": "Sets won", "games_won": "Games won", "tpw": "Total points won", "hold": "Hold / break rate",
              "spw": "Serve / return points won", "first_won": "First-serve points won", "bp_faced_pg": "Break points faced per service game",
              "second_won": "Second-serve points won", "bp_saved": "Break points saved / converted", "tb_won": "Tiebreaks won",
              "ace": "Aces per serve point", "df": "Double faults per serve point", "first_in": "First serves in",
              "iid_floor": "The iid model's chance (reference)"}


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


def r2(x) -> str:
    return f"{x:.2f}".replace("-0.00", "0.00")


def same(a, b) -> bool:
    """Equal as numbers when both read as numbers (the JSON writes best of 3 as 3.0), else as text."""
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div>'
            f'<div class="note">{note}</div></div>')


def render(study_dir: Path) -> dict:
    r = load(study_dir, "stage2_results.json")
    pbp = load(study_dir, "stage2_pbp_results.json") if (study_dir / "stage2_pbp_results.json").exists() else None
    coin = r["coin"]
    steps = r["population"]["steps"]
    final = steps[-1]
    first = r["first_year"]
    parts = []

    # ------------------------------------------------------------------ the numbers the prose uses
    fits = {(f["tour"], f["best_of"]): f for f in r["a_points_to_wins"]["fits"]}
    fits_l = {(f["tour"], f["best_of"]): f for f in r["a_points_to_wins"]["fits_pure_luck"]}
    fewer = r["a_points_to_wins"]["fewer_rows"]
    allrow = {x["tour"]: x for x in fewer if x["dim"] == "all"}
    ret = {x["tour"]: x for x in r["a_points_to_wins"]["retirements"]}
    fit_world = r["twin"]["fit"]
    models = r["b_beyond_points"]["models"]

    def gain(world, tour, model, bo="all"):
        for x in models:
            if x["world"] == world and x["tour"] == tour and str(x["best_of"]) == str(bo) and x["model"] == model:
                return x["gain_over_base_milli"]
        raise KeyError((world, tour, model, bo))
    desc = {(d["tour"], str(d["best_of"])): d for d in r["b_beyond_points"]["descriptive"]}
    desc_l = {(d["tour"], str(d["best_of"])): d for d in r["b_beyond_points"]["pure_luck_descriptive"]}
    cells = r["c_floor"]["cells"]

    def cell(tour, window, dim="all", value=None, odds=True):
        for c in cells:
            if (c["tour"] == tour and c["window"] == window and c["dim"] == dim and c["value"] == value
                    and c["odds_only"] == odds):
                return c
        raise KeyError((tour, window, dim, value, odds))
    win_all = {t: f"{first[t]}-2026" for t in TOUR}
    H = {t: cell(t, HEAD) for t in TOUR}
    slope = {s["tour"]: s for s in r["c_floor"]["slope"]}
    pers = {(x["tour"], x["min_matches_per_half"], x["measure"]): x for x in r["d_persistence"]["rows"]}
    comp = {(x["tour"], x["surface"]): x for x in r["e_components"]["rows"]}
    impact = [x for x in r["f_match_impact"]["rows"] if str(x["best_of"]) == "all"]
    imp = {(x["tour"], x["rate"]): x for x in impact}

    # ------------------------------------------------------------------ intro and tiles
    lk = {t: fit_world["twin"][t] for t in TOUR}
    p25 = {t: pers[(t, 25, "bp_both_over")] for t in TOUR}
    s25 = {t: pers[(t, 25, "spw")] for t in TOUR}
    parts.append(f'''    <div class="prose">
      <p>Stage 2 looks inside matches: what decides who wins, read from each match's own statistics, its <b>box score</b>
      (points won on serve and on return, aces, double faults, break points) and its score. <b>None of this is a pre-match
      forecast</b>: every number uses the match's own events, so it says how matches are won, not how to predict them.
      It covers {n(final["atp"])} men's and {n(final["wta"])} women's evaluation matches that were completed and have a box score
      (the women's from {first["wta"]}, as the Brief sets for box scores). Retirements are set aside: their statistics cover part
      of a match that something else decided.</p>
      <p>One device runs through the section, the <b>pure-luck replay</b>. Every match is played again, point by point, as if each
      point were an independent draw: the server wins it with a fixed probability, whatever the score, at the serve rates the two
      players showed that day. The replay has no skill on big points, no nerves and no streaks. What the real matches show
      beyond the replay is something more than scoring luck; what they share with it is not.</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("Matches won by the player who won fewer points", pct(allrow["atp"]["won_with_fewer_points_pct"]),
                 pct(allrow["wta"]["won_with_fewer_points_pct"]),
                 f"pure-luck replay: {pct(lk['atp']['won_with_fewer_points_pct'])} and {pct(lk['wta']['won_with_fewer_points_pct'])}")}
      {pair_tile("Share of all points that wins 90% of the time", pct(fits[("atp", 3)]["share_for_90pct"]),
                 pct(fits[("wta", 3)]["share_for_90pct"]), "best of three; 50% is a coin flip")}
      {pair_tile("Scoring luck: the best a day-perfect forecast could do", ll3(H["atp"]["luck"]), ll3(H["wta"]["luck"]),
                 f"log loss of a forecaster who knew how well each player would serve that day; closing odds {ll3(H['atp']['market'])} "
                 f"and {ll3(H['wta']['market'])}, a coin {coin:.3f} (2022–2026, matches with odds)")}
      {pair_tile("Break-point over-performance that carries over", r2(p25["atp"]["r_mean"]), r2(p25["wta"]["r_mean"]),
                 f"correlation between two random halves of each player's matches; serve points won {s25['atp']['r_mean']:.2f} and "
                 f"{s25['wta']['r_mean']:.2f}, pure luck {r2(p25['atp']['luck_r_mean'])} and {r2(p25['wta']['luck_r_mean'])}")}
    </div>''')

    # ------------------------------------------------------------------ terms
    def serve_range(t):
        means = [x["mean"] for x in r["twin"]["prior"] if x["tour"] == t]
        return f"{100 * min(means):.1f}–{100 * max(means):.1f}%"
    parts.append(f'''    <div class="sub">
      <h3>Terms used in this section</h3>
      <dl class="terms">
        <dt>Points share</dt><dd>The share of all the points in a match that a player won, on serve and on return together.
        The points edge is that share minus 50%.</dd>
        <dt>Serve rate</dt><dd>The share of the points on their own serve that a player won in the match. Serving wins most
        points: on average {serve_range("atp")} for the men and {serve_range("wta")} for the women, by surface.</dd>
        <dt>Break point</dt><dd>A point that would give the receiver the server's game (a <i>break</i>) if the receiver won it.
        The server <i>saves</i> it by winning it; the receiver <i>converts</i> it.</dd>
        <dt>Tiebreak</dt><dd>At six games all a set is decided by a race to 7 points, won by two. Grand Slam deciding sets
        have their own rules (a race to 10, a tiebreak only at 12 games all, or none), listed in
        <code>stage2_slam_final_set_rules.csv</code>.</dd>
        <dt>Best of three, five</dt><dd>The first to win two sets, or three. Only men's Grand Slam main draws (and, in most years,
        Wimbledon's last qualifying round) are best of five. The <i>deciding set</i> is the one played at one set all, or two all.</dd>
        <dt>The iid model</dt><dd>Every point an independent draw ("independent and identically distributed"): the server wins
        it with their serve rate, whatever the score. From the two serve rates it gives the exact chance of winning a game, a
        tiebreak, a set and the match, under the match's format.</dd>
        <dt>Expected</dt><dd>What the iid model says a player should have won: break points saved = break points faced times the
        serve rate; tiebreaks = the model's chance of winning a tiebreak from the two serve rates. <i>Over-performance</i> is the
        actual count minus this.</dd>
        <dt>Plug-in floor</dt><dd>The iid model's chance that a player wins, fed the serve rates measured in the match itself.</dd>
        <dt>Pure-luck replay</dt><dd>The same matches played again point by point under the iid model. The measured rates carry
        noise (a rate measured over one match's serve points can sit several points from the player's true rate that day), so the
        replay draws each player's true rate from what the measured one allows, shrinking it toward the tour's average for that surface by the amount the noise implies.</dd>
        <dt>Log loss</dt><dd>As in Stage 1: the average of minus the natural log of the probability given to the player who won;
        a coin scores 0.693, lower is better, and 0.001 is one milli-log-loss.</dd>
        <dt>Split-half correlation</dt><dd>Each player's matches are split into two random halves; the correlation, across
        players, between a measure in one half and in the other. A stable trait correlates highly; luck does not correlate.</dd>
      </dl>
    </div>''')

    # ------------------------------------------------------------------ 1. points to wins
    curve = {}
    for t in TOUR:
        series = []
        for key, bo, world, label, color in (("bo3", 3, "real", "Best of 3", "var(--series-1)"),
                                             ("bo5", 5, "real", "Best of 5", "var(--series-2)"),
                                             ("luck", 3, "pure luck", "Pure luck, best of 3", "var(--axis-ink)")):
            pts = [[c["points_share_pct"], c["won_pct"], c["player_matches"]] for c in r["a_points_to_wins"]["curve"]
                   if c["tour"] == t and c["best_of"] == bo and c["world"] == world
                   and c["player_matches"] >= r["a_points_to_wins"]["curve_min_rows_to_show"] and CURVE_LO <= c["points_share_pct"] <= CURVE_HI]
            if pts:
                series.append({"key": key, "label": label, "color": color, "pts": sorted(pts)})
        curve[t] = series
    ftab = []
    for label, dim, key, vals in (("Best of", "best_of", "best_of", [3, 5]), ("Surface", "surface", "surface", ["Hard", "Clay", "Grass", "Carpet"]),
                                  ("Level", "level", "level_group", LEVEL_ORDER), ("Era", "era", "era", ["2013-16", "2017-19", "2020-21", "2022-26"])):
        ftab.append(f'<tr class="group"><td colspan="5">{esc(label)}</td></tr>')
        for v in vals:
            row = {t: next((x for x in fewer if x["dim"] == dim and x["tour"] == t and same(x[key], v)), None) for t in TOUR}
            if not any(row.values()):
                continue
            name = LEVEL_WORDS.get(v, f"Best of {v}" if dim == "best_of" else str(v).replace("-", "–"))
            cellsx = []
            for t in TOUR:
                x = row[t]
                cellsx.append(f'<td class="r">{pct(x["won_with_fewer_points_pct"])}{"*" if x["directional_only"] else ""}</td>'
                              f'<td class="r">{n(x["matches"])}</td>' if x else '<td class="r">–</td><td class="r">–</td>')
            ftab.append(f'<tr><td>{esc(name)}</td>{"".join(cellsx)}</tr>')
    ctab = "".join(f'<tr><td>{TOUR[t]}</td><td>{esc(s["label"])}</td><td class="r">{p[0]}%</td><td class="r">{pct(p[1])}</td>'
                   f'<td class="r">{n(p[2])}</td></tr>' for t in TOUR for s in curve[t] for p in s["pts"])
    a3, a5, w3 = fits[("atp", 3)], fits[("atp", 5)], fits[("wta", 3)]
    grass = next(x for x in fewer if x["dim"] == "surface" and x["tour"] == "atp" and x["surface"] == "Grass")
    clay = next(x for x in fewer if x["dim"] == "surface" and x["tour"] == "atp" and x["surface"] == "Clay")
    parts.append(f'''    <div class="sub">
      <h3>1. Points to wins</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>Winning more points almost always wins the match, and the margin is thin. In men's
        best-of-three matches a player who wins {pct(a3["share_for_90pct"])} of all the points wins about 90% of the time (each extra
        point of share multiplies the odds of winning by {math.exp(a3["slope_per_point"]):.1f}); in best of five it takes
        {pct(a5["share_for_90pct"])}, and for the women {pct(w3["share_for_90pct"])}. Winners take on average {pct(a3["mean_winner_share"])}
        of the points (men, best of three) and {pct(w3["mean_winner_share"])} (women).</p>
        <p><span class="kind">Observed</span>Still, {pct(allrow["atp"]["won_with_fewer_points_pct"], 2)} of men's matches and
        {pct(allrow["wta"]["won_with_fewer_points_pct"], 2)} of women's went to the player who won fewer points, and in
        {pct(allrow["atp"]["equal_points_pct"])} and {pct(allrow["wta"]["equal_points_pct"])} the points were level. On grass it happens
        in {pct(grass["won_with_fewer_points_pct"])} of men's matches, on clay {pct(clay["won_with_fewer_points_pct"])}. Among retirements
        it is {pct(ret["atp"]["advanced_with_fewer_points_pct"])} and {pct(ret["wta"]["advanced_with_fewer_points_pct"])}: their box scores cover
        part of a match.</p>
        <p><span class="kind">Inferred</span>The pure-luck replay gives {pct(lk["atp"]["won_with_fewer_points_pct"], 2)} and
        {pct(lk["wta"]["won_with_fewer_points_pct"], 2)}, and almost the same curve below. Winning with fewer points is what independent
        points produce at these serve rates; it does not need clutch play to explain it. <span class="kind">Observed</span>One difference:
        for the women the points share decides a little less than pure luck predicts. A logistic regression of the result on the points
        share scores {fits[("wta", 3)]["cv_logloss"]:.3f} on the real matches against {fits_l[("wta", 3)]["cv_logloss"]:.3f} on the replay
        (men, best of three: {fits[("atp", 3)]["cv_logloss"]:.3f} against {fits_l[("atp", 3)]["cv_logloss"]:.3f}).</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Chance of winning, by share of points won</h3><p>Share of player-matches won, in one-point bins of the points
        share (bins with at least 100 player-matches, {CURVE_LO}–{CURVE_HI}%; outside it the result is all but certain)</p></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-line" style="background:var(--series-1)"></span>Best of 3</span>
          <span class="key"><span class="sw-line" style="background:var(--series-2)"></span>Best of 5 (men's Grand Slams)</span>
          <span class="key"><span class="sw-line" style="background:var(--axis-ink)"></span>Pure-luck replay, best of 3</span>
        </div>
        <div class="chart-pair" id="s2-curve"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Tour</th><th>Series</th><th class="r">Points share</th><th class="r">Won</th><th class="r">Player-matches</th></tr></thead>
          <tbody>{ctab}</tbody></table></div></details>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Matches won by the player who won fewer points</h3><p>* under 300 matches: directional only</p></div>
        <div class="table-wrap"><table class="num">
          <thead><tr><th></th><th class="r">ATP</th><th class="r">Matches</th><th class="r">WTA</th><th class="r">Matches</th></tr></thead>
          <tbody>{"".join(ftab)}</tbody></table></div>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 2. break points and tiebreaks
    beyond = {t: [{"cat": cat, "real": gain("real", t, model), "luck": gain("pure luck", t, model)}
                  for cat, model in (("Break points", "points + break points"), ("Tiebreaks", "points + tiebreaks"),
                                     ("Both", "points + both"))] for t in TOUR}
    da, dl = {t: desc[(t, "all")] for t in TOUR}, {t: desc_l[(t, "all")] for t in TOUR}

    def over(d):
        return d["all_players"]["saved_pct"] - d["all_players"]["expected_saved_pct"]
    press = {t: over(da[t]) - over(dl[t]) for t in TOUR}
    btab = []
    for t in TOUR:
        for world, dd in (("Real", da[t]), ("Pure luck", dl[t])):
            for who in ("all_players", "winners", "losers"):
                x = dd[who]
                btab.append(f'<tr><td>{TOUR[t]}</td><td>{world}</td><td>{who.replace("_", " ").capitalize()}</td>'
                            f'<td class="r">{n(x["break_points_faced"])}</td><td class="r">{pct(x["saved_pct"], 2)}</td>'
                            f'<td class="r">{pct(x["expected_saved_pct"], 2)}</td>'
                            f'<td class="r">{mm(x["saved_pct"] - x["expected_saved_pct"], True)}</td>'
                            f'<td class="r">{pct(x["tiebreaks_won_pct"])}</td><td class="r">{pct(x["tiebreaks_expected_pct"])}</td></tr>')
    mtab = []
    for x in models:
        if str(x["best_of"]) == "all" or x["tour"] == "atp":
            g = x["gain_over_base_milli"]
            gtxt = f'{mm(g["milli"])} ({mm(g["lo"])} to {mm(g["hi"])})' if g.get("milli") else "–"
            mtab.append(f'<tr><td>{TOUR[x["tour"]]}</td><td>{esc(x["best_of"])}</td><td>{esc(x["world"])}</td>'
                        f'<td>{esc(x["model"])}</td><td class="r">{x["cv_logloss"]:.4f}</td><td class="r">{gtxt}</td></tr>')
    base = {t: next(x for x in models if x["world"] == "real" and x["tour"] == t and str(x["best_of"]) == "all"
                    and x["model"] == "points") for t in TOUR}
    parts.append(f'''    <div class="sub">
      <h3>2. Beyond the points: break points and tiebreaks</h3>
      <div class="prose">
        <p>Given the points share, how much do break points and tiebreaks explain? A logistic regression of the result on the points
        share alone scores a log loss of {base["atp"]["cv_logloss"]:.3f} (men) and {base["wta"]["cv_logloss"]:.3f} (women), five-fold
        cross-validated. Two inputs are then added: break points won above expectation (saves on serve and conversions on return
        together, in break points), and tiebreaks won above expectation.</p>
        <p><span class="kind">Observed</span>Break points add {mm(beyond["atp"][0]["real"]["milli"])} milli-log-loss for the men (95% range
        {mm(beyond["atp"][0]["real"]["lo"])} to {mm(beyond["atp"][0]["real"]["hi"])}) and {mm(beyond["wta"][0]["real"]["milli"])} for the women
        ({mm(beyond["wta"][0]["real"]["lo"], True)} to {mm(beyond["wta"][0]["real"]["hi"], True)}); tiebreaks add {mm(beyond["atp"][1]["real"]["milli"])} and
        {mm(beyond["wta"][1]["real"]["milli"])}; both, {mm(beyond["atp"][2]["real"]["milli"])} and {mm(beyond["wta"][2]["real"]["milli"])}.
        In the pure-luck replay the same steps give {mm(beyond["atp"][0]["luck"]["milli"])}, {mm(beyond["wta"][0]["luck"]["milli"])};
        {mm(beyond["atp"][1]["luck"]["milli"])}, {mm(beyond["wta"][1]["luck"]["milli"])}; and {mm(beyond["atp"][2]["luck"]["milli"])},
        {mm(beyond["wta"][2]["luck"]["milli"])}.</p>
        <p><span class="kind">Inferred</span>Tiebreaks, not break points, carry what the points share misses: a tiebreak settles a
        whole set on a dozen points. They do so about as much as pure luck predicts, slightly less (the real matches play fewer
        tiebreaks than the replay: {fit_world["real"]["atp"]["tiebreaks_per_match"]:.3f} a match against
        {fit_world["twin"]["atp"]["tiebreaks_per_match"]:.3f} for the men).</p>
        <p><span class="kind">Observed</span>Measured against their serve rate in the match, servers seem to save more break points
        than expected: {pct(da["atp"]["all_players"]["saved_pct"], 2)} against {pct(da["atp"]["all_players"]["expected_saved_pct"], 2)} for the men.
        That is an artefact of the measure: in the replay, where points are pure luck, it gives {pct(dl["atp"]["all_players"]["saved_pct"], 2)}
        against {pct(dl["atp"]["all_players"]["expected_saved_pct"], 2)}. A player who faces many break points has usually had an unlucky day
        on serve, which drags the rate they are measured against below their true one (the tests show the bias is absent against the
        true rate). <span class="kind">Inferred</span>Against the replay, real servers save {mm(abs(press["atp"]))} points
        {"fewer" if press["atp"] < 0 else "more"} break points than pure luck gives for the men and {mm(abs(press["wta"]))}
        {"fewer" if press["wta"] < 0 else "more"} for the women{": a small pressure effect" if press["atp"] < 0 and press["wta"] < 0 else ""}.</p>
        <p><span class="kind">Observed</span>Winners won {pct(da["atp"]["winners"]["tiebreaks_won_pct"])} of the tiebreaks they played,
        against {pct(da["atp"]["winners"]["tiebreaks_expected_pct"])} their serve rates predict (men; replay
        {pct(dl["atp"]["winners"]["tiebreaks_won_pct"])} against {pct(dl["atp"]["winners"]["tiebreaks_expected_pct"])}): winning tiebreaks is
        much of how matches are won, and selection, not skill, makes winners look clutch. Of the matches won with fewer points, the winner
        was ahead of expectation on break points or tiebreaks in {pct(da["atp"]["of_those_ahead_on_either_pct"])} (men) and
        {pct(da["wta"]["of_those_ahead_on_either_pct"])} (women); in the replay {pct(dl["atp"]["of_those_ahead_on_either_pct"])} and
        {pct(dl["wta"]["of_those_ahead_on_either_pct"])}.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>What break points and tiebreaks add to the points share</h3><p>Milli-log-loss better than the
        points share alone, cross-validated; whiskers are 95% ranges</p></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-1)"></span>Real matches</span>
          <span class="key"><span class="sw-rect" style="background:var(--axis-ink)"></span>Pure-luck replay</span>
        </div>
        <div class="chart-pair" id="s2-beyond"></div>
        <details class="twin"><summary>Show the regressions as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Best of</th><th>World</th><th>Inputs</th><th class="r">Log loss</th><th class="r">Gain over the base</th></tr></thead>
          <tbody>{"".join(mtab)}</tbody></table></div>
          <p class="note-small">The base is the points share (inputs starting "points") or the iid model's chance from the two serve rates
          (inputs starting "iid model").</p></details>
        <details class="twin"><summary>Break points and tiebreaks against expectation</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>World</th><th>Players</th><th class="r">Break points faced</th><th class="r">Saved</th><th class="r">Expected</th>
          <th class="r">Saved minus expected</th><th class="r">Tiebreaks won</th><th class="r">Expected</th></tr></thead>
          <tbody>{"".join(btab)}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 3. the randomness floor
    split = []
    for t in TOUR:
        c = H[t]
        for kind, fl in (("Plug-in floor", c["floor"]), ("Corrected floor", c["luck"])):
            split.append({"tour": t, "name": TOUR_LONG[t], "kind": kind, "known": 1000 * (coin - c["market"]),
                          "day": 1000 * (c["market"] - fl), "luck": 1000 * fl, "market": c["market"], "floor": fl})
    ftr = []
    for t in TOUR:
        for w in (win_all[t], HEAD):
            for dim, val, lab in (("all", None, "All"), ("best_of", 3, "Best of 3"), ("best_of", 5, "Best of 5")):
                for odds in (False, True):
                    try:
                        c = cell(t, w, dim, val, odds)
                    except KeyError:
                        continue
                    mk = f'<td class="r">{ll3(c["market"])}</td>' if odds else '<td class="r">–</td>'
                    ftr.append(f'<tr><td>{TOUR[t]}</td><td>{w.replace("-", "–")}</td><td>{lab}</td><td>{"with odds" if odds else "all"}</td>'
                               f'<td class="r">{n(c["matches"])}</td><td class="r">{ll3(c["floor"])}</td><td class="r">{ll3(c["luck"])}</td>'
                               f'<td class="r">{ll3(c["twin_plugin"])}</td><td class="r">{ll3(c["elo"])}</td>{mk}</tr>')
    ltr = []
    for t in TOUR:
        for lg in LEVEL_ORDER:
            try:
                c = cell(t, win_all[t], "level", lg, False)
            except KeyError:
                continue
            ltr.append(f'<tr><td>{TOUR[t]}</td><td>{esc(LEVEL_WORDS[lg])}{"*" if c["directional_only"] else ""}</td><td class="r">{n(c["matches"])}</td>'
                       f'<td class="r">{ll3(c["floor"])}</td><td class="r">{ll3(c["luck"])}</td><td class="r">{ll3(c["elo"])}</td></tr>')
    wtr = []
    for key, lab in (("plug_in_floor_logloss", "Plug-in floor, log loss"), ("points_share_sd_points", "Spread of the points share (SD, points)"),
                     ("won_with_fewer_points_pct", "Matches won with fewer points (%)"), ("tiebreaks_per_match", "Tiebreaks per match"),
                     ("break_points_per_match", "Break points per match")):
        vals = []
        for t in TOUR:
            for w in ("real", "twin", "replay_at_measured_rates"):
                v = fit_world[w][t][key]
                vals.append(f'<td class="r">{v:.3f}</td>' if key in ("plug_in_floor_logloss", "tiebreaks_per_match") else f'<td class="r">{v:.2f}</td>')
        wtr.append(f'<tr><td>{esc(lab)}</td>{"".join(vals)}</tr>')
    b3, b5 = cell("atp", win_all["atp"], "best_of", 3), cell("atp", win_all["atp"], "best_of", 5)
    sh = {t: {k: 100 * v / (1000 * coin) for k, v in (("known", split[2 * i + 1]["known"]), ("day", split[2 * i + 1]["day"]),
                                                       ("luck", split[2 * i + 1]["luck"]))} for i, t in enumerate(TOUR)}
    parts.append(f'''    <div class="sub">
      <h3>3. The randomness floor</h3>
      <div class="prose">
        <p>For each match, the iid model gives the chance that a player wins from the two players' serve rates in that match, with the
        match's format and its deciding-set rule. That is the <b>plug-in floor</b>: roughly the best anyone could do knowing how each
        player would play that day. <span class="kind">Observed</span>On the 2022–2026 matches with closing odds it scores
        {ll3(H["atp"]["floor"])} for the men and {ll3(H["wta"]["floor"])} for the women, against {ll3(H["atp"]["market"])} and
        {ll3(H["wta"]["market"])} for the market and {ll3(H["atp"]["elo"])} and {ll3(H["wta"]["elo"])} for surface Elo. Taken at face value it
        splits a coin's uncertainty into {mm(split[0]["known"])} milli-log-loss the market knew before the match,
        {mm(split[0]["day"])} for how the players played on the day, and {mm(split[0]["luck"])} of scoring luck (men).</p>
        <p><span class="kind">Inferred</span>The plug-in floor is optimistic, more than "rough" allows. The rates are measured on the very
        points that decided the match, so a player who won the match by luck also shows a higher rate; as a forecast of the real result
        the plug-in chances are far too timid, and refitting them needs their log-odds multiplied by {slope["atp"]["slope"]:.2f} (men)
        and {slope["wta"]["slope"]:.2f} (women). The pure-luck replay shows the same: its plug-in chances need {slope["atp"]["twin_slope"]:.2f}
        and {slope["wta"]["twin_slope"]:.2f}, and its own plug-in floor, {ll3(H["atp"]["twin_plugin"])} and {ll3(H["wta"]["twin_plugin"])},
        is close to the real one. In the replay the true rates are known: a forecaster who knew them would score
        {ll3(H["atp"]["luck"])} and {ll3(H["wta"]["luck"])}. That is the better floor. With it, of a coin's {1000 * coin:.0f}
        milli-log-loss the closing odds remove {mm(split[1]["known"])} ({pct(sh["atp"]["known"], 0)}), knowing how each player would play
        that day would remove {mm(split[1]["day"])} more ({pct(sh["atp"]["day"], 0)}), and {mm(split[1]["luck"])} ({pct(sh["atp"]["luck"], 0)})
        is scoring luck no forecast can remove (men; women {pct(sh["wta"]["known"], 0)}, {pct(sh["wta"]["day"], 0)} and
        {pct(sh["wta"]["luck"], 0)}).</p>
        <p><span class="kind">Observed</span>Longer matches hold less luck: on the men's matches with odds of {win_all["atp"].replace("-", "–")},
        the corrected floor is {ll3(b5["luck"])} at best of five against {ll3(b3["luck"])} at best of three, and the market
        {ll3(b5["market"])} against {ll3(b3["market"])}.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Where a match's uncertainty lies</h3><p>A coin's log loss of {coin:.3f} split three ways, milli-log-loss;
        matches with closing odds, 2022–2026</p></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-2)"></span>Known before the match (the closing odds)</span>
          <span class="key"><span class="sw-rect" style="background:var(--series-1)"></span>How each player played on the day</span>
          <span class="key"><span class="sw-rect" style="background:var(--axis-ink)"></span>Scoring luck</span>
        </div>
        <div class="chart-pair" id="s2-split"></div>
        <p class="note-small">The plug-in floor feeds the iid model the rates measured in the match; the corrected floor is the log loss of a
        forecaster who knew each player's true rates, from the pure-luck replay.</p>
        <details class="twin"><summary>Show the floors as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Years</th><th>Best of</th><th>Matches</th><th class="r">Number</th><th class="r">Plug-in floor</th>
          <th class="r">Corrected floor</th><th class="r">Replay's plug-in</th><th class="r">Surface Elo</th><th class="r">Market</th></tr></thead>
          <tbody>{"".join(ftr)}</tbody></table></div></details>
        <details class="twin"><summary>By level, every evaluation match</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Tour</th><th>Level</th><th class="r">Matches</th><th class="r">Plug-in floor</th><th class="r">Corrected floor</th>
          <th class="r">Surface Elo</th></tr></thead><tbody>{"".join(ltr)}</tbody></table></div>
          <p class="note-small">* under 300 matches: directional only.</p></details>
        <details class="twin"><summary>Does the replay look like the real matches?</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th></th><th class="r">ATP real</th><th class="r">Replay</th><th class="r">At measured rates</th>
          <th class="r">WTA real</th><th class="r">Replay</th><th class="r">At measured rates</th></tr></thead>
          <tbody>{"".join(wtr)}</tbody></table></div>
          <p class="note-small">"At measured rates" replays each match at the rates measured in it, without allowing for their noise: its matches
          are more lopsided than the real ones, which is why the replay draws true rates instead.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 4. persistence
    persist = {t: {str(h): [{"key": k, "label": lab, "real": [pers[(t, h, k)]["r_mean"], pers[(t, h, k)]["r_ci_lo"], pers[(t, h, k)]["r_ci_hi"]],
                             "luck": [pers[(t, h, k)]["luck_r_mean"], pers[(t, h, k)]["luck_r_min"], pers[(t, h, k)]["luck_r_max"]],
                             "players": pers[(t, h, k)]["players"]} for k, lab in MEASURES]
                   for h in (10, 25, 50)} for t in TOUR}
    ptr = "".join(f'<tr><td>{TOUR[t]}</td><td class="r">{h}</td><td>{esc(lab)}</td><td class="r">{n(pers[(t, h, k)]["players"])}</td>'
                  f'<td class="r">{r2(pers[(t, h, k)]["r_mean"])}</td><td class="r">{r2(pers[(t, h, k)]["r_ci_lo"])} to {r2(pers[(t, h, k)]["r_ci_hi"])}</td>'
                  f'<td class="r">{r2(pers[(t, h, k)]["luck_r_mean"])}</td><td class="r">{r2(pers[(t, h, k)]["luck_r_min"])} to {r2(pers[(t, h, k)]["luck_r_max"])}</td></tr>'
                  for t in TOUR for h in (10, 25, 50) for k, lab in MEASURES)
    pb50 = {t: pers[(t, 50, "bp_both_over")] for t in TOUR}
    ps50 = {t: pers[(t, 50, "bp_saved_over")] for t in TOUR}
    tb50 = {t: pers[(t, 50, "tb_over")] for t in TOUR}
    sb = 2 * pb50["atp"]["r_mean"] / (1 + pb50["atp"]["r_mean"])
    parts.append(f'''    <div class="sub">
      <h3>4. Does it carry over?</h3>
      <div class="prose">
        <p>Each player's matches were split into two random halves ({r["d_persistence"]["splits"]} times), and each measure correlated across players
        between one half and the other. <span class="kind">Observed</span>With at least 25 matches in each half, serve points won correlate at
        {s25["atp"]["r_mean"]:.2f} (men) and {s25["wta"]["r_mean"]:.2f} (women): a stable trait. Break points won above expectation, serving and
        returning together: {r2(p25["atp"]["r_mean"])} and {r2(p25["wta"]["r_mean"])}; tiebreaks: {r2(pers[("atp", 25, "tb_over")]["r_mean"])} and
        {r2(pers[("wta", 25, "tb_over")]["r_mean"])}. Pure luck ({r["d_persistence"]["twin_replays"]} replays) gives
        {r2(p25["atp"]["luck_r_mean"])} and {r2(p25["wta"]["luck_r_mean"])} for break points, {r2(pers[("atp", 25, "tb_over")]["luck_r_mean"])} and
        {r2(pers[("wta", 25, "tb_over")]["luck_r_mean"])} for tiebreaks.</p>
        <p><span class="kind">Inferred</span>For the women nothing can be told apart from luck. For the men a small part of break-point play
        does persist: with at least 50 matches in each half, {r2(pb50["atp"]["r_mean"])} (95% range {r2(pb50["atp"]["r_ci_lo"])} to
        {r2(pb50["atp"]["r_ci_hi"])}), saves alone {r2(ps50["atp"]["r_mean"])}, against {r2(pb50["atp"]["luck_r_mean"])} in the replays. On a
        hundred-match record that is about {pct(100 * sb, 0)} signal and the rest luck. Tiebreak over-performance, {r2(tb50["atp"]["r_mean"])}
        at 50 matches a half, is not clearly above luck. Near-zero persistence means luck, which cannot be a pre-match feature; break-point
        record could only enter heavily shrunk.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Split-half correlation of each measure</h3><p>Dots: real matches with a 95% range, and the mean of the
        pure-luck replays with their spread; players with at least the chosen number of matches in each half</p></div>
        <div class="controls"><span>Matches in each half, at least:</span><div class="seg" role="group" aria-label="Matches in each half">
          <button type="button" data-half="10" aria-pressed="false">10</button>
          <button type="button" data-half="25" aria-pressed="true">25</button>
          <button type="button" data-half="50" aria-pressed="false">50</button></div></div>
        <div class="legend" aria-hidden="true">
          <span class="key"><span class="sw-rect" style="background:var(--series-1);border-radius:6px"></span>Real matches</span>
          <span class="key"><span class="sw-rect" style="background:var(--axis-ink);border-radius:6px"></span>Pure-luck replays</span>
        </div>
        <div class="chart-pair" id="s2-persist"></div>
        <p class="note-small">* above expectation: won minus what the match's serve rates predict, per break point or tiebreak played.</p>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th class="r">Matches a half</th><th>Measure</th><th class="r">Players</th><th class="r">Correlation</th>
          <th class="r">95% range</th><th class="r">Pure luck</th><th class="r">Replays' spread</th></tr></thead>
          <tbody>{ptr}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 5. components
    compd = {t: {s: [{"key": k, "label": lab, "share": comp[(t, s)][f"variance_share_{k}_pct"],
                      "points": comp[(t, s)][f"winner_{k}_points"]} for k, lab in COMPONENTS]
                 for s in ("all", "Hard", "Clay", "Grass") if (t, s) in comp} for t in TOUR}
    etr = []
    for t in TOUR:
        for s in ("all", "Hard", "Clay", "Grass", "Carpet"):
            x = comp.get((t, s))
            if not x:
                continue
            etr.append(f'<tr><td>{TOUR[t]}</td><td>{esc("All" if s == "all" else s)}{"*" if x["directional_only"] else ""}</td>'
                       f'<td class="r">{n(x["matches"])}</td><td class="r">{x["winner_edge_points"]:.2f}</td>'
                       + "".join(f'<td class="r">{x[f"winner_{k}_points"]:.2f} · {x[f"variance_share_{k}_pct"]:.1f}%</td>' for k, _ in COMPONENTS)
                       + f'<td class="r">{x["regression_r2"]:.3f}</td></tr>')
    ca, cw = comp[("atp", "all")], comp[("wta", "all")]
    parts.append(f'''    <div class="sub">
      <h3>5. Which points make the edge</h3>
      <div class="prose">
        <p>A player wins points on serve and on return. But a player's return points against the first serve are the opponent's
        first-serve points lost, so in a match serving well and returning well are one contest seen from either side, and the parts
        below are the two players' difference on each kind of point. The points edge (share minus 50%) splits exactly into six parts:
        <b>aces</b>; <b>first serves in play</b> (points that start with a first serve in that is not an ace); <b>first serves in</b>
        (landing more first serves, which win more often than second serves); <b>second serves in play</b>; <b>double faults</b>; and
        <b>serve-point count</b> (who served more points).</p>
        <p><span class="kind">Observed</span>Men's winners take {ca["winner_edge_points"]:.1f} points more per 100 played than an even share. Of
        these, {ca["winner_first_play_points"]:.1f} come from first serves in play, {ca["winner_second_play_points"]:.1f} from second serves in
        play, {ca["winner_ace_points"]:.1f} from aces, {ca["winner_double_faults_points"]:.1f} from double faults and
        {ca["winner_first_in_points"]:.1f} from first serves in; the serve-point count takes {abs(ca["winner_serve_count_points"]):.1f} away, as a
        winner's service games are shorter. Across matches, first serves in play account for {ca["variance_share_first_play_pct"]:.0f}% of the
        variation in the points edge, second serves in play {ca["variance_share_second_play_pct"]:.0f}%, aces {ca["variance_share_ace_pct"]:.0f}%
        (grass {comp[("atp", "Grass")]["variance_share_ace_pct"]:.0f}%, clay {comp[("atp", "Clay")]["variance_share_ace_pct"]:.0f}%), double faults
        {ca["variance_share_double_faults_pct"]:.0f}% and first serves in {ca["variance_share_first_in_pct"]:.0f}% (women:
        {cw["variance_share_first_play_pct"]:.0f}%, {cw["variance_share_second_play_pct"]:.0f}%, {cw["variance_share_ace_pct"]:.0f}%,
        {cw["variance_share_double_faults_pct"]:.0f}% and {cw["variance_share_first_in_pct"]:.0f}%).</p>
        <p><span class="kind">Inferred</span>The edge is made in the exchange once the serve is in play, far more than by aces, double faults or
        the first-serve percentage. A regression of the points share on the six differences explains {100 * ca["regression_r2"]:.1f}% of its
        variation and apportions it alike (the table). Aces are counted against first serves: the source does not say which serve an ace came
        on{f", and {pbp['file_notes']['aces_on_second_serve_pct']:.1f}% come on second serves in the Grand Slam point-by-point files that record it" if pbp else ""}.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Share of the points edge's variation, by part</h3><p>Percent; the serve-point count runs against the edge</p></div>
        <div class="controls"><span>Surface:</span><div class="seg" role="group" aria-label="Surface">
          <button type="button" data-surface="all" aria-pressed="true">All</button>
          <button type="button" data-surface="Hard" aria-pressed="false">Hard</button>
          <button type="button" data-surface="Clay" aria-pressed="false">Clay</button>
          <button type="button" data-surface="Grass" aria-pressed="false">Grass</button></div></div>
        <div class="chart-pair" id="s2-comp"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Surface</th><th class="r">Matches</th><th class="r">Winners' edge</th>
          {"".join(f'<th class="r">{esc(lab)}</th>' for _, lab in COMPONENTS)}<th class="r">Regression R²</th></tr></thead>
          <tbody>{"".join(etr)}</tbody></table></div>
          <p class="note-small">Each part: winners' points per 100 played · share of the variation. * under 300 matches: directional only.</p></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 6. match impact
    order = [k for k in RATE_WORDS]
    imp_d = {t: [{"key": k, "label": RATE_WORDS[k], "all": imp[(t, k)]["all_impact_milli"],
                  "defined": imp[(t, k)].get("defined_impact_milli"), "defined_pct": imp[(t, k)]["defined_pct"],
                  "ref": k == "iid_floor", "def": k == "sets_won"} for k in order if (t, k) in imp] for t in TOUR}
    itr = "".join(f'<tr><td>{TOUR[x["tour"]]}</td><td><code>{esc(x["rate"])}</code></td><td>{esc(x["words"])}</td>'
                  f'<td>{esc(x.get("same_as") or "")}</td><td class="r">{x["defined_pct"]:.1f}%</td><td class="r">{x["all_impact_milli"]:.1f}</td>'
                  f'<td class="r">{x["defined_impact_milli"]:.1f}</td></tr>' if x.get("defined_impact_milli") is not None else
                  f'<tr><td>{TOUR[x["tour"]]}</td><td><code>{esc(x["rate"])}</code></td><td>{esc(x["words"])}</td><td></td>'
                  f'<td class="r">{x["defined_pct"]:.1f}%</td><td class="r">{x["all_impact_milli"]:.1f}</td><td class="r">–</td></tr>'
                  for x in impact)
    ia = {k: imp[("atp", k)]["all_impact_milli"] for k in RATE_WORDS}
    iw = {k: imp[("wta", k)]["all_impact_milli"] for k in RATE_WORDS}
    tbd = imp[("atp", "tb_won")]
    parts.append(f'''    <div class="sub">
      <h3>6. Match impact of each statistic</h3>
      <div class="prose">
        <p>For every per-match rate in the Stage 0 table, a one-input logistic regression of the result on the difference between the two
        players in the same match, scored by how much better than a coin it does (milli-log-loss; {1000 * coin:.0f} is perfect). This is the table
        the study's summary will chart (<code>stage2_match_impact.csv</code>). <span class="kind">Observed</span>Sets won decides the match by
        definition. Then games won ({mm(ia["games_won"])} men, {mm(iw["games_won"])} women), total points won ({mm(ia["tpw"])}, {mm(iw["tpw"])}),
        the hold rate ({mm(ia["hold"])}, {mm(iw["hold"])}), serve points won ({mm(ia["spw"])}, {mm(iw["spw"])}), first-serve points won
        ({mm(ia["first_won"])}, {mm(iw["first_won"])}) and second-serve points won ({mm(ia["second_won"])}, {mm(iw["second_won"])}). Aces
        ({mm(ia["ace"])}, {mm(iw["ace"])}), double faults ({mm(ia["df"])}, {mm(iw["df"])}) and first serves in ({mm(ia["first_in"])},
        {mm(iw["first_in"])}) say little about who won. Tiebreaks won scores {mm(ia["tb_won"])} over every match but {mm(tbd["defined_impact_milli"])}
        on the {pct(tbd["defined_pct"], 0)} of men's matches that had a tiebreak.</p>
        <p>A rate and its mirror are the same number seen from the other player: a player's return points won are the opponent's serve points
        lost, the break rate is the opponent's hold rate turned over, and break points converted are the opponent's saves turned over. Each pair
        is shown once.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>How well each statistic, A minus B in the same match, separates winner from loser</h3><p>Milli-log-loss
        better than a coin; every completed match with a box score (a rate missing for a player counts as no difference)</p></div>
        <div class="chart-pair" id="s2-impact"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th>Rate</th><th>What it is</th><th>Same as</th><th class="r">Defined in</th><th class="r">Every match</th>
          <th class="r">Where defined</th></tr></thead><tbody>{itr}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ 7. big points, point by point (optional part)
    pbp_file = study_dir / "stage2_pbp_results.json"
    if pbp_file.exists():
        parts.append(pbp_section(load(study_dir, "stage2_pbp_results.json")))

    # ------------------------------------------------------------------ how it was built and checked
    pop = "".join(f'<tr><td>{esc(s["step"])}</td><td class="r">{n(s["atp"])}</td><td class="r">{n(s["wta"])}</td></tr>' for s in steps)
    rc = r["rules_check"]
    tbm = rc["tiebreak_loser_points_mean_by_rule"]
    bo = r["population"]["best_of_from_score"]
    blank = r["population"]["stage0_kept_box_with_a_blank_count"]
    rules_used = {(x["tour"], x["rule"]): x["matches"] for x in r["population"]["deciding_rules"]}
    parts.append(f'''    <div class="sub">
      <h3>How Stage 2 was built and checked</h3>
      <ul class="plain">
        <li><b>The matches.</b> Every step from Stage 0's evaluation matches to the analysed ones:
        <div class="table-wrap"><table class="num"><thead><tr><th>Step</th><th class="r">ATP</th><th class="r">WTA</th></tr></thead><tbody>{pop}</tbody></table></div></li>
        <li><b>Best of three or five</b> is read from the score (the winner's sets). The source records {bo["matches"]} men's Wimbledon matches of the last
        qualifying round ({", ".join(str(x["year"]) for x in bo["by_event"])}) as best of three although their scores show best of five.</li>
        <li><b>Grand Slam deciding sets.</b> The rule for each Slam, draw and year is in <code>stage2_slam_final_set_rules.csv</code>, with its source:
        advantage sets at the Australian Open to 2018, Roland Garros to 2021 and Wimbledon to 2018; a 10-point tiebreak at 6-6 at the Australian Open
        from 2019; a 7-point tiebreak at 12-12 at Wimbledon in 2019 and 2021; a 7-point tiebreak at 6-6 at the US Open to 2021; and a 10-point
        tiebreak at 6-6 at all four from 2022. Two qualifying rules were found in the scores, not in a published source: Roland Garros qualifying
        played 7-point deciding-set tiebreaks from 2017 (a 2017 draw sheet shows one won 8-6), and the Australian Open qualifying had deciding-set
        tiebreaks in 2018 (their length unknown; 7 points assumed). Against every completed Grand Slam score since 2010 the rules hold in all
        {rc["cells"]} Slam, draw and year cells; deciding-set tiebreaks average {tbm["TB7@6"]:.1f} points for the loser under 7-point rules and
        {tbm["TB10@6"]:.1f} under 10-point ones. No simplification was needed: the model plays each rule exactly
        ({n(rules_used.get(("atp", "ADV"), 0) + rules_used.get(("wta", "ADV"), 0))} analysed matches were played under an advantage deciding set).</li>
        <li><b>The iid model</b> (<code>stage2_iid.py</code>) is tested against a brute-force reading of the scoring rules, against itself with the
        server reversed (who serves first does not change the chance of winning a tiebreak or a set, so sets are independent draws), and against
        a point-by-point simulation of the same rules.</li>
        <li><span class="flag">A Stage 0 problem.</span> {"One" if blank["matches"] == 1 else n(blank["matches"])} Tennis My Life box
        score{"" if blank["matches"] == 1 else "s"} that Stage 0 kept as complete ({esc(", ".join(blank["examples"]))}) {"has" if blank["matches"] == 1 else "have"}
        a break-point count that does not read as a number; Stage 2 leaves {"it" if blank["matches"] == 1 else "them"} out. Reported, not fixed.</li>
      </ul>
    </div>''')

    data = {"tours": [[t, TOUR_LONG[t]] for t in TOUR], "curve": curve, "curve_range": [CURVE_LO, CURVE_HI], "beyond": beyond,
            "split": split, "coin": coin,
            "persist": persist, "comp": compd, "impact": imp_d}
    return {"html": "\n".join(parts), "data": data, "script": JS}


PBP_MEASURES = [("serve_rate", "Serve points won (yardstick)"), ("return_rate", "Return points won (yardstick)"),
                ("clutch_serve", "Big points on serve"), ("clutch_return", "Big points on return"), ("clutch", "Big points, both")]


def pbp_section(p: dict) -> str:
    """The optional part: importance-weighted play in the Grand Slam point-by-point files (stage2_pbp_results.json)."""
    mt = p["matches"]
    imp = {x["tour"]: x for x in p["importance"]}
    cm = {x["tour"]: x for x in p["clutch_mean"]}
    cl = {x["tour"]: x for x in p["pure_luck"]["clutch_mean"]}
    reg = {(x["tour"], x["model"]): x for x in p["regressions"]}
    regl = {(x["tour"], x["model"]): x for x in p["pure_luck"]["regressions"]}
    pers = {(x["tour"], x["min_matches_per_half"], x["measure"]): x for x in p["persistence"]}
    rate = p["serve_rate_used"]
    beyond = {t: cm[t]["serve"]["mean_points"] - cl[t]["serve"]["mean_points"] for t in TOUR}
    rows = []
    for t in TOUR:
        for h in (5, 10, 20):
            for k, lab in PBP_MEASURES:
                x = pers[(t, h, k)]
                rows.append(f'<tr><td>{TOUR[t]}</td><td class="r">{h}</td><td>{esc(lab)}</td><td class="r">{n(x["players"])}</td>'
                            f'<td class="r">{r2(x["r_mean"])}</td><td class="r">{r2(x["r_ci_lo"])} to {r2(x["r_ci_hi"])}</td>'
                            f'<td class="r">{r2(x["luck_r_mean"])}</td><td class="r">{r2(x["luck_r_min"])} to {r2(x["luck_r_max"])}</td></tr>')
    r10 = {t: {k: pers[(t, 10, k)] for k, _ in PBP_MEASURES} for t in TOUR}
    gain = {t: reg[(t, "points + clutch")]["gain_over_points_milli"]["milli"] for t in TOUR}
    gainl = {t: regl[(t, "points + clutch")]["gain_over_points_milli"]["milli"] for t in TOUR}
    ratio_bp = {t: imp[t]["break_point_mean"] / imp[t]["mean"] for t in TOUR}
    ratio_tb = {t: imp[t]["tiebreak_mean"] / imp[t]["mean"] for t in TOUR}
    return f'''    <div class="sub">
      <h3>7. Big points, point by point (Grand Slams, the optional part)</h3>
      <div class="prose">
        <p>Jeff Sackmann's Grand Slam point-by-point files record who served and who won every point of most main-draw singles
        matches of 2011–2024. Each match was replayed point by point and checked against the file (the set, the games where written,
        the score in every game, and who serves): {n(mt["atp"]["kept"])} of {n(mt["atp"]["in_files"])} men's and {n(mt["wta"]["kept"])} of
        {n(mt["wta"]["in_files"])} women's matches pass ({n(mt["atp"]["points_kept"] + mt["wta"]["points_kept"])} points); most of the rest end
        before the match does (retirements, or files cut short). Each point gets an <b>importance</b>: how much winning it rather than losing
        it raises the chance of winning the match, from the score alone, with both players at their tour's average serve rate in these
        files ({pct(100 * rate["atp"])} men, {pct(100 * rate["wta"])} women). <b>Big-point play</b> ("clutch") is a player's importance-weighted
        share of points won minus their plain share, on serve and on return, in the same match. Every result is set beside pure-luck
        replays of the same matches, point by point.</p>
        <p><span class="kind">Observed</span>Importance is concentrated: the most important tenth of points carries
        {pct(imp["atp"]["top10pct_share_pct"], 0)} of all importance (men) and {pct(imp["wta"]["top10pct_share_pct"], 0)} (women). Break points are
        {pct(imp["atp"]["break_point_share_of_points_pct"])} of men's points and {pct(imp["atp"]["break_point_share_of_importance_pct"])} of the
        importance, {ratio_bp["atp"]:.1f} times an average point; tiebreak points {ratio_tb["atp"]:.1f} times.</p>
        <p><span class="kind">Observed</span>On serve, players win slightly fewer of the big points than of their serve points overall:
        {mm(cm["atp"]["serve"]["mean_points"], True)} points (men) and {mm(cm["wta"]["serve"]["mean_points"], True)} (women). Pure luck gives
        {mm(cl["atp"]["serve"]["mean_points"], True)} and {mm(cl["wta"]["serve"]["mean_points"], True)}, so the real shortfall beyond luck is
        {mm(beyond["atp"], True)} and {mm(beyond["wta"], True)}: the same small pressure effect as the break points. Adding the big-point
        difference to the points share improves the log loss by {mm(gain["atp"])} milli-log-loss for the men and {mm(gain["wta"])} for the
        women; pure luck gives {mm(gainl["atp"])} and {mm(gainl["wta"])}. As with tiebreaks, big points decide close matches, about as much as
        luck predicts.</p>
        <p><span class="kind">Inferred</span>Does big-point play carry over? On serve, no more than luck. On return it does: with at least
        10 matches in each half, {r2(r10["atp"]["clutch_return"]["r_mean"])} for the men (95% range {r2(r10["atp"]["clutch_return"]["r_ci_lo"])}
        to {r2(r10["atp"]["clutch_return"]["r_ci_hi"])}) and {r2(r10["wta"]["clutch_return"]["r_mean"])} for the women
        ({r2(r10["wta"]["clutch_return"]["r_ci_lo"])} to {r2(r10["wta"]["clutch_return"]["r_ci_hi"])}), against {r2(r10["atp"]["clutch_return"]["luck_r_mean"])}
        and {r2(r10["wta"]["clutch_return"]["luck_r_mean"])} in the replays. This is the one place in Stage 2 where play on big points looks
        like more than luck. It rests on {n(r10["atp"]["clutch_return"]["players"])} men and {n(r10["wta"]["clutch_return"]["players"])} women with
        many Grand Slam matches, and it could also come from form that swings within matches, which the replays do not model. Pure luck itself
        makes big-point play look persistent for players with many matches, because they win most of them; that is why the replays, not
        zero, are the benchmark.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Split-half correlation of big-point play</h3><p>Real matches and pure-luck replays; players with at least the
        given number of Grand Slam matches in each half</p></div>
        <details class="twin" open><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th>Tour</th><th class="r">Matches a half</th><th>Measure</th><th class="r">Players</th><th class="r">Correlation</th>
          <th class="r">95% range</th><th class="r">Pure luck</th><th class="r">Replays' spread</th></tr></thead>
          <tbody>{"".join(rows)}</tbody></table></div></details>
      </div>
    </div>'''


JS = r"""
(function () {
  const D = window.REPORT["anatomy"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const fmtN = v => Math.round(v).toLocaleString("en-US");
  const f1 = v => (v < 0 ? "−" : "") + Math.abs(v).toFixed(1);
  const f2 = v => (v < 0 ? "−" : "") + Math.abs(v).toFixed(2);
  const bar = (x0, x1, y, h, r) => {          // a horizontal bar from x0 to x1, rounded at the data end only
    const right = x1 >= x0, len = Math.abs(x1 - x0), rr = Math.min(r, len / 2, h / 2);
    if (len < 0.5) return `M${x0},${y} H${x0 + (right ? 0.5 : -0.5)} V${y + h} H${x0} Z`;
    return right
      ? `M${x0},${y} H${x1 - rr} Q${x1},${y} ${x1},${y + rr} V${y + h - rr} Q${x1},${y + h} ${x1 - rr},${y + h} H${x0} Z`
      : `M${x0},${y} H${x1 + rr} Q${x1},${y} ${x1},${y + rr} V${y + h - rr} Q${x1},${y + h} ${x1 + rr},${y + h} H${x0} Z`;
  };
  const tip = (node, rows) => window.reportTip.bind(node, rows);

  // ---------------------------------------------------------------- 1. chance of winning by points share
  (function curve() {
    const host = document.getElementById("s2-curve");
    D.tours.forEach(([t, name]) => {
      const series = D.curve[t];
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, H = 280, L = 44, R = 12, T = 10, B = 34;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": share of matches won against the share of points won, real matches and the pure-luck replay; the table below holds the numbers" });
      const [lo, hi] = D.curve_range;
      const x = v => L + (W - L - R) * (v - lo) / (hi - lo);
      const y = v => T + (H - T - B) * (100 - v) / 100;
      for (let v = lo; v <= hi; v += 2) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 50 ? "ref" : "grid" }, svg);
        S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v + "%";
      }
      for (let v = 0; v <= 100; v += 25) {
        S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: v === 0 ? "axis" : "grid" }, svg);
        S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = v + "%";
      }
      S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "share of all points won";
      [...series].sort((a, b) => (a.key === "luck" ? -1 : 0) - (b.key === "luck" ? -1 : 0)).forEach(s => {
        const d = s.pts.map((p, i) => (i ? "L" : "M") + x(p[0]).toFixed(1) + "," + y(p[1]).toFixed(1)).join(" ");
        S("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      });
      const cross = S("line", { x1: 0, x2: 0, y1: T, y2: H - B, class: "cross", visibility: "hidden" }, svg);
      const xs = [...new Set(series.flatMap(s => s.pts.map(p => p[0])))].sort((a, b) => a - b);
      const step = (W - L - R) / (hi - lo);
      xs.forEach(v => {
        const hit = S("rect", { x: x(v) - step / 2, y: T, width: step, height: H - T - B, class: "hit", tabindex: "0" }, svg);
        tip(hit, () => {
          cross.setAttribute("x1", x(v)); cross.setAttribute("x2", x(v)); cross.setAttribute("visibility", "visible");
          const out = [v + "% of points won"];
          series.forEach(s => { const p = s.pts.find(q => q[0] === v); if (p) out.push(p[1].toFixed(1) + "% won  " + s.label + " (" + fmtN(p[2]) + ")"); });
          return out;
        });
        hit.addEventListener("pointerleave", () => cross.setAttribute("visibility", "hidden"));
        hit.addEventListener("blur", () => cross.setAttribute("visibility", "hidden"));
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();

  // ---------------------------------------------------------------- 2. what break points and tiebreaks add
  (function beyond() {
    const host = document.getElementById("s2-beyond");
    let max = 0;
    D.tours.forEach(([t]) => D.beyond[t].forEach(c => { max = Math.max(max, c.real.hi, c.luck.hi); }));
    const top = Math.ceil(max / 10) * 10;
    D.tours.forEach(([t, name]) => {
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, L = 96, R = 56, T = 6, B = 26, barH = 14, gap = 2, groupH = 2 * barH + gap + 18;
      const H = T + D.beyond[t].length * groupH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": milli-log-loss gained by adding break points, tiebreaks or both to the points share, real and pure luck; the table below holds the numbers" });
      const x = v => L + (W - L - R) * Math.max(0, v) / top;
      for (let v = 0; v <= top; v += 10) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
        S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v;
      }
      D.beyond[t].forEach((c, i) => {
        const y0 = T + i * groupH + 9;
        S("text", { x: L - 8, y: y0 + barH + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.cat;
        [["real", "var(--series-1)", "Real matches"], ["luck", "var(--axis-ink)", "Pure-luck replay"]].forEach(([k, color, lab], j) => {
          const g = c[k], yy = y0 + j * (barH + gap);
          const p = S("path", { d: bar(x(0), x(g.milli), yy, barH, 4), fill: color, class: "mark", tabindex: "0" }, svg);
          S("line", { x1: x(g.lo), x2: x(g.hi), y1: yy + barH / 2, y2: yy + barH / 2, stroke: "var(--ink-2)", "stroke-width": 1 }, svg);
          S("text", { x: x(Math.max(g.milli, g.hi)) + 6, y: yy + barH - 3, class: "val" }, svg).textContent = f1(g.milli);
          const hit = S("rect", { x: 0, y: yy - 1, width: W, height: barH + 2, class: "hit" }, svg);
          const rows = () => [f1(g.milli) + " milli-log-loss better", c.cat + " · " + lab + " · " + name,
            "95% range " + f1(g.lo) + " to " + f1(g.hi) + " · " + fmtN(g.n) + " matches"];
          tip(hit, rows); tip(p, rows);
        });
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();

  // ---------------------------------------------------------------- 3. where a match's uncertainty lies
  (function split() {
    const host = document.getElementById("s2-split");
    const total = 1000 * D.coin;
    const segs = [["known", "var(--series-2)", "Known before the match"], ["day", "var(--series-1)", "How each played on the day"],
                  ["luck", "var(--axis-ink)", "Scoring luck"]];
    D.tours.forEach(([t, name]) => {
      const rows = D.split.filter(r => r.tour === t);
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, L = 2, R = 10, T = 4, B = 26, barH = 22, rowH = 52;
      const H = T + rows.length * rowH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": a coin's log loss split into what the closing odds know, how each player played on the day, and scoring luck, with the plug-in and the corrected floor; the tables below hold the numbers" });
      const x = v => L + (W - L - R) * v / total;
      for (let v = 0; v <= total; v += 100) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
        S("text", { x: x(v), y: H - B + 16, "text-anchor": v === 0 ? "start" : "middle" }, svg).textContent = v;
      }
      rows.forEach((row, i) => {
        const yl = T + i * rowH + 13, y0 = yl + 7;
        S("text", { x: L, y: yl, class: "lab" }, svg).textContent = row.kind + " (" + row.floor.toFixed(3) + ")";
        let acc = 0;
        segs.forEach(([k, color, lab], j) => {
          const v = row[k], x0 = x(acc) + (j ? 1 : 0), x1 = x(acc + v) - (j < segs.length - 1 ? 1 : 0);
          const d = j === segs.length - 1 ? bar(x0, x1, y0, barH, 4) : `M${x0},${y0} H${x1} V${y0 + barH} H${x0} Z`;
          const p = S("path", { d, fill: color, class: "mark", tabindex: "0" }, svg);
          if (x1 - x0 > 30) S("text", { x: (x0 + x1) / 2, y: y0 + barH / 2 + 4, "text-anchor": "middle",
                                         style: "fill:#0b0b0b;font-size:12px;font-variant-numeric:tabular-nums" }, svg).textContent = Math.round(v);
          tip(p, () => [Math.round(v) + " milli-log-loss (" + (100 * v / total).toFixed(0) + "% of a coin's)", lab + " · " + name,
            row.kind + " " + row.floor.toFixed(3) + " · market " + row.market.toFixed(3)]);
          acc += v;
        });
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();

  // ---------------------------------------------------------------- 4. split-half correlations
  (function persist() {
    const host = document.getElementById("s2-persist");
    let half = "25";
    function draw() {
      host.replaceChildren();
      D.tours.forEach(([t, name]) => {
        const rows = D.persist[t][half];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        const W = 460, L = 170, R = 14, T = 6, B = 30, rowH = 30;
        const H = T + rows.length * rowH + B;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": split-half correlation of each measure, real and pure luck; the table below holds the numbers" });
        const lo = -0.2, hi = 1.0;
        const x = v => L + (W - L - R) * (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo);
        for (let v = -0.2; v <= 1.0001; v += 0.2) {
          const vv = Math.round(v * 10) / 10;
          S("line", { x1: x(vv), x2: x(vv), y1: T, y2: H - B, class: vv === 0 ? "ref" : "grid" }, svg);
          S("text", { x: x(vv), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = vv.toFixed(1);
        }
        S("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "correlation between the halves";
        rows.forEach((m, i) => {
          const yc = T + i * rowH + rowH / 2;
          S("text", { x: L - 8, y: yc + 4, "text-anchor": "end", class: "lab" }, svg).textContent = m.label;
          [["luck", "var(--axis-ink)", yc + 5], ["real", "var(--series-1)", yc - 5]].forEach(([k, color, yy]) => {
            const [v, a, b] = m[k];
            S("line", { x1: x(a), x2: x(b), y1: yy, y2: yy, stroke: color, "stroke-width": 1.5 }, svg);
            const dot = S("circle", { cx: x(v), cy: yy, r: 4.5, fill: color, stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
            const hit = S("rect", { x: L, y: yy - 6, width: W - L - R, height: 12, class: "hit" }, svg);
            const rowsFn = () => [(k === "real" ? "r = " : "mean r = ") + f2(v), m.label + " · " + name,
              (k === "real" ? "95% range " : "replays from ") + f2(a) + " to " + f2(b) + " · " + fmtN(m.players) + " players"];
            tip(hit, rowsFn); tip(dot, rowsFn);
          });
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    document.querySelectorAll('#anatomy [data-half]').forEach(b => b.addEventListener("click", () => {
      half = b.dataset.half;
      document.querySelectorAll('#anatomy [data-half]').forEach(o => o.setAttribute("aria-pressed", String(o === b)));
      draw();
    }));
    draw();
  })();

  // ---------------------------------------------------------------- 5. components of the points edge
  (function comp() {
    const host = document.getElementById("s2-comp");
    let surface = "all";
    function draw() {
      host.replaceChildren();
      let lo = 0, hi = 0;
      D.tours.forEach(([t]) => Object.values(D.comp[t]).forEach(rows => rows.forEach(c => { lo = Math.min(lo, c.share); hi = Math.max(hi, c.share); })));
      lo = Math.floor(lo / 10) * 10; hi = Math.ceil(hi / 10) * 10;
      D.tours.forEach(([t, name]) => {
        const rows = D.comp[t][surface];
        const box = el("div", "chart"); box.appendChild(el("h4", null, name));
        if (!rows) { box.appendChild(el("p", "note-small", "No matches on this surface.")); host.appendChild(box); return; }
        const W = 460, L = 150, R = 48, T = 6, B = 26, rowH = 30, barH = 16;
        const H = T + rows.length * rowH + B;
        const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
          "aria-label": name + ": share of the variation in the points edge from each part; the table below holds the numbers" });
        const x = v => L + (W - L - R) * (v - lo) / (hi - lo);
        for (let v = lo; v <= hi; v += 10) {
          S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
          if (v % 20 === 0) S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v + "%";
        }
        rows.forEach((c, i) => {
          const y0 = T + i * rowH + (rowH - barH) / 2;
          S("text", { x: L - 8, y: y0 + barH / 2 + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.label;
          const p = S("path", { d: bar(x(0), x(c.share), y0, barH, 4), fill: "var(--series-1)", class: "mark", tabindex: "0" }, svg);
          const right = c.share >= 0;
          S("text", { x: right ? x(c.share) + 6 : x(0) + 6, y: y0 + barH - 3, class: "val" }, svg).textContent = f1(c.share) + "%";
          const hit = S("rect", { x: 0, y: T + i * rowH, width: W, height: rowH, class: "hit" }, svg);
          const rowsFn = () => [f1(c.share) + "% of the variation", c.label + " · " + name + " · " + (surface === "all" ? "all surfaces" : surface),
            "winners: " + f2(c.points) + " points per 100 played"];
          tip(hit, rowsFn); tip(p, rowsFn);
        });
        box.appendChild(svg); host.appendChild(box);
      });
    }
    document.querySelectorAll('#anatomy [data-surface]').forEach(b => b.addEventListener("click", () => {
      surface = b.dataset.surface;
      document.querySelectorAll('#anatomy [data-surface]').forEach(o => o.setAttribute("aria-pressed", String(o === b)));
      draw();
    }));
    draw();
  })();

  // ---------------------------------------------------------------- 6. match impact
  (function impact() {
    const host = document.getElementById("s2-impact");
    const top = Math.ceil(1000 * D.coin / 100) * 100;
    const order = D.impact[D.tours[0][0]].filter(r => !r.ref).sort((a, b) => b.all - a.all).map(r => r.key).concat(["iid_floor"]);
    D.tours.forEach(([t, name]) => {
      const byKey = Object.fromEntries(D.impact[t].map(r => [r.key, r]));
      const rows = order.map(k => byKey[k]).filter(Boolean);
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 460, L = 210, R = 44, T = 6, B = 26, rowH = 24, barH = 14;
      const H = T + rows.length * rowH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": milli-log-loss better than a coin for each statistic's difference between the players; the table below holds the numbers" });
      const x = v => L + (W - L - R) * Math.max(0, v) / top;
      for (let v = 0; v <= top; v += 100) {
        S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
        if (v % 200 === 0) S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = v;
      }
      rows.forEach((c, i) => {
        const y0 = T + i * rowH + (rowH - barH) / 2;
        S("text", { x: L - 8, y: y0 + barH / 2 + 4, "text-anchor": "end", class: "lab" }, svg).textContent = c.label;
        const p = S("path", { d: bar(x(0), x(c.all), y0, barH, 4), fill: c.ref ? "var(--axis-ink)" : "var(--series-1)", class: "mark", tabindex: "0" }, svg);
        S("text", { x: x(c.all) + 6, y: y0 + barH - 3, class: "val" }, svg).textContent = Math.round(c.all);
        const hit = S("rect", { x: 0, y: T + i * rowH, width: W, height: rowH, class: "hit" }, svg);
        const rowsFn = () => {
          const out = [f1(c.all) + " milli-log-loss better than a coin", c.label + " · " + name];
          if (c.def) out.push("decides the match by definition");
          else if (c.ref) out.push("the iid model's chance from both serve rates, for reference");
          else if (c.defined != null && c.defined_pct < 99) out.push(f1(c.defined) + " on the " + c.defined_pct.toFixed(0) + "% of matches where it exists");
          return out;
        };
        tip(hit, rowsFn); tip(p, rowsFn);
      });
      box.appendChild(svg); host.appendChild(box);
    });
  })();
})();
"""
