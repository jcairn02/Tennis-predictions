"""Local TabPFN-3.5 fits of the serve-speed study (audit C5): the fit plan, the CPU checks that let the base arm's
earlier fits be reused, and the GPU runner (run by the lead only, in the `tennis-tabpfn-local` env).

The expanding window. Job (arm, Y, seed) trains on the model frame's matches of 2013 .. Y - 1 and predicts season Y:
    td      every season-Y match, as stored and with A and B swapped (the scorer symmetrises)
    early   arms with the odds, 2025-2026: the matches with a Polymarket price, odds_logit replaced by the price 24 hours
            before the listed start (surface_elo_pieces/early_price_frame.parquet)
    late    the same with the price 30 minutes before the listed start
Settings: 8 estimators, softmax temperature 0.9, pretraining limits ignored (feature interactions' runner, unchanged).

The plan (223 jobs; `plan_jobs`):
    spd (A1)            2019-2023 seeds 0-3, 2024-2026 seeds 0-15     68
    spd_raw (A2)        2019-2023 seeds 0-3, 2024-2026 seeds 0-7      44
    spd_all (A3)        2019-2023 seeds 0-3, 2024-2026 seeds 0-7      44
    spd_noodds          2019-2023 seeds 0-3, 2024-2026 seeds 0-7      44
    model_noodds        2019-2023 seed 3, 2024-2026 seeds 3-7         20   (new seeds; the race has 0-2)
    reproduction        model 2024 seed 0, model 2026 seed 2, model_noodds 2025 seed 1      3
Base fits reused read-only: "model" seeds 0-2 (the rating race, no fingerprint) and 3-15 (feature interactions,
fingerprinted), "model_noodds" seeds 0-2 (the race). They are used only after:
    --fingerprint-check   (CPU) this harness's job_data fingerprints for "model" equal every feature-interactions fit's
                          stored fingerprint, 2019-2026; the race's stored column lists, training shapes and query ids
                          of "model" and "model_noodds" equal this harness's (it hashes training labels; relates nothing)
    --repro-check         the 3 reproduction fits equal the race's stored forecasts within 1e-6 (td, early, late)

Fits are written to data/studies/serve_speed_tabpfn/local/ (reproductions to local/repro/) and never refitted. The runner
fits "model" with the odds only for the two reproduction jobs, and refuses a feature file whose speed_meta.json lacks
passing probe records; the feature file's SHA-256 goes in every fit's metadata.

    ./python.sh src/eda/serve_speed_tabpfn/local_fits.py --plan
    ./python.sh src/eda/serve_speed_tabpfn/local_fits.py --fingerprint-check
    ./python_tabpfn_local.sh src/eda/serve_speed_tabpfn/local_fits.py --run --jobs repro     # the lead, GPU
    ./python.sh src/eda/serve_speed_tabpfn/local_fits.py --repro-check
    ./python_tabpfn_local.sh src/eda/serve_speed_tabpfn/local_fits.py --run --jobs all       # the lead, GPU
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402


@dataclass(frozen=True)
class Job:
    arm: str
    season: int
    seed: int
    kind: str = "fit"                  # "fit" or "repro"

    @property
    def name(self) -> str:
        return f"{self.arm}__{self.season}__seed{self.seed}.npz"


REPRO_JOBS = (Job("model", 2024, 0, "repro"), Job("model", 2026, 2, "repro"), Job("model_noodds", 2025, 1, "repro"))
ARM_SEEDS = {"spd": (range(4), range(16)), "spd_raw": (range(4), range(8)), "spd_all": (range(4), range(8)),
             "spd_noodds": (range(4), range(8)), "model_noodds": ((3,), range(3, 8))}


def plan_jobs() -> list[Job]:
    jobs = []
    for arm, (cal, test) in ARM_SEEDS.items():
        jobs += [Job(arm, s, k) for s in C.CAL_SEASONS for k in cal]
        jobs += [Job(arm, s, k) for s in C.TEST_SEASONS for k in test]
    return jobs + list(REPRO_JOBS)


def out_path(job: Job, P: C.Paths = C.DEFAULT) -> Path:
    return (P.repro if job.kind == "repro" else P.local) / job.name


def estimate_seconds(job: Job) -> float:
    return C.FIT_SECONDS["odds" if A.has_odds(job.arm) else "noodds"][job.season] + C.FIT_OVERHEAD_S


def plan_table(P: C.Paths = C.DEFAULT) -> pd.DataFrame:
    rows = [{**asdict(j), "file": str(out_path(j, P).relative_to(P.out)) if out_path(j, P).is_relative_to(P.out)
             else str(out_path(j, P)), "est_seconds": estimate_seconds(j), "done": out_path(j, P).exists()}
            for j in plan_jobs()]
    return pd.DataFrame(rows)


def queries(ep: pd.DataFrame, season: int, X_test: pd.DataFrame, ids: np.ndarray, P: C.Paths = C.DEFAULT) -> dict:
    """Feature interactions' query blocks, unchanged (so the reused fits' fingerprints can be reproduced)."""
    out = {"td": (pd.concat([X_test, A.flip(X_test, P)], ignore_index=True), ids)}
    if "odds_logit" in X_test.columns and season in C.PRICE_SEASONS:
        e = ep.set_index("match_id").reindex(ids)
        ok = e["has_early"].fillna(False).to_numpy(bool)
        for name, col in (("early", "p_early_a"), ("late", "p_close_a")):
            Xq = X_test[ok].reset_index(drop=True).copy()
            Xq["odds_logit"] = logit(np.clip(e[col].to_numpy(dtype=float)[ok], C.EPS, 1 - C.EPS))
            out[name] = (pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), ids[ok])
    return out


def early_frame(P: C.Paths = C.DEFAULT) -> pd.DataFrame:
    ep = pd.read_parquet(P.early, columns=["match_id", "has_early", "p_early_a", "p_close_a"])
    ep["match_id"] = ep["match_id"].astype(str)
    return ep


def stored_meta(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return json.loads(str(z["meta"]))


# ------------------------------------------------------------------------------------------------
# CPU checks before any reuse of the base fits (audit C5; coordinator's R3 note on model_noodds)

def fingerprint_check(P: C.Paths = C.DEFAULT, seasons=range(2019, 2027)) -> dict:
    frame = A.load_frame([], P, labels=True)
    ep = early_frame(P)
    rows, ok_all = [], True
    for arm in ("model", "model_noodds"):
        cols = A.arm_inputs(arm, P)
        for season in seasons:
            X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
            qs = queries(ep, season, X_test, ids, P)
            X_query = pd.concat([qs[n][0] for n in qs], ignore_index=True)
            fp = C.fingerprint(X_train, y_train, X_query) if arm == "model" else None
            for folder, label in ((P.fi_local, "feature_interactions"), (P.race_local, "race")):
                for k in range(16):
                    path = folder / f"{arm}__{season}__seed{k}.npz"
                    if not path.exists():
                        continue
                    meta = stored_meta(path)
                    with np.load(path, allow_pickle=False) as z:
                        ids_ok = bool(np.array_equal(z["ids_td"].astype(str), ids.astype(str)))
                    stored_cols = meta.get("columns") or []
                    r = {"arm": arm, "season": season, "seed": k, "folder": label,
                         "columns_identical": stored_cols == cols,
                         "columns_equal": (C.race_names(stored_cols) if label == "race" else stored_cols) == cols,
                         "train_shape_equal": list(meta.get("train_shape", [])) == [len(X_train), len(cols)],
                         "query_rows_equal": meta.get("query_rows") == {n: int(len(qs[n][0])) for n in qs},
                         "ids_equal": ids_ok, "stored_fingerprint": meta.get("fingerprint") is not None}
                    if fp is not None and meta.get("fingerprint") is not None:
                        r["fingerprint_equal"] = meta["fingerprint"] == fp
                    r["ok"] = all(v for key, v in r.items() if key.endswith("_equal"))
                    ok_all &= r["ok"]
                    rows.append(r)
    fi_model = [r for r in rows if r["arm"] == "model" and r["folder"] == "feature_interactions"]
    out = {"what": "this harness's job_data against the stored base fits (no result related; labels only hashed)",
           "model_frame_sha256": C.sha256_file(P.model_frame), "fits_checked": len(rows),
           "fi_model_fingerprints_checked": sum("fingerprint_equal" in r for r in fi_model),
           "fi_model_fingerprints_equal": sum(r.get("fingerprint_equal", False) for r in fi_model),
           "race_fits_checked": sum(r["folder"] == "race" for r in rows), "all_ok": bool(ok_all and rows),
           "rows": rows}
    C.write_json(P.checks / "fingerprint_check.json", out)
    return out


def compare_fit_files(new: Path, stored: Path, tol: float = C.REPRO_TOL) -> dict:
    """Every block of the stored file must be reproduced: same ids, max |p_new - p_stored| <= tol."""
    out = {"new": str(new), "stored": str(stored), "blocks": {}}
    if not new.exists() or not stored.exists():
        out["passed"] = False
        out["problem"] = "missing file"
        return out
    with np.load(new, allow_pickle=False) as a, np.load(stored, allow_pickle=False) as b:
        names = [k[2:] for k in b.files if k.startswith("p_")]
        passed = bool(names)
        for n in names:
            if f"p_{n}" not in a.files:
                out["blocks"][n] = {"present": False}
                passed = False
                continue
            same_ids = bool(np.array_equal(a[f"ids_{n}"].astype(str), b[f"ids_{n}"].astype(str)))
            diff = float(np.abs(a[f"p_{n}"] - b[f"p_{n}"]).max()) if same_ids else float("inf")
            out["blocks"][n] = {"present": True, "same_ids": same_ids, "max_abs_diff": diff}
            passed &= same_ids and diff <= tol
    out["passed"] = bool(passed)
    return out


def repro_check(P: C.Paths = C.DEFAULT) -> dict:
    rows = [{"job": asdict(j), **compare_fit_files(out_path(j, P), P.race_local / j.name)} for j in REPRO_JOBS]
    out = {"what": "reproduction fits against the rating race's stored forecasts (tolerance 1e-6)",
           "tolerance": C.REPRO_TOL, "passed": all(r["passed"] for r in rows), "rows": rows}
    C.write_json(P.checks / "repro_check.json", out)
    return out


# ------------------------------------------------------------------------------------------------
# The GPU runner (the lead only)

def wait_for_memory(need_gb: float = 12.0, patience_s: int = 6 * 3600) -> float:
    import torch
    t0, last_note = time.monotonic(), -1e9
    while True:
        free = torch.cuda.mem_get_info()[0] / 2**30
        if free >= need_gb:
            return free
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"under {need_gb} GB free for {patience_s} s ({free:.1f} GB)")
        if time.monotonic() - last_note > 300:
            C.log(f"waiting for GPU memory: {free:.1f} GB free")
            last_note = time.monotonic()
        time.sleep(20)


def guard(job: Job, P: C.Paths = C.DEFAULT) -> None:
    """The runner's refusals: "model" with the odds only as a named reproduction; never a seed the race already holds
    unless it is the named reproduction; only planned jobs."""
    if job not in plan_jobs():
        raise RuntimeError(f"{job}: not in the 223-job plan")
    if job.arm == "model" and job.kind != "repro":
        raise RuntimeError("the base arm 'model' is reused, never refitted (except the two reproduction jobs)")
    if job.kind != "repro" and job.arm == "model_noodds" and (P.race_local / job.name).exists():
        raise RuntimeError(f"{job.name}: the rating race holds this seed; only new seeds are fitted")


def select_jobs(spec: str, seasons: tuple[int, int] | None = None, seeds: tuple[int, ...] | None = None) -> list[Job]:
    jobs = plan_jobs()
    if spec == "repro":
        jobs = list(REPRO_JOBS)
    elif spec != "all":
        keep = set(spec.split(","))
        jobs = [j for j in jobs if j.arm in keep and j.kind == "fit"]
    if seasons:
        jobs = [j for j in jobs if seasons[0] <= j.season <= seasons[1]]
    if seeds is not None:
        jobs = [j for j in jobs if j.seed in seeds]
    return jobs


def run(jobs: list[Job], P: C.Paths = C.DEFAULT) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    for j in jobs:
        guard(j, P)
    extra = sorted({c for j in jobs for c in A.arm_inputs(j.arm, P) if c not in A.base_inputs(P)[0]})
    feat = A.require_features(P) if extra else {"sha256": None}
    frame = A.load_frame(extra, P, labels=True)
    ep = early_frame(P)
    frame_sha = C.sha256_file(P.model_frame)
    for arm in sorted({j.arm for j in jobs}):
        cols = A.arm_inputs(arm, P)
        if not A.check_flip(frame, cols, P):
            raise RuntimeError(f"{arm}: flip is not an involution")
        empty = [c for c in cols if not np.isfinite(frame[f"in_{c}"].to_numpy(dtype=float)).any()]
        if empty:
            raise RuntimeError(f"{arm}: inputs without any value: {empty}")
    P.local.mkdir(parents=True, exist_ok=True)
    P.repro.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        path = out_path(job, P)
        if path.exists():
            continue
        cols = A.arm_inputs(job.arm, P)
        X_train, y_train, X_test, ids = A.job_data(frame, cols, job.season)
        qs = queries(ep, job.season, X_test, ids, P)
        names = list(qs)
        X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
        free_gb = wait_for_memory()
        clf = runtime.classifier(**C.CONFIG, random_state=job.seed)
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_query)
        secs = time.monotonic() - t0
        if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
            raise RuntimeError(f"{path.name}: invalid probabilities")
        p = proba[:, 1]
        payload, start = {}, 0
        for n in names:
            k = len(qs[n][0])
            payload[f"p_{n}"] = p[start:start + k]
            payload[f"ids_{n}"] = qs[n][1].astype(str)
            start += k
        speed_cols = [c for c in cols if c in A.REGISTRY_SPEC]
        meta = {"arm": job.arm, "season": job.season, "seed": job.seed, "kind": job.kind,
                "config": {**C.CONFIG, "random_state": job.seed}, "train_shape": list(X_train.shape),
                "train_seasons": [C.TRAIN_FROM, job.season - 1], "query_rows": {n: int(len(qs[n][0])) for n in names},
                "columns": list(X_train.columns), "fingerprint": C.fingerprint(X_train, y_train, X_query),
                "feature_sha256": feat["sha256"] if speed_cols else None,
                "registry": {c: A.registry(P)[c] for c in speed_cols}, "model_frame_sha256": frame_sha,
                "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
        tmp = path.with_name(path.name + ".tmp.npz")
        np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
        tmp.replace(path)
        C.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}")
        del clf
        torch.cuda.empty_cache()
    return 0


def main() -> int:
    args = sys.argv[1:]
    P = C.DEFAULT
    if "--plan" in args:
        t = plan_table(P)
        P.out.mkdir(parents=True, exist_ok=True)
        t.to_csv(P.out / "fit_plan.csv", index=False)
        by = t.groupby(["arm", "kind"]).agg(fits=("seed", "size"), seconds=("est_seconds", "sum"),
                                           done=("done", "sum")).reset_index()
        print(by.to_string(index=False))
        print(f"total {len(t)} jobs, {t['est_seconds'].sum() / 3600:.2f} h at the logged speeds "
              f"({1.5 * t['est_seconds'].sum() / 3600:.2f} h at 1.5 x); done {int(t['done'].sum())}")
        return 0
    if "--fingerprint-check" in args:
        r = fingerprint_check(P)
        print({k: v for k, v in r.items() if k != "rows"})
        return 0 if r["all_ok"] else 1
    if "--repro-check" in args:
        r = repro_check(P)
        print(json.dumps(r, indent=1))
        return 0 if r["passed"] else 1
    if "--run" in args:
        spec = args[args.index("--jobs") + 1] if "--jobs" in args else "all"
        seasons = tuple(int(x) for x in args[args.index("--seasons") + 1].split("-")) if "--seasons" in args else None
        seeds = None
        if "--seeds" in args:
            s = args[args.index("--seeds") + 1]
            a, _, b = s.partition("-")
            seeds = tuple(range(int(a), int(b) + 1)) if b else tuple(int(x) for x in s.split(","))
        return run(select_jobs(spec, seasons, seeds), P)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
