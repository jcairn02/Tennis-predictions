"""Step 6, fit: the instance's TabPFN-3.5 for the live matches' season, every live match at a grid of prices.

The decided inference path (model_rebuild/fits.py, serve_speed_tabpfn: its job_data, CONFIG and the local classifier:
8 estimators, softmax temperature 0.9, pretraining limits ignored): season Y trained on the instance frame's matches of
2013 .. Y - 1, predicted as stored and with A and B swapped (the flip of the instance's input kinds), the two
symmetrised; seeds 0-15, one fit each. A prediction costs about the same for 23 rows or 8,714 (the training rows are
processed at every call: daily_update_speed's measurement), so every live match goes in one call per seed at:
    GRID     91 log-odds prices, logit(0.05) .. logit(0.95) (daily_update_speed's grid: read back at a match's own price
             by linear interpolation in log-odds, within 0.0008 of a direct prediction on one seed)
    own      the match's own price (its in_odds_logit): the direct prediction, in the same call
A price outside the grid's range is not read from the curve: its own-price forecast stands, and a re-price there needs a
new call. Writes <run>/fit/seed<k>.npz (symmetrised grid and own-price probabilities) and fit.json. With
--direct-seeds, those seeds also predict the own-price rows alone in a separate call (the batch's effect, recorded).
Needs the tennis-tabpfn-local environment (./python_tabpfn_local.sh) and the card (waits as fits.py does: the other
processes checked once, the free memory before every seed).

By default each seed's classifier comes from its training cache on disk (dp_tabcache: built and saved the first time,
then loaded; the same numbers as the decided path, bit for bit, in seconds instead of ~45 s a seed). cache="off" runs
the decided path itself (fit_preprocessors: the training rows processed at this call).
"""
from __future__ import annotations

import json
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

GRID = np.linspace(np.log(0.05 / 0.95), np.log(0.95 / 0.05), 91)


def _mods():
    import sys
    if str(DC.REPO) not in sys.path:
        sys.path.insert(0, str(DC.REPO))
    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import arms as A
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.training_window import fits as TWF
    return FITS, A, C, TWF


def query_rows(live: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, int]:
    """Each live match at the 91 grid prices, then each at its own price (live's order)."""
    X = pd.DataFrame({c: live[f"in_{c}"].to_numpy(dtype="float64") for c in cols})
    n = len(X)
    grid = X.loc[X.index.repeat(len(GRID))].reset_index(drop=True)
    grid["odds_logit"] = np.tile(GRID, n)
    return pd.concat([grid, X], ignore_index=True), n


def interp(own_logit: np.ndarray, p_grid: np.ndarray) -> np.ndarray:
    """The grid's forecast read at each match's own price: linear in log-odds (NaN outside the grid)."""
    from scipy.special import expit, logit
    out = np.array([expit(np.interp(x, GRID, logit(p_grid[i]))) for i, x in enumerate(own_logit)])
    return np.where((own_logit >= GRID[0]) & (own_logit <= GRID[-1]), out, np.nan)


def season_jobs(run_dir: Path, instance: Path = DC.INSTANCE):
    """Per season of the run's live matches: (season, its live rows, X_train, y_train, the query rows as stored then
    swapped, the stored half's length, the matches), as the fit predicts them. The training rows are the instance's
    (current_best_model/training_rows.job_data): season Y on 2013 .. Y - 1, plus the season-Y matches its retrain
    admitted (the owner, 20 Oct 2026); without a record, the season rule."""
    FITS, A, C, TWF = _mods()
    from src.eda.current_best_model import training_rows as TR
    P = FITS.paths(instance)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    live = pd.read_parquet(run_dir / "live_frame.parquet")
    meta = pd.read_parquet(run_dir / "live_meta.parquet").astype({"match_id": str}).set_index("match_id")
    live["season"] = pd.to_datetime(meta.loc[live["match_id"].astype(str), "day"]).dt.year.to_numpy()
    for season, part in live.groupby("season"):
        X_train, y_train, _, _ = TR.job_data(frame, cols, int(season), instance)
        Xq, n = query_rows(part, cols)
        yield int(season), part, X_train, y_train, pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), len(Xq), n


def run(run_dir: Path, seeds: list[int], instance: Path = DC.INSTANCE, direct_seeds: list[int] = (),
        patience_s: int = 6 * 3600, cache: str = "use") -> dict:
    """cache: "use" (each seed's training cache, built when missing or stale), "rebuild" (every seed's rebuilt), "off"
    (the decided path)."""
    import torch
    FITS, A, C, TWF = _mods()
    from src.eda.tabpfn_local import runtime

    import dp_tabcache as TC
    if cache not in ("use", "rebuild", "off"):
        raise ValueError(f"cache: {cache}")
    P = FITS.paths(instance)
    cols = A.arm_inputs("model", P)
    out_dir = run_dir / "fit"
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"instance": str(instance), "frame_sha256": C.sha256_file(P.model_frame), "inputs": cols, "config": C.CONFIG,
           "grid": {"prices": len(GRID), "from_logit": float(GRID[0]), "to_logit": float(GRID[-1])},
           "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__}, "seasons": {}, "seeds": {},
           "path": "decided (fit_preprocessors)" if cache == "off" else "training cache (dp_tabcache)"}
    checked_processes = False
    from src.eda.current_best_model import training_rows as TR
    cut = TR.read_cutoff(instance)
    for season, part, X_train, y_train, X_all, k, n in season_jobs(run_dir, instance):
        own = cut if cut and int(cut["season"]) == int(season) else None
        rec["seasons"][int(season)] = {"matches": int(n), "train_rows": int(len(X_train)), "query_rows": int(len(X_all)),
                                       "training_cutoff": own["cutoff"] if own else None,
                                       "admitted": own["admitted"] if own else 0}
        for seed in seeds:
            path = out_dir / f"season{int(season)}_seed{seed}.npz"
            if path.exists():
                continue
            free = TWF.wait_for_card(patience_s=patience_s, processes=not checked_processes)
            checked_processes = True
            torch.cuda.reset_peak_memory_stats()
            t0 = time.monotonic()
            if cache == "off":
                clf = runtime.classifier(**C.CONFIG, random_state=seed)
                clf.fit(X_train, y_train)
                how: dict = {"how": "decided path"}
            else:
                clf, how = TC.get(X_train, y_train, int(season), seed, C.CONFIG, instance, rebuild=cache == "rebuild")
            t_fit = time.monotonic() - t0

            def proba(X):
                return clf.predict_proba(X)[:, 1] if cache == "off" else TC.predict(clf, X)
            p = proba(X_all)
            torch.cuda.synchronize()
            secs = time.monotonic() - t0
            if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(p).all():
                raise RuntimeError(f"seed {seed}: invalid probabilities")
            ps = C.symmetrize(p[:k], p[k:])
            payload = {"match_id": np.asarray(part["match_id"].astype(str).to_numpy(), dtype=str),
                       "grid": ps[:n * len(GRID)].reshape(n, -1), "own": ps[n * len(GRID):],
                       "own_logit": part["in_odds_logit"].to_numpy(dtype="float64")}
            info = {"seconds": round(secs, 1), "fit_seconds": round(t_fit, 2), "predict_seconds": round(secs - t_fit, 2),
                    "gpu_free_gb_before": round(free, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "checkpoint": str(clf.model_path), **how}
            if seed in direct_seeds:                      # the own-price rows alone, a separate call
                Xo = pd.concat([part[[f"in_{c}" for c in cols]].set_axis(cols, axis=1).astype("float64")
                                .reset_index(drop=True)], ignore_index=True)
                Xo_all = pd.concat([Xo, A.flip(Xo, P)], ignore_index=True)
                t1 = time.monotonic()
                po = proba(Xo_all)
                payload["own_separate"] = C.symmetrize(po[:n], po[n:])
                info["separate_seconds"] = round(time.monotonic() - t1, 1)
                info["separate_vs_in_batch_max_abs"] = float(np.max(np.abs(payload["own_separate"] - payload["own"])))
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, **payload)
            tmp.replace(path)
            DC.write_json(path.with_suffix(".json"), info)
            rec["seeds"][f"{int(season)}_{seed}"] = info
            DC.log(f"season {int(season)} seed {seed}: {secs:.0f} s ({n} matches x {len(GRID) + 1} prices x 2)")
            del clf
            torch.cuda.empty_cache()
    for f in sorted(out_dir.glob("season*_seed*.json")):          # every seed's record, also of an earlier call
        key = f.stem.replace("season", "").replace("_seed", "_")
        rec["seeds"].setdefault(key, DC.read_json(f))
    rec["summary"] = summarise(run_dir, seeds)
    DC.write_json(run_dir / "fit.json", rec)
    return rec


def load(run_dir: Path, seeds: list[int]) -> dict:
    """The seeds' symmetrised probabilities: {match_id, grid (seeds, n, 91), own (seeds, n), own_logit}."""
    files = sorted((run_dir / "fit").glob("season*_seed*.npz"))
    by = {}
    for f in files:
        seed = int(f.stem.split("_seed")[1])
        if seed not in seeds:
            continue
        with np.load(f, allow_pickle=False) as z:
            d = {k: z[k] for k in z.files}
        for i, mid in enumerate(d["match_id"]):
            by.setdefault(str(mid), {})[seed] = (d["grid"][i], d["own"][i], d["own_logit"][i],
                                                 d["own_separate"][i] if "own_separate" in d else np.nan)
    ids = sorted(by)
    missing = [m for m in ids if sorted(by[m]) != sorted(seeds)]
    if missing:
        raise RuntimeError(f"{len(missing)} matches lack some seeds' fits")
    grid = np.array([[by[m][s][0] for m in ids] for s in seeds])
    own = np.array([[by[m][s][1] for m in ids] for s in seeds])
    sep = np.array([[by[m][s][3] for m in ids] for s in seeds])
    return {"match_id": np.array(ids), "grid": grid, "own": own, "own_separate": sep,
            "own_logit": np.array([by[m][seeds[0]][2] for m in ids]), "seeds": list(seeds)}


def summarise(run_dir: Path, seeds: list[int]) -> dict:
    """The seed mean, the grid read back at each own price against the direct own-price forecast."""
    d = load(run_dir, seeds)
    pg, po = d["grid"].mean(axis=0), d["own"].mean(axis=0)
    back = interp(d["own_logit"], pg)
    inside = np.isfinite(back)
    steps = np.diff(pg, axis=1)
    out = {"matches": int(len(po)), "seeds": len(seeds), "inside_grid": int(inside.sum()),
           "interpolated_vs_own_max_abs": float(np.max(np.abs(back[inside] - po[inside]))) if inside.any() else None,
           "interpolated_vs_own_mean_abs": float(np.mean(np.abs(back[inside] - po[inside]))) if inside.any() else None,
           "falling_steps": int((steps < 0).sum()), "steps": int(steps.size)}
    if np.isfinite(d["own_separate"]).any():
        ok = np.isfinite(d["own_separate"])
        out["separate_vs_in_batch_max_abs"] = float(np.max(np.abs(d["own_separate"][ok] - d["own"][ok])))
    return out
