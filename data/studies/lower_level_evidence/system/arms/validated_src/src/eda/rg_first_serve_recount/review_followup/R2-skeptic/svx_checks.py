"""R2-skeptic (round 2, SVX): the skeptic's checks on the swapped matches (svx_matches.csv, my derivation), against
the lead's proposed_swaps.csv.

    same set        my swapped matches against the lead's 323 (and its one left-out override)
    labels          the file's server labels fit the players named (serve points by name: RG's statistics, or the
                    AO row's)
    score           the row's score against the Slam's own (RG's set scores; the AO file's games per set where whole)
    file count      where the file holds the whole match, its own count of games each player served is the truth
    independent     the first server named by a hand chart, and by the Court Vision copy (its first point; RG
                    2019-2024), against the file's; calibrated on every match both hold, swapped or not
    Tennis My Life  TML's row of the same match (same tour, tournament id, round and names): its service games
                    against the truth and against Sackmann's
    candidate       another correction of the same raw row in the candidate's row_corrections.csv; B8 after the
                    exchange; retirements, walkovers, other statuses
    mechanism       the row equals the score's count as if the winner had served first
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    svx_checked.csv, svx_checks.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx_checks.py
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

import svx as SX  # noqa: E402  (my name folding and similarity)

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
DUMP = ROOT / "data" / "dump" / "points"
AO_ROUND = {"R128": "R128", "R64": "R64", "R32": "R32", "R16": "R16", "QF": "QF", "SF": "SF", "F": "F",
            "Q1": "Q1", "Q2": "Q2", "Q3": "Q3"}


def chart_first(df: pd.DataFrame) -> pd.Series:
    """The hand chart's first server for each match (by the row's names), where a chart of the match exists."""
    ch = pd.read_parquet(OUT / "mcp_first.parquet")
    ch["event"] = np.where(ch["tournament"].str.contains("Australian", case=False), "AO", "RG")
    ch["year"] = ch["date"].astype(str).str[:4].astype(int)
    ch["rnd"] = ch["round"].astype(str).str.upper()
    out = {}
    groups = {k: g for k, g in ch.groupby(["event", "year", "tour"])}
    for r in df.itertuples(index=False):
        g = groups.get((r.event, int(r.year), r.tour))
        if g is None:
            continue
        g = g[g["rnd"].eq(str(r.round))]
        wn, ln = SX.fold(r.winner), SX.fold(r.loser)
        best = None
        for c in g.itertuples(index=False):
            a, b = SX.fold(c.p1), SX.fold(c.p2)
            sc = max(min(SX.sim(wn, a), SX.sim(ln, b)), min(SX.sim(wn, b), SX.sim(ln, a)))
            if sc >= 2 and (best is None or sc > best[0]):
                best = (sc, c)
        if best is None:
            continue
        c = best[1]
        fs = SX.fold(c.parity_first_server)
        who = "w" if SX.sim(fs, wn) >= 2 and SX.sim(fs, wn) >= SX.sim(fs, ln) else (
            "l" if SX.sim(fs, ln) >= 2 else None)
        out[r.match_id] = (who, c.mcp_id, bool(c.opens_match), int(c.parity_dissent))
    return pd.Series(out, dtype=object)


def cv_first(df: pd.DataFrame) -> pd.Series:
    """The Court Vision copy's first server (its first point by point_ID order) for RG 2019-2024 matches it holds."""
    cat = pd.read_parquet(DUMP / "slam_ball_tracking" / "matches.parquet")
    cat = cat[cat["slam"].eq("RG")]
    out = {}
    for year in range(2019, 2025):
        f = DUMP / "slam_ball_tracking" / "points" / f"RG_{year}.parquet"
        if not f.exists():
            continue
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "server_id", "set_num", "game_num", "point_num"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        c = cat[cat["year"].astype(str).eq(str(year))]
        ids = {str(x).split("_")[-1]: (str(p1), str(p2), str(n1), str(n2)) for x, p1, p2, n1, n2 in
               zip(c["match_id"], c["player1_id"], c["player2_id"], c["player1"], c["player2"])}
        sub = df[df["event"].eq("RG") & df["year"].eq(year)]
        for r in sub.itertuples(index=False):
            q = pt[pt["code"].eq(str(r.code))]
            if q.empty or str(r.code) not in ids:
                continue
            order = pd.to_numeric(q["point_ID"].astype(str).str.replace(r"\D", "", regex=True), errors="coerce")
            if "set_num" in q and "game_num" in q:
                key = pd.DataFrame({"s": pd.to_numeric(q["set_num"], errors="coerce"),
                                    "g": pd.to_numeric(q["game_num"], errors="coerce"), "o": order})
                q = q.loc[key.sort_values(["s", "g", "o"]).index]
                first = q.iloc[0]
                opens = (pd.to_numeric(first["set_num"], errors="coerce") == 1
                         and pd.to_numeric(first["game_num"], errors="coerce") == 1)
            else:
                q = q.loc[order.sort_values().index]
                first, opens = q.iloc[0], None
            p1, p2, n1, n2 = ids[str(r.code)]
            sid = str(first["server_id"])
            name = n1 if sid == p1 else n2 if sid == p2 else None
            last = SX.fold(str(name).split(".", 1)[-1]) if name else []
            wl, ll = SX.fold(r.winner), SX.fold(r.loser)
            hit_w = bool(last) and any(t in wl for t in last)
            hit_l = bool(last) and any(t in ll for t in last)
            who = "w" if hit_w and not hit_l else "l" if hit_l and not hit_w else None
            out[r.match_id] = (who, opens)
    return pd.Series(out, dtype=object)


def tml_rows(df: pd.DataFrame) -> pd.DataFrame:
    """TML's raw row of each Stage 0 match (Sackmann rows only): same tour and round, the event's TML id, names."""
    rg = pd.read_parquet(OUT / "raw_rg.parquet")
    ao = pd.read_parquet(OUT / "raw_ao.parquet")
    t = pd.concat([rg[rg["source"].eq("tml")], ao[ao["source"].eq("tml")]], ignore_index=True)
    t["year"] = t["tid"].str[:4].astype(int)
    t["event"] = np.where(t["tourney_name"].str.contains("australian", case=False), "AO", "RG")
    t["tour_l"] = np.where(t["tour"].eq("atp"), "M", "W")
    t["round"] = t["round"].astype(str).str.upper()
    t["wn"], t["ln"] = t["winner_name"].map(SX.fold), t["loser_name"].map(SX.fold)
    groups = {k: g for k, g in t.groupby(["event", "year", "tour_l", "round"])}
    out = []
    for r in df.itertuples(index=False):
        g = groups.get((r.event, int(r.year), r.tour, str(r.round)))
        rec = {"match_id": r.match_id, "tml_w": np.nan, "tml_l": np.nan, "tml_found": False}
        if g is not None:
            wn, ln = SX.fold(r.winner), SX.fold(r.loser)
            for c in g.itertuples(index=False):
                straight = min(SX.sim(wn, c.wn), SX.sim(ln, c.ln))
                crossed = min(SX.sim(wn, c.ln), SX.sim(ln, c.wn))
                if max(straight, crossed) >= 2:
                    vw, vl = pd.to_numeric(c.w_SvGms, errors="coerce"), pd.to_numeric(c.l_SvGms, errors="coerce")
                    if crossed > straight:
                        vw, vl = vl, vw
                    rec.update({"tml_w": vw, "tml_l": vl, "tml_found": True, "tml_crossed": crossed > straight})
                    break
        out.append(rec)
    return pd.DataFrame(out)


def main() -> int:
    df = pd.read_csv(OUT / "svx_matches.csv")
    lead = pd.read_csv(LEAD / "service_games" / "proposed_swaps.csv")
    lm = pd.read_csv(LEAD / "service_games" / "matches.csv").drop_duplicates("match_id")
    mine = df[df["cls"].eq("swapped")]
    res = {"my_swapped": int(len(mine)), "lead_proposed": int(len(lead)),
           "mine_not_lead": sorted(set(mine["match_id"]) - set(lead["match_id"])),
           "lead_not_mine": sorted(set(lead["match_id"]) - set(mine["match_id"]))}
    res["lead_class_of_mine_not_lead"] = lm[lm["match_id"].isin(res["mine_not_lead"])][
        ["match_id", "cls", "rg_override", "decided_correction"]].to_dict("records")
    # independent first servers, on every match (calibration) and on the swapped ones
    ch, cv = chart_first(df), cv_first(df)
    df["chart_first"] = df["match_id"].map(lambda m: ch[m][0] if m in ch.index else None)
    df["chart_id"] = df["match_id"].map(lambda m: ch[m][1] if m in ch.index else None)
    df["cv_first"] = df["match_id"].map(lambda m: cv[m][0] if m in cv.index else None)
    df["cv_opens"] = df["match_id"].map(lambda m: cv[m][1] if m in cv.index else None)
    file_first = np.where(df["w_first"], "w", "l")
    df["file_first"] = file_first
    tm = tml_rows(df[df["source"].eq("sackmann")])
    df = df.merge(tm, on="match_id", how="left")
    # other corrections of the same raw row in the candidate
    rc = pd.read_csv(LEAD / "confirmed" / "candidate" / "corrections" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    rc_key = set(rc["source_file"] + "|" + rc["source_row"].astype(str))
    df["candidate_correction"] = (df["source_file"] + "|" + df["source_row"].astype(str)).isin(rc_key)
    rc_fix = dict(zip(rc["source_file"] + "|" + rc["source_row"].astype(str), rc["fix"] + ":" + rc["action"]))
    df["candidate_fix"] = (df["source_file"] + "|" + df["source_row"].astype(str)).map(rc_fix)
    ov = pd.read_csv(LEAD / "confirmed" / "candidate" / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    df["candidate_override"] = df["match_id"].isin(set(ov["stage0_match_id"]))
    df.to_csv(OUT / "svx_checked.csv", index=False)

    def tally(d: pd.DataFrame) -> dict:
        h = d[d["chart_first"].notna()]
        c = d[d["cv_first"].notna()]
        t = d[d["tml_found"].eq(True) & d["tml_w"].notna()]
        return {"matches": int(len(d)),
                "labels_exact": int(d["labels_exact"].sum()), "labels_fit_not_exact": int((~d["labels_exact"] &
                                                                                            d["labels_fit"]).sum()),
                "labels_fail": int((~d["labels_ok"]).sum()),
                "row_score_equals_slam_score": int(d["row_games_per_set"].eq(d["slam_games_per_set"]).sum()),
                "file_whole": int(d["file_whole"].sum()),
                "file_count_is_truth_where_whole": int(d.loc[d["file_whole"], "file_count_is_truth"].astype(bool).sum()),
                "chart_held": int(len(h)), "chart_agrees_with_file": int((h["chart_first"] == h["file_first"]).sum()),
                "cv_held": int(len(c)), "cv_agrees_with_file": int((c["cv_first"] == c["file_first"]).sum()),
                "tml_held": int(len(t)),
                "tml_equals_truth": int((t["tml_w"].eq(t["true_w"]) & t["tml_l"].eq(t["true_l"])).sum()),
                "tml_equals_sackmann": int((t["tml_w"].eq(t["raw_w"]) & t["tml_l"].eq(t["raw_l"])).sum()),
                "tml_zero_or_blank": int((t["tml_w"].fillna(0).eq(0) | t["tml_l"].fillna(0).eq(0)).sum()),
                "candidate_correction_same_row": int(d["candidate_correction"].sum()),
                "candidate_override_same_match": int(d["candidate_override"].sum()),
                "b8_after_fails": int((~d["b8_after_ok"]).sum()), "b8_before_fails": int((~d["b8_before_ok"]).sum()),
                "status": d["status"].value_counts().to_dict(),
                "row_as_if_winner_first": int(d["row_as_if_winner_first"].sum()),
                "winner_disagrees_with_slam": int(d["winner_agrees"].eq(False).sum())}
    sw = df[df["cls"].eq("swapped")]
    res["swapped"] = tally(sw)
    res["swapped_by_edition"] = {f"{e}{y}": tally(g) for (e, y), g in sw.groupby(["event", "year"])}
    res["all_proven_matches"] = tally(df[df["proven"]])
    res["chart_disagreements_all"] = df[df["chart_first"].notna() & (df["chart_first"] != df["file_first"])][
        ["match_id", "event", "year", "cls", "chart_id", "chart_first", "file_first", "proven"]].to_dict("records")
    res["cv_disagreements_all"] = df[df["cv_first"].notna() & (df["cv_first"] != df["file_first"])][
        ["match_id", "event", "year", "cls", "cv_first", "cv_opens", "file_first", "proven"]].to_dict("records")
    res["swapped_flags"] = sw[(~sw["labels_ok"]) | (~sw["b8_after_ok"]) | sw["candidate_correction"]
                              | sw["candidate_override"] | (sw["row_games_per_set"] != sw["slam_games_per_set"])
                              | sw["status"].ne("completed")][
        ["match_id", "status", "labels_ok", "b8_after_ok", "candidate_fix", "candidate_override", "row_score",
         "slam_games_per_set", "row_games_per_set"]].to_dict("records")
    (OUT / "svx_checks.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("swapped_by_edition",)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
