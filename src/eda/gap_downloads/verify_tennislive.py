"""Check TennisLive's event listings against the official results: does each listed match have the winner and set
scores of the result file that holds it?

Every played singles match of data/dump/points/tennislive/listed.parquet (src/ingest/point_sources/tennislive_events.py)
is looked up in the result files the map is built from (Tennis My Life, then Sackmann: verify_links.RESULT_FILES):
the same tour, the same pair of surnames (the map's key) with first names that agree (the map's same_first_name),
the same draw (qualifying or main) and round (where both name one), and the official row
dated inside the event's own span (the file's date is its tournament's Monday, or the day played: 3 days before the
day played to 8 days after it, 14 at a two-week 1000, and three weeks either way at a Slam, whose qualifying one file
can date weeks apart); the nearest such row is taken. The listed match's winner and games per set are then compared
with it (tiebreak points are left aside). A wider window would let the same pair's meeting at a weekly venue's
previous edition stand in for a match the files lack.

Verdicts:
    agrees                     same winner, same games in every set (at a retirement, all but the unfinished set, and
                               without the unstarted 0-0 set the files write)
    winner agrees, official score written loser first
                               the official row's games are the listed ones turned round (Tennis My Life's WTA Rome
                               2026 rows, for one)
    winner agrees, no listed score
    winner agrees, score differs
    winner differs             a wrong link, or a result recorded differently
    no official row            no result file holds the match: men's ITF qualifying (no file lists it), ITF matches
                               after the files end (June 2026), and events or names the files miss

Writes data/studies/gap_downloads/tennislive_link_check.json (counts by tour, kind, year and draw) and
tennislive_link_check.csv.gz (one row per listed match whose winner or score differs from its official row; the
agreeing and unmatched ones, about a million, are only counted, to keep the evidence small).

Usage: ./python.sh src/eda/gap_downloads/verify_tennislive.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M                          # noqa: E402
from src.eda.gap_downloads import verify_links as V                # noqa: E402
from src.ingest.point_sources import common as P                   # noqa: E402

LISTED = P.DUMP_ROOT / "tennislive" / "listed.parquet"
STUDY = PROJECT_ROOT / "data" / "studies" / "gap_downloads"
WINDOWS = {"slam": (-21, 21), "tour": (-3, 14), "finals": (-3, 8)}     # days from the file's date to the day played
WINDOW = (-3, 8)                                                       # every other kind: one week


def official_rows() -> pd.DataFrame:
    """Every result file's rows from 2018 on, with the tour, the draw and the surname pair; Tennis My Life's first."""
    cols = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]
    frames = []
    for source, pattern in V.RESULT_FILES:
        for path in sorted(V.RESULTS.glob(pattern)):
            year = M._year_of(path)
            if year is not None and year < M.FIRST_YEAR:
                continue
            tour = "W" if "wta" in path.as_posix().lower() else "M"
            frames.append(pd.read_parquet(path, columns=cols).assign(official=source, tour=tour,
                                                                     qual_file=path.parent.name == "atp_qualifying"))
    rows = pd.concat(frames, ignore_index=True)
    rows["d"] = M.to_date(rows["tourney_date"].astype(str).str[:8], "%Y%m%d")
    rows["draw"] = np.where(rows["qual_file"] | M.is_qual_round(rows["round"]), "qual", "main")
    rows["kw"], rows["kl"] = rows["winner_name"].map(M.surname_key), rows["loser_name"].map(M.surname_key)
    rows["pair"] = M.pair_key(rows["kw"], rows["kl"])
    rows = rows.dropna(subset=["pair", "d"])
    return rows.drop_duplicates(["tour", "tourney_name", "d", "pair", "draw"])


def listed_rows(path: Path = LISTED) -> pd.DataFrame:
    cols = ["event_key", "event_name", "event_kind", "tour", "discipline", "junior", "played", "match_id", "url",
            "draw", "round", "start_utc", "winner_side", "score", "player1_name", "player2_name", "end_reason"]
    li = pd.read_parquet(path, columns=cols)
    li = li[li["discipline"].eq("singles") & li["played"].eq("TRUE") & ~li["junior"].eq("TRUE")]
    li = li.drop_duplicates(["event_key", "match_id"]).copy()
    li["tour"] = li["tour"].map({"atp": "M", "wta": "W"})
    li["draw"] = np.where(li["draw"].eq("qualifying"), "qual", "main")
    li["day"] = pd.to_datetime(li["start_utc"].str[:10], errors="coerce")
    li["k1"], li["k2"] = li["player1_name"].map(M.surname_key), li["player2_name"].map(M.surname_key)
    li["pair"] = M.pair_key(li["k1"], li["k2"])
    li["year"] = li["day"].dt.year
    return li


def official_sets(score) -> list[tuple[int, int]]:
    """verify_links.tml_sets, with a match tiebreak written in brackets read as a set: '4-6 7-5 [10-5] ' ->
    [(4, 6), (7, 5), (10, 5)] (the files bracket it; TennisLive writes it as a set)."""
    return V.tml_sets(" ".join(t.strip("[]") for t in str(score or "").split()))


def listed_sets(score, winner_side) -> list[tuple[int, int]]:
    """'7-6(6) 1-6 6-3' with player 1 first -> games per set with the winner first."""
    sets = [(int(a), int(b)) for a, b in (s.split("(")[0].split("-") for s in str(score or "").split() if "-" in s)
            if a.isdigit() and b.isdigit()]
    return [(b, a) for a, b in sets] if str(winner_side) == "2" else sets


def verdict(row) -> str:
    if pd.isna(row["official"]):
        return "no official row"
    side = str(row["winner_side"])
    winner_key = row["k1"] if side == "1" else row["k2"] if side == "2" else None
    if winner_key is None or winner_key != row["kw"]:
        return "winner differs"
    ours, theirs = listed_sets(row["score"], side), official_sets(row["official_score"])
    if not ours:
        return "winner agrees, no listed score"
    retired = "RET" in str(row["official_score"] or "").upper() or str(row["end_reason"]).lower() == "retired"
    if retired:
        while theirs and theirs[-1] == (0, 0):          # the set never started
            theirs = theirs[:-1]
    if ours == theirs or (retired and len(ours) == len(theirs) and ours[:-1] == theirs[:-1]) or \
            (retired and ours[:len(theirs)] == theirs and len(ours) == len(theirs) + 1):
        return "agrees"
    if theirs and [(b, a) for a, b in theirs] == ours:
        return "winner agrees, official score written loser first"
    return "winner agrees, score differs"


def check(listed: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Each listed match with its nearest official row (same tour, pair and draw, inside the window) and the verdict."""
    cand = listed[["match_id", "event_key", "event_kind", "tour", "pair", "draw", "day", "player1_name", "player2_name",
                   "k1", "round"]].dropna(subset=["pair", "day"]).merge(
        official[["tour", "pair", "draw", "d", "tourney_name", "winner_name", "loser_name", "kw", "score", "official",
                  "round"]].rename(columns={"score": "official_score", "round": "official_round"}),
        on=["tour", "pair", "draw"])
    delta = (cand["day"] - cand["d"]).dt.days
    lo = cand["event_kind"].map(lambda k: WINDOWS.get(k, WINDOW)[0])
    hi = cand["event_kind"].map(lambda k: WINDOWS.get(k, WINDOW)[1])
    cand = cand[(delta >= lo) & (delta <= hi)].copy()
    # the same pair can meet at two events a week apart: where both name the round, it must be the same
    ours, theirs = cand["round"].map(M.canon_round), cand["official_round"].map(M.canon_round)
    cand = cand[ours.isna() | theirs.isna() | ours.eq(theirs)].copy()
    # the same surnames are not enough: brothers (Cerundolo) and namesakes (Wang) meet the same opponents
    first_is_winner = cand["k1"].eq(cand["kw"])
    as_winner = cand["player1_name"].where(first_is_winner, cand["player2_name"])
    as_loser = cand["player2_name"].where(first_is_winner, cand["player1_name"])
    same = [M.same_first_name(a, b) and M.same_first_name(c, e)
            for a, b, c, e in zip(as_winner, cand["winner_name"], as_loser, cand["loser_name"])]
    cand = cand[pd.Series(same, index=cand.index, dtype=bool)].assign(
        gap=lambda f: ((f["day"] - f["d"]).dt.days - 3).abs())
    cand = cand.drop(columns=["event_kind", "player1_name", "player2_name", "k1", "loser_name", "round"])
    best = cand.sort_values(["match_id", "gap"]).drop_duplicates(["event_key", "match_id"])
    out = listed.merge(best.drop(columns=["tour", "pair", "draw", "day", "gap"]), on=["event_key", "match_id"],
                       how="left")
    out["verdict"] = out.apply(verdict, axis=1)
    return out


def summarize(frame: pd.DataFrame) -> dict:
    def counts(g):
        return {str(k): int(v) for k, v in g["verdict"].value_counts().items()}

    with_row = frame[frame["official"].notna()]
    return {"generated_at": P.utc_now_iso(), "listed_played_singles": int(len(frame)), "verdicts": counts(frame),
            "with_an_official_row": counts(with_row),
            "by_tour_kind_draw": {f"{t}|{k}|{d}": counts(g) for (t, k, d), g in
                                  frame.groupby(["tour", "event_kind", "draw"])},
            "by_tour_kind_year": {f"{t}|{k}|{int(y)}": counts(g) for (t, k, y), g in
                                  frame.dropna(subset=["year"]).groupby(["tour", "event_kind", "year"])},
            "by_official_file": {str(k): counts(g) for k, g in frame.groupby(frame["official"].fillna("none"))}}


def main() -> int:
    P.configure_stdout()
    frame = check(listed_rows(), official_rows())
    summary = summarize(frame)
    cols = ["event_key", "event_name", "event_kind", "tour", "draw", "round", "year", "day", "match_id", "url",
            "player1_name", "player2_name", "winner_side", "score", "end_reason", "official", "tourney_name", "d",
            "winner_name", "official_score", "verdict"]
    STUDY.mkdir(parents=True, exist_ok=True)
    differ = frame[frame["verdict"].str.startswith("winner")]
    differ[cols].sort_values(["day", "event_key", "match_id"]).to_csv(STUDY / "tennislive_link_check.csv.gz", index=False)
    (STUDY / "tennislive_link_check.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("listed_played_singles", "verdicts", "with_an_official_row")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
