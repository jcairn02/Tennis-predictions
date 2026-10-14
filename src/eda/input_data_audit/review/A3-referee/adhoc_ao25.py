import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, pandas as pd
import x50_f5 as F
pd.set_option("display.width", 250)
P = F.pbp()
m = rc.rd(rc.PTS/"infosys_slams"/"matches.parquet")
m = m[(m.slam=="AO")&(m.year.astype(str)=="2025")]
for a, b in [("Garin","Djere"), ("Blinkova","Saville")]:
    x = m[(m.p1_last_name.astype(str).str.contains(a, case=False)&m.p2_last_name.astype(str).str.contains(b, case=False))|(m.p1_last_name.astype(str).str.contains(b, case=False)&m.p2_last_name.astype(str).str.contains(a, case=False))]
    print(x[["match_id","p1_first_name","p1_last_name","p2_first_name","p2_last_name","match_winner","round_from_code"]].to_string())
    for _, r in x.iterrows():
        print(P[(P.slam=="AO")&(P.year==2025)&(P.match_id==r.match_id)].to_string())
o = pd.read_csv(rc.OUT/"f2_referee_rows.csv")
print(o[o.match_id.isin(["atp|2025-580|Q2|atp:106426|atp:111513","wta|2025-580|R128|wta:201611|wta:215020"])][["match_id","ref","ref_name","about"]+[f"rec_{b}" for b in rc.BOX]].drop_duplicates(["match_id","about"]).to_string())
