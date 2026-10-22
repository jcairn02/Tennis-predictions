"""R1 recompute, step 2: read the raw Tennis My Life files at the claimed rows (read-only)."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 400)

F1 = "data/raw/public_dump/tennis_my_life/2024_challenger.csv"
with open(F1, encoding="utf-8", errors="replace") as fh:
    lines = fh.readlines()
print("lines in file (incl header):", len(lines))
print("HEADER:", lines[0].strip()[:600])
# print raw lines around 278..313 (line index = 0 is header)
for i in range(277, 314):
    print(i, lines[i].strip()[:260])

t = pd.read_csv(F1, low_memory=False)
print("\npandas rows:", len(t))
print(t.columns.tolist())
keep = [c for c in ["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor", "tourney_date",
                    "match_num", "winner_id", "winner_name", "loser_id", "loser_name", "score", "best_of", "round",
                    "minutes"] if c in t.columns]
print(t.iloc[276:314][keep].to_string())

# The whole edition as TML holds it
for col in ["tourney_id"]:
    if col in t.columns:
        sub = t[t[col].astype(str).str.contains("2847")]
        print("\nTML rows with tourney_id containing 2847:", len(sub), "index range", sub.index.min(), sub.index.max())
        print(sub[keep].drop_duplicates(subset=["tourney_id", "tourney_name", "tourney_date"]).to_string())
# All Tenerife editions in the TML 2024 Challenger file
sub = t[t["tourney_name"].astype(str).str.contains("Tenerife", case=False)]
print("\nTML 2024 challenger Tenerife editions:")
print(sub.groupby(["tourney_id", "tourney_name", "tourney_date"]).size().to_string())

# G2
F2 = "data/raw/public_dump/tennis_my_life/atp_quali/2021_atp_quali.csv"
with open(F2, encoding="utf-8", errors="replace") as fh:
    lines2 = fh.readlines()
print("\nG2 file lines:", len(lines2))
print("HEADER:", lines2[0].strip()[:600])
for i in [96, 97, 98, 99, 100, 104, 105, 106, 107, 108]:
    print(i, lines2[i].strip()[:300])
q = pd.read_csv(F2, low_memory=False)
keep2 = [c for c in keep if c in q.columns]
print(q.iloc[94:110][keep2].to_string())
print("\nTML 2021 quali file, editions with 'Australian' or 580:")
s2 = q[q["tourney_name"].astype(str).str.contains("Australian", case=False) | q["tourney_id"].astype(str).str.contains("580")]
print(s2.groupby(["tourney_id", "tourney_name", "tourney_date"]).size().to_string())
print("rounds:", s2["round"].value_counts().to_string())
print("walkover-like scores in AO quali:")
print(s2[s2["score"].astype(str).str.contains("W/O|w/o|WO|Walk", case=False, regex=True)][keep2].to_string())
