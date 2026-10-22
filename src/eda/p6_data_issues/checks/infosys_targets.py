"""How many of P6's targets without a SofaScore point record the ATP's Infosys copy holds without rally analysis (the
matches whose point file the ATP's host now serves, by the probe of 14 Oct 2026). Read-only. A target links to a
copy record of the same year by the two surnames (the copy writes 'A. ZVEREV') within 7 days of the target's date."""
import gzip
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
COPY = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "infosys_full"


def key(name) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ")
    w = [x for x in s.split() if len(x) > 1]
    return w[-1] if w else ""


t = pd.read_csv(ROOT / "data/studies/p6_data_issues/flashscore/targets.csv.gz", low_memory=False)
t["d"] = pd.to_datetime(t["d"])
t = t[t["tour"].eq("M")].copy()
t["pair"] = ["|".join(sorted([key(a), key(b)])) for a, b in zip(t["name1"], t["name2"])]
recs = []
for year in (2021, 2022, 2023, 2024, 2025):
    p = COPY / f"{year}_data.jsonl.gz"
    if not p.exists():
        continue
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            recs.append({"year": year, "event": d.get("tournament_id"), "mid": d.get("match_id"),
                         "date": d.get("match_date"), "rally": d.get("rally_analysis") is not None,
                         "pair": "|".join(sorted([key(d.get("player1_name")), key(d.get("player2_name"))]))})
r = pd.DataFrame(recs)
r["date"] = pd.to_datetime(r["date"], errors="coerce")
m = t.reset_index().merge(r, on="pair", how="inner")
m = m[(m["date"] - m["d"]).abs().dt.days.le(7)]
best = m.sort_values("rally", ascending=False).drop_duplicates("index")
t["copy"] = t.index.map(best.set_index("index")["rally"]).map({True: "with rally analysis", False: "without rally analysis"})
t["copy"] = t["copy"].fillna("not in the copy")
out = t.groupby(["gap", "copy"]).size().unstack(fill_value=0)
print(out.to_string())
print("men's targets:", len(t))

# The targets whose point file the copy already holds: are they the misdated Tennis My Life copies (phantom targets)?
mm = pd.read_csv(ROOT / "data/studies/p6_data_issues/tml_misdates/misdated_matches.csv.gz", low_memory=False,
                 usecols=["category", "tourney_name", "tourney_date"])
mm = mm[mm["category"].astype(str).str.startswith(("misdated", "lumped", "consecutive", "dated by"))]
mm["d"] = pd.to_datetime(mm["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
bad = set(zip(mm["tourney_name"], mm["d"]))
w = t[t["copy"].eq("with rally analysis")]
flag = pd.Series([(n, d) in bad for n, d in zip(w["tname"], w["d"])], index=w.index)
print("targets whose point file the copy holds:", len(w), "; in a flagged Tennis My Life edition:", int(flag.sum()),
      "; by creator:", w["creator"].value_counts().to_dict())

# ... or the second (Sackmann) copies of the map's doubles, whose Tennis My Life twin took the Infosys record?
dbl = pd.read_csv(ROOT / "data/studies/p6_data_issues/tml_misdates/map_doubles.csv")
dbl["d2"] = pd.to_datetime(dbl["map_other_d"])
dbl["pair"] = ["|".join(sorted([key(a), key(b)])) for a, b in zip(dbl["winner_name"], dbl["loser_name"])]
dk = set(zip(dbl["pair"], dbl["d2"].dt.strftime("%Y-%m-%d")))
inside = pd.Series([(p, d.strftime("%Y-%m-%d")) in dk for p, d in zip(w["pair"], w["d"])], index=w.index)
print("of those, the second copy of a map double:", int(inside.sum()), "of", len(w))
