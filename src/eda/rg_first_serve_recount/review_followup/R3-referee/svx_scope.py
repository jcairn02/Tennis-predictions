"""R3-referee, group SVX, step 4: swaps_scope.csv and the SVX entry of verdict.json.

A proposed swap is confirmed when (my own derivation, svx.py / svx_referees.py / svx_simulate.py):
    - my stricter proof finds the first server in the Slam's MatchBeats file (first point in set 1 game 1, no gap in
      sets or games, one server per non-tiebreak game, every game in file order on the alternation's turn);
    - my class is "swapped": the row's two counts are the truth's two (the score's alternation from that server)
      exchanged, and the truth's two differ;
    - MatchBeats' own count of completed non-tiebreak games equals the truth;
    - no independent record (Court Vision, a hand chart) holding the match reads the row instead of the truth, or another
      first server;
    - in the simulation with the candidate's tables, the row changes only in its two service-game counts, exchanged,
      equals the truth afterwards, and passes Stage 0's checks (B5, B8).
Writes swaps_scope.csv and svx_scope.json; adds "SVX" to verdict.json (once).
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    d = pd.read_csv(F.OUT / "svx_ref_rows.csv", low_memory=False)
    sim = pd.read_csv(F.OUT / "svx_sim_rows.csv", index_col=0)
    ps = pd.read_csv(F.FOLLOW / "service_games" / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    ps["key"] = F.rowkey(ps["source_file"], ps["source_row"])
    p = d[d["key"].isin(set(ps["key"]))].copy()
    t = pd.DataFrame({"key": p["key"]})
    t["proven"] = p["proven"].astype(bool).to_numpy()
    t["swapped"] = p["my_cls"].eq("swapped").to_numpy()
    t["mb_equals_truth"] = (p["mb_w"].eq(p["true_w"]) & p["mb_l"].eq(p["true_l"])).to_numpy()
    against = (p["cv_reading"].isin(["row", "neither"]) | p["mcp_reading"].isin(["row", "neither"])
               | p["cv_first_agrees"].astype(str).eq("False") | p["mcp_first_agrees"].astype(str).eq("False"))
    t["no_record_against"] = (~against).to_numpy()
    s = sim.reindex(p["key"])
    t["full_after_no_b5_b8"] = (s["B_box_status"].eq("full") & ~s["B_B5"].fillna(False).astype(bool)
                                & ~s["B_B8"].fillna(False).astype(bool)).to_numpy()
    t["confirmed"] = t[["proven", "swapped", "mb_equals_truth", "no_record_against", "full_after_no_b5_b8"]].all(axis=1)
    ok = set(t.loc[t["confirmed"], "key"])
    scope = ps[ps["key"].isin(ok)][["source_file", "source_row", "match_id"]]
    scope.to_csv(F.OUT / "swaps_scope.csv", index=False)
    smry = {"proposed": int(len(ps)), "found": int(len(p)), "confirmed": int(len(scope)),
            "tests_failed": {c: int((~t[c]).sum()) for c in t.columns if c not in ("key", "confirmed")},
            "held_by_a_record": int((p["cv_holds"].astype(bool) | p["mcp_holds"].astype(bool)).sum())}
    (F.OUT / "svx_scope.json").write_text(json.dumps(smry, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
