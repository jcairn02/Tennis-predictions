"""F2 step 1: the 88 candidate matches, internal evidence and the WTA API.

Per match (Stage 0, live 7 Oct tables):
  * games identity (my own): for each player, holds + breaks of the opponent's serve (+ tiebreak sets won, when
    service games exclude tiebreaks) must equal the games the score gives that player. Tested as recorded and with
    the two box scores exchanged. Tiebreak matches are also tested with service games counting tiebreaks
    (total service games = all games; each player's box games within [games - tiebreaks won, games]).
  * points: total points won by the recorded winner, as recorded and exchanged;
  * progression: does the recorded winner / loser play the next round of the same event in Stage 0;
  * service games: |sv_gms difference| <= 1 (symmetric, a sanity check only);
  * the raw Sackmann row equals Stage 0's counts (player by player);
  * WTA API (wta_api_links_2019..2026.parquet): Stage 0 box under each player equals the API's counts for that
    player (all nine) as recorded, or exchanged.
Writes f2_internal.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_colwidth", 60)
cand = pd.read_csv(R.AUDIT / "box_swapped_oct07.csv")
m, p = R.stage0()
m = m.set_index("match_id")
NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F"}

# progression index: (tour, tournament_id, round) -> set of players
mm = m.reset_index()
held = {}
for t, tid, rnd, a, b in zip(mm["tour"], mm["tournament_id"], mm["round"], mm["player_a_id"], mm["player_b_id"]):
    held.setdefault((t, tid, rnd), set()).update((a, b))

links = pd.read_parquet(R.OUT / "wta_api_links_2019_2020_2021_2022_2023_2024_2025_2026.parquet")
links["key"] = links["_source_file"] + "#" + links["_row"].astype(str)
links = links.set_index("key")


def box_games(bme, bop):
    holds = bme["sv_gms"] - (bme["bp_faced"] - bme["bp_saved"])
    brk = bop["bp_faced"] - bop["bp_saved"]
    return holds + brk


def pts_won(bme, bop):
    return (bme["first_won"] + bme["second_won"]) + (bop["svpt"] - bop["first_won"] - bop["second_won"])


rows = []
for mid in cand["match_id"]:
    mr = m.loc[mid]
    pr = p[p["match_id"].eq(mid)]
    W = pr[pr["won"]].iloc[0]
    L = pr[~pr["won"]].iloc[0]
    bW = {b: W[b] for b in R.BOX}
    bL = {b: L[b] for b in R.BOX}
    gw, gl, tw, tl, ntb, ret = R.games_of(mr["score"])
    if mr["score_flag"] == "read_reversed":
        gw, gl, tw, tl = gl, gw, tl, tw
    retired = mr["status"] != "completed"

    def fits(bw, bl):
        a_w, a_l = box_games(bw, bl), box_games(bl, bw)
        excl = (a_w == gw - tw) and (a_l == gl - tl)
        incl = (bw["sv_gms"] + bl["sv_gms"] == gw + gl) and (gw - tw <= a_w <= gw) and (gl - tl <= a_l <= gl) and ntb > 0
        loose = retired and abs(a_w - (gw - tw)) <= 1 and abs(a_l - (gl - tl)) <= 1
        return bool(excl or incl), bool(loose), (a_w, a_l)

    f_rec, l_rec, g_rec = fits(bW, bL)
    f_exc, l_exc, g_exc = fits(bL, bW)
    tid, rnd, tour = mr["tournament_id"], mr["round"], mr["tour"]
    nxt = NEXT.get(rnd)
    nxt_players = held.get((tour, tid, nxt), set()) if nxt else set()
    row = {"match_id": mid, "tour": tour, "event": mr["tournament_name"], "year": mr["year"], "round": rnd,
           "qualifying": mr["qualifying"], "level": mr["level"], "score": mr["score"], "status": mr["status"],
           "score_flag": mr["score_flag"], "winner": W["player_name"], "winner_id": W["player_id"],
           "loser": L["player_name"], "loser_id": L["player_id"], "source_file": mr["source_file"],
           "source_row": mr["source_row"], "tml_link": mr["tml_link"], "games_w": gw, "games_l": gl, "tb_sets": ntb,
           "box_games_rec": f"{int(g_rec[0])}-{int(g_rec[1])}" if pd.notna(g_rec[0]) and pd.notna(g_rec[1]) else "",
           "box_games_exc": f"{int(g_exc[0])}-{int(g_exc[1])}" if pd.notna(g_exc[0]) and pd.notna(g_exc[1]) else "", "fit_recorded": f_rec, "fit_exchanged": f_exc,
           "loose_rec_ret": l_rec, "loose_exc_ret": l_exc,
           "pts_w_rec": pts_won(bW, bL), "pts_l_rec": pts_won(bL, bW),
           "svg_diff": abs(bW["sv_gms"] - bL["sv_gms"]) if pd.notna(bW["sv_gms"]) and pd.notna(bL["sv_gms"]) else np.nan,
           "next_round": nxt or "", "next_round_held": bool(nxt_players),
           "winner_next": W["player_id"] in nxt_players, "loser_next": L["player_id"] in nxt_players}
    row["winner_fewer_pts_rec"] = row["pts_w_rec"] < row["pts_l_rec"]
    # raw row check
    key = f"{mr['source_file']}#{mr['source_row']}"
    row["api"] = "no_link"
    if key in links.index:
        lk = links.loc[key]
        raw_w_id = f"wta:{lk['winner_id']}"
        api = {}
        for side in ("w", "l"):
            pid = f"wta:{lk[f'{side}_id' if False else ('winner_id' if side == 'w' else 'loser_id')]}"
            api[pid] = {b: lk[f"a_{side}_{b}"] for b in R.BOX}
        if W["player_id"] in api and L["player_id"] in api:
            aW, aL = api[W["player_id"]], api[L["player_id"]]
            eq_rec = all(bW[b] == aW[b] for b in R.BOX) and all(bL[b] == aL[b] for b in R.BOX)
            eq_exc = all(bW[b] == aL[b] for b in R.BOX) and all(bL[b] == aW[b] for b in R.BOX)
            n_rec = sum(bW[b] == aW[b] for b in R.BOX) + sum(bL[b] == aL[b] for b in R.BOX)
            n_exc = sum(bW[b] == aL[b] for b in R.BOX) + sum(bL[b] == aW[b] for b in R.BOX)
            row["api"] = "equal_recorded" if eq_rec else ("equal_exchanged" if eq_exc else f"other(rec {n_rec}/18, exc {n_exc}/18)")
            row["api_result"] = lk["api_result"]
            row["api_winner_agrees"] = bool(lk["api_winner_is_sack_winner"]) if raw_w_id == W["player_id"] else (not bool(lk["api_winner_is_sack_winner"]))
        else:
            row["api"] = "link_ids_differ"
    rows.append(row)

d = pd.DataFrame(rows)
d.to_csv(R.OUT / "f2_internal.csv", index=False)
print(d[["match_id", "score", "winner", "loser", "fit_recorded", "fit_exchanged", "box_games_rec", "pts_w_rec", "pts_l_rec",
         "winner_next", "loser_next", "next_round_held", "api"]].to_string())
print(d["api"].value_counts().to_string())
print("fit_exchanged:", int(d["fit_exchanged"].sum()), " fit_recorded:", int(d["fit_recorded"].sum()),
      " winner fewer points as recorded:", int(d["winner_fewer_pts_rec"].sum()),
      " loser plays next round:", int(d["loser_next"].sum()), " winner plays next round:", int(d["winner_next"].sum()))
