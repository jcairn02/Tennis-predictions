import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, refs, pandas as pd, numpy as np
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
m, p = rc.stage0()
mm = m[(m.tournament_name.isin(["Roland Garros","Australian Open"]) & m.year.between(2022, 2025)) | (m.tournament_name.str.contains("Olympics") & m.year.eq(2024))]
W = rc.wide(mm, p[p.match_id.isin(mm.match_id)])
rows = []
for side, oth in (("w","l"),("l","w")):
    d = W[["match_id","tour","year","qualifying","tournament_name","has_box","source"]].copy()
    d["name"], d["oname"] = W[f"{side}_player_name"], W[f"{side if False else oth}_player_name"]
    for b in rc.BOX: d[b] = W[f"{side}_{b}"]
    rows.append(d)
S = pd.concat(rows, ignore_index=True)
S["pk"], S["ok"] = rc.keys(S["name"]), rc.keys(S["oname"])
for nm, R in (("sofascore", refs.ref_sofascore()), ("mcp", refs.ref_mcp())):
    x = S[S.has_box].merge(R[["year","pk","ok","event"] + rc.BOX], on=["year","pk","ok"], suffixes=("","_r"))
    if nm == "mcp":
        x = x[x.event.astype(str).str.contains("Roland|Australian|Olymp", case=False)]
    else:
        x = x[x.event.astype(str).str.contains("French|Australian|Olymp", case=False)]
    x = x.drop_duplicates(["match_id","name"])
    x["all8"] = np.all([x[b].eq(x[f"{b}_r"]).to_numpy() for b in rc.BOX if b != "sv_gms"], axis=0)
    x["fi_eq"] = x.first_in.eq(x.first_in_r)
    print(nm, x.groupby(["tournament_name","year","qualifying","tour"]).agg(rows=("all8","size"), all8=("all8","mean"), first_in_eq=("fi_eq","mean")).round(3).to_string())
