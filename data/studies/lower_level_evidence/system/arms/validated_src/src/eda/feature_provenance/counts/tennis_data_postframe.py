# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""tennis-data.co.uk 2026 rows after 28 Jul 2026, by event, and those Stage 1 left unlinked (read-only)."""
from pathlib import Path
import pandas as pd

rows = []
for f in Path("data/dump/odds/tennis_data_couk").glob("*/*/2026.parquet"):
    d = pd.read_parquet(f)
    d = d[["Date", "Tournament", "Round"] + [c for c in ("PSW", "AvgW", "B365W") if c in d.columns]].copy()
    d["tour"], d["series"] = f.parts[-3], f.parts[-2]
    rows.append(d)
td = pd.concat(rows, ignore_index=True)
td["Date"] = pd.to_datetime(td["Date"], errors="coerce")
print("2026 rows by tour:", td.groupby("tour").size().to_dict(), "last date:", td.groupby("tour")["Date"].max().to_dict())
for c in ("PSW", "AvgW", "B365W"):
    td[c] = pd.to_numeric(td.get(c), errors="coerce")
print("PSW present, last date by tour:", td[td["PSW"] > 1].groupby("tour")["Date"].max().to_dict())
post = td[td["Date"] > "2026-07-28"]
print(post.groupby(["tour", "series", "Tournament"]).agg(n=("Date", "size"), first=("Date", "min"),
      last=("Date", "max"), avg=("AvgW", lambda x: int((x > 1).sum())), ps=("PSW", lambda x: int((x > 1).sum()))).to_string())
u = pd.read_parquet("data/studies/predictability_diagnostic/stage1_odds_unlinked.parquet")
u = u[u["td_date"] > "2026-07-28"]
print("unlinked tennis-data rows after 28 Jul:", len(u))
print(u[["tour", "td_tournament", "td_round", "reason"]].to_string())
