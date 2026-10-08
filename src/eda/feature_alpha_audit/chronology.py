"""Frozen adjperf profile sensitivity to calendar-week tournament dates.

Run: ./python.sh src/eda/feature_alpha_audit/chronology.py
Every event date is moved to the preceding Monday, including Sundays. This is
a sensitivity analysis, NOT an actual-match-date repair. It changes both history
eligibility and decay ages; overlapping fortnight events remain unresolved.
Original studies, constants, outcomes, pool ordering and baselines are untouched.
"""
from __future__ import annotations

import json
import gc
import os
import sys
import time
from pathlib import Path

for _var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_var, "2")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.ufc_ideas import common as U
from src.eda.ufc_ideas import stageB_adjperf as AP
from src.eda.ufc_ideas import stageB_common as B
from src.eda.ufc_ideas import stageD_profile as D

OUT = ROOT / "data/studies/feature_alpha_audit"
FEATURES = OUT / "chronology_calendar_week_features.parquet"
PROFILE = [f"adjperf_{s}|decayed" for s in D.ADJ_STATS] + [f"adjdef_{s}|decayed" for s in D.NO_MIRROR]


def calendar_monday(dates: pd.Series) -> pd.Series:
    """Preceding/same calendar Monday; Sunday also moves backwards six days."""
    d = pd.to_datetime(dates)
    return d - pd.to_timedelta(d.dt.dayofweek, unit="D")


def normalize_rows(rows: pd.DataFrame) -> pd.DataFrame:
    r = rows.copy()
    # Preserve event identity even if two date-distinct records collapse to one week.
    r["tournament_id"] = r["tournament_id"].astype(str) + "|original_date=" + r["tournament_date"].astype(str)
    r["tournament_date"] = calendar_monday(r["tournament_date"])
    return B.F.prepare(r.drop(columns=["day"]))


def frozen_profile(ctx: AP.Ctx, chosen: dict) -> dict[str, np.ndarray]:
    """Original AP algorithm, restricted to profile channels and the decayed form."""
    specs = [(s, "adjperf") for s in D.ADJ_STATS] + [(s, "adjdef") for s in D.NO_MIRROR]
    wanted = sorted({(s, ch, AP.constants_for(chosen, s, ch, t)["h1"],
                      AP.constants_for(chosen, s, ch, t)["tau"])
                     for s, ch in specs for t in B.C.TOURS}, key=str)
    mom = ctx.moments(wanted)
    out = {}
    for s, ch in specs:
        z = np.full(len(ctx.box_idx), np.nan)
        for t in B.C.TOURS:
            c = AP.constants_for(chosen, s, ch, t)
            zt, _, _ = ctx.z(s, ch, mom[(s, ch, c["h1"], c["tau"])], c["K1"], c["tau"])
            m = ctx.tour_box == t
            z[m] = zt[m]
        units, ok = ctx.step3_units(s, ch)
        col = f"{ch}_{s}|decayed"
        out[col] = np.full(len(ctx.A), np.nan)
        for t in B.C.TOURS:
            c = AP.constants_for(chosen, s, ch, t)
            sums = ctx.step3([z], units, ok & (ctx.tour_box == t), c["tau"], (c["h3"],))
            val, _ = ctx.pool_values(sums, AP.form_key("decayed", c["h3"]), 0,
                                     ctx.pool_kref(s, c["K3"], c["tau"]), exists_key="career")
            m = ctx.rows["tour"].to_numpy()[ctx.A] == t
            out[col][m] = val[m]
        print(f"built {col}", flush=True)
    return out


def build_arrays() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    print("loading original rows and frozen constants", flush=True)
    rows, _ = B.load_rows()
    chosen, typ, madpop = AP.load_frozen()
    normalized = normalize_rows(rows)
    date_changed = rows["tournament_date"].ne(normalized["tournament_date"]).to_numpy()[::2]
    del rows
    gc.collect()
    print(f"normalized {int(date_changed.sum()):,} match event dates", flush=True)
    ctx = AP.Ctx(normalized, B.surface_means(), typ=typ, madpop=madpop, stats=D.ADJ_STATS)
    print(f"context: {len(ctx.box_idx):,} box rows; {ctx.P.n_pairs:,} history pairs", flush=True)
    built = frozen_profile(ctx, chosen)
    rebuilt_ids = normalized["match_id"].to_numpy()[ctx.A].copy()
    checkpoint = OUT / "chronology_profile_arrays.npz"
    print("saving numeric checkpoint before any further data reads", flush=True)
    np.savez_compressed(checkpoint, match_id=rebuilt_ids.astype(str),
                        changed_dates=np.asarray(int(date_changed.sum())),
                        total_dates=np.asarray(len(date_changed)), **built)
    print(f"saved {checkpoint}; build seconds {time.time() - t0:.1f}", flush=True)
    del ctx, normalized
    gc.collect()


def main() -> int:
    t0 = time.time()
    if "--assemble-only" not in sys.argv:
        build_arrays()
    if "--build-only" in sys.argv:
        return 0
    cache = np.load(OUT / "chronology_profile_arrays.npz", allow_pickle=False)
    rebuilt_ids = cache["match_id"]
    built = {c: cache[c] for c in PROFILE}
    dates_changed_count = int(cache["changed_dates"])
    dates_total_count = int(cache["total_dates"])
    print("loading pool for assembly", flush=True)
    pool = U.load_pool()
    assert np.array_equal(pool["match_id"], rebuilt_ids)
    original = pd.read_parquet(U.OUT / "stageD_profile_features.parquet", columns=["match_id"] + PROFILE)
    assert np.array_equal(original["match_id"], pool["match_id"])
    delta = []
    for col in PROFILE:
        pool[col] = built[col].astype("float32")
        for tour in B.C.TOURS:
            old = original[col].to_numpy(dtype=float)
            new = pool[col].to_numpy(dtype=float)
            mask = pool["tour"].eq(tour).to_numpy() & pool["evaluation"].to_numpy()
            both = mask & np.isfinite(old) & np.isfinite(new)
            d = new[both] - old[both]
            delta.append({"tour": tour, "column": col, "n": int(both.sum()),
                          "changed_above_1e_6": int((np.abs(d) > 1e-6).sum()),
                          "availability_changed": int((mask & (np.isfinite(old) ^ np.isfinite(new))).sum()),
                          "mean_abs_change": float(np.abs(d).mean()), "max_abs_change": float(np.abs(d).max()),
                          "correlation": float(np.corrcoef(old[both], new[both])[0, 1])})
    pool.to_parquet(FEATURES, index=False, compression="zstd")
    pd.DataFrame(delta).to_csv(OUT / "chronology_feature_deltas.csv", index=False)
    print(f"saved {FEATURES}", flush=True)
    scores = []
    oldframe = pool.copy()
    oldframe[PROFILE] = original[PROFILE]
    # Identical original/normalized sample and original walk-forward fitting rule.
    common = np.isfinite(oldframe[PROFILE].to_numpy()).all(axis=1) & np.isfinite(pool[PROFILE].to_numpy()).all(axis=1)
    for tour in B.C.TOURS:
        task = U.task(tour, "profile_adjperf", "calendar_week_sensitivity", "Adjperf profile", "profile", PROFILE,
                      scores=("elo", "market"), wta_box_from_2019=True)
        for start in (2013, 2019, 2022):
            for variant, frame in (("original", oldframe), ("calendar_week", pool)):
                f = frame.loc[common].copy()
                f["evaluation"] = f["evaluation"] & f["year"].ge(start)
                result = U.score_plain(f, task)
                for base, stats in result.items():
                    scores.append({"tour": tour, "variant": variant, "window_start": start, "base": base,
                                   **{k: v for k, v in stats.items() if k != "coefs"}})
    pd.DataFrame(scores).to_csv(OUT / "chronology_scores.csv", index=False)
    summary = {"method": "All event dates -> preceding/same calendar Monday (Sunday backwards); frozen profile constants.",
               "interpretation": "Sensitivity, not a chronology correction. History eligibility and decay ages change together.",
               "unresolved": ["No actual match timestamps", "Overlapping fortnight events", "Original Elo baselines retained",
                              "Original outcome/identity/data issues retained", "Original unpenalized scorer and match-iid intervals"],
               "matches_date_changed": dates_changed_count, "matches_total": dates_total_count,
               "profile_features": PROFILE, "feature_deltas": delta, "scores": scores,
               "seconds": round(time.time() - t0, 1)}
    (OUT / "chronology_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(pd.DataFrame(scores).to_string(index=False), flush=True)
    print(f"finished in {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        raise
