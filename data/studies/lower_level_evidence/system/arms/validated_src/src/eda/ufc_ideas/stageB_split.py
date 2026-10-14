"""Stage B, part 3: who the statistics were produced against. A player's opponent-adjusted performance (Part 1's per-match
adjperf z) split by the opponent's strength, the within-player slope of performance on the opponent's strength, results
above Elo's expectation against strong and weak opponents, and whether a player's gap between the two is a lasting trait.

Opponent strength is the opponent's pre-match surface Elo (Stage 1's, retirements counted) against a fixed line per tour:
the median pre-match surface Elo of the player-rows of the tour's main-tour matches (Grand Slam to 250 main draws,
completed or retired) of 2010-2018. "Strong" is above it, "weak" at or below; the thirds use that population's terciles.

Features (A - B; the last 52 weeks and career; each player's earlier box-score matches under the time rule; the weights,
K3 and tau are Part 1's frozen constants of adjperf on the statistic, K3 in matches):
    vs_strong_<s>, vs_weak_<s>      the mean adjperf z over matches against strong (weak) opponents only, shrunk toward 0:
                                    sum w z / (sum w + K3 u_typ^tau), s in tpw, spw, rpw
    strong_minus_weak_<s>           the player's own contrast: (mean z against strong - mean z against weak) shrunk toward
                                    0 as one quantity, x n / (n + K3), n = W_strong W_weak / (W_strong + W_weak) (the
                                    effective sample of a difference); 0 when either group is empty. Shrinking the two
                                    means toward 0 separately would make a player with few strong opponents' difference
                                    equal minus their mean against the weak, so the difference of the two shrunk means is
                                    kept as a reference row for tpw (strong_minus_weak_naive_tpw)
    slope_tpw                       the within-player slope of the per-match z on the opponent's Elo (per 100 points),
                                    ridge-shrunk toward the population's within-player slope b0 (player-seasons of
                                    2010-2018): (cov + lambda b0) / (var + lambda), lambda = K3 typical matches' worth of
                                    the population's within-player variance of the opponent's Elo
    wins_over_strong, wins_over_weak  sum (won - p_elo) over matches played (completed or retired, every level) against
                                    strong (weak) opponents, p_elo the pre-match surface-Elo chance, / (n + K3)
    strong_gap_x_strong_opp         A's strong-minus-weak (tpw) x 1[B is strong] - B's x 1[A is strong]
    vs_top_third_tpw, vs_mid_third_tpw, vs_bottom_third_tpw, top_minus_bottom_third_tpw   the same by thirds

A recency diagnostic for Part 1 is built here too (it reads the same per-match z): adjperf_<s>|decayed, earlier weeks,
the decayed form at Part 1's frozen constants with the same event's earlier rounds left out, on the same matches as the
full decayed form, so that the two rows' difference is what an event's earlier rounds add.

Descriptive measures (stageB_split_summary.json): the mean z by opponent group; per player-season (2013-2026, 5+ matches
in each group) the gap between the groups, its spread beyond chance (method of moments) and its season-to-season
correlation.

The probe: on the slice from 2023, the per-match z rebuilt (Part 1's code, frozen constants) and the features rebuilt with
the box scores, results and later matches' pre-match Elo of every match a cut may not see redrawn (4 cuts in 2026).

Writes, in data/studies/ufc_ideas/:
    stageB_split_features.parquet   per pool match: every feature above (float32)
    stageB_split_summary.json       the lines, the population slope, the descriptive measures, the probe, timings

Run after stageB_adjperf.py: ./python.sh src/eda/ufc_ideas/stageB_split.py   (about 6 minutes, of which the probe 4)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")       # Stage B's share of the machine: at most 5 processes or threads at once

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as H  # noqa: E402
from src.eda.ufc_ideas import stageB_adjperf as AP  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402

SPLIT_FEATURES = B.OUT / "stageB_split_features.parquet"
SPLIT_SUMMARY = B.OUT / "stageB_split_summary.json"

SPLIT_STATS = ("tpw", "spw", "rpw")
FORMS = ("52 weeks", "career")
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")
LINE_YEARS = range(2010, 2019)
ELO_UNIT = 100.0                     # the slope is per 100 Elo points
MIN_GROUP = 5                        # player-season matches in each group for the descriptive gap
DESC_YEARS = range(2013, 2027)
PROBE_FROM = "2023-01-01"
PROBE_CUTS = 4
PROBE_ATOL = 1e-9


def strength_lines(rows: pd.DataFrame) -> dict:
    """Per tour: the median and terciles of the pre-match surface Elo over the player-rows of main-tour matches
    (completed or retired) of 2010-2018."""
    e = rows["elo_surf_own"].to_numpy(dtype="float64")
    m = (rows["level"].isin(MAIN_TOUR).to_numpy() & ~rows["qualifying"].to_numpy(dtype=bool)
         & rows["played"].to_numpy() & np.isin(rows["year"].to_numpy(), list(LINE_YEARS)) & np.isfinite(e))
    out = {}
    for t in C.TOURS:
        v = e[m & (rows["tour"].to_numpy() == t)]
        out[t] = {"median": float(np.median(v)), "q33": float(np.quantile(v, 1 / 3)), "q67": float(np.quantile(v, 2 / 3)),
                  "player_rows": int(len(v))}
    return out


def groups(rows: pd.DataFrame, lines: dict, r: np.ndarray) -> dict:
    """For rows r: the opponent's pre-match surface Elo and its group (missing Elo: no group)."""
    e = rows["elo_surf_own"].to_numpy(dtype="float64")[r ^ 1]
    tour = rows["tour"].to_numpy()[r]
    med = np.where(tour == "atp", lines["atp"]["median"], lines["wta"]["median"])
    q33 = np.where(tour == "atp", lines["atp"]["q33"], lines["wta"]["q33"])
    q67 = np.where(tour == "atp", lines["atp"]["q67"], lines["wta"]["q67"])
    fin = np.isfinite(e)
    return {"e": e, "fin": fin, "strong": fin & (e > med), "weak": fin & (e <= med), "top": fin & (e > q67),
            "bottom": fin & (e <= q33), "mid": fin & (e > q33) & (e <= q67), "centred": (e - med) / ELO_UNIT}


def population_slope(rows: pd.DataFrame, box_idx: np.ndarray, z: np.ndarray, g: dict) -> dict:
    """Per tour: the pooled within-player-season slope of z on the opponent's Elo (per 100 points) and the pooled
    within-player-season variance of the opponent's Elo (per match), on the box rows of 2010-2018."""
    out = {}
    yr = rows["year"].to_numpy()[box_idx]
    pc = rows["pcode"].to_numpy()[box_idx].astype("int64")
    tour = rows["tour"].to_numpy()[box_idx]
    for t in C.TOURS:
        m = np.isfinite(z) & g["fin"] & np.isin(yr, list(LINE_YEARS)) & (tour == t)
        key = pd.factorize(pd.Series(pc[m] * 100 + (yr[m] - 2000)))[0]
        e, zz = g["centred"][m], z[m]
        n = np.bincount(key).astype("float64")
        em, zm = np.bincount(key, weights=e) / n, np.bincount(key, weights=zz) / n
        de, dz = e - em[key], zz - zm[key]
        sxx, sxy = float((de * de).sum()), float((de * dz).sum())
        out[t] = {"b0": sxy / sxx, "var_e_within": sxx / len(e), "rows": int(m.sum())}
    return out


def split_features(rows: pd.DataFrame, box_idx: np.ndarray, Z: dict, used: dict, typ: dict, lines: dict,
                   slope_pop: dict, sa: dict) -> dict:
    """Every Part 3 feature for the pool matches. Z: per statistic the adjperf z per box row (box order); used: per
    statistic and tour Part 1's constants (K3, tau)."""
    A, Bi = B.pool_rows(rows)
    U = np.union1d(box_idx, np.concatenate([A, Bi]))
    upos = np.searchsorted(U, box_idx)
    ia, ib = np.searchsorted(U, A), np.searchsorted(U, Bi)
    frame = B.asof_frame(rows, U)
    g = groups(rows, lines, box_idx)
    tour_box = rows["tour"].to_numpy()[box_idx]
    tour_pool = rows["tour"].to_numpy()[A]
    out = {}

    def put(name, form, t, v):
        out.setdefault(f"{name}|{form}", np.full(len(A), np.nan))
        m = tour_pool == t
        out[f"{name}|{form}"][m] = v[m]

    gaps = {}
    for s in SPLIT_STATS:
        z = Z[s]
        for t in C.TOURS:
            c = used[s][t]
            K3, tau = float(c["K3"]), int(c["tau"])
            ok = np.isfinite(z) & (tour_box == t)
            units = sa[s]["d"][box_idx]
            w = np.where(ok, units ** tau if tau else 1.0, 0.0)
            zz = np.where(ok, z, 0.0)
            cols = []
            for grp in ("strong", "weak"):
                m = g[grp]
                cols += [w * zz * m, w * m]
            cols += [ok.astype("float64")]
            if s == "tpw":
                for grp in ("top", "mid", "bottom"):
                    m = g[grp]
                    cols += [w * zz * m, w * m]
                e = np.where(g["fin"], g["centred"], 0.0)
                f = g["fin"].astype("float64")
                cols += [w * f, w * e * f, w * e * e * f, w * zz * f, w * e * zz * f]
            V = np.zeros((len(U), len(cols)))
            V[upos] = np.column_stack(cols)
            sums = B.windowed_sums(frame, V, ())
            kref = K3 * typ[(s, t)] ** tau
            for form in FORMS:
                S = sums[form]

                def at(rowsel):
                    return S[rowsel]
                res = {}
                for side, rr in (("a", ia), ("b", ib)):
                    x = S[rr]
                    exists = x[:, 4] > 0.5
                    vs_s = x[:, 0] / (x[:, 1] + kref)
                    vs_w = x[:, 2] / (x[:, 3] + kref)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ms = np.where(x[:, 1] > 0, x[:, 0] / x[:, 1], 0.0)
                        mw = np.where(x[:, 3] > 0, x[:, 2] / x[:, 3], 0.0)
                        neff = np.where((x[:, 1] > 0) & (x[:, 3] > 0), x[:, 1] * x[:, 3] / (x[:, 1] + x[:, 3]), 0.0)
                    gap = (ms - mw) * neff / (neff + kref)
                    res[side] = {"exists": exists, "vs_strong": vs_s, "vs_weak": vs_w, "gap": gap, "naive": vs_s - vs_w}
                    if s == "tpw":
                        vt = x[:, 5] / (x[:, 6] + kref)
                        vm = x[:, 7] / (x[:, 8] + kref)
                        vb = x[:, 9] / (x[:, 10] + kref)
                        with np.errstate(divide="ignore", invalid="ignore"):
                            mt = np.where(x[:, 6] > 0, x[:, 5] / x[:, 6], 0.0)
                            mb = np.where(x[:, 10] > 0, x[:, 9] / x[:, 10], 0.0)
                            ne3 = np.where((x[:, 6] > 0) & (x[:, 10] > 0), x[:, 6] * x[:, 10] / (x[:, 6] + x[:, 10]), 0.0)
                        Sw, Se, See, Sz, Sez = x[:, 11], x[:, 12], x[:, 13], x[:, 14], x[:, 15]
                        lam = kref * slope_pop[t]["var_e_within"]
                        with np.errstate(divide="ignore", invalid="ignore"):
                            cov = np.where(Sw > 0, Sez - Se * Sz / np.where(Sw > 0, Sw, 1.0), 0.0)
                            var = np.where(Sw > 0, See - Se * Se / np.where(Sw > 0, Sw, 1.0), 0.0)
                        slope = (cov + lam * slope_pop[t]["b0"]) / (var + lam)
                        res[side].update({"top": vt, "mid": vm, "bottom": vb, "top_minus_bottom": (mt - mb) * ne3 / (ne3 + kref),
                                          "slope": slope})
                both = res["a"]["exists"] & res["b"]["exists"]

                def diff(key):
                    return np.where(both, res["a"][key] - res["b"][key], np.nan)
                put(f"vs_strong_{s}", form, t, diff("vs_strong"))
                put(f"vs_weak_{s}", form, t, diff("vs_weak"))
                put(f"strong_minus_weak_{s}", form, t, diff("gap"))
                if s == "tpw":
                    put("strong_minus_weak_naive_tpw", form, t, diff("naive"))
                    put("vs_top_third_tpw", form, t, diff("top"))
                    put("vs_mid_third_tpw", form, t, diff("mid"))
                    put("vs_bottom_third_tpw", form, t, diff("bottom"))
                    put("top_minus_bottom_third_tpw", form, t, diff("top_minus_bottom"))
                    put("slope_tpw", form, t, diff("slope"))
                    gaps.setdefault(form, {"a": np.full(len(A), np.nan), "b": np.full(len(A), np.nan),
                                           "both": np.zeros(len(A), dtype=bool)})
                    m = tour_pool == t
                    gaps[form]["a"][m] = res["a"]["gap"][m]
                    gaps[form]["b"][m] = res["b"]["gap"][m]
                    gaps[form]["both"][m] = both[m]
    # the interaction: A's gap when B is strong, minus B's when A is strong
    e_pool = rows["elo_surf_own"].to_numpy(dtype="float64")
    med = np.where(tour_pool == "atp", lines["atp"]["median"], lines["wta"]["median"])
    a_strong, b_strong = e_pool[A] > med, e_pool[Bi] > med
    known = np.isfinite(e_pool[A]) & np.isfinite(e_pool[Bi])
    for form in FORMS:
        gg = gaps[form]
        v = gg["a"] * b_strong - gg["b"] * a_strong
        out[f"strong_gap_x_strong_opp|{form}"] = np.where(gg["both"] & known, v, np.nan)
    # results above Elo's expectation against strong and weak opponents: every match played, every level
    pl = rows["played"].to_numpy() & np.isfinite(rows["p_elo_a"].to_numpy(dtype="float64"))
    allr = np.arange(len(rows))
    ga = groups(rows, lines, allr)
    p_own = np.where(rows["side"].to_numpy() == "A", rows["p_elo_a"].to_numpy(dtype="float64"),
                     1 - rows["p_elo_a"].to_numpy(dtype="float64"))
    resid = np.where(pl, rows["won"].to_numpy().astype("float64") - p_own, 0.0)
    plf = pl.astype("float64")
    V = np.column_stack([resid * ga["strong"], plf * ga["strong"], resid * ga["weak"], plf * ga["weak"], plf])
    fr_all = B.asof_frame(rows, allr)
    sums = B.windowed_sums(fr_all, V, ())
    for form in FORMS:
        S = sums[form]
        for t in C.TOURS:
            K3 = float(used["tpw"][t]["K3"])
            xa, xb = S[A], S[Bi]
            both = (xa[:, 4] > 0.5) & (xb[:, 4] > 0.5)
            put("wins_over_strong", form, t, np.where(both, xa[:, 0] / (xa[:, 1] + K3) - xb[:, 0] / (xb[:, 1] + K3), np.nan))
            put("wins_over_weak", form, t, np.where(both, xa[:, 2] / (xa[:, 3] + K3) - xb[:, 2] / (xb[:, 3] + K3), np.nan))
    return out


def earlier_weeks_variant(rows: pd.DataFrame, box_idx: np.ndarray, Z: dict, used_full: dict, typ: dict, sa: dict) -> dict:
    """A recency diagnostic for Part 1: adjperf's decayed form (its frozen h3, K3, tau) with the same event's earlier rounds
    left out, i.e. the history cut at the event's start week. It exists exactly where the full decayed form exists (a player
    whose only history is this event's earlier rounds gets 0, the prior), so the two are scored on the same matches and
    their difference is what the event's earlier rounds add."""
    A, Bi = B.pool_rows(rows)
    U = np.union1d(box_idx, np.concatenate([A, Bi]))
    upos = np.searchsorted(U, box_idx)
    ia, ib = np.searchsorted(U, A), np.searchsorted(U, Bi)
    frame = B.asof_frame(rows, U)
    pcode = pd.factorize(pd.Series(frame["player_id"].to_numpy()))[0]
    day = frame["day"].to_numpy()
    tour_box = rows["tour"].to_numpy()[box_idx]
    tour_pool = rows["tour"].to_numpy()[A]
    out = {}
    for s in SPLIT_STATS:
        col = np.full(len(A), np.nan)
        for t in C.TOURS:
            c = used_full[f"adjperf_{s}"][t]
            h3, K3, tau = float(c["h3"]), float(c["K3"]), int(c["tau"])
            ok = np.isfinite(Z[s]) & (tour_box == t)
            units = sa[s]["d"][box_idx]
            w = np.where(ok, units ** tau if tau else 1.0, 0.0)
            V = np.zeros((len(U), 3))
            lam = 0.0 if not np.isfinite(h3) else 1.0 / (7.0 * h3)
            scale = np.exp2((day[upos] - B.REF_DAY) * lam)
            V[upos, 0] = w * np.where(ok, Z[s], 0.0) * scale
            V[upos, 1] = w * scale
            V[upos, 2] = ok.astype("float64")
            before = T_sums_before(pcode, day, V, pcode, day)            # rows of earlier weeks only
            back = np.exp2(-(day - B.REF_DAY) * lam)
            num, den = before[:, 0] * back, before[:, 1] * back
            car = B.windowed_sums(frame, V[:, 2:3], ())["career"][:, 0]   # exists: as the full decayed form
            kref = K3 * typ[(s, t)] ** tau
            va, vb = num[ia] / (den[ia] + kref), num[ib] / (den[ib] + kref)
            both = (car[ia] > 0.5) & (car[ib] > 0.5)
            m = tour_pool == t
            col[m] = np.where(both, va - vb, np.nan)[m]
        out[f"adjperf_{s}|decayed, earlier weeks"] = col
    return out


def T_sums_before(pcode, day, V, q_pcode, q_day):
    from src.eda.predictability_diagnostic import stage3_traits as T
    return T.sums_before(pcode, day, V, q_pcode, q_day)


def describe(rows: pd.DataFrame, box_idx: np.ndarray, Z: dict, lines: dict) -> dict:
    """The mean z by opponent group (evaluation-level box rows, 2013-2026), and per player-season (2013-2026, every level,
    5+ matches in each group) the gap between the groups: its mean, its observed spread, the part of that spread that
    chance explains, the true spread (method of moments) and the season-to-season correlation."""
    g = groups(rows, lines, box_idx)
    yr = rows["year"].to_numpy()[box_idx]
    ev = rows["evaluation"].to_numpy()[box_idx].astype(bool)
    tour = rows["tour"].to_numpy()[box_idx]
    pc = rows["pcode"].to_numpy()[box_idx].astype("int64")
    out = {"group_means": [], "player_season_gap": []}
    for s in SPLIT_STATS:
        z = Z[s]
        for t in C.TOURS:
            base = np.isfinite(z) & (tour == t) & np.isin(yr, list(DESC_YEARS))
            for grp in ("strong", "weak", "top", "mid", "bottom"):
                m = base & ev & g[grp]
                out["group_means"].append({"stat": s, "tour": t, "group": grp, "rows": int(m.sum()),
                                           "mean_z": float(z[m].mean()), "sd_z": float(z[m].std())})
            # player-season gaps
            key = pc * 100 + (yr - 2000)
            rec = {}
            for grp in ("strong", "weak"):
                m = base & g[grp]
                df = pd.DataFrame({"k": key[m], "z": z[m]}).groupby("k")["z"].agg(["mean", "count", "var"])
                rec[grp] = df
            j = rec["strong"].join(rec["weak"], lsuffix="_s", rsuffix="_w", how="inner")
            j = j[(j["count_s"] >= MIN_GROUP) & (j["count_w"] >= MIN_GROUP)]
            # the within-group variance of a single match's z, pooled over these player-season groups
            sw = ((j["var_s"] * (j["count_s"] - 1)).sum() + (j["var_w"] * (j["count_w"] - 1)).sum()) / \
                 ((j["count_s"] - 1).sum() + (j["count_w"] - 1).sum())
            gap = j["mean_s"] - j["mean_w"]
            se2 = sw * (1 / j["count_s"] + 1 / j["count_w"])
            true_var = float(gap.var() - se2.mean())
            # season to season
            gp = pd.DataFrame({"player": j.index // 100, "season": j.index % 100, "gap": gap.to_numpy()})
            nxt = gp.assign(season=gp["season"] - 1)
            pair = gp.merge(nxt, on=["player", "season"], suffixes=("", "_next"))
            ms = pd.DataFrame({"player": j.index // 100, "season": j.index % 100, "m": j["mean_s"].to_numpy()})
            pair_s = ms.merge(ms.assign(season=ms["season"] - 1), on=["player", "season"], suffixes=("", "_next"))
            out["player_season_gap"].append({
                "stat": s, "tour": t, "player_seasons": int(len(j)), "mean_gap": float(gap.mean()),
                "sd_gap_observed": float(gap.std()), "sd_chance": float(np.sqrt(se2.mean())),
                "sd_true": float(np.sqrt(true_var)) if true_var > 0 else 0.0, "true_var": true_var,
                "reliability_typical": (float(true_var / (true_var + se2.median())) if true_var > 0 else 0.0),
                "median_matches_strong": float(j["count_s"].median()), "median_matches_weak": float(j["count_w"].median()),
                "season_pairs": int(len(pair)),
                "season_to_season_r": float(np.corrcoef(pair["gap"], pair["gap_next"])[0, 1]) if len(pair) > 2 else None,
                "strong_mean_season_to_season_r": float(np.corrcoef(pair_s["m"], pair_s["m_next"])[0, 1]) if len(pair_s) > 2 else None,
                "strong_mean_pairs": int(len(pair_s))})
    return out


def used_constants(summary_used: dict) -> dict:
    return {s: {t: summary_used[f"adjperf_{s}"][t] for t in C.TOURS} for s in SPLIT_STATS}


def probe(rows: pd.DataFrame, means: dict, chosen: dict, typ: dict, madpop: dict, used: dict, lines: dict,
          slope_pop: dict, used_full: dict) -> dict:
    """On the slice from PROBE_FROM: the per-match z (Part 1's code, frozen constants and priors) and every Part 3 feature
    rebuilt with the box scores, results, and later matches' pre-match Elo of every match a cut may not see redrawn. The
    protected matches' features must not move."""
    sl = rows["tournament_date"].ge(pd.Timestamp(PROBE_FROM)).to_numpy()
    base_rows = B.F.prepare(rows[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))
    rng = np.random.default_rng(B.SEED + 11)

    def feats(r):
        ctx = AP.Ctx(r, means, typ=typ, madpop=madpop)
        built = AP.build(ctx, chosen, stats=SPLIT_STATS)
        Z = {s: built["z"][(s, "adjperf")] for s in SPLIT_STATS}
        out = split_features(r, ctx.box_idx, Z, used, typ, lines, slope_pop, ctx.sa)
        out.update(earlier_weeks_variant(r, ctx.box_idx, Z, used_full, typ, ctx.sa))
        return out
    b0 = feats(base_rows)
    names = sorted(b0)
    A, _ = B.pool_rows(base_rows)
    week, ev, rnd = (base_rows[c].to_numpy()[A] for c in ("day", "ev", "round_order"))
    yr = base_rows["year"].to_numpy()[A]
    cand = np.flatnonzero(yr == yr.max())
    wk_all, ev_all, rn_all = (base_rows[c].to_numpy() for c in ("day", "ev", "round_order"))
    res = {"slice_from": PROBE_FROM, "cuts": 0, "protected_checked": 0, "protected_changed": 0, "later_changed": 0,
           "largest_protected_difference": 0.0, "columns": len(names)}
    counts = [f"{r}_{x}" for r in C.RATES for x in ("n",)]
    for c in rng.choice(cand, size=min(PROBE_CUTS, len(cand)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((ev != ev[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (ev == ev[c]) & (rnd <= rnd[c]))
        lat_all = (wk_all > week[c]) | ((wk_all == week[c]) & ((ev_all != ev[c]) | (rn_all >= rnd[c])))
        keep_all = (wk_all < week[c]) | ((wk_all == week[c]) & (ev_all == ev[c]) & (rn_all <= rnd[c]))
        pert = base_rows.copy()
        for col in counts:
            v = pert[col].to_numpy(dtype="float64").copy()
            dcol = np.nan_to_num(pert[col[:-2] + "_d"].to_numpy(dtype="float64"))
            draw = np.minimum(np.floor(rng.random(len(v)) * (dcol + 1)), dcol)
            pert[col] = np.where(lat_all & np.isfinite(v), draw, v)
        won = pert["won"].to_numpy().copy()
        flip = np.repeat(rng.random(len(won) // 2) < 0.5, 2) & lat_all
        pert["won"] = np.where(flip, ~won, won)
        after = lat_all & ~keep_all
        for col in ("elo_surf_own", "p_elo_a"):
            v = pert[col].to_numpy(dtype="float64").copy()
            new = (np.repeat(rng.random(len(v) // 2), 2) if col == "p_elo_a" else 1500 + 1000 * rng.random(len(v)))
            pert[col] = np.where(after, new, v)
        pert = B.F.prepare(pert)
        b1 = feats(pert)
        G = np.column_stack([b1[k] for k in names])
        B0 = np.column_stack([b0[k] for k in names])
        diff = ~np.isclose(G, B0, equal_nan=True, rtol=0, atol=PROBE_ATOL)
        gap = np.where(np.isfinite(G) & np.isfinite(B0) & keep[:, None], np.abs(G - B0), 0.0)
        res["cuts"] += 1
        res["protected_checked"] += int(keep.sum())
        res["protected_changed"] += int((diff.any(axis=1) & keep).sum())
        res["later_changed"] += int((diff.any(axis=1) & ~keep).sum())
        res["largest_protected_difference"] = max(res["largest_protected_difference"], float(gap.max()))
        B.log(f"  probe cut {res['cuts']}: protected changed {res['protected_changed']}, later changed {res['later_changed']}")
    return res


def main() -> int:
    t_start = time.time()
    timings = {}
    rows, _ = B.load_rows()
    means = B.surface_means()
    import json
    summ = json.loads(AP.ADJ_SUMMARY.read_text(encoding="utf-8"))
    chosen, typ, madpop = AP.load_frozen()
    used = used_constants(summ["used"])
    adj = pd.read_parquet(AP.ADJ_PARQUET, columns=["row"] + [f"z_adjperf_{s}" for s in SPLIT_STATS])
    box_idx = adj["row"].to_numpy()
    Z = {s: adj[f"z_adjperf_{s}"].to_numpy(dtype="float64") for s in SPLIT_STATS}
    sa = B.stat_arrays(rows, means, SPLIT_STATS)
    lines = strength_lines(rows)
    g = groups(rows, lines, box_idx)
    slope_pop = population_slope(rows, box_idx, Z["tpw"], g)
    B.log(f"lines {lines}; population slope {slope_pop}")
    feats = split_features(rows, box_idx, Z, used, typ, lines, slope_pop, sa)
    feats.update(earlier_weeks_variant(rows, box_idx, Z, summ["used"], typ, sa))
    pool = H.load_pool()
    A, _ = B.pool_rows(rows)
    assert (pool["match_id"].to_numpy() == rows["match_id"].to_numpy()[A]).all()
    fr = pd.DataFrame({"match_id": pool["match_id"].to_numpy()})
    for k, v in feats.items():
        fr[k] = np.asarray(v, dtype="float32")
    fr.to_parquet(SPLIT_FEATURES, index=False, compression="zstd")
    timings["features"] = round(time.time() - t_start, 1)
    B.log(f"wrote {SPLIT_FEATURES.name} ({fr.shape[1] - 1} columns)")
    desc = describe(rows, box_idx, Z, lines)
    for d in desc["player_season_gap"]:
        B.log(f"  gap {d['tour']} {d['stat']}: {d['player_seasons']} player-seasons, mean {d['mean_gap']:.3f}, observed sd "
              f"{d['sd_gap_observed']:.3f}, chance sd {d['sd_chance']:.3f}, true sd {d['sd_true']:.3f}, "
              f"season to season r {d['season_to_season_r']}")
    t0 = time.time()
    pr = probe(rows, means, chosen, typ, madpop, used, lines, slope_pop, summ["used"])
    timings["probe"] = round(time.time() - t0, 1)
    timings["total"] = round(time.time() - t_start, 1)
    exists = {col: {t: int(np.isfinite(v[(pool["tour"].to_numpy() == t) & pool["evaluation"].to_numpy()]).sum())
                    for t in C.TOURS} for col, v in feats.items()}
    corr = {}
    for form in FORMS:
        for s in ("tpw",):
            a, b = feats[f"strong_minus_weak_{s}|{form}"], feats[f"strong_minus_weak_naive_{s}|{form}"]
            e = np.isfinite(a) & np.isfinite(b)
            corr[f"contrast_vs_naive_{s}|{form}"] = float(np.corrcoef(a[e], b[e])[0, 1])
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "settings": {"stats": list(SPLIT_STATS), "forms": list(FORMS), "main_tour": list(MAIN_TOUR),
                            "line_years": [LINE_YEARS[0], LINE_YEARS[-1]], "elo_unit": ELO_UNIT, "min_group": MIN_GROUP,
                            "describe_years": [DESC_YEARS[0], DESC_YEARS[-1]]},
               "lines": lines, "population_slope": slope_pop, "used": used, "describe": desc,
               "share_vs_strong": {t: float(g["strong"][(rows["tour"].to_numpy()[box_idx] == t) & np.isfinite(Z["tpw"])].mean())
                                   for t in C.TOURS},
               "contrast_vs_naive_corr": corr, "exists_evaluation_matches": exists, "probe": pr, "seconds": timings}
    B.jdump(summary, SPLIT_SUMMARY)
    B.log(f"wrote {SPLIT_SUMMARY.name}; total {timings['total']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
