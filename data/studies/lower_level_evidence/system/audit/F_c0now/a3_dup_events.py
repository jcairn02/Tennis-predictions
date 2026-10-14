"""Role E audit of C0_now, part 3: certain duplicates (the same pair, the same round, the same week, two tournaments),
counted per match and per event, and whole events listed twice. Counts and non-outcome labels only.
Run from the repository root: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a3_dup_events.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as LC  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
OUT: dict = {}


@lru_cache(maxsize=None)
def name_key(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


cols = ["match_id", "tour", "year", "tournament_id", "tournament_name", "tournament_date", "round", "map_level",
        "source", "player_a_id", "player_b_id", "qualifying"]
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=cols)
ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
m["new"] = ~m["match_id"].isin(ref_ids)
m["bucket"] = LC.bucket(m["map_level"])
m["holdout"] = LC.in_holdout(m["tournament_date"])
mp = pd.read_parquet(CAND / "stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
nk = mp.assign(k=mp["player_name"].map(name_key)).pivot(index="match_id", columns="side", values="k")
m["nkA"], m["nkB"] = m["match_id"].map(nk["A"]).fillna(""), m["match_id"].map(nk["B"]).fillna("")
lo = np.where(m["player_a_id"] < m["player_b_id"], m["player_a_id"], m["player_b_id"])
hi = np.where(m["player_a_id"] < m["player_b_id"], m["player_b_id"], m["player_a_id"])
m["idkey"] = m["tour"] + "|" + lo + "|" + hi
nlo = np.where(m["nkA"] < m["nkB"], m["nkA"], m["nkB"])
nhi = np.where(m["nkA"] < m["nkB"], m["nkB"], m["nkA"])
m["nmkey"] = m["tour"] + "|" + pd.Series(nlo, index=m.index) + "|" + pd.Series(nhi, index=m.index)
m.loc[m["nkA"].eq("") | m["nkB"].eq(""), "nmkey"] = np.nan

twins = []
for key in ("idkey", "nmkey"):
    g = m.dropna(subset=[key]).groupby([key, "tournament_date", "round"])
    sz = g["match_id"].transform("size")
    nev = g["tournament_id"].transform("nunique")
    sel = m.dropna(subset=[key])[(sz > 1) & (nev > 1)]
    sel = sel.assign(group=sel[key] + "|" + sel["tournament_date"].astype(str) + "|" + sel["round"])
    sel = sel[sel.groupby("group")["new"].transform("any")]
    twins.append(sel.assign(by=key))
tw = pd.concat(twins, ignore_index=True)
tw = tw.sort_values("by").drop_duplicates("match_id", keep="first")      # a match counted once (by id first)
# one copy per group may be the true one: the extra copies are size - 1 per group
grp = tw.groupby("group").agg(n=("match_id", "size"), any_frozen=("new", lambda s: bool((~s).any())),
                              sources=("source", lambda s: ",".join(sorted(set(s)))), by=("by", "first"),
                              holdout=("holdout", "first"), tour=("tour", "first"), bucket=("bucket", "first"),
                              date=("tournament_date", "first"))
OUT["same_pair_round_week_in_2plus_events_groups"] = int(len(grp))
OUT["matches_in_such_groups"] = int(grp["n"].sum())
OUT["extra_copies_at_least"] = int((grp["n"] - 1).sum())
OUT["groups_with_a_frozen_match"] = int(grp["any_frozen"].sum())
OUT["groups_by_sources"] = grp.groupby(["sources", "by"]).size().rename("n").reset_index().to_dict("records")
OUT["groups_by_tour_bucket_holdout"] = grp.groupby(["tour", "bucket", "holdout"]).size().rename("n").reset_index() \
    .to_dict("records")
OUT["groups_by_week"] = grp.groupby(pd.to_datetime(grp["date"]).dt.strftime("%Y-%m-%d")).size().sort_values(
    ascending=False).head(25).to_dict()
tw.drop(columns=["nkA", "nkB"]).to_csv(AUD / "dup_same_week_same_round_matches.csv", index=False)

# events: new tournament (id, date) whose matches mostly have a twin in another event of the same week
ev = m[m["new"]].groupby(["tournament_id", "tournament_date"]).agg(
    matches=("match_id", "size"), source=("source", "first"), name=("tournament_name", "first"),
    tour=("tour", "first")).reset_index()
tws = set(tw.loc[tw["new"], "match_id"])
evt = m[m["new"] & m["match_id"].isin(tws)].groupby(["tournament_id", "tournament_date"]).size().rename("twins")
ev = ev.merge(evt.reset_index(), on=["tournament_id", "tournament_date"], how="left").fillna({"twins": 0})
ev["share"] = ev["twins"] / ev["matches"]
OUT["new_events"] = int(len(ev))
OUT["new_events_with_any_twin"] = int((ev["twins"] > 0).sum())
OUT["new_events_half_or_more_twins"] = ev[ev["share"] >= 0.5][["tournament_id", "tournament_date", "name", "source",
                                                                "matches", "twins"]].astype(str).to_dict("records")
ev.sort_values("twins", ascending=False).to_csv(AUD / "dup_events.csv", index=False)

# the same name-key pair in the same tournament and round (ids differ): a split identity inside one event
g = m.dropna(subset=["nmkey"]).groupby(["nmkey", "tournament_id", "tournament_date", "round"])
sel = m.dropna(subset=["nmkey"])[(g["match_id"].transform("size") > 1) & (g["idkey"].transform("nunique") > 1)]
sel = sel[sel.groupby(["nmkey", "tournament_id", "tournament_date", "round"])["new"].transform("any")]
OUT["same_names_same_event_round_ids_differ_matches"] = int(len(sel))
(AUD / "a3_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:20000])
