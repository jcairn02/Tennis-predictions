"""Is the training history still the frozen reference's? The owner's rule (8 Oct 2026; docs/decisions/
2026-10-08-current-best-model.md, amendment):

    "I just want the same data as before for training + training updates from future dates frozen. But if we are
    downloading new LOWER LEVEL data, challenger +ITF it doesnt get auto included in the model. I want a way to test
    if this lower level skill data is harming our model (though the data is prior to the current date)."

So the model trains on the reference's matches (the frozen Stage 0 of 8 Oct, reference.py) plus the matches played from
then on, from the sources that were feeding it. Anything else that changes the history (new lower-level matches or box
scores of past dates, a new source, a dropped or revised past match) is a CANDIDATE: built apart and compared with the
reference (compare.py) before the owner accepts it.

check() compares a Stage 0 (default: the live one) with the reference's, match by match:
    future     a match the reference lacks, possibly played from FREEZE - GRACE_DAYS on, from a source, tour and level
               that fed the reference in its last RECENT_DAYS days. These are the updates the rule lets in
    updated    a reference match possibly played from FREEZE - GRACE_DAYS on, from such a feed, that changed (a box score
               completed, a score corrected) or left the table: the feed completing a match it was still publishing at
               the freeze. Allowed like a future match (the owner, 8 Oct 2026, docs/decisions/
               2026-10-08-prediction-run-box-scores.md)
    new past   every other match the reference lacks: new history (a backfill, a new source or a new level)
    dropped    every other reference match the table lacks
    revised    every other match in both whose facts (players, date, round, surface, format, status, score, minutes) or
               box score (each player's serve and return counts, rank, age) differ
"Possibly played from" a day: the match's latest possible finish (the timeline's lf; its tournament date when the
timeline lacks it) falls on or after it. Undated matches carry wide windows (Shanghai 2026's first round starts its
window on 3 Oct), so their earliest start would call matches of the events in progress at the freeze old. A new match
is placed by the live timeline; a reference match by the reference's own, so no revision can move it into the window.
The template may be built only when new past, dropped and revised are all empty. run_chain.py --setup enforces it; a
build that changes the history is made with --candidate and compared with the reference.

Run: ./python.sh src/eda/current_best_model/history.py [--stage0 <folder holding stage0_matches.parquet>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import reference as R  # noqa: E402

LIVE = ROOT / "data" / "studies" / "predictability_diagnostic"
REF_STAGE0 = R.FROZEN / "tables" / "data" / "studies" / "predictability_diagnostic"
LIVE_TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
# the reference's timeline as it stood at the freeze (reference.py: a TDI refresh rewrote the build's own copy)
REF_TIMING = R.FROZEN / "tables_later" / "data" / "studies" / "match_timing" / "timing.parquet"
FREEZE = pd.Timestamp("2026-10-08")      # the reference's Stage 0 was rebuilt on this day (18:53 UTC)
GRACE_DAYS = 3                           # a source's results of the last days before the freeze may still arrive
RECENT_DAYS = 60                         # the sources feeding the reference: its source x tour x level of these days
EPOCH = pd.Timestamp("1970-01-01")
MATCH_FACTS = ["tour", "year", "level", "qualifying", "round", "surface", "indoor", "best_of", "tournament_id",
               "tournament_date", "status", "score", "minutes", "format", "has_box", "player_a_id", "player_b_id",
               "a_won"]
PLAYER_FACTS = ["side", "player_id", "opponent_id", "won", "rank", "rank_points", "age", "ace", "df", "svpt",
                "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "has_box"]
KEEP = ["match_id", "source", "tour", "map_level", "tournament_date", "year"]


def content_hash(matches: pd.DataFrame, players: pd.DataFrame) -> pd.Series:
    """One 64-bit hash per match id over its facts and both players' rows (row order does not matter)."""
    m = pd.Series(pd.util.hash_pandas_object(matches[MATCH_FACTS].astype(str), index=False).to_numpy(),
                  index=matches["match_id"].to_numpy())
    order = np.argsort(players["match_id"].to_numpy(), kind="stable")
    ids = players["match_id"].to_numpy()[order]
    rows = pd.util.hash_pandas_object(players[PLAYER_FACTS].astype(str), index=False).to_numpy()[order]
    if len(ids):
        starts = np.flatnonzero(np.r_[True, ids[1:] != ids[:-1]])
        p = pd.Series(np.bitwise_xor.reduceat(rows, starts), index=ids[starts])
    else:
        p = pd.Series([], dtype="uint64")
    pm = p.reindex(m.index).fillna(0).to_numpy().astype("uint64")
    return pd.Series(m.to_numpy() ^ pm, index=m.index)


def load(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = pd.read_parquet(folder / "stage0_matches.parquet", columns=sorted(set(MATCH_FACTS + KEEP)))
    players = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id"] + PLAYER_FACTS)
    for t in (matches, players):
        t["match_id"] = t["match_id"].astype(str)
    return matches, players


def recent_feeds(ref: pd.DataFrame) -> set[tuple[str, str, str]]:
    """(source, tour, level) of the reference's matches of its last RECENT_DAYS days: the feeds updates may come from."""
    d = pd.to_datetime(ref["tournament_date"], errors="coerce")
    r = ref[d >= FREEZE - pd.Timedelta(days=RECENT_DAYS)]
    return set(map(tuple, r[["source", "tour", "map_level"]].astype(str).drop_duplicates().to_numpy().tolist()))


def played_until(rows: pd.DataFrame, timing: Path | None) -> pd.Series:
    """Each match's latest possible finish (the timeline's lf), else its tournament date: the last day it may have been
    played on."""
    last = pd.to_datetime(rows["tournament_date"], errors="coerce")
    if timing is not None and Path(timing).exists():
        t = pd.read_parquet(timing, columns=["match_id", "lf"]).astype({"match_id": str}).set_index("match_id")["lf"]
        lf = rows["match_id"].map(t)
        last = last.where(lf.isna(), EPOCH + pd.to_timedelta(lf, unit="D"))
    return last


def fed(rows: pd.DataFrame, feeds: set) -> np.ndarray:
    """Whether each row's (source, tour, level) fed the reference in its last RECENT_DAYS days."""
    return np.array([tuple(x) in feeds for x in rows[["source", "tour", "map_level"]].astype(str).to_numpy().tolist()],
                    dtype=bool)


def tally(t: pd.DataFrame) -> list[dict]:
    if t.empty:
        return []
    g = t.groupby(["source", "tour", "map_level", "year"]).size().rename("matches").reset_index()
    return g.sort_values(["source", "tour", "map_level", "year"]).to_dict("records")


def check(stage0: Path = LIVE, timing: Path | None = LIVE_TIMING, ref_stage0: Path = REF_STAGE0,
          ref_timing: Path | None = REF_TIMING) -> dict:
    ref_m, ref_p = load(ref_stage0)
    m, p = load(stage0)
    ref_ids, ids = pd.Index(ref_m["match_id"]), pd.Index(m["match_id"])
    new = m[~ids.isin(ref_ids)].copy()
    gone = ref_m[~ref_ids.isin(ids)]
    both = ids.intersection(ref_ids)
    h_ref = content_hash(ref_m[ref_m["match_id"].isin(both)], ref_p[ref_p["match_id"].isin(both)])
    h = content_hash(m[m["match_id"].isin(both)], p[p["match_id"].isin(both)])
    revised_ids = both[(h.reindex(both).to_numpy() != h_ref.reindex(both).to_numpy())]
    changed = m[m["match_id"].isin(revised_ids)]
    feeds = recent_feeds(ref_m)
    since = FREEZE - pd.Timedelta(days=GRACE_DAYS)
    is_future = (played_until(new, timing) >= since).to_numpy() & fed(new, feeds)
    future, new_past = new[is_future], new[~is_future]
    # reference matches the feed was still publishing at the freeze, placed by the reference's own timeline; a changed
    # one must still come from such a feed
    recent_ref = set(ref_m["match_id"][(played_until(ref_m, ref_timing) >= since).to_numpy() & fed(ref_m, feeds)])
    ok = changed["match_id"].isin(recent_ref).to_numpy() & fed(changed, feeds)
    updated_revised, revised = changed[ok], changed[~ok]
    ok = gone["match_id"].isin(recent_ref).to_numpy()
    updated_dropped, dropped = gone[ok], gone[~ok]
    updated = pd.concat([updated_revised, updated_dropped])
    out = {"checked": str(stage0), "reference": R.REF_ID, "freeze": str(FREEZE.date()), "since": str(since.date()),
           "matches": int(len(m)), "reference_matches": int(len(ref_m)),
           "future": {"matches": int(len(future)), "by": tally(future)},
           "updated": {"matches": int(len(updated)), "revised": int(len(updated_revised)),
                       "dropped": int(len(updated_dropped)), "by": tally(updated),
                       "examples": updated["match_id"].head(10).tolist()},
           "new_past": {"matches": int(len(new_past)), "by": tally(new_past),
                        "examples": new_past["match_id"].head(10).tolist()},
           "dropped": {"matches": int(len(dropped)), "by": tally(dropped), "examples": dropped["match_id"].head(10).tolist()},
           "revised": {"matches": int(len(revised)), "by": tally(revised), "examples": revised["match_id"].head(10).tolist()},
           "feeds": sorted("/".join(f) for f in feeds)}
    out["template_ok"] = not (len(new_past) or len(dropped) or len(revised))
    return out


def summary_line(res: dict) -> str:
    return (f"history vs the reference of {res['reference']}: future {res['future']['matches']:,} and updated "
            f"{res['updated']['matches']:,} (allowed); new past {res['new_past']['matches']:,}, dropped "
            f"{res['dropped']['matches']:,}, revised {res['revised']['matches']:,} -> "
            + ("the template may be built" if res["template_ok"] else "the history changed: a template build is refused"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", default=str(LIVE), help="the folder holding stage0_matches.parquet")
    ap.add_argument("--timing", default=str(LIVE_TIMING), help="its timeline (timing.parquet)")
    a = ap.parse_args()
    res = check(Path(a.stage0), Path(a.timing))
    print(json.dumps({k: v for k, v in res.items() if k != "feeds"}, indent=1, default=str))
    print(summary_line(res))
    return 0 if res["template_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
