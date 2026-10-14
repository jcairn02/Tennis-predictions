"""F1: rows outside the proposed 2,382 that carry the same fault (listed for the lead; not part of the confirmed scope).

    * matches of the 30 events that Stage 0 dropped only because of B6 (double faults exceed svpt - first_in), which is
      impossible when serve points include double faults, and that pass every check after svpt := svpt + df;
    * Doha 2015 rows whose MCP chart shows serve points without double faults (the semi-final and final).
Writes f1_extension_rows.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

ev = pd.read_csv(rc.AUD / "box_wta2015_events.csv", parse_dates=["tournament_date"])
events = ev[ev["in_fault"]][["tournament_date", "tournament_name"]]
m, p = rc.stage0()
mm = m[m["tour"].eq("wta") & m["year"].eq(2015) & ~m["qualifying"]].merge(events, on=["tournament_date", "tournament_name"])
bad = mm[mm["box_status"].eq("failed_check")]
raw = pd.read_parquet(rc.SACK / "wta" / "wta_matches_2015.parquet").set_index(["_source_file", "_row"])
rows = []
for _, r in bad.iterrows():
    rr = raw.loc[(r["source_file"], r["source_row"])]
    w, l_ = rc.raw_counts(rr.to_frame().T, "w"), rc.raw_counts(rr.to_frame().T, "l")
    w, l_ = w.reset_index(drop=True).astype(float), l_.reset_index(drop=True).astype(float)
    c0 = rc.box_checks(w, l_, pd.Series([r["score"]]), pd.Series([r["status"]]), pd.Series([r["status_detail"]]))
    w2, l2 = w.copy(), l_.copy()
    w2["svpt"] += w2["df"]
    l2["svpt"] += l2["df"]
    c1 = rc.box_checks(w2, l2, pd.Series([r["score"]]), pd.Series([r["status"]]), pd.Series([r["status_detail"]]))
    only_b6 = bool(c0["B6"][0]) and not any(bool(c0[k][0]) for k in ["B0", "B1", "B2", "B3", "B4", "B7", "B8", "B9"])
    if only_b6 and bool(c1["has_box"][0]):
        for side, who in (("w", "winner"), ("l", "loser")):
            rows.append({"group": "fails only B6 now; passes after the fix", "match_id": r["match_id"],
                         "player_id": f"wta:{rr[f'{who}_id']}", "player_name": rr[f"{who}_name"],
                         "tournament": r["tournament_name"], "round": r["round"], "_source_file": r["source_file"],
                         "_row": r["source_row"], "raw_side": side,
                         "svpt_old": (w if side == "w" else l_)["svpt"][0], "df": (w if side == "w" else l_)["df"][0]})
j = pd.read_csv(rc.OUT / "f1_mcp_rows.csv")
d = j[j["tourney_name"].eq("Doha") & j["verdict"].eq("excludes_df")]
for _, r in d.iterrows():
    rows.append({"group": "Doha 2015, MCP shows svpt without double faults", "match_id": None, "player_id": r["pid"],
                 "player_name": r["name"], "tournament": "Doha", "round": r["round"], "_source_file": r["_source_file"],
                 "_row": r["_row"], "raw_side": r["side"], "svpt_old": r["svpt"], "df": r["df"],
                 "mcp_serve_pts": r["serve_pts"]})
out = pd.DataFrame(rows)
# Stage 0 match ids for the Doha rows
for i, r in out[out["match_id"].isna()].iterrows():
    hit = m[(m["source_file"] == r["_source_file"]) & (m["source_row"] == r["_row"])]
    out.loc[i, "match_id"] = hit["match_id"].iloc[0] if len(hit) else None
out.to_csv(rc.OUT / "f1_extension_rows.csv", index=False)
print(out.to_string())
