"""Scoring of the training-window study: each arm as its own two-stage forecast, against the current model's.

For each arm (common.ARMS) and test season Y in 2020-2024:
    eta      the log-odds of the mean over seeds 0-3 of the symmetrised forecasts
    stage 2  (s_atp, s_wta, b) fitted on the arm's own forecasts of 2019 .. Y - 1 (debut seasons out) with spd_L as the
             weekly feed has it, b shrunk (tau 0.05): q = expit(s_tour eta + b spd_L), spd_L = 0 for women. The decided
             rule (serve_speed_tabpfn/adaptive/adjust.py, mode L, weekly feed), with seeds 0-3 for every arm
    close    the closing price recalibrated the decided way: one slope per tour on its log-odds, 2019 .. Y - 1

Comparisons on the scored matches (2020-2024, debut seasons out), milli-log-loss per match:
    vs_exp     the arm's two-stage forecast against the current model's: positive = the arm better
    recency    lastN against randN, the same training size: positive = the recent rows better
    vs_close   a two-stage forecast against the recalibrated close: positive = the forecast better
    vs_pinnacle  the same against Pinnacle's margin-free price (recalibrated the same way on the earlier matches it
               prices), on the matches it prices: a sharper benchmark than the average close the model takes as input
    stage1     the arm's calibrated stage 1 against exp's (a reference only; decisions use both stages)
    stage1_vs_close, stage1_vs_pinnacle   the calibrated stage 1 against the prices: TabPFN's learned move without
               the speed term, which adds a disagreement of its own for men
    speed_adjustment   side check: exp's two-stage forecast against its calibrated stage 1, i.e. what the speed
               adjustment added walk-forward (men; positive = the adjustment helped)
Intervals: four-week blocks plus the seeds' variance (serve_speed_tabpfn.score.paired_stats); a 95% interval spanning 0
is a tie. Since 9 Oct 2026 the seed term between two forecasts is paired by seed (every arm uses seeds 0-3, random state
k), and against a price it is the arm's own; the unpaired intervals, as published, are kept as lo_unpaired / hi_unpaired.

Diagnostics: the realisation of each forecast's disagreement with the recalibrated close, c: logistic of the result on
c x (logit q - logit q_close) with logit q_close as an offset. 1 = every claimed point came true; below 1 = the forecast
moves too far from the close; above 1 = not far enough. SE over four-week blocks. Also the spread of the disagreement,
and, in-sample, what the disagreement is worth over the price at its best size (gain_at_best_size, mLL: the log loss
with c fitted on the same rows). Equal values mean the same information about the result beyond the price, whatever
the size of the moves.

Secondary, no refit (rebuild protocol Q29): exp's two-part recalibration, logit q = a_tour logit p_close +
c_tour (eta - logit p_close) + b spd_L, all five fitted jointly, b shrunk as in stage 2, on 2019 .. Y - 1 (2p_all) or on
the last two seasons only (2p_recent): the move away from the close re-sized on recent seasons without refitting TabPFN.

Checks before any score: every fit's td ids, training shape (recomputed from common.train_mask), season, seed and
settings; last7's and rand7's 2019-2020 fits (the same rows as exp) equal the stored exp fits within 1e-6; exp's
stage-2 coefficients for 2024 equal the published ones (adaptive/coefficients.json, L_weekly).

Writes data/studies/training_window/results.csv, season_params.csv and results.json.
Run: ./python.sh src/eda/training_window/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import score as SS  # noqa: E402  (paired_stats, seed_loss)
from src.eda.training_window import common as C  # noqa: E402

STAGE2_TOL = 1e-12
POPULATIONS = ("both", "atp", "wta")
PINNACLE = C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_baselines.parquet"


# ------------------------------------------------------------------------------------------------
# Forecasts, with the file checks

def load_arm(frame: pd.DataFrame, arm: str) -> dict[int, pd.DataFrame]:
    """Per fitted season: a matches x seeds table of symmetrised P(A wins), in frame order."""
    seasons = frame["season"].to_numpy()
    out = {}
    for s in C.SEASONS:
        ids = frame.loc[frame["season"] == s, "match_id"].to_numpy()
        cols = {}
        for k in C.SEEDS:
            path = C.fit_path(arm, s, k)
            p, meta = C.symmetrised(path, ids)
            stored_cols = meta.get("columns") or []
            n = int(C.train_mask(seasons, arm, s, k).sum())
            problems = [what for what, ok in (
                ("arm", meta.get("arm") == ("model" if arm == "exp" else arm)),
                ("season", meta.get("season") == s), ("seed", meta.get("seed") == k),
                ("config", meta.get("config") == {**C.CONFIG, "random_state": k}),
                ("columns", C.SC.race_names(stored_cols) == C.inputs()),
                ("train_shape", list(meta.get("train_shape", [])) == [n, len(C.inputs())])) if not ok]
            if problems:
                raise RuntimeError(f"{path.name}: {problems}")
            cols[k] = p
        out[s] = pd.DataFrame(cols, index=pd.Index(ids, dtype=str))
    return out


def reproduction() -> dict:
    """last7 and rand7 have exp's rows in 2019-2020: their raw td forecasts must equal the stored ones."""
    rows = []
    for arm in ("last7", "rand7"):
        for s in (2019, 2020):
            for k in C.SEEDS:
                a, ia, _ = C.read_fit(C.fit_path(arm, s, k))
                b, ib, _ = C.read_fit(C.stored_path(s, k))
                diff = float(np.abs(a - b).max()) if np.array_equal(ia, ib) else float("inf")
                rows.append({"arm": arm, "season": s, "seed": k, "max_abs_diff": diff, "passed": diff <= C.REPRO_TOL})
    return {"tolerance": C.REPRO_TOL, "passed": all(r["passed"] for r in rows), "rows": rows}


# ------------------------------------------------------------------------------------------------
# Fits on earlier seasons only

def history(info: pd.DataFrame, season: int, start: int = C.CALIB_FROM) -> np.ndarray:
    s = info["season"].to_numpy()
    m = (s >= start) & (s < season) & ~info["debut"].to_numpy(bool)
    if s[m].max() >= season:
        raise RuntimeError("a fit read a season >= Y")
    return m


def slope(x: np.ndarray, y: np.ndarray) -> float:
    beta, _ = C.fit_logistic(x[:, None], y)
    return float(beta[0])


def two_part_fit(lc, eta, atp, z, y) -> dict:
    d = eta - lc
    Z = np.column_stack([np.where(atp, lc, 0.0), np.where(atp, d, 0.0), np.where(~atp, lc, 0.0),
                         np.where(~atp, d, 0.0), z])
    beta, se = C.fit_logistic(Z, y)
    b, s = float(beta[4]), float(se[4])
    return {"a_atp": float(beta[0]), "c_atp": float(beta[1]), "a_wta": float(beta[2]), "c_wta": float(beta[3]),
            "b_mle": b, "se_b": s, "b_shrunk": b * C.TAU ** 2 / (C.TAU ** 2 + s ** 2), "rows": int(len(y))}


def two_part_apply(lc, eta, atp, z, par: dict) -> np.ndarray:
    a = np.where(atp, par["a_atp"], par["a_wta"])
    c = np.where(atp, par["c_atp"], par["c_wta"])
    if np.ndim(eta) == 2:
        return expit((a * lc)[:, None] + c[:, None] * (eta - lc[:, None]) + par["b_shrunk"] * np.where(atp, z, 0.0)[:, None])
    return expit(a * lc + c * (eta - lc) + par["b_shrunk"] * np.where(atp, z, 0.0))


# ------------------------------------------------------------------------------------------------
# Measures

def realisation(q, q_ref, y, clusters, iters: int = 100) -> dict:
    """c in logit P = logit q_ref + c (logit q - logit q_ref), by Newton; cluster-sandwich SE (G / (G - 1))."""
    off, d = C.lg(q_ref), C.lg(q) - C.lg(q_ref)
    c = 0.0
    for _ in range(iters):
        p = expit(off + c * d)
        step = float(np.clip(np.dot(d, y - p) / (np.dot(d * d, p * (1 - p)) + 1e-12), -4, 4))
        c += step
        if abs(step) < 1e-12:
            break
    p = expit(off + c * d)
    bread = float(np.dot(d * d, p * (1 - p)))
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    u = np.bincount(ix, weights=(y - p) * d)
    se = float(np.sqrt(g / (g - 1) * np.dot(u, u)) / bread)
    # in-sample: what the disagreement is worth at its best size (one scale fitted on these rows; a diagnostic)
    best = 1000 * float((C.ll(q_ref, y) - C.ll(p, y)).mean())
    return {"c": c, "c_se": se, "sd_delta": float(np.std(d)), "gain_at_best_size": best}


def paired(rows: pd.DataFrame, q_base, qk_base, q_arm, qk_arm) -> dict:
    """1000 x mean(loss_base - loss_arm), positive = the arm better; block interval plus the seed term, paired by seed
    when both forecasts have seeds (a price has none)."""
    y = rows["y"].to_numpy(float)
    sb = SS.seed_loss(qk_base, y) if qk_base is not None else np.zeros(1)
    sa = SS.seed_loss(qk_arm, y) if qk_arm is not None else np.zeros(1)
    r = SS.paired_stats(C.ll(q_base, y), C.ll(q_arm, y), sb, sa, rows["block"].to_numpy(), rows["week"].to_numpy(),
                        matched_seeds=qk_base is not None and qk_arm is not None)
    r["reading"] = "better" if r["lo"] > 0 else ("worse" if r["hi"] < 0 else "tie")
    return r


# ------------------------------------------------------------------------------------------------

def build(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict, list[dict]]:
    """The 2019-2024 table (results, close, speed column, blocks), every forecast and the per-season parameters."""
    info = frame[frame["season"].between(C.SEASONS[0], C.SEASONS[-1])].set_index("match_id")
    info = info[["tour", "season", "tournament_date", "debut", "a_won"]].copy()
    info["y"] = info["a_won"].astype(float)
    info["block"] = C.SC.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.SC.blocks(info["tournament_date"].to_numpy(), 7)
    pm = pd.read_parquet(C.P.model_frame, columns=["match_id", "season", "p_mkt"],
                         filters=[("season", ">=", C.SEASONS[0]), ("season", "<=", C.LAST_SEASON)])
    pm["match_id"] = pm["match_id"].astype(str)
    info["p_mkt"] = pm.set_index("match_id")["p_mkt"].reindex(info.index).to_numpy(float)
    if not np.isfinite(info["p_mkt"]).all():
        raise RuntimeError("closing price missing")
    info["z"] = C.speed_column(info.index)
    info["atp"] = (info["tour"] == "atp").to_numpy()

    y, atp, z = info["y"].to_numpy(), info["atp"].to_numpy(), info["z"].to_numpy()
    lc = C.lg(info["p_mkt"].to_numpy())
    season = info["season"].to_numpy()
    test = np.isin(season, C.TEST) & ~info["debut"].to_numpy(bool)

    forecasts: dict[str, tuple[np.ndarray, np.ndarray]] = {}       # name -> (q, per-seed q), every 2019-2024 row
    params: list[dict] = []
    # the close, recalibrated the decided way
    q_close = np.full(len(info), np.nan)
    for Y in C.TEST:
        h, rows = history(info, Y), season == Y
        sl = {t: slope(lc[h & (atp == (t == "atp"))], y[h & (atp == (t == "atp"))]) for t in C.SC.TOURS}
        q_close[rows] = expit(np.where(atp[rows], sl["atp"], sl["wta"]) * lc[rows])
        params.append({"arm": "close", "season": Y, "s_atp": sl["atp"], "s_wta": sl["wta"]})
    forecasts["close"] = (q_close, None)
    # Pinnacle, the same way on the matches it prices (NaN elsewhere)
    pin = pd.read_parquet(PINNACLE, columns=["match_id", "p_pinnacle"])
    pin["match_id"] = pin["match_id"].astype(str)
    lp = C.lg(pin.set_index("match_id")["p_pinnacle"].reindex(info.index).to_numpy(float))
    has = np.isfinite(lp)
    q_pin = np.full(len(info), np.nan)
    for Y in C.TEST:
        h, rows = history(info, Y) & has, (season == Y) & has
        sl = {t: slope(lp[h & (atp == (t == "atp"))], y[h & (atp == (t == "atp"))]) for t in C.SC.TOURS}
        q_pin[rows] = expit(np.where(atp[rows], sl["atp"], sl["wta"]) * lp[rows])
        params.append({"arm": "pinnacle", "season": Y, "s_atp": sl["atp"], "s_wta": sl["wta"],
                       "rows": int(h.sum())})
    forecasts["pinnacle"] = (q_pin, None)

    etas = {}
    for arm in C.ARMS:
        per = load_arm(frame, arm)
        p = pd.concat([per[s] for s in C.SEASONS]).reindex(info.index)
        if p.isna().to_numpy().any():
            raise RuntimeError(f"{arm}: forecasts missing")
        pk = p.to_numpy()
        eta, eta_k = C.lg(pk.mean(axis=1)), C.lg(pk)
        etas[arm] = eta
        q2, q2k = np.full(len(info), np.nan), np.full(pk.shape, np.nan)
        q1, q1k = np.full(len(info), np.nan), np.full(pk.shape, np.nan)
        for Y in C.TEST:
            h, rows = history(info, Y), season == Y
            par = C.stage2_fit(eta[h], atp[h], z[h], y[h])
            q2[rows] = C.stage2_apply(eta[rows], atp[rows], z[rows], par)
            q2k[rows] = C.stage2_apply(eta_k[rows], atp[rows], z[rows], par)
            s1 = {t: slope(eta[h & (atp == (t == "atp"))], y[h & (atp == (t == "atp"))]) for t in C.SC.TOURS}
            s1r = np.where(atp[rows], s1["atp"], s1["wta"])
            q1[rows], q1k[rows] = expit(s1r * eta[rows]), expit(s1r[:, None] * eta_k[rows])
            params.append({"arm": arm, "season": Y, **par, "s1_atp": s1["atp"], "s1_wta": s1["wta"]})
        forecasts[arm] = (q2, q2k)
        forecasts[f"{arm}_stage1"] = (q1, q1k)
        if arm == "exp":
            eta_exp_k = eta_k
    # secondary: exp's two-part recalibration
    for name, start_of in (("2p_all", lambda Y: C.CALIB_FROM), ("2p_recent", lambda Y: max(C.CALIB_FROM, Y - 2))):
        q, qk = np.full(len(info), np.nan), np.full(eta_exp_k.shape, np.nan)
        for Y in C.TEST:
            h, rows = history(info, Y, start_of(Y)), season == Y
            par = two_part_fit(lc[h], etas["exp"][h], atp[h], z[h], y[h])
            q[rows] = two_part_apply(lc[rows], etas["exp"][rows], atp[rows], z[rows], par)
            qk[rows] = two_part_apply(lc[rows], eta_exp_k[rows], atp[rows], z[rows], par)
            params.append({"arm": f"exp_{name}", "season": Y, "fit_from": start_of(Y), **par})
        forecasts[f"exp_{name}"] = (q, qk)
    return info, forecasts, {"test_mask": test}, params


def stage2_check(params: list[dict]) -> dict:
    pub = C.read_json(C.STAGE2_PUBLISHED)["L_weekly"]["2024"]
    mine = next(p for p in params if p["arm"] == "exp" and p["season"] == 2024)
    diff = {k: abs(mine[k] - pub[k]) for k in ("s_atp", "s_wta", "b_mle", "se_b", "b_shrunk")}
    return {"published": "data/studies/serve_speed_tabpfn/adaptive/coefficients.json L_weekly 2024", "max_abs_diff":
            max(diff.values()), "rows_equal": mine["rows"] == pub["rows"],
            "passed": max(diff.values()) <= STAGE2_TOL and mine["rows"] == pub["rows"], "by_key": diff}


def comparisons(info: pd.DataFrame, fc: dict, test: np.ndarray) -> pd.DataFrame:
    out = []
    pairs = [("vs_exp", "exp", a) for a in C.NEW_ARMS + ("exp_2p_all", "exp_2p_recent")]
    pairs += [("recency", f"rand{n}", f"last{n}") for n in (7, 5, 3)]
    pairs += [("vs_close", "close", a) for a in C.ARMS + ("exp_2p_all", "exp_2p_recent")]
    pairs += [("vs_pinnacle", "pinnacle", a) for a in C.ARMS + ("exp_2p_all", "exp_2p_recent")]
    pairs += [("stage1", "exp_stage1", f"{a}_stage1") for a in C.NEW_ARMS]
    # the learned move without the speed term (stage 2 adds a disagreement of its own for men)
    pairs += [("stage1_vs_close", "close", f"{a}_stage1") for a in C.ARMS]
    pairs += [("stage1_vs_pinnacle", "pinnacle", f"{a}_stage1") for a in C.ARMS]
    pairs += [("speed_adjustment", "exp_stage1", "exp")]      # stage 2 against the calibrated base (side check)
    season = info["season"].to_numpy()
    priced = np.isfinite(fc["pinnacle"][0])
    windows = dict(C.ERAS)
    windows.update({str(s): (s,) for s in C.TEST if str(s) not in windows})     # "2024" is an era and a season
    for era, seasons in windows.items():
        for pop in POPULATIONS:
            m0 = test & np.isin(season, seasons)
            if pop != "both":
                m0 &= (info["tour"] == pop).to_numpy()
            for kind, base, arm in pairs:
                m = m0 & priced if kind.endswith("vs_pinnacle") else m0
                rows = info[m]
                y = rows["y"].to_numpy(float)
                (qb, qbk), (qa, qak) = fc[base], fc[arm]
                r = paired(rows, qb[m], None if qbk is None else qbk[m], qa[m], None if qak is None else qak[m])
                rec = {"comparison": kind, "base": base, "arm": arm, "window": era, "population": pop,
                       **{k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "blocks", "reading", "seed_term",
                                            "se_unpaired", "lo_unpaired", "hi_unpaired")},
                       "ll_base": float(C.ll(qb[m], y).mean()), "ll_arm": float(C.ll(qa[m], y).mean())}
                if kind.endswith(("vs_close", "vs_pinnacle")):
                    rec.update(realisation(qa[m], qb[m], y, rows["block"].to_numpy()))
                out.append(rec)
    return pd.DataFrame(out)


def main() -> int:
    frame = C.load_frame(labels=True)
    rep = reproduction()
    if not rep["passed"]:
        C.write_json(C.OUT / "results.json", {"reproduction": rep})
        raise RuntimeError("the reproduction check failed: see results.json")
    info, fc, extra, params = build(frame)
    st2 = stage2_check(params)
    if not st2["passed"]:
        C.write_json(C.OUT / "results.json", {"reproduction": rep, "stage2_check": st2})
        raise RuntimeError(f"exp's stage-2 coefficients differ from the published ones: {st2}")
    res = comparisons(info, fc, extra["test_mask"])
    res.to_csv(C.OUT / "results.csv", index=False)
    pd.DataFrame(params).to_csv(C.OUT / "season_params.csv", index=False)
    fits = []
    for arm in C.ARMS:
        for s in C.SEASONS:
            for k in C.SEEDS:
                _, _, meta = C.read_fit(C.fit_path(arm, s, k))
                fits.append({"arm": arm, "season": s, "seed": k, "train_rows": meta["train_shape"][0],
                             "seconds": meta.get("seconds")})
    C.write_json(C.OUT / "results.json", {
        "what": "training-window study: each arm's two-stage forecast against the current model's, 2020-2024",
        "units": "milli-log-loss per match; positive = the arm (second-named) better; a 95% interval spanning 0 is a "
                 "tie; c: 1 = right-sized moves away from the close, below 1 = too far, above 1 = not far enough",
        "seasons_read": [int(frame["season"].min()), int(frame["season"].max())],
        "model_frame_sha256": C.sha256_file(C.P.model_frame), "speed_sha256": C.sha256_file(C.SPEED),
        "pinnacle_sha256": C.sha256_file(PINNACLE),
        "reproduction": rep, "stage2_check": st2, "scored_matches": int(extra["test_mask"].sum()),
        "fits": fits})
    head = res[(res["window"] == "2020-2024")]
    cols = ["comparison", "base", "arm", "population", "matches", "estimate", "lo", "hi", "reading"]
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print(head[cols + ["c", "c_se", "sd_delta"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
