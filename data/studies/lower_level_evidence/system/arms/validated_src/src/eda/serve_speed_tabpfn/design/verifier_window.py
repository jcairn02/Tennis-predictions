"""R4 test verifier, part 6: everything score.py fits for season Y reads seasons < Y only (synthetic outcomes).

World: verifier_signs.full_world (every arm injected, synthetic outcomes, a planted speed term) on the real base
forecasts and the real features. For each test season Y and every arm, the scorer's season-Y quantities are computed:
    the calibration slopes (per tour), the closing price's slopes (S13), the nudge's parameters (S9: s_tour, b_MLE,
    SE, b_shrunk), the calibrated season-Y forecasts of every arm, and the nudge's season-Y forecast.
Then three perturbations, each in a fresh Scorer:
    B  only the outcomes of season Y are flipped                         -> all of the above must be bit-identical
    A  outcomes AND every arm's forecasts AND p_mkt of seasons >= Y are replaced by noise
                                                                         -> slopes, price slopes and nudge parameters
                                                                            must be bit-identical
    C  (positive control) only the outcomes of season Y - 1 are flipped -> each must change
Also the fit metadata: every fit file score.py reads that exists now, and this study's own fits: the stored training
window (train_seasons) and training shape against the expanding window 2013 .. Y - 1, and a refusal test (a fit whose
stored training shape is not the expanding window's is refused by forecasts.load_fit).

Writes data/studies/serve_speed_tabpfn/design/verifier_window.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_window.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_signs as VS  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_worlds as V  # noqa: E402

OUT = C.OUT / "design" / "verifier_window.json"
ARMS = VS.ARMS


def season_quantities(sc: S.Scorer, info: pd.DataFrame, Y: int) -> dict:
    ids_y = S.population_ids(info, "men", (Y,))
    out = {"slopes": {a: sc.slopes(a, Y) for a in ARMS}, "price_slopes": sc.price_slopes(Y),
           "nudge": S.nudge_parameters(sc, Y)}
    q = {}
    for a in ARMS:
        seeds = S.SEEDS16 if a in ("model", "spd") else S.SEEDS8
        q[a] = sc.forecast(a, seeds, (Y,), "td", "calibrated", ids_y)[0]
    out["q"] = q
    p = out["nudge"]
    eta16 = sc.bank.eta("model", S.SEEDS16, (Y,), "td").reindex(ids_y).to_numpy()
    out["nudge_forecast"] = expit(p["s_atp"] * eta16 + p["b_mle"] * info.loc[ids_y, "spd_f"].to_numpy(float))
    return out


def same(a: dict, b: dict, keys=("slopes", "price_slopes", "nudge", "q", "nudge_forecast")) -> dict:
    res = {}
    for k in keys:
        x, y = a[k], b[k]
        if k in ("q",):
            res[k] = all(np.array_equal(x[arm], y[arm]) for arm in x)
        elif k == "nudge_forecast":
            res[k] = bool(np.array_equal(x, y))
        else:
            res[k] = x == y
    return res


def perturbed_bank(bank: S.Bank, W: V.World, rng, from_season: int) -> S.Bank:
    """A copy of the injected world with every arm's forecasts of seasons >= from_season replaced by noise."""
    nb = S.Bank(W.P, W.fx, require_checks=False)
    for key, blocks in bank.injected.items():
        arm, s, k = key
        if s >= from_season:
            nb.injected[key] = {b: pd.Series(rng.uniform(0.02, 0.98, len(v)), index=v.index) for b, v in blocks.items()}
        else:
            nb.injected[key] = blocks
    return nb


def metadata_audit(W: V.World) -> dict:
    """Stored training windows of every fit score.py reads (that exists now) and of this study's own fits."""
    rows = []
    paths = {}
    for arm, need in sorted(S.needed_fits().items()):
        for season, seed in sorted(need):
            try:
                label, path = F.find_fit(arm, season, seed, W.P)
            except FileNotFoundError:
                continue
            paths[path] = (arm, season, seed, label)
    for path in sorted(W.P.local.rglob("*.npz")):
        if ".tmp" in path.name:
            continue
        arm, season, seed = path.stem.split("__")
        paths.setdefault(path, (arm, int(season), int(seed.replace("seed", "")),
                                "study_repro" if path.parent.name == "repro" else "study"))
    for path, (arm, season, seed, label) in paths.items():
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
        ts = meta.get("train_seasons")
        rows.append({"file": path.name, "folder": label, "arm": arm, "season": season, "seed": seed,
                     "has_train_seasons": ts is not None,
                     "train_seasons_ok": ts == [C.TRAIN_FROM, season - 1] if ts is not None else None,
                     "train_shape_ok": (meta.get("train_shape") or [None])[0] == W.fx.n_train[season],
                     "has_fingerprint": meta.get("fingerprint") is not None})
    t = pd.DataFrame(rows)
    by = t.groupby("folder").agg(files=("file", "size"), with_train_seasons=("has_train_seasons", "sum"),
                                 train_seasons_ok=("train_seasons_ok", lambda s: int((s == True).sum())),  # noqa: E712
                                 train_shape_ok=("train_shape_ok", "sum"),
                                 with_fingerprint=("has_fingerprint", "sum")).reset_index()
    return {"by_folder": by.to_dict(orient="records"),
            "bad": t[(t["train_seasons_ok"] == False) | (~t["train_shape_ok"])].to_dict(orient="records")}  # noqa: E712


def refusal_test(W: V.World) -> dict:
    """forecasts.load_fit refuses a fit whose stored training shape is not the expanding window's."""
    tmp = Path(tempfile.mkdtemp(prefix="ssp_verifier_window_"))
    label, src = F.find_fit("model", 2024, 5, W.P)
    with np.load(src, allow_pickle=False) as z:
        payload = {k: z[k] for k in z.files if k != "meta"}
        meta = json.loads(str(z["meta"]))
    out = {"source": f"{label}/{src.name}"}
    P = W.P.with_(local=tmp, fi_local=tmp / "none", race_local=tmp / "none")
    for name, change in (("train_shape_one_short", lambda m: {**m, "train_shape": [m["train_shape"][0] - 1,
                                                                                    m["train_shape"][1]]}),
                         ("unchanged_control", lambda m: m)):
        np.savez(tmp / "model__2024__seed5.npz", meta=np.asarray(json.dumps(change(meta))), **payload)
        try:
            F.load_fit("model", 2024, 5, W.fx, P, require_checks=False)
            out[name] = "loaded"
        except RuntimeError as e:
            out[name] = f"refused: {str(e)[-90:]}"
    out["passed"] = out["train_shape_one_short"].startswith("refused") and out["unchanged_control"] == "loaded"
    out["tmp"] = str(tmp)
    return out


def main() -> int:
    W = V.World()
    rng = np.random.default_rng(606)
    bank, info, y, _ = VS.full_world(W, rng, reverse_test=False)
    report = {"what": "calibration, close calibration and nudge read seasons < Y only (synthetic outcomes, injected "
                      "forecasts); fit metadata", "seasons": {}}
    ok_all = True
    for Y in S.TEST:
        base = season_quantities(S.Scorer(bank, info, y), info, Y)
        season = info["season"].to_numpy()
        yB = y.copy()
        yB[season == Y] = 1 - yB[season == Y]
        qB = season_quantities(S.Scorer(bank, info, yB), info, Y)
        yA = y.copy()
        late = season >= Y
        yA[late] = (rng.random(late.sum()) < 0.5).astype(float)
        infoA = info.copy()
        infoA.loc[late, "p_mkt"] = rng.uniform(0.05, 0.95, late.sum())
        scA = S.Scorer(perturbed_bank(bank, W, rng, Y), infoA, yA)
        qA = {"slopes": {a: scA.slopes(a, Y) for a in ARMS}, "price_slopes": scA.price_slopes(Y),
              "nudge": S.nudge_parameters(scA, Y)}
        yC = y.copy()
        yC[season == Y - 1] = 1 - yC[season == Y - 1]
        qC = season_quantities(S.Scorer(bank, info, yC), info, Y)
        rB = same(base, qB)
        rA = same(base, qA, keys=("slopes", "price_slopes", "nudge"))
        rC = {k: not v for k, v in same(base, qC).items()}
        ok = all(rB.values()) and all(rA.values()) and all(rC.values())
        ok_all &= ok
        report["seasons"][str(Y)] = {
            "B_outcomes_of_Y_flipped_unchanged": rB, "A_outcomes_forecasts_prices_of_ge_Y_noised_unchanged": rA,
            "C_outcomes_of_Y_minus_1_flipped_changed": rC, "passed": ok,
            "slopes_model": base["slopes"]["model"], "slopes_model_after_C": qC["slopes"]["model"],
            "nudge_b_mle": base["nudge"]["b_mle"], "nudge_b_mle_after_C": qC["nudge"]["b_mle"]}
    report["fit_metadata"] = metadata_audit(W)
    report["refusal_test"] = refusal_test(W)
    report["passed"] = bool(ok_all and report["refusal_test"]["passed"] and not report["fit_metadata"]["bad"])
    C.write_json(OUT, report)
    print(json.dumps(report, indent=1, default=str)[:6000])
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
