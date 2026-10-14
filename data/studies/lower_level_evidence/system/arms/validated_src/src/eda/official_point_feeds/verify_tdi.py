"""Checks of TDI Tennis Results (study official_point_feeds): what was listed, fetched and parsed; whether each
match's points replay to its result; duplicates; the ATP code; field fill by level, draw and month; pages answered
200 against 404 with points; and agreement with SofaScore and TennisLive where the point_shot_sources study holds
the same match.

Reads the staged tables in data/dump/points/tdi/ (matches, points, statistics). The comparison reads
data/dump/points/sofascore/ and tennislive/ through that study's links
(data/studies/point_shot_sources/scrape/verification_matches.csv), whose ref_id carries the ATP code
("<player>:atp:<year>/<tournament>/<match code>:<opponent>"): the same code as a TDI page's title, so the join is
exact.

The replay: advantage games in singles and no-ad games in doubles; sets to six games, a tiebreak to 7 at 6-6; best
of three sets; in doubles a match tiebreak to 10 in place of a third set (the ATP's rules outside the Slams).

Outputs in data/studies/official_point_feeds/:
    tdi_verification.json   every total
    tdi_accounting.csv      every match id: listed, fetched, parsed
    tdi_checks.csv          every match with points: replay, score against the header and the description, the
                            point score TDI shows after each point, aces and double faults against the page's own
                            statistics, clock order
    tdi_field_fill.csv      share of points carrying each field, by level, draw type, draw and month
    tdi_cross_source.csv    every linked match: games, winners, servers, points and score states against SofaScore
                            and TennisLive, and aces and double faults against their statistics

Usage:
    ./python.sh src/eda/official_point_feeds/verify_tdi.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import pyarrow.parquet as pq  # noqa: E402

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402

DUMP = P.DUMP_ROOT / "tdi"
OUT = F.STUDY_ROOT
LINKS = PROJECT_ROOT / "data" / "studies" / "point_shot_sources" / "scrape" / "verification_matches.csv"
FILL_FIELDS = ["time", "completed_utc", "serve", "outcome", "total_shots", "winning_shot_type", "error_type", "situation"]
POINT_COLUMNS = ["match_id", "point_id", "id_set", "id_game", "id_point", "set", "game", "point", "time", "winner",
                 "team_serving", "team_a_game_score", "team_b_game_score", "team_a_sets", "team_b_sets", "ace", "rally",
                 *FILL_FIELDS]
REF_ID = re.compile(r"^(?P<code>[^:]+):atp:(?P<year>\d{4})/(?P<tournament>\d+)/(?P<match>[a-z]+\d+):(?P<opponent>.*)$")
LADDER = ["0", "15", "30", "40"]
ADVANTAGE = {"Av": "A", "AD": "A", "A": "A"}


# --------------------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------------------
def table(path: Path, columns=None) -> list[dict]:
    return pq.read_table(path, columns=columns).to_pylist() if path.exists() else []


def points_by_match(columns: list[str]):
    """(match_id, points) for each match, points in page order: staging writes a match's points together."""
    path = DUMP / "points.parquet"
    if not path.exists():
        return
    current, bucket = None, []
    for batch in pq.ParquetFile(path).iter_batches(columns=columns, batch_size=100_000):
        for row in batch.to_pylist():
            if row["match_id"] != current:
                if bucket:
                    yield current, bucket
                current, bucket = row["match_id"], []
            bucket.append(row)
    if bucket:
        yield current, bucket


def month(row: dict) -> str:
    return (row.get("completed_on") or row.get("stamp") or "")[:7] or "?"


# --------------------------------------------------------------------------------------
# the replay (pure; tested offline)
# --------------------------------------------------------------------------------------
def game_state(a: int, b: int, doubles: bool) -> tuple[str, str]:
    """A game in play as TDI writes it: 0, 15, 30, 40, and 40 or Av at deuce in singles."""
    if not doubles and a >= 3 and b >= 3:
        return ("40", "40") if a == b else (("Av", "40") if a > b else ("40", "Av"))
    return LADDER[min(a, 3)], LADDER[min(b, 3)]


RANKS = {"0": 0, "15": 1, "30": 2, "40": 3, "Av": 4}


def score_winner(before: tuple, after: tuple, tiebreak: bool) -> str | None:
    """Who won a point by the change in TDI's point score (team A's, team B's): the side whose score rose, or whose
    opponent lost the advantage; None for a game's last point (the score reads 0-0 again) or an unreadable score."""
    if after == ("0", "0") and before != ("0", "0"):
        return None
    try:
        a0, b0, a1, b1 = (int(x) if tiebreak else RANKS[x] for x in (*before, *after))
    except (KeyError, TypeError, ValueError):
        return None
    if a1 > a0 or b1 < b0:
        return "teamA"
    if b1 > b0 or a1 < a0:
        return "teamB"
    return None


def set_games(text: str | None) -> dict:
    """A point's per-set games, "1:6/0 2:1/0" -> {1: 6, 2: 1}."""
    return {int(m.group(1)): int(m.group(2)) for m in re.finditer(r"(\d+):(\d+)/", text or "")}


def winner_contradictions(points: list[dict]) -> int:
    """Points whose ``winner`` differs from the side TDI's own score shows won it: the point score's change, or on
    a game's last point (the point score back at 0-0) the side whose games in the set went up."""
    games = []
    for p in points:
        key = (p["set"], p["game"])
        if not games or games[-1][0] != key:
            games.append((key, []))
        games[-1][1].append(p)
    out, prev_a, prev_b = 0, {}, {}
    for (set_no, game_no), ps in games:
        tiebreak, before = is_tiebreak(int(game_no), ps), ("0", "0")
        for p in ps:
            after = (p["team_a_game_score"], p["team_b_game_score"])
            said = score_winner(before, after, tiebreak)
            now_a, now_b = set_games(p.get("team_a_sets")), set_games(p.get("team_b_sets"))
            if said is None and after == ("0", "0") and before != ("0", "0"):
                s = int(set_no)
                up_a, up_b = now_a.get(s, 0) > prev_a.get(s, 0), now_b.get(s, 0) > prev_b.get(s, 0)
                said = "teamA" if up_a and not up_b else "teamB" if up_b and not up_a else None
            if said and p["winner"] in ("teamA", "teamB") and said != p["winner"]:
                out += 1
            before, prev_a, prev_b = after, now_a, now_b
    return out


def is_tiebreak(game_no: int, points: list[dict]) -> bool:
    """Game 13 of a set, or a game whose point scores leave the 0/15/30/40/Av ladder (the doubles match tiebreak)."""
    return game_no == 13 or any(s not in LADDER + ["Av"] for p in points
                                for s in (p["team_a_game_score"], p["team_b_game_score"]))


def set_winner(s: dict) -> str | None:
    """"a" or "b" for a finished set (six games and two clear, 7-6, or a match tiebreak), else None."""
    hi, lo = max(s["a"], s["b"]), min(s["a"], s["b"])
    if s["match_tiebreak"] or (hi >= 6 and hi - lo >= 2) or (hi == 7 and lo == 6):
        return "a" if s["a"] > s["b"] else "b"
    return None


def replay(points: list[dict], doubles: bool) -> dict:
    """Each game replayed from its point winners, game by game as TDI numbers them: advantage games in singles,
    no-ad games in doubles, tiebreaks to 7 and a doubles match tiebreak to 10. A game whose points stop before
    anyone has won it is a gap in the record; points after a game was won are counted, not replayed. TDI's point
    score after each point is compared with the replayed one (after a game's last point both read 0)."""
    groups = []
    for p in points:
        key = (int(p["set"]), int(p["game"]))
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(p)
    by_set, gaps = {}, []
    state_mismatches = extra = unknown = 0
    for (set_no, game_no), ps in groups:
        tiebreak = is_tiebreak(game_no, ps)
        match_tiebreak = doubles and tiebreak and game_no != 13
        score, winner = [0, 0], None
        for p in ps:
            w = {"teamA": 0, "teamB": 1}.get(p["winner"])
            if w is None:
                unknown += 1
                continue
            if winner is not None:
                extra += 1
                continue
            score[w] += 1
            if tiebreak:
                ended = score[w] >= (10 if match_tiebreak else 7) and score[w] - score[1 - w] >= 2
                state = ("0", "0") if ended else (str(score[0]), str(score[1]))
            else:
                ended = score[w] >= 4 and (doubles or score[w] - score[1 - w] >= 2)
                state = ("0", "0") if ended else game_state(score[0], score[1], doubles)
            if (p["team_a_game_score"], p["team_b_game_score"]) != state:
                state_mismatches += 1
            if ended:
                winner = w
        s = by_set.setdefault(set_no, {"a": 0, "b": 0, "tiebreak": None, "match_tiebreak": False})
        if winner is None:
            gaps.append(f"{set_no}.{game_no}")
            continue
        s["a" if winner == 0 else "b"] += 1
        if tiebreak:
            s.update(tiebreak=(score[0], score[1]), match_tiebreak=match_tiebreak)
    sets = [by_set[k] for k in sorted(by_set)]
    won = Counter(set_winner(s) for s in sets)
    winner = "teamA" if won["a"] >= 2 else "teamB" if won["b"] >= 2 else None
    return {"sets": sets, "winner": winner, "complete": winner is not None, "gaps": gaps,
            "state_mismatches": state_mismatches, "points_after_game_end": extra, "unknown_winner": unknown}


def header_games(text: str | None) -> list[int]:
    """Games per set of a scoreboard row, "1:7/7 2:6 3:1/10" -> [7, 6, 1] (tiebreak points left out)."""
    return [int(m.group(1)) for m in re.finditer(r"\d+:(\d+)(?:/\d+)?", text or "")]


def description_numbers(sets: list[dict], winner: str | None) -> list[int]:
    """The replayed score as the description writes it, from the winner's side ("7/6(5) 6/3", "4/6 6/4 10-6"),
    as its list of numbers."""
    first = "b" if winner == "teamB" else "a"
    second = "a" if first == "b" else "b"
    out = []
    for s in sets:
        if s["match_tiebreak"]:
            tb = s["tiebreak"] if first == "a" else (s["tiebreak"][1], s["tiebreak"][0])
            out += [tb[0], tb[1]]
        else:
            out += [s[first], s[second]]
            if s["tiebreak"]:
                out.append(min(s["tiebreak"]))
    return out


def result_check(match: dict, replayed: dict) -> dict:
    """The replay against the header's scoreboard (games per set) and the description's score. "reproduced":
    every game complete and the sets as the header's; "reproduced, unfinished": the same without a winner (a
    retirement); "points missing": a game stops before anyone won it; "differs": complete games, other sets."""
    header = list(zip(header_games(match.get("team_a_scores")), header_games(match.get("team_b_scores"))))
    sets = [(s["a"], s["b"]) for s in replayed["sets"]]
    if not header:
        result = "no header score"
    elif replayed["gaps"]:
        result = "points missing"
    elif sets == header:
        result = "reproduced" if replayed["complete"] else "reproduced, unfinished"
    else:
        result = "differs"
    wanted = [int(x) for x in re.findall(r"\d+", match.get("description_score") or "")]
    agrees = None
    if wanted and not replayed["gaps"]:
        # the description is from the winner's side; without a replayed winner (a retirement) either side may be it
        sides = [replayed["winner"]] if replayed["winner"] else ["teamA", "teamB"]
        agrees = any(wanted == description_numbers(replayed["sets"], side) for side in sides)
    return {"result": result, "replayed_sets": " ".join(f"{x}-{y}" for x, y in sets) or None,
            "header_sets": " ".join(f"{x}-{y}" for x, y in header) or None, "gaps": ";".join(replayed["gaps"]) or None,
            "description_agrees": agrees}


def serve_counts(points: list[dict]) -> dict:
    """Aces and double faults per team, from the points (the serving team's)."""
    out = Counter()
    for p in points:
        side = {"teamA": "a", "teamB": "b"}.get(p["team_serving"])
        if not side:
            continue
        if p["ace"] == "TRUE" or "ACE" in (p["rally"] or "").split("/"):
            out[f"aces_{side}"] += 1
        if p["serve"] == "DOUBLE FAULT":
            out[f"double_faults_{side}"] += 1
    return {k: out[k] for k in ("aces_a", "aces_b", "double_faults_a", "double_faults_b")}


def clock_check(points: list[dict]) -> dict:
    times = [p["time"] for p in points]
    back = sum(1 for x, y in zip(times, times[1:]) if x and y and y < x)
    ends_before = sum(1 for p in points if p["completed_utc"] and p["time"] and p["completed_utc"] < p["time"])
    return {"time_steps_back": back, "completed_before_time": ends_before, "points_without_time": sum(1 for t in times if not t)}


# --------------------------------------------------------------------------------------
# the comparison with SofaScore and TennisLive
# --------------------------------------------------------------------------------------
def norm_state(value) -> str:
    text = str(value if value is not None else "").strip()
    return ADVANTAGE.get(text, text)


def tdi_games(points: list[dict], side: str) -> dict:
    """{(set, game): points, winner, server and the states before the last point} from the career player's side
    ("teamA" or "teamB")."""
    games = defaultdict(list)
    for p in points:
        games[(int(p["set"]), int(p["game"]))].append(p)
    out = {}
    for key, ps in games.items():
        mine = side == "teamA"
        states = [(norm_state(p["team_a_game_score"]), norm_state(p["team_b_game_score"])) for p in ps[:-1]]
        out[key] = {"points": len(ps), "winner": "me" if ps[-1]["winner"] == side else "them",
                    "server": "me" if ps[0]["team_serving"] == side else "them",
                    "states": states if mine else [(y, x) for x, y in states]}
    return out


def sofascore_games(rows: list[dict], home_is_me: bool) -> dict:
    """SofaScore's games: states after each listed point, the game-winning point implied except in tiebreaks,
    where the final state is listed; ``scoring`` names the winner and ``serving`` the server (1 home, 2 away)."""
    games = defaultdict(list)
    for r in rows:
        games[(int(r["set"]), int(r["game"]))].append(r)
    out = {}
    for key, rs in games.items():
        rs.sort(key=lambda r: int(r["point"]))
        tiebreak = rs[0]["tiebreak"] == "TRUE"
        listed = [(norm_state(r["home_point"]), norm_state(r["away_point"])) for r in rs]
        states = listed[:-1] if tiebreak else listed
        me, them = ("1", "2") if home_is_me else ("2", "1")
        out[key] = {"points": len(listed) + (0 if tiebreak else 1),
                    "winner": "me" if rs[0]["scoring"] == me else "them" if rs[0]["scoring"] == them else None,
                    "server": "me" if rs[0]["serving"] == me else "them" if rs[0]["serving"] == them else None,
                    "states": states if home_is_me else [(y, x) for x, y in states]}
    return out


def tennislive_games(games_rows: list[dict], point_rows: list[dict], first_is_me: bool) -> dict:
    """TennisLive's games: the same convention as SofaScore's; ``winner_index`` and ``server_index`` are 0 for
    player 1 and 1 for player 2."""
    points = defaultdict(list)
    for r in point_rows:
        points[(int(r["set"]), int(r["game"]))].append(r)
    me, them = ("0", "1") if first_is_me else ("1", "0")
    out = {}
    for g in games_rows:
        key = (int(g["set"]), int(g["game"]))
        rs = sorted(points.get(key, []), key=lambda r: int(r["point"]))
        tiebreak = g["tiebreak"] == "TRUE"
        listed = [(norm_state(r["player1_point"]), norm_state(r["player2_point"])) for r in rs]
        states = listed[:-1] if tiebreak else listed
        out[key] = {"points": len(listed) + (0 if tiebreak else 1) if listed else None,
                    "winner": "me" if g["winner_index"] == me else "them" if g["winner_index"] == them else None,
                    "server": "me" if g["server_index"] == me else "them" if g["server_index"] == them else None,
                    "states": (states if first_is_me else [(y, x) for x, y in states]) if listed else None}
    return out


def compare_games(ours: dict, theirs: dict, prefix: str) -> dict:
    both = [k for k in ours if k in theirs]
    agree = lambda field: sum(1 for k in both if theirs[k][field] is not None and ours[k][field] == theirs[k][field])  # noqa: E731
    known = lambda field: sum(1 for k in both if theirs[k][field] is not None)  # noqa: E731
    out = {f"{prefix}_games": len(theirs), f"{prefix}_games_in_both": len(both)}
    for field in ("winner", "server", "points", "states"):
        out[f"{prefix}_{field}_agree"] = agree(field)
        out[f"{prefix}_{field}_known"] = known(field)
    out[f"{prefix}_identical"] = bool(both) and len(both) == len(ours) == len(theirs) and all(
        out[f"{prefix}_{f}_agree"] == out[f"{prefix}_{f}_known"] for f in ("winner", "server", "points", "states"))
    return out


def last_name_key(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", (name or "").split()[-1].casefold()) if name and name.split() else ""


def cross_source(linked: dict, tdi_rows: dict, stats_by_match: dict) -> list[dict]:
    """Every TDI match the point_shot_sources links reach: games against SofaScore and TennisLive, and aces and
    double faults against their statistics."""
    if not linked:
        return []
    sofa_ids = {r["sofa_id"] for r in linked.values() if r.get("sofa_id")}
    tl_ids = {r["tl_id"] for r in linked.values() if r.get("tl_id")}
    sofa_dir, tl_dir = P.DUMP_ROOT / "sofascore", P.DUMP_ROOT / "tennislive"
    filt = lambda path, column, ids, cols: pq.read_table(path, columns=cols, filters=[(column, "in", sorted(ids))]).to_pylist() \
        if path.exists() and ids else []  # noqa: E731
    sofa_points = defaultdict(list)
    for r in filt(sofa_dir / "points.parquet", "event_id", sofa_ids, ["event_id", "set", "game", "point", "home_point",
                                                                          "away_point", "serving", "scoring", "tiebreak"]):
        sofa_points[r["event_id"]].append(r)
    sofa_events = {r["event_id"]: r for r in filt(sofa_dir / "events.parquet", "event_id", sofa_ids,
                                                   ["event_id", "home_id", "away_id", "home_name", "away_name"])}
    sofa_stats = defaultdict(dict)
    for r in filt(sofa_dir / "statistics.parquet", "event_id", sofa_ids, ["event_id", "period", "name", "home_value", "away_value"]):
        if r["period"] == "ALL" and r["name"] in ("Aces", "Double faults"):
            sofa_stats[r["event_id"]][r["name"]] = (r["home_value"], r["away_value"])
    tl_games, tl_points = defaultdict(list), defaultdict(list)
    for r in filt(tl_dir / "games.parquet", "url", tl_ids, ["url", "set", "game", "server_index", "winner_index", "tiebreak"]):
        tl_games[r["url"]].append(r)
    for r in filt(tl_dir / "points.parquet", "url", tl_ids, ["url", "set", "game", "point", "player1_point", "player2_point"]):
        tl_points[r["url"]].append(r)
    tl_matches = {r["url"]: r for r in filt(tl_dir / "matches.parquet", "url", tl_ids, ["url", "player1_name", "player2_name"])}
    tl_stats = defaultdict(dict)
    for r in filt(tl_dir / "statistics.parquet", "url", tl_ids, ["url", "period", "name", "player1_value", "player2_value"]):
        if r["period"] == "match" and r["name"] in ("Aces", "Double faults"):
            tl_stats[r["url"]][r["name"]] = (r["player1_value"], r["player2_value"])
    sofa_team = P.study_players()
    out = []
    for match_id, link in sorted(linked.items()):
        match, points = tdi_rows[match_id]
        code = link["code"]
        side = "teamA" if code in (match.get("team_a_atp_ids") or "").split(";") else \
            "teamB" if code in (match.get("team_b_atp_ids") or "").split(";") else None
        row = {"match_id": match_id, "ref_id": link["ref_id"], "atp_code": match.get("atp_code"), "player": link.get("player"),
               "completed_on": match.get("completed_on"), "tournament": match.get("tournament"), "career_side": side}
        counts = serve_counts(points)
        mine, theirs = ("a", "b") if side == "teamA" else ("b", "a")
        row.update(tdi_aces=f"{counts['aces_' + mine]}-{counts['aces_' + theirs]}",
                   tdi_double_faults=f"{counts['double_faults_' + mine]}-{counts['double_faults_' + theirs]}")
        page = stats_by_match.get(match_id, {})
        if "Aces" in page:
            a, b = page["Aces"]
            row["tdi_page_aces"] = f"{a}-{b}" if side == "teamA" else f"{b}-{a}"
        if side is None:
            row["note"] = "the career player's ATP id is not on the page"
            out.append(row)
            continue
        ours = tdi_games(points, side)
        row["tdi_games"] = len(ours)
        event = sofa_events.get(link.get("sofa_id"))
        if event and sofa_points.get(link["sofa_id"]):
            home_is_me = str(event["home_id"]) == str(sofa_team.get(code))
            row.update(compare_games(ours, sofascore_games(sofa_points[link["sofa_id"]], home_is_me), "sofa"))
            for name, key in (("Aces", "aces"), ("Double faults", "double_faults")):
                if name in sofa_stats.get(link["sofa_id"], {}):
                    h, a = sofa_stats[link["sofa_id"]][name]
                    row[f"sofa_{key}"] = f"{h}-{a}" if home_is_me else f"{a}-{h}"
        tl = tl_matches.get(link.get("tl_id"))
        if tl and tl_games.get(link["tl_id"]):
            first_is_me = last_name_key(link.get("player")) == last_name_key(tl["player1_name"])
            theirs = tennislive_games(tl_games[link["tl_id"]], tl_points[link["tl_id"]], first_is_me)
            row.update(compare_games(ours, theirs, "tl"))
            # TennisLive's server_index (its page's server-ball marker) is read the other way round as well
            flipped = {k: {**v, "server": {"me": "them", "them": "me"}.get(v["server"])} for k, v in theirs.items()}
            row["tl_server_reversed_agree"] = compare_games(ours, flipped, "x")["x_server_agree"]
            for name, key in (("Aces", "aces"), ("Double faults", "double_faults")):
                if name in tl_stats.get(link["tl_id"], {}):
                    p1, p2 = tl_stats[link["tl_id"]][name]
                    row[f"tl_{key}"] = f"{p1}-{p2}" if first_is_me else f"{p2}-{p1}"
        for src in ("sofa", "tl"):
            for key in ("aces", "double_faults"):
                if row.get(f"{src}_{key}") is not None:
                    row[f"{src}_{key}_agree"] = row[f"{src}_{key}"] == row[f"tdi_{key}"]
        out.append(row)
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def write_csv(name: str, rows: list[dict]) -> str:
    fields = list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return P.rel(path)


def main() -> int:
    P.configure_stdout()
    matches = {r["match_id"]: r for r in table(DUMP / "matches.parquet")}
    stats_by_match = defaultdict(dict)
    for r in table(DUMP / "statistics.parquet", ["match_id", "period", "label", "team_a", "team_b"]):
        if r["period"] == "match" and r["label"] in ("Aces", "Double Faults"):
            stats_by_match[r["match_id"]][r["label"]] = (r["team_a"], r["team_b"])
    links = {}
    if LINKS.exists():
        with LINKS.open(encoding="utf-8", newline="") as handle:
            for r in csv.DictReader(handle):
                m = REF_ID.match(r.get("ref_id") or "")
                if m:
                    links[(m.group("year"), m.group("tournament"), m.group("match").upper())] = r
    by_code = {(r["atp_year"], r["atp_tournament_id"], r["atp_match_code"]): mid for mid, r in matches.items() if r.get("atp_code")}
    linked = {by_code[k]: v for k, v in links.items() if k in by_code}
    checks, fill, keep = [], defaultdict(Counter), {}
    point_ids, number_keys, duplicates = set(), set(), Counter()
    for match_id, points in points_by_match(POINT_COLUMNS):
        match = matches.get(match_id, {})
        for p in points:
            duplicates["point_id"] += p["point_id"] in point_ids
            point_ids.add(p["point_id"])
            key = (match_id, p["set"], p["game"], p["point"])
            duplicates["set_game_point"] += key in number_keys
            number_keys.add(key)
            duplicates["id_differs_from_numbers"] += (p["id_set"], p["id_game"], p["id_point"]) != (p["set"], p["game"], p["point"])
        doubles = match.get("draw_type") == "doubles"
        replayed = replay(points, doubles)
        counts = serve_counts(points)
        page = stats_by_match.get(match_id, {})
        row = {"match_id": match_id, "atp_code": match.get("atp_code"), "level": match.get("level"),
               "draw_type": match.get("draw_type"), "draw": match.get("draw"), "month": month(match),
               "http_status": match.get("http_status"), "points": len(points), **result_check(match, replayed),
               "state_mismatches": replayed["state_mismatches"], "points_after_game_end": replayed["points_after_game_end"],
               "unknown_winner": replayed["unknown_winner"], "winner_contradicts_score": winner_contradictions(points),
               **counts, **clock_check(points)}
        for name, key in (("Aces", "aces"), ("Double Faults", "double_faults")):
            if name in page:
                row[f"page_{key}"] = f"{page[name][0]}-{page[name][1]}"
                row[f"{key}_agree_with_page"] = row[f"page_{key}"] == f"{counts[key + '_a']}-{counts[key + '_b']}"
        checks.append(row)
        cell = fill[(match.get("level"), match.get("draw_type"), match.get("draw"), month(match))]
        cell["matches"] += 1
        cell["points"] += len(points)
        for field in FILL_FIELDS:
            cell[field] += sum(1 for p in points if p[field] not in (None, ""))
        if match_id in linked:
            keep[match_id] = (match, points)
    cross = cross_source({k: v for k, v in linked.items() if k in keep}, keep, stats_by_match)
    fill_rows = []
    for (level, draw_type, draw, mon), c in sorted(fill.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        fill_rows.append({"level": level, "draw_type": draw_type, "draw": draw, "month": mon, "matches": c["matches"],
                          "points": c["points"], **{f"{f}_share": round(c[f] / c["points"], 3) if c["points"] else None
                                                    for f in FILL_FIELDS}})
    accounting = [{k: r.get(k) for k in ("match_id", "in_index", "in_wayback_list", "id_source", "record", "record_reason",
                                         "http_status", "atp_code", "level", "draw_type", "draw", "completed_on",
                                         "listing_day", "round", "tournament", "points", "points_with_outcome")}
                  for r in matches.values()]
    docs = [r for r in matches.values() if r.get("record") in ("points", "no points")]
    challenger_singles = sorted((r["completed_on"], int(r["points_with_outcome"] or 0) > 0) for r in docs
                                if r.get("level") == "challenger" and r.get("draw_type") == "singles" and r.get("completed_on"))
    last_without = max((d for d, has in challenger_singles if not has), default=None)
    first_with = min((d for d, has in challenger_singles if has), default=None)
    summary = {
        "generated_at": P.utc_now_iso(),
        "accounting": {
            "ids": len(matches),
            "by_list_and_record": dict(Counter(f"{'index' if r['in_index'] == 'TRUE' else ''}"
                                               f"{'+' if r['in_index'] == 'TRUE' and r['in_wayback_list'] == 'TRUE' else ''}"
                                               f"{'wayback' if r['in_wayback_list'] == 'TRUE' else ''}|{r['record']}"
                                               for r in matches.values())),
            "documents_by_http_status": dict(Counter(r.get("http_status") for r in docs)),
            "documents_by_level_draw_type_draw": dict(sorted(Counter(f"{r.get('level')}|{r.get('draw_type')}|{r.get('draw')}"
                                                                     for r in docs).items())),
            "documents_by_month": dict(sorted(Counter(month(r) for r in docs).items())),
            "http_status_by_month": dict(sorted(Counter(f"{month(r)}|{r.get('http_status')}" for r in docs).items())),
            "atp_code_parsed": sum(1 for r in docs if r.get("atp_code")),
            "level_sources": dict(Counter(str(r.get("level_source")) for r in docs)),
            "unknown_level_tournaments": dict(Counter(r.get("tournament") for r in docs if r.get("level") == "unknown").most_common(20)),
        },
        "replay": {
            "matches": len(checks),
            "results": dict(Counter(r["result"] for r in checks)),
            "results_by_draw_type": dict(Counter(f"{r['draw_type']}|{r['result']}" for r in checks)),
            "description_agrees": dict(Counter(str(r["description_agrees"]) for r in checks)),
            "matches_with_state_mismatches": sum(1 for r in checks if r["state_mismatches"]),
            "state_mismatches": sum(r["state_mismatches"] for r in checks),
            "points_after_game_end": sum(r["points_after_game_end"] for r in checks),
            "games_with_points_missing": sum(len((r["gaps"] or "").split(";")) for r in checks if r["gaps"]),
            "matches_with_a_winner_contradicting_the_score": sum(1 for r in checks if r["winner_contradicts_score"]),
            "points_whose_winner_contradicts_the_score": sum(r["winner_contradicts_score"] for r in checks),
            "results_of_matches_without_contradiction": dict(Counter(r["result"] for r in checks if not r["winner_contradicts_score"])),
            "differs_examples": [r["match_id"] for r in checks if r["result"] == "differs"][:20],
            "points_missing_examples": [(r["match_id"], r["gaps"]) for r in checks if r["gaps"]][:20],
        },
        "aces_double_faults_against_the_page": {
            key: dict(Counter(str(r.get(f"{key}_agree_with_page")) for r in checks)) for key in ("aces", "double_faults")},
        "duplicates": dict(duplicates),
        "clock": {"matches_with_steps_back": sum(1 for r in checks if r["time_steps_back"]),
                  "steps_back": sum(r["time_steps_back"] for r in checks),
                  "completed_before_time": sum(r["completed_before_time"] for r in checks),
                  "points_without_time": sum(r["points_without_time"] for r in checks)},
        "challenger_singles_outcomes": {"last_match_without": last_without, "first_match_with": first_with,
                                        "matches_with_by_month": dict(sorted(Counter(
                                            f"{d[:7]}|{'with' if has else 'without'}" for d, has in challenger_singles).items()))},
        "cross_source": {
            "linked_matches": len(cross),
            "career_side_found": sum(1 for r in cross if r["career_side"]),
            **{f"{src}_{what}": sum(1 for r in cross if r.get(f"{src}_{what}")) for src in ("sofa", "tl") for what in ("identical",)},
            **{f"{src}_compared": sum(1 for r in cross if f"{src}_games" in r) for src in ("sofa", "tl")},
            **{f"{src}_{field}_agree_share": round(sum(r.get(f"{src}_{field}_agree", 0) for r in cross) /
                                                   max(1, sum(r.get(f"{src}_{field}_known", 0) for r in cross)), 4)
               for src in ("sofa", "tl") for field in ("winner", "server", "points", "states")},
            "tl_server_reversed_agree_share": round(sum(r.get("tl_server_reversed_agree", 0) for r in cross) /
                                                    max(1, sum(r.get("tl_server_known", 0) for r in cross)), 4),
            **{f"{src}_games_only_in_tdi": sum(r["tdi_games"] - r[f"{src}_games_in_both"] for r in cross if f"{src}_games" in r)
               for src in ("sofa", "tl")},
            **{f"{src}_{key}_agree": dict(Counter(str(r.get(f"{src}_{key}_agree")) for r in cross if f"{src}_{key}_agree" in r))
               for src in ("sofa", "tl") for key in ("aces", "double_faults")},
        },
        "files": [write_csv("tdi_accounting.csv", accounting), write_csv("tdi_checks.csv", checks),
                  write_csv("tdi_field_fill.csv", fill_rows), write_csv("tdi_cross_source.csv", cross)],
    }
    path = OUT / "tdi_verification.json"
    path.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("replay", "duplicates", "cross_source")}, indent=1, default=str)[:4000])
    print(f"written {P.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
