"""The event-levels study's local TabPFN-3.5 fits: the plan, a CPU check, and the GPU runner (common.py has the arms).

Experiment A reads the model frame (seasons <= 2024, training_window's reader); experiment B the extended frame
(frame.py). Every fit has the decided settings (8 estimators, softmax temperature 0.9, pretraining limits ignored) and
predicts its query rows as stored and with A and B swapped (td; the scorer symmetrises). One fit at a time on the card,
waiting as training_window's runner waits (no other local-env process, 12 GB free). A finished fit is saved under
data/studies/event_levels/local/ and never refitted.

    ./python.sh src/eda/event_levels/fits.py --plan
    ./python.sh src/eda/event_levels/fits.py --check          # CPU: exp's and nmt's job data equal the stored fits'
    ./python_tabpfn_local.sh src/eda/event_levels/fits.py --run A [--arms own_GS,w25_GS] [--seasons 2019-2024]
    ./python_tabpfn_local.sh src/eda/event_levels/fits.py --run B [--arms nch]

--check relates no result: it compares shapes, columns, ids and (for A) the stored fingerprints.
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.training_window import common as TW  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402  (wait_for_card)

NAMES = TW.inputs()                                   # the 58 inputs in the model's order
NOODDS = [n for n in NAMES if n != "odds_logit"]


# ------------------------------------------------------------------------------------------------
# Frames and job data

def frame_a(labels: bool = True) -> pd.DataFrame:
    f = TW.load_frame(labels=labels)
    f["level_code"] = f["in_level"].to_numpy(dtype="float64")
    return f


def frame_b(labels: bool = True) -> pd.DataFrame:
    f = pd.read_parquet(C.FRAME)
    C.frame_seasons_ok(f)
    f = f[f["pop"].isin(["MT", "CH"])].reset_index(drop=True)
    if not labels:
        f = f.drop(columns=["a_won"])
    return f


def job_data_a(frame: pd.DataFrame, arm: str, season: int, seed: int):
    tr = C.train_mask_a(frame["season"].to_numpy(), frame["level_code"].to_numpy(), arm, season, seed)
    te = (frame["season"] == season).to_numpy()
    X = SA.matrix(frame, NAMES)
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, SA.flip(X_test)], ignore_index=True)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(), X_query,
            frame.loc[te, "match_id"].to_numpy(), tr)


def frame_c(labels: bool = True) -> pd.DataFrame:
    """The model frame (<= 2024) with low_share_diff: A's share of the previous 365 days' matches below the main tour
    (qualifying, Challenger, ITF) minus B's (blend.py's history.parquet; a count of each player's own earlier
    matches, so safe by construction under the match clock). Missing when either player has no match in the window."""
    f = frame_a(labels=labels)
    h = pd.read_parquet(C.OUT / "history.parquet", columns=["match_id", "side", "low_share"])
    a = h[h["side"] == "A"].set_index("match_id")["low_share"]
    b = h[h["side"] == "B"].set_index("match_id")["low_share"]
    f[f"in_{C.NEW_INPUT_C}"] = (a.reindex(f["match_id"]).to_numpy(float) - b.reindex(f["match_id"]).to_numpy(float))
    return f


def job_data_c(frame: pd.DataFrame, arm: str, season: int):
    """exp's rows and 58 inputs, plus the new difference column (negated in the swapped half)."""
    tr = C.train_mask_a(frame["season"].to_numpy(), frame["level_code"].to_numpy(), "exp", season, 0)
    te = (frame["season"] == season).to_numpy()
    X = SA.matrix(frame, NAMES)
    X[C.NEW_INPUT_C] = frame[f"in_{C.NEW_INPUT_C}"].to_numpy(dtype="float64")
    X_test = X[te].reset_index(drop=True)
    X_flip = SA.flip(X_test[NAMES])
    X_flip[C.NEW_INPUT_C] = -X_test[C.NEW_INPUT_C]
    X_query = pd.concat([X_test, X_flip], ignore_index=True)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(), X_query,
            frame.loc[te, "match_id"].to_numpy(), tr)


def job_data_b(frame: pd.DataFrame, arm: str, season: int):
    cols = NAMES if C.has_odds_b(arm) else NOODDS
    tr = C.train_mask_b(frame["season"].to_numpy(), frame["pop"].to_numpy(), arm, season)
    te = C.query_mask_b(frame["season"].to_numpy(), frame["pop"].to_numpy(), season)
    X = SA.matrix(frame, cols)
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, SA.flip(X_test)], ignore_index=True)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(), X_query,
            frame.loc[te, "match_id"].to_numpy(), tr)


def jobs(which: str, arms=None, seasons=None) -> list[tuple[str, int, int]]:
    if which == "A":
        arms = arms or list(C.ARMS_A)
        seasons = seasons or list(C.SEASONS_A)
        return [(a, s, k) for a in arms for s in seasons for k in C.SEEDS_A]
    if which == "C":
        arms = arms or list(C.ARMS_C)
        seasons = seasons or list(C.SEASONS_C)
        return [(a, s, k) for a in arms for s in seasons for k in C.SEEDS_C]
    arms = arms or list(C.ARMS_B)
    seasons = seasons or list(C.SEASONS_B)
    return [(a, s, k) for a in arms for s in seasons for k in C.SEEDS_B]


def path_of(which: str, arm: str, season: int, seed: int) -> Path:
    return {"A": C.fit_path_a, "B": C.fit_path_b, "C": C.fit_path_c}[which](arm, season, seed)


# ------------------------------------------------------------------------------------------------
# Plan and check

def plan() -> pd.DataFrame:
    rows = []
    fa = frame_a(labels=False)
    s, lv = fa["season"].to_numpy(), fa["level_code"].to_numpy()
    for arm, season, seed in jobs("A"):
        m = C.train_mask_a(s, lv, arm, season, seed)
        rows.append({"exp": "A", "arm": arm, "season": season, "seed": seed, "train_rows": int(m.sum()),
                     "query_rows": int(2 * (s == season).sum()), "done": C.fit_path_a(arm, season, seed).exists()})
    fb = frame_b(labels=False)
    s, pop = fb["season"].to_numpy(), fb["pop"].to_numpy()
    for arm, season, seed in jobs("B"):
        m = C.train_mask_b(s, pop, arm, season)
        rows.append({"exp": "B", "arm": arm, "season": season, "seed": seed, "train_rows": int(m.sum()),
                     "query_rows": int(2 * C.query_mask_b(s, pop, season).sum()),
                     "done": C.fit_path_b(arm, season, seed).exists()})
    return pd.DataFrame(rows)


def check() -> dict:
    """A: exp's job data rebuilt here against the stored current-model fits (columns, training shape, td ids, and the
    fingerprints the stored files carry). B: nmt's training rows against the stored no-odds fits (columns, training
    shape) and its MT query ids against theirs."""
    out = {"A": [], "B": []}
    fa = frame_a(labels=True)
    for s in C.SEASONS_A:
        X_train, y_train, X_query, ids, _ = job_data_a(fa, "exp", s, 0)
        fp = TW.SC.fingerprint(X_train, y_train, X_query)
        for k in C.SEEDS_A:
            _, stored_ids, meta = C.read_fit(TW.stored_path(s, k))
            r = {"season": s, "seed": k,
                 "columns_equal": TW.SC.race_names(meta.get("columns") or []) == NAMES,
                 "train_shape_equal": list(meta.get("train_shape", [])) == list(X_train.shape),
                 "ids_equal": bool(np.array_equal(stored_ids, ids.astype(str)))}
            if meta.get("fingerprint") is not None:
                r["fingerprint_equal"] = meta["fingerprint"] == fp
            r["ok"] = all(v for key, v in r.items() if key.endswith("_equal"))
            out["A"].append(r)
    fb = frame_b(labels=True)
    for s in C.SEASONS_B:
        X_train, y_train, X_query, ids, tr = job_data_b(fb, "nmt", s)
        mt_ids = ids[(fb.loc[C.query_mask_b(fb["season"], fb["pop"], s), "pop"] == "MT").to_numpy()]
        for k in C.SEEDS_B:
            p, stored_ids, meta = C.read_fit(C.stored_noodds_path(s, k))
            r = {"season": s, "seed": k,
                 "columns_equal": TW.SC.race_names(meta.get("columns") or []) == NOODDS,
                 "train_shape_equal": list(meta.get("train_shape", [])) == list(X_train.shape),
                 "td_is_twice_the_ids": len(p) == 2 * len(stored_ids),
                 "mt_ids_equal": bool(np.array_equal(np.sort(stored_ids.astype(str)), np.sort(mt_ids.astype(str))))}
            r["ok"] = all(v for key, v in r.items() if key.endswith("_equal"))
            out["B"].append(r)
    out["C"] = []
    fc = frame_c(labels=True)
    for s in C.SEASONS_C:
        Xa, ya, Qa, ida, _ = job_data_a(fa, "exp", s, 0)
        Xc, yc, Qc, idc, _ = job_data_c(fc, "hist1", s)
        n = len(Qc) // 2
        v = Qc[C.NEW_INPUT_C].to_numpy()
        r = {"season": s, "base_columns_equal": bool(np.array_equal(Xc[NAMES].to_numpy(), Xa.to_numpy(), equal_nan=True)
                                                     and np.array_equal(Qc[NAMES].to_numpy(), Qa.to_numpy(),
                                                                        equal_nan=True)),
             "labels_equal": bool(np.array_equal(yc, ya)), "ids_equal": bool(np.array_equal(idc, ida)),
             "new_column_flips": bool(np.allclose(v[n:], -v[:n], equal_nan=True)),
             "new_column_coverage_train": float(np.isfinite(Xc[C.NEW_INPUT_C].to_numpy()).mean())}
        r["ok"] = all(r[k] for k in ("base_columns_equal", "labels_equal", "ids_equal", "new_column_flips"))
        out["C"].append(r)
    res = {"what": "job data rebuilt by this harness against the stored fits (no result related)",
           "all_ok": all(r["ok"] for r in out["A"] + out["B"] + out["C"]), **out}
    C.OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(C.OUT / "input_check.json", res)
    return res


# ------------------------------------------------------------------------------------------------
# GPU runner

def run(which: str, arms=None, seasons=None) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    if not C.read_json(C.OUT / "input_check.json").get("all_ok"):
        raise RuntimeError("run --check first: the input check has not passed")
    frame = {"A": frame_a, "B": frame_b, "C": frame_c}[which](labels=True)
    src_sha = C.sha256_file(C.FRAME if which == "B" else C.MODEL_FRAME)
    todo = [(a, s, k) for a, s, k in jobs(which, arms, seasons) if not path_of(which, a, s, k).exists()]
    C.log(f"experiment {which}: {len(todo)} fits to run")
    last_season = None
    for arm, season, seed in todo:
        path = path_of(which, arm, season, seed)
        path.parent.mkdir(parents=True, exist_ok=True)
        if season != last_season:
            TWF.wait_for_card()
            last_season = season
        if which == "A":
            X_train, y_train, X_query, ids, tr = job_data_a(frame, arm, season, seed)
        elif which == "C":
            X_train, y_train, X_query, ids, tr = job_data_c(frame, arm, season)
        else:
            X_train, y_train, X_query, ids, tr = job_data_b(frame, arm, season)
        free_gb = TWF.wait_for_card(processes=False)
        clf = runtime.classifier(**C.CONFIG, random_state=seed)
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_query)
        secs = time.monotonic() - t0
        if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
            raise RuntimeError(f"{path.name}: invalid probabilities")
        trained = frame.loc[tr]
        by = (trained.groupby("level").size() if "level" in trained.columns else
              trained.groupby("level_code").size().rename(index=lambda c: C.CODE_LEVEL[int(c)]))
        meta = {"experiment": which, "arm": arm, "season": season, "seed": seed,
                "config": {**C.CONFIG, "random_state": seed}, "train_shape": list(X_train.shape),
                "train_rows_by_level": {str(k): int(v) for k, v in by.items()},
                "train_seasons": [int(trained["season"].min()), int(trained["season"].max())],
                "query_rows": {"td": int(len(X_query))}, "columns": list(X_train.columns),
                "fingerprint": TW.SC.fingerprint(X_train, y_train, X_query), "frame_sha256": src_sha,
                "draw_seed": C.DRAW_SEED, "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
        tmp = path.with_name(path.name + ".tmp.npz")
        np.savez(tmp, meta=np.asarray(json.dumps(meta)), p_td=proba[:, 1], ids_td=ids.astype(str))   # ids once
        tmp.replace(path)
        C.log(f"{which} {path.name}: {X_train.shape[0]:,} rows, {secs:.0f} s, peak {meta['peak_gpu_gb']} GB")
        del clf
        torch.cuda.empty_cache()
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--plan" in args:
        t = plan()
        C.OUT.mkdir(parents=True, exist_ok=True)
        t.to_csv(C.OUT / "fit_plan.csv", index=False)
        with pd.option_context("display.width", 250, "display.max_columns", 40):
            for which in ("A", "B"):
                show = t[(t["exp"] == which) & (t["seed"] == 0)].pivot(index="season", columns="arm",
                                                                         values="train_rows")
                print(f"experiment {which}: training rows (seed 0)\n{show.to_string()}")
            print(t.groupby("exp")[["done"]].agg(["sum", "count"]).to_string())
        return 0
    if "--check" in args:
        r = check()
        print({k: v for k, v in r.items() if k not in ("A", "B", "C")})
        print("C coverage of the new input (train):", [round(x["new_column_coverage_train"], 4) for x in r["C"]])
        for which in ("A", "B", "C"):
            bad = [x for x in r[which] if not x["ok"]]
            print(which, "rows", len(r[which]), "failed", bad[:3])
        return 0 if r["all_ok"] else 1
    if "--run" in args:
        which = args[args.index("--run") + 1]
        if which not in ("A", "B", "C"):
            raise SystemExit("--run A, B or C")
        arms = args[args.index("--arms") + 1].split(",") if "--arms" in args else None
        valid = {"A": C.ARMS_A, "B": C.ARMS_B, "C": C.ARMS_C}[which]
        if arms and any(a not in valid for a in arms):
            raise SystemExit(f"unknown arm for experiment {which}: {[a for a in arms if a not in valid]}")
        seasons = None
        if "--seasons" in args:
            lo, hi = args[args.index("--seasons") + 1].split("-")
            seasons = [s for s in {"A": C.SEASONS_A, "B": C.SEASONS_B, "C": C.SEASONS_C}[which]
                       if int(lo) <= s <= int(hi)]
        return run(which, arms, seasons)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
