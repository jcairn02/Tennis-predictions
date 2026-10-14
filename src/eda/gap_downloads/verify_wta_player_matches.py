"""Check the WTA API's player-matches results (work package P2(b) of docs/studies/gap_downloads/collection-plan.md)
against the other copies of the same matches.

The results: data/dump/points/wta/player_results/<year>.parquet (src/ingest/point_sources/wta.py --player-matches), one
row per played singles match with the winner first.

1. **The Kaggle copy** (version 29, to the editions of 7 Sep 2026), the same website read earlier. Each of its played
   singles matches at the year's ITF editions is looked for among the results by edition (tournament group and start
   date), draw, round and the two players' ids, and its winner and score are compared. This measures how much of the
   year the crawl reached, and checks the staging's winner rule on matches the crawl did not choose.
2. **TennisLive's event listings** (work package P4, to 4 Oct 2026) and 3. **the ITF's live-data API** (P1, from 15 Sep
   2026). Each women's ITF singles match they hold at an edition whose week starts after the cut (default 7 Sep 2026,
   the Kaggle copy's last ITF start) is looked up among the results with verify_tennislive.check: the results stand in
   for its official rows, dated by their edition's Monday. Its verdicts apply; "no official row" here means the results
   lack the match. Read the other way round, the matches found say how many of the results each source confirms.

Writes data/studies/gap_downloads/wta_player_matches_check.json and wta_player_matches_check.csv.gz (every TennisLive
and ITF-live match from the cut on, with its verdict and the result it was matched to).

Usage: ./python.sh src/eda/gap_downloads/verify_wta_player_matches.py [--year 2026] [--since 2026-09-07]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M                          # noqa: E402
from src.eda.gap_downloads import verify_tennislive as T           # noqa: E402
from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import wta as W                      # noqa: E402

STUDY = PROJECT_ROOT / "data" / "studies" / "gap_downloads"
ITF_LIVE = P.DUMP_ROOT / "itf_live"


def results(year: int) -> pd.DataFrame:
    r = pd.read_parquet(P.dump_path(W.SOURCE, "player_results", f"{year}.parquet"))
    r["d"] = pd.to_datetime(r["start_date"], errors="coerce")
    return r


def same_score(a, b) -> bool:
    return " ".join(str(a or "").split()) == " ".join(str(b or "").split())


# 1. the Kaggle copy -------------------------------------------------------------------
def kaggle_matches(year: int) -> pd.DataFrame:
    """The copy's played singles matches at the year's ITF editions, once each, with the winner's id."""
    folder = W.kaggle_folder()
    t = pd.read_csv(folder / "tournaments.csv", low_memory=False,
                    usecols=["pseudo_tournament_id", "startDate", "level", "tournamentGroupId"])
    t = t[t["level"].eq("ITF") & t["startDate"].astype(str).str.startswith(str(year))
          & t["tournamentGroupId"].notna()]
    cols = ["pseudo_tournament_id", "player_1", "player_2", "winner", "reason_code", "qpm_flag", "round_name", "scores"]
    m = pd.concat([c[c["pseudo_tournament_id"].isin(set(t["pseudo_tournament_id"]))] for c in
                   pd.read_csv(folder / "matches.csv", usecols=cols, chunksize=500_000, low_memory=False)])
    m = m.merge(t, on="pseudo_tournament_id")
    a = pd.to_numeric(m["player_1"], errors="coerce")
    b = pd.to_numeric(m["player_2"], errors="coerce")
    played = (~m["reason_code"].isin(list(W.NOT_PLAYED)) & m["winner"].astype(str).isin(["1", "2"])
              & a.notna() & b.notna())
    m, a, b = m[played].copy(), a[played].astype("int64").astype(str), b[played].astype("int64").astype(str)
    m["winner_id"] = np.where(m["winner"].astype(str).eq("1"), a, b)
    m["key"] = (m["tournamentGroupId"].astype("int64").astype(str) + "|" + m["startDate"].astype(str).str[:10] + "|"
                + m["qpm_flag"].astype(str) + "|" + m["round_name"].astype(str) + "|"
                + np.where(a <= b, a, b) + "|" + np.where(a <= b, b, a))
    m["kaggle_rows"] = m.groupby("key")["key"].transform("size")
    m["kaggle_winners"] = m.groupby("key")["winner_id"].transform("nunique")
    return m.drop_duplicates("key")


def result_keys(r: pd.DataFrame) -> pd.Series:
    a, b = r["winner_id"].fillna("").astype(str), r["loser_id"].fillna("").astype(str)
    key = (r["tournament_group_id"].astype(str) + "|" + r["start_date"].astype(str).str[:10] + "|"
           + r["qpm_flag"].astype(str) + "|" + r["round_name"].astype(str) + "|"
           + np.where(a <= b, a, b) + "|" + np.where(a <= b, b, a))
    return key.where((a != "") & (b != ""), None)


def check_kaggle(r: pd.DataFrame, year: int) -> dict:
    k = kaggle_matches(year)
    api = r[r["level"].eq("ITF")].assign(key=result_keys).dropna(subset=["key"]).drop_duplicates("key")
    j = k.merge(api[["key", "winner_id", "scores"]].rename(columns={"winner_id": "api_winner", "scores": "api_scores"}),
                on="key", how="left")
    found = j["api_winner"].notna()
    by_month = {}
    for month, g in j.groupby(j["startDate"].astype(str).str[:7]):
        by_month[month] = {"kaggle": int(len(g)), "found": int(g["api_winner"].notna().sum())}
    # the other way: results the copy lacks (a player's records in the copy can end months before its 24 Sep date)
    new = api[~api["key"].isin(set(k["key"]))]
    for month, g in new.groupby(new["start_date"].astype(str).str[:7]):
        by_month.setdefault(month, {"kaggle": 0, "found": 0})["results_not_in_kaggle"] = {
            d: int(n) for d, n in g["qpm_flag"].value_counts().items()}
    return {"kaggle_folder": P.rel(W.kaggle_folder()), "kaggle_matches": int(len(k)),
            "kaggle_matches_listed_with_two_winners": int((k["kaggle_winners"] > 1).sum()),
            "found_in_results": int(found.sum()), "share_found": round(float(found.mean()), 4) if len(j) else None,
            "itf_results_with_both_ids": int(len(api)), "itf_results_not_in_kaggle": int(len(new)),
            "found_by_draw": {d: {"kaggle": int(len(g)), "found": int(g["api_winner"].notna().sum())}
                              for d, g in j.groupby("qpm_flag")},
            "found_by_month": by_month,
            "same_winner": int((found & j["api_winner"].eq(j["winner_id"])).sum()),
            "different_winner": int((found & j["api_winner"].ne(j["winner_id"])).sum()),
            "same_score": int((found & np.array([same_score(x, y) for x, y in zip(j["scores"], j["api_scores"])],
                                                dtype=bool)).sum()),
            "different_winner_examples": j[found & j["api_winner"].ne(j["winner_id"])][
                ["key", "winner_id", "api_winner", "scores", "api_scores"]].head(10).to_dict("records")}


# 2-3. TennisLive and the ITF's live-data API --------------------------------------------
def as_official(r: pd.DataFrame) -> pd.DataFrame:
    """The ITF results in verify_tennislive's official-row columns; `official` carries the result's match key."""
    itf = r[r["level"].eq("ITF")].copy()
    itf["pseudo_tournament_id"] = itf["tournament_group_id"].astype(str) + "|" + itf["start_date"].astype(str)
    out = pd.DataFrame({
        "tour": "W", "draw": np.where(itf["qpm_flag"].eq("Q"), "qual", "main"), "d": itf["d"],
        "tourney_name": itf["title"], "winner_name": itf["winner_name"], "loser_name": itf["loser_name"],
        "kw": itf["winner_name"].map(M.surname_key),
        "score": itf["scores"].fillna("").astype(str) + np.where(itf["reason_code"].eq("R"), " RET", ""),
        "official": itf["match_key"], "round": M.wta_site_rounds(itf)})
    out["pair"] = M.pair_key(out["kw"], itf["loser_name"].map(M.surname_key))
    return out.dropna(subset=["pair", "d"])


def tennislive_rows(since: str) -> pd.DataFrame:
    """TennisLive's played women's ITF singles at events whose last week starts after ``since``."""
    li = T.listed_rows()
    ev = pd.read_parquet(P.DUMP_ROOT / "tennislive" / "events.parquet", columns=["key", "last_week"])
    li = li.merge(ev.rename(columns={"key": "event_key"}), on="event_key", how="left")
    return li[li["tour"].eq("W") & li["event_kind"].eq("itf") & (li["last_week"].astype(str) > since)].copy()


def itf_live_sets(s1, s2) -> str:
    """'1:6/0 2:7/5' and '1:2/0 2:6/7' -> '6-2 7-6' (side 1 first; tiebreak points left aside)."""
    def games(text):
        return {int(n): g.split("/")[0] for n, g in (part.split(":") for part in str(text or "").split() if ":" in part)}
    a, b = games(s1), games(s2)
    return " ".join(f"{a[n]}-{b.get(n, '0')}" for n in sorted(a))


def itf_live_rows(since: str) -> pd.DataFrame:
    """The ITF's women's singles that ended with a result, latest capture, at editions whose main draw starts after
    ``since``, in verify_tennislive's listed-row columns."""
    m = pd.read_parquet(ITF_LIVE / "matches.parquet")
    m = m[m["discipline"].eq("Women Singles") & m["latest"].eq("TRUE")].drop_duplicates("match_id")
    m = m[m["status"].str.upper().isin(["COMPLETE", "RETIREMENT"]) & m["winner_side_order"].isin(["1", "2"])]
    ev = pd.read_parquet(ITF_LIVE / "events.parquet", columns=["event_key", "main_draw_week"])
    m = m.merge(ev, on="event_key", how="left")
    week = pd.to_datetime(m["main_draw_week"].astype(str) + "-1", format="%G-W%V-%u", errors="coerce")
    m = m[week > pd.Timestamp(since)].copy()
    day = pd.to_datetime(m["actual_start_date"].astype(str).str[:10], errors="coerce").fillna(
        pd.to_datetime(m["list_date"].astype(str).str[:10], errors="coerce"))
    out = pd.DataFrame({
        "event_key": m["event_key"], "event_name": m["event_name"], "event_kind": "itf", "tour": "W",
        "match_id": m["match_id"], "draw": np.where(m["draw"].eq("Qualifying Draw"), "qual", "main"),
        # qualifying rounds are named by the draw's size (R64, R32, R16), which the map's canon_round would read as
        # main-draw rounds; numbering them Q1.. would need the event's first round, which a capture can miss. Unset,
        # the round does not filter (pair, draw and the event's week still do).
        "round": m["round"].where(m["draw"].ne("Qualifying Draw"), None), "day": day,
        "winner_side": m["winner_side_order"],
        "score": [itf_live_sets(a, b) for a, b in zip(m["side1_sets"], m["side2_sets"])],
        "player1_name": m["side1_players"], "player2_name": m["side2_players"],
        "end_reason": np.where(m["status"].str.upper().eq("RETIREMENT"), "retired", "")})
    out["k1"], out["k2"] = out["player1_name"].map(M.surname_key), out["player2_name"].map(M.surname_key)
    out["pair"] = M.pair_key(out["k1"], out["k2"])
    out["year"] = out["day"].dt.year
    return out


def counts(frame: pd.DataFrame) -> dict:
    return {str(k): int(v) for k, v in frame["verdict"].value_counts().items()}


def against(name: str, listed: pd.DataFrame, official: pd.DataFrame, since: str) -> tuple[dict, pd.DataFrame]:
    out = T.check(listed, official)
    out["verdict"] = out["verdict"].replace({"no official row": "not in the results"})
    later = official[official["d"] > pd.Timestamp(since)]
    confirmed = set(out["official"].dropna())
    return ({"matches": int(len(out)), "verdicts": counts(out),
             "by_draw": {d: counts(g) for d, g in out.groupby("draw")},
             "by_week": {str(w)[:10]: counts(g) for w, g in out.groupby(out["day"].dt.to_period("W-SUN").dt.start_time)},
             "results_after_cut": int(len(later)),
             "results_after_cut_confirmed": int(later["official"].isin(confirmed).sum())},
            out.assign(source=name))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--since", default="2026-09-07", help="the cut: editions starting after it are checked")
    a = ap.parse_args()
    r = results(a.year)
    official = as_official(r)
    report = {"generated_at": P.utc_now_iso(), "results_file": P.rel(P.dump_path(W.SOURCE, "player_results",
                                                                                  f"{a.year}.parquet")),
              "results": int(len(r)), "itf_results": int(r["level"].eq("ITF").sum()), "since": a.since,
              "kaggle": check_kaggle(r, a.year)}
    frames = []
    for name, rows in (("tennislive", tennislive_rows(a.since)), ("itf_live", itf_live_rows(a.since))):
        report[name], frame = against(name, rows, official, a.since)
        frames.append(frame)
    keep = ["source", "event_key", "event_name", "match_id", "draw", "round", "day", "player1_name", "player2_name",
            "winner_side", "score", "verdict", "official", "official_score", "winner_name"]
    table = pd.concat([f.reindex(columns=keep) for f in frames], ignore_index=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    table.to_csv(STUDY / "wta_player_matches_check.csv.gz", index=False, compression="gzip")
    (STUDY / "wta_player_matches_check.json").write_text(json.dumps(report, indent=1, default=str) + "\n",
                                                         encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "kaggle"} | {"kaggle": {
        k: v for k, v in report["kaggle"].items() if k not in ("different_winner_examples", "found_by_month")}},
        indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
