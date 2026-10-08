"""The real-date probe: no input of a match moves when results that surely happened AFTER it are changed.

On a slice of history (every level, 2023-2024, history inside the slice), for each cut day D:

    later    matches that surely started after D      (earliest possible start > D)
    earlier  matches that surely finished by D         (latest possible finish <= D)

Every later match's result is reversed (the winner and the two players' statistics exchanged), every input rebuilt, and
every input of every earlier pool match compared with the unchanged build. Matches whose window straddles D are neither
changed nor checked. The cut days sit where events overlap: a Grand Slam's second Monday, the day Cincinnati started while
Montreal finished.

Run twice: on the leak-proof timeline (no earlier input may move) and, for the IOS inputs, on Stage B's week clock (the
leak: some earlier inputs do move). The probe tests the inputs against the timeline; whether the windows themselves hold
the true days is checked separately (window coverage in timing_check.py).

Writes data/studies/match_timing/probe.json and probe_details.csv.
Run: ./python.sh src/eda/match_timing/probe.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import rebuild as RB  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402

SLICE = ("2023-01-01", "2024-12-31")
# Wednesdays of a two-week event's second week (US Open 2023, Australian Open 2024, Wimbledon 2024) and Cincinnati 2024's
# third day (Montreal's final was its first): events that started that Monday have played rounds by then, while the
# long event's quarter-finals, semi-finals and final are still to come
CUTS = ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")
ATOL = 1e-9
SWAP_EXTRA = ["won"]


def flip(matches: pd.DataFrame, players: pd.DataFrame, ids: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reverse the results of the given matches: the winner flag, and every per-player count and rate exchanged between
    the two players (each player's derived return figures come from the other's serve, so the swap stays consistent)."""
    m, p = matches.copy(), players.copy()
    sel = m["match_id"].isin(ids)
    m.loc[sel, "a_won"] = ~m.loc[sel, "a_won"].astype(bool)
    stat_cols = [c for c in p.columns if c.endswith("_n") or c.endswith("_d")]
    stat_cols += [c for c in C.BOX if c in p.columns] + ["has_box"] + SWAP_EXTRA
    stat_cols = list(dict.fromkeys(c for c in stat_cols if c in p.columns))
    ps = p[p["match_id"].isin(ids)]
    a = ps[ps["side"].eq("A")].set_index("match_id")
    b = ps[ps["side"].eq("B")].set_index("match_id")
    a, b = a.loc[sorted(ids & set(a.index))], b.loc[sorted(ids & set(b.index))]
    ia = p.index[p["match_id"].isin(ids) & p["side"].eq("A")]
    ib = p.index[p["match_id"].isin(ids) & p["side"].eq("B")]
    order_a = p.loc[ia, "match_id"].to_numpy()
    order_b = p.loc[ib, "match_id"].to_numpy()
    for c in stat_cols:
        p.loc[ia, c] = b.loc[order_a, c].to_numpy()
        p.loc[ib, c] = a.loc[order_b, c].to_numpy()
    return m, p


def compare(base: pd.DataFrame, got: pd.DataFrame, check: np.ndarray, cols: list[str]) -> dict:
    x = base[cols].to_numpy(dtype=float)
    y = got[cols].to_numpy(dtype=float)
    moved = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
    gap = np.where(np.isfinite(x) & np.isfinite(y), np.abs(x - y), 0.0)
    by_col = {c: int(moved[check, j].sum()) for j, c in enumerate(cols) if moved[check, j].any()}
    return {"checked_matches": int(check.sum()), "checked_values": int(check.sum() * len(cols)),
            "moved_matches": int(moved[check].any(axis=1).sum()),
            "largest_difference": float(gap[check].max()) if check.any() else 0.0,
            "moved_by_input": by_col,
            "unchecked_moved_matches": int(moved[~check].any(axis=1).sum())}


def main() -> int:
    global SLICE, CUTS
    args = sys.argv[1:]
    if "--slice" in args:
        i = args.index("--slice")
        SLICE = (args[i + 1], args[i + 2])
    if "--cuts" in args:
        CUTS = tuple(args[args.index("--cuts") + 1].split(","))
    start = time.time()
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs", "start"])
    matches = C.load_matches()
    sl = matches["tournament_date"].between(pd.Timestamp(SLICE[0]), pd.Timestamp(SLICE[1]))
    matches = matches[sl].reset_index(drop=True)
    ids_all = set(matches["match_id"])
    players = pd.read_parquet(C.MATCH_PLAYERS)
    players = players[players["match_id"].isin(ids_all)].reset_index(drop=True)
    odds = pd.read_parquet(E.ODDS)
    tm = timing[timing["match_id"].isin(ids_all)].reset_index(drop=True)
    week = tm.assign(es=tm["start"], lf=tm["start"], obs=tm["start"])   # Stage B's clock, for the leak demonstration
    MT.log(f"slice {SLICE}: {len(matches):,} matches")
    base = RB.features_from_tables(matches, players, odds, tm)
    base_week = RB.features_from_tables(matches, players, odds, week, per_player=False)
    cols = [c for c in base.columns if c != "match_id"]
    ios_cols = [c for c in base_week.columns if c != "match_id"]
    tmi = tm.set_index("match_id")
    es_pool = base["match_id"].map(tmi["es"]).to_numpy()
    lf_pool = base["match_id"].map(tmi["lf"]).to_numpy()
    results, details = [], []
    for cut in CUTS:
        D = float(MT.to_day([cut])[0])
        later = set(tm.loc[tm["es"] > D, "match_id"])
        earlier = lf_pool <= D
        straddle = int(((tm["es"] <= D) & (tm["lf"] > D)).sum())
        m2, p2 = flip(matches, players, later)
        got = RB.features_from_tables(m2, p2, odds, tm)
        got_week = RB.features_from_tables(m2, p2, odds, week, per_player=False)
        rec = {"cut": cut, "changed_matches": len(later), "straddling_matches_unchecked": straddle,
               "leakproof": compare(base, got, earlier, cols),
               "week_clock_ios": compare(base_week, got_week, earlier, ios_cols)}
        results.append(rec)
        MT.log(f"cut {cut}: leak-proof moved {rec['leakproof']['moved_matches']} of "
               f"{rec['leakproof']['checked_matches']:,} earlier matches; week-clock IOS moved "
               f"{rec['week_clock_ios']['moved_matches']}")
        for clock, r in (("leakproof", rec["leakproof"]), ("week_clock_ios", rec["week_clock_ios"])):
            for c, n in r["moved_by_input"].items():
                details.append({"cut": cut, "clock": clock, "input": c, "earlier_matches_moved": n})
    out = {"slice": SLICE, "cuts": results, "tolerance": ATOL, "inputs_checked": cols,
           "verdict": ("PASS: no input of a match that surely finished by the cut moved"
                       if all(r["leakproof"]["moved_matches"] == 0 for r in results) else "FAIL: see moved_by_input"),
           "seconds": round(time.time() - start, 1)}
    MT.jdump(out, MT.OUT / "probe.json")
    pd.DataFrame(details, columns=["cut", "clock", "input", "earlier_matches_moved"]).to_csv(
        MT.OUT / "probe_details.csv", index=False)
    MT.log(out["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
