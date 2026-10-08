"""Return leverage (RL) and serve leverage (SL): the pre-registered trait gate.

Pre-registration: data/studies/point_sequence/lev_prereg.md (frozen by lev_prereg.sha256; this script stops if the
file's hash differs). Run after trait_build.py:  ./python.sh src/eda/point_sequence/lev_run.py

Worlds: real; 3 exact within-set shuffles per side (shuf_j); the 3 V1 iid replays (rep_r, regenerated with
trait_build's seeds) and one shuffle of each (repshuf_r). Importance always at the pre-match p_serve.
Writes lev_player_matches.parquet, lev_reliability.csv, lev_tests.csv, lev_rho2.csv, lev_mass.csv, lev_results.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import lev_common as LC  # noqa: E402
from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.point_sequence import trait_reliability as TR  # noqa: E402

PREREG = TC.OUT / "lev_prereg.md"
HASH = TC.OUT / "lev_prereg.sha256"
STATS = ["RL", "SL"]
SHUF = [f"shuf_{j}" for j in range(3)]
REP = [f"rep_{r}" for r in range(3)]
REPSHUF = [f"repshuf_{r}" for r in range(3)]
REL_SEED = 20261009


def combine(levs: dict) -> np.ndarray:
    """Null rows from the two side-worlds of one shuffle: SL of side X and RL of the other from world X."""
    out = np.zeros((len(levs[1]), 4))
    side = levs[1]["side"].to_numpy()
    for X in (1, 2):
        d = levs[X]
        sl = side == X
        rl = side == 3 - X
        out[sl, 2:] = d.loc[sl, ["X_SL", "D_SL"]].to_numpy()
        out[rl, :2] = d.loc[rl, ["X_RL", "D_RL"]].to_numpy()
    return out                                                  # columns X_RL, D_RL, X_SL, D_SL


def world_arrays(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return a[:, [0, 2]], a[:, [1, 3]]


def delta(res, ia, ib):
    rel, boot = res["rel"], res["boot"]
    out = []
    for k in range(rel.shape[1]):
        d = rel[ia, k].mean() - rel[ib, k].mean()
        bd = boot[:, ia, k].mean(1) - boot[:, ib, k].mean(1)
        bd = bd[np.isfinite(bd)]
        se = float(bd.std(ddof=1))
        out.append({"a_r": float(rel[ia, k].mean()), "b_r": float(rel[ib, k].mean()), "delta": float(d),
                    "lo": float(np.percentile(bd, 2.5)), "hi": float(np.percentile(bd, 97.5)), "se": se,
                    "p": float(2 * norm.sf(abs(d) / se)) if se > 0 else np.nan})
    return out


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty(len(p))
    run = 0.0
    for i, j in enumerate(o):
        run = max(run, min(1.0, (len(p) - i) * p[j]))
        adj[j] = run
    return adj


def rho2(rows, Xw, Dw, worlds):
    """Disjoint-truth rho^2 of the shrunk 52-week value, overall and by depth quartile (trait_reliability's logic)."""
    out = []
    for tour in ("atp", "wta"):
        sub = np.flatnonzero(rows["tour"].to_numpy() == tour)
        rt = rows.iloc[sub].reset_index(drop=True)
        pcode, _ = pd.factorize(rt["player"])
        order = np.lexsort((rt["mcode"].to_numpy(), rt["round_order"].to_numpy(), rt["obs"].to_numpy(), pcode))
        pc = pcode[order]
        obs = rt["obs"].to_numpy()[order].astype(np.int64)
        key = pc * 1_000_000 + obs
        lo = np.searchsorted(key, pc * 1_000_000 + obs - TR.WEEK52, side="left")
        pos = np.arange(len(order))
        target = rt["year"].to_numpy()[order] >= TR.TARGET_FROM[tour]
        rto = rt.iloc[order].reset_index(drop=True)
        for k, s in enumerate(STATS):
            vals, depth = {}, None
            for w in worlds:
                X, D = Xw[w][sub][order], Dw[w][sub][order]
                mu, K, _, _ = TR.eb_for(rto, X, D, k)
                cx, cd = np.r_[0, np.cumsum(X[:, k])], np.r_[0, np.cumsum(D[:, k])]
                X52, D52 = cx[pos] - cx[lo], cd[pos] - cd[lo]
                Xc = np.bincount(pc, weights=X[:, k])[pc]
                Dc = np.bincount(pc, weights=D[:, k])[pc]
                Xd, Dd = Xc - X52 - X[:, k], Dc - D52 - D[:, k]
                with np.errstate(divide="ignore", invalid="ignore"):
                    if np.isfinite(K) and K > 0:
                        v52, td = (X52 + K * mu) / (D52 + K), (Xd + K * mu) / (Dd + K)
                    else:
                        v52, td = X52 / D52, Xd / Dd
                vals[w] = (v52, td, float(K))
                if w == "real":
                    depth = D52
            ok = target & (depth > 0)
            edges = np.quantile(depth[ok], [0, 0.25, 0.5, 0.75, 1.0])
            q = np.clip(np.searchsorted(edges, depth, side="right") - 1, 0, 3)
            for qi in [None, 0, 1, 2, 3]:
                m = ok & ((q == qi) if qi is not None else True)
                row = {"tour": tour, "stat": s, "quartile": "all" if qi is None else qi + 1, "targets": int(m.sum()),
                       "depth_median": float(np.median(depth[m]))}
                for w in worlds:
                    v52, td, K = vals[w]
                    mm = m & np.isfinite(v52) & np.isfinite(td)
                    row[f"rho2_{w}"] = float(np.corrcoef(v52[mm], td[mm])[0, 1] ** 2) if mm.sum() > 10 else np.nan
                    if qi is None:
                        row[f"K_{w}"] = K
                out.append(row)
    return pd.DataFrame(out)


def score_profile(score: pd.Series) -> pd.Series:
    return score.fillna("").str.replace(r"\(\d+\)", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()


def mass_lost(pop, imp_total_real) -> tuple[pd.DataFrame, dict]:
    """Importance mass of the matches held in a sequence source but not in the population, estimated by score profile."""
    m = pd.read_parquet(TC.S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "status", "format", "best_of", "score", "level"])
    sm = pd.read_parquet(TC.OUT / "seq_matches.parquet", columns=["match_id", "source", "a1"])
    held = sm[sm["match_id"].notna() & sm["a1"].notna()]
    src = held.groupby("match_id")["source"].agg(lambda s: "|".join(sorted(set(s))))
    u = m[m["match_id"].isin(src.index) & m["status"].eq("completed") & m["format"].eq("standard") & m["year"].le(2024)
          & ((m["tour"].eq("atp") & m["year"].ge(2013)) | (m["tour"].eq("wta") & m["year"].ge(2016)))].copy()
    u["sources"] = u["match_id"].map(src)
    u["kept"] = u["match_id"].isin(pop["match_id"])
    u["prof"] = score_profile(u["score"])
    u["n_sets"] = u["prof"].str.count("-")
    u["n_tb"] = u["score"].fillna("").str.count(r"7-6|6-7")
    kept_mass = pd.Series(imp_total_real, index=pop["match_id"].to_numpy())
    u["mass"] = u["match_id"].map(kept_mass)
    k = u[u["kept"]]
    by_prof = k.groupby(["tour", "best_of", "prof"])["mass"].mean()
    by_cell = k.groupby(["tour", "best_of", "n_sets", "n_tb"])["mass"].mean()
    lost = ~u["kept"]
    est = pd.Series(np.nan, index=u.index)
    key1 = pd.MultiIndex.from_frame(u.loc[lost, ["tour", "best_of", "prof"]])
    est[lost] = by_prof.reindex(key1).to_numpy()
    miss = lost & est.isna()
    key2 = pd.MultiIndex.from_frame(u.loc[miss, ["tour", "best_of", "n_sets", "n_tb"]])
    est[miss] = by_cell.reindex(key2).to_numpy()
    u["mass_est"] = np.where(u["kept"], u["mass"], est)
    rows = []
    for tour in ("atp", "wta"):
        for label, sel in (("all", u["tour"].eq(tour)),
                           ("with a tie-break set", u["tour"].eq(tour) & (u["n_tb"] > 0)),
                           ("no tie-break set", u["tour"].eq(tour) & (u["n_tb"] == 0)),
                           ("held by the WTA umpire log", u["tour"].eq(tour) & u["sources"].str.contains(r"(^|\|)wta($|\|)")),
                           ("WTA umpire log, with a tie-break set", u["tour"].eq(tour) & u["sources"].str.contains(r"(^|\|)wta($|\|)") & (u["n_tb"] > 0))):
            g = u[sel]
            if len(g) == 0:
                continue
            tot = g["mass_est"].sum()
            rows.append({"tour": tour, "subset": label, "matches_held": int(len(g)), "kept": int(g["kept"].sum()),
                         "lost": int((~g["kept"]).sum()), "lost_share": float((~g["kept"]).mean()),
                         "mass_lost_share_est": float(g.loc[~g["kept"], "mass_est"].sum() / tot) if tot > 0 else np.nan,
                         "lost_without_estimate": int((~g["kept"] & g["mass_est"].isna()).sum()),
                         "tb_share_of_kept": float((g.loc[g["kept"], "n_tb"] > 0).mean()) if g["kept"].any() else np.nan,
                         "tb_share_of_lost": float((g.loc[~g["kept"], "n_tb"] > 0).mean()) if (~g["kept"]).any() else np.nan})
    return pd.DataFrame(rows), {"universe": "Stage 0 completed standard-format matches in the window with a linked sequence (any source, any tier)"}


def main() -> int:
    t0 = time.time()
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if digest != HASH.read_text(encoding="utf-8").split()[0]:
        raise SystemExit("lev_prereg.md changed after its hash was recorded: refusing to run")
    info = {"prereg_sha256": digest, "deviations": []}
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    n = len(pop)
    rat = pd.read_parquet(TC.RATINGS, columns=["match_id", "p_serve_a", "p_serve_b"]).set_index("match_id")
    pre_a = rat["p_serve_a"].reindex(pop["match_id"]).to_numpy("float64")
    pre_b = rat["p_serve_b"].reindex(pop["match_id"]).to_numpy("float64")
    info["matches_without_p_serve"] = int((~np.isfinite(pre_a) | ~np.isfinite(pre_b)).sum())
    assert info["matches_without_p_serve"] == 0, info
    bo, fc, s0 = pop["bo"].to_numpy(), pop["final_code"].to_numpy(), pop["s0"].to_numpy()
    P = TC.real_points(pop)
    sinfo = LC.set_info(P, fc, bo)
    worlds = {}
    w_real = LC.importance(P, pre_a, pre_b, bo, fc)
    lev_real = LC.leverage(P, w_real, n)
    worlds["real"] = lev_real[["X_RL", "D_RL", "X_SL", "D_SL"]].to_numpy()
    TC.log(f"real: importance and leverage for {n:,} matches ({len(w_real):,} points)")
    diags = {}
    for j in range(3):
        levs = {}
        for X in (1, 2):
            Q, d = LC.shuffle_world(P, X, np.random.default_rng([20261006, 91, X, j]), sinfo)
            levs[X] = LC.leverage(Q, LC.importance(Q, pre_a, pre_b, bo, fc), n)
            diags[f"shuf_{j}_side{X}"] = d
            TC.log(f"shuf_{j} side {X}: {d}")
        worlds[f"shuf_{j}"] = combine(levs)
    # V1 replays (trait_build seeds) and one shuffle of each
    pm, _ = TC.point_stats(P, n, pop["late_set"].to_numpy())
    rr = TC.player_match_rates(pop, pm)
    pri = TC.fit_priors(rr)
    vi = list(TC.VARIANTS).index("V1")
    stored = pd.read_parquet(TC.OUT / "trait_player_matches.parquet", columns=["world", "mcode", "side", "svpt_won"])
    for r in range(3):
        rng = np.random.default_rng([TC.SEED, vi, r])
        true = TC.draw_rates(rr, pri, "V1", rng)
        Qr = TC.replay_points(true[:n], true[n:], bo, fc, s0, rng)
        chk = stored[stored["world"] == f"V1_{r}"].sort_values(["mcode", "side"])["svpt_won"].to_numpy()
        pmr, _ = TC.point_stats(Qr, n)
        assert np.array_equal(pmr.sort_values(["mcode", "side"])["svpt_won"].to_numpy(), chk), "replay not reproduced"
        worlds[f"rep_{r}"] = LC.leverage(Qr, LC.importance(Qr, pre_a, pre_b, bo, fc), n)[["X_RL", "D_RL", "X_SL", "D_SL"]].to_numpy()
        ir = LC.set_info(Qr, fc, bo)
        levs = {}
        for X in (1, 2):
            Q, d = LC.shuffle_world(Qr, X, np.random.default_rng([20261006, 92, X, r]), ir)
            levs[X] = LC.leverage(Q, LC.importance(Q, pre_a, pre_b, bo, fc), n)
            diags[f"repshuf_{r}_side{X}"] = d
        worlds[f"repshuf_{r}"] = combine(levs)
        TC.log(f"rep_{r} and its shuffle done")
    info["shuffle_diagnostics"] = diags
    # store
    frames = []
    for w, a in worlds.items():
        f = pd.DataFrame(a.astype("float32"), columns=["X_RL", "D_RL", "X_SL", "D_SL"])
        f.insert(0, "side", np.tile([1, 2], n).astype("int8"))
        f.insert(0, "mcode", np.repeat(np.arange(n), 2))
        f.insert(0, "world", w)
        frames.append(f)
    pd.concat(frames, ignore_index=True).to_parquet(TC.OUT / "lev_player_matches.parquet", index=False)
    # reliability
    _, rows, _, tot = TR.load()
    assert (rows["mcode"].to_numpy() == np.repeat(np.arange(n), 2)).all()
    wl = list(worlds)
    Xw, Dw = {}, {}
    for w in wl:
        Xw[w], Dw[w] = world_arrays(worlds[w])
    rng = np.random.default_rng(REL_SEED)
    iR = wl.index("real")
    iS = [wl.index(w) for w in SHUF]
    iP = [wl.index(w) for w in REP]
    iQ = [wl.index(w) for w in REPSHUF]
    rel_rows, store = [], {}
    for tour in ("atp", "wta"):
        tm = rows["tour"].to_numpy() == tour
        for label, hm in (("ge20", 20), ("ge50", 50)):
            res = TR.run_population(label, tour, tm, rows, {"X": Xw, "D": Dw}, wl, hm, rng)
            store[(tour, label)] = res
            dn, di, dv = delta(res, [iR], iS), delta(res, iP, iQ), delta(res, [iR], iP)
            for k, s in enumerate(STATS):
                rel_rows.append({"tour": tour, "population": label, "stat": s, "players": res["players"],
                                 "player_matches": res["player_matches"],
                                 "matches_per_player_median": res["matches_per_player_median"],
                                 "real_r": dn[k]["a_r"], "null_r": dn[k]["b_r"], "delta": dn[k]["delta"],
                                 "lo": dn[k]["lo"], "hi": dn[k]["hi"], "p": dn[k]["p"],
                                 "null_r_each": [float(res["rel"][i, k]) for i in iS],
                                 "iid_replay_r": di[k]["a_r"], "iid_shuffled_r": di[k]["b_r"], "delta_iid": di[k]["delta"],
                                 "delta_iid_lo": di[k]["lo"], "delta_iid_hi": di[k]["hi"],
                                 "delta_V1": dv[k]["delta"], "delta_V1_lo": dv[k]["lo"], "delta_V1_hi": dv[k]["hi"]})
            TC.log(f"{tour} {label}: {res['players']} players")
    rel = pd.DataFrame(rel_rows)
    rel.to_csv(TC.OUT / "lev_reliability.csv", index=False)
    # ability (real, >= 20 per half)
    abil = {}
    for tour in ("atp", "wta"):
        res = store[(tour, "ge20")]
        sub, pc, Pn = res["sub"], res["pcode"], res["players"]
        T = tot["real"][sub]
        hold = np.bincount(pc, weights=T[:, 1], minlength=Pn) / np.bincount(pc, weights=T[:, 0], minlength=Pn)
        brk = np.bincount(pc, weights=T[:, 3], minlength=Pn) / np.bincount(pc, weights=T[:, 2], minlength=Pn)
        for k, s in enumerate(STATS):
            v = np.bincount(pc, weights=Xw["real"][sub][:, k], minlength=Pn) / np.bincount(pc, weights=Dw["real"][sub][:, k], minlength=Pn)
            ok = np.isfinite(v)
            abil[(tour, s)] = {"r_hold": float(np.corrcoef(v[ok], hold[ok])[0, 1]),
                               "r_break": float(np.corrcoef(v[ok], brk[ok])[0, 1])}
    TC.log("ability done")
    rho = rho2(rows, Xw, Dw, ["real"] + SHUF + REP)
    rho.to_csv(TC.OUT / "lev_rho2.csv", index=False)
    TC.log("rho2 done")
    # population means
    means = []
    for tour in ("atp", "wta"):
        sub = np.flatnonzero(rows["tour"].to_numpy() == tour)
        pc, uq = pd.factorize(rows["player"].to_numpy()[sub])
        Pn = len(uq)
        Wb = np.stack([np.bincount(rng.integers(0, Pn, Pn), minlength=Pn) for _ in range(1000)]).astype(float)
        for k, s in enumerate(STATS):
            def pooled(ws):
                sx = [np.bincount(pc, weights=Xw[w][sub][:, k], minlength=Pn) for w in ws]
                sd = [np.bincount(pc, weights=Dw[w][sub][:, k], minlength=Pn) for w in ws]
                point = float(np.mean([a.sum() / b.sum() for a, b in zip(sx, sd)]))
                boot = np.mean([(Wb @ a) / (Wb @ b) for a, b in zip(sx, sd)], axis=0)
                return point, boot
            r_, rb = pooled(["real"])
            s_, sb_ = pooled(SHUF)
            p_, pb_ = pooled(REP)
            q_, qb_ = pooled(REPSHUF)
            means.append({"tour": tour, "stat": s, "real": r_, "shuffled": s_, "real_minus_shuffled": r_ - s_,
                          "lo": float(np.percentile(rb - sb_, 2.5)), "hi": float(np.percentile(rb - sb_, 97.5)),
                          "iid_replay": p_, "iid_shuffled": q_, "replay_minus_shuffled": p_ - q_,
                          "iid_lo": float(np.percentile(pb_ - qb_, 2.5)), "iid_hi": float(np.percentile(pb_ - qb_, 97.5)),
                          "real_minus_replay": r_ - p_})
    means = pd.DataFrame(means)
    # tests
    t = rel[rel["population"] == "ge20"].copy()
    t["p_holm"] = holm(t["p"].to_numpy())
    t["ability_r"] = [abil[(tr, s)]["r_break"] if s == "RL" else abil[(tr, s)]["r_hold"] for tr, s in zip(t["tour"], t["stat"])]
    t["r_hold"] = [abil[(tr, s)]["r_hold"] for tr, s in zip(t["tour"], t["stat"])]
    t["r_break"] = [abil[(tr, s)]["r_break"] for tr, s in zip(t["tour"], t["stat"])]
    ra = rho[rho["quartile"].astype(str) == "all"].set_index(["tour", "stat"])
    t["rho2_real"] = [ra.loc[(tr, s), "rho2_real"] for tr, s in zip(t["tour"], t["stat"])]
    t["rho2_null"] = [float(np.mean([ra.loc[(tr, s), f"rho2_{w}"] for w in SHUF])) for tr, s in zip(t["tour"], t["stat"])]
    t["rho2_V1"] = [float(np.mean([ra.loc[(tr, s), f"rho2_{w}"] for w in REP])) for tr, s in zip(t["tour"], t["stat"])]
    calib_excl = (t["delta_iid_lo"] > 0) | (t["delta_iid_hi"] < 0)
    t["calibration_flag"] = calib_excl
    t["pass"] = ((t["delta"] >= 0.10) & (t["delta"] > 0) & (t["p_holm"] < 0.05) & (t["ability_r"].abs() < 0.3)
                 & (t["rho2_real"] > t["rho2_null"]) & (~calib_excl | (t["delta"] - t["delta_iid"] >= 0.10)))
    t.to_csv(TC.OUT / "lev_tests.csv", index=False)
    mass, minfo = mass_lost(pop, lev_real.loc[lev_real["side"] == 1, "imp_total"].to_numpy())
    mass.to_csv(TC.OUT / "lev_mass.csv", index=False)
    kept_tb = lev_real[lev_real["side"] == 1]
    has_tb = kept_tb["imp_tb"].to_numpy() > 0
    tb_share = {}
    for tour in ("atp", "wta"):
        sel = (pop["tour"].to_numpy() == tour) & has_tb
        tb_share[tour] = float(kept_tb["imp_tb"].to_numpy()[sel].sum() / kept_tb["imp_total"].to_numpy()[sel].sum())
    info.update({"reliability": json.loads(rel.to_json(orient="records")), "tests": json.loads(t.to_json(orient="records")),
                 "means": json.loads(means.to_json(orient="records")), "rho2": json.loads(rho.to_json(orient="records")),
                 "mass_lost": json.loads(mass.to_json(orient="records")), "mass_info": minfo,
                 "tiebreak_points_share_of_mass_in_kept_tiebreak_matches": tb_share,
                 "ability": {f"{k[0]}|{k[1]}": v for k, v in abil.items()}, "seconds": round(time.time() - t0, 1)})
    (TC.OUT / "lev_results.json").write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote lev_* outputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
