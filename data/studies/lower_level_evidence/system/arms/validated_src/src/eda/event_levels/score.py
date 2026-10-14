"""Scoring of the event-levels study (reading rules: data/studies/event_levels/reading_rules.md, written before this).

Part 1, the current model by level (2020-2024, debut seasons out). The current model's two-stage forecast (exp: stored
fits, seeds 0-3, stage 2 as decided on every level's matches of 2019 .. Y - 1) against the recalibrated close and
Pinnacle on each level's matches, with the realisation of its moves away from the close, and each forecast's own
calibration slope by level.

Part 2, experiment A. Every arm's eta is the log-odds of its seed-mean symmetrised forecast. A forecast is given its
stage 2 (the decided rule: logit q = s_tour eta + b spd_L, b shrunk) fitted on a named group of matches of
2019 .. Y - 1, and is scored on that group's matches of season Y:
    target arms (own, w25, w50, size of level L)   stage 2 on L's matches; compared with exp (decided, every level)
                                                   and exp_L (exp with its stage 2 on L's matches)
    drop_L                                         on L's matches (stage 2 on L's, against exp_L) and on the other
                                                   levels' (stage 2 on theirs, against exp_notL)
Part 3, experiment B (2022-2024; calibration 2021 .. Y - 1, seeds 0-1). No-odds arms are calibrated per tour on their
own forecasts of the scored population (MT or CH); omtch and exp (seeds 0-1) get stage 2 on MT matches of 2021 .. Y - 1.
Part 4, players between levels: logistic of the result on a forecast's log-odds (slope fitted) plus beta x (A's share
of last year's matches below the main tour - B's), on main-tour matches 2020-2024, for exp, the close and Pinnacle.

Writes data/studies/event_levels/results.csv (every comparison), by_level.csv (part 1), climbers.csv (part 4),
b_levels.csv (log loss by population) and results.json (checks, reproduction, parameters).
Run: ./python.sh src/eda/event_levels/score.py [--only A|B]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import blend as BL  # noqa: E402  (logistic_cluster)
from src.eda.event_levels import common as C  # noqa: E402
from src.eda.event_levels import fits as F  # noqa: E402
from src.eda.training_window import common as TW  # noqa: E402
from src.eda.training_window import score as TWS  # noqa: E402

WINDOWS_A = {"2020-2024": C.TEST_A, "2020-2021": (2020, 2021), "2022-2024": (2022, 2023, 2024)}
WINDOWS_B = {"2022-2024": C.TEST_B, **{str(s): (s,) for s in C.TEST_B}}
POPS = ("both", "atp", "wta")


# ------------------------------------------------------------------------------------------------
# Shared

def base_info(frame: pd.DataFrame, seasons) -> pd.DataFrame:
    info = frame[frame["season"].isin(seasons)].set_index("match_id").copy()
    info["y"] = info["a_won"].astype(float)
    info["block"] = TW.SC.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = TW.SC.blocks(info["tournament_date"].to_numpy(), 7)
    info["atp"] = (info["tour"] == "atp").to_numpy()
    return info


def seed_matrix(paths_ids, check=None) -> pd.DataFrame:
    """[(season, seed, path, ids)] -> matches x seeds of symmetrised P(A wins)."""
    per = {}
    for season, seed, path, ids in paths_ids:
        p, meta = TW.symmetrised(path, ids)
        if check is not None:
            check(meta, season, seed)
        per.setdefault(season, {})[seed] = pd.Series(p, index=pd.Index(ids, dtype=str))
    return pd.concat([pd.DataFrame(v) for _, v in sorted(per.items())])


def staged(info: pd.DataFrame, P: pd.DataFrame, group: np.ndarray, tests, calib_from: int, speed: bool = True):
    """The forecast P (matches x seeds, reindexed to info) with its stage 2 (speed: the decided rule) or its stage 1
    (one slope per tour) fitted on `group`'s matches of calib_from .. Y - 1, applied to `group`'s matches of each test
    season Y. Returns {"s2": (q, qk), "s1": (q, qk), "params": [...]}; NaN outside the group's test rows."""
    pk = P.reindex(info.index).to_numpy()
    eta_k = TW.lg(pk)
    eta = TW.lg(np.nanmean(pk, axis=1))
    y, atp, season = info["y"].to_numpy(), info["atp"].to_numpy(), info["season"].to_numpy()
    debut = info["debut"].to_numpy(bool)
    z = info["z"].to_numpy() if "z" in info.columns else np.zeros(len(info))
    out = {k: (np.full(len(info), np.nan), np.full(pk.shape, np.nan)) for k in ("s1", "s2")}
    params = []
    for Y in tests:
        hist = group & (season >= calib_from) & (season < Y) & ~debut
        rows = group & (season == Y)
        if not rows.any():
            continue
        if not (np.isfinite(eta[hist]).all() and np.isfinite(eta[rows]).all()):
            raise RuntimeError("a forecast is missing on a calibration or test row")
        s1 = {t: TWS.slope(eta[hist & (atp == (t == "atp"))], y[hist & (atp == (t == "atp"))]) for t in C.TOURS}
        s1r = np.where(atp[rows], s1["atp"], s1["wta"])
        out["s1"][0][rows], out["s1"][1][rows] = expit(s1r * eta[rows]), expit(s1r[:, None] * eta_k[rows])
        rec = {"season": Y, "s1_atp": s1["atp"], "s1_wta": s1["wta"], "calib_rows": int(hist.sum())}
        if speed:
            par = TW.stage2_fit(eta[hist], atp[hist], z[hist], y[hist])
            out["s2"][0][rows] = TW.stage2_apply(eta[rows], atp[rows], z[rows], par)
            out["s2"][1][rows] = TW.stage2_apply(eta_k[rows], atp[rows], z[rows], par)
            rec.update(par)
        params.append(rec)
    out["params"] = params
    return out


def recal_price(info: pd.DataFrame, logit_price: np.ndarray, tests, calib_from: int = TW.CALIB_FROM) -> np.ndarray:
    """A price recalibrated the decided way: one slope per tour on its log-odds, calib_from .. Y - 1 (NaN where no
    price)."""
    y, atp, season = info["y"].to_numpy(), info["atp"].to_numpy(), info["season"].to_numpy()
    debut = info["debut"].to_numpy(bool)
    has = np.isfinite(logit_price)
    q = np.full(len(info), np.nan)
    for Y in tests:
        h = has & (season >= calib_from) & (season < Y) & ~debut
        rows = has & (season == Y)
        sl = {t: TWS.slope(logit_price[h & (atp == (t == "atp"))], y[h & (atp == (t == "atp"))]) for t in C.TOURS}
        q[rows] = expit(np.where(atp[rows], sl["atp"], sl["wta"]) * logit_price[rows])
    return q


def compare(info, mask, base, arm, meta: dict, realise: bool = False) -> dict:
    """base, arm: (q, qk or None). + = arm better."""
    rows = info[mask]
    y = rows["y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    qb, qa = qb[mask], qa[mask]
    if not (np.isfinite(qb).all() and np.isfinite(qa).all()):
        raise RuntimeError(f"missing forecasts in comparison {meta}")
    r = TWS.paired(rows, qb, None if qbk is None else qbk[mask], qa, None if qak is None else qak[mask])
    rec = {**meta, **{k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "blocks", "reading")},
           "ll_base": float(TW.ll(qb, y).mean()), "ll_arm": float(TW.ll(qa, y).mean())}
    if realise:
        rec.update(TWS.realisation(qa, qb, y, rows["block"].to_numpy()))
    return rec


def each(info, mask0, windows, fn):
    """fn(mask, window, population) for each window and population."""
    season = info["season"].to_numpy()
    out = []
    for w, seasons in windows.items():
        for pop in POPS:
            m = mask0 & np.isin(season, seasons)
            if pop != "both":
                m &= (info["tour"] == pop).to_numpy()
            if m.sum() >= 50:
                out += fn(m, w, pop)
    return out


# ------------------------------------------------------------------------------------------------
# Experiment A and part 1

def info_a() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = F.frame_a(labels=True)
    info = base_info(frame, C.SEASONS_A)
    info["level"] = [C.CODE_LEVEL[int(c)] for c in info["level_code"]]
    pm = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "season", "p_mkt"],
                         filters=[("season", ">=", C.SEASONS_A[0]), ("season", "<=", C.LAST_SEASON)])
    pm["match_id"] = pm["match_id"].astype(str)
    info["p_mkt"] = pm.set_index("match_id")["p_mkt"].reindex(info.index).to_numpy(float)
    info["z"] = TW.speed_column(info.index)
    return info, frame


def load_a(frame: pd.DataFrame, arm: str) -> pd.DataFrame:
    seasons, levels = frame["season"].to_numpy(), frame["level_code"].to_numpy()

    def check(meta, season, seed):
        n = int(C.train_mask_a(seasons, levels, arm, season, seed).sum())
        want_arm = "model" if arm == "exp" else arm
        problems = [w for w, ok in (("arm", meta.get("arm") == want_arm), ("season", meta.get("season") == season),
                                    ("seed", meta.get("seed") == seed),
                                    ("config", meta.get("config") == {**C.CONFIG, "random_state": seed}),
                                    ("columns", TW.SC.race_names(meta.get("columns") or []) == F.NAMES),
                                    ("train_shape", list(meta.get("train_shape", [])) == [n, len(F.NAMES)]))
                    if not ok]
        if problems:
            raise RuntimeError(f"{arm} {season} seed {seed}: {problems}")

    jobs = [(s, k, C.fit_path_a(arm, s, k), frame.loc[frame["season"] == s, "match_id"].to_numpy())
            for s in C.SEASONS_A for k in C.SEEDS_A]
    return seed_matrix(jobs, check)


def score_a(experiment: bool = True, levels=C.TARGETS) -> tuple[list[dict], pd.DataFrame, pd.DataFrame, list[dict]]:
    """Parts 1, 2 and 4; experiment=False skips part 2 (the stored fits alone); levels limits part 2's targets."""
    info, frame = info_a()
    season, level = info["season"].to_numpy(), info["level"].to_numpy()
    test = np.isin(season, C.TEST_A) & ~info["debut"].to_numpy(bool)
    allrows = np.ones(len(info), bool)
    q_close = recal_price(info, TW.lg(info["p_mkt"].to_numpy()), C.TEST_A)
    pin = pd.read_parquet(TWS.PINNACLE, columns=["match_id", "p_pinnacle"])
    pin["match_id"] = pin["match_id"].astype(str)
    lp = TW.lg(pin.set_index("match_id")["p_pinnacle"].reindex(info.index).to_numpy(float))
    q_pin = recal_price(info, lp, C.TEST_A)
    close, pinn = (q_close, None), (q_pin, None)
    E = load_a(frame, "exp")
    exp = staged(info, E, allrows, C.TEST_A, TW.CALIB_FROM)
    results, params = [], [{"arm": "exp", "group": "all", **p} for p in exp["params"]]

    # part 1: the current model by level
    by_level = []
    for lv, lvls in [(lv, (lv,)) for lv in C.MAIN] + [("all", C.MAIN)]:
        g = test & np.isin(level, lvls)

        def p1(m, w, pop):
            out = [compare(info, m, close, exp["s2"], {"part": 1, "comparison": "exp_vs_close", "level": lv,
                                                        "window": w, "population": pop}, realise=True)]
            mp = m & np.isfinite(q_pin)
            if mp.sum() >= 50:
                out.append(compare(info, mp, pinn, exp["s2"], {"part": 1, "comparison": "exp_vs_pinnacle",
                                                                "level": lv, "window": w, "population": pop},
                                   realise=True))
            return out
        results += each(info, g, WINDOWS_A, p1)
        for pop in POPS:
            m = g & (True if pop == "both" else (info["tour"] == pop).to_numpy())
            y = info.loc[m, "y"].to_numpy()
            rec = {"level": lv, "population": pop, "matches": int(m.sum())}
            for name, q in (("close", q_close), ("exp", exp["s2"][0]), ("pinnacle", q_pin)):
                mm = m & np.isfinite(q)
                yy = info.loc[mm, "y"].to_numpy()
                b, se = BL.logistic_cluster(TW.lg(q[mm])[:, None], yy, info.loc[mm, "block"].to_numpy())
                rec[f"ll_{name}"] = float(TW.ll(q[mm], yy).mean())
                rec[f"slope_{name}"], rec[f"slope_se_{name}"] = float(b[0]), float(se[0])
            rec["ll_coin"] = float(np.log(2))
            rec["fav_won_close"] = float(((q_close[m] > 0.5) == (y == 1)).mean())
            by_level.append(rec)

    # part 2: experiment A
    pk_exp = E.reindex(info.index).to_numpy()
    eta_exp, eta_exp_k = TW.lg(pk_exp.mean(axis=1)), TW.lg(pk_exp)
    lc = TW.lg(info["p_mkt"].to_numpy())
    y_all, atp_all, z_all = info["y"].to_numpy(), info["atp"].to_numpy(), info["z"].to_numpy()
    season_all, debut_all = info["season"].to_numpy(), info["debut"].to_numpy(bool)
    for L in (levels if experiment else ()):
        gL = level == L
        exp_L = staged(info, E, gL, C.TEST_A, TW.CALIB_FROM)
        exp_notL = staged(info, E, ~gL, C.TEST_A, TW.CALIB_FROM)
        params += [{"arm": "exp", "group": L, **p} for p in exp_L["params"]]
        # exploratory (reading rules A6): the move away from the close re-sized per level, no refit
        q2p, q2pk = np.full(len(info), np.nan), np.full(eta_exp_k.shape, np.nan)
        for Y in C.TEST_A:
            h = gL & (season_all >= TW.CALIB_FROM) & (season_all < Y) & ~debut_all
            rows = gL & (season_all == Y)
            par = TWS.two_part_fit(lc[h], eta_exp[h], atp_all[h], z_all[h], y_all[h])
            q2p[rows] = TWS.two_part_apply(lc[rows], eta_exp[rows], atp_all[rows], z_all[rows], par)
            q2pk[rows] = TWS.two_part_apply(lc[rows], eta_exp_k[rows], atp_all[rows], z_all[rows], par)
            params.append({"arm": "exp_2pL", "group": L, "season": Y, **par})
        fc = {"exp": exp["s2"], "exp_L": exp_L["s2"], "close": close, "exp_2pL": (q2p, q2pk)}
        s1 = {"exp_L": exp_L["s1"]}
        for kind in ("own", "w25", "w50", "size"):
            arm = f"{kind}_{L}"
            st = staged(info, load_a(frame, arm), gL, C.TEST_A, TW.CALIB_FROM)
            fc[arm], s1[arm] = st["s2"], st["s1"]
            params += [{"arm": arm, "group": L, **p} for p in st["params"]]
        D = load_a(frame, f"drop_{L}")
        drop_L = staged(info, D, gL, C.TEST_A, TW.CALIB_FROM)
        drop_o = staged(info, D, ~gL, C.TEST_A, TW.CALIB_FROM)

        def p2(m, w, pop):
            meta = {"part": 2, "level": L, "window": w, "population": pop}
            out = [compare(info, m, fc["exp"], fc["exp_L"], {**meta, "comparison": "expL_vs_exp", "arm": "exp_L"}),
                   compare(info, m, fc["exp"], fc["exp_2pL"], {**meta, "comparison": "exp2pL_vs_exp",
                                                                "arm": "exp_2pL"}),
                   compare(info, m, fc["close"], fc["exp_2pL"], {**meta, "comparison": "vs_close", "arm": "exp_2pL"},
                           realise=True)]
            for kind in ("own", "w25", "w50", "size"):
                arm = f"{kind}_{L}"
                out.append(compare(info, m, fc["exp"], fc[arm], {**meta, "comparison": "vs_exp", "arm": arm}))
                out.append(compare(info, m, fc["exp_L"], fc[arm], {**meta, "comparison": "vs_exp_L", "arm": arm}))
                out.append(compare(info, m, s1["exp_L"], s1[arm], {**meta, "comparison": "stage1_vs_exp_L",
                                                                    "arm": arm}))
                out.append(compare(info, m, fc["close"], fc[arm], {**meta, "comparison": "vs_close", "arm": arm},
                                   realise=True))
            out.append(compare(info, m, fc["close"], fc["exp_L"], {**meta, "comparison": "vs_close", "arm": "exp_L"},
                               realise=True))
            out.append(compare(info, m, fc[f"size_{L}"], fc[f"own_{L}"], {**meta, "comparison": "own_vs_size",
                                                                          "arm": f"own_{L}"}))
            out.append(compare(info, m, fc["exp_L"], drop_L["s2"], {**meta, "comparison": "drop_on_own_level",
                                                                    "arm": f"drop_{L}"}))
            return out
        results += each(info, test & gL, WINDOWS_A, p2)

        def p2o(m, w, pop):
            meta = {"part": 2, "level": L, "window": w, "population": pop, "arm": f"drop_{L}"}
            out = [compare(info, m, exp_notL["s2"], drop_o["s2"], {**meta, "comparison": "drop_on_other_levels",
                                                                   "scored_level": "others"})]
            for M in C.TARGETS:
                mm = m & (level == M)
                if M != L and mm.sum() >= 50:
                    out.append(compare(info, mm, exp_notL["s2"], drop_o["s2"],
                                       {**meta, "comparison": "drop_on_other_levels", "scored_level": M}))
            return out
        results += each(info, test & ~gL, WINDOWS_A, p2o)
        C.log(f"experiment A scored for {L}")

    # part 4: players between levels, the model and the prices
    hist = pd.read_parquet(C.OUT / "history.parquet", columns=["match_id", "side", "low_share", "home", "n_all"])
    ph = BL.pair_history(hist.assign(n_all=hist["n_all"]))
    j = ph.reindex(info.index)
    z_low = (j["low_a"] - j["low_b"]).to_numpy(float)
    climbers = []
    for where, lvls in (("main tour", C.MAIN), ("GS", ("GS",)), ("T1000", ("T1000",)), ("T500", ("T500",)),
                        ("T250", ("T250",))):
        for pop in POPS:
            m = test & np.isin(level, lvls) & np.isfinite(z_low)
            if pop != "both":
                m &= (info["tour"] == pop).to_numpy()
            for name, q in (("exp", exp["s2"][0]), ("close", q_close), ("pinnacle", q_pin)):
                mm = m & np.isfinite(q)
                if mm.sum() < 300:
                    continue
                y = info.loc[mm, "y"].to_numpy()
                b, se = BL.logistic_cluster(np.column_stack([TW.lg(q[mm]), z_low[mm]]), y,
                                            info.loc[mm, "block"].to_numpy())
                climbers.append({"where": where, "population": pop, "forecast": name, "rows": int(mm.sum()),
                                 "slope": float(b[0]), "beta": float(b[1]), "se": float(se[1]),
                                 "lo": float(b[1] - 1.96 * se[1]), "hi": float(b[1] + 1.96 * se[1]),
                                 "sd_z": float(np.std(z_low[mm]))})
    return results, pd.DataFrame(by_level), pd.DataFrame(climbers), params


# ------------------------------------------------------------------------------------------------
# Part 4b: the prices on every season (the replication on 2013-2019, where the lead was not found) and what drives it

ERAS_4B = {"2013-2016": range(2013, 2017), "2017-2019": range(2017, 2020), "2013-2019": range(2013, 2020),
           "2020-2024": range(2020, 2025), "2013-2024": range(2013, 2025)}


def pair_cols(hist: pd.DataFrame, ids: pd.Index) -> pd.DataFrame:
    a = hist[hist["side"] == "A"].set_index("match_id").reindex(ids)
    b = hist[hist["side"] == "B"].set_index("match_id").reindex(ids)
    return pd.DataFrame({"d_low": a["low_share"].to_numpy(float) - b["low_share"].to_numpy(float),
                         "d_logn": np.log1p(a["n_all"].to_numpy(float)) - np.log1p(b["n_all"].to_numpy(float)),
                         "d_win": a["win_share"].to_numpy(float) - b["win_share"].to_numpy(float)}, index=ids)


def climbers_prices() -> pd.DataFrame:
    """logit P = a logit(price) + beta . terms, slope fitted, on every main-tour match with the price (raw de-vigged,
    the slope absorbs the recalibration), debut seasons out, by era. Models: the share alone; with match volume; with
    last year's win share; with both."""
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "a_won", "p_mkt"], filters=[("season", "<=", C.LAST_SEASON)])
    f["match_id"] = f["match_id"].astype(str)
    C.frame_seasons_ok(f)
    f = f[~f["debut_season"].astype(bool)].set_index("match_id")
    pin = pd.read_parquet(TWS.PINNACLE, columns=["match_id", "p_pinnacle"])
    pin["match_id"] = pin["match_id"].astype(str)
    f["p_pinnacle"] = pin.set_index("match_id")["p_pinnacle"].reindex(f.index).to_numpy(float)
    hist = pd.read_parquet(C.OUT / "history.parquet", columns=["match_id", "side", "low_share", "n_all", "win_share"])
    f = f.join(pair_cols(hist, f.index))
    f["y"] = f["a_won"].astype(float)
    f["block"] = TW.SC.blocks(f["tournament_date"].to_numpy(), 28)
    models = {"share": ["d_low"], "share+volume": ["d_low", "d_logn"], "share+wins": ["d_low", "d_win"],
              "share+volume+wins": ["d_low", "d_logn", "d_win"], "volume": ["d_logn"], "wins": ["d_win"]}
    rows = []
    for era, seasons in ERAS_4B.items():
        for pop in POPS:
            for price in ("p_mkt", "p_pinnacle"):
                m = f["season"].isin(list(seasons)) & np.isfinite(f[price]) & f[["d_low", "d_logn", "d_win"]].notna().all(axis=1)
                if pop != "both":
                    m &= f["tour"] == pop
                g = f[m]
                if len(g) < 500:
                    continue
                for name, terms in models.items():
                    if price == "p_pinnacle" and name not in ("share", "share+volume+wins"):
                        continue
                    Z = np.column_stack([TW.lg(g[price].to_numpy())] + [g[t].to_numpy() for t in terms])
                    b, se = BL.logistic_cluster(Z, g["y"].to_numpy(), g["block"].to_numpy())
                    for i, t in enumerate(terms, start=1):
                        rows.append({"era": era, "population": pop, "price": "close" if price == "p_mkt" else
                                     "pinnacle", "model": name, "term": t, "rows": int(len(g)), "slope": float(b[0]),
                                     "beta": float(b[i]), "se": float(se[i]), "lo": float(b[i] - 1.96 * se[i]),
                                     "hi": float(b[i] + 1.96 * se[i]), "sd_term": float(np.std(g[t]))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# Experiment C: the history composition as an input

def score_c() -> tuple[list[dict], pd.DataFrame, list[dict]]:
    info, frame = info_a()
    level = info["level"].to_numpy()
    test = np.isin(info["season"].to_numpy(), C.TEST_A) & ~info["debut"].to_numpy(bool)
    allrows = np.ones(len(info), bool)
    q_close = recal_price(info, TW.lg(info["p_mkt"].to_numpy()), C.TEST_A)
    pin = pd.read_parquet(TWS.PINNACLE, columns=["match_id", "p_pinnacle"])
    pin["match_id"] = pin["match_id"].astype(str)
    q_pin = recal_price(info, TW.lg(pin.set_index("match_id")["p_pinnacle"].reindex(info.index).to_numpy(float)),
                        C.TEST_A)
    exp = staged(info, load_a(frame, "exp"), allrows, C.TEST_A, TW.CALIB_FROM)
    pool_n = {s: int(C.train_mask_a(frame["season"].to_numpy(), frame["level_code"].to_numpy(), "exp", s, 0).sum())
              for s in C.SEASONS_C}

    def check(meta, season, seed):
        problems = [w for w, ok in (("arm", meta.get("arm") == "hist1"), ("season", meta.get("season") == season),
                                    ("seed", meta.get("seed") == seed),
                                    ("config", meta.get("config") == {**C.CONFIG, "random_state": seed}),
                                    ("columns", meta.get("columns") == F.NAMES + [C.NEW_INPUT_C]),
                                    ("train_shape", list(meta.get("train_shape", [])) == [pool_n[season],
                                                                                          len(F.NAMES) + 1]))
                    if not ok]
        if problems:
            raise RuntimeError(f"hist1 {season} seed {seed}: {problems}")

    H = seed_matrix([(s, k, C.fit_path_c("hist1", s, k), frame.loc[frame["season"] == s, "match_id"].to_numpy())
                     for s in C.SEASONS_C for k in C.SEEDS_C], check)
    hist1 = staged(info, H, allrows, C.TEST_A, TW.CALIB_FROM)
    params = [{"arm": "hist1", **p} for p in hist1["params"]]
    # C2 (exploratory, reading rules C4): the share as a third walk-forward term in the current model's stage 2
    hist = pd.read_parquet(C.OUT / "history.parquet", columns=["match_id", "side", "low_share", "n_all", "win_share"])
    zlow = np.nan_to_num(pair_cols(hist, info.index)["d_low"].to_numpy(), nan=0.0)
    pk = load_a(frame, "exp").reindex(info.index).to_numpy()
    eta, eta_k = TW.lg(pk.mean(axis=1)), TW.lg(pk)
    y, atp, z = info["y"].to_numpy(), info["atp"].to_numpy(), info["z"].to_numpy()
    season, debut = info["season"].to_numpy(), info["debut"].to_numpy(bool)
    q3, q3k = np.full(len(info), np.nan), np.full(pk.shape, np.nan)
    for Y in C.TEST_A:
        h = (season >= TW.CALIB_FROM) & (season < Y) & ~debut
        rows = season == Y
        Z = np.column_stack([np.where(atp, eta, 0.0), np.where(~atp, eta, 0.0), np.where(atp, z, 0.0), zlow])
        beta, se = C.fit_logistic(Z[h], y[h])
        b = float(beta[2]) * TW.TAU ** 2 / (TW.TAU ** 2 + float(se[2]) ** 2)
        s_r = np.where(atp[rows], beta[0], beta[1])
        q3[rows] = expit(s_r * eta[rows] + b * np.where(atp[rows], z[rows], 0.0) + beta[3] * zlow[rows])
        q3k[rows] = expit(s_r[:, None] * eta_k[rows] + (b * np.where(atp[rows], z[rows], 0.0)
                                                         + beta[3] * zlow[rows])[:, None])
        params.append({"arm": "exp_s2low", "season": Y, "s_atp": float(beta[0]), "s_wta": float(beta[1]),
                       "b_mle": float(beta[2]), "b_shrunk": b, "g": float(beta[3]), "se_g": float(se[3]),
                       "rows": int(h.sum())})
    s2low = (q3, q3k)
    results = []
    for where, lvls in (("main tour", C.MAIN), ("GS", ("GS",)), ("T1000", ("T1000",)), ("T500", ("T500",)),
                        ("T250", ("T250",))):
        def pc(m, w, pop):
            meta = {"part": "C", "level": where, "window": w, "population": pop, "arm": "hist1"}
            out = [compare(info, m, exp["s2"], hist1["s2"], {**meta, "comparison": "hist1_vs_exp", "stage": 2}),
                   compare(info, m, exp["s1"], hist1["s1"], {**meta, "comparison": "hist1_vs_exp", "stage": 1}),
                   compare(info, m, (q_close, None), hist1["s2"], {**meta, "comparison": "vs_close", "stage": 2},
                           realise=True)]
            mp = m & np.isfinite(q_pin)
            out.append(compare(info, mp, (q_pin, None), hist1["s2"], {**meta, "comparison": "vs_pinnacle",
                                                                       "stage": 2}, realise=True))
            out.append(compare(info, m, exp["s2"], s2low, {**meta, "arm": "exp_s2low",
                                                           "comparison": "s2low_vs_exp", "stage": 2}))
            out.append(compare(info, m, (q_close, None), s2low, {**meta, "arm": "exp_s2low",
                                                                 "comparison": "vs_close", "stage": 2}, realise=True))
            out.append(compare(info, mp, (q_pin, None), s2low, {**meta, "arm": "exp_s2low",
                                                                "comparison": "vs_pinnacle", "stage": 2},
                               realise=True))
            return out
        results += each(info, test & np.isin(level, lvls), WINDOWS_A, pc)
    z = pair_cols(hist, info.index)["d_low"].to_numpy()
    cl = []
    for pop in POPS:
        m = test & np.isfinite(z) & (True if pop == "both" else (info["tour"] == pop).to_numpy())
        for name, q in (("exp", exp["s2"][0]), ("hist1", hist1["s2"][0]), ("exp_s2low", s2low[0])):
            b, se = BL.logistic_cluster(np.column_stack([TW.lg(q[m]), z[m]]), info.loc[m, "y"].to_numpy(),
                                        info.loc[m, "block"].to_numpy())
            cl.append({"population": pop, "forecast": name, "rows": int(m.sum()), "slope": float(b[0]),
                       "beta": float(b[1]), "se": float(se[1]), "lo": float(b[1] - 1.96 * se[1]),
                       "hi": float(b[1] + 1.96 * se[1])})
    return results, pd.DataFrame(cl), params


# ------------------------------------------------------------------------------------------------
# Experiment B

def score_b() -> tuple[list[dict], pd.DataFrame, dict, list[dict]]:
    frame = F.frame_b(labels=True)
    info = base_info(frame, C.SEASONS_B)
    info["debut"] = info["debut_season"].astype(bool)          # the extended frame's name for the decided flag
    pop = info["pop"].to_numpy()
    season = info["season"].to_numpy()
    mt, ch = pop == "MT", pop == "CH"
    z = np.zeros(len(info))
    z[mt] = TW.speed_column(info.index[mt])
    info["z"] = z
    test = np.isin(season, C.TEST_B) & ~info["debut"].to_numpy(bool)

    def check_for(arm):
        def check(meta, s, k):
            n = int(C.train_mask_b(frame["season"].to_numpy(), frame["pop"].to_numpy(), arm, s).sum())
            cols = F.NAMES if C.has_odds_b(arm) else F.NOODDS
            problems = [w for w, ok in (("arm", meta.get("arm") == arm), ("season", meta.get("season") == s),
                                        ("seed", meta.get("seed") == k),
                                        ("config", meta.get("config") == {**C.CONFIG, "random_state": k}),
                                        ("columns", meta.get("columns") == cols),
                                        ("train_shape", list(meta.get("train_shape", [])) == [n, len(cols)]))
                        if not ok]
            if problems:
                raise RuntimeError(f"{arm} {s} seed {k}: {problems}")
        return check

    def ids_of(s):
        return frame.loc[C.query_mask_b(frame["season"], frame["pop"], s), "match_id"].to_numpy()

    P = {arm: seed_matrix([(s, k, C.fit_path_b(arm, s, k), ids_of(s)) for s in C.SEASONS_B for k in C.SEEDS_B],
                          check_for(arm)) for arm in C.ARMS_B}
    # exp, seeds 0-1, on MT rows (its stored fits query the model frame's season rows)
    fa = F.frame_a(labels=False)
    P["exp"] = seed_matrix([(s, k, TW.stored_path(s, k), fa.loc[fa["season"] == s, "match_id"].to_numpy())
                            for s in C.SEASONS_B for k in C.SEEDS_B])
    # reproduction: nmt on MT rows against the stored no-odds fits
    stored = seed_matrix([(s, k, C.stored_noodds_path(s, k), fa.loc[fa["season"] == s, "match_id"].to_numpy())
                          for s in C.SEASONS_B for k in C.SEEDS_B])
    common_ids = stored.index.intersection(P["nmt"].index)
    diff = np.abs(stored.loc[common_ids].to_numpy() - P["nmt"].loc[common_ids].to_numpy())
    repro = {"rows": int(len(common_ids)), "max_abs_diff": float(diff.max()), "mean_abs_diff": float(diff.mean()),
             "passed": bool(diff.max() <= 1e-4)}

    st = {}
    params = []
    for arm in ("nmt", "nch", "nmtch", "omtch"):
        for name, g in (("MT", mt), ("CH", ch)):
            st[(arm, name)] = staged(info, P[arm], g, C.TEST_B, C.SEASONS_B[0], speed=(arm == "omtch" and name == "MT"))
            params += [{"arm": arm, "group": name, **p} for p in st[(arm, name)]["params"]]
    st[("exp", "MT")] = staged(info, P["exp"], mt, C.TEST_B, C.SEASONS_B[0], speed=True)
    q_close = recal_price(info, TW.lg(info["p_mkt"].to_numpy()), C.TEST_B, calib_from=C.SEASONS_B[0])
    pc = pd.read_parquet(C.SOURCES["pieces"][0], columns=["match_id", "R_a", "R_b"]).set_index("match_id")
    elo = (np.log(10) / 400) * (pc["R_a"] - pc["R_b"]).reindex(info.index).to_numpy(float)
    q_elo = np.full(len(info), np.nan)
    for g in (mt, ch):
        q_g = recal_price(info.assign(_g=g), np.where(g, elo, np.nan), C.TEST_B, calib_from=C.SEASONS_B[0])
        q_elo[g] = q_g[g]

    results = []

    def pb_mt(m, w, p):
        meta = {"part": 3, "scored": "MT", "window": w, "population": p}
        return [
            compare(info, m, st[("exp", "MT")]["s2"], st[("omtch", "MT")]["s2"],
                    {**meta, "comparison": "omtch_vs_exp", "stage": 2, "arm": "omtch"}),
            compare(info, m, st[("exp", "MT")]["s1"], st[("omtch", "MT")]["s1"],
                    {**meta, "comparison": "omtch_vs_exp", "stage": 1, "arm": "omtch"}),
            compare(info, m, (q_close, None), st[("omtch", "MT")]["s2"],
                    {**meta, "comparison": "vs_close", "stage": 2, "arm": "omtch"}, realise=True),
            compare(info, m, (q_close, None), st[("exp", "MT")]["s2"],
                    {**meta, "comparison": "vs_close", "stage": 2, "arm": "exp"}, realise=True),
            compare(info, m, st[("nmt", "MT")]["s1"], st[("nmtch", "MT")]["s1"],
                    {**meta, "comparison": "nmtch_vs_nmt", "stage": 1, "arm": "nmtch"}),
            compare(info, m, st[("nmt", "MT")]["s1"], st[("nch", "MT")]["s1"],
                    {**meta, "comparison": "nch_vs_nmt", "stage": 1, "arm": "nch"}),
            compare(info, m, (q_elo, None), st[("nmt", "MT")]["s1"],
                    {**meta, "comparison": "vs_elo", "stage": 1, "arm": "nmt"}),
        ]

    def pb_ch(m, w, p):
        meta = {"part": 3, "scored": "CH", "window": w, "population": p}
        return [
            compare(info, m, st[("nch", "CH")]["s1"], st[("nmtch", "CH")]["s1"],
                    {**meta, "comparison": "nmtch_vs_nch", "stage": 1, "arm": "nmtch"}),
            compare(info, m, st[("nmt", "CH")]["s1"], st[("nch", "CH")]["s1"],
                    {**meta, "comparison": "nch_vs_nmt", "stage": 1, "arm": "nch"}),
            compare(info, m, st[("nmtch", "CH")]["s1"], st[("omtch", "CH")]["s1"],
                    {**meta, "comparison": "omtch_vs_nmtch", "stage": 1, "arm": "omtch"}),
            compare(info, m, (q_elo, None), st[("nch", "CH")]["s1"],
                    {**meta, "comparison": "vs_elo", "stage": 1, "arm": "nch"}),
            compare(info, m, (q_elo, None), st[("nmtch", "CH")]["s1"],
                    {**meta, "comparison": "vs_elo", "stage": 1, "arm": "nmtch"}),
        ]
    results += each(info, test & mt, WINDOWS_B, pb_mt)
    results += each(info, test & ch, WINDOWS_B, pb_ch)
    # log loss of every forecast on each population (2022-2024)
    lv = []
    for name, g in (("MT", mt), ("CH", ch)):
        for p in POPS:
            m = test & g & (True if p == "both" else (info["tour"] == p).to_numpy())
            y = info.loc[m, "y"].to_numpy()
            rec = {"scored": name, "population": p, "matches": int(m.sum()), "ll_coin": float(np.log(2)),
                   "ll_elo": float(TW.ll(q_elo[m], y).mean())}
            for arm in ("nmt", "nch", "nmtch", "omtch"):
                rec[f"ll_{arm}"] = float(TW.ll(st[(arm, name)]["s1"][0][m], y).mean())
            if name == "MT":
                rec["ll_close"] = float(TW.ll(q_close[m], y).mean())
                rec["ll_exp_s2"] = float(TW.ll(st[("exp", "MT")]["s2"][0][m], y).mean())
            lv.append(rec)
    return results, pd.DataFrame(lv), repro, params


def main() -> int:
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out = {"what": "event-levels study scores; + = the named arm better; mLL per match",
           "reading_rules": "data/studies/event_levels/reading_rules.md",
           "reading_rules_sha256": C.sha256_file(C.OUT / "reading_rules.md")}
    res = []
    levels = tuple(sys.argv[sys.argv.index("--levels") + 1].split(",")) if "--levels" in sys.argv else C.TARGETS
    if levels != C.TARGETS and only == "A":
        only = "A_" + "_".join(levels)                      # a partial run writes its own files
    if only is None or only.startswith("A"):
        ra, by_level, climbers, pa = score_a(experiment=only != "A14", levels=levels)
        res += ra
        by_level.to_csv(C.OUT / "by_level.csv", index=False)
        climbers.to_csv(C.OUT / "climbers.csv", index=False)
        pd.DataFrame(pa).to_csv(C.OUT / "params_a.csv", index=False)
    if only is None or only in ("A", "A14", "4B"):
        climbers_prices().to_csv(C.OUT / "climbers_prices.csv", index=False)
    if only in (None, "C"):
        rc, cc, pcp = score_c()
        res += rc
        cc.to_csv(C.OUT / "climbers_c.csv", index=False)
        pd.DataFrame(pcp).to_csv(C.OUT / "params_c.csv", index=False)
    if only in (None, "B"):
        rb, b_levels, repro, pb = score_b()
        res += rb
        b_levels.to_csv(C.OUT / "b_levels.csv", index=False)
        pd.DataFrame(pb).to_csv(C.OUT / "params_b.csv", index=False)
        out["reproduction_nmt"] = repro
    r = pd.DataFrame(res)
    if r.empty:
        return 0
    name = "results.csv" if only is None else f"results_{only}.csv"
    r.to_csv(C.OUT / name, index=False)
    out["model_frame_sha256"] = C.sha256_file(C.MODEL_FRAME)
    out["frame_sha256"] = C.sha256_file(C.FRAME)
    C.write_json(C.OUT / ("results.json" if only is None else f"results_{only}.json"), out)
    with pd.option_context("display.width", 250, "display.max_rows", 500, "display.max_columns", 30):
        head = r[r["window"].isin(["2020-2024", "2022-2024"]) & (r["population"] == "both")]
        cols = [c for c in ("part", "comparison", "level", "scored", "scored_level", "stage", "arm", "window",
                            "matches", "estimate", "lo", "hi", "reading", "c", "c_se") if c in head.columns]
        print(head[cols].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
