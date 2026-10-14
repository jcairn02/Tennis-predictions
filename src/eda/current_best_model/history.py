"""Is the training history still the frozen reference's? The owner's rule (8 Oct 2026; docs/decisions/
2026-10-08-current-best-model.md, amendment):

    "I just want the same data as before for training + training updates from future dates frozen. But if we are
    downloading new LOWER LEVEL data, challenger +ITF it doesnt get auto included in the model. I want a way to test
    if this lower level skill data is harming our model (though the data is prior to the current date)."

So the model trains on the reference's matches (the frozen Stage 0 of 8 Oct, reference.py) plus the matches played from
then on, from the sources that were feeding it.

NARROWED BY THE OWNER ON 9 OCT 2026 (docs/decisions/2026-10-08-current-best-model.md, amendment of 9 Oct, evening): "the
oct 8 freeze I suggested was more about the data from the challenger series/ITF tour and I think the agent I was
talking to read into it deeper than I was intending" ... "Ok, do this".
    * LOWER-LEVEL history (every level below the main draw: tour and Slam qualifying, Challengers and their qualifying,
      ITF and its qualifying, and any level this check does not know) that is new, dropped or revised is a CANDIDATE:
      built apart and compared with the reference before the owner accepts it. Since 9 Oct it is judged as a harm check
      (docs/decisions/2026-10-09-adoption-by-change-class.md).
    * MAIN-TOUR history (the main draws of the Slams, the Finals, the 1000s, 500s and 250s, and team events) that is
      new, dropped or revised is a repair, decided on the data evidence. It is listed here, so nothing changes silently,
      but it does not refuse a template build.

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
new past, dropped and revised count every level. Each is split into "gated" (lower-level) and "allowed_main_tour". The
template may be built only when the gated new past, dropped and revised are all empty (until 9 Oct 2026: all three, at
every level). run_chain.py --setup enforces it; a build that changes the lower-level history is made with --candidate
and compared with the reference.
    accepted   (since 10 Oct 2026) new past matches and completed box scores of the lower-level packages the owner
               accepted after their candidate's test (current_best_model/additions.py, accepted.json): allowed, and
               counted apart, so a build that merged them (run_chain.py --additions, a prediction run) is not refused.
               Since 13 Oct 2026 also the decided repairs: a revised match that the decided correction or override
               tables name (every Stage 0 build applies them; each row an owner's decision: the corrupt-data fixes of
               8 Oct, the Slam box scores of 6 Oct, the Roland Garros repair of 9-10 Oct once adopt.py swaps it in),
               whose lower-level rows (Slam qualifying) would otherwise refuse every template build
               (docs/studies/data_gaps_2026/)
    tml_lower  (since 13 Oct 2026; the owner, docs/decisions/2026-10-13-tml-lower-level-revisions.md) lower-level new
               past, dropped and revised matches that are Tennis My Life's own rows (source "tml") at a level it fed the
               reference (tour, map_level and qualifying flag of the reference's own tml rows: men's Challengers, tour
               and Slam qualifying): its corrections, drops and backfills enter by themselves. Listed apart from "gated",
               so they refuse no template build. A match a candidate's box layers changed (box_layers.parquet in the
               checked folder, applied) stays gated: another source's box score, not Tennis My Life's own revision. A
               row Stage 0 takes from Sackmann stays gated whatever caused its change. The all-level counts (new_past,
               dropped, revised) still hold these matches

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
# Main-tour data (the owner, 9 Oct 2026): the main draws of the Slams, the Finals, the 1000s, 500s and 250s, and team
# events. Every other map_level (TQ, GSQ, CH, CHQ, ITF, ITFQ, or one this check does not know) is lower-level and gated.
MAIN_TOUR = {"GS", "FIN", "T1000", "T500", "T250", "TEAM"}
# the decided correction and override tables every Stage 0 build applies (stage0_build.DECIDED_CORRECTIONS and
# DECIDED_OVERRIDES), with the column that names each row's Stage 0 match
DECIDED_TABLES = {ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv": "match_id",
                  ROOT / "data" / "studies" / "data_continuity" / "slam_box_overrides.csv": "stage0_match_id"}


def decided_repair_ids(tables: dict | None = None) -> set:
    """The Stage 0 matches the decided correction and override tables name (the accepted class's repairs)."""
    out = set()
    for path, col in (tables or DECIDED_TABLES).items():
        if Path(path).exists():
            out |= set(pd.read_csv(path, usecols=[col], dtype=str)[col].dropna())
    return out


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


def lower_level(rows: pd.DataFrame) -> np.ndarray:
    """Whether each row is lower-level history (gated): any level outside MAIN_TOUR, or a qualifying match."""
    qualifying = rows["qualifying"].eq(True).to_numpy() if "qualifying" in rows else False
    return ~rows["map_level"].astype(str).isin(MAIN_TOUR).to_numpy() | qualifying


def tml_levels(ref: pd.DataFrame) -> set[tuple[str, str, bool]]:
    """(tour, map_level, qualifying) of the reference's own Tennis My Life rows: the levels it fed the reference."""
    t = ref[ref["source"].astype(str).eq("tml")]
    return set(zip(t["tour"].astype(str), t["map_level"].astype(str), t["qualifying"].eq(True)))


def layered_ids(folder: Path) -> set:
    """Matches a candidate build's box layers changed (candidate_stage0.py's box_layers.parquet, the applied rows):
    another source's box score on a reference match, not a revision of Tennis My Life's own."""
    p = Path(folder) / "box_layers.parquet"
    if not p.exists():
        return set()
    lay = pd.read_parquet(p, columns=["match_id", "applied"])
    return set(lay.loc[lay["applied"].astype(bool), "match_id"].astype(str))


def tml_own(rows: pd.DataFrame, levels: set, layered: set) -> np.ndarray:
    """Whether each row is Tennis My Life's own, at a level it fed the reference, and not changed by a candidate's box
    layers (the tml_lower class, 13 Oct 2026)."""
    if rows.empty:
        return np.zeros(0, dtype=bool)
    own = rows["source"].astype(str).eq("tml").to_numpy()
    fed_level = np.array([x in levels for x in zip(rows["tour"].astype(str), rows["map_level"].astype(str),
                                                   rows["qualifying"].eq(True))], dtype=bool)
    return own & fed_level & ~rows["match_id"].astype(str).isin(layered).to_numpy()


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
    # the packages the owner accepted (additions.py): their added matches and completed box scores
    from src.eda.current_best_model import additions as AD
    acc_added, acc_completed = AD.accepted_ids()
    acc_new = new_past["match_id"].isin(acc_added).to_numpy()
    acc_rev = revised["match_id"].isin(acc_completed).to_numpy()
    acc_rep = revised["match_id"].isin(decided_repair_ids()).to_numpy() & ~acc_rev    # decided repairs (13 Oct 2026)
    accepted = pd.concat([new_past[acc_new], revised[acc_rev], revised[acc_rep]])
    new_past, revised = new_past[~acc_new], revised[~acc_rev & ~acc_rep]
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
           "accepted": {"matches": int(len(accepted)), "added": int(acc_new.sum()), "completed": int(acc_rev.sum()),
                        "decided_repairs": int(acc_rep.sum()), "by": tally(accepted)},
           "feeds": sorted("/".join(f) for f in feeds)}
    parts = {"new_past": new_past, "dropped": dropped, "revised": revised}
    levels, layered = tml_levels(ref_m), layered_ids(stage0)
    for key, keep in (("gated", True), ("allowed_main_tour", False)):
        out[key] = {}
        for name, t in parts.items():
            s = t[lower_level(t) == keep]
            if keep:                          # Tennis My Life's own lower-level changes are allowed (13 Oct 2026)
                s = s[~tml_own(s, levels, layered)]
            out[key][name] = {"matches": int(len(s)), "by": tally(s), "examples": s["match_id"].head(10).tolist()}
    out["tml_lower"] = {}
    for name, t in parts.items():
        s = t[lower_level(t)]
        s = s[tml_own(s, levels, layered)]
        out["tml_lower"][name] = {"matches": int(len(s)), "by": tally(s), "examples": s["match_id"].head(10).tolist()}
    out["template_ok"] = not any(v["matches"] for v in out["gated"].values())
    return out


def summary_line(res: dict) -> str:
    g, mt = res["gated"], res["allowed_main_tour"]
    main = sum(v["matches"] for v in mt.values())
    acc = res.get("accepted", {}).get("matches", 0)
    tl = res.get("tml_lower", {})
    tml = sum(v["matches"] for v in tl.values())
    return (f"history vs the reference of {res['reference']}: future {res['future']['matches']:,} and updated "
            f"{res['updated']['matches']:,} (allowed); "
            + (f"accepted {acc:,} (allowed: lower-level additions {res['accepted'].get('added', 0):,}, completions "
               f"{res['accepted'].get('completed', 0):,}, decided repairs {res['accepted'].get('decided_repairs', 0):,}); "
               if acc else "")
            + f"main-tour changes {main:,} (allowed, listed: new past "
            f"{mt['new_past']['matches']:,}, dropped {mt['dropped']['matches']:,}, revised {mt['revised']['matches']:,}); "
            + (f"Tennis My Life's own lower-level changes {tml:,} (allowed, decided 13 Oct: new past "
               f"{tl['new_past']['matches']:,}, dropped {tl['dropped']['matches']:,}, revised "
               f"{tl['revised']['matches']:,}); " if tml else "")
            + f"lower-level new past {g['new_past']['matches']:,}, dropped {g['dropped']['matches']:,}, revised "
            f"{g['revised']['matches']:,} -> "
            + ("the template may be built" if res["template_ok"]
               else "the lower-level history changed: a template build is refused"))


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
