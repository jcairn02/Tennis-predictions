"""Stage A of "ideas borrowed from UFC-predictions", part 3: the rundown through the shared harness, the comparisons
outside it, and the catalog of scored rows.

The harness (common.rundown; walk-forward by season, a logistic regression without an intercept, 20 shuffled copies,
the family-wide line, the reading given Elo), per tour, on stageA_features.parquet:
    every BT variant, MESR and the two gaps    alone, given Elo, given the market (and given BT for the variants, MESR
                                               and the gaps; the primary BT also given MESR)
    elo|single                                 alone, given BT, given the market, given MESR
    each Stage 4 leader                        given Elo (the earlier reference, reproduced), given BT, given MESR and
                                               given the market, on the same pool
    bt_plus_ratings ([bt, rating_matchup])     given Elo and given the market
Women's rows are results-based (scored from 2013) except those reading box scores (rating_matchup, mu_points and
bt_plus_ratings: from 2019), as in Stage 4.

Outside the harness (stageA_summary.json; the harness's stageA_results.json is left as it writes it):
    raw log loss of P(A wins) from BT (and its variants), surface Elo (Stage 1's p_elo_surf_ret), MESR and the market,
    on the evaluation matches by window, era and level group, on the matches with odds and on those with an MESR;
    differences in milli-log-loss with 95% ranges from the per-match differences; Stage 1's numbers reproduced from
    stage1_results.json (asserted); calibration in ten bins of the forecast, 2019-2026, with a one-number slope; the
    share of the Elo-to-market gap BT closes, (Elo - BT) / (Elo - market) on the matches with odds; MESR's coverage;
    the leaders given Elo and given BT side by side; the earlier ranking's given-Elo numbers reproduced.

Writes, in data/studies/ufc_ideas/: stageA_ranking.csv, stageA_results.csv, stageA_null_copies.csv, stageA_results.json
(the harness), stageA_summary.json (the comparisons), stageA_catalog.json (one entry per scored row id).
With --catalog-only it rewrites stageA_catalog.json alone, from the task list and stageA_bt_summary.json.
Run after stageA_features.py: ./python.sh src/eda/ufc_ideas/stageA_rundown.py   (5 worker processes; ran in about a
minute on 2 Oct 2026, 54.8 seconds, the harness 51.3 of them: stageA_summary.json "seconds" and "harness")
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

FEATURES = U.OUT / "stageA_features.parquet"
PREFIX = U.OUT / "stageA"
SUMMARY = U.OUT / "stageA_summary.json"
CATALOG = U.OUT / "stageA_catalog.json"
BT = U.OUT / "stageA_bt.parquet"
MESR = U.OUT / "stageA_mesr.parquet"
BT_SUMMARY = U.OUT / "stageA_bt_summary.json"
STAGE1 = C.OUT / "stage1_results.json"
WORKERS = 5
EPS = 1e-12
WINDOWS = {"2013-2026": (2013, 2026), "2013-2018 (tuning)": (2013, 2018), "2019-2026": (2019, 2026),
           "2022-2026 (headline)": (2022, 2026)}
BINS = np.linspace(0.0, 1.0, 11)
# the Stage 4 leaders: id, form, name (Stage 4's), columns, box-score based (women scored from 2019)
LEADERS = [("rating_matchup", "single", "Serve and return ratings through the iid model", ["rating_matchup|single"], True),
           ("elo_games", "single", "Games-weighted Elo", ["elo_games|single"], False),
           ("sets_14d", "single", "Sets over the last 14 days", ["sets_14d|single"], False),
           ("mu_points", "52 weeks", "Serve against return: points", ["mu_points|52 weeks"], True),
           ("age", "single", "Age and age squared", ["age|single", "age|single|2"], False),
           ("surface_first", "single", "One of the first matches on this surface this season", ["surface_first|single"], False)]
DESCRIPTIONS = {
    "bt": "Bradley-Terry rating from wins and losses: every earlier result re-solved at once each week with a time "
          "decay and a ridge toward a newcomer anchor, plus the same event's earlier rounds; A's minus B's",
    "bt_games": "The same rating with each result weighted by the winner's share of the games over its mean in the "
                "warm-up and tuning years",
    "bt_nodecay": "The same rating without time decay (the best setting without decay)",
    "bt_surface": "The rating plus a per-surface deviation with its own ridge (the analogue of surface Elo)",
    "mesr": "Market-embedded skill rating: a rating solved from earlier closing odds instead of results, carried "
            "forward; missing where a player has no odds history",
    "mesr_minus_bt": "The market's view of the pair (MESR) minus the results' view (BT), both on the log-odds scale",
    "mesr_minus_elo": "The market's view of the pair (MESR) minus surface Elo on the log-odds scale",
    "elo": "The earlier study's surface Elo on the log-odds scale, scored as a feature on top of BT, MESR or the market",
    "rating_matchup": "The earlier study's leader: the serve and return ratings combined through the iid point model",
    "elo_games": "The earlier study's games-weighted Elo",
    "sets_14d": "The earlier study's sets played over the last two weeks (recent workload)",
    "mu_points": "The earlier study's serve-against-return points matchup over the last year",
    "age": "The earlier study's age and age squared (two inputs)",
    "surface_first": "The earlier study's flag for one of a player's first matches on the surface this season",
    "bt_plus_ratings": "Two inputs: the BT rating and the serve and return ratings through the iid model"}
FAMILY = {"bt": "BT rating", "bt_games": "BT rating", "bt_nodecay": "BT rating", "bt_surface": "BT rating",
          "bt_plus_ratings": "BT rating", "mesr": "MESR", "mesr_minus_bt": "MESR", "mesr_minus_elo": "MESR",
          "elo": "Elo", **{c[0]: "earlier leaders" for c in LEADERS}}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The harness tasks

def tasks(nodecay_separate: bool) -> list[dict]:
    B_BT, B_ME = {"bt": "p_bt"}, {"mesr": "p_mesr"}
    out = []
    for tour in C.TOURS:
        out.append(U.task(tour, "bt", "single", "Bradley-Terry rating (wins and losses)", FAMILY["bt"], ["bt|single"],
                          scores=("alone", "elo", "market", "mesr"), bases=B_ME))
        out.append(U.task(tour, "bt_games", "single", "Bradley-Terry rating weighted by the games margin", FAMILY["bt"],
                          ["bt_games|single"], scores=("alone", "elo", "market", "bt"), bases=B_BT))
        if nodecay_separate:
            out.append(U.task(tour, "bt_nodecay", "single", "Bradley-Terry rating without decay", FAMILY["bt"],
                              ["bt_nodecay|single"], scores=("alone", "elo", "market", "bt"), bases=B_BT))
        out.append(U.task(tour, "bt_surface", "single", "Surface Bradley-Terry rating", FAMILY["bt"], ["bt_surface|single"],
                          scores=("alone", "elo", "market", "bt"), bases=B_BT))
        out.append(U.task(tour, "mesr", "single", "Market-embedded skill rating (MESR)", FAMILY["mesr"], ["mesr|single"],
                          scores=("alone", "elo", "market", "bt"), bases=B_BT))
        out.append(U.task(tour, "mesr_minus_bt", "single", "MESR minus BT (market's view minus results' view)",
                          FAMILY["mesr"], ["mesr_minus_bt|single"], scores=("alone", "elo", "market", "bt"), bases=B_BT))
        out.append(U.task(tour, "mesr_minus_elo", "single", "MESR minus surface Elo", FAMILY["mesr"],
                          ["mesr_minus_elo|single"], scores=("alone", "elo", "market", "bt"), bases=B_BT))
        out.append(U.task(tour, "elo", "single", "Surface Elo (Stage 1)", FAMILY["elo"], ["elo|single"],
                          scores=("alone", "bt", "market", "mesr"), bases={**B_BT, **B_ME}))
        for cid, form, name, cols, box in LEADERS:
            out.append(U.task(tour, cid, form, name, FAMILY[cid], cols, scores=("elo", "bt", "mesr", "market"),
                              bases={**B_BT, **B_ME}, wta_box_from_2019=box))
        out.append(U.task(tour, "bt_plus_ratings", "single", "BT plus the ratings through the iid model", FAMILY["bt"],
                          ["bt|single", "rating_matchup|single"], scores=("elo", "market"), wta_box_from_2019=True))
    return out


# ------------------------------------------------------------------------------------------------
# Comparisons outside the harness

def ll_rows(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -np.where(y, np.log(p), np.log(1 - p))


def diff_stats(a: np.ndarray, b: np.ndarray) -> dict:
    """mean(a - b) in milli-log-loss with a 95% range from the per-match differences."""
    d = 1000 * (a - b)
    n = len(d)
    if n < 2:
        return {"n": int(n), "milli": float(d.mean()) if n else np.nan, "lo": np.nan, "hi": np.nan,
                "directional_only": True}
    se = d.std(ddof=1) / np.sqrt(n)
    return {"n": int(n), "milli": float(d.mean()), "lo": float(d.mean() - 1.96 * se), "hi": float(d.mean() + 1.96 * se),
            "directional_only": bool(n < C.DIRECTIONAL_ONLY_BELOW)}


def block(L: dict, mask: np.ndarray, keys: list[str], market: bool) -> dict:
    """Log loss of each forecaster on the rows of mask, the BT - Elo difference, and (with the market) the gap
    closed: (Elo - forecaster) / (Elo - market)."""
    n = int(mask.sum())
    out = {"n": n, "directional_only": bool(n < C.DIRECTIONAL_ONLY_BELOW), "ll": {}}
    if n == 0:
        return out
    for k in keys:
        out["ll"][k] = float(L[k][mask].mean())
    out["elo_minus_bt"] = diff_stats(L["elo"][mask], L["bt"][mask])
    out["elo_minus"] = {k: diff_stats(L["elo"][mask], L[k][mask]) for k in keys if k != "elo"}
    if market:
        out["elo_minus_market"] = diff_stats(L["elo"][mask], L["market"][mask])
        out["bt_minus_market"] = diff_stats(L["bt"][mask], L["market"][mask])
        room = out["ll"]["elo"] - out["ll"]["market"]
        out["gap_closed"] = {k: (out["ll"]["elo"] - out["ll"][k]) / room for k in keys if k not in ("elo", "market")}
    return out


def calibration(p: np.ndarray, y: np.ndarray) -> dict:
    """Ten equal bins of the forecast P(A wins): matches, mean forecast, A's win share (95% range); and the
    calibration slope (a_won on logit(p), no intercept: below 1 over-confident, above 1 under-confident)."""
    bins = []
    k = np.clip(np.digitize(p, BINS[1:-1]), 0, 9)
    for i in range(10):
        m = k == i
        n = int(m.sum())
        if n == 0:
            bins.append({"bin": f"{BINS[i]:.1f}-{BINS[i + 1]:.1f}", "n": 0})
            continue
        sh = float(y[m].mean())
        se = np.sqrt(max(sh * (1 - sh), 1e-12) / n)
        bins.append({"bin": f"{BINS[i]:.1f}-{BINS[i + 1]:.1f}", "n": n, "mean_forecast": float(p[m].mean()),
                     "won": sh, "won_lo": sh - 1.96 * se, "won_hi": sh + 1.96 * se,
                     "won_minus_forecast_points": 100 * (sh - float(p[m].mean()))})
    x = logit(np.clip(p, 1e-9, 1 - 1e-9))
    b = 1.0
    for _ in range(50):
        q = expit(b * x)
        g = float(np.sum(x * (y - q)))
        h = float(np.sum(x * x * q * (1 - q)))
        b += g / h
        if abs(g / h) < 1e-12:
            break
    q = expit(b * x)
    se = 1 / np.sqrt(float(np.sum(x * x * q * (1 - q))))
    return {"bins": bins, "slope": b, "slope_lo": b - 1.96 * se, "slope_hi": b + 1.96 * se, "n": int(len(p)),
            "max_abs_gap_points_bins_300": max((abs(x_["won_minus_forecast_points"]) for x_ in bins
                                                if x_["n"] >= C.DIRECTIONAL_ONLY_BELOW), default=np.nan)}


def comparisons(f: pd.DataFrame) -> dict:
    bt = pd.read_parquet(BT).set_index("match_id").reindex(f["match_id"])
    me = pd.read_parquet(MESR).set_index("match_id").reindex(f["match_id"])
    y = f["a_won"].to_numpy(dtype=bool)
    P = {"bt": f["p_bt"].to_numpy(dtype="float64"), "elo": f["p_elo"].to_numpy(dtype="float64"),
         "market": f["p_mkt"].to_numpy(dtype="float64"), "mesr": f["p_mesr"].to_numpy(dtype="float64"),
         "mesr_snap": expit(me["mesr_snap_a"].to_numpy(dtype="float64") - me["mesr_snap_b"].to_numpy(dtype="float64"))}
    for k in ("bt_games", "bt_nodecay", "bt_surface"):
        P[k] = expit(bt[f"{k}_a"].to_numpy(dtype="float64") - bt[f"{k}_b"].to_numpy(dtype="float64"))
    L = {k: ll_rows(v, y) for k, v in P.items()}
    ev = f["evaluation"].to_numpy(dtype=bool)
    year, era, grp = f["year"].to_numpy(), f["era"].to_numpy(), f["group"].to_numpy()
    odds = np.isfinite(P["market"])
    has_me = np.isfinite(P["mesr"]) & np.isfinite(P["mesr_snap"])
    BTK = ["bt", "bt_games", "bt_nodecay", "bt_surface", "elo"]
    out = {"raw": {}, "by_era": {}, "by_level": {}, "calibration_2019_2026": {}, "gap_closed_2022_2026": {},
           "mesr_coverage": {}}
    for tour in C.TOURS:
        t = (f["tour"].to_numpy() == tour) & ev
        out["raw"][tour], out["by_era"][tour], out["by_level"][tour] = {}, {}, {}

        def cell(m):
            return {"all": block(L, m, BTK, False), "odds": block(L, m & odds, BTK + ["market"], True),
                    "mesr": block(L, m & has_me, ["mesr", "mesr_snap", "bt", "elo"], False),
                    "mesr_odds": block(L, m & has_me & odds, ["mesr", "mesr_snap", "bt", "elo", "market"], True)}
        for w, (a, b) in WINDOWS.items():
            out["raw"][tour][w] = cell(t & (year >= a) & (year <= b))
        for e in C.ERAS:
            out["by_era"][tour][e] = cell(t & (era == e))
        for g in U.LEVEL_GROUPS:
            out["by_level"][tour][g] = cell(t & (grp == g))
        late = t & (year >= 2019)
        out["calibration_2019_2026"][tour] = {"bt": calibration(P["bt"][late], y[late]),
                                              "elo": calibration(P["elo"][late], y[late])}
        hw = out["raw"][tour]["2022-2026 (headline)"]["odds"]
        out["gap_closed_2022_2026"][tour] = {"n": hw["n"], **{k: hw["gap_closed"][k] for k in hw["gap_closed"]},
                                             "elo_minus_market_milli": hw["elo_minus_market"]["milli"],
                                             "elo_minus_bt_milli": hw["elo_minus_bt"]["milli"]}
        cov = {}
        me_any = np.isfinite(P["mesr"])
        for w, (a, b) in WINDOWS.items():
            m = t & (year >= a) & (year <= b)
            cov[w] = {"evaluation": int(m.sum()), "with_mesr": int((m & me_any).sum()),
                      "with_odds": int((m & odds).sum()), "with_odds_and_mesr": int((m & odds & me_any).sum()),
                      "share_of_odds_matches_with_mesr": float((m & odds & me_any).sum() / max(1, (m & odds).sum())),
                      "share_of_evaluation_with_mesr": float((m & me_any).sum() / max(1, m.sum())),
                      "with_both_mesr_forms": int((m & has_me).sum())}
        out["mesr_coverage"][tour] = cov
    out["diagnostics"] = diagnostics(f, L, ev)
    return out


def diagnostics(f: pd.DataFrame, L: dict, ev: np.ndarray) -> dict:
    """Where BT loses to Elo (raw log loss, Elo minus BT, milli-log-loss; positive: BT better), on the evaluation
    matches: by the fewer snapshot edges of the two players (newcomers get the anchor), by the longer layoff of the two
    (days since the player's previous date with a rating-moving match; long layoffs decay BT's data), by Grand Slam
    qualifying round, by season, and by level after recalibrating each forecast by its own slope (in-sample, a reading
    of ordering apart from calibration)."""
    bt = pd.read_parquet(BT, columns=["match_id", "n_a", "n_b"]).set_index("match_id").reindex(f["match_id"])
    m = C.load_matches(["match_id", "tournament_date", "status", "player_a_id", "player_b_id", "round"])
    long = pd.concat([m[["tournament_date", "status", c]].rename(columns={c: "pid"}) for c in ("player_a_id", "player_b_id")])
    long = long[long["status"].isin(["completed", "retired"])].drop_duplicates(["pid", "tournament_date"])
    long = long.sort_values(["pid", "tournament_date"])
    long["prev"] = long.groupby("pid")["tournament_date"].shift(1)
    last = long.set_index(["pid", "tournament_date"])["prev"]
    mm = m.set_index("match_id").reindex(f["match_id"])
    days = {}
    for side in ("player_a_id", "player_b_id"):
        # the player's previous date with a rated match before this match's date
        key = pd.MultiIndex.from_arrays([mm[side].to_numpy(), mm["tournament_date"].to_numpy()])
        prev = last.reindex(key).to_numpy()
        days[side] = (mm["tournament_date"].to_numpy() - prev) / np.timedelta64(1, "D")
    layoff = np.fmax(days["player_a_id"], days["player_b_id"])           # missing only if neither has an earlier date
    fewest = np.minimum(bt["n_a"].to_numpy(), bt["n_b"].to_numpy())
    year, grp, rnd = f["year"].to_numpy(), f["group"].to_numpy(), mm["round"].to_numpy()
    y = f["a_won"].to_numpy(dtype=bool)
    edges_bins = [(-1, 0, "0"), (0, 5, "1-5"), (5, 20, "6-20"), (20, 50, "21-50"), (50, 100, "51-100"), (100, 10 ** 9, "over 100")]
    lay_bins = [(-1, 14, "up to 14"), (14, 35, "15-35"), (35, 90, "36-90"), (90, 180, "91-180"), (180, 365, "181-365"),
                (365, 10 ** 9, "over 365")]
    out = {}
    for tour in C.TOURS:
        t = (f["tour"].to_numpy() == tour) & ev

        def cut(vals, bins):
            ok = t & np.isfinite(vals)
            return {lab: diff_stats(L["elo"][ok & (vals > lo) & (vals <= hi)], L["bt"][ok & (vals > lo) & (vals <= hi)])
                    for lo, hi, lab in bins}
        recal = {}
        for g in U.LEVEL_GROUPS:
            mk = t & (grp == g)
            if mk.sum() < 2:
                continue
            res = {}
            for k in ("bt", "elo"):
                p = f["p_bt" if k == "bt" else "p_elo"].to_numpy(dtype="float64")[mk]
                b = calibration(p, y[mk])["slope"]
                res[k] = ll_rows(expit(b * logit(np.clip(p, 1e-9, 1 - 1e-9))), y[mk])
                res[f"{k}_slope"] = b
            recal[g] = {**diff_stats(res["elo"], res["bt"]), "slope_bt": res["bt_slope"], "slope_elo": res["elo_slope"]}
        out[tour] = {"fewest_snapshot_edges": cut(fewest.astype("float64"), edges_bins),
                     "longest_layoff_days": cut(layoff, lay_bins),
                     "grand_slam_qualifying_by_round": {r: diff_stats(L["elo"][t & (grp == "GSQ") & (rnd == r)],
                                                                      L["bt"][t & (grp == "GSQ") & (rnd == r)])
                                                        for r in ("Q1", "Q2", "Q3")},
                     "season": {int(s): diff_stats(L["elo"][t & (year == s)], L["bt"][t & (year == s)])
                                for s in range(C.EVAL_YEARS[0], C.EVAL_YEARS[-1] + 1)},
                     "no_snapshot_edge_by_season": {int(s): diff_stats(L["elo"][t & (year == s) & (fewest == 0)],
                                                                       L["bt"][t & (year == s) & (fewest == 0)])
                                                    for s in range(C.EVAL_YEARS[0], C.EVAL_YEARS[-1] + 1)},
                     "level_after_recalibration": recal,
                     "note": "Elo's log loss minus BT's (milli-log-loss): positive is BT better"}
    return out


def stage1_reproduced(cmp: dict) -> dict:
    """Stage 1's surface Elo and market log losses (stage1_results.json), recomputed here on the same matches."""
    s1 = json.loads(STAGE1.read_text(encoding="utf-8"))
    rows, worst = [], 0.0
    for h in s1["headline"]:
        mine = cmp["raw"][h["tour"]][h["window"]]
        pairs = [("all evaluation, surface Elo", h["p_elo_surf_ret"], mine["all"]["ll"]["elo"], h["n"], mine["all"]["n"]),
                 ("with odds, surface Elo", h["market_subset"]["p_elo_surf_ret"], mine["odds"]["ll"]["elo"],
                  h["market_subset"]["n"], mine["odds"]["n"]),
                 ("with odds, market", h["market_subset"]["p_market"], mine["odds"]["ll"]["market"],
                  h["market_subset"]["n"], mine["odds"]["n"])]
        for what, theirs, ours, n1, n2 in pairs:
            d = abs(theirs - ours)
            worst = max(worst, d)
            rows.append({"tour": h["tour"], "window": h["window"], "what": what, "stage1": theirs, "here": ours,
                         "stage1_n": int(n1), "here_n": int(n2)})
            assert int(n1) == int(n2) and d < 1e-12, rows[-1]
    for r in s1["margins"]["era"]["rows"]:
        mine = cmp["by_era"][r["tour"]][r["era"]]
        for what, theirs, ours in [("era, surface Elo", r["p_elo_surf_ret"], mine["all"]["ll"]["elo"]),
                                   ("era, market", r["p_market__m"], mine["odds"]["ll"]["market"])]:
            d = abs(theirs - ours)
            worst = max(worst, d)
            rows.append({"tour": r["tour"], "window": r["era"], "what": what, "stage1": theirs, "here": ours})
            assert d < 1e-9, rows[-1]
    return {"checked": len(rows), "max_abs_difference": worst, "rows": rows}


def date_convention() -> dict:
    """The time rule reads a 'week' as a tournament date (stage1_baselines.elo_pass; BT follows it for comparability).
    A match dated later in a calendar (Monday) week than another event of that week sees that event in full. Counted
    per tour: evaluation matches so placed, and those where a player had a rating-moving match at an earlier date of
    the same Monday-week, split by the weekday of the later date (Sunday starts, such as Monte Carlo or Roland Garros,
    begin after the earlier week's events end; Tuesday-Saturday dates, such as Indian Wells or Madrid, overlap them)."""
    m = C.load_matches(["tour", "evaluation", "status", "tournament_date", "player_a_id", "player_b_id"])
    m["monday"] = m["tournament_date"] - pd.to_timedelta(m["tournament_date"].dt.dayofweek, unit="D")
    mv = m[m["status"].isin(["completed", "retired"])]
    pl = pd.concat([mv[["tour", "monday", "tournament_date", c]].rename(columns={c: "pid"})
                    for c in ("player_a_id", "player_b_id")])
    first = pl.groupby(["tour", "monday", "pid"])["tournament_date"].min()
    wk_first = mv.groupby(["tour", "monday"])["tournament_date"].min()
    fa = pd.MultiIndex.from_frame(m[["tour", "monday", "player_a_id"]])
    fb = pd.MultiIndex.from_frame(m[["tour", "monday", "player_b_id"]])
    ta = first.reindex(fa).to_numpy()
    tb = first.reindex(fb).to_numpy()
    d = m["tournament_date"].to_numpy()
    later = d > wk_first.reindex(pd.MultiIndex.from_frame(m[["tour", "monday"]])).to_numpy()
    overlap = (ta < d) | (tb < d)
    sunday = m["tournament_date"].dt.dayofweek.to_numpy() == 6
    ev = m["evaluation"].to_numpy(dtype=bool)
    out = {}
    for tour in C.TOURS:
        t = (m["tour"].to_numpy() == tour) & ev
        out[tour] = {"evaluation_matches_dated_later_in_their_week": int((t & later).sum()),
                     "with_a_player_from_an_earlier_date_that_week": int((t & later & overlap).sum()),
                     "of_which_sunday_dated": int((t & later & overlap & sunday).sum()),
                     "of_which_tuesday_to_saturday": int((t & later & overlap & ~sunday).sum())}
    return out


def side_by_side(rank: pd.DataFrame) -> list:
    """The leaders (and BT, Elo, MESR) with each base's improvement, range, band and line, side by side."""
    keep = ["tour", "id", "form", "name", "group", "inputs", "scored_from", "reading"]
    out = []
    for _, r in rank.iterrows():
        rec = {k: (r[k] if not (isinstance(r[k], float) and np.isnan(r[k])) else None) for k in keep}
        for s in ("alone", "elo", "bt", "mesr", "market"):
            if f"{s}_imp" not in r or pd.isna(r.get(f"{s}_imp")):
                continue
            rec[s] = {k: (None if pd.isna(r.get(f"{s}_{k}")) else (bool(r[f"{s}_{k}"]) if k in ("above_band", "clears_line")
                                                                   else r[f"{s}_{k}"] if k == "observed" else float(r[f"{s}_{k}"])))
                      for k in ("imp", "lo", "hi", "band_min", "band_max", "z", "above_band", "clears_line", "observed",
                                "scored", "eligible", "coverage", "2019-2026", "2022-2026", "coef")
                      if f"{s}_{k}" in r}
        out.append(rec)
    return out


def reference_check(rank: pd.DataFrame) -> dict:
    """The leaders' given-Elo and given-market scores against the earlier study's ranking (stage4_ranking.csv)."""
    ref = U.stage4_reference([c[0] for c in LEADERS])
    rows, worst = [], 0.0
    for cid, form, _, _, _ in LEADERS:
        for tour in C.TOURS:
            a = rank[(rank["id"] == cid) & (rank["form"] == form) & (rank["tour"] == tour)].iloc[0]
            b = ref[(ref["id"] == cid) & (ref["form"] == form) & (ref["tour"] == tour)].iloc[0]
            for s in ("elo", "market"):
                for k in ("imp", "lo", "hi", "band_min", "band_max", "scored"):
                    d = abs(float(a[f"{s}_{k}"]) - float(b[f"{s}_{k}"]))
                    worst = max(worst, d)
            rows.append({"tour": tour, "id": cid, "form": form, "elo_imp_here": float(a["elo_imp"]),
                         "elo_imp_stage4": float(b["elo_imp"]), "market_imp_here": float(a["market_imp"]),
                         "market_imp_stage4": float(b["market_imp"])})
    return {"max_abs_difference": worst, "rows": rows}


def catalog(rank: pd.DataFrame, task_list: list[dict], bts: dict) -> list:
    ch = bts["chosen"]
    tuned = {"bt": {t: {"constants": ch[t]["bt"], "tuned_on": "2013-2018 evaluation matches"} for t in C.TOURS},
             "bt_games": {t: {"constants": ch[t]["bt"], "games_scale": bts["games_scale"][t],
                              "note": "the primary's constants; each result's weight times the games share over the scale"}
                          for t in C.TOURS},
             "bt_nodecay": {t: {"constants": ch[t]["bt_nodecay"], "tuned_on": "the best grid row without decay"}
                            for t in C.TOURS},
             "bt_surface": {t: {"constants": ch[t]["bt"], "lam_u": ch[t]["bt_surface_lam_u"],
                                "tuned_on": "lam_u on 2013-2018, the other constants the primary's"} for t in C.TOURS},
             "mesr": {t: {"constants": ch[t]["mesr"], "tuned_on": "2013-2018 evaluation matches with odds"} for t in C.TOURS}}
    tuned["mesr_minus_bt"] = {t: {"mesr": ch[t]["mesr"], "bt": ch[t]["bt"]} for t in C.TOURS}
    tuned["mesr_minus_elo"] = {t: {"mesr": ch[t]["mesr"]} for t in C.TOURS}
    tuned["bt_plus_ratings"] = {t: {"bt": ch[t]["bt"]} for t in C.TOURS}
    out = []
    for cid in dict.fromkeys(t["id"] for t in task_list):
        tk = [t for t in task_list if t["id"] == cid]
        out.append({"id": cid, "name": tk[0]["name"], "family": FAMILY[cid], "description": DESCRIPTIONS[cid],
                    "form": tk[0]["form"], "columns": tk[0]["cols"],
                    "tuned": tuned.get(cid, "none in this stage (the earlier study's constants)" if FAMILY[cid] ==
                                       "earlier leaders" else "Stage 1's frozen constants" if cid == "elo" else None),
                    "base_variants": {t["tour"]: {s: (b if b else "coin") for s, b in t["bases"].items()} for t in tk},
                    "scored_from": {t["tour"]: t["from"] for t in tk}})
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    bts = json.loads(BT_SUMMARY.read_text(encoding="utf-8"))
    nodecay_separate = not all(bts["nodecay_is_primary"].values())
    task_list = tasks(nodecay_separate)
    if "--catalog-only" in argv:                    # rewrite stageA_catalog.json alone (no scoring)
        CATALOG.write_text(json.dumps(catalog(None, task_list, bts), indent=2, default=float), encoding="utf-8")
        log(f"wrote {CATALOG.name}")
        return 0
    log(f"{len(task_list)} rows; no-decay BT scored separately: {nodecay_separate}")
    t1 = time.time()
    res = U.rundown(FEATURES, task_list, PREFIX, workers=WORKERS)
    harness_seconds = round(time.time() - t1, 1)
    rank = res["ranking"]
    f = pd.read_parquet(FEATURES)
    f["era"] = f["era"].astype(object).fillna("").astype(str)
    cmp = comparisons(f)
    rep = stage1_reproduced(cmp)
    log(f"Stage 1 reproduced: {rep['checked']} numbers, largest difference {rep['max_abs_difference']:.2e}")
    ref = reference_check(rank)
    log(f"earlier ranking reproduced (leaders, given Elo and the market): largest difference {ref['max_abs_difference']:.2e}")
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "note": "the comparisons outside the harness; the harness's own output is stageA_results.json",
               "windows": {k: list(v) for k, v in WINDOWS.items()}, "eras": list(C.ERAS), "level_groups": U.LEVEL_GROUPS,
               "directional_only_below": C.DIRECTIONAL_ONLY_BELOW, "coin": float(np.log(2)),
               **cmp, "stage1_reproduced": rep, "stage4_reference_reproduced": ref,
               "date_convention": date_convention(),
               "elo_constants_stage1": [c for c in json.loads((C.OUT / "stage1_baselines_summary.json").read_text(
                   encoding="utf-8"))["chosen"] if c["rule"] == "ret"],
               "side_by_side": side_by_side(rank), "lines": res["lines"],
               "harness": {"rows": len(task_list), "workers": WORKERS, "seconds": harness_seconds,
                           "nodecay_scored_separately": nodecay_separate},
               "ratings": {k: bts[k] for k in ("chosen", "flatness", "checks", "probes", "top10_2026", "timings",
                                               "mesr_rms_gap_chosen", "seconds", "games_scale", "design", "grids",
                                               "full_passes", "tuning_pass_seconds")}}
    pr = bts["probes"]
    summary["probe_totals"] = {
        "cuts_real": int(sum(p["cuts"] for p in pr if p["what"] != "bt_leaky")),
        "protected_checked_real": int(sum(p["protected_matches_checked"] for p in pr if p["what"] != "bt_leaky")),
        "protected_changed_real": int(sum(p["protected_matches_changed"] for p in pr if p["what"] != "bt_leaky")),
        "protected_changed_leaky": int(sum(p["protected_matches_changed"] for p in pr if p["what"] == "bt_leaky")),
        "passes_probed": sorted({p["what"] for p in pr if p["what"] != "bt_leaky"})}
    import pyarrow.parquet as pq
    summary["table_rows"] = {"stageA_bt.parquet": int(pq.ParquetFile(BT).metadata.num_rows),
                             "stageA_mesr.parquet": int(pq.ParquetFile(MESR).metadata.num_rows)}
    summary["ratings"]["edge_drop_age_years_chosen"] = {
        t: {"half_life": bts["chosen"][t]["bt"]["half_life"],
            "years": float(bts["chosen"][t]["bt"]["half_life"]) * float(np.log2(1 / bts["design"]["min_decay_weight"]))}
        for t in C.TOURS if bts["chosen"][t]["bt"]["half_life"] != "none"}
    CATALOG.write_text(json.dumps(catalog(rank, task_list, bts), indent=2, default=float), encoding="utf-8")
    summary["files_mb"] = {p.name: round(p.stat().st_size / 1e6, 2) for p in sorted(U.OUT.glob("stageA_*"))
                           if p.name != SUMMARY.name}
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}, {CATALOG.name}; total {summary['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
