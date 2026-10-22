"""Independent re-checks of subagent B's clock-leak readers and the map's doubles (read-only)."""
import pandas as pd, numpy as np
ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/"
EP = pd.Timestamp("1970-01-01")
s0 = pd.read_parquet(ROOT + "data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_id", "player_a_id", "player_b_id", "evaluation", "tournament_date"])
tm = pd.read_parquet(ROOT + "data/studies/match_timing/timing.parquet", columns=["match_id", "es", "lf"])
s = s0.merge(tm, on="match_id")
s["es_d"] = EP + pd.to_timedelta(s["es"], unit="D"); s["lf_d"] = EP + pd.to_timedelta(s["lf"], unit="D")
leak = s[s["tournament_id"].astype(str).eq("2024-2847")].copy()
# true play days: TennisLive's listing day, else the edition's span (26 Feb - 3 Mar 2024)
first_play = pd.Timestamp("2024-02-26")
long = pd.concat([leak[["match_id", "player_a_id", "lf_d"]].rename(columns={"player_a_id": "pid"}),
                  leak[["match_id", "player_b_id", "lf_d"]].rename(columns={"player_b_id": "pid"})])
readers = []
for _, r in long.iterrows():
    other = s[((s["player_a_id"] == r["pid"]) | (s["player_b_id"] == r["pid"])) & (s["match_id"] != r["match_id"])]
    # a reader sees the result from lf + 1 on, before the earliest day the Tenerife match was played
    hit = other[(other["es_d"] >= r["lf_d"] + pd.Timedelta(days=1)) & (other["es_d"] < first_play)]
    for _, h in hit.iterrows():
        readers.append((r["match_id"], h["match_id"], r["pid"], bool(h["evaluation"])))
rd = pd.DataFrame(readers, columns=["leak", "reader", "pid", "evaluation"])
u = rd.drop_duplicates("reader")
print("reader rows:", len(rd), " distinct readers:", len(u), " of them evaluation:", int(u["evaluation"].sum()))
print("readers' es range:", s.set_index("match_id").loc[u["reader"], "es_d"].min().date(), "to", s.set_index("match_id").loc[u["reader"], "es_d"].max().date())
b = pd.read_csv(ROOT + "data/studies/p6_data_issues/tml_misdates/clock_leak_readers.csv")
print("B's:", len(b), b["reader_match_id"].nunique(), int(b.drop_duplicates("reader_match_id")["reader_evaluation"].sum()),
      " same reader set:", set(b["reader_match_id"]) == set(u["reader"]))
# the map's doubles
mp = pd.read_parquet(ROOT + "data/studies/data_map/matches.parquet", columns=["uid", "tour", "level", "d", "name1", "name2", "creator", "tname"])
d = pd.read_csv(ROOT + "data/studies/p6_data_issues/tml_misdates/map_doubles.csv")
a = d.merge(mp.add_prefix("t_"), left_on="map_tml_uid", right_on="t_uid", how="left").merge(mp.add_prefix("o_"), left_on="map_other_uid", right_on="o_uid", how="left")
def sur(n): 
    w = str(n).lower().replace("-", " ").split(); return w[-1] if w else ""
same_pair = [{sur(x1), sur(x2)} & {sur(y1), sur(y2)} != set() for x1, x2, y1, y2 in zip(a["t_name1"], a["t_name2"], a["o_name1"], a["o_name2"])]
print("map doubles:", len(d), " both uids on the map:", int(a["t_uid"].notna().sum()), int(a["o_uid"].notna().sum()),
      " TML copy created by tml:", int(a["t_creator"].eq("tml").sum()), " other by sackmann/api:", a["o_creator"].value_counts().to_dict(),
      " a shared surname:", int(sum(same_pair)), " days apart >7:", int(((pd.to_datetime(a["t_d"]) - pd.to_datetime(a["o_d"])).abs().dt.days > 7).sum()))
print(d.groupby(d["map_tml_year"]).size().to_dict())
