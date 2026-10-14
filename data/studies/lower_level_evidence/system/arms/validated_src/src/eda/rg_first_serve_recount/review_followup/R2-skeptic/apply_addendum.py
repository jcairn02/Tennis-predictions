"""R2-skeptic (round 2, addendum): update overrides_scope.csv with the addendum's confirmed matches (addendum.py).

    QM080 (Maestrelli-Noguchi 2026): its row is replaced; only the two service-game counts may change (blank -> the
        exact count), and the eight counts must be the row's as confirmed before
    the added matches I confirm: appended, with my values
    every other row: left as it is (checked)
The pre-addendum table is kept as overrides_scope_v1.csv. Usage:
./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/apply_addendum.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
QM080 = "atp|2026-520|Q1|atp:200677|atp:208353"


def main() -> int:
    v1_path = OUT / "overrides_scope_v1.csv"
    if not v1_path.exists():
        shutil.copyfile(OUT / "overrides_scope.csv", v1_path)
    v1 = pd.read_csv(v1_path, dtype=str, keep_default_na=False)
    add = pd.read_csv(OUT / "addendum_scope_rows.csv", dtype=str, keep_default_na=False)
    chk = pd.read_csv(OUT / "addendum_check.csv")
    cols = list(v1.columns)
    add = add[cols]
    new_rows = add[~add["stage0_match_id"].eq(QM080)]
    assert not new_rows["stage0_match_id"].isin(set(v1["stage0_match_id"])).any(), "an added match is already listed"
    assert set(new_rows["stage0_match_id"]) <= set(chk.loc[chk["confirmed"] & chk["what"].eq("added"),
                                                           "stage0_match_id"])
    out = v1.copy()
    if QM080 in set(add["stage0_match_id"]):
        old = v1[v1["stage0_match_id"].eq(QM080)].iloc[0]
        new = add[add["stage0_match_id"].eq(QM080)].iloc[0]
        moved = [c for c in cols if old[c] != new[c]]
        assert set(moved) <= {"w_SvGms", "l_SvGms"}, moved
        out.loc[out["stage0_match_id"].eq(QM080), cols] = new[cols].to_numpy()
        print("QM080 replaced:", {c: (old[c], new[c]) for c in moved})
    else:
        out = out[~out["stage0_match_id"].eq(QM080)]
        print("QM080 removed")
    out = pd.concat([out, new_rows], ignore_index=True)
    untouched = v1[~v1["stage0_match_id"].eq(QM080)].merge(out, on=cols, how="left", indicator=True)
    assert untouched["_merge"].eq("both").all(), "a pre-addendum row changed"
    out.to_csv(OUT / "overrides_scope.csv", index=False)
    print(f"overrides_scope.csv: {len(v1)} rows before, {len(out)} after ({len(new_rows)} appended)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
