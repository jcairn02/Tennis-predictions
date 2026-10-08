"""What SofaScore's undocumented per-point codes mean, inferred from the downloaded records.

Each listed point state carries ``pointDescription``, ``homePointType`` and ``awayPointType`` (integers). This
script derives, for every state, who won the point (from the score progression within the game), who served,
and the situation the state creates (game point, break point, set point, match point), then tabulates the codes
against those facts. Ace and double-fault codes are checked against the same matches' box scores.

Output: data/studies/point_shot_sources/scrape/sofascore_point_codes.json
Usage:  ./python.sh src/eda/point_shot_sources/sofascore_codes.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402

RAW = P.raw_path("sofascore", "events")
OUT = P.STUDY_ROOT / "sofascore_point_codes.json"
ORDER = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4}


def point_winner(prev: tuple[str, str], cur: tuple[str, str], tiebreak: bool) -> int | None:
    """1 if home won the point that produced ``cur`` from ``prev``, 2 if away, None if unclear."""
    if tiebreak:
        try:
            dh, da = int(cur[0]) - int(prev[0]), int(cur[1]) - int(prev[1])
        except ValueError:
            return None
        return 1 if (dh, da) == (1, 0) else 2 if (dh, da) == (0, 1) else None
    ph, pa, ch, ca = (ORDER.get(prev[0]), ORDER.get(prev[1]), ORDER.get(cur[0]), ORDER.get(cur[1]))
    if None in (ph, pa, ch, ca):
        return None
    if (ch, ca) == (ph + 1, pa):
        return 1
    if (ch, ca) == (ph, pa + 1):
        return 2
    if (prev, cur) == (("A", "40"), ("40", "40")):
        return 2
    if (prev, cur) == (("40", "A"), ("40", "40")):
        return 1
    return None


def game_point_for(state: tuple[str, str], tiebreak: bool, target: int = 7) -> set[int]:
    """Sides one point from winning the game (1 home, 2 away) at this state."""
    h, a = state
    if tiebreak:
        try:
            ih, ia = int(h), int(a)
        except ValueError:
            return set()
        out = set()
        if ih >= target - 1 and ih - ia >= 1:
            out.add(1)
        if ia >= target - 1 and ia - ih >= 1:
            out.add(2)
        return out
    out = set()
    if h == "A" or (h == "40" and a in ("0", "15", "30")):
        out.add(1)
    if a == "A" or (a == "40" and h in ("0", "15", "30")):
        out.add(2)
    return out


def set_point_for(games_before: tuple[int, int], side: int, tiebreak: bool) -> bool:
    """Would winning this game win the set for ``side``? (standard sets; a 6-6 tiebreak decides)"""
    mine, theirs = games_before if side == 1 else games_before[::-1]
    if tiebreak:
        return True
    return (mine + 1 >= 6 and mine + 1 - theirs >= 2)


def main():
    counts = {"pointDescription": Counter(), "homePointType": Counter(), "awayPointType": Counter()}
    by_winner = defaultdict(Counter)       # (homeType, awayType) -> winner
    by_situation = defaultdict(Counter)    # winner's type -> situation created
    desc_by_server = defaultdict(Counter)  # pointDescription -> who served / who won
    ace_check, df_check = [], []
    events = 0
    for folder in sorted(RAW.iterdir()):
        pbp_path, stats_path = folder / "point-by-point.json", folder / "statistics.json"
        if not pbp_path.exists():
            continue
        events += 1
        pbp = P.read_json(pbp_path).get("pointByPoint") or []
        sets = sorted(pbp, key=lambda s: s.get("set") or 0)
        set_tally = [0, 0]
        best_of_sets = 2
        desc_counts = defaultdict(Counter)  # description -> serving side -> count
        for st in sets:
            games = sorted(st.get("games") or [], key=lambda g: g.get("game") or 0)
            games_before = (0, 0)
            for g in games:
                score = g.get("score") or {}
                serving = score.get("serving")
                points = g.get("points") or []
                tiebreak = any(str(p.get("homePoint")) not in ORDER or str(p.get("awayPoint")) not in ORDER for p in points)
                prev = ("0", "0")
                for p in points:
                    cur = (str(p.get("homePoint")), str(p.get("awayPoint")))
                    winner = point_winner(prev, cur, tiebreak)
                    ht, at, desc = p.get("homePointType"), p.get("awayPointType"), p.get("pointDescription")
                    counts["pointDescription"][str(desc)] += 1
                    counts["homePointType"][str(ht)] += 1
                    counts["awayPointType"][str(at)] += 1
                    by_winner[f"{ht},{at}"][str(winner)] += 1
                    desc_by_server[str(desc)][f"serving={serving},won={winner}"] += 1
                    desc_counts[str(desc)][serving] += 1
                    gp = game_point_for(cur, tiebreak)
                    for side in (1, 2):
                        code = ht if side == 1 else at
                        if winner != side:
                            continue
                        situation = []
                        if side in gp:
                            situation.append("game point" if serving == side else "break point")
                            if set_point_for(games_before, side, tiebreak):
                                situation.append("set point")
                                if set_tally[side - 1] + 1 > best_of_sets - 1:
                                    situation.append("match point")
                        if not situation:
                            situation.append("plain")
                        by_situation[str(code)][" + ".join(situation)] += 1
                    prev = cur
                scoring = score.get("scoring")
                games_before = (games_before[0] + (scoring == 1), games_before[1] + (scoring == 2))
            winner_set = 1 if games_before[0] > games_before[1] else 2
            set_tally[winner_set - 1] += 1
        if stats_path.exists():
            stats = P.read_json(stats_path).get("statistics") or []
            items = {i["key"]: i for per in stats if per.get("period") == "ALL" for grp in per.get("groups") or []
                     for i in grp.get("statisticsItems") or []}
            aces = items.get("aces") or {}
            dfs = items.get("doubleFaults") or {}
            if aces:
                ace_check.append({"event": folder.name, "aces_home": aces.get("homeValue"), "aces_away": aces.get("awayValue"),
                                  **{f"desc{d}_served_by_home": desc_counts[d].get(1, 0) for d in ("1", "2", "3")},
                                  **{f"desc{d}_served_by_away": desc_counts[d].get(2, 0) for d in ("1", "2", "3")}})
            if dfs:
                df_check.append({"event": folder.name, "df_home": dfs.get("homeValue"), "df_away": dfs.get("awayValue"),
                                 **{f"desc{d}_served_by_home": desc_counts[d].get(1, 0) for d in ("1", "2", "3")},
                                 **{f"desc{d}_served_by_away": desc_counts[d].get(2, 0) for d in ("1", "2", "3")}})

    def agreement(rows, value_key, desc):
        n = sum(1 for r in rows if r[f"{value_key}_home"] is not None)
        hits = sum(1 for r in rows if r[f"{value_key}_home"] == r[f"desc{desc}_served_by_home"]
                   and r[f"{value_key}_away"] == r[f"desc{desc}_served_by_away"])
        return {"matches": n, "exact_agreement": hits}

    summary = {
        "events_with_record": events,
        "value_counts": {k: dict(v.most_common()) for k, v in counts.items()},
        "type_pair_vs_point_winner": {k: dict(v) for k, v in sorted(by_winner.items(), key=lambda kv: -sum(kv[1].values()))},
        "winner_type_vs_situation_created": {k: dict(v.most_common()) for k, v in sorted(by_situation.items())},
        "description_vs_server_and_winner": {k: dict(v.most_common()) for k, v in sorted(desc_by_server.items())},
        "aces_vs_description_code": {d: agreement(ace_check, "aces", d) for d in ("1", "2", "3")},
        "double_faults_vs_description_code": {d: agreement(df_check, "df", d) for d in ("1", "2", "3")},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
