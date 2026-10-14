"""R2-skeptic (round 2, SVX): my scope of swaps, and a dry run of it with the build's own code.

A proposed swap (the lead's proposed_swaps.csv) is confirmed when, in my own derivation (svx.py, svx_checks.py,
svx_identity.py, the multi-count label test of svx_labels.csv):
    my class is "swapped" (the row's two counts are the truth exchanged, and differ), with the first server proven
        twice (opening point and in-order alternation; parity over every game held)
    the file's server labels belong to the players named (serve points, aces, double faults and serve points won fit
        the row's box by name strictly better than exchanged: the box itself is not exchanged)
    the identity "games won on serve = service games - service games lost + the opponent's lost", from the row's own
        score and break points, holds for the truth and not for the row (independent of MatchBeats)
    the winner agrees with the Slam's; no hand chart or Court Vision file names another first server
    no other correction of the same raw row in the candidate, no override of the match, and B8 passes after
Writes swaps_scope.csv (source_file, source_row, match_id) and svx_dry_run.json in
data/studies/rg_first_serve_recount/followup/review/R2-skeptic/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def main() -> int:
    prop = pd.read_csv(LEAD / "service_games" / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    x = pd.read_csv(OUT / "svx_checked.csv")
    lab = pd.read_csv(OUT / "svx_labels.csv")[["match_id", "labels_by_name"]]
    ide = pd.read_csv(OUT / "svx_identity.csv")[["match_id", "identity_truth", "identity_row"]]
    x = x.merge(lab, on="match_id", how="left").merge(ide, on="match_id", how="left")
    x["chart_ok"] = x["chart_first"].isna() | x["chart_first"].eq(x["file_first"])
    x["cv_ok"] = x["cv_first"].isna() | x["cv_first"].eq(x["file_first"])
    ok = (x["cls"].eq("swapped") & x["proven"] & x["labels_by_name"].eq(True) & x["identity_truth"].eq(True)
          & x["identity_row"].eq(False) & ~x["winner_agrees"].eq(False) & x["chart_ok"] & x["cv_ok"]
          & ~x["candidate_correction"] & ~x["candidate_override"] & x["b8_after_ok"])
    good = set(x.loc[ok, "match_id"])
    scope = prop[prop["match_id"].isin(good)][["source_file", "source_row", "match_id"]]
    scope.to_csv(OUT / "swaps_scope.csv", index=False)
    left = prop[~prop["match_id"].isin(good)]["match_id"].tolist()
    # dry run: the confirmed rows of the proposal applied to the raw rows of RG and AO 2025 with the build's code
    raw = pd.concat([pd.read_parquet(OUT / "raw_rg.parquet"), pd.read_parquet(OUT / "raw_ao.parquet")],
                    ignore_index=True)
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    table = prop[prop["match_id"].isin(good)]
    before = raw[["w_SvGms", "l_SvGms"]].copy()
    after, done = K.apply_row_corrections(raw.copy(), table)
    rows = done.get("exchange_svgms", pd.Index([]))
    exchanged = (after.loc[rows, "w_SvGms"].astype(str).to_numpy() == before.loc[rows, "l_SvGms"].astype(str).to_numpy()) & \
                (after.loc[rows, "l_SvGms"].astype(str).to_numpy() == before.loc[rows, "w_SvGms"].astype(str).to_numpy())
    others = [c for c in raw.columns if c.startswith(("w_", "l_")) and c not in ("w_SvGms", "l_SvGms")]
    other_changed = int((after[others].astype(str) != raw[others].astype(str)).to_numpy().sum())
    # after the exchange, each row reads the truth
    key = x.set_index("match_id")
    truth_ok = 0
    for r in table.itertuples(index=False):
        hit = after[(after["_source_file"].eq(r.source_file)) & (after["_row"].eq(str(r.source_row)))]
        t = key.loc[r.match_id]
        truth_ok += int(float(hit["w_SvGms"].iloc[0]) == t["true_w"] and float(hit["l_SvGms"].iloc[0]) == t["true_l"])
    res = {"proposed": int(len(prop)), "confirmed": int(len(scope)), "left_out": left,
           "dry_run": {"rows_exchanged": int(len(rows)), "rows_reading_exchanged": int(exchanged.sum()),
                       "rows_reading_the_truth_after": truth_ok, "other_counts_changed": other_changed}}
    (OUT / "svx_dry_run.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
