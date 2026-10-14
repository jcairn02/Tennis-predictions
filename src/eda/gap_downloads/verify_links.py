"""Check the by-edition SofaScore links against the official result: does each linked event have the target
match's winner and set scores?

For every target of a gap (the frozen list, data/studies/gap_downloads/sofascore_<gap>_matches.csv), the links
are rebuilt offline from the adapter's cached listings with the adapter's own functions (no HTTP). Each linked
SofaScore event is then compared with the result file the map took the target from: Tennis My Life's or
Sackmann's row for the same match, found by the tournament, date, both names and the draw exactly as the map
reads them (src/eda/data_map/measure.py: load_tml, load_sackmann). Where both files hold the match, Tennis My
Life's row is used. The comparison covers the winner and the games of every set (tiebreak points are left aside).

Verdicts:
    agrees                     same winner, same games in every set (at a retirement, all but the unfinished set,
                               and without the unstarted 0-0 set SofaScore adds)
    winner agrees, SofaScore lists no score   early retirements
    winner agrees, score differs
    SofaScore lists no winner  winner code 3 (some retirements and abandoned matches) or none (cancelled, suspended)
    winner differs             a wrong link, or a result recorded differently
    no official row            the target came from a file this check does not read (API-Tennis, the WTA's lists
                               or website, a Slam's draws ...); the ``creator`` column names it
    not linked                 the adapter found no event for it

Writes data/studies/gap_downloads/sofascore_<gap>_link_check.csv (one row per target, with the ``official`` file
read; gzipped, .csv.gz, for the big ITF gaps, sofascore_editions.GZIPPED) and sofascore_<gap>_link_check.json (counts
overall, by year and level, and by the file read).

Usage: ./python.sh src/eda/gap_downloads/verify_links.py [--gap atp_points_2025]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M                          # noqa: E402
from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import sofascore_editions as E       # noqa: E402

RESULTS = PROJECT_ROOT / "data" / "dump" / "matches"
# the result files the map builds its matches from (measure.load_tml, load_sackmann), Tennis My Life's first
RESULT_FILES = [("tml", "tennis_my_life/atp_main/*.parquet"), ("tml", "tennis_my_life/atp_qualifying/*.parquet"),
                ("tml", "tennis_my_life/atp_challenger/*.parquet"), ("tml", "tennis_my_life/wta_main/*.parquet"),
                ("tml", "tennis_my_life/ongoing/*.parquet"),
                ("sackmann", "sackmann_archive/atp/atp_matches_20[0-9][0-9].parquet"),
                ("sackmann", "sackmann_archive/atp/atp_matches_qual_chall_*.parquet"),
                ("sackmann", "sackmann_archive/atp/atp_matches_futures_*.parquet"),
                ("sackmann", "sackmann_archive/wta/wta_matches_20[0-9][0-9].parquet"),
                ("sackmann", "sackmann_archive/wta/wta_matches_qual_itf_*.parquet")]
KEY = ["tourney_name", "d", "winner_name", "loser_name", "draw"]
SET = re.compile(r"^(\d+)-(\d+)")


def tml_sets(score) -> list[tuple[int, int]]:
    """'6-7(2) 7-6(3) 7-5 RET' -> [(6, 7), (7, 6), (7, 5)]: games per set, winner first."""
    return [(int(m.group(1)), int(m.group(2))) for tok in str(score or "").split() if (m := SET.match(tok))]


def ss_sets(event: dict) -> list[tuple[int, int]]:
    """Games per set of a SofaScore event, winner first."""
    hs, as_ = event.get("homeScore") or {}, event.get("awayScore") or {}
    sets = []
    for n in range(1, 6):
        h, a = hs.get(f"period{n}"), as_.get(f"period{n}")
        if h is None or a is None:
            break
        sets.append((int(h), int(a)) if event.get("winnerCode") != 2 else (int(a), int(h)))
    return sets


def compare(event: dict, winner: str, score) -> str:
    """The verdict for one linked event against the official winner and score."""
    side = {1: "homeTeam", 2: "awayTeam"}.get(event.get("winnerCode"))
    if side is None:   # winner code 3 (some retirements and abandoned matches) or none (cancelled, suspended)
        return "SofaScore lists no winner"
    if not (E.team_words(event.get(side) or {}) & E.words(winner)):
        return "winner differs"
    ours, theirs = ss_sets(event), tml_sets(score)
    if not ours:
        return "winner agrees, SofaScore lists no score"
    retired = any(end in str(score or "").upper() for end in ("RET", "DEF"))   # a retirement or a default
    while retired and len(ours) > len(theirs) and ours[-1] == (0, 0):   # SofaScore adds the set never started
        ours = ours[:-1]
    if ours == theirs or (retired and len(ours) == len(theirs) and ours[:-1] == theirs[:-1]):
        return "agrees"
    return "winner agrees, score differs"


def official_rows(tnames=None) -> pd.DataFrame:
    """Every result file's rows from 2018 on (only those of the tournaments ``tnames``, when given), keyed as the
    map keys them plus the draw: a pair can meet in the qualifying and again in the main draw of one event
    (Basel 2025). A row of Tennis My Life's qualifying folder is qualifying whatever its round says, as on the map.
    Where both files hold a match, Tennis My Life's row comes first and is kept."""
    cols = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]
    frames = []
    for source, pattern in RESULT_FILES:
        for path in sorted(RESULTS.glob(pattern)):
            year = M._year_of(path)
            if year is not None and year < M.FIRST_YEAR:
                continue
            f = pd.read_parquet(path, columns=cols)
            if tnames is not None:
                f = f[f["tourney_name"].isin(tnames)]
            frames.append(f.assign(official=source, qual_file=path.parent.name == "atp_qualifying"))
    if not frames:
        return pd.DataFrame(columns=KEY + ["score", "official"])
    rows = pd.concat(frames, ignore_index=True)
    rows["d"] = M.to_date(rows["tourney_date"].astype(str), "%Y%m%d").dt.strftime("%Y-%m-%d")
    rows["draw"] = np.where(rows["qual_file"] | M.is_qual_round(rows["round"]), "qual", "main")
    return rows.drop_duplicates(KEY)[KEY + ["score", "official"]]


def check(gap: str) -> tuple[pd.DataFrame, dict]:
    """Each target's verdict (one row per target) and the counts."""
    targets, origin = E.load_targets(gap, refresh=False)
    targets = targets.assign(w1=targets["name1"].map(E.words), w2=targets["name2"].map(E.words))
    known = E.known_matches(targets)
    known = known.assign(w1=known["name1"].map(E.words), w2=known["name2"].map(E.words))
    lister = E.Lister(None, P.receipts_for(E.SOURCE), offline=True)
    _, rows, linked = E.list_and_link(lister, targets, known, log_every=10 ** 6)
    official = {k[:5]: (k[5], k[6]) for k in official_rows(set(targets["tname"].dropna())).itertuples(index=False)}
    out = []
    for r in rows:
        key = (r["tname"], pd.Timestamp(r["d"]).strftime("%Y-%m-%d"), r["name1"], r["name2"], r["draw"])
        score, source = official.get(key, (None, None))
        row = {k: r[k] for k in ("gap", "edition", "uid", "level", "draw", "year", "tname", "name1", "name2",
                                 "creator")}
        row.update(d=pd.Timestamp(r["d"]).date(), event_id=r.get("event_id"), ss_home=r.get("ss_home"),
                   ss_away=r.get("ss_away"), ss_winner_code=r.get("ss_winner_code"), official=source,
                   official_score=score)
        if not r["listed"]:
            row["verdict"] = "not linked"
        else:
            event = linked[r["event_id"]]
            row["ss_score"] = " ".join(f"{w}-{l}" for w, l in ss_sets(event))
            row["verdict"] = "no official row" if source is None else compare(event, r["name1"], score)
        out.append(row)
    frame = pd.DataFrame(out)
    frame["event_id"] = pd.to_numeric(frame["event_id"], errors="coerce").astype("Int64")
    shared = frame.dropna(subset=["event_id"]).groupby("event_id").filter(lambda g: len(g) > 1)
    summary = {"gap": gap, "targets_from": origin, "generated_at": P.utc_now_iso(),
               "verdicts": frame["verdict"].value_counts().to_dict(),
               "by_year_level": {f"{y}|{lv}": g["verdict"].value_counts().to_dict()
                                 for (y, lv), g in frame.groupby(["year", "level"])},
               "by_official_file": {str(k): g["verdict"].value_counts().to_dict()
                                    for k, g in frame.groupby(frame["official"].fillna("none"))},
               "no_official_row_by_creator": frame.loc[frame["verdict"].eq("no official row"), "creator"]
               .value_counts().to_dict(),
               "events_linked_by_two_targets": shared[["event_id", "tname", "d", "name1", "name2", "verdict"]]
               .astype(str).to_dict(orient="records")}
    return frame, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gap", default=E.DEFAULT_GAP)
    args = parser.parse_args()
    P.configure_stdout()
    frame, summary = check(args.gap)
    frame.sort_values(["d", "edition", "uid"]).to_csv(E.table_path(args.gap, "link_check"), index=False)
    (E.STUDY / f"sofascore_{args.gap}_link_check.json").write_text(json.dumps(summary, indent=1, default=str) + "\n",
                                                                   encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("verdicts", "no_official_row_by_creator", "events_linked_by_two_targets")},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
