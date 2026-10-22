"""Step 6b, thinking: TabPFN-3.5-Thinking on the hosted API beside the local model, uncalibrated (the owner, 20 Oct 2026;
docs/decisions/2026-10-20-thinking-beside-local.md).

With `run_day --thinking --spend-tokens` every live match is also predicted by TabPFN-3.5-Thinking, and the prediction
used is the two chances averaged 50/50 in log-odds (dp_predict.log_odds_mean). Thinking is the local model in everything but how it is
called and that its probabilities are used as the API gives them: the instance's 57 inputs; exactly the local fit's
training rows of the season (their train_sha256, dp_tabcache's recipe, must equal the season fit's); the same query
rows (dp_fit.season_jobs: each match at the 91 grid prices and its own, stored then swapped), symmetrised as the local
seeds are. Never the calibration slope; the predict step adds stage 2's serve-speed term to Thinking's chance
(dp_predict.speed_only; the owner, the evening of 20 Oct 2026: "should still move with the serve speed numbers ... just
not the calibration"). This step's forecasts are the API's own.

The paid parts run in the hosted API's environment (DC.PY_API, tennis-tabpfn) through the project's guard
(src/eda/tabpfn_thinking58/guard.py, tabpfn-client 0.6.0: the SDK's retry removed from the one POST):
    the season fit   ONE paid fit per instance and season (seed 0), made by the master pipeline (src/pipeline/thinking.py
                     and thinking_api.py) into DC.THINKING_FITS/<instance>/season<Y>/: this step only re-attaches to it
                     (load_model, no new fit)
    the day's call   ONE paid prediction per run and season: predict_slot.json is written immediately before the POST and,
                     once it exists, nothing is sent from that folder again (an attempt with an unknown outcome is never
                     repeated); the answers are saved the moment they arrive and only read back after
Three parts, each in its process:
    query  (tennis env)          <run>/thinking/query.npz, query.json: the rows of every season, each segment's hash
    send   (tennis-tabpfn env)   <run>/thinking/season<Y>/: account_preflight_*.json, predict_slot.json, predictions.npz,
                                 predict_complete.json (the served model's metadata, the tokens the account counted)
    read   (tennis env)          <run>/thinking/thinking.npz (match_id, grid (n, 91), own (n), own_logit), thinking.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

SCHEMA = "tennis-daily-thinking-v1"
SUBDIR = "thinking"
FIT_FILES = ("fit.json", "fit_complete.json", "fitted_model.json", "train.npz")


def folder(run_dir: Path) -> Path:
    return Path(run_dir) / SUBDIR


def fit_slot(instance: Path, season: int) -> Path:
    """Where the master pipeline keeps the instance's paid season fit (src/pipeline/thinking.folder)."""
    return DC.THINKING_FITS / Path(instance).name / f"season{int(season)}"


def fit_record(instance: Path, season: int) -> dict:
    slot = fit_slot(instance, season)
    missing = [n for n in FIT_FILES if not (slot / n).exists()]
    if missing:
        raise SystemExit(f"no TabPFN-3.5-Thinking season fit of {Path(instance).name} for {season} ({slot}: "
                         f"{', '.join(missing)} missing). The master pipeline makes it: tp.fit_seasons(model="
                         f"'tabpfn35_thinking', seasons='{season}', spend_tokens=True), or A4 with spend_tokens=True")
    return DC.read_json(slot / "fit.json")


def query_sha256(X: pd.DataFrame) -> str:
    """sha256 over a salt, the column names joined by NUL and X as little-endian float64 (one NaN pattern)."""
    h = hashlib.sha256(b"daily_prediction/thinking_query/v1")
    h.update("\x00".join(map(str, X.columns)).encode())
    v = np.asarray(X, dtype="float64")
    h.update(np.ascontiguousarray(np.where(np.isnan(v), np.nan, v), dtype="<f8").tobytes())
    return h.hexdigest()


def binding(seg: dict, fit: dict, config_sha256: str) -> dict:
    """What one season's saved answers are bound to: the query, the training rows, the fitted model, its settings."""
    return {"schema": SCHEMA, "query_sha256": seg["query_sha256"], "train_sha256": fit["train_sha256"],
            "fitted_train_set_id": fit["fitted_train_set_id"], "config_sha256": config_sha256,
            "model_path": fit["config"]["model_path"]}


# --- query (tennis env) -------------------------------------------------------------------------------------------------
def build_query(run_dir: Path, instance: Path) -> dict:
    """The run's live matches as the local fit queries them, one segment per season, each refused unless its training
    rows are the season fit's (train_sha256) and its columns the fit's, in its order."""
    import dp_fit as FT
    import dp_tabcache as TC
    parts, segments, start = [], [], 0
    for season, part, X_train, y_train, X_all, k, n in FT.season_jobs(run_dir, instance):
        fit = fit_record(instance, season)
        digest = TC.train_sha256(X_train, y_train)
        if digest != fit["train_sha256"]:
            raise SystemExit(f"season {season}: the instance's training rows are not the ones the Thinking fit was made on "
                             f"({digest[:12]} here, {fit['train_sha256'][:12]} in {fit_slot(instance, season)}): a "
                             "rebuilt instance needs its own fit")
        if list(map(str, X_all.columns)) != list(fit["columns"]):
            raise SystemExit(f"season {season}: the query's columns differ from the Thinking fit's")
        parts.append(X_all)
        segments.append({"season": int(season), "start": start, "rows": int(len(X_all)), "stored_rows": int(k),
                         "matches": int(n), "match_id": part["match_id"].astype(str).tolist(),
                         "own_logit": part["in_odds_logit"].astype("float64").tolist(), "train_sha256": digest,
                         "query_sha256": query_sha256(X_all), "fitted_train_set_id": fit["fitted_train_set_id"],
                         "fit_slot": str(fit_slot(instance, season))})
        start += len(X_all)
    if not parts:
        raise SystemExit("thinking: the run has no live match")
    X = pd.concat(parts, ignore_index=True)
    out = folder(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "query.tmp.npz"
    np.savez(tmp, X=X.to_numpy(dtype="float64"), columns=np.asarray(list(map(str, X.columns))))
    tmp.replace(out / "query.npz")
    rec = {"schema": SCHEMA, "made_at": DC.stamp(), "instance": str(instance), "rows": int(len(X)),
           "columns": list(map(str, X.columns)), "query_sha256": query_sha256(X),
           "grid": {"prices": int(len(FT.GRID)), "from_logit": float(FT.GRID[0]), "to_logit": float(FT.GRID[-1])},
           "segments": segments}
    DC.write_json(out / "query.json", rec)
    return {"rows": rec["rows"], "seasons": [s["season"] for s in segments], "matches": sum(s["matches"] for s in segments)}


def _query(run_dir: Path) -> tuple[dict, pd.DataFrame]:
    q = DC.read_json(folder(run_dir) / "query.json")
    with np.load(folder(run_dir) / "query.npz", allow_pickle=False) as z:
        X = pd.DataFrame(z["X"], columns=[str(c) for c in z["columns"]])
    if query_sha256(X) != q["query_sha256"]:
        raise SystemExit("thinking: query.npz does not match query.json's query_sha256")
    return q, X


def _segment(X: pd.DataFrame, seg: dict) -> pd.DataFrame:
    Xs = X.iloc[seg["start"]:seg["start"] + seg["rows"]].reset_index(drop=True)
    if query_sha256(Xs) != seg["query_sha256"]:
        raise SystemExit(f"thinking: season {seg['season']}'s rows do not match their hash")
    return Xs


# --- send (tennis-tabpfn env) -------------------------------------------------------------------------------------------
def api_env() -> dict:
    """The environment of the API worker: its own conda folders first on PATH, as `conda activate` sets them (a child
    inherits the tennis environment's folders, and numpy's maths library must be its own environment's)."""
    prefix = DC.PY_API.parent
    first = [prefix, prefix / "Library" / "mingw-w64" / "bin", prefix / "Library" / "usr" / "bin",
             prefix / "Library" / "bin", prefix / "Scripts", prefix / "bin"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    if sys.platform == "win32":
        env["PATH"] = os.pathsep.join([str(p) for p in first] + [os.environ.get("PATH", "")])
    return env


def send(run_dir: Path, spend_tokens: bool, backend_factory=None, log=DC.log) -> dict:
    """The run's one paid prediction per season on the season fit. Saved answers are read back, never sent again."""
    if str(DC.REPO) not in sys.path:
        sys.path.append(str(DC.REPO))
    from src.eda.tabpfn_thinking58 import guard as G
    q, X = _query(run_dir)
    done = {}
    for seg in q["segments"]:
        slot = Path(seg["fit_slot"])
        fit, complete = G._read(slot / "fit.json"), G._read(slot / "fit_complete.json")
        if (fit["train_sha256"], fit["fitted_train_set_id"]) != (seg["train_sha256"], seg["fitted_train_set_id"]):
            raise G.OnceOnlyError(f"season {seg['season']}: the query was built for another fit than {slot}'s")
        if complete["fit_state"]["fitted_train_set_id"] != fit["fitted_train_set_id"]:
            raise G.OnceOnlyError(f"{slot}: fit_complete.json and fit.json name different fits")
        Xs = _segment(X, seg)
        out = folder(run_dir) / f"season{seg['season']}"
        out.mkdir(parents=True, exist_ok=True)
        bind = binding(seg, fit, G._digest(fit["config"]))
        pred = out / "predictions.npz"
        if pred.exists():
            G.load_predictions(pred, bind, len(Xs))
            log(f"thinking season {seg['season']}: the saved answers read back; nothing sent")
            done[seg["season"]] = "read back"
            continue
        if (out / "predict_slot.json").exists():
            raise G.OnceOnlyError(f"{out}: this run's call was dispatched with an unknown outcome and is never repeated; "
                                  "inspect its receipts (a new run makes a new call)")
        if not spend_tokens:
            raise SystemExit("thinking: refused, the prediction is a paid call: pass --spend-tokens")
        backend = (backend_factory or G.LiveBackend)(dict(fit["config"]))
        account = backend.preflight()
        with np.load(slot / "train.npz", allow_pickle=False) as z:
            X_train = pd.DataFrame(z["X"], columns=[str(c) for c in z["columns"]])
        capacity = G.validate_account(account, X_train, Xs)
        G._publish_json(out / f"account_preflight_{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.json",
                        {**account, "capacity": capacity})
        backend.resume(slot / "fitted_model.json")
        usage_before = account.get("usage", {})

        def before():
            G._write_exclusive(out / "predict_slot.json", {**bind, "operation": "predict", "attempted_at": DC.stamp(),
                                                           "query_rows": int(len(Xs)),
                                                           "status": "DISPATCHED_OR_OUTCOME_UNKNOWN"})
        try:
            log(f"thinking season {seg['season']}: the one paid call, {len(Xs)} rows on fit {fit['fitted_train_set_id']}")
            result = backend.predict(Xs, complete["fit_state"], before)
            if not (out / "predict_slot.json").exists():
                raise G.OnceOnlyError("the backend bypassed the prediction guard")
            proba, _ = G._validate_probabilities(result, len(Xs))
            G._save_predictions(pred, proba, result["classes"], result.get("metadata", {}), bind)
        except Exception as exc:  # noqa: BLE001 - every failure after the slot is fail-closed
            raise G.OnceOnlyError(f"the prediction did not complete durably ({type(exc).__name__}: {exc}); inspect the "
                                  f"receipts in {out} before any further action") from None
        try:
            usage_after = backend.usage()
        except Exception:  # noqa: BLE001 - informational
            usage_after = {}
        used = None
        if isinstance(usage_before.get("daily_usage"), (int, float)) and isinstance(usage_after.get("daily_usage"),
                                                                                    (int, float)):
            used = usage_after["daily_usage"] - usage_before["daily_usage"]
        G._publish_json(out / "predict_complete.json", {**bind, "status": "COMPLETE", "completed_at": DC.stamp(),
                                                        "query_rows": int(len(Xs)),
                                                        "metadata": result.get("metadata", {}),
                                                        "tokens_used_daily_counter": used, "usage_after": usage_after})
        log(f"thinking season {seg['season']}: answered; {used} tokens on the account's daily counter")
        done[seg["season"]] = "sent"
    return done


# --- read (tennis env) --------------------------------------------------------------------------------------------------
def read(run_dir: Path) -> dict:
    """Each season's answers symmetrised as the local seeds are (dp_fit.run): thinking.npz and thinking.json."""
    if str(DC.REPO) not in sys.path:
        sys.path.append(str(DC.REPO))
    import dp_fit as FT
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.tabpfn_thinking58 import guard as G
    q = DC.read_json(folder(run_dir) / "query.json")
    ids, grids, owns, logits, seasons = [], [], [], [], {}
    for seg in q["segments"]:
        slot = Path(seg["fit_slot"])
        fit = G._read(slot / "fit.json")
        out = folder(run_dir) / f"season{seg['season']}"
        _, p1, meta, _ = G.load_predictions(out / "predictions.npz", binding(seg, fit, G._digest(fit["config"])),
                                            seg["rows"])
        k, n = seg["stored_rows"], seg["matches"]
        ps = C.symmetrize(p1[:k], p1[k:])
        ids += seg["match_id"]
        grids.append(ps[:n * len(FT.GRID)].reshape(n, -1))
        owns.append(ps[n * len(FT.GRID):])
        logits += seg["own_logit"]
        done = DC.read_json(out / "predict_complete.json") if (out / "predict_complete.json").exists() else {}
        seasons[str(seg["season"])] = {
            "fitted_train_set_id": fit["fitted_train_set_id"], "fit_slot": str(slot), "train_sha256": fit["train_sha256"],
            "config": fit["config"], "query_rows": seg["rows"], "matches": n,
            "served": {k2: meta.get(k2) for k2 in ("package_version", "billing_model_version", "execution_mode")}
            | {"weights": (meta.get("tabpfn_config") or {}).get("model_path")},
            "tokens_used_daily_counter": done.get("tokens_used_daily_counter")}
    grid, own = np.concatenate(grids), np.concatenate(owns)
    if not (np.isfinite(grid).all() and np.isfinite(own).all()):
        raise SystemExit("thinking: a non-finite probability")
    rec = {"schema": SCHEMA, "made_at": DC.stamp(), "matches": len(ids), "query_sha256": q["query_sha256"],
           "seasons": seasons, "symmetrised": True, "calibrated": False, "seeds": [0],
           "note": "TabPFN-3.5-Thinking's own probability, symmetrised over the two orientations; the predict step "
                   "adds stage 2's serve-speed term, never the calibration slope"}
    DC.write_json(folder(run_dir) / "thinking.json", rec)       # the record first: thinking.npz exists only beside it
    path = folder(run_dir) / "thinking.npz"
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, match_id=np.asarray(ids, dtype=str), grid=grid, own=own, own_logit=np.asarray(logits, dtype="float64"))
    tmp.replace(path)
    return {"matches": len(ids), "seasons": sorted(seasons),
            "tokens_used_daily_counter": sum(int(s["tokens_used_daily_counter"] or 0) for s in seasons.values())}


def load(run_dir: Path, ids) -> dict | None:
    """Thinking's symmetrised chances of side A for the run's matches in `ids`' order: own (n), grid (n, 91); None when
    the run has none (the step failed, or was not asked for)."""
    path = folder(run_dir) / "thinking.npz"
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    at = {str(m): i for i, m in enumerate(d["match_id"])}
    ids = [str(m) for m in ids]
    missing = [m for m in ids if m not in at]
    if missing:
        raise RuntimeError(f"thinking: {len(missing)} of the run's matches have no Thinking forecast (first {missing[0]})")
    pick = np.array([at[m] for m in ids], dtype=int)
    return {"own": d["own"][pick], "grid": d["grid"][pick], "own_logit": d["own_logit"][pick],
            "record": DC.read_json(folder(run_dir) / "thinking.json")}
