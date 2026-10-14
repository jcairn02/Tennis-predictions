"""B1-rederive reviewer: F7 women, the WTA's own player ids (WTA API match list) against Stage 0 (read-only).

The nine 'new' women's ids are numbers from TML's 2026 file. For each, take every WTA API singles match of
the WTA player id with the same number, and look for the same match in Stage 0 under the ESTABLISHED id
(same opponent name key, tournament date within 10 days). If the WTA's own id number covers matches that
Stage 0 holds under the established id, the two ids are one person by an independent record.
Also lists, per pair, the countries the WTA API gives and Stage 0's ranks around the switch.
Writes f7_wta_api_match.csv.
"""
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
S0 = ROOT / "data/studies/predictability_diagnostic"


def name_key(value):
    if pd.isna(value):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def skey(v):
    return " ".join(sorted(name_key(v).split()))


api = pq.ParquetFile(ROOT / "data/dump/points/wta/matches.parquet").read().to_pandas()
api = api.loc[:, ~api.columns.duplicated()]
api = api[api.DrawMatchType.eq("S")]
ev = pq.ParquetFile(ROOT / "data/dump/points/wta/editions.parquet").read().to_pandas()
ev = ev.loc[:, ~ev.columns.duplicated()]
print("editions columns:", ev.columns.tolist()[:40])

long = []
for s, o in (("A", "B"), ("B", "A")):
    x = api[["year", "tournament_id", "MatchID", "DrawLevelType", "MatchTimeStamp", "RoundID",
             f"PlayerID{s}", f"PlayerNameFirst{s}", f"PlayerNameLast{s}", f"PlayerCountry{s}",
             f"PlayerNameFirst{o}", f"PlayerNameLast{o}"]].copy()
    x.columns = ["year", "tid", "mid", "lvl", "ts", "rnd", "pid", "first", "last", "ctry", "ofirst", "olast"]
    long.append(x)
long = pd.concat(long, ignore_index=True)
long["pid"] = long.pid.astype(str)
long["okey"] = (long.ofirst.astype(str) + " " + long.olast.astype(str)).map(skey)
long["date"] = pd.to_datetime(long.ts, errors="coerce", utc=True).dt.tz_localize(None)

m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date", "tournament_name",
                                                             "source", "level", "qualifying", "round"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "opponent_id",
                                                                   "player_name", "rank", "country"])
p = p.merge(m, on="match_id")
p["tdate"] = pd.to_datetime(p.tournament_date)
names = p.drop_duplicates("player_id").set_index("player_id").player_name
p["okey"] = p.opponent_id.map(names).map(skey)

pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
res = []
for r in pairs[pairs.tour.eq("wta")].itertuples():
    num = r.new_id.split(":")[1]
    a = long[long.pid.eq(num)].copy()
    est = p[p.player_id.eq(r.established_id)]
    new = p[p.player_id.eq(r.new_id)]
    hit_est = hit_new = 0
    det = []
    for x in a.itertuples():
        if pd.isna(x.date):
            continue
        cand = est[est.okey.eq(x.okey) & (est.tdate - x.date).abs().le(pd.Timedelta(days=16))]
        cand_new = new[new.okey.eq(x.okey) & (new.tdate - x.date).abs().le(pd.Timedelta(days=16))]
        hit_est += len(cand) > 0
        hit_new += len(cand_new) > 0
        det.append((x.date.date(), x.ctry, x.okey, len(cand), len(cand_new)))
    print(f"\n{r.name_key}: WTA API id {num}: {len(a)} singles matches; countries {a.ctry.value_counts().to_dict()}; "
          f"found in Stage 0 under ESTABLISHED {r.established_id}: {hit_est}; under NEW id: {hit_new}")
    for d in det[-6:]:
        print("    ", d)
    # ranks around the switch
    t0 = pd.Timestamp(r.new_id_first)
    win = est[(est.tdate >= t0 - pd.Timedelta(days=70)) & (est.tdate <= t0 + pd.Timedelta(days=70))]
    print("    est ranks within 70 days:", win.sort_values("tdate")[["tdate", "tournament_name", "rank", "source"]]
          .assign(tdate=lambda z: z.tdate.dt.date).drop_duplicates(["tdate", "tournament_name"]).values.tolist())
    print("    new-id ranks:", new[["tdate", "tournament_name", "rank"]].assign(tdate=lambda z: z.tdate.dt.date)
          .drop_duplicates().values.tolist())
    res.append({"name_key": r.name_key, "established_id": r.established_id, "new_id": r.new_id,
                "wta_api_matches_of_new_number": len(a), "wta_api_countries": str(a.ctry.value_counts().to_dict()),
                "api_matches_found_under_established_id": hit_est, "api_matches_found_under_new_id": hit_new})
pd.DataFrame(res).to_csv(OUT / "f7_wta_api_match.csv", index=False)

# Also: does any OTHER WTA API id carry the same name (a second person)?
for nm in ["vivian wolff", "alisa oktiabreva"]:
    y = long[(long["first"].astype(str) + " " + long["last"].astype(str)).map(skey).eq(skey(nm))]
    print(nm, y[["pid", "ctry", "date", "lvl", "tid", "okey"]].to_string())
