"""R2-skeptic (round 2, SVS): the 558 proposed set_svgms rows, attacked, with my own links, proofs and truth
(svx.py, svx2.py, svx3.py), against the lead's proposed_sets.csv.

Per proposed row:
    link        my match record for the raw row (source file and row), its code, the first server proven twice
                (opening point and in-order alternation; parity over every held game); the file's serve points against
                the row's by name (the link and the slots right)
    truth       completed non-tie-break service games from the row's score and the first server (mine), against the
                proposal's values
    the row     its current counts (the guard "value" too); kind: fill (blank, or 0 with serve points played) or
                other; for a fill, whether the rest of the box is there (the eight counts, both players)
    convention  for an "other": is the row the tie-breaks-counted count (a convention, not an error), the truth with a
                retirement's unfinished game counted, the truth exchanged, a total within one of the truth, or far
                short (a partial count)
    tests       the consistency identity from the row's score and break points, for the truth and for the row; Stage
                0's checks B0-B9 on the box after the set; the file's own count where it holds the whole match
    candidate   any other correction of the same raw row: the candidate's row_corrections.csv, the swap table, the
                overrides
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/: sets_checked.csv, sets_checks.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/sets_check.py
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_scope as BS  # noqa: E402  (Stage 0's box checks)
import svx as SX  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]


def truth_incl(sets, w_first: bool) -> tuple[int, int]:
    """The tie-breaks-counted convention: each tie-break counted for the player whose turn it is."""
    turn_w, sw, sl = w_first, 0, 0
    for a, b, tbset in sets:
        n = a + b
        if n == 0 and tbset:
            turn_w = not turn_w
            continue
        for _ in range(n):
            sw, sl = sw + turn_w, sl + (not turn_w)
            turn_w = not turn_w
    return sw, sl


def main() -> int:
    prop = pd.read_csv(LEAD / "service_games" / "proposed_sets.csv", dtype=str, keep_default_na=False)
    # my match records, one per raw row
    a = pd.read_csv(OUT / "svx_matches.csv")
    a = a.merge(pd.read_csv(OUT / "svx_identity.csv")[["match_id", "identity_truth", "identity_row"]], on="match_id",
                how="left")
    a = a.merge(pd.read_csv(OUT / "svx_labels.csv")[["match_id", "labels_by_name"]], on="match_id", how="left")
    b = pd.read_csv(OUT / "svx2_matches.csv")
    c = pd.read_csv(OUT / "rg1618_matches.csv")
    keep = ["event", "match_id", "year", "status", "source_file", "source_row", "row_score", "winner", "loser",
            "code", "w_slot", "first_slot", "proven", "w_first", "raw_w", "raw_l", "true_w", "true_l",
            "w_bp_lost", "l_bp_lost", "identity_truth", "identity_row", "labels_by_name", "file_whole",
            "file_svpt_1", "file_svpt_2", "file_count_1", "file_count_2", "winner_agrees", "cls"]
    mine = pd.concat([d[[k for k in keep if k in d.columns]] for d in (a, b, c)], ignore_index=True)
    mine["source_row"] = pd.to_numeric(mine["source_row"]).astype("Int64").astype(str)
    mine = mine.drop_duplicates(["source_file", "source_row"])
    # the raw rows' nine counts
    raw = pd.concat([pd.read_parquet(OUT / "raw_rg.parquet"), pd.read_parquet(OUT / "raw_ao_all.parquet")],
                    ignore_index=True).drop_duplicates(["_source_file", "_row"])
    raw["_row"] = raw["_row"].astype("Int64").astype(str)
    raw = raw.rename(columns={"_source_file": "source_file", "_row": "source_row"})
    rc = pd.read_csv(LEAD / "confirmed" / "candidate" / "corrections" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    sw = pd.read_csv(LEAD / "service_games" / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    ov = pd.read_csv(LEAD / "confirmed" / "candidate" / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    rc_key = set(rc["source_file"] + "|" + rc["source_row"])
    sw_key = set(sw["source_file"] + "|" + sw["source_row"])
    p = prop.merge(mine, on=["source_file", "source_row"], how="left", suffixes=("", "_mine"))
    p = p.merge(raw[["source_file", "source_row"] + [f"{s}_{x}" for s in ("w", "l") for x in NINE]],
                on=["source_file", "source_row"], how="left", suffixes=("", "_raw"))
    rows = []
    for r in p.itertuples(index=False):
        d = r._asdict()
        rec = {"source_file": r.source_file, "source_row": r.source_row, "match_id": r.match_id,
               "event": d.get("event"), "year": d.get("year"), "status": d.get("status"), "score": d.get("row_score"),
               "value": r.value, "prop_w": float(r.w_SvGms), "prop_l": float(r.l_SvGms),
               "linked": isinstance(d.get("code"), str), "match_id_agrees": d.get("match_id_mine") == r.match_id}
        box = {f"{s}_{x}": pd.to_numeric(d.get(f"{s}_{x}_raw"), errors="coerce") for s in ("w", "l") for x in NINE}
        rec.update({f"row_{k}": v for k, v in box.items()})
        cur_w, cur_l = box["w_SvGms"], box["l_SvGms"]
        rec["value_matches_row"] = r.value == (f"{'' if pd.isna(cur_w) else int(cur_w)}/"
                                               f"{'' if pd.isna(cur_l) else int(cur_l)}")
        svpt_ok = box["w_svpt"] > 0 and box["l_svpt"] > 0
        rec["kind"] = ("fill" if (pd.isna(cur_w) or pd.isna(cur_l) or ((cur_w == 0 or cur_l == 0) and svpt_ok))
                       else "other")
        eight = [k for k in box if not k.endswith("SvGms")]
        rec["rest_of_box_complete"] = all(pd.notna(box[k]) for k in eight) and svpt_ok
        rec["proven"] = bool(d.get("proven")) if d.get("proven") is not None and not pd.isna(d.get("proven")) else False
        rec["my_truth"] = (d.get("true_w"), d.get("true_l"))
        rec["values_equal"] = rec["proven"] and float(d.get("true_w")) == rec["prop_w"] and \
            float(d.get("true_l")) == rec["prop_l"]
        # the link and slots: the file's serve points against the row's, by name
        if rec["linked"] and pd.notna(d.get("w_slot")):
            ws = int(d.get("w_slot"))
            fw, fl = (d.get("file_svpt_1"), d.get("file_svpt_2")) if ws == 1 else (d.get("file_svpt_2"),
                                                                                    d.get("file_svpt_1"))
            rec["file_svpt_by_name"] = (fw, fl)
            rec["svpt_fits_by_name"] = (abs(fw - box["w_svpt"]) + abs(fl - box["l_svpt"])) < \
                (abs(fw - box["l_svpt"]) + abs(fl - box["w_svpt"])) if svpt_ok else None
            rec["svpt_exact"] = bool(fw == box["w_svpt"] and fl == box["l_svpt"]) if svpt_ok else None
        # convention patterns for an "other"
        sets = SX.score_sets(d.get("row_score"))
        wf = bool(d.get("w_first")) if d.get("w_first") is not None and not pd.isna(d.get("w_first")) else None
        if wf is not None:
            inc = truth_incl(sets, wf)
            rec["row_is_tiebreaks_counted"] = (cur_w, cur_l) == inc and inc != rec["my_truth"]
            rec["row_is_truth_exchanged"] = (cur_w, cur_l) == (d.get("true_l"), d.get("true_w")) and \
                d.get("true_w") != d.get("true_l")
            unfinished = d.get("status") == "retired"
            rec["row_counts_unfinished_game"] = bool(unfinished and pd.notna(cur_w) and pd.notna(cur_l)
                                                     and (cur_w + cur_l) == (d.get("true_w") + d.get("true_l") + 1)
                                                     and abs(cur_w - d.get("true_w")) + abs(cur_l - d.get("true_l")) == 1)
            tot = (cur_w + cur_l) - (d.get("true_w") + d.get("true_l")) if pd.notna(cur_w) and pd.notna(cur_l) else np.nan
            rec["row_total_minus_truth"] = tot
        rec["identity_truth"], rec["identity_row"] = d.get("identity_truth"), d.get("identity_row")
        rec["labels_by_name"] = d.get("labels_by_name")
        rec["winner_agrees"] = d.get("winner_agrees")
        # Stage 0's checks on the box after the set
        after = {x: box[f"w_{x}"] for x in NINE}, {x: box[f"l_{x}"] for x in NINE}
        after[0]["SvGms"], after[1]["SvGms"] = rec["prop_w"], rec["prop_l"]
        fails = BS.stage0_checks(after[0], after[1], d.get("row_score") or "", d.get("status") or "completed") \
            if rec["rest_of_box_complete"] else ["box incomplete"]
        rec["stage0_checks_after"] = ";".join(fails)
        before = {x: box[f"w_{x}"] for x in NINE}, {x: box[f"l_{x}"] for x in NINE}
        rec["stage0_checks_before"] = ";".join(BS.stage0_checks(before[0], before[1], d.get("row_score") or "",
                                                                d.get("status") or "completed")) \
            if rec["rest_of_box_complete"] and pd.notna(cur_w) and pd.notna(cur_l) else "service games missing"
        key = f"{r.source_file}|{r.source_row}"
        rec["other_correction"] = key in rc_key
        rec["also_swapped"] = key in sw_key
        rec["override"] = r.match_id in set(ov["stage0_match_id"])
        # the file's own count where whole
        if bool(d.get("file_whole")) and pd.notna(d.get("w_slot")):
            ws = int(d.get("w_slot"))
            fcw, fcl = (d.get("file_count_1"), d.get("file_count_2")) if ws == 1 else (d.get("file_count_2"),
                                                                                        d.get("file_count_1"))
            rec["file_count_is_truth"] = bool(fcw == d.get("true_w") and fcl == d.get("true_l"))
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "sets_checked.csv", index=False)
    o = out[out["kind"].eq("other")]
    res = {"proposed": int(len(out)), "kinds": out["kind"].value_counts().to_dict(),
           "linked": int(out["linked"].sum()), "match_id_agrees": int(out["match_id_agrees"].sum()),
           "proven": int(out["proven"].sum()), "values_equal": int(out["values_equal"].sum()),
           "value_guard_matches_row": int(out["value_matches_row"].sum()),
           "fill_rest_of_box_complete": int((out["kind"].eq("fill") & out["rest_of_box_complete"]).sum()),
           "fill_rows": int(out["kind"].eq("fill").sum()),
           "svpt_fits_by_name": int(out["svpt_fits_by_name"].eq(True).sum()),
           "svpt_exact": int(out["svpt_exact"].eq(True).sum()),
           "identity_truth": int(out["identity_truth"].eq(True).sum()),
           "identity_row": int(out["identity_row"].eq(True).sum()),
           "labels_by_name": int(out["labels_by_name"].eq(True).sum()),
           "winner_disagrees": int(out["winner_agrees"].eq(False).sum()),
           "stage0_after_fail": out[out["stage0_checks_after"].ne("")][["match_id", "kind", "stage0_checks_after",
                                                                        "stage0_checks_before"]].to_dict("records"),
           "other_correction": int(out["other_correction"].sum()), "also_swapped": int(out["also_swapped"].sum()),
           "override": int(out["override"].sum()),
           "file_count_is_truth": f"{int(out['file_count_is_truth'].eq(True).sum())} of "
                                  f"{int(out['file_count_is_truth'].notna().sum())}",
           "other_patterns": {"rows": int(len(o)),
                              "tiebreaks_counted": int(o["row_is_tiebreaks_counted"].eq(True).sum()),
                              "truth_exchanged": int(o["row_is_truth_exchanged"].eq(True).sum()),
                              "unfinished_game_counted": int(o["row_counts_unfinished_game"].eq(True).sum()),
                              "total_minus_truth": o["row_total_minus_truth"].value_counts().sort_index().to_dict()},
           "by_year_kind": out.groupby(["event", "year", "kind"]).size().rename("n").reset_index().to_dict("records")}
    (OUT / "sets_checks.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
