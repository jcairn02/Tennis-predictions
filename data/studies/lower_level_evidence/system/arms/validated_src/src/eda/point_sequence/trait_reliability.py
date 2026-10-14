"""A1-T step 2: split-half reliability of the momentum and streak statistics, real against iid replays; the ability
check; Holm over the pre-registered family; recovery of the career truth by depth; and the calibration diagnostics.

Pre-registration: data/studies/point_sequence/trait_prereg.md. Run after trait_build.py:
    ./python.sh src/eda/point_sequence/trait_reliability.py

Writes (data/studies/point_sequence/):
    trait_reliability.csv     per tour x population (>= 20 / >= 50 per half, strict, source-centred) x statistic x world
                              family: reliability (mean r over 50 splits), players, and real - replay with a player
                              bootstrap interval
    trait_tests.csv           the pre-registered family (S1-S5 x tours, V1), Holm, the ability check, pass / fail; the
                              placebo; S4r (secondary); the same decisions under V05, V15, VPS
    trait_means.csv           population means of each statistic (pooled sum X / sum D), real against replays
    trait_rho2_depth.csv      rho^2 of the shrunk 52-week value with the career truth, by depth quartile
    trait_calibration.csv     between-set serve-residual correlation and match-structure diagnostics, real vs replays
    trait_results.json        everything above, plus the empirical-Bayes constants
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.predictability_diagnostic.stage3_traits import eb_constants, unit_sums  # noqa: E402

SPLITS = 50
BOOT = 2000
SEED = 20261007
HALF_MIN = {"ge20": 20, "ge50": 50}
FAMILIES = {"V1": [f"V1_{r}" for r in range(TC.REPLAYS)], "V05": [f"V05_{r}" for r in range(TC.REPLAYS)],
            "V15": [f"V15_{r}" for r in range(TC.REPLAYS)], "VPS": [f"VPS_{r}" for r in range(TC.REPLAYS)]}
ALL_WORLDS = ["real"] + [w for f in FAMILIES.values() for w in f]
K = len(TC.STATS)
TARGET_FROM = {"atp": 2014, "wta": 2017}
WEEK52 = 364
ALPHA = 0.05
MARGIN = 0.10
ABILITY_MAX = 0.3


def log(msg):
    TC.log(msg)


# ------------------------------------------------------------------------------------------------
# Loading

def load() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    pm = pd.concat([pd.read_parquet(TC.OUT / "trait_player_matches.parquet"),
                    pd.read_parquet(TC.OUT / "trait_player_matches_variants.parquet")], ignore_index=True)
    X, D = {}, {}
    base = None
    tot = {}
    for w, g in pm.groupby("world", sort=False):
        g = g.sort_values(["mcode", "side"], kind="mergesort")
        key = g[["mcode", "side"]].to_numpy()
        if base is None:
            base = key
        assert (key == base).all(), w
        X[w] = np.column_stack([g[f"X_{s}"].to_numpy("float64") for s in TC.STATS])
        D[w] = np.column_stack([g[f"D_{s}"].to_numpy("float64") for s in TC.STATS])
        tot[w] = g[["svc_games", "holds", "ret_games", "breaks", "svpt", "svpt_won", "set1_n", "set1_w", "late_n",
                    "late_w"]].to_numpy("float64")
    rows = pd.DataFrame({"mcode": base[:, 0], "side": base[:, 1]})
    mc = rows["mcode"].to_numpy()
    rows["player"] = np.where(rows["side"].to_numpy() == 1, pop["player_a_id"].to_numpy()[mc],
                              pop["player_b_id"].to_numpy()[mc])
    for c in ("tour", "year", "obs", "round_order", "source", "strict", "match_id", "bo", "surface"):
        rows[c] = pop[c].to_numpy()[mc]
    return pop, rows, {"X": X, "D": D}, tot


# ------------------------------------------------------------------------------------------------
# Split-half reliability with a player bootstrap

def make_splits(pcode: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """SPLITS x rows: 0/1 half of each row; each player's rows split at random into halves of equal size (+- 1)."""
    out = np.empty((SPLITS, len(pcode)), np.int8)
    for s in range(SPLITS):
        o = np.lexsort((rng.random(len(pcode)), pcode))
        ps = pcode[o]
        rank = np.arange(len(ps)) - np.searchsorted(ps, ps, side="left")
        h = np.empty(len(pcode), np.int8)
        h[o] = (rank % 2).astype(np.int8)
        out[s] = h
    return out


def half_rates(pcode, P, half, Xw, Dw):
    """Per player x half: rates (P, 2, K) and validity (P, K)."""
    idx = pcode * 2 + half
    sx = np.stack([np.bincount(idx, weights=Xw[:, k], minlength=2 * P) for k in range(Xw.shape[1])], axis=1).reshape(P, 2, -1)
    sd = np.stack([np.bincount(idx, weights=Dw[:, k], minlength=2 * P) for k in range(Dw.shape[1])], axis=1).reshape(P, 2, -1)
    valid = (sd[:, 0, :] > 0) & (sd[:, 1, :] > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = np.where(sd > 0, sx / np.where(sd > 0, sd, 1.0), 0.0)
    return rate, valid


def corr_valid(a, b, v):
    a, b = a[v], b[v]
    if len(a) < 4 or a.std() == 0 or b.std() == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def reliability_block(pcode, P, halves, Xs: dict, Ds: dict, worlds: list, W: np.ndarray | None):
    """Reliability per world x statistic (mean r over splits) and, with bootstrap weights W (B x P), the bootstrap
    replicates (B x worlds x K). Also returns the per-split full-sample r (splits x worlds x K) and players used."""
    nw = len(worlds)
    K = Xs[worlds[0]].shape[1]
    r_full = np.full((SPLITS, nw, K), np.nan)
    n_used = np.zeros((SPLITS, nw, K))
    boot = None if W is None else np.zeros((W.shape[0], nw, K))
    for s in range(SPLITS):
        cols, metas = [], []
        for wi, w in enumerate(worlds):
            rate, valid = half_rates(pcode, P, halves[s], Xs[w], Ds[w])
            for k in range(K):
                v = valid[:, k]
                a, b = rate[:, 0, k], rate[:, 1, k]
                r_full[s, wi, k] = corr_valid(a, b, v)
                n_used[s, wi, k] = v.sum()
                if W is not None:
                    vf = v.astype("float64")
                    am = a[v].mean() if v.any() else 0.0
                    bm = b[v].mean() if v.any() else 0.0
                    ac, bc = (a - am) * vf, (b - bm) * vf
                    cols.append(np.column_stack([vf, ac, bc, ac * ac, bc * bc, ac * bc]))
                    metas.append((wi, k))
        if W is not None:
            M = np.concatenate(cols, axis=1)                       # P x 6*(nw*K)
            S = W @ M                                              # B x 6*(nw*K)
            S = S.reshape(W.shape[0], -1, 6)
            n = S[:, :, 0]
            with np.errstate(divide="ignore", invalid="ignore"):
                ma, mb = S[:, :, 1] / n, S[:, :, 2] / n
                cov = S[:, :, 5] / n - ma * mb
                va = S[:, :, 3] / n - ma * ma
                vb = S[:, :, 4] / n - mb * mb
                r = cov / np.sqrt(va * vb)
            for j, (wi, k) in enumerate(metas):
                boot[:, wi, k] += r[:, j]
    if boot is not None:
        boot /= SPLITS
    return np.nanmean(r_full, axis=0), boot, r_full, np.median(n_used, axis=0)


def run_population(label, tour, rows_mask, rows, XD, worlds, half_min, rng, want_boot=True, Xover=None):
    """Reliability for one tour x population. Returns per-world reliability, bootstrap replicates, players."""
    sub = np.flatnonzero(rows_mask)
    players = rows["player"].to_numpy()[sub]
    pc_all, uniq = pd.factorize(pd.Series(players))
    cnt = np.bincount(pc_all)
    elig_p = cnt >= 2 * half_min
    keep = elig_p[pc_all]
    sub = sub[keep]
    pcode, uniq2 = pd.factorize(pd.Series(rows["player"].to_numpy()[sub]))
    P = len(uniq2)
    halves = make_splits(pcode, rng)
    Xsrc = XD["X"] if Xover is None else Xover
    Xs = {w: Xsrc[w][sub] for w in worlds}
    Ds = {w: XD["D"][w][sub] for w in worlds}
    W = None
    if want_boot:
        W = np.zeros((BOOT, P))
        for b in range(BOOT):
            W[b] = np.bincount(rng.integers(0, P, P), minlength=P)
    rel, boot, r_full, n_used = reliability_block(pcode, P, halves, Xs, Ds, worlds, W)
    return {"label": label, "tour": tour, "players": P, "player_matches": int(len(sub)),
            "matches_per_player_median": float(np.median(np.bincount(pcode))), "rel": rel, "boot": boot,
            "r_split_sd": np.nanstd(r_full, axis=0), "n_used": n_used, "worlds": worlds, "sub": sub,
            "pcode": pcode, "halves": halves}


def family_index(worlds, fam):
    return [worlds.index(w) for w in FAMILIES[fam]]


def delta_stats(res, fam, k):
    wi = family_index(res["worlds"], fam)
    real = res["rel"][res["worlds"].index("real"), k]
    rep = float(np.mean(res["rel"][wi, k]))
    d = real - rep
    out = {"real_r": real, "replay_r": rep, "delta": d}
    if res["boot"] is not None:
        bd = res["boot"][:, res["worlds"].index("real"), k] - res["boot"][:, wi, k].mean(axis=1)
        bd = bd[np.isfinite(bd)]
        se = float(bd.std(ddof=1))
        out.update({"delta_lo": float(np.percentile(bd, 2.5)), "delta_hi": float(np.percentile(bd, 97.5)),
                    "delta_se": se, "p_two_sided": float(2 * norm.sf(abs(d) / se)) if se > 0 else np.nan,
                    "boot_valid": int(len(bd)), "_boot": bd})
    return out


def holm(p: np.ndarray) -> np.ndarray:
    m = len(p)
    o = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for i, j in enumerate(o):
        run = max(run, min(1.0, (m - i) * p[j]))
        adj[j] = run
    return adj


# ------------------------------------------------------------------------------------------------
# Ability check

def ability(res, XD, tot, world="real"):
    """Across the eligible players: r of the statistic (all their matches) with hold rate and with break rate; and the
    cross-half version (statistic in one half against the rate in the other)."""
    sub, pcode = res["sub"], res["pcode"]
    P = res["players"]
    Xw, Dw, T = XD["X"][world][sub], XD["D"][world][sub], tot[world][sub]
    sx = np.stack([np.bincount(pcode, weights=Xw[:, k], minlength=P) for k in range(K)], 1)
    sd = np.stack([np.bincount(pcode, weights=Dw[:, k], minlength=P) for k in range(K)], 1)
    hold = np.bincount(pcode, weights=T[:, 1], minlength=P) / np.bincount(pcode, weights=T[:, 0], minlength=P)
    brk = np.bincount(pcode, weights=T[:, 3], minlength=P) / np.bincount(pcode, weights=T[:, 2], minlength=P)
    out = {}
    for k, s in enumerate(TC.STATS):
        v = (sd[:, k] > 0) & np.isfinite(hold) & np.isfinite(brk)
        st = sx[v, k] / sd[v, k]
        out[s] = {"r_hold": float(np.corrcoef(st, hold[v])[0, 1]), "r_break": float(np.corrcoef(st, brk[v])[0, 1]),
                  "players": int(v.sum())}
    # cross-half
    cross = {s: {"hold": [], "break": []} for s in TC.STATS}
    for s_i in range(SPLITS):
        h = res["halves"][s_i]
        idx = pcode * 2 + h
        sxh = np.stack([np.bincount(idx, weights=Xw[:, k], minlength=2 * P) for k in range(K)], 1).reshape(P, 2, K)
        sdh = np.stack([np.bincount(idx, weights=Dw[:, k], minlength=2 * P) for k in range(K)], 1).reshape(P, 2, K)
        sg = np.bincount(idx, weights=T[:, 0], minlength=2 * P).reshape(P, 2)
        hd = np.bincount(idx, weights=T[:, 1], minlength=2 * P).reshape(P, 2)
        rg = np.bincount(idx, weights=T[:, 2], minlength=2 * P).reshape(P, 2)
        bk = np.bincount(idx, weights=T[:, 3], minlength=2 * P).reshape(P, 2)
        for k, s in enumerate(TC.STATS):
            for a, b in ((0, 1), (1, 0)):
                v = (sdh[:, a, k] > 0) & (sg[:, b] > 0) & (rg[:, b] > 0)
                st = sxh[v, a, k] / sdh[v, a, k]
                cross[s]["hold"].append(np.corrcoef(st, hd[v, b] / sg[v, b])[0, 1])
                cross[s]["break"].append(np.corrcoef(st, bk[v, b] / rg[v, b])[0, 1])
    for s in TC.STATS:
        out[s]["cross_half_r_hold"] = float(np.nanmean(cross[s]["hold"]))
        out[s]["cross_half_r_break"] = float(np.nanmean(cross[s]["break"]))
    return out


# ------------------------------------------------------------------------------------------------
# Population means (within-match dynamics at population level)

def pop_means(rows, XD, rng, B=1000):
    out = []
    for tour in ("atp", "wta"):
        sub = np.flatnonzero(rows["tour"].to_numpy() == tour)
        pcode, uniq = pd.factorize(pd.Series(rows["player"].to_numpy()[sub]))
        P = len(uniq)
        W = np.zeros((B, P))
        for b in range(B):
            W[b] = np.bincount(rng.integers(0, P, P), minlength=P)
        sums = {}
        for w in ALL_WORLDS:
            sx = np.stack([np.bincount(pcode, weights=XD["X"][w][sub][:, k], minlength=P) for k in range(K)], 1)
            sd = np.stack([np.bincount(pcode, weights=XD["D"][w][sub][:, k], minlength=P) for k in range(K)], 1)
            sums[w] = (sx, sd)
        for k, s in enumerate(TC.STATS):
            real = sums["real"][0][:, k].sum() / sums["real"][1][:, k].sum()
            breal = (W @ sums["real"][0][:, k]) / (W @ sums["real"][1][:, k])
            row = {"tour": tour, "stat": s, "player_matches": int(len(sub)), "real_mean": float(real)}
            for fam, ws in FAMILIES.items():
                rep = np.mean([sums[w][0][:, k].sum() / sums[w][1][:, k].sum() for w in ws])
                brep = np.mean([(W @ sums[w][0][:, k]) / (W @ sums[w][1][:, k]) for w in ws], axis=0)
                d = breal - brep
                row[f"{fam}_mean"] = float(rep)
                row[f"real_minus_{fam}"] = float(real - rep)
                row[f"real_minus_{fam}_lo"] = float(np.percentile(d, 2.5))
                row[f"real_minus_{fam}_hi"] = float(np.percentile(d, 97.5))
            out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# Recovery of the career truth by depth

def eb_for(rows_t, Xw, Dw, k):
    """Empirical-Bayes mu, K on seasons <= 2018 with player-season windows (Stage 3's method of moments)."""
    sel = rows_t["year"].to_numpy() <= TC.PRIOR_LAST_YEAR
    x, d = Xw[sel, k], Dw[sel, k]
    key = pd.Series(rows_t["player"].to_numpy()[sel]).astype(str) + "|" + pd.Series(rows_t["year"].to_numpy()[sel]).astype(str)
    unit, _ = pd.factorize(key)
    s = unit_sums(unit, x, d)
    est = eb_constants(s["D"], s["X"], s["W"], s["m"])
    return float(est["mu"]), float(est["K"]), float(est["s2"]), float(est["tau2"])


def rho2_depth(rows, XD):
    out, consts = [], []
    for tour in ("atp", "wta"):
        sub = np.flatnonzero(rows["tour"].to_numpy() == tour)
        rt = rows.iloc[sub].reset_index(drop=True)
        pcode, _ = pd.factorize(rt["player"])
        order = np.lexsort((rt["mcode"].to_numpy(), rt["round_order"].to_numpy(), rt["obs"].to_numpy(), pcode))
        pc_o = pcode[order]
        obs_o = rt["obs"].to_numpy()[order].astype(np.int64)
        key = pc_o * 1_000_000 + obs_o
        lo = np.searchsorted(key, pc_o * 1_000_000 + obs_o - WEEK52, side="left")
        pos = np.arange(len(order))
        year_o = rt["year"].to_numpy()[order]
        target = year_o >= TARGET_FROM[tour]
        n52 = pos - lo
        for k, s in enumerate(TC.STATS):
            real_depth = None
            per_world = {}
            for w in ALL_WORLDS:
                Xw, Dw = XD["X"][w][sub][order], XD["D"][w][sub][order]
                mu, Kc, s2, tau2 = eb_for(rt.iloc[order].reset_index(drop=True), Xw, Dw, k)
                consts.append({"tour": tour, "stat": s, "world": w, "mu": mu, "K": Kc, "s2": s2, "tau2": tau2})
                cx = np.r_[0, np.cumsum(Xw[:, k])]
                cd = np.r_[0, np.cumsum(Dw[:, k])]
                X52, D52 = cx[pos] - cx[lo], cd[pos] - cd[lo]
                Xc = np.bincount(pc_o, weights=Xw[:, k])[pc_o]
                Dc = np.bincount(pc_o, weights=Dw[:, k])[pc_o]
                Xd, Dd = Xc - X52 - Xw[:, k], Dc - D52 - Dw[:, k]
                finite = np.isfinite(Kc) and Kc > 0
                with np.errstate(divide="ignore", invalid="ignore"):
                    if finite:
                        v52 = (X52 + Kc * mu) / (D52 + Kc)
                        tc = (Xc + Kc * mu) / (Dc + Kc)
                        td = (Xd + Kc * mu) / (Dd + Kc)
                    else:
                        v52, tc, td = X52 / D52, Xc / Dc, Xd / Dd
                if w == "real":
                    real_depth = D52.copy()
                per_world[w] = (v52, tc, td, finite)
            ok = target & (real_depth > 0)
            edges = np.quantile(real_depth[ok], [0, 0.25, 0.5, 0.75, 1.0])
            q = np.clip(np.searchsorted(edges, real_depth, side="right") - 1, 0, 3)
            for qi in [None, 0, 1, 2, 3]:
                m = ok & ((q == qi) if qi is not None else True)
                row = {"tour": tour, "stat": s, "quartile": "all" if qi is None else qi + 1, "targets": int(m.sum()),
                       "depth_min": float(real_depth[m].min()), "depth_median": float(np.median(real_depth[m])),
                       "depth_max": float(real_depth[m].max()), "matches_in_52w_median": float(np.median(n52[m]))}
                for fam in ["real"] + list(FAMILIES):
                    ws = ["real"] if fam == "real" else FAMILIES[fam]
                    for tname, ti in (("career", 1), ("disjoint", 2)):
                        vals = []
                        for w in ws:
                            v52, tc, td, finite = per_world[w]
                            tr = (tc, td)[ti - 1]
                            mm = m & np.isfinite(v52) & np.isfinite(tr)
                            vals.append(np.corrcoef(v52[mm], tr[mm])[0, 1] ** 2 if mm.sum() > 10 else np.nan)
                        row[f"rho2_{tname}_{fam}"] = float(np.nanmean(vals))
                    row[f"shrunk_{fam}"] = bool(all(per_world[w][3] for w in ws))
                out.append(row)
        log(f"  rho2 {tour} done")
    return pd.DataFrame(out), pd.DataFrame(consts)


# ------------------------------------------------------------------------------------------------
# Calibration diagnostics

def calibration(rows, tot, pop):
    rat = pd.read_parquet(TC.RATINGS, columns=["match_id", "p_serve_a", "p_serve_b"])
    pa = pd.Series(rat["p_serve_a"].to_numpy(), index=rat["match_id"]).reindex(rows["match_id"]).to_numpy()
    pb = pd.Series(rat["p_serve_b"].to_numpy(), index=rat["match_id"]).reindex(rows["match_id"]).to_numpy()
    p = np.where(rows["side"].to_numpy() == 1, pa, pb)
    out = []
    for tour in ("atp", "wta"):
        for bo in (3, 5):
            m0 = (rows["tour"].to_numpy() == tour) & (rows["bo"].to_numpy() == bo) & np.isfinite(p)
            if m0.sum() == 0:
                continue
            row = {"tour": tour, "best_of": bo, "player_matches": int(m0.sum()),
                   "p_serve_coverage": float(np.isfinite(p[(rows["tour"].to_numpy() == tour) & (rows["bo"].to_numpy() == bo)]).mean())}
            for fam in ["real"] + list(FAMILIES):
                ws = ["real"] if fam == "real" else FAMILIES[fam]
                rs, rs_own = [], []
                for w in ws:
                    T = tot[w]
                    n1, w1, nl, wl = T[:, 6], T[:, 7], T[:, 8], T[:, 9]
                    mm = m0 & (n1 > 0) & (nl > 0)
                    pp = p[mm]
                    z1 = (w1[mm] - n1[mm] * pp) / np.sqrt(n1[mm] * pp * (1 - pp))
                    zl = (wl[mm] - nl[mm] * pp) / np.sqrt(nl[mm] * pp * (1 - pp))
                    rs.append(np.corrcoef(z1, zl)[0, 1])
                row[f"r_set1_late_{fam}"] = float(np.mean(rs))
            out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    pop, rows, XD, tot = load()
    log(f"loaded {len(rows):,} player-match rows x {len(XD['X'])} worlds")
    rng = np.random.default_rng(SEED)
    results = {"seed": SEED, "splits": SPLITS, "boot": BOOT, "families": FAMILIES}
    rel_rows, test_rows = [], []
    store = {}
    for tour in ("atp", "wta"):
        tmask = rows["tour"].to_numpy() == tour
        for pname, hm in HALF_MIN.items():
            res = run_population(pname, tour, tmask, rows, XD, ALL_WORLDS, hm, rng)
            store[(tour, pname)] = res
            log(f"{tour} {pname}: {res['players']} players, {res['player_matches']:,} player-matches")
            for k, s in enumerate(TC.STATS):
                base = {"tour": tour, "population": pname, "stat": s, "players": res["players"],
                        "player_matches": res["player_matches"], "matches_per_player_median": res["matches_per_player_median"],
                        "players_used_real": float(res["n_used"][0, k])}
                for fam in FAMILIES:
                    d = delta_stats(res, fam, k)
                    d.pop("_boot", None)
                    rel_rows.append({**base, "family": fam, **d,
                                     "real_r_split_sd": float(res["r_split_sd"][0, k])})
        # sensitivities at >= 20 per half: strict subset; source-centred
        smask = tmask & rows["strict"].to_numpy().astype(bool)
        res = run_population("ge20_strict", tour, smask, rows, XD, ["real"] + FAMILIES["V1"], 20, rng)
        store[(tour, "ge20_strict")] = res
        for k, s in enumerate(TC.STATS):
            d = delta_stats(res, "V1", k)
            d.pop("_boot", None)
            rel_rows.append({"tour": tour, "population": "ge20_strict", "stat": s, "players": res["players"],
                             "player_matches": res["player_matches"],
                             "matches_per_player_median": res["matches_per_player_median"],
                             "players_used_real": float(res["n_used"][0, k]), "family": "V1", **d,
                             "real_r_split_sd": float(res["r_split_sd"][0, k])})
        Xc = {}
        src = rows["source"].to_numpy()
        for w in ["real"] + FAMILIES["V1"]:
            Xw, Dw = XD["X"][w].copy(), XD["D"][w]
            for sname in np.unique(src[tmask]):
                mm = tmask & (src == sname)
                mu = Xw[mm].sum(0) / np.where(Dw[mm].sum(0) > 0, Dw[mm].sum(0), 1)
                Xw[mm] = Xw[mm] - Dw[mm] * mu
            Xc[w] = Xw
        res = run_population("ge20_source_centred", tour, tmask, rows, XD, ["real"] + FAMILIES["V1"], 20, rng, Xover=Xc)
        store[(tour, "ge20_source_centred")] = res
        for k, s in enumerate(TC.STATS):
            d = delta_stats(res, "V1", k)
            d.pop("_boot", None)
            rel_rows.append({"tour": tour, "population": "ge20_source_centred", "stat": s, "players": res["players"],
                             "player_matches": res["player_matches"],
                             "matches_per_player_median": res["matches_per_player_median"],
                             "players_used_real": float(res["n_used"][0, k]), "family": "V1", **d,
                             "real_r_split_sd": float(res["r_split_sd"][0, k])})
        log(f"{tour} sensitivities done")
    rel = pd.DataFrame(rel_rows)
    rel.to_csv(TC.OUT / "trait_reliability.csv", index=False)
    # ---- the pre-registered family and decisions
    abil = {tour: ability(store[(tour, "ge20")], XD, tot) for tour in ("atp", "wta")}
    abil_rep = {tour: ability(store[(tour, "ge20")], XD, tot, world="V1_0") for tour in ("atp", "wta")}
    for fam in FAMILIES:
        fam_rows = []
        for tour in ("atp", "wta"):
            res = store[(tour, "ge20")]
            for k, s in enumerate(TC.STATS):
                d = delta_stats(res, fam, k)
                d.pop("_boot", None)
                a = abil[tour][s]
                fam_rows.append({"family": fam, "tour": tour, "stat": s, **d, "players": res["players"],
                                 "r_hold": a["r_hold"], "r_break": a["r_break"],
                                 "ability_max_abs_r": max(abs(a["r_hold"]), abs(a["r_break"])),
                                 "cross_half_r_hold": a["cross_half_r_hold"], "cross_half_r_break": a["cross_half_r_break"],
                                 "replay_r_hold": abil_rep[tour][s]["r_hold"], "replay_r_break": abil_rep[tour][s]["r_break"]})
        fr = pd.DataFrame(fam_rows)
        prim = fr["stat"].isin(TC.PRIMARY)
        fr.loc[prim, "p_holm"] = holm(fr.loc[prim, "p_two_sided"].to_numpy())
        sec = fr["stat"].eq("S4r")
        fr.loc[sec, "p_holm"] = holm(fr.loc[sec, "p_two_sided"].to_numpy())
        pl = fr[fr["stat"].eq("P0")].set_index("tour")
        fr["placebo_delta"] = fr["tour"].map(pl["delta"])
        fr["placebo_covers_0"] = fr["tour"].map((pl["delta_lo"] <= 0) & (pl["delta_hi"] >= 0))
        ok = (fr["delta"] >= MARGIN) & (fr["delta"] > 0) & (fr["p_holm"] < ALPHA) & (fr["ability_max_abs_r"] < ABILITY_MAX)
        tighten = ~fr["placebo_covers_0"].astype(bool) & (fr["delta"] - fr["placebo_delta"] < MARGIN)
        fr["pass"] = np.where(fr["stat"].isin(TC.PRIMARY + ["S4r"]), ok & ~tighten, np.nan)
        test_rows.append(fr)
    tests = pd.concat(test_rows, ignore_index=True)
    tests.to_csv(TC.OUT / "trait_tests.csv", index=False)
    log("tests written")
    means = pop_means(rows, XD, rng)
    means.to_csv(TC.OUT / "trait_means.csv", index=False)
    log("population means written")
    cal = calibration(rows, tot, pop)
    cal.to_csv(TC.OUT / "trait_calibration.csv", index=False)
    log("calibration written")
    rho, consts = rho2_depth(rows, XD)
    rho.to_csv(TC.OUT / "trait_rho2_depth.csv", index=False)
    results.update({"reliability": json.loads(rel.to_json(orient="records")),
                    "tests": json.loads(tests.to_json(orient="records")),
                    "means": json.loads(means.to_json(orient="records")),
                    "calibration": json.loads(cal.to_json(orient="records")),
                    "rho2_depth": json.loads(rho.to_json(orient="records")),
                    "eb_constants": json.loads(consts.to_json(orient="records")),
                    "ability": abil, "ability_replay_V1_0": abil_rep,
                    "seconds": round(time.time() - t0, 1)})
    (TC.OUT / "trait_results.json").write_text(json.dumps(results, indent=1, default=float) + "\n", encoding="utf-8")
    log("wrote trait_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
