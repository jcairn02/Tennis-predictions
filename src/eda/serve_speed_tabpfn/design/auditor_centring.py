"""Design R2 (auditor): does centring on as-of edition offsets beat the modeller's frozen system offsets, judged on
targets that do NOT reward carrying an edition's artefact forward? Result-free: no match result is read anywhere.

Looks (logged in 2_audit.md):
  * statistic targets, seasons <= 2023 only: the target match's own first-serve speeds (T1) and, for the gate, the
    player's aces per serve point, first-serve points won per first serve in and serve points won per serve point in
    the target match (one player's own rate; never an A - B difference of serve points won);
  * 2024-2026: feature values only (A - B distributions, correlations, shares that move), no outcome of any kind.

Part 0  my vectorised filter (auditor_lib.kalman_batch) reproduces the modeller's f_hat (modeller_state.kalman) on his own
        panel, offsets and constants, 2023 targets, full history, projected to obs.
Part 1  T1, the within-match speed difference. For a match where both players are timed, T = y_A - y_B (the target
        edition's offset cancels exactly: both serve in the same match). Forecast = (L_hat_A + f_hat_A) - (L_hat_B +
        f_hat_B) from each player's own earlier rows (364 days before es), under three centrings of the history:
            raw     no offsets
            frozen  the modeller's within-player system offsets, fitted on <= 2022 (men) / <= 2019 (women)
            asof    the engineer's edition offsets refitted at the target's es on released rows (lf + 1 <= es)
        Constants: the modeller's (h 14 d, s2f 12, q 4/yr, c 2, nu 7/8), and (h, s2f) re-tuned per centring on the
        tuning seasons (men 2019-2022, women Slams 2016-2020) by T1's MSE; evaluated on men 2023, women 2021-2023.
        Also: the registered window (c52 + b x), the change part MSE(dL) - MSE(dL + df), situations, calibration.
Part 2  the mechanism gate with and without target-edition fixed effects (men 2022-2023, women Slams 2016-2023), the
        modeller's controls (modeller_gate.own_rates), f_hat under frozen and as-of centring.
Part 3  2022-2026 frame matches (values only): A - B of f_hat under frozen (<= 2023) and as-of centring: SDs,
        correlations, the share that moves by more than one SD, and two named artefacts (Slam qualifiers at main-draw
        round 1; tour events in the 21 days after a Slam with a measuring break).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_centring.py
Writes data/studies/serve_speed_tabpfn/design/auditor_centring.json (+ .log)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

OUT = AL.OUT / "auditor_centring.json"
T0 = time.time()
GRID_HL = (7.0, 10.0, 14.0, 21.0, 28.0, 42.0)
GRID_S2F = (4.0, 6.0, 8.0, 12.0, 18.0)
RNG = np.random.default_rng(20261007)
SPLIT = {"atp": ((2019, 2022), (2023, 2023)), "wta": ((2016, 2020), (2021, 2023))}
FROZEN_LAST = {"atp": 2022, "wta": 2019}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 5)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def block_boot(values: dict, blocks: np.ndarray, reps: int = 2000) -> dict:
    """Means and 95% block-bootstrap intervals of per-row quantities (each a 1-D array over the same rows)."""
    ub = np.unique(blocks)
    ix = [np.flatnonzero(blocks == u) for u in ub]
    out = {k: {"est": float(np.mean(v))} for k, v in values.items()}
    draws = {k: [] for k in values}
    for _ in range(reps):
        s = np.concatenate([ix[j] for j in RNG.integers(0, len(ub), len(ub))])
        for k, v in values.items():
            draws[k].append(np.mean(v[s]))
    for k in values:
        out[k]["lo"], out[k]["hi"] = float(np.percentile(draws[k], 2.5)), float(np.percentile(draws[k], 97.5))
    return out


# ------------------------------------------------------------------------------------------------ Part 0
def part0() -> dict:
    from src.eda.serve_speed_tabpfn.design import modeller_common as M
    from src.eda.serve_speed_tabpfn.design import modeller_state as MS
    rows = pd.read_parquet(AL.OUT / "modeller_state_rows_ks_first_atp.parquet",
                           columns=["tour", "player_id", "tdate", "tournament_id", "round_order", "obs", "year",
                                    "f_hat", "L_hat"])
    rows = rows[rows["year"] == 2023].reset_index(drop=True)
    p0 = M.panel("ks_first")
    p0 = p0[(p0["tour"] == "atp") & (p0["year"] <= 2023)].copy()
    off = MS.offsets(p0, 2022)
    st = json.loads((AL.OUT / "modeller_state_ks_first.json").read_text(encoding="utf-8"))["tours"]["atp"]
    prm = dict(st["kalman_tuned"]["params"])
    nu = st["kalman_tuned"]["nu"]
    p = MS.centre(p0, off, nu).sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"],
                                             kind="mergesort").reset_index(drop=True)
    tg = rows.assign(es=rows["obs"])
    h = AL.histories(p, tg, window=1e9)
    idx = h["idx"]
    ok = idx >= 0
    Z = np.where(ok, p["z"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    R = np.where(ok, p["R"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    D = np.where(ok, p["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    kf = AL.kalman_batch(Z, R, D, tg["obs"].to_numpy(float), prm | {"nu_pm": nu["pm"], "nu_ks": nu["ks"]})
    d = np.abs(kf["f_hat"] - rows["f_hat"].to_numpy(float))
    return {"targets": int(len(rows)), "max_abs_diff_f_hat": float(np.nanmax(d)),
            "share_within_1e-6": float(np.mean(d < 1e-6))}


# ------------------------------------------------------------------------------------------------ Part 1
def t1_pairs(tg: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Row positions (iA, iB) of the matches where both sides are targets."""
    a = tg.reset_index(drop=True)
    pos = pd.Series(np.arange(len(a)), index=pd.MultiIndex.from_arrays([a["match_id"], a["side"]]))
    mids = a.loc[a["side"].eq("A"), "match_id"]
    has_b = pd.MultiIndex.from_arrays([mids, np.full(len(mids), "B")]).isin(pos.index)
    mids = mids[has_b].to_numpy()
    iA = pos.reindex(pd.MultiIndex.from_arrays([mids, np.full(len(mids), "A")])).to_numpy()
    iB = pos.reindex(pd.MultiIndex.from_arrays([mids, np.full(len(mids), "B")])).to_numpy()
    return iA.astype(int), iB.astype(int)


def part1(p: pd.DataFrame, tour: str, snaps: dict) -> tuple[dict, dict]:
    (t_lo, t_hi), (e_lo, e_hi) = SPLIT[tour]
    pt = p[p["tour"] == tour].copy()
    tg = pt[pt["year"].between(t_lo, e_hi)].reset_index(drop=True)
    h = AL.histories(p, tg)
    tday = tg["es"].to_numpy(float)
    frozen = AL.frozen_offsets(p[p["tour"] == tour], FROZEN_LAST[tour])
    Zs = {"raw": AL.centred_values(p, tg, h, "raw"),
          "frozen": AL.centred_values(p, tg, h, "frozen", frozen=frozen),
          "asof": AL.centred_values(p, tg, h, "asof", snaps=snaps)}
    D = AL.days_matrix(p, h)
    base = AL.MEN if tour == "atp" else AL.WOMEN_MENDYN
    R = AL.noise(p, h, base)
    iA, iB = t1_pairs(tg)
    y = tg["y"].to_numpy(float)
    T = y[iA] - y[iB]
    year = tg["year"].to_numpy()[iA]
    has = np.isfinite(Zs["raw"][iA]).any(1) & np.isfinite(Zs["raw"][iB]).any(1)
    tune = has & (year >= t_lo) & (year <= t_hi)
    ev = has & (year >= e_lo) & (year <= e_hi)
    blk = (tday[iA] // 28).astype(int)
    k14 = h["k14"]
    same = h["same_event"]
    res = {"tour": tour, "matches_tune": int(tune.sum()), "matches_eval": int(ev.sum()),
           "frozen_offsets": {k: v for k, v in frozen[tour].items() if not k.startswith("_")}, "schemes": {}}
    feats = {}
    for name, Z in Zs.items():
        grid = {}
        for hl in GRID_HL:
            for s2f in GRID_S2F:
                prm = dict(base, hl=hl, s2f=s2f)
                kf = AL.kalman_batch(Z, R, D, tday, prm)
                F = (kf["L_hat"][iA] + kf["f_hat"][iA]) - (kf["L_hat"][iB] + kf["f_hat"][iB])
                grid[(hl, s2f)] = (float(np.mean((T[tune] - F[tune]) ** 2)), float(np.mean((T[ev] - F[ev]) ** 2)))
        best = min(grid, key=lambda k: grid[k][0])
        out = {"best_hl_s2f": list(best), "mse_tune_best": grid[best][0], "mse_eval_best": grid[best][1],
               "mse_eval_modeller_constants": grid[(base["hl"], base["s2f"])][1],
               "mse_tune_modeller_constants": grid[(base["hl"], base["s2f"])][0],
               "grid_eval": {f"{k[0]:g}|{k[1]:g}": v[1] for k, v in grid.items()},
               "grid_tune": {f"{k[0]:g}|{k[1]:g}": v[0] for k, v in grid.items()},
               "best_on_grid_edge": bool(best[0] in (GRID_HL[0], GRID_HL[-1]) or best[1] in (GRID_S2F[0], GRID_S2F[-1]))}
        for label, prm in (("tuned", dict(base, hl=best[0], s2f=best[1])), ("modeller", dict(base))):
            kf = AL.kalman_batch(Z, R, D, tday, prm)
            wm = AL.window_means(Z, h, p, tday)
            dL = kf["L_hat"][iA] - kf["L_hat"][iB]
            df = kf["f_hat"][iA] - kf["f_hat"][iB]
            dc = wm["c52"][iA] - wm["c52"][iB]
            xa, xb = np.nan_to_num(wm["x"][iA]), np.nan_to_num(wm["x"][iB])
            dx = xa - xb
            bx = float(np.dot(dx[tune], (T - dc)[tune]) / np.dot(dx[tune], dx[tune]))
            feats[(name, label)] = {"dL": dL, "df": df, "dc": dc, "dx": dx, "bx": bx,
                                    "fA": kf["f_hat"][iA], "fB": kf["f_hat"][iB]}
            e = ev
            r = {"mse_L_plus_f": float(np.mean((T[e] - dL[e] - df[e]) ** 2)),
                 "mse_L_only": float(np.mean((T[e] - dL[e]) ** 2)),
                 "mse_c52_plus_bx": float(np.mean((T[e] - dc[e] - bx * dx[e]) ** 2)),
                 "mse_c52_only": float(np.mean((T[e] - dc[e]) ** 2)), "b_x_tune": bx,
                 "sd_df_eval": float(np.std(df[e])),
                 "corr_df_with_T_minus_dL": float(np.corrcoef(df[e], (T - dL)[e])[0, 1]),
                 "calib_slope_T_minus_dL_on_df": {}}
            for lab, m in (("both_k14_ge1", (k14[iA] >= 1) & (k14[iB] >= 1)),
                           ("one_k14_0", ((k14[iA] >= 1) ^ (k14[iB] >= 1))),
                           ("both_k14_0", (k14[iA] == 0) & (k14[iB] == 0))):
                mm = e & m
                if mm.sum() > 30 and np.dot(df[mm], df[mm]) > 0:
                    r["calib_slope_T_minus_dL_on_df"][lab] = {
                        "rows": int(mm.sum()), "slope": float(np.dot(df[mm], (T - dL)[mm]) / np.dot(df[mm], df[mm])),
                        "sd_df": float(np.std(df[mm]))}
            out[label] = r
        res["schemes"][name] = out
        log(f"{tour} {name}: best (hl, s2f) {best} tune {grid[best][0]:.3f} eval {grid[best][1]:.3f}; modeller "
            f"constants eval {out['mse_eval_modeller_constants']:.3f}; L+f {out['modeller']['mse_L_plus_f']:.3f} "
            f"L {out['modeller']['mse_L_only']:.3f}")
    # paired comparisons on the evaluation matches (positive = the second named scheme better, i.e. lower MSE)
    e = ev
    cmp = {}
    for label in ("modeller", "tuned"):
        sq = {}
        for name in Zs:
            ft = feats[(name, label)]
            sq[name] = (T - ft["dL"] - ft["df"]) ** 2
            sq[name + "_Lonly"] = (T - ft["dL"]) ** 2
            sq[name + "_win"] = (T - ft["dc"] - ft["bx"] * ft["dx"]) ** 2
        vals = {"frozen_minus_asof": (sq["frozen"] - sq["asof"])[e], "raw_minus_asof": (sq["raw"] - sq["asof"])[e],
                "raw_minus_frozen": (sq["raw"] - sq["frozen"])[e],
                "change_gain_frozen": (sq["frozen_Lonly"] - sq["frozen"])[e],
                "change_gain_asof": (sq["asof_Lonly"] - sq["asof"])[e],
                "window_frozen_minus_kalman_frozen": (sq["frozen_win"] - sq["frozen"])[e],
                "window_asof_minus_kalman_asof": (sq["asof_win"] - sq["asof"])[e],
                "window_raw_minus_kalman_asof": (sq["raw_win"] - sq["asof"])[e]}
        cmp[label] = block_boot(vals, blk[e])
        # situations: both players' recent history includes the target event, neither, or one
        sit = {}
        sA, sB = same[iA], same[iB]
        for lab, m in (("both_same_event", sA & sB), ("neither_same_event", ~sA & ~sB), ("one_same_event", sA ^ sB)):
            mm = e & m
            if mm.sum() >= 40:
                sit[lab] = {"matches": int(mm.sum()),
                            **block_boot({"frozen_minus_asof": (sq["frozen"] - sq["asof"])[mm],
                                          "change_gain_frozen": (sq["frozen_Lonly"] - sq["frozen"])[mm],
                                          "change_gain_asof": (sq["asof_Lonly"] - sq["asof"])[mm]}, blk[mm], 1000)}
        cmp[label]["situations"] = sit
    res["paired_eval"] = cmp
    res["key"] = ("MSE in km/h^2 of the within-match A - B first-serve speed; 'x_minus_y' = MSE(x) - MSE(y): "
                  "positive = y better (lower MSE); change_gain_* = MSE(level only) - MSE(level + f_hat): positive = "
                  "f_hat helps; intervals: 95% four-week-block bootstrap; a tie when the interval spans 0")
    log(f"{tour} paired (modeller constants): " + json.dumps(jsonable({k: v for k, v in cmp['modeller'].items()
                                                                        if k != 'situations'})))
    # the constants each scheme would use downstream (Part 3)
    best_by = {n: res["schemes"][n]["best_hl_s2f"] for n in Zs}
    return res, best_by


# ------------------------------------------------------------------------------------------------ Part 2
def wls_fe(y, X, w, groups, clusters, fe: bool):
    y, X, w = np.asarray(y, float), np.asarray(X, float), np.asarray(w, float)
    if fe:
        g = pd.factorize(groups)[0]
        sw = np.bincount(g, weights=w)
        y = y - (np.bincount(g, weights=w * y) / sw)[g]
        X = X - np.column_stack([(np.bincount(g, weights=w * X[:, j]) / sw)[g] for j in range(X.shape[1])])
    XtW = X.T * w
    A = XtW @ X
    beta = np.linalg.solve(A, XtW @ y)
    e = y - X @ beta
    c = pd.factorize(clusters)[0]
    G = c.max() + 1
    S = np.zeros((G, X.shape[1]))
    np.add.at(S, c, (w * e)[:, None] * X)
    Ai = np.linalg.inv(A)
    V = Ai @ (S.T @ S) @ Ai * G / (G - 1)
    return beta, np.sqrt(np.diag(V))


def part2(p: pd.DataFrame, tour: str, snaps: dict, prm_by: dict) -> dict:
    from src.eda.serve_speed_tabpfn.design import modeller_gate as MG
    years, levels = ((2022, 2023), ("GS", "T1000", "T500", "T250", "FIN", "CH")) if tour == "atp" else \
        ((2016, 2023), ("GS",))
    b = MG.box_history((2013, 2023), tour)
    tg = b[b["year"].between(*years) & b["level"].isin(levels)].reset_index(drop=True)
    for s, (n, d) in MG.STATS.items():
        tg = tg[tg[d] > 0]
    tg = tg.reset_index(drop=True)
    tg["tour"] = tour
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es"])
    tg = tg.merge(tm, on="match_id", how="left")
    tg = tg[tg["es"].notna()].reset_index(drop=True)
    h = AL.histories(p, tg)
    tday = tg["es"].to_numpy(float)
    frozen = AL.frozen_offsets(p[p["tour"] == tour], FROZEN_LAST[tour])
    D = AL.days_matrix(p, h)
    base = AL.MEN if tour == "atp" else AL.WOMEN_MENDYN
    R = AL.noise(p, h, base)
    fh = {}
    for name in ("frozen", "asof"):
        Z = AL.centred_values(p, tg, h, name, frozen=frozen, snaps=snaps)
        for label, prm in (("modeller", dict(base)), ("tuned", dict(base, hl=prm_by[name][0], s2f=prm_by[name][1]))):
            kf = AL.kalman_batch(Z, R, D, tday, prm)
            fh[(name, label)] = (kf["f_hat"], kf["L_hat"])
    orates = MG.own_rates(b, tg)
    tg = tg.join(orates)
    opp_cols = [c for c in tg.columns if c.startswith("c52_")]
    oppv = tg[["match_id", "player_id"] + opp_cols].rename(columns={"player_id": "opponent_id"})
    tg = tg.merge(oppv, on=["match_id", "opponent_id"], how="left", suffixes=("", "_opp"))
    tg["block"] = (tg["obs"] // 28).astype(int)
    tg["edition"] = tg["tournament_id"].astype(str) + "|" + tg["qualifying"].astype(str)
    out = {"tour": tour, "years": list(years), "targets": int(len(tg)), "results": {}}
    for s, (n, d) in MG.STATS.items():
        yv = (tg[n] / tg[d]).to_numpy(float)
        r52 = (tg[f"s52_{n}"] / tg[f"s52_{d}"]).to_numpy(float)
        rew = (tg[f"ew_{n}"] / tg[f"ew_{d}"]).to_numpy(float)
        oc = (tg[f"c52_{n}_opp"] / tg[f"c52_{d}_opp"]).to_numpy(float)
        w = tg[d].to_numpy(float)
        for (name, label), (f_hat, L_hat) in fh.items():
            base_ok = np.isfinite(r52) & np.isfinite(rew) & np.isfinite(oc) & np.isfinite(L_hat) & np.isfinite(yv)
            recent = np.isfinite(h["last_age"]) & (h["last_age"] <= 28)
            for subset, m in (("all", base_ok), ("timed_within_28d", base_ok & recent),
                              ("within_28d_earlier_events_only", base_ok & recent & ~h["same_event"])):
                g = np.flatnonzero(m)
                if len(g) < 200:
                    continue
                F = f_hat[g] / f_hat[g].std()
                surf = pd.get_dummies(tg.loc[g, "surface"].fillna("Hard"), drop_first=True).to_numpy(float)
                lev = pd.get_dummies(tg.loc[g, "level"], drop_first=True).to_numpy(float)
                ctrl_nofe = np.column_stack([np.ones(len(g)), r52[g], rew[g], oc[g], L_hat[g], surf, lev])
                ctrl_fe = np.column_stack([r52[g], rew[g], oc[g], L_hat[g]])
                key = f"{s}|{subset}|{name}|{label}"
                row = {"rows": int(len(g))}
                for fe, ctrl in ((False, ctrl_nofe), (True, ctrl_fe)):
                    beta, se = wls_fe(yv[g], np.column_stack([F, ctrl]), w[g], tg.loc[g, "edition"].to_numpy(),
                                      tg.loc[g, "block"].to_numpy(), fe)
                    row["edition_fe" if fe else "no_fe"] = {"pp_per_sd": 100 * beta[0],
                                                            "lo": 100 * (beta[0] - 1.96 * se[0]),
                                                            "hi": 100 * (beta[0] + 1.96 * se[0])}
                out["results"][key] = row
        log(f"{tour} gate {s}: " + "; ".join(
            f"{k.split('|', 1)[1]} noFE {v['no_fe']['pp_per_sd']:+.2f} FE {v['edition_fe']['pp_per_sd']:+.2f} "
            f"[{v['edition_fe']['lo']:+.2f}, {v['edition_fe']['hi']:+.2f}]"
            for k, v in out["results"].items() if k.startswith(s + "|") and "|modeller" in k))
    out["key"] = ("percentage points of the rate per SD of f_hat, beyond the player's 364-day and two-week box-score "
                  "rate, his level L_hat and the opponent's conceded rate (no_fe: + surface and level dummies; "
                  "edition_fe: + target-edition fixed effects); positive = speed above his norm serves better; "
                  "95% intervals clustered by 28-day blocks")
    return out


# ------------------------------------------------------------------------------------------------ Part 3
def frame_targets() -> pd.DataFrame:
    fr = pd.read_parquet(EC.MODEL_FRAME, columns=["match_id", "tour", "season"])
    pre = EC.stage0(EC.S0_PRE, cols=["match_id", "player_a_id", "player_b_id", "tournament_id", "tournament_date",
                                     "round_order", "round", "level", "qualifying", "tournament_name"])
    f = fr.merge(pre, on="match_id", how="left", validate="one_to_one")
    remap = EC.id_map()
    f["nid"] = f["match_id"].map(lambda x: remap.get(x, x))
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es"]).rename(columns={"match_id": "nid"})
    f = f.merge(tm, on="nid", how="left")
    f["tdate"] = f["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    sides = pd.concat([f.assign(side="A", player_id=f["player_a_id"]), f.assign(side="B", player_id=f["player_b_id"])],
                      ignore_index=True)
    return sides[sides["es"].notna() & sides["player_id"].notna()].reset_index(drop=True)


def part3(p: pd.DataFrame, snaps: dict, best: dict) -> dict:
    tg = frame_targets()
    tg = tg[tg["season"] >= 2022].reset_index(drop=True)
    res = {}
    for tour in ("atp", "wta"):
        prm_by = best[tour]
        t = tg[tg["tour"] == tour].reset_index(drop=True)
        h = AL.histories(p, t)
        tday = t["es"].to_numpy(float)
        D = AL.days_matrix(p, h)
        base = AL.MEN if tour == "atp" else AL.WOMEN_MENDYN
        R = AL.noise(p, h, base)
        fz = AL.frozen_offsets(p[p["tour"] == tour], 2023)
        vals = {}
        for name in ("raw", "frozen", "asof"):
            Z = AL.centred_values(p, t, h, name, frozen=fz, snaps=snaps)
            vals[name] = AL.kalman_batch(Z, R, D, tday, dict(base))["f_hat"]
            if name in prm_by:
                vals[name + "_tuned"] = AL.kalman_batch(Z, R, D, tday, dict(base, hl=prm_by[name][0],
                                                                             s2f=prm_by[name][1]))["f_hat"]
        t = t.assign(**{f"f_{k}": v for k, v in vals.items()}, last_age=h["last_age"], k14=h["k14"])
        a = t[t["side"] == "A"].set_index("match_id")
        b = t[t["side"] == "B"].set_index("match_id")
        m = a[["season", "level", "round", "qualifying"]].copy()
        for k in vals:
            m[k] = a[f"f_{k}"] - b[f"f_{k}"]
        m["slam"] = m["level"].eq("GS")
        rows = []
        sd_ref = float(m.loc[m["season"].between(2022, 2023), "asof"].std())
        for (season, slam), g in m.groupby(["season", "slam"]):
            r = {"season": int(season), "slam": bool(slam), "matches": int(len(g)),
                 "sd_frozen": float(g["frozen"].std()), "sd_asof": float(g["asof"].std()),
                 "sd_raw": float(g["raw"].std()), "corr_frozen_asof": float(g[["frozen", "asof"]].corr().iloc[0, 1]),
                 "corr_raw_asof": float(g[["raw", "asof"]].corr().iloc[0, 1]),
                 "share_move_gt_1sd": float(((g["frozen"] - g["asof"]).abs() > sd_ref).mean()),
                 "share_move_gt_half_sd": float(((g["frozen"] - g["asof"]).abs() > 0.5 * sd_ref).mean()),
                 "share_nonzero_asof": float((g["asof"].abs() > 0.05).mean())}
            if "asof_tuned" in g:
                r["corr_asof_modeller_vs_tuned_constants"] = float(g[["asof", "asof_tuned"]].corr().iloc[0, 1])
            rows.append(r)
        res[tour] = {"sd_ref_asof_2022_23": sd_ref, "by_season_slam": rows}
        # artefact 1: main-draw round 1 at a Slam, a side whose latest history row is this Slam's qualifying
        sl = t[t["level"].eq("GS") & ~t["qualifying"].astype(bool) & t["round"].isin(["R128"])].copy()
        pq = p[["tour", "player_id", "tournament_id", "qualifying"]]
        qual_ids = set(map(tuple, pq[pq["qualifying"].astype(bool)][["tour", "player_id", "tournament_id"]]
                           .drop_duplicates().to_numpy()))
        sl["came_through_q"] = [(tr, pid, tid) in qual_ids for tr, pid, tid in
                                zip(sl["tour"], sl["player_id"], sl["tournament_id"])]
        art1 = []
        for (season, cq), g in sl.groupby(["season", "came_through_q"]):
            art1.append({"season": int(season), "qualifier": bool(cq), "sides": int(len(g)),
                         "mean_f_frozen": float(g["f_frozen"].mean()), "mean_f_asof": float(g["f_asof"].mean()),
                         "mean_f_raw": float(g["f_raw"].mean())})
        res[tour]["slam_R1_qualifiers"] = art1
        # artefact 2: non-Slam targets within 21 days after the end of a Slam with a break; sides whose latest
        # history row is that Slam vs the rest
        art2 = []
        for slam_name, yr in (("W", 2025), ("USO", 2026), ("AO", 2024), ("USO", 2025), ("W", 2024)):
            ev = p[(p["tour"] == tour) & (p["slam"] == slam_name) & (p["year"] == yr)]
            if ev.empty:
                continue
            end = ev["lf"].max()
            tids = set(ev["tournament_id"])
            nt = t[(~t["level"].eq("GS")) & (t["es"] > end) & (t["es"] <= end + 21)].copy()
            if nt.empty:
                continue
            # the latest own history row's tournament for each side
            hh = AL.histories(p, nt.reset_index(drop=True))
            last = np.array([p["tournament_id"].to_numpy()[r[r >= 0][-1]] if (r >= 0).any() else None
                             for r in hh["idx"]], dtype=object)
            from_slam = np.array([x in tids for x in last])
            nt = nt.reset_index(drop=True)
            for flag in (True, False):
                g = nt[from_slam == flag]
                if len(g):
                    art2.append({"slam": f"{slam_name} {yr}", "latest_row_at_that_slam": bool(flag),
                                 "sides": int(len(g)), "mean_f_frozen": float(g["f_frozen"].mean()),
                                 "mean_f_asof": float(g["f_asof"].mean()), "mean_f_raw": float(g["f_raw"].mean())})
        res[tour]["after_slam_breaks"] = art2
        log(f"{tour} values: " + json.dumps(jsonable(rows))[:1500])
    return res


def main() -> None:
    res = {"reads_results": False}
    log("part 0: re-implementation check")
    res["part0_reimplementation"] = part0()
    log(json.dumps(res["part0_reimplementation"]))
    p = AL.panel("ks_first")
    log(f"panel ks_first: {len(p)} rows")
    res["panel_rows_by_tour_basis"] = {f"{k[0]}|{k[1]}": int(v) for k, v in p.groupby(["tour", "basis"]).size().items()}
    snaps = {t: AL.Snapshots(p[p["tour"] == t].reset_index(drop=True)) for t in ("atp", "wta")}
    # Snapshots index the tour's own rows; centred_values looks editions up by name, so build per-tour panels aligned
    # with the full panel's edition names (the per-tour objects only need the edition list and the fits)
    res["part1"], best = {}, {}
    for tour in ("atp", "wta"):
        log(f"part 1: T1 {tour}")
        r, b = part1(p, tour, {tour: snaps[tour]})
        res["part1"][tour], best[tour] = r, b
    res["part2"] = {}
    for tour in ("atp", "wta"):
        log(f"part 2: gate {tour}")
        res["part2"][tour] = part2(p, tour, {tour: snaps[tour]}, best[tour])
    log("part 3: values 2022-2026")
    res["part3"] = part3(p, snaps, best)
    OUT.write_text(json.dumps(jsonable(res), indent=1) + "\n", encoding="utf-8")
    log(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
