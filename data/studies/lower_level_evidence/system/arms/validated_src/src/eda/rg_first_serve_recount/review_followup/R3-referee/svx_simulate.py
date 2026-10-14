"""R3-referee, group SVX, step 3: the swaps applied with the candidate's other tables, and Stage 0's checks.

  1. raw = stage0_build.normalise(stage0_build.load_raw()), read once.
  2. Version A, the candidate as confirmed (followup/confirmed/candidate/): slam_box_overrides.csv with
     stage0_build.apply_box_overrides, then corrections/row_corrections.csv with
     input_data_audit.corrections.apply_row_corrections, on the subset of the review (every row of the Slams, the clay
     Masters and the Olympics of 2018-2026, and every row a table names).
  3. Version B, the same plus the swaps (the lead's proposed_swaps.csv, or --table <csv>, appended to the corrections),
     applied to the WHOLE raw frame, so that the exactly-one-row and guard tests run on every row.
  4. Checks: every row that changes in B against the raw rows is named by a table; between A and B only the swap rows
     differ, only in w_SvGms and l_SvGms, exchanged; after B each swap row's service games equal the truth
     (svx_rows.csv); no swap row is named by another box correction (apply_row_corrections would stop); Stage 0's box
     checks (simulate.checks: B0-B9, status as Stage 0 holds it) on every Stage 0 row of AO 2025, RG 2019-2026 and the
     Olympics, in A and in B: status changes, B5 and B8 failures, rows losing a box.
Writes svx_sim_rows.csv and svx_sim_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_simulate.py [--table <csv>] [--tag x]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402
from simulate import checks  # noqa: E402

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

CAND = F.FOLLOW / "confirmed" / "candidate"
NAMES = {"Roland Garros", "Paris Olympics", "Tokyo Olympics", "Australian Open", "Wimbledon", "US Open", "Us Open",
         "Madrid Masters", "Rome Masters", "Monte Carlo Masters", "Madrid", "Rome"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=str(F.FOLLOW / "service_games" / "proposed_swaps.csv"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--base-extra", default="", help="comma-separated swap tables (row_corrections columns) that join "
                                                     "version A as well, e.g. the swaps already confirmed")
    args = ap.parse_args()
    ov = pd.read_csv(CAND / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    rc = pd.read_csv(CAND / "corrections" / "row_corrections.csv", dtype=str, keep_default_na=False)
    sw = pd.read_csv(args.table, dtype=str, keep_default_na=False)
    if "fix" not in sw.columns:          # a scope file (source_file, source_row, match_id): take the lead's rows for it
        lead = pd.read_csv(F.FOLLOW / "service_games" / "proposed_swaps.csv", dtype=str, keep_default_na=False)
        sw = lead.merge(sw[["source_file", "source_row"]], on=["source_file", "source_row"], how="inner")
    extra = [pd.read_csv(x, dtype=str, keep_default_na=False) for x in args.base_extra.split(",") if x]
    if extra:
        rc = pd.concat([rc] + [e.reindex(columns=rc.columns, fill_value="") for e in extra], ignore_index=True)
    rc_b = pd.concat([rc, sw.reindex(columns=rc.columns, fill_value="")], ignore_index=True)
    smry: dict = {"swap_rows": int(len(sw)), "candidate_overrides": int(len(ov)), "candidate_corrections": int(len(rc)),
                  "base_extra_rows": int(sum(len(e) for e in extra))}
    raw = B.normalise(B.load_raw())
    rk = F.rowkey(raw["_source_file"], raw["_row"])
    src = ov["source"].replace("", "tml") if "source" in ov else pd.Series("tml", index=ov.index)
    key = raw["source"] + "|" + raw["tour"] + "|" + raw["tid"] + "|" + raw["round"] + "|" + raw["wkey"] + "|" + raw["lkey"]
    want = src + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + ov["loser_key"]
    named_ov = key.isin(set(want))
    named_rc = rk.isin(set(F.rowkey(rc_b["source_file"], rc_b["source_row"])))
    yr = pd.to_numeric(raw["season"], errors="coerce")
    sub = ((raw["tourney_name"].isin(NAMES) | raw["tourney_name"].str.contains("Olympic", case=False))
           & yr.between(2018, 2026)) | raw["tid"].str.fullmatch(r"20(1[89]|2[0-6])-520") | named_ov | named_rc \
        | (raw["tourney_name"].isin(["Roland Garros", "Australian Open"]) & yr.between(2013, 2026))
    a = raw.loc[sub].copy()
    a = B.apply_box_overrides(a, ov, "candidate overrides (R3 SVX)", {})
    a, done_a = K.apply_row_corrections(a, rc)
    # version B on the whole frame
    counts = [f"{s}_{c}" for s in ("w", "l") for c in F.NINE.values()]
    before = F.numbers(raw, counts).astype("float32")
    raw = B.apply_box_overrides(raw, ov, "candidate overrides + swaps (R3 SVX)", {})
    raw, done_b = K.apply_row_corrections(raw, rc_b)
    after = F.numbers(raw, counts).astype("float32")
    changed = ~((before == after) | (before.isna() & after.isna())).all(axis=1)
    named = named_ov | named_rc
    smry["whole_frame"] = {"rows_changed": int(changed.sum()), "rows_changed_not_named": int((changed & ~named).sum()),
                           "corrections_by_action": {k: int(len(v)) for k, v in done_b.items() if len(v)}}
    b = raw.loc[sub].copy()
    del raw, before, after
    # A against B on the subset
    na, nb = F.numbers(a, counts), F.numbers(b, counts)
    diff = ~((na == nb) | (na.isna() & nb.isna()))
    swk = set(F.rowkey(sw["source_file"], sw["source_row"]))
    is_sw = F.rowkey(a["_source_file"], a["_row"]).isin(swk)
    cols_changed = diff.any(axis=0)
    exch = (nb["w_SvGms"] == na["l_SvGms"]) & (nb["l_SvGms"] == na["w_SvGms"])
    smry["a_vs_b"] = {"rows_differing": int(diff.any(axis=1).sum()),
                      "rows_differing_not_swaps": int((diff.any(axis=1) & ~is_sw).sum()),
                      "columns_differing": cols_changed[cols_changed].index.tolist(),
                      "swap_rows_in_subset": int(is_sw.sum()),
                      "swap_rows_exchanged": int((exch & is_sw).sum()),
                      "swap_rows_changed": int((diff.any(axis=1) & is_sw).sum())}
    # after B, the truth
    sv = pd.read_csv(F.OUT / "svx_rows.csv", low_memory=False)
    for f in sorted(F.OUT.glob("svx_add*_rows.csv")):      # the editions of the SVX addenda
        sv = pd.concat([sv, pd.read_csv(f, low_memory=False)], ignore_index=True)
    sv = sv.drop_duplicates("key").set_index("key")
    kb = F.rowkey(b["_source_file"], b["_row"])
    t = pd.DataFrame({"key": kb, "w_after": nb["w_SvGms"].to_numpy(), "l_after": nb["l_SvGms"].to_numpy()})[is_sw.to_numpy()]
    t["true_w"], t["true_l"] = t["key"].map(sv["true_w"]), t["key"].map(sv["true_l"])
    smry["swap_rows_equal_to_truth_after"] = int((t["w_after"].eq(t["true_w"]) & t["l_after"].eq(t["true_l"])).sum())
    # box checks
    s0 = pd.read_parquet(F.S0 / "stage0_matches.parquet",
                         columns=["match_id", "source_file", "source_row", "status", "status_detail", "box_status",
                                  "tournament_name", "year"])
    s0 = s0[(s0["tournament_name"].isin(["Roland Garros", "Australian Open"]) & s0["year"].between(2013, 2026))
            | s0["tournament_name"].eq("Paris Olympics")].copy()
    s0["key"] = F.rowkey(s0["source_file"], s0["source_row"])
    st = s0.drop_duplicates("key").set_index("key")
    out = {}
    for name, fr in (("A", a), ("B", b)):
        fk = F.rowkey(fr["_source_file"], fr["_row"])
        f = fr[fk.isin(st.index).to_numpy()].copy()
        f["_key"] = F.rowkey(f["_source_file"], f["_row"])
        f = f.drop_duplicates("_key")
        r = checks(f.drop(columns="_key").reset_index(drop=True), st)
        r.index = f["_key"].to_numpy()
        out[name] = r
    tab = pd.DataFrame({"stage0_match_id": st["match_id"], "event": st["tournament_name"], "year": st["year"],
                        "stage0_box_status": st["box_status"]})
    for name, r in out.items():
        tab[f"{name}_box_status"] = r["box_status"].reindex(tab.index)
        for k in ("B5", "B8"):
            tab[f"{name}_{k}"] = r[f"fail_{k}"].reindex(tab.index)
    tab["swap"] = tab.index.isin(swk)
    usable = ["full", "no_svgms"]
    smry["box_checks"] = {
        "stage0_rows": int(len(tab)),
        "status_A": tab["A_box_status"].value_counts().to_dict(), "status_B": tab["B_box_status"].value_counts().to_dict(),
        "status_changes_A_to_B": tab.groupby(["A_box_status", "B_box_status"]).size().rename("rows").reset_index()
        .query("A_box_status != B_box_status").to_dict("records"),
        "B5_failures": {"A": int(tab["A_B5"].sum()), "B": int(tab["B_B5"].sum())},
        "B8_failures": {"A": int(tab["A_B8"].sum()), "B": int(tab["B_B8"].sum())},
        "swap_rows_B5_or_B8_after": int((tab["swap"] & (tab["B_B5"].fillna(False) | tab["B_B8"].fillna(False))).sum()),
        "swap_rows_status_after": tab.loc[tab["swap"], "B_box_status"].value_counts().to_dict(),
        "rows_losing_a_usable_box": int((tab["A_box_status"].isin(usable) & ~tab["B_box_status"].isin(usable)).sum()),
        "B8_rows_after": tab.loc[tab["B_B8"].fillna(False).astype(bool), ["stage0_match_id", "event", "year", "swap"]]
        .to_dict("records")}
    tab.to_csv(F.OUT / f"svx_sim_rows{args.tag}.csv")
    (F.OUT / f"svx_sim_summary{args.tag}.json").write_text(json.dumps(smry, indent=1, default=str) + "\n",
                                                          encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
