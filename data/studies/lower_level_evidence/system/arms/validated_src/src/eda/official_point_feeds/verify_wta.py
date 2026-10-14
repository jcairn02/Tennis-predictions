"""Check the WTA API download: each point sequence replayed against the listed score, the timestamps' order, and the
point-by-point feed against the umpire's event log and the box score.

Inputs: the raw documents under data/raw/point_sources/wta/ (match lists, point-by-point, events, stats), read
through src/ingest/point_sources/wta.py.

What the documents look like (observed 24 Sep 2026; these observations are why the checks are built this way):
    point-by-point
        * gameScore is the game score after each point in fixed A/B order: 0, 15, 30, 40, A (advantage), G (the
          game's last point); tiebreak points as numbers, the last one included (7-0, not G).
        * pointWinner is wrong on some points: when a player at advantage loses the point, the score returns to
          deuce but pointWinner repeats the previous point's winner (1045/2024/LS001 points 89 and 160, where the
          umpire's log reads "advantage in" then "deuce"). Each point's winner is therefore derived from the score
          change, and pointWinner is only compared with it.
        * server is blank on tiebreak points and on every doubles point.
    events (the umpire's log)
        * an Ace is won by the server; a Fault with firstServe true is a first-serve fault (no point); a Fault
          without firstServe true is a double fault, won by the receiver; a Point record's firstServe says
          whether it was played on the first serve (true) or the second (false in 2024, absent in 2020).
        * scores are written server first in a regular game (0/15/30/40, "deuce", "advantage in" = the server's,
          "advantage out", "game"). A tiebreak's scores are numbers, written with the tiebreak's first server first
          in the 2020 logs and with each point's server first in 2026/2021/LS001's; some 2022 logs write "0-0" on
          every tiebreak point and end the tiebreak with "game".
        * the set and game numbers on a game-ending record are its own game's in the 2020 logs and the next
          game's in 1045/2024/LS001's, so games are cut from the scores instead.
        * a StateIndicator "Correction" either replaces the point before it (the next record redoes that point) or
          only precedes a let with the score unchanged.
        * in doubles, server names the team's first-listed player. At deuce in a doubles game (no-ad) the
          deciding point's record says only "game", so its winner is not recorded.
        * point records carry millisecond times; other records (state changes, challenges, overrules) are stamped
          to the second and can sit a few seconds out of order among them.
        * GameScore and MatchScore are filled in 2024 and empty in 2020; they are not used.
        * 2019 (batch B2): the logs are empty until March, and from Monterrey and Charleston (1 Apr) to Strasbourg
          (May) "bare": Point, Ace and Fault records with set, game and time but no Attributes, so no score,
          server, winner or serve number. A bare log is not replayed; its aces are checked against the box score.
          From Bol (4 Jun 2019) the logs are complete.
    listing
        * set scores in A/B order, ScoreTbSet the tiebreak loser's points, a doubles match tiebreak as a third set
          of 1-0 with the loser's points, Winner 2/3 (A/B won), 4/5 (by retirement), 6/7 (walkover).

Checks, per match with a point-by-point or an events document:
    numbering      pointNumber runs 1..n without gaps or repeats (point-by-point)
    timestamps     each point's UTC time is not earlier than the one before (the log's point records only)
    winner field   pointWinner against the winner derived from the score change (point-by-point)
    replay         point-by-point: the derived winners replayed under WTA rules (advantage games in singles;
                   no-ad games and a 10-point match tiebreak for the deciding set in doubles; 7-point tiebreaks at
                   6-6) must give the listing's set scores, tiebreak points and winner, end where the match ends
                   (or, after a retirement, at the listed score), and number sets and games as the feed does.
                   events: the log cut into games by its scores, each game's winner derived, and the games replayed
                   under the same rules, with tiebreaks where the rules put them. Games whose winner the log does
                   not record (no-ad deciding points, unwritten tiebreaks ended by a Point or by the next game)
                   are given the winners
                   that reproduce the listing when some assignment does; that is flagged, and is not an
                   independent check of those games
    agreement      where both documents exist: the same number of points and the same winner, point by point;
                   the log's aces and double faults against the box score (stats, set 0)

Outputs (data/studies/official_point_feeds/):
    wta_checks.csv          one row per match with a point-by-point or events document: the result of each check
    wta_mismatches.csv      one row per disagreement found by the checks
    wta_verification.json   the totals
Usage:
    ./python.sh src/eda/official_point_feeds/verify_wta.py [--years 2019-2026]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402

OUT = PROJECT_ROOT / "data" / "studies" / "official_point_feeds"
LADDER = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4, "G": 5}
EVENT_LADDER = {"0": 0, "15": 1, "30": 2, "40": 3}
EVENT_WORDS = {"deuce": (3, 3), "advantage in": (4, 3), "advantage out": (3, 4)}
WINNER_CODES = {"2": ("A", "played"), "3": ("B", "played"), "4": ("A", "retired"), "5": ("B", "retired"),
                "6": ("A", "walkover"), "7": ("B", "walkover")}
OTHER = {"A": "B", "B": "A"}


# --------------------------------------------------------------------------------------
# point winners (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def score_value(text) -> int | None:
    text = "" if text is None else str(text).strip().upper()
    if text in LADDER:
        return LADDER[text]
    return int(text) if text.isdigit() else None


def rose(before: tuple, after: tuple) -> int | None:
    """0 when the first count won the point, 1 when the second did, None when the change says neither.

    A count rising wins; a count falling back (advantage lost, back to deuce) loses."""
    (pa, pb), (va, vb) = before, after
    if va > pa and vb <= pb:
        return 0
    if vb > pb and va <= pa:
        return 1
    if va < pa and vb == pb:
        return 1
    if vb < pb and va == pa:
        return 0
    return None


def derived_winners(points: list[dict]) -> list[str | None]:
    """Each point's winner ("A"/"B") from the change of the point-by-point game score (rows of wta.point_rows)."""
    out, key, before = [], None, (0, 0)
    for p in points:
        if (p["set"], p["game"]) != key:
            key, before = (p["set"], p["game"]), (0, 0)
        after = (score_value(p["game_score_a"]), score_value(p["game_score_b"]))
        side = rose(before, after) if None not in after else None
        out.append(None if side is None else "AB"[side])
        if None not in after:
            before = after
    return out


def teams_of(match: dict) -> dict[str, str]:
    """Player id -> "A" or "B" from a listing row (both players of a doubles team)."""
    out = {}
    for side in ("A", "B"):
        for suffix in ("", "2"):
            pid = str(match.get(f"PlayerID{side}{suffix}") or "")
            if pid:
                out[pid] = side
    return out


def parse_event_score(text, *, tiebreak: bool):
    """An event's score text: a pair of counts (server's or first server's first), "game", or None."""
    text = str(text or "").strip().lower()
    if text == "game":
        return "game"
    if not tiebreak and text in EVENT_WORDS:
        return EVENT_WORDS[text]
    left, sep, right = text.partition("-")
    if not sep:
        return None
    if tiebreak:
        return (int(left), int(right)) if left.isdigit() and right.isdigit() else None
    return (EVENT_LADDER[left], EVENT_LADDER[right]) if left in EVENT_LADDER and right in EVENT_LADDER else None


FIRST_POINTS = ("15-0", "0-15", "1-0", "0-1", "0-0")  # scores a game's or a tiebreak's first point can leave


def one_point_apart(a: str, b: str) -> bool:
    """Whether score text ``b`` can follow ``a`` after one point (both as the log writes them, server first in a
    regular game; a tiebreak is judged by its point count, which does not depend on the orientation)."""
    if a == "game":
        return b in FIRST_POINTS
    tiebreak = is_tiebreak_score(a) or is_tiebreak_score(b)
    pa = parse_event_score(a, tiebreak=tiebreak)
    if b == "game":
        return isinstance(pa, tuple) and (tiebreak or max(pa) >= 3)
    pb = parse_event_score(b, tiebreak=tiebreak)
    if not (isinstance(pa, tuple) and isinstance(pb, tuple)):
        return False
    if tiebreak:
        return sum(pb) == sum(pa) + 1 or b == "0-0"
    step = (pb[0] - pa[0], pb[1] - pa[1])
    return step in ((1, 0), (0, 1)) or (pa, pb) in (((4, 3), (3, 3)), ((3, 4), (3, 3)))


def kind(record: dict) -> str | None:
    """A record's type: Attributes.type, falling back on Name. The two agree in every log but two of the 361 first
    fetched (Brisbane 2020, 800/2020/LS008 and LS010), where Name is shifted by one record against the rest of it
    ("Let" on a record typed "Point" with the score "game") and Attributes.type fits the scores."""
    return (record.get("Attributes") or {}).get("type") or record.get("Name")


def scoring_records(payload: dict) -> list[dict]:
    """The records that end a point, in log order: Point, Ace, and a Fault without firstServe true (a double
    fault); first-serve faults leave the point going on.

    A StateIndicator "Correction" sometimes replaces the point before it and sometimes only precedes a let with
    the score unchanged (21 of the 23 corrections in the 24 Sep sample). The point before it is dropped when the
    next scoring record follows from the score before that point rather than from its own
    (1003/2022/LS001: 30-15, then "30-30", a Correction, and an Ace to "40-15")."""
    out, pending = [], False
    for e in sorted(payload.get("Events") or [], key=lambda e: e.get("Index") or 0):
        attrs = e.get("Attributes") or {}
        if kind(e) == "StateIndicator" and attrs.get("reason") == "Correction":
            pending = bool(out)
        elif kind(e) in ("Point", "Ace") or (kind(e) == "Fault" and attrs.get("firstServe") is not True):
            if pending:
                before = _text(out[-2]) if len(out) > 1 else "game"
                prev, now = _text(out[-1]), _text(e)
                if now == prev or (one_point_apart(before, now) and not one_point_apart(prev, now)):
                    out.pop()
                pending = False
            out.append(e)
    return out


def tiebreak_lead(how: str, records: list[dict], i: int, teams: dict[str, str], before: tuple, parsed: tuple) -> str | None:
    """The side whose count record ``i`` of a tiebreak writes first, under orientation ``how``: "server" (the point's
    server), "next" (the next point's server; at the last point, whichever side makes a one-point step), "first"
    (the tiebreak's first server) or "A"."""
    if how == "A":
        return "A"
    if how == "first":
        return teams.get(_server(records[0]))
    if how == "server" or i + 1 < len(records):
        return teams.get(_server(records[i] if how == "server" else records[i + 1]))
    for lead in ("A", "B"):  # "next" at the tiebreak's last point
        after = parsed if lead == "A" else (parsed[1], parsed[0])
        if sum(after) == sum(before) + 1 and after[0] >= before[0] and after[1] >= before[1]:
            return lead
    return None


def tiebreak_orientation(records: list[dict], teams: dict[str, str]) -> str:
    """Whose count a tiebreak's scores write first. The log has used at least three conventions: the tiebreak's
    first server (the 2020 logs: 2014/2020/LS003 ends "4-7" on the first server's side, whom the listing has
    losing 4-7), each point's server (2026/2021/LS001), and the next point's server (894/2025/LD006, whose scores
    flip exactly where the serve changes hands). The one chosen is the one under which the most scores move by
    exactly one point from the one before; "A" (team A first) is only a last resort, since it mirrors "first"."""
    best, best_valid = "server", -1
    for how in ("server", "next", "first", "A"):
        before, valid = (0, 0), 0
        for i, e in enumerate(records):
            parsed = parse_event_score(_text(e), tiebreak=True)
            if not isinstance(parsed, tuple) or parsed == (0, 0):
                continue
            lead = tiebreak_lead(how, records, i, teams, before, parsed)
            if lead not in ("A", "B"):
                continue
            after = parsed if lead == "A" else (parsed[1], parsed[0])
            valid += sum(after) == sum(before) + 1 and after[0] >= before[0] and after[1] >= before[1]
            before = after
        if valid > best_valid:
            best, best_valid = how, valid
    return best


def _text(record: dict) -> str:
    return str((record.get("Attributes") or {}).get("score") or "").strip().lower()


def _server(record: dict) -> str:
    return str((record.get("Attributes") or {}).get("server") or "")


def is_tiebreak_score(text: str) -> bool:
    """A score only a tiebreak point leaves: two numbers, at least one outside 0/15/30/40 ("1-0", "6-6", "10-8"),
    or "0-0", which no point of a regular game can leave and which some logs write on every tiebreak point
    until the last (609/2022/LS105: "0-0" twelve times, then "5-7")."""
    left, sep, right = text.partition("-")
    if not (sep and left.isdigit() and right.isdigit()):
        return False
    return text == "0-0" or not (left in EVENT_LADDER and right in EVENT_LADDER)


def continues_tiebreak(here: str, there: str | None) -> bool:
    """Whether the next score is the tiebreak's next point: one point more, a score the log left unwritten
    ("0-0"), or "game", with which logs that leave the scores unwritten end the tiebreak (808/2022/LS001).
    A regular game's first point ("15-0", "0-15") never continues one; a long tiebreak's "15-15" can."""
    if there is None or there in ("15-0", "0-15") or here == "game":
        return False
    if there == "game":
        return True
    a = parse_event_score(here, tiebreak=True)
    b = parse_event_score(there, tiebreak=True)
    if not isinstance(b, tuple):
        return False
    if here == "0-0" or there == "0-0" or not isinstance(a, tuple):
        return is_tiebreak_score(there)
    return sum(b) == sum(a) + 1


def event_games(payload: dict, teams: dict[str, str] | None = None) -> list[dict]:
    """The log's points cut into games by their scores, not by the records' set and game numbers, which follow
    different conventions (a game-ending record carries the next game's number in 1045/2024/LS001's log and its
    own game's in the 2020 logs). A regular game ends at a "game" score, or when the next point is served by the
    other side; a tiebreak starts with a tiebreak score and ends when the next score does not continue it. Sides
    are compared through ``teams`` when given: after a SwapServer record, a doubles log can name the serving team's
    other player within the same game (1050/2026/LD006, after its game's first point)."""
    side = (lambda e: teams.get(_server(e), _server(e))) if teams else _server
    records = scoring_records(payload)
    games, current = [], []
    for i, e in enumerate(records):
        current.append(e)
        nxt = records[i + 1] if i + 1 < len(records) else None
        tiebreak = is_tiebreak_score(_text(current[0]))
        if tiebreak:
            ends = not continues_tiebreak(_text(e), _text(nxt) if nxt is not None else None)
        else:
            ends = _text(e) == "game" or nxt is None or side(nxt) != side(e)
        if ends:
            games.append({"tiebreak": tiebreak, "records": current,
                          "ended_by_score": tiebreak or _text(e) == "game"})
            current = []
    return games


def event_points(payload: dict, teams: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """The points of an events document with their derived winners, and its games.

    An Ace is won by the server and a double fault by the receiver. A regular game's scores are the server's
    count first, and "game" goes to the side that held game point; from deuce (the no-ad deciding point of a
    doubles game) its winner is not recorded and stays None. A tiebreak's scores are read in the orientation
    tiebreak_orientation finds; a tiebreak point the log wrote as "0-0" has no recorded winner. Each game carries
    its winner (a regular game's last point's; a tiebreak's from its last written score), whether it finished (a
    regular game on "game", a tiebreak at 7 or more with two clear; 10 is checked by the replay; a tiebreak whose
    scores are all unwritten once play goes on after it, as in 1160/2026/LS016's second set) and tiebreak
    points."""
    points, games = [], []
    segments = event_games(payload, teams)
    for n, game in enumerate(segments, 1):
        records, tiebreak = game["records"], game["tiebreak"]
        how = tiebreak_orientation(records, teams) if tiebreak else "server"
        before = (0, 0)  # (A, B) in a tiebreak; (server, receiver) in a regular game
        for i, e in enumerate(records):
            attrs = e.get("Attributes") or {}
            name = kind(e)
            server = teams.get(_server(e))
            parsed = parse_event_score(attrs.get("score"), tiebreak=tiebreak)
            winner = server if name == "Ace" else OTHER.get(server) if name == "Fault" else None
            if tiebreak:
                lead = tiebreak_lead(how, records, i, teams, before, parsed) if isinstance(parsed, tuple) else None
                if isinstance(parsed, tuple) and parsed != (0, 0) and lead in ("A", "B"):
                    after = parsed if lead == "A" else (parsed[1], parsed[0])
                    side = rose(before, after) if sum(after) == sum(before) + 1 else None
                    winner = winner or (None if side is None else "AB"[side])
                    before = after
            elif parsed == "game":
                srv, rcv = before
                winner = winner or (server if srv >= 3 and srv > rcv else
                                    OTHER.get(server) if rcv >= 3 and rcv > srv else None)
            elif isinstance(parsed, tuple):
                side = rose(before, parsed)
                winner = winner or (None if side is None or server is None else server if side == 0 else OTHER[server])
                before = parsed
            points.append({"game_seq": n, "set": e.get("Set"), "game": e.get("Game"), "index": e.get("Index"),
                           "server": server, "winner": winner,
                           "kind": "ace" if name == "Ace" else "double_fault" if name == "Fault" else "point",
                           "first_serve": attrs.get("firstServe") is True, "tiebreak": tiebreak,
                           "tiebreak_orientation": how if tiebreak else None, "score": attrs.get("score"),
                           "timestamp": e.get("Timestamp")})
        if tiebreak:
            written = before != (0, 0)
            tb = before if written else None
            if written and max(tb) >= 7 and abs(tb[0] - tb[1]) >= 2:
                finished, winner = True, "A" if tb[0] > tb[1] else "B"
            else:  # ended by a "game" record, or unwritten with play going on after it: its winner is known only
                # for an ace or a double fault
                finished = _text(records[-1]) == "game" or (not written and n < len(segments))
                winner = points[-1]["winner"] if finished else None
        else:
            tb, finished = None, game["ended_by_score"]
            winner = points[-1]["winner"] if records else None
        games.append({"tiebreak": tiebreak, "winner": winner, "finished": finished, "tb": tb, "points": len(records)})
    return points, games


def replay_games(games: list[dict], *, doubles: bool, sets_to_win: int = 2) -> dict:
    """Play a list of games (each with its winner, tiebreak flag and tiebreak points) under WTA rules: a set to six
    by two, a tiebreak at 6-6, a match tiebreak for the deciding set of a doubles match. The log's tiebreaks must
    fall where the rules put them. An unfinished last game (a retirement) is left out. Shaped like replay()."""
    sets, cur, won_sets = [], [0, 0], [0, 0]
    finished, stopped, extra = False, None, 0
    for i, g in enumerate(games, 1):
        if finished:
            extra += g["points"]
            continue
        if not g["finished"] and i == len(games):
            break
        deciding = won_sets[0] == won_sets[1] == sets_to_win - 1
        expect = "match_tiebreak" if doubles and deciding else "tiebreak" if cur == [6, 6] else "game"
        if (expect != "game") != g["tiebreak"]:
            stopped = f"game {i}: the log has {'a tiebreak' if g['tiebreak'] else 'a regular game'}, the rules {expect}"
            break
        if g["winner"] not in ("A", "B"):
            stopped = f"game {i}: winner unknown"
            break
        w = 0 if g["winner"] == "A" else 1
        tb = g["tb"] or (None, None)  # a tiebreak whose points the log left unwritten has no score to compare
        if expect == "match_tiebreak":
            sets.append({"a": 1 - w, "b": w, "tb_a": tb[0], "tb_b": tb[1]})
        else:
            cur[w] += 1
            if expect == "game" and not (max(cur) >= 6 and abs(cur[0] - cur[1]) >= 2):
                continue
            tb = tb if expect == "tiebreak" else (None, None)
            sets.append({"a": cur[0], "b": cur[1], "tb_a": tb[0], "tb_b": tb[1]})
            cur = [0, 0]
        won_sets[w] += 1
        finished = won_sets[w] == sets_to_win
    return {"sets": sets, "games": cur, "points": [0, 0], "finished": finished, "stopped": stopped,
            "extra_points": extra, "winner": ("A" if won_sets[0] > won_sets[1] else "B") if finished else None}


def resolve_unknown_games(games: list[dict], listed: dict, *, doubles: bool, limit: int = 12) -> tuple[list[dict] | None, int]:
    """Winners for the games the log leaves open (no-ad deciding points, unwritten tiebreaks) such that the replay
    gives the listing's score: returns the first such assignment and how many fit, or (None, 0). Not an independent
    check for those games; the others still are."""
    open_ = [i for i, g in enumerate(games) if g["winner"] not in ("A", "B") and g["finished"]]
    if not open_ or len(open_) > limit:
        return None, 0
    first, fits = None, 0
    for mask in range(2 ** len(open_)):
        trial = [dict(g) for g in games]
        for bit, i in enumerate(open_):
            trial[i]["winner"] = "B" if mask >> bit & 1 else "A"
        result = replay_games(trial, doubles=doubles)
        if not result["stopped"] and not score_differences(result, listed):
            fits += 1
            first = first or trial
    return first, fits


# --------------------------------------------------------------------------------------
# replay and comparison with the listing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def replay(winners: list[str | None], *, doubles: bool, sets_to_win: int = 2) -> dict:
    """Play the point winners under WTA rules; returns completed sets, the state reached and each point's place.

    Singles: advantage games, sets to six by two with a 7-point tiebreak at 6-6 in every set. Doubles: no-ad games
    and a 10-point match tiebreak in place of the deciding set. A point with no known winner stops the replay."""
    sets, per_point = [], []
    games, points, won_sets = [0, 0], [0, 0], [0, 0]
    finished, stopped, extra = False, None, 0
    for n, w in enumerate(winners, 1):
        if finished:
            extra += 1
            per_point.append(None)
            continue
        if w not in ("A", "B"):
            stopped = f"point {n}: winner unknown"
            break
        deciding = won_sets[0] == won_sets[1] == sets_to_win - 1
        kind = "match_tiebreak" if doubles and deciding else "tiebreak" if games == [6, 6] else "game"
        points[0 if w == "A" else 1] += 1
        per_point.append({"set": len(sets) + 1, "game": games[0] + games[1] + 1, "kind": kind})
        a, b = points
        if kind == "game":
            won = (0 if a >= 4 else 1 if b >= 4 else None) if doubles else \
                  (0 if a >= 4 and a - b >= 2 else 1 if b >= 4 and b - a >= 2 else None)
        else:
            target = 10 if kind == "match_tiebreak" else 7
            won = 0 if a >= target and a - b >= 2 else 1 if b >= target and b - a >= 2 else None
        if won is None:
            continue
        points = [0, 0]
        if kind == "match_tiebreak":
            sets.append({"a": 1 - won, "b": won, "tb_a": a, "tb_b": b})
        else:
            games[won] += 1
            if kind != "tiebreak" and not (max(games) >= 6 and abs(games[0] - games[1]) >= 2):
                continue
            tb = (a, b) if kind == "tiebreak" else (None, None)
            sets.append({"a": games[0], "b": games[1], "tb_a": tb[0], "tb_b": tb[1]})
            games = [0, 0]
        won_sets[won] += 1
        finished = won_sets[won] == sets_to_win
    return {"sets": sets, "games": games, "points": points, "finished": finished, "stopped": stopped,
            "extra_points": extra, "winner": ("A" if won_sets[0] > won_sets[1] else "B") if finished else None,
            "per_point": per_point}


def listing_result(match: dict) -> dict:
    """The listing's score: sets in A/B order with the tiebreak loser's points, the winning side and how it won."""
    sets = []
    for i in range(1, 6):
        a, b = match.get(f"ScoreSet{i}A"), match.get(f"ScoreSet{i}B")
        if a in (None, "") and b in (None, ""):
            continue
        tb = match.get(f"ScoreTbSet{i}") if i <= 4 else None
        sets.append({"a": int(a) if str(a).isdigit() else None, "b": int(b) if str(b).isdigit() else None,
                     "tb_loser": int(tb) if str(tb or "").isdigit() else None})
    side, how = WINNER_CODES.get(str(match.get("Winner") or ""), (None, None))
    result = (match.get("ResultString") or "").lower()
    if how is None:
        how = "retired" if "ret" in result else "walkover" if "w/o" in result else None
    return {"sets": sets, "winner": side, "how": how}


def result_string_sets(text: str | None) -> list[tuple[int, int]]:
    """Games per set from a ResultString, written from the winner's side: "7-6(6),2-1" -> [(7, 6), (2, 1)]."""
    out = []
    for part in re.findall(r"(\d+)-(\d+)(?:\(\d+\))?", (text or "").split(" d ", 1)[-1]):
        out.append((int(part[0]), int(part[1])))
    return out


def listing_consistent(match: dict) -> bool | None:
    """Whether the listing's set fields agree with its own result string (None when it has no result string).

    The result string is written from the winner's side at WTA events and in A/B order at the Slams; either reading
    counts, and a trailing 0-0 set (a retirement before it began) is ignored. They disagree now and then:
    800/2020/LS010's fields read 6-4 6-4 while its result string reads "7-6(6),2-1", which is what the umpire's log
    replays to."""
    listed = listing_result(match)
    written = result_string_sets(match.get("ResultString"))
    if not written or listed["winner"] not in ("A", "B"):
        return None
    fields = [(s["a"], s["b"]) for s in listed["sets"]]
    while fields and fields[-1] == (0, 0):
        fields.pop()
    from_winner = fields if listed["winner"] == "A" else [(b, a) for a, b in fields]
    return written in (from_winner, fields)


def score_differences(result: dict, listed: dict) -> list[str]:
    """How a replay disagrees with the listing (empty when it reproduces it)."""
    out = []
    sets = result["sets"]
    if listed["how"] == "retired":
        # the listing gives the score at the retirement: the completed sets and the set in progress
        if result["finished"]:
            out.append("the points finish the match, but the listing says it ended in a retirement")
        replayed = [(s["a"], s["b"]) for s in sets] + [tuple(result["games"])]
        wanted = [(s["a"], s["b"]) for s in listed["sets"]]
        if replayed != wanted and not (replayed[-1] == (0, 0) and replayed[:-1] == wanted):
            out.append(f"sets: replay {replayed}, listing {wanted} (retirement)")
        return out
    if not result["finished"]:
        out.append(f"the points stop before the match ends (replay at sets {[(s['a'], s['b']) for s in sets]}, "
                   f"games {result['games']}, points {result['points']})")
    if result["extra_points"]:
        out.append(f"{result['extra_points']} points after the replay ends the match")
    if len(sets) != len(listed["sets"]):
        out.append(f"the replay has {len(sets)} sets, the listing {len(listed['sets'])}")
    for i, (mine, theirs) in enumerate(zip(sets, listed["sets"]), 1):
        if (mine["a"], mine["b"]) != (theirs["a"], theirs["b"]):
            out.append(f"set {i}: replay {mine['a']}-{mine['b']}, listing {theirs['a']}-{theirs['b']}")
        if mine["tb_a"] is not None and min(mine["tb_a"], mine["tb_b"]) != theirs["tb_loser"]:
            out.append(f"set {i} tiebreak: replay {mine['tb_a']}-{mine['tb_b']}, listing loser {theirs['tb_loser']}")
    if result["finished"] and listed["winner"] and result["winner"] != listed["winner"]:
        out.append(f"winner: replay {result['winner']}, listing {listed['winner']}")
    return out


def parse_time(text) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def timestamp_check(stamps: list) -> dict:
    times = [parse_time(t) for t in stamps]
    known = [t for t in times if t is not None]
    back = sum(1 for x, y in zip(known, known[1:]) if y < x)
    gaps = [(y - x).total_seconds() for x, y in zip(known, known[1:])]
    return {"missing": len(times) - len(known), "decreases": back, "in_order": back == 0 and len(known) == len(times),
            "first": min(known).isoformat() if known else None, "last": max(known).isoformat() if known else None,
            "max_gap_seconds": max(gaps) if gaps else None}


def box_score(payload) -> dict | None:
    for row in payload if isinstance(payload, list) else []:
        if str(row.get("setnum")) == "0":
            return row
    return None


BARE_CHECK = "not checkable: no score, server or winner recorded"


def is_bare_log(records: list[dict]) -> bool:
    """A log whose Point, Ace and Fault records carry no Attributes: set, game and time only, with no score, server,
    point winner or serve number. All 662 logs from Monterrey and Charleston (1 Apr 2019) to Strasbourg (May 2019)
    are like this, and none before or since."""
    named = [e for e in records if e.get("Name") in ("Point", "Ace", "Fault")]
    return bool(named) and not any(e.get("Attributes") for e in named)


def check_bare_log(records: list[dict], box: dict | None, row: dict, miss) -> None:
    """What a bare log allows: its records counted, their times' order, and its Ace records against the box score's
    aces. Its double faults are not counted: without firstServe, a first-serve fault and a double fault look alike,
    and "a Fault right after a Fault" gives the attribute-based count in only 94% of the logs that have both."""
    named = [e for e in records if e.get("Name") in ("Point", "Ace", "Fault")]
    ts = timestamp_check([e.get("Timestamp") for e in named])
    aces = sum(e.get("Name") == "Ace" for e in named)
    row.update(events_form="bare", events_records=len(records),
               events_point_records=sum(e.get("Name") in ("Point", "Ace") for e in named),
               events_fault_records=sum(e.get("Name") == "Fault" for e in named), events_aces=aces,
               events_timestamps_in_order=ts["in_order"], events_timestamp_decreases=ts["decreases"],
               events_first_utc=ts["first"], events_last_utc=ts["last"], events_check=BARE_CHECK)
    if not ts["in_order"]:
        miss("events timestamps", f"{ts['decreases']} decreases among the records of a bare log, {ts['missing']} missing")
    if box is not None:
        listed_aces = (box.get("acesa") or 0) + (box.get("acesb") or 0)
        row.update(stats_aces=listed_aces, events_aces_agree=listed_aces == aces)
        if listed_aces != aces:
            miss("events vs box score", f"aces {aces} vs {listed_aces} (a bare log)")


# --------------------------------------------------------------------------------------
# the checks over the download
# --------------------------------------------------------------------------------------
def saved(receipts, tid: str, year: int, mid: str, endpoint: str):
    if W.endpoint_status(receipts, tid, year, mid, endpoint) != "200":
        return None
    path = W.endpoint_dest(tid, year, mid, endpoint)
    return P.read_json(path) if path.exists() else None


def check_sequence(prefix: str, winners: list, listed: dict, doubles: bool, row: dict, miss) -> dict:
    """Replay one source's winners against the listing; fills ``row`` with prefix_* columns."""
    result = replay(winners, doubles=doubles)
    row[f"{prefix}_replay_sets"] = " ".join(
        f"{s['a']}-{s['b']}" + (f"({min(s['tb_a'], s['tb_b'])})" if s["tb_a"] is not None else "")
        for s in result["sets"]) or None
    diffs = score_differences(result, listed) if not result["stopped"] else [f"replay stopped: {result['stopped']}"]
    row[f"{prefix}_score_reproduced"] = not diffs
    for d in diffs:
        miss(f"{prefix} score replay", d)
    return result


def check_match(edition: dict, match: dict, receipts, mismatches: list) -> dict | None:
    tid, year, mid = edition["tournament_id"], edition["year"], match["MatchID"]
    pbp = saved(receipts, tid, year, mid, "point-by-point")
    events = saved(receipts, tid, year, mid, "events")
    if pbp is None and events is None:
        return None
    key = f"{tid}/{year}/{mid}"
    draw = W.draw_of(match)
    doubles = match.get("DrawMatchType") == "D"
    listed = listing_result(match)
    consistent = listing_consistent(match)
    row = {"key": key, "tournament_id": tid, "year": year, "tier": edition["tier"], "draw": draw, "match_id": mid,
           "round": match.get("RoundID"), "result": match.get("ResultString"), "listing_how": listed["how"],
           "listing_consistent": consistent, "has_point_by_point": pbp is not None, "has_events": events is not None}

    def miss(check: str, detail: str) -> None:
        if check.endswith("score replay") and consistent is False:
            detail += " (the listing's own set scores disagree with its result string)"
        mismatches.append({"key": key, "year": year, "tier": edition["tier"], "draw": draw, "check": check,
                           "detail": detail})

    pbp_winners = None
    if pbp is not None:
        points = W.point_rows(tid, year, mid, pbp)
        row.update(pbp_status=pbp.get("matchStatus"), pbp_points=len(points))
        if points:
            numbers = [p["point_number"] for p in points]
            row["pbp_numbering_ok"] = numbers == list(range(1, len(points) + 1))
            if not row["pbp_numbering_ok"]:
                miss("pbp numbering", f"pointNumber runs {numbers[:3]}...{numbers[-3:]} over {len(points)} points")
            ts = timestamp_check([p["timestamp"] for p in points])
            row.update(pbp_timestamps_in_order=ts["in_order"], pbp_timestamp_decreases=ts["decreases"],
                       pbp_first_point_utc=ts["first"], pbp_last_point_utc=ts["last"],
                       pbp_max_gap_seconds=ts["max_gap_seconds"])
            if not ts["in_order"]:
                miss("pbp timestamps", f"{ts['decreases']} decreases, {ts['missing']} missing")
            pbp_winners = derived_winners(points)
            row["pbp_winners_underived"] = sum(1 for w in pbp_winners if w is None)
            wrong = [p["point_number"] for p, w in zip(points, pbp_winners) if w and p["point_winner"] != w]
            row["pbp_point_winner_field_disagrees"] = len(wrong)
            if wrong:
                miss("pbp pointWinner field", f"{len(wrong)} points: {wrong[:10]}")
            result = check_sequence("pbp", pbp_winners, listed, doubles, row, miss)
            placed = [(q["set"], q["game"]) if q else None for q in result["per_point"]]
            off = [(i, (p["set"], p["game"]), q) for i, (p, q) in enumerate(zip(points, placed), 1)
                   if q is not None and (p["set"], p["game"]) != q]
            row["pbp_set_game_numbering_disagrees"] = len(off)
            if off:
                miss("pbp set/game numbering", f"{len(off)} points; first at point {off[0][0]}: feed {off[0][1]}, "
                                               f"replay {off[0][2]}")
            row["pbp_server_blank"] = sum(1 for p in points if not p["server"])
    if events is not None:
        records = sorted(events.get("Events") or [], key=lambda e: e.get("Index") or 0)
        if is_bare_log(records):
            check_bare_log(records, box_score(saved(receipts, tid, year, mid, "stats")), row, miss)
            return row
        ev, games = event_points(events, teams_of(match))
        # the point records' times (milliseconds) are checked; other records (state changes, challenges,
        # overrules) are stamped to the second and can sit a few seconds out of order among them
        ts = timestamp_check([r["timestamp"] for r in ev])
        winners = [r["winner"] for r in ev]
        row.update(events_form="full" if ev else "empty", events_records=len(records), events_points=len(ev),
                   events_aces=sum(r["kind"] == "ace" for r in ev),
                   events_double_faults=sum(r["kind"] == "double_fault" for r in ev),
                   events_second_serve_points=sum(r["kind"] != "double_fault" and not r["first_serve"] for r in ev),
                   events_corrections=sum(1 for e in records if (e.get("Attributes") or {}).get("reason") == "Correction"),
                   events_timestamps_in_order=ts["in_order"], events_timestamp_decreases=ts["decreases"],
                   events_all_records_decreases=timestamp_check([e.get("Timestamp") for e in records])["decreases"],
                   events_first_utc=ts["first"], events_last_utc=ts["last"],
                   events_winners_unknown=sum(w is None for w in winners), events_games=len(games),
                   events_games_winner_unknown=sum(g["winner"] not in ("A", "B") and g["finished"] for g in games),
                   events_games_not_ended_by_score=sum(not g["finished"] for g in games[:-1]),
                   events_tiebreak_orientations=";".join(sorted({r["tiebreak_orientation"] for r in ev
                                                                 if r["tiebreak_orientation"]})) or None)
        if not ts["in_order"]:
            miss("events timestamps", f"{ts['decreases']} decreases among point records, {ts['missing']} missing")
        if row["events_games_not_ended_by_score"]:
            miss("events games", f"{row['events_games_not_ended_by_score']} games end without a game score")
        if games:
            unknown = row["events_games_winner_unknown"]
            if unknown:
                resolved, fits = resolve_unknown_games(games, listed, doubles=doubles)
                row["events_check"] = f"game replay, {unknown} unrecorded winners resolved by the listing ({fits} fits)" \
                    if resolved else f"game replay, {unknown} unrecorded winners unresolved"
                result = replay_games(resolved or games, doubles=doubles)
            else:
                row["events_check"] = "game replay"
                result = replay_games(games, doubles=doubles)
            diffs = score_differences(result, listed) if not result["stopped"] else [f"replay stopped: {result['stopped']}"]
            row["events_score_reproduced"] = not diffs
            row["events_replay_sets"] = " ".join(
                f"{s['a']}-{s['b']}" + (f"({min(s['tb_a'], s['tb_b'])})" if s["tb_a"] is not None else "")
                for s in result["sets"]) or None
            for d in diffs:
                miss("events score replay", d)
        if pbp_winners is not None and ev:
            row["events_points_agree"] = len(ev) == len(pbp_winners)
            if len(ev) != len(pbp_winners):
                miss("events vs point-by-point", f"{len(ev)} points in the log, {len(pbp_winners)} in point-by-point")
            else:
                differ = [i for i, (a, b) in enumerate(zip(winners, pbp_winners), 1) if a and b and a != b]
                row["events_winners_differ"] = len(differ)
                if differ:
                    miss("events vs point-by-point", f"winners differ on {len(differ)} points: {differ[:10]}")
        box = box_score(saved(receipts, tid, year, mid, "stats"))
        if box is not None and ev:
            aces = (box.get("acesa") or 0) + (box.get("acesb") or 0)
            dfs = (box.get("dblflta") or 0) + (box.get("dblfltb") or 0)
            row.update(stats_aces=aces, stats_double_faults=dfs, events_aces_agree=aces == row["events_aces"],
                       events_double_faults_agree=dfs == row["events_double_faults"])
            if not (row["events_aces_agree"] and row["events_double_faults_agree"]):
                miss("events vs box score", f"aces {row['events_aces']} vs {aces}; "
                                            f"double faults {row['events_double_faults']} vs {dfs}")
    return row


def share(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame:
        return None
    values = frame[column].dropna()
    return f"{int(values.astype(bool).sum())} of {len(values)}"


def run(years: list[int]) -> dict:
    receipts = P.receipts_for(W.SOURCE)
    rows, mismatches = [], []
    for edition in W.load_editions(years):
        for match in W.load_listing(edition["tournament_id"], edition["year"]):
            row = check_match(edition, match, receipts, mismatches)
            if row is not None:
                rows.append(row)
    checks = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    checks.to_csv(OUT / "wta_checks.csv", index=False)
    pd.DataFrame(mismatches, columns=["key", "year", "tier", "draw", "check", "detail"]).to_csv(
        OUT / "wta_mismatches.csv", index=False)
    summary = {"matches": len(checks)}
    if len(checks):
        pbp = checks[checks.get("pbp_points", pd.Series(dtype=float)).fillna(0) > 0] if "pbp_points" in checks else checks.iloc[0:0]
        ev = checks[checks.get("events_points", pd.Series(dtype=float)).fillna(0) > 0] if "events_points" in checks else checks.iloc[0:0]
        summary["point_by_point"] = {
            "matches_with_points": len(pbp), "points": int(pbp["pbp_points"].sum()) if len(pbp) else 0,
            "numbering_ok": share(pbp, "pbp_numbering_ok"), "timestamps_in_order": share(pbp, "pbp_timestamps_in_order"),
            "score_reproduced": share(pbp, "pbp_score_reproduced"),
            "set_game_numbering_ok": f"{int((pbp['pbp_set_game_numbering_disagrees'] == 0).sum())} of {len(pbp)}" if len(pbp) else None,
            "point_winner_field_wrong": {"matches": int((pbp["pbp_point_winner_field_disagrees"] > 0).sum()) if len(pbp) else 0,
                                         "points": int(pbp["pbp_point_winner_field_disagrees"].sum()) if len(pbp) else 0},
        }
        summary["events"] = {
            "matches_with_points": len(ev), "points": int(ev["events_points"].sum()) if len(ev) else 0,
            "timestamps_in_order": share(ev, "events_timestamps_in_order"),
            "score_reproduced": share(ev, "events_score_reproduced"),
            "checked_by": dict(Counter(ev["events_check"].fillna("none"))) if len(ev) else {},
            "points_agree_with_point_by_point": share(ev, "events_points_agree"),
            "winners_agree_with_point_by_point": f"{int((ev['events_winners_differ'] == 0).sum())} of {int(ev['events_winners_differ'].notna().sum())}"
            if "events_winners_differ" in ev else None,
            "aces_agree_with_box_score": share(ev, "events_aces_agree"),
            "double_faults_agree_with_box_score": share(ev, "events_double_faults_agree"),
        }
        bare = checks[checks["events_form"] == "bare"] if "events_form" in checks else checks.iloc[0:0]
        summary["events"]["bare_logs"] = {  # records without a score, server or winner (April-May 2019)
            "matches": len(bare), "check": BARE_CHECK, "timestamps_in_order": share(bare, "events_timestamps_in_order"),
            "aces_agree_with_box_score": share(bare, "events_aces_agree")}
        by = {}
        for (y, d), g in checks.groupby(["year", "draw"]):
            by[f"{y}|{d}"] = {"matches": len(g), "pbp_reproduced": share(g, "pbp_score_reproduced"),
                              "events_reproduced": share(g, "events_score_reproduced"),
                              "events_bare": int((g["events_form"] == "bare").sum()) if "events_form" in g else 0}
        summary["by_year_draw"] = by
    if len(checks):
        summary["listings_contradicting_their_result_string"] = int((checks["listing_consistent"] == False).sum())  # noqa: E712
    summary["mismatches_by_check"] = dict(Counter(m["check"] for m in mismatches))
    (OUT / "wta_verification.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", default="2019-2026")
    args = parser.parse_args()
    P.configure_stdout()
    summary = run(W.parse_years(args.years))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
