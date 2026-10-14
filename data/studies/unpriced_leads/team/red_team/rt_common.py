"""Red team (R2) of the unpriced-leads study: shared loaders and an independent fit (13 Oct 2026).

Independent of src/eda/unpriced_leads/screen.py on purpose: its own frame loader (seasons <= 2024 filtered inside the
parquet read, then asserted), its own input list, its own projection (scipy.linalg.lstsq), sklearn's logistic
regression for the estimates and its own cluster sandwich. Outcomes of seasons >= 2025 are never loaded: the only
loader that reads `a_won` is disc_frame(); outcome_free_frame() never reads it.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import linalg  # noqa: E402
from scipy.special import expit  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

ROOT = Path(__file__).resolve().parents[5]
INST = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
FRAME = INST / "model_frame.parquet"
REGISTRY = ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json"
OUT = Path(__file__).resolve().parent
CUT = pd.Timestamp("2025-01-01")
ORIGIN = pd.Timestamp("2010-01-04")
ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024)}
CONTEXT = {"tour", "surface", "level", "indoor", "best_of", "round"}


def model_inputs() -> list[str]:
    return [d["name"] for d in json.loads((INST / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]]


def diff_inputs() -> list[str]:
    """My own construction of the 48: every model input except the price and the six context inputs; the two surface
    pairs enter as one A - B each."""
    out = []
    for n in model_inputs():
        if n == "odds_logit" or n in CONTEXT:
            continue
        if n.endswith("_a") or n.endswith("_b"):
            stem = n[:-2]
            if stem not in out:
                out.append(stem)
            continue
        out.append(n)
    return out


def _finish(f: pd.DataFrame) -> pd.DataFrame:
    f = f[~f["debut_season"].astype(bool)].copy()
    f["match_id"] = f["match_id"].astype(str)
    for stem in ("surf_season", "surf_layoff"):
        f[f"in_{stem}"] = f[f"in_{stem}_a"] - f[f"in_{stem}_b"]
    p = np.clip(f["p_mkt"].to_numpy(float), 1e-6, 1 - 1e-6)
    f["L"] = np.log(p / (1 - p))
    f["block"] = ((pd.to_datetime(f["tournament_date"]) - ORIGIN).dt.days // 28).to_numpy()
    return f.reset_index(drop=True)


def frame_cols(extra=()) -> list[str]:
    raw = [n for n in model_inputs() if n != "odds_logit"]
    return ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "odds_input"] + \
        [f"in_{n}" for n in raw] + list(extra)


def disc_frame() -> pd.DataFrame:
    """Seasons <= 2024 with the result (filtered inside the read, then asserted)."""
    f = pd.read_parquet(FRAME, columns=frame_cols(["a_won"]),
                        filters=[("season", "<=", 2024), ("tournament_date", "<", CUT)])
    assert len(f) and f["season"].max() <= 2024 and pd.to_datetime(f["tournament_date"]).max() < CUT
    f = _finish(f)
    f["y"] = f["a_won"].astype(float)
    return f.drop(columns=["a_won"])


def outcome_free_frame() -> pd.DataFrame:
    """Every season, never the result column."""
    cols = frame_cols()
    assert "a_won" not in cols
    return _finish(pd.read_parquet(FRAME, columns=cols))


def values(frame: pd.DataFrame, path: str, col: str) -> np.ndarray:
    v = pd.read_parquet(ROOT / path, columns=["match_id", col]).astype({"match_id": str})
    return v.drop_duplicates("match_id").set_index("match_id")[col].reindex(frame["match_id"]).to_numpy(float)


def project(frame: pd.DataFrame, x: np.ndarray, coef: dict | None = None):
    """x minus its no-intercept least-squares projection on the 48 inputs (NaN -> 0), by tour, on rows with x."""
    names = diff_inputs()
    res = np.full(len(x), np.nan)
    fitted = {}
    for t in ("atp", "wta"):
        m = (frame["tour"] == t).to_numpy() & np.isfinite(x)
        X = np.nan_to_num(frame.loc[m, [f"in_{n}" for n in names]].to_numpy(float), nan=0.0)
        if coef is None:
            b = linalg.lstsq(X, x[m], lapack_driver="gelsd")[0]
        else:
            assert coef[t]["inputs"] == names, "input order differs"
            b = np.asarray(coef[t]["b"], float)
        fitted[t] = b
        res[m] = x[m] - X @ b
    return res, fitted


def blocks_of(dates) -> np.ndarray:
    return ((pd.to_datetime(pd.Series(dates)) - ORIGIN).dt.days // 28).to_numpy()


def logit_fit(y: np.ndarray, X: np.ndarray, blk: np.ndarray) -> dict:
    """No-intercept logistic regression by sklearn (lbfgs, no penalty), then my own CR1 sandwich over blocks."""
    m = LogisticRegression(C=np.inf, fit_intercept=False, solver="lbfgs", max_iter=5000, tol=1e-12)
    m.fit(X, y)
    b = m.coef_.ravel()
    p = expit(X @ b)
    Hm = (X * (p * (1 - p))[:, None]).T @ X
    Hi = np.linalg.inv(Hm)
    sc = X * (y - p)[:, None]
    lab, ix = np.unique(blk, return_inverse=True)
    S = np.zeros((len(lab), X.shape[1]))
    np.add.at(S, ix, sc)
    G = len(lab)
    V = G / (G - 1) * Hi @ (S.T @ S) @ Hi
    se = np.sqrt(np.diag(V))
    se_model = np.sqrt(np.diag(Hi))
    ll = float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return {"b": b, "se": se, "se_model": se_model, "G": G, "ll": ll, "grad_max": float(np.abs(X.T @ (y - p)).max())}


def base_cols(frame: pd.DataFrame, L: np.ndarray | None = None, curv: bool = True) -> list[np.ndarray]:
    L = frame["L"].to_numpy(float) if L is None else L
    atp = (frame["tour"] == "atp").to_numpy()
    cols = [np.where(atp, L, 0.0), np.where(~atp, L, 0.0)]
    if curv:
        cols += [np.where(atp, L * np.abs(L), 0.0), np.where(~atp, L * np.abs(L), 0.0)]
    return [c for c in cols if np.any(c != 0)]


def beta_z(frame: pd.DataFrame, s: np.ndarray, extra: list[np.ndarray] | None = None, curv: bool = True,
           L: np.ndarray | None = None) -> dict:
    """The registered fit: per-tour slope (and curvature) on L, plus optional extra base columns, plus the score scaled
    to unit RMS in the window. Returns beta, cluster SE, z, model SE, G, n."""
    s = np.asarray(s, float)
    rms = float(np.sqrt(np.mean(s ** 2)))
    if not rms > 0 or len(s) < 200:
        return {"beta": np.nan, "se": np.nan, "z": np.nan, "se_model": np.nan, "G": 0, "n": int(len(s)), "rms": rms,
                "ll": np.nan, "grad_max": np.nan}
    cols = base_cols(frame, L, curv) + (extra or []) + [s / rms]
    X = np.column_stack(cols)
    r = logit_fit(frame["y"].to_numpy(float), X, frame["block"].to_numpy())
    return {"beta": float(r["b"][-1]), "se": float(r["se"][-1]), "z": float(r["b"][-1] / r["se"][-1]),
            "se_model": float(r["se_model"][-1]), "G": r["G"], "n": int(len(s)), "rms": rms, "ll": r["ll"],
            "grad_max": r["grad_max"]}


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def scores(frame: pd.DataFrame, reg: dict, orth: bool = True, own_projection: bool = False):
    """(member scores dict, group scores dict, omnibus) by the registered recipe; with own_projection the projections
    and scales are refitted here on `frame` (for the re-derivation), else the registry's frozen ones are applied."""
    mem, grp = {}, {}
    for g in reg["groups"]:
        parts = []
        for m in g["members"]:
            x = values(frame, m["values"], m["column"])
            if orth:
                if own_projection:
                    x, _ = project(frame, x)
                else:
                    x, _ = project(frame, x, coef=m["orth_coef"])
            sc = np.ones(len(frame))
            for t in ("atp", "wta"):
                tm = (frame["tour"] == t).to_numpy()
                if own_projection:
                    sc[tm] = np.sqrt(np.nanmean(x[tm] ** 2))
                else:
                    sc[tm] = m["scale_orth" if orth else "scale_raw"][t]
            z = m["sign"] * x / sc
            z = np.where(np.isfinite(z), z, 0.0)
            mem[f"{g['id']}:{m['name']}"] = z
            parts.append(z)
        grp[g["id"]] = np.mean(np.column_stack(parts), axis=1)
    if own_projection:
        gs = {k: float(np.sqrt(np.mean(v ** 2))) for k, v in grp.items()}
    else:
        gs = {g["id"]: g["omnibus_scale_orth" if orth else "omnibus_scale_raw"] for g in reg["groups"]}
    omni = np.mean(np.column_stack([grp[k] / gs[k] for k in grp]), axis=1)
    return mem, grp, omni, gs
