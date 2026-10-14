import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, pandas as pd, numpy as np
import x50_f5 as F
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
K = F.keystats(); P = F.pbp()
KP = K.merge(P, on=["slam","year","match_id","pno"], how="left")
k = KP[(KP.year==2025)]
# per match: keystats sv_gms both players vs pbp svg and vs the match's games
pt = rc.rd(rc.PTS/"infosys_slams"/"points.parquet")
pt = pt[(pt.slam=="RG")&(pt.year.astype(str)=="2025")]
for c in ["set","game","server"]: pt[c] = pd.to_numeric(pt[c], errors="coerce")
# games per match from pbp = distinct (set, game)
gm = pt.groupby("match_id")[["set","game"]].apply(lambda z: z.drop_duplicates().shape[0]).rename("pbp_games")
# tiebreak games: a set's game 13
tb = pt[pt.game.eq(13)].groupby("match_id")["set"].nunique().rename("tb_games")
x = k.pivot_table(index="match_id", columns="pno", values=["sv_gms","p_sv_gms","bp_faced","bp_saved"], aggfunc="first")
x.columns = [f"{a}_{b}" for a, b in x.columns]
x = x.join(gm).join(tb).fillna({"tb_games": 0})
x["ks_total"] = x["sv_gms_1"] + x["sv_gms_2"]
x["pbp_total"] = x["p_sv_gms_1"] + x["p_sv_gms_2"]
x["ks_minus_games"] = x["ks_total"] - x["pbp_games"]
x["ks_minus_games_excl_tb"] = x["ks_total"] - (x["pbp_games"] - x["tb_games"])
print(x["ks_minus_games"].value_counts().sort_index().to_dict())
print(x["ks_minus_games_excl_tb"].value_counts().sort_index().to_dict())
print(pd.crosstab(x["tb_games"], x["ks_minus_games"]))
print(x[x.ks_minus_games.abs()>1].head(10).to_string())
