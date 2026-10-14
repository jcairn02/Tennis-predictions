"""Link each match of the gap slam_points_ao_rg to its SofaScore event.

Reads data/studies/ao_rg_points/gap_matches.csv (gap.py) and the season listings held under
data/raw/point_sources/sofascore_tournaments/ (src/ingest/point_sources/sofascore_tournaments.py).

Rules (those of the gap probe, src/eda/gap_sources/sofascore_probe.py, restricted to the edition's own season):
* Candidates: singles events of the edition's SofaScore season: the category of the tour (ATP, WTA), the unique
  tournament "<Slam>, Men|Women", the season of the year; starting from 10 days before to 21 after the edition's
  first gap match (the map dates Slam matches by the tournament's first day).
* Names: both players share a name word (three letters or more, accents and particles dropped; two letters for a
  name with no longer word, such as Li Tu), in one orientation; the score is the number of words shared. The
  highest score wins; between equal scores, an event of the main draw's days whose round is not labelled
  qualifying wins. Two best candidates still equal are left unlinked and reported.
* The map lists the winner first, so the SofaScore winner's side is checked against it.

Writes data/studies/ao_rg_points/sofascore_links.csv (one row per gap match; ``event_id`` blank when unlinked) and
sofascore_fetch_order.csv (the linked events, those without a complete point record first), which the adapter's
--events-file reads.

Run: ./python.sh src/eda/ao_rg_points/link_sofascore.py
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import sofascore as S                  # noqa: E402
from src.ingest.point_sources import sofascore_tournaments as T      # noqa: E402

OUT = PROJECT_ROOT / "data" / "studies" / "ao_rg_points"
CATEGORY_TOUR = {"ATP": "M", "WTA": "W"}
EVENT = {"M": "Men", "W": "Women"}
PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos", "du"}
WINDOW = (-10, 21)
MAIN_DRAW_LEAD = 2   # days before the edition's first gap match from which an event counts as main draw


def words(name) -> frozenset:
    """Name words of three letters or more; a name with none ('Li Tu') keeps its two-letter words."""
    text = "".join(ch for ch in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(ch))
    found = [w for w in re.split(r"[^a-z]+", text.lower()) if len(w) >= 2 and w not in PARTICLES]
    return frozenset(w for w in found if len(w) >= 3) or frozenset(found)


def team_words(team: dict) -> frozenset:
    return words(team.get("name")) | words(team.get("shortName")) | words((team.get("slug") or "").replace("-", " "))


def pair_score(a: frozenset, b: frozenset, home: frozenset, away: frozenset) -> tuple[int, int]:
    """(words shared in the better orientation, 1 if name1 is home else 2); (0, 0) unless both players share one."""
    best = (0, 0)
    for side, (x, y) in ((1, (home, away)), (2, (away, home))):
        s1, s2 = len(a & x), len(b & y)
        if s1 and s2 and s1 + s2 > best[0]:
            best = (s1 + s2, side)
    return best


def is_qualifying(event: dict) -> bool:
    return "qualif" in str(S._dig(event, ("roundInfo", "name")) or "").lower()


def candidates_by_edition(events: dict[int, dict]) -> dict[str, list[dict]]:
    """Singles events of the Slam singles seasons held, keyed 'tour|tname|year'."""
    out: dict[str, list[dict]] = {}
    for entry in events.values():
        e = entry["event"]
        if S.is_doubles(e):
            continue
        tour = CATEGORY_TOUR.get(S._dig(e, ("tournament", "category", "name")))
        ut_name = S._dig(e, ("tournament", "uniqueTournament", "name")) or ""
        m = re.fullmatch(r"(Australian Open|Roland Garros|Wimbledon|US Open), (Men|Women)", ut_name)
        if not tour or not m or EVENT[tour] != m.group(2):
            continue
        year = S._dig(e, ("season", "year"))
        e = dict(e, _hw=team_words(e.get("homeTeam") or {}), _aw=team_words(e.get("awayTeam") or {}))
        out.setdefault(f"{tour}|{m.group(1)}|{year}", []).append(e)
    return out


def link_one(row: pd.Series, cands: list[dict], d0: pd.Timestamp) -> dict:
    """The event of one gap match. Between events naming both players equally well, one in the main-draw window
    (from two days before the edition's first gap match, which the map dates by the main draw's first day) and
    not labelled qualifying is preferred: two players can meet in qualifying and again in the first round
    (Pouille and Rodionov, Roland Garros 2023), and SofaScore gives some qualifying events no round name."""
    a, b = words(row["name1"]), words(row["name2"])
    lo, hi = (d0 + pd.Timedelta(days=WINDOW[0])).timestamp(), (d0 + pd.Timedelta(days=WINDOW[1])).timestamp()
    main_from = (d0 - pd.Timedelta(days=MAIN_DRAW_LEAD)).timestamp()
    scored = []
    for e in cands:
        ts = e.get("startTimestamp") or 0
        if not lo <= ts <= hi:
            continue
        score, side = pair_score(a, b, e["_hw"], e["_aw"])
        if score:
            scored.append(((score, ts >= main_from and not is_qualifying(e)), side, e))
    out = {"candidates": len(scored)}
    if not scored:
        return {**out, "note": "no event names both players"}
    scored.sort(key=lambda t: t[0], reverse=True)
    top = [t for t in scored if t[0] == scored[0][0]]
    if len(top) > 1:
        return {**out, "note": "tie: " + ";".join(str(t[2]["id"]) for t in top)}
    (score, main), side, e = top[0]
    ts = e.get("startTimestamp")
    winner = e.get("winnerCode")
    return {**out, "event_id": e["id"], "link_score": score, "name1_side": "home" if side == 1 else "away",
            "ss_home": S._dig(e, ("homeTeam", "name")), "ss_away": S._dig(e, ("awayTeam", "name")),
            "ss_round": S._dig(e, ("roundInfo", "name")), "ss_qualifying": not main,
            "ss_start": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else None,
            "ss_status": S._dig(e, ("status", "description")), "ss_winner_code": winner,
            "winner_agrees": None if winner not in (1, 2) else winner == side,
            "note": None}


def main() -> int:
    gap = pd.read_csv(OUT / "gap_matches.csv", parse_dates=["d"])
    by_edition = candidates_by_edition(T.load_season_events())
    rows = []
    for edition, g in gap.groupby("edition", sort=True):
        cands = by_edition.get(edition, [])
        d0 = g["d"].min()
        for _, row in g.iterrows():
            base = row[["map_uid", "edition", "tour", "tname", "year", "d", "name1", "name2"]].to_dict()
            base["d"] = base["d"].date()
            if not cands:
                rows.append({**base, "candidates": 0, "note": "season not listed"})
                continue
            rows.append({**base, **link_one(row, cands, d0)})
    links = pd.DataFrame(rows)
    cols = ["map_uid", "edition", "tour", "tname", "year", "d", "name1", "name2", "event_id", "link_score",
            "name1_side", "ss_home", "ss_away", "ss_round", "ss_qualifying", "ss_start", "ss_status",
            "ss_winner_code", "winner_agrees", "candidates", "note"]
    links = links.reindex(columns=cols)
    links["event_id"] = links["event_id"].astype("Int64")
    links.to_csv(OUT / "sofascore_links.csv", index=False)
    linked = links["event_id"].notna()
    print(f"{int(linked.sum())} of {len(links)} gap matches linked; "
          f"{int(links['event_id'].dropna().duplicated().sum())} event ids used twice")
    print(links.assign(linked=linked).groupby("edition")["linked"].agg(["sum", "size"]).to_string())
    print(links["note"].value_counts(dropna=False).to_string())
    print("winner side agrees:", links["winner_agrees"].value_counts(dropna=False).to_dict())
    print("qualifying events linked:", int(links["ss_qualifying"].fillna(False).astype(bool).sum()))
    order = fetch_order(links)
    order.to_csv(OUT / "sofascore_fetch_order.csv", index=False)
    print("fetch order:", order["priority"].value_counts().sort_index().to_dict())
    return 0


def fetch_order(links: pd.DataFrame) -> pd.DataFrame:
    """The linked events in the order to fetch them, so that a run SofaScore stops part-way has done the most
    useful part: first the gap matches no complete point record fills (priority 1), then those the Hawk-Eye copy
    already fills (priority 2; SofaScore adds its own record and the box score). Newest first within each."""
    linked = links[links["event_id"].notna()].copy()
    hawkeye = OUT / "hawkeye_gap.csv"
    complete = set()
    if hawkeye.exists():
        h = pd.read_csv(hawkeye)
        complete = set(h.loc[h["fills_point"].astype(str).str.lower().eq("true"), "map_uid"])
    linked["priority"] = [2 if uid in complete else 1 for uid in linked["map_uid"]]
    linked["reason"] = linked["priority"].map({1: "no complete point record held",
                                               2: "complete Hawk-Eye record held; SofaScore adds its record and box score"})
    linked = linked.sort_values(["priority", "ss_start"], ascending=[True, False])
    return linked[["event_id", "priority", "reason", "map_uid", "edition", "name1", "name2", "ss_start"]]


if __name__ == "__main__":
    sys.exit(main())
