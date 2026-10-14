"""R2-skeptic (round 2): the four RG 2021 boxes proposed for exchange_box (fix RGX), attacked.

For each match (the lead's proposed_exchanges.csv), from my own parses:
    the raw row (Stage 0's raw loader): names, score, the nine counts per side
    RG's match document: names, winner flags, set scores, the eight counts per team
    RG's MatchBeats (2021, decrypted): the eight point counts recounted, completeness, integrity, the first server,
        and the service games each player served (tie-breaks not counted) against the score
    the Court Vision copy, where it holds the match (recounted here; one row per serve, faults their own rows)
    the hand charts (Match Charting Project), where they hold the match
    who played the next round (Stage 0's RG 2021 women's matches)
    the exchanged box under Stage 0's checks (B0-B9) and against RG's record
Alternatives tested: names swapped instead of boxes (then RG's winner, the score's orientation and the next round would
name the other player); a partial exchange (some counts only).

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    rgx_evidence.json, rgx_rows.csv
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/rgx.py
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

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
DUMP = ROOT / "data" / "dump" / "points"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
EIGHT = [c for c in NINE if c != "SvGms"]
NEXT = {"R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF"}


def cv_counts(year: int, code: str) -> dict:
    cat = pd.read_parquet(DUMP / "slam_ball_tracking" / "matches.parquet")
    c = cat[(cat["slam"].eq("RG")) & cat["year"].astype(str).eq(str(year)) & cat["match_id"].astype(str).eq(code)]
    if c.empty:
        return {}
    pt = pd.read_parquet(DUMP / "slam_ball_tracking" / "points" / f"RG_{year}.parquet")
    pt = pt[pt["match_id"].astype(str).str.split("_").str[-1].eq(code)].drop_duplicates(["match_id", "point_ID"])
    pts = pt[~pt["point_end_type"].isin(["Faulty Serve"])]
    out = {}
    r = c.iloc[0]
    for pid, nm in ((r["player1_id"], r["player1"]), (r["player2_id"], r["player2"])):
        s = pts[pts["server_id"].astype(str).eq(str(pid))]
        n = s["serve_num"].astype(str)
        w = s["point_winner_id"].astype(str).eq(str(pid))
        out[str(nm)] = {"svpt": int(len(s)), "1stIn": int(n.eq("1").sum()), "1stWon": int((n.eq("1") & w).sum()),
                        "2ndWon": int((n.eq("2") & w).sum()), "ace": int(s["point_end_type"].eq("Ace").sum()),
                        "df": int(s["point_end_type"].eq("DoubleFault").sum())}
    return out


def mcp_counts(year: int, names: list[str]) -> list[dict]:
    base = DUMP / "match_charting_project"
    out = []
    for g in ("w",):
        o = pd.read_parquet(base / "stats" / f"charting-{g}-stats-Overview.parquet")
        o = o[o["set"].astype(str).eq("Total")]
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        mm = mm[mm["Tournament"].astype(str).str.contains("Roland Garros", case=False)
                & mm["Date"].astype(str).str.startswith(str(year))]
        last = [n.split()[-1].casefold() for n in names]
        hit = mm[mm["Player 1"].astype(str).str.casefold().str.contains(last[0])
                 & mm["Player 2"].astype(str).str.casefold().str.contains(last[1])
                 | mm["Player 1"].astype(str).str.casefold().str.contains(last[1])
                 & mm["Player 2"].astype(str).str.casefold().str.contains(last[0])]
        for mid in hit["match_id"]:
            for r in o[o["match_id"].eq(mid)].itertuples(index=False):
                out.append({"mcp_id": mid, "player": r.player, "svpt": r.serve_pts, "1stIn": r.first_in,
                            "1stWon": r.first_won, "2ndWon": r.second_won, "ace": r.aces, "df": r.dfs})
    return out


def main() -> int:
    ex = pd.read_csv(LEAD / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    s = pd.read_parquet(OUT / "players.parquet")
    sv = pd.read_csv(OUT / "svgms_rows.csv")
    it = pd.read_csv(OUT / "mb_integrity.csv")
    bp = pd.read_csv(OUT / "bp_rows.csv")
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tournament_id", "round", "year"])
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    rg21 = p.merge(m[m["tournament_id"].eq("2021-520")], on="match_id")
    ev, rows = [], []
    for e in ex.itertuples(index=False):
        g = s[s["match_id"].eq(e.match_id)]
        w, l = g[g["side"].eq("w")].iloc[0], g[g["side"].eq("l")].iloc[0]
        rec = {"match_id": e.match_id, "source_file": e.source_file, "source_row": int(e.source_row),
               "code": w["code"], "round": w["round"], "raw_winner": w["player"], "raw_loser": l["player"],
               "raw_score": w["raw_score"], "rg_winner_is_raw_winner": bool(w["rg_winner"] is True or w["rg_winner"] == True),
               "rg_loser_flag_false": bool(l["rg_winner"] is False or l["rg_winner"] == False),
               "rg_sets_winner_side": [json.loads(w["rg_set_games"]), json.loads(w["rg_opp_set_games"])]}
        # the box as recorded vs RG, and exchanged vs RG
        rec["as_recorded_equal_rg"] = {c: [bool(w[f"raw_{c}"] == w[f"my_{c}"]), bool(l[f"raw_{c}"] == l[f"my_{c}"])]
                                       for c in EIGHT}
        rec["exchanged_equal_rg"] = {c: [bool(l[f"raw_{c}"] == w[f"my_{c}"]), bool(w[f"raw_{c}"] == l[f"my_{c}"])]
                                     for c in EIGHT}
        rec["all_eight_exchanged_equal"] = all(all(v) for v in rec["exchanged_equal_rg"].values())
        rec["any_count_equal_as_recorded_and_different_exchanged"] = [c for c in EIGHT if all(rec["as_recorded_equal_rg"][c])
                                                                      and not all(rec["exchanged_equal_rg"][c])]
        # MatchBeats as a second RG record
        rec["mb"] = {side: {c: (None if pd.isna(x.get(f"mb_{k}")) else int(x.get(f"mb_{k}"))) for c, k in
                            (("svpt", "svpt"), ("1stIn", "first_in"), ("1stWon", "first_won"), ("2ndWon", "second_won"),
                             ("ace", "ace"), ("df", "df"))} for side, x in (("w", w), ("l", l))}
        rec["mb_equals_rg_both"] = all(rec["mb"][sd][c] == int(x[f"my_{c}"]) for sd, x in (("w", w), ("l", l))
                                       for c in ("svpt", "1stIn", "1stWon", "2ndWon", "ace", "df"))
        iti = it[(it["year"].eq(2021)) & it["code"].eq(w["code"])]
        rec["mb_integrity"] = bool(iti["integrity"].iloc[0]) if len(iti) else None
        b = bp[bp["match_id"].eq(e.match_id)].set_index("side")
        rec["mb_break_points_w_l"] = [[int(b.loc["w", "mbbp_faced"]), int(b.loc["w", "mbbp_saved"])],
                                      [int(b.loc["l", "mbbp_faced"]), int(b.loc["l", "mbbp_saved"])]]
        v = sv[sv["match_id"].eq(e.match_id)].set_index("side")
        rec["service_games"] = {"raw_w_l": [w["raw_SvGms"], l["raw_SvGms"]],
                                "score_excl_w_l": [int(v.loc["w", "exp_excl"]), int(v.loc["l", "exp_excl"])],
                                "mb_regular_w_l": [int(v.loc["w", "mb_sv_gms_regular"]), int(v.loc["l", "mb_sv_gms_regular"])]}
        rec["service_games"]["exchange_is_exact"] = (rec["service_games"]["raw_w_l"][::-1] ==
                                                     rec["service_games"]["score_excl_w_l"])
        # the next round
        nxt = rg21[rg21["round"].eq(NEXT.get(w["round"], "-"))]
        rec["winner_plays_next_round"] = bool(nxt["player_name"].eq(w["player"]).any())
        rec["loser_plays_next_round"] = bool(nxt["player_name"].eq(l["player"]).any())
        rec["court_vision"] = cv_counts(2021, w["code"])
        rec["mcp"] = mcp_counts(2021, [w["player"], l["player"]])
        # Stage 0's checks on the exchanged box, under the row's score
        exch = {"w": {c: l[f"raw_{c}"] for c in NINE}, "l": {c: w[f"raw_{c}"] for c in NINE}}
        fails = []
        for sd, f in exch.items():
            if f["1stIn"] > f["svpt"]:
                fails.append(f"B1 {sd}")
            if f["1stWon"] > f["1stIn"]:
                fails.append(f"B2 {sd}")
            if f["2ndWon"] > f["svpt"] - f["1stIn"]:
                fails.append(f"B3 {sd}")
            if f["bpSaved"] > f["bpFaced"]:
                fails.append(f"B4 {sd}")
            if f["df"] > f["svpt"] - f["1stIn"]:
                fails.append(f"B6 {sd}")
            if f["ace"] > f["1stWon"] + f["2ndWon"]:
                fails.append(f"B7 {sd}")
            if f["bpFaced"] - f["bpSaved"] > f["SvGms"]:
                fails.append(f"B8 {sd}")
        games = sum(sum(x) for x in zip(*rec["rg_sets_winner_side"]))
        if exch["w"]["svpt"] + exch["l"]["svpt"] < 4.5 * games:
            fails.append("B9")
        rec["exchanged_box_fails"] = fails
        # breaks conceded = the opponent's games won on serve: a check of bp against the score
        ev.append(rec)
        for sd, x, o in (("w", w, l), ("l", l, w)):
            rows.append({"match_id": e.match_id, "side": sd, "player": x["player"],
                         **{f"raw_{c}": x[f"raw_{c}"] for c in NINE}, **{f"rg_{c}": x[f"my_{c}"] for c in EIGHT},
                         **{f"exchanged_{c}": o[f"raw_{c}"] for c in NINE}})
    pd.DataFrame(rows).to_csv(OUT / "rgx_rows.csv", index=False)
    (OUT / "rgx_evidence.json").write_text(json.dumps(ev, indent=1, default=str) + "\n", encoding="utf-8")
    for r in ev:
        print(json.dumps({k: v for k, v in r.items() if k not in ("as_recorded_equal_rg", "exchanged_equal_rg")},
                         default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
