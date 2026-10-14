"""R2-skeptic (round 2, SVS): my scope of the proposed set_svgms rows, with my own values, and a dry run with the build's
own corrections.apply_row_corrections (set_svgms, rule E8).

A proposed row is confirmed (sets_check.py -> sets_checked.csv) when: my link places it on the same match; the first
server is proven (both proofs; RG 2014 SD078, whose file stores set 1's game 8 twice under the same server, passes the
parity proof with no dissent over 30 games and is accepted); my truth equals the proposal's values; the guard value is
the row's; the consistency identity holds for the truth and not for the row; no other correction, swap or override
names the row; Stage 0's checks pass after the set, or the box stays as partial as before (6 RG 2013-2014 rows whose
double faults are blank: the fill is right but leaves those boxes partial). For an "other", the row is impossible under
either order of serve (the score alone disproves it).
Writes sets_scope.csv (source_file, source_row, w_SvGms, l_SvGms) and sets_dry_run.json in
data/studies/rg_first_serve_recount/followup/review/R2-skeptic/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/sets_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import svx as SX  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
ACCEPTED_ON_PARITY = {"wta|2014-W-SL-FRA-1A-2014|R128|wta:201450|wta:202470"}


def main() -> int:
    s = pd.read_csv(OUT / "sets_checked.csv")
    prop = pd.read_csv(LEAD / "service_games" / "proposed_sets.csv", dtype=str, keep_default_na=False)
    truth = s["my_truth"].map(lambda t: tuple(float(v) for v in t.strip("()").split(",")))
    s["my_w"], s["my_l"] = truth.str[0], truth.str[1]
    impossible = []
    for r in s.itertuples(index=False):
        sets = SX.score_sets(r.score)
        a, b = SX.truth(sets, True), SX.truth(sets, False)
        impossible.append((r.row_w_SvGms, r.row_l_SvGms) not in (a, b))
    s["row_impossible"] = impossible
    proven = s["proven"] | s["match_id"].isin(ACCEPTED_ON_PARITY)
    ok = (s["linked"] & s["match_id_agrees"] & proven & s["value_matches_row"] & s["identity_truth"].eq(True)
          & ~s["identity_row"].eq(True) & ~s["other_correction"] & ~s["also_swapped"] & ~s["override"]
          & (s["stage0_checks_after"].fillna("").eq("") | s["stage0_checks_after"].eq("box incomplete"))
          & (s["kind"].eq("fill") | s["row_impossible"])
          & s["my_w"].eq(s["prop_w"]) & s["my_l"].eq(s["prop_l"]))
    scope = s[ok][["source_file", "source_row", "my_w", "my_l"]].rename(columns={"my_w": "w_SvGms", "my_l": "l_SvGms"})
    scope["w_SvGms"], scope["l_SvGms"] = scope["w_SvGms"].astype(int), scope["l_SvGms"].astype(int)
    scope.to_csv(OUT / "sets_scope.csv", index=False)
    # dry run: the proposal's rows I confirm, applied with the build's code to the raw rows
    keys = set(scope["source_file"] + "|" + scope["source_row"].astype(str))
    table = prop[(prop["source_file"] + "|" + prop["source_row"]).isin(keys)]
    raw = pd.concat([pd.read_parquet(OUT / "raw_rg.parquet"), pd.read_parquet(OUT / "raw_ao_all.parquet")],
                    ignore_index=True).drop_duplicates(["_source_file", "_row"]).reset_index(drop=True)
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    after, done = K.apply_row_corrections(raw.copy(), table)
    rows = done.get("set_svgms", pd.Index([]))
    mine = scope.assign(k=scope["source_file"] + "|" + scope["source_row"].astype(str)).set_index("k")
    reads = 0
    for i in rows:
        k = f"{after.at[i, '_source_file']}|{after.at[i, '_row']}"
        reads += int(float(after.at[i, "w_SvGms"]) == mine.at[k, "w_SvGms"]
                     and float(after.at[i, "l_SvGms"]) == mine.at[k, "l_SvGms"])
    others = [c for c in raw.columns if c.startswith(("w_", "l_")) and c not in ("w_SvGms", "l_SvGms")]
    res = {"proposed": int(len(s)), "confirmed": int(len(scope)),
           "left_out": s[~ok][["match_id", "kind"]].to_dict("records"),
           "values_equal_proposal": int((s["my_w"].eq(s["prop_w"]) & s["my_l"].eq(s["prop_l"])).sum()),
           "other_rows_impossible_either_order": f"{int((s['kind'].eq('other') & s['row_impossible']).sum())} of "
                                                 f"{int(s['kind'].eq('other').sum())}",
           "partial_boxes_filled": s[s["stage0_checks_after"].eq("box incomplete")]["match_id"].tolist(),
           "dry_run": {"rows_set": int(len(rows)), "rows_reading_my_values": reads,
                       "other_counts_changed": int((after[others].astype(str) != raw[others].astype(str)).to_numpy().sum())}}
    (OUT / "sets_dry_run.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
