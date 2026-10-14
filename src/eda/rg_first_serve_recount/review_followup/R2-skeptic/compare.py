"""R2-skeptic (round 2): my values (link_values.py) against the lead's proposed_overrides.csv, match by match and count
by count; the feed key's code against my link; the document hash against the raw file.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    value_compare.csv        one row per proposed override: my code, the lead's, each of the 18 counts (mine / lead's)
                             and a list of the counts that differ
    value_compare.json       summary
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/compare.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
RAW = ROOT / "data" / "raw" / "point_sources" / "rolandgarros" / "matches"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def main() -> int:
    s = pd.read_parquet(OUT / "players.parquet")
    ov = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    rows = []
    for o in ov.itertuples(index=False):
        g = s[s["match_id"].eq(o.stage0_match_id)]
        rec = {"feed_key": o.feed_key, "stage0_match_id": o.stage0_match_id}
        if len(g) != 2:
            rec["problem"] = f"{len(g)} of my player rows"
            rows.append(rec)
            continue
        year, code = o.feed_key.split(":")[1].split("/")
        rec["my_code"], rec["lead_code"] = g["code"].iloc[0], code
        rec["code_agrees"] = g["code"].iloc[0] == code
        diffs = []
        for side in ("w", "l"):
            x = g[g["side"].eq(side)].iloc[0]
            for c in NINE:
                mine = x[f"my_{c}"]
                lead = o._asdict()[f"{side}_{c}"]
                lead_v = float(lead) if lead != "" else np.nan
                rec[f"my_{side}_{c}"], rec[f"lead_{side}_{c}"] = mine, lead_v
                same = (pd.isna(mine) and pd.isna(lead_v)) or (pd.notna(mine) and pd.notna(lead_v)
                                                               and float(mine) == lead_v)
                if not same:
                    diffs.append(f"{side}_{c}")
        rec["differs"] = ";".join(diffs)
        # the document hash: of the raw file as saved, and of its decompressed body
        p = RAW / year / f"{code}.json.gz"
        blob = p.read_bytes()
        rec["sha_file"] = hashlib.sha256(blob).hexdigest() == o.feed_sha256
        rec["sha_body"] = hashlib.sha256(gzip.decompress(blob)).hexdigest() == o.feed_sha256
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "value_compare.csv", index=False)
    d = out["differs"].fillna("")
    summ = {"proposed_overrides": int(len(ov)), "matched_to_my_rows": int(out["my_code"].notna().sum()),
            "code_agrees": int(out["code_agrees"].fillna(False).sum()),
            "all_18_equal": int(d.eq("").sum()),
            "differ_by_count": pd.Series([c for x in d for c in x.split(";") if c]).value_counts().to_dict(),
            "differ_only_svgms": int(d.ne("").sum() - d.str.contains(
                "|".join(f"_{c}(;|$)" for c in NINE if c != "SvGms")).sum()),
            "sha_matches_file": int(out["sha_file"].sum()), "sha_matches_body": int(out["sha_body"].sum()),
            "examples": out[d.ne("")].head(20)[["feed_key", "stage0_match_id", "differs"]].to_dict("records")}
    (OUT / "value_compare.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
