"""Task 6: a timing probe on the 52-week aggregator (build_common.window_sums), in the spirit of
src/eda/match_timing/probe.py. The atoms follow each player's own matches, so they are safe by construction; this
checks the code.

The aggregate probed: each player-match's 52-week sums of the atoms' won counts (srv_won, ret_won and by band) and their
denominators, for every row of atoms.parquet (2018-2026). For each cut, every point winner of the matches on one side of
the cut is scrambled (each point's winner set at random to one of the two players), the atoms of those matches are
rebuilt (build_atoms.atoms), the aggregate recomputed, and every row compared with the unchanged build:
    1. Stage 0's clock (the aggregator's own): scramble every match with a tournament date after the cut day; no row
       dated on or before it may move (20 random cut days in 2019-2026).
    2. The real dates (the match clock, data/studies/match_timing/timing.parquet): scramble every match that surely
       started after D (es > D); no row of a match that surely finished by D (lf <= D) may move. Cut days where events
       overlap: the second Wednesday of the 2025-26 Grand Slams, and Cincinnati 2025's third day.
    3. The match itself: for 200 random rows, scramble that match, every match of the same event's same or later
       rounds and every later date; that row may not move.
Each probe also counts the rows on the other side that did move (the scramble has an effect). No match result is read.

Run:  ./python.sh src/eda/p9_point_details/build_probe.py      (after build_atoms.py; a few minutes)
Writes data/studies/p9_point_details/build/probe.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_atoms as BA  # noqa: E402
from src.eda.p9_point_details import build_common as B  # noqa: E402

VALUES = ["srv_won", "ret_won"] + [f"srv_w_b{b}" for b in range(5)] + [f"ret_w_b{b}" for b in range(5)] + \
         ["srv_pts", "ret_pts"]
REAL_CUTS = ["2025-01-22", "2025-06-04", "2025-07-09", "2025-09-03", "2026-01-28", "2026-06-03", "2026-07-08",
             "2026-09-09", "2025-08-09"]
EPOCH = pd.Timestamp("1970-01-01")


def scrambled_atoms(pts: pd.DataFrame, s0: pd.DataFrame, atoms: pd.DataFrame, matches: set,
                    rng: np.random.Generator) -> pd.DataFrame:
    """atoms with the won counts of ``matches`` rebuilt from points whose winners were drawn at random."""
    sub = pts[pts["match_id"].isin(matches)].copy()
    if sub.empty:
        return atoms
    ab = sub.merge(s0[["match_id", "player_a_id", "player_b_id"]], on="match_id", how="left")
    coin = rng.random(len(ab)) < 0.5
    sub["winner_id"] = np.where(coin, ab["player_a_id"], ab["player_b_id"])
    new = BA.atoms(sub, s0)
    keep = atoms[~atoms["match_id"].isin(matches)]
    cols = [c for c in atoms.columns if c in new.columns]
    return pd.concat([keep[cols], new[cols]], ignore_index=True)


def aggregate(a: pd.DataFrame) -> pd.DataFrame:
    s = B.window_sums(a, VALUES)
    s.index = pd.MultiIndex.from_frame(a[["match_id", "player_id"]])
    return s


def compare(base: pd.DataFrame, got: pd.DataFrame, rows: pd.Index) -> int:
    g = got.reindex(base.index)
    diff = ~np.all(np.isclose(g.to_numpy(), base.to_numpy()), axis=1)
    return int(pd.Series(diff, index=base.index).reindex(rows).fillna(False).sum())


def main() -> int:
    pts = pd.read_parquet(B.OUT / "rally_points.parquet",
                          columns=["match_id", "source", "server_id", "winner_id", "rally_c", "band", "net_server",
                                   "net_returner"])
    atoms = pd.read_parquet(B.OUT / "atoms.parquet")
    atoms["tournament_date"] = pd.to_datetime(atoms["tournament_date"])
    s0 = B.stage0_men(["player_a_id", "player_b_id", "tournament_date", "tournament_id", "round", "round_order",
                       "level", "qualifying", "surface", "best_of"], 2018)
    tm = pd.read_parquet(B.TIMING, columns=["match_id", "es", "lf"]).set_index("match_id")
    atoms["es"] = atoms["match_id"].map(tm["es"])
    atoms["lf"] = atoms["match_id"].map(tm["lf"])
    base = aggregate(atoms)
    rng = np.random.default_rng(20261028)
    res = {"rows": int(len(atoms)), "values": VALUES}
    # 1. Stage 0's clock
    days = np.sort(atoms["tournament_date"].unique())
    days = days[(days >= np.datetime64("2019-01-01")) & (days <= np.datetime64("2026-09-30"))]
    cuts = rng.choice(days, size=20, replace=False)
    out1 = []
    for c in cuts:
        after = set(atoms.loc[atoms["tournament_date"] > c, "match_id"])
        got = aggregate(scrambled_atoms(pts, s0, atoms, after, rng))
        before_rows = pd.MultiIndex.from_frame(atoms.loc[atoms["tournament_date"] <= c, ["match_id", "player_id"]])
        after_rows = pd.MultiIndex.from_frame(atoms.loc[atoms["tournament_date"] > c, ["match_id", "player_id"]])
        out1.append({"cut": str(pd.Timestamp(c).date()), "rows_on_or_before": int(len(before_rows)),
                     "moved_on_or_before": compare(base, got, before_rows),
                     "rows_after": int(len(after_rows)), "moved_after": compare(base, got, after_rows)})
    res["stage0_clock"] = out1
    B.log(f"Stage 0 clock: moved before the cut {sum(r['moved_on_or_before'] for r in out1)} "
          f"(after: {sum(r['moved_after'] for r in out1)})")
    # 2. real dates
    out2 = []
    for d in REAL_CUTS:
        D = (pd.Timestamp(d) - EPOCH).days
        later = set(atoms.loc[atoms["es"] > D, "match_id"])
        got = aggregate(scrambled_atoms(pts, s0, atoms, later, rng))
        earlier = pd.MultiIndex.from_frame(atoms.loc[atoms["lf"] <= D, ["match_id", "player_id"]])
        later_rows = pd.MultiIndex.from_frame(atoms.loc[atoms["es"] > D, ["match_id", "player_id"]])
        moved = compare(base, got, earlier)
        rec = {"cut": d, "rows_surely_finished": int(len(earlier)), "moved_surely_finished": moved,
               "rows_surely_later": int(len(later_rows)), "moved_surely_later": compare(base, got, later_rows)}
        if moved:
            g = got.reindex(base.index)
            diff = pd.Series(~np.all(np.isclose(g.to_numpy(), base.to_numpy()), axis=1), index=base.index)
            rec["examples"] = [list(x) for x in diff[diff].index.intersection(earlier)[:10]]
        out2.append(rec)
    res["real_dates"] = out2
    B.log(f"real dates: moved surely-finished rows {sum(r['moved_surely_finished'] for r in out2)}")
    # 3. the match itself
    idx = rng.choice(len(atoms), size=200, replace=False)
    moved3, effect3 = 0, 0
    for i in idx:
        r = atoms.iloc[i]
        same_ev = atoms["tournament_id"].eq(r["tournament_id"]) & atoms["tournament_date"].eq(r["tournament_date"])
        hit = (atoms["tournament_date"] > r["tournament_date"]) | (same_ev & (atoms["round_order"] >= r["round_order"]))
        ms = set(atoms.loc[hit, "match_id"])
        sub_rows = atoms[atoms["player_id"].eq(r["player_id"])]
        got = aggregate(scrambled_atoms(pts, s0, sub_rows, ms & set(sub_rows["match_id"]), rng))
        b = base.loc[[(r["match_id"], r["player_id"])]]
        g = got.reindex(b.index)
        moved3 += int(not np.allclose(g.to_numpy(), b.to_numpy()))
        later = sub_rows[sub_rows["tournament_date"] > r["tournament_date"] + pd.Timedelta(days=6)]
        if len(later):
            bl = base.reindex(pd.MultiIndex.from_frame(later[["match_id", "player_id"]]))
            gl = got.reindex(bl.index)
            effect3 += int(not np.allclose(gl.to_numpy(), bl.to_numpy()))
    res["match_itself"] = {"rows_probed": 200, "moved": moved3, "later_rows_of_the_player_moved_in": effect3}
    B.log(f"match itself: moved {moved3} of 200 (the scramble moved later rows in {effect3} probes)")
    res["verdict"] = {"stage0_clock_clean": all(r["moved_on_or_before"] == 0 for r in out1),
                      "real_dates_clean": all(r["moved_surely_finished"] == 0 for r in out2),
                      "match_itself_clean": moved3 == 0}
    B.write_json(B.OUT / "probe.json", res)
    print(res["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
