"""Stage C of the study "ideas borrowed from UFC-predictions", part 2: fatigue. Does a player degrade as a match gets
long? Three measurements, each turned into pre-match features for the shared pool (common.load_pool()).

1. Late-match decline, from the Grand Slam point-by-point files (stage2_pbp_points.parquet, the points of 9,948
   validated main-draw matches of 2011-2024 in order; stage2_pbp_players.parquet, the players; each player linked to a
   Stage 0 id within the same Slam's main draw as stage4_features.pbp_history links them). Per match:
       d = (own serve-point win rate in the third set onward - in the first two sets)
           - (the opponent's same change), in points won per point (player 2's d is minus player 1's)
       u = 1 / (1/n_own_late + 1/n_own_early + 1/n_opp_late + 1/n_opp_early), the "effective points": d's chance
           variance is about p(1 - p) / u, so u weights a match in every mean and in the reliability
   Variants for the reliability only: the first 150 points against the rest; and, for the men's best-of-five matches,
   the first two sets against the third alone (always played, so no match is selected by how it went).
   The trait: a player's u-weighted mean of d over their earlier Slams, shrunk toward 0 (the mean of d over all
   player-matches is exactly 0) with Stage 3's empirical-Bayes constant (stage3_traits.eb_constants on player-seasons
   of 2011-2018). Reliability: Stage 3's split-half correlation across a player's matches (stage3_traits.split_half,
   career units), beside the same measure on Stage 2's pure-luck replays of the same matches (stage2_pbp.replay_luck:
   every point an independent draw at de-noised rates, so no fatigue exists in them): a reliability no higher than
   the replays' is not a fatigue trait. Features (A - B): late_decline|career; late_decline_x_bo5 (x 1[best of five,
   from the source's record]); late_decline_x_long (x the match's expected length: closeness = 1 - 2|p - 1/2| with p
   the Stage 3 ratings' probability through the iid model, expit(rating_matchup|single); 1 for an even match, which
   is expected to run long, 0 for a certain one).
2. The "grinder" trait, from box scores and minutes. Per player-match (completed, standard format, a box score, minutes
   with 15 to 120 seconds per point): the residual points r = total points won - the Stage 3 expectation
   (serve points x p_serve_own + return points x (1 - p_serve_opp), the iid points share at the pre-match ratings),
   over the points played u. "Long" = minutes per set above the tour's 75th percentile of 2010-2018 (fixed). A
   player's grinder value = their residual share in long matches minus in short ones, G = R_L / U_L - R_S / U_S, shrunk
   as a contrast: G x U / (U + K) with U = 1 / (1/U_L + 1/U_S) and K by eb_constants' method of moments on
   player-seasons of 2010-2018. Reliability: split-half correlation of G across a player's matches, beside the same on
   an iid replay of every match (stage2_iid.simulate's rules at Stage 2's de-noised rates, with the sets counted so
   that "long" can be read as points per set): long matches are close ones, so a favourite's residual is low in them by
   selection alone, and the replay shows how much of G that explains. Features: grinder|career, grinder|52 weeks,
   grinder_x_bo5.
3. Load x fatigue: Stage 4's sets (minutes) over the last 14 days, log(1 + x), times the late-decline trait, A's
   product minus B's: sets_14d_x_decline, minutes_14d_x_decline.

Checks: the per-row 14-day load equals Stage 4's sets_14d|single and minutes_14d|single; the set-counting simulator
equals stage2_iid.simulate draw for draw (tests); a probe cut by date, event and round on a 2023-2024 slice with cuts
before and at Wimbledon 2024, so that point-by-point records after the cut exist and are redrawn.

Writes, in data/studies/ufc_ideas/:
    stageC_fatigue_part.parquet   match_id (the pool's order) and every fatigue feature column (A - B)
    stageC_fatigue_players.csv    per player: the late-decline and grinder traits at the end of the data (shrunk and
                                  raw) and their samples, for the sanity check
    stageC_fatigue_part.json      the constants (K, the long-match line), the reliability (real and pure luck), the
                                  selection diagnostics, coverage, checks, the probe, timings; folded into
                                  stageC_summary.json by stageC_rundown.py

Run: ./python.sh src/eda/ufc_ideas/stageC_fatigue.py   (about 2 minutes; 116 seconds on 2 Oct 2026; measured runtime in
stageC_fatigue_part.json, timings)
"""
from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_anatomy as A2  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic import stage2_pbp as PBP  # noqa: E402
from src.eda.predictability_diagnostic import stage3_traits as T  # noqa: E402
from src.eda.predictability_diagnostic import stage4_candidates as P  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as F  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402
from src.eda.ufc_ideas import stageC_sos as S  # noqa: E402

PART = U.OUT / "stageC_fatigue_part.parquet"
PART_JSON = U.OUT / "stageC_fatigue_part.json"
PLAYERS_CSV = U.OUT / "stageC_fatigue_players.csv"
PBP_POINTS = C.OUT / "stage2_pbp_points.parquet"
PBP_PLAYERS = C.OUT / "stage2_pbp_players.parquet"

SEED = 20261003
PBP_K_YEARS = range(2011, 2019)            # the point-by-point seasons for the constant (Stage 4's for big points)
K_YEARS = range(2010, 2019)                # box-score constants and the long-match line
TUNE_YEARS = range(2013, 2019)
LATE_SET = 3                               # the late segment starts at the third set
SPLIT_POINTS = 150                         # the points variant: the first 150 points against the rest
SPP_RANGE = (15.0, 120.0)                  # plausible seconds per point; minutes outside are not read
LONG_Q = 0.75                              # long = minutes per set above this quantile (tour, 2010-2018)
REPLAYS = 3                                # pure-luck replays for the benchmark
DRAWS = 20                                 # split-half draws per n
N_GRID_PBP = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
N_GRID_BOX = [5, 10, 15, 20, 30, 40, 50, 60]
MIN_UNITS = 30                             # a correlation needs 30 players (stage3_traits.MIN_UNITS)
FIT_UNITS = C.DIRECTIONAL_ONLY_BELOW       # the Spearman-Brown fit uses n's with 300+ players where it can
K_FALLBACK_GRID = (100.0, 300.0, 1000.0, 3000.0, 10000.0)   # only if empirical Bayes finds no spread
BOOT = 200
WINDOW14 = 14
SLAM_FILES = {"ausopen": "Australian Open", "frenchopen": "Roland Garros", "wimbledon": "Wimbledon", "usopen": "US Open"}
FEATURES = {
    "late_decline|career": "Late-match decline (Grand Slam point by point), career",
    "late_decline_x_bo5|single": "Late-match decline x best of five",
    "late_decline_x_long|single": "Late-match decline x expected match length (closeness)",
    "grinder|career": "Grinder: points won above expectation in long minus short matches, career",
    "grinder|52 weeks": "Grinder: points won above expectation in long minus short matches, last 52 weeks",
    "grinder_x_bo5|single": "Grinder (career) x best of five",
    "sets_14d_x_decline|single": "Sets over the last 14 days x late-match decline",
    "minutes_14d_x_decline|single": "Minutes over the last 14 days x late-match decline",
}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def seeded(*parts) -> np.random.Generator:
    return np.random.default_rng([SEED] + [zlib.crc32(str(p).encode("utf-8")) for p in parts])


# ------------------------------------------------------------------------------------------------
# 1. Late-match decline from the point-by-point files

def match_change(pts: pd.DataFrame, early: np.ndarray, late: np.ndarray) -> pd.DataFrame:
    """Per match (the order of first appearance): player 1's change d1 = (late - early serve-point win rate) minus
    player 2's, and the effective points u; d1 missing (u 0) unless both players served in both segments."""
    code, mids = pd.factorize(pts["match_id"])
    srv1 = pts["srv1"].to_numpy(dtype=bool)
    sw = srv1 == pts["won1"].to_numpy(dtype=bool)            # the server won the point
    M_ = len(mids)

    def cnt(mask):
        return np.bincount(code[mask], minlength=M_).astype("float64")
    n_e1, w_e1 = cnt(early & srv1), cnt(early & srv1 & sw)
    n_l1, w_l1 = cnt(late & srv1), cnt(late & srv1 & sw)
    n_e2, w_e2 = cnt(early & ~srv1), cnt(early & ~srv1 & sw)
    n_l2, w_l2 = cnt(late & ~srv1), cnt(late & ~srv1 & sw)
    ok = (n_e1 > 0) & (n_l1 > 0) & (n_e2 > 0) & (n_l2 > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        d1 = (w_l1 / n_l1 - w_e1 / n_e1) - (w_l2 / n_l2 - w_e2 / n_e2)
        u = 1.0 / (1.0 / n_l1 + 1.0 / n_e1 + 1.0 / n_l2 + 1.0 / n_e2)
    return pd.DataFrame({"match_id": np.asarray(mids), "d1": np.where(ok, d1, np.nan), "u": np.where(ok, u, 0.0),
                         "n_early_1": n_e1, "n_late_1": n_l1, "n_early_2": n_e2, "n_late_2": n_l2})


def segments(pts: pd.DataFrame) -> dict:
    """The early / late masks of each variant, point by point (points in match order within each match)."""
    s = pts["set_no"].to_numpy()
    idx = pts.groupby("match_id", sort=False).cumcount().to_numpy()
    return {"sets": (s < LATE_SET, s >= LATE_SET),
            "set3": (s < LATE_SET, s == LATE_SET),
            "points150": (idx < SPLIT_POINTS, idx >= SPLIT_POINTS)}


def player_changes(pts: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match (sides 1 and 2): d and u of every variant (d_sets, u_sets, d_set3, ...)."""
    seg = segments(pts)
    base = None
    for name, (early, late) in seg.items():
        mc = match_change(pts, early, late)
        if base is None:
            base = mc[["match_id"]].copy()
        base[f"d1_{name}"], base[f"u_{name}"] = mc["d1"].to_numpy(), mc["u"].to_numpy()
    tour = pts.groupby("match_id", sort=False)["tour"].first()
    base["tour"] = tour.reindex(base["match_id"]).to_numpy()
    out = []
    for side, sign in ((1, 1.0), (2, -1.0)):
        r = base[["match_id", "tour"]].copy()
        r["side"] = side
        for name in seg:
            r[f"d_{name}"] = sign * base[f"d1_{name}"].to_numpy()
            r[f"u_{name}"] = base[f"u_{name}"].to_numpy()
        out.append(r)
    pm = pd.concat(out, ignore_index=True)
    # the women's matches are best of three: the "set3" variant is the men's (best of five) only
    w = pm["tour"].eq("wta").to_numpy()
    pm.loc[w, "d_set3"] = np.nan
    pm.loc[w, "u_set3"] = 0.0
    return pm


def link_players(rows: pd.DataFrame) -> pd.DataFrame:
    """Each point-by-point player-match (match_id, side) linked to a Stage 0 id within the same Slam's main draw, as
    stage4_features.pbp_history links them, with the Slam's tournament Monday (day), the year and the result."""
    p = pd.read_parquet(PBP_PLAYERS, columns=["match_id", "tour", "player", "side", "won_match"])
    p["year"] = p["match_id"].str.slice(0, 4).astype(int)
    slam = {"ausopen": "australian open", "frenchopen": "roland garros", "wimbledon": "wimbledon", "usopen": "us open"}
    p["slam"] = p["match_id"].str.split("-").str[1].map(slam)
    gs = rows[rows["level"].eq("GS") & ~rows["qualifying"].astype(bool)][["tour", "year", "tournament_name", "day",
                                                                          "player_id", "pcode"]]
    gs = gs.assign(slam=gs["tournament_name"].str.lower())
    names = C.load_match_players(["match_id", "player_id", "player_name"], with_order=False).drop_duplicates(
        "player_id").set_index("player_id")["player_name"]
    gs = gs.assign(player_name=gs["player_id"].map(names))
    days = gs.drop_duplicates(["tour", "year", "slam"])[["tour", "year", "slam", "day"]]
    p = p.merge(days, on=["tour", "year", "slam"], how="left")
    draw = {k: [(pid, P.name_parts(nm)[0]) for pid, nm in g[["player_id", "player_name"]].drop_duplicates().itertuples(index=False)]
            for k, g in gs.groupby(["tour", "year", "slam"])}
    p["player_id"] = [P.link_in_event(nm, draw.get((t, y, s), [])) for nm, t, y, s in
                      p[["player", "tour", "year", "slam"]].itertuples(index=False)]
    pc = pd.Series(rows["pcode"].to_numpy(), index=rows["player_id"].to_numpy())
    pc = pc[~pc.index.duplicated()]
    p["pcode"] = pc.reindex(p["player_id"]).to_numpy()
    p["linked"] = p["player_id"].notna() & p["day"].notna() & p["pcode"].notna()
    p["pcode"] = p["pcode"].fillna(-1).astype("int64")
    p["day"] = p["day"].fillna(-1).astype("int64")
    p["player_name_stage0"] = p["player_id"].map(names)
    return p


def pbp_status(pl: pd.DataFrame) -> pd.DataFrame:
    """The match statuses stage2_pbp.measured / replay_luck read: tour, deciding-set rule, Slam name, the two players."""
    s = pl.pivot_table(index="match_id", columns="side", values="player", aggfunc="first")
    st = pd.DataFrame({"match_id": s.index, "player1": s[1].to_numpy(), "player2": s[2].to_numpy()})
    st["tour"] = pl.groupby("match_id")["tour"].first().reindex(st["match_id"]).to_numpy()
    st["year"] = st["match_id"].str.slice(0, 4).astype(int)
    st["tournament_name"] = st["match_id"].str.split("-").str[1].map(SLAM_FILES)
    st["rule"] = M.deciding_set_rule(pd.Series(["GS"] * len(st)), st["tournament_name"], st["year"],
                                     pd.Series([False] * len(st))).to_numpy()
    return st


def luck_changes(pts: pd.DataFrame, pl: pd.DataFrame, k: int) -> pd.DataFrame:
    """Pure-luck replay k of every kept match (stage2_pbp.replay_luck at Stage 2's de-noised rates), the same per
    player-match changes computed on it, and who won the replayed match."""
    st = pbp_status(pl)
    ms = PBP.measured(pts, st)
    lp, ls = PBP.replay_luck(ms, SEED + 1000 * (k + 1))
    pc = player_changes(lp)
    w1 = ls.drop_duplicates("match_id").set_index("match_id")["p1_won"].astype(bool).reindex(pc["match_id"]).to_numpy()
    pc["won_match"] = np.where(pc["side"].to_numpy() == 1, w1, ~w1)
    return pc


def window_key(pcode: np.ndarray, year: np.ndarray, window: str) -> np.ndarray:
    """Player-window codes: a season (Stage 3's windows), or the whole span (career)."""
    return pcode.astype("int64") * 100 + ((year - 2010) if window == "season" else 0)


def pbp_k(pm: pd.DataFrame, d_col: str, u_col: str, years=PBP_K_YEARS, window: str = "season") -> dict:
    """Stage 3's empirical-Bayes constant for the late-match change, on player-windows (seasons, or careers) of
    ``years``: x = u d, units u; with a bootstrap range over players."""
    g = pm[pm["linked"] & pm["year"].isin(list(years)) & (pm[u_col] > 0)]
    if len(g) < 50:
        return {"K": np.inf, "player_matches": int(len(g))}
    unit, uniq = pd.factorize(pd.Series(window_key(g["pcode"].to_numpy(), g["year"].to_numpy(), window)))
    x = (g[u_col] * g[d_col]).to_numpy()
    s = T.unit_sums(unit, x, g[u_col].to_numpy())
    est = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
    pu = pd.factorize(pd.Series(np.asarray(uniq) // 100))[0]
    P_ = int(pu.max()) + 1
    rng = seeded("K", d_col, g["tour"].iloc[0], window)
    Ks = np.concatenate([T.eb_constants(s["D"], s["X"], s["W"], s["m"], weight=np.stack(
        [np.bincount(row, minlength=P_) for row in rng.integers(0, P_, size=(50, P_))])[:, pu].astype("float64"))["K"]
        for _ in range(BOOT // 50)])
    return {"K": float(est["K"]), "K_lo": float(np.percentile(Ks, 2.5, method="nearest")),
            "K_hi": float(np.percentile(Ks, 97.5, method="nearest")), "mean": float(est["mu"]),
            "chance_var_per_unit": float(est["s2"]), "true_var": float(est["tau2"]), "window": window,
            "player_windows": int((s["D"] > 0).sum()), "player_matches": int(len(g)),
            "units_per_match": float(g[u_col].mean())}


def reliability_pbp(pm: pd.DataFrame, d_col: str, u_col: str, label: str) -> list:
    """Split-half correlations of the u-weighted mean of d across each player's matches (career units), per n."""
    g = pm[pm["linked"] & (pm[u_col] > 0) & np.isfinite(pm[d_col])]
    unit = pd.factorize(g["pcode"])[0]
    res = T.split_half(unit, (g[u_col] * g[d_col]).to_numpy(), g[u_col].to_numpy(), seeded("rel", label, d_col),
                       N_GRID_PBP, DRAWS)
    return [{"n": x["n"], "r": x["r"], "r_lo": x["r_lo"], "r_hi": x["r_hi"], "players": x["player_windows"],
             "units_per_half": x["units_per_set"], "directional_only": x["directional_only"]} for x in res]


def sb_of(rel: list) -> dict:
    """The Spearman-Brown k (matches for half signal) fitted on the n's with 300+ players, or on every n with 30+
    (directional) where fewer than two have 300."""
    use = [x for x in rel if x["players"] >= FIT_UNITS]
    basis = "300+ players"
    if len(use) < 2:
        use, basis = [x for x in rel if x["players"] >= MIN_UNITS], "30+ players (directional)"
    if not use:
        return {"k": None, "basis": "none"}
    f = T.sb_fit([x["n"] for x in use], [x["r"] for x in use], [x["players"] for x in use])
    return {"k": f["k"] if np.isfinite(f["k"]) else None, "no_signal": bool(f.get("no_signal", False)), "basis": basis,
            "n_values": len(use)}


def decline_trait(pbp_pm: pd.DataFrame, rows: pd.DataFrame, K: dict, d_col: str = "d_sets", u_col: str = "u_sets") -> tuple[np.ndarray, np.ndarray]:
    """Per row of ``rows``: the player's late-match trait before the match (earlier Slams only, day strictly before)
    and whether it exists (at least one earlier match with the measure)."""
    g = pbp_pm[pbp_pm["linked"] & (pbp_pm[u_col] > 0) & np.isfinite(pbp_pm[d_col])]
    V = np.column_stack([(g[u_col] * g[d_col]).to_numpy(), g[u_col].to_numpy(), np.ones(len(g))])
    sb = T.sums_before(g["pcode"].to_numpy(), g["day"].to_numpy(), V, rows["pcode"].to_numpy(), rows["day"].to_numpy())
    k = np.where(rows["tour"].to_numpy() == "atp", K["atp"], K["wta"])
    return sb[:, 0] / (sb[:, 1] + k), sb[:, 2] > 0.5


# ------------------------------------------------------------------------------------------------
# 2. The grinder

def grinder_inputs(rows: pd.DataFrame, line: dict | None = None) -> dict:
    """Per row: whether it enters the grinder history (completed, standard format, box score, plausible minutes, the
    Stage 3 expectation), the residual points r, the points u, minutes per set, and long (with ``line``)."""
    num = lambda c: rows[c].to_numpy(dtype="float64")  # noqa: E731
    tpw_n, tpw_d, spw_d, rpw_d = num("tpw_n"), num("tpw_d"), num("spw_d"), num("rpw_d")
    ps, po = num("p_serve_own"), num("p_serve_opp")
    minutes, sets = num("minutes"), num("sets_won_d")
    with np.errstate(invalid="ignore", divide="ignore"):
        spp = 60.0 * minutes / tpw_d
        mps = minutes / sets
    ok = (rows["box_hist"].to_numpy() & np.isfinite(tpw_n) & np.isfinite(tpw_d) & np.isfinite(spw_d) & np.isfinite(rpw_d)
          & (tpw_d > 0) & np.isfinite(ps) & np.isfinite(po) & np.isfinite(minutes) & (minutes > 0) & np.isfinite(sets)
          & (sets > 0) & (spp >= SPP_RANGE[0]) & (spp <= SPP_RANGE[1]))
    exp_pts = spw_d * ps + rpw_d * (1 - po)
    out = {"ok": ok, "r": np.where(ok, tpw_n - exp_pts, 0.0), "u": np.where(ok, tpw_d, 0.0), "mps": np.where(ok, mps, np.nan)}
    if line is not None:
        lv = np.where(rows["tour"].to_numpy() == "atp", line["atp"], line["wta"])
        out["long"] = ok & (mps > lv)
    return out


def long_line(rows: pd.DataFrame, gi: dict) -> dict:
    """The tour's 75th percentile of minutes per set over the matches of 2010-2018 that enter the history (one value
    per match)."""
    a = np.arange(len(rows)) % 2 == 0
    yr, tour = rows["year"].to_numpy(), rows["tour"].to_numpy()
    out = {}
    for t in C.TOURS:
        m = a & gi["ok"] & np.isin(yr, list(K_YEARS)) & (tour == t)
        out[t] = float(np.quantile(gi["mps"][m], LONG_Q))
        out[f"{t}_matches"] = int(m.sum())
    return out


def contrast(RL, UL, RS, US) -> tuple[np.ndarray, np.ndarray]:
    """The long-minus-short residual share and its effective units 1 / (1/U_L + 1/U_S) (0 where either is empty)."""
    both = (UL > 0) & (US > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        G = np.where(both, RL / np.where(UL > 0, UL, 1) - RS / np.where(US > 0, US, 1), 0.0)
        Ue = np.where(both, UL * US / np.where(both, UL + US, 1), 0.0)
    return G, Ue


def grinder_k(rows: pd.DataFrame, gi: dict, years=K_YEARS, label: str = "real", window: str = "season") -> dict:
    """eb_constants' method of moments for the contrast on player-windows (seasons, or careers): chance variance per
    point from the within-window variation of the residual share (all the window's matches), true spread of G across
    windows."""
    yr, tour = rows["year"].to_numpy(), rows["tour"].to_numpy()
    out = {}
    for t in C.TOURS:
        sel = gi["ok"] & np.isin(yr, list(years)) & (tour == t)
        unit, uniq = pd.factorize(pd.Series(window_key(rows["pcode"].to_numpy()[sel], yr[sel], window)))
        r, u, L = gi["r"][sel], gi["u"][sel], gi["long"][sel]
        Uw = int(unit.max()) + 1
        RL = np.bincount(unit, weights=r * L, minlength=Uw)
        UL = np.bincount(unit, weights=u * L, minlength=Uw)
        RS = np.bincount(unit, weights=r * ~L, minlength=Uw)
        US = np.bincount(unit, weights=u * ~L, minlength=Uw)
        G, Ue = contrast(RL, UL, RS, US)
        s = T.unit_sums(unit, r, u)
        keep = Ue > 0
        est = T.eb_constants(Ue[keep], (G * Ue)[keep], s["W"][keep], s["m"][keep])
        pu = pd.factorize(pd.Series(np.asarray(uniq)[keep] // 100))[0]
        P_ = int(pu.max()) + 1
        rng = seeded("Kg", label, t, window)
        Ks = np.concatenate([T.eb_constants(Ue[keep], (G * Ue)[keep], s["W"][keep], s["m"][keep], weight=np.stack(
            [np.bincount(row, minlength=P_) for row in rng.integers(0, P_, size=(50, P_))])[:, pu].astype("float64"))["K"]
            for _ in range(BOOT // 50)])
        out[t] = {"K": float(est["K"]), "K_lo": float(np.percentile(Ks, 2.5, method="nearest")),
                  "K_hi": float(np.percentile(Ks, 97.5, method="nearest")), "mean": float(est["mu"]),
                  "chance_var_per_point": float(est["s2"]), "true_var": float(est["tau2"]), "window": window,
                  "player_windows": int(keep.sum()), "player_matches": int(sel.sum()),
                  "long_share": float(L.mean())}
    return out


def split_half_contrast(unit: np.ndarray, r: np.ndarray, u: np.ndarray, L: np.ndarray, rng, n_grid=N_GRID_BOX,
                        draws: int = DRAWS) -> list:
    """Split-half correlations of the contrast G (long minus short residual share) across players: per n, every player
    with 2n matches gives two random sets of n; players whose either half lacks a long or a short match are left out of
    that draw."""
    Uw = int(unit.max()) + 1
    count = np.bincount(unit, minlength=Uw)
    acc = {n: ([], []) for n in n_grid}
    for _ in range(draws):
        o = np.lexsort((rng.random(len(unit)), unit))
        us = unit[o]
        rank = np.arange(len(us)) - np.searchsorted(us, us, side="left")
        for n in n_grid:
            ok = count >= 2 * n
            if ok.sum() < MIN_UNITS:
                continue
            sel = ok[us] & (rank < 2 * n)
            rr = o[sel]
            idx = us[sel] * 2 + (rank[sel] >= n)
            Lr = L[rr]
            sums = [np.bincount(idx, weights=w, minlength=2 * Uw).reshape(Uw, 2)
                    for w in (r[rr] * Lr, u[rr] * Lr, r[rr] * ~Lr, u[rr] * ~Lr)]
            G, Ue = contrast(*sums)
            good = ok & (Ue[:, 0] > 0) & (Ue[:, 1] > 0)
            if good.sum() < MIN_UNITS or G[good, 0].std() == 0 or G[good, 1].std() == 0:
                continue
            acc[n][0].append(float(np.corrcoef(G[good, 0], G[good, 1])[0, 1]))
            acc[n][1].append(int(good.sum()))
    out = []
    for n, (rs, us_) in acc.items():
        if not rs:
            continue
        rbar, units = float(np.mean(rs)), int(np.median(us_))
        lo, hi = T.fisher_ci(rbar, units)
        out.append({"n": n, "r": rbar, "r_lo": lo, "r_hi": hi, "players": units, "draws": len(rs),
                    "directional_only": bool(units < FIT_UNITS)})
    return out


def simulate_sets(pa, pb, best_of, final_rule, seed: int = 0, max_points: int = 5000) -> dict:
    """stage2_iid.simulate's rules and random draws, point by point, also counting the sets played (it returns the
    same served, won and a_won for the same seed; a test checks it)."""
    pa, pb = M._arrays(pa, pb)
    n = pa.size
    rng = np.random.default_rng(seed)
    need = (np.broadcast_to(np.asarray(best_of), (n,)).astype("int64") + 1) // 2
    fr = np.broadcast_to(np.asarray(final_rule, dtype=object), (n,))
    fr_at = np.array([M.SET_RULES[r][0] or 0 for r in fr], dtype="int64")
    fr_pts = np.array([M.SET_RULES[r][1] for r in fr], dtype="int64")
    p_srv = np.stack([pa.ravel(), pb.ravel()], axis=1)
    sets = np.zeros((n, 2), dtype="int64")
    games = np.zeros((n, 2), dtype="int64")
    pts = np.zeros((n, 2), dtype="int64")
    server = rng.integers(0, 2, n)
    in_tb = np.zeros(n, dtype=bool)
    tb_first = np.zeros(n, dtype="int64")
    tb_target = np.zeros(n, dtype="int64")
    served = np.zeros((n, 2), dtype="int64")
    won_srv = np.zeros((n, 2), dtype="int64")
    done = np.zeros(n, dtype=bool)
    a_won = np.zeros(n, dtype=bool)
    for _ in range(max_points):
        idx = np.flatnonzero(~done)
        if idx.size == 0:
            break
        k = pts[idx, 0] + pts[idx, 1]
        tb = in_tb[idx]
        tb_srv = np.where((k == 0) | (((k - 1) // 2) % 2 == 1), tb_first[idx], 1 - tb_first[idx])
        srv = np.where(tb, tb_srv, server[idx])
        win = rng.random(idx.size) < p_srv[idx, srv]
        pw = np.where(win, srv, 1 - srv)
        served[idx, srv] += 1
        won_srv[idx, srv] += win
        pts[idx, pw] += 1
        target = np.where(tb, tb_target[idx], 4)
        lead = pts[idx, pw] - pts[idx, 1 - pw]
        over = (pts[idx, pw] >= target) & (lead >= 2)
        g, gw, gtb = idx[over], pw[over], tb[over]
        if g.size == 0:
            continue
        games[g, gw] += 1
        pts[g] = 0
        server[g] = 1 - np.where(gtb, tb_first[g], server[g])
        in_tb[g] = False
        final = (sets[g, 0] == need[g] - 1) & (sets[g, 1] == need[g] - 1)
        at = np.where(final, fr_at[g], 6)
        gwin, glose = games[g, gw], games[g, 1 - gw]
        set_over = gtb | ((gwin >= 6) & (gwin - glose >= 2))
        start = ~set_over & (at > 0) & (games[g, 0] == at) & (games[g, 1] == at)
        s = g[start]
        in_tb[s] = True
        tb_first[s] = server[s]
        tb_target[s] = np.where(final[start], fr_pts[g][start], 7)
        so, sw = g[set_over], gw[set_over]
        sets[so, sw] += 1
        games[so] = 0
        fin = sets[so, sw] >= need[so]
        done[so[fin]] = True
        a_won[so[fin]] = sw[fin] == 0
    if not done.all():
        raise RuntimeError(f"{int((~done).sum())} simulated matches unfinished after {max_points} points")
    return {"a_won": a_won, "served": served, "won": won_srv, "sets": sets.sum(axis=1)}


def grinder_replay(rows: pd.DataFrame, gi: dict, seed: int) -> dict:
    """Every match that enters the grinder history replayed under the iid model (the match's format and deciding-set
    rule) at Stage 2's de-noised rates of the day; the residual against the same Stage 3 expectation; "long" = points
    per set above the replay's own 75th percentile of 2010-2018 per tour. Returns per-row arrays like grinder_inputs."""
    n = len(rows)
    a = np.arange(n) % 2 == 0
    both = gi["ok"][0::2] & gi["ok"][1::2]
    ia = np.flatnonzero(a)[both]
    ib = ia + 1
    num = lambda c: rows[c].to_numpy(dtype="float64")  # noqa: E731
    spw_n, spw_d = num("spw_n"), num("spw_d")
    t = pd.DataFrame({"pa": spw_n[ia] / spw_d[ia], "pb": spw_n[ib] / spw_d[ib], "svpt_a": spw_d[ia], "svpt_b": spw_d[ib],
                      "tour": rows["tour"].to_numpy()[ia], "surface": rows["surface"].fillna("Unknown").to_numpy()[ia]})
    rng = np.random.default_rng(seed)
    pa, pb, _ = A2.denoised_rates(t, rng)
    bo = np.where(F.retrospective_best_of_five(rows)[ia], 5, 3)
    rule = F.deciding_rules(rows)[ia]
    sim = simulate_sets(pa, pb, bo, rule, seed=seed + 1)
    served, won, sets = sim["served"], sim["won"], sim["sets"]
    ps, po = num("p_serve_own"), num("p_serve_opp")
    out_r, out_u, out_pps = np.zeros(n), np.zeros(n), np.full(n, np.nan)
    tot = served.sum(axis=1).astype("float64")
    for j, (own, oth) in enumerate(((ia, ib), (ib, ia))):
        sv_own, sv_opp = served[:, j].astype("float64"), served[:, 1 - j].astype("float64")
        w_own, w_opp = won[:, j].astype("float64"), won[:, 1 - j].astype("float64")
        tpw = w_own + (sv_opp - w_opp)
        out_r[own] = tpw - (sv_own * ps[own] + sv_opp * (1 - po[own]))
        out_u[own] = tot
        out_pps[own] = tot / sets
    ok = np.zeros(n, dtype=bool)
    ok[ia], ok[ib] = True, True
    yr, tour = rows["year"].to_numpy(), rows["tour"].to_numpy()
    line = {}
    for tt in C.TOURS:
        m = a & ok & np.isin(yr, list(K_YEARS)) & (tour == tt)
        line[tt] = float(np.quantile(out_pps[m], LONG_Q))
    lv = np.where(tour == "atp", line["atp"], line["wta"])
    return {"ok": ok, "r": out_r, "u": out_u, "long": ok & (out_pps > lv), "line_points_per_set": line}


def grinder_sums(rows: pd.DataFrame, gi: dict) -> dict:
    """As-of sums per row (career; the last 52 weeks) of r and u in long and short matches, and the count."""
    L = gi["long"]
    ok = gi["ok"]
    V = np.column_stack([gi["r"] * L, gi["u"] * L, gi["r"] * (ok & ~L), gi["u"] * (ok & ~L), ok.astype("float64")])
    tmp = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    for j in range(V.shape[1]):
        tmp[f"_v{j}"] = V[:, j]
    car = C.asof_sums(tmp, [f"_v{j}" for j in range(V.shape[1])]).to_numpy()
    bef = T.sums_before(rows["pcode"].to_numpy(), rows["day"].to_numpy(), V, rows["pcode"].to_numpy(),
                        rows["day"].to_numpy() - S.WEEK52)
    return {"career": car, "52 weeks": car - bef}


def grinder_value(sums: np.ndarray, K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    G, Ue = contrast(sums[:, 0], sums[:, 1], sums[:, 2], sums[:, 3])
    return G * Ue / (Ue + K), sums[:, 4] > 0.5


# ------------------------------------------------------------------------------------------------
# 3. Load

def load_windows(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per row, Stage 4's load over the last 14 days (this event's earlier rounds and events that started up to 14 days
    before): log(1 + sets) and log(1 + minutes), missing where a match of the window lacks the count."""
    played = rows["played"].to_numpy()
    minutes = rows["minutes"].to_numpy(dtype="float64")
    sets = rows["sets_won_d"].to_numpy(dtype="float64")
    V = np.column_stack([played.astype("float64"), (played & np.isnan(minutes)).astype("float64"),
                         np.where(played & ~np.isnan(minutes), minutes, 0.0),
                         (played & np.isnan(sets)).astype("float64"), np.where(played & ~np.isnan(sets), sets, 0.0)])
    tmp = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    for j in range(V.shape[1]):
        tmp[f"_v{j}"] = V[:, j]
    car = C.asof_sums(tmp, [f"_v{j}" for j in range(V.shape[1])]).to_numpy()
    bef = T.sums_before(rows["pcode"].to_numpy(), rows["day"].to_numpy(), V, rows["pcode"].to_numpy(),
                        rows["day"].to_numpy() - WINDOW14)
    win = car - bef
    sets14 = np.where(win[:, 3] < 0.5, np.log1p(np.maximum(win[:, 4], 0)), np.nan)
    min14 = np.where(win[:, 1] < 0.5, np.log1p(np.maximum(win[:, 2], 0)), np.nan)
    return sets14, min14


# ------------------------------------------------------------------------------------------------
# Every fatigue feature for the pool of ``rows`` (also the probe's builder)

def build(rows: pd.DataFrame, pbp_pm: pd.DataFrame, ctx: dict, pool: np.ndarray | None = None) -> dict:
    """Every fatigue column (A - B) for the pool matches of ``rows``, with the frozen constants in ``ctx``."""
    pool, A, Bi = S.pool_rows(rows, pool)
    tour = rows["tour"].to_numpy()
    atp = tour[A] == "atp"
    out = {}
    trait, ex = decline_trait(pbp_pm, rows, ctx["K_decline"])
    ld = np.where(ex[A] & ex[Bi], trait[A] - trait[Bi], np.nan)
    out["late_decline|career"] = ld
    bo5 = F.best_of_five(rows)[A]
    out["late_decline_x_bo5|single"] = np.where(atp, ld * bo5, np.nan)
    p = rows["p_ratings_a"].to_numpy(dtype="float64")[A]
    closeness = 1.0 - 2.0 * np.abs(p - 0.5)
    out["late_decline_x_long|single"] = ld * closeness
    sets14, min14 = load_windows(rows)
    both = ex[A] & ex[Bi]
    out["sets_14d_x_decline|single"] = np.where(both, sets14[A] * trait[A] - sets14[Bi] * trait[Bi], np.nan)
    out["minutes_14d_x_decline|single"] = np.where(both, min14[A] * trait[A] - min14[Bi] * trait[Bi], np.nan)
    gi = grinder_inputs(rows, ctx["long_line"])
    gs = grinder_sums(rows, gi)
    kg = np.where(tour == "atp", ctx["K_grinder"]["atp"], ctx["K_grinder"]["wta"])
    for form in ("career", "52 weeks"):
        v, e = grinder_value(gs[form], kg)
        out[f"grinder|{form}"] = np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)
    out["grinder_x_bo5|single"] = np.where(atp, out["grinder|career"] * bo5, np.nan)
    return out


def tune_k_fallback(frame: pd.DataFrame, col_fn, label: str) -> dict:
    """Only if empirical Bayes finds no spread: K per tour from K_FALLBACK_GRID by the in-sample gain given Elo on the
    evaluation matches of 2013-2018 (before every scored season of the women's point- and box-based rows)."""
    chosen, grid = {}, []
    for t in C.TOURS:
        best, bestK = -np.inf, K_FALLBACK_GRID[-1]
        for Kv in K_FALLBACK_GRID:
            f = col_fn(Kv)
            m = (frame["evaluation"].to_numpy(dtype=bool) & (frame["tour"].to_numpy() == t)
                 & np.isin(frame["year"].to_numpy(), list(TUNE_YEARS)) & np.isfinite(f))
            if m.sum() < 300:
                continue
            g = S.gain_given_elo(f[m], frame["p_elo"].to_numpy()[m], frame["a_won"].to_numpy(dtype=bool)[m])
            grid.append({"label": label, "tour": t, "K": Kv, "gain_milli": g, "matches": int(m.sum())})
            if g > best:
                best, bestK = g, Kv
        chosen[t] = bestK
    return {"K": chosen, "grid": grid}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t_start = time.time()
    timings = {}
    rows, _ = S.load_inputs()
    frame = U.load_pool(["rating_matchup|single", "sets_14d|single", "minutes_14d|single"])
    pool, A, Bi = S.pool_rows(rows)
    assert (rows["match_id"].to_numpy()[A] == frame["match_id"].to_numpy()).all()
    pr = np.full(len(rows), np.nan)
    p_rat = expit(frame["rating_matchup|single"].to_numpy(dtype="float64"))
    pr[A], pr[Bi] = p_rat, p_rat
    rows["p_ratings_a"] = pr
    timings["load_s"] = round(time.time() - t_start, 1)
    summary: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                     "settings": {"late_from_set": LATE_SET, "split_points": SPLIT_POINTS, "seconds_per_point_range": SPP_RANGE,
                                  "long_quantile": LONG_Q, "replays": REPLAYS, "draws": DRAWS, "n_grid_pbp": N_GRID_PBP,
                                  "n_grid_box": N_GRID_BOX, "pbp_k_years": [PBP_K_YEARS[0], PBP_K_YEARS[-1]],
                                  "k_years": [K_YEARS[0], K_YEARS[-1]], "seed": SEED, "boot": BOOT}}

    # ---------------------------------------------------------------- 1. late-match decline
    t1 = time.time()
    pts = pd.read_parquet(PBP_POINTS, columns=["match_id", "tour", "set_no", "srv1", "won1"])
    pl = link_players(rows)
    pm = player_changes(pts).merge(pl[["match_id", "side", "player", "player_id", "player_name_stage0", "pcode", "day",
                                       "year", "slam", "linked", "won_match"]], on=["match_id", "side"], how="left")
    pm["linked"] = pm["linked"].fillna(False).astype(bool)
    log(f"point-by-point player-matches: {len(pm):,}; linked {int(pm['linked'].sum()):,}")
    cover = {}
    for t in C.TOURS:
        g = pm[pm["tour"] == t]
        cover[t] = {"player_matches": int(len(g)), "linked": int(g["linked"].sum()),
                    **{f"with_{v}": int((g["linked"] & (g[f"u_{v}"] > 0)).sum()) for v in ("sets", "set3", "points150")},
                    "players_linked": int(g.loc[g["linked"], "pcode"].nunique())}
    summary["pbp_coverage"] = cover
    # selection: d of the match's winner against its loser, real and in the replays
    replays = []
    for k in range(REPLAYS):
        lpm = luck_changes(pts, pd.read_parquet(PBP_PLAYERS, columns=["match_id", "tour", "player", "side"]), k)
        lpm = lpm.merge(pm[["match_id", "side", "pcode", "day", "year", "linked"]], on=["match_id", "side"], how="left")
        lpm["linked"] = lpm["linked"].fillna(False).astype(bool)
        replays.append(lpm)
        log(f"pure-luck replay {k + 1} of {REPLAYS}")
    timings["pbp_replays_s"] = round(time.time() - t1, 1)
    # selection: the match winner's d (u-weighted; the loser's is its negative), real and in the replays, where no
    # fatigue exists; a winner's d above zero in the replays is what selection alone produces
    sel = {}
    for t in C.TOURS:
        sel[t] = {}
        for v in ("sets", "set3", "points150"):
            g = pm[(pm["tour"] == t) & (pm[f"u_{v}"] > 0)]
            if len(g) == 0:
                continue
            wv = g["won_match"].astype(bool).to_numpy()
            dv, uv = g[f"d_{v}"].to_numpy(), g[f"u_{v}"].to_numpy()
            luck_w, luck_sd = [], []
            for lpm in replays:
                gl = lpm[(lpm["tour"] == t) & (lpm[f"u_{v}"] > 0)]
                wl = gl["won_match"].astype(bool).to_numpy()
                dl, ul = gl[f"d_{v}"].to_numpy(), gl[f"u_{v}"].to_numpy()
                luck_w.append(float(np.average(dl[wl], weights=ul[wl])))
                luck_sd.append(float(np.sqrt(np.average(dl ** 2, weights=ul))))
            sel[t][v] = {"player_matches": int(len(g)), "matches_with_measure": int(len(g) // 2),
                         "winners_mean_d_real": float(np.average(dv[wv], weights=uv[wv])),
                         "winners_mean_d_luck": float(np.mean(luck_w)),
                         "sd_d_real": float(np.sqrt(np.average(dv ** 2, weights=uv))),
                         "sd_d_luck": float(np.mean(luck_sd)),
                         "effective_points_mean": float(uv.mean())}
    summary["selection"] = sel
    # reliability: real and pure luck
    rel = {}
    for t in C.TOURS:
        rel[t] = {}
        for v in ("sets", "set3", "points150"):
            g = pm[pm["tour"] == t]
            if not (g[f"u_{v}"] > 0).any():
                continue
            real = reliability_pbp(g, f"d_{v}", f"u_{v}", f"{t}|{v}|real")
            luck = [reliability_pbp(lpm[lpm["tour"] == t], f"d_{v}", f"u_{v}", f"{t}|{v}|luck{k}") for k, lpm in enumerate(replays)]
            by_n = {}
            for x in real:
                lv = [y["r"] for L_ in luck for y in L_ if y["n"] == x["n"]]
                by_n[x["n"]] = {**x, "luck_r_mean": float(np.mean(lv)) if lv else None,
                                "luck_r_min": float(np.min(lv)) if lv else None, "luck_r_max": float(np.max(lv)) if lv else None}
            rel[t][v] = {"by_n": list(by_n.values()), "sb_real": sb_of(real),
                         "sb_luck": [sb_of(L_) for L_ in luck]}
            log(f"  reliability {t} {v}: " + ", ".join(f"n={x['n']}: {x['r']:.3f} (luck {x['luck_r_mean']:.3f}, {x['players']})"
                                                       for x in by_n.values() if x["luck_r_mean"] is not None))
    summary["reliability_decline"] = rel
    # the constant (2011-2018): player-seasons (Stage 3's and Stage 4's windows), then careers; real and in the replays
    Kd_info = {}
    for t in C.TOURS:
        g = pm[pm["tour"] == t]
        Kd_info[t] = {w: pbp_k(g, "d_sets", "u_sets", window=w) for w in ("season", "career")}
        Kd_info[t]["luck"] = [{w: pbp_k(lpm[lpm["tour"] == t], "d_sets", "u_sets", window=w) for w in ("season", "career")}
                              for lpm in replays]
    summary["K_decline"] = Kd_info
    timings["pbp_s"] = round(time.time() - t1, 1)

    # ---------------------------------------------------------------- 2. the grinder
    t2 = time.time()
    gi0 = grinder_inputs(rows)
    line = long_line(rows, gi0)
    gi = grinder_inputs(rows, {"atp": line["atp"], "wta": line["wta"]})
    log(f"long-match line (minutes per set): {line}")
    drop = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        spp = 60.0 * rows["minutes"].to_numpy(dtype="float64") / rows["tpw_d"].to_numpy(dtype="float64")
    a_row = np.arange(len(rows)) % 2 == 0
    for t in C.TOURS:
        tt = rows["tour"].to_numpy() == t
        base = (rows["box_hist"].to_numpy() & tt & rows["minutes"].notna().to_numpy() & rows["tpw_d"].notna().to_numpy()
                & (rows["tpw_d"].to_numpy(dtype="float64") > 0))
        bad = base & ((spp < SPP_RANGE[0]) | (spp > SPP_RANGE[1]))
        drop[t] = {"box_rows_with_minutes": int(base.sum()), "entering": int((gi["ok"] & tt).sum()),
                   "matches_with_implausible_minutes": int((bad & a_row).sum()),
                   "matches_with_minutes": int((base & a_row).sum())}
    summary["grinder_rows"] = drop
    Kg = {w: grinder_k(rows, gi, window=w) for w in ("season", "career")}
    log(f"grinder K: {json.dumps(Kg)}")
    rel_g, Kg_luck = {}, []
    luck_g = [grinder_replay(rows, gi, SEED + 77 * (k + 1)) for k in range(2)]
    for k, lg in enumerate(luck_g):
        Kg_luck.append({w: grinder_k(rows, lg, label=f"luck{k}", window=w) for w in ("season", "career")})
    for t in C.TOURS:
        tt = rows["tour"].to_numpy() == t
        m = gi["ok"] & tt
        unit = pd.factorize(rows["pcode"].to_numpy()[m])[0]
        real = split_half_contrast(unit, gi["r"][m], gi["u"][m], gi["long"][m], seeded("relg", t))
        luck = []
        for k, lg in enumerate(luck_g):
            ml = lg["ok"] & tt
            ul = pd.factorize(rows["pcode"].to_numpy()[ml])[0]
            luck.append(split_half_contrast(ul, lg["r"][ml], lg["u"][ml], lg["long"][ml], seeded("relg", t, k)))
        by_n = []
        for x in real:
            lv = [y["r"] for L_ in luck for y in L_ if y["n"] == x["n"]]
            by_n.append({**x, "luck_r_mean": float(np.mean(lv)) if lv else None,
                         "luck_r_min": float(np.min(lv)) if lv else None, "luck_r_max": float(np.max(lv)) if lv else None})
        rel_g[t] = {"by_n": by_n, "sb_real": sb_of(real), "sb_luck": [sb_of(L_) for L_ in luck]}
        log(f"  grinder reliability {t}: " + ", ".join(f"n={x['n']}: {x['r']:.3f} (luck {x['luck_r_mean']:.3f}, {x['players']})"
                                                      for x in by_n if x["luck_r_mean"] is not None))
    summary["reliability_grinder"] = rel_g
    summary["K_grinder"] = {"real": Kg, "luck": Kg_luck,
                            "replay_lines_points_per_set": [lg["line_points_per_set"] for lg in luck_g]}
    summary["long_line_minutes_per_set"] = line
    timings["grinder_s"] = round(time.time() - t2, 1)

    # ---------------------------------------------------------------- constants and features
    t3 = time.time()

    def first_finite(info: dict) -> tuple[float, str]:
        for w in ("season", "career"):
            if np.isfinite(info[w]["K"]):
                return float(info[w]["K"]), w
        return np.inf, "none"
    ctx = {"K_decline": {}, "K_grinder": {}, "long_line": {"atp": line["atp"], "wta": line["wta"]}}
    source = {}
    for t in C.TOURS:
        ctx["K_decline"][t], source[f"decline {t}"] = first_finite(Kd_info[t])
        ctx["K_grinder"][t], source[f"grinder {t}"] = first_finite({w: Kg[w][t] for w in ("season", "career")})
    fallback = {}
    for t in C.TOURS:
        if not np.isfinite(ctx["K_decline"][t]):
            def col_fn(Kv, tt=t):
                c2 = dict(ctx, K_decline={**ctx["K_decline"], tt: Kv})
                tr, e = decline_trait(pm, rows, c2["K_decline"])
                return np.where(e[A] & e[Bi], tr[A] - tr[Bi], np.nan)
            fb = tune_k_fallback(frame, col_fn, f"decline {t}")
            ctx["K_decline"][t] = fb["K"][t]
            fallback[f"decline {t}"] = fb
        if not np.isfinite(ctx["K_grinder"][t]):
            def col_fn(Kv, tt=t):
                kg = {**ctx["K_grinder"], tt: Kv}
                gs = grinder_sums(rows, gi)
                v, e = grinder_value(gs["career"], np.where(rows["tour"].to_numpy() == "atp", kg["atp"], kg["wta"]))
                return np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)
            fb = tune_k_fallback(frame, col_fn, f"grinder {t}")
            ctx["K_grinder"][t] = fb["K"][t]
            fallback[f"grinder {t}"] = fb
    for k_, fb in fallback.items():
        source[k_] = "tuned (in-sample gain given Elo, 2013-2018)"
    summary["K_used"] = {"decline": ctx["K_decline"], "grinder": ctx["K_grinder"], "source": source, "fallback": fallback}
    log(f"constants used: {json.dumps(summary['K_used'], default=float)}")
    feats = build(rows, pm, ctx)
    timings["features_s"] = round(time.time() - t3, 1)
    # check: the 14-day load against Stage 4's columns
    sets14, min14 = load_windows(rows)
    chk = {}
    for name, v in (("sets_14d|single", sets14), ("minutes_14d|single", min14)):
        mine = np.where(np.isfinite(v[A]) & np.isfinite(v[Bi]), v[A] - v[Bi], np.nan)
        theirs = frame[name].to_numpy(dtype="float64")
        same_missing = bool(np.array_equal(np.isnan(mine), np.isnan(theirs)))
        both_f = np.isfinite(mine) & np.isfinite(theirs)
        chk[name] = {"same_missing": same_missing, "largest_difference": float(np.max(np.abs(mine[both_f] - theirs[both_f])))}
    log(f"load check against Stage 4: {chk}")
    assert all(c["same_missing"] and c["largest_difference"] < 1e-4 for c in chk.values()), chk
    ev = frame["evaluation"].to_numpy(dtype=bool)
    tour = frame["tour"].to_numpy()
    yr = frame["year"].to_numpy()
    coverage = {}
    for c, v in feats.items():
        coverage[c] = {}
        for t in C.TOURS:
            first = C.WTA_BOX_FROM if t == "wta" else C.EVAL_YEARS[0]
            m = ev & (tour == t) & (yr >= first)
            coverage[c][t] = {"evaluation_matches": int(m.sum()), "exists": int((m & np.isfinite(v)).sum()),
                              "nonzero": int((m & np.isfinite(v) & (v != 0)).sum()), "sd": float(np.nanstd(v[m])) if (m & np.isfinite(v)).any() else None}
    summary["coverage"] = coverage
    summary["checks"] = {"load_vs_stage4": chk}
    out = pd.DataFrame({"match_id": frame["match_id"].to_numpy()})
    for c in FEATURES:
        out[c] = feats[c].astype("float64")
    out.to_parquet(PART, index=False)
    log(f"wrote {PART.name}: {out.shape}")

    # ---------------------------------------------------------------- per player (the end of the data)
    lk = pm[pm["linked"] & (pm["u_sets"] > 0)]
    dpl = lk.groupby("pcode").agg(tour=("tour", "first"), player_id=("player_id", "first"),
                                  player=("player_name_stage0", "first"), decline_matches=("u_sets", "size"),
                                  decline_effective_points=("u_sets", "sum"))
    dpl["decline_raw"] = (lk["u_sets"] * lk["d_sets"]).groupby(lk["pcode"]).sum() / dpl["decline_effective_points"]
    kd = np.where(dpl["tour"].eq("atp"), ctx["K_decline"]["atp"], ctx["K_decline"]["wta"])
    dpl["decline_shrunk"] = dpl["decline_raw"] * dpl["decline_effective_points"] / (dpl["decline_effective_points"] + kd)
    dpl["decline_reliability"] = dpl["decline_effective_points"] / (dpl["decline_effective_points"] + kd)
    m = gi["ok"]
    gdf = pd.DataFrame({"pcode": rows["pcode"].to_numpy()[m], "tour": rows["tour"].to_numpy()[m],
                        "player_id": rows["player_id"].to_numpy()[m], "r": gi["r"][m], "u": gi["u"][m], "L": gi["long"][m]})
    gg = gdf.groupby("pcode").agg(tour=("tour", "first"), player_id=("player_id", "first"), grinder_matches=("u", "size"),
                                  long_matches=("L", "sum"))
    for nm, mask in (("L", gdf["L"]), ("S", ~gdf["L"])):
        gg[f"R{nm}"] = gdf["r"].where(mask, 0).groupby(gdf["pcode"]).sum()
        gg[f"U{nm}"] = gdf["u"].where(mask, 0).groupby(gdf["pcode"]).sum()
    G, Ue = contrast(gg["RL"].to_numpy(), gg["UL"].to_numpy(), gg["RS"].to_numpy(), gg["US"].to_numpy())
    kgr = np.where(gg["tour"].eq("atp"), ctx["K_grinder"]["atp"], ctx["K_grinder"]["wta"])
    gg["grinder_raw"], gg["grinder_effective_points"] = G, Ue
    gg["grinder_shrunk"] = G * Ue / (Ue + kgr)
    gg["grinder_reliability"] = Ue / (Ue + kgr)
    gg["short_matches"] = gg["grinder_matches"] - gg["long_matches"]
    names = C.load_match_players(["player_id", "player_name"], with_order=False).drop_duplicates("player_id").set_index("player_id")["player_name"]
    allp = dpl.drop(columns=["player"]).join(gg[["grinder_matches", "long_matches", "short_matches", "grinder_effective_points",
                                                 "grinder_raw", "grinder_shrunk", "grinder_reliability"]], how="outer")
    allp["tour"] = allp["tour"].fillna(gg["tour"])
    allp["player_id"] = allp["player_id"].fillna(gg["player_id"])
    allp["player"] = allp["player_id"].map(names)
    allp = allp.reset_index(drop=True)[["tour", "player_id", "player", "decline_matches", "decline_effective_points",
                                       "decline_raw", "decline_shrunk", "decline_reliability", "grinder_matches",
                                       "long_matches", "short_matches", "grinder_effective_points", "grinder_raw",
                                       "grinder_shrunk", "grinder_reliability"]]
    allp = allp.sort_values(["tour", "decline_matches", "grinder_matches"], ascending=[True, False, False])
    allp.to_csv(PLAYERS_CSV, index=False, float_format="%.6g")
    log(f"wrote {PLAYERS_CSV.name}: {len(allp):,} players")
    # strength: each player's mean pre-match blended Elo over their played matches; its correlation with the raw
    # traits, real and in the replays (which hold strength and selection but no fatigue)
    played = rows["played"].to_numpy()
    own_elo = S.blended(rows, S.elo_constants())
    strength = pd.Series(own_elo[played]).groupby(rows["pcode"].to_numpy()[played]).mean()
    strength_by_id = pd.Series(strength.reindex(rows["pcode"].to_numpy()).to_numpy(), index=rows["player_id"].to_numpy())
    strength_by_id = strength_by_id[~strength_by_id.index.duplicated()]
    allp["mean_elo"] = strength_by_id.reindex(allp["player_id"]).to_numpy()
    corr = {}
    for t in C.TOURS:
        c = {}
        dsel = (allp["tour"] == t) & (allp["decline_matches"] >= 20)
        if dsel.sum() >= 10:
            c["decline_players"] = int(dsel.sum())
            c["decline_real"] = float(np.corrcoef(allp.loc[dsel, "decline_raw"], allp.loc[dsel, "mean_elo"])[0, 1])
            ids = set(allp.loc[dsel, "player_id"])
            lv = []
            for lpm in replays:
                g = lpm[(lpm["tour"] == t) & lpm["linked"] & (lpm["u_sets"] > 0)]
                g = g.assign(player_id=pm.set_index(["match_id", "side"])["player_id"].reindex(
                    pd.MultiIndex.from_frame(g[["match_id", "side"]])).to_numpy())
                g = g[g["player_id"].isin(ids)]
                raw = (g["u_sets"] * g["d_sets"]).groupby(g["player_id"]).sum() / g["u_sets"].groupby(g["player_id"]).sum()
                lv.append(float(np.corrcoef(raw.to_numpy(), strength_by_id.reindex(raw.index).to_numpy())[0, 1]))
            c["decline_luck"] = lv
        gsel = (allp["tour"] == t) & (allp["grinder_matches"] >= 100)
        c["grinder_players"] = int(gsel.sum())
        c["grinder_real"] = float(np.corrcoef(allp.loc[gsel, "grinder_raw"], allp.loc[gsel, "mean_elo"])[0, 1])
        ids = set(allp.loc[gsel, "player_id"])
        lv = []
        for lg in luck_g:
            m_ = lg["ok"] & (rows["tour"].to_numpy() == t)
            d_ = pd.DataFrame({"player_id": rows["player_id"].to_numpy()[m_], "r": lg["r"][m_], "u": lg["u"][m_], "L": lg["long"][m_]})
            d_ = d_[d_["player_id"].isin(ids)]
            sums = {f"{a}{b}": d_[a.lower()].where(d_["L"] if b == "L" else ~d_["L"], 0).groupby(d_["player_id"]).sum()
                    for a in ("R", "U") for b in ("L", "S")}
            Gl, _ = contrast(sums["RL"].to_numpy(), sums["UL"].to_numpy(), sums["RS"].to_numpy(), sums["US"].to_numpy())
            lv.append(float(np.corrcoef(Gl, strength_by_id.reindex(sums["RL"].index).to_numpy())[0, 1]))
        c["grinder_luck"] = lv
        corr[t] = c
    summary["strength_correlation"] = corr
    log(f"strength correlation: {json.dumps(corr)}")
    allp.to_csv(PLAYERS_CSV, index=False, float_format="%.6g")
    summary["players"] = {t: {"with_decline": int(((allp["tour"] == t) & allp["decline_matches"].notna()).sum()),
                              "with_grinder": int(((allp["tour"] == t) & allp["grinder_matches"].notna()).sum()),
                              "decline_reliability_median_20plus": float(allp.loc[(allp["tour"] == t) & (allp["decline_matches"] >= 20), "decline_reliability"].median())
                              if ((allp["tour"] == t) & (allp["decline_matches"] >= 20)).any() else None,
                              "grinder_reliability_median_100plus": float(allp.loc[(allp["tour"] == t) & (allp["grinder_matches"] >= 100), "grinder_reliability"].median())
                              if ((allp["tour"] == t) & (allp["grinder_matches"] >= 100)).any() else None}
                          for t in C.TOURS}

    # ---------------------------------------------------------------- the probe (2023-2024 slice; cuts before and at Wimbledon 2024)
    t4 = time.time()
    sl = S.probe_slice(rows[rows["tournament_date"].lt(pd.Timestamp("2025-01-01")).to_numpy()].reset_index(drop=True),
                       start="2023-01-01")
    pid_to_slice = pd.Series(sl["pcode"].to_numpy(), index=sl["player_id"].to_numpy()).groupby(level=0).first()
    pm_sl = pm.assign(pcode=pid_to_slice.reindex(pm["player_id"]).fillna(-1).to_numpy().astype("int64"))
    pm_sl["linked"] = pm_sl["linked"] & (pm_sl["pcode"] >= 0)
    pool_sl, A_sl, _ = S.pool_rows(sl)
    a = sl.iloc[0::2]
    date = a["tournament_date"].to_numpy()
    rng = np.random.default_rng(SEED)
    early = np.flatnonzero(pool_sl & (date >= np.datetime64("2024-01-01")) & (date < np.datetime64("2024-07-01")))
    wim = np.flatnonzero(pool_sl & (a["tournament_name"].to_numpy() == "Wimbledon") & (a["year"].to_numpy() == 2024)
                         & ~a["qualifying"].to_numpy(dtype=bool))
    cuts = np.r_[rng.choice(early, 3, replace=False), rng.choice(wim, 1, replace=False)]

    def perturb_pbp(aux, rws, c, rg):
        wk = rws["day"].to_numpy()[2 * c]
        later = aux["day"].to_numpy() >= wk
        out_ = aux.copy()
        for v in ("sets", "set3", "points150"):
            out_.loc[later, f"d_{v}"] = rg.normal(0, 0.1, int(later.sum()))
        return out_
    pr = S.probe(sl, lambda r, aux, pool: build(r, aux, ctx, pool=pool), aux=pm_sl, perturb_aux=perturb_pbp, cuts=cuts,
                 pre_match=S.PRE_MATCH + ["p_serve_own", "p_serve_opp", "p_ratings_a"])
    pr["pbp_records_after_cuts"] = [int((pm_sl["day"].to_numpy() >= sl["day"].to_numpy()[2 * int(c)]).sum()) for c in cuts]
    summary["probe"] = pr
    timings["probe_s"] = round(time.time() - t4, 1)
    timings["total_s"] = round(time.time() - t_start, 1)
    summary["timings"] = timings
    summary["columns"] = FEATURES
    PART_JSON.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {PART_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
