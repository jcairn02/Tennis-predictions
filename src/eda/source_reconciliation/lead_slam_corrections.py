"""Candidate corrections of Grand Slam box scores, proved by the Slams' own point records (Sackmann's Slam
point-by-point archive, recounted by lead_slam_pbp.py).

Class S1, service games exchanged. Stage 0's two service-game counts are exactly the point record's exchanged, while
everything else agrees: the fault the 9 Oct 2026 decision corrected at the Australian Open (2019-2026) and Roland
Garros (2013-2021, 2025-2026) with the decided action exchange_svgms (input_data_audit/corrections.py; rule F2y/E8),
"wherever the Slam's own point record proves who served first". A match is a candidate only when all of these hold:
    * the recount is complete: every game has a winner, its set scores equal Stage 0's score, the match was completed;
    * Stage 0's (winner, loser) service games equal the recount's (loser, winner), and the two differ;
    * Stage 0's break points equal the recount's, both players (so nothing else needs changing);
    * after the exchange, both players pass the games identity I1 and the serving-order identity I2;
    * the match's row is Sackmann's (the decided table names raw rows by file and row), not already in the decided
      row-correction table.
Class S2, break points off by one where nothing else is: listed for review only (no candidate row: a whole-box
replacement would be needed, and the archive's own box for these matches is not held).

Writes data/studies/source_reconciliation/box/:
    slam_svgms_candidates.csv     the S1 rows in the decided table's format (fix S1, action exchange_svgms), with the
                                  evidence columns x_* (the recount's counts); not applied anywhere
    slam_svgms_candidates.json    counts by edition, the checks, and the S2 list's size
    slam_bp_review.csv            the S2 rows (match ids, both counts)
Run: ./python.sh src/eda/source_reconciliation/lead_slam_corrections.py   (after lead_slam_pbp.py and box_engine.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.input_data_audit import corrections as COR  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation.box_engine import games_from_score  # noqa: E402

BOX = C.OUT / "box"


def raw_rows(files: set[str]) -> pd.DataFrame:
    """The raw Sackmann rows (file and row) with the guard columns the decided table names."""
    parts = []
    for f in sorted(files):
        staged = C.DUMP / "matches" / "sackmann_archive" / ("atp" if "/atp/" in f else "wta") / (Path(f).stem + ".parquet")
        d = pd.read_parquet(staged, columns=["tourney_id", "round", "winner_name", "loser_name", "w_SvGms", "l_SvGms",
                                             "_source_file", "_row"])
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    L = pd.read_parquet(BOX / "engine_long.parquet")
    m = pd.read_parquet(C.SNAP / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "map_level", "status", "score", "tournament_name",
                                 "source", "source_file", "source_row"])
    s0 = L[L["reader"] == "lead_stage0"]
    rc = L[L["reader"] == "lead_slam_pbp_recount"]
    cols = ["match_id", "player_id", "won", "sv_gms", "o_sv_gms", "bp_faced", "bp_saved", "o_bp_faced", "o_bp_saved",
            "complete"]
    j = s0[cols].merge(rc[cols].drop(columns=["won"]), on=["match_id", "player_id"], suffixes=("", "_r"))
    j = j.merge(m, on="match_id", how="left")
    j = j[j["map_level"].eq("GS") & j["status"].eq("completed") & j["complete_r"].astype(bool)]
    w = j[j["won"].astype(bool)].copy()           # one row per match, from the winner's side
    exch = (w["sv_gms"] == w["o_sv_gms_r"]) & (w["o_sv_gms"] == w["sv_gms_r"]) & (w["sv_gms"] != w["o_sv_gms"])
    bp_same = ((w["bp_faced"] == w["bp_faced_r"]) & (w["bp_saved"] == w["bp_saved_r"])
               & (w["o_bp_faced"] == w["o_bp_faced_r"]) & (w["o_bp_saved"] == w["o_bp_saved_r"]))
    cand = w[exch & bp_same].copy()
    # the identities after the exchange (winner's side and loser's side)
    g = np.array([games_from_score(s) for s in cand["score"]], dtype="int64")
    gw, gl, tw, tl, _, sv_wf_w, sv_wf_l = g.T
    new_w, new_l = cand["o_sv_gms"].to_numpy(), cand["sv_gms"].to_numpy()
    brk_by_w = (cand["o_bp_faced"] - cand["o_bp_saved"]).to_numpy()
    brk_by_l = (cand["bp_faced"] - cand["bp_saved"]).to_numpy()
    i1_w = (new_w - brk_by_l + brk_by_w + tw) == gw
    i1_l = (new_l - brk_by_w + brk_by_l + tl) == gl
    i2 = ((new_w == sv_wf_w) & (new_l == sv_wf_l)) | ((new_w == sv_wf_l) & (new_l == sv_wf_w))
    cand["i1_after"] = i1_w & i1_l
    cand["i2_after"] = i2
    # before: Stage 0 as it stands
    old_i1_w = (cand["sv_gms"].to_numpy() - brk_by_l + brk_by_w + tw) == gw
    cand["i1_before"] = old_i1_w
    ok = cand["i1_after"] & cand["i2_after"] & cand["source"].eq("sackmann")
    # not already corrected by the decided table
    decided = pd.read_csv(COR.ROW_CORRECTIONS, dtype=str)
    already = set(decided["match_id"])
    ok &= ~cand["match_id"].isin(already)
    final = cand[ok].copy()
    raw = raw_rows(set(final["source_file"]))
    raw["key"] = raw["_source_file"].astype(str) + "#" + raw["_row"].astype(str)
    final["key"] = final["source_file"].astype(str) + "#" + final["source_row"].astype(str)
    final = final.merge(raw.drop(columns=["_source_file", "_row"]), on="key", how="left", validate="one_to_one")
    # the raw row must still read Stage 0's (exchanged) service games
    raw_ok = (pd.to_numeric(final["w_SvGms"], errors="coerce") == final["sv_gms"]) & \
             (pd.to_numeric(final["l_SvGms"], errors="coerce") == final["o_sv_gms"])
    table = pd.DataFrame({
        "fix": "S1", "action": "exchange_svgms", "match_id": final["match_id"], "source_file": final["source_file"],
        "source_row": final["source_row"], "tourney_id": final["tourney_id"], "round": final["round"],
        "winner_name": final["winner_name"], "loser_name": final["loser_name"], "side": "", "value": ""})
    for c in COR.COUNTS:
        table[f"w_{c}"] = ""
        table[f"l_{c}"] = ""
    table["x_raw_reads_stage0"] = raw_ok.to_numpy()
    table["x_recount_w_svgms"] = final["sv_gms_r"].astype(int).to_numpy()
    table["x_recount_l_svgms"] = final["o_sv_gms_r"].astype(int).to_numpy()
    table["x_tournament"] = final["tournament_name"].to_numpy()
    table["x_year"] = final["year"].to_numpy()
    table["x_tour"] = final["tour"].to_numpy()
    table.to_csv(BOX / "slam_svgms_candidates.csv", index=False)
    # S2: service games equal, break points differ, the recount's break points pass I1 and Stage 0's do not
    sv_same = (w["sv_gms"] == w["sv_gms_r"]) & (w["o_sv_gms"] == w["o_sv_gms_r"])
    s2 = w[sv_same & ~bp_same].copy()
    s2[["match_id", "tournament_name", "year", "tour", "score", "bp_faced", "bp_saved", "o_bp_faced", "o_bp_saved",
        "bp_faced_r", "bp_saved_r", "o_bp_faced_r", "o_bp_saved_r"]].to_csv(BOX / "slam_bp_review.csv", index=False)
    summary = {
        "slam_completed_matches_with_complete_recount": int(len(w)),
        "exchanged_with_equal_break_points": int(len(cand)),
        "pass_i1_and_i2_after_exchange": int((cand["i1_after"] & cand["i2_after"]).sum()),
        "failed_i1_before": int((~cand["i1_before"]).sum()),
        "already_in_decided_table": int(cand["match_id"].isin(already).sum()),
        "not_sackmann_rows": int((~cand["source"].eq("sackmann")).sum()),
        "candidates": int(len(table)),
        "raw_row_reads_stage0s_counts": int(raw_ok.sum()),
        "by_edition": table.groupby(["x_tour", "x_tournament", "x_year"]).size().rename("matches").reset_index()
                           .to_dict("records"),
        "s2_break_points_differ_service_games_equal": int(len(s2)),
    }
    C.write_json(BOX / "slam_svgms_candidates.json", summary)
    print({k: v for k, v in summary.items() if k != "by_edition"})
    for r in summary["by_edition"]:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
