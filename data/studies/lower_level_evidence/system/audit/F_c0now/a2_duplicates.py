"""Role E audit of C0_now, part 2: duplicates. Independent of candidate_stage0.check_duplicates.

(a) a new match that repeats a frozen one, (b) two new matches that are one match, (c) the weekly-venue problem.
Rule: same tour, same unordered pair (by player id; and separately by exact name key, which catches identity splits),
|tournament-date difference| <= 10 days. Outcomes (winner, score) are compared ONLY where both matches have a tournament
date before 2024-12-30; holdout pairs are counted, never compared. Nothing but counts and non-outcome labels is printed.
Run from the repository root: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a2_duplicates.py
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
H0 = pd.Timestamp("2024-12-30")
OUT: dict = {}


@lru_cache(maxsize=None)
def name_key(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


@lru_cache(maxsize=None)
def venue(name) -> str:
    """A rough venue key: the tournament name without level/prize tokens, years and digits."""
    s = name_key(name)
    toks = [t for t in s.split() if not re.fullmatch(r"(m|w)\d+k?|itf|\d+k?|futures?|challenger|women|men|s|"
                                                         r"wta|atp|q|qualifying|open|cup|international|tennis|"
                                                         r"championships?|trophy|tournament|pro|circuit|ladies|"
                                                         r"r\d+|w\d+|f\d+|usa|esp|fra|ita|tur|tun|egy|mex|can", t)]
    return " ".join(toks[:2])


cols = ["match_id", "tour", "year", "tournament_id", "tournament_name", "tournament_date", "round", "status", "score",
        "player_a_id", "player_b_id", "a_won", "map_level", "source"]
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=cols)
ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
m["new"] = ~m["match_id"].isin(ref_ids)
m["td"] = pd.to_datetime(m["tournament_date"])
m["day"] = (m["td"] - pd.Timestamp("1970-01-01")).dt.days.astype("int64")
lo = np.where(m["player_a_id"] < m["player_b_id"], m["player_a_id"], m["player_b_id"])
hi = np.where(m["player_a_id"] < m["player_b_id"], m["player_b_id"], m["player_a_id"])
m["key"] = m["tour"] + "|" + lo + "|" + hi
m["pre"] = m["td"] < H0
# outcomes kept only for matches before the holdout (never read for 2025-2026)
m["winner"] = pd.Series(np.where(m["a_won"].astype(bool), m["player_a_id"], m["player_b_id"]), index=m.index).where(
    m["pre"], None)
m["score"] = m["score"].where(m["pre"], None)
m = m.drop(columns=["a_won"])
m["bucket"] = LC.bucket(m["map_level"])
m["venue"] = m["tournament_name"].map(venue)


def pairs_within(frame: pd.DataFrame, key: str, days: int = 10) -> pd.DataFrame:
    """Every (new match, other match) with the same key within `days`; a new-new pair once."""
    left = frame[frame["new"]][["match_id", key, "day"]]
    right = frame[[key, "match_id", "day"]]
    j = left.merge(right, on=key, suffixes=("", "_o"))
    j = j[(j["match_id"] != j["match_id_o"]) & ((j["day"] - j["day_o"]).abs() <= days)]
    # a new-new pair once
    o_new = j["match_id_o"].isin(set(frame.loc[frame["new"], "match_id"]))
    j = j[~o_new | (j["match_id"] < j["match_id_o"])]
    return j.drop(columns=[key])


def describe(j: pd.DataFrame, label: str) -> pd.DataFrame:
    a = m.set_index("match_id")
    x = j.copy()
    for c in ("tournament_id", "td", "round", "source", "status", "pre", "bucket", "new", "venue",
              "tour", "player_a_id", "player_b_id"):
        x[c] = x["match_id"].map(a[c])
        x[c + "_o"] = x["match_id_o"].map(a[c])
    # outcomes are looked up only for pairs whose two matches are both before the holdout
    bp = x["pre"].astype(bool) & x["pre_o"].astype(bool)
    pre = a.loc[a["pre"].astype(bool), ["winner", "score"]]
    for c in ("winner", "score"):
        x[c] = pd.Series(np.nan, index=x.index, dtype=object)
        x[c + "_o"] = pd.Series(np.nan, index=x.index, dtype=object)
        x.loc[bp, c] = x.loc[bp, "match_id"].map(pre[c])
        x.loc[bp, c + "_o"] = x.loc[bp, "match_id_o"].map(pre[c])
    x["gap"] = (x["td"] - x["td_o"]).dt.days.abs()
    x["same_event"] = (x["tournament_id"] == x["tournament_id_o"]) & (x["td"] == x["td_o"])
    x["kind"] = np.where(x["new_o"], "new-new", "new-frozen")
    x["gapcls"] = np.select([x["same_event"], x["gap"].eq(0), x["gap"] <= 3, x["gap"].between(4, 10)],
                            ["same event", "same week, other event", "1-3 days", "4-10 days"], "other")
    x["same_venue"] = x["venue"].eq(x["venue_o"]) & x["venue"].ne("")
    x["both_pre"] = x["pre"].astype(bool) & x["pre_o"].astype(bool)
    x["same_round"] = x["round"] == x["round_o"]
    # outcome comparison only where both are before the holdout
    x["same_winner_pre"] = np.where(x["both_pre"], x["winner"] == x["winner_o"], np.nan)
    x["same_score_pre"] = np.where(x["both_pre"], x["score"].astype(str) == x["score_o"].astype(str), np.nan)
    x = x.drop(columns=["winner", "winner_o", "score", "score_o"])
    x["check"] = label
    return x


# ---------------------------------------------------------------- by player id
jid = describe(pairs_within(m, "key"), "id pair")
# ---------------------------------------------------------------- by exact name key (identity splits)
mp = pd.read_parquet(CAND / "stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
nk = mp.assign(k=mp["player_name"].map(name_key)).pivot(index="match_id", columns="side", values="k")
m["nkA"] = m["match_id"].map(nk["A"])
m["nkB"] = m["match_id"].map(nk["B"])
nlo = np.where(m["nkA"] < m["nkB"], m["nkA"], m["nkB"])
nhi = np.where(m["nkA"] < m["nkB"], m["nkB"], m["nkA"])
m["nkey"] = m["tour"] + "|" + pd.Series(nlo, index=m.index).astype(str) + "|" + pd.Series(nhi, index=m.index).astype(str)
okname = m["nkA"].fillna("").ne("") & m["nkB"].fillna("").ne("")
jn = pairs_within(m[okname], "nkey")
jn = jn.merge(jid[["match_id", "match_id_o"]].assign(dup=1), on=["match_id", "match_id_o"], how="left")
jn = jn[jn["dup"].isna()].drop(columns="dup")          # pairs the id check already holds
jn = describe(jn, "name pair, ids differ")
allp = pd.concat([jid, jn], ignore_index=True)
allp.to_parquet(AUD / "dup_pairs.parquet", index=False)

summ = allp.groupby(["check", "kind", "gapcls"]).agg(
    pairs=("match_id", "size"), both_pre=("both_pre", "sum"), same_round=("same_round", "sum"),
    same_venue=("same_venue", "sum"),
    same_winner_pre=("same_winner_pre", lambda s: int(np.nansum(s.astype(float)))),
    same_score_pre=("same_score_pre", lambda s: int(np.nansum(s.astype(float))))).reset_index()
summ.to_csv(AUD / "dup_summary.csv", index=False)
OUT["summary"] = summ.to_dict("records")
OUT["by_source_kind_gap"] = allp.groupby(["check", "source", "source_o", "kind", "gapcls"]).size().rename("n") \
    .reset_index().sort_values("n", ascending=False).head(40).to_dict("records")
OUT["by_bucket_period"] = allp.assign(holdout=~allp["pre"].astype(bool)).groupby(
    ["check", "kind", "gapcls", "bucket", "holdout"]).size().rename("n").reset_index().to_dict("records")
# weekly venue: consecutive weeks, other event, same venue key
wk = allp[(allp["gap"].isin([7])) & ~allp["same_event"]]
OUT["weekly_7d_pairs"] = wk.groupby(["check", "kind", "same_venue"]).agg(
    pairs=("match_id", "size"), both_pre=("both_pre", "sum"), same_round=("same_round", "sum"),
    same_score_pre=("same_score_pre", lambda s: int(np.nansum(s.astype(float)))),
    same_winner_pre=("same_winner_pre", lambda s: int(np.nansum(s.astype(float))))).reset_index().to_dict("records")

# ---------------------------------------------------------------- baseline: frozen-frozen pairs within 10 days
f = m[~m["new"]]
ff = f[["match_id", "key", "day"]].merge(f[["match_id", "key", "day"]], on="key", suffixes=("", "_o"))
ff = ff[(ff["match_id"] < ff["match_id_o"]) & ((ff["day"] - ff["day_o"]).abs() <= 10)]
a = m.set_index("match_id")
ff["same_event"] = (ff["match_id"].map(a["tournament_id"]) == ff["match_id_o"].map(a["tournament_id"])) & (
    ff["day"] == ff["day_o"])
ff["gap"] = (ff["day"] - ff["day_o"]).abs()
ff["both_pre"] = ff["match_id"].map(a["pre"]) & ff["match_id_o"].map(a["pre"])
ff["same_venue"] = (ff["match_id"].map(a["venue"]) == ff["match_id_o"].map(a["venue"])) & ff["match_id"].map(
    a["venue"]).ne("")
ffp = ff[ff["both_pre"]].copy()
apre = a.loc[a["pre"].astype(bool), ["winner", "score"]]
ffp["same_score"] = ffp["match_id"].map(apre["score"]).astype(str) == ffp["match_id_o"].map(apre["score"]).astype(str)
ffp["same_winner"] = ffp["match_id"].map(apre["winner"]) == ffp["match_id_o"].map(apre["winner"])
ffp["same_round"] = ffp["match_id"].map(a["round"]) == ffp["match_id_o"].map(a["round"])
ffp["gapcls"] = np.select([ffp["same_event"], ffp["gap"].eq(0), ffp["gap"] <= 3, ffp["gap"].between(4, 10)],
                          ["same event", "same week, other event", "1-3 days", "4-10 days"], "other")
OUT["baseline_frozen_frozen_pre_holdout"] = ffp.groupby(["gapcls", "same_venue"]).agg(
    pairs=("match_id", "size"), same_round=("same_round", "sum"), same_score=("same_score", "sum"),
    same_winner=("same_winner", "sum")).reset_index().to_dict("records")
OUT["baseline_frozen_frozen_holdout_count"] = int((~ff["both_pre"]).sum())

# ---------------------------------------------------------------- a player twice in one round / one week
pl = pd.concat([m[["match_id", "new", "tournament_id", "td", "round", "bucket"]].assign(pid=m["player_a_id"]),
                m[["match_id", "new", "tournament_id", "td", "round", "bucket"]].assign(pid=m["player_b_id"])])
pl = pl[pl["round"].ne("RR")]
g = pl.groupby(["pid", "tournament_id", "td", "round"])["new"].agg(["size", "any", "all"])
OUT["player_twice_same_round_event_with_new"] = int(((g["size"] > 1) & g["any"]).sum())
OUT["player_twice_same_round_event_frozen_only"] = int(((g["size"] > 1) & ~g["any"]).sum())
(AUD / "a2_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:30000])
