"""R2 (attack) scratch: G1 clash test, compact. Read-only; prints only.

For each of the 32 players of 2024-2847: the last round reached there; their other Stage 0 matches whose
event is dated 2024-02-19..2024-03-10 (the proposed week and its neighbours) and 2024-01-14..2024-01-28
(Stage 0's current week, under either convention).
"""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 600)
pd.set_option("display.max_colwidth", 32)

d = pd.read_csv("data/studies/p6_data_issues/stage0_review/R2_attack/g1_players_jan_mar_2024.csv",
                encoding="utf-8", encoding_errors="replace")
m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "player_name"])
names = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]
g1 = m[m["tournament_id"].eq("2024-2847")]
order = {"R32": 1, "R16": 2, "QF": 3, "SF": 4, "F": 5}
reach = {}
for _, r in g1.iterrows():
    for p, won in ((r.player_a_id, r.a_won), (r.player_b_id, not r.a_won)):
        n = names[p]
        lab = r["round"] + ("W" if won else "L")
        if n not in reach or order[r["round"]] > order[reach[n][:-1] if reach[n][-1] in "WL" else reach[n]]:
            reach[n] = lab
d["s0_date"] = pd.to_datetime(d["s0_date"])
feb = d[(d["s0_date"] >= "2024-02-19") & (d["s0_date"] <= "2024-03-10")]
jan = d[(d["s0_date"] >= "2024-01-14") & (d["s0_date"] <= "2024-01-28")]
for p in sorted(reach):
    print(f"\n### {p}: at 2024-2847 last {reach[p]}")
    f = feb[feb["player"].eq(p)]
    j = jan[jan["player"].eq(p)]
    for lab, x in (("Feb19-Mar10", f), ("Jan14-28", j)):
        for _, r in x.iterrows():
            print(f"   [{lab}] {r.s0_date.date()} {r.event:<28} {r['round']:<5} {r.res} v {r.opp:<26} {r.score:<18} {r.src}")
