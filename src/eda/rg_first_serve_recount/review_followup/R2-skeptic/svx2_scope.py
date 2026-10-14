"""R2-skeptic (round 2, SVX addendum): append the addendum swaps I confirm (svx2_checks.py ->
swaps_addendum_rows.csv) to swaps_scope.csv, keeping the first round's rows as they are (asserted; the table before is
kept as swaps_scope_round1.csv), and dry-run the appended rows with the build's own apply_row_corrections on the raw
rows of AO 2018-2026 and RG.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx2_scope.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def main() -> int:
    r1_path = OUT / "swaps_scope_round1.csv"
    if not r1_path.exists():
        shutil.copyfile(OUT / "swaps_scope.csv", r1_path)
    r1 = pd.read_csv(r1_path, dtype=str, keep_default_na=False)
    add = pd.read_csv(OUT / "swaps_addendum_rows.csv", dtype=str, keep_default_na=False)
    assert not add["match_id"].isin(set(r1["match_id"])).any(), "an addendum swap is already listed"
    out = pd.concat([r1, add[list(r1.columns)]], ignore_index=True)
    kept = r1.merge(out, on=list(r1.columns), how="left", indicator=True)
    assert kept["_merge"].eq("both").all()
    out.to_csv(OUT / "swaps_scope.csv", index=False)
    # dry run of the appended rows (the lead's rows, as they name the raw rows and their guards)
    lead = pd.read_csv(LEAD / "review" / "addendum_swaps.csv", dtype=str, keep_default_na=False)
    table = lead[lead["match_id"].isin(set(add["match_id"]))]
    raw = pd.concat([pd.read_parquet(OUT / "raw_ao_all.parquet"), pd.read_parquet(OUT / "raw_rg.parquet")],
                    ignore_index=True).drop_duplicates(["_source_file", "_row"])
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    raw = raw.reset_index(drop=True)
    after, done = K.apply_row_corrections(raw.copy(), table)
    rows = done.get("exchange_svgms", pd.Index([]))
    ok = int(((after.loc[rows, "w_SvGms"].to_numpy() == raw.loc[rows, "l_SvGms"].to_numpy())
              & (after.loc[rows, "l_SvGms"].to_numpy() == raw.loc[rows, "w_SvGms"].to_numpy())).sum())
    chk = pd.read_csv(OUT / "svx2_checked.csv").set_index("match_id")
    truth = 0
    for r in table.itertuples(index=False):
        hit = after[after["_source_file"].eq(r.source_file) & after["_row"].eq(str(r.source_row))].iloc[0]
        t = chk.loc[r.match_id]
        truth += int(float(hit["w_SvGms"]) == t["true_w"] and float(hit["l_SvGms"]) == t["true_l"])
    others = [c for c in raw.columns if c.startswith(("w_", "l_")) and c not in ("w_SvGms", "l_SvGms")]
    res = {"round1_rows": int(len(r1)), "appended": int(len(add)), "total": int(len(out)),
           "dry_run": {"rows_exchanged": int(len(rows)), "rows_reading_exchanged": ok,
                       "rows_reading_the_truth_after": truth,
                       "other_counts_changed": int((after[others].astype(str) != raw[others].astype(str)).to_numpy().sum())}}
    (OUT / "svx2_dry_run.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
