"""B1 scout: outcome-free coverage of doubles rows in TennisLive's listings and SofaScore's events,
of the WTA umpire log's event types, of the US Open distance paths and the Wimbledon 'tz' paths.

Reads no winner or score columns. Run: ./python.sh .../peek_doubles.py > .../peek_doubles.txt
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
D = ROOT / "data" / "dump" / "points"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 300)

print("== TennisLive listed")
tl = pd.read_parquet(D / "tennislive/listed.parquet",
                     columns=["event_name", "event_kind", "event_rank", "tour", "stage", "round", "draw", "discipline",
                              "mixed", "junior", "played", "start_utc", "finished_at", "duration", "player1_id",
                              "player1_name", "player1_members", "player2_id", "player2_members"])
tl["t0"] = pd.to_datetime(tl["start_utc"], errors="coerce", utc=True)
tl["year"] = tl["t0"].dt.year
print("discipline:", tl["discipline"].value_counts(dropna=False).to_dict())
print("mixed:", tl["mixed"].value_counts(dropna=False).to_dict())
print("junior:", tl["junior"].value_counts(dropna=False).to_dict())
print("tour:", tl["tour"].value_counts(dropna=False).head(12).to_dict())
print("event_kind:", tl["event_kind"].value_counts(dropna=False).head(12).to_dict())
print("event_rank:", tl["event_rank"].value_counts(dropna=False).head(20).to_dict())
print(pd.crosstab(tl["year"], tl["discipline"]))
dbl = tl[tl["discipline"].astype(str).str.lower().str.contains("doub")]
print("\ndoubles rows by tour x year:")
print(pd.crosstab(dbl["year"], dbl["tour"]))
print("doubles with finished_at:", dbl["finished_at"].notna().mean().round(3), " with duration:", dbl["duration"].notna().mean().round(3))
print(dbl[["event_name", "event_rank", "tour", "round", "start_utc", "finished_at", "duration", "player1_name", "player1_members"]].head(6).to_string())
sgl = tl[tl["discipline"].astype(str).str.lower().str.contains("sing")]
print("singles with finished_at:", sgl["finished_at"].notna().mean().round(3), " duration:", sgl["duration"].notna().mean().round(3))

print("\n== TennisLive events (doubles totals)")
ev = pd.read_parquet(D / "tennislive/events.parquet",
                     columns=["tour", "rank", "kind", "name", "first_week", "total_singles", "total_doubles", "first_start_utc"])
ev["y"] = pd.to_datetime(ev["first_start_utc"], errors="coerce", utc=True).dt.year
ev["td"] = pd.to_numeric(ev["total_doubles"], errors="coerce")
print(ev.groupby(["y"])["td"].agg(["count", "sum"]).tail(12))

print("\n== SofaScore events doubles flag")
for name in ["sofascore", "sofascore_editions", "sofascore_tournaments"]:
    so = pd.read_parquet(D / f"{name}/events.parquet", columns=["start_utc", "doubles", "category_name", "unique_tournament_name"])
    so["y"] = pd.to_datetime(so["start_utc"], errors="coerce", utc=True).dt.year
    print(name, so["doubles"].value_counts(dropna=False).to_dict(), "years", so["y"].min(), so["y"].max(),
          so["category_name"].value_counts().head(6).to_dict())

print("\n== WTA umpire event log: types and reasons (all years, counts only)")
we = pd.read_parquet(D / "wta/events.parquet", columns=["year", "name", "type", "reason"])
print("years:", we["year"].value_counts().sort_index().to_dict())
print(we["type"].value_counts().head(40).to_string())
print(we["name"].value_counts().head(40).to_string())
print(we["reason"].value_counts().head(40).to_string())
wd = sorted((D / "wta/events").glob("*.parquet"))
tot = 0
for f in wd:
    t = pd.read_parquet(f, columns=["type"])
    tot += len(t)
    print(f.name, len(t), t["type"].value_counts().head(8).to_dict())

print("\n== US Open distance paths")
di = pd.read_parquet(D / "usopen/distance.parquet", columns=["year", "event", "match_id", "path", "value"])
print(di["year"].value_counts().sort_index().to_dict())
print(di["path"].value_counts().head(30).to_string())
print(di.head(12).to_string())

print("\n== Wimbledon tz paths")
tz = pd.read_parquet(D / "wimbledon/tz.parquet", columns=["year", "event", "match_id", "path", "value"])
print(tz["year"].value_counts().sort_index().to_dict())
print(tz["path"].value_counts().head(40).to_string())

print("\n== US Open / Wimbledon matches: duration, set durations, epoch, eventDay presence")
for name in ["usopen", "wimbledon"]:
    m = pd.read_parquet(D / f"{name}/matches.parquet",
                        columns=["year", "event", "entry.duration", "entry.scores.setDurations", "entry.epoch", "entry.eventDay", "distance_outcome"] if name == "usopen"
                        else ["year", "event", "entry.duration", "entry.scores.setDurations", "entry.epoch", "entry.eventDay"])
    print(name, m.groupby("year").size().to_dict())
    print(" duration non-null", m["entry.duration"].notna().mean().round(3), "setDurations", m["entry.scores.setDurations"].notna().mean().round(3),
          "epoch", m["entry.epoch"].notna().mean().round(3))
    if name == "usopen":
        print(" distance_outcome", m["distance_outcome"].value_counts().to_dict())
    print(m.head(3).to_string())

print("\n== AO archive: session and actual start")
ao = pd.read_parquet(D / "ausopen/matches.parquet", columns=["year", "event", "date", "actual_start_time", "duration", "session"])
print(ao.groupby("year").size().to_dict(), ao["session"].value_counts().to_dict())
print(ao.head(3).to_string())
