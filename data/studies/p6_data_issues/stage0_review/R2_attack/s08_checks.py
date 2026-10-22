"""R2 (attack) scratch: last checks. Read-only; prints only.

A. G1 readers: other Stage 0 matches of the 32 players whose clock start (es) falls on or after a 2847 result
   counts (lf + 1) and before that 2847 match was actually played (TennisLive's day): they read it early.
B. Stage 0's dating convention for Slam qualifying rows: tournament_date of qualifying vs main draw, by Slam-year.
C. G2 after the proposed fix: the clock rule the two rows would fall under (label 'Australian Open', 2021, Q2) and
   the window it gives from the new anchor (Mon 2021-01-11), next to Sackmann's own rows of the same draw.
"""
import numpy as np
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
R2 = "data/studies/p6_data_issues/stage0_review/R2_attack/"
m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "tour", "year", "level", "qualifying", "round", "tournament_id", "tournament_name",
                             "tournament_date", "player_a_id", "player_b_id", "source", "status"])
t = pd.read_parquet("data/studies/match_timing/timing.parquet", columns=["match_id", "es", "lf", "anchor"])
day = lambda d: (pd.Timestamp(d) - pd.Timestamp("1970-01-01")).days

# ---- A
g = m[m["tournament_id"].eq("2024-2847")].merge(t, on="match_id")
tl = pd.read_csv(R2 + "g1_vs_tennislive.csv")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet", columns=["player_id", "player_name"])
names = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]
g["w"] = None
true_day = {}
for _, r in tl.iterrows():
    true_day[(r["round"], r["s0_winner"], r["s0_loser"])] = day(r["tl_day"])
mm = m.merge(t, on="match_id")
readers = set()
pairs = 0
for _, r in g.iterrows():
    a, b = names[r.player_a_id], names[r.player_b_id]
    td = true_day.get((r["round"], a, b), true_day.get((r["round"], b, a)))
    for p in (r.player_a_id, r.player_b_id):
        q = mm[(mm["player_a_id"].eq(p) | mm["player_b_id"].eq(p)) & ~mm["tournament_id"].eq("2024-2847")]
        hit = q[(q["es"] >= r.lf + 1) & (q["es"] < td)]
        pairs += len(hit)
        readers.update(hit["match_id"])
print("A. distinct reader matches:", len(readers), " (reader, 2847 result) pairs:", pairs)

# ---- B: Slam qualifying dates vs main-draw dates (ATP, 2015-2025)
gs = m[m["level"].eq("GS") & m["tour"].eq("atp") & m["year"].between(2015, 2025)]
md = gs[~gs["qualifying"]].groupby(["year", "tournament_name"])["tournament_date"].min().rename("main_date")
qd = gs[gs["qualifying"]].groupby(["year", "tournament_id", "tournament_name", "source"])["tournament_date"].agg(["min", "max", "size"]).reset_index()
qd = qd.merge(md.reset_index(), on=["year", "tournament_name"], how="left")
qd["q_minus_main"] = (qd["min"] - qd["main_date"]).dt.days
print("\nB. ATP Slam qualifying rows: date vs the main draw's date (same name)")
print(qd.to_string())

# ---- C: the clock rule for label 'Australian Open', 2021, Q2 and the window after the fix
rules = pd.read_csv("data/studies/match_timing/schedule_rules.csv")
r = rules[rules["event_or_pattern"].eq("Australian Open") & rules["era_from"].le(2021) & rules["era_to"].ge(2021)
          & rules["round"].eq("Q2")]
print("\nC. rule rows:", r[["tour", "level", "event_or_pattern", "era_from", "era_to", "round", "earliest_day_offset",
                            "latest_day_offset"]].to_string())
MARGIN = 2
for label, date in (("now", "2021-02-08"), ("after the fix", "2021-01-10")):
    d = day(date)
    dow = (d + 3) % 7
    shift = {1: -1, 2: -2, 3: -3, 4: 3, 5: 2, 6: 1}.get(dow, 0)
    anc = d + shift
    lo = anc + int(r["earliest_day_offset"].iloc[0]) - MARGIN
    hi = anc + int(r["latest_day_offset"].iloc[0]) + MARGIN
    f = lambda x: str((pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(x))).date())
    print(f"   {label}: date {date} anchor {f(anc)} -> es {f(lo)} lf {f(hi)}")
s = m[m["tournament_id"].eq("2021-581") & m["round"].eq("Q2")].merge(t, on="match_id")
f = lambda x: str((pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(x))).date())
print("   Sackmann's own Q2 rows of the draw: es", f(s["es"].min()), "..", f(s["es"].max()), " lf", f(s["lf"].min()), "..", f(s["lf"].max()))
