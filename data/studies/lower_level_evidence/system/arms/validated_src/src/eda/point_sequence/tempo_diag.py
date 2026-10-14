"""POST-HOC diagnostics for the tempo gate (not pre-registered; recorded in tempo_results.json under "post_hoc").

Run after tempo_run.py: ./python.sh src/eda/point_sequence/tempo_diag.py

1. Convergence: the fixed-effects fit run to 4,000 iterations against tempo_run's 500 (adjusted gaps compared).
2. Is pressure pace tempo level in disguise? Player-level r of pressure pace with tempo level (all matches; and
   cross-half), and pressure pace on log gaps (a ratio: proportional slowing cancels).
3. Is it pressure, or position in the game? Placebo contrasts with the same machinery: game points for the server
   (40-0, 40-15, 40-30, advantage server) against the rest, and late points (5th point of the game or later) that are
   not pressure points against early points.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import tempo_run as TP  # noqa: E402
from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.point_sequence import trait_reliability as TR  # noqa: E402


def fe_exact(y: np.ndarray, factors: dict, player: np.ndarray) -> dict:
    """The same fixed-effects least squares solved exactly (sparse LSQR); non-player effects centred as fe_fit does."""
    from scipy.sparse import csr_matrix, hstack
    from scipy.sparse.linalg import lsqr
    n = len(y)
    blocks, sizes = [], []
    for v in [player] + list(factors.values()):
        k = int(v.max()) + 1
        blocks.append(csr_matrix((np.ones(n), (np.arange(n), v)), shape=(n, k)))
        sizes.append(k)
    A = hstack(blocks).tocsr()
    sol = lsqr(A, y, atol=1e-12, btol=1e-12, iter_lim=20000)
    beta = sol[0]
    cuts = np.cumsum([0] + sizes)
    pe = beta[cuts[0]:cuts[1]]
    eff = {}
    for i, (k, v) in enumerate(factors.items()):
        e = beta[cuts[i + 1]:cuts[i + 2]]
        cnt = np.bincount(v, minlength=len(e))
        c = float(np.average(e, weights=cnt))
        eff[k] = e - c
        pe = pe + c
    return {"effects": eff, "player": pe, "lsqr_iterations": int(sol[2]), "lsqr_stop": int(sol[1])}


def contrast(adj, pm, label, n_pm):
    """X/D of median(adj | label) - median(adj | not label) per player-match (as tempo_run.stats' pace)."""
    return TP.stats(adj, pm, label, n_pm)[:, 2:]


def main() -> int:
    import src.eda.point_sequence.tempo_run as T
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    tp = pop[pop["tour"].eq("wta") & pop["source"].eq("wta") & (pop["obs"] >= T.JUNE_2019) & pop["year"].le(2024)].copy()
    tp = tp.reset_index(drop=True)
    tp["tcode"] = np.arange(len(tp))
    s = pd.read_parquet(TC.OUT / "sequences.parquet",
                        columns=["match_id", "key", "usable", "seq", "game_idx", "pt_no", "is_tb", "server", "winner",
                                 "serve_no", "end", "t_utc"])
    s = s[s["usable"]]
    s["match_id"] = s["match_id"].astype(str)
    s = s[s["match_id"].isin(set(tp["match_id"]))]
    s["tcode"] = s["match_id"].map(pd.Series(tp["tcode"].to_numpy(), index=tp["match_id"].to_numpy()))
    s = s.sort_values(["tcode", "seq"], kind="mergesort").reset_index(drop=True)
    tp["key"] = s.groupby("tcode")["key"].first().reindex(tp["tcode"]).to_numpy()
    ev = pd.read_parquet(TC.OUT / "wta_events.parquet", columns=["key", "name", "reason", "next_point_seq"])
    ex = ev[ev["name"].isin(T.EXCLUDE_NAMES) | (ev["name"].eq("StateIndicator") & ev["reason"].isin(T.EXCLUDE_STATE_REASONS))]
    ex_pairs = set(zip(ex["key"], ex["next_point_seq"]))
    tp["umpire"] = tp["key"].map(T.umpires(set(tp["key"].dropna())))
    tc = s["tcode"].to_numpy()
    same = np.r_[False, (tc[1:] == tc[:-1]) & (s["game_idx"].to_numpy()[1:] == s["game_idx"].to_numpy()[:-1])]
    t = s["t_utc"].to_numpy("float64")
    gap = np.r_[np.nan, np.diff(t)]
    srv = s["server"].to_numpy()
    won = (s["winner"].to_numpy() == srv).astype(np.int64)
    gid = np.cumsum(~same) - 1
    cs = np.cumsum(won) - won
    sb = cs - cs[np.flatnonzero(~same)][gid]
    rb = (s["pt_no"].to_numpy().astype(np.int64) - 1) - sb
    deu = (sb >= 3) & (rb >= 3)
    state = np.where(deu, 17 + np.sign(sb - rb), np.minimum(sb, 3) * 4 + np.minimum(rb, 3))
    pressure = ((sb == 2) & (rb == 2)) | (deu & (sb <= rb)) | ((rb == 3) & (sb < 3))
    gamept = ((sb == 3) & (rb < 3)) | (deu & (sb > rb))
    late = (s["pt_no"].to_numpy() >= 5) & ~pressure
    end = s["end"].to_numpy()
    prev_type = np.where(np.r_[0, end[:-1]] == T.ACE, 1, np.where(np.r_[0, end[:-1]] == T.DF, 2, 0))
    sn = s["serve_no"].to_numpy()
    cur_type = np.where(end == T.ACE, 0, np.where(end == T.DF, 1, np.where(sn == 1, 2, np.where(sn == 2, 3, 4))))
    interrupted = np.fromiter(((k, q) in ex_pairs for k, q in zip(s["key"].to_numpy(), s["seq"].to_numpy())), bool, len(s))
    elig = same & ~s["is_tb"].to_numpy().astype(bool) & np.isfinite(gap) & (gap >= 5) & (gap <= 120) & ~interrupted
    e = np.flatnonzero(elig)
    side = srv[e].astype(np.int64)
    mc = tc[e]
    player = np.where(side == 1, tp["player_a_id"].to_numpy()[mc], tp["player_b_id"].to_numpy()[mc])
    pcode, _ = pd.factorize(pd.Series(player))
    ucode, _ = pd.factorize(tp["umpire"].fillna("unknown").to_numpy()[mc])
    eycode, _ = pd.factorize(pd.Series(tp["tournament_id"].to_numpy()[mc]).astype(str) + "|" + pd.Series(tp["year"].to_numpy()[mc]).astype(str))
    fac = {"umpire": ucode, "event_year": eycode, "state": state[e], "prev": prev_type[e], "cur": cur_type[e]}
    y = gap[e]
    f500 = T.fe_fit(y, fac, pcode, iters=500)
    fx = fe_exact(y, fac, pcode)
    adj500 = y - sum(f500["effects"][k][v] for k, v in fac.items())
    adj = y - sum(fx["effects"][k][v] for k, v in fac.items())
    ly = np.log(y)
    flog = fe_exact(ly, fac, pcode)
    ladj = ly - sum(flog["effects"][k][v] for k, v in fac.items())
    pm = mc * 2 + (side - 1)
    n_pm = 2 * len(tp)
    out = {"note": "post-hoc diagnostics, not pre-registered",
           "convergence": {"exact_lsqr_iterations": fx["lsqr_iterations"], "exact_lsqr_stop": fx["lsqr_stop"],
                           "max_abs_diff_adjusted_gap_500_vs_exact_s": float(np.max(np.abs(adj500 - adj))),
                           "p99_abs_diff_s": float(np.percentile(np.abs(adj500 - adj), 99)),
                           "median_abs_diff_s": float(np.median(np.abs(adj500 - adj)))}}
    # the pre-registered statistics recomputed on the exact fit, against tempo_run's (500 iterations)
    ex_stats = TP.stats(adj, pm, pressure[e], n_pm)
    ps_stats = TP.stats(adj500, pm, pressure[e], n_pm)
    okp = (ex_stats[:, 3] > 0) & (ps_stats[:, 3] > 0)
    okt = (ex_stats[:, 1] > 0) & (ps_stats[:, 1] > 0)
    out["convergence"]["pace_per_match_max_abs_diff_s"] = float(np.max(np.abs(ex_stats[okp, 2] / ex_stats[okp, 3] - ps_stats[okp, 2] / ps_stats[okp, 3])))
    out["convergence"]["tempo_per_match_max_abs_diff_s"] = float(np.max(np.abs(ex_stats[okt, 0] / ex_stats[okt, 1] - ps_stats[okt, 0] / ps_stats[okt, 1])))
    # worlds: tempo, pressure pace (seconds), pressure pace (log), game-point contrast, late-not-pressure contrast
    base = TP.stats(adj, pm, pressure[e], n_pm)
    fs = np.isin(cur_type[e], [0, 2])                       # first-serve points only (ace or first serve in play)
    fsx = np.flatnonzero(fs)
    first_only = np.zeros((n_pm, 2))
    first_only[:] = TP.stats(adj[fsx], pm[fsx], pressure[e][fsx], n_pm)[:, 2:]
    stat_cols = {"tempo": base[:, :2], "pace_s": base[:, 2:], "pace_log": TP.stats(ladj, pm, pressure[e], n_pm)[:, 2:],
                 "gamepoint_s": contrast(adj, pm, gamept[e], n_pm), "late_nonpressure_s": contrast(adj, pm, late[e], n_pm),
                 "pace_first_serve_only_s": first_only}
    names = list(stat_cols)
    Xr = np.column_stack([stat_cols[k][:, 0] for k in names])
    Dr = np.column_stack([stat_cols[k][:, 1] for k in names])
    worlds_X, worlds_D = {"real": Xr}, {"real": Dr}
    order0 = np.argsort(pm, kind="stable")
    for j in range(TP.SHUFFLES):
        r = np.random.default_rng([20261006, 94, j])
        o = np.lexsort((r.random(len(pm)), pm))
        cols_x, cols_d = [Xr[:, 0]], [Dr[:, 0]]
        for k, lab_all, vals in (("pace_s", pressure[e], adj), ("pace_log", pressure[e], ladj),
                                 ("gamepoint_s", gamept[e], adj), ("late_nonpressure_s", late[e], adj)):
            lab = np.empty(len(pm), bool)
            lab[order0] = lab_all[o]
            st = TP.stats(vals, pm, lab, n_pm)
            cols_x.append(st[:, 2])
            cols_d.append(st[:, 3])
        o2 = np.lexsort((r.random(fsx.size), pm[fsx]))
        ord_f = np.argsort(pm[fsx], kind="stable")
        lab_f = np.empty(fsx.size, bool)
        lab_f[ord_f] = pressure[e][fsx][o2]
        st = TP.stats(adj[fsx], pm[fsx], lab_f, n_pm)
        cols_x.append(st[:, 2])
        cols_d.append(st[:, 3])
        worlds_X[f"shuf_{j}"] = np.column_stack(cols_x)
        worlds_D[f"shuf_{j}"] = np.column_stack(cols_d)
    rows = pd.DataFrame({"mcode": np.repeat(tp["tcode"].to_numpy(), 2), "side": np.tile([1, 2], len(tp))})
    mcx = rows["mcode"].to_numpy()
    rows["player"] = np.where(rows["side"] == 1, tp["player_a_id"].to_numpy()[mcx], tp["player_b_id"].to_numpy()[mcx])
    for c in ("tour", "year", "obs", "round_order", "source", "strict", "match_id", "bo", "surface"):
        rows[c] = tp[c].to_numpy()[mcx]
    wl = list(worlds_X)
    res = TR.run_population("ge20", "wta", np.ones(len(rows), bool), rows, {"X": worlds_X, "D": worlds_D}, wl, 20,
                            np.random.default_rng(20261011))
    rel = {}
    for k, nm in enumerate(names):
        d = res["rel"][0, k] - res["rel"][1:, k].mean()
        bd = res["boot"][:, 0, k] - res["boot"][:, 1:, k].mean(axis=1)
        bd = bd[np.isfinite(bd)]
        rel[nm] = {"real_r": float(res["rel"][0, k]), "null_r": float(res["rel"][1:, k].mean()), "delta": float(d),
                   "lo": float(np.percentile(bd, 2.5)), "hi": float(np.percentile(bd, 97.5))}
    out["reliability_ge20"] = rel
    # player-level correlation of pressure pace with tempo level (all matches; cross-half)
    sub, pc, Pn = res["sub"], res["pcode"], res["players"]
    def plev(col):
        return np.bincount(pc, weights=Xr[sub][:, col], minlength=Pn) / np.bincount(pc, weights=Dr[sub][:, col], minlength=Pn)
    tempo_p, pace_p, pacel_p = plev(0), plev(1), plev(2)
    ok = np.isfinite(tempo_p) & np.isfinite(pace_p) & np.isfinite(pacel_p)
    cross = []
    for s_i in range(TR.SPLITS):
        h = res["halves"][s_i]
        idx = pc * 2 + h
        tx = np.bincount(idx, weights=Xr[sub][:, 0], minlength=2 * Pn).reshape(Pn, 2)
        td = np.bincount(idx, weights=Dr[sub][:, 0], minlength=2 * Pn).reshape(Pn, 2)
        px = np.bincount(idx, weights=Xr[sub][:, 1], minlength=2 * Pn).reshape(Pn, 2)
        pd_ = np.bincount(idx, weights=Dr[sub][:, 1], minlength=2 * Pn).reshape(Pn, 2)
        v = (td > 0).all(1) & (pd_ > 0).all(1)
        cross.append(np.corrcoef(px[v, 0] / pd_[v, 0], tx[v, 1] / td[v, 1])[0, 1])
    out["pace_vs_tempo"] = {"r_player_level": float(np.corrcoef(pace_p[ok], tempo_p[ok])[0, 1]),
                            "r_player_level_log_pace": float(np.corrcoef(pacel_p[ok], tempo_p[ok])[0, 1]),
                            "r_cross_half": float(np.mean(cross)), "players": int(ok.sum()),
                            "pace_sd_s": float(np.std(pace_p[ok])), "tempo_sd_s": float(np.std(tempo_p[ok]))}
    path = TC.OUT / "tempo_results.json"
    info = json.loads(path.read_text(encoding="utf-8"))
    info["post_hoc"] = out
    info["deviations"].append("Post-hoc diagnostics added after the pre-registered results were seen (tempo_diag.py): "
                              "fixed-effects convergence, pressure pace against tempo level, log-gap pace, placebo "
                              "contrasts. They change no pre-registered number.")
    path.write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
