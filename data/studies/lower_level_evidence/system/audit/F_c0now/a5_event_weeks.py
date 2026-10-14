"""Role E audit of C0_now, part 5: does a source event sit in the week of the Stage 0 tournament it was mapped to?
(the wrong-week / wrong-venue placement risk). For every source: the source event's own Monday against the Stage 0
tournament_date of (a) its linked reference matches and (b) the event it was mapped to (new matches joining it).
Dates, names and counts only. Run: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a5_event_weeks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import candidate_stage0 as F  # noqa: E402  (its loaders read the raw sources)

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
OUT: dict = {}
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=["match_id", "tournament_id", "tournament_date",
                                                               "tournament_name", "map_level", "tour"])
mm = m.set_index("match_id")
adds = pd.read_parquet(CAND / "additions.parquet", columns=["match_id", "sid", "source", "ev_key", "event_tid",
                                                             "event_date", "joins_stage0_event", "map_level", "day"])
for src in ("wta_site", "tennislive", "wta_api", "itf_live", "sofascore"):
    R, _ = F.LOADERS[src]()
    evd = R.drop_duplicates("ev_key").set_index("ev_key")["ev_date"]
    evn = R.drop_duplicates("ev_key").set_index("ev_key")["ev_name"]
    sid_ev = R.set_index("sid")["ev_key"]
    lk = pd.read_parquet(CAND / "evidence" / f"links_{src}.parquet", columns=["sid", "match_id", "sc"])
    lk["ev_key"] = lk["sid"].map(sid_ev)
    lk["src_monday"] = pd.to_datetime(lk["ev_key"].map(evd))
    lk["s0_date"] = pd.to_datetime(lk["match_id"].map(mm["tournament_date"]))
    lk["gap"] = (lk["s0_date"] - lk["src_monday"]).dt.days
    lk["ym"] = lk["s0_date"].dt.strftime("%Y")
    res = {"links": int(len(lk)), "links_gap_ne_0": int(lk["gap"].ne(0).sum()),
           "links_abs_gap_ge_7": int((lk["gap"].abs() >= 7).sum()),
           "links_abs_gap_ge_7_by_year": lk[lk["gap"].abs() >= 7].groupby("ym").size().to_dict()}
    a = adds[adds["source"].eq(src)].copy()
    a["src_monday"] = pd.to_datetime(a["ev_key"].map(evd))
    a["gap"] = (pd.to_datetime(a["event_date"]) - a["src_monday"]).dt.days
    j = a[a["joins_stage0_event"].astype(bool)]
    res["new_joining"] = int(len(j))
    res["new_joining_gap_ne_0"] = int(j["gap"].ne(0).sum())
    res["new_joining_abs_gap_ge_7"] = int((j["gap"].abs() >= 7).sum())
    big = j[j["gap"].abs() >= 7]
    ev = big.groupby(["ev_key", "event_tid", "event_date"]).size().rename("new").reset_index()
    ev["src_name"] = ev["ev_key"].map(evn)
    ev["src_monday"] = ev["ev_key"].map(evd).astype(str)
    ev["s0_name"] = [mm.loc[mm["tournament_id"].eq(t)].iloc[0]["tournament_name"] if (mm["tournament_id"] == t).any()
                     else "" for t in ev["event_tid"]]
    res["new_joining_abs_gap_ge_7_events"] = ev.sort_values("new", ascending=False).head(15).astype(str).to_dict(
        "records")
    res["new_joining_abs_gap_ge_7_by_year_level"] = big.assign(y=pd.to_datetime(big["event_date"]).dt.year).groupby(
        ["y", "map_level"]).size().rename("n").reset_index().to_dict("records")
    OUT[src] = res
    print(src, json.dumps({k: v for k, v in res.items() if not k.endswith("_events")}, default=str), flush=True)
(AUD / "a5_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:15000])
