"""F2 step 4: per-match verdict for the 88 candidates (box_swapped_oct07.csv).

Evidence, in order of strength:
  1. WTA API (f2_internal.py 'api'): all 18 counts equal once exchanged -> confirm; equal as recorded -> reject.
  2. Official Slam / ATP records read here: US Open 2022 statistics (usopen/statistics.parquet), Wimbledon 2019 statistics
     (wimbledon/statistics.parquet), ATP key statistics 2025 (sirgenkii_infotennis), AO 2022 ball tracking
     (slam_ball_tracking/points/AO_2022.parquet), and f2_external.csv (Sackmann's Slam point-by-point, infosys AO 2025).
  3. Internal only (no independent record): confirm only when the exchange fits the score (exactly, or within one game
     where the source's own count is one game short), the games margin is >= 4, the recorded winner's box gives him
     >= 10 fewer points than the loser's, and the recorded winner plays the next round (so the winner is right).
     Calibration (f2_calibration.csv): among 22,576 boxes the WTA API shows to be genuine, none fits only when exchanged;
     among 72 verified exchanges, 48 have margin >= 4 and deficit >= 10. Closer matches are not decisive: at the Slams
     5 of 5 such 'fits' checked against an independent record were service-game attribution, not an exchange.
Writes f2_verdicts.csv (all 88) and f2_scope.csv (confirmed matches, both player rows).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

d = pd.read_csv(R.OUT / "f2_internal.csv")
ext = pd.read_csv(R.OUT / "f2_external.csv")
m, p = R.stage0()


def box(mid):
    pr = p[p["match_id"].eq(mid)]
    return pr[pr["won"]].iloc[0], pr[~pr["won"]].iloc[0]


def cmp9(stage, official):
    return sum(stage[b] == official[b] for b in official)


checks = {}

# ---- US Open 2022 men's qualifying R1, Seppi d. Horansky (usopen match 11131; team_1 = Seppi, winner 1)
us = pd.read_parquet(R.DUMP / "points" / "usopen" / "statistics.parquet")
s = us[(us["year"].astype(str) == "2022") & (us["match_id"].astype(str) == "11131") & (us["period"] == "match")]
s = s.drop_duplicates(["team", "key"]).pivot(index="key", columns="team", values="value")


def us_counts(t, o):
    v = lambda k, tt=t: float(s.loc[k, tt])  # noqa: E731
    return {"ace": v("t_ace"), "df": v("df"), "svpt": v("t_f_srv"), "first_in": v("t_f_srv_in"),
            "first_won": v("t_f_srv_w"), "second_won": v("t_s_srv_w"), "sv_gms": v("t_gms"),
            "bp_faced": float(s.loc["t_bp", o]), "bp_saved": float(s.loc["t_bp", o]) - float(s.loc["t_bp_w", o])}


mid = "atp|2022-560|Q1|atp:104312|atp:106110"
W, L = box(mid)
seppi, horansky = us_counts("team_1", "team_2"), us_counts("team_2", "team_1")
checks[mid] = ("US Open 2022 official statistics (match 11131)",
               cmp9(W, seppi) + cmp9(L, horansky), cmp9(L, seppi) + cmp9(W, horansky), 18)

# ---- Wimbledon 2019 R128, Wang d. Martincova (wimbledon match 2126; team_1 = Wang)
ws = pd.read_parquet(R.DUMP / "points" / "wimbledon" / "statistics.parquet")
s = ws[(ws["year"].astype(str) == "2019") & (ws["match_id"].astype(str) == "2126") & (ws["period"] == "match")]
s = s.drop_duplicates(["team", "key"]).pivot(index="key", columns="team", values="value")
mid = "wta|2019-540|R128|wta:206124|wta:206374"
W, L = box(mid)
wang, mart = us_counts("team_1", "team_2"), us_counts("team_2", "team_1")
checks[mid] = ("Wimbledon 2019 official statistics (match 2126); Wang's box is one point and one service game short",
               cmp9(W, wang) + cmp9(L, mart), cmp9(L, wang) + cmp9(W, mart), 18)

# ---- Miami 2025 R64, Bergs d. Rublev (ATP key statistics, tournament 403, ms047; Bergs = BU13; Rublev's row is -999)
ks = pd.read_parquet(R.DUMP / "points" / "sirgenkii_infotennis" / "atp_key_stats.parquet")
k = ks[(ks["tournament_id"].astype(str) == "403") & (ks["match_id"].astype(str) == "ms047") & (ks["set_n"].astype(str) == "0")
       & (ks["player_id"].astype(str) == "BU13")].iloc[0]
f = lambda c: float(k[c])  # noqa: E731
svpt_b = round(f("service_games_played") and 0) or None
# serve points from the shares: first-serve share 0.66176 = 45/68; points won on serve 0.69118 = 47/68
n_b = int(round(47 / f("service_points_won"))) if abs(47 / f("service_points_won") - round(47 / f("service_points_won"))) < 1e-3 else None
bergs = {"ace": f("aces"), "df": f("double_faults"), "svpt": 68.0, "first_in": round(f("serve1") * 68),
         "first_won": round(f("serve1_pts_won") * round(f("serve1") * 68)),
         "second_won": round(f("serve2_pts_won") * (68 - round(f("serve1") * 68))),
         "sv_gms": f("service_games_played"), "bp_faced": f("break_points_faced"),
         "bp_saved": round(f("break_points_saved") * f("break_points_faced"))}
# Rublev from Bergs's return side: return points won 0.43243 = 32/74; break points converted 0.375 = 3/8
rublev = {"svpt": 74.0, "bp_faced": 8.0, "bp_saved": 5.0}
mid = "atp|2025-403|R64|atp:126094|atp:200267"
W, L = box(mid)   # W = Bergs
rec = cmp9(W, bergs) + cmp9(L, rublev)
exc = cmp9(L, bergs) + cmp9(W, rublev)
assert abs(f("serve1") - 45 / 68) < 1e-4 and abs(f("return_points_won") - 32 / 74) < 1e-4
checks[mid] = ("ATP key statistics 2025 (Miami ms047): Bergs 9 counts, Rublev 3 derived", rec, exc, 12)

# ---- AO 2022 R128, Paire d. Monteiro (ball tracking 2022_MS146; rows are serves, faults dropped)
bt = pd.read_parquet(R.DUMP / "points" / "slam_ball_tracking" / "points" / "AO_2022.parquet")
x = bt[bt["match_id"].eq("2022_MS146")].drop_duplicates("point_ID")
x = x[x["point_end_type"] != "Faulty Serve"]


def bt_counts(pid):
    s_ = x[x["server_id"].astype(str) == pid]
    fw = int(((s_["serve_num"].astype(str) == "1") & (s_["point_winner_id"].astype(str) == pid)).sum())
    return {"ace": float((s_["point_end_type"] == "Ace").sum()), "df": float((s_["point_end_type"] == "DoubleFault").sum()),
            "svpt": float(len(s_)), "first_in": float((s_["serve_num"].astype(str) == "1").sum()), "first_won": float(fw),
            "second_won": float((s_["point_winner_id"].astype(str) == pid).sum() - fw),
            "sv_gms": float(s_.groupby(["set_num", "game_num"]).ngroups)}


mid = "atp|2022-580|R128|atp:105332|atp:106329"
W, L = box(mid)   # W = Paire
paire, monteiro = bt_counts("ATPPD31"), bt_counts("ATPMJ08")
checks[mid] = ("AO 2022 ball tracking (2022_MS146): point counts as recorded; only service games differ",
               cmp9(W, paire) + cmp9(L, monteiro), cmp9(L, paire) + cmp9(W, monteiro), 14)

# ---- external (f2_external.csv)
for r in ext[ext["source"].ne("none")].itertuples():
    if r.match_id not in checks:
        checks[r.match_id] = (r.source, r.match_recorded, r.match_exchanged, r.n_compared)

rows = []
for r in d.to_dict("records"):
    mid = r["match_id"]
    margin = abs(r["games_w"] - r["games_l"])
    deficit = r["pts_l_rec"] - r["pts_w_rec"]
    bg = r["box_games_rec"]
    verdict, reason = "reject", ""
    if r["api"] == "equal_exchanged":
        verdict = "confirm"
        reason = "WTA API: all 18 counts equal once the boxes are exchanged; API winner = recorded winner"
    elif r["api"] == "equal_recorded":
        reason = "WTA API: all 18 counts equal AS RECORDED: not exchanged"
    elif mid in checks:
        src, n_rec, n_exc, n = checks[mid]
        if n_exc >= n - 4 and n_rec <= n // 3:
            verdict = "confirm"
            reason = f"{src}: {n_exc}/{n} counts match exchanged, {n_rec}/{n} as recorded"
        else:
            reason = f"{src}: {n_rec}/{n} counts match as recorded, {n_exc}/{n} exchanged: not an exchange"
    else:
        strong = (margin >= 4 and deficit >= 10 and r["winner_next"] and not r["loser_next"]
                  and (r["fit_exchanged"] or abs(int(bg.split("-")[1]) - r["games_w"]) + abs(int(bg.split("-")[0]) - r["games_l"]) <= 1)
                  and r["score_flag"] != "read_reversed")
        if strong:
            verdict = "confirm"
            reason = (f"internal: exchanged box gives the score's games ({r['games_w']}-{r['games_l']}; recorded box "
                      f"{bg} for winner-loser); recorded winner wins {deficit:.0f} fewer points as recorded; recorded winner plays the "
                      f"next round; no independent record")
        elif r["score_flag"] == "read_reversed":
            reason = ("score written from the recorded winner's losing side ('1-6 2-6') and the box agrees with it: "
                      "the winner label, not the box, is the likely error (final: no next round to check)")
        else:
            reason = (f"internal only and not decisive: games margin {margin}, point deficit {deficit:.0f}"
                      + ("" if r["fit_exchanged"] else ", exchange does not fit the score exactly")
                      + "; a one-game service-game attribution error gives the same fit (5 of 5 Slam cases with a "
                        "record were not exchanges)")
    rows.append({"match_id": mid, "source_file": r["source_file"], "source_row": r["source_row"], "event": r["event"],
                 "year": r["year"], "round": r["round"], "score": r["score"], "recorded_winner": r["winner"],
                 "recorded_loser": r["loser"], "games_w": r["games_w"], "games_l": r["games_l"],
                 "box_games_recorded": bg, "pts_w_recorded": r["pts_w_rec"], "pts_l_recorded": r["pts_l_rec"],
                 "winner_plays_next_round": r["winner_next"], "next_round_held": r["next_round_held"],
                 "wta_api": r["api"], "verdict": verdict, "reason": reason})
v = pd.DataFrame(rows)
v.to_csv(R.OUT / "f2_verdicts.csv", index=False)
print(v["verdict"].value_counts().to_dict())
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 140)
print(v[v["wta_api"].ne("equal_exchanged")][["match_id", "verdict", "reason"]].to_string())

# scope: both player rows of each confirmed match
conf = v[v["verdict"].eq("confirm")]
sc = p[p["match_id"].isin(conf["match_id"])][["match_id", "player_id", "player_name", "won"] + R.BOX].copy()
sc = sc.merge(conf[["match_id", "source_file", "source_row"]], on="match_id")
sc = sc.rename(columns={"source_file": "_source_file", "source_row": "_row"})
sc.to_csv(R.OUT / "f2_scope.csv", index=False)
print("confirmed matches:", conf["match_id"].nunique(), " player rows:", len(sc))
