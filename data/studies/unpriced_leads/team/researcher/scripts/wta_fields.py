"""R1 researcher scratch: outcome-free field census of the staged WTA API tables.

1. Advanced statistics: every distinct `path`, flagging anything speed-like (serve speed for women is the gap).
2. Umpire event log: distinct event `type`/`name`/`reason` values, and counts of medical / physio / toilet /
   coaching-type events by year (no result is read; event counts only).

Run: ./python.sh data/studies/unpriced_leads/team/researcher/scripts/wta_fields.py
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1] / "wta_fields.json"


def read(f: str, cols: list[str]) -> pd.DataFrame:
    """Read columns by their first occurrence (some staged files repeat `year`)."""
    pf = pq.ParquetFile(f)
    names = pf.schema_arrow.names
    idx = [names.index(c) for c in cols]
    t = pf.read()
    return pd.DataFrame({c: t.column(i).to_pandas() for c, i in zip(cols, idx)})


def main() -> None:
    res: dict = {}
    paths: dict[str, set] = {}
    for f in sorted(glob.glob(str(ROOT / "data/dump/points/wta/advanced/*.parquet"))):
        yr = Path(f).stem
        d = read(f, ["path"])
        paths[yr] = set(d["path"].astype(str).unique())
    allp = sorted(set().union(*paths.values()))
    res["advanced_n_paths"] = len(allp)
    res["advanced_speed_like"] = [p for p in allp if any(k in p.lower() for k in ("speed", "kmh", "mph", "veloc"))]
    res["advanced_paths_by_year_n"] = {k: len(v) for k, v in paths.items()}
    res["advanced_paths_sample"] = allp[:400]
    ev = []
    for f in sorted(glob.glob(str(ROOT / "data/dump/points/wta/events/*.parquet"))):
        d = read(f, ["tournament_id", "year", "match_id", "type", "name", "reason"]); d["match_id"] = d["tournament_id"].astype(str) + ":" + d["year"].astype(str) + ":" + d["match_id"].astype(str)
        ev.append(d)
    e = pd.concat(ev, ignore_index=True)
    res["events_rows"] = int(len(e))
    res["events_type_counts"] = e["type"].astype(str).value_counts().head(60).to_dict()
    res["events_name_counts"] = e["name"].astype(str).value_counts().head(80).to_dict()
    res["events_reason_counts"] = e["reason"].astype(str).value_counts().head(60).to_dict()
    key = e["type"].astype(str) + "|" + e["name"].astype(str) + "|" + e["reason"].astype(str)
    med = key.str.contains("medic|physio|trainer|doctor|injur|toilet|bathroom|comfort|coach|retire|heat|cool",
                           case=False, regex=True)
    sub = e[med].assign(key=key[med])
    res["medical_like_by_year"] = sub.groupby(["year", "key"]).size().unstack(fill_value=0).to_dict(orient="index")
    res["matches_with_any_medical_like_by_year"] = sub.groupby("year")["match_id"].nunique().to_dict()
    res["matches_with_events_by_year"] = e.groupby("year")["match_id"].nunique().to_dict()
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "advanced_paths_sample"}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
