"""Checks of the ITF live-data API collection (study official_point_feeds; work package P1 of
docs/studies/gap_downloads/collection-plan.md): what the day lists hold, which played singles matches have
statistics and points (by tour, draw and round), whether each match's points rebuild its listed set scores, whether
the points' aces and double faults equal the statistics', and whether a full week's events equal Wikipedia's lists.

Reads the staged tables in data/dump/points/itf_live/ (matches, events, documents, statistics, points); rebuild them
first with ./python.sh -m src.ingest.point_sources.itf_live --stage-only. Wikipedia's "2026 ITF Men's / Women's World
Tennis Tour" pages are read through the MediaWiki API (--fetch-wikipedia: four requests, at most once a day) into
data/raw/point_sources/itf_live/_reference/wikipedia/, with receipts in _reference/_receipts.jsonl. Each Wikipedia
event cell links the ITF's draw page, whose last part is the event's ITF key (m-itf-chn-2026-030): the comparison is
by that key, week by week (the week block's Monday is the main draw's). The week of 28 Sep 2026 (ISO week 40) is on
the July-September pages; the October-December pages begin with 5 Oct (week 41).

Played: a singles match whose latest listed status is over (stateType "post") and not a walkover. The final
qualifying round of an event is its qualifying draw's highest round order.

Outputs in data/studies/official_point_feeds/:
    itf_live_verification.json   every total, and each figure the plan's "Expected" names beside it
    itf_live_events.csv          one row per event: tour, grade, ITF key, main-draw week, singles listed and played by
                                 draw, played matches with statistics and with points, whether Wikipedia lists it
    itf_live_rounds.csv          by tour, draw and round: singles played, with statistics, with points
    itf_live_checks.csv.gz       one row per played singles match: its documents, the games of each set rebuilt from
                                 its points against the listed set scores, and aces and double faults counted from
                                 the points against the statistics

Usage:
    ./python.sh src/eda/official_point_feeds/verify_itf_live.py [--fetch-wikipedia] [--week 2026-W40]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.point_sources import itf_live as L      # noqa: E402

DUMP = P.dump_path(L.SOURCE)
OUT = L.STUDY
REFERENCE = "_reference"                                 # data/raw/point_sources/itf_live/_reference/
WIKI_API = "https://en.wikipedia.org/w/api.php?action=parse&format=json&formatversion=2&redirects=1&prop=wikitext%7Crevid&page="
WIKI_PAGES = {
    ("M", "jul_sep"): "2026 ITF Men's World Tennis Tour (July–September)",
    ("W", "jul_sep"): "2026 ITF Women's World Tennis Tour (July–September)",
    ("M", "oct_dec"): "2026 ITF Men's World Tennis Tour (October–December)",
    ("W", "oct_dec"): "2026 ITF Women's World Tennis Tour (October–December)",
}
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
WEEK_MARK = re.compile(r"^\|\s*rowspan\s*=\s*\"?\d+\"?\s*\|\s*(" + "|".join(MONTHS) + r")\s+(\d{1,2})\s*$", re.M)
ITF_KEY = re.compile(r"/((?:m|w)-itf-[a-z]{3}-\d{4}-[0-9a-z]+)/", re.I)


# ------------------------------------------------------------------------------------------ Wikipedia
def wiki_receipts():
    return P.C.Receipts(REFERENCE, root=P.raw_path(L.SOURCE))


def wiki_name(tour: str, period: str, day: str) -> str:
    return f"wikipedia/itf_{'men' if tour == 'M' else 'women'}_2026_{period}@{day}"


def wiki_dest(name: str) -> Path:
    return P.raw_path(L.SOURCE, REFERENCE, *name.split("/")[:-1], name.split("/")[-1] + ".json.gz")


def fetch_wikipedia() -> dict:
    """The four pages, once a day (a page already read today is not asked again)."""
    from urllib.parse import quote

    receipts = wiki_receipts()
    client = P.Client("chrome", min_interval=2.0, jitter=1.0, max_requests=8,
                      headers={"Accept": "application/json", "Accept-Language": "en-GB,en;q=0.9"})
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    out = {}
    for (tour, period), title in WIKI_PAGES.items():
        name = wiki_name(tour, period, day)
        r = P.fetch(client, WIKI_API + quote(title), wiki_dest(name), receipts, name=name,
                    validator=P.json_validator, compress=True, extra={"title": title})
        out[name] = {k: r.get(k) for k in ("status", "bytes", "sha256", "retrieved_at", "error", "skipped")}
    return out


def latest_wiki_pages() -> dict:
    """(tour, period) -> (receipt, parsed answer) of the latest saved read of each page."""
    pages = {}
    for name, r in sorted(wiki_receipts().all().items()):
        m = re.match(r"wikipedia/itf_(men|women)_2026_(\w+?)@(\d{8})$", name)
        if not m or r.get("status") != 200 or r.get("error") or not wiki_dest(name).exists():
            continue
        pages[("M" if m.group(1) == "men" else "W", m.group(2))] = (r, P.read_json(wiki_dest(name)))
    return pages


def wiki_week_keys(text: str, year: int = 2026) -> pd.DataFrame:
    """Every ITF key a Wikipedia tour page links, with the Monday of the week block it sits in."""
    marks = [(m.start(), dt.date(year, MONTHS[m.group(1)], int(m.group(2)))) for m in WEEK_MARK.finditer(text)]
    rows = []
    for k in ITF_KEY.finditer(text):
        week = next((d for pos, d in reversed(marks) if pos < k.start()), None)
        if week is not None:
            rows.append({"itf_key": k.group(1).upper(), "week_monday": week})
    out = pd.DataFrame(rows, columns=["itf_key", "week_monday"]).drop_duplicates("itf_key")
    out["iso_week"] = [f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" for d in out["week_monday"]]
    return out


# ------------------------------------------------------------------------------------------ the checks
def sets_of(text) -> dict[int, tuple[int, int]]:
    """'1:6/0 2:7/5' -> {1: (6, 0), 2: (7, 5)}: games and tiebreak points of each set."""
    out = {}
    for part in str(text or "").split():
        m = re.match(r"^(\d+):(-?\d+)/(-?\d+)$", part)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
    return out


def games_from_points(points: pd.DataFrame) -> dict[int, tuple[int, int]]:
    """Games won by side 1 and side 2 in each set, counted from the points' game-won flags (one per game)."""
    out = {}
    first = points.drop_duplicates(["set_index", "game_index"])
    for (set_no, s1, s2) in zip(first["set_number"], first["side1_game_won"], first["side2_game_won"]):
        a, b = out.get(int(set_no), (0, 0))
        out[int(set_no)] = (a + (s1 == "TRUE"), b + (s2 == "TRUE"))
    return out


def set_winner(games: tuple) -> int | None:
    a, b = games
    return 1 if (a or 0) > (b or 0) else 2 if (b or 0) > (a or 0) else None


def games_check(listed: dict[int, tuple], rebuilt: dict[int, tuple]) -> str:
    """How a match's games by set, rebuilt from its points, stand against the listed set scores:
    "agree";
    "match tiebreak": the last set is a tiebreak to 10 played in place of a set (some qualifying draws), which the point
                      log counts point by point as games (10-7) where the list writes a set (6-4 or 7-6); the earlier
                      sets agree and so does the last set's winner;
    "points short":   the points lack games the list has (the log stops early); nothing else differs;
    "list short":     the list lacks games the points have (its record stopped before the end); nothing else differs;
    "contradiction":  anything else."""
    if rebuilt == listed:
        return "agree"
    last = max(rebuilt) if rebuilt else None
    if (last in listed and max(rebuilt[last]) >= 10 and set_winner(rebuilt[last]) == set_winner(listed[last])
            and all(rebuilt.get(s) == listed.get(s) for s in set(rebuilt) | set(listed) if s != last)):
        return "match tiebreak"

    def within(small: dict, big: dict) -> bool:
        return set(small) <= set(big) and all(small[s][i] <= (big[s][i] or 0) for s in small for i in (0, 1))

    if within(rebuilt, listed):
        return "points short"
    if within(listed, rebuilt):
        return "list short"
    return "contradiction"


def match_checks(played: pd.DataFrame, docs: pd.DataFrame, stats: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    has = docs[docs["has_data"].eq("TRUE")]
    with_stats, with_points = set(has.loc[has["kind"].eq("stats"), "match_id"]), set(has.loc[has["kind"].eq("points"), "match_id"])
    asked = docs.groupby("match_id")["kind"].agg(lambda k: ";".join(sorted(set(k))))
    ace = stats[stats["period"].eq("match") & stats["stat"].isin(["Aces", "Double Faults"])]
    ace_val = {(m, s, o): v for m, s, o, v in zip(ace["match_id"], ace["stat"], ace["side_order"], ace["value"])}
    by_match = {m: g for m, g in points.groupby("match_id")}
    rows = []
    for r in played.itertuples(index=False):
        mid = r.match_id
        rec = {"match_id": mid, "list_date": r.list_date, "event_tennis_id": r.event_tennis_id, "event": r.event_name,
               "tour": r.tour, "draw": r.draw, "round": r.round, "round_order": r.round_order,
               "final_qualifying_round": r.final_qualifying_round, "status": r.status,
               "documents_asked": asked.get(mid), "has_stats": mid in with_stats, "has_points": mid in with_points}
        sets1, sets2 = sets_of(r.side1_sets), sets_of(r.side2_sets)
        rec["zero_set_listed"] = any(sets1.get(s) == (0, 0) and sets2.get(s) == (0, 0) for s in sets1)
        rec["listed_winner"] = isinstance(r.winner_side_id, str) and bool(r.winner_side_id)
        pts = by_match.get(mid)
        if pts is not None and len(pts):
            listed = {n: sets_of(getattr(r, f"side{n}_sets")) for n in (1, 2)}
            # a set begun but with no game won (a retirement in its first game) rebuilds as 0-0: no set, as listed
            rebuilt = {s: g for s, g in games_from_points(pts).items() if g != (0, 0)}
            # a retirement is listed "Complete" with the unplayed set as 0-0 (no games, no tiebreak): not a set
            listed_games = {s: (listed[1].get(s, (None,))[0], listed[2].get(s, (None,))[0])
                            for s in set(listed[1]) | set(listed[2])
                            if listed[1].get(s, (0, 0)) != (0, 0) or listed[2].get(s, (0, 0)) != (0, 0)}
            rec.update(points=len(pts), points_consistent=bool(pts["consistent"].eq("TRUE").all()),
                       sets_listed=" ".join(f"{s}:{a}-{b}" for s, (a, b) in sorted(listed_games.items())),
                       sets_from_points=" ".join(f"{s}:{a}-{b}" for s, (a, b) in sorted(rebuilt.items())),
                       games_agree=rebuilt == listed_games, games_check=games_check(listed_games, rebuilt))
            for side in (1, 2):
                serve = pts[pts["server_side_order"].eq(str(side))]
                for stat, outcome in (("Aces", "ACE"), ("Double Faults", "DOUBLE_FAULT")):
                    key = f"{'aces' if stat == 'Aces' else 'double_faults'}_side{side}"
                    rec[f"{key}_points"] = int(serve["outcome"].eq(outcome).sum())
                    value = ace_val.get((mid, stat, str(side)))
                    rec[f"{key}_stats"] = None if value is None else int(float(value))
            if mid in with_stats:
                rec["aces_df_agree"] = all(rec[f"{k}_points"] == rec[f"{k}_stats"] for k in
                                           ("aces_side1", "aces_side2", "double_faults_side1", "double_faults_side2"))
        rows.append(rec)
    return pd.DataFrame(rows)


def share(n: int, d: int) -> str:
    return f"{n} of {d} ({100 * n / d:.1f}%)" if d else "0 of 0"


def main() -> int:
    P.configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch-wikipedia", action="store_true", help="read Wikipedia's four pages first (4 requests)")
    ap.add_argument("--week", default="2026-W40", help="the full week whose singles are counted (main-draw ISO week)")
    ap.add_argument("--wiki-weeks", default="2026-W38,2026-W39,2026-W40,2026-W41",
                    help="main-draw ISO weeks whose events are compared with Wikipedia's (comma list)")
    ap.add_argument("--first-own-day", default="2026-09-24",
                    help="the first day the collector's own first run listed (earlier days: the research's lists)")
    args = ap.parse_args()
    fetched = fetch_wikipedia() if args.fetch_wikipedia else None

    m = pd.read_parquet(DUMP / "matches.parquet")
    ev = pd.read_parquet(DUMP / "events.parquet")
    docs = pd.read_parquet(DUMP / "documents.parquet")
    stats = pd.read_parquet(DUMP / "statistics.parquet", columns=["match_id", "stat", "period", "side_order", "value"])
    points = pd.read_parquet(DUMP / "points.parquet")
    # documents are filed under the id they were asked for; the statistics rows carry the API's own matchId
    latest = m[m["latest"].eq("TRUE")].copy()
    latest["tour"] = latest["gender"].map({"men": "M", "women": "W"})
    singles = latest[latest["match_type"].str.lower().eq("singles")].copy()
    singles["draw_kind"] = np.where(singles["draw"].str.contains("Qualif", case=False), "qualifying", "main")
    singles["round_order_n"] = pd.to_numeric(singles["round_order"], errors="coerce")
    top = singles[singles["draw_kind"].eq("qualifying")].groupby("event_tennis_id")["round_order_n"].max()
    singles["final_qualifying_round"] = singles["draw_kind"].eq("qualifying") & singles["round_order_n"].eq(
        singles["event_tennis_id"].map(top))
    over = singles["status_state_type"].str.lower().eq("post")
    walkover = singles["status"].fillna("").str.lower().eq("walkover")
    played = singles[over & ~walkover].copy()
    played["draw"] = played["draw_kind"]

    checks = match_checks(played, docs, stats, points)
    OUT.mkdir(parents=True, exist_ok=True)
    checks.to_csv(OUT / "itf_live_checks.csv.gz", index=False, compression="gzip")

    # by tour, draw and round
    rounds = (checks.assign(final_q=checks["final_qualifying_round"])
              .groupby(["tour", "draw", "round", "round_order"], dropna=False)
              .agg(played=("match_id", "size"), with_stats=("has_stats", "sum"), with_points=("has_points", "sum"),
                   documents_asked=("documents_asked", lambda s: int(s.notna().sum())))
              .reset_index().sort_values(["tour", "draw", "round_order"]))
    rounds.to_csv(OUT / "itf_live_rounds.csv", index=False)

    # events, with Wikipedia's listing
    pages = latest_wiki_pages()
    wiki = pd.concat([wiki_week_keys(page["parse"]["wikitext"]).assign(tour=tour, page=period,
                                                                      revid=page["parse"].get("revid"))
                      for (tour, period), (_, page) in pages.items()], ignore_index=True) if pages else \
        pd.DataFrame(columns=["itf_key", "week_monday", "iso_week", "tour", "page", "revid"])
    wiki = wiki.drop_duplicates("itf_key", keep="last")
    per_event = []
    for e in ev.itertuples(index=False):
        mine = checks[checks["event_tennis_id"].eq(e.tennis_id)]
        listed = singles[singles["event_tennis_id"].eq(e.tennis_id)]
        row = {"tour": e.tour, "grade": e.grade, "name": e.name, "tennis_id": e.tennis_id, "start_date": e.start_date[:10],
               "end_date": e.end_date[:10], "main_draw_week": e.main_draw_week, "surface": e.surface,
               "country": e.country, "list_dates": f"{e.first_list_date}..{e.last_list_date}"}
        for kind in ("main", "qualifying"):
            lk, pk = listed[listed["draw_kind"].eq(kind)], mine[mine["draw"].eq(kind)]
            row.update({f"{kind}_listed": len(lk), f"{kind}_played": len(pk),
                        f"{kind}_with_stats": int(pk["has_stats"].sum()), f"{kind}_with_points": int(pk["has_points"].sum())})
        row["doubles_listed"] = int(e.doubles)
        w = wiki[wiki["itf_key"].eq(e.tennis_id)]
        row["wikipedia_week"] = w["iso_week"].iloc[0] if len(w) else None
        per_event.append(row)
    events = pd.DataFrame(per_event).sort_values(["main_draw_week", "tour", "grade", "name"])
    events.to_csv(OUT / "itf_live_events.csv", index=False)

    # weeks against Wikipedia, by ITF key
    by_week = {}
    for week in args.wiki_weeks.split(","):
        week_api = set(events.loc[events["main_draw_week"].eq(week), "tennis_id"])
        week_wiki = set(wiki.loc[wiki["iso_week"].eq(week), "itf_key"])
        for tour in ("M", "W"):
            a = {k for k in week_api if k.startswith(tour)}
            b = {k for k in week_wiki if k.startswith(tour)}
            by_week[f"{week} {tour}"] = {"api_events": len(a), "wikipedia_events": len(b), "both": len(a & b),
                                         "api_only": sorted(a - b), "wikipedia_only": sorted(b - a)}
    by_tour = {t: by_week.get(f"{args.week} {t}", {}) for t in ("M", "W")}
    wk = checks.merge(events[["tennis_id", "main_draw_week"]], left_on="event_tennis_id", right_on="tennis_id")
    week_singles = singles.merge(events[["tennis_id", "main_draw_week"]], left_on="event_tennis_id", right_on="tennis_id")
    week_singles = week_singles[week_singles["main_draw_week"].eq(args.week)]

    def coverage(frame: pd.DataFrame) -> dict:
        """Shares over the played matches whose two documents were both asked (the rest are not counted as lacking
        them: the research, whose answers were imported, often asked for the statistics alone)."""
        asked = frame[frame["documents_asked"].eq("points;stats")]
        return {"played": int(len(frame)), "documents_asked": share(len(asked), len(frame)),
                "with_stats": share(int(asked["has_stats"].sum()), len(asked)),
                "with_points": share(int(asked["has_points"].sum()), len(asked))}

    with_pts = checks[checks["has_points"]] if "games_agree" in checks else checks.iloc[0:0]

    # by grade, the statistic types each grade's matches carry, and the time fields
    grade = checks["event_tennis_id"].map(events.set_index("tennis_id")["grade"])
    by_grade = {f"{str(g).upper()} {d}": coverage(f) for (g, d), f in checks.assign(grade=grade).groupby(["grade", "draw"])}
    st_types = stats[stats["period"].eq("match")].groupby("match_id")["stat"].nunique()
    doc_event = docs[docs["kind"].eq("stats")].set_index("match_id")["event_tennis_id"]
    types_by_grade = (pd.DataFrame({"types": st_types, "grade": st_types.index.map(doc_event).map(
        events.set_index("tennis_id")["grade"])}).groupby("grade")["types"]
        .agg(lambda s: dict(Counter(s.astype(int)).most_common())))
    all_types = sorted(stats["stat"].dropna().unique().tolist())
    have_stats = docs[docs["kind"].eq("stats") & docs["has_data"].eq("TRUE")]

    def fill(frame: pd.DataFrame, column: str) -> str:
        return share(int(frame[column].notna().sum()), len(frame))

    time_fields = {"day_lists (played singles)": {c: fill(played, c) for c in
                                                  ("date_start_local", "actual_end_date", "duration", "schedule_text",
                                                   "order_in_schedule", "court_name", "actual_start_date")},
                   "statistics answers with data": {c: fill(have_stats, c) for c in
                                                    ("actual_start_date", "actual_end_date", "duration")}}
    summary = {
        "built_at": P.utc_now_iso(),
        "tables": {k: int(len(v)) for k, v in (("matches_rows", m), ("events", ev), ("documents", docs),
                                                ("statistics", stats), ("points", points))},
        "list_days": sorted(m["list_date"].unique().tolist()),
        "captures": int(m["capture"].nunique()),
        "distinct_matches": int(len(latest)),
        "singles": {"listed": int(len(singles)), "played": int(len(played)), "walkovers": int((over & walkover).sum()),
                    "not_over": int((~over).sum()),
                    "not_over_by_status": dict(Counter(singles.loc[~over, "status"].fillna("(none)")))},
        "doubles_listed": int((latest["match_type"].str.lower() == "doubles").sum()),
        "documents": {"asked": int(len(docs)), "by_kind_status": {f"{k}:{s}": int(n) for (k, s), n in
                                                                  docs.groupby(["kind", "status"]).size().items()},
                      "with_data": {k: int(n) for k, n in docs[docs["has_data"].eq("TRUE")].groupby("kind").size().items()}},
        "coverage": {
            "main_draw": coverage(checks[checks["draw"].eq("main")]),
            "qualifying": coverage(checks[checks["draw"].eq("qualifying")]),
            "qualifying_final_round": coverage(checks[checks["final_qualifying_round"]]),
            "qualifying_earlier_rounds": coverage(checks[checks["draw"].eq("qualifying") & ~checks["final_qualifying_round"]]),
            "by_tour_and_draw": {f"{t} {d}": coverage(g) for (t, d), g in checks.groupby(["tour", "draw"])},
            "by_grade_and_draw": by_grade,
            "by_listing": {
                f"own lists ({args.first_own_day} on)": coverage(checks[checks["list_date"] >= args.first_own_day]),
                f"research lists only (before {args.first_own_day})": coverage(
                    checks[checks["list_date"] < args.first_own_day]),
            },
        },
        "points_checks": {
            "matches_with_points": int(len(with_pts)),
            "games_by_set_agree_with_the_list": share(int(with_pts.get("games_agree", pd.Series(dtype=bool)).eq(True).sum()),
                                                      len(with_pts)),
            "games_check": {str(k): int(v) for k, v in with_pts["games_check"].value_counts().items()},
            "list_short_without_a_listed_winner": int((with_pts["games_check"].eq("list short")
                                                       & ~with_pts["listed_winner"]).sum()),
            "played_matches_listed_complete_without_a_winner": {
                "matches": int((~checks["listed_winner"]).sum()),
                "by_list_date": {str(k): int(v) for k, v in
                                 checks[~checks["listed_winner"]].groupby("list_date").size().items()},
                "with_points": int((~checks["listed_winner"] & checks["has_points"]).sum())},
            "played_matches_listed_with_a_0_0_set (retirements, status still Complete)": {
                str(k): int(v) for k, v in checks[checks["zero_set_listed"]].groupby("status").size().items()},
            "both_views_agree_on_every_point": share(int(with_pts.get("points_consistent", pd.Series(dtype=bool)).eq(True).sum()),
                                                     len(with_pts)),
            "aces_and_double_faults_agree_with_statistics": share(
                int(checks.get("aces_df_agree", pd.Series(dtype=object)).eq(True).sum()),
                int(checks.get("aces_df_agree", pd.Series(dtype=object)).notna().sum())),
        },
        "statistic_types": {"all_seen": all_types, "count": len(all_types),
                            "types_per_match_by_grade": {str(k).upper(): v for k, v in types_by_grade.items()}},
        "time_fields": time_fields,
        "events_against_wikipedia": by_week,
        "full_week": {"week": args.week, "events_by_tour": by_tour,
                      "singles_listed": int(len(week_singles)),
                      "singles_played": int(len(wk[wk["main_draw_week"].eq(args.week)])),
                      "wikipedia_pages": {f"{t} {p}": {"revid": page["parse"].get("revid"), "retrieved_at": r.get("retrieved_at"),
                                                       "url": r.get("url"), "sha256": r.get("sha256")}
                                          for (t, p), (r, page) in pages.items()}},
        "expected_in_the_plan": {
            "every event of a week (23 of 23 against Wikipedia)": {k: f"{v['both']} of {v['wikipedia_events']} "
                                                                       f"(API {v['api_events']})"
                                                                    for k, v in by_week.items()},
            "about 1,500 singles matches a week": int(len(week_singles)),
            "statistics and points on every main-draw match sampled (32 of 32)": coverage(checks[checks["draw"].eq("main")]),
            "about two-thirds of qualifying matches (the final round always)": {
                "qualifying": coverage(checks[checks["draw"].eq("qualifying")]),
                "final_round": coverage(checks[checks["final_qualifying_round"]])},
        },
        "wikipedia_fetch": fetched,
    }
    (OUT / "itf_live_verification.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
                                                    encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("singles", "coverage", "points_checks", "expected_in_the_plan")},
                     indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
