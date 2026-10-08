"""Check the Australian Open match-centre download: every match accounted for, every commentary string mapped, aces and
double faults against the set statistics, and each point sequence replayed against the final score.

Inputs: the raw match-centre documents (data/raw/point_sources/ausopen/) and the tables staged from them by
src/ingest/point_sources/ausopen.py (data/dump/points/ausopen/).

Checks:
    accounting       each match of the six draws (and each Wayback capture) is fetched with points, or recorded as
                     empty or absent with the reason, or listed as not fetched / failed
    commentary map   every commentary sentence of every document, names replaced by <name>, with the outcome and
                     stroke side it maps to; sentences the parser does not know are listed as unmapped
    aces, DFs        per match, set and team, the points described as an Ace or a Double Fault against the "Aces" and
                     "Double faults" of the key statistics, for each set and for the match ("All"); and whether each
                     ace and double fault falls on a point served by the team that hit it (the server is derived
                     from the "is serving game" lines and the tiebreak rotation)
    score replay     the point winners alone, replayed under the Slam's scoring rules (games with advantage, sets to
                     six with a tiebreak to 7 at 6-6, a tiebreak to 10 at 6-6 in the deciding set, best of five for
                     format A, of three otherwise; format D, legends' and junior doubles, with no-ad games and a match
                     tiebreak for the third set), must give the listed set scores, tiebreak points and winner, and
                     end each game where the commentary types it as ending ("game", "set", "match") and numbers it;
                     each point's score string (server first) is compared with the replayed state
    feed defects     the patterns behind the disagreements: games with more than one entry typed as their end
                     (superseded entries left in place), serve lines inside a game (a point typed "serve"), and serve
                     lines whose game's scores are written as if the other side served
    timestamps       points stamped later than the point after them (entry or edit times rather than play times)

Outputs (data/studies/official_point_feeds/):
    ausopen_accounting.csv        one row per match of the draws and per Wayback capture: record, reason, points
    ausopen_commentary_map.csv    one row per sentence template: count, outcome, stroke side, mapped
    ausopen_checks.csv            one row per match with points: the result of each check
    ausopen_mismatches.csv        one row per disagreement found by the checks
    ausopen_wayback_coverage.csv  per earlier edition and event: matches in the archived draw, played, and with points
                                  in a Wayback capture (from archived_draws.parquet, when it has been staged)
    ausopen_verification.json     the totals, how each entry type writes its games score, and the fetch record
                                  (receipts by kind and outcome, bytes, time span, the runs that made requests)
Usage:
    ./python.sh src/eda/official_point_feeds/verify_ausopen.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import ausopen as A  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402

DUMP = PROJECT_ROOT / "data" / "dump" / "points" / "ausopen"
OUT = PROJECT_ROOT / "data" / "studies" / "official_point_feeds"
LADDER = ["0", "15", "30", "40"]
GAME_END_TYPES = {"game", "set", "match"}


# --------------------------------------------------------------------------------------
# score replay (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def rules(scoring_format: str | None) -> dict:
    """Replay rules for the match centre's scoring formats. A (men's singles): best of five. B (doubles) and C (other
    singles): best of three. D (legends' and junior doubles, seen only in Wayback captures): best of three with no-ad
    games and a match tiebreak to 10 instead of a third set, as the records themselves show (games decided at 40-40,
    third sets written "1(10)" and "0(7)"); the format codes are not documented."""
    if scoring_format == "A":
        return {"sets_to_win": 3}
    if scoring_format == "D":
        return {"sets_to_win": 2, "no_ad": True, "match_tiebreak": True}
    return {"sets_to_win": 2}


def replay(winners: list[int], sets_to_win: int, tiebreak_to: int = 7, final_tiebreak_to: int = 10,
           no_ad: bool = False, match_tiebreak: bool = False) -> dict:
    """Replay point winners (1 or 2) under Slam rules: advantage games (or no-ad), sets to six with a tiebreak to 7 at
    6-6, and in the deciding set a tiebreak to 10 at 6-6 (or, with ``match_tiebreak``, a tiebreak to 10 as the whole set).

    Returns the completed sets as (games1, games2, tiebreak1, tiebreak2), the unfinished set's games and points,
    the index of the point that ended the match (None if it did not end), and for each point the set and game it
    belongs to, the score after it and whether it ended its game, set or match."""
    sets: list[tuple] = []
    games, points = [0, 0], [0, 0]
    tiebreak = False
    finished_at = None
    per_point = []
    won = [0, 0]
    for i, w in enumerate(winners):
        set_no, game_no = len(sets) + 1, games[0] + games[1] + 1
        games_before = tuple(games)
        points[w - 1] += 1
        deciding = won[0] == won[1] == sets_to_win - 1
        target = (final_tiebreak_to if deciding else tiebreak_to) if tiebreak else 4
        margin = 1 if no_ad and not tiebreak else 2
        game_over = max(points) >= target and abs(points[0] - points[1]) >= margin
        state = {"set": set_no, "game": game_no, "tiebreak": tiebreak, "points": tuple(points), "ends": None,
                 "after_match": finished_at is not None, "games_before": games_before, "games_after": games_before}
        if game_over:
            tb_points = tuple(points) if tiebreak else (None, None)
            games[w - 1] += 1
            points = [0, 0]
            state["ends"] = "game"
            state["games_after"] = tuple(games)
            if tiebreak or (max(games) >= 6 and abs(games[0] - games[1]) >= 2):
                sets.append((games[0], games[1], *tb_points))
                won[w - 1] += 1
                games, tiebreak = [0, 0], False
                state["ends"] = "set"
                if won[w - 1] == sets_to_win and finished_at is None:
                    finished_at = i
                    state["ends"] = "match"
                elif match_tiebreak and won[0] == won[1] == sets_to_win - 1:
                    tiebreak = True  # the deciding set is a single tiebreak
            else:
                tiebreak = games[0] == games[1] == 6
        per_point.append(state)
    return {"sets": sets, "current_games": tuple(games), "current_points": tuple(points), "finished_at": finished_at,
            "winner": (1 if won[0] > won[1] else 2) if finished_at is not None else None, "per_point": per_point}


def official_sets(team1: str | None, team2: str | None) -> list[tuple]:
    """The draw's set scores ("6 7(7)" and "3 6(2)") as (games1, games2, tiebreak1, tiebreak2) per set."""
    def parse(text):
        out = []
        for token in (text or "").split():
            m = re.fullmatch(r"(\d+)(?:\((\d+)\))?", token)
            out.append((int(m.group(1)), int(m.group(2)) if m.group(2) else None) if m else (None, None))
        return out
    a, b = parse(team1), parse(team2)
    return [(x[0], y[0], x[1], y[1]) for x, y in zip(a, b)]


def score_differences(result: dict, official: list[tuple], winner_team: int | None, complete: bool) -> list[str]:
    """Where the replayed score departs from the draw's; empty when it reproduces it."""
    out = []
    sets = result["sets"]
    for i, (mine, theirs) in enumerate(zip(sets, official), 1):
        if mine[:2] != theirs[:2]:
            out.append(f"set {i}: replay {mine[0]}-{mine[1]}, draw {theirs[0]}-{theirs[1]}")
        elif mine[2] is not None and (mine[2], mine[3]) != (theirs[2], theirs[3]):
            out.append(f"set {i} tiebreak: replay {mine[2]}-{mine[3]}, draw {theirs[2]}-{theirs[3]}")
    extra = official[len(sets):]
    if result["finished_at"] is not None:
        if extra:
            out.append(f"the replay ends the match after {len(sets)} sets; the draw lists {len(official)}")
        if complete and winner_team and result["winner"] != winner_team:
            out.append(f"winner: replay team {result['winner']}, draw team {winner_team}")
    else:
        if complete:
            out.append(f"the points do not finish the match (replay stops at {len(sets)} sets, "
                       f"{result['current_games'][0]}-{result['current_games'][1]})")
        current = result["current_games"]
        if len(extra) > 1:
            out.append(f"the draw lists {len(official)} sets; the replay reaches set {len(sets) + 1}")
        elif extra and extra[0][:2] != current:
            out.append(f"unfinished set {len(sets) + 1}: replay {current[0]}-{current[1]}, draw {extra[0][0]}-{extra[0][1]}")
        elif not extra and current != (0, 0):
            out.append(f"the replay has set {len(sets) + 1} at {current[0]}-{current[1]}; the draw lists no such set")
    if len(sets) > len(official):
        out.append(f"the replay completes {len(sets)} sets; the draw lists {len(official)}")
    return out


def score_text(points: tuple, server: int | None, tiebreak: bool) -> str | None:
    """The score after a point as the feed writes it, server first ("30 - 15", "AD - 40", tiebreak "5 - 2")."""
    if server not in (1, 2):
        return None
    s, r = (points[0], points[1]) if server == 1 else (points[1], points[0])
    if tiebreak:
        return f"{s} - {r}"
    if s >= 3 and r >= 3:
        return "40 - 40" if s == r else ("AD - 40" if s > r else "40 - AD")
    return f"{LADDER[s]} - {LADDER[r]}"


# --------------------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------------------
def template(entry_text: str | None, parsed: dict) -> str:
    text = (entry_text or "").strip()
    if parsed["kind"] == "serve":
        return re.sub(r"^.+? is serving game \d+$", "<name> is serving game <n>", text)
    if parsed["kind"] == "point":
        return text.replace(parsed["subject"], "<name>", 1)
    return text


def commentary_map(documents: list[tuple[str, dict]]) -> tuple[pd.DataFrame, dict]:
    """Every sentence of every document, grouped by template."""
    groups: dict[str, dict] = {}
    by_type = Counter()
    for key, payload in documents:
        for e in payload.get("commentary") or []:
            parsed = A.parse_commentary(e.get("commentary"))
            by_type[f"{e.get('type')}|{parsed['kind']}"] += 1
            t = template(e.get("commentary"), parsed)
            g = groups.setdefault(t, {"template": t, "kind": parsed["kind"], "entries": 0, "records": set(),
                                      "entry_types": Counter(), "outcome": parsed.get("outcome"),
                                      "stroke_side": parsed.get("stroke_side"), "subject_role": parsed.get("subject_role"),
                                      "verb_agrees": parsed.get("verb_agrees"),
                                      "mapped": parsed["kind"] == "serve" or bool(parsed.get("mapped")),
                                      "example": e.get("commentary"), "example_entry": f"{key}:{e.get('id')}"})
            g["entries"] += 1
            g["records"].add(key)
            g["entry_types"][str(e.get("type"))] += 1
    rows = []
    for g in groups.values():
        rows.append({**{k: v for k, v in g.items() if k not in ("records", "entry_types")}, "records": len(g["records"]),
                     "entry_types": ";".join(f"{k}:{v}" for k, v in sorted(g["entry_types"].items()))})
    table = pd.DataFrame(rows).sort_values(["mapped", "kind", "entries"], ascending=[True, True, False])
    unmapped = table[~table["mapped"]]
    summary = {"entries": int(table["entries"].sum()), "templates": len(table),
               "entries_by_type_and_kind": dict(sorted(by_type.items())),
               "unmapped_templates": len(unmapped), "unmapped_entries": int(unmapped["entries"].sum()),
               "unmapped_examples": unmapped["example"].head(20).tolist(),
               "verb_disagrees_entries": int(table.loc[table["verb_agrees"] == False, "entries"].sum())}  # noqa: E712
    return table, summary


def to_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def check_aces(key: str, points: pd.DataFrame, stats: pd.DataFrame, mismatches: list) -> dict:
    """Commentary aces and double faults per set and team against the key statistics."""
    out = {"sets_compared": 0, "sets_agree": 0, "totals_agree": None, "struck_by_server": 0, "struck_by_receiver": 0,
           "server_unknown": 0}
    key_stats = stats[stats["group"] == "key_stats"]
    periods = sorted({s for s in key_stats["set"].dropna()}, key=lambda s: (not s.isdigit(), s.zfill(3)))
    all_agree = True
    for period in periods:
        rows = points if period == "All" else points[points["set"] == period]
        agree = True
        for stat, outcome in (("Aces", "ace"), ("Double faults", "double_fault")):
            found = key_stats[(key_stats["set"] == period) & (key_stats["stat"] == stat)]
            if found.empty:
                continue
            for team in (1, 2):
                counted = int(((rows["outcome"] == outcome) & (rows["subject_team"] == str(team))).sum())
                listed = to_int(found.iloc[0][f"team{team}_primary"])
                if counted != listed:
                    agree = False
                    mismatches.append({"record_key": key, "check": "aces_double_faults", "set": period,
                                       "detail": f"{stat}, team {team}", "expected": listed, "found": counted})
        if period == "All":
            out["totals_agree"] = agree
        else:
            out["sets_compared"] += 1
            out["sets_agree"] += int(agree)
            all_agree &= agree
    out["sets_all_agree"] = all_agree
    served = points[points["outcome"].isin(["ace", "double_fault"])]
    for _, r in served.iterrows():
        if r["point_server_team"] is None or pd.isna(r["point_server_team"]):
            out["server_unknown"] += 1
        elif r["point_server_team"] == r["subject_team"]:
            out["struck_by_server"] += 1
        else:
            out["struck_by_receiver"] += 1
            mismatches.append({"record_key": key, "check": "ace_or_df_server", "set": r["set"],
                               "detail": f"{r['entry_id']}: {r['commentary']}", "expected": f"server team {r['subject_team']}",
                               "found": f"derived server team {r['point_server_team']}"})
    return out


def games_score_readings(text, winner: int | None, server: int | None, state: dict) -> list[str]:
    """Which readings of an entry's ``games_score`` agree with the replay: the set's games before or after the point,
    in team order, server first (the game's first server) or winner first."""
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(text or ""))
    if not m:
        return ["missing"]
    found = (int(m.group(1)), int(m.group(2)))
    before, after = state["games_before"], state["games_after"]
    flip = lambda g, first: (g[first - 1], g[2 - first])  # noqa: E731
    readings = {"team_order_before": before, "team_order_after": after}
    if server in (1, 2):
        readings.update(server_first_before=flip(before, server), server_first_after=flip(after, server))
    if winner in (1, 2):
        readings["winner_first_after"] = flip(after, winner)
    return sorted(name for name, value in readings.items() if value == found) or ["none"]


def check_replay(key: str, match: dict, points: pd.DataFrame, mismatches: list, readings: Counter | None = None) -> dict:
    winners = [to_int(w) for w in points["winner"]]
    if any(w not in (1, 2) for w in winners):
        mismatches.append({"record_key": key, "check": "score_replay", "set": None,
                           "detail": "points without a winner", "expected": None, "found": sum(w not in (1, 2) for w in winners)})
        return {"replayed": False}
    result = replay(winners, **rules(match["scoring_format"]))
    official = official_sets(match["team1_score"], match["team2_score"])
    complete = match["match_status"] == "CMP"
    differences = score_differences(result, official, to_int(match["winner_team"]), complete)
    for d in differences:
        mismatches.append({"record_key": key, "check": "final_score", "set": None, "detail": d, "expected": None, "found": None})
    # game ends and numbering: the replay's against the commentary's types and ids
    typed_ends = [t in GAME_END_TYPES for t in points["type"]]
    replay_ends = [s["ends"] is not None for s in result["per_point"]]
    ends_differ = [i for i, (a, b) in enumerate(zip(typed_ends, replay_ends)) if a != b]
    numbering_differ = [i for i, (s, g, st) in enumerate(zip(points["set"], points["game"], result["per_point"]))
                        if (to_int(s), to_int(g)) != (st["set"], st["game"])]
    kinds_differ = [i for i, (t, st) in enumerate(zip(points["type"], result["per_point"]))
                    if t in GAME_END_TYPES and st["ends"] is not None and t != st["ends"]]
    for label, idx in (("game_ends", ends_differ), ("game_numbering", numbering_differ), ("end_type", kinds_differ)):
        if idx:
            first = points.iloc[idx[0]]
            mismatches.append({"record_key": key, "check": label, "set": first["set"],
                               "detail": f"{len(idx)} points, first {first['entry_id']} ({first['type']})",
                               "expected": None, "found": None})
    after = sum(s["after_match"] for s in result["per_point"])
    if after:
        mismatches.append({"record_key": key, "check": "points_after_match_end", "set": None,
                           "detail": f"{after} points after the replay ended the match", "expected": None, "found": None})
    # the score string after each point, server first; and how the games score is written
    wrong_scores, unknown_server = [], 0
    per_game = defaultdict(lambda: {"listed": 0, "other": 0, "server": None, "first": None})
    for (_, r), st in zip(points.iterrows(), result["per_point"]):
        if readings is not None:
            for name in games_score_readings(r["games_score"], to_int(r["winner"]), to_int(r["game_server_team"]), st):
                readings[f"{r['type']}|{name}"] += 1
            readings[f"{r['type']}|entries"] += 1
        server = to_int(r["point_server_team"])
        found = re.sub(r"\s+", " ", str(r["score"] or "")).strip()
        if st["ends"] is not None:
            expected = "Game"
        else:
            expected = score_text(st["points"], server, st["tiebreak"])
            other = score_text(st["points"], 3 - server, False) if server and not st["tiebreak"] else None
            if other is not None and other != expected:  # 15-15, 30-30 and 40-40 read the same either way
                game = per_game[(r["set"], r["game"])]
                game["server"] = to_int(r["game_server_team"])
                if found == other:  # written as if the other side served
                    game["other"] += 1
                    game["first"] = game["first"] or r["entry_id"]
                elif found == expected:
                    game["listed"] += 1
        if expected is None:
            unknown_server += 1
        elif found != expected:
            wrong_scores.append((r["entry_id"], r["score"], expected))
    if wrong_scores:
        eid, found, expected = wrong_scores[0]
        mismatches.append({"record_key": key, "check": "point_score_text", "set": None,
                           "detail": f"{len(wrong_scores)} points, first {eid}", "expected": expected, "found": found})
    contradicted = [(g, v) for g, v in per_game.items() if v["other"] >= 2 and v["listed"] == 0]
    for (set_no, game_no), v in contradicted:
        mismatches.append({"record_key": key, "check": "serve_line_contradicted", "set": set_no,
                           "detail": f"game {game_no}: the serve line names team {v['server']}, but {v['other']} scores "
                                     f"are written as if team {3 - v['server']} served (first {v['first']})",
                           "expected": None, "found": None})
    # a game with more than one entry typed as its end: superseded entries left in the commentary
    ends = points[points["type"].isin(GAME_END_TYPES)].groupby(["set", "game"], sort=False)
    extra_ends = [(g, len(rows)) for g, rows in ends if len(rows) > 1]
    for (set_no, game_no), n in extra_ends:
        mismatches.append({"record_key": key, "check": "extra_game_end_entries", "set": set_no,
                           "detail": f"game {game_no}: {n} entries typed as the game's end", "expected": 1, "found": n})
    return {"replayed": True, "final_score_reproduced": not differences, "replay_finished": result["finished_at"] is not None,
            "game_ends_agree": not ends_differ, "game_numbering_agrees": not numbering_differ, "end_types_agree": not kinds_differ,
            "points_after_end": after, "score_texts_differing": len(wrong_scores), "score_texts_unchecked": unknown_server,
            "serve_lines_contradicted": len(contradicted), "games_with_extra_end_entries": len(extra_ends)}


def serve_lines_inside_games(key: str, payload: dict, mismatches: list) -> int:
    """Serve lines that sit inside a game (point number other than 000): an entry typed "serve" in place of a point."""
    found = 0
    for e in payload.get("commentary") or []:
        k = A.entry_key(e)
        if e.get("type") == "serve" and k and k[2] != 0:
            found += 1
            mismatches.append({"record_key": key, "check": "serve_line_inside_game", "set": k[0],
                               "detail": f"{e.get('id')} typed serve: {e.get('commentary')!r} (games {e.get('games_score')})",
                               "expected": "a point", "found": "a serve line"})
    return found


def timestamp_steps(points: pd.DataFrame) -> list[int]:
    """For each point stamped later than the point after it, by how many seconds."""
    stamps = [to_int(t) for t in points["timestamp"]]
    return [a - b for a, b in zip(stamps, stamps[1:]) if a is not None and b is not None and a > b]


def check_servers(key: str, points: pd.DataFrame, mismatches: list) -> dict:
    """Game servers alternate between the teams through the whole match (a tiebreak counts as one game)."""
    games = points.drop_duplicates(["set", "game"])[["set", "game", "game_server_team", "entry_id"]]
    teams = [to_int(t) for t in games["game_server_team"]]
    unknown = sum(t is None for t in teams)
    breaks = [i for i in range(1, len(teams)) if teams[i] and teams[i - 1] and teams[i] == teams[i - 1]]
    if breaks:
        first = games.iloc[breaks[0]]
        mismatches.append({"record_key": key, "check": "server_alternation", "set": first["set"],
                           "detail": f"{len(breaks)} games served by the same team as the game before, first {first['entry_id']}",
                           "expected": None, "found": None})
    return {"games": len(teams), "server_unknown_games": unknown, "server_repeats": len(breaks)}


def receipts_summary() -> dict:
    """The fetch record: every receipt line (attempts), the latest answer per document by kind and status, bytes
    saved, the time span, and the adapter's runs (requests, retries and stops) from runs.jsonl."""
    path = P.raw_path(A.SOURCE, "_receipts.jsonl")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = {r["name"]: r for r in lines}
    kind = lambda r: r["name"].split("/")[0] + ("-cdx" if r["name"].endswith("/cdx") else "")  # noqa: E731
    outcome = lambda r: "error" if r.get("error") else "absent" if r.get("absent") else str(r.get("status"))  # noqa: E731
    times = sorted(r["retrieved_at"] for r in lines)
    by_kind = defaultdict(lambda: {"documents": 0, "bytes": 0, "outcomes": Counter()})
    for r in latest.values():
        k = by_kind[kind(r)]
        k["documents"] += 1
        k["bytes"] += int(r.get("bytes") or 0)
        k["outcomes"][outcome(r)] += 1
    runs = []
    runs_path = OUT / "runs.jsonl"
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            run = json.loads(line) if line.strip() else {}
            fetched = {k: n for k, n in (run.get("fetch_outcomes") or {}).items() if not k.endswith(":cached")}
            if run.get("source") == A.SOURCE and fetched:
                runs.append({"started_at": run.get("started_at"), "seconds": run.get("seconds"), "fetched": fetched,
                             "stopped": run.get("stopped"), "client": run.get("client")})
    return {"file": P.rel(path), "receipt_lines": len(lines), "documents": len(latest),
            "first_retrieved_at": times[0] if times else None, "last_retrieved_at": times[-1] if times else None,
            "by_kind": {k: {**v, "outcomes": dict(v["outcomes"])} for k, v in sorted(by_kind.items())},
            "superseded_lines": len(lines) - len(latest),
            "runs_that_fetched": runs,
            "note": "the pilot's 11 documents (the six draws and five matches) were fetched through the adapter's "
                    "functions before its command line existed, so no run line records them; their receipts do"}


def captures_against_live(matches: pd.DataFrame, raw: dict) -> dict:
    """Wayback captures of the current edition set against the documents the API serves now: every captured entry
    should still be served unchanged (a capture taken mid-match holds fewer entries)."""
    live = matches[matches["route"] == "api"].set_index("match_id")["record_key"]
    out = {"compared": 0, "identical": 0, "captured_mid_match_and_contained": 0, "differing": []}
    for _, m in matches[(matches["route"] == "wayback") & (matches["record"] == "points")].iterrows():
        if str(m["year"]) != str(A.YEAR) or m["match_id"] not in live.index or live[m["match_id"]] not in raw:
            continue
        key = lambda e: (e.get("id"), e.get("type"), e.get("winner"), e.get("score"), e.get("commentary"), e.get("timestamp"))  # noqa: E731
        captured = {key(e) for e in raw[m["record_key"]].get("commentary") or []}
        served = {key(e) for e in raw[live[m["match_id"]]].get("commentary") or []}
        out["compared"] += 1
        if captured == served:
            out["identical"] += 1
        elif captured < served:
            out["captured_mid_match_and_contained"] += 1
        else:
            out["differing"].append({"capture": m["record_key"], "entries_not_served_now": len(captured - served)})
    return out


MAIN_EVENTS = ["MS", "WS", "MQ", "WQ", "MD", "WD"]


def archived_coverage(archived: pd.DataFrame, matches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """How much of each earlier edition the Wayback's point captures cover, measured against the archived draws.

    A draw copied before its event finished lists every match but not which were played, so each row also gives how
    many of its matches the copy shows finished."""
    a = archived.copy()
    a["played"] = a["match_status"].isin(["CMP", "RET"])
    a["walkover"] = a["match_status"] == "W/O"
    a["with_points"] = a["points_capture"].notna()
    a["with_finished_points"] = a["points_capture_status"].isin(["CMP", "RET"])
    table = (a.groupby(["year", "event"], sort=True)
             .agg(event_name=("event_name", "first"), matches=("match_id", "size"), played=("played", "sum"),
                  walkovers=("walkover", "sum"), with_points=("with_points", "sum"),
                  with_finished_points=("with_finished_points", "sum"), draw_capture=("draw_capture", "first"),
                  draw_copies=("draw_captures_of_event", "first"))
             .reset_index())
    table["draw_copy_finished"] = table["played"] + table["walkovers"] == table["matches"]
    linked = set(a.loc[a["with_points"], "points_capture"])
    captures = matches[(matches["route"] == "wayback") & (matches["record"] == "points")]
    unlinked = captures[~captures["record_key"].isin(linked)]
    # a match can have several captures; count matches, not captures
    unlinked_matches = unlinked.drop_duplicates(["year", "match_id"])
    per_match = captures.assign(finished=captures["match_status"].isin(["CMP", "RET"])) \
        .groupby(["year", "match_id"]).agg(event=("event", "first"), finished=("finished", "max")).reset_index()
    edition_size = sum(A.EXPECTED_MATCHES.values())  # 604 in every edition: the archived 2025 draws confirm it
    by_year = {}
    for year in sorted(set(table["year"]) | set(per_match["year"])):
        part = table[table["year"] == year]
        main = part[part["event"].isin(MAIN_EVENTS)]
        caught = per_match[(per_match["year"] == year) & per_match["event"].isin(MAIN_EVENTS)]
        by_year[str(year)] = {
            "main_event_matches_in_edition": edition_size,
            "main_event_matches_with_archived_points": len(caught),
            "of_them_captured_finished": int(caught["finished"].sum()),
            "share_with_archived_points": round(len(caught) / edition_size, 4),
            "events_with_archived_draw": sorted(part["event"].dropna().unique().tolist()),
            "main_events_with_archived_draw": sorted(main["event"].unique().tolist()),
            "main_draw_copies_finished": int(main["draw_copy_finished"].sum()),
            "matches_in_archived_draws": int(part["matches"].sum()),
        }
    summary = {"by_year": by_year,
               "point_captures_linked_to_an_archived_draw": int(captures["record_key"].isin(linked).sum()),
               "matches_with_point_captures_but_no_archived_draw": {
                   str(y): sorted(g["match_id"].tolist()) for y, g in unlinked_matches.groupby("year")}}
    return table, summary


def main() -> int:
    P.configure_stdout()
    matches = pd.read_parquet(DUMP / "matches.parquet")
    points = pd.read_parquet(DUMP / "points.parquet")
    stats = pd.read_parquet(DUMP / "set_statistics.parquet")
    OUT.mkdir(parents=True, exist_ok=True)

    # accounting
    accounting = matches[["record_key", "route", "year", "event", "match_id", "round_name", "match_status", "record",
                          "record_reason", "points", "fetch_status", "retrieved_at", "source_file"]]
    accounting.to_csv(OUT / "ausopen_accounting.csv", index=False)
    api = matches[matches["route"] == "api"]
    summary = {"generated_at": P.utc_now_iso(), "inputs": {"dump": P.rel(DUMP), "raw": P.rel(A.P.raw_path(A.SOURCE))}}
    summary["accounting"] = {
        "draw_matches": len(api), "expected": sum(A.EXPECTED_MATCHES.values()),
        "by_event": {e: {"listed": int((api["event"] == e).sum()), "expected": n,
                         "records": dict(Counter(api.loc[api["event"] == e, "record"]))}
                     for e, n in A.EXPECTED_MATCHES.items()},
        "by_record": dict(Counter(api["record"])),
        "reasons": dict(Counter(f"{r} | {why}" for r, why in zip(api["record"], api["record_reason"]) if r != "points")),
        "by_status_and_record": dict(Counter(f"{s} | {r}" for s, r in zip(api["match_status"], api["record"]))),
        "points": int(api["points"].fillna("0").astype(int).sum()),
    }
    wayback = matches[matches["route"] == "wayback"]
    if len(wayback):
        summary["accounting"]["wayback"] = {"captures": len(wayback), "by_record": dict(Counter(wayback["record"])),
                                            "by_year_event": dict(Counter(f"{y}|{e}" for y, e in zip(wayback["year"], wayback["event"]))),
                                            "points": int(wayback["points"].fillna("0").astype(int).sum())}

    # commentary map, from the raw documents (serve lines included)
    documents = []
    for _, m in matches[matches["record"].isin(["points", "empty"])].iterrows():
        documents.append((m["record_key"], P.read_json(PROJECT_ROOT / m["source_file"])))
    cmap, csummary = commentary_map(documents)
    cmap.to_csv(OUT / "ausopen_commentary_map.csv", index=False)
    summary["commentary"] = csummary
    summary["commentary"]["outcomes"] = dict(Counter(points["outcome"]))
    named = points[points["subject_name_team"].notna()]
    summary["commentary"]["subject_named_team_agrees"] = int((named["subject_name_team"] == named["subject_team"]).sum())
    summary["commentary"]["subject_named_team_differs"] = int((named["subject_name_team"] != named["subject_team"]).sum())
    summary["commentary"]["subject_name_not_matched"] = int(points["subject_name_team"].isna().sum())

    # per-match checks
    raw = dict(documents)
    mismatches: list[dict] = []
    checks = []
    readings: dict[str, Counter] = defaultdict(Counter)
    steps_back: dict[str, list] = defaultdict(list)
    points_by = dict(tuple(points.groupby("record_key", sort=False)))
    stats_by = dict(tuple(stats.groupby("record_key", sort=False)))
    for _, m in matches[matches["record"] == "points"].iterrows():
        key = m["record_key"]
        pts = points_by[key].sort_values("seq", key=lambda s: s.astype(int))
        row = {"record_key": key, "route": m["route"], "year": m["year"], "event": m["event"], "match_id": m["match_id"],
               "match_status": m["match_status"], "points": len(pts)}
        row.update({f"aces_{k}": v for k, v in check_aces(key, pts, stats_by.get(key, stats.iloc[0:0]), mismatches).items()})
        row.update(check_replay(key, m, pts, mismatches, readings[m["route"]]))
        row.update(check_servers(key, pts, mismatches))
        row["serve_lines_inside_games"] = serve_lines_inside_games(key, raw[key], mismatches)
        steps = timestamp_steps(pts)
        steps_back[m["route"]].extend(steps)
        row["timestamp_steps_back"], row["timestamp_largest_step_back_s"] = len(steps), max(steps, default=0)
        row["points_without_timestamp"] = int(pts["timestamp"].isna().sum())
        checks.append(row)
    checks = pd.DataFrame(checks)
    checks.to_csv(OUT / "ausopen_checks.csv", index=False)
    mism = pd.DataFrame(mismatches, columns=["record_key", "check", "set", "detail", "expected", "found"])
    mism.to_csv(OUT / "ausopen_mismatches.csv", index=False)

    for route, part in checks.groupby("route"):
        summary[f"checks_{route}"] = {
            "matches_with_points": len(part),
            "aces_dfs": {"sets_compared": int(part["aces_sets_compared"].sum()), "sets_agree": int(part["aces_sets_agree"].sum()),
                         "matches_all_sets_agree": int(part["aces_sets_all_agree"].sum()),
                         "matches_totals_agree": int(part["aces_totals_agree"].fillna(False).astype(bool).sum()),
                         "aces_and_dfs_struck_by_server": int(part["aces_struck_by_server"].sum()),
                         "struck_by_receiver": int(part["aces_struck_by_receiver"].sum()),
                         "server_unknown": int(part["aces_server_unknown"].sum())},
            "score_replay": {"replayed": int(part["replayed"].sum()),
                             "final_score_reproduced": int(part["final_score_reproduced"].fillna(False).astype(bool).sum()),
                             "game_ends_agree": int(part["game_ends_agree"].fillna(False).astype(bool).sum()),
                             "game_numbering_agrees": int(part["game_numbering_agrees"].fillna(False).astype(bool).sum()),
                             "end_types_agree": int(part["end_types_agree"].fillna(False).astype(bool).sum()),
                             "matches_with_points_after_end": int((part["points_after_end"].fillna(0) > 0).sum()),
                             "matches_with_score_text_differences": int((part["score_texts_differing"].fillna(0) > 0).sum()),
                             "score_texts_differing": int(part["score_texts_differing"].fillna(0).sum()),
                             "score_texts_unchecked": int(part["score_texts_unchecked"].fillna(0).sum())},
            "servers": {"games": int(part["games"].sum()), "server_unknown_games": int(part["server_unknown_games"].sum()),
                        "matches_with_server_repeats": int((part["server_repeats"] > 0).sum())},
            "feed_defects": {"games_with_extra_end_entries": int(part["games_with_extra_end_entries"].fillna(0).sum()),
                             "serve_lines_inside_games": int(part["serve_lines_inside_games"].sum()),
                             "serve_lines_contradicted_by_scores": int(part["serve_lines_contradicted"].fillna(0).sum())},
            "timestamps": {"points": int(part["points"].sum()),
                           "points_without_timestamp": int(part["points_without_timestamp"].sum()),
                           "points_stamped_later_than_the_next": len(steps_back[route]),
                           "matches_with_such_points": int((part["timestamp_steps_back"] > 0).sum()),
                           "step_back_seconds": ({q: float(pd.Series(steps_back[route]).quantile(v))
                                                  for q, v in (("median", .5), ("p90", .9), ("max", 1.0))}
                                                 if steps_back[route] else {}),
                           "steps_back_over_10_min": sum(s > 600 for s in steps_back[route]),
                           "steps_back_over_1_hour": sum(s > 3600 for s in steps_back[route])},
            "games_score_readings": dict(sorted(readings[route].items())),
        }
    summary["wayback_captures_against_live"] = captures_against_live(matches, raw)
    archived_path = DUMP / "archived_draws.parquet"
    if archived_path.exists():
        archived = pd.read_parquet(archived_path)
        if len(archived):
            coverage, summary["archived_editions"] = archived_coverage(archived, matches)
            coverage.to_csv(OUT / "ausopen_wayback_coverage.csv", index=False)
    summary["receipts"] = receipts_summary()
    summary["mismatches_by_check_and_route"] = dict(Counter(
        f"{c}|{'wayback' if '@' in k else 'api'}" for c, k in zip(mism["check"], mism["record_key"])))
    (OUT / "ausopen_verification.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
                                                   encoding="utf-8")
    P.log(json.dumps(summary, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
