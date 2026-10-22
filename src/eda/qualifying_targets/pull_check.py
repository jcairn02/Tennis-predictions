"""Step 3: the every-book pull of the qualifying events must change no main-draw price of the model.

The odds step reads OddsTrader's every-book lines only for the events its link (tennis-data rows to OddsTrader events)
assigns to frame matches (odds_sources/table.oddstrader). The qualifying events are not in that link, so the prices of
the instance's main-draw matches should not move when their lines join books_lines.parquet. This checks it: the
instance's OddsTrader sources (every book's last line and Pinnacle's opening, for each frame match) computed before and
after the pull must be equal, cell for cell.

    --before   writes data/studies/qualifying_targets/pull_check_before.parquet
    --after    recomputes and compares; writes pull_check.json

Run: ./python.sh src/eda/qualifying_targets/pull_check.py --before | --after
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import table as OT  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402

BEFORE = C.OUT / "pull_check_before.parquet"
STAGE1 = C.TREE_STUDIES / "predictability_diagnostic" / "stage1_odds.parquet"


def sources() -> tuple[pd.DataFrame, dict]:
    f = OT.frame_rows(C.INSTANCE / "model_frame_chain.parquet", STAGE1)
    return OT.oddstrader(f)


def main() -> int:
    if "--before" in sys.argv:
        ot, counts = sources()
        ot.to_parquet(BEFORE, index=False)
        C.write_json(C.OUT / "pull_check_before.json", {"counts": counts, "books_lines": C.sha256_file(C.OT_BOOKS),
                                                         "rows": int(len(ot))})
        C.log(f"before: {len(ot):,} frame matches, books {counts['books_kept']}")
        return 0
    before = pd.read_parquet(BEFORE)
    after, counts = sources()
    same_cols = list(before.columns) == list(after.columns)
    equal = same_cols and len(before) == len(after) and all(
        np.array_equal(before[c].to_numpy(), after[c].to_numpy(),
                       equal_nan=before[c].dtype.kind == "f") for c in before.columns)
    out = {"rows_before": int(len(before)), "rows_after": int(len(after)), "same_columns": same_cols,
           "equal_cell_for_cell": bool(equal), "books_after": counts["books_kept"],
           "books_lines_after": C.sha256_file(C.OT_BOOKS)}
    if not equal:
        diff = {}
        for c in set(before.columns) & set(after.columns):
            a, b = before[c].to_numpy(), after[c].to_numpy()
            if len(a) == len(b) and not np.array_equal(a, b, equal_nan=a.dtype.kind == "f"):
                diff[c] = int((~((a == b) | (pd.isna(a) & pd.isna(b)))).sum())
        out["differing_cells_by_column"] = diff
    C.write_json(C.OUT / "pull_check.json", out)
    C.log(f"after: equal cell for cell: {equal}")
    return 0 if equal else 4


if __name__ == "__main__":
    sys.exit(main())
