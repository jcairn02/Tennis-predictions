"""R2-skeptic (round 2): is RG's record the faulty one on the small differences? The honest referee tally.

The lead's tally (brief E2) leaves out the 13 matches where a referee read the row's value ("referee_contradicts"), so
its zeros are partly by construction. This tally counts every 2022-2025 match the proposal considered after its
earlier classes (proposed or referee_contradicts), per count that changes and per direction of the change, for each
independent record that holds every point of the player row:
    cv    the Court Vision copy, RG 2022 only (a referee there, report § 2.5), recounted by me in round 1
          (review/R2-skeptic/cv2022_sides.csv); the lead's cv_* columns are compared with it
    mcp   the Match Charting Project's hand charts (the lead's link, whole_box_rows.csv mcp_*)
"Holds every point": the referee's serve points equal RG's or the row's.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    referee_tally.json   per count, direction and referee: reads RG's value / the row's / neither; the CV check
    referee_rows.csv     every player row where a referee holds every point and a count changes, with the readings
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/referees.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
R1 = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
COUNTS = {"svpt": "svpt", "ace": "ace", "df": "df", "1stIn": "first_in", "1stWon": "first_won", "2ndWon": "second_won"}


def main() -> int:
    s = pd.read_parquet(OUT / "players.parquet")
    w = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False).rename(columns={"raw_side": "side"})
    s = s.merge(w[["match_id", "side", "cls"] + [f"{r}_{c}" for r in ("cv", "mcp") for c in COUNTS.values()]],
                on=["match_id", "side"], how="left")
    # my own Court Vision 2022 recount (round 1), keyed by the raw CSV row and side
    cv = pd.read_csv(R1 / "cv2022_sides.csv", low_memory=False)
    cv = cv[["source_file", "source_row", "side", "cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won", "cv_ace",
             "cv_df"]].rename(columns={c: "my" + c for c in ["cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won",
                                                              "cv_ace", "cv_df"]})
    s["source_row_i"] = pd.to_numeric(s["source_row"], errors="coerce")
    cv["source_row_i"] = pd.to_numeric(cv["source_row"], errors="coerce")
    s = s.merge(cv.drop(columns="source_row"), on=["source_file", "source_row_i", "side"], how="left")
    check = s[s["year"].eq(2022) & s["mycv_svpt"].notna()]
    cv_check = {"rows_2022_with_my_cv": int(len(check)),
                "lead_cv_equals_mine_all_six": int(np.all([check[f"cv_{c}"].eq(check[f"mycv_{c}"])
                                                           for c in COUNTS.values()], axis=0).sum())}
    scope = s[s["year"].between(2022, 2025) & s["cls"].isin(["proposed", "referee_contradicts"])].copy()
    tally, rows = {}, []
    for short, c in COUNTS.items():
        raw, off = scope[f"raw_{short}"], scope[f"my_{short}"]
        moves = raw.notna() & off.notna() & raw.ne(off)
        direction = np.where(raw > off, "row_higher", "row_lower")
        tally[c] = {"player_rows_changing": int(moves.sum()),
                    "row_higher": int((moves & (raw > off)).sum()), "row_lower": int((moves & (raw < off)).sum())}
        for ref, col, ok in (("cv2022", "mycv", scope["year"].eq(2022)), ("mcp", "mcp", pd.Series(True, index=scope.index))):
            full = ok & (scope[f"{col}_svpt"].eq(scope["my_svpt"]) | scope[f"{col}_svpt"].eq(scope["raw_svpt"]))
            h = moves & full & scope[f"{col}_{c}"].notna()
            reads_rg = h & scope[f"{col}_{c}"].eq(off)
            reads_row = h & scope[f"{col}_{c}"].eq(raw)
            for d in ("row_higher", "row_lower"):
                k = h & (direction == d)
                tally[c][f"{ref}:{d}"] = {"held": int(k.sum()), "reads_rg": int((reads_rg & k).sum()),
                                          "reads_row": int((reads_row & k).sum())}
            for i in scope.index[h]:
                x = scope.loc[i]
                rows.append({"match_id": x["match_id"], "side": x["side"], "year": x["year"], "draw": x["draw"],
                             "code": x["code"], "player": x["player"], "cls": x["cls"], "count": c, "referee": ref,
                             "raw": x[f"raw_{short}"], "rg": x[f"my_{short}"], "ref_value": x[f"{col}_{c}"],
                             "reads": "rg" if reads_rg[i] else "row" if reads_row[i] else "neither"})
    rr = pd.DataFrame(rows)
    rr.to_csv(OUT / "referee_rows.csv", index=False)
    by_match = rr.groupby("match_id")["reads"].agg(lambda x: "row" if (x == "row").any() else
                                                   ("rg" if (x == "rg").any() else "neither"))
    out = {"cv_check": cv_check, "tally": tally,
           "matches_where_a_referee_holds_a_changing_count": int(len(by_match)),
           "matches_any_reading_row": int(by_match.eq("row").sum()),
           "matches_reading_rg_only": int(by_match.eq("rg").sum()),
           "matches_neither_only": int(by_match.eq("neither").sum()),
           "row_readings": rr[rr["reads"].eq("row")][["match_id", "side", "code", "player", "count", "referee", "raw",
                                                      "rg", "ref_value", "cls"]].to_dict("records")}
    (OUT / "referee_tally.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "row_readings"}, indent=1, default=str))
    print(pd.DataFrame(out["row_readings"]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
