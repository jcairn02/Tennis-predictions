import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import rc, refs, pandas as pd
pd.set_option("display.width", 250)
mc = refs.ref_mcp()
x = mc[mc.pk.isin(["kvitova petra","barbora strycova"]) & mc.ok.isin(["kvitova petra","barbora strycova"])]
print(x[["date","event","round","name","ace","df","svpt","first_in","first_won","second_won","bp_saved","bp_faced"]].to_string())
r = pd.read_parquet(rc.SACK/"wta"/"wta_matches_2014.parquet")
y = r[(r.winner_name=="Petra Kvitova")&(r.loser_name=="Barbora Strycova")]
print(y[["tourney_name","round","score","w_ace","w_df","w_svpt","w_1stIn","w_1stWon","w_2ndWon","w_bpSaved","w_bpFaced","l_ace","l_df","l_svpt","l_1stIn","l_1stWon","l_2ndWon","l_bpSaved","l_bpFaced"]].to_string())
for yr, a, b in [(2013, "Alla Kudryavtseva", "Arantxa Parra Santonja")]:
    for f in [f"wta_matches_{yr}.parquet", f"wta_matches_qual_itf_{yr}.parquet"]:
        r = pd.read_parquet(rc.SACK/"wta"/f)
        y = r[(r.winner_name==a)&(r.loser_name==b)]
        print(f, y[["tourney_name","round","score","w_ace","w_df","w_svpt","w_1stIn","w_1stWon","w_2ndWon","w_SvGms","w_bpSaved","w_bpFaced","l_ace","l_df","l_svpt","l_1stIn","l_1stWon","l_2ndWon","l_bpSaved","l_bpFaced"]].to_string())
