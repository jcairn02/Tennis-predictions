"""Predictability diagnostic, the summary: the numbers the summary quotes, gathered from the stages' outputs.

1. The chart of persistence against match impact. Every per-match statistic that both tables hold is placed by how
   well a regular's season repeats (stage3_persistence.csv, all surfaces) against how much its in-match difference
   decides the match (stage2_match_impact.csv, best of three and five together), on every analysed match and on the
   matches where the statistic occurs. Each point gets a corner: trait (repeats and decides), style (repeats,
   decides little), luck (decides, does not repeat) or noise (neither).
2. The corners beside Stage 4's rows of the same statistic (stage4_results.json, its five forms), with the
   expectation each corner carries and where Stage 4 departs from it.
3. Every other number the summary and its plain-language opening quote, copied from the stages' JSON (and the
   Stage 4 audit's evidence) under the file they come from.

Nothing new is estimated: the join, the corner of each point, which corner rows Stage 4 found, and a few shares of
quoted numbers (each named where it is made). The two CSVs are checked against their stages' JSON first.

Reads data/studies/predictability_diagnostic/ (and its audit4/); writes summary_results.json and summary_chart.csv.
Run: ./python.sh src/eda/predictability_diagnostic/summary_results.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

AUDIT4 = C.OUT / "audit4"
OUT_JSON = C.OUT / "summary_results.json"
OUT_CSV = C.OUT / "summary_chart.csv"

TOURS = C.TOURS
# The statistics both tables hold (Stage 2 measured the raw rates only; Stage 3's two opponent-adjusted rates have
# no match impact and are carried beside the chart, not on it).
STATS = ["spw", "rpw", "tpw", "hold", "brk", "ace", "df", "first_in", "first_won", "second_won", "bp_saved", "bp_conv",
         "bp_faced_pg", "tb_won", "sets_won", "games_won"]
ADJUSTED = {"spw_adj": "spw", "rpw_adj": "rpw"}
LABEL = {"spw": "Serve points won", "rpw": "Return points won", "tpw": "Total points won", "hold": "Service games held",
         "brk": "Return games won (breaks)", "ace": "Aces per serve point", "df": "Double faults per serve point",
         "first_in": "First serves in", "first_won": "First-serve points won", "second_won": "Second-serve points won",
         "bp_saved": "Break points saved", "bp_conv": "Break points converted",
         "bp_faced_pg": "Break points faced per service game", "tb_won": "Tiebreaks won", "sets_won": "Sets won",
         "games_won": "Games won", "spw_adj": "Serve points won, opponent-adjusted",
         "rpw_adj": "Return points won, opponent-adjusted"}
SHORT = {"spw": "Serve points won", "rpw": "Return points won", "tpw": "Total points won", "hold": "Holds",
         "brk": "Breaks", "ace": "Aces", "df": "Double faults", "first_in": "First serves in",
         "first_won": "1st-serve points won", "second_won": "2nd-serve points won", "bp_saved": "Break points saved",
         "bp_conv": "Break points converted", "bp_faced_pg": "Break points faced", "tb_won": "Tiebreaks won",
         "sets_won": "Sets won", "games_won": "Games won"}
CORNERS = {"trait": "repeats and decides", "style": "repeats, decides little", "luck": "decides, does not repeat",
           "noise": "neither repeats nor decides"}
BASES = {"all": "every analysed match", "defined": "the matches where the statistic occurs"}
# The line for "decides", set here (Stage 3 set the line for "repeats" in advance): a quarter of a coin's log loss.
DECIDES_SHARE_OF_COIN = 0.25
FORMS = ["career", "52 weeks", "decayed", "surface", "adjusted"]
# Stage 4's own scale for the score alone (candidates.md, section 3), and what each corner leads one to expect.
ALONE_PREDICTS = ("moderate", "strong")
EXPECT = {"trait": {"alone": "moderate or strong", "elo": "a finding in at least one form"},
          "style": {"alone": "none or weak", "elo": "no finding"},
          "luck": {"alone": "none or weak", "elo": "no finding"},
          "noise": {"alone": "none or weak", "elo": "no finding"}}
LEADERS = 10


def load(name: str, folder: Path = C.OUT) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


def num(x):
    """A finite float, or None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def corner_of(reliability: float, impact: float, repeats_line: float, decides_line: float) -> str:
    repeats, decides = reliability >= repeats_line, impact >= decides_line
    return {(True, True): "trait", (True, False): "style", (False, True): "luck", (False, False): "noise"}[(repeats, decides)]


def borderline(lo: float | None, hi: float | None, line: float) -> bool:
    """The 95% range of the season's reliability holds the line, so the side of it is not settled."""
    return lo is not None and hi is not None and lo <= line <= hi


def check_csvs(persist: pd.DataFrame, impact: pd.DataFrame, s3: dict, s2: dict) -> dict:
    """The two CSVs the chart reads against the rows of their stages' JSON (the CSV keeps 6-7 significant digits)."""
    pj = pd.DataFrame(s3["persistence"]).merge(persist, on=["tour", "surface", "stat"], suffixes=("_j", "_c"))
    # best_of is "all", 3 or 5: a number in the JSON, text in the CSV's mixed column
    mj = (pd.DataFrame(s2["f_match_impact"]["rows"]).astype({"best_of": str})
          .merge(impact.astype({"best_of": str}), on=["tour", "best_of", "rate"], suffixes=("_j", "_c")))
    out = {"persistence_rows": [len(s3["persistence"]), len(persist), len(pj)],
           "match_impact_rows": [len(s2["f_match_impact"]["rows"]), len(impact), len(mj)]}
    for name, df, cols in (("persistence", pj, ["reliability_typical", "reliability_typical_lo", "reliability_typical_hi"]),
                           ("match_impact", mj, ["all_impact_milli", "defined_impact_milli", "defined_pct"])):
        out[f"{name}_largest_difference"] = float(max(np.nanmax(np.abs(df[c + "_j"].astype(float) - df[c + "_c"].astype(float)))
                                                      for c in cols))
    assert out["persistence_rows"][0] == out["persistence_rows"][1] == out["persistence_rows"][2]
    assert out["match_impact_rows"][0] == out["match_impact_rows"][1] == out["match_impact_rows"][2]
    assert out["persistence_largest_difference"] < 1e-6 and out["match_impact_largest_difference"] < 1e-9
    return out


def chart_points(persist: pd.DataFrame, impact: pd.DataFrame, repeats_line: float, decides_line: float) -> list[dict]:
    p = persist[persist["surface"] == "all"].set_index(["tour", "stat"])
    m = impact[impact["best_of"].astype(str) == "all"].set_index(["tour", "rate"])
    rows = []
    for t in TOURS:
        for s in STATS:
            a, b = p.loc[(t, s)], m.loc[(t, s)]
            rel, lo, hi = num(a["reliability_typical"]), num(a["reliability_typical_lo"]), num(a["reliability_typical_hi"])
            imp_all, imp_def = num(b["all_impact_milli"]), num(b["defined_impact_milli"])
            rows.append({
                "tour": t, "stat": s, "label": LABEL[s], "short": SHORT[s], "words": a["words"], "unit": a["unit"],
                "same_as": None if pd.isna(b["same_as"]) else b["same_as"],
                "reliability": rel, "reliability_lo": lo, "reliability_hi": hi, "verdict": a["verdict"],
                "verdict_firm": bool(a["verdict_firm"]), "typical_matches": num(a["typical_matches"]),
                "k_matches": num(a["k_matches"]), "year_to_year_r": num(a["year_to_year_r"]),
                "matches": int(b["matches"]), "defined": int(b["defined"]), "defined_pct": num(b["defined_pct"]),
                "impact_all": imp_all, "impact_defined": imp_def, "separates": bool(b["all_separates"]),
                # the same, as a share of a coin's log loss: how much of the doubt about who won it removes in the match
                "impact_share": imp_all / (1000 * np.log(2)), "impact_defined_share": imp_def / (1000 * np.log(2)),
                # the statistic's direction within a match: more of it goes with winning (+1) or losing (-1); sets won
                # separates the result completely (no coefficient), in the winning direction
                "in_match_sign": 1 if bool(b["all_separates"]) or num(b["all_coef"]) > 0 else -1,
                "corner_all": corner_of(rel, imp_all, repeats_line, decides_line),
                "corner_defined": corner_of(rel, imp_def, repeats_line, decides_line),
                "borderline": borderline(lo, hi, repeats_line)})
    return rows


def adjusted_points(persist: pd.DataFrame, repeats_line: float) -> list[dict]:
    p = persist[persist["surface"] == "all"].set_index(["tour", "stat"])
    out = []
    for t in TOURS:
        for s, raw in ADJUSTED.items():
            a, r = p.loc[(t, s)], p.loc[(t, raw)]
            out.append({"tour": t, "stat": s, "raw": raw, "label": LABEL[s], "reliability": num(a["reliability_typical"]),
                        "reliability_lo": num(a["reliability_typical_lo"]), "reliability_hi": num(a["reliability_typical_hi"]),
                        "raw_reliability": num(r["reliability_typical"]), "k_matches": num(a["k_matches"]),
                        "raw_k_matches": num(r["k_matches"]), "repeats": num(a["reliability_typical"]) >= repeats_line})
    return out


def gaps(points: list[dict], decides_line: float) -> list[dict]:
    """Per tour and basis: the statistics nearest the line for "decides" on either side. Any line between them
    gives the same corners."""
    out = []
    for t in TOURS:
        for basis in BASES:
            vals = [(p[f"impact_{basis}"], p["stat"]) for p in points if p["tour"] == t]
            below = max((v for v in vals if v[0] < decides_line), default=(None, None))
            above = min((v for v in vals if v[0] >= decides_line), default=(None, None))
            out.append({"tour": t, "basis": basis, "below_max": below[0], "below_stat": below[1],
                        "above_min": above[0], "above_stat": above[1]})
    return out


def corner_lists(points: list[dict]) -> dict:
    return {t: {basis: {c: [p["stat"] for p in points if p["tour"] == t and p[f"corner_{basis}"] == c] for c in CORNERS}
                for basis in BASES} for t in TOURS}


def ranking_index(s4: dict) -> dict:
    return {(r["tour"], r["id"], r["form"]): r for r in s4["ranking"]}


def form_row(r: dict) -> dict:
    keep = ["reading", "elo_imp", "elo_lo", "elo_hi", "elo_2019-2026", "elo_2022-2026", "elo_clears_line", "eras_positive",
            "eras_scored", "sign_coef", "alone_imp", "alone_observed", "market_imp", "market_lo", "market_hi",
            "market_above_band", "market_below_band", "market_clears_line", "elo_coverage", "rank_given_elo"]
    return {"form": r["form"], **{k: r.get(k) for k in keep}}


def best(forms: list[dict], key: str) -> dict | None:
    scored = [f for f in forms if num(f.get(key)) is not None]
    return max(scored, key=lambda f: f[key]) if scored else None


def against_stage4(points: list[dict], s4: dict) -> list[dict]:
    """Each chart statistic beside Stage 4's five rows of it, and whether Stage 4 met the corner's expectation."""
    idx = ranking_index(s4)
    out = []
    for p in points:
        t, s, corner = p["tour"], p["stat"], p["corner_all"]
        forms = [form_row(idx[(t, s, f)]) for f in FORMS]
        findings = [f for f in forms if f["reading"] == "finding"]
        b_elo, b_alone, b_mkt = best(forms, "elo_imp"), best(forms, "alone_imp"), best(forms, "market_imp")
        alone_predicts = b_alone is not None and b_alone["alone_observed"] in ALONE_PREDICTS
        # a finding is reversed when its history points the other way from the statistic within a match: a better
        # record goes with losing more often than Elo says
        reversed_ = [f for f in findings if (num(f["sign_coef"]) or 0) * p["in_match_sign"] < 0]
        out.append({
            "tour": t, "stat": s, "label": p["label"], "corner": corner, "corner_defined": p["corner_defined"],
            "borderline": p["borderline"], "forms": forms, "in_match_sign": p["in_match_sign"],
            "findings": [{"form": f["form"], "elo_imp": f["elo_imp"], "sign_coef": f["sign_coef"],
                          "reversed": f in reversed_} for f in findings],
            "findings_reversed": len(reversed_),
            "readings": {f["form"]: f["reading"] for f in forms},
            "worse_forms": [f["form"] for f in forms if f["reading"] == "worse"],
            "best_elo": b_elo, "best_alone": b_alone, "best_market": b_mkt,
            "market_above_band_forms": [f["form"] for f in forms if f["market_above_band"]],
            "market_clears_line_forms": [f["form"] for f in forms if f["market_clears_line"]],
            "expected_alone": EXPECT[corner]["alone"], "expected_elo": EXPECT[corner]["elo"],
            "alone_agrees": alone_predicts == (corner == "trait"),
            "elo_agrees": (len(findings) > 0) == (corner == "trait")})
    return out


# ------------------------------------------------------------------------------------------------ quoted numbers
def quoted_stage1(s1: dict) -> dict:
    out = {}
    for h in s1["headline"]:
        g = h["gaps_milli"]["p_elo_surf_ret"]
        out[f'{h["tour"]}|{h["window"]}'] = {
            "matches": h["n"], "coin": h["p_coin"], "ranking": h["p_rank"], "surface_elo": h["p_elo_surf_ret"],
            "odds_matches": h["market_subset"]["n"], "surface_elo_on_odds": h["market_subset"]["p_elo_surf_ret"],
            "market": h["market_subset"]["p_market"], "room_milli": g["milli"], "room_lo": g["lo"], "room_hi": g["hi"]}
    return {"headline": out}


def quoted_stage2(s2: dict) -> dict:
    coin = s2["coin"]
    split = {}
    for c in s2["c_floor"]["cells"]:
        if c["dim"] == "all" and c["odds_only"] and c["window"] == "2022-2026":
            day = c["market_minus_luck"]
            # the shares are this summary's arithmetic on Stage 2's numbers: each part over a coin's log loss
            known = 1000 * (coin - c["market"])
            split[c["tour"]] = {"matches": c["matches"], "coin_milli": 1000 * coin, "market": c["market"],
                                "luck_floor": c["luck"], "known_before_milli": known, "on_the_day_milli": day["milli"],
                                "on_the_day_lo": day["lo"], "on_the_day_hi": day["hi"], "luck_milli": 1000 * c["luck"],
                                "known_before_share": known / (1000 * coin), "on_the_day_share": day["milli"] / (1000 * coin),
                                "luck_share": 1000 * c["luck"] / (1000 * coin)}
    fits = {f'{f["tour"]}|{f["best_of"]}': {k: f[k] for k in ("matches", "share_for_90pct", "won_with_fewer_points_pct")}
            for f in s2["a_points_to_wins"]["fits"]}
    return {"coin": coin, "split_2022_2026_with_odds": split, "points_to_wins": fits}


def quoted_stage3(s3: dict) -> dict:
    shr = {(x["stat"], x["tour"]): x for x in s3["shrinkage"]["rows"] if x["surface"] == "all" and x["years"] == "2010-2018"}
    fc = {(x["stat"], x["tour"], x["form"]): x for x in s3["forecast"]["rows"]
          if x["window"] == "2019-2026" and x["surface"] == "all"}
    return {
        "serve_point_average": {t: shr[("spw", t)]["mean"] for t in TOURS},
        "tiebreaks_beyond_point_luck": {t: fc[("tb_won", t, "career to date")]["non_chance_part"] for t in TOURS},
        "break_points_saved_beyond_point_luck": {t: fc[("bp_saved", t, "career to date")]["non_chance_part"] for t in TOURS},
        "serve_points_share_captured": {t: {"ratings": fc[("spw", t, "serve and return ratings")]["share_of_non_chance"],
                                            "career": fc[("spw", t, "career to date")]["share_of_non_chance"]} for t in TOURS},
        "verdict_thresholds": s3["settings"]["verdict_thresholds"]}


def tallies(comp: list[dict]) -> dict:
    """How often Stage 4 met each corner's expectation, trait against the other three corners, per tour."""
    out = {}
    for t in TOURS:
        for group, pick in (("trait", lambda c: c["corner"] == "trait"), ("other", lambda c: c["corner"] != "trait")):
            rows = [c for c in comp if c["tour"] == t and pick(c)]
            out[f"{t}|{group}"] = {"statistics": len(rows), "alone_agree": sum(c["alone_agrees"] for c in rows),
                                   "elo_agree": sum(c["elo_agrees"] for c in rows),
                                   "best_form_52_weeks": sum(1 for c in rows if c["best_elo"] and c["best_elo"]["form"] == "52 weeks"),
                                   "career_worse": sum(1 for c in rows if c["readings"].get("career") == "worse"),
                                   "clear_given_elo": [c["stat"] for c in rows if c["best_elo"] and c["best_elo"]["reading"] == "finding"
                                                       and (num(c["best_elo"]["elo_imp"]) or 0) >= 1.0]}
        other = [f for c in comp if c["tour"] == t and c["corner"] != "trait" for f in c["findings"]]
        top = max(other, key=lambda f: f["elo_imp"]) if other else None
        out[f"{t}|other_largest_finding"] = top
    for test in ("alone", "elo"):
        out[f"all|{test}_agree"] = sum(c[f"{test}_agrees"] for c in comp)
    out["all|statistics"] = len(comp)
    return out


# ------------------------------------------------------------------------------------------------ the plain summary
# Every Stage 4 candidate in one of thirteen families, for the summary's table (each id once; checked below).
FAMILIES = [
    ("ratings", "Serve and return strength ratings",
     "how well each player serves and returns, rated point by point against each opponent",
     ["rating_matchup", "rating_serve", "rating_return"]),
    ("points", "Points won", "share of serve, return and total points won, from the last year to the whole career",
     ["spw", "rpw", "tpw", "hold", "brk", "first_won", "second_won", "rpw_first", "rpw_second", "bp_faced_pg",
      "mu_points", "mu_components", "mu_games"]),
    ("workload", "Recent workload", "sets and minutes played in the last one or two weeks, days since the last match",
     ["sets_14d", "sets_7d", "minutes_14d", "minutes_7d", "days_since", "played_52w", "played_career", "prev_minutes",
      "prev_sets", "last_early"]),
    ("margin", "Margin of recent wins", "an Elo rating that counts how decisively matches were won",
     ["elo_games", "elo_points"]),
    ("surface", "New surface", "a player's first few matches on a surface this season", ["surface_first"]),
    ("age", "Age", "the player's age", ["age"]),
    ("rankings", "Rankings", "official ranking and ranking points; Elo's recent trend",
     ["rank", "rank_points", "rank_elo_gap", "recent_level", "elo_change_26w", "elo_change_52w"]),
    ("length", "Match length", "best of five sets (men's Grand Slams)", ["best_of_five"]),
    ("style", "Serving style", "aces, double faults, first serves in", ["ace", "df", "first_in"]),
    ("clutch", "“Clutch” records", "break points, tiebreaks, deciding sets, big points",
     ["bp_saved", "bp_conv", "tb_won", "deciding", "bigpoint_return", "bp_over", "mu_bp"]),
    ("results", "Win-loss records", "share of matches, sets and games won", ["win", "sets_won", "games_won"]),
    ("h2h", "Head to head", "earlier meetings between the two players", ["h2h"]),
    ("background", "Player background", "height, handedness, home country, wild card, qualifier",
     ["height", "lefty", "vs_hand", "home", "entry_q", "entry_ll", "entry_wc", "entry_pr"]),
]
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")      # the levels the bookmakers price (main draws)
# records with a direction of their own: more of it means doing better (the chart's statistics take theirs from Stage 2)
GOOD_DIRECTION = {"deciding": 1, "bigpoint_return": 1, "bp_over": 1, "mu_bp": 1, "h2h": 1, "win": 1}


def plain_summary(s1: dict, s4: dict, points: list[dict]) -> dict:
    """The plain-language summary's numbers, re-expressed from Stages 1 and 4 and the Stage 4 audit (no estimation):

    * the ladder: how far each forecaster gets from a coin (0%) to the closing odds (100%) on the main-tour matches
      with odds of 2022-2026: (coin - log loss) / (coin - the odds' log loss);
    * each family's gain on Elo where the odds are: its best "finding" (Stage 4's reading) by its gain on the main-tour
      matches (GS, Finals, 1000s, 500s, 250s), as a share of Elo's gap to the odds over the same seasons (Stage 1's
      "room"). The gain on those levels is the per-match average over Stage 4's level groups, each the same walk-forward
      model restricted to the group, so it is exact; the room is measured on the matches with odds, nearly the same
      matches (91% of the men's main tour, 98% of the women's), so the share is approximate;
    * each family's largest gain on the odds, as a share of the distance from a coin to the odds."""
    coin = 1000 * s1["coin"]
    head = {(h["tour"], h["window"].split(" ")[0]): h for h in s1["headline"]}
    audit = {f'{x["tour"]}|{x["row"]}': x for x in load("scoring.json", AUDIT4)["leaders_on_odds_2022_2026"]}
    ladder = {}
    for t in TOURS:
        h = head[(t, "2022-2026")]
        ms = h["market_subset"]
        span = coin - 1000 * ms["p_market"]
        best = audit[f"{t}|rating_matchup|single"]
        ladder[t] = {"matches": ms["n"], "coin_to_market_milli": span,
                     "ranking": (coin - 1000 * ms["p_rank"]) / span, "elo": (coin - 1000 * ms["p_elo_surf_ret"]) / span,
                     "elo_plus_best": (coin - 1000 * best["elo_plus_row"]) / span, "market": 1.0}
    room = {(t, w): head[(t, w)]["gaps_milli"]["p_elo_surf_ret"]["milli"] for t in TOURS for w in ("2013-2026", "2019-2026")}
    to_market = {(t, w): coin - 1000 * head[(t, w)]["market_subset"]["p_market"] for t in TOURS for w in ("2013-2026", "2019-2026")}
    level = {}
    for g in s4["by_group"]:
        if g["score"] == "elo" and g["group_kind"] == "level" and g["group_name"] in MAIN_TOUR and num(g["imp"]) is not None:
            level.setdefault((g["tour"], g["id"], g["form"]), []).append((g["n"], g["imp"]))
    sign = {(p["tour"], p["stat"]): p["in_match_sign"] for p in points}
    rows = {(r["tour"], r["id"]): [] for r in s4["ranking"]}
    for r in s4["ranking"]:
        rows[(r["tour"], r["id"])].append(r)
    covered = [i for _, _, _, ids in FAMILIES for i in ids]
    assert sorted(covered) == sorted({i for _, i in rows}) and len(covered) == len(set(covered)), "families must cover every candidate once"

    def main_tour(r):
        g = level.get((r["tour"], r["id"], r["form"]), [])
        n = sum(k for k, _ in g)
        return sum(k * v for k, v in g) / n if n else None

    fams = []
    for key, title, what, ids in FAMILIES:
        fam = {"key": key, "title": title, "what": what, "ids": ids, "tours": {}}
        for t in TOURS:
            rs = [r for i in ids for r in rows.get((t, i), [])]
            if not rs:
                continue
            window = lambda r: "2013-2026" if r["scored_from"] == 2013 else "2019-2026"
            direction = lambda r: sign.get((t, r["id"]), GOOD_DIRECTION.get(r["id"]))
            out = []
            for r in rs:
                mt = main_tour(r)
                rev = r["reading"] == "finding" and direction(r) is not None and (num(r["sign_coef"]) or 0) * direction(r) < 0
                out.append({"id": r["id"], "form": r["form"], "name": r["name"], "reading": r["reading"],
                            "reversed": rev, "overall_gain": num(r["elo_imp"]), "main_tour_gain": mt,
                            "share_of_gap": None if mt is None else mt / room[(t, window(r))],
                            "market_gain": num(r["market_imp"]), "market_line": bool(r["market_clears_line"]),
                            "market_share": None if num(r["market_imp"]) is None else r["market_imp"] / to_market[(t, window(r))]})
            helps = [o for o in out if o["reading"] == "finding" and not o["reversed"] and o["main_tour_gain"] is not None]
            best = max(helps, key=lambda o: o["main_tour_gain"]) if helps else None
            on_market = [o for o in out if o["market_line"]]
            fam["tours"][t] = {
                "verdict": "helps" if helps else ("reversed" if any(o["reversed"] for o in out) else "no"),
                "findings": sum(o["reading"] == "finding" for o in out), "versions": len(out),
                "best": best, "reversed": [o for o in out if o["reversed"]],
                "worse": sum(o["reading"] == "worse" for o in out),
                "market": max(on_market, key=lambda o: o["market_gain"]) if on_market else None}
        fams.append(fam)
    best_market = {t: max((o for f in fams for o in ([f["tours"][t]["market"]] if t in f["tours"] and f["tours"][t]["market"] else [])),
                          key=lambda o: o["market_share"]) for t in TOURS}
    return {"ladder": ladder, "families": fams, "best_market": best_market,
            "room": {f"{t}|{w}": v for (t, w), v in room.items()},
            "coin_to_market": {f"{t}|{w}": v for (t, w), v in to_market.items()},
            "candidates": len(set(covered)), "versions": {t: sum(1 for r in s4["ranking"] if r["tour"] == t) for t in TOURS}}


def short_row(r: dict) -> dict:
    keep = ["tour", "id", "form", "name", "reading", "elo_imp", "elo_lo", "elo_hi", "elo_2019-2026", "elo_2022-2026",
            "eras_positive", "eras_scored", "sign_coef", "alone_imp", "market_imp", "market_lo", "market_hi",
            "market_above_band", "market_clears_line", "elo_coverage", "rank_given_elo"]
    return {k: r.get(k) for k in keep}


def quoted_stage4(s4: dict) -> dict:
    rank = s4["ranking"]
    by_tour = {t: [r for r in rank if r["tour"] == t] for t in TOURS}
    readings = sorted({r["reading"] for r in rank})
    counts = {t: {k: sum(1 for r in by_tour[t] if r["reading"] == k) for k in readings} for t in TOURS}
    clear = {t: sum(1 for r in by_tour[t] if r["reading"] == "finding" and (num(r["elo_imp"]) or 0) >= 1.0) for t in TOURS}
    leaders = {t: [short_row(r) for r in sorted((r for r in by_tour[t] if num(r.get("elo_imp")) is not None),
                                                 key=lambda r: -r["elo_imp"])[:LEADERS]] for t in TOURS}
    market = {t: [short_row(r) for r in sorted((r for r in by_tour[t] if r.get("market_clears_line")),
                                                key=lambda r: -r["market_imp"])] for t in TOURS}
    best_market = {t: short_row(max((r for r in by_tour[t] if num(r.get("market_imp")) is not None),
                                    key=lambda r: r["market_imp"])) for t in TOURS}
    groups = {}
    for g in s4["by_group"]:
        if g["id"] == "rating_matchup" and g["score"] == "elo" and g["group_kind"] in ("era", "level"):
            groups[f'{g["tour"]}|{g["group_name"]}'] = {k: g[k] for k in ("n", "imp", "lo", "hi", "directional")}
    lag = {f'{x["tour"]}|{x["id"]}|{x["form"]}': {"original_elo": x.get("original_elo"), "rebuilt_elo": x.get("rebuilt_elo"),
                                                  "original_market": x.get("original_market"),
                                                  "rebuilt_market": x.get("rebuilt_market")}
           for x in s4["leak_checks"] if x["check"] == "one match later"}
    idx = ranking_index(s4)
    named = {}
    for key in [("rank", "single"), ("rank_points", "single"), ("rank_elo_gap", "single"), ("recent_level", "single"),
                ("bigpoint_return", "single"), ("lefty", "single"), ("vs_hand", "single"), ("elo_change_26w", "single"),
                ("elo_change_52w", "single"), ("entry_wc", "single"), ("entry_ll", "single"), ("prev_sets", "single"),
                ("height", "single"), ("age", "single"), ("best_of_five", "single"), ("tb_won", "52 weeks"),
                ("rating_serve", "single"), ("rating_return", "single")]:
        for t in TOURS:
            if (t, *key) in idx:
                named[f"{t}|{key[0]}|{key[1]}"] = short_row(idx[(t, *key)])
    families = {}
    for fid in ("deciding", "win", "h2h", "bp_over", "mu_points", "mu_components", "mu_games", "tpw"):
        for t in TOURS:
            rows = [idx[(t, fid, f)] for f in FORMS if (t, fid, f) in idx]
            scored = [r for r in rows if num(r.get("elo_imp")) is not None]
            b = max(scored, key=lambda r: r["elo_imp"]) if scored else None
            families[f"{t}|{fid}"] = {"readings": {r["form"]: r["reading"] for r in rows},
                                      "forms": {r["form"]: {k: r.get(k) for k in ("reading", "elo_imp", "sign_coef")} for r in rows},
                                      "findings": sum(1 for r in rows if r["reading"] == "finding"),
                                      "best": short_row(b) if b else None,
                                      "market_best": max((num(r.get("market_imp")) for r in rows
                                                          if num(r.get("market_imp")) is not None), default=None),
                                      "market_below_band": [r["form"] for r in rows if r.get("market_below_band")]}
    slopes = {f'{c["stat"]}|{c["tour"]}': {k: c[k] for k in ("value", "lo", "hi")} for c in s4["constants"]
              if c["kind"] == "adjustment beta, reference (not used)" and c["stat"] == "spw"}
    # which of the five forms adds most to Elo, per statistic or matchup that has forms (rows carrying nothing aside)
    best_form = {t: {f: 0 for f in FORMS} for t in TOURS}
    for t in TOURS:
        for fid in sorted({r["id"] for r in by_tour[t] if r["form"] in FORMS}):
            rows = [idx[(t, fid, f)] for f in FORMS if (t, fid, f) in idx and num(idx[(t, fid, f)].get("elo_imp")) is not None
                    and not idx[(t, fid, f)]["constant"]]
            if rows:
                best_form[t][max(rows, key=lambda r: r["elo_imp"])["form"]] += 1
    return {"rows": {t: len(by_tour[t]) for t in TOURS}, "readings": counts, "findings_clear": clear,
            "lines": {k: v["line"] for k, v in s4["lines"].items()},
            "clears_line": {f"{t}|{s}": sum(1 for r in by_tour[t] if r.get(f"{s}_clears_line")) for t in TOURS
                            for s in ("alone", "elo", "market")},
            "market_above_band": {t: sum(1 for r in by_tour[t] if r.get("market_above_band")) for t in TOURS},
            "market_at_least_clear": {t: sum(1 for r in by_tour[t] if (num(r.get("market_imp")) or 0) >= 1.0) for t in TOURS},
            "leaders": leaders, "market_line_rows": market, "best_market": best_market,
            "rating_matchup_groups": groups, "one_match_later": lag, "named": named, "families": families,
            "spw_simple_slope": slopes, "pool_evaluation": s4["pool_evaluation"], "best_form_counts": best_form}


def quoted_audit4() -> dict:
    sc = load("scoring.json", AUDIT4)
    lead = {f'{x["tour"]}|{x["row"]}': {k: x[k] for k in ("matches", "market_better_than_refitted_elo_milli",
                                                          "row_gain_given_elo_milli")}
            for x in sc["leaders_on_odds_2022_2026"]}
    rows = pd.read_csv(AUDIT4 / "scoring_rows.csv")
    pin = {}
    for t in TOURS:
        r = rows[(rows["tour"] == t) & rows["pinnacle_imp"].notna()]
        top = r.loc[r["pinnacle_imp"].idxmax()]
        pin[t] = {"largest_gain": float(top["pinnacle_imp"]), "largest_row": f'{top["id"]}|{top["form"]}',
                  "rows_above_band": int(r["pinnacle_above_band"].astype(bool).sum()),
                  "rows_clear_line": int(r["pinnacle_clears_own_line"].astype(bool).sum()),
                  "rows_at_least_clear": int((r["pinnacle_imp"] >= 1.0).sum())}
    return {"leaders_on_odds_2022_2026": lead, "pinnacle": pin,
            "pinnacle_lines": {k: v["line"] for k, v in sc["pinnacle_lines"].items()}}


def main() -> int:
    s1, s2, s3, s4 = (load(f"stage{i}_results.json") for i in (1, 2, 3, 4))
    persist = pd.read_csv(C.OUT / "stage3_persistence.csv")
    impact = pd.read_csv(C.OUT / "stage2_match_impact.csv")
    checks = check_csvs(persist, impact, s3, s2)

    repeats_line = float(s3["settings"]["verdict_thresholds"][0])
    weakly_line = float(s3["settings"]["verdict_thresholds"][1])
    coin_milli = 1000 * s2["coin"]
    decides_line = DECIDES_SHARE_OF_COIN * coin_milli
    points = chart_points(persist, impact, repeats_line, decides_line)
    comp = against_stage4(points, s4)

    pd.DataFrame([{k: v for k, v in p.items()} for p in points]).to_csv(OUT_CSV, index=False)
    res = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {"chart_x": "stage3_persistence.csv (surface all)", "chart_y": "stage2_match_impact.csv (best_of all)",
                    "stage4": "stage4_results.json (ranking, by_group, leak_checks, constants)",
                    "quoted": ["stage1_results.json", "stage2_results.json", "stage3_results.json", "stage4_results.json",
                               "audit4/scoring.json", "audit4/scoring_rows.csv"]},
        "settings": {"repeats_line": repeats_line, "repeats_weakly_line": weakly_line, "coin_milli": coin_milli,
                     "decides_share_of_coin": DECIDES_SHARE_OF_COIN, "decides_line_milli": decides_line,
                     "corners": CORNERS, "bases": BASES, "expect": EXPECT, "alone_predicts": list(ALONE_PREDICTS),
                     "forms": FORMS},
        "csv_checks": checks,
        "chart": {"points": points, "adjusted": adjusted_points(persist, repeats_line),
                  "gaps": gaps(points, decides_line), "corners": corner_lists(points)},
        "stage4_by_stat": comp,
        "tallies": tallies(comp),
        "plain": plain_summary(s1, s4, points),
        "disagreements": [{k: c[k] for k in ("tour", "stat", "label", "corner", "borderline", "alone_agrees",
                                              "elo_agrees")} for c in comp if not (c["alone_agrees"] and c["elo_agrees"])],
        "quoted": {"stage1": quoted_stage1(s1), "stage2": quoted_stage2(s2), "stage3": quoted_stage3(s3),
                   "stage4": quoted_stage4(s4), "audit4": quoted_audit4()},
    }
    OUT_JSON.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    n_dis = len(res["disagreements"])
    print(f"wrote {OUT_JSON.name} and {OUT_CSV.name}: {len(points)} points, {n_dis} statistic-tours depart from their corner")
    return 0


if __name__ == "__main__":
    sys.exit(main())
