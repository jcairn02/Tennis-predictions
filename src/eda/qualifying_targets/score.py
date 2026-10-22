"""Step 8: the scores (preregistration.md, "Readings"). Reads the qualifying results of 2019-2026 and the instance's
main-draw results of 2019-2026.

Everything goes through compare.py's own arithmetic (src/eda/current_best_model/compare.py):
    * the seed table: each fit's block as stored and swapped, symmetrised (serve_speed_tabpfn/common.symmetrize), one
      column per seed 0-3;
    * stage 1: the seed mean's log-odds with one slope per tour, fitted walk-forward on the same population's matches of
      2019 .. Y - 1, debut seasons out (compare.walk_forward, z None); stage 2: plus b * spd_L (men; women 0), b shrunk
      (tau 0.05); a match without a speed value gets 0 (the "zero" rule);
    * the calibrated close: the closing price with one slope per tour fitted the same way (compare.close_forecast);
    * paired log loss: 1000 x mean(LL(base) - LL(arm)), positive = the arm better; the interval from 4-week blocks plus
      the seeds' variance (compare.paired; matched seeds when both sides are fits, unmatched against a price);
    * reading: "better" / "worse" when the 95% interval clears 0, else "unresolved", with P(better) (the t CDF).
Populations: seasons 2020-2026, debut seasons out.

    qual      every arm against the calibrated close (and the raw close): both tours (the primary for M1, both stages),
              men, women; Slam qualifying (GSQ) and tour qualifying (TQ); 2020-2024 and 2025-2026; each season; matches
              priced by Pinnacle and by BetOnline; arms against each other (M1 - M0, M1 - M2)
    betting   each arm's stage-2 forecast against the closing odds with the margin: the side with EV > 0 (and EV >= 0.02),
              1 unit; at Pinnacle's close and at BetOnline's close separately; ROI with a 2,000-draw bootstrap of
              4-week blocks
    market    question 1, on the matches of 2019-2025 that have both closes (qualifying: prices.py; main draw: the
              instance's odds_sources.parquet, OddsTrader's Pinnacle and BetOnline with the same 30-minute rule): each
              close's log loss (proportional; power as a check), BetOnline - Pinnacle, margins, calibration slopes
    harm      M1 against M0 on the main draw (M0 = the instance's own fits: fits.py's check), both stages, 2020-2026:
              harm = worse by more than 0.10 mLL with the whole interval below 0

Writes data/studies/qualifying_targets/scores.csv, betting.csv, market.json, harm.json, forecasts.parquet, summary.json.
Run: ./python.sh src/eda/qualifying_targets/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

FIT, TEST = C.FIT_SEASONS, C.TEST_SEASONS
PERIODS = {"2020-2024": (2020, 2021, 2022, 2023, 2024), "2025-2026": (2025, 2026)}
HARM_MLL = 0.10
N_BOOT = 2000
BOOT_SEED = 20261022


# ------------------------------------------------------------------------------------------------
# Loading

def seed_table(arm: str, block: str) -> pd.DataFrame:
    parts = []
    for s in FIT:
        per = {}
        for k in C.SEEDS:
            with np.load(C.LOCAL / f"{arm}__{s}__seed{k}.npz", allow_pickle=False) as z:
                p, ids = z[f"p_{block}"], z[f"ids_{block}"].astype(str)
            n = len(ids)
            if len(p) != 2 * n:
                raise SystemExit(f"{arm} {s} seed {k}: block {block} is not stored + swapped")
            per[k] = pd.Series(SC.symmetrize(p[:n], p[n:]), index=ids)
        parts.append(pd.DataFrame(per))
    t = pd.concat(parts)
    if t.index.duplicated().any() or t.isna().any().any():
        raise SystemExit(f"{arm} {block}: duplicate or missing forecasts")
    return t


def qual_info() -> tuple[pd.DataFrame, pd.Series]:
    f = pd.read_parquet(C.FRAME, columns=["match_id", "tour", "season", "tournament_date", "kind", "a_won",
                                          "debut_season"])
    pr = pd.read_parquet(C.PRICES)
    f = f.merge(pr, on="match_id", how="inner", validate="one_to_one")
    f = f[np.isfinite(f["p_close"].to_numpy(float)) & f["season"].between(min(FIT), max(FIT))].copy()
    info = f.set_index("match_id")
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = info["a_won"].astype(float)
    info["block"] = SC.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = SC.blocks(info["tournament_date"].to_numpy(), 7)
    sp = pd.read_parquet(C.OUT / "speed.parquet").set_index("match_id")
    z = sp["spd_L_B"].reindex(info.index).astype(float)
    z = pd.Series(np.where(info["tour"].to_numpy() == "wta", 0.0, np.nan_to_num(z.to_numpy(), nan=0.0)),
                  index=info.index)
    return info, z


def main_info() -> tuple[pd.DataFrame, pd.Series]:
    f = pd.read_parquet(C.INSTANCE / "model_frame.parquet", columns=["match_id", "tour", "season", "tournament_date",
                                                                     "debut_season", "a_won", "in_level", "p_mkt"])
    f["match_id"] = f["match_id"].astype(str)
    f = f[f["season"].between(min(FIT), max(FIT))]
    info = f.set_index("match_id")
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = info["a_won"].astype(float)
    info["block"] = SC.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = SC.blocks(info["tournament_date"].to_numpy(), 7)
    info["level"] = info["in_level"].map(CMP.LEVELS)
    sp = pd.read_parquet(C.INSTANCE / "stage2_speed_columns.parquet").astype({"match_id": str}).set_index("match_id")
    z = sp["spd_L_B"].reindex(info.index).astype(float)
    z = pd.Series(np.where(info["tour"].to_numpy() == "wta", 0.0, np.nan_to_num(z.to_numpy(), nan=0.0)),
                  index=info.index)
    return info, z


def model(p: pd.DataFrame, info: pd.DataFrame, z: pd.Series) -> dict:
    p = p.reindex(info.index)
    if p.isna().any().any():
        raise SystemExit(f"{int(p.isna().any(axis=1).sum())} matches without forecasts")
    eta = pd.Series(SC.lg(p.mean(axis=1).to_numpy()), index=p.index)
    return {"p": p, "z": z, "s1": CMP.walk_forward(eta, info, None, TEST), "s2": CMP.walk_forward(eta, info, z, TEST)}


def fc(m: dict, stage: str, info: pd.DataFrame, ids: pd.Index):
    return CMP.forecasts(m["p"], info, m[stage], m["z"] if stage == "s2" else None, ids)


# ------------------------------------------------------------------------------------------------
# Readings

def populations(info: pd.DataFrame) -> list[tuple[str, str, np.ndarray]]:
    keep = ~info["debut"].to_numpy() & info["season"].isin(TEST).to_numpy()
    tour = info["tour"].to_numpy()
    out = [("primary", "both tours", keep), ("tour", "men", keep & (tour == "atp")),
           ("tour", "women", keep & (tour == "wta"))]
    if "kind" in info.columns:
        out += [("kind", k, keep & (info["kind"].to_numpy() == k)) for k in ("TQ", "GSQ")]
        out += [("price", s, keep & (info["close_source"].to_numpy() == s)) for s in ("pinnacle", "betonline")]
    out += [("period", n, keep & info["season"].isin(s).to_numpy()) for n, s in PERIODS.items()]
    out += [("season", str(Y), ~info["debut"].to_numpy() & (info["season"].to_numpy() == Y)) for Y in TEST]
    return out


def row(info, ids, base_fc, arm_fc, matched, **labels) -> dict:
    if len(ids) < 2 or min(info.loc[ids, "block"].nunique(), info.loc[ids, "week"].nunique()) < 2:
        return {**labels, "matches": int(len(ids)), "reading": "too few blocks"}
    r = CMP.paired(info, ids, base_fc, arm_fc, matched=matched)
    return {**labels, **{k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "p_better", "reading", "blocks")}}


def qual_scores(info: pd.DataFrame, models: dict) -> pd.DataFrame:
    rows = []
    for group, name, mask in populations(info):
        ids = info.index[mask]
        if len(ids) == 0:
            continue
        closes = {"calibrated close": CMP.close_forecast(info, "p_close", TEST, ids)}
        raw = info.loc[ids, "p_close"].to_numpy(float)
        closes["raw close"] = (raw, raw[:, None])
        for arm, m in models.items():
            for stage, sname in (("s2", "both stages"), ("s1", "stage 1")):
                a = fc(m, stage, info, ids)
                for bname, b in closes.items():
                    rows.append(row(info, ids, b, a, False, comparison=f"{arm} vs {bname}", arm=arm, base=bname,
                                    stage=sname, group=group, population=name))
        for x, y in (("M1", "M0"), ("M1", "M2"), ("M0", "M2")):
            for stage, sname in (("s2", "both stages"), ("s1", "stage 1")):
                rows.append(row(info, ids, fc(models[y], stage, info, ids), fc(models[x], stage, info, ids), True,
                                comparison=f"{x} vs {y}", arm=x, base=y, stage=sname, group=group, population=name))
    return pd.DataFrame(rows)


def bets(info: pd.DataFrame, ids: pd.Index, q: np.ndarray, d_a: np.ndarray, d_b: np.ndarray, min_ev: float) -> dict:
    """1-unit bets on the side whose EV at these odds exceeds min_ev; ROI with a block bootstrap."""
    y = info.loc[ids, "y"].to_numpy(float)
    ok = np.isfinite(d_a) & np.isfinite(d_b)
    ev_a, ev_b = q * d_a - 1, (1 - q) * d_b - 1
    pick_a, pick_b = ok & (ev_a > min_ev), ok & (ev_b > min_ev)
    if (pick_a & pick_b).any():
        raise SystemExit("both sides +EV at once: the odds are not coherent")
    profit = np.where(pick_a, np.where(y == 1, d_a - 1, -1.0), 0.0) + np.where(pick_b, np.where(y == 0, d_b - 1, -1.0), 0.0)
    n = (pick_a | pick_b).astype(float)
    nb = int(n.sum())
    out = {"priced": int(ok.sum()), "bets": nb, "on_favourite": int(((pick_a & (d_a < d_b)) | (pick_b & (d_b < d_a))).sum()),
           "won": int(((pick_a & (y == 1)) | (pick_b & (y == 0))).sum()),
           "mean_odds": float(np.r_[d_a[pick_a], d_b[pick_b]].mean()) if nb else None,
           "model_ev": float(np.r_[ev_a[pick_a], ev_b[pick_b]].mean()) if nb else None,
           "profit": float(profit.sum()), "roi": float(profit.sum() / nb) if nb else None}
    if nb:
        blk = info.loc[ids, "block"].to_numpy()
        labels, ix = np.unique(blk, return_inverse=True)
        pb, nbk = np.bincount(ix, weights=profit), np.bincount(ix, weights=n)
        rng = np.random.default_rng(BOOT_SEED)
        w = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=N_BOOT)
        num, den = w @ pb, w @ nbk
        r = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        out.update({"roi_lo": float(np.nanquantile(r, 0.025)), "roi_hi": float(np.nanquantile(r, 0.975)),
                    "p_roi_positive": float(np.nanmean(r > 0)), "blocks": int(len(labels))})
    return out


def betting(info: pd.DataFrame, models: dict) -> pd.DataFrame:
    rows = []
    for group, name, mask in populations(info):
        if group not in ("primary", "tour", "kind", "period"):
            continue
        ids = info.index[mask]
        for arm, m in models.items():
            q, _ = fc(m, "s2", info, ids)
            for venue, (ca, cb) in (("pinnacle", ("pin_a", "pin_b")), ("betonline", ("bol_a", "bol_b"))):
                d_a, d_b = info.loc[ids, ca].to_numpy(float), info.loc[ids, cb].to_numpy(float)
                for min_ev in (0.0, 0.02):
                    rows.append({"arm": arm, "venue": venue, "min_ev": min_ev, "group": group, "population": name,
                                 **bets(info, ids, q, d_a, d_b, min_ev)})
    return pd.DataFrame(rows)


def power_devig(d_a, d_b) -> np.ndarray:
    """P(A) with the margin removed by the power method: (1/d_a)^k + (1/d_b)^k = 1."""
    ia, ib = 1 / np.asarray(d_a, float), 1 / np.asarray(d_b, float)
    lo, hi = np.full(len(ia), 0.5), np.full(len(ia), 3.0)
    for _ in range(60):
        k = (lo + hi) / 2
        s = ia ** k + ib ** k
        lo, hi = np.where(s > 1, k, lo), np.where(s > 1, hi, k)
    return ia ** ((lo + hi) / 2)


def market() -> dict:
    """Question 1: the two closes on the same matches, qualifying and main draw, 2019-2025."""
    f = pd.read_parquet(C.FRAME, columns=["match_id", "tour", "season", "tournament_date", "kind", "a_won"])
    q = f.merge(pd.read_parquet(C.PRICES), on="match_id", how="inner")
    q = q.rename(columns={"pin_a": "pa", "pin_b": "pb", "bol_a": "ba", "bol_b": "bb"})
    src = pd.read_parquet(C.INSTANCE / "odds_sources.parquet")
    src["match_id"] = src["match_id"].astype(str)
    late20 = src["after_ot20_min"].to_numpy(float) > C.LATE_MIN
    late8 = src["after_ot8_min"].to_numpy(float) > C.LATE_MIN
    m = pd.DataFrame({"match_id": src["match_id"], "tour": src["tour"], "season": src["season"],
                      "tournament_date": src["tournament_date"], "a_won": src["a_won"],
                      "pa": np.where(late20, np.nan, src["ot20_a"]), "pb": np.where(late20, np.nan, src["ot20_b"]),
                      "ba": np.where(late8, np.nan, src["ot8_a"]), "bb": np.where(late8, np.nan, src["ot8_b"])})
    out = {}
    for pop, d in (("qualifying", q), ("main draw", m)):
        d = d[d["season"].between(2019, 2025) & np.isfinite(d[["pa", "pb", "ba", "bb"]].to_numpy(float)).all(axis=1)]
        y = d["a_won"].astype(float).to_numpy()
        blk = OC.blocks(pd.to_datetime(d["tournament_date"]).to_numpy("datetime64[D]"))
        res = {"matches": int(len(d))}
        for method, dv in (("proportional", OC.devig), ("power", power_devig)):
            p_pin, p_bol = dv(d["pa"], d["pb"]), dv(d["ba"], d["bb"])
            ll_pin, ll_bol = OC.log_loss(p_pin, y), OC.log_loss(p_bol, y)
            res[method] = {"ll_pinnacle": float(ll_pin.mean()), "ll_betonline": float(ll_bol.mean()),
                           "betonline_minus_pinnacle_mll": OC.mean_ci(ll_bol - ll_pin, blk)}
            if method == "proportional":
                for tour in ("atp", "wta"):
                    t = (d["tour"] == tour).to_numpy()
                    res[f"slope_{tour}"] = {"pinnacle": OC.slope_ci(OC.lg(p_pin[t]), y[t], blk[t]),
                                            "betonline": OC.slope_ci(OC.lg(p_bol[t]), y[t], blk[t]),
                                            "matches": int(t.sum())}
                    res[f"betonline_minus_pinnacle_mll_{tour}"] = OC.mean_ci((ll_bol - ll_pin)[t], blk[t])
        over_pin = 1 / d["pa"].to_numpy(float) + 1 / d["pb"].to_numpy(float) - 1
        over_bol = 1 / d["ba"].to_numpy(float) + 1 / d["bb"].to_numpy(float) - 1
        res["margin_pct"] = {"pinnacle_mean": float(100 * over_pin.mean()), "pinnacle_median": float(100 * np.median(over_pin)),
                             "betonline_mean": float(100 * over_bol.mean()),
                             "betonline_median": float(100 * np.median(over_bol))}
        res["agreement_logodds_sd"] = float(np.std(OC.lg(OC.devig(d["ba"], d["bb"])) - OC.lg(OC.devig(d["pa"], d["pb"]))))
        out[pop] = res
    return out


def harm(minfo: pd.DataFrame, mmodels: dict) -> dict:
    keep = ~minfo["debut"].to_numpy() & minfo["season"].isin(TEST).to_numpy()
    tour = minfo["tour"].to_numpy()
    rows = []
    pops = [("both tours", keep), ("men", keep & (tour == "atp")), ("women", keep & (tour == "wta"))]
    pops += [(n, keep & minfo["season"].isin(s).to_numpy()) for n, s in PERIODS.items()]
    for name, mask in pops:
        ids = minfo.index[mask]
        for stage, sname in (("s2", "both stages"), ("s1", "stage 1")):
            rows.append(row(minfo, ids, fc(mmodels["M0"], stage, minfo, ids), fc(mmodels["M1"], stage, minfo, ids),
                            True, comparison="M1 vs M0 (main draw)", stage=sname, population=name))
    prim = next(r for r in rows if r["population"] == "both tours" and r["stage"] == "both stages")
    is_harm = bool(prim["estimate"] < -HARM_MLL and prim["hi"] < 0)
    return {"primary": prim, "harm_rule": f"worse by more than {HARM_MLL} mLL with the whole 95% interval below 0",
            "harm": is_harm, "rows": rows}


def main() -> int:
    info, z = qual_info()
    models = {arm: model(seed_table(arm, "qual"), info, z) for arm in C.ARMS}
    scores = qual_scores(info, models)
    scores.to_csv(C.OUT / "scores.csv", index=False)
    bt = betting(info, models)
    bt.to_csv(C.OUT / "betting.csv", index=False)
    keep = ~info["debut"].to_numpy() & info["season"].isin(TEST).to_numpy()
    ids = info.index[keep]
    fcst = pd.DataFrame(index=ids)
    for arm, m in models.items():
        for stage in ("s1", "s2"):
            fcst[f"q_{arm}_{stage}"] = fc(m, stage, info, ids)[0]
    fcst["q_close_cal"] = CMP.close_forecast(info, "p_close", TEST, ids)[0]
    fcst = fcst.join(info.loc[ids, ["tour", "season", "kind", "y", "p_close", "close_source"]])
    fcst.reset_index().to_parquet(C.OUT / "forecasts.parquet", index=False)
    mk = market()
    C.write_json(C.OUT / "market.json", mk)
    minfo, mz = main_info()
    mmodels = {arm: model(seed_table(arm, "main"), minfo, mz) for arm in ("M0", "M1")}
    hm = harm(minfo, mmodels)
    C.write_json(C.OUT / "harm.json", hm)
    prim = scores[(scores["comparison"] == "M1 vs calibrated close") & (scores["stage"] == "both stages")
                  & (scores["population"] == "both tours")].iloc[0].to_dict()
    summary = {"primary": prim, "harm": {k: hm[k] for k in ("primary", "harm")},
               "params_M1_s2": {str(k): v for k, v in models["M1"]["s2"].items()},
               "qualifying_scored": int(keep.sum()), "qualifying_in_info": int(len(info))}
    C.write_json(C.OUT / "summary.json", summary)
    C.log(f"primary: {prim}")
    C.log(f"harm: {hm['primary']} -> harm {hm['harm']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
