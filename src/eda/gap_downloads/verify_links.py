"""Check the by-edition SofaScore links against the official result: does each linked event have the target
match's winner and set scores?

For every target of a gap (the frozen list, data/studies/gap_downloads/sofascore_<gap>_matches.csv), the links
are rebuilt offline from the adapter's cached listings with the adapter's own functions (no HTTP). Each linked
SofaScore event is then compared with Tennis My Life's row for the same match: the tournament, date and both
names exactly as the map took them from it. The comparison covers the winner and the games of every set
(tiebreak points are left aside).

Verdicts:
    agrees                     same winner, same games in every set (at a retirement, all but the unfinished set,
                               and without the unstarted 0-0 set SofaScore adds)
    winner agrees, SofaScore lists no score   early retirements
    winner agrees, score differs
    winner differs             a wrong link, or a result recorded differently
    no official row            the target did not come from Tennis My Life (6 came from Sackmann)
    not linked                 the adapter found no event for it

Writes data/studies/gap_downloads/sofascore_<gap>_link_check.csv (one row per target) and
sofascore_<gap>_link_check.json (counts overall and by year and level).

Usage: ./python.sh src/eda/gap_downloads/verify_links.py [--gap atp_points_2025]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import sofascore_editions as E       # noqa: E402

TML = PROJECT_ROOT / "data" / "dump" / "matches" / "tennis_my_life"
TML_FILES = ["atp_main/2025.parquet", "atp_main/2026.parquet", "atp_qualifying/2025_atp_quali.parquet",
             "atp_qualifying/2026_atp_quali.parquet", "ongoing/ongoing_tourneys.parquet"]
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
    """The verdict for one linked event against Tennis My Life's winner and score."""
    side = {1: "homeTeam", 2: "awayTeam"}.get(event.get("winnerCode"))
    if side is None or not (E.team_words(event.get(side) or {}) & E.words(winner)):
        return "winner differs"
    ours, theirs = ss_sets(event), tml_sets(score)
    if not ours:
        return "winner agrees, SofaScore lists no score"
    retired = "RET" in str(score or "").upper()
    while retired and len(ours) > len(theirs) and ours[-1] == (0, 0):   # SofaScore adds the set never started
        ours = ours[:-1]
    if ours == theirs or (retired and len(ours) == len(theirs) and ours[:-1] == theirs[:-1]):
        return "agrees"
    return "winner agrees, score differs"


def official_rows() -> pd.DataFrame:
    """Tennis My Life's ATP rows, keyed as the map took them plus the draw: a pair can meet in the qualifying
    and again in the main draw of one event (Basel 2025), and 2025 rows carry the tournament's start date."""
    cols = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]
    tml = pd.concat([pd.read_parquet(TML / f, columns=cols) for f in TML_FILES if (TML / f).exists()], ignore_index=True)
    tml["d"] = pd.to_datetime(tml["tourney_date"].astype(str), format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
    tml["draw"] = tml["round"].fillna("").astype(str).str.match(r"^Q\d").map({True: "qual", False: "main"})
    return tml.drop_duplicates(["tourney_name", "d", "winner_name", "loser_name", "draw"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gap", default=E.DEFAULT_GAP)
    args = parser.parse_args()
    P.configure_stdout()
    targets, origin = E.load_targets(args.gap, refresh=False)
    targets = targets.assign(w1=targets["name1"].map(E.words), w2=targets["name2"].map(E.words))
    known = E.known_matches(targets)
    known = known.assign(w1=known["name1"].map(E.words), w2=known["name2"].map(E.words))
    lister = E.Lister(None, P.receipts_for(E.SOURCE), offline=True)
    _, rows, linked = E.list_and_link(lister, targets, known, log_every=10 ** 6)
    tml = official_rows().set_index(["tourney_name", "d", "winner_name", "loser_name", "draw"])
    out = []
    for r in rows:
        key = (r["tname"], pd.Timestamp(r["d"]).strftime("%Y-%m-%d"), r["name1"], r["name2"], r["draw"])
        score = tml["score"].get(key) if key in tml.index else None
        row = {k: r[k] for k in ("gap", "edition", "uid", "level", "draw", "year", "tname", "name1", "name2")}
        row.update(d=pd.Timestamp(r["d"]).date(), event_id=r.get("event_id"), ss_home=r.get("ss_home"),
                   ss_away=r.get("ss_away"), ss_winner_code=r.get("ss_winner_code"), tml_score=score)
        if not r["listed"]:
            row["verdict"] = "not linked"
        else:
            event = linked[r["event_id"]]
            row["ss_score"] = " ".join(f"{w}-{l}" for w, l in ss_sets(event))
            row["verdict"] = "no official row" if score is None else compare(event, r["name1"], score)
        out.append(row)
    check = pd.DataFrame(out)
    check["event_id"] = pd.to_numeric(check["event_id"], errors="coerce").astype("Int64")
    shared = check.dropna(subset=["event_id"]).groupby("event_id").filter(lambda g: len(g) > 1)
    summary = {"gap": args.gap, "targets_from": origin, "generated_at": P.utc_now_iso(),
               "verdicts": check["verdict"].value_counts().to_dict(),
               "by_year_level": {f"{y}|{lv}": g["verdict"].value_counts().to_dict()
                                 for (y, lv), g in check.groupby(["year", "level"])},
               "events_linked_by_two_targets": shared[["event_id", "tname", "d", "name1", "name2", "verdict"]]
               .astype(str).to_dict(orient="records")}
    base = E.STUDY / f"sofascore_{args.gap}_link_check"
    check.sort_values(["d", "edition", "uid"]).to_csv(base.with_suffix(".csv"), index=False)
    base.with_suffix(".json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("verdicts", "events_linked_by_two_targets")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
