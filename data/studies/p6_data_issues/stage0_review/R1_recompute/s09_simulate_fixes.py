"""R1 recompute, step 9: simulate both proposed fixes with the clock's own functions (anchor_day, rule_label,
rule_windows from src/eda/match_timing/timing.py; imported read-only, run with python -B so no bytecode is written),
compare my reader set with the study's, and look for the G2 walkovers in TennisLive / SofaScore. Read-only."""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from src.eda.match_timing import timing as T  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 300)
OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"
EPOCH = pd.Timestamp("1970-01-01")
d2s = lambda x: "NaN" if not np.isfinite(x) else (EPOCH + pd.Timedelta(days=int(x))).strftime("%Y-%m-%d")

s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
tm = pd.read_parquet("data/studies/match_timing/timing.parquet")

# ---------------- G2: the clock's rule window before and after the proposed date
g2ids = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
g2 = s0[s0["match_id"].isin(g2ids)].copy()
for label, date in [("as is", "2021-02-08"), ("proposed fix", "2021-01-10")]:
    m = g2.copy()
    m["tournament_date"] = pd.Timestamp(date)
    anchor = T.anchor_day(m)
    lab = T.rule_label(m)
    lo, hi, named = T.rule_windows(m)
    for i in range(len(m)):
        print(f"G2 {label:13s} {m['match_id'].iloc[i]}: date {date} anchor {d2s(anchor[i])} label '{lab.iloc[i]}' "
              f"named {named[i]} offsets [{lo[i]}, {hi[i]}] -> window {d2s(anchor[i] + lo[i])} .. {d2s(anchor[i] + hi[i])}; "
              f"counts from {d2s(anchor[i] + hi[i] + 1)}")
# check the as-is simulation reproduces the stored clock
t2 = tm[tm["match_id"].isin(g2ids)][["match_id", "es", "lf", "window_basis"]]
print("stored clock:", [(r.match_id, d2s(r.es), d2s(r.lf), r.window_basis) for r in t2.itertuples()])
# Sackmann's twin rows (same players, same round) and their windows
twins = s0[(s0["tournament_id"] == "2021-581") & (s0["round"] == "Q2")
           & s0["match_id"].str.contains("atp:106045\\|atp:208013|atp:106408\\|atp:202103", regex=True)]
tw = twins.merge(tm[["match_id", "es", "lf", "window_basis"]], on="match_id")
print("\nSackmann twins in Stage 0:")
print(tw[["match_id", "tournament_name", "tournament_date", "round", "score", "status", "player_a_id", "player_b_id", "a_won",
          "source", "tml_link"]].to_string())
print([(r.match_id, d2s(r.es), d2s(r.lf), r.window_basis) for r in tw.itertuples()])
print("\nTML rows, same fields:")
print(g2[["match_id", "tournament_name", "tournament_date", "round", "score", "status", "player_a_id", "player_b_id", "a_won",
          "source", "tml_link"]].to_string())
# who won: compare (winner id) between the twin pairs
def winner(r):
    return r["player_a_id"] if r["a_won"] else r["player_b_id"]
for mid in g2ids:
    a = g2[g2["match_id"] == mid].iloc[0]
    b = tw[tw["match_id"] == mid.replace("2021-580", "2021-581")].iloc[0]
    print(f"{mid}: TML winner {winner(a)}; Sackmann twin {b['match_id']} winner {winner(b)}; same pair "
          f"{set([a['player_a_id'], a['player_b_id']]) == set([b['player_a_id'], b['player_b_id']])}")

# ---------------- G1: the windows after the proposed date (offsets are date-independent; check with anchor_day)
g1 = pd.read_csv(OUT + "g1_clock_windows.csv")
t1 = tm[tm["tournament_id"] == "2024-2847"].copy()
m_old = s0[s0["tournament_id"] == "2024-2847"].copy()
m_new = m_old.copy()
m_new["tournament_date"] = pd.Timestamp("2024-02-26")
a_old, a_new = T.anchor_day(m_old), T.anchor_day(m_new)
assert len(set(a_old)) == 1 and len(set(a_new)) == 1
shift = a_new[0] - a_old[0]
print(f"\nG1 anchor as is {d2s(a_old[0])}, after the fix {d2s(a_new[0])}: shift {shift:+.0f} days")
lab_old, lab_new = T.rule_label(m_old), T.rule_label(m_new)
r_old, r_new = T.rule_windows(m_old), T.rule_windows(m_new)
print("rule label unchanged:", (lab_old.values == lab_new.values).all(), set(lab_old),
      "| rule offsets unchanged:", np.array_equal(r_old[0], r_new[0], equal_nan=True) and np.array_equal(r_old[1], r_new[1], equal_nan=True))
# alternative value 2024-02-25 (Sunday, qualifying's first day) gives the same anchor?
m_alt = m_old.copy(); m_alt["tournament_date"] = pd.Timestamp("2024-02-25")
print("anchor for 2024-02-25:", d2s(T.anchor_day(m_alt)[0]))
t1 = t1.merge(g1[["match_id", "play_day"]], on="match_id")
t1["play"] = (pd.to_datetime(t1["play_day"]) - EPOCH).dt.days
t1["es_new"], t1["lf_new"] = t1["es"] + shift, t1["lf"] + shift
t1["holds_new"] = (t1["es_new"] <= t1["play"]) & (t1["play"] <= t1["lf_new"])
t1["holds_old"] = (t1["es"] <= t1["play"]) & (t1["play"] <= t1["lf"])
print(t1.groupby("round").agg(n=("match_id", "size"), es_new=("es_new", lambda x: d2s(x.min())),
                              lf_new=("lf_new", lambda x: d2s(x.max())), play_min=("play_day", "min"),
                              play_max=("play_day", "max"), holds_old=("holds_old", "sum"), holds_new=("holds_new", "sum")).to_string())
print("windows holding the play day: as is", int(t1["holds_old"].sum()), "| after the fix", int(t1["holds_new"].sum()), "of", len(t1))

# ---------------- my reader set vs the study's
mine = pd.read_csv(OUT + "g1_leak_readers_R1.csv")
st = pd.read_csv("data/studies/p6_data_issues/tml_misdates/clock_leak_readers.csv")
A = set(zip(mine["g1_match"], mine["match_id"], mine["player"]))
B = set(zip(st["leak_match_id"], st["reader_match_id"], st["player_id"]))
print(f"\nreader rows: mine {len(A)}, study {len(B)}, equal sets: {A == B}; only mine {len(A - B)}, only study {len(B - A)}")
print("distinct readers: mine", mine["match_id"].nunique(), "study", st["reader_match_id"].nunique(),
      "| equal:", set(mine["match_id"]) == set(st["reader_match_id"]))
print("study's leak_first_play_day values:", st["leak_first_play_day"].value_counts().to_dict())

# ---------------- G2 walkovers in TennisLive / SofaScore (local)
tl = pd.read_parquet("data/dump/points/tennislive/listed.parquet",
                     columns=["event_name", "draw", "discipline", "round", "start_utc", "player1_name", "player2_name",
                              "score", "state", "end_reason", "winner_side"])
x = tl[tl["start_utc"].astype(str).str.startswith(("2021-01", "2021-02")) & tl["event_name"].astype(str).str.contains("Australian|Doha|Melbourne", case=False)
       & (tl["discipline"] == "singles")]
print("\nTennisLive events Jan-Feb 2021 matching Australian/Doha/Melbourne:")
print(x.groupby(["event_name", "draw"]).agg(n=("start_utc", "size"), first=("start_utc", "min"), last=("start_utc", "max")).to_string())
for a, b in [("Sweeny", "Kudla"), ("Vilella", "Cerundolo")]:
    h = x[(x["player1_name"].str.contains(a) & x["player2_name"].str.contains(b)) | (x["player1_name"].str.contains(b) & x["player2_name"].str.contains(a))]
    print(f"TennisLive {a}-{b}:", h.to_dict("records"))
for f in ["data/dump/points/sofascore_editions/events.parquet", "data/dump/points/sofascore/events.parquet"]:
    ss = pd.read_parquet(f)
    y = ss[ss["start_utc"].astype(str).str.startswith(("2021-01", "2021-02")) & (ss["season_name"].astype(str).str.contains("Australian|Doha", case=False)
           | ss["tournament_name"].astype(str).str.contains("Australian|Doha", case=False))]
    print(f"\n{f}: Jan-Feb 2021 Australian/Doha rows:", len(y))
    if len(y):
        print(y.groupby(["tournament_name", "season_name"]).agg(n=("event_id", "size"), first=("start_utc", "min"), last=("start_utc", "max")).to_string())
        for a, b in [("Sweeny", "Kudla"), ("Vilella", "Cerundolo")]:
            h = y[(y["home_name"].astype(str).str.contains(a) & y["away_name"].astype(str).str.contains(b)) | (y["home_name"].astype(str).str.contains(b) & y["away_name"].astype(str).str.contains(a))]
            print(f"  {a}-{b}:", h[["tournament_name", "round_name", "start_utc", "home_name", "away_name", "status_type", "status_description", "winner_code"]].to_dict("records"))
