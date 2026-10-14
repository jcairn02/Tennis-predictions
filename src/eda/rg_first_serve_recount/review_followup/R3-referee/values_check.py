"""R3-referee (follow-up), step 2: my values against the lead's override rows, and the matches the lead leaves out.

Reads official_rows.csv (official.py: my parse of RG's raw documents and MatchBeats, my links) and the lead's
followup/proposed_overrides.csv and followup/whole_box_rows.csv, and Stage 0's match ids (by source file and row).
For every lead override row: the raw row it names (by the override key), the RG code (feed_key), the eighteen values;
every difference listed. For every RG 2022-2026 raw row not proposed: why (the lead's class) and what my numbers say.

Writes values_check.csv, values_check_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/values_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    o = o[o["season"].between(2022, 2026)].copy()
    ov = pd.read_csv(F.FOLLOW / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    wb = pd.read_csv(F.FOLLOW / "whole_box_rows.csv", low_memory=False)
    m = pd.read_parquet(F.S0 / "stage0_matches.parquet", columns=["match_id", "source", "source_file", "source_row"])
    m["key"] = F.rowkey(m["source_file"], m["source_row"])
    o["key"] = F.rowkey(o["source_file"], o["source_row"])
    o = o.merge(m[["key", "match_id"]].drop_duplicates("key"), on="key", how="left")
    o["ovkey"] = o["source"] + "|" + o["tour"] + "|" + o["tid"] + "|" + o["round"] + "|" + o["wkey"] + "|" + o["lkey"]
    ov["ovkey"] = ov["source"] + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" \
        + ov["loser_key"]
    if o["ovkey"].duplicated().any():
        print("duplicate override keys among my rows:", o.loc[o["ovkey"].duplicated(keep=False), "ovkey"].tolist())
    j = ov.merge(o, on="ovkey", how="left", suffixes=("_lead", ""), indicator=True)
    out = []
    for r in j.to_dict("records"):
        rec = {"feed_key": r["feed_key"], "stage0_match_id_lead": r["stage0_match_id"], "stage0_match_id": r["match_id"],
               "found": r["_merge"] == "both", "source": r["source_lead"], "season": r["season"], "tour": r["tour_lead"],
               "round": r["round_lead"], "winner_name": r["winner_name_lead"], "loser_name": r["loser_name_lead"],
               "my_code": r["code"], "link_min": r["link_min"]}
        rec["code_equal"] = r["feed_key"] == f"rolandgarros:{int(r['season'])}/{r['code']}" if r["_merge"] == "both" else False
        rec["match_id_equal"] = r["stage0_match_id"] == r["match_id"]
        diffs = []
        for s in ("w", "l"):
            for c, col in F.NINE.items():
                lead = pd.to_numeric(r[f"{s}_{col}"], errors="coerce")
                mine = r.get(f"my_{s}_{c}")
                rec[f"lead_{s}_{c}"], rec[f"my_{s}_{c}"] = lead, mine
                if not ((pd.isna(lead) and pd.isna(mine)) or lead == mine):
                    diffs.append(f"{s}_{c}:{lead}/{mine}")
        rec["differences"] = " ".join(diffs)
        rec["my_sv_from"] = r.get("my_sv_from")
        out.append(rec)
    d = pd.DataFrame(out)
    d.to_csv(F.OUT / "values_check.csv", index=False)
    # the lead's classes for the rows not proposed, joined on source file and row
    wb["key"] = F.rowkey(wb["source_file"], wb["source_row"])
    cls = wb.drop_duplicates("key").set_index("key")["cls"]
    o["lead_cls"] = o["key"].map(cls)
    o["proposed"] = o["ovkey"].isin(set(ov["ovkey"]))
    smry = {
        "lead_override_rows": int(len(ov)), "found_by_key": int(d["found"].sum()),
        "rg_code_equal": int(d["code_equal"].sum()), "stage0_match_id_equal": int(d["match_id_equal"].sum()),
        "rows_with_any_value_difference": int(d["differences"].ne("").sum()),
        "value_differences": d.loc[d["differences"].ne(""), ["feed_key", "winner_name", "loser_name", "differences",
                                                              "my_sv_from"]].to_dict("records"),
        "my_rows_2022_2026": int(len(o)), "my_rows_proposed": int(o["proposed"].sum()),
        "not_proposed_by_lead_class": o.loc[~o["proposed"], "lead_cls"].fillna("(not in whole_box_rows)").value_counts()
        .to_dict(),
        "proposed_by_lead_class": o.loc[o["proposed"], "lead_cls"].fillna("(none)").value_counts().to_dict(),
    }
    (F.OUT / "values_check_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str)[:8000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
