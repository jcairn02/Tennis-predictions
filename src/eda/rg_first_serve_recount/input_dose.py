"""Read the Roland Garros candidate's input flags against its dose (step 9 of README section 10.3).

compare.py's input check flags an input "uneven" when its scale or level moves in some tour-seasons only. Under the
adoption-by-kind decision of 9 Oct 2026 (docs/decisions/2026-10-09-adoption-by-change-class.md, point 4), a repair's
flag counts as harm only when its dose does not explain it. This reads the candidate's flags against what its tables
change in Stage 0:
    * the dose: by tour and year, the player rows whose service games (Stage 0's hold denominator) are known, in the
      frozen reference's Stage 0 and in the candidate's, and where the two differ (tournament, and whether the
      reference had none);
    * the timing: for WTA 2013-2014, the matches of each flagged input that move materially (more than --threshold of
      the input's WTA SD, or known in one frame only), before Roland Garros 2013, from it to the end of 2013, and in
      2014; and those that go from missing to known.
Reads no result. Writes into <out>/input_dose/: coverage.csv, dose_rows.csv, timing.csv, summary.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/input_dose.py --candidate-stage0 C:/Users/zerom/tnr_sb/data/studies/predictability_diagnostic
           --out data/studies/current_best_model/2026-10-09_rg_box_scores
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402

REF_STAGE0 = (ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "tables" / "data"
              / "studies" / "predictability_diagnostic")
RG2013 = pd.Timestamp("2013-05-26")          # the first day of Roland Garros 2013, the first edition the sets fill
PERIODS = ("before RG 2013", "RG 2013 to end 2013", "2014")


def stage0(folder: Path) -> pd.DataFrame:
    m = pd.read_parquet(folder / "stage0_matches.parquet", columns=["match_id", "tour", "year", "tournament_name"])
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "player_id", "hold_d"])
    return p.merge(m, on="match_id")


def dose(ref_folder: Path, cand_folder: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    r, c = stage0(ref_folder), stage0(cand_folder)
    x = r.merge(c[["match_id", "player_id", "hold_d"]], on=["match_id", "player_id"], suffixes=("_r", "_c"),
                how="outer", indicator=True)
    rows = x["_merge"].value_counts().to_dict()
    x = x[x["_merge"].eq("both")].copy()
    x["known_r"], x["known_c"] = x["hold_d_r"].gt(0), x["hold_d_c"].gt(0)
    coverage = (x.groupby(["tour", "year"]).agg(player_rows=("known_r", "size"), known_reference=("known_r", "sum"),
                                                known_candidate=("known_c", "sum")).reset_index())
    moved = x[x["hold_d_r"].fillna(-1) != x["hold_d_c"].fillna(-1)]
    dose_rows = (moved.groupby(["tour", "year", "tournament_name"])
                 .agg(player_rows=("match_id", "size"), known_in_reference=("known_r", "sum")).reset_index()
                 .sort_values(["year", "tour", "tournament_name"]))
    info = {"player_rows": {str(k): int(v) for k, v in rows.items()}, "hold_d_changed_player_rows": int(len(moved))}
    return coverage, dose_rows, info


def timing(candidate: str, threshold: float) -> tuple[pd.DataFrame, list[str]]:
    _, p_cand, _ = CMP.candidate(candidate)
    ref, cand = CMP.inputs_frame(R.paths("reference")), CMP.inputs_frame(p_cand)
    _, per_input = CMP.input_drift(ref, cand)
    flagged = per_input.loc[per_input["flag"].ne("none"), "input"].tolist()
    w = ref.index[ref["tour"].eq("wta") & ref["season"].isin([2013, 2014])]
    day = pd.to_datetime(ref.loc[w, "tournament_date"])
    period = np.where(day < RG2013, PERIODS[0], np.where(day.dt.year.eq(2013), PERIODS[1], PERIODS[2]))
    rows = []
    for name in flagged:
        a, b = ref.loc[w, f"in_{name}"], cand.loc[w, f"in_{name}"]
        sd = ref.loc[ref["tour"].eq("wta"), f"in_{name}"].std()
        material = ((a - b).abs() / sd > threshold) | (a.isna() != b.isna())
        filled = a.isna() & b.notna()
        for k in PERIODS:
            sel = period == k
            rows.append({"input": name, "period": k, "matches": int(sel.sum()),
                         "material_change": int(material[sel].sum()), "missing_to_known": int(filled[sel].sum())})
    return pd.DataFrame(rows), flagged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate-stage0", required=True, help="the candidate's Stage 0 folder (the sandbox's)")
    ap.add_argument("--out", required=True, help="the candidate build's records folder")
    ap.add_argument("--threshold", type=float, default=1e-3, help="a material change, in the input's WTA SDs")
    a = ap.parse_args()
    out = Path(a.out) / "input_dose"
    out.mkdir(parents=True, exist_ok=True)
    coverage, dose_rows, info = dose(REF_STAGE0, Path(a.candidate_stage0))
    tim, flagged = timing(a.out, a.threshold)
    coverage.to_csv(out / "coverage.csv", index=False)
    dose_rows.to_csv(out / "dose_rows.csv", index=False)
    tim.to_csv(out / "timing.csv", index=False)
    before = tim[tim["period"].eq(PERIODS[0])]
    summary = {
        "flagged_inputs": flagged,
        "threshold_sd": a.threshold,
        **info,
        "wta_known_service_games": {str(int(r.year)): {"reference": int(r.known_reference),
                                                       "candidate": int(r.known_candidate)}
                                    for r in coverage[coverage["tour"].eq("wta") & coverage["year"].isin([2013, 2014,
                                                                                                          2015])]
                                    .itertuples()},
        "material_changes_before_rg2013": int(before["material_change"].sum()),
        "reads_no_result": True,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(tim.pivot(index="input", columns="period", values="material_change").to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
