"""The lean review's T2 scorer: the IOS 2x2 at Pinnacle's opening line (O, the declared primary) and at the
Pinnacle-first close (C), 2020-2024 (docs/studies/lean_review/README.md, "The test plan" and "Settled before any fit
ran").

Each arm and yardstick goes through the decided recipe of src/eda/current_best_model/compare.py, reused unchanged: the
seed mean of seeds 0-3, the per-tour calibration slopes and stage 2's b fitted walk-forward on 2019 .. Y - 1 (debut
seasons out, b shrunk with tau 0.05; the reference's speed column), scored on 2020-2024; paired log loss in mLL per
match, POSITIVE = THE SECOND-NAMED ARM (the one without the dropped inputs) BETTER; the seed term paired by seed. At (O)
the calibration and stage 2 are fitted on the (O) matches' opening-fed forecasts.

The rule (fixed before any fit ran): removal X qualifies if B * est_X + c_X > 0 at (O), both tours, with
B = tau^2 / (tau^2 + SE^2); vetoed if at (C) est < -0.1 with P(better) <= 0.1; "both" first, then the single removal
with the larger B * est + c, else neither. Outcomes are proposals; the owner decides.

Refuses to run unless fits.py --repro passed. Reads results of seasons <= 2024 only.

Writes data/studies/lean_review/t2_scores.csv and t2_summary.json.
Run: ./python.sh src/eda/lean_review/score.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as K  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.lean_review import common as L  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

THROUGH = 2024
RULES = {"both": ("A3", 0.10, 0.06), "profile": ("A1", 0.10, 0.05), "short": ("A2", 0.03, 0.01)}
VETO_EST, VETO_P = -0.10, 0.10
PAIRS = [("A1 vs A0", "A0", "A1"), ("A2 vs A0", "A0", "A2"), ("A3 vs A0", "A0", "A3"),
         ("A3 vs A1", "A1", "A3"), ("A3 vs A2", "A2", "A3")]


def open_table(arm: str, fx: F.FrameIndex) -> pd.DataFrame:
    """Rows: the (O) matches of 2019-2024; columns: seed -> symmetrised P(A wins) fed the opening line. The file checks
    of serve_speed_tabpfn.forecasts.load_fit (columns, training shape, td ids)."""
    P = L.paths(arm)
    cols = A.arm_inputs("model", P)
    parts = []
    for s in L.SEASONS:
        per = {}
        for k in L.SEEDS:
            path = P.local / f"model__{s}__seed{k}.npz"
            with np.load(path, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
                if meta.get("columns") != cols or meta.get("lean_review_arm") != arm:
                    raise RuntimeError(f"{path}: columns or arm differ from {arm}'s")
                if list(meta.get("train_shape", [])) != [fx.n_train[s], len(cols)]:
                    raise RuntimeError(f"{path}: not the expanding window's training shape")
                if not np.array_equal(z["ids_td"].astype(str), fx.ids[s]):
                    raise RuntimeError(f"{path}: td ids are not the season's frame matches in order")
                p, ids = z["p_open"], z["ids_open"].astype(str)
            n = len(ids)
            if len(p) != 2 * n:
                raise RuntimeError(f"{path}: the open block is not stored + flipped")
            per[k] = pd.Series(C.symmetrize(p[:n], p[n:]), index=ids)
        parts.append(pd.DataFrame(per))
    return pd.concat(parts)


def logit_cluster(Z: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict:
    """Logistic regression without intercept, cluster-sandwich covariance (bet_timing/score.py's logit_cluster)."""
    beta, _ = C.fit_logistic(Z, y)
    p = 1 / (1 + np.exp(-(Z @ beta)))
    Hinv = np.linalg.inv((Z.T * (p * (1 - p))) @ Z)
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    S = np.zeros((g, Z.shape[1]))
    np.add.at(S, ix, Z * (y - p)[:, None])
    V = Hinv @ (S.T @ S) @ Hinv * (g / (g - 1))
    se = np.sqrt(np.diag(V))
    tq = student_t.ppf(0.975, g - 1)
    return {"beta": beta.tolist(), "se": se.tolist(), "lo": (beta - tq * se).tolist(), "hi": (beta + tq * se).tolist(),
            "n": int(len(y)), "clusters": int(g)}


def realisation(q: np.ndarray, p_price: np.ndarray, y: np.ndarray, block: np.ndarray) -> dict:
    """How much of the forecast's disagreement with the price comes true: the coefficient on logit q - logit p in a
    regression of the result on logit p and that difference (1 = right-sized, below 1 = over-reacting)."""
    lp, lq = C.lg(p_price), C.lg(q)
    r = logit_cluster(np.column_stack([lp, lq - lp]), y, block)
    return {"slope": r["beta"][1], "lo": r["lo"][1], "hi": r["hi"][1], "price_slope": r["beta"][0], "n": r["n"]}


def decide(primary_O: dict, primary_C: dict) -> dict:
    """The pre-declared rule. primary_O / primary_C: {removal: {"estimate", "se", "p_better"}} (both tours, both
    stages, + = without the removed inputs better). Returns each removal's terms and the proposal."""
    rows = {}
    for x, (arm, tau, c) in RULES.items():
        o, cl = primary_O[x], primary_C[x]
        B = tau ** 2 / (tau ** 2 + o["se"] ** 2)
        score = B * o["estimate"] + c
        veto = bool(cl["estimate"] < VETO_EST and cl["p_better"] <= VETO_P)
        rows[x] = {"arm": arm, "tau": tau, "c": c, "estimate_O": o["estimate"], "se_O": o["se"],
                   "p_better_O": o["p_better"], "B": B, "B_est_plus_c": score, "qualifies": bool(score > 0),
                   "estimate_C": cl["estimate"], "p_better_C": cl["p_better"], "vetoed": veto,
                   "eligible": bool(score > 0 and not veto)}
    if rows["both"]["eligible"]:
        proposal = "both"
    else:
        singles = [x for x in ("profile", "short") if rows[x]["eligible"]]
        proposal = max(singles, key=lambda x: rows[x]["B_est_plus_c"]) if singles else "neither"
    return {"removals": rows, "proposal": proposal}


def main() -> int:
    rp = L.OUT / "repro.json"
    if not rp.exists() or not C.read_json(rp).get("passed"):
        raise SystemExit("run fits.py --repro first: A0 must reproduce the instance's stored fits")
    P0 = L.paths("A0")
    frame = K.inputs_frame(P0)
    y = K.outcomes(P0, THROUGH)
    info = K.scoring_info(frame, frame, y, y, THROUGH)
    fx = F.FrameIndex(frame.reset_index()[["match_id", "season"]])
    op = L.opening_prices(frame.reset_index())
    p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].astype(str).to_numpy())
    z = R.speed_column("reference")
    tables = {}
    for arm in L.ARMS:
        pc = K.seed_table(L.paths(arm), frame, L.SEASONS).reindex(info.index)
        po = open_table(arm, fx)
        if pc.isna().any().any():
            raise SystemExit(f"{arm}: close-fed forecasts missing")
        tables[arm] = {"C": pc, "O": po}
    ids_O = info.index[np.isfinite(p_open.reindex(info.index).to_numpy())]
    for arm in L.ARMS:
        if not ids_O.isin(tables[arm]["O"].index).all():
            raise SystemExit(f"{arm}: opening-fed forecasts missing on (O) matches")
        tables[arm]["O"] = tables[arm]["O"].reindex(ids_O)
    infos = {"C": info, "O": info.loc[ids_O].assign(p_open=p_open.reindex(ids_O).to_numpy())}
    rows, coef, real = [], {}, {}
    for yard, inf in infos.items():
        models = {}
        for arm in L.ARMS:
            p = tables[arm][yard]
            eta = pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=p.index)
            models[arm] = (p, K.walk_forward(eta, inf, z, L.TEST), K.walk_forward(eta, inf, None, L.TEST))
            coef[f"{yard} {arm}"] = {str(Y): v for Y, v in models[arm][1].items()}
        price_col = "p_open" if yard == "O" else "p_ref"
        for group, name, mask in K.populations(inf, L.TEST):
            ids = inf.index[mask]
            if len(ids) == 0:
                continue
            fc2 = {a: K.forecasts(p, inf, par2, z, ids) for a, (p, par2, _) in models.items()}
            fc1 = {a: K.forecasts(p, inf, par1, None, ids) for a, (p, _, par1) in models.items()}
            for label, base, arm in PAIRS:
                rows.append({"yardstick": yard, "group": group, "population": name, "stages": "both",
                             "comparison": label, **K.paired(inf, ids, fc2[base], fc2[arm])})
                if group == "primary":
                    rows.append({"yardstick": yard, "group": group, "population": name, "stages": "stage 1",
                                 "comparison": label, **K.paired(inf, ids, fc1[base], fc1[arm])})
            if group == "primary":
                price = K.close_forecast(inf, price_col, L.TEST, ids)
                for arm in L.ARMS:
                    rows.append({"yardstick": yard, "group": group, "population": name, "stages": "both",
                                 "comparison": f"for scale: {arm} vs its calibrated price",
                                 **K.paired(inf, ids, price, fc2[arm], matched=False)})
                    if yard == "O":
                        yy = inf.loc[ids, "y"].to_numpy(float)
                        real[f"{name} {arm}"] = realisation(fc2[arm][0], inf.loc[ids, "p_open"].to_numpy(float), yy,
                                                            inf.loc[ids, "block"].to_numpy())
    scores = pd.DataFrame(rows)
    scores.to_csv(L.OUT / "t2_scores.csv", index=False)

    def primary(yard: str) -> dict:
        out = {}
        for x, (arm, _, _) in RULES.items():
            r = scores[(scores["yardstick"] == yard) & (scores["group"] == "primary") &
                       (scores["population"] == "both tours") & (scores["stages"] == "both") &
                       (scores["comparison"] == f"{arm} vs A0")].iloc[0]
            out[x] = {"estimate": float(r["estimate"]), "se": float(r["se"]), "p_better": float(r["p_better"]),
                      "lo": float(r["lo"]), "hi": float(r["hi"]), "matches": int(r["matches"])}
        return out

    pO, pC = primary("O"), primary("C")
    decision = decide(pO, pC)
    prim = scores[scores["group"] == "primary"]
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "results_read_through": THROUGH, "scored_seasons": [L.TEST[0], L.TEST[-1]],
               "unit": "mLL per match; positive = the second-named arm (the one without the dropped inputs) better; "
                       "intervals 95% over four-week blocks plus the seed term, paired by seed; p_better = the t CDF "
                       "of estimate / se on blocks - 1 df",
               "matches": {"C": int(len(infos["C"].index[~infos["C"]["debut"] & infos["C"]["season"].isin(L.TEST)])),
                           "O": int(len(infos["O"].index[~infos["O"]["debut"] & infos["O"]["season"].isin(L.TEST)]))},
               "primary_O": pO, "primary_C": pC, "decision": decision, "realisation_O": real,
               "coefficients_last_season": {k: v[str(L.TEST[-1])] for k, v in coef.items()},
               "primary_rows": [{k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in r.items()}
                                for r in prim.to_dict("records")]}
    C.write_json(L.OUT / "t2_summary.json", summary)
    pd.set_option("display.width", 240)
    show = prim[(prim["stages"] == "both") & ~prim["comparison"].str.startswith("for scale")]
    print(show[["yardstick", "population", "comparison", "matches", "estimate", "lo", "hi", "p_better", "reading"]]
          .round(3).to_string(index=False))
    for x, r in decision["removals"].items():
        print(f"{x:8s} ({r['arm']}): est_O {r['estimate_O']:+.3f} SE {r['se_O']:.3f} B {r['B']:.2f} "
              f"B*est+c {r['B_est_plus_c']:+.3f} qualifies {r['qualifies']} | est_C {r['estimate_C']:+.3f} "
              f"P {r['p_better_C']:.2f} vetoed {r['vetoed']}")
    print(f"proposal: {decision['proposal']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
