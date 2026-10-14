"""R2-skeptic (round 2, addendum): the 32 matches the amended proposal adds (service games only) and Maestrelli-Noguchi
2026 (QM080, service games derived where MatchBeats misses points), with the same bars as before: the 8 Oct bar for
W22 (2022-2025), the source rule for W26 (2026).

For each match, from my own tables (players.parquet, svgms_rows.csv, mb_integrity.csv, mb_points.parquet,
api.parquet):
    eight      the row's eight counts equal RG's statistics (my parse), and so do the amended table's
    first      MatchBeats' first point is the match's first point (set 1, game 1, point 1), and every game MatchBeats
               holds outside tie-breaks is served by the player the alternation from that first server names
               (servers alternate game by game through the match, a tie-break taking one turn), indexing games by RG's
               set scores: the first server is then certain even where the file misses points or games
    exact      each player's completed non-tie-break service games from RG's set scores and that first server
    row        the row's service games: TML's zero, Sackmann's blank, or Sackmann's count; for the latter, whether it is
               the exact count, the tie-breaks-counted count (a convention, not an error), the exact count exchanged
               between the players, or neither
    amended    the amended table's service games against mine
Decision:
    W26 (source rule): confirm where the eight counts equal RG's, the first server is certain and the amended values are
        the exact count.
    W22 (8 Oct bar): confirm where, besides that, MatchBeats holds RG's serve points and passes the integrity test, and
        the row's count is corrupt: the exact count (from the score and the first server) disproves it, and it is not
        the tie-breaks-counted convention. A blank count is not corrupt (as T0 of build_scope.py): left out.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    addendum_check.csv    one row per match (33): every test, my values, the decision and the reason
    addendum_summary.json counts
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/addendum.py
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

import build_scope as BS  # noqa: E402  (my own Stage 0 box checks, B0-B9)

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
EIGHT = [c for c in NINE if c != "SvGms"]


def alternation(pts: pd.DataFrame, set_games: list[tuple[int, int]]) -> dict:
    """Is MatchBeats' first point the match's first, and does every non-tie-break game it holds follow the
    alternation from that first server? Games are indexed through the match by RG's set scores."""
    pts = pts.sort_values("idx")
    first = pts.iloc[0]
    starts_at_start = int(first["set"]) == 1 and int(first["game"]) == 1 and str(first["pointId"]).startswith("1_1_1_")
    offset, before = {}, 0
    for i, (a, b) in enumerate(set_games, 1):
        offset[i] = before
        before += a + b
    breaks, held = 0, 0
    fs = str(first["server"])
    other = "2" if fs == "1" else "1"
    for (s, g), game in pts.groupby(["set", "game"]):
        if bool(game["tb"].iloc[0]) or int(s) not in offset:
            continue
        held += 1
        k = offset[int(s)] + int(g)                  # 1-based index of the game in the match
        expect = fs if k % 2 == 1 else other
        server = game["server"].mode().iloc[0]
        breaks += int(server != expect)
    return {"first_point_is_match_first": bool(starts_at_start), "first_server_slot": fs,
            "games_held": held, "games_off_alternation": breaks,
            "games_in_score": before}


def main() -> int:
    add = pd.read_csv(LEAD / "review" / "addendum_matches.csv")
    add = add[add["what"].eq("added") | add["stage0_match_id"].eq("atp|2026-520|Q1|atp:200677|atp:208353")]
    v2 = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    s = pd.read_parquet(OUT / "players.parquet")
    sv = pd.read_csv(OUT / "svgms_rows.csv")[["match_id", "side", "exp_excl", "exp_incl", "mb_sv_gms_regular"]]
    s = s.merge(sv, on=["match_id", "side"], how="left", suffixes=("", "_sv"))
    it = pd.read_csv(OUT / "mb_integrity.csv")[["year", "code", "integrity", "last_game_open"]]
    s = s.merge(it, on=["year", "code"], how="left")
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    rows, scope = [], []
    for a in add.itertuples(index=False):
        mid = a.stage0_match_id
        g = s[s["match_id"].eq(mid)]
        w, l = g[g["side"].eq("w")].iloc[0], g[g["side"].eq("l")].iloc[0]
        o = v2[v2["stage0_match_id"].eq(mid)].iloc[0]
        year = int(w["year"])
        group = "W26" if year == 2026 else "W22"
        rec = {"group": group, "what": a.what, "feed_key": a.feed_key, "stage0_match_id": mid, "year": year,
               "draw": w["draw"], "round": w["round"], "source": w["source"], "status": w["status"],
               "winner": w["player"], "loser": l["player"], "row_score": w["raw_score"]}
        rec["eight_row_equal_rg"] = all(w[f"raw_{c}"] == w[f"my_{c}"] and l[f"raw_{c}"] == l[f"my_{c}"] for c in EIGHT)
        rec["eight_amended_equal_rg"] = all(float(o[f"{sd}_{c}"]) == x[f"my_{c}"] for sd, x in (("w", w), ("l", l))
                                            for c in EIGHT)
        # the first server and the alternation
        sg = list(zip(json.loads(w["rg_set_games"]), json.loads(w["rg_opp_set_games"])))
        sg = [(x, y) for x, y in sg if x is not None and y is not None]
        p = pts[(pts["year"].eq(year)) & pts["code"].eq(w["code"])]
        # RG's set scores in MatchBeats' slot order (the alternation does not depend on the order of the two numbers)
        alt = alternation(p, sg)
        rec.update(alt)
        rec["mb_complete"] = bool(w["mb_complete_match"])
        rec["mb_integrity"] = bool(w["integrity"]) if pd.notna(w["integrity"]) else None
        rec["first_server_certain"] = alt["first_point_is_match_first"] and alt["games_off_alternation"] == 0 \
            and alt["games_held"] > 0
        rec["exact_w_l"] = [w["exp_excl"], l["exp_excl"]]
        rec["incl_w_l"] = [w["exp_incl"], l["exp_incl"]]
        rec["mb_completed_w_l"] = [w["mb_sv_gms_regular"], l["mb_sv_gms_regular"]]
        rec["row_w_l"] = [w["raw_SvGms"], l["raw_SvGms"]]
        rec["amended_w_l"] = [float(o["w_SvGms"]) if o["w_SvGms"] != "" else np.nan,
                              float(o["l_SvGms"]) if o["l_SvGms"] != "" else np.nan]
        rec["amended_equals_exact"] = rec["amended_w_l"] == rec["exact_w_l"]
        rw, rl = rec["row_w_l"]
        if w["source"] == "tml" and (rw == 0 or rl == 0):
            kind = "TML zero"
        elif pd.isna(rw) or pd.isna(rl):
            kind = "row blank"
        elif [rw, rl] == rec["exact_w_l"]:
            kind = "row exact"
        elif [rw, rl] == rec["incl_w_l"]:
            kind = "row tie-breaks counted (convention)"
        elif [rw, rl] == rec["exact_w_l"][::-1]:
            kind = "row exchanged between the players"
        elif rw + rl == sum(rec["exact_w_l"]):
            kind = "row right total, impossible split"
        else:
            kind = "row neither"
        rec["row_kind"] = kind
        reasons = []
        # an added match changes service games only (its row's eight counts are RG's); QM080 was proposed in v1 and
        # its amended eight counts are RG's (TML's differ)
        if not rec["eight_amended_equal_rg"] or (a.what == "added" and not rec["eight_row_equal_rg"]):
            reasons.append("eight counts not RG's")
        if not rec["first_server_certain"]:
            reasons.append("first server not certain")
        if not rec["amended_equals_exact"]:
            reasons.append("amended service games are not the exact count")
        if group == "W22":
            if not (rec["mb_complete"] and rec["mb_integrity"]):
                reasons.append("T1 capture incomplete or incoherent")
            if kind == "row blank":
                reasons.append("T0 the row's service games are blank, not corrupt: filling them is the source rule")
            elif kind in ("row exact", "row tie-breaks counted (convention)"):
                reasons.append(f"not corrupt: {kind}")
        fails = BS.stage0_checks({c: (w[f"my_{c}"] if c != "SvGms" else w["exp_excl"]) for c in NINE},
                                 {c: (l[f"my_{c}"] if c != "SvGms" else l["exp_excl"]) for c in NINE},
                                 w["raw_score"], w["status"])
        rec["stage0_checks_failed"] = ";".join(fails)
        if fails:
            reasons.append("fails Stage 0 checks: " + ";".join(fails))
        rec["confirmed"] = not reasons
        rec["reasons"] = "; ".join(reasons)
        rows.append(rec)
        if rec["confirmed"]:
            vals = {}
            for sd, x in (("w", w), ("l", l)):
                for c in EIGHT:
                    vals[f"{sd}_{c}"] = int(x[f"my_{c}"])
                vals[f"{sd}_SvGms"] = int(x["exp_excl"])
            scope.append({"feed_key": a.feed_key, "stage0_match_id": mid, **vals})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "addendum_check.csv", index=False)
    pd.DataFrame(scope).to_csv(OUT / "addendum_scope_rows.csv", index=False)
    summ = {"matches": int(len(out)), "confirmed": int(out["confirmed"].sum()),
            "by_group_kind": out.groupby(["group", "what", "row_kind"])["confirmed"].agg(["size", "sum"]).reset_index()
            .to_dict("records"),
            "left_out": out[~out["confirmed"]][["stage0_match_id", "row_kind", "reasons"]].to_dict("records"),
            "first_server_certain": int(out["first_server_certain"].sum()),
            "amended_equals_exact": int(out["amended_equals_exact"].sum()),
            "eight_equal": int((out["eight_row_equal_rg"] & out["eight_amended_equal_rg"]).sum())}
    (OUT / "addendum_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 60)
    print(out[["group", "what", "feed_key", "status", "row_kind", "row_w_l", "exact_w_l", "incl_w_l", "amended_w_l",
               "mb_completed_w_l", "mb_complete", "mb_integrity", "first_server_certain", "games_held",
               "games_in_score", "confirmed", "reasons"]].to_string())
    print(json.dumps({k: v for k, v in summ.items() if k != "by_group_kind"}, indent=1, default=str))
    print(pd.DataFrame(summ["by_group_kind"]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
