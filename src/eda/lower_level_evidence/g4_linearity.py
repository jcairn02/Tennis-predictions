"""G4 of the role-08 candidate (lower-level evidence): are the 17 forms and points_52w linear in the offsets? And, when
points_52w is not, its exact value at half the offsets for the FP_half arm.

Run inside the built sandbox's code and tables: the script puts the sandbox first on sys.path, so stageB_adjperf and
stage4_features (the sandbox's patched copies) read the sandbox's own Stage B constants (stageB_adj_summary.json),
Stage 4 constants and rows. For each scale in (0, 0.5, 1) it sets the hook's config (translate_hooks: scale x every
offset; the offsets files are the build's) and recomputes, in memory, without writing anything to the sandbox:
    forms       stageB_adjperf.build at the frozen constants -> the 17 decayed forms (float64) of every pool match
    points_52w  stage4_features: history_sums (all statistics, as the build), the format rules, matchup("mu_points",
                "52 weeks")
Checks: scale 0 must reproduce the reference frame's column and scale 1 FP's (after the float32 cast the chain applies:
exactly); the forms must satisfy f(0.5) = (f(0) + f(1)) / 2 to 1e-9; points_52w's departure from linearity is measured,
and its scale-0.5 column is kept (g4_points_half.parquet) when scales 0 and 1 reproduce both frames exactly.
Writes candidates/checks/g4_linearity.json and g4_points_half.parquet. No result is read.
Run: ./python.sh src/eda/lower_level_evidence/g4_linearity.py --sandbox C:/Users/zerom/tnr_lle
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
CAND = REPO / "data" / "studies" / "lower_level_evidence" / "candidates"
CHECKS = CAND / "checks"
REF_FRAME = REPO / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance" / \
    "model_frame.parquet"
FP_FRAME = CAND / "FP" / "model_frame.parquet"
SCALES = (0.0, 0.5, 1.0)
TOL = 1e-9


def log(msg: str) -> None:
    print(f"[g4 {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def set_scale(scale: float) -> None:
    cfg = json.loads((CAND / "hook_config_FP.json").read_text(encoding="utf-8"))
    cfg.update({"scale": scale, "estimate_forms": False, "what": f"G4: scale {scale}"})
    p = CHECKS / f"g4_config_{scale}.json"
    p.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    os.environ["LLE_TRANSLATE"] = str(p)


def frame_cols(path: Path, cols: list[str]) -> pd.DataFrame:
    f = pd.read_parquet(path, columns=["match_id"] + cols)
    return f.set_index("match_id")


def compare_to_frames(name: str, ids: np.ndarray, vals: dict, col: str) -> dict:
    """float32 casts of the scale-0 and scale-1 values against the reference's and FP's frame columns."""
    out = {}
    for scale, path, label in ((0.0, REF_FRAME, "reference"), (1.0, FP_FRAME, "FP")):
        f = frame_cols(path, [col])[col]
        v = pd.Series(np.asarray(vals[scale], dtype=np.float32).astype(np.float64), index=ids)
        common = f.index.intersection(v.index)
        a, b = f.loc[common].to_numpy(float), v.loc[common].to_numpy(float)
        same_nan = bool(np.array_equal(np.isnan(a), np.isnan(b)))
        both = np.isfinite(a) & np.isfinite(b)
        gap = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
        out[label] = {"frame_matches": int(len(f)), "found": int(len(common)), "largest_difference": gap,
                      "same_missing": same_nan, "exact": bool(len(common) == len(f) and gap == 0.0 and same_nan)}
    return out


def forms(sandbox: Path) -> dict:
    from src.eda.lower_level_evidence import translate_hooks as H
    from src.eda.ufc_ideas import stageB_adjperf as AP
    from src.eda.ufc_ideas import stageB_common as B
    assert Path(AP.__file__).resolve().is_relative_to(sandbox.resolve()), AP.__file__
    rows, _ = B.load_rows()
    means = B.surface_means()
    chosen, typ, madpop = AP.load_frozen()
    ctx = AP.Ctx(rows, means, typ=typ, madpop=madpop)
    stats = tuple(dict.fromkeys(s for s, _ in H.FORM_SPECS))
    ids = rows["match_id"].to_numpy()[ctx.A]
    vals = {}
    for scale in SCALES:
        set_scale(scale)
        t0 = time.time()
        built = AP.build(ctx, chosen, stats=stats)["features"]
        vals[scale] = {H.input_name(s, ch): np.asarray(built[f"{ch}_{s}|decayed"], float) for s, ch in H.FORM_SPECS}
        log(f"forms at scale {scale}: {time.time() - t0:.0f} s")
    out = {"inputs": {}}
    ok = True
    for name in vals[0.0]:
        f0, fh, f1 = vals[0.0][name], vals[0.5][name], vals[1.0][name]
        both = np.isfinite(f0) & np.isfinite(fh) & np.isfinite(f1)
        dev = float(np.max(np.abs(fh[both] - (f0[both] + f1[both]) / 2))) if both.any() else 0.0
        rep = compare_to_frames(name, ids, {0.0: f0, 1.0: f1}, f"in_{name}")
        lin = dev < TOL and bool(np.array_equal(np.isnan(f0), np.isnan(fh)))
        out["inputs"][name] = {"largest_departure_from_midpoint": dev, "linear": lin, "reproduces": rep}
        ok &= lin and rep["reference"]["exact"] and rep["FP"]["exact"]
    out["pass"] = bool(ok)
    return out


def points(sandbox: Path) -> tuple[dict, pd.DataFrame | None]:
    from src.eda.predictability_diagnostic import stage4_features as F4
    from src.eda.predictability_diagnostic.scheduled_format import scheduled_format
    assert Path(F4.__file__).resolve().is_relative_to(sandbox.resolve()), F4.__file__
    rows, typical = F4.load_rows()
    xd = F4.stat_xd(rows)
    pbp = F4.pbp_history(rows)
    ctx, _ = F4.constants(rows, xd, typical, pbp)
    pool = F4.pool_mask(rows)
    A = np.flatnonzero(pool) * 2
    Bi = A + 1
    ids = rows["match_id"].to_numpy()[A]
    base = {"bo5": F4.best_of_five(rows, ctx.get("format_from", "scheduled")), "rule": F4.deciding_rules(rows),
            "format": scheduled_format(rows)["format"].to_numpy()}
    vals = {}
    for scale in SCALES:
        set_scale(scale)
        t0 = time.time()
        S = {"hist": F4.history_sums(rows, xd, ctx), **base}
        vals[scale] = np.asarray(F4.matchup(rows, S, ctx, "mu_points", "52 weeks", A, Bi), float)
        log(f"points_52w at scale {scale}: {time.time() - t0:.0f} s")
    f0, fh, f1 = vals[0.0], vals[0.5], vals[1.0]
    both = np.isfinite(f0) & np.isfinite(fh) & np.isfinite(f1)
    dev = np.abs(fh[both] - (f0[both] + f1[both]) / 2)
    rep = compare_to_frames("points_52w", ids, {0.0: f0, 1.0: f1}, "in_points_52w")
    accepted = rep["reference"]["exact"] and rep["FP"]["exact"]
    out = {"largest_departure_from_midpoint": float(dev.max()) if len(dev) else 0.0,
           "median_departure_from_midpoint": float(np.median(dev)) if len(dev) else 0.0,
           "linear": bool(len(dev) == 0 or dev.max() < TOL), "reproduces": rep, "half_column_accepted": bool(accepted),
           "note": "points_52w passes the shrunk 52-week rates through logit and the iid match model: not linear by "
                   "construction; FP_half takes its exact value at scale 0.5 when scales 0 and 1 reproduce both frames"}
    half = pd.DataFrame({"match_id": ids, "points_52w_half": np.asarray(fh, dtype=np.float32).astype(np.float64)})
    return out, half if accepted else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--only", choices=("forms", "points"), default=None)
    a = ap.parse_args()
    sb = Path(a.sandbox)
    if not (sb / "src" / "eda" / "lower_level_evidence" / "translate_hooks.py").exists():
        raise SystemExit(f"{sb}: not a patched sandbox")
    sys.path.insert(0, str(sb))
    for k in [k for k in sys.modules if k == "src" or k.startswith("src.")]:
        del sys.modules[k]
    CHECKS.mkdir(parents=True, exist_ok=True)
    path = CHECKS / "g4_linearity.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    res.update({"what": "G4: the 17 forms and points_52w recomputed by the sandbox's code at scales 0, 0.5 and 1 of "
                        "the offsets", "sandbox": str(sb), "tolerance": TOL})
    if a.only in (None, "forms"):
        res["forms"] = forms(sb)
        path.write_text(json.dumps(res, indent=1), encoding="utf-8")
        log(f"forms pass: {res['forms']['pass']}")
    if a.only in (None, "points"):
        res["points_52w"], half = points(sb)
        if half is not None:
            half.to_parquet(CHECKS / "g4_points_half.parquet", index=False)
        path.write_text(json.dumps(res, indent=1), encoding="utf-8")
        log(f"points_52w: linear {res['points_52w']['linear']}, half accepted {res['points_52w']['half_column_accepted']}")
    os.environ.pop("LLE_TRANSLATE", None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
