"""Simulate today's feed builder on the WTA website source alone: how many copies of each of the 187 September matches
it would hold (read-only; no file written). Usage: sim_wta_site.py [--drop-last-week]"""
import sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import candidate_stage0 as C
rows, stats = C.load_wta_site()
print(stats.get("wta_api_player_matches"), {k: v for k, v in stats.items() if k.startswith("v29") or k.startswith("dropped")})
print(list(rows.columns)[:40])
r = rows[(rows["tour"] == "wta")].copy()
r = r[(r["ev_date"] >= "2026-08-31") & (r["ev_date"] <= "2026-09-21")].copy()
def surn(n):
    k = C.name_key(n).split()
    return k[-1] if k else ""
def pair_of(a, b):
    return "|".join(sorted([a, b]))
r["pair"] = [pair_of(surn(a), surn(b)) for a, b in zip(r["p1"], r["p2"])]
r["idpair"] = [pair_of(str(a), str(b)) for a, b in zip(r["id1"], r["id2"])]
m = pd.read_csv(ROOT / "data/studies/p6_data_issues/wta_site/sep2026_matches.csv")
m = m[m["played"]].copy()
m["pair"] = [pair_of(a, b) for a, b in zip(m["k_a"], m["k_b"])]
hit = r[r["pair"].isin(set(m["pair"]))].copy()
hit["part"] = np.where(hit["sid"].str.contains(":api:"), "api", "copy")
true = m.drop_duplicates("pair").set_index("pair")["true_event"]
def right(name, p):
    t = str(true.get(p, "")).lower(); n = str(name).lower()
    return t.split(" - ")[-1].split(",")[0].strip() in n or n.split(" - ")[-1].split(",")[0].strip() in t
hit["right"] = [right(n, p) for n, p in zip(hit["ev_name"], hit["pair"])]
print("rows of the 186 played matches:", len(hit), hit["part"].value_counts().to_dict())
cnt = hit.groupby("pair").size()
print("copies per match:", cnt.value_counts().sort_index().to_dict(), " matches found:", cnt.size, "of", m["pair"].nunique())
print(hit.groupby(["part", "right"]).size().to_string())
wrong = hit[~hit["right"]]
print("wrong copies by event and level:"); print(wrong.groupby(["ev_name", "ev_level", "qual"]).size().to_string())
both = hit.groupby("pair")["right"].agg(["sum", "size"])
print("matches held right and wrong:", int(((both["sum"] >= 1) & (both["size"] > both["sum"])).sum()),
      " wrong only:", int((both["sum"] == 0).sum()), " right only, once:", int(((both["sum"] == 1) & (both["size"] == 1)).sum()))
