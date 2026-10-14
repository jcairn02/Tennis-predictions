"""Stage B of "rating systems against Elo": the frozen ratings against Stage 1's surface Elo and the closing odds, and
through the shared harness.

Outside the harness (stageB_summary.json), per tour, on the evaluation matches of 2013-2026 (the Stage 4 pool, side A
random):
    * raw log loss of P(A wins) of every system (its frozen surface blend, and its overall rating alone), surface Elo
      (p_elo), the closing odds' average (p_mkt) and Pinnacle (stage1_baselines' p_pinnacle), by window (2013-2026,
      the tuning years 2013-2018, 2019-2026, 2022-2026), era, level and season; on every evaluation match and on the
      matches with odds;
    * each system minus Elo in milli-log-loss with two 95% intervals: the per-match one of the earlier studies and the
      feature-alpha audit's, clustered by calendar week (elo_retest.clustered_gain); and the share of the Elo-to-market
      gap closed, (Elo - system) / (Elo - market), on the matches with odds;
    * calibration, 2019-2026 (ten bins and the slope; ufc_ideas.stageA_rundown.calibration);
    * where a system gains or loses against Elo: by the fewer prior rated matches of the two players, by the longer
      layoff of the two, by the larger rating uncertainty of the two (the match-by-match Glicko-2's phi), at best of
      five, by Grand Slam qualifying round.
Through the harness (src/eda/ufc_ideas/common.py: walk-forward by season, a logistic regression without an intercept,
20 shuffled copies, the family-wide line, the reading given Elo):
    * every system's rating difference (logit of its probability): alone, given Elo, given the market;
    * surface Elo given each of the two leading systems (does Elo add to them?);
    * the earlier leaders given Elo (the earlier ranking reproduced), given each leading system and given the market:
      the serve and return ratings through the iid model, the games-weighted Elo, sets over 14 days, the 52-week points
      matchup, age, the first matches on a surface, the 2-week adjperf of total points and the short-memory IOS
      matchup, and the men's lead against the odds, the 16-input adjperf / adjdef profile (Stage D);
    * the two leading systems together with Elo (does a second rating add to the market?).

Writes, in data/studies/rating_systems/: stageB_features.parquet (the scored frame), stageB_ranking.csv,
stageB_results.csv, stageB_null_copies.csv, stageB_results.json (the harness), stageB_summary.json (the comparisons),
stageB_catalog.json (one entry per scored row id).
Run after stageA_ratings.py: ./python.sh src/eda/rating_systems/stageB_compare.py   (5 worker processes)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_alpha_audit.elo_retest import clustered_gain  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402
from src.eda.ufc_ideas.stageA_rundown import calibration, diff_stats, ll_rows  # noqa: E402

OUT = RC.OUT
RATINGS = OUT / "stageA_ratings.parquet"
A_SUMMARY = OUT / "stageA_summary.json"
FEATURES = OUT / "stageB_features.parquet"
PREFIX = OUT / "stageB"
SUMMARY = OUT / "stageB_summary.json"
CATALOG = OUT / "stageB_catalog.json"
BASELINES = C.OUT / "stage1_baselines.parquet"
UFC = ROOT / "data" / "studies" / "ufc_ideas"
WORKERS = 5
SYSTEMS = ("glicko_cs", "ttt", "glicko2m", "trueskill", "trueskill_cs", "glicko2", "glicko1m", "glicko1")
HOLD = OUT / "stageA_ttt_hold.parquet"           # the sensitivity (stageA_ttt_hold.py), scored when present
if HOLD.exists():
    SYSTEMS = SYSTEMS + ("ttt_hold",)
CORRELATED = ("glicko_cs", "trueskill_cs")        # surface inside the model: no separate overall-only forecast
LEADING = ("glicko_cs", "ttt", "glicko2m", "trueskill")   # the systems scored as bases in the harness
WINDOWS = {"2013-2026": (2013, 2026), "2013-2018 (tuning)": (2013, 2018), "2019-2026": (2019, 2026),
           "2022-2026 (headline)": (2022, 2026)}
STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
         "rpw_first", "rpw_second"]
PROFILE = [f"adjperf_{s}|decayed" for s in STATS] + [f"adjdef_{s}|decayed" for s in ("ace", "df", "first_in", "bp_faced_pg")]
IOS_SHORT = {"atp": "ios_matchup_points|diagnostic: h 4 weeks", "wta": "ios_matchup_points|diagnostic: h 13 weeks"}
# the leaders: id, form, name, columns, box-score based (the women's scored from 2019, as in Stage 4)
LEADERS = [("rating_matchup", "single", "Serve and return ratings through the iid model", ["rating_matchup|single"], True),
           ("elo_games", "single", "Games-weighted Elo", ["elo_games|single"], False),
           ("sets_14d", "single", "Sets over the last 14 days", ["sets_14d|single"], False),
           ("mu_points", "52 weeks", "Serve against return: points", ["mu_points|52 weeks"], True),
           ("age", "single", "Age and age squared", ["age|single", "age|single|2"], False),
           ("surface_first", "single", "One of the first matches on this surface this season", ["surface_first|single"], False)]
NAMES = {"glicko_cs": "Glicko with correlated surface skills", "ttt": "TrueSkill Through Time",
         "glicko2m": "Glicko-2, match by match", "trueskill": "TrueSkill", "trueskill_cs": "TrueSkill with correlated surfaces",
         "glicko2": "Glicko-2, weekly rating periods", "glicko1m": "Glicko-1, match by match",
         "glicko1": "Glicko-1, weekly rating periods", "ttt_hold": "TrueSkill Through Time, two-week events held"}
DESCRIPTIONS = {
    "glicko_cs": "A skill per surface, correlated (the Bayesian form of the surface blend), updated match by match by "
                 "Glicko's (Kalman) step; the deviation grows with the time since the player's last match",
    "ttt": "TrueSkill Through Time run causally: each finished week joins the model, then the last weeks' results are "
           "re-scored against what each opponent turned out to be worth; a surface rating blended in",
    "trueskill_cs": "Correlated surface skills with TrueSkill's update",
    "ttt_hold": "TrueSkill Through Time at the same constants, with each two-week event (a round of 128) joining the "
                "smoothed model only two weeks after its start date: the overlap sensitivity",
    "glicko2m": "Glicko-2 updated round by round, the rating deviation growing with the time since the player's last match; "
                "a surface rating blended in as for surface Elo; A's rating minus B's on the log-odds scale",
    "trueskill": "Two-player TrueSkill (Gaussian skill, probit link), the variance growing with the time since the player's "
                 "last match; a surface rating blended in; the forecast's probit turned into log-odds",
    "glicko2": "Glicko-2 as Glickman specifies it, with each tournament week a rating period",
    "glicko1m": "The match-by-match Glicko-2 with the volatility held fixed (Glicko-1)",
    "glicko1": "The weekly Glicko-2 with the volatility held fixed (Glicko-1)",
    "elo": "Stage 1's surface Elo on the log-odds scale, scored on top of the new ratings and the market",
    "rating_matchup": "The predictability diagnostic's leader: the serve and return ratings through the iid model",
    "elo_games": "The games-weighted Elo (margin of victory)", "sets_14d": "Sets played over the last two weeks",
    "mu_points": "The serve-against-return points matchup over the last year", "age": "Age and age squared",
    "surface_first": "One of a player's first matches on the surface this season",
    "adjperf_tpw": "The UFC-ideas study's 2-week opponent-adjusted total points won",
    "ios_short": "The UFC-ideas study's short-memory IOS points matchup (4 weeks men, 13 weeks women)",
    "profile_adjperf": "The UFC-ideas study's men's lead against the odds: the 16-input 2-week adjperf / adjdef profile",
    "pair_glicko_cs": "Glicko with correlated surfaces and surface Elo together (two inputs)",
    "pair_ttt": "TrueSkill Through Time and surface Elo together (two inputs)",
    "ratings_three": "Glicko with correlated surfaces, TrueSkill Through Time and surface Elo together (three inputs)"}
FAMILY = {**{s: "new rating" for s in SYSTEMS}, "elo": "Elo", "pair_glicko_cs": "ratings together",
          "pair_ttt": "ratings together", "ratings_three": "ratings together", "profile_adjperf": "statistics profile",
          **{c[0]: "earlier leaders" for c in LEADERS}, "adjperf_tpw": "earlier leaders", "ios_short": "earlier leaders"}
EDGES_BINS = [(-1, 0, "0"), (0, 5, "1-5"), (5, 20, "6-20"), (20, 50, "21-50"), (50, 100, "51-100"), (100, 10 ** 9, "over 100")]
LAYOFF_BINS = [(-1, 14, "up to 14"), (14, 35, "15-35"), (35, 90, "36-90"), (90, 180, "91-180"), (180, 365, "181-365"),
               (365, 10 ** 9, "over 365")]
PHI_BINS = [(0, 0.35, "under 0.35"), (0.35, 0.5, "0.35-0.5"), (0.5, 0.8, "0.5-0.8"), (0.8, 1.5, "0.8-1.5"), (1.5, 99, "over 1.5")]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The frame

def build_frame() -> pd.DataFrame:
    leader_cols = [c for x in LEADERS for c in x[3]]
    pool = U.load_pool(extra=leader_cols)
    rt = pd.read_parquet(RATINGS).set_index("match_id")
    if HOLD.exists():
        rt = rt.join(pd.read_parquet(HOLD).set_index("match_id"), how="left")
    rt = rt.reindex(pool["match_id"])
    assert rt["p_glicko2m"].notna().all(), "every pool match has a rating"
    f = pool.copy()
    for s in SYSTEMS:
        f[f"p_{s}"] = rt[f"p_{s}"].to_numpy(dtype="float64")
        if s not in CORRELATED:
            f[f"p_{s}_overall"] = rt[f"p_{s}_overall"].to_numpy(dtype="float64")
        f[f"{s}|single"] = logit(np.clip(f[f"p_{s}"].to_numpy(), 1e-12, 1 - 1e-12))
    f["elo|single"] = logit(np.clip(f["p_elo"].to_numpy(dtype="float64"), 1e-12, 1 - 1e-12))
    for c in ("n_a", "n_b", "glicko2m_u_a", "glicko2m_u_b"):
        f[c] = rt[c].to_numpy(dtype="float64")
    bl = pd.read_parquet(BASELINES, columns=["match_id", "p_pinnacle", "p_elo_ret"]).set_index("match_id").reindex(pool["match_id"])
    f["p_pin"] = bl["p_pinnacle"].to_numpy(dtype="float64")
    f["p_elo_overall"] = bl["p_elo_ret"].to_numpy(dtype="float64")
    adj = pd.read_parquet(UFC / "stageB_adj_features.parquet", columns=["match_id", "adjperf_tpw|decayed"] + PROFILE)
    adj = adj.set_index("match_id").reindex(pool["match_id"])
    f["adjperf_tpw|decayed"] = adj["adjperf_tpw|decayed"].to_numpy(dtype="float64")
    for c in PROFILE:
        f[c] = adj[c].to_numpy(dtype="float64")
    ios = pd.read_parquet(UFC / "stageB_ios_features.parquet", columns=["match_id"] + list(IOS_SHORT.values()))
    ios = ios.set_index("match_id").reindex(pool["match_id"])
    f["ios_short|single"] = np.where(f["tour"].eq("atp"), ios[IOS_SHORT["atp"]].to_numpy(dtype="float64"),
                                     ios[IOS_SHORT["wta"]].to_numpy(dtype="float64"))
    m = C.load_matches(["match_id", "tournament_date", "round", "best_of", "status", "player_a_id", "player_b_id"])
    mm = m.set_index("match_id").reindex(pool["match_id"])
    f["week"] = pd.to_datetime(mm["tournament_date"]).dt.to_period("W-SUN").astype(str).to_numpy()
    f["tournament_date"] = mm["tournament_date"].to_numpy()
    f["player_a_id"], f["player_b_id"] = mm["player_a_id"].to_numpy(), mm["player_b_id"].to_numpy()
    f["round"] = mm["round"].to_numpy()
    f["best_of"] = mm["best_of"].to_numpy()
    f["layoff"] = layoff(m, mm)
    return f


def layoff(m: pd.DataFrame, mm: pd.DataFrame) -> np.ndarray:
    """The longer of the two players' gaps (days) since their previous date with a rating-moving match."""
    long = pd.concat([m[["tournament_date", "status", c]].rename(columns={c: "pid"}) for c in ("player_a_id", "player_b_id")])
    long = long[long["status"].isin(RC.UPDATES)].drop_duplicates(["pid", "tournament_date"]).sort_values(["pid", "tournament_date"])
    long["prev"] = long.groupby("pid")["tournament_date"].shift(1)
    last = long.set_index(["pid", "tournament_date"])["prev"]
    days = []
    for side in ("player_a_id", "player_b_id"):
        key = pd.MultiIndex.from_arrays([mm[side].to_numpy(), mm["tournament_date"].to_numpy()])
        prev = last.reindex(key).to_numpy()
        days.append((mm["tournament_date"].to_numpy() - prev) / np.timedelta64(1, "D"))
    return np.fmax(days[0], days[1])


# ------------------------------------------------------------------------------------------------
# Comparisons outside the harness

def compare(L: dict, keys: list[str], mask: np.ndarray, weeks: np.ndarray, market: bool) -> dict:
    """Log loss of each forecaster on the rows of mask; each minus... Elo minus each (positive: the forecaster better),
    per-match and week-clustered 95% intervals; with the market, the share of the Elo-to-market gap closed."""
    n = int(mask.sum())
    out = {"n": n, "directional_only": bool(n < C.DIRECTIONAL_ONLY_BELOW), "ll": {}}
    if n == 0:
        return out
    for k in keys:
        out["ll"][k] = float(L[k][mask].mean())
    out["elo_minus"] = {}
    for k in keys:
        if k == "elo":
            continue
        d = diff_stats(L["elo"][mask], L[k][mask])
        cg = clustered_gain(L["elo"][mask] - L[k][mask], weeks[mask])
        d.update({"week_lo": cg["lo_mll"], "week_hi": cg["hi_mll"], "weeks": cg["weeks"]})
        out["elo_minus"][k] = d
    if market:
        room = out["ll"]["elo"] - out["ll"]["market"]
        out["room_milli"] = 1000 * room
        out["gap_closed"] = {k: (out["ll"]["elo"] - out["ll"][k]) / room for k in keys if k not in ("elo", "market", "pinnacle")}
        out["coin_to_market"] = {k: (np.log(2) - out["ll"][k]) / (np.log(2) - out["ll"]["market"]) for k in keys}
    return out


def comparisons(f: pd.DataFrame) -> dict:
    y = f["a_won"].to_numpy(dtype=bool)
    P = {"elo": f["p_elo"].to_numpy(dtype="float64"), "elo_overall": f["p_elo_overall"].to_numpy(dtype="float64"),
         "market": f["p_mkt"].to_numpy(dtype="float64"), "pinnacle": f["p_pin"].to_numpy(dtype="float64")}
    for s in SYSTEMS:
        P[s] = f[f"p_{s}"].to_numpy(dtype="float64")
        if s not in CORRELATED:
            P[f"{s}_overall"] = f[f"p_{s}_overall"].to_numpy(dtype="float64")
    L = {k: ll_rows(np.nan_to_num(v, nan=0.5), y) for k, v in P.items()}
    ev = f["evaluation"].to_numpy(dtype=bool)
    year, era, grp = f["year"].to_numpy(), f["era"].to_numpy(), f["group"].to_numpy()
    weeks = f["week"].to_numpy()
    odds = np.isfinite(P["market"])
    pin = odds & np.isfinite(P["pinnacle"])
    keys_all = ["elo", "elo_overall"] + [k for s in SYSTEMS for k in ((s,) if s in CORRELATED else (s, f"{s}_overall"))]
    out = {"raw": {}, "by_era": {}, "by_level": {}, "by_season": {}, "calibration_2019_2026": {}, "diagnostics": {},
           "weekly_overshoot": {}}
    for tour in C.TOURS:
        t = (f["tour"].to_numpy() == tour) & ev

        def cell(mk, full=True):
            c = {"all": compare(L, keys_all, mk, weeks, False),
                 "odds": compare(L, keys_all + ["market"], mk & odds, weeks, True)}
            if full:
                c["pinnacle"] = compare(L, ["elo", "market", "pinnacle"] + list(SYSTEMS), mk & pin, weeks, True)
            return c
        out["raw"][tour] = {w: cell(t & (year >= a) & (year <= b)) for w, (a, b) in WINDOWS.items()}
        out["by_era"][tour] = {e: cell(t & (era == e), False) for e in C.ERAS}
        out["by_level"][tour] = {g: cell(t & (grp == g), False) for g in U.LEVEL_GROUPS}
        out["by_season"][tour] = {int(s): {"all": compare(L, ["elo"] + list(SYSTEMS), t & (year == s), weeks, False)}
                                  for s in range(C.EVAL_YEARS[0], C.EVAL_YEARS[-1] + 1)}
        late = t & (year >= 2019)
        out["calibration_2019_2026"][tour] = {k: calibration(P[k][late], y[late]) for k in ["elo"] + list(SYSTEMS)}
        out["diagnostics"][tour] = diagnostics(f, L, t)
        out["weekly_overshoot"][tour] = weekly_overshoot(f, L, t)
    return out


def in_week_counts(f: pd.DataFrame) -> np.ndarray:
    """For each pool match, the larger of the two players' rated matches earlier in the same start date's week (their
    pre-match count minus their smallest pre-match count that week; the pool holds evaluation-level matches only, so
    a lower-level match the same week is not seen here)."""
    long = pd.concat([pd.DataFrame({"row": np.arange(len(f)), "pid": f[c].to_numpy(), "date": f["tournament_date"].to_numpy(),
                                    "n": f[n].to_numpy()}) for c, n in (("player_a_id", "n_a"), ("player_b_id", "n_b"))])
    long["first"] = long.groupby(["pid", "date"])["n"].transform("min")
    long["earlier"] = long["n"] - long["first"]
    return long.groupby("row")["earlier"].max().reindex(np.arange(len(f))).to_numpy()


def weekly_overshoot(f: pd.DataFrame, L: dict, t: np.ndarray) -> dict:
    """The weekly Glicko-2 (a week's games scored together around the pre-week rating) against the match-by-match one,
    by how many matches the players had already played that week and by experience: the weekly log loss minus the
    match-by-match one (positive: weekly worse)."""
    if "glicko2" not in L or "glicko2m" not in L:
        return {}
    earlier = in_week_counts(f)
    fewest = np.fmin(f["n_a"].to_numpy(), f["n_b"].to_numpy())
    out = {}
    for lab, lo, hi in (("first match of the week for both", -1, 0), ("1 earlier", 0, 1), ("2 earlier", 1, 2),
                        ("3 or more earlier", 2, 10 ** 6)):
        m = t & (earlier > lo) & (earlier <= hi)
        out[lab] = {"all": diff_stats(L["glicko2"][m], L["glicko2m"][m]),
                    "fewer_than_21_prior": diff_stats(L["glicko2"][m & (fewest <= 20)], L["glicko2m"][m & (fewest <= 20)]),
                    "over_100_prior": diff_stats(L["glicko2"][m & (fewest > 100)], L["glicko2m"][m & (fewest > 100)])}
    return out


def diagnostics(f: pd.DataFrame, L: dict, t: np.ndarray) -> dict:
    """Elo's log loss minus each leading system's (positive: the system better), by the fewer prior rated matches of
    the two players, the longer layoff of the two, the larger match-by-match Glicko-2 deviation of the two, best of
    five, and Grand Slam qualifying round."""
    fewest = np.fmin(f["n_a"].to_numpy(), f["n_b"].to_numpy())
    lay = f["layoff"].to_numpy(dtype="float64")
    phi = np.fmax(f["glicko2m_u_a"].to_numpy(), f["glicko2m_u_b"].to_numpy())
    bo5 = f["best_of"].to_numpy() == 5
    grp, rnd = f["group"].to_numpy(), f["round"].to_numpy()
    out = {}
    for s in LEADING:
        def cut(vals, bins):
            ok = t & np.isfinite(vals)
            return {lab: diff_stats(L["elo"][ok & (vals > lo) & (vals <= hi)], L[s][ok & (vals > lo) & (vals <= hi)])
                    for lo, hi, lab in bins}
        out[s] = {"fewest_prior_matches": cut(fewest.astype("float64"), EDGES_BINS),
                  "longest_layoff_days": cut(lay, LAYOFF_BINS),
                  "largest_glicko2m_deviation": cut(phi, PHI_BINS),
                  "best_of_five": diff_stats(L["elo"][t & bo5], L[s][t & bo5]),
                  "best_of_three": diff_stats(L["elo"][t & ~bo5], L[s][t & ~bo5]),
                  "grand_slam_qualifying_by_round": {r: diff_stats(L["elo"][t & (grp == "GSQ") & (rnd == r)],
                                                                   L[s][t & (grp == "GSQ") & (rnd == r)])
                                                     for r in ("Q1", "Q2", "Q3")},
                  "note": "Elo's log loss minus the system's (milli-log-loss): positive is the system better"}
    return out


# ------------------------------------------------------------------------------------------------
# The harness tasks

def tasks() -> list[dict]:
    out = []
    lead_bases = {s: f"p_{s}" for s in LEADING}
    for tour in C.TOURS:
        for s in SYSTEMS:
            out.append(U.task(tour, s, "single", NAMES[s], FAMILY[s], [f"{s}|single"], scores=("alone", "elo", "market")))
        out.append(U.task(tour, "elo", "single", "Surface Elo (Stage 1)", FAMILY["elo"], ["elo|single"],
                          scores=("alone", "market") + LEADING, bases=lead_bases))
        for cid, form, name, cols, box in LEADERS:
            out.append(U.task(tour, cid, form, name, FAMILY[cid], cols, scores=("elo",) + LEADING + ("market",),
                              bases=lead_bases, wta_box_from_2019=box))
        out.append(U.task(tour, "adjperf_tpw", "decayed", "Opponent-adjusted total points won, 2-week memory",
                          FAMILY["adjperf_tpw"], ["adjperf_tpw|decayed"], scores=("elo",) + LEADING + ("market",),
                          bases=lead_bases, wta_box_from_2019=True))
        out.append(U.task(tour, "ios_short", "single", "Short-memory IOS points matchup", FAMILY["ios_short"],
                          ["ios_short|single"], scores=("elo",) + LEADING + ("market",), bases=lead_bases,
                          wta_box_from_2019=True))
        out.append(U.task(tour, "profile_adjperf", "profile", "The adjperf profile, decayed (16 inputs)",
                          FAMILY["profile_adjperf"], PROFILE, scores=("alone", "elo") + LEADING + ("market",),
                          bases=lead_bases, wta_box_from_2019=True))
        out.append(U.task(tour, "pair_glicko_cs", "single", "Glicko with correlated surfaces and surface Elo",
                          FAMILY["pair_glicko_cs"], ["glicko_cs|single", "elo|single"], scores=("alone", "market")))
        out.append(U.task(tour, "pair_ttt", "single", "TrueSkill Through Time and surface Elo", FAMILY["pair_ttt"],
                          ["ttt|single", "elo|single"], scores=("alone", "market")))
        out.append(U.task(tour, "ratings_three", "single", "Correlated-surface Glicko, TrueSkill Through Time and surface Elo",
                          FAMILY["ratings_three"], ["glicko_cs|single", "ttt|single", "elo|single"],
                          scores=("alone", "market")))
    return out


def catalog(task_list: list[dict], a_summary: dict) -> list:
    out = []
    for cid in dict.fromkeys(t["id"] for t in task_list):
        tk = [t for t in task_list if t["id"] == cid]
        tuned = None
        if cid == "ttt_hold":
            tuned = {t: {"constants": a_summary["chosen"][f"ttt|{t}"], "tuned_on": "TrueSkill Through Time's frozen "
                         "constants, not retuned (stageA_ttt_hold.py)"} for t in C.TOURS}
        elif cid in SYSTEMS:
            tuned = {t: {"constants": a_summary["chosen"][f"{cid}|{t}"], "tuned_on": "2013-2018 evaluation matches"}
                     for t in C.TOURS}
        out.append({"id": cid, "name": tk[0]["name"], "family": FAMILY[cid], "description": DESCRIPTIONS[cid],
                    "form": tk[0]["form"], "columns": tk[0]["cols"],
                    "tuned": tuned or ("Stage 1's frozen constants" if cid == "elo" else "the earlier studies' frozen constants"),
                    "base_variants": {t["tour"]: {s: (b if b else "coin") for s, b in t["bases"].items()} for t in tk},
                    "scored_from": {t["tour"]: t["from"] for t in tk}})
    return out


def reference_check(rank: pd.DataFrame) -> dict:
    """The leaders' given-Elo and given-market scores against the predictability diagnostic's ranking."""
    ref = U.stage4_reference([c[0] for c in LEADERS])
    rows, worst = [], 0.0
    for cid, form, _, _, _ in LEADERS:
        for tour in C.TOURS:
            a = rank[(rank["id"] == cid) & (rank["form"] == form) & (rank["tour"] == tour)].iloc[0]
            b = ref[(ref["id"] == cid) & (ref["form"] == form) & (ref["tour"] == tour)].iloc[0]
            for s in ("elo", "market"):
                for k in ("imp", "lo", "hi", "band_min", "band_max", "scored"):
                    worst = max(worst, abs(float(a[f"{s}_{k}"]) - float(b[f"{s}_{k}"])))
            rows.append({"tour": tour, "id": cid, "elo_imp_here": float(a["elo_imp"]), "elo_imp_stage4": float(b["elo_imp"])})
    return {"max_abs_difference": worst, "rows": rows}


def main() -> int:
    a_summary = json.loads(A_SUMMARY.read_text(encoding="utf-8"))
    f = build_frame()
    keep = [c for c in f.columns if c not in ("round", "best_of", "tournament_date", "player_a_id", "player_b_id")]
    f[keep].to_parquet(FEATURES, index=False, compression="zstd")
    log(f"frame: {len(f):,} matches, {f.shape[1]} columns; wrote {FEATURES.name}")
    cmp = comparisons(f)
    log("comparisons done")
    task_list = tasks()
    t1 = time.time()
    res = U.rundown(FEATURES, task_list, PREFIX, workers=WORKERS)
    harness_seconds = round(time.time() - t1, 1)
    rank = res["ranking"]
    ref = reference_check(rank)
    log(f"earlier ranking reproduced (leaders given Elo and the market): largest difference {ref['max_abs_difference']:.2e}")
    CATALOG.write_text(json.dumps(catalog(task_list, a_summary), indent=2, default=float), encoding="utf-8")
    corr = {}
    ev = f["evaluation"].to_numpy(dtype=bool)
    cols = ["elo|single"] + [f"{s}|single" for s in SYSTEMS] + ["rating_matchup|single", "elo_games|single",
                                                                  "adjperf_tpw|decayed", "ios_short|single"]
    for tour in C.TOURS:
        t = f["tour"].eq(tour).to_numpy() & ev
        corr[tour] = {k: {k2: round(float(v2), 4) for k2, v2 in v.items()} for k, v in f.loc[t, cols].corr().to_dict().items()}
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "note": "comparisons outside the harness; the harness's own output is stageB_results.json",
               "windows": {k: list(v) for k, v in WINDOWS.items()}, "eras": list(C.ERAS), "level_groups": U.LEVEL_GROUPS,
               "directional_only_below": C.DIRECTIONAL_ONLY_BELOW, "coin": float(np.log(2)), "systems": list(SYSTEMS),
               "names": NAMES, **cmp, "correlations_evaluation_matches": corr,
               "stage4_reference_reproduced": ref, "lines": res["lines"],
               "harness": {"rows": len(task_list), "workers": WORKERS, "seconds": harness_seconds,
                           "note": "the shared harness as revised on 2 Oct 2026 (16:48): lo / hi are paired four-week "
                                   "cluster t intervals, week_lo / week_hi calendar-week ones; point estimates and bands "
                                   "as before"},
               "chosen": a_summary["chosen"], "shared_code": RC.dependency_hashes()}
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}, {CATALOG.name}; total {summary['seconds']}s")
    show = ["tour", "id", "form", "alone_imp", "elo_imp", "glicko_cs_imp", "ttt_imp", "glicko2m_imp", "trueskill_imp",
            "market_imp", "market_lo", "market_hi", "reading"]
    print(rank[[c for c in show if c in rank.columns]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
