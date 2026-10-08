"""Score the race (plan: docs/studies/surface_rating_race/plan.md, fixed before any race fit).

    forecasts     per arm, season and block: the seed-mean (seeds 0-2) of the symmetrised local forecasts
    calibration   per arm and tour: a logistic slope without intercept of the result on the arm's log-odds over its
                  2019-2021 forecasts (debut seasons left out), applied to 2022-2026 and, for the arms with odds, to their
                  early (24 h) and late (30 min) Polymarket queries
    H1            ttt_off vs elo_off, both fed the 24-hour price (2025-2026; every match with that price, debut seasons
                  out; the clean event openers as a sensitivity)
    H2            ttt_off_noodds vs elo_off_noodds (2022-2026)
    H3            ttt_off vs elo_off at the close (2022-2026)
    H4            the move M = logit P(30 min) - logit P(24 h) on b = logit elo_off_noodds and Delta = logit ttt_off_noodds
                  - logit elo_off_noodds (calibrated; OLS without intercept, cluster-robust over four-week blocks); the
                  same for each arm against base and for ttt_off against ttt_blend (secondary)
    secondary     every arm vs base, ttt_off vs ttt_blend, ttt_blend vs elo_off, both_off vs the single arms, each arm
                  vs the price it was fed (the close recalibrated per fold; the 24-hour price raw and recalibrated by a
                  leave-one-block-out logistic fit); uncalibrated forecasts and the full population as sensitivities

Milli-log-loss, positive = the second-named forecast is better; 95% intervals over four-week blocks (calendar weeks and
seasons-as-samples, t on 4 df, alongside); spanning 0 = tie.
Writes data/studies/surface_rating_race/results.csv, results.json, predictions.parquet.
Run: ./python.sh src/eda/surface_rating_race/score.py [--partial]   (--partial: whatever seeds exist; for monitoring)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces.early_price_score import crossfit_stack, ols_cluster  # noqa: E402
from src.eda.surface_rating_race import arms as A  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

LOCAL = C.OUT / "local"
EPS = 1e-6
WITH_ODDS = ("base", "elo_off", "ttt_blend", "ttt_off", "both_off")
ARM_PAIRS = [("elo_off", "ttt_off"),                                            # the race (H1-H3)
             ("base", "elo_off"), ("base", "ttt_blend"), ("base", "ttt_off"), ("base", "both_off"),
             ("ttt_blend", "ttt_off"), ("elo_off", "ttt_blend"), ("elo_off", "both_off"), ("ttt_off", "both_off")]
KEY = ("milli-log-loss; positive = the second-named forecast has the lower log loss (better); 95% intervals over "
       "four-week blocks; spanning 0 = tie")


def lg(p):
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def load_arm(arm: str, partial: bool) -> tuple[dict, dict]:
    """{block: Series of seed-mean symmetrised P(A wins) by match id} and the seeds used per season."""
    parts, used = {}, {}
    for season in C.SEASONS:
        per = {}
        for seed in C.SEEDS:
            path = LOCAL / f"{arm}__{season}__seed{seed}.npz"
            if not path.exists():
                if partial:
                    continue
                raise FileNotFoundError(path)
            used.setdefault(season, []).append(seed)
            with np.load(path, allow_pickle=False) as z:
                for key in z.files:
                    if key.startswith("p_"):
                        b = key[2:]
                        p, ids = z[key], z[f"ids_{b}"]
                        k = len(ids)
                        per.setdefault(b, []).append(pd.Series(T.symmetrize(p[:k], p[k:]), index=ids.astype(str)))
        for b, lst in per.items():
            parts.setdefault(b, []).append(pd.concat(lst, axis=1).mean(axis=1))
    return {b: pd.concat(v) for b, v in parts.items()}, used


def market_recalibrated(frame: pd.DataFrame, season: int) -> np.ndarray:
    """The closing odds recalibrated per tour by one slope fitted on the fold's training matches (2013 .. season - 1),
    as the Elo-pieces study's scorer."""
    te_all = (frame["season"] == season).to_numpy()
    out = np.full(int(te_all.sum()), np.nan)
    for tour in C.TOURS:
        tr = (frame["season"].between(C.TRAIN_FROM, season - 1) & (frame["tour"] == tour)).to_numpy()
        te = te_all & (frame["tour"] == tour).to_numpy()
        beta, _ = T.fit_logistic(frame.loc[tr, ["x_odds_logit"]].to_numpy(), frame.loc[tr, "a_won"].to_numpy(float))
        out[(frame.loc[te_all, "tour"] == tour).to_numpy()] = expit(frame.loc[te, "x_odds_logit"].to_numpy() * beta[0])
    return out


def build(partial: bool) -> tuple[pd.DataFrame, dict, dict]:
    frame = pd.read_parquet(C.PIECES_FRAME)
    frame = frame[frame["season"].between(C.SEASONS[0], C.SEASONS[-1])].reset_index(drop=True)
    full = pd.read_parquet(C.PIECES_FRAME)
    F = frame[["match_id", "tour", "season", "a_won", "tournament_date", "debut_season", "p_mkt"]].copy()
    F["match_id"] = F["match_id"].astype(str)
    F = F.rename(columns={"p_mkt": "p_market_raw"})
    F["p_market"] = np.nan
    for season in C.SEASONS:
        F.loc[(F["season"] == season).to_numpy(), "p_market"] = market_recalibrated(full, season)
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a", "clean", "all_early"])
    ep["match_id"] = ep["match_id"].astype(str)
    F = F.merge(ep, on="match_id", how="left", validate="one_to_one")
    for c in ("has_early", "clean", "all_early"):
        F[c] = F[c].fillna(False).astype(bool)
    seeds_used, slopes = {}, {}
    y = F["a_won"].to_numpy(bool)
    calib = F["season"].between(*C.CALIB_YEARS).to_numpy() & ~F["debut_season"].to_numpy(bool)
    for arm in A.ARMS:
        if not any(LOCAL.glob(f"{arm}__*.npz")):
            continue
        blocks, used = load_arm(arm, partial)
        seeds_used[arm] = used
        for b, s in blocks.items():
            name = f"p_{arm}" if b == "td" else f"p_{arm}@{b}"
            F[f"{name}_raw"] = F["match_id"].map(s).to_numpy(dtype=float)
        x = lg(F[f"p_{arm}_raw"])
        for tour in C.TOURS:
            k = calib & (F["tour"] == tour).to_numpy() & np.isfinite(x)
            if k.sum() < 1000:
                continue
            beta, se = T.fit_logistic(x[k][:, None], y[k].astype(float))
            slopes[(arm, tour)] = (float(beta[0]), float(se[0]))
        if not all((arm, t) in slopes for t in C.TOURS):
            continue
        sl = np.where(F["tour"] == "atp", slopes[(arm, "atp")][0], slopes[(arm, "wta")][0])
        for col in [c for c in F.columns if c.startswith(f"p_{arm}") and c.endswith("_raw")
                    and c[2:-4].split("@")[0] == arm]:
            F[col[:-4]] = expit(sl * lg(F[col]))
    return F, seeds_used, slopes


def seasons_as_samples(gains: list[float]) -> dict:
    g = np.asarray(gains, dtype=float)
    k = len(g)
    if k < 2:
        return {}
    r = student_t.ppf(0.975, k - 1) * g.std(ddof=1) / np.sqrt(k)
    return {"s_mean": float(g.mean()), "s_lo": float(g.mean() - r), "s_hi": float(g.mean() + r),
            "s_positive": int((g > 0).sum()), "s_gains": json.dumps([round(float(x), 3) for x in g])}


def cmp_rows(F: pd.DataFrame, k: np.ndarray, pa: str, pb: str, label: dict, by_season: bool) -> dict | None:
    if pa not in F.columns or pb not in F.columns:
        return None
    g = F[k]
    ok = (np.isfinite(g[pa]) & np.isfinite(g[pb])).to_numpy()
    g = g[ok]
    if len(g) < 50:
        return None
    y = g["a_won"].to_numpy(bool)
    la, lb = T.ll(g[pa].to_numpy(), y), T.ll(g[pb].to_numpy(), y)
    c = T.compare(la, lb, g["tournament_date"].to_numpy())
    row = {**label, "base": pa, "model": pb, "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
           "week_lo": c["week_lo"], "week_hi": c["week_hi"], "blocks": c["blocks"],
           "ll_base": float(la.mean()), "ll_model": float(lb.mean())}
    if by_season:
        seasons = sorted(g["season"].unique())
        gains = [1000 * float((la - lb)[(g["season"] == s).to_numpy()].mean()) for s in seasons]
        row.update(seasons_as_samples(gains))
    return row


MOVE_PAIRS = [("elo_off", "ttt_off"),                                           # H4
              ("base", "elo_off"), ("base", "ttt_blend"), ("base", "ttt_off"), ("base", "both_off"),
              ("ttt_blend", "ttt_off")]                                          # the plan's secondary comparisons


def comparisons(F: pd.DataFrame, arm_pairs: list, with_odds: tuple, move_pairs: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every comparison of the given arm pairs (close, no odds, the 24-hour and 30-minute prices), each arm with odds
    against the price it was fed, and the move regressions of the given pairs. Adds the price columns to F."""
    debut = F["debut_season"].to_numpy(bool)
    test = F["season"].between(C.TEST_YEARS[0], C.TEST_YEARS[-1]).to_numpy()
    tours = {"atp": (F["tour"] == "atp").to_numpy(), "wta": (F["tour"] == "wta").to_numpy(),
             "both": np.ones(len(F), bool)}
    rows = []
    # close and no odds, 2022-2026
    for pop, pm in (("excl_debut", ~debut), ("all", np.ones(len(F), bool))):
        for tour, tm in tours.items():
            k = test & pm & tm
            for cal in ("", "_raw"):
                for setting, suffix in (("close", ""), ("no odds", "_noodds")):
                    pairs = [(f"p_{a}{suffix}{cal}", f"p_{b}{suffix}{cal}") for a, b in arm_pairs]
                    if setting == "close":
                        pairs += [("p_market", f"p_{a}{cal}") for a in with_odds]
                    for pa, pb in pairs:
                        r = cmp_rows(F, k, pa, pb, {"setting": setting, "calibrated": cal == "", "population": pop,
                                                    "tour": tour, "window": "2022-2026"}, by_season=True)
                        if r:
                            rows.append(r)
    # the Polymarket prices, 2025-2026: the arms fed the 24-hour (early) or 30-minute (late) price
    for pop, pm in (("early_all", F["all_early"].to_numpy() & ~debut), ("early_clean", F["clean"].to_numpy())):
        for tour, tm in tours.items():
            k = pm & tm & np.isfinite(F["p_early_a"]).to_numpy() & np.isfinite(F["p_close_a"]).to_numpy()
            g = F[k]
            blk = T.blocks(g["tournament_date"].to_numpy(), 28)
            y = g["a_won"].to_numpy(bool)
            for leg, col in (("early", "p_early_a"), ("late", "p_close_a")):
                F.loc[k, f"p_price_{leg}"] = g[col].to_numpy()
                F.loc[k, f"p_price_{leg}_recal"] = crossfit_stack(lg(g[col])[:, None], y, blk)
                for cal in ("", "_raw"):
                    pairs = [(f"p_{a}@{leg}{cal}", f"p_{b}@{leg}{cal}") for a, b in arm_pairs]
                    pairs += [(f"p_price_{leg}", f"p_{a}@{leg}{cal}") for a in with_odds]
                    pairs += [(f"p_price_{leg}_recal", f"p_{a}@{leg}{cal}") for a in with_odds]
                    for pa, pb in pairs:
                        r = cmp_rows(F, k, pa, pb, {"setting": f"{leg} price", "calibrated": cal == "",
                                                    "population": pop, "tour": tour, "window": "2025-2026"},
                                     by_season=False)
                        if r:
                            rows.append(r)
    R = pd.DataFrame(rows)
    # does the price move toward an arm's view (beyond its reference's) between 24 h and 30 minutes before the start?
    moves = []
    F["M"] = lg(F["p_close_a"]) - lg(F["p_early_a"])
    for ref, arm in move_pairs:
        if not {f"p_{ref}_noodds", f"p_{arm}_noodds"} <= set(F.columns):
            continue
        for cal in ("", "_raw"):
            b = lg(F[f"p_{ref}_noodds{cal}"])
            d = lg(F[f"p_{arm}_noodds{cal}"]) - b
            for pop, pm in (("early_clean", F["clean"].to_numpy()), ("early_all", F["all_early"].to_numpy() & ~debut)):
                for tour, tm in tours.items():
                    k = pm & tm & np.isfinite(F["M"]).to_numpy() & np.isfinite(b) & np.isfinite(d)
                    if k.sum() < 50:            # an arm without forecasts in 2025-2026 yet (partial runs)
                        continue
                    for cl, width in (("block", 28), ("week", 7)):
                        r = ols_cluster(F.loc[k, "M"].to_numpy(), np.column_stack([b[k], d[k]]),
                                        T.blocks(F.loc[k, "tournament_date"].to_numpy(), width))
                        moves.append({"reference": ref, "arm": arm, "calibrated": cal == "", "population": pop,
                                      "tour": tour, "clusters_by": cl, "matches": r["n"], "clusters": r["clusters"],
                                      "beta_b": r["beta"][0], "lo_b": r["lo"][0], "hi_b": r["hi"][0],
                                      "beta_Delta": r["beta"][1], "lo_Delta": r["lo"][1], "hi_Delta": r["hi"][1],
                                      "sd_Delta": float(np.std(d[k])), "corr_b_Delta": float(np.corrcoef(b[k], d[k])[0, 1])})
    return R, pd.DataFrame(moves)


def main() -> int:
    partial = "--partial" in sys.argv
    F, seeds_used, slopes = build(partial)
    R, M = comparisons(F, ARM_PAIRS, WITH_ODDS, MOVE_PAIRS)
    debut = F["debut_season"].to_numpy(bool)
    test = F["season"].between(C.TEST_YEARS[0], C.TEST_YEARS[-1]).to_numpy()
    R.to_csv(C.OUT / ("results_partial.csv" if partial else "results.csv"), index=False)
    M.to_csv(C.OUT / ("moves_partial.csv" if partial else "moves.csv"), index=False)
    keep = [c for c in F.columns if c.startswith("p_") or c in ("match_id", "tour", "season", "a_won",
                                                                 "tournament_date", "debut_season", "clean",
                                                                 "all_early", "has_early")]
    if not partial:
        F[keep].to_parquet(C.OUT / "predictions.parquet", index=False)
    C.write_json(C.OUT / ("results_partial.json" if partial else "results.json"), {
        "key": KEY, "partial": partial, "seeds_used": {a: {str(s): v for s, v in u.items()} for a, u in seeds_used.items()},
        "slopes_2019_2021": {f"{a}|{t}": {"slope": v[0], "se": v[1]} for (a, t), v in slopes.items()},
        "matches": {"test_excl_debut": int((test & ~debut).sum()), "early_all": int((F["all_early"] & ~F["debut_season"]).sum()),
                    "early_clean": int(F["clean"].sum())}})
    show = R[(R["population"].isin(["excl_debut", "early_all"])) & R["calibrated"]]
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print({f"{a}|{t}": round(v[0], 3) for (a, t), v in slopes.items()})
        print(show[["setting", "tour", "base", "model", "matches", "gain", "lo", "hi", "s_mean", "s_lo", "s_hi",
                    "s_positive"]].round(2).to_string(index=False))
        if len(M):
            print(M[(M["clusters_by"] == "block") & M["calibrated"]].drop(columns=["clusters_by", "calibrated"])
                  .round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
