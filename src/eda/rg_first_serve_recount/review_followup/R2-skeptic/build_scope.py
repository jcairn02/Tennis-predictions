"""R2-skeptic (round 2): my scope for W22, W26 and RGX, with my own values, and the verdict's numbers.

Inputs: my tables (players.parquet, svgms_rows.csv, mb_integrity.csv, bp_rows.csv, referee_rows.csv, scores.csv,
rgx_evidence.json, value_compare.csv), round 1's Court Vision 2022 recount (review/R2-skeptic/cv2022_sides.csv),
and the lead's tables (whole_box_rows.csv for its classes and hand-chart columns, proposed_overrides.csv,
proposed_exchanges.csv).

My values (all matches): the eight counts from RG's match statistics (my parse); SvGms = the non-tie-break games the
player served in COMPLETED games, from RG's set scores and MatchBeats' first server (equal to MatchBeats' own count in
every completed match; in a retirement a game in progress is not counted, as in every Sackmann retirement row of
2022-2025); blank where MatchBeats does not hold every serve point of both players (as the lead, except that the lead
then takes the row's own count).

W26 (2026: Sackmann's blank main-draw rows, TML's men's qualifying): the source rule of the 6 Oct decision. Confirm a
proposed match when my link is the lead's, the row's score is RG's, the values are RG's record (mine), no
independent record holds a changing count against RG, and the box passes Stage 0's checks (B0-B4, B6-B9; B5).

W22 (2022-2025, Sackmann's own rows): the 8 Oct bar, corrupt beyond reasonable doubt on every count that changes.
A proposed match is confirmed when all of these hold:
    T0  the row has a box score (a blank row is not corrupt; filling it is the source rule's "replacing beats blanking")
    T1  MatchBeats holds every serve point of both players (RG's serve points) and passes the integrity test
        (mb_integrity.py) with an ended last game in a completed match; and agrees with RG's statistics on the split,
        aces and double faults (a second record)
    T2  serve points: equal, or settled by T1 (the coherent capture holds the points played; the row holds others).
        Not settled: the row holds MORE serve points than the capture in a retirement (its end cannot be verified)
    T3  break points: equal, or my MatchBeats recount equals RG's (the row's then is wrong)
    T4  service games: equal to the exact count, or the row's differs from the exact count (score + first server)
    T5  the split: where serve points are equal, a change is settled when Sackmann has MORE first serves in than RG
        ("+", the fault, as in round 1); a "-" or "0" change (fewer first serves in, or points won moved between the
        serves) is settled only where my Court Vision 2022 recount holds every point and reads RG's split exactly.
        Where serve points differ (settled by T2), the row's split is on another set of points and RG's is taken
    T6  aces and double faults: where serve points are equal, a change is settled when the row is LOWER than RG (the
        row's record's systematic undercount: 71 of 72 ace and 175 of 195 double-fault changes); a row HIGHER than RG
        needs a referee (Court Vision 2022 or a hand chart) holding every point and reading RG's value
    T7  no independent record holding every point reads the row's value on a changing count (the lead's 13)
    T8  the box passes Stage 0's checks under the row's score
RGX: confirm an exchange when RG's record equals the raw boxes exchanged on all eight counts and not as recorded, its
winner, the score's orientation and the next round agree with the raw row, MatchBeats agrees with RG and is coherent,
and the service games are equal (so the exchange of all nine is exact).

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    overrides_scope.csv   one row per confirmed match (W22 and W26), the brief's columns, my values
    exchanges_scope.csv   one row per confirmed exchange
    scope_matches.csv     one row per proposed match: group, every test, my decision and the reason
    scope_summary.json    counts
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/build_scope.py
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

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
R1 = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
EIGHT = [c for c in NINE if c != "SvGms"]
SCOPE_COLS = ["feed_key", "stage0_match_id"] + [f"{s}_{c}" for s in ("w", "l") for c in NINE]


def stage0_checks(w: dict, l: dict, score: str, status: str) -> list[str]:
    """Stage 0's box checks (stage0_build.box_scores) on one match's two boxes under the row's score."""
    c = B.score_counts(str(score or ""), False)
    games, tb = c[2] + c[3], c[6]
    fails = []
    for side, f in (("w", w), ("l", l)):
        if any(pd.notna(f[k]) and f[k] < 0 for k in NINE):
            fails.append(f"B0 {side}")
        if f["1stIn"] > f["svpt"]:
            fails.append(f"B1 {side}")
        if f["1stWon"] > f["1stIn"]:
            fails.append(f"B2 {side}")
        if f["2ndWon"] > f["svpt"] - f["1stIn"]:
            fails.append(f"B3 {side}")
        if f["bpSaved"] > f["bpFaced"]:
            fails.append(f"B4 {side}")
        if f["df"] > f["svpt"] - f["1stIn"]:
            fails.append(f"B6 {side}")
        if f["ace"] > f["1stWon"] + f["2ndWon"]:
            fails.append(f"B7 {side}")
    sv = (w["SvGms"] + l["SvGms"]) if pd.notna(w["SvGms"]) and pd.notna(l["SvGms"]) else np.nan
    b5 = pd.notna(sv) and not (abs(sv - (games - tb)) <= 1 or abs(sv - games) <= 1)
    if b5:
        fails.append("B5")
    for side, f in (("w", w), ("l", l)):
        if not b5 and pd.notna(f["SvGms"]) and (f["bpFaced"] - f["bpSaved"]) > f["SvGms"]:
            fails.append(f"B8 {side}")
    played = (games - tb) - (0 if status == "completed" else 1)
    if w["svpt"] + l["svpt"] < B.MIN_POINTS_PER_GAME * played:
        fails.append("B9")
    return fails


def main() -> int:
    s = pd.read_parquet(OUT / "players.parquet")
    lead = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False).rename(columns={"raw_side": "side"})
    s = s.merge(lead[["match_id", "side", "cls", "mcp_svpt", "mcp_first_in", "mcp_first_won", "mcp_second_won",
                      "mcp_ace", "mcp_df", "off_sv_gms", "sv_gms_from"]], on=["match_id", "side"], how="left")
    sv = pd.read_csv(OUT / "svgms_rows.csv")[["match_id", "side", "exp_excl", "exp_incl", "mb_sv_gms_regular"]]
    s = s.merge(sv, on=["match_id", "side"], how="left", suffixes=("", "_sv"))
    it = pd.read_csv(OUT / "mb_integrity.csv")[["year", "code", "integrity", "last_game_open"]]
    s = s.merge(it, on=["year", "code"], how="left")
    bp = pd.read_csv(OUT / "bp_rows.csv")[["match_id", "side", "mbbp_faced", "mbbp_saved"]]
    s = s.merge(bp, on=["match_id", "side"], how="left")
    cv = pd.read_csv(R1 / "cv2022_sides.csv", low_memory=False)[
        ["source_file", "source_row", "side", "cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won", "cv_ace",
         "cv_df"]]
    cv["source_row_i"] = pd.to_numeric(cv["source_row"], errors="coerce")
    s["source_row_i"] = pd.to_numeric(s["source_row"], errors="coerce")
    s = s.merge(cv.drop(columns="source_row"), on=["source_file", "source_row_i", "side"], how="left")
    rr = pd.read_csv(OUT / "referee_rows.csv")
    against = set(rr.loc[rr["reads"].eq("row"), "match_id"])
    sc = pd.read_csv(OUT / "scores.csv")[["match_id", "differs"]]
    s = s.merge(sc, on="match_id", how="left")
    ov = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    s = s[s["match_id"].isin(set(ov["stage0_match_id"]))].copy()

    # my service games: completed games served, tie-breaks not counted, from the score and MatchBeats' first server
    s["my_SvGms_final"] = np.where(s["mb_complete_match"].fillna(False), s["exp_excl"], np.nan)

    d = {c: s[f"raw_{c}"] - s[f"my_{c}"] for c in EIGHT}
    s["d_svpt"] = d["svpt"]
    split_moves = d["1stIn"].ne(0) | d["1stWon"].ne(0) | d["2ndWon"].ne(0)
    has_raw = s["raw_svpt"].notna()
    s["sign"] = np.where(~has_raw | ~split_moves, "", np.where(d["1stIn"] > 0, "+", np.where(d["1stIn"] < 0, "-", "0")))
    svpt_eq = d["svpt"].eq(0)
    # T1: the second record, complete and coherent, agreeing with RG on the split, aces and double faults
    agree = np.all([s[f"mb_{k}"].eq(s[f"my_{c}"]) for c, k in (("1stIn", "first_in"), ("1stWon", "first_won"),
                                                               ("2ndWon", "second_won"), ("ace", "ace"), ("df", "df"))],
                   axis=0)
    t1_side = s["mb_complete_match"].fillna(False) & s["integrity"].eq(True) & agree
    t1_side &= ~(s["status"].eq("completed") & s["last_game_open"].eq(True))
    # T2: serve points
    t2_side = ~has_raw | svpt_eq | (t1_side & (s["status"].eq("completed") | (d["svpt"] < 0)))
    # T3: break points
    bpch = has_raw & (d["bpFaced"].ne(0) | d["bpSaved"].ne(0))
    t3_side = ~bpch | (s["mbbp_faced"].eq(s["my_bpFaced"]) & s["mbbp_saved"].eq(s["my_bpSaved"]))
    # T4: service games (the row's count differs from the exact one, or is equal to mine)
    svch = has_raw & s["raw_SvGms"].ne(s["my_SvGms_final"])
    t4_side = ~svch | s["raw_SvGms"].ne(s["exp_excl"])
    # T5: the split
    doubtful_split = has_raw & svpt_eq & s["sign"].isin(["-", "0"])
    cv_full = s["year"].eq(2022) & s["cv_svpt"].eq(s["my_svpt"])
    cv_reads_rg_split = cv_full & s["cv_first_in"].eq(s["my_1stIn"]) & s["cv_first_won"].eq(s["my_1stWon"]) & \
        s["cv_second_won"].eq(s["my_2ndWon"])
    t5_side = ~doubtful_split | cv_reads_rg_split
    # T6: aces and double faults higher in the row than in RG's record, with the same serve points
    t6_side = pd.Series(True, index=s.index)
    for c, cvc, mc in (("ace", "cv_ace", "mcp_ace"), ("df", "cv_df", "mcp_df")):
        up = has_raw & svpt_eq & (d[c] > 0)
        cv_ok = s["year"].eq(2022) & (s["cv_svpt"].eq(s["my_svpt"]) | s["cv_svpt"].eq(s["raw_svpt"]))
        mcp_ok = s["mcp_svpt"].eq(s["my_svpt"]) | s["mcp_svpt"].eq(s["raw_svpt"])
        rg_read = (cv_ok & s[cvc].eq(s[f"my_{c}"])) | (mcp_ok & s[mc].eq(s[f"my_{c}"]))
        row_read = (cv_ok & s[cvc].eq(s[f"raw_{c}"])) | (mcp_ok & s[mc].eq(s[f"raw_{c}"]))
        t6_side &= ~up | (rg_read & ~row_read)
    s["t1"], s["t2"], s["t3"], s["t4"], s["t5"], s["t6"] = t1_side, t2_side, t3_side, t4_side, t5_side, t6_side
    s["doubtful_split"], s["cv_reads_rg_split"] = doubtful_split, cv_reads_rg_split

    rows, scope = [], []
    for mid, g in s.groupby("match_id", sort=False):
        w, l = g[g["side"].eq("w")].iloc[0], g[g["side"].eq("l")].iloc[0]
        o = ov[ov["stage0_match_id"].eq(mid)].iloc[0]
        year = int(w["year"])
        group = "W26" if year == 2026 else "W22"
        vals = {}
        for sd, x in (("w", w), ("l", l)):
            for c in EIGHT:
                vals[f"{sd}_{c}"] = x[f"my_{c}"]
            vals[f"{sd}_SvGms"] = x["my_SvGms_final"]
        fails = stage0_checks({c: vals[f"w_{c}"] for c in NINE}, {c: vals[f"l_{c}"] for c in NINE}, w["raw_score"],
                              w["status"])
        lead_vals = {k: (float(o[k]) if o[k] != "" else np.nan) for k in vals}
        same_as_lead = all((pd.isna(vals[k]) and pd.isna(lead_vals[k])) or vals[k] == lead_vals[k] for k in vals)
        diff_lead = [k for k in vals if not ((pd.isna(vals[k]) and pd.isna(lead_vals[k])) or vals[k] == lead_vals[k])]
        rec = {"group": group, "feed_key": o["feed_key"], "stage0_match_id": mid, "year": year, "tour": w["tour"],
               "draw": w["draw"], "round": w["round"], "source": w["source"], "status": w["status"],
               "code": w["code"], "my_code_equals_lead": o["feed_key"].endswith("/" + str(w["code"])),
               "score_differs": w["differs"] if isinstance(w["differs"], str) else "",
               "link_score": w["lscore"], "winner_agrees": w["winner_agrees"],
               "stage0_checks_failed": ";".join(fails), "values_equal_lead": same_as_lead,
               "values_differ_from_lead": ";".join(diff_lead), "referee_against": mid in against,
               "signs": f"{w['sign']}/{l['sign']}", "d_svpt": f"{w['d_svpt']}/{l['d_svpt']}"}
        for t in ("t1", "t2", "t3", "t4", "t5", "t6"):
            rec[t] = bool(w[t] and l[t])
        reasons = []
        if not rec["my_code_equals_lead"]:
            reasons.append("link differs")
        if rec["winner_agrees"] is False:
            reasons.append("winner differs")
        if fails:
            reasons.append("fails Stage 0 checks: " + ";".join(fails))
        if rec["referee_against"]:
            reasons.append("T7 a referee reads the row's value")
        if group == "W22":
            if pd.isna(w["raw_svpt"]) and pd.isna(l["raw_svpt"]):
                reasons.append("T0 the row is blank, not corrupt: filling it is the source rule, not the 8 Oct bar")
            if not rec["t1"]:
                reasons.append("T1 MatchBeats incomplete, incoherent or not agreeing")
            if not rec["t2"]:
                reasons.append("T2 serve points not settled (row higher in a retirement, or no coherent capture)")
            if not rec["t3"]:
                reasons.append("T3 break points not settled")
            if not rec["t4"]:
                reasons.append("T4 service games")
            if not rec["t5"]:
                reasons.append("T5 '-'/'0' split change without Court Vision 2022 reading RG's split")
            if not rec["t6"]:
                reasons.append("T6 ace/double fault higher in the row, no referee reading RG's value")
        rec["confirmed"] = not reasons
        rec["reasons"] = "; ".join(reasons)
        rows.append(rec)
        if rec["confirmed"]:
            scope.append({"feed_key": o["feed_key"], "stage0_match_id": mid,
                          **{k: ("" if pd.isna(vals[k]) else int(vals[k])) for k in
                             [f"{sd}_{c}" for sd in ("w", "l") for c in NINE]}})
    sm = pd.DataFrame(rows)
    sm.to_csv(OUT / "scope_matches.csv", index=False)
    pd.DataFrame(scope, columns=SCOPE_COLS).to_csv(OUT / "overrides_scope.csv", index=False)

    # RGX
    ev = json.loads((OUT / "rgx_evidence.json").read_text(encoding="utf-8"))
    ex_rows = []
    for e in ev:
        ok = (e["all_eight_exchanged_equal"] and e["rg_winner_is_raw_winner"] and e["rg_loser_flag_false"]
              and e["winner_plays_next_round"] and not e["loser_plays_next_round"] and e["mb_equals_rg_both"]
              and e["mb_integrity"] and e["service_games"]["exchange_is_exact"] and not e["exchanged_box_fails"])
        if ok:
            ex_rows.append({"source_file": e["source_file"], "source_row": e["source_row"], "match_id": e["match_id"]})
    pd.DataFrame(ex_rows, columns=["source_file", "source_row", "match_id"]).to_csv(OUT / "exchanges_scope.csv",
                                                                                   index=False)

    def tally(g):
        return {"proposed": int(len(g)), "confirmed": int(g["confirmed"].sum()),
                "confirmed_values_equal_lead": int((g["confirmed"] & g["values_equal_lead"]).sum()),
                "confirmed_values_differ_from_lead": g[g["confirmed"] & ~g["values_equal_lead"]][
                    ["stage0_match_id", "values_differ_from_lead", "status"]].to_dict("records"),
                "excluded_by_reason": g.loc[~g["confirmed"], "reasons"].str.split("; ").explode()
                .str.replace(r":.*", "", regex=True).value_counts().to_dict(),
                "by_year_draw": g.groupby(["year", "tour", "draw"])["confirmed"].agg(["size", "sum"])
                .reset_index().to_dict("records")}
    summ = {"W22": tally(sm[sm["group"].eq("W22")]), "W26": tally(sm[sm["group"].eq("W26")]),
            "RGX": {"proposed": len(ev), "confirmed": len(ex_rows)}}
    (OUT / "scope_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk not in ("by_year_draw",)} if isinstance(v, dict) else v)
                      for k, v in summ.items()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
