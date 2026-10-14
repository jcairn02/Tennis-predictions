"""TabPFN's cached mode against the decided path: where the two diverge (docs/studies/daily_prediction/, part 2).

The decided path (fit_mode "fit_preprocessors", the library's default) processes the training rows at every call;
fit_mode "fit_with_cache" processes them once and keeps what the test rows read (the scaler and ECDF context, the
inducing states, the 24 ICL layers' keys and values, the decoder keys). On the instance (template_2026-10-10, season
2026) the two differed by up to 0.18 (prediction_pipeline/cache_precision.json). Here both run on the same data, with
hooks on the model recording the values at each stage: the model's input, the column aggregator (end of stages 0-2),
every ICL block, the output norm and the decoder. The first stage where they differ locates the cause. The cached
path's training-only forward (the cache build) is compared with the decided path's training rows as well.

Data: season 2026's training rows (2013-2025; --rows draws a subset, fixed seed), the 23 matches of the replay of
15 Jul 2026 as stored and swapped. No outcome is read.
Run: ./python_tabpfn_local.sh src/eda/daily_prediction/dp_cachediag.py --rows 4000 --estimators 1 --tag small
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dp_common as DC  # noqa: E402
from dp_fit import _mods  # noqa: E402

REPLAY = DC.OUT / "runs" / "replay_2026-07-13_R16"


def data(rows: int, seed: int = 0):
    FITS, A, C, TWF = _mods()
    P = FITS.paths(DC.INSTANCE)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    X_train, y_train, X_test, ids = A.job_data(frame, cols, 2026)
    if rows and rows < len(X_train):
        keep = np.sort(np.random.default_rng(seed).choice(len(X_train), rows, replace=False))
        X_train, y_train = X_train.iloc[keep].reset_index(drop=True), y_train[keep]
    live = set(pd.read_parquet(REPLAY / "live_meta.parquet")["match_id"].astype(str))
    Xq = X_test[np.isin(ids.astype(str), list(live))].reset_index(drop=True)
    return X_train, y_train, pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), C


class Recorder:
    """Every forward of the TabPFN model: its input and each stage's output, on the CPU in float32."""

    def __init__(self):
        import torch
        self.calls: list[dict] = []
        self.hooked: set[int] = set()
        self.handle = torch.nn.modules.module.register_module_forward_pre_hook(self._pre)

    def _pre(self, module, args):
        if type(module).__name__ != "TabPFNV3p5":
            return
        if id(module) not in self.hooked:
            self.hooked.add(id(module))
            module.column_aggregator.register_forward_hook(self._out("agg"))
            for i, b in enumerate(module.icl_blocks):
                b.register_forward_hook(self._out(f"icl{i:02d}"))
            module.output_norm.register_forward_hook(self._out("norm"))
            module.heads.register_forward_hook(self._out("heads"))
        x, y = args[0], args[1]
        self.calls.append({"x": x.detach().float().cpu(), "rows": int(x.shape[0]), "n_train": int(y.shape[0]),
                           "parts": {}})

    def _out(self, name):
        def hook(module, args, out):
            o = out[0] if isinstance(out, tuple) else out
            self.calls[-1]["parts"].setdefault(name, []).append(o.detach().float().cpu())
        return hook

    def close(self):
        self.handle.remove()


def stage_tensor(call: dict, name: str):
    import torch
    parts = call["parts"].get(name)
    if not parts:
        return None
    if name == "agg":                                  # row chunks, in order, along the row axis
        return torch.cat(parts, dim=1)
    return parts[-1]


def test_rows(call: dict, name: str):
    """The test rows' values at a stage: the decided path's rows after the training rows; the cached path's all."""
    t = stage_tensor(call, name)
    if t is None:
        return None
    if name == "heads":
        return t
    if name == "x":
        return t
    return t[:, call["n_train"]:] if call["rows"] > call["n_train"] else t


def compare(a, b) -> dict:
    if a is None or b is None:
        return {"missing": True}
    if a.shape != b.shape:
        return {"shapes": [list(a.shape), list(b.shape)]}
    d = (a - b).abs()
    fin = np.isfinite(d.numpy())
    return {"max_abs": float(d.numpy()[fin].max()) if fin.any() else None,
            "mean_abs": float(d.numpy()[fin].mean()) if fin.any() else None,
            "scale": float(a.abs().mean())}


def run(rows: int, estimators: int, seed: int, msm: bool, patch: bool, precision: str | None,
        c_msm: str = "same", c_single: bool = False, record: bool = True) -> dict:
    """c_msm: the cached path's memory_saving_mode: "same" (the decided path's), "false", "auto", or "predict-off"
    (the build as the decided path, the cached predictions without the peak-memory chunking). c_single: the cached
    path with one cache per estimator (tabpfn's max_batched_estimator_rows 0, set for the cached classifier only)."""
    import torch
    from tabpfn import TabPFNClassifier
    from tabpfn.settings import settings

    from src.eda.tabpfn_local import runtime
    X_train, y_train, Xq, C = data(rows)
    if patch:
        runtime.prepare()
    else:
        torch.cuda.set_per_process_memory_fraction(runtime.MEMORY_FRACTION)
    cfg = {**C.CONFIG, "n_estimators": estimators}
    base = {"model_path": str(runtime.checkpoint_path()), "device": "cuda", "memory_saving_mode": msm, **cfg,
            "random_state": seed}
    out: dict = {"rows": int(len(X_train)), "test_rows": int(len(Xq)), "estimators": estimators, "seed": seed,
                 "memory_saving_mode": msm, "gqa_patch": patch, "kv_cache_precision": precision, "c_msm": c_msm,
                 "c_single": c_single}
    c_extra = {"fit_mode": "fit_with_cache", "kv_cache_precision": precision}
    if c_msm in ("false", "auto"):
        c_extra["memory_saving_mode"] = False if c_msm == "false" else "auto"
    probs, recs = {}, {}
    before = settings.tabpfn.max_batched_estimator_rows
    for name, extra in (("A", {}), ("C", c_extra)):
        rec = Recorder() if record else None
        if name == "C" and c_single:
            settings.tabpfn.max_batched_estimator_rows = 0
        try:
            clf = TabPFNClassifier(**{**base, **extra})
            t0 = time.monotonic()
            clf.fit(X_train, y_train)
            t1 = time.monotonic()
            if name == "C" and c_msm == "predict-off":
                clf.executor_.save_peak_mem = False
            probs[name] = clf.predict_proba(Xq)[:, 1]
            torch.cuda.synchronize()
            out[f"{name}_seconds"] = {"fit": round(t1 - t0, 2), "predict": round(time.monotonic() - t1, 2)}
            if name == "C":
                out["C_caches"] = len(clf.executor_.kv_caches)
                t2 = time.monotonic()
                again = clf.predict_proba(Xq)[:, 1]
                out["C_seconds"]["predict_again"] = round(time.monotonic() - t2, 2)
                out["C_repeat_max_abs"] = float(np.max(np.abs(again - probs["C"])))
        finally:
            settings.tabpfn.max_batched_estimator_rows = before
        if rec is not None:
            rec.close()
            recs[name] = rec.calls
        del clf
        torch.cuda.empty_cache()
    out["proba_max_abs"] = float(np.max(np.abs(probs["A"] - probs["C"])))
    out["proba_mean_abs"] = float(np.mean(np.abs(probs["A"] - probs["C"])))
    out["proba_equal_bitwise"] = bool(np.array_equal(probs["A"], probs["C"]))
    if not record:
        return out
    out["calls"] = {k: [{"rows": c["rows"], "n_train": c["n_train"]} for c in v] for k, v in recs.items()}
    a_pred = [c for c in recs["A"] if c["rows"] > c["n_train"]]
    c_pred = [c for c in recs["C"] if c["rows"] < c["n_train"] or c["rows"] == len(Xq)]
    c_build = [c for c in recs["C"] if c["rows"] == c["n_train"]]
    stages = ["x", "agg"] + [f"icl{i:02d}" for i in range(24)] + ["norm", "heads"]
    if a_pred and c_pred:
        a, c = a_pred[-1], c_pred[-1]
        a["parts"]["x"], c["parts"]["x"] = [a["x"]], [c["x"]]
        a_x = a["x"][a["n_train"]:]
        out["test_rows_by_stage"] = {s: compare(a_x if s == "x" else test_rows(a, s), test_rows(c, s)) for s in stages}
    if a_pred and c_build:                              # the training rows: the decided path's against the cache build
        a, b = a_pred[-1], c_build[-1]
        tr = {"x": compare(a["x"][:a["n_train"]], b["x"])}
        for s in ["agg"] + [f"icl{i:02d}" for i in range(24)] + ["norm"]:
            ta, tb = stage_tensor(a, s), stage_tensor(b, s)
            tr[s] = compare(ta[:, :a["n_train"]] if ta is not None else None, tb)
        out["train_rows_by_stage"] = tr
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=4000)
    ap.add_argument("--estimators", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-msm", action="store_true", help="memory_saving_mode False")
    ap.add_argument("--no-patch", action="store_true", help="without the runtime's grouped-query attention patch")
    ap.add_argument("--precision", default="auto")
    ap.add_argument("--c-msm", default="same", choices=("same", "false", "auto", "predict-off"))
    ap.add_argument("--c-single", action="store_true", help="one cache per estimator for the cached path")
    ap.add_argument("--no-record", action="store_true", help="probabilities only (no per-stage tensors)")
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    _, _, _, TWF = _mods()
    free = TWF.wait_for_card(need_gb=12, patience_s=3600, processes=True)
    t0 = time.monotonic()
    out = run(a.rows, a.estimators, a.seed, not a.no_msm, not a.no_patch, a.precision, a.c_msm, a.c_single,
              not a.no_record)
    out.update({"gpu_free_gb_before": round(free, 1), "seconds": round(time.monotonic() - t0, 1)})
    path = DC.OUT / "checks" / f"cache_diag_{a.tag}.json"
    DC.write_json(path, out)
    print(json.dumps({k: v for k, v in out.items() if not k.endswith("by_stage")}, indent=1))
    for key in ("test_rows_by_stage", "train_rows_by_stage"):
        if key in out:
            print(key)
            for s, v in out[key].items():
                print(f"  {s:8s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
