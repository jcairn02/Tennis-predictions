import sys, re
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, pandas as pd
o = pd.read_csv(rc.OUT/"f2_matches_raw.csv")
a = rc.wta_api_totals()
def surname(n):
    ws = rc.name_key(n).split(); return max(ws, key=len) if ws else ""
res = []
for _, r in o[o.referees.fillna("").str.contains("wta_api")].iterrows():
    m = re.match(r"^\d{4}-(\d+)$", r.match_id.split("|")[1])
    x = a[(a.tournament_id == m.group(1)) & (a.year == str(r.year))]
    ws, ls = surname(r.winner), surname(r.loser)
    hit = x[x.pk.str.contains(ws) & x.ok.str.contains(ls)]
    rs = hit.result.dropna().unique().tolist()
    res.append((r.tournament, r["round"], r.winner, r.loser, rs[:1]))
for t in res: print(t)
