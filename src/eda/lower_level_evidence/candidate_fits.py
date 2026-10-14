"""Local TabPFN-3.5 fits for the role-08 candidate arms that carry extra inputs (R_L and FP_L: low_share_diff; R_S2, the
dated addition: box_low_share_h2w_diff and box_low_share_365d_diff): src/eda/model_rebuild/fits.py line for line, except
that it admits one registered set of extra inputs (kind diff, negated when A and B swap) after the 58. model_rebuild/fits.py itself refuses any frame that does not list 58 inputs, and it is a decided
file, so it is not edited.

Everything else is fits.py's: the serve-speed study's job_data and queries, the local classifier with C.CONFIG (8
estimators, softmax temperature 0.9, pretraining limits ignored), season Y trained on the frame's 2013 .. Y - 1, the
td block (stored, then swapped), the same metadata, one fit at a time on the card (training_window.fits.wait_for_card),
a fit on disk never redone, and fits.py's --wait-memory-only option (added there on 9 Oct 2026, 16:28 UTC: before each
fit, wait only for free memory on the card, not for other local-env processes to exit). compare.py and the scorer read
these files exactly as fits.py's.

G5 (pre-registered): --repro refits the frozen reference's season 2019, seed 0 from the frozen frame into
candidates/checks/g5_repro/ and compares it with the stored fit (largest difference of the td block under 1e-6);
--out refuses to run until that check has passed.

Run: ./python_tabpfn_local.sh src/eda/lower_level_evidence/candidate_fits.py --repro
     ./python_tabpfn_local.sh src/eda/lower_level_evidence/candidate_fits.py --out <arm folder> [--seeds 0-3]
                                                                             [--seasons 2019-2024]
"""
from __future__ import annotations

import argparse
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

from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import local_fits as LF  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402

CAND = ROOT / "data" / "studies" / "lower_level_evidence" / "candidates"
REPRO = CAND / "checks" / "g5_repro"
REPRO_JSON = CAND / "checks" / "g5_fit_runner.json"
FROZEN = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance"
EXTRA = "low_share_diff"
TOL = 1e-6


def paths(out: Path, local: Path | None = None) -> C.Paths:
    """model_rebuild/fits.paths, with the fit folder optionally elsewhere (the reproduction)."""
    return C.DEFAULT.with_(model_frame=out / "model_frame.parquet", model_inputs=out / "model_inputs.json",
                           local=local or (out / "fits"), fi_local=out / "no_fits_here", race_local=out / "no_fits_here")


def span(text: str) -> list[int]:
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


# the registered extra inputs, appended after the 58: R_L and FP_L (pre-registered), R_S2 (the dated addition of 9 Oct)
EXTRAS = ([EXTRA], ["box_low_share_h2w_diff", "box_low_share_365d_diff"])


def admitted(cols: list[str], P: C.Paths) -> bool:
    if len(cols) == 58:
        return True
    kinds, _ = A.kinds_and_partners(cols, P)
    return any(cols[58:] == list(ex) and all(kinds[c] == "diff" for c in ex) for ex in EXTRAS)


def run(out: Path, seasons: list[int], seeds: list[int], local: Path | None = None, frame_label: str = "",
        wait_memory_only: bool = False) -> list[Path]:
    import torch

    from src.eda.tabpfn_local import runtime
    P = paths(out, local)
    arm = "model"
    cols = A.arm_inputs(arm, P)
    if not admitted(cols, P):
        raise SystemExit(f"{out}: {len(cols)} inputs; only the 58, or the 58 plus one registered set of extras "
                         f"{EXTRAS} (kind diff), are admitted")
    frame = A.load_frame([], P, labels=True)
    if not A.check_flip(frame, cols, P):
        raise SystemExit("flip is not an involution")
    ep = LF.early_frame(P)
    frame_sha = C.sha256_file(P.model_frame)
    P.local.mkdir(parents=True, exist_ok=True)
    written = []
    for season in seasons:
        for seed in seeds:
            path = P.local / f"{arm}__{season}__seed{seed}.npz"
            if path.exists():
                continue
            X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
            qs = LF.queries(ep, season, X_test, ids, P)
            names = list(qs)
            X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
            free_gb = TWF.wait_for_card(patience_s=12 * 3600, processes=not wait_memory_only)
            clf = runtime.classifier(**C.CONFIG, random_state=seed)
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
            meta = {"arm": arm, "season": season, "seed": seed, "kind": "fit",
                    "frame": frame_label or f"lower_level_evidence candidate ({out.name})",
                    "runner": "src/eda/lower_level_evidence/candidate_fits.py (model_rebuild/fits.py + one registered "
                              "extra input)",
                    "config": {**C.CONFIG, "random_state": seed}, "train_shape": list(X_train.shape),
                    "train_seasons": [C.TRAIN_FROM, season - 1], "query_rows": {n: int(len(qs[n][0])) for n in names},
                    "columns": list(X_train.columns), "fingerprint": C.fingerprint(X_train, y_train, X_query),
                    "model_frame_sha256": frame_sha, "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            written.append(path)
            C.log(f"{path.name}: {secs:.0f} s, train {X_train.shape}, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return written


def repro() -> int:
    """G5: the frozen reference's season 2019, seed 0, refitted from the frozen frame by this runner."""
    run(FROZEN, [2019], [0], local=REPRO, frame_label="the frozen reference (G5 reproduction)")
    with np.load(REPRO / "model__2019__seed0.npz", allow_pickle=False) as z:
        p_new, ids_new = z["p_td"], z["ids_td"].astype(str)
        meta_new = json.loads(str(z["meta"]))
    with np.load(FROZEN / "fits" / "model__2019__seed0.npz", allow_pickle=False) as z:
        p_old, ids_old = z["p_td"], z["ids_td"].astype(str)
        meta_old = json.loads(str(z["meta"]))
    res = {"what": "G5: candidate_fits.py refits the frozen reference's season 2019, seed 0 from the frozen frame",
           "ids_equal": bool(np.array_equal(ids_new, ids_old)), "rows": int(len(p_new)),
           "largest_difference": float(np.max(np.abs(p_new - p_old))) if len(p_new) == len(p_old) else None,
           "fingerprint_equal": meta_new.get("fingerprint") == meta_old.get("fingerprint"),
           "columns_equal": meta_new.get("columns") == meta_old.get("columns"),
           "train_shape_equal": meta_new.get("train_shape") == meta_old.get("train_shape"),
           "tolerance": TOL, "checked_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    res["pass"] = bool(res["ids_equal"] and res["largest_difference"] is not None and res["largest_difference"] <= TOL
                       and res["columns_equal"] and res["train_shape_equal"])
    REPRO_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPRO_JSON.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res)
    return 0 if res["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--repro", action="store_true")
    g.add_argument("--out")
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--seasons", default="2019-2024")
    ap.add_argument("--wait-memory-only", action="store_true",
                    help="as model_rebuild/fits.py's option (added there on 9 Oct 2026): wait only for free memory on the "
                         "card, not for other local-env processes to exit")
    a = ap.parse_args()
    if a.repro:
        return repro()
    if not (REPRO_JSON.exists() and json.loads(REPRO_JSON.read_text(encoding="utf-8")).get("pass")):
        raise SystemExit("G5 has not passed: run --repro first")
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    if any(s > 2024 for s in span(a.seasons)):
        raise SystemExit("seasons after 2024 are the proposed clean holdout: not fitted here")
    run(out, span(a.seasons), span(a.seeds), wait_memory_only=a.wait_memory_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
