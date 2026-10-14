"""Checks of an IBM SlamTracker collection (Wimbledon; the US Open uses the same checks).

Reads the staged tables in data/dump/points/<source>/ (built by src/ingest/point_sources/slamtracker.py) and the
dump's copy of Sackmann's Slam archive; writes to data/studies/official_point_feeds/:

    <source>_checks.json          everything below in summary, plus the lists of problems
    <source>_coverage.csv         year x event: matches listed, statsLevel, each feed's outcomes, histories with
                                  points, "H" matches without points, and the 24 Sep research table's counts
    <source>_sackmann.csv         every match Sackmann's archive holds: point counts and whether the point-winner
                                  sequences agree (marker rows 0X/0Y excluded on both sides)
    <source>_sentences.csv        the Sentence of every point tallied into stroke x outcome; the ones naming no shot
                                  by pattern and event ("<actor> wins the point"), and any not parsed at all
    <source>_epoch_problems.csv   matches whose points lack EpochTimeStart/End or run out of order, jump by a day
                                  between two points, or end over 10 minutes after the listing's time
    <source>_result_problems.csv  matches whose points do not reproduce the listed result (sets won, winner), or
                                  that repeat a point row (same times, score and sentence as the row before)
    <source>_field_fill.csv       year x event: share of points with a value in each per-point field

A point is a history row whose PointNumber is numeric. The others are markers, kept verbatim in the staged table
and left out here: 0X and 0Y before play ("Players arrive on court.", "Players warming up.", epoch 0), <n>D for
"Match suspended." and <n>X, <n>Y when play resumes.

Sentence grammar (observed): "<player> <situation> with a(n) <shot>", where the situation is "wins the point",
"loses the game", "saves the break point", "fails to convert the break point" and the like, and the shot is
"<stroke> winner | forced error | unforced error", or "ace", "double fault", "service winner". The player named
is the one who hit the last shot, so the verb and the outcome both say who won the point; that is checked
against PointWinner through the players' names in the draw.

Usage:
    ./python.sh src/eda/official_point_feeds/slamtracker_checks.py --site wimbledon
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402

SACKMANN = P.DUMP_ROOT / "sackmann_archive" / "slam_pointbypoint"
RESEARCH_TABLE = ROOT / "data" / "studies" / "granular_data_leads" / "probe_logs" / "B_slams_coverage_table.json"
RESEARCH_KEY = {"wimbledon": "wim", "usopen": "uso"}

SERVE_SHOTS = {"ace": "ace", "double fault": "double fault", "service winner": "service winner"}
OUTCOMES = ("unforced error", "forced error", "winner")          # longest first
WIN_OUTCOMES = {"winner", "ace", "service winner"}
WIN_VERBS = ("wins", "saves", "converts", "breaks", "holds", "takes", "clinches")
LOSE_VERBS = ("loses", "fails", "drops", "concedes")
SIDES = ("forehand", "backhand")


# --------------------------------------------------------------------------------------
# pure parts (tested offline)
# --------------------------------------------------------------------------------------
def parse_sentence(text: str | None) -> dict | None:
    """Actor, situation, stroke and outcome of a point's Sentence, or None when it does not fit the grammar."""
    if not text:
        return None
    body = text.strip().rstrip(".")
    match = re.search(r" with an? (?P<shot>[a-z][a-z -]*)$", body)
    if not match:
        return None
    shot, head = match.group("shot").strip(), body[:match.start()]
    verb = re.search(r" (?P<verb>" + "|".join(WIN_VERBS + LOSE_VERBS) + r") (?P<rest>.+)$", head)
    if not verb:
        return None
    actor, situation = head[:verb.start()].strip(), f"{verb.group('verb')} {verb.group('rest')}"
    if shot in SERVE_SHOTS:
        stroke, outcome = "serve", SERVE_SHOTS[shot]
    else:
        outcome = next((o for o in OUTCOMES if shot == o or shot.endswith(" " + o)), None)
        if outcome is None:
            return None
        stroke = shot[: -len(outcome)].strip() or None
        if stroke is None:
            return None
    words = (stroke or "").split()
    side = words[0] if words and words[0] in SIDES else None
    kind = " ".join(words[1:]) if side else stroke
    return {"actor": actor, "situation": situation, "verb": verb.group("verb"), "shot": shot, "stroke": stroke,
            "side": side, "stroke_type": (kind or "groundstroke") if side else kind, "outcome": outcome,
            "actor_won": verb.group("verb") in WIN_VERBS}


def parse_situation(text: str | None) -> dict | None:
    """Actor and situation of any point Sentence with a known verb, whether or not it names a shot: doubles
    sentences mostly do not ("S. Hsieh/J. Ostapenko wins the point"). None for the marker rows and the rest."""
    if not text:
        return None
    body = re.sub(r" with an? [a-z][a-z -]*$", "", text.strip().rstrip("."))
    verb = re.search(r" (?P<verb>" + "|".join(WIN_VERBS + LOSE_VERBS) + r") (?P<rest>.+)$", body)
    if not verb:
        return None
    return {"actor": body[:verb.start()].strip(), "situation": f"{verb.group('verb')} {verb.group('rest')}",
            "verb": verb.group("verb"), "actor_won": verb.group("verb") in WIN_VERBS}


def first_difference(a: list, b: list) -> int | None:
    """Index of the first position where two sequences differ (the shorter length if one is a prefix), else None."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


DAY = 86_400


def is_day_jump(gap: float) -> bool:
    """A gap between consecutive points of one day plus an ordinary point interval: the spurious shift seen in
    matches suspended overnight (Wimbledon 2025 MS 1113: +86,446 s mid-set, then the real overnight gap)."""
    return DAY - 60 <= gap <= DAY + 900


PLAUSIBLE = (946_684_800, 4_102_444_800)  # 2000-01-01 to 2100-01-01 in Unix seconds


def epoch_problems(starts: list, ends: list) -> dict:
    """Fill and order of one match's per-point epochs (points in file order), and jumps between points. A value
    outside 2000-2100 counts as implausible, not filled, and is left out of the order checks: Wimbledon 2026 MS 1127
    has EpochTimeEnd 93,053 and the like from point 202 on, while its EpochTimeStart stays right."""
    def num(v):
        text = str(v or "").strip()
        return int(text) if text.isdigit() and int(text) > 0 else None

    raw_s, raw_e = [num(v) for v in starts], [num(v) for v in ends]
    plausible = lambda v: v is not None and PLAUSIBLE[0] <= v <= PLAUSIBLE[1]
    s, e = [v if plausible(v) else None for v in raw_s], [v if plausible(v) else None for v in raw_e]
    out = {"points": len(s), "start_missing": sum(v is None for v in raw_s), "end_missing": sum(v is None for v in raw_e),
           "start_implausible": sum(1 for v in raw_s if v is not None and not plausible(v)),
           "end_implausible": sum(1 for v in raw_e if v is not None and not plausible(v)),
           "end_before_start": 0, "start_backwards": 0, "end_backwards": 0, "overlaps_previous": 0,
           "day_jumps": 0, "first_day_jump_at_point": None, "gaps_over_1h": 0, "last_gap_s": None}
    prev_s = prev_e = None
    for n, (a, b) in enumerate(zip(s, e), 1):
        if n == len(e) and b is not None and prev_e is not None:
            out["last_gap_s"] = b - prev_e
        if a is not None and b is not None and b < a:
            out["end_before_start"] += 1
        if a is not None and prev_s is not None and a < prev_s:
            out["start_backwards"] += 1
        if b is not None and prev_e is not None and b < prev_e:
            out["end_backwards"] += 1
        if a is not None and prev_e is not None and a < prev_e:
            out["overlaps_previous"] += 1
        if b is not None and prev_e is not None:
            if is_day_jump(b - prev_e):
                out["day_jumps"] += 1
                out["first_day_jump_at_point"] = out["first_day_jump_at_point"] or n
            elif b - prev_e > 3600:
                out["gaps_over_1h"] += 1
        prev_s = a if a is not None else prev_s
        prev_e = b if b is not None else prev_e
    out["filled"] = not (out["start_missing"] or out["end_missing"] or out["start_implausible"] or out["end_implausible"])
    out["in_order"] = out["end_before_start"] == 0 and out["start_backwards"] == 0 and out["end_backwards"] == 0
    return out


def name_key(name: str) -> str:
    """A name without case, spaces, dots or apostrophes, so the feed's slips still match ("C.O'Connell", "C Gauff",
    and the US Open's "C. O''Connell")."""
    return re.sub(r"[\s.'’`]", "", str(name)).lower()


def actor_side(actor: str, names: dict[int, set[str]]) -> int | None:
    """1 or 2 when the actor's name belongs to exactly one side's players (display or last names)."""
    key = name_key(actor)
    sides = [side for side, known in names.items() if key in {name_key(k) for k in known}]
    return sides[0] if len(sides) == 1 else None


def set_complete(g1, g2) -> bool:
    """A set's games show it finished: six or more with a two-game lead, or a tiebreak at 6-6 or 12-12."""
    try:
        hi, lo = max(int(g1), int(g2)), min(int(g1), int(g2))
    except (TypeError, ValueError):
        return False
    return (hi >= 6 and hi - lo >= 2) or (hi, lo) in ((7, 6), (13, 12))


def result_from_points(rows: list[dict]) -> dict:
    """Sets won by each side, replayed from one match's points in file order: a set belongs to the PointWinner of
    its last point. Every set followed by another is complete (the games counter sometimes lags on a set's last
    point); the last set counts when its games show it finished or its last Sentence ends the match ("wins the
    match", "loses the match"). The SetWinner and MatchWinner flags are not used: they are often unset on the
    deciding point before 2024 (2021 MS 1113) and stray on a few points (2025 MS 1201). Repeated rows (the same
    times, score and sentence as the row before) are counted."""
    last_of_set: dict[str, dict] = {}
    repeated, previous = 0, None
    for row in rows:
        last_of_set.pop(row.get("SetNo"), None)  # keep sets in order of their last point
        last_of_set[row.get("SetNo")] = row
        key = tuple(row.get(k) for k in ("EpochTimeStart", "EpochTimeEnd", "P1Score", "P2Score", "Sentence"))
        repeated += int(key == previous)
        previous = key
    lasts = list(last_of_set.values())
    match_point = bool(lasts) and " the match" in str(rows[-1].get("Sentence") or "")
    won = Counter()
    for n, row in enumerate(lasts, 1):
        if n < len(lasts) or match_point or set_complete(row.get("P1GamesWon"), row.get("P2GamesWon")):
            won[str(row.get("PointWinner"))] += 1
    s1, s2 = won.get("1", 0), won.get("2", 0)
    return {"sets_1": s1, "sets_2": s2, "sets_played": len(lasts), "ends_on_match_point": match_point,
            "winner": "1" if s1 > s2 else "2" if s2 > s1 else None, "repeated_rows": repeated}


def sets_from_score(sets) -> tuple[int, int, int]:
    """Sets won by each side according to a listing's own scores.sets, and the number of sets listed."""
    s1 = s2 = 0
    for pair in sets or []:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        a, b = ((x or {}).get("score") for x in pair)
        if set_complete(a, b):
            if int(a) > int(b):
                s1 += 1
            else:
                s2 += 1
    return s1, s2, len(sets or [])


# --------------------------------------------------------------------------------------
# checks over the staged tables
# --------------------------------------------------------------------------------------
def load_site(key: str):
    module = importlib.import_module(f"src.ingest.point_sources.{key}")
    return module.SITE


def read(source: str, name: str, columns=None) -> pd.DataFrame:
    path = P.dump_path(source, f"{name}.parquet")
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    schema = pq.read_schema(path).names
    cols = [c for c in (columns or schema) if c in schema]
    return pq.read_table(path, columns=cols).to_pandas()


def coverage(site, matches: pd.DataFrame, points: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    research = defaultdict(dict)
    if RESEARCH_TABLE.exists():
        for slam, year, event, total, h, s_, other in json.loads(RESEARCH_TABLE.read_text(encoding="utf-8")):
            research[(slam, int(year), event)] = {"total": total, "H": h, "S": s_, "other": other}
    key = RESEARCH_KEY.get(site.key, site.key)
    feed_names = [f.name for f in site.feeds]
    rows, problems = [], {"H_without_points": [], "points_but_not_H": []}
    for (year, event), group in matches.groupby(["year", "event"], sort=True):
        year = int(year)
        points_n = pd.to_numeric(group["history_points"], errors="coerce").fillna(0)
        row = {"year": year, "event": event, "listed": len(group),
               "in_draw": int(group["listed_in"].str.contains("draw").sum()),
               "in_days": int(group["listed_in"].str.contains("days").sum()),
               "H": int((group["stats_level"] == "H").sum()), "not_H": int((group["stats_level"] != "H").sum()),
               "held_by_sackmann": int((group["held_by_sackmann"] == "TRUE").sum()),
               "histories_with_points": int((points_n > 0).sum()), "points": int(points_n.sum())}
        for name in feed_names:
            counts = group[f"{name}_outcome"].value_counts()
            for value in ("ok", "absent", "blocked", "error", "unreadable", "not requested", "not applicable"):
                row[f"{name}_{value.replace(' ', '_')}"] = int(counts.get(value, 0))
        h = group[group["stats_level"] == "H"]
        missing = h[pd.to_numeric(h["history_points"], errors="coerce").fillna(0) <= 0]
        row["H_without_points"] = len(missing)
        problems["H_without_points"] += [f"{year} {event} {m} ({o})" for m, o in zip(missing["match_id"], missing["history_outcome"])]
        extra = group[(group["stats_level"] != "H") & (points_n > 0)]
        problems["points_but_not_H"] += [f"{year} {event} {m} (statsLevel {lv})" for m, lv in zip(extra["match_id"], extra["stats_level"])]
        ref = research.get((key, year, event), {})
        row.update({"research_total": ref.get("total"), "research_H": ref.get("H")})
        rows.append(row)
    table = pd.DataFrame(rows)
    return table, problems


def sackmann_comparison(site, matches: pd.DataFrame, points: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Point counts and point-winner sequences of every match Sackmann's archive holds, for the years staged."""
    staged_years = set(matches["year"].astype(int)) if len(matches) else set()
    sack, out_of_scope = [], Counter()
    for path in sorted(SACKMANN.glob(f"*-{site.slam}-points*.parquet")):
        year = int(path.name[:4])
        if year not in staged_years:
            continue
        if "-mixed" in path.name:  # mixed doubles is not one of the collected events
            out_of_scope[path.name] = len(pq.read_table(path, columns=["match_id"]).column("match_id").unique())
            continue
        table = pq.read_table(path, columns=["match_id", "PointNumber", "PointWinner", "_row"]).to_pandas()
        table["year"] = year
        table["file"] = path.name
        sack.append(table)
    if not sack:
        return pd.DataFrame(), {"held_matches": 0}
    sack = pd.concat(sack, ignore_index=True)
    sack = sack[sack["PointNumber"].astype(str).str.isdigit()].copy()
    sack["match_num"] = sack["match_id"].str.rsplit("-", n=1).str[-1]
    sack = sack.sort_values(["year", "match_num", "_row"])
    ours = points[points["PointNumber"].astype(str).str.isdigit()].copy()
    ours["row_n"] = pd.to_numeric(ours["row"])
    ours = ours.sort_values(["year", "match_id", "row_n"])
    our_seq = {(int(y), m): list(g["PointWinner"]) for (y, m), g in ours.groupby(["year", "match_id"], sort=False)}
    listed = {(int(y), m): (e, o) for y, m, e, o in zip(matches["year"], matches["match_id"], matches["event"],
                                                        matches["history_outcome"])}
    rows = []
    for (year, match_num), group in sack.groupby(["year", "match_num"], sort=True):
        theirs = list(group["PointWinner"])
        mine = our_seq.get((year, match_num))
        event, history = listed.get((year, match_num), (None, None))
        row = {"year": year, "match_id": match_num, "event": event, "sackmann_file": group["file"].iloc[0],
               "sackmann_points": len(theirs), "feed_points": len(mine) if mine is not None else None,
               "history_outcome": history}
        if event is None:
            row["result"] = "not in the feed's listings"
        elif mine is None:
            row["result"] = "no feed history"
        else:
            diff = first_difference(theirs, mine)
            if diff is None:
                row["result"] = "identical"
            else:
                row["result"] = "count differs" if len(theirs) != len(mine) else "sequence differs"
                row["first_difference_at_point"] = diff + 1
                row["sackmann_winner_there"] = theirs[diff] if diff < len(theirs) else None
                row["feed_winner_there"] = mine[diff] if diff < len(mine) else None
                if len(theirs) == len(mine):
                    row["points_differing"] = sum(1 for a, b in zip(theirs, mine) if a != b)
                elif mine[:len(theirs)] == theirs or theirs[:len(mine)] == mine:
                    row["result"] = "count differs (one is a prefix of the other)"
        rows.append(row)
    table = pd.DataFrame(rows)
    if len(table):
        table["feed_points"] = table["feed_points"].astype("Int64")
    summary = {"held_matches": len(table), "by_result": dict(Counter(table["result"])) if len(table) else {},
               "by_year_result": {f"{y}|{r}": int(n) for (y, r), n in table.groupby(["year", "result"]).size().items()}
               if len(table) else {},
               "mixed_doubles_not_collected": dict(out_of_scope)}
    return table, summary


def side_names(entry: dict) -> dict[int, set[str]]:
    """The names a Sentence may use for each side of a listing entry: each player's display and last name and,
    for a doubles team, the pair joined by "/" as the sentences write it ("A. Erler/R. Galloway")."""
    sides = {}
    for side in (1, 2):
        known = set()
        for field in ("displayName", "lastName"):
            a, b = (entry.get(f"entry.team{side}.{field}{s}") for s in ("A", "B"))
            a, b = (x.strip() if isinstance(x, str) and x.strip() else None for x in (a, b))
            known.update(x for x in (a, b) if x)
            if a and b:
                known.add(f"{a}/{b}")
        sides[side] = known
    return sides


def sentence_tally(matches: pd.DataFrame, points: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Every point's Sentence: stroke x outcome where it names a shot; otherwise its pattern with the actor
    masked ("<actor> wins the point", mostly doubles) or, when not even the verb is recognised, the raw text.
    The verb says whether the named side won the point, which is checked against PointWinner either way."""
    names = {(int(m["year"]), m["match_id"]): side_names(m) for m in matches.to_dict("records")}
    tally, situations, no_shot, not_parsed = Counter(), Counter(), Counter(), Counter()
    mapped_by_event, points_by_event, agree = Counter(), Counter(), Counter()
    disagreements, contradictions = [], []
    pts = points[points["PointNumber"].astype(str).str.isdigit()]
    for year, event, match_id, number, winner, sentence in zip(pts["year"], pts["event"], pts["match_id"],
                                                               pts["PointNumber"], pts["PointWinner"], pts["Sentence"]):
        points_by_event[event] += 1
        parsed = parse_sentence(sentence)
        situation = parsed or parse_situation(sentence)
        if parsed:
            kind = "shot named"
            mapped_by_event[event] += 1
            tally[(parsed["stroke"], parsed["side"], parsed["stroke_type"], parsed["outcome"])] += 1
            if (parsed["outcome"] in WIN_OUTCOMES) != parsed["actor_won"]:
                agree["verb and outcome disagree"] += 1
                contradictions.append(f"{year} {match_id} point {number}: {sentence!r}")
        elif situation:
            kind = "no shot named"
            no_shot[(event, "<actor>" + sentence[len(situation["actor"]):])] += 1
        else:
            not_parsed[sentence if sentence else "(empty)"] += 1
            continue
        situations[situation["situation"]] += 1
        side = actor_side(situation["actor"], names.get((int(year), match_id), {}))
        if side is None or str(winner) not in ("1", "2"):
            agree[f"{kind}: actor not resolved"] += 1
            continue
        implied = side if situation["actor_won"] else 3 - side
        if implied == int(winner):
            agree[f"{kind}: agrees with PointWinner"] += 1
        else:
            agree[f"{kind}: disagrees with PointWinner"] += 1
            if len(disagreements) < 50:
                disagreements.append(f"{year} {match_id} point {number}: {sentence!r}, PointWinner {winner}")
    rows = [{"stroke": k[0], "side": k[1], "stroke_type": k[2], "outcome": k[3], "event": None, "points": n}
            for k, n in sorted(tally.items(), key=lambda kv: -kv[1])]
    rows += [{"stroke": "(no shot named)", "side": None, "stroke_type": None, "outcome": pattern, "event": event,
              "points": n} for (event, pattern), n in sorted(no_shot.items(), key=lambda kv: (kv[0][0], -kv[1]))]
    rows += [{"stroke": "(not parsed)", "side": None, "stroke_type": None, "outcome": text, "event": None, "points": n}
             for text, n in not_parsed.most_common()]
    table = pd.DataFrame(rows)
    pivot, outcomes, patterns = defaultdict(dict), Counter(), Counter()
    for (stroke, _, _, outcome), n in tally.items():
        pivot[stroke][outcome] = n
        outcomes[outcome] += n
    for (_, pattern), n in no_shot.items():
        patterns[pattern] += n
    unmapped = sum(no_shot.values()) + sum(not_parsed.values())
    summary = {"points": int(len(pts)), "mapped": int(sum(tally.values())), "unmapped": int(unmapped),
               "unmapped_no_shot_named": int(sum(no_shot.values())), "unmapped_not_parsed": int(sum(not_parsed.values())),
               "mapped_share_by_event": {e: round(mapped_by_event[e] / n, 4) for e, n in sorted(points_by_event.items())},
               "no_shot_patterns": dict(patterns.most_common()),
               "not_parsed_sentences": dict(not_parsed.most_common(100)),
               "stroke_by_outcome": {k: dict(sorted(v.items())) for k, v in sorted(pivot.items())},
               "outcomes": dict(outcomes.most_common()),
               "situations": dict(situations.most_common()), "point_winner_check": dict(sorted(agree.items())),
               "point_winner_disagreements": disagreements, "verb_outcome_contradictions": contradictions[:100]}
    return table, summary


EMPTY = {"", "0", "0.0", "0.0,0.0", "0.000,0.000"}
FILL_FIELDS = ("EpochTimeStart", "EpochTimeEnd", "Sentence", "ServeNumber", "Speed_KMH", "RallyCount", "KickHeight",
               "ServeWidth", "ServeDepth", "ReturnDepth", "P1DistanceRun", "WinnerShotType", "Court", "CourtIndicator",
               "TeamOrientStart", "ChallengeWon", "PointID")


def field_fill(site) -> pd.DataFrame:
    """Share of points (numeric PointNumber) with a value in each field, by year and event. Empty strings, zeros
    and the zero pairs of KickHeight and the distance fields count as no value; a field a year's files lack is
    left blank. ChallengeWon and similar flags are 0 unless something happened, so their share is a rate."""
    path = P.dump_path(site.source, "points.parquet")
    names = set(pq.read_schema(path).names)
    keys = pq.read_table(path, columns=["year", "event", "PointNumber"]).to_pandas()
    is_point = keys["PointNumber"].astype(str).str.isdigit()
    frame = keys.loc[is_point, ["year", "event"]].copy()
    for field in FILL_FIELDS:
        if field not in names:
            continue
        column = pq.read_table(path, columns=[field]).column(field).to_pandas()[is_point]
        values = (column.notna() & ~column.fillna("").astype(str).str.strip().isin(EMPTY)).astype(float)
        years_with = set(frame.loc[column.notna(), "year"])
        values[~frame["year"].isin(years_with)] = float("nan")  # the field is not in that year's files
        frame[field] = values
    grouped = frame.groupby(["year", "event"])
    table = grouped.mean(numeric_only=False).round(3)
    table.insert(0, "points", grouped.size())
    return table.reset_index()


def result_check(matches: pd.DataFrame, points: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Whether each history reproduces its listing's result: sets won by each side and, for completed matches,
    the winner. A mismatch is put down to a history that ends early (fewer sets than the score lists), to a
    listing whose set count contradicts its own score, or else to the sets differing."""
    pts = points[points["PointNumber"].astype(str).str.isdigit()].copy()
    pts["row_n"] = pd.to_numeric(pts["row"])
    pts = pts.sort_values(["year", "match_id", "row_n"])
    listing = matches.set_index(["year", "match_id"])
    columns = ["SetNo", "PointWinner", "P1GamesWon", "P2GamesWon", "EpochTimeStart", "EpochTimeEnd", "P1Score",
               "P2Score", "Sentence"]
    rows, totals = [], Counter()
    for (year, match_id), group in pts.groupby(["year", "match_id"], sort=True):
        entry = listing.loc[(year, match_id)]
        try:
            score_sets = json.loads(entry.get("entry.scores.sets") or "[]")
        except (TypeError, ValueError):
            score_sets = []
        c1, c2, listed_sets = sets_from_score(score_sets)
        completed = entry.get("entry.status") == "Completed"
        got = result_from_points(group[columns].to_dict("records"))
        played = got["sets_played"]
        want = (str(entry.get("entry.team1.totalSetsWon")), str(entry.get("entry.team2.totalSetsWon")))
        mine = (str(got["sets_1"]), str(got["sets_2"]))
        winner_ok = not completed or got["winner"] == str(entry.get("entry.winner"))
        if mine == want and winner_ok:
            result = "reproduced"
        elif mine == (str(c1), str(c2)) and winner_ok:
            result = "reproduced; the listing's set count contradicts its own score"
        elif completed and not got["ends_on_match_point"]:
            result = f"history ends early: in set {played} of {listed_sets}, {len(group)} points"
        else:
            result = "sets differ" if mine != want else "winner differs"
        totals[result if not result.startswith("history ends early") else "history ends early"] += 1
        totals["repeated_rows"] += got["repeated_rows"]
        totals["matches_with_repeated_rows"] += int(got["repeated_rows"] > 0)
        if result != "reproduced" or got["repeated_rows"]:
            rows.append({"year": int(year), "event": entry.get("event"), "match_id": match_id, "result": result,
                         "status": entry.get("entry.status"), "score": entry.get("entry.score_text"),
                         "points": len(group), "sets_in_history": played, "sets_in_score": listed_sets,
                         "sets_from_points": "-".join(mine), "sets_listed": "-".join(want),
                         "sets_from_listed_score": f"{c1}-{c2}", "winner_from_points": got["winner"],
                         "winner_listed": entry.get("entry.winner"), "repeated_rows": got["repeated_rows"]})
    return pd.DataFrame(rows), dict(totals)


def epoch_check(points: pd.DataFrame, matches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fill, order and one-day jumps of every match's epochs, and the last point's EpochTimeEnd against the time
    the listing gives (entry.epoch, milliseconds; the match's end, or a later update of the listing)."""
    pts = points[points["PointNumber"].astype(str).str.isdigit()].copy()
    pts["row_n"] = pd.to_numeric(pts["row"])
    pts = pts.sort_values(["year", "match_id", "row_n"])
    listed = {(int(y), m): e for y, m, e in zip(matches["year"], matches["match_id"], matches.get("entry.epoch", []))}
    rows, totals, versus_listing = [], Counter(), Counter()
    for (year, match_id, event), group in pts.groupby(["year", "match_id", "event"], sort=True):
        result = epoch_problems(list(group["EpochTimeStart"]), list(group["EpochTimeEnd"]))
        last_end = pd.to_numeric(group["EpochTimeEnd"], errors="coerce").iloc[-1]
        listing = pd.to_numeric(listed.get((int(year), match_id)), errors="coerce")
        result["last_end_minus_listing_s"] = None if pd.isna(last_end) or pd.isna(listing) else int(last_end - listing / 1000)
        consistent = (not result["end_backwards"] and not result["day_jumps"] and not result["end_implausible"]
                      and (result["last_gap_s"] is None or result["last_gap_s"] <= 3600))  # the end series only
        result["listing_bin"] = listing_bin(result["last_end_minus_listing_s"], consistent)
        versus_listing[result["listing_bin"]] += 1
        totals["matches"] += 1
        totals["points"] += result["points"]
        totals["points_start_missing"] += result["start_missing"]
        totals["points_end_missing"] += result["end_missing"]
        totals["points_start_implausible"] += result["start_implausible"]
        totals["points_end_implausible"] += result["end_implausible"]
        totals["points_end_before_start"] += result["end_before_start"]
        totals["matches_filled"] += int(result["filled"])
        totals["matches_in_order"] += int(result["in_order"])
        totals["matches_with_a_day_jump"] += int(result["day_jumps"] > 0)
        totals["gaps_over_1h_not_day_jumps"] += result["gaps_over_1h"]
        totals["points_overlapping_previous"] += result["overlaps_previous"]
        if not (result["filled"] and result["in_order"]) or result["day_jumps"] or result["listing_bin"] in LATE:
            rows.append({"year": int(year), "event": event, "match_id": match_id, **result})
    totals = dict(totals)
    totals["last_point_versus_listing_time"] = dict(versus_listing)
    return pd.DataFrame(rows), totals


LATE = ("last point a day after the listing", "last point later than the listing otherwise")


def listing_bin(diff, consistent: bool = True) -> str:
    """The last point's EpochTimeEnd against the listing's time, in words. A whole number of hours (1-23, within
    6 minutes) counts as the listing's own offset when the history's end times are ``consistent`` (none steps back
    or is implausible, no day jump, an ordinary gap before the last point; faults in EpochTimeStart do not
    matter here): the US Open's 2026 listings run 5 hours early, as its points, its live likelihood-to-win rows
    and Polymarket's prices agree. Otherwise the last point is out of line."""
    if diff is None:
        return "no listing time"
    if -600 <= diff <= 600:
        return "within 10 minutes"
    if diff < -600:
        return "listing later by over 10 minutes (updated after the match)"
    if is_day_jump(diff):
        return "last point a day after the listing"
    hours = round(diff / 3600)
    if consistent and 1 <= hours <= 23 and abs(diff - hours * 3600) <= 360:
        return f"listing {hours} h early (a whole-hour offset of the listing's clock)"
    return "last point later than the listing otherwise"


def l2w_kind(created: list, ends: list, margin: int = 3600) -> str:
    """"live" when a likelihood-to-win file was written while its match was played (its created_epoch range
    overlaps the points' EpochTimeEnd range, give or take ``margin`` seconds), "replay" when it was generated
    afterwards (the US Open's 2025 MS 1101 file was written eleven months later; Wimbledon's "2024" file in 2025),
    "unknown" without times. EpochTimeEnd is used because EpochTimeStart can go wrong mid-match (US Open 2026)."""
    c = [int(x) for x in created if str(x).strip().isdigit()]
    e = [int(x) for x in ends if str(x).strip().isdigit() and int(x) > 0]
    if not c or not e:
        return "unknown"
    return "live" if min(c) <= max(e) + margin and max(c) >= min(e) - margin else "replay"


def l2w_check(site, points: pd.DataFrame, matches: pd.DataFrame, suspect: set | None = None) -> dict:
    """Likelihood-to-win rows joined to the points on point_number; the lag behind EpochTimeEnd over live files,
    leaving out ``suspect`` matches, whose history times are known to be wrong (a one-day jump, a late point)."""
    if "livel2w" not in [f.name for f in site.feeds]:
        return {}
    l2w = read(site.source, "livel2w", ["year", "match_id", "point_number", "created_epoch", "player_one_tour_id",
                                        "player_two_tour_id"])
    if l2w.empty:
        return {"matches": 0}
    l2w["year"] = l2w["year"].astype(int)
    pts = points[points["PointNumber"].astype(str).str.isdigit()][["year", "match_id", "PointNumber", "EpochTimeEnd"]]
    joined = pts.merge(l2w, left_on=["year", "match_id", "PointNumber"], right_on=["year", "match_id", "point_number"],
                       how="right", indicator=True)
    with_l2w = set(zip(l2w["year"], l2w["match_id"]))
    pts_l2w = pts[[k in with_l2w for k in zip(pts["year"], pts["match_id"])]]
    ends = {k: list(g["EpochTimeEnd"]) for k, g in pts_l2w.groupby(["year", "match_id"])}
    kinds = {k: l2w_kind(list(g["created_epoch"]), ends.get(k, [])) for k, g in l2w.groupby(["year", "match_id"])}
    joined["kind"] = [kinds.get(k) for k in zip(joined["year"], joined["match_id"])]
    suspect = suspect or set()
    left_out = {k for k, kind in kinds.items() if kind == "live" and k in suspect}
    trusted = pd.Series([k not in suspect for k in zip(joined["year"], joined["match_id"])], index=joined.index)
    live = joined[(joined["kind"] == "live") & trusted]
    lag = (pd.to_numeric(live["created_epoch"], errors="coerce") - pd.to_numeric(live["EpochTimeEnd"], errors="coerce")).dropna()
    replays = [f"{y} {m}" for (y, m), kind in sorted(kinds.items()) if kind != "live"]
    ids = matches.set_index(["year", "match_id"])
    oriented = Counter()
    for (year, match_id), group in l2w.groupby(["year", "match_id"]):
        try:
            one = ids.loc[(year, match_id), "entry.team1.idA"]
        except KeyError:
            oriented["match not listed"] += 1
            continue
        oriented["player one is team1" if group["player_one_tour_id"].iloc[0] == one else "player one is not team1"] += 1
    return {"matches": len(with_l2w), "rows": int(len(l2w)),
            "rows_joined_to_a_point": int((joined["_merge"] == "both").sum()),
            "rows_without_a_point": int((joined["_merge"] == "right_only").sum()),
            "points_of_those_matches": int(len(pts_l2w)),
            "files_by_kind": dict(Counter(kinds.values())), "files_not_live": replays[:100],
            "live_files_left_out_of_the_lag_for_history_time_errors": sorted(f"{y} {m}" for y, m in left_out),
            "lag_seconds_live_files": {"median": float(lag.median()) if len(lag) else None,
                            "p10": float(lag.quantile(0.1)) if len(lag) else None,
                            "p90": float(lag.quantile(0.9)) if len(lag) else None,
                            "p99": float(lag.quantile(0.99)) if len(lag) else None,
                            "max": float(lag.max()) if len(lag) else None,
                            "rows_over_10_min": int((lag > 600).sum()), "negative": int((lag < 0).sum())},
            "orientation": dict(oriented)}


def run(site_key: str) -> dict:
    P.configure_stdout()
    site = load_site(site_key)
    matches = read(site.source, "matches")
    points = read(site.source, "points", ["year", "event", "match_id", "row", "PointNumber", "PointWinner", "SetNo",
                                          "P1GamesWon", "P2GamesWon", "P1Score", "P2Score", "EpochTimeStart",
                                          "EpochTimeEnd", "Sentence"])
    for frame in (matches, points):
        if "year" in frame:
            frame["year"] = frame["year"].astype(int)
    out = {"source": site.source, "site": site.key, "checked_at": P.utc_now_iso(), "matches_listed": int(len(matches)),
           "point_rows": int(len(points))}
    cov, problems = coverage(site, matches, points)
    out["coverage_problems"] = problems
    sack, out["sackmann"] = sackmann_comparison(site, matches, points)
    sentences, out["sentences"] = sentence_tally(matches, points)
    epochs, out["epochs"] = epoch_check(points, matches)
    results, out["results"] = result_check(matches, points)
    suspect = set()
    if len(epochs):
        wrong = (epochs["day_jumps"] > 0) | epochs["listing_bin"].isin(LATE)
        suspect = {(int(y), m) for y, m in zip(epochs.loc[wrong, "year"], epochs.loc[wrong, "match_id"])}
    out["livel2w"] = l2w_check(site, points, matches, suspect)
    out["coverage"] = cov.to_dict(orient="records")
    fill = field_fill(site)
    F.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    for name, frame in (("coverage", cov), ("sackmann", sack), ("sentences", sentences), ("epoch_problems", epochs),
                        ("result_problems", results), ("field_fill", fill)):
        path = F.STUDY_ROOT / f"{site.source}_{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8")
        P.log(f"[{site.source}] wrote {P.rel(path)} ({len(frame)} rows)")
    path = F.STUDY_ROOT / f"{site.source}_checks.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    P.log(f"[{site.source}] wrote {P.rel(path)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", default="wimbledon", help="module in src/ingest/point_sources/ that defines SITE")
    run(parser.parse_args().site)
    return 0


if __name__ == "__main__":
    sys.exit(main())
