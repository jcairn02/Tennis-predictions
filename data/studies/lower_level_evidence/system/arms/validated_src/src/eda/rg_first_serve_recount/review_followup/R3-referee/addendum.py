"""R3-referee (follow-up, addendum): the 12 changed and 32 added matches of the amended proposal.

For each match of followup/review/addendum_matches.csv, derived here with my own code:
  * MatchBeats (decrypted with the adapter's decrypt/blocks_of): per player the completed, non-tiebreak games it
    served (isGameComplete not false; isTieBreak false and one server; a game's server is the one serving most of its
    points), the unfinished games, who served the match's first point, and whether it holds every point of both
    players (its serve points equal RG's statistics');
  * the score's alternation (my own implementation): from the row's score and MatchBeats' first server, servers
    alternate game by game through the match, a tiebreak taking one turn and not counted, a match tiebreak one turn;
    a score holds only finished games;
  * my value per player, in the amended rule's order, each only where the pair fits the score (B5): MatchBeats where
    it holds every point of both players, else the alternation, else the row's own count, else blank; and whether
    MatchBeats and the alternation agree where both exist;
  * the eight counts: my parse of RG's raw API documents (official_rows.csv), against the row's and the proposal's;
  * independent records: Court Vision (2019-2024; games one player served outside tiebreaks, and whether the match's
    last game is unfinished) and the hand charts (games served outside 6-6 tiebreaks), with the unfinished game of a
    retirement reported apart;
  * the amended override row's eighteen values against mine.
Writes addendum_rows.csv and addendum_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/addendum.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import official as OF  # noqa: E402
import r3f as F  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_saved", "bp_faced"]


def mb_games(doc: dict) -> dict:
    """Per MatchBeats slot: completed non-tiebreak games served, all games served, unfinished games; the first server."""
    games = []
    for s in doc.get("setData") or []:
        for g in s.get("gameData") or []:
            pts = g.get("pointData") or []
            if not pts:
                continue
            srv = Counter(str(p.get("server")) for p in pts)
            tb = bool(g.get("isTieBreak")) or len(srv) > 1
            games.append({"server": srv.most_common(1)[0][0], "tb": tb, "done": g.get("isGameComplete") is not False,
                          "first_point_server": str(pts[0].get("server"))})
    first = games[0]["first_point_server"] if games else None
    out = {"first": first, "unfinished": sum(not g["done"] for g in games),
           "unfinished_server": next((g["server"] for g in games if not g["done"]), None)}
    for k in ("1", "2"):
        out[f"p{k}_done_regular"] = sum(1 for g in games if g["done"] and not g["tb"] and g["server"] == k)
        out[f"p{k}_all_regular"] = sum(1 for g in games if not g["tb"] and g["server"] == k)
    return out


def alternation(score: str, first_is_winner: bool) -> tuple[float, float]:
    """(winner, loser) service games from the score's sets read from the winner's side: game slots alternate from the
    first server; the deciding game of a tiebreak set is a slot but no service game; a match tiebreak is one slot."""
    sets, _ = B.tokens_of(str(score or ""))
    if not sets:
        return np.nan, np.nan
    slot, w, l = 0, 0, 0
    for a, b, tb, bracket in sets:
        if bracket:
            slot += 1
            continue
        n = a + b
        tiebreak_set = B.is_tiebreak(a, b, tb, bracket, False) and B.set_complete(a, b, tb, bracket, False)
        for i in range(n):
            last_tb = tiebreak_set and i == n - 1
            winner_serves = (slot % 2 == 0) == first_is_winner
            if not last_tb:
                if winner_serves:
                    w += 1
                else:
                    l += 1
            slot += 1
    return float(w), float(l)


def fits(w, l, games, tb) -> bool:
    if pd.isna(w) or pd.isna(l):
        return False
    t = w + l
    return abs(t - (games - tb)) <= 1 or abs(t - games) <= 1


def main() -> int:
    add = pd.read_csv(F.FOLLOW / "review" / "addendum_matches.csv", dtype=str, keep_default_na=False)
    ov2 = pd.read_csv(F.FOLLOW / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    ov1 = pd.read_csv(F.FOLLOW / "proposed_overrides_v1.csv", dtype=str, keep_default_na=False)
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    o = o[o["code"].notna() & ~(o["source"].eq("tml") & o["draw"].eq("main"))].copy()
    o["feed_key"] = "rolandgarros:" + o["season"].astype(int).astype(str) + "/" + o["code"]
    P = pd.read_csv(F.OUT / "ref_rows.csv", low_memory=False)
    # the referees' service games and whether their last game is the unfinished one
    cvp = {}
    for f in sorted((F.DUMP / "slam_ball_tracking" / "points").glob("RG_*.parquet")):
        yr = int(f.stem.split("_")[1])
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "set_num", "game_num", "server_id", "point_end_type",
                                         "is_tiebreak"])
        pt = pt[~pt["point_end_type"].eq("Faulty Serve")].drop_duplicates(["match_id", "point_ID"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        for code, g in pt.groupby("code"):
            g = g.assign(s=pd.to_numeric(g["set_num"], errors="coerce"), gm=pd.to_numeric(g["game_num"], errors="coerce"))
            last = g.sort_values(["s", "gm"]).iloc[-1]
            cvp[(yr, code)] = {"last_game_server": str(last["server_id"]).replace(".0", "")}
    out = []
    for a in add.to_dict("records"):
        x = o[o["feed_key"].eq(a["feed_key"])]
        if len(x) != 1:
            out.append({"feed_key": a["feed_key"], "what": a["what"], "problem": f"{len(x)} rows of mine"})
            continue
        x = x.iloc[0]
        year, code = int(x["season"]), x["code"]
        route, doc = OF.mb_doc(year, code)
        g = mb_games(doc) if doc is not None else {}
        w_slot = x.get("mb_w_slot")
        w_slot = str(int(w_slot)) if pd.notna(w_slot) else None
        l_slot = None if w_slot is None else ("2" if w_slot == "1" else "1")
        rec = {"what": a["what"], "feed_key": a["feed_key"], "stage0_match_id": a["stage0_match_id"],
               "source": x["source"], "season": year, "draw": x["draw"], "round": x["round"],
               "winner_name": x["winner_name"], "loser_name": x["loser_name"], "score": x["score"],
               "status": x["status_parsed"], "games": x["games"], "std_tb": x["std_tb"], "mb_route": route,
               "mb_complete_both": bool(x["mb_complete_both"]), "mb_unfinished_games": g.get("unfinished")}
        first_is_w = None
        if w_slot is not None and g.get("first") is not None:
            first_is_w = g["first"] == w_slot
        rec["first_server"] = None if first_is_w is None else ("w" if first_is_w else "l")
        alt = alternation(x["score"], first_is_w) if first_is_w is not None else (np.nan, np.nan)
        for s, k in (("w", w_slot), ("l", l_slot)):
            rec[f"row_{s}"] = x[f"raw_{s}_sv_gms"]
            rec[f"mb_done_{s}"] = g.get(f"p{k}_done_regular") if k else np.nan
            rec[f"mb_all_{s}"] = g.get(f"p{k}_all_regular") if k else np.nan
            rec[f"alt_{s}"] = alt[0] if s == "w" else alt[1]
        games, tb = x["games"], x["std_tb"]
        mb_ok = rec["mb_complete_both"] and fits(rec["mb_done_w"], rec["mb_done_l"], games, tb)
        alt_ok = fits(rec["alt_w"], rec["alt_l"], games, tb)
        row_ok = fits(rec["row_w"], rec["row_l"], games, tb) and not (rec["row_w"] == 0 or rec["row_l"] == 0)
        src = "matchbeats" if mb_ok else "alternation" if alt_ok else "row" if row_ok else "none"
        rec["my_sv_from"] = src
        for s in ("w", "l"):
            rec[f"my_{s}_sv_gms"] = {"matchbeats": rec[f"mb_done_{s}"], "alternation": rec[f"alt_{s}"],
                                    "row": rec[f"row_{s}"], "none": np.nan}[src]
        rec["mb_equals_alternation"] = (rec["mb_done_w"] == rec["alt_w"] and rec["mb_done_l"] == rec["alt_l"]) \
            if not pd.isna(rec["alt_w"]) and not pd.isna(rec["mb_done_w"]) else None
        rec["row_equals_mine"] = rec["row_w"] == rec["my_w_sv_gms"] and rec["row_l"] == rec["my_l_sv_gms"]
        rec["unfinished_server_side"] = None if not g.get("unfinished_server") or w_slot is None else (
            "w" if g["unfinished_server"] == w_slot else "l")
        # the eight counts: mine (RG's statistics) against the row's
        rec["eight_mine_equal_row"] = all(x[f"my_{s}_{c}"] == x[f"raw_{s}_{c}"] for s in ("w", "l") for c in EIGHT)
        # referees
        for s, side in (("w", "w"), ("l", "l")):
            q = P[(P["source_file"] == x["source_file"]) & (P["source_row"] == x["source_row"]) & (P["side"] == side)]
            rec[f"cv_{s}"] = q["cv_sv_gms"].iloc[0] if len(q) else np.nan
            rec[f"mcp_{s}"] = q["mcp_sv_gms"].iloc[0] if len(q) else np.nan
            rec[f"rg_id_{s}"] = q["rg_id"].iloc[0] if len(q) else None
        cvl = cvp.get((year, code), {})
        rec["cv_last_game_server"] = ("w" if cvl.get("last_game_server") == str(rec["rg_id_w"]) else
                                      "l" if cvl.get("last_game_server") == str(rec["rg_id_l"]) else None) if cvl else None
        # the amended override row and v1
        r2 = ov2[ov2["feed_key"].eq(a["feed_key"])]
        r1 = ov1[ov1["feed_key"].eq(a["feed_key"])]
        rec["in_v2"], rec["in_v1"] = len(r2) == 1, len(r1) == 1
        mine = {}
        for s in ("w", "l"):
            for c, col in F.NINE.items():
                v = rec[f"my_{s}_sv_gms"] if c == "sv_gms" else x[f"my_{s}_{c}"]
                mine[f"{s}_{col}"] = "" if pd.isna(v) else str(int(v))
        diffs = [f"{k}:{r2.iloc[0][k]}/{v}" for k, v in mine.items() if len(r2) and r2.iloc[0][k] != v]
        rec["differences_from_v2"] = " ".join(diffs) if len(r2) else "not in v2"
        rec.update({f"mine_{k}": v for k, v in mine.items()})
        out.append(rec)
    d = pd.DataFrame(out)
    d.to_csv(F.OUT / "addendum_rows.csv", index=False)
    smry = {"matches": int(len(d)), "by_what": d["what"].value_counts().to_dict(),
            "values_equal_v2": int(d["differences_from_v2"].eq("").sum()),
            "differences": d.loc[d["differences_from_v2"].ne(""), ["feed_key", "differences_from_v2"]].to_dict("records"),
            "my_sv_from": d.groupby(["what", "my_sv_from"]).size().rename("matches").reset_index().to_dict("records"),
            "mb_equals_alternation": d["mb_equals_alternation"].value_counts(dropna=False).astype(int).to_dict(),
            "eight_mine_equal_row_added": int(d.loc[d["what"].eq("added"), "eight_mine_equal_row"].sum())}
    (F.OUT / "addendum_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 100)
    pd.set_option("display.max_columns", 60)
    print(json.dumps(smry, indent=1, default=str))
    print(d[["what", "feed_key", "winner_name", "loser_name", "score", "status", "first_server", "row_w", "row_l",
             "mb_done_w", "mb_done_l", "mb_all_w", "mb_all_l", "alt_w", "alt_l", "my_sv_from", "my_w_sv_gms",
             "my_l_sv_gms", "mb_complete_both", "unfinished_server_side", "cv_w", "cv_l", "mcp_w", "mcp_l",
             "cv_last_game_server"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
