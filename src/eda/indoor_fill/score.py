"""The indoor fill's harm check: the lean review's arm A2 (the current best model, 57 inputs) against the same frame with
the indoor input filled (arm.py, fits.py), 2020-2024 (docs/studies/indoor_fill/README.md, "The test plan", written
before any fit ran).

Each arm goes through the decided recipe of src/eda/current_best_model/compare.py, reused unchanged, as the lean review's
scorer runs it: the seed mean of seeds 0-3; the per-tour calibration slopes and stage 2's b fitted walk-forward on
2019 .. Y - 1 (debut seasons out, b shrunk with tau 0.05, the reference's speed column); scored on 2020-2024. Paired log
loss in mLL per match, POSITIVE = THE FILL BETTER; the seed term paired by seed. Two yardsticks:
    O  Pinnacle's opening line fed in place of the close (lean_review/common.opening_prices; the declared primary)
    C  the close, as the model is trained
The rule, fixed before any fit: suggest adoption unless (1) both tours, both stages, at O or C, the 95% interval lies
below 0; (2) the same for the women; or (3) at O, both tours, the fill's realisation slope is below 0.9 while A2's is
not. Otherwise adopt, claiming no edge.

Reads results of seasons <= 2024 only. Writes data/studies/indoor_fill/scores.csv and score_summary.json.
Run: ./python.sh src/eda/indoor_fill/score.py
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

from src.eda.current_best_model import compare as K  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.indoor_fill import fits as FI  # noqa: E402
from src.eda.lean_review import common as L  # noqa: E402
from src.eda.lean_review import score as LS  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

THROUGH = 2024
OUT = FI.OUT
REALISATION_FLOOR = 0.9
ARMS = {"A2": L.paths("A2"), "fill": FI.paths()}


def open_table(P: C.Paths, fx: F.FrameIndex) -> pd.DataFrame:
    """Rows: the (O) matches of 2019-2024; columns: seed -> symmetrised P(A wins) fed the opening line, after
    lean_review/score.open_table's file checks (columns, training shape, td ids)."""
    cols = A.arm_inputs("model", P)
    parts = []
    for s in L.SEASONS:
        per = {}
        for k in L.SEEDS:
            path = P.local / f"model__{s}__seed{k}.npz"
            with np.load(path, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
                if meta.get("columns") != cols:
                    raise RuntimeError(f"{path}: columns differ from the arm's")
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


def decide(scores: pd.DataFrame, real: dict) -> dict:
    def row(yard, pop):
        r = scores[(scores["yardstick"] == yard) & (scores["group"] == "primary") & (scores["population"] == pop)
                   & (scores["stages"] == "both") & (scores["comparison"] == "fill vs A2")].iloc[0]
        return {k: float(r[k]) for k in ("estimate", "lo", "hi", "se", "p_better")} | {"matches": int(r["matches"])}

    checks = {f"{pop} {yard}": row(yard, pop) for pop in ("both tours", "women", "men") for yard in ("O", "C")}
    fails = [f"{k}: clearly worse" for k, v in checks.items() if not k.startswith("men") and v["hi"] < 0]
    ra, rf = real["both tours A2"]["slope"], real["both tours fill"]["slope"]
    if rf < REALISATION_FLOOR <= ra:
        fails.append(f"realisation at O: {rf:.3f} below {REALISATION_FLOOR} while A2's is {ra:.3f}")
    return {"readings": checks, "realisation_O": {"A2": ra, "fill": rf}, "fails": fails,
            "outcome": "adopt (claim no edge)" if not fails else "do not adopt: " + "; ".join(fails)}


def main() -> int:
    P0, P1 = ARMS["A2"], ARMS["fill"]
    frame0, frame1 = K.inputs_frame(P0), K.inputs_frame(P1)
    if not frame0.index.equals(frame1.index):
        raise SystemExit("the two frames hold different matches")
    y = K.outcomes(P0, THROUGH)
    info = K.scoring_info(frame0, frame1, y, K.outcomes(P1, THROUGH), THROUGH)
    fx = F.FrameIndex(frame0.reset_index()[["match_id", "season"]])
    op = L.opening_prices(frame0.reset_index())
    p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].astype(str).to_numpy())
    z = R.speed_column("reference")
    ids_O = info.index[np.isfinite(p_open.reindex(info.index).to_numpy())]
    tables = {}
    for arm, P in ARMS.items():
        pc = K.seed_table(P, frame0 if arm == "A2" else frame1, L.SEASONS).reindex(info.index)
        po = open_table(P, fx)
        if pc.isna().any().any() or not ids_O.isin(po.index).all():
            raise SystemExit(f"{arm}: forecasts missing")
        tables[arm] = {"C": pc, "O": po.reindex(ids_O)}
    infos = {"C": info, "O": info.loc[ids_O].assign(p_open=p_open.reindex(ids_O).to_numpy())}
    rows, coef, real = [], {}, {}
    for yard, inf in infos.items():
        models = {}
        for arm in ARMS:
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
            rows.append({"yardstick": yard, "group": group, "population": name, "stages": "both",
                         "comparison": "fill vs A2", **K.paired(inf, ids, fc2["A2"], fc2["fill"])})
            if group == "primary":
                rows.append({"yardstick": yard, "group": group, "population": name, "stages": "stage 1",
                             "comparison": "fill vs A2", **K.paired(inf, ids, fc1["A2"], fc1["fill"])})
                price = K.close_forecast(inf, price_col, L.TEST, ids)
                yy = inf.loc[ids, "y"].to_numpy(float)
                for arm in ARMS:
                    rows.append({"yardstick": yard, "group": group, "population": name, "stages": "both",
                                 "comparison": f"for scale: {arm} vs its calibrated price",
                                 **K.paired(inf, ids, price, fc2[arm], matched=False)})
                    real[f"{yard} {name} {arm}"] = LS.realisation(fc2[arm][0], inf.loc[ids, price_col].to_numpy(float),
                                                                  yy, inf.loc[ids, "block"].to_numpy())
    scores = pd.DataFrame(rows)
    scores.to_csv(OUT / "scores.csv", index=False)
    decision = decide(scores, {k[2:]: v for k, v in real.items() if k.startswith("O ")})
    prim = scores[scores["group"] == "primary"]
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "results_read_through": THROUGH, "scored_seasons": [L.TEST[0], L.TEST[-1]],
               "unit": "mLL per match; positive = the fill better; 95% intervals over four-week blocks plus the seed "
                       "term, paired by seed; p_better = the t CDF of estimate / se on blocks - 1 df",
               "decision": decision, "realisation": real,
               "coefficients_last_season": {k: v[str(L.TEST[-1])] for k, v in coef.items()},
               "primary_rows": [{k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in r.items()}
                                for r in prim.to_dict("records")]}
    C.write_json(OUT / "score_summary.json", summary)
    pd.set_option("display.width", 240)
    show = scores[~scores["comparison"].str.startswith("for scale")]
    print(show[["yardstick", "group", "population", "stages", "matches", "estimate", "lo", "hi", "p_better", "reading"]]
          .round(3).to_string(index=False))
    print(json.dumps({k: round(v["slope"], 3) for k, v in real.items()}, indent=0))
    print(f"outcome: {decision['outcome']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
