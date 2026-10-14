"""R2-skeptic (round 2, SVX addendum 2): my scope of the RG 2016-2018 swaps, appended to swaps_scope.csv, and a dry run.

From svx3.py (rg1618_matches.csv): the 103 swaps that pass every test, plus one judged on the evidence:
    wta|2016-520|R128|wta:201597|wta:202653 (Nara d. Allertova, 5-7 6-3 2-0 RET): its only failed check is the file's
        winner flag, which names Allertova. The flag is wrong: Nara plays the next round in Stage 0, and the file's own
        games give Nara 13 to 10, 2-0 up in the third set at the retirement. It is the flag's only disagreement in RG
        2016-2018 (1,316 matches where it is set). Every other test passes: proofs, labels by name, the
        score-and-break identity for the truth and not the row, B8.
Left out:
    wta|2016-520|R16|wta:201325|wta:201594 (Stosur d. Halep, 7-6(0) 6-3): the file proves the truth (Stosur 10,
        Halep 11), but Sackmann's row carries a second error that the exchange does not touch. The file's complete,
        coherent game record has Halep facing 12 break points and losing 3 (Sackmann: 7 and 2). Sackmann's swapped
        counts and his break points are consistent with each other; after the exchange alone the row would not be,
        and Halep's hold rate would move further from the truth (80.0% -> 81.8%, truth 72.7%). Not a clear fix by
        exchange_svgms alone.
The first two rounds' rows (705) are kept as they are (asserted; the table before is kept as swaps_scope_round2a.csv).
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx3_scope.py
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
ON_EVIDENCE = {"wta|2016-520|R128|wta:201597|wta:202653"}
LEFT_OUT = {"wta|2016-520|R16|wta:201325|wta:201594"}


def main() -> int:
    x = pd.read_csv(OUT / "rg1618_matches.csv")
    lead = pd.read_csv(LEAD / "review" / "addendum2_swaps.csv", dtype=str, keep_default_na=False)
    strict = set(x.loc[x["confirm_strict"], "match_id"])
    ev = x[x["match_id"].isin(ON_EVIDENCE)].iloc[0]
    assert (ev["cls"] == "swapped" and bool(ev["proven"]) and bool(ev["labels_by_name"]) and bool(ev["identity_truth"])
            and not bool(ev["identity_row"]) and bool(ev["b8_after_ok"]) and str(ev["winner_agrees"]) == "False"), ev
    good = (strict | ON_EVIDENCE) - LEFT_OUT
    add = lead[lead["match_id"].isin(good)][["source_file", "source_row", "match_id"]]
    prev_path = OUT / "swaps_scope_round2a.csv"
    if not prev_path.exists():
        shutil.copyfile(OUT / "swaps_scope.csv", prev_path)
    prev = pd.read_csv(prev_path, dtype=str, keep_default_na=False)
    assert not add["match_id"].isin(set(prev["match_id"])).any()
    out = pd.concat([prev, add], ignore_index=True)
    assert prev.merge(out, on=list(prev.columns), how="left", indicator=True)["_merge"].eq("both").all()
    out.to_csv(OUT / "swaps_scope.csv", index=False)
    add.to_csv(OUT / "swaps_addendum2_rows.csv", index=False)
    # dry run of the appended rows
    table = lead[lead["match_id"].isin(set(add["match_id"]))]
    raw = pd.read_parquet(OUT / "raw_rg.parquet").reset_index(drop=True)
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    after, done = K.apply_row_corrections(raw.copy(), table)
    rows = done.get("exchange_svgms", pd.Index([]))
    ok = int(((after.loc[rows, "w_SvGms"].to_numpy() == raw.loc[rows, "l_SvGms"].to_numpy())
              & (after.loc[rows, "l_SvGms"].to_numpy() == raw.loc[rows, "w_SvGms"].to_numpy())).sum())
    xi = x.set_index("match_id")
    truth = sum(int(float(after[(after["_source_file"].eq(r.source_file)) & (after["_row"].eq(str(r.source_row)))]
                          .iloc[0]["w_SvGms"]) == xi.loc[r.match_id, "true_w"]) for r in table.itertuples(index=False))
    others = [c for c in raw.columns if c.startswith(("w_", "l_")) and c not in ("w_SvGms", "l_SvGms")]
    res = {"lead": int(len(lead)), "confirmed": int(len(add)), "left_out": sorted(set(lead["match_id"]) - good),
           "confirmed_on_evidence": sorted(ON_EVIDENCE), "scope_total": int(len(out)),
           "dry_run": {"rows_exchanged": int(len(rows)), "rows_reading_exchanged": ok,
                       "rows_reading_the_truth_after": truth,
                       "other_counts_changed": int((after[others].astype(str) != raw[others].astype(str)).to_numpy().sum())}}
    (OUT / "svx3_dry_run.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
