"""Part 4's proof (14 Oct 2026; docs/studies/daily_prediction/process_log.md, part 4): stage 2 re-run on finished runs.

    run <tag> <run name> ...   copies what the predict step reads from each run folder (fit/, the live tables, the
                               gate, the prices, fit.json, states.json, run.json) to checks/stage2_proof/<tag>/<run>/
                               and calls dp_predict.run there (never the predict step: nothing is archived to
                               predictions/). The pattern adjustment is off (UL_PATTERNS_CONFIG -> a missing file), so
                               q_a is stage 2 alone. The run folders are only read; stage 2's record cache
                               (data/studies/daily_prediction/stage2/) is the engine's own and is written as in any run
    diff <tag a> <tag b>       every run both tags hold: predictions.csv and curves.parquet column by column (bit for
                               bit, else the largest difference) and q_a's move in points; writes diff_<a>_<b>.json
    instances                  dp_predict.stage2_keys on every template instance, both feeds, read only: each instance's
                               seeds 0-3 fits must carry one TabPFN record, or the next run on it is refused

The baseline of 14 Oct, made with the code before part 4 (dp_predict.py as written at 07:45), is kept in
checks/stage2_proof/base/ (its outputs only: the code itself is gone).
Run: ./python.sh src/eda/daily_prediction/dp_stage2_proof.py run|diff|instances ...
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

PROOF = DC.OUT / "checks" / "stage2_proof"
READS = ("fit", "live_meta.parquet", "live_stage0.parquet", "live_frame.parquet", "gate.csv", "prices.parquet",
         "fit.json", "states.json", "run.json")
OUTPUTS = ("predictions.csv", "curves.parquet")


def run(tag: str, names: list[str]) -> None:
    os.environ["UL_PATTERNS_CONFIG"] = str(PROOF / "no_adjustment_here.json")   # off: stage 2 alone
    import dp_predict as PR
    for name in names:
        src, dst = DC.RUNS / name, PROOF / tag / name
        if dst.exists():
            raise SystemExit(f"{dst} exists: use a new tag")
        dst.mkdir(parents=True)
        for part in READS:
            if (src / part).is_dir():
                shutil.copytree(src / part, dst / part)
            elif (src / part).exists():
                shutil.copy2(src / part, dst / part)
        states, cfg = DC.read_json(dst / "states.json"), DC.read_json(dst / "run.json")
        a, _, b = cfg["seeds"].partition("-")
        out = PR.run(dst, list(range(int(a), int(b or a) + 1)), Path(cfg["instance"]),
                     checkpoint=Path(states["checkpoint"]).name if states["checkpoint"]
                     else "none: every part from scratch (tier 2)")
        shutil.rmtree(dst / "fit")                    # a copy of the run's own fit: the outputs are what is kept
        prov = DC.read_json(dst / "provenance.json")["stage2"]
        DC.log(f"{name}: {out['matches']} matches, feed {prov.get('feed', 'weekly')}")


def diff(a: str, b: str) -> dict:
    res = {}
    for name in sorted(p.name for p in (PROOF / a).iterdir() if p.is_dir() and (PROOF / b / p.name).is_dir()):
        r = {}
        for f in OUTPUTS:
            read = pd.read_csv if f.endswith(".csv") else pd.read_parquet
            x, y = read(PROOF / a / name / f), read(PROOF / b / name / f)
            cols = {"rows": [len(x), len(y)], "only_in_a": sorted(set(x.columns) - set(y.columns)),
                    "only_in_b": sorted(set(y.columns) - set(x.columns)), "differ": {}}
            for c in [c for c in x.columns if c in y.columns]:
                u, v = x[c], y[c]
                if pd.api.types.is_numeric_dtype(u) and pd.api.types.is_numeric_dtype(v):
                    cmp = DC.compare(u.to_numpy(float), v.to_numpy(float))
                    if not DC.bitwise(cmp):
                        cols["differ"][c] = cmp["max_abs_diff"]
                elif not u.astype(str).equals(v.astype(str)):
                    cols["differ"][c] = "text"
            if f == "predictions.csv":
                d = np.abs((y["q_a"] - x["q_a"]).to_numpy(float)) * 100
                cols["q_a_move_points"] = {"mean_abs": float(d.mean()), "max_abs": float(d.max())}
            r[f] = cols
        res[name] = r
    DC.write_json(PROOF / f"diff_{a}_{b}.json", res)
    print(json.dumps(res, indent=1))
    return res


def instances() -> dict:
    import dp_predict as PR
    out = {}
    for inst in sorted(p for p in (DC.REPO / "data" / "studies" / "current_best_model").glob("template_*") if p.is_dir()):
        for feed in PR.FEED_COLUMN:
            try:
                k = PR.stage2_keys(2026, inst, feed)
                out[f"{inst.name} {feed}"] = {"accepted": True, "fit_files": k["fit_files"], **k["fits_model"]}
            except Exception as e:  # noqa: BLE001 (each instance's refusal is the finding)
                out[f"{inst.name} {feed}"] = {"accepted": False, "why": str(e)}
    DC.write_json(PROOF / "instances.json", out)
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "diff":
        diff(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "instances":
        instances()
    else:
        raise SystemExit(__doc__)
