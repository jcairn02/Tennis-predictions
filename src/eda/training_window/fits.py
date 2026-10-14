"""The training-window study's local TabPFN-3.5 fits: the plan, a CPU check, and the GPU runner.

Job (arm, Y, seed), arm in common.NEW_ARMS, Y in 2019-2024, seed 0-3: trains on the arm's rows of seasons before Y
(common.train_mask) and predicts every season-Y match as stored and with A and B swapped (td; the scorer symmetrises).
The settings and the classifier are every local fit's (src/eda/tabpfn_local/runtime.py). One fit at a time on the card:
before each season's jobs the runner waits until no other process of the local env is running and 12 GB are free. A
finished job is saved to data/studies/training_window/local/ and never refitted.

    ./python.sh src/eda/training_window/fits.py --plan
    ./python.sh src/eda/training_window/fits.py --check      # CPU: this harness's exp inputs equal the stored fits'
    ./python_tabpfn_local.sh src/eda/training_window/fits.py --run [--arms last7,last5] [--seasons 2019-2024]

--check relates no result: it hashes the training labels inside the fingerprint, as the stored fits' runner did.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.training_window import common as C  # noqa: E402


def plan(frame: pd.DataFrame) -> pd.DataFrame:
    seasons = frame["season"].to_numpy()
    rows = []
    for arm in C.ARMS:
        for s in C.SEASONS:
            for k in C.SEEDS:
                m = C.train_mask(seasons, arm, s, k)
                rows.append({"arm": arm, "season": s, "seed": k, "train_rows": int(m.sum()),
                             "first_season": int(seasons[m].min()), "last_season": int(seasons[m].max()),
                             "same_rows_as_exp": bool(np.array_equal(m, C.train_mask(seasons, "exp", s, k))),
                             "done": C.fit_path(arm, s, k).exists()})
    return pd.DataFrame(rows)


def check(frame: pd.DataFrame) -> dict:
    """The exp jobs rebuilt by this harness against the stored fits: feature interactions' fingerprints (seed 3) and
    every stored file's columns, training shape and td ids (seeds 0-3)."""
    rows = []
    for s in C.SEASONS:
        X_train, y_train, X_query, ids = C.job_data(frame, "exp", s, 0)
        fp = C.SC.fingerprint(X_train, y_train, X_query)
        for k in C.SEEDS:
            _, stored_ids, meta = C.read_fit(C.stored_path(s, k))
            r = {"season": s, "seed": k, "file": str(C.stored_path(s, k).relative_to(C.ROOT)),
                 "columns_equal": C.SC.race_names(meta.get("columns") or []) == C.inputs(),
                 "train_shape_equal": list(meta.get("train_shape", [])) == list(X_train.shape),
                 "query_rows_equal": meta.get("query_rows") == {"td": int(len(X_query))},
                 "ids_equal": bool(np.array_equal(stored_ids, ids.astype(str))),
                 "config_equal": meta.get("config") == {**C.CONFIG, "random_state": k}}
            if meta.get("fingerprint") is not None:
                r["fingerprint_equal"] = meta["fingerprint"] == fp
            r["ok"] = all(v for key, v in r.items() if key.endswith("_equal"))
            rows.append(r)
    out = {"what": "this harness's exp job data against the stored current-model fits (no result related)",
           "model_frame_sha256": C.sha256_file(C.P.model_frame), "fits_checked": len(rows),
           "fingerprints_checked": sum("fingerprint_equal" in r for r in rows),
           "all_ok": bool(rows) and all(r["ok"] for r in rows) and all(r.get("fingerprint_equal", True) for r in rows),
           "rows": rows}
    C.OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(C.OUT / "input_check.json", out)
    return out


def other_local_processes() -> list[int]:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -like '*tennis-tabpfn-local*' } | ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         timeout=120).stdout
    return [int(x) for x in out.split() if x.strip().isdigit() and int(x) != os.getpid()]


def wait_for_card(need_gb: float = 12.0, patience_s: int = 4 * 3600, processes: bool = True) -> float:
    import torch
    t0, last_note = time.monotonic(), -1e9
    while True:
        others = other_local_processes() if processes else []
        free = torch.cuda.mem_get_info()[0] / 2**30
        if not others and free >= need_gb:
            return free
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"the card stayed busy for {patience_s} s (other processes {others}, {free:.1f} GB free)")
        if time.monotonic() - last_note > 300:
            C.log(f"waiting for the card: other local-env processes {others}, {free:.1f} GB free")
            last_note = time.monotonic()
        time.sleep(30)


def run(frame: pd.DataFrame, arms, seasons) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    if not C.read_json(C.OUT / "input_check.json").get("all_ok"):
        raise RuntimeError("run --check first: the input check has not passed")
    cols = C.inputs()
    if not C.SA.check_flip(frame, cols, C.P):
        raise RuntimeError("flip is not an involution")
    frame_sha = C.sha256_file(C.P.model_frame)
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        for season in seasons:
            todo = [k for k in C.SEEDS if not C.fit_path(arm, season, k).exists()]
            if not todo:
                continue
            free_gb = wait_for_card()
            for seed in todo:
                path = C.fit_path(arm, season, seed)
                X_train, y_train, X_query, ids = C.job_data(frame, arm, season, seed)
                trained = frame.loc[C.train_mask(frame["season"].to_numpy(), arm, season, seed), "season"]
                free_gb = wait_for_card(processes=False)
                clf = runtime.classifier(**C.CONFIG, random_state=seed)
                torch.cuda.reset_peak_memory_stats()
                t0 = time.monotonic()
                clf.fit(X_train, y_train)
                proba = clf.predict_proba(X_query)
                secs = time.monotonic() - t0
                if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
                    raise RuntimeError(f"{path.name}: invalid probabilities")
                meta = {"arm": arm, "season": season, "seed": seed, "config": {**C.CONFIG, "random_state": seed},
                        "train_shape": list(X_train.shape), "train_rows_by_season": trained.value_counts().sort_index()
                        .to_dict(), "query_rows": {"td": int(len(X_query))}, "columns": list(X_train.columns),
                        "fingerprint": C.SC.fingerprint(X_train, y_train, X_query), "model_frame_sha256": frame_sha,
                        "draw_seed": C.DRAW_SEED, "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                        "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
                meta["train_rows_by_season"] = {str(int(k)): int(v) for k, v in meta["train_rows_by_season"].items()}
                tmp = path.with_name(path.name + ".tmp.npz")
                np.savez(tmp, meta=np.asarray(json.dumps(meta)), p_td=proba[:, 1], ids_td=ids.astype(str))
                tmp.replace(path)
                C.log(f"{path.name}: {X_train.shape[0]:,} rows, {secs:.0f} s, peak {meta['peak_gpu_gb']} GB")
                del clf
                torch.cuda.empty_cache()
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--plan" in args:
        t = plan(C.load_frame(labels=False))
        C.OUT.mkdir(parents=True, exist_ok=True)
        t.to_csv(C.OUT / "fit_plan.csv", index=False)
        show = t[t["seed"] == 0].pivot(index="season", columns="arm", values="train_rows")[list(C.ARMS)]
        print(show.to_string())
        print(t.groupby("arm")[["same_rows_as_exp", "done"]].sum().to_string())
        return 0
    if "--check" in args:
        r = check(C.load_frame(labels=True))
        print({k: v for k, v in r.items() if k != "rows"})
        return 0 if r["all_ok"] else 1
    if "--run" in args:
        arms = args[args.index("--arms") + 1].split(",") if "--arms" in args else list(C.NEW_ARMS)
        bad = [a for a in arms if a not in C.NEW_ARMS]
        if bad:
            raise SystemExit(f"not a new arm: {bad} (exp is reused, never refitted)")
        lo, hi = args[args.index("--seasons") + 1].split("-") if "--seasons" in args else (C.SEASONS[0], C.SEASONS[-1])
        seasons = [s for s in C.SEASONS if int(lo) <= s <= int(hi)]
        return run(C.load_frame(labels=True), arms, seasons)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
