"""R3-referee, group SVX addendum: append the confirmed addendum swaps to swaps_scope.csv, add "SVX_addendum" to
verdict.json (once).

An addendum swap is confirmed when (svx_addendum.py, svx_simulate.py --tag _add):
    - the row's two counts are the truth's two exchanged and the truth's two differ, the first server being proven by
      the file under my stricter test, or, where the file is irregular, named by an independent record holding the
      match whose service games equal the truth;
    - MatchBeats' own count of completed non-tiebreak games equals the truth;
    - no independent record holding the match reads the row or names another first server;
    - with the candidate as confirmed (its 323 round-1 swaps included), the swap changes only the row's two counts,
      exchanged, which then equal the truth, and the row passes Stage 0's checks (B5, B8).
Writes swaps_scope.csv (the 323 rows kept, the confirmed ones appended; the round-1 file kept as
swaps_scope_round1.csv) and svx_add_scope.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_addendum_scope.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    v = json.loads((F.OUT / "verdict.json").read_text(encoding="utf-8"))
    if "SVX_addendum" in v:
        raise SystemExit("verdict.json already has an SVX_addendum entry")
    if not (F.OUT / "swaps_scope_round1.csv").exists():
        shutil.copy2(F.OUT / "swaps_scope.csv", F.OUT / "swaps_scope_round1.csv")
    r1 = pd.read_csv(F.OUT / "swaps_scope_round1.csv", dtype=str, keep_default_na=False)
    d = pd.read_csv(F.OUT / "svx_add_rows.csv", low_memory=False)
    sim = pd.read_csv(F.OUT / "svx_sim_rows_add.csv", index_col=0)
    ad = pd.read_csv(F.FOLLOW / "review" / "addendum_swaps.csv", dtype=str, keep_default_na=False)
    ad["key"] = F.rowkey(ad["source_file"], ad["source_row"])
    p = d.set_index("key").reindex(ad["key"])
    cvh = p["cv_holds"].fillna(False).astype(bool)
    mch = p["mcp_holds"].fillna(False).astype(bool)
    t = pd.DataFrame({"key": ad["key"].to_numpy()})
    swapped_shape = (p["true_w"].ne(p["true_l"]) & p["row_w"].eq(p["true_l"]) & p["row_l"].eq(p["true_w"])).to_numpy()
    proven = p["my_cls"].eq("swapped").to_numpy()
    by_record = ((cvh & p["cv_first_agrees"].astype(str).eq("True"))
                 | (mch & p["mcp_first_agrees"].astype(str).eq("True") & p["mcp_reading"].eq("truth"))).to_numpy()
    t["swapped"] = swapped_shape & (proven | by_record)
    t["first_server_by_file"] = proven
    t["first_server_by_record_only"] = swapped_shape & ~proven & by_record
    t["mb_equals_truth"] = (p["mb_w"].eq(p["true_w"]) & p["mb_l"].eq(p["true_l"])).to_numpy()
    # a record against: it reads the row, or names another first server; Court Vision's own one-game glitches (a
    # game with points of both servers) are not readings of the row
    against = ((cvh & (p["cv_reading"].eq("row") | p["cv_first_agrees"].astype(str).eq("False")))
               | (mch & (p["mcp_reading"].isin(["row", "neither"]) | p["mcp_first_agrees"].astype(str).eq("False"))))
    t["no_record_against"] = (~against).to_numpy()
    s = sim.reindex(ad["key"])
    t["full_after_no_b5_b8"] = (s["B_box_status"].eq("full") & ~s["B_B5"].fillna(False).astype(bool)
                                & ~s["B_B8"].fillna(False).astype(bool)).to_numpy()
    tests = ["swapped", "mb_equals_truth", "no_record_against", "full_after_no_b5_b8"]
    t["confirmed"] = t[tests].all(axis=1)
    conf = ad[t["confirmed"].to_numpy()][["source_file", "source_row", "match_id"]]
    out = pd.concat([r1, conf], ignore_index=True)
    if out.duplicated(["source_file", "source_row"]).any():
        raise SystemExit("a swap named twice")
    out.to_csv(F.OUT / "swaps_scope.csv", index=False)
    smry = {"addendum_swaps": int(len(ad)), "confirmed": int(len(conf)),
            "tests_failed": {c: int((~t[c]).sum()) for c in tests},
            "first_server_by_record_only": t.loc[t["first_server_by_record_only"], "key"].tolist(),
            "held_by_a_record": int((cvh | mch).sum()), "scope_rows_after": int(len(out))}
    (F.OUT / "svx_add_scope.json").write_text(json.dumps(smry, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
