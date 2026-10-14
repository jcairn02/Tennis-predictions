"""The pre-registered comparison (docs/studies/ios_product_centring/preregistration.md): the centred arm against the
current best model, both stages. The only reader of match results is serve_speed_tabpfn.score.labels.

Refuses to start unless the pre-registration equals its recorded hash, gates G1, G2, G3, G4 and G6 passed and every
needed fit exists; refuses to overwrite results.json (one look). G5 is checked here first: the stage-2 fit of this
scorer reproduces the published L_weekly coefficients of 2024-2026 for the base to 1e-12.

Forecasts. Symmetrised P(A wins) per seed (seeds 0-3, both arms); eta = logit of the seed mean. Both stages:
logit q = s_tour,Y eta + b_Y z, z = spd_B_M1 for men (the L_weekly history column), 0 for women; s and b fitted for
season Y on 2019 .. Y - 1 from the arm's own seeds 0-3 mean, debut seasons out (serve_speed_tabpfn.score.
nudge_parameters with the arm as a parameter); b shrunk with tau = 0.05. Per seed: the same s, b on that seed's eta.
Stage 1 only (S5): the decided calibration (Scorer.slopes). S6: both arms fed Polymarket's 24-hour price (block
"early"), with their td-fitted s and b.

Score. 1000 x mean(LL_model - LL_cprod) in mLL: POSITIVE = THE CENTRED ARM HAS THE LOWER LOG LOSS (BETTER). The interval
combines the four-week-block SE with both arms' seed variance (serve_speed_tabpfn.score.paired_stats); t on G - 1. S7
(context): each arm against the closing price recalibrated the decided way, block-only interval, positive = the arm
better than the close.

Writes data/studies/ios_product_centring/results.json and results.csv.
Run: ./python.sh src/eda/ios_product_centring/score.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.ios_product_centring import fits as FT  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import score as SS  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import adjust as AD  # noqa: E402

SEEDS = (0, 1, 2, 3)
HIST = tuple(range(2019, 2027))
TEST = (2022, 2023, 2024, 2025, 2026)
ARMS = ("model", "cprod")
DIRECTION = "positive = the centred arm (cprod) has the lower log loss (better) than the current model"
GATES = ("g1_reference.json", "g2_products.json", "g3_probe.json", "g4_repro.json", "g6_symmetry.json")

# (id, population, seasons, kind): kind "both" = both stages, "stage1" = calibrated stage 1, "early" = both stages at
# Polymarket's 24-hour price
COMPARISONS = [("P", "both", (2025, 2026), "both"),
               ("S1", "both", (2022, 2023, 2024), "both"),
               ("S2", "both", TEST, "both")]
COMPARISONS += [(f"S3_{y}", "both", (y,), "both") for y in TEST]
COMPARISONS += [(f"S4_{p}_{w}", p, s, "both") for p in ("men", "women")
                for w, s in (("2025-2026", (2025, 2026)), ("2022-2026", TEST))]
COMPARISONS += [("S5", "both", (2025, 2026), "stage1"),
                ("S6", "both", (2025, 2026), "early")]


def load_arm_fits(bank: SS.Bank, fx) -> list[dict]:
    """Inject the centred arm's fits into the bank, after the serve-speed loader's checks (columns, training shape,
    td ids in the season's frame order)."""
    cols = SA.arm_inputs("model", SC.DEFAULT)
    prov = []
    for season in HIST:
        for seed in SEEDS:
            path = FT.out_path(FT.ARM, season, seed)
            with np.load(path, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
                if meta.get("columns") != cols:
                    raise RuntimeError(f"{path.name}: columns differ from the model's 58 inputs")
                if list(meta.get("train_shape", [])) != [fx.n_train[season], len(cols)]:
                    raise RuntimeError(f"{path.name}: training shape is not the expanding window's")
                if not np.array_equal(z["ids_td"].astype(str), fx.ids[season]):
                    raise RuntimeError(f"{path.name}: td ids are not the season's frame matches in order")
                if meta.get("frame_sha256") != C.sha256(FT.ARM_FRAME):
                    raise RuntimeError(f"{path.name}: fitted on another arm frame")
                blocks = {}
                for b in ("td", "early", "late"):
                    if f"p_{b}" in z.files:
                        p, ids = z[f"p_{b}"], z[f"ids_{b}"].astype(str)
                        k = len(ids)
                        blocks[b] = pd.Series(SC.symmetrize(p[:k], p[k:]), index=ids)
            bank.injected[(FT.ARM, season, seed)] = blocks
            prov.append({"season": season, "seed": seed, "file": path.name, "fingerprint": meta.get("fingerprint")})
    return prov


def nudge_parameters(sc: SS.Scorer, arm: str, season: int) -> dict:
    """serve_speed_tabpfn.score.nudge_parameters with the arm as a parameter (the same fit, line for line)."""
    hist = tuple(range(SC.CALIB_FROM, season))
    eta = sc.bank.eta(arm, SC.CAL_SEEDS, hist, "td")
    inf = sc.info.reindex(eta.index)
    if inf["season"].max() >= season:
        raise RuntimeError("nudge read a season >= Y")
    keep = ~inf["debut"].to_numpy(bool)
    e, atp = eta.to_numpy()[keep], (inf["tour"].to_numpy() == "atp")[keep]
    z = inf["spd_f"].to_numpy(float)[keep]
    yy = sc.y.reindex(eta.index[keep]).to_numpy(float)
    beta, se = SC.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0), z]), yy)
    b, s = float(beta[2]), float(se[2])
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "b_mle": b, "se_b": s,
            "b_shrunk": b * SC.TAU_NUDGE ** 2 / (SC.TAU_NUDGE ** 2 + s ** 2), "rows": int(keep.sum())}


def forecasts(sc: SS.Scorer, arm: str, ids, kind: str, params: dict) -> tuple[np.ndarray, np.ndarray]:
    """(seed-mean forecast, per-seed forecasts) of one arm on rows ids."""
    inf = sc.info.loc[ids]
    seasons = tuple(sorted(set(int(s) for s in inf["season"])))
    block = "early" if kind == "early" else "td"
    p = sc.bank.per_seed(arm, SEEDS, seasons, block).reindex(ids)
    if p.isna().to_numpy().any():
        raise RuntimeError(f"{arm} {block}: forecasts missing for {int(p.isna().any(axis=1).sum())} rows")
    eta, eta_k = SC.lg(p.mean(axis=1).to_numpy()), SC.lg(p.to_numpy())
    if kind == "stage1":
        s = sc.row_slopes(arm, ids)
        return expit(s * eta), expit(s[:, None] * eta_k)
    men = (inf["tour"].to_numpy() == "atp")
    s = np.array([params[arm][int(y)]["s_atp" if m else "s_wta"] for y, m in zip(inf["season"], men)])
    b = np.array([params[arm][int(y)]["b_shrunk"] for y in inf["season"]])
    z = np.where(men, inf["spd_f"].to_numpy(float), 0.0)
    return expit(s * eta + b * z), expit(s[:, None] * eta_k + (b * z)[:, None])


def population(sc: SS.Scorer, pop: str, seasons, kind: str):
    ids = SS.population_ids(sc.info, pop, seasons)
    if kind == "early":
        inf = sc.info.loc[ids]
        priced = np.isfinite(inf["p_early_a"].to_numpy(float)) & np.isfinite(inf["p_close_a"].to_numpy(float))
        ids = ids[inf["has_early"].to_numpy(bool) & inf["all_early"].to_numpy(bool) & priced]
        have = None
        for arm in ARMS:
            idx = sc.bank.per_seed(arm, SEEDS, tuple(seasons), "early").dropna().index
            have = idx if have is None else have.intersection(idx)
        ids = ids[ids.isin(have)]
    return ids


def compare(sc: SS.Scorer, cid: str, pop: str, seasons, kind: str, params: dict) -> dict:
    ids = population(sc, pop, seasons, kind)
    qb, qbk = forecasts(sc, "model", ids, kind, params)
    qa, qak = forecasts(sc, "cprod", ids, kind, params)
    y = sc.y.reindex(ids).to_numpy(float)
    if np.isnan(y).any():
        raise RuntimeError("outcomes missing")
    inf = sc.info.loc[ids]
    r = SS.paired_stats(SC.ll(qb, y), SC.ll(qa, y), SS.seed_loss(qbk, y), SS.seed_loss(qak, y),
                        inf["block"].to_numpy(), inf["week"].to_numpy())
    return {"cid": cid, "population": pop, "seasons": list(seasons), "kind": kind, "direction": DIRECTION, "unit": "mLL",
            "verdict": SS.verdict(r["lo"], r["hi"]), **r}


def against_close(sc: SS.Scorer, arm: str, seasons, params: dict) -> dict:
    ids = SS.population_ids(sc.info, "both", seasons)
    q, _ = forecasts(sc, arm, ids, "both", params)
    qm = sc.price_forecast(ids)
    y = sc.y.reindex(ids).to_numpy(float)
    inf = sc.info.loc[ids]
    r = SS.paired_stats(SC.ll(qm, y), SC.ll(q, y), np.zeros(1), np.zeros(1), inf["block"].to_numpy(),
                        inf["week"].to_numpy())
    return {"cid": f"S7_{arm}_{seasons[0]}-{seasons[-1]}", "arm": arm, "population": "both", "seasons": list(seasons),
            "kind": "both stages against the recalibrated close", "unit": "mLL",
            "direction": f"positive = {arm} (both stages) has the lower log loss (better) than the recalibrated close",
            "matches": r["matches"], "estimate": r["estimate"], "lo": r["lo_block_only"], "hi": r["hi_block_only"],
            "blocks": r["blocks"], "verdict": SS.verdict(r["lo_block_only"], r["hi_block_only"])}


def dry_run() -> int:
    """Every code path on DRAWN outcomes (fair coins; no result is read), with the base's fits standing in for any
    centred-arm fit not yet made. Prints only that it ran; writes nothing."""
    P = SC.DEFAULT
    fx = SS.frame_index(P)
    bank = SS.Bank(P, fx, require_checks=True)
    have = all(FT.out_path(FT.ARM, s, k).exists() for s in HIST for k in SEEDS)
    if have:
        load_arm_fits(bank, fx)
    else:
        for s in HIST:
            for k in SEEDS:
                bank.injected[(FT.ARM, s, k)] = bank.blocks("model", s, k)
    info = AD.with_history(AD.history_info(P), "L_weekly")
    ids = pd.read_parquet(P.model_frame, columns=["match_id", "season"])
    ids = ids[ids["season"].between(SC.CALIB_FROM, 2026)]["match_id"].astype(str).to_numpy()
    y = pd.Series(np.random.default_rng(0).integers(0, 2, len(ids)).astype(float), index=ids)
    sc = SS.Scorer(bank, info, y)
    params = {arm: {Y: nudge_parameters(sc, arm, Y) for Y in TEST} for arm in ARMS}
    rows = [compare(sc, cid, pop, seasons, kind, params) for cid, pop, seasons, kind in COMPARISONS]
    context = [against_close(sc, arm, w, params) for arm in ARMS for w in ((2025, 2026), TEST)]
    C.log(f"dry run OK on drawn outcomes ({'centred fits' if have else 'base fits standing in'}): "
          f"{len(rows)} comparisons, {len(context)} context rows, matches per comparison "
          f"{sorted({r['matches'] for r in rows})}")
    return 0


def main() -> int:
    if "--dry-run" in sys.argv:
        return dry_run()
    out_json, out_csv = C.OUT / "results.json", C.OUT / "results.csv"
    if out_json.exists():
        raise SystemExit("results.json exists: the comparison is read once (pre-registration); not overwritten")
    prereg = C.verify_prereg()
    gates = {g: bool((C.CHECKS / g).exists() and C.read_json(C.CHECKS / g).get("passed") is True) for g in GATES}
    if not all(gates.values()):
        raise SystemExit(f"gates not passed: {gates}")
    missing = [(s, k) for s in HIST for k in SEEDS if not FT.out_path(FT.ARM, s, k).exists()]
    if missing:
        raise SystemExit(f"centred-arm fits missing: {missing}")
    P = SC.DEFAULT
    fx = SS.frame_index(P)
    bank = SS.Bank(P, fx, require_checks=True)
    prov = load_arm_fits(bank, fx)
    info = AD.with_history(AD.history_info(P), "L_weekly")       # spd_B_M1 in the spd_f slot
    y = SS.labels(P)                                              # THE RESULTS (2019 - 28 Jul 2026)
    sc = SS.Scorer(bank, info, y)

    # G5: this fit reproduces the published stage-2 coefficients of the base
    params = {arm: {Y: nudge_parameters(sc, arm, Y) for Y in TEST} for arm in ARMS}
    published = AD.load_coefficients(P)["L_weekly"]
    g5_gaps = {f"{Y}_{k}": abs(params["model"][Y][k] - published[str(Y)][k])
               for Y in (2024, 2025, 2026) for k in ("s_atp", "s_wta", "b_mle", "se_b", "b_shrunk")}
    g5 = {"what": "G5: the scorer's stage-2 fit reproduces the published L_weekly coefficients of 2024-2026 for the base",
          "tolerance": C.EXACT, "max_abs_gap": max(g5_gaps.values()), "gaps": g5_gaps,
          "passed": max(g5_gaps.values()) <= C.EXACT}
    C.jdump(g5, C.CHECKS / "g5_stage2.json")
    if not g5["passed"]:
        raise SystemExit(f"G5 failed: {g5['max_abs_gap']}")

    rows = [compare(sc, cid, pop, seasons, kind, params) for cid, pop, seasons, kind in COMPARISONS]
    context = [against_close(sc, arm, w, params) for arm in ARMS for w in ((2025, 2026), TEST)]
    res = {"preregistration_sha256": prereg, "gates": {**gates, "g5_stage2.json": True},
           "direction": DIRECTION, "seeds": list(SEEDS), "comparisons": rows, "context": context,
           "stage2_parameters": {arm: {str(Y): v for Y, v in d.items()} for arm, d in params.items()},
           "fits": prov, "frames": {"model_frame_sha256": C.sha256(P.model_frame),
                                    "arm_frame_sha256": C.sha256(FT.ARM_FRAME)},
           "results_read": "a_won of the model frame's 2019 - 28 Jul 2026 matches (serve_speed_tabpfn.score.labels)"}
    C.jdump(res, out_json)
    keys = ["cid", "population", "seasons", "kind", "matches", "estimate", "lo", "hi", "se", "blocks", "verdict"]
    table = pd.DataFrame([{k: r.get(k) for k in keys} for r in rows + context])
    table.to_csv(out_csv, index=False)
    with pd.option_context("display.width", 220, "display.max_rows", 100):
        print(table.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
