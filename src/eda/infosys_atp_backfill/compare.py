"""Does the ATP's decrypted backfill help the offline TabPFN model? The current best model, both stages, on the two
speed histories; and what the longer history says about the speed feature's future.

The model: the rebuilt local TabPFN-3.5 on 58 inputs (data/studies/model_rebuild/: season Y trained on 2013 .. Y - 1,
seeds 0-3, symmetrised) and the walk-forward serve-speed adjustment logit q = s_tour,Y eta + b_Y spd_L_B, with s and b
fitted by maximum likelihood on 2019 .. Y - 1 (debut seasons out) and b shrunk with tau 0.05 (model_rebuild/compare.py's
walk_forward, the decided fit). Two speed histories, everything else equal:
    current     spd_L_B on the corrected history (data/studies/model_rebuild/speed_columns_corrected.parquet)
    augmented   spd_L_B on the corrected history plus the ATP's own files of 2018 to Oct 2021 (columns.py)
Matches: every match both the rebuilt frame and the columns hold, 2019 .. --through, debut seasons out.

Results are read through --through only. The default, 2024, keeps 2025-2026 out, as the current best model's comparison
protocol does (src/eda/current_best_model/compare.py): they are the proposed clean holdout
(docs/studies/clean_holdout_rebuild/). --through 2026 reads them (the H-exposed part, events to 28 Jul 2026, which
earlier studies have read about 20 times; the speed columns end there, so no H-sealed match is read) and writes its own
files, labelled.

    gains       log loss in milli-log-loss per match, paired; positive = the second-named arm has the lower log loss
                (better). Intervals: serve_speed_tabpfn/score.paired_stats (4-week blocks plus the seeds' variance;
                since 9 Oct 2026 paired by seed through model_rebuild.compare.paired, every arm being the same fits;
                the unpaired intervals, as published, kept as lo_unpaired / hi_unpaired).
                Scored on 2022 .. --through both tours and men, and men by season from 2020.
    coefficients s_atp, s_wta, b (MLE, SE) and the shrunk b for every Y of 2020 .. --through + 1, on each history: the
                last is the coefficient the model would use in the next season.
    seasons     the information test season by season (serve_speed_tabpfn/score.encompassing: y on the base's
                log-odds with a slope per tour and season and a cubic, plus spd_L_B; per unit of spd_L_B; positive = the
                man whose 28-day speed form is higher wins more than the base says), men 2019 .. --through, each
                history; and pooled; with Cochran's Q across seasons (do the seasons share one effect?) and the
                random-effects (DerSimonian-Laird) mean and between-season SD
    walk        the adjustment's realised gain over the calibrated base in each season from 2020, coefficients from the
                seasons before only (2020 is fitted on 2019 alone, 2021 on 2019-20)
Writes data/studies/infosys_atp_backfill/comparison.json and comparison.csv (--through 2024), or
comparison_through_<Y>.json / .csv.
Run: ./python.sh src/eda/infosys_atp_backfill/compare.py [--through 2026]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.model_rebuild import compare as MR  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"
CURRENT = ROOT / "data" / "studies" / "model_rebuild" / "speed_columns_corrected.parquet"
AUGMENTED = OUT / "speed_columns_augmented.parquet"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
TEST = MR.TEST


def column(path: Path, col: str = "spd_L_B") -> pd.Series:
    z = pd.read_parquet(path, columns=["match_id", col]).astype({"match_id": str})
    return z.set_index("match_id")[col]


def walk(eta: pd.Series, info: pd.DataFrame, z: pd.Series | None, years) -> dict:
    """{Y: (s_atp, s_wta, b_shrunk, b_mle, se_b)} from 2019 .. Y - 1, debut out (model_rebuild.compare.walk_forward's
    fit, for any Y)."""
    out = {}
    for Y in years:
        hist = info.index[(info["season"] < Y) & ~info["debut"]]
        e = eta.reindex(hist).to_numpy()
        atp = (info.loc[hist, "tour"] == "atp").to_numpy()
        y = info.loc[hist, "y"].to_numpy(float)
        X = [np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]
        if z is not None:
            X.append(np.where(atp, z.reindex(hist).to_numpy(float), 0.0))
        beta, se = C.fit_logistic(np.column_stack(X), y)
        b = float(beta[2]) * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + float(se[2]) ** 2) if z is not None else 0.0
        out[Y] = (float(beta[0]), float(beta[1]), b, float(beta[2]) if z is not None else 0.0,
                  float(se[2]) if z is not None else 0.0)
    return out


def heterogeneity(rows: list[dict]) -> dict:
    """Cochran's Q over the single seasons' estimates, and the DerSimonian-Laird random-effects mean, its SE and the
    between-season SD (tau). A new season's effect is then about N(mean, tau^2 + se^2) (the predictive interval)."""
    from scipy.stats import chi2, t as student_t
    b = np.array([r["estimate"] for r in rows])
    se = np.array([r["se"] for r in rows])
    w = 1 / se ** 2
    fe = float((w * b).sum() / w.sum())
    q = float((w * (b - fe) ** 2).sum())
    df = len(b) - 1
    tau2 = max(0.0, (q - df) / (w.sum() - (w ** 2).sum() / w.sum()))
    wr = 1 / (se ** 2 + tau2)
    re = float((wr * b).sum() / wr.sum())
    re_se = float(np.sqrt(1 / wr.sum()))
    tq = float(student_t.ppf(0.975, df))
    half = tq * np.sqrt(tau2 + re_se ** 2)
    return {"seasons": [r["seasons"] for r in rows], "fixed_effect_mean": fe, "fixed_effect_se": float(np.sqrt(1 / w.sum())),
            "Q": q, "df": df, "p_heterogeneity": float(chi2.sf(q, df)), "I2": max(0.0, (q - df) / q) if q > 0 else 0.0,
            "tau_between_seasons": float(np.sqrt(tau2)), "random_effects_mean": re, "random_effects_se": re_se,
            "prediction_interval_next_season": [re - half, re + half],
            "share_of_new_seasons_below_0": float(student_t.cdf(-re / np.sqrt(tau2 + re_se ** 2), df))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--through", type=int, default=2024, help="the last season whose results are read")
    through = ap.parse_args().through
    if through > 2024:
        C.log(f"--through {through} reads 2025-2026 results (H-exposed): the proposed clean holdout; recorded in the "
              "study's report")
    fit_years = tuple(range(2020, through + 2))
    walk_years = tuple(range(2020, through + 1))
    test = tuple(Y for Y in TEST if Y <= through)
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt"]
    new = pd.read_parquet(MR.P_NEW.model_frame, columns=cols).astype({"match_id": str}).set_index("match_id")
    res = pd.read_parquet(MR.P_NEW.model_frame, columns=["match_id", "season", "a_won"],
                          filters=[("season", "<=", through)])          # no result after `through` is read
    if res["season"].max() > through:
        raise RuntimeError("a result after --through was read")
    a_won = pd.Series(res["a_won"].astype(float).to_numpy(), index=res["match_id"].astype(str).to_numpy())
    z_cur, z_aug = column(CURRENT), column(AUGMENTED)
    both = new.index.intersection(z_cur.index)
    both = both[new.loc[both, "season"].between(2019, through).to_numpy()]
    info = new.loc[both, ["tour", "season", "tournament_date", "debut_season", "p_mkt"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = a_won.reindex(both).to_numpy(float)
    if info["y"].isna().any():
        raise SystemExit("a result is missing")
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    s0 = pd.read_parquet(S0, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
    info = info.join(s0.set_index("match_id"), how="left")
    p = MR.seed_table(MR.P_NEW, require_checks=False).reindex(both)
    if p.isna().any().any():
        raise SystemExit("forecasts missing")
    eta = pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=both)
    par = {"base": walk(eta, info, None, fit_years), "current": walk(eta, info, z_cur, fit_years),
           "augmented": walk(eta, info, z_aug, fit_years)}
    ref = MR.walk_forward(eta, info, z_cur)                 # the decided fit reproduced on the test seasons
    assert all(np.allclose(par["current"][Y], ref[Y], rtol=0, atol=1e-10) for Y in test)
    zs = {"base": None, "current": z_cur, "augmented": z_aug}
    tag = f"{2022 % 100:02d}_{through % 100:02d}"
    pops = {f"both_20{tag}": info["season"].between(2022, through),
            f"men_20{tag}": (info["tour"] == "atp") & info["season"].between(2022, through)}
    if through >= 2025:
        pops[f"men_2024_{through % 100:02d}"] = (info["tour"] == "atp") & info["season"].between(2024, through)
    pops.update({f"men_{Y}": (info["tour"] == "atp") & (info["season"] == Y) for Y in walk_years})
    pops.update({f"both_{Y}": info["season"] == Y for Y in test})
    rows = []
    comparisons = [("the backfill: augmented against current, both stages", "current", "augmented"),
                   ("for scale: the adjustment on the current history against the calibrated base", "base", "current"),
                   ("for scale: the adjustment on the augmented history against the calibrated base", "base",
                    "augmented")]
    for name, pmask in pops.items():
        ids = info.index[pmask.to_numpy() & ~info["debut"].to_numpy()]
        if not len(ids):
            continue
        fc = {m: MR.forecasts(p, info, par[m], zs[m], ids) for m in par}
        for label, a, b in comparisons:
            rows.append({"population": name, "comparison": label, "base": a, "arm": b,
                         **MR.paired(info, ids, fc[a], fc[b])})
    # the information test, season by season and pooled (men; spd_L_B per unit)
    seasons = []
    men = info["tour"].eq("atp") & ~info["debut"]
    pooled = [(f"2019-{through}", tuple(range(2019, through + 1))), ("2019-2023", tuple(range(2019, 2024)))]
    if through >= 2025:
        pooled.append((f"2024-{through}", tuple(range(2024, through + 1))))
    for label, years in [(str(Y), (Y,)) for Y in range(2019, through + 1)] + pooled:
        ids = info.index[men.to_numpy() & info["season"].isin(years).to_numpy()]
        inf = info.loc[ids]
        y = inf["y"].to_numpy(float)
        for hname, z in (("current", z_cur), ("augmented", z_aug)):
            zz = z.reindex(ids).to_numpy(float)
            r = S.encompassing(inf, y, eta.reindex(ids).to_numpy(), zz, unit="log-odds per unit of spd_L_B")
            r.update({"seasons": label, "history": hname, "nonzero_share": float((np.abs(zz) > 1e-9).mean()),
                      "sd_z": float(np.std(zz))})
            seasons.append(r)
    het = {h: heterogeneity([r for r in seasons if r["history"] == h and r["seasons"].isdigit()])
           for h in ("current", "augmented")}
    # the next season: the coefficient the walk-forward fit gives it (b, fitted on 2019 .. through) against the
    # spread of season effects. For a season whose true effect is beta per unit, adding b z to the calibrated log-odds
    # changes the expected log loss by about k (b beta - b^2 / 2), k = mean p(1 - p) z^2 (second order); so the season
    # gains when beta > b / 2. beta ~ N(random-effects mean, tau^2 + se^2), the predictive distribution above.
    from scipy.stats import norm
    nxt = through + 1
    recent = info.index[men.to_numpy() & info["season"].between(through - 2, through).to_numpy()]
    for h, z in (("current", z_cur), ("augmented", z_aug)):
        inf = info.loc[recent]
        s_atp = np.array([par[h][int(Y)][0] for Y in inf["season"]])
        q = 1 / (1 + np.exp(-(s_atp * eta.reindex(recent).to_numpy())))
        k = float(np.mean(q * (1 - q) * z.reindex(recent).to_numpy(float) ** 2))
        b = par[h][nxt][2]
        mu, sd = het[h]["random_effects_mean"], float(np.hypot(het[h]["tau_between_seasons"],
                                                               het[h]["random_effects_se"]))
        het[h]["next_season"] = {
            "season": nxt, "b_shrunk": b, "k_mean_pq_z2": k, "k_from_seasons": [through - 2, through],
            "expected_gain_mll_at_mean_effect": 1000 * k * (b * mu - b * b / 2),
            "gain_mll_if_effect_at_prediction_bounds": [1000 * k * (b * x - b * b / 2)
                                                        for x in het[h]["prediction_interval_next_season"]],
            "probability_the_season_loses": float(norm.cdf((b / 2 - mu) / sd)),
            "note": "men; mLL per match, positive = the adjustment helps; normal approximation"}
    table = pd.DataFrame(rows)
    stem = "comparison" if through == 2024 else f"comparison_through_{through}"
    table.to_csv(OUT / f"{stem}.csv", index=False)
    meta = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
            "results_read_through": through,
            "holdout": ("none of the proposed holdout read" if through <= 2024 else
                        "reads 2025-2026 to 28 Jul 2026 (H-exposed of docs/studies/clean_holdout_rebuild/)"),
            "model": "the rebuilt current best model (data/studies/model_rebuild/fits, seeds 0-3)",
            "matches": int(len(both)), "matches_non_debut": int((~info["debut"]).sum()),
            "unit": "mLL per match; positive = the arm (second-named) has the lower log loss",
            "coefficients": {m: {str(Y): dict(zip(["s_atp", "s_wta", "b_shrunk", "b_mle", "se_b"], v))
                                 for Y, v in par_m.items()} for m, par_m in par.items()},
            "information_by_season": seasons, "heterogeneity_across_seasons": het,
            "rows": rows}
    (OUT / f"{stem}.json").write_text(json.dumps(meta, indent=1, default=float) + "\n", encoding="utf-8")
    show = table[table["population"].isin(list(pops)[:3])]
    print(show[["population", "comparison", "matches", "estimate", "lo", "hi"]].to_string(index=False))
    for m in ("current", "augmented"):
        print(m, {Y: tuple(round(x, 4) for x in v) for Y, v in par[m].items()})
    print(pd.DataFrame(seasons)[["seasons", "history", "matches", "estimate", "lo", "hi", "p_two_sided",
                                 "nonzero_share"]].to_string(index=False))
    print(json.dumps(het, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
