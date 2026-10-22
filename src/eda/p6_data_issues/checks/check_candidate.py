"""Copies of the 186 played September 2026 matches in a feed candidate (or snapshot) folder: by the two surnames and
the set scores (read-only). Usage: check_candidate.py <folder with stage0_matches.parquet or matches.parquet>"""
import sys, re
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import candidate_stage0 as C
f = Path(sys.argv[1])
mfile = f / "stage0_matches.parquet" if (f / "stage0_matches.parquet").exists() else f / "matches.parquet"
pfile = f / "stage0_match_players.parquet" if (f / "stage0_match_players.parquet").exists() else f / "match_players.parquet"
m = pd.read_parquet(mfile); mp = pd.read_parquet(pfile, columns=["match_id", "side", "player_name", "player_id"])
w = m[(m["tour"] == "wta") & (pd.to_datetime(m["tournament_date"]) >= "2026-08-31") & (pd.to_datetime(m["tournament_date"]) <= "2026-09-21")].copy()
names = mp[mp["match_id"].isin(w["match_id"])].pivot_table(index="match_id", columns="side", values="player_name", aggfunc="first")
w = w.join(names, on="match_id")
sides = list(names.columns)
def sur(n):
    k = C.name_key(n).split(); return k[-1] if k else ""
def sig(s):
    s = re.sub(r"\(\d+\)", "", str(s or "")); sets = [tuple(sorted((int(a), int(b)), reverse=True)) for a, b in re.findall(r"(\d+)-(\d+)", s)]
    return ";".join(f"{a}-{b}" for a, b in sets)
w["pair"] = ["|".join(sorted([sur(a), sur(b)])) for a, b in zip(w[sides[0]], w[sides[1]])]
w["sig"] = w["score"].map(sig)
t = pd.read_csv(ROOT / "data/studies/p6_data_issues/wta_site/sep2026_matches.csv")
t = t[t["played"]].copy()
t["pair"] = ["|".join(sorted([a, b])) for a, b in zip(t["k_a"], t["k_b"])]
t["sig"] = t["score_c"].map(sig)
key = t.drop_duplicates(["pair", "sig"]).set_index(["pair", "sig"])
hit = w.merge(t[["pair", "sig", "true_event", "true_level", "true_map_level"]].drop_duplicates(["pair", "sig"]), on=["pair", "sig"])
def place(n): return str(n).lower().split(" - ")[-1].split(",")[0].strip()
hit["right"] = [place(a) in str(b).lower() or place(b) in str(a).lower() for a, b in zip(hit["tournament_name"], hit["true_event"])]
cnt = hit.groupby(["pair", "sig"])["right"].agg(["sum", "size"])
print(f"{f.name}: rows {len(hit)}; matches found {len(cnt)} of {len(key)}; once right {int(((cnt['sum']==1)&(cnt['size']==1)).sum())}; "
      f"wrong only {int((cnt['sum']==0).sum())}; twice or more {int((cnt['size']>=2).sum())}")
print(hit[~hit["right"]].groupby(["tournament_name", "level"]).size().to_string() if (~hit["right"]).any() else "no wrong copies")
print(hit.groupby(["level", "right"]).size().to_string())
found = set(zip(hit["pair"], hit["sig"]))
miss = t[[(p, s) not in found for p, s in zip(t["pair"], t["sig"])]]
print("not found:", miss[["name_a", "name_b", "score_c", "reason", "true_event", "qpm_flag", "round_name"]].to_string())
for _, r in miss.iterrows():
    a, b = r["k_a"], r["k_b"]
    x = w[w["pair"].str.contains(a) | w["pair"].str.contains(b)]
    print(x[["tournament_name", "level", "round", "score", "pair"] + sides].to_string())
