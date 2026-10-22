"""Flashscore's point-by-point records of the ITF matches SofaScore lacks: January 2025 to February 2026 (work
package P13 of docs/studies/gap_downloads/collection-plan.md).

SofaScore holds no ITF point records from January 2025 to February 2026 (work package P7). Flashscore's live site
serves them for many of those matches, one feed request per match, and the Flashscore copy on disk (the Hugging Face
handoff, data/raw/public_dump/atp_pipeline_handoff/flashscore_full/) holds their match ids, so nothing needs listing
(docs/research/gap-sources/itf_2025_points.md).

1. **Extract** (--extract; offline, once): every ITF singles record of the handoff copy (tournament names "M15 ...",
   "W35 ...") dated in or near the window, one row per Flashscore match id, the richest copy kept: date, tournament,
   players, set scores, start and end times, duration. Staged as data/dump/points/flashscore_points/handoff_itf.parquet.
2. **Targets:** the gap's frozen list (P7's, sofascore_<gap>_matches.csv.gz in data/studies/gap_downloads/) whose map
   date falls in the window (--from, --to).
3. **Link:** each target to the handoff record of its tour dated from 3 days before to 8 days after the target's date
   (the edition's week), whose two players' first surname words are each a word of a different target player's name.
   On several, the one whose grade ("M15", "W35") is in the target's tournament name; otherwise the target is left
   unlinked (a tie).
4. **Fetch:** the point feed of every linked record: global.flashscore.ninja/2/x/feed/df_mh_1_<id>, with the feed
   signature the site's own pages send (x-fsign). Records with a match duration in the handoff copy go first, newest
   first, then the rest (in the trial, none without a duration had a point record). An empty answer means no record:
   it is recorded once, like a 404, and not asked again.
5. **Parse:** sets, games (server, winner, broken or not), and every point: its winner and the score after it, with
   Flashscore's break-, set- and match-point marks; tiebreaks point by point. A record is "complete" when every set has
   as many games as the record's own set score (the handoff's), as in P6 and P7.

Feed codes (read from the data, 13 Oct 2026): HA a set's label; HB a section label ("Tiebreak - Set 2"); HC and HE the
home and away games after a game (in a tiebreak, the points after a point); HG the server (1 home, 2 away); HH the side
that lost its serve; HK the game's (or tiebreak point's) winner; HL the score after each point of a game except the
last, which its winner takes, with |B1| break point, |B2| set point, |B3| match point; HD and HF the tiebreak's points on
the set's closing record; HM a tiebreak point's mark (2 set point, 3 match point; then the side). A1 ends the feed.

Raw (gitignored): data/raw/point_sources/flashscore_points/feed/<id>.txt.gz with _receipts.jsonl, logs in _logs/.
Staged (data/dump/points/flashscore_points/, all strings): handoff_itf.parquet; matches.parquet (one row per feed
asked); points.parquet (one row per point). Evidence (data/studies/gap_downloads/): flashscore_<gap>_matches.csv.gz
(one row per target: its link, what was fetched, the record's shape and verdict), flashscore_<gap>_summary.json,
runs.jsonl. Flashscore's terms forbid automated extraction; collected under the owner's decision of 8 Oct 2026
(docs/decisions/2026-10-08-scraping-approved.md).

Usage:
    ./python.sh -m src.ingest.point_sources.flashscore_points --extract                     # once, offline
    ./python.sh -m src.ingest.point_sources.flashscore_points --trial 200 --max-requests 250 # a seeded trial
    ./python.sh -m src.ingest.point_sources.flashscore_points --max-requests 30000          # a run (resumes)
    ./python.sh -m src.ingest.point_sources.flashscore_points --stage-only                  # no HTTP
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

SOURCE = "flashscore_points"
HANDOFF = P.PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
HANDOFF_FOLDERS = ("flashscore_full", "flashscore_gql_stats")   # the folders whose records carry a match id
STUDY = P.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
DEFAULT_GAP = "itf_points_2025_2026"
WINDOW = ("2024-12-29", "2026-02-28")    # the map dates of P7's hole: editions of 30 Dec 2024 to 23 Feb 2026
EXTRACT_SPAN = ("20241220", "20260315")  # handoff dates read: the window, widened by the link's reach
FEED = "https://global.flashscore.ninja/2/x/feed/df_mh_1_{id}"
FSIGN = "SW9D1eZo"   # the feed signature in the site's own page settings (feed_sign), 13 Oct 2026
HEADERS = {"Accept": "*/*", "Referer": "https://www.flashscore.com/", "Origin": "https://www.flashscore.com"}
LINK_DAYS = (-3, 8)
ITF_NAME = re.compile(r"^([MW])(\d{2,3})\b")
PREFILTER = re.compile(r'"(?:tournament_name|tournament)"\s*:\s*"[MW]\d{2,3}\b')
SEP_R, SEP_F, SEP_KV = "~", "¬", "÷"   # Flashscore's record, field and key-value separators
RANK = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4}
MARKS = {"B1": "break_point", "B2": "set_point", "B3": "match_point"}
COMPLETE = ("complete",)

HANDOFF_COLUMNS = ["fs_id", "fs_date", "tour", "grade", "fs_tournament", "fs_home", "fs_away", "fs_score",
                   "fs_status", "fs_start_ts", "fs_end_ts", "fs_duration", "handoff_file"]
TARGET_COLUMNS = ["gap", "edition", "uid", "tour", "level", "draw", "year", "d", "tname", "name1", "name2",
                  "creator", "best", "sources"]
LINK_COLUMNS = ["fs_id", "candidates", "link_note", "fs_date", "fs_tournament", "fs_home", "fs_away", "fs_score",
                "fs_duration"]
FETCH_COLUMNS = ["feed_status", "feed_bytes", "fb_sets", "fb_games", "fb_points", "fb_score", "fb_verdict"]
MATCH_COLUMNS = ["fs_id", "fs_date", "tour", "grade", "fs_tournament", "fs_home", "fs_away", "fs_score",
                 "fs_duration", "feed_status", "feed_retrieved_at", "feed_sha256", "fb_sets", "fb_games",
                 "fb_points", "fb_score", "fb_verdict", "irregular_games"]
POINT_COLUMNS = ["fs_id", "set", "game", "tiebreak", "point", "server", "winner", "score_after", "break_point",
                 "set_point", "match_point", "game_server_broken"]


# --------------------------------------------------------------------------------------
# names and linking (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def fold(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


def name_words(name) -> set:
    """A map name's words of two letters or more, accents dropped."""
    return {w for w in re.split(r"[^a-z]+", fold(name)) if len(w) > 1}


def surname_text(fs_name) -> str:
    """A Flashscore name without its initials: "Cunha Winheski de Lima V." -> "Cunha Winheski de Lima"."""
    parts = str(fs_name or "").strip().split(" ")
    while parts and re.fullmatch(r"(?:[A-Z][a-z]?\.-?)+", parts[-1]):
        parts.pop()
    return " ".join(parts)


def surname_words(fs_name) -> list[str]:
    """A Flashscore name's surname words, its initials dropped: "Cunha Winheski de Lima V." -> cunha, winheski, de,
    lima; "Lee Y.-H." -> lee."""
    return [w for w in re.split(r"[^a-z]+", fold(surname_text(fs_name))) if len(w) > 1]


def pair_matches(w1: set, w2: set, home: list, away: list) -> bool:
    """Whether each Flashscore player's first surname word is a word of a different target player's name."""
    if not home or not away:
        return False
    return (home[0] in w1 and away[0] in w2) or (home[0] in w2 and away[0] in w1)


def link_targets(targets: pd.DataFrame, handoff: pd.DataFrame) -> pd.DataFrame:
    """Each target's handoff record (LINK_COLUMNS), by the rule of the module docstring."""
    by_day = defaultdict(list)
    for r in handoff.itertuples(index=False):
        by_day[(r.tour, r.fs_date)].append((r.fs_id, surname_words(r.fs_home), surname_words(r.fs_away), r.grade, r))
    rows = []
    for t in targets.itertuples(index=False):
        w1, w2 = name_words(t.name1), name_words(t.name2)
        d = pd.Timestamp(t.d).date()
        cands = {}
        for k in range(LINK_DAYS[0], LINK_DAYS[1] + 1):
            day = (d + dt.timedelta(days=k)).strftime("%Y%m%d")
            for fs_id, home, away, grade, rec in by_day.get((t.tour, day), []):
                if pair_matches(w1, w2, home, away):
                    cands[fs_id] = (grade, rec)
        chosen, note = None, None
        if len(cands) == 1:
            chosen = next(iter(cands))
        elif len(cands) > 1:
            same = [i for i, (grade, _) in cands.items() if grade and grade in str(t.tname)]
            if len(same) == 1:
                chosen = same[0]
            else:
                note = f"tie: {len(cands)} records name the pair"
        else:
            note = "no record names the pair"
        row = {"fs_id": chosen, "candidates": len(cands), "link_note": note}
        if chosen:
            rec = cands[chosen][1]
            row.update(fs_date=rec.fs_date, fs_tournament=rec.fs_tournament, fs_home=rec.fs_home, fs_away=rec.fs_away,
                       fs_score=rec.fs_score, fs_duration=rec.fs_duration)
        rows.append(row)
    return pd.DataFrame(rows, columns=LINK_COLUMNS, index=targets.index)


# --------------------------------------------------------------------------------------
# the point feed (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def records(text: str) -> list[dict]:
    """A feed's records, each as {code: value}."""
    out = []
    for rec in str(text or "").split(SEP_R):
        fields = {}
        for kv in rec.split(SEP_F):
            if SEP_KV in kv:
                k, v = kv.split(SEP_KV, 1)
                fields[k.strip()] = v
        if fields:
            out.append(fields)
    return out


def split_state(token: str) -> tuple[str, set]:
    """'40:A |B1| |B2|' -> ('40:A', {'B1', 'B2'})."""
    marks = set(re.findall(r"\|([A-Z]\d)\|", token))
    return token.split("|")[0].strip(), marks


def point_winner(prev: str, cur: str) -> int | None:
    """The side (1 home, 2 away) that won the point taking a game's score from ``prev`` to ``cur``; None when the step
    is not a legal one."""
    try:
        (ph, pa), (ch, ca) = ([RANK[x] for x in s.split(":")] for s in (prev, cur))
    except (KeyError, ValueError):
        return None
    if (ch, ca) == (ph + 1, pa) or (ph, pa, ch, ca) == (3, 4, 3, 3):     # home scores, or wipes away's advantage
        return 1
    if (ch, ca) == (ph, pa + 1) or (ph, pa, ch, ca) == (4, 3, 3, 3):
        return 2
    return None


def parse_feed(text: str) -> dict:
    """Sets, games and points of a feed; ``irregular`` counts games whose score steps are not all legal."""
    sets, cur_set, game, in_tiebreak, irregular = [], None, None, False, 0
    for f in records(text):
        if "HA" in f:                                          # a set begins
            cur_set = {"set": len(sets) + 1, "games": [], "score": None}
            sets.append(cur_set)
            in_tiebreak = False
            continue
        if cur_set is None:
            continue
        if "HB" in f and "HC" not in f:                        # "Tiebreak - Set N": its points follow
            in_tiebreak = "tiebreak" in f["HB"].lower()
            continue
        if "HC" not in f or "HE" not in f:
            continue
        if in_tiebreak and game is not None and game["tiebreak"]:
            winner = int(f.get("HK") or 0) or None
            game["points"].append({"winner": winner, "server": int(f.get("HG") or 0) or None,
                                   "score_after": f"{f['HC']}:{f['HE']}", "marks": set(),
                                   "hm": f.get("HM")})
            continue
        if "HD" in f or "HF" in f:                             # the set's closing record: a tiebreak game
            game = {"game": len(cur_set["games"]) + 1, "tiebreak": True, "server": None,
                    "winner": int(f.get("HK") or 0) or None, "broken": None, "points": [],
                    "games_after": (int(f["HC"]), int(f["HE"])), "tiebreak_points": (f.get("HD"), f.get("HF"))}
            cur_set["games"].append(game)
            cur_set["score"] = game["games_after"]
            continue
        server, winner = int(f.get("HG") or 0) or None, int(f.get("HK") or 0) or None
        states = [split_state(s) for s in (f.get("HL") or "").split(",") if s.strip()]
        points, prev, legal = [], "0:0", True
        for score, marks in states:
            w = point_winner(prev, score)
            legal &= w is not None
            points.append({"winner": w, "server": server, "score_after": score, "marks": marks, "hm": None})
            prev = score
        points.append({"winner": winner, "server": server, "score_after": "game", "marks": set(), "hm": None})
        irregular += not legal
        game = {"game": len(cur_set["games"]) + 1, "tiebreak": False, "server": server, "winner": winner,
                "broken": bool(f.get("HH")), "points": points, "games_after": (int(f["HC"]), int(f["HE"]))}
        cur_set["games"].append(game)
        cur_set["score"] = game["games_after"]
    n_points = sum(len(g["points"]) for s in sets for g in s["games"])
    return {"sets": sets, "n_sets": len(sets), "n_games": sum(len(s["games"]) for s in sets), "n_points": n_points,
            "score": " ".join(f"{s['score'][0]}-{s['score'][1]}" for s in sets if s["score"]), "irregular": irregular}


def score_sets(score) -> list[tuple[int, int]]:
    """'6-2 7-6' -> [(6, 2), (7, 6)] (home first, as the handoff's set scores)."""
    out = []
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def verdict(parsed: dict, fs_score) -> str:
    """*complete*: every set of the record's score has its games, and no more; *short*: games or sets missing; *no
    score to compare*; else *other*."""
    want = score_sets(fs_score)
    if not parsed["sets"]:
        return "empty"
    if not want:
        return "no score to compare"
    got = [len(s["games"]) for s in parsed["sets"]]
    final = [s["score"] for s in parsed["sets"]]
    if len(got) == len(want) and all(g == h + a for g, (h, a) in zip(got, want)) and final == want:
        return "complete"
    if len(got) <= len(want) and all(g <= h + a for g, (h, a) in zip(got, want)):
        return "short"
    return "other"


def point_rows(fs_id: str, parsed: dict) -> list[dict]:
    rows = []
    for s in parsed["sets"]:
        for g in s["games"]:
            for i, p in enumerate(g["points"], 1):
                hm = str(p.get("hm") or "")
                rows.append({"fs_id": fs_id, "set": s["set"], "game": g["game"], "tiebreak": g["tiebreak"],
                             "point": i, "server": p["server"], "winner": p["winner"], "score_after": p["score_after"],
                             "break_point": "B1" in p["marks"],
                             "set_point": "B2" in p["marks"] or hm.startswith("2,"),
                             "match_point": "B3" in p["marks"] or hm.startswith("3,"),
                             "game_server_broken": g["broken"]})
    return rows


# --------------------------------------------------------------------------------------
# the handoff copy: extract (offline)
# --------------------------------------------------------------------------------------
def handoff_files() -> list[Path]:
    files = []
    for folder in HANDOFF_FOLDERS:
        root = HANDOFF / folder
        if root.exists():
            files += [p for p in root.iterdir() if p.name.endswith((".jsonl", ".jsonl.gz"))]
    return sorted(files, key=lambda p: -p.stat().st_size)


def _below_normal() -> None:
    try:
        import psutil

        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def handoff_row(r: dict, file: str) -> dict | None:
    """A handoff record as an extract row, or None when it is not an ITF singles record dated in EXTRACT_SPAN."""
    name = r.get("tournament_name") or r.get("tournament") or ""
    m = ITF_NAME.match(name)
    date = str(r.get("match_date") or "")
    if not m or not (EXTRACT_SPAN[0] <= date <= EXTRACT_SPAN[1]):
        return None
    home, away = r.get("home_player") or "", r.get("away_player") or ""
    if "/" in home or "/" in away:                             # doubles
        return None
    return {"fs_id": r.get("match_id") or r.get("fs_mid") or "", "fs_date": date, "tour": m.group(1),
            "grade": m.group(0), "fs_tournament": name, "fs_home": home, "fs_away": away,
            "fs_score": r.get("set_scores") or "", "fs_status": str(r.get("status") or ""),
            "fs_start_ts": str(r.get("match_start_ts") or ""), "fs_end_ts": str(r.get("match_end_ts") or ""),
            "fs_duration": r.get("match_duration") or "", "handoff_file": file}


def scan_file(path_text: str) -> list[dict]:
    """The extract rows of one handoff file (lines pre-filtered by tournament name before parsing)."""
    _below_normal()
    path = Path(path_text)
    rel = f"{path.parent.name}/{path.name}"
    opener = gzip.open if path.suffix == ".gz" else open
    out = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not PREFILTER.search(line):
                continue
            try:
                row = handoff_row(json.loads(line), rel)
            except json.JSONDecodeError:
                continue
            if row and row["fs_id"]:
                out.append(row)
    return out


def richer(a: dict, b: dict) -> dict:
    """Of two copies of one match, the one with more filled fields (a duration first)."""
    key = lambda r: (bool(r["fs_duration"]), bool(r["fs_score"]), sum(bool(v) for v in r.values()))  # noqa: E731
    return b if key(b) > key(a) else a


def extract(workers: int = 4) -> dict:
    files = handoff_files()
    if not files:
        raise SystemExit(f"no handoff files under {P.rel(HANDOFF)}")
    best: dict[str, dict] = {}
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, rows in enumerate(pool.map(scan_file, [str(p) for p in files]), 1):
            for row in rows:
                best[row["fs_id"]] = richer(best[row["fs_id"]], row) if row["fs_id"] in best else row
            if i % 10 == 0 or i == len(files):
                P.log(f"[{SOURCE}] extract: {i}/{len(files)} files; {len(best):,} ITF records so far")
    rows = sorted(best.values(), key=lambda r: (r["fs_date"], r["fs_tournament"], r["fs_id"]))
    dest = P.dump_path(SOURCE, "handoff_itf.parquet")
    stats = P.stage_table(SOURCE, dest, HANDOFF_COLUMNS, ([r.get(c) for c in HANDOFF_COLUMNS] for r in rows),
                          source_file=P.rel(HANDOFF), retrieved_at=P.utc_now_iso())
    P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows in {time.time() - started:.0f} s")
    return {"files": len(files), "records": stats["rows"], "dest": stats["dest"]}


def load_handoff() -> pd.DataFrame:
    path = P.dump_path(SOURCE, "handoff_itf.parquet")
    if not path.exists():
        raise SystemExit(f"{P.rel(path)} is missing: run --extract first")
    return pd.read_parquet(path, columns=HANDOFF_COLUMNS).fillna("")


def load_info() -> pd.DataFrame:
    """What staging says of each feed: every handoff extract staged here (handoff_*.parquet), one row per match id, the
    ITF extract first. Besides this module's ITF extract, flashscore_p6.py stages handoff_p6.parquet: the copy's records
    of work package P6's men's ATP and Challenger targets (its grade is Flashscore's category). Linking reads only the
    ITF extract (load_handoff)."""
    paths = sorted(P.dump_path(SOURCE).glob("handoff_*.parquet"), key=lambda p: (p.name != "handoff_itf.parquet", p.name))
    frames = [pd.read_parquet(p, columns=HANDOFF_COLUMNS).fillna("") for p in paths]
    if not frames:
        return pd.DataFrame(columns=HANDOFF_COLUMNS)
    return pd.concat(frames, ignore_index=True).drop_duplicates("fs_id").reset_index(drop=True)


# --------------------------------------------------------------------------------------
# targets, fetching, staging
# --------------------------------------------------------------------------------------
def table_path(gap: str, kind: str) -> Path:
    return STUDY / f"flashscore_{gap}_{kind}.csv.gz"


def load_targets(gap: str, window=WINDOW) -> pd.DataFrame:
    """The gap's frozen targets (P7's list) whose map date falls in the window."""
    path = STUDY / f"sofascore_{gap}_matches.csv.gz"
    if not path.exists():
        path = STUDY / f"sofascore_{gap}_matches.csv"
    t = pd.read_csv(path, usecols=TARGET_COLUMNS, dtype=str, keep_default_na=False)
    d = pd.to_datetime(t["d"])
    return t[(d >= pd.Timestamp(window[0])) & (d <= pd.Timestamp(window[1]))].reset_index(drop=True)


def trial_sample(linked: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """About ``n`` linked targets, spread evenly over months and tours (seeded)."""
    month = linked["fs_date"].str[:6]
    cells = linked.groupby([month, linked["tour"]], sort=True)
    per = max(1, round(n / max(cells.ngroups, 1)))
    rng = random.Random(seed)
    picks = []
    for _, g in cells:
        idx = sorted(g.index)
        picks += rng.sample(idx, min(per, len(idx)))
    return linked.loc[sorted(picks)]


def make_client(args):
    return P.Client("chrome", min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests,
                    headers={**HEADERS, "x-fsign": args.fsign})


def feed_validator(body: bytes):
    head = body[:200].lstrip().lower()
    return "response is an HTML page (a block?)" if head.startswith((b"<!doctype", b"<html")) else None


def empty_feed(response) -> str | None:
    return "empty feed (no point record)" if response.status_code == 200 and not response.content.strip() else None


def feed_path(fs_id: str) -> Path:
    return P.raw_path(SOURCE, "feed", f"{fs_id}.txt.gz")


def fetch_feeds(client, receipts, ids: list[str], log_every: int = 100) -> Counter:
    outcomes = Counter()
    for n, fs_id in enumerate(ids, 1):
        before = receipts.get(f"feed/{fs_id}")
        r = P.fetch(client, FEED.format(id=fs_id), feed_path(fs_id), receipts, name=f"feed/{fs_id}",
                    validator=feed_validator, compress=True, absent=empty_feed)
        status = "absent" if r.get("absent") else r.get("error") or r.get("status")
        outcomes[f"{status}" + (":cached" if before and receipts.get(f"feed/{fs_id}") is before else "")] += 1
        if n % log_every == 0 or n == len(ids):
            P.log(f"[{SOURCE}] feeds: {n}/{len(ids)}; requests={client.requests}; " +
                  ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    return outcomes


def feed_status(receipts, fs_id: str):
    r = receipts.get(f"feed/{fs_id}") or {}
    if not r:
        return "not fetched"
    if r.get("absent"):
        return "absent"
    return r.get("error") or r.get("status")


def read_feed(receipts, fs_id: str) -> str | None:
    path = feed_path(fs_id)
    if feed_status(receipts, fs_id) == 200 and path.exists():
        return P.read_bytes(path).decode("utf-8", errors="replace")
    return None


def results(receipts, frame: pd.DataFrame) -> pd.DataFrame:
    """Each linked target's fetch outcome and record shape (FETCH_COLUMNS)."""
    out = []
    for r in frame.itertuples(index=False):
        row = {c: None for c in FETCH_COLUMNS}
        if r.fs_id:
            row["feed_status"] = feed_status(receipts, r.fs_id)
            rec = receipts.get(f"feed/{r.fs_id}") or {}
            row["feed_bytes"] = rec.get("bytes")
            text = read_feed(receipts, r.fs_id)
            if text is not None:
                parsed = parse_feed(text)
                row.update(fb_sets=parsed["n_sets"], fb_games=parsed["n_games"], fb_points=parsed["n_points"],
                           fb_score=parsed["score"], fb_verdict=verdict(parsed, r.fs_score))
        out.append(row)
    return pd.DataFrame(out, columns=FETCH_COLUMNS, index=frame.index)


def stage(receipts, handoff: pd.DataFrame) -> dict:
    """Rebuild matches.parquet and points.parquet from every feed on disk, streamed."""
    rec = {k[len("feed/"):]: v for k, v in receipts.all().items() if k.startswith("feed/")}
    info = handoff.set_index("fs_id")
    ids = sorted(rec, key=lambda i: (str(info["fs_date"].get(i, "")) if i in info.index else "", i), reverse=True)
    shapes = {}

    def point_iter():
        for fs_id in ids:
            text = read_feed(receipts, fs_id)
            if text is None:
                continue
            parsed = parse_feed(text)
            h = info.loc[fs_id] if fs_id in info.index else None
            shapes[fs_id] = (parsed, verdict(parsed, h["fs_score"] if h is not None else ""))
            r = rec[fs_id]
            for p in point_rows(fs_id, parsed):
                yield {**p, "source_file": P.rel(feed_path(fs_id)), "source_sha256": r.get("sha256"),
                       "retrieved_at": r.get("retrieved_at")}

    def match_iter():
        for fs_id in ids:
            r, h = rec[fs_id], (info.loc[fs_id] if fs_id in info.index else None)
            row = {"fs_id": fs_id, "feed_status": feed_status(receipts, fs_id), "feed_retrieved_at": r.get("retrieved_at"),
                   "feed_sha256": r.get("sha256")}
            if h is not None:
                row.update({c: h[c] for c in ("fs_date", "tour", "grade", "fs_tournament", "fs_home", "fs_away",
                                              "fs_score", "fs_duration")})
            if fs_id in shapes:
                parsed, v = shapes[fs_id]
                row.update(fb_sets=parsed["n_sets"], fb_games=parsed["n_games"], fb_points=parsed["n_points"],
                           fb_score=parsed["score"], fb_verdict=v, irregular_games=parsed["irregular"])
            yield row

    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("points", POINT_COLUMNS + ["source_file", "source_sha256", "retrieved_at"], point_iter()),
                                ("matches", MATCH_COLUMNS, match_iter())):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        stats = P.stage_table(SOURCE, dest, columns, ([P.s(r.get(c)) for c in columns] for r in rows),
                              source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now)
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return out


def tally(frame: pd.DataFrame) -> dict:
    def cell(g: pd.DataFrame) -> dict:
        status = g["feed_status"].astype(str)
        return {"targets": int(len(g)), "linked": int(g["fs_id"].astype(bool).sum()),
                "points_any": int((pd.to_numeric(g["fb_points"], errors="coerce").fillna(0) > 0).sum()),
                "points_complete": int(g["fb_verdict"].isin(COMPLETE).sum()), "absent": int(status.eq("absent").sum()),
                "not_fetched": int((g["fs_id"].astype(bool) & status.eq("not fetched")).sum())}

    month = pd.to_datetime(frame["d"]).dt.strftime("%Y-%m")
    out = {"all": cell(frame), "by_month_tour": {f"{m}|{t}": cell(g) for (m, t), g in frame.groupby([month, "tour"])},
           "verdicts": {str(k): int(v) for k, v in frame["fb_verdict"].value_counts(dropna=False).items()},
           "link_notes": {str(k): int(v) for k, v in frame["link_note"].value_counts().items()}}
    asked = frame[frame["feed_status"].astype(str).isin(["200", "absent"])]
    has_dur = asked["fs_duration"].astype(str).str.len() > 0
    has_pts = asked["feed_status"].astype(str).eq("200")
    out["duration_proxy"] = {f"duration={'yes' if d else 'no'}|record={'yes' if p else 'no'}": int(((has_dur == d) & (has_pts == p)).sum())
                             for d in (True, False) for p in (True, False)}
    return out


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    if args.extract:
        return extract(args.workers)
    STUDY.mkdir(parents=True, exist_ok=True)
    targets = load_targets(args.gap, (args.date_from, args.date_to))
    handoff = load_handoff()
    links = link_targets(targets, handoff)
    frame = pd.concat([targets, links], axis=1)
    frame["fs_id"] = frame["fs_id"].fillna("")
    P.log(f"[{SOURCE}] gap {args.gap}, {args.date_from} to {args.date_to}: {len(frame):,} targets; "
          f"{frame['fs_id'].astype(bool).sum():,} linked to a Flashscore record")
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "gap": args.gap, "window": [args.date_from, args.date_to], "started_at": P.utc_now_iso(),
               "args": {k: v for k, v in vars(args).items()}}
    linked = frame[frame["fs_id"].astype(bool)]
    if args.trial:
        linked = trial_sample(linked, args.trial, args.seed)
        summary["trial_ids"] = linked["fs_id"].tolist()
    # those with a duration in the handoff copy first: in the trial of 14 Oct 2026 none of the 52 without one had a
    # record, and 131 of the 137 with one had; the rest follow, so nothing is skipped
    order = linked.assign(_dur=linked["fs_duration"].astype(str).str.len().gt(0))
    order = order.sort_values(["_dur", "fs_date"], ascending=[False, False], kind="stable")
    ids = list(dict.fromkeys(order["fs_id"]))
    outcomes = Counter()
    client = None
    if not args.stage_only:
        client = make_client(args)
        P.log(f"[{SOURCE}] {len(ids):,} feeds to ask (cached ones are not asked again); budget {args.max_requests}; "
              f"interval {args.min_interval}s + up to {args.jitter}s")
        try:
            outcomes = fetch_feeds(client, receipts, ids)
        except (P.Blocked, P.BudgetExhausted) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    frame = pd.concat([frame, results(receipts, frame)], axis=1)
    frame.sort_values(["d", "edition", "uid"]).to_csv(table_path(args.gap, "matches"), index=False)
    if not args.no_stage:
        summary["staged"] = stage(receipts, load_info())
    if args.trial:
        summary["trial"] = tally(frame[frame["fs_id"].isin(set(summary["trial_ids"]))])
    summary.update(tally(frame))
    summary["matches_selected"] = int(frame["feed_status"].astype(str).eq("200").sum())
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary(f"flashscore_{args.gap}_summary.json", summary, root=STUDY)
    P.log(f"[{SOURCE}] {json.dumps(summary.get('trial', summary)['all'])}")
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--extract", action="store_true", help="read the handoff copy's ITF records (offline, once)")
    parser.add_argument("--workers", type=int, default=4, help="processes for --extract")
    parser.add_argument("--gap", default=DEFAULT_GAP)
    parser.add_argument("--from", dest="date_from", default=WINDOW[0], help="first map date of the window")
    parser.add_argument("--to", dest="date_to", default=WINDOW[1], help="last map date of the window")
    parser.add_argument("--trial", type=int, help="only about N linked targets, spread over months and tours")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-requests", type=int, default=10_000)
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--fsign", default=FSIGN, help="the x-fsign header the site's pages send")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the evidence and tables")
    parser.add_argument("--no-stage", action="store_true", help="skip the Parquet rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
