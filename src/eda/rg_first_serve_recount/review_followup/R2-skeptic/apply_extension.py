"""R2-skeptic (round 2, extension): append the extension's confirmed matches (extension.py) to overrides_scope.csv,
keeping every other row as it is (asserted). The table before this step is kept as overrides_scope_v2.csv.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/apply_extension.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def main() -> int:
    before_path = OUT / "overrides_scope_v2.csv"
    if not before_path.exists():
        shutil.copyfile(OUT / "overrides_scope.csv", before_path)
    before = pd.read_csv(before_path, dtype=str, keep_default_na=False)
    add = pd.read_csv(OUT / "extension_scope_rows.csv", dtype=str, keep_default_na=False)[list(before.columns)]
    chk = pd.read_csv(OUT / "extension_check.csv")
    assert set(add["stage0_match_id"]) == set(chk.loc[chk["confirmed"], "stage0_match_id"])
    assert not add["stage0_match_id"].isin(set(before["stage0_match_id"])).any(), "a match is already listed"
    out = pd.concat([before, add], ignore_index=True)
    kept = before.merge(out, on=list(before.columns), how="left", indicator=True)
    assert kept["_merge"].eq("both").all(), "an earlier row changed"
    out.to_csv(OUT / "overrides_scope.csv", index=False)
    print(f"overrides_scope.csv: {len(before)} rows before, {len(out)} after ({len(add)} appended)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
