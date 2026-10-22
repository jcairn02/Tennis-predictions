"""Tennis My Life's misdated and lumped editions, 2018-2026: what other sources say, and what Stage 0, the leak-proof
clock and the data map do with them (P6 data issues; a read-only investigation, 14 Oct 2026).

Question
    Tennis My Life (TML) dates some editions in the wrong week (Nottingham 2025, id 2025-2907: dated 7 July, played
    6-12 January) and gives several consecutive Challengers at one venue one name and date (six "Biella 1" of 2021).
    Which editions, 2018-2026? What date does Stage 0 hold for their matches, does the clock's window hold the day each
    match was played, and how many does the data map hold twice?

Evidence (read-only)
    * TML's staged files (data/dump/matches/tennis_my_life/: atp_main, atp_challenger, atp_qualifying, wta_main, ongoing).
    * Sackmann's staged files (data/dump/matches/sackmann_archive/): his tournament date and name for the same match.
    * TennisLive's event listings (data/dump/points/tennislive/listed.parquet): the day each match was listed as played.
    * SofaScore's events (data/dump/points/sofascore_editions/events.parquet, data/dump/points/sofascore/events.parquet):
      each match's start (UTC).
    * TDI's 2026 match ids (data/dump/points/tdi/match_ids.parquet): the day of a 2026 men's match (no score: linked by the
      players and the round, within 60 days).
    A TML row links to another source's row by the two players (surname keys; a second pass allows one name written
    differently, as the data map's linker does) AND identical set scores, within WINDOW days; the same draw and round
    first, then the nearest date; each row of the other source serves one TML row. A third pass (Sackmann only) takes,
    for a row the score could not link (walkovers, retirements written otherwise), the row of the same round and one
    surname in the Sackmann event its edition's other rows link to.

Verdicts
    * An edition is TML's tour, tournament id and name (Stage 0's event key); its TML date is its main draw's first date,
      as Stage 0's rule C05 sets it.
    * A row's play day is TennisLive's and SofaScore's day (read as +-1 day: a listing day, a UTC day), else TDI's; none
      where they disagree by more than CONFLICT days.
    * Each round's typical day is measured from Sackmann's dates (median of play day - his tournament date, by round and
      kind of event: round_offsets.csv); a row's play day minus it is the start that row implies.
    * The edition's true start: the Monday nearest the median start its rows imply; Sackmann's most common date instead
      where at least half his linked rows carry it and it lies within AGREE days of the play days' start (or no row has a
      play day). Its span: the play days of the rows supporting that start.
    * The date error of the edition (TML's date against the truth):
        another week (misdated): before the span's first day - 3 (earlier than any qualifying), or after its last day + 1
            and more than WRONG_DAYS late; "unresolved" when fewer than MIN_ROWS rows support the true start;
        dated by its last days: more than 2 days after the true start and in the later half of the span (TML dates many
            Challengers of 2018-2024 by the final's day);
        dated by day: as above, but the rows carry three or more TML dates (2026's two-week events);
        right: otherwise.
    * Lumped: one tour, season, name and date carried by two or more tournament ids (team-event rubbers aside); a lump
      holding a misdated member is a true lump, one without is two consecutive editions (the first dated by its closing
      Sunday, the second by its opening one) under one name.
    * Rows dated apart: an edition not misdated with MIN_ROWS rows or more played in another week than its true start
      (the 2021 Australian Open's qualifying, played in Doha and Dubai four weeks before the main draw).
    * A row's true start: its own Sackmann date where that agrees with its own play day (and the play day with its
      edition or draw); else its draw's Sackmann date or play days (MIN_ROWS rows); else the edition's. Its true play
      days are its own where they agree with that start, else the window of an ordinary edition of its kind. A Sackmann
      twin that agrees with neither is set aside (the pair's other meeting, same score, where Sackmann lacks this one).
    * A row is resolved when its edition's true start is supported by MIN_ROWS rows.

Then, for every TML row (the outputs keep those of flagged editions, except the correction table, the clock's misses
and the map's doubles, which cover every row):
    * Stage 0 (data/studies/predictability_diagnostic/stage0_matches.parquet): the row it keeps (Sackmann's twin or the
      TML row itself, found by source file and row), its date, and whether that is more than WRONG_DAYS from the truth.
    * The clock (data/studies/match_timing/timing.parquet; days since 1970): es and lf against the true play days. lf
      before the play day lets the result count before it happened (a leak); es after it lets the match's own inputs read
      results of later days.
    * The data map (data/studies/data_map/matches.parquet): the TML copy (created by 'tml' at TML's date) and Sackmann's
      own copy (created by 'sackmann' at his date), which exists only where the map failed to link his row to TML's; for
      a row without a Sackmann twin, a copy another source created near the truth.
    * Where a window ends before the play day, the later matches of either player that read the result too early.

Writes data/studies/p6_data_issues/tml_misdates/ (nothing else is written):
    editions.csv               every TML edition of 2018-2026 with its evidence and verdict
    misdated_editions.csv      the flagged editions: TML's id, name and date; true dates and names; evidence; counts
    misdated_matches.csv.gz    every row of those editions: twins, play days, Stage 0 row, the clock's window, map copies
    stage0_date_corrections.csv  candidate correction table: Stage 0 rows dated more than WRONG_DAYS from the truth
    clock_windows.csv          the clock's windows that end before the play day or start after it
    clock_leak_readers.csv     the later matches that read a leaking result before it happened (same player)
    map_doubles.csv            the map's second copies of these matches
    stage0_tml_only_check.csv  every TML-only Stage 0 row whose date is more than WRONG_DAYS from its truth
    stage0_duplicates.csv      TML rows Stage 0 keeps besides their Sackmann twin (the match held twice)
    tml_edition_date_corrections.csv  candidate edition-level dates: each misdated edition (and the draw played apart)
                               with its true start, for the map's TML rows and Stage 0's TML-only rows
    round_offsets.csv          the typical day of each round (from Sackmann's dates)
    summary.json               the counts

Run: ./python.sh src/eda/p6_data_issues/tml_misdates.py      (under a minute)
"""
from __future__ import annotations

import glob
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.data_map import measure as M  # noqa: E402  (name keys, rounds, levels; read-only helpers)

DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "p6_data_issues" / "tml_misdates"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"

FIRST_DATE = pd.Timestamp("2017-12-01")   # TML rows of the 2018 season on (its first week can start in December)
WINDOW = 400          # days a twin may lie from the TML row's date
CONFLICT = 3          # TennisLive's and SofaScore's days further apart than this: no play day for the row
MIN_ROWS = 3          # rows an edition needs for a verdict, and rows played in another week for "rows dated apart"
AGREE = 3             # Sackmann's date within this many days of the play days' start: his date is the true start
WRONG_DAYS = 7        # a date further than this from the true start is wrong (the brief's threshold)
TRUST = 7             # a row's implied start within this of its edition's (or its Sackmann date's): its play day counts
# play day - true start, for every round of an ordinary week (qualifying from the Friday, a final delayed to Monday),
# and of a two-week event (Slams with their qualifying, 1000s of 96, team events)
PLAY_WINDOW = {"week": (-4, 9), "fortnight": (-9, 15)}
EPOCH = pd.Timestamp("1970-01-01")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Scores, names, dates

SET = re.compile(r"(\d+)-(\d+)")


def sig_of(score) -> str:
    """The set scores without who won each set or the tiebreak points: '6-4 3-6 7-6(5)' -> '6-4;6-3;7-6'. Blank for a
    walkover or an unreadable score. Two sources agree on a match when its two players and this signature agree."""
    s = re.sub(r"\(\d+\)", "", str(score or ""))
    sets = [tuple(sorted((int(a), int(b)), reverse=True)) for a, b in SET.findall(s)]
    return ";".join(f"{a}-{b}" for a, b in sets)


def sig_sets(home: pd.DataFrame, away: pd.DataFrame) -> pd.Series:
    """The same signature from per-set columns (SofaScore's home_setN / away_setN)."""
    out = np.full(len(home), "", dtype=object)
    for i in range(home.shape[1]):
        h = pd.to_numeric(home.iloc[:, i], errors="coerce").to_numpy()
        a = pd.to_numeric(away.iloc[:, i], errors="coerce").to_numpy()
        ok = ~np.isnan(h) & ~np.isnan(a)
        hi = np.where(ok, np.fmax(h, a), 0).astype(int).astype(str)
        lo = np.where(ok, np.fmin(h, a), 0).astype(int).astype(str)
        part = np.where(ok, np.char.add(np.char.add(hi, "-"), lo), "")
        out = np.where(ok & (out != ""), out + ";" + part, np.where(ok, part, out))
    return pd.Series(out, index=home.index)


def draw_of(rounds: pd.Series) -> pd.Series:
    return pd.Series(np.where(M.is_qual_round(rounds), "qual", "main"), index=rounds.index)


def prep(df: pd.DataFrame, n1: str, n2: str) -> pd.DataFrame:
    """Surname keys and the pair key, as the data map makes them."""
    df["n1"], df["n2"] = df[n1].fillna("").astype(str), df[n2].fillna("").astype(str)
    df["k1"], df["k2"] = df["n1"].map(M.surname_key), df["n2"].map(M.surname_key)
    df["pair"] = M.pair_key(df["k1"], df["k2"])
    return df


def nearest_monday(d: pd.Series) -> pd.Series:
    """The timing study's anchor rule: Tue -1, Wed -2, Thu -3, Fri +3, Sat +2, Sun +1."""
    shift = d.dt.weekday.map({0: 0, 1: -1, 2: -2, 3: -3, 4: 3, 5: 2, 6: 1})
    return d + pd.to_timedelta(shift, unit="D")


def to_days(d: pd.Series) -> pd.Series:
    return (pd.to_datetime(d) - EPOCH).dt.days


def window_kind(level: pd.Series, draw_size: pd.Series) -> pd.Series:
    big = pd.to_numeric(draw_size, errors="coerce").fillna(0) >= 96
    two = level.isin(["GS", "GSQ", "TEAM"]) | (level.isin(["T1000", "TQ"]) & big)
    return pd.Series(np.where(two, "fortnight", "week"), index=level.index)


def calib_kind(level: pd.Series, draw_size: pd.Series) -> pd.Series:
    """The kind of event a round's typical day is measured on: Slams (qualifying a week before), 96-draw 1000s,
    team events, and ordinary weeks."""
    big = pd.to_numeric(draw_size, errors="coerce").fillna(0) >= 96
    return pd.Series(np.select([level.isin(["GS", "GSQ"]), level.isin(["T1000", "TQ"]) & big, level.eq("TEAM")],
                               ["slam", "big", "team"], "week"), index=level.index)


def joined(s: pd.Series) -> str:
    return ";".join(sorted(set(s.dropna().astype(str))))


# ------------------------------------------------------------------------------------------------
# Loaders

TML_COLS = ["tourney_id", "tourney_name", "tourney_date", "tourney_level", "round", "winner_name", "loser_name", "score",
            "draw_size", "_source_file", "_row"]
TML_GROUPS = [("atp", "atp_challenger", "tennis_my_life/atp_challenger/*_challenger.parquet"),
              ("atp", "atp_main", "tennis_my_life/atp_main/[0-9]*.parquet"),
              ("atp", "atp_qualifying", "tennis_my_life/atp_qualifying/*_atp_quali.parquet"),
              ("wta", "wta_main", "tennis_my_life/wta_main/*_wta.parquet"),
              ("atp", "atp_ongoing", "tennis_my_life/ongoing/ongoing_tourneys.parquet"),
              ("atp", "atp_challenger_ongoing", "tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet"),
              ("wta", "wta_ongoing", "tennis_my_life/ongoing/wta_ongoing_tourneys.parquet")]
SACK_GROUPS = [("atp", "sackmann_archive/atp/atp_matches_[0-9]*.parquet"),
               ("atp", "sackmann_archive/atp/atp_matches_qual_chall_*.parquet"),
               ("wta", "sackmann_archive/wta/wta_matches_[0-9]*.parquet"),
               ("wta", "sackmann_archive/wta/wta_matches_qual_itf_*.parquet")]


def file_year(path: str) -> int | None:
    m = re.search(r"(\d{4})", Path(path).name)
    return int(m.group(1)) if m else None


def read_group(pattern: str, columns: list[str], first_year: int) -> list[pd.DataFrame]:
    frames = []
    for f in sorted(glob.glob(str(DUMP / "matches" / pattern))):
        y = file_year(f)
        if y is not None and y < first_year:
            continue
        have = set(pq.read_schema(f).names)
        frames.append(pd.read_parquet(f, columns=[c for c in columns if c in have]).reindex(columns=columns))
    return frames


def level_of(tour: str, code: str, name: str, rnd: str, group: str) -> str:
    """The data map's level code for a TML row, qualifying as the map files it."""
    lv = M.tour_level_atp(code, name) if tour == "atp" else M.tour_level_wta(code, name)
    if group == "atp_qualifying":
        return "GSQ" if code == "G" else "TQ"
    if re.match(r"^Q\d", rnd or ""):
        return M.to_qual(lv)
    return lv


def load_tml() -> pd.DataFrame:
    frames = []
    for tour, group, pattern in TML_GROUPS:
        for d in read_group(pattern, TML_COLS, 2018):
            d["tour"], d["group"] = tour, group
            frames.append(d)
    t = pd.concat(frames, ignore_index=True)
    for c in ["tourney_id", "tourney_name", "tourney_date", "tourney_level", "round", "winner_name", "loser_name", "score"]:
        t[c] = t[c].fillna("").astype(str).str.strip()
    t["round"] = t["round"].str.upper()
    t["date"] = pd.to_datetime(t["tourney_date"], format="%Y%m%d", errors="coerce")
    t = t[t["date"] >= FIRST_DATE].copy()
    t["draw"] = draw_of(t["round"])
    t["sig"] = t["score"].map(sig_of)
    t["level"] = [level_of(a, b, c, d, e) for a, b, c, d, e in
                  zip(t["tour"], t["tourney_level"], t["tourney_name"], t["round"], t["group"])]
    # the edition as Stage 0 keys it (tournament id and name), dated as its rule C05 dates it: the main draw's first date
    t["ekey"] = t["tour"] + "|" + t["tourney_id"] + "|" + t["tourney_name"]
    main_day = t[t["draw"].eq("main")].groupby("ekey")["date"].min()
    any_day = t.groupby("ekey")["date"].min()
    t["ed_date"] = t["ekey"].map(main_day).fillna(t["ekey"].map(any_day))
    far = (t["date"] - t["ed_date"]).dt.days.abs() > 21      # C05 leaves such rows alone: their own date
    t.loc[far, "ed_date"] = t.loc[far, "date"]
    t["edition"] = t["ekey"] + "|" + t["ed_date"].dt.strftime("%Y%m%d")
    t["season"] = pd.to_numeric(t["tourney_id"].str[:4], errors="coerce").fillna(t["date"].dt.year).astype(int)
    t = prep(t, "winner_name", "loser_name")
    t["lid"] = np.arange(len(t))
    t["rnd"] = t["round"].map(M.canon_round)
    return t.reset_index(drop=True)


def load_sackmann() -> pd.DataFrame:
    frames = []
    cols = ["tourney_id", "tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score", "_source_file",
            "_row"]
    for tour, pattern in SACK_GROUPS:
        for d in read_group(pattern, cols, 2017):
            d["tour"] = tour
            frames.append(d)
    s = pd.concat(frames, ignore_index=True)
    for c in ["tourney_id", "tourney_name", "tourney_date", "round", "score"]:
        s[c] = s[c].fillna("").astype(str).str.strip()
    s["round"] = s["round"].str.upper()
    s["day"] = pd.to_datetime(s["tourney_date"], format="%Y%m%d", errors="coerce")
    s["draw"] = draw_of(s["round"])
    s["sig"] = s["score"].map(sig_of)
    s["rnd"] = s["round"].map(M.canon_round)
    s = prep(s, "winner_name", "loser_name")
    return s[s["day"].notna()].reset_index(drop=True)


def load_tennislive() -> pd.DataFrame:
    cols = ["event_key", "event_name", "event_kind", "tour", "round", "draw", "discipline", "player1_name",
            "player2_name", "score", "start_utc"]
    t = pd.read_parquet(DUMP / "points" / "tennislive" / "listed.parquet", columns=cols)
    t = t[t["discipline"].eq("singles") & ~t["event_kind"].eq("itf")].copy()
    t["day"] = pd.to_datetime(t["start_utc"].astype(str).str[:10], errors="coerce")
    t["sig"] = t["score"].map(sig_of)
    t["rnd"] = t["round"].map(M.canon_round)
    t["draw"] = np.where(t["draw"].eq("qualifying"), "qual", "main")
    t = prep(t, "player1_name", "player2_name")
    return t[t["day"].notna()].reset_index(drop=True)


SS_COLS = (["event_id", "start_utc", "tournament_name", "category_name", "season_name", "round_name", "home_name",
            "away_name", "status_type", "doubles"] + [f"{s}_set{i}" for s in ("home", "away") for i in range(1, 6)])


def load_sofascore() -> pd.DataFrame:
    frames = []
    for name in ("sofascore_editions", "sofascore"):
        d = pd.read_parquet(DUMP / "points" / name / "events.parquet", columns=SS_COLS)
        d["ss_file"] = name
        frames.append(d)
    s = pd.concat(frames, ignore_index=True)
    s = s[~s["doubles"].astype(str).str.lower().isin(["true", "1"]) & s["status_type"].eq("finished")].copy()
    s["tour"] = s["category_name"].map({"ATP": "atp", "Challenger": "atp", "WTA": "wta", "WTA 125": "wta"})
    s = s[s["tour"].notna()].copy()
    s["day"] = pd.to_datetime(s["start_utc"].astype(str).str[:10], errors="coerce")
    s["sig"] = sig_sets(s[[f"home_set{i}" for i in range(1, 6)]], s[[f"away_set{i}" for i in range(1, 6)]])
    s["rnd"] = s["round_name"].map(M.canon_round)
    s["draw"] = np.where(s["round_name"].fillna("").str.lower().str.contains("qualif"), "qual", "main")
    s = prep(s, "home_name", "away_name")
    s = s.sort_values(["event_id", "ss_file"]).drop_duplicates("event_id")      # one event in both copies
    return s[s["day"].notna()].reset_index(drop=True)


TDI_ROUNDS = {"round of 128": "R128", "round of 64": "R64", "round of 32": "R32", "round of 16": "R16",
              "quarter-finals": "QF", "quarterfinals": "QF", "semi-finals": "SF", "semifinals": "SF", "final": "F",
              "finals": "F", "qualifying round 1": "Q1", "qualifying round 2": "Q2", "qualifying round 3": "Q3"}


def load_tdi() -> pd.DataFrame:
    d = pd.read_parquet(DUMP / "points" / "tdi" / "match_ids.parquet",
                        columns=["listing_day", "stamp_day", "round", "tournament", "draw_type", "team1_names",
                                 "team2_names"])
    d = d[d["draw_type"].eq("singles")].copy()
    d["day"] = pd.to_datetime(d["stamp_day"].fillna(d["listing_day"]), errors="coerce")
    d["rnd"] = d["round"].map(lambda r: TDI_ROUNDS.get(str(r).strip().lower(), M.canon_round(r)))
    d["draw"] = np.where(d["round"].fillna("").str.contains("Qualif"), "qual", "main")
    d["tour"], d["sig"] = "atp", ""
    d = prep(d, "team1_names", "team2_names")
    return d[d["day"].notna()].reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Linking

def _quality(c: pd.DataFrame) -> pd.DataFrame:
    c = c.copy()
    c["q_draw"] = (c["draw"] == c["draw_r"]).astype(int)
    c["q_rnd"] = (c["rnd"].notna() & (c["rnd"] == c["rnd_r"])).astype(int)
    c["agap"] = c["gap"].abs()
    return c


def _assign(cand: pd.DataFrame) -> pd.DataFrame:
    """One right row per left row and one left row per right row: the best candidate first (same draw, same round,
    nearest date), then the next best for rows that lost theirs."""
    order = ["q_draw", "q_rnd", "agap"]
    cand = cand.sort_values(["lid"] + order + ["rid"], ascending=[True, False, False, True, True])
    taken_l, taken_r, out = set(), set(), []
    for _ in range(4):
        c = cand[~cand["lid"].isin(taken_l) & ~cand["rid"].isin(taken_r)]
        if c.empty:
            break
        best = c.drop_duplicates("lid")
        best = best.sort_values(["rid"] + order + ["lid"], ascending=[True, False, False, True, True]).drop_duplicates("rid")
        out.append(best)
        taken_l |= set(best["lid"])
        taken_r |= set(best["rid"])
    return pd.concat(out, ignore_index=True) if out else cand.head(0)


def link(left: pd.DataFrame, right: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """The link of each left row (lid) to a right row (rid): lid, rid, gap (right day - left date, days), pass.
    Pass 1: same tour, surname-key pair and set-score signature. Pass 2, for the rest: the same signature, one surname
    key agreeing (with the first name), the other names passing the map's same_player."""
    L = left[left["sig"].ne("")][["lid", "tour", "pair", "k1", "k2", "n1", "n2", "sig", "date", "draw", "rnd"]]
    R = right[right["sig"].ne("")][["rid", "tour", "pair", "k1", "k2", "n1", "n2", "sig", "day", "draw", "rnd"]]
    c = L[L["pair"].notna()].merge(R[R["pair"].notna()], on=["tour", "pair", "sig"], suffixes=("", "_r"))
    c["gap"] = (c["day"] - c["date"]).dt.days
    c = c[c["gap"].abs() <= window].assign(**{"pass": 1})
    first = _assign(_quality(c))
    rest = L[~L["lid"].isin(first["lid"])]
    free = R[~R["rid"].isin(first["rid"])]
    parts = []
    for lk, lo, lown in (("k1", "n2", "n1"), ("k2", "n1", "n2")):
        a = rest[["lid", "tour", "sig", "date", "draw", "rnd", lk, lo, lown]].rename(
            columns={lk: "key", lo: "other", lown: "own"})
        for rk, ro, rown in (("k1", "n2", "n1"), ("k2", "n1", "n2")):
            b = free[["rid", "tour", "sig", "day", "draw", "rnd", rk, ro, rown]].rename(
                columns={rk: "key", ro: "uother", rown: "uown", "draw": "draw_r", "rnd": "rnd_r"})
            m = a[a["key"].ne("")].merge(b[b["key"].ne("")], on=["tour", "key", "sig"])
            m["gap"] = (m["day"] - m["date"]).dt.days
            parts.append(m[m["gap"].abs() <= window])
    c2 = pd.concat(parts, ignore_index=True)
    ok = np.array([M.same_player(o, u) and M.same_first_name(w, x)
                   for o, u, w, x in zip(c2["other"], c2["uother"], c2["own"], c2["uown"])], dtype=bool)
    second = _assign(_quality(c2[ok].assign(**{"pass": 2}))) if ok.any() else c2.head(0).assign(**{"pass": 2})
    return pd.concat([first, second], ignore_index=True)[["lid", "rid", "gap", "pass"]]


def link_same_event(left: pd.DataFrame, right: pd.DataFrame, first: pd.DataFrame) -> pd.DataFrame:
    """Pass 3, Sackmann only: a TML row the score could not link (a retirement written otherwise, a walkover, a name
    spelled otherwise such as O'Connell) takes the Sackmann row of the same round in the Sackmann event its edition's
    other rows link to, one surname key agreeing (a player plays once per round of an event; round robins aside)."""
    lk = first.merge(right[["rid", "tourney_id"]], on="rid").merge(left[["lid", "edition"]], on="lid")
    ev = lk.groupby("edition")["tourney_id"].agg(lambda s: s.value_counts().index[0])
    rest = left[~left["lid"].isin(first["lid"]) & left["round"].ne("RR")].copy()
    rest["sk_event"] = rest["edition"].map(ev)
    R = right[~right["rid"].isin(first["rid"]) & right["round"].ne("RR")]
    parts = []
    for lk_ in ("k1", "k2"):
        for rk in ("k1", "k2"):
            a = rest[["lid", "tour", "round", "date", "draw", "rnd", "sk_event", lk_]].rename(columns={lk_: "key"})
            b = R[["rid", "tour", "round", "day", "draw", "rnd", "tourney_id", rk]].rename(
                columns={rk: "key", "tourney_id": "sk_event", "draw": "draw_r", "rnd": "rnd_r"})
            parts.append(a[a["key"].ne("")].merge(b[b["key"].ne("")], on=["tour", "round", "sk_event", "key"]))
    c = pd.concat(parts, ignore_index=True).drop_duplicates(["lid", "rid"])
    c["gap"] = (c["day"] - c["date"]).dt.days
    c = c[c["gap"].abs() <= WINDOW].assign(**{"pass": 3})
    return _assign(_quality(c))[["lid", "rid", "gap", "pass"]]


def link_tdi(left: pd.DataFrame, tdi: pd.DataFrame) -> pd.DataFrame:
    """TDI has no score: the same pair and round within 60 days, the nearest date."""
    L = left[left["tour"].eq("atp") & left["pair"].notna() & left["date"].ge("2025-12-01")]
    c = L[["lid", "tour", "pair", "date", "draw", "rnd"]].merge(
        tdi[["rid", "tour", "pair", "day", "draw", "rnd"]], on=["tour", "pair"], suffixes=("", "_r"))
    c = c[c["rnd"].notna() & (c["rnd"] == c["rnd_r"])]
    c["gap"] = (c["day"] - c["date"]).dt.days
    c = c[c["gap"].abs() <= 60].assign(**{"pass": 1})
    return _assign(_quality(c))[["lid", "rid", "gap", "pass"]]


def attach(t: pd.DataFrame, links: dict) -> pd.DataFrame:
    """Each TML row's twins in the other sources, and its play days."""
    sk = links["sk"].set_index("lid")
    t["sk_tid"], t["sk_name"], t["sk_date"] = sk["tourney_id"], sk["tourney_name"], sk["day"]
    t["sk_round"], t["sk_file"], t["sk_row"], t["sk_pass"] = sk["round"], sk["_source_file"], sk["_row"], sk["pass"]
    li = links["tl"].set_index("lid")
    t["tl_day"], t["tl_event"], t["tl_event_name"] = li["day"], li["event_key"], li["event_name"]
    so = links["ss"].set_index("lid")
    t["ss_day"], t["ss_event"], t["ss_name"] = so["day"], so["event_id"], so["season_name"].fillna(so["tournament_name"])
    td = links["tdi"].set_index("lid")
    t["tdi_day"], t["tdi_tournament"] = td["day"], td["tournament"]
    lo, hi = t[["tl_day", "ss_day"]].min(axis=1), t[["tl_day", "ss_day"]].max(axis=1)
    agree = lo.notna() & ((hi - lo).dt.days <= CONFLICT)
    t["day_conflict"] = lo.notna() & ~agree
    use_tdi = ~lo.notna() & t["tdi_day"].notna()
    t["day_min"] = lo.where(agree, t["tdi_day"].where(use_tdi))          # the days as reported
    t["day_max"] = hi.where(agree, t["tdi_day"].where(use_tdi))
    t["day"] = t["day_min"] + (t["day_max"] - t["day_min"]) / 2
    t["day_source"] = np.select([t["tl_day"].notna() & t["ss_day"].notna() & agree, t["tl_day"].notna() & agree,
                                 t["ss_day"].notna() & agree, use_tdi, t["day_conflict"]],
                                ["tennislive+sofascore", "tennislive", "sofascore", "tdi", "conflict"], "")
    t["has_day"] = t["day_min"].notna()
    t["wkind"] = window_kind(t["level"], t["draw_size"])
    t["ckind"] = calib_kind(t["level"], t["draw_size"])
    return t


def round_offsets(t: pd.DataFrame) -> pd.DataFrame:
    """Each round's typical day after Sackmann's tournament date, by kind of event: the median over rows whose TML row,
    Sackmann twin and play day all agree within a fortnight."""
    c = t[t["has_day"] & t["sk_date"].notna()].copy()
    c["offset"] = (c["day"] - c["sk_date"]).dt.days
    c = c[c["offset"].between(-12, 20)]
    out = c.groupby(["ckind", "round"])["offset"].agg(["median", "count"]).reset_index()
    out = out[out["count"] >= 30]
    allk = c.groupby("ckind")["offset"].agg(["median", "count"]).reset_index().assign(round="*")
    return pd.concat([out, allk], ignore_index=True)


def implied_start(t: pd.DataFrame, offsets: pd.DataFrame) -> pd.Series:
    typ = offsets.set_index(["ckind", "round"])["median"]
    key = pd.MultiIndex.from_arrays([t["ckind"], t["round"]])
    any_key = pd.MultiIndex.from_arrays([t["ckind"], pd.Series("*", index=t.index)])
    med = pd.Series(typ.reindex(key).to_numpy(), index=t.index).fillna(
        pd.Series(typ.reindex(any_key).to_numpy(), index=t.index)).fillna(2)
    return t["day"] - pd.to_timedelta(med.round(), unit="D")


# ------------------------------------------------------------------------------------------------
# Verdicts

def editions(t: pd.DataFrame) -> pd.DataFrame:
    g = t.groupby("edition")
    ed = pd.DataFrame({
        "tour": g["tour"].first(), "season": g["season"].first(), "group": g["group"].agg(joined),
        "tml_id": g["tourney_id"].first(), "tml_name": g["tourney_name"].first(), "tml_date": g["ed_date"].first(),
        "tml_dates_in_rows": g["date"].agg(lambda s: joined(s.dt.strftime("%Y-%m-%d"))),
        "rows": g.size(), "rows_with_day": g["has_day"].sum(),
        "play_start": g["cand_start"].agg(lambda s: s.dropna().sort_values().iloc[len(s.dropna()) // 2]
                                          if s.notna().any() else pd.NaT),
        "first_play_day": g["day_min"].min(), "last_play_day": g["day_max"].max(),
        "rows_with_sackmann": g["sk_date"].count(),
        "sackmann_ids": g["sk_tid"].agg(joined), "sackmann_names": g["sk_name"].agg(joined),
        "sackmann_dates": g["sk_date"].agg(lambda s: joined(s.dt.strftime("%Y-%m-%d"))),
        "tennislive_events": g["tl_event_name"].agg(joined), "sofascore_events": g["ss_name"].agg(joined),
        "tdi_events": g["tdi_tournament"].agg(joined),
    })
    main = t[t["draw"].eq("main")].groupby("edition")["level"].agg(lambda s: s.value_counts().index[0])
    ed["level"] = main.reindex(ed.index).fillna(g["level"].agg(lambda s: s.value_counts().index[0]))
    mode = t.dropna(subset=["sk_date"]).groupby("edition")["sk_date"].agg(lambda s: s.value_counts().index[0])
    share = t.dropna(subset=["sk_date"]).groupby("edition")["sk_date"].agg(lambda s: s.value_counts().iloc[0] / len(s))
    ed["sackmann_mode"], ed["sackmann_mode_share"] = mode, share
    ed = ed.reset_index()
    ed["play_start"] = nearest_monday(pd.to_datetime(ed["play_start"]))
    gap = (ed["sackmann_mode"] - ed["play_start"]).dt.days
    sk_ok = ed["sackmann_mode"].notna() & ed["sackmann_mode_share"].ge(0.5)
    use_sk = sk_ok & (gap.abs().le(AGREE) | (ed["play_start"].isna() & ed["rows_with_sackmann"].ge(MIN_ROWS)))
    ed["true_start"] = ed["sackmann_mode"].where(use_sk, ed["play_start"])
    ed["true_start_basis"] = np.select(
        [use_sk & ed["play_start"].notna(), use_sk, ed["play_start"].notna() & sk_ok, ed["play_start"].notna()],
        ["sackmann (agrees with the play days)", "sackmann only (no play days)",
         "play days (Sackmann's date disagrees)", "play days (no Sackmann twin)"], "none")
    ed["sackmann_minus_play_days"] = gap
    ed["tml_minus_true_days"] = (ed["tml_date"] - ed["true_start"]).dt.days
    # rows that support the true start: their implied start (or Sackmann date) within AGREE days of it; their play days
    # are the edition's span (else the span of an ordinary edition of its kind)
    sup = t.merge(ed[["edition", "true_start"]], on="edition")
    sup["ok"] = ((sup["cand_start"] - sup["true_start"]).dt.days.abs().le(AGREE)
                 | (sup["sk_date"] - sup["true_start"]).dt.days.abs().le(AGREE))
    ed["rows_supporting_true_start"] = ed["edition"].map(sup.groupby("edition")["ok"].sum()).fillna(0).astype(int)
    sd = sup[sup["ok"] & sup["has_day"]].groupby("edition")
    kind = ed["edition"].map(t.groupby("edition")["wkind"].agg(lambda s: s.value_counts().index[0]))
    lo = ed["true_start"] + pd.to_timedelta(np.where(kind.eq("fortnight"), -7, -2), unit="D")
    hi = ed["true_start"] + pd.to_timedelta(np.where(kind.eq("fortnight"), 13, 6), unit="D")
    ed["span_first_day"] = ed["edition"].map(sd["day_min"].min()).fillna(lo)
    ed["span_last_day"] = ed["edition"].map(sd["day_max"].max()).fillna(hi)
    ed["tml_dates_count"] = ed["tml_dates_in_rows"].str.count(";") + 1
    tml = ed["tml_date"]
    err = (tml - ed["true_start"]).dt.days
    before = tml < ed["span_first_day"] - pd.Timedelta(days=3)          # before even the qualifying's Friday
    # after the day after the final, and more than a week late (an edition cut short, as in March 2020, ends early
    # while TML still dates it by its closing Sunday)
    after = (tml > ed["span_last_day"] + pd.Timedelta(days=1)) & err.gt(WRONG_DAYS)
    # the closing days of its own week: more than 2 days after the true start and in the later half of the play days (a
    # 96-draw event whose main draw starts mid-week is dated by its first main-draw day, which is right)
    mid = ed["span_first_day"] + (ed["span_last_day"] - ed["span_first_day"]) / 2
    late = ~before & ~after & err.gt(2) & (tml > mid)
    ed["date_error"] = np.select(
        [ed["true_start"].isna(), before, after, late & ed["tml_dates_count"].ge(3), late],
        ["no evidence", "another week (early)", "another week (late)", "dated by day (each match its own day)",
         "dated by its last days"], "right")
    weak = ed["rows_supporting_true_start"].lt(MIN_ROWS) & ed["date_error"].str.startswith("another week")
    ed.loc[weak, "date_error"] = "unresolved (" + ed.loc[weak, "date_error"] + " on fewer than 3 rows)"
    # lumped: one name and date for two or more tournament ids of a season (team-event rubbers aside)
    cand = ed[~ed["level"].eq("TEAM")]
    n_ids = cand.groupby(["tour", "season", "tml_name", "tml_date"])["tml_id"].transform("nunique")
    ids = cand.groupby(["tour", "season", "tml_name", "tml_date"])["tml_id"].transform(joined)
    ed["lumped"] = (n_ids >= 2).reindex(ed.index).fillna(False).astype(bool)
    ed["lumped_ids"] = ids.where(n_ids >= 2).reindex(ed.index)
    # does the lump hold a member dated in another week (a true lump), or only editions within their weeks (two
    # consecutive editions, the first dated by its closing Sunday and the second by its opening one)?
    another = ed["date_error"].str.startswith("another week")
    has = ed[ed["lumped"]].assign(a=another).groupby("lumped_ids")["a"].any()
    ed["lump_has_another_week"] = ed["lumped_ids"].map(has).fillna(False).astype(bool) & ed["lumped"]
    return ed


def row_truth(rows: pd.DataFrame) -> pd.DataFrame:
    """Each row's true start and true play days. In order: its own Sackmann date where that agrees with its own play day
    (or, without a play day, with the edition); the Sackmann date most of its draw's rows (qualifying or main) carry
    where at least MIN_ROWS of them agree with their play days; the Monday nearest the start its draw's play days imply
    (MIN_ROWS rows or more); the edition's true start. Its play days are its own where they agree with that start
    (TRUST days), else the window of an ordinary edition of its kind around it."""
    lo_off = rows["wkind"].map({k: v[0] for k, v in PLAY_WINDOW.items()})
    hi_off = rows["wkind"].map({k: v[1] for k, v in PLAY_WINDOW.items()})
    grp = rows["edition"] + "|" + rows["draw"]
    days = rows[rows["has_day"]].groupby(grp[rows["has_day"]])["cand_start"]
    g_play = days.agg(lambda s: s.sort_values().iloc[len(s) // 2])[days.size() >= MIN_ROWS]
    g_play = pd.Series(nearest_monday(pd.to_datetime(g_play)).to_numpy(), index=g_play.index)
    by_play = grp.map(g_play)
    # a row's play day counts when it belongs to its edition or to its draw's cluster (a lone outlier is a mislink:
    # the pair's other meeting with the same score)
    row_ok = rows["has_day"] & ((rows["cand_start"] - rows["ed_true_start"]).dt.days.abs().le(TRUST)
                                | (rows["cand_start"] - by_play).dt.days.abs().le(TRUST))
    own_ok = row_ok & rows["sk_date"].notna() & (rows["cand_start"] - rows["sk_date"]).dt.days.abs().le(TRUST)
    near = rows["sk_date"].notna() & ~rows["has_day"] & (rows["sk_date"] - rows["ed_true_start"]).dt.days.abs().le(AGREE)
    ok_sk = rows[own_ok].groupby(grp[own_ok])["sk_date"]
    g_mode = ok_sk.agg(lambda s: s.value_counts().index[0])
    g_mode = g_mode[ok_sk.size() >= MIN_ROWS]
    by_mode = grp.map(g_mode)
    rows["true_start"] = rows["sk_date"].where(own_ok | near, by_mode.fillna(by_play).fillna(rows["ed_true_start"]))
    rows["true_start_basis"] = np.select([own_ok, near, by_mode.notna(), by_play.notna()],
                                         ["own Sackmann date (agrees with its play day)",
                                          "own Sackmann date (no play day)", "its draw's Sackmann date",
                                          "its draw's play days"], "edition")
    rows["day_trusted"] = row_ok & (rows["cand_start"] - rows["true_start"]).dt.days.abs().le(TRUST)
    # a Sackmann twin that agrees with neither the row's play day nor its truth is another match (the pair's other
    # meeting with the same score, where Sackmann lacks this one): it is set aside
    keep = (own_ok | near | (rows["sk_date"] - rows["true_start"]).dt.days.abs().le(WRONG_DAYS)
            | rows["true_start"].isna())                         # no evidence on the edition: nothing contradicts him
    rows["sk_set_aside"] = rows["sk_date"].notna() & ~keep
    for c in ("sk_tid", "sk_name", "sk_date", "sk_round", "sk_file", "sk_row", "sk_pass"):
        rows[c] = rows[c].where(~rows["sk_set_aside"])
    rows["true_lo"] = rows["day_min"].where(rows["day_trusted"], rows["true_start"] + pd.to_timedelta(lo_off, unit="D"))
    rows["true_hi"] = rows["day_max"].where(rows["day_trusted"], rows["true_start"] + pd.to_timedelta(hi_off, unit="D"))
    rows["true_basis"] = np.where(rows["day_trusted"], "own play day (" + rows["day_source"] + ")",
                                  np.where(rows["true_start"].notna(), "the edition's week", ""))
    # the TML date of the row against its own truth
    rows["tml_minus_true_days"] = (rows["ed_date"] - rows["true_start"]).dt.days
    return rows


def stage0_join(rows: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    s0k = s0.set_index("key")
    rows["tml_key"] = rows["_source_file"].astype(str) + "#" + rows["_row"].astype(str)
    rows["sk_key"] = rows["sk_file"].astype(str) + "#" + rows["sk_row"].astype("Int64").astype(str)
    for pre, key in (("s0t", "tml_key"), ("s0s", "sk_key")):
        hit = rows[key].isin(s0k.index)
        for col in ("match_id", "tournament_date", "tournament_id", "level", "evaluation", "status"):
            rows[f"{pre}_{col}"] = rows[key].map(s0k[col]).where(hit)
    rows["s0_held_as"] = np.select([rows["s0s_match_id"].notna() & rows["s0t_match_id"].notna(),
                                    rows["s0s_match_id"].notna(), rows["s0t_match_id"].notna()],
                                   ["both (twice)", "sackmann_row", "tml_row"], "not_in_stage0")
    rows["s0_match_id"] = rows["s0s_match_id"].fillna(rows["s0t_match_id"])
    rows["s0_date"] = pd.to_datetime(rows["s0s_tournament_date"].fillna(rows["s0t_tournament_date"]))
    rows["s0_level"] = rows["s0s_level"].fillna(rows["s0t_level"])
    rows["s0_evaluation"] = rows["s0s_evaluation"].fillna(rows["s0t_evaluation"])
    rows["s0_status"] = rows["s0s_status"].fillna(rows["s0t_status"])
    rows["s0_minus_true_days"] = (rows["s0_date"] - rows["true_start"]).dt.days
    rows["s0_date_is"] = np.select([rows["s0_date"].isna(), rows["s0_date"].eq(rows["sk_date"]),
                                    rows["s0_date"].eq(rows["ed_date"]) | rows["s0_date"].eq(rows["date"])],
                                   ["", "sackmann_date", "tml_date"], "other")
    rows["s0_wrong"] = rows["s0_minus_true_days"].abs().gt(WRONG_DAYS)
    return rows


def clock_check(rows: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    """lf before the first day the match can have been played: its result counts from lf + 1, before it happened.
    'certain' allows the play day's own error (one day each way); 'reported' compares with the reported day itself."""
    tm = tm.set_index("match_id")
    for col in ("es", "lf", "exact", "window_basis", "sources"):
        rows[f"clock_{col}"] = rows["s0_match_id"].map(tm[col])
    rows["clock_es_date"] = EPOCH + pd.to_timedelta(rows["clock_es"], unit="D")
    rows["clock_lf_date"] = EPOCH + pd.to_timedelta(rows["clock_lf"], unit="D")
    lo, hi = to_days(rows["true_lo"]), to_days(rows["true_hi"])
    pad = np.where(rows["day_trusted"], 1, 0)      # a reported day may be one off; an edition's window is padded already
    has = rows["clock_lf"].notna() & lo.notna()
    rows["clock_leak"] = np.select([has & (rows["clock_lf"] < lo - pad), has & (rows["clock_lf"] < lo)],
                                   ["lf before the play day (certain)", "lf the day before the reported play day"], "")
    rows["clock_lf_days_before"] = np.where(has, lo - rows["clock_lf"], np.nan)
    rows["clock_late_start"] = np.select([has & (rows["clock_es"] > hi + pad), has & (rows["clock_es"] > hi)],
                                         ["es after the play day (certain)", "es the day after the reported play day"], "")
    rows["clock_es_days_after"] = np.where(has, rows["clock_es"] - hi, np.nan)
    rows["clock_holds_day"] = has & (rows["clock_es"] <= hi + pad) & (rows["clock_lf"] >= lo - pad)
    return rows


def leak_reach(t: pd.DataFrame, tm: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    """Where a window ends before its match was played, the later matches that read the result too early: matches of
    either player whose es lies after the leaking match's lf and no later than the day before its first possible play
    day (they read the state as of es, and the result counts from lf + 1). One row per (leaking match, reader)."""
    leaks = t[t["clock_leak"].eq("lf before the play day (certain)") & t["resolved"]]
    cols = ["leak_match_id", "reader_match_id", "player_id", "leak_lf", "leak_first_play_day", "reader_es",
            "reader_evaluation"]
    if leaks.empty:
        return pd.DataFrame(columns=cols)
    pl = s0.set_index("match_id")[["player_a_id", "player_b_id"]]
    L = leaks[["s0_match_id", "clock_lf", "true_lo", "day_trusted"]].join(pl, on="s0_match_id")
    L["first"] = to_days(L["true_lo"]) - np.where(L["day_trusted"], 1, 0)
    long = pd.concat([L[["s0_match_id", "clock_lf", "first", c]].rename(columns={c: "player_id"})
                      for c in ("player_a_id", "player_b_id")])
    allm = s0[["match_id", "player_a_id", "player_b_id", "evaluation"]].merge(tm[["match_id", "es"]], on="match_id")
    allp = pd.concat([allm[["match_id", c, "es", "evaluation"]].rename(columns={c: "player_id"})
                      for c in ("player_a_id", "player_b_id")])
    x = long.merge(allp, on="player_id")
    x = x[(x["es"] >= x["clock_lf"] + 1) & (x["es"] < x["first"]) & x["match_id"].ne(x["s0_match_id"])]
    return pd.DataFrame({"leak_match_id": x["s0_match_id"], "reader_match_id": x["match_id"], "player_id": x["player_id"],
                         "leak_lf": EPOCH + pd.to_timedelta(x["clock_lf"], unit="D"),
                         "leak_first_play_day": EPOCH + pd.to_timedelta(x["first"], unit="D"),
                         "reader_es": EPOCH + pd.to_timedelta(x["es"], unit="D"), "reader_evaluation": x["evaluation"]})


def map_copies(rows: pd.DataFrame, mp: pd.DataFrame) -> pd.DataFrame:
    """The map's copies of each TML row's match. The TML copy: created by 'tml' with the row's own date, name, pair and
    draw (TML's rows build the map first, so each makes one). Sackmann's copy: created by 'sackmann' with his twin's
    date, name, pair and draw; it exists only where the map failed to link his row to the TML copy (his date minus TML's
    outside -10..+21 days), so the match is then held twice. Without a Sackmann twin, a copy another source created near
    the true play days (not 'tml'), where the TML copy lies outside the map's window of the truth, counts the same way."""
    tml_copy = mp[mp["creator"].eq("tml")][["uid", "tour", "pair", "d", "tname", "draw", "level", "year"]]
    a = rows[["lid", "tour", "pair", "date", "tourney_name", "draw"]].rename(columns={"date": "d", "tourney_name": "tname"})
    a = a.merge(tml_copy, on=["tour", "pair", "d", "tname", "draw"], how="left").drop_duplicates("lid").set_index("lid")
    rows["map_tml_uid"], rows["map_tml_level"], rows["map_tml_year"] = (rows["lid"].map(a["uid"]),
                                                                        rows["lid"].map(a["level"]),
                                                                        rows["lid"].map(a["year"]))
    sk_copy = mp[mp["creator"].eq("sackmann")][["uid", "tour", "pair", "d", "tname", "draw"]]
    b = rows[rows["sk_date"].notna()][["lid", "tour", "pair", "sk_date", "sk_name", "sk_round"]].rename(
        columns={"sk_date": "d", "sk_name": "tname"})
    b["draw"] = draw_of(b["sk_round"])
    b = b.merge(sk_copy, on=["tour", "pair", "d", "tname", "draw"]).drop_duplicates("lid").set_index("lid")
    rows["map_sk_uid"] = rows["lid"].map(b["uid"])
    o = rows[rows["sk_date"].isna()][["lid", "tour", "pair", "draw", "true_lo", "true_hi", "map_tml_uid"]].merge(
        mp[~mp["creator"].isin(["tml", "sackmann"])][["uid", "tour", "pair", "draw", "d", "creator"]],
        on=["tour", "pair", "draw"])
    o = o[(o["d"] >= o["true_lo"] - pd.Timedelta(days=21)) & (o["d"] <= o["true_hi"] + pd.Timedelta(days=10))]
    o = o.drop_duplicates("lid").set_index("lid")
    tml_far = ~(rows["date"] - rows["true_start"]).dt.days.between(-21, 10)     # TML - truth outside the map's window
    rows["map_other_uid"] = rows["lid"].map(o["uid"]).where(tml_far)
    rows["map_other_creator"] = np.where(rows["map_sk_uid"].notna(), "sackmann", rows["lid"].map(o["creator"]))
    rows["map_other_creator"] = rows["map_other_creator"].where(rows["map_sk_uid"].notna() | rows["map_other_uid"].notna())
    rows["map_other_uid"] = rows["map_sk_uid"].fillna(rows["map_other_uid"])
    rows["map_other_d"] = np.where(rows["map_sk_uid"].notna(), rows["sk_date"], rows["lid"].map(o["d"]))
    rows["map_twice"] = rows["map_tml_uid"].notna() & rows["map_other_uid"].notna() & rows["map_other_uid"].ne(
        rows["map_tml_uid"])
    return rows


# ------------------------------------------------------------------------------------------------

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tml = load_tml()
    log(f"TML rows from {FIRST_DATE.date()}: {len(tml):,} in {tml['edition'].nunique():,} editions")
    sources = {"sk": load_sackmann(), "tl": load_tennislive(), "ss": load_sofascore()}
    tdi = load_tdi()
    log("rows: " + ", ".join(f"{k} {len(v):,}" for k, v in sources.items()) + f", tdi {len(tdi):,}")
    links = {}
    for name, right in sources.items():
        r = right.assign(rid=np.arange(len(right)))
        lk = link(tml, r)
        if name == "sk":
            lk = pd.concat([lk, link_same_event(tml, r, lk)], ignore_index=True)
        links[name] = lk.merge(r.drop(columns=["tour", "pair", "k1", "k2", "n1", "n2", "sig", "draw", "rnd"]),
                               on="rid", how="left")
        log(f"linked to {name}: {len(lk):,} rows (by pass: {lk['pass'].value_counts().sort_index().to_dict()})")
    r = tdi.assign(rid=np.arange(len(tdi)))
    links["tdi"] = link_tdi(tml, r).merge(r[["rid", "day", "tournament"]], on="rid", how="left")
    log(f"linked to TDI: {len(links['tdi']):,} rows")

    t = attach(tml.copy(), links)
    offsets = round_offsets(t)
    offsets.to_csv(OUT / "round_offsets.csv", index=False)
    t["cand_start"] = implied_start(t, offsets)
    log(f"rows with a play day: {int(t['has_day'].sum()):,} of {len(t):,} ({int(t['day_conflict'].sum()):,} conflicts)")

    ed = editions(t)
    t = t.merge(ed[["edition", "true_start", "date_error", "lumped", "rows_supporting_true_start"]].rename(
        columns={"true_start": "ed_true_start", "rows_supporting_true_start": "ed_support"}), on="edition", how="left")
    # rows played in another week than the rest of their edition: their implied start far from the edition's true start
    t["row_apart"] = t["has_day"] & (t["cand_start"] - t["ed_true_start"]).dt.days.abs().gt(TRUST)
    ed["rows_played_another_week"] = ed["edition"].map(t.groupby("edition")["row_apart"].sum()).fillna(0).astype(int)
    misdated = ed["date_error"].str.startswith("another week")
    last_days = ed["date_error"].eq("dated by its last days") & ~ed["level"].eq("TEAM")
    apart = ~misdated & ed["rows_played_another_week"].ge(MIN_ROWS)
    lump = ed["lumped"] & ed["lump_has_another_week"]
    pair = ed["lumped"] & ~ed["lump_has_another_week"]
    ed["category"] = np.select([misdated & ed["lumped"], misdated, lump, apart, pair, last_days],
                               ["misdated, lumped", "misdated", "lumped, dated within its week", "rows dated apart",
                                "consecutive editions under one name and date", "dated by its last days"], "")
    ed.sort_values(["tour", "tml_date", "tml_name"]).to_csv(OUT / "editions.csv", index=False, date_format="%Y-%m-%d")
    log("editions: " + ", ".join(f"{k or 'not flagged'} {v:,}" for k, v in ed["category"].value_counts().items()))

    # every TML row: its truth, Stage 0's row, the clock's window and the map's copies (the outputs keep the flagged)
    t = t.merge(ed[["edition", "category"]], on="edition", how="left")
    t = row_truth(t)
    # a verdict on a row needs its edition's true start supported by MIN_ROWS rows
    t["resolved"] = t["ed_support"].ge(MIN_ROWS)
    s0 = pd.read_parquet(STAGE0, columns=["match_id", "tour", "year", "level", "qualifying", "evaluation", "round",
                                          "tournament_id", "tournament_name", "tournament_date", "status", "source",
                                          "tml_link", "source_file", "source_row", "player_a_id", "player_b_id"])
    s0["key"] = s0["source_file"] + "#" + s0["source_row"].astype(str)
    if s0["key"].duplicated().any():
        raise SystemExit("Stage 0: one source row behind two matches; the join by source file and row is ambiguous")
    t = stage0_join(t, s0)
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "exact", "window_basis", "sources"])
    t = clock_check(t, tm)
    reach = leak_reach(t, tm, s0)
    mp = pd.read_parquet(MAP, columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname", "creator"])
    mp["tour"] = mp["tour"].map({"M": "atp", "W": "wta"})
    mp = prep(mp, "name1", "name2")
    t = map_copies(t, mp)
    flagged = ed[ed["category"].ne("")]
    rows = t[t["category"].ne("")].copy()
    log(f"flagged editions {len(flagged):,}, rows {len(rows):,}")

    # every TML-only Stage 0 row, flagged edition or not, whose date is more than WRONG_DAYS from its truth
    only = t[t["s0_held_as"].isin(["tml_row", "both (twice)"])]
    only_bad = only[only["s0_wrong"] & only["resolved"]]
    reach.to_csv(OUT / "clock_leak_readers.csv", index=False, date_format="%Y-%m-%d")
    write_outputs(t, ed, flagged, rows, only, only_bad, links, offsets, reach)
    return 0


def write_outputs(t, ed, flagged, rows, only, only_bad, links, offsets, reach) -> None:
    keep = ["category", "edition", "lumped", "tour", "group", "season", "level", "tourney_id", "tourney_name",
            "tourney_date", "ed_date", "round", "draw", "winner_name", "loser_name", "score", "_source_file", "_row",
            "sk_tid", "sk_name", "sk_date", "sk_round", "sk_file", "sk_row", "sk_pass", "sk_set_aside", "tl_day", "tl_event",
            "tl_event_name", "ss_day", "ss_event", "ss_name", "tdi_day", "tdi_tournament", "day_source", "day_min",
            "day_max", "cand_start", "ed_true_start", "true_start", "true_start_basis", "day_trusted", "resolved",
            "true_lo", "true_hi",
            "true_basis", "tml_minus_true_days", "s0_held_as", "s0_match_id", "s0t_match_id", "s0s_match_id", "s0_date",
            "s0_date_is", "s0_minus_true_days", "s0_wrong", "s0_level", "s0_evaluation", "s0_status", "clock_es_date",
            "clock_lf_date", "clock_exact", "clock_window_basis", "clock_sources", "clock_holds_day", "clock_leak",
            "clock_lf_days_before", "clock_late_start", "clock_es_days_after", "map_tml_uid", "map_tml_level",
            "map_tml_year", "map_other_uid", "map_other_creator", "map_other_d", "map_twice"]
    rows[keep].to_csv(OUT / "misdated_matches.csv.gz", index=False, date_format="%Y-%m-%d", compression="gzip")

    rg = rows.groupby("edition")
    fl = flagged.set_index("edition")
    fl["stage0_sackmann_rows"] = rg["s0_held_as"].agg(lambda s: int(s.eq("sackmann_row").sum()))
    fl["stage0_tml_rows"] = rg["s0_held_as"].agg(lambda s: int(s.eq("tml_row").sum()))
    fl["stage0_twice"] = rg["s0_held_as"].agg(lambda s: int(s.eq("both (twice)").sum()))
    fl["stage0_missing"] = rg["s0_held_as"].agg(lambda s: int(s.eq("not_in_stage0").sum()))
    fl["stage0_dates_wrong"] = rg["s0_wrong"].sum()
    fl["clock_lf_before_play_day"] = rg["clock_leak"].agg(lambda s: int(s.eq("lf before the play day (certain)").sum()))
    fl["clock_es_after_play_day"] = rg["clock_late_start"].agg(
        lambda s: int(s.eq("es after the play day (certain)").sum()))
    fl["map_held_twice"] = rg["map_twice"].sum()
    fl = fl.reset_index()
    cols = ["category", "tour", "season", "level", "tml_id", "tml_name", "tml_date", "date_error", "tml_minus_true_days",
            "true_start", "true_start_basis", "span_first_day", "span_last_day", "lumped", "lumped_ids",
            "lump_has_another_week", "rows",
            "rows_with_day", "rows_supporting_true_start", "rows_played_another_week", "rows_with_sackmann",
            "sackmann_ids", "sackmann_names", "sackmann_dates", "tennislive_events", "sofascore_events", "tdi_events",
            "stage0_sackmann_rows", "stage0_tml_rows", "stage0_twice", "stage0_missing", "stage0_dates_wrong",
            "clock_lf_before_play_day", "clock_es_after_play_day", "map_held_twice", "group", "tml_dates_in_rows",
            "edition"]
    fl.sort_values(["category", "tour", "tml_date", "tml_name", "tml_id"])[cols].to_csv(
        OUT / "misdated_editions.csv", index=False, date_format="%Y-%m-%d")

    # the correction table, the clock's misses and the map's doubles cover every TML row, flagged edition or not
    t = t.assign(category=t["category"].replace("", "not flagged"))
    wrong = t[t["s0_wrong"] & t["resolved"]].copy()
    sk_part = np.where(wrong["sk_date"].notna(), "; Sackmann " + wrong["sk_tid"].fillna("") + " '"
                       + wrong["sk_name"].fillna("") + "' " + wrong["sk_date"].dt.strftime("%Y-%m-%d").fillna(""),
                       "; no Sackmann row")
    wrong["evidence"] = ("TML " + wrong["tourney_id"] + " '" + wrong["tourney_name"] + "' dated "
                         + wrong["ed_date"].dt.strftime("%Y-%m-%d") + "; played " + wrong["true_lo"].dt.strftime("%Y-%m-%d")
                         + ".." + wrong["true_hi"].dt.strftime("%Y-%m-%d") + " (" + wrong["true_basis"] + ")"
                         + np.where(wrong["tl_event_name"].notna(), "; TennisLive '" + wrong["tl_event_name"].fillna("")
                                    + "' " + wrong["tl_day"].dt.strftime("%Y-%m-%d").fillna(""), "")
                         + np.where(wrong["ss_name"].notna(), "; SofaScore '" + wrong["ss_name"].fillna("").astype(str)
                                    + "' " + wrong["ss_day"].dt.strftime("%Y-%m-%d").fillna(""), "") + sk_part)
    corr = wrong[["category", "s0_match_id", "s0_held_as", "s0_level", "s0_evaluation", "s0_status", "s0_date",
                  "true_start", "true_start_basis", "s0_minus_true_days", "true_lo", "true_hi", "true_basis",
                  "clock_es_date", "clock_lf_date", "clock_leak", "tourney_id", "tourney_name", "round", "winner_name",
                  "loser_name", "score", "_source_file", "_row", "evidence"]].rename(
        columns={"s0_match_id": "stage0_match_id", "s0_date": "stage0_date", "true_start": "true_date",
                 "true_lo": "played_from", "true_hi": "played_to"})
    corr.sort_values(["stage0_date", "stage0_match_id"]).to_csv(OUT / "stage0_date_corrections.csv", index=False,
                                                                date_format="%Y-%m-%d")
    miss = t[(t["clock_leak"].ne("") | t["clock_late_start"].ne("")) & t["resolved"]]
    miss[["category", "s0_match_id", "s0_held_as", "s0_level", "s0_evaluation", "tourney_id", "tourney_name", "round",
          "winner_name", "loser_name", "s0_date", "clock_es_date", "clock_lf_date", "clock_window_basis", "clock_sources",
          "true_lo", "true_hi", "true_basis", "clock_leak", "clock_lf_days_before", "clock_late_start",
          "clock_es_days_after"]].to_csv(OUT / "clock_windows.csv", index=False, date_format="%Y-%m-%d")
    t[t["map_twice"]][["category", "map_tml_uid", "map_other_uid", "map_other_creator", "map_tml_year", "map_tml_level",
                       "tour", "tourney_id", "tourney_name", "date", "map_other_d", "true_start",
                       "round", "winner_name", "loser_name", "score"]].to_csv(OUT / "map_doubles.csv", index=False,
                                                                              date_format="%Y-%m-%d")
    twice = t[t["s0_held_as"].eq("both (twice)") & (t["resolved"] | t["ed_true_start"].isna())]
    twice[["category", "s0t_match_id", "s0s_match_id", "tourney_id", "tourney_name", "date", "sk_tid", "sk_name", "sk_date",
           "round", "sk_round", "winner_name", "loser_name", "score"]].to_csv(OUT / "stage0_duplicates.csv", index=False,
                                                                             date_format="%Y-%m-%d")
    # the edition-level correction (for the map's TML rows, and Stage 0's TML-only rows): the misdated editions, and
    # the draw played apart (the 2021 Australian Open's qualifying)
    mis_ed = ed[ed["category"].str.startswith("misdated")].assign(draw="all")
    apart_rows = t[t["category"].eq("rows dated apart") & t["row_apart"]]
    apart_ed = (apart_rows.groupby(["edition", "draw"])["true_start"].agg(lambda s: s.value_counts().index[0])
                .rename("true_start").reset_index()
                .merge(ed.drop(columns=["true_start"]), on="edition"))
    fix = pd.concat([mis_ed, apart_ed], ignore_index=True)
    fix["true_names"] = fix["sackmann_names"].fillna(fix["tennislive_events"])
    fix["evidence"] = ("play days " + fix["span_first_day"].dt.strftime("%Y-%m-%d").fillna("?") + ".."
                       + fix["span_last_day"].dt.strftime("%Y-%m-%d").fillna("?") + " (TennisLive '"
                       + fix["tennislive_events"].fillna("") + "'; SofaScore '" + fix["sofascore_events"].fillna("")
                       + "'); Sackmann " + fix["sackmann_ids"].fillna("none") + " " + fix["sackmann_dates"].fillna(""))
    fix[["tour", "season", "level", "tml_id", "tml_name", "tml_date", "draw", "true_start", "true_start_basis",
         "tml_minus_true_days", "true_names", "lumped_ids", "rows", "rows_supporting_true_start", "category",
         "evidence", "edition"]].sort_values(["tour", "tml_date", "tml_id"]).to_csv(
        OUT / "tml_edition_date_corrections.csv", index=False, date_format="%Y-%m-%d")
    only_bad[["category", "s0_match_id", "s0_level", "s0_evaluation", "s0_status", "s0_date", "true_start",
              "true_start_basis", "s0_minus_true_days", "day_source", "day_min", "day_max", "tourney_id", "tourney_name",
              "tourney_date", "round", "winner_name", "loser_name", "score", "tl_event_name", "ss_name", "sk_tid",
              "sk_date"]].to_csv(OUT / "stage0_tml_only_check.csv", index=False, date_format="%Y-%m-%d")

    def by(frame: pd.DataFrame, cols: list[str]) -> list[dict]:
        return json.loads(frame.groupby(cols, dropna=False).size().rename("matches").reset_index()
                          .to_json(orient="records", date_format="iso"))

    cat = rows["category"]
    mis = cat.str.startswith("misdated")
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "parameters": {"window_days": WINDOW, "conflict_days": CONFLICT, "min_rows": MIN_ROWS, "agree_days": AGREE,
                       "wrong_days": WRONG_DAYS, "trust_days": TRUST, "play_window": PLAY_WINDOW},
        "inputs": {"tml_rows": int(len(t))},
        "links": {k: {"rows": int(len(v)), "pass2": int(v["pass"].eq(2).sum())} for k, v in links.items()},
        "rows_with_play_day": int(t["has_day"].sum()), "rows_day_conflict": int(t["day_conflict"].sum()),
        "editions": {"all": int(len(ed)), "date_error": ed["date_error"].value_counts().to_dict(),
                     "category": ed["category"].replace("", "not flagged").value_counts().to_dict(),
                     "category_by_season_level": by(ed[ed["category"].ne("")], ["category", "season", "level"])},
        "rows_by_category": cat.value_counts().to_dict(),
        "stage0": {
            "held_as_by_category": by(rows, ["category", "s0_held_as"]),
            "date_is_by_category": by(rows, ["category", "s0_date_is"]),
            "wrong_dates_all_tml_rows": int(len(wrong)),
            "wrong_by_category_year_level_held_as": by(wrong, ["category", "season", "s0_level", "s0_held_as"]),
            "wrong_evaluation_matches": int(wrong["s0_evaluation"].fillna(False).astype(bool).sum()),
            "unresolved_rows_all": int((~t["resolved"]).sum()),
            "sackmann_twins_set_aside_all": int(t["sk_set_aside"].sum()),
            "tml_only_rows_in_stage0": int(len(only)), "tml_only_rows_with_play_day": int(only["has_day"].sum()),
            "tml_only_rows_dated_wrong": int(len(only_bad)),
            "tml_only_wrong_by_year_level": by(only_bad, ["season", "s0_level"])},
        "clock": {"by_category_all_rows": by(miss, ["category", "clock_leak", "clock_late_start"]),
                  "holds_day_flagged": int(rows["clock_holds_day"].sum()),
                  "with_clock_flagged": int(rows["clock_lf"].notna().sum()),
                  "leaks_certain_by_year_level": by(miss[miss["clock_leak"].eq("lf before the play day (certain)")],
                                                    ["category", "season", "s0_level", "s0_held_as", "s0_evaluation"]),
                  "leak_readers": {"pairs": int(len(reach)), "reader_matches": int(reach["reader_match_id"].nunique()),
                                   "reader_evaluation_matches": int(reach.loc[reach["reader_evaluation"].fillna(False)
                                                                              .astype(bool), "reader_match_id"].nunique()),
                                   "leaking_matches_read": int(reach["leak_match_id"].nunique())}},
        "map": {"twice_all_rows": int(t["map_twice"].sum()), "twice_flagged": int(rows["map_twice"].sum()),
                "twice_misdated": int((rows["map_twice"] & mis).sum()),
                "tml_copy_found_flagged": int(rows["map_tml_uid"].notna().sum()),
                "twice_by_category_year_level": by(t[t["map_twice"]], ["category", "map_tml_year", "map_tml_level"]),
                "other_copy_creator": t.loc[t["map_twice"], "map_other_creator"].value_counts().to_dict()},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(json.dumps({k: summary[k] for k in ("rows_by_category",)}, default=str))
    log(json.dumps(summary["stage0"]["held_as_by_category"], default=str))
    log(f"Stage 0 wrong dates (all TML rows): {summary['stage0']['wrong_dates_all_tml_rows']}; TML-only rows dated "
        f"wrong: {summary['stage0']['tml_only_rows_dated_wrong']}; clock: {summary['clock']['by_category_all_rows']}; "
        f"map twice: {summary['map']['twice_all_rows']}")


if __name__ == "__main__":
    sys.exit(main())
