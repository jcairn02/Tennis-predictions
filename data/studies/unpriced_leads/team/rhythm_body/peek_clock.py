"""B1 scout: outcome-free coverage of clock times (start_utc, end_utc) and of doubles rows.

Reads no winner, no sets, no score. Only ids, times, categories, flags.
Run: ./python.sh data/studies/unpriced_leads/team/rhythm_body/peek_clock.py > .../peek_clock.txt
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "studies"
L = S / "match_timing" / "links"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 300)


def tod_share(s: pd.Series) -> float:
    t = pd.to_datetime(s, errors="coerce", utc=True)
    ok = t.notna()
    if ok.sum() == 0:
        return float("nan")
    has_time = (t[ok].dt.hour != 0) | (t[ok].dt.minute != 0)
    return float(has_time.mean())


print("== start_utc samples and time-of-day share per link source")
for f in sorted(L.glob("*.parquet")):
    if f.name.startswith("flashscore_") or f.name in ("sirgenkii.parquet",):
        continue
    d = pd.read_parquet(f, columns=["match_id", "start_utc", "date_basis"])
    nn = d["start_utc"].notna().mean()
    print(f"{f.name:28s} rows={len(d):7d} start_utc non-null={nn:.3f} time-of-day share={tod_share(d['start_utc']):.3f}",
          "sample:", d["start_utc"].dropna().head(2).tolist(), d["date_basis"].value_counts().head(3).to_dict())

print("\n== flashscore_records")
fr = pd.read_parquet(L / "flashscore_records.parquet",
                     columns=["fs_match_id", "start_utc", "end_utc", "gender", "category", "is_doubles", "is_junior",
                              "is_exhibition", "tournament_name", "home_name", "away_name", "home_fs_id", "away_fs_id",
                              "status", "round"])
fr["t0"] = pd.to_datetime(fr["start_utc"], errors="coerce", utc=True)
fr["t1"] = pd.to_datetime(fr["end_utc"], errors="coerce", utc=True)
fr["year"] = fr["t0"].dt.year
print("is_doubles:", fr["is_doubles"].value_counts(dropna=False).to_dict())
print("is_exhibition:", fr["is_exhibition"].value_counts(dropna=False).to_dict())
print("category:", fr["category"].value_counts(dropna=False).head(20).to_dict())
print("status:", fr["status"].value_counts(dropna=False).head(10).to_dict())
g = fr.groupby(["year", "is_doubles"]).agg(n=("fs_match_id", "size"), end_nn=("t1", lambda s: s.notna().mean()))
print(g.unstack(1).round(3))
dbl = fr[fr["is_doubles"].astype(str).str.lower().isin(["true", "1"])]
print("\ndoubles sample:")
print(dbl[["start_utc", "end_utc", "category", "tournament_name", "home_name", "away_name", "home_fs_id", "away_fs_id"]].head(8))
print("doubles by category x year (counts):")
print(pd.crosstab(dbl["category"], dbl["year"]).iloc[:, -16:])
print("\ndoubles: share with end_utc", dbl["t1"].notna().mean().round(3))
dur = (fr["t1"] - fr["t0"]).dt.total_seconds() / 60
print("singles duration minutes (end - start) describe:")
print(dur[~fr.index.isin(dbl.index)].describe())

print("\n== frame matches: flashscore start time-of-day and end_utc coverage by tour x season")
fm = pd.read_parquet(S / "current_best_model/template_2026-10-10/model_frame.parquet", columns=["match_id", "tour", "season"])
fl = pd.read_parquet(L / "flashscore.parquet", columns=["match_id", "source_key", "start_utc"])
fl = fl.merge(fr[["fs_match_id", "t1"]], left_on="source_key", right_on="fs_match_id", how="left")
fl["t0"] = pd.to_datetime(fl["start_utc"], errors="coerce", utc=True)
fl["tod"] = fl["t0"].notna() & ((fl["t0"].dt.hour != 0) | (fl["t0"].dt.minute != 0))
fl = fl.drop_duplicates("match_id")
x = fm.merge(fl[["match_id", "tod", "t1"]], on="match_id", how="left")
x["fs_tod"] = x["tod"].fillna(False).astype(bool)
x["fs_end"] = x["t1"].notna()
# any source with a time of day
anyt = []
for f in ["sofascore", "live_tennis_api", "api_tennis", "wta_api", "slam_feeds", "infosys", "open_tennis_data", "pbp_copy", "tdi"]:
    d = pd.read_parquet(L / f"{f}.parquet", columns=["match_id", "start_utc"])
    t = pd.to_datetime(d["start_utc"], errors="coerce", utc=True)
    d = d[t.notna() & ((t.dt.hour != 0) | (t.dt.minute != 0))]
    anyt.append(d[["match_id"]])
anyt = pd.concat(anyt).drop_duplicates()
x["other_tod"] = x["match_id"].isin(anyt["match_id"])
x["any_tod"] = x["fs_tod"] | x["other_tod"]
print(x.groupby(["tour", "season"])[["fs_tod", "fs_end", "any_tod"]].mean().round(3).unstack(0))
