import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, pandas as pd, numpy as np
m, p = rc.stage0()
mm = m[m.has_box & m.status.eq("completed") & m.year.between(2010, 2019) & m.tour.eq("wta") & m.level.isin(["GS","T1000","T500","T250"])]
W = rc.wide(mm, p[p.match_id.isin(mm.match_id)])
sp = rc.score_parts(W["score"])
g = sp.games_w + sp.games_l - sp.std_tb
lg = sp.games_l
ppg = (W.w_svpt + W.l_svpt) / g
d = pd.DataFrame({"g": g, "lg": lg, "ppg": ppg, "sets": sp.sets_w + sp.sets_l})
def q(cond, x, lo=True):
    s = d[cond].ppg
    return len(s), round(float((s <= x).mean() if lo else (s >= x).mean()), 5)
print("RG 2010 Peer-MS 3-6 6-0 6-1 (22 games, loser 7): ppg<=4.77", q((d.g.between(21,23)) & (d.lg.between(6,8)) & (d.sets==3), 4.77))
print("   IW 6-2 6-3 (17 games, loser 5): P(ppg>=6.18) ", q((d.g.between(16,18)) & (d.lg.between(4,6)) & (d.sets==2), 6.18, lo=False))
print("Tokyo 2011 Q2 4-6 6-2 6-1 (25 games, loser 9): ppg<=4.56", q((d.g.between(24,26)) & (d.lg.between(8,10)) & (d.sets==3), 4.56))
print("   USO Q3 6-4 6-3 (19 games): ppg>=6.0", q((d.g.between(18,20)) & (d.lg.between(6,8)) & (d.sets==2), 6.0, lo=False))
print("Florianopolis 6-3 6-3 (18 games): ppg>=9.67", q((d.g.between(17,19)) & (d.lg.between(5,7)) & (d.sets==2), 9.67, lo=False))
print("   Istanbul 4-6 6-0 6-4 (26): ppg>=6.69", q((d.g.between(25,27)) & (d.sets==3), 6.69, lo=False), " Shenzhen 6-3 7-5 (21) ppg>=8.29", q((d.g.between(20,22)) & (d.sets==2), 8.29, lo=False))
print("all clean ppg >= 9.67:", round(float((d.ppg>=9.67).mean()),5), "<= 4.56:", round(float((d.ppg<=4.56).mean()),5), "<= 4.77:", round(float((d.ppg<=4.77).mean()),5), len(d))
