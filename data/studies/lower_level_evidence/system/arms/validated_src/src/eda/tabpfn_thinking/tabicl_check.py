"""A free check of the paid result with a comparable local tabular foundation model: TabICL v2 (the UFC project's
free production vehicle), run on the GPU through the UFC project's `tabiclv2` conda env (read-only use of that
interpreter: C:/Users/zerom/miniforge3/envs/tabiclv2/python.exe; this study installs nothing there).

Three input sets, all trained on 2013-2021 and predicting 2022-2026 main-tour matches with odds, both orientations:

    full54      the exact upload the paid fit received (odds + 53 inputs): does a second foundation model reproduce
                TabPFN's gain on the same original features?
    short_orig  the 25 differences that have a repaired counterpart + the odds + the six context columns (32
                columns), original features, on the matches present in both feature sets
    short_rep   the same 32 columns from the feature-alpha audit's repaired rebuild, on the same matches: does the
                gain survive the chronology repair?

Modes:
    ./python.sh src/eda/tabpfn_thinking/tabicl_check.py --prepare      (tennis env) write the input sets
    "C:/Users/zerom/miniforge3/envs/tabiclv2/python.exe" src/eda/tabpfn_thinking/tabicl_check.py --run
                                                                         (tabiclv2 env, CUDA) fit and predict
    ./python.sh src/eda/tabpfn_thinking/tabicl_check.py --score        (tennis env) score against the odds, the
                                                                         flexible odds calibration and linear fits
Outputs in data/studies/tabpfn_thinking/tabicl/ and tabicl_check.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "tabpfn_thinking"
DIR = OUT / "tabicl"
SETS = ("full54", "short_orig", "short_rep")
TABICL = {"checkpoint_version": "tabicl-classifier-v2-20260212.ckpt", "n_estimators": 8, "softmax_temperature": 0.9,
          "batch_size": 8, "random_state": 42, "device": "cuda"}


def prepare() -> int:
    from src.eda.tabpfn_thinking import common as T
    from src.eda.tabpfn_thinking import repaired_check as RC
    DIR.mkdir(parents=True, exist_ok=True)
    # full54: the paid fit's own upload
    Xtr = pd.read_parquet(T.UPLOAD / "X_train.parquet")
    ytr = np.load(T.UPLOAD / "y_train.npy")
    Xq = pd.read_parquet(T.UPLOAD / "X_query.parquet")
    ids = pd.read_parquet(T.UPLOAD / "query_ids.parquet")
    _save("full54", Xtr, ytr, Xq, ids)
    # the shortlist on original and repaired features, identical matches
    O, R, info = RC.frames()
    cols = ["odds_logit"] + RC.DIFF25 + T.CONTEXT
    for name, F in (("short_orig", O), ("short_rep", R)):
        F = F.copy()
        F["in_odds_logit"] = F["mkt_logit"]
        has = np.isfinite(F["mkt_logit"].to_numpy())
        tr = ((F["split"] == "train").to_numpy() & has)
        te = ((F["split"] == "test").to_numpy() & has)
        X = pd.DataFrame({c: F[f"in_{c}"].to_numpy(dtype=float) for c in cols})
        X_te = X[te].reset_index(drop=True)
        q = pd.concat([X_te, T.flip(X_te)], ignore_index=True)
        mid = F.loc[te, "match_id"].to_numpy()
        _save(name, X[tr].reset_index(drop=True), F.loc[tr, "a_won"].astype("int64").to_numpy(), q,
              pd.DataFrame({"match_id": np.r_[mid, mid], "orientation": np.r_[np.zeros(len(mid), int), np.ones(len(mid), int)]}))
    (DIR / "prepare_info.json").write_text(json.dumps({"repaired_common": info, "short_columns": cols}, indent=1,
                                                      default=str), encoding="utf-8")
    print("prepared", {s: pd.read_parquet(DIR / f"{s}_X_train.parquet").shape for s in SETS})
    return 0


def _save(name, Xtr, ytr, Xq, ids):
    Xtr.to_parquet(DIR / f"{name}_X_train.parquet", index=False)
    np.save(DIR / f"{name}_y_train.npy", ytr)
    Xq.to_parquet(DIR / f"{name}_X_query.parquet", index=False)
    ids.to_parquet(DIR / f"{name}_query_ids.parquet", index=False)


def run() -> int:
    import torch  # noqa: F401  (import before sklearn-heavy modules: the Windows fbgemm DLL guard)
    from tabicl import TabICLClassifier
    meta = {"tabicl": TABICL, "runs": {}}
    for name in SETS:
        Xtr = pd.read_parquet(DIR / f"{name}_X_train.parquet")
        ytr = np.load(DIR / f"{name}_y_train.npy")
        Xq = pd.read_parquet(DIR / f"{name}_X_query.parquet")
        t0 = time.time()
        clf = TabICLClassifier(**TABICL)
        clf.fit(Xtr, ytr)
        proba = []
        for start in range(0, len(Xq), 8192):                    # bounded GPU memory
            proba.append(clf.predict_proba(Xq.iloc[start:start + 8192]))
        proba = np.vstack(proba)
        pos = list(clf.classes_).index(1)
        np.save(DIR / f"{name}_p_a.npy", proba[:, pos])
        meta["runs"][name] = {"train": list(Xtr.shape), "query": list(Xq.shape), "seconds": round(time.time() - t0, 1)}
        print(name, meta["runs"][name], flush=True)
    (DIR / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


def score() -> int:
    from scipy.special import expit, logit
    from src.eda.tabpfn_thinking import common as T
    from src.eda.tabpfn_thinking import diagnostics as D
    from src.eda.tabpfn_thinking import repaired_check as RC
    res = {"tabicl": json.loads((DIR / "run_meta.json").read_text(encoding="utf-8")), "sets": {}}
    O, R, _ = RC.frames()
    for name in SETS:
        ids = pd.read_parquet(DIR / f"{name}_query_ids.parquet")
        p = np.load(DIR / f"{name}_p_a.npy")
        n = len(ids) // 2
        P = pd.DataFrame({"match_id": ids["match_id"].to_numpy()[:n], "p_tabicl": T.symmetrize(p[:n], p[n:]),
                          "asym": np.abs(p[:n] - (1 - p[n:]))})
        if name == "full54":
            F = pd.read_parquet(T.OUT / "test_predictions.parquet")
            F = F.merge(P, on="match_id", how="inner")
            F["p_mkt"] = F["p_market_raw"]
            fr = pd.read_parquet(T.OUT / "frame.parquet", columns=["match_id", "in_odds_logit", "in_best_of"])
            F = F.merge(fr, on="match_id", how="left")
            F["p_odds_both"] = F["match_id"].map(D.calibrated("both")).to_numpy()
            pairs = [("market", "tabicl"), ("odds_both", "tabicl"), ("lr_mkt_all", "tabicl"), ("tabicl", "tabpfn"),
                     ("market", "tabpfn")]
        else:
            Fsrc = O if name == "short_orig" else R
            F = Fsrc[Fsrc["split"].isin(["train", "test"])].copy()
            F["in_odds_logit"] = F["mkt_logit"]
            has = np.isfinite(F["mkt_logit"].to_numpy())
            y = F["a_won"].to_numpy()
            # odds recalibrated and a linear fit on the same 25 differences, per tour, on the same training matches
            F["p_market"], F["p_lr_mkt_short"] = np.nan, np.nan
            for t in T.TOURS:
                tr = ((F["split"] == "train") & (F["tour"] == t)).to_numpy() & has
                te = ((F["split"] == "test") & (F["tour"] == t)).to_numpy() & has
                m = F["mkt_logit"].to_numpy()
                b, _ = T.fit_logistic(m[tr, None], y[tr])
                F.loc[te, "p_market"] = expit(m[te] * b[0])
                X = np.column_stack([F[f"in_{c}"].to_numpy(dtype=float) for c in RC.DIFF25])
                sd = np.nanstd(X[tr], axis=0)
                Xs = np.nan_to_num(X / np.where(sd > 0, sd, 1.0), nan=0.0)
                Z = np.column_stack([m, Xs])
                b, _ = T.fit_logistic(Z[tr], y[tr])
                F.loc[te, "p_lr_mkt_short"] = expit(Z[te] @ b)
            F = F[(F["split"] == "test").to_numpy() & has].merge(P, on="match_id", how="inner")
            pairs = [("market", "tabicl"), ("lr_mkt_short", "tabicl"), ("market", "lr_mkt_short")]
        rows = []
        for tname, sub in (("atp", (F["tour"] == "atp").to_numpy()), ("wta", (F["tour"] == "wta").to_numpy()),
                           ("both", np.ones(len(F), dtype=bool))):
            for b, m in pairs:
                pb, pm = F[f"p_{b}"].to_numpy(dtype=float), F[f"p_{m}"].to_numpy(dtype=float)
                ok = sub & np.isfinite(pb) & np.isfinite(pm)
                yy = F["a_won"].to_numpy()[ok]
                r = T.compare(T.ll(pb[ok], yy), T.ll(pm[ok], yy), F["tournament_date"].to_numpy()[ok])
                rows.append({"tour": tname, "base": b, "model": m, **r})
        res["sets"][name] = {"rows": rows, "asymmetry_mean_abs": float(P["asym"].mean()), "matches": int(len(F))}
        for r in rows:
            print(f"{name:10s} {r['tour']:4s} {r['base']:>13s} -> {r['model']:<13s} {r['gain']:+.2f} "
                  f"[{r['lo']:+.2f}, {r['hi']:+.2f}] n={r['n']}")
    T.write_json(T.OUT / "tabicl_check.json", res)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--score", action="store_true")
    a = ap.parse_args()
    return prepare() if a.prepare else run() if a.run else score()


if __name__ == "__main__":
    sys.exit(main())
