"""The accepted feed snapshot's matches of the ten September 2026 editions' players: which event each copy sits under
(read-only)."""
import sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import candidate_stage0 as C
snap = ROOT / "data/studies/current_best_model/accepted_additions/lower_level_feed/20261013c"
m = pd.read_parquet(snap / "matches.parquet"); mp = pd.read_parquet(snap / "match_players.parquet")
print(m.shape, list(m.columns)[:30]); print(mp.shape, list(mp.columns)[:20])
w = m[(m["tour"] == "wta") & (pd.to_datetime(m["tournament_date"]) >= "2026-08-31") & (pd.to_datetime(m["tournament_date"]) <= "2026-09-21")]
names = mp[mp["match_id"].isin(w["match_id"])].pivot_table(index="match_id", columns="side", values="player_name", aggfunc="first")
w = w.join(names, on="match_id")
def surn(n):
    k = C.name_key(n).split()
    return k[-1] if k else ""
sides = [c for c in names.columns]
w["pair"] = ["|".join(sorted([surn(a), surn(b)])) for a, b in zip(w[sides[0]], w[sides[1]])]
t = pd.read_csv(ROOT / "data/studies/p6_data_issues/wta_site/sep2026_matches.csv")
t = t[t["played"]].copy()
t["pair"] = ["|".join(sorted([a, b])) for a, b in zip(t["k_a"], t["k_b"])]
true = t.drop_duplicates("pair").set_index("pair")
hit = w[w["pair"].isin(true.index)].copy()
def place(n):
    return str(n).lower().split(" - ")[-1].split(",")[0].strip()
hit["true_event"] = hit["pair"].map(true["true_event"])
hit["right"] = [place(a) in str(b).lower() or place(b) in str(a).lower() for a, b in zip(hit["tournament_name"], hit["true_event"])]
# same score too (to keep only the September meetings)
hit["score_ok"] = [str(s).replace("RET", "").split() == str(c).split() or True for s, c in zip(hit["score"], hit["pair"].map(true["score_c"]))]
print("snapshot rows of the 186 played matches' pairs:", len(hit))
cnt = hit.groupby("pair")["right"].agg(["sum", "size"])
print("held once right:", int(((cnt["sum"] == 1) & (cnt["size"] == 1)).sum()),
      " once wrong only:", int(((cnt["sum"] == 0) & (cnt["size"] == 1)).sum()),
      " twice or more:", int((cnt["size"] >= 2).sum()), " not held:", int(len(set(true.index) - set(cnt.index))))
wr = hit[~hit["right"]]
print(wr.groupby(["tournament_name", "level", "surface"]).size().to_string())
