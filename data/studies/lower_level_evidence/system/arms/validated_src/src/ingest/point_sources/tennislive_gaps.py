"""TennisLive.net match pages for the data map's gap matches: Challengers 2018-2024, tour-level and Grand Slam
qualifying 2018-2026, and WTA 2018 (work package P5 of docs/studies/gap_downloads/collection-plan.md).

P4's event mode (tennislive_events.py) listed every event of 2018-2026 whole, each match with its page URL. This
mode links the map's gap matches to those listings and fetches their pages: the score after each point, game by
game (the game that closed each set is usually missing), the server, break-point markers and 8 match statistics.

1. Targets. Each gap's matches: its ``select`` under ``gaps:`` in data/data_map.yaml applied to
   data/studies/data_map/matches.parquet (best grain below ``below``; sofascore_editions.in_select). They are frozen
   at the first run in data/studies/gap_downloads/tennislive_<gap>_matches.csv.gz, every gap from the same map
   build: the pages lift matches out of the gaps once the map is rebuilt, so a later build would freeze fewer.
   --refresh-targets derives them again.
2. Events. Each edition of the targets (tour, tournament, year and ISO week of the map's date) goes to the
   TennisLive event holding most of the map's matches of that edition, gap or not, by player pairs: P4's rule
   (tennislive_events.link_editions).
3. Link. Candidates are the listed singles matches whose players both share a name word with the target's
   (sofascore_editions.words and pair_score, the rule of sofascore_editions.best_event), ordered by the words
   shared, then the target's draw, its round, its games per set, played, and the nearest to the map's date. The
   reference is the row of the file the map took the target from: Tennis My Life's or Sackmann's (round, score,
   box score), or API-Tennis's fixture (score and winner). A candidate is the target's own match (*confirmed*):
   * in the edition's event: its games per set equal the reference's, or the map's surname pair
     (data_map.measure.pair_key) and the round agree and so does a set's score, or the reference's match ended early
     (Tennis My Life's 'Prague' of 2020 is Prague I and II, where one pair met in the same round twice);
   * in another event within 10 days before to 21 after the map's date (an edition whose event lacks the match, or
     an edition that is two events): the games agree, and the surname pair or at least three name words;
   * elsewhere in the target's year (``another week``: Tennis My Life files the 2018 Irving Challenger under
     Dallas's name and date, and Biella 2-7 of 2021 under Biella 1's): the surname pair, games, draw and round agree;
   * with no reference (matches only TennisLive or the WTA's lists hold): the surname pair, in the edition's event
     or, elsewhere, in the target's week.
   They are asked in that order, except that games per set found in another event of the window come before a
   pair, round and set found in the edition's event; a target with no confirmed candidate keeps its edition's best
   candidate, unconfirmed. ``tl_selected``: confirmed, with a page URL,
   and in the target's draw or with the reference's games per set (API-Tennis files some Challenger qualifying
   matches as main-draw rounds, 'Final' or 'Semi-finals').
4. Fetch. The page of every selected link, newest first, once: the gaps overlap in WTA 2018 qualifying, and the
   pages the ten careers or P4's samples asked for are held already. Each receipt names the gaps that asked.
5. Stage. tennislive.stage(): every page on disk into matches, games, points and statistics
   (data/dump/points/tennislive/; ``gaps_in`` names the gaps whose targets link to a page).
6. Check, offline, against the row of the result file the map took each target from (Tennis My Life's or
   Sackmann's, read as verify_links reads them):
   * the link (``link_verdict``): the listed match's winner and games per set, verify_tennislive's verdicts;
   * the record (``record_verdict``): the page's games per set against the official score (the listed one where no
     file holds the match), with verify_scrape's rules: complete; only set-closing games missing; other shortfall;
     no points;
   * the statistics: the block read as a box score (aces, double faults, serve points, first serves in and won,
     second-serve points won, break points faced and saved) against the official one, the players aligned by name
     (tennislive_probe.tl_box and box_compare): every field equal; the two players' values exchanged
     (``box_swapped``, 2 of 36 sampled tour matches in the gap research); or differing.
7. Evidence (data/studies/gap_downloads/): tennislive_<gap>_matches.csv.gz (one row per target: the link, the page
   and the checks), tennislive_<gap>_editions.csv (each edition and its event), tennislive_gaps_summary.json and a
   line in runs.jsonl.

Raw: the player adapter's folder and receipts, data/raw/point_sources/tennislive/matches/<atp|wta>/<p1>-VS-<p2>/
<event>.html.gz, gzipped as served; logs in _logs/.

Pace and stops are common.Client's (Safari's TLS fingerprint, one request at a time, a --max-requests budget, a stop
on HTTP 429, a challenge or an unexpected 403), at the decision's 2 s + up to 1 s by default. TennisLive stopped
answering this address for about 35 minutes on 9 Oct 2026, after some 12,200 requests in seven hours, with no
refusal: after two requests in a row with no answer, the run pauses 30 minutes and goes on at 3 s + up to 2 s; four
pauses in a row with no answer between them stop it. TennisLive's terms forbid automated extraction; collected
under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md).

Usage:
    ./python.sh -m src.ingest.point_sources.tennislive_gaps --link-only                    # freeze and link, no HTTP
    ./python.sh -m src.ingest.point_sources.tennislive_gaps --limit 3 --max-requests 300   # a trial
    ./python.sh -m src.ingest.point_sources.tennislive_gaps --max-requests 40000           # the run (resumes)
    ./python.sh -m src.ingest.point_sources.tennislive_gaps --stage-only                   # no HTTP
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.data_map import measure as M                                      # noqa: E402
from src.eda.gap_downloads import verify_links as V                            # noqa: E402
from src.eda.gap_downloads import verify_tennislive as VT                      # noqa: E402
from src.eda.gap_sources import tennislive_probe as TP                         # noqa: E402
from src.eda.point_shot_sources.verify_scrape import COMPLETE, completeness, official_sets, short_kind  # noqa: E402
from src.ingest.point_sources import common as P                               # noqa: E402
from src.ingest.point_sources import sofascore_editions as SE                  # noqa: E402
from src.ingest.point_sources import tennislive as TL                          # noqa: E402
from src.ingest.point_sources import tennislive_events as TE                   # noqa: E402

SOURCE = TL.SOURCE
STUDY = TE.STUDY
MATCHES = SE.MATCHES
GAPS = ("challenger_points_2018_2021", "wta_2018_points", "challenger_points_2022_2024", "qualifying_points_2018_2026")
WEEK = (-3, 8)                      # days from the map's date (its tournament's Monday) that are the edition's own
MIN_WORDS_ELSEWHERE = 3             # name words a link outside the edition's event needs when the surnames differ
BOX_COLUMNS = [f"{side}_{k}" for side in ("w", "l") for k in TP.BOX]
API_TENNIS = M.HANDOFF / "api_tennis"

TARGET_COLUMNS = SE.TARGET_COLUMNS
OFFICIAL_COLUMNS = ["official", "official_round", "official_score", "official_winner", "official_box"]
LINK_COLUMNS = ["edition_event", "link_how", "link_confirmed", "link_names", "link_score", "tl_event_key",
                "tl_event_name", "tl_match_id", "tl_url", "tl_draw", "tl_round", "tl_state", "tl_played",
                "tl_end_reason", "tl_score", "tl_winner_side", "tl_player1", "tl_player2", "tl_start_utc",
                "tl_days_off", "tl_same_round", "tl_games_agree", "tl_set_agrees", "tl_selected", "link_verdict"]
PAGE_COLUMNS = ["page_status", "page_retrieved_at", "page_score", "pbp_available", "points_listed", "games_listed",
                "games_without_points", "record_games", "score_games", "score_from", "record_verdict",
                "point_game_share", "stats_available", "stats_rows", "box_compared", "box_fields", "box_fields_equal",
                "box_all_equal", "box_swapped", "box_max_abs_diff", "box_differences"]
EDITION_COLUMNS = ["gap", "edition", "tour", "tname", "year", "levels", "d_min", "d_max", "targets", "map_matches",
                   "event_key", "tl_name", "tl_kind", "tl_url", "matches_linked", "next_best_linked", "targets_linked",
                   "targets_in_event", "targets_elsewhere", "targets_selected"]
LISTED_READ = ["event_key", "event_name", "event_kind", "tour", "discipline", "junior", "played", "match_id", "url",
               "draw", "round", "state", "end_reason", "winner_side", "score", "player1_name", "player2_name",
               "start_utc"]
EPOCH = pd.Timestamp("1970-01-01")


# --------------------------------------------------------------------------------------
# targets
# --------------------------------------------------------------------------------------
def targets_path(gap: str) -> Path:
    return STUDY / f"tennislive_{gap}_matches.csv.gz"


def editions_path(gap: str) -> Path:
    return STUDY / f"tennislive_{gap}_editions.csv"


def derive_targets(gap: str, m: pd.DataFrame) -> pd.DataFrame:
    t = m[SE.in_select(m, SE.gap_select(gap))].copy()
    t.insert(0, "gap", gap)
    t["edition"] = SE.edition_key(t)
    return t[TARGET_COLUMNS].sort_values(["d", "edition", "uid"]).reset_index(drop=True)


def load_targets(gaps, refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    """Every gap's matches: frozen in its evidence table after the first run, else derived from the map. The gaps
    not frozen yet are derived from one read of the map and frozen at once, before anything is fetched."""
    frames, origins, todo = [], {}, []
    for gap in gaps:
        path = targets_path(gap)
        if path.exists() and not refresh:
            frames.append(pd.read_csv(path, usecols=TARGET_COLUMNS, parse_dates=["d"], keep_default_na=False,
                                      na_values=[""]))
            origins[gap] = f"frozen in {P.rel(path)}"
        else:
            todo.append(gap)
    if todo:
        m = pd.read_parquet(MATCHES)
        built = dt.datetime.fromtimestamp(MATCHES.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        STUDY.mkdir(parents=True, exist_ok=True)
        for gap in todo:
            t = derive_targets(gap, m)
            t.assign(d=t["d"].dt.date).to_csv(targets_path(gap), index=False)
            frames.append(t)
            origins[gap] = f"derived from {P.rel(MATCHES)} built {built}"
    targets = pd.concat(frames, ignore_index=True)
    targets["d"] = pd.to_datetime(targets["d"])
    return targets, origins


# --------------------------------------------------------------------------------------
# the official rows
# --------------------------------------------------------------------------------------
def official_rows(tnames) -> pd.DataFrame:
    """The result files' rows of these tournaments from 2018 on (verify_links.RESULT_FILES, Tennis My Life's first),
    keyed as the map keys its matches (verify_links.KEY: tournament, date, winner, loser, draw), with the round, the
    score and the box score."""
    cols = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"] + BOX_COLUMNS
    frames = []
    for source, pattern in V.RESULT_FILES:
        for path in sorted(V.RESULTS.glob(pattern)):
            year = M._year_of(path)
            if year is not None and year < M.FIRST_YEAR:
                continue
            names = set(pq.read_schema(path).names)
            f = pd.read_parquet(path, columns=[c for c in cols if c in names])
            f = f[f["tourney_name"].isin(tnames)]
            if len(f):
                frames.append(f.assign(official=source, qual_file=path.parent.name == "atp_qualifying"))
    if not frames:
        return pd.DataFrame(columns=list(dict.fromkeys(V.KEY + cols + ["official"])))
    rows = pd.concat(frames, ignore_index=True).reindex(columns=cols + ["official", "qual_file"])
    rows["d"] = M.to_date(rows["tourney_date"].astype(str), "%Y%m%d").dt.strftime("%Y-%m-%d")
    qual = rows["qual_file"].astype("boolean").fillna(False).astype(bool)
    rows["draw"] = np.where(qual | M.is_qual_round(rows["round"]), "qual", "main")
    return rows.drop_duplicates(V.KEY)


def box_json(row) -> str | None:
    """The official box score as tennislive_probe.box_compare reads it ({"w_ace": ..., "l_bpFaced": ...}), when the
    row has one (serve points above 0)."""
    box = {}
    for c in BOX_COLUMNS:
        v = row.get(c)
        try:
            if v is not None and str(v).strip() != "" and not pd.isna(v):
                box[c] = int(float(v))
        except (TypeError, ValueError):
            continue
    return json.dumps(box) if box.get("w_svpt", 0) > 0 else None


def api_tennis_sets(scores_json) -> list[tuple[int, int]]:
    """API-Tennis's set scores, first player first: a tiebreak set is written '6.4' / '7.7' (games.tiebreak)."""
    try:
        sets = json.loads(scores_json or "[]")
    except (TypeError, ValueError):
        return []
    out = []
    for s in sorted(sets, key=lambda s: int(str(s.get("score_set") or 0) or 0)):
        try:
            out.append((int(str(s["score_first"]).split(".")[0]), int(str(s["score_second"]).split(".")[0])))
        except (KeyError, TypeError, ValueError):
            return []
    return out


def api_tennis_refs(targets: pd.DataFrame) -> dict[tuple, dict]:
    """(first player, second player, day) -> the fixture's winner, round and score (winner first), for the targets
    the map took from API-Tennis (measure.load_api_tennis keeps the fixture's names and date)."""
    want = targets[targets["creator"].eq("api_tennis")]
    if want.empty or not API_TENNIS.exists():
        return {}
    keys = set(zip(want["name1"], want["name2"], want["d"].dt.strftime("%Y-%m-%d")))
    out = {}
    for path in sorted(API_TENNIS.glob("fixtures_*.csv*")):
        f = pd.read_csv(path, dtype=str, low_memory=False,
                        usecols=["event_date", "event_first_player", "event_second_player", "event_winner",
                                 "tournament_round", "scores_json"])
        f = f[[k in keys for k in zip(f["event_first_player"], f["event_second_player"], f["event_date"])]]
        for r in f.itertuples(index=False):
            side = {"First Player": 1, "Second Player": 2}.get(r.event_winner)
            sets = api_tennis_sets(r.scores_json)
            if side is None or not sets:
                continue
            winner = r.event_first_player if side == 1 else r.event_second_player
            score = " ".join(f"{a}-{b}" if side == 1 else f"{b}-{a}" for a, b in sets)
            out.setdefault((r.event_first_player, r.event_second_player, r.event_date),
                           {"winner": winner, "round": r.tournament_round, "score": score})
    return out


def official_for(targets: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Each target's reference row, found by the map's own key: Tennis My Life's or Sackmann's (file, round, score,
    box score; the winner is the map's name1), else API-Tennis's fixture (score and winner)."""
    table = {tuple(k): r for k, r in zip(official[V.KEY].itertuples(index=False, name=None),
                                         official.to_dict(orient="records"))}
    api = api_tennis_refs(targets)
    out = []
    for t in targets.itertuples(index=False):
        day = pd.Timestamp(t.d).strftime("%Y-%m-%d")
        r = table.get((t.tname, day, t.name1, t.name2, t.draw))
        a = api.get((t.name1, t.name2, day)) if r is None and t.creator == "api_tennis" else None
        if r is not None:
            out.append({"official": r["official"], "official_round": r.get("round"), "official_score": r.get("score"),
                        "official_winner": t.name1, "official_box": box_json(r)})
        elif a is not None:
            out.append({"official": "api_tennis", "official_round": a["round"], "official_score": a["score"],
                        "official_winner": a["winner"], "official_box": None})
        else:
            out.append({c: None for c in OFFICIAL_COLUMNS})
    return pd.DataFrame(out, index=targets.index, columns=OFFICIAL_COLUMNS)


# --------------------------------------------------------------------------------------
# linking (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def games_of(score) -> list[int]:
    """Games per set of a score, whichever player is written first: '7-6(6) 1-6 6-3' -> [13, 7, 9]."""
    return official_sets(score) if isinstance(score, str) and score.strip() else []


def link_key(score: int, c: dict, draw: str, rnd: str | None, games: list[int], day: int | None) -> tuple:
    """The order of candidates that share name words with a target: more words, the target's draw, its round, its
    games per set, played, then the nearest to the map's date."""
    near = -abs(c["day"] - day) if c["day"] is not None and day is not None else -10 ** 6
    return (score, c["draw"] == draw, rnd is not None and c["round"] == rnd, bool(games) and c["games"] == games,
            c["played"], near)


def scored(w1: frozenset, w2: frozenset, draw: str, rnd: str | None, games: list[int], day: int | None,
           cands) -> list[tuple[tuple, dict]]:
    """Every candidate whose players both share a name word with the target's, with its order key, best first."""
    out = []
    for c in cands:
        score = SE.pair_score(w1, w2, c["w1"], c["w2"])
        if score:
            out.append((link_key(score, c, draw, rnd, games, day), c))
    return sorted(out, key=lambda x: x[0], reverse=True)


def set_scores(score, listed: bool = False) -> frozenset:
    """A score's sets, each as its two games in order of size: '6-7(3) 7-5 6-3' -> {(6, 7), (5, 7), (3, 6)}."""
    if not isinstance(score, str):
        return frozenset()
    sets = VT.listed_sets(score, "1") if listed else VT.official_sets(score)
    return frozenset(tuple(sorted(s)) for s in sets)


def ended_early(score) -> bool:
    return bool(re.search(r"RET|DEF|W/O|ABD|ABN", str(score or ""), re.I))


def evidence(c: dict, pair, rnd: str | None, games: list[int], day: int | None, ref=None) -> dict:
    """What a candidate shares with its target beyond name words: the map's surname pair, the round, the games per
    set and a set's score (None where the target has no reference score: ``ref``), and the days from the map's
    date."""
    return {"pair_agrees": isinstance(pair, str) and c["pair"] == pair,
            "same_round": None if rnd is None or c["round"] is None else rnd == c["round"],
            "games_agree": (c["games"] == games) if games else None,
            "set_agrees": bool(c["sets"] & set_scores(ref)) or ended_early(ref) if games else None,
            "days_off": c["day"] - day if c["day"] is not None and day is not None else None}


def confirmed(how: str, ev: dict, words_shared: int, draw_agrees: bool = True, games_only: bool = False) -> bool:
    """Whether a candidate is the target's own match (module docstring, step 3); ``games_only`` asks the edition's
    event for the reference's games per set alone."""
    if ev["games_agree"] is None:                       # no reference: the surname pair, in the edition or its week
        if not ev["pair_agrees"]:
            return False
        return how == "edition's event" or (ev["days_off"] is not None and WEEK[0] <= ev["days_off"] <= WEEK[1])
    if how == "edition's event":
        return bool(ev["games_agree"]) or (not games_only and ev["pair_agrees"] and ev["same_round"] is True
                                           and bool(ev["set_agrees"]))
    if how == "another event":
        return bool(ev["games_agree"]) and (ev["pair_agrees"] or words_shared >= MIN_WORDS_ELSEWHERE)
    return (bool(ev["games_agree"]) and ev["pair_agrees"] and draw_agrees and ev["same_round"] is not False)


def pick(how: str, ranked: list[tuple[tuple, dict]], pair, rnd, games, day, draw: str, ref=None,
         games_only: bool = False):
    """The first confirmed candidate of ``ranked``: (candidate, words shared, evidence), or None."""
    for key, c in ranked:
        ev = evidence(c, pair, rnd, games, day, ref)
        if confirmed(how, ev, key[0], c["draw"] == draw, games_only):
            return c, key[0], ev
    return None


def listed_winner_agrees(winner: str, loser: str, name1: str, name2: str) -> bool:
    """Whether the listed winner is the official winner (``name1``): their name words agree at least as well that
    way round as the other."""
    W, L, A, B = (SE.words(x) for x in (winner, loser, name1, name2))
    direct = len(W & A) + len(L & B) if (W & A and L & B) else 0
    reverse = len(W & B) + len(L & A) if (W & B and L & A) else 0
    return direct > 0 and direct >= reverse


def link_verdict(name1: str, name2: str, official_score, tl_p1, tl_p2, tl_winner_side, tl_score,
                 tl_end_reason) -> str:
    """The linked listed match against the reference row (``name1`` its winner, its score winner first):
    verify_tennislive's verdicts, with the winner matched by name words as the link is."""
    if not isinstance(official_score, str):
        return "no official row"
    side = str(tl_winner_side or "").split(".")[0]
    if side not in ("1", "2"):
        return "no listed winner"
    winner, loser = (tl_p1, tl_p2) if side == "1" else (tl_p2, tl_p1)
    if not listed_winner_agrees(winner, loser, name1, name2):
        return "winner differs"
    ours, theirs = VT.listed_sets(tl_score, side), VT.official_sets(official_score)
    if not ours:
        return "winner agrees, no listed score"
    retired = "RET" in official_score.upper() or str(tl_end_reason).lower() == "retired"
    if retired:
        while theirs and theirs[-1] == (0, 0):          # the set never started
            theirs = theirs[:-1]
    if ours == theirs or (retired and len(ours) == len(theirs) and ours[:-1] == theirs[:-1]) or \
            (retired and ours[:len(theirs)] == theirs and len(ours) == len(theirs) + 1):
        return "agrees"
    if theirs and [(b, a) for a, b in theirs] == ours:
        return "winner agrees, official score written loser first"
    return "winner agrees, score differs"


# --------------------------------------------------------------------------------------
# the listings as link candidates
# --------------------------------------------------------------------------------------
def read_listed() -> tuple[pd.DataFrame, pd.DataFrame]:
    """P4's listed singles (every state; juniors left out) and its events."""
    li = pd.read_parquet(P.dump_path(SOURCE, "listed.parquet"), columns=LISTED_READ)
    li = li[li["discipline"].eq("singles") & ~li["junior"].eq("TRUE")].drop_duplicates(["event_key", "match_id"])
    ev = pd.read_parquet(P.dump_path(SOURCE, "events.parquet"),
                         columns=["key", "first_week", "url", "name", "kind", "section_status"])
    return li.reset_index(drop=True), ev


class Listing:
    """The listed singles as candidates: by event, and by tour and name word (built when first asked)."""

    def __init__(self, listed: pd.DataFrame, events: pd.DataFrame):
        first = events.set_index("key")["first_week"]
        day = pd.to_datetime(listed["start_utc"].str[:10].fillna(listed["event_key"].map(first)), errors="coerce")
        days = ((day - EPOCH).dt.days).astype("Int64")
        pair = M.pair_key(listed["player1_name"].map(M.surname_key), listed["player2_name"].map(M.surname_key))
        cache: dict = {}

        def w(name):
            if name not in cache:
                cache[name] = SE.words(name)
            return cache[name]

        self.rows = []
        self.by_event: dict[str, list[dict]] = defaultdict(list)
        for i, r in enumerate(listed.itertuples(index=False)):
            c = {"i": i, "event_key": r.event_key, "event_name": r.event_name, "tour": {"atp": "M", "wta": "W"}.get(r.tour),
                 "match_id": r.match_id, "url": r.url if isinstance(r.url, str) and r.url else None,
                 "draw": "qual" if r.draw == "qualifying" else "main", "round": M.canon_round(r.round),
                 "round_name": r.round, "state": r.state, "played": r.played == "TRUE", "end_reason": r.end_reason,
                 "winner_side": r.winner_side, "score": r.score, "games": games_of(r.score),
                 "sets": set_scores(r.score, listed=True),
                 "player1": r.player1_name, "player2": r.player2_name, "start_utc": r.start_utc,
                 "day": None if pd.isna(days.iat[i]) else int(days.iat[i]), "pair": pair.iat[i],
                 "w1": w(r.player1_name), "w2": w(r.player2_name)}
            self.rows.append(c)
            self.by_event[r.event_key].append(c)
        self._by_word: dict | None = None

    def in_event(self, key) -> list[dict]:
        return self.by_event.get(key, []) if isinstance(key, str) else []

    def near(self, tour: str, w1: frozenset, w2: frozenset, lo: int, hi: int) -> list[dict]:
        """The tour's listed matches dated ``lo`` to ``hi`` (days since 1970) whose players share a word with each."""
        if self._by_word is None:
            self._by_word = defaultdict(set)
            for c in self.rows:
                for word in c["w1"] | c["w2"]:
                    self._by_word[(c["tour"], word)].add(c["i"])
        a = set().union(*(self._by_word.get((tour, x), ()) for x in w1)) if w1 else set()
        b = set().union(*(self._by_word.get((tour, x), ()) for x in w2)) if w2 else set()
        return [self.rows[i] for i in sorted(a & b) if self.rows[i]["day"] is not None and lo <= self.rows[i]["day"] <= hi]


def edition_events(targets: pd.DataFrame, listed: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Each edition of the targets and the TennisLive event holding most of the map's matches of that edition, gap
    or not (P4's rule: same tour and surname pair, played 10 days before to 21 after the map's date)."""
    if MATCHES.exists():
        m = pd.read_parquet(MATCHES, columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname",
                                              "creator"])
        m["edition"] = SE.edition_key(m)
        e = m[m["edition"].isin(set(targets["edition"]))].copy()
    else:
        e = targets.copy()
    return TE.link_editions(e.assign(group=""), listed, events)


def days_of(day) -> int:
    return int((pd.Timestamp(day) - EPOCH).days)


def link_target(t, pair, listing: Listing, event: str | None) -> tuple[dict | None, str, bool]:
    """(candidate, how, confirmed) for one target (module docstring, step 3). With a reference score: the edition's
    event by its games per set, the window's other events, the edition's event by pair, round and a set, the
    target's year; without: the edition's event, then the window's other events. Failing all, the edition's best
    candidate, unconfirmed; else (None, "not linked", False)."""
    w1, w2 = SE.words(t.name1), SE.words(t.name2)
    ref = t.official_score if isinstance(t.official_score, str) else None
    day, rnd, games = days_of(t.d), M.canon_round(t.official_round), games_of(ref)
    ranked: dict[str, list] = {"edition's event": scored(w1, w2, t.draw, rnd, games, day, listing.in_event(event))}

    def candidates(how: str) -> list:
        if how not in ranked:
            if how == "another event":
                lo, hi = day + SE.LINK_DAYS[0], day + SE.LINK_DAYS[1]
            else:                                        # the target's year
                lo = days_of(pd.Timestamp(int(t.year), 1, 1)) + SE.LINK_DAYS[0]
                hi = days_of(pd.Timestamp(int(t.year), 12, 31)) + SE.LINK_DAYS[1]
            near = [c for c in listing.near(t.tour, w1, w2, lo, hi) if c["event_key"] != event]
            ranked[how] = scored(w1, w2, t.draw, rnd, games, day, near)
        return ranked[how]

    steps = ([("edition's event", True), ("another event", False), ("edition's event", False), ("another week", False)]
             if games else [("edition's event", False), ("another event", False)])
    for how, games_only in steps:
        found = pick(how, candidates(how), pair, rnd, games, day, t.draw, ref, games_only)
        if found is not None:
            return found, how, True
    if ranked["edition's event"]:
        key, c = ranked["edition's event"][0]
        return (c, key[0], evidence(c, pair, rnd, games, day, ref)), "edition's event", False
    return None, "not linked", False


def link_targets(targets: pd.DataFrame, listing: Listing, edition_event: dict) -> pd.DataFrame:
    """Each target's listed match, its evidence and whether its page is fetched (module docstring, step 3)."""
    pairs = M.pair_key(targets["name1"].map(M.surname_key), targets["name2"].map(M.surname_key))
    out = []
    for n, t in enumerate(targets.itertuples(index=False)):
        event = edition_event.get(t.edition)
        event = event if isinstance(event, str) else None
        found, how, ok = link_target(t, pairs.iat[n], listing, event)
        row = {"edition_event": event, "link_how": how, "link_confirmed": ok}
        if found is None:
            row.update(tl_selected=False, link_verdict="not linked")
        else:
            c, words_shared, ev = found
            winner = t.official_winner if isinstance(t.official_winner, str) else t.name1
            loser = t.name2 if winner == t.name1 else t.name1
            row.update(link_names="pair" if ev["pair_agrees"] else "words", link_score=words_shared,
                       tl_event_key=c["event_key"], tl_event_name=c["event_name"], tl_match_id=c["match_id"],
                       tl_url=c["url"], tl_draw=c["draw"], tl_round=c["round_name"], tl_state=c["state"],
                       tl_played=c["played"], tl_end_reason=c["end_reason"], tl_score=c["score"],
                       tl_winner_side=c["winner_side"], tl_player1=c["player1"], tl_player2=c["player2"],
                       tl_start_utc=c["start_utc"], tl_days_off=ev["days_off"], tl_same_round=ev["same_round"],
                       tl_games_agree=ev["games_agree"], tl_set_agrees=ev["set_agrees"],
                       tl_selected=ok and bool(c["url"]) and (c["draw"] == t.draw or ev["games_agree"] is True),
                       link_verdict=link_verdict(winner, loser, t.official_score, c["player1"], c["player2"],
                                                 c["winner_side"], c["score"], c["end_reason"]))
        out.append(row)
    return pd.DataFrame(out, index=targets.index).reindex(columns=LINK_COLUMNS)


def link(targets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The targets with their official rows and links, and the editions with their events (no HTTP)."""
    t0 = time.time()
    official = official_rows(set(targets["tname"].dropna()))
    frame = pd.concat([targets, official_for(targets, official)], axis=1)
    P.log(f"[{SOURCE}] official rows: {frame['official'].notna().sum():,} of {len(frame):,} targets "
          f"({frame['official_box'].notna().sum():,} with a box score); {time.time() - t0:.0f}s")
    listed, events = read_listed()
    editions = edition_events(frame, listed, events)
    edition_event = editions.set_index("edition")["event_key"].to_dict() if len(editions) else {}
    P.log(f"[{SOURCE}] {len(editions):,} editions, {editions['event_key'].notna().sum() if len(editions) else 0:,} "
          f"with a TennisLive event; {time.time() - t0:.0f}s")
    listing = Listing(listed, events)
    frame = pd.concat([frame, link_targets(frame, listing, edition_event)], axis=1)
    P.log(f"[{SOURCE}] linked {frame['link_confirmed'].eq(True).sum():,} of {len(frame):,} targets (confirmed); "
          f"{frame['tl_selected'].sum():,} selected; {time.time() - t0:.0f}s")
    return frame, editions


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def timed_out(r: dict) -> bool:
    return r.get("status") is None and "timed out" in str(r.get("error") or "").lower()


class Pauses:
    """Requests in a row that got no answer at all (every retry timed out). TennisLive dropped this address silently
    for about 35 minutes on 9 Oct 2026, after some 12,200 requests in seven hours, with no HTTP 403 or 429. After
    ``limit`` such requests the run pauses ``minutes`` and goes on at ``slower`` (seconds between requests, jitter);
    ``max_pauses`` pauses in a row with no answer between them stop it (Blocked)."""

    def __init__(self, client, limit: int = 2, minutes: float = 30.0, max_pauses: int = 4,
                 slower: tuple[float, float] = (3.0, 2.0), sleep=time.sleep):
        self.client, self.limit, self.minutes, self.max_pauses = client, limit, minutes, max_pauses
        self.slower, self.sleep = slower, sleep
        self.row, self.in_row = 0, 0
        self.log: list[dict] = []

    def note(self, r: dict) -> dict:
        if timed_out(r):
            self.row += 1
            if self.row >= self.limit:
                if self.in_row >= self.max_pauses:
                    raise P.Blocked(f"no answer after {self.in_row} pauses of {self.minutes:g} minutes "
                                    f"(the last error: {str(r.get('error'))[:120]})")
                self.in_row += 1
                self.row = 0
                self.log.append({"paused_at": P.utc_now_iso(), "minutes": self.minutes, "in_row": self.in_row,
                                 "requests_before": getattr(self.client, "requests", None)})
                P.log(f"[{SOURCE}] no answer to {self.limit} requests in a row: pausing {self.minutes:g} minutes "
                      f"(pause {self.in_row} in a row)")
                self.sleep(self.minutes * 60)
                if self.client is not None and hasattr(self.client, "min_interval"):
                    self.client.min_interval = max(self.client.min_interval, self.slower[0])
                    self.client.jitter = max(self.client.jitter, self.slower[1])
                P.log(f"[{SOURCE}] resuming at {getattr(self.client, 'min_interval', '?')} s + up to "
                      f"{getattr(self.client, 'jitter', '?')} s")
        elif r.get("status") is not None:
            self.row, self.in_row = 0, 0
        return r


def select_pages(frame: pd.DataFrame, limit: int | None = None) -> pd.DataFrame:
    """The pages to ask for: every selected link's URL, newest first, once, with the gaps that want it; with
    ``limit``, only those of each gap's ``limit`` newest editions."""
    f = frame[frame["tl_selected"].eq(True)]
    if limit:
        keep = set()
        for gap, g in f.groupby("gap"):
            keep |= {(gap, e) for e in g.sort_values("d", ascending=False, kind="stable")["edition"].drop_duplicates()
                     .head(limit)}
        f = f[[(g, e) in keep for g, e in zip(f["gap"], f["edition"])]]
    if f.empty:
        return pd.DataFrame(columns=["url", "gaps", "d", "start"])
    pages = f.assign(start=f["tl_start_utc"].fillna("")).groupby("tl_url").agg(
        gaps=("gap", lambda s: ";".join(sorted(set(s)))), d=("d", "max"), start=("start", "max")).reset_index()
    pages = pages.rename(columns={"tl_url": "url"})
    return pages.sort_values(["d", "start", "url"], ascending=False, kind="stable").reset_index(drop=True)


def outcome_of(r: dict) -> str:
    if timed_out(r):
        what = "timed out"
    else:
        what = str(r.get("error") or r.get("status"))[:40]
    return f"page:{what}" + (":cached" if r.get("skipped") else "")


def fetch_pages(client, receipts, pages: pd.DataFrame, pauses: Pauses, log_every: int = 100) -> Counter:
    """Each page, in order; a page whose request timed out is asked once more at the end."""
    outcomes, again = Counter(), []
    started = time.time()
    for n, row in enumerate(pages.itertuples(index=False), 1):
        r = TL.fetch_match(client, receipts, row.url, refresh=False, extra={"gaps": row.gaps})
        if timed_out(r):
            again.append(row)
        outcomes[outcome_of(r)] += 1
        pauses.note(r)
        if n % log_every == 0 or n == len(pages):
            rate = client.requests / max(time.time() - started, 1) * 3600
            P.log(f"[{SOURCE}] pages {n:,}/{len(pages):,} (date {pd.Timestamp(row.d).date()}); "
                  f"requests={client.requests:,} ({rate:,.0f}/h); "
                  + ", ".join(f"{k}={v:,}" for k, v in sorted(outcomes.items())))
    for row in again:
        r = TL.fetch_match(client, receipts, row.url, refresh=False, extra={"gaps": row.gaps})
        outcomes[outcome_of(r).replace("page:", "page again:")] += 1
        pauses.note(r)
    return outcomes


# --------------------------------------------------------------------------------------
# the records (from the staged tables)
# --------------------------------------------------------------------------------------
def record_verdict(points_listed, record: list[int], last_after: list, official: list[int]) -> str:
    """verify_scrape's rules, worded as P4's samples: complete; only set-closing games missing; other shortfall."""
    if not points_listed:
        return "no points"
    kind = completeness(official, record)
    if kind is None:
        return "no score to compare"
    if kind in COMPLETE:
        return "complete"
    if kind == "short":
        return ("only set-closing games missing" if short_kind(official, record, last_after) == "set closers only"
                else "other shortfall")
    return "other shortfall (more games than the score)"


def shapes(games: pd.DataFrame) -> dict[str, tuple[list[int], list]]:
    """URL -> (games listed per set, the games score after each set's last listed game), as page_record reads a
    page: a set with no game listed counts 0."""
    out = {}
    g = games.assign(set=pd.to_numeric(games["set"], errors="coerce"), game=pd.to_numeric(games["game"], errors="coerce"))
    g = g.dropna(subset=["set", "game"])
    g["set"] = g["set"].astype(int)
    for url, gu in g.groupby("url", sort=False):
        per_set = gu.groupby("set")["game"].max().astype(int).to_dict()
        last = {}
        for s, after in gu.groupby("set").tail(1)[["set", "after"]].itertuples(index=False, name=None):
            m = re.fullmatch(r"(\d+)-(\d+)", str(after or "").strip())
            last[s] = int(m.group(1)) + int(m.group(2)) if m else None
        sets = range(1, int(max(per_set)) + 1)
        out[url] = ([per_set.get(s, 0) for s in sets], [last.get(s) for s in sets])
    return out


def winner_index(p1, p2, winner: str, loser: str) -> int | None:
    """Which of the page's two players (0 or 1, page order) is the official winner, by name words."""
    a = 1 if listed_winner_agrees(p1, p2, winner, loser) else 0
    b = 1 if listed_winner_agrees(p2, p1, winner, loser) else 0
    return 0 if a > b else 1 if b > a else None


def records(frame: pd.DataFrame, receipts) -> pd.DataFrame:
    """The page columns of every target: what its page's receipt says, and from the staged tables its points,
    completeness against the official score (else the listed one) and its statistics against the official box."""
    urls = set(frame["tl_url"].dropna())
    out = pd.DataFrame(index=frame.index, columns=PAGE_COLUMNS, dtype=object)
    rec = {u: receipts.get(f"matches{u}") or {} for u in urls}
    out["page_status"] = [(rec[u].get("error") or rec[u].get("status") or "not fetched") if isinstance(u, str) else None
                          for u in frame["tl_url"]]
    out["page_retrieved_at"] = [rec[u].get("retrieved_at") if isinstance(u, str) else None for u in frame["tl_url"]]
    base = P.dump_path(SOURCE)
    if not urls or not (base / "matches.parquet").exists():
        return out
    pages = pd.read_parquet(base / "matches.parquet",
                            columns=["url", "page_status", "score", "pbp_available", "points_listed", "games_listed",
                                     "games_without_points", "stats_available", "stats_rows", "player1_name",
                                     "player2_name"])
    pages = pages[pages["url"].isin(urls) & pages["page_status"].eq("200")].drop_duplicates("url").set_index("url")
    games = pd.read_parquet(base / "games.parquet", columns=["url", "set", "game", "after"])
    shape = shapes(games[games["url"].isin(set(pages.index))])
    stats = pd.read_parquet(base / "statistics.parquet",
                            columns=["url", "period", "name", "player1_value", "player1_detail", "player2_value",
                                     "player2_detail"])
    stats = stats[stats["url"].isin(set(pages.index))]
    boxes = {u: TP.tl_box(g.to_dict(orient="records")) for u, g in stats.groupby("url", sort=False)}
    for i, t in zip(frame.index, frame.itertuples(index=False)):
        u = t.tl_url
        if not isinstance(u, str) or out.at[i, "page_status"] != 200:
            continue
        if u not in pages.index:
            out.at[i, "record_verdict"] = "not staged"
            continue
        p = pages.loc[u]
        points = int(pd.to_numeric(p["points_listed"], errors="coerce") or 0)
        record, last_after = shape.get(u, ([], []))
        if isinstance(t.official_score, str):
            score, source = games_of(t.official_score), "official"
        elif games_of(t.tl_score):
            score, source = games_of(t.tl_score), "listed"
        else:
            score, source = games_of(p["score"]), "page"
        listed_games = int(pd.to_numeric(p["games_listed"], errors="coerce") or 0)
        without = int(pd.to_numeric(p["games_without_points"], errors="coerce") or 0)
        total = sum(score)
        out.loc[i, ["page_score", "pbp_available", "points_listed", "games_listed", "games_without_points",
                    "record_games", "score_games", "score_from", "record_verdict", "point_game_share",
                    "stats_available", "stats_rows"]] = [
            p["score"], p["pbp_available"] == "TRUE", points, listed_games, without,
            " ".join(str(x) for x in record), " ".join(str(x) for x in score), source,
            record_verdict(points, record, last_after, score),
            round(min(listed_games - without, total) / total, 3) if total else None,
            p["stats_available"] == "TRUE", int(pd.to_numeric(p["stats_rows"], errors="coerce") or 0)]
        side = winner_index(p["player1_name"], p["player2_name"], t.name1, t.name2) if t.official_box else None
        # (a box score comes only from Tennis My Life's or Sackmann's rows, whose winner is the map's name1)
        check = TP.box_compare(t.official_box, boxes.get(u), side)
        for k in ("box_compared", "box_fields", "box_fields_equal", "box_all_equal", "box_swapped", "box_max_abs_diff",
                  "box_differences"):
            out.at[i, k] = check.get(k)
    return out


# --------------------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------------------
def edition_rows(frame: pd.DataFrame, editions: pd.DataFrame) -> pd.DataFrame:
    ev = editions.set_index("edition") if len(editions) else pd.DataFrame()
    rows = []
    for (gap, edition), g in frame.groupby(["gap", "edition"], sort=False):
        e = ev.loc[edition] if edition in ev.index else {}
        rows.append({"gap": gap, "edition": edition, "tour": g["tour"].iloc[0], "tname": g["tname"].iloc[0],
                     "year": int(g["year"].iloc[0]), "levels": ";".join(sorted(set(g["level"]))),
                     "d_min": g["d"].min().date(), "d_max": g["d"].max().date(), "targets": len(g),
                     "map_matches": e.get("matches"), "event_key": e.get("event_key"), "tl_name": e.get("tl_name"),
                     "tl_kind": e.get("tl_kind"), "tl_url": e.get("tl_url"), "matches_linked": e.get("matches_linked"),
                     "next_best_linked": e.get("next_best_linked"),
                     "targets_linked": int(g["link_confirmed"].eq(True).sum()),
                     "targets_in_event": int((g["link_confirmed"].eq(True) & g["link_how"].eq("edition's event")).sum()),
                     "targets_elsewhere": int((g["link_confirmed"].eq(True) & g["link_how"].isin(
                         ["another event", "another week"])).sum()),
                     "targets_selected": int(g["tl_selected"].eq(True).sum())})
    return pd.DataFrame(rows, columns=EDITION_COLUMNS)


def cell(g: pd.DataFrame) -> dict:
    fetched = g[g["page_status"].astype(str).eq("200")]
    v = fetched["record_verdict"].value_counts()
    share = pd.to_numeric(fetched["point_game_share"], errors="coerce")
    box = fetched[fetched["box_compared"].eq(True)]
    return {"targets": int(len(g)), "linked": int(g["link_confirmed"].eq(True).sum()),
            "selected": int(g["tl_selected"].eq(True).sum()), "pages": int(len(fetched)),
            "with_points": int(fetched["pbp_available"].eq(True).sum()),
            "complete": int(v.get("complete", 0)),
            "only_set_closing_missing": int(v.get("only set-closing games missing", 0)),
            "other_shortfall": int(sum(n for k, n in v.items() if str(k).startswith("other shortfall"))),
            "no_points": int(v.get("no points", 0)), "with_statistics": int(fetched["stats_available"].eq(True).sum()),
            "median_games_with_points": float(share.median()) if share.notna().any() else None,
            "box_compared": int(len(box)), "box_all_equal": int(box["box_all_equal"].eq(True).sum()),
            "box_swapped": int(box["box_swapped"].eq(True).sum()),
            "page_absent": int(g["page_status"].astype(str).eq("404").sum()),
            "page_not_fetched": int((g["tl_selected"].eq(True) & g["page_status"].astype(str).eq("not fetched")).sum())}


def tally(frame: pd.DataFrame) -> dict:
    out = {"all": cell(frame), "gaps": {}}
    for gap, g in frame.groupby("gap", sort=False):
        out["gaps"][gap] = {
            "all": cell(g),
            "by_year_level": {f"{y}|{lv}": cell(gg) for (y, lv), gg in g.groupby(["year", "level"])},
            "link_how": {f"{h}|{'confirmed' if c else 'unconfirmed'}": int(n) for (h, c), n in
                         g.groupby(["link_how", g["link_confirmed"].eq(True)]).size().items()},
            "link_names": g.loc[g["link_confirmed"].eq(True), "link_names"].value_counts().to_dict(),
            "link_verdict": {f"{v}|{'confirmed' if c else 'unconfirmed'}": int(n) for (v, c), n in
                             g.groupby(["link_verdict", g["link_confirmed"].eq(True)]).size().items()},
            "record_verdict": g["record_verdict"].fillna("none").value_counts().to_dict(),
            "official": g["official"].fillna("none").value_counts().to_dict(),
            "unconfirmed_by_creator": g.loc[~g["link_confirmed"].eq(True), "creator"].value_counts().to_dict(),
            "confirmed_in_other_draw": {
                "selected (games agree)": int((g["link_confirmed"].eq(True) & g["tl_draw"].ne(g["draw"])
                                               & g["tl_selected"].eq(True)).sum()),
                "not selected": int((g["link_confirmed"].eq(True) & g["tl_draw"].ne(g["draw"])
                                     & ~g["tl_selected"].eq(True)).sum())},
            "confirmed_without_page_url": g.loc[g["link_confirmed"].eq(True) & g["tl_url"].isna(), "tl_event_name"]
            .value_counts().to_dict()}
    pages = frame[frame["tl_selected"].eq(True)].drop_duplicates("tl_url")
    out["pages"] = {"selected": int(len(pages)),
                    "status": pages["page_status"].astype(str).value_counts().to_dict()}
    shared = frame[frame["tl_selected"].eq(True)].groupby("tl_url")["uid"].nunique()
    out["pages_linked_by_two_map_matches"] = int((shared > 1).sum())
    return out


def write_tables(frame: pd.DataFrame, editions: pd.DataFrame) -> None:
    STUDY.mkdir(parents=True, exist_ok=True)
    columns = TARGET_COLUMNS + OFFICIAL_COLUMNS + LINK_COLUMNS + PAGE_COLUMNS
    out = frame.assign(official_box=frame["official_box"].notna(), d=frame["d"].dt.date)   # the box: held or not
    for gap, g in out.groupby("gap", sort=False):
        g.reindex(columns=columns).sort_values(["d", "edition", "uid"]).to_csv(targets_path(gap), index=False)
        rows = edition_rows(frame[frame["gap"].eq(gap)], editions)
        rows.sort_values(["d_min", "edition"]).to_csv(editions_path(gap), index=False)


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def make_client(args) -> P.Client:
    return P.Client(TL.IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests)


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    gaps = [g.strip() for g in args.gaps.split(",") if g.strip()]
    targets, origins = load_targets(gaps, args.refresh_targets)
    P.log(f"[{SOURCE}] gaps {', '.join(gaps)}: {len(targets):,} targets, {targets['edition'].nunique():,} editions")
    for gap, origin in origins.items():
        P.log(f"[{SOURCE}]   {gap}: {int(targets['gap'].eq(gap).sum()):,} ({origin})")
    summary = {"source": SOURCE, "mode": "gaps", "gaps": gaps, "targets_from": origins, "started_at": P.utc_now_iso(),
               "args": vars(args)}
    receipts = P.receipts_for(SOURCE)
    frame, editions = link(targets)
    frame = pd.concat([frame, records(frame, receipts)], axis=1)
    write_tables(frame, editions)              # the links, before any request: the stage reads them (gaps_in)
    client = None if (args.stage_only or args.link_only) else make_client(args)
    outcomes = Counter()
    pauses = Pauses(client, minutes=args.pause_minutes, max_pauses=args.max_pauses)
    if client is not None:
        pages = select_pages(frame, args.limit)
        summary["pages_asked"] = int(len(pages))
        P.log(f"[{SOURCE}] {len(pages):,} pages to ask for (held ones are skipped); budget {args.max_requests:,}; "
              f"{args.min_interval} s + up to {args.jitter} s")
        try:
            outcomes = fetch_pages(client, receipts, pages, pauses)
        except (P.Blocked, P.BudgetExhausted) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["client"] = client.stats() if client is not None else None
    summary["pauses"] = pauses.log
    if not (args.no_stage or args.link_only):
        summary["staged"] = TL.stage(receipts)
    frame = pd.concat([frame.drop(columns=PAGE_COLUMNS), records(frame, receipts)], axis=1)
    write_tables(frame, editions)
    summary.update(tally(frame))
    summary["editions"] = {"all": int(len(editions)), "with_event": int(editions["event_key"].notna().sum())
                           if len(editions) else 0}
    summary["matches_selected"] = int(frame["tl_selected"].eq(True).sum())
    errors = [r for r in receipts.all().values() if r.get("error") and r["name"].startswith("matches/")
              and r.get("gaps")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("tennislive_gaps_summary.json", summary, root=STUDY)
    P.log(f"[{SOURCE}] {json.dumps(summary['all'])}")
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gaps", default=",".join(GAPS), help=f"comma list of gap ids (default {','.join(GAPS)})")
    parser.add_argument("--refresh-targets", action="store_true",
                        help="derive the gaps' matches from the current map instead of the frozen lists")
    parser.add_argument("--limit", type=int, help="fetch only the pages of each gap's N newest editions (trials)")
    parser.add_argument("--max-requests", type=int, default=40_000, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--pause-minutes", type=float, default=30.0,
                        help="pause after two requests in a row with no answer (default 30)")
    parser.add_argument("--max-pauses", type=int, default=4, help="stop after this many pauses in a row (default 4)")
    parser.add_argument("--link-only", action="store_true", help="freeze, link and write the evidence; no HTTP")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; restage the pages and rebuild the evidence")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; leave the staged tables as they are")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
