"""Audit of Stage 0, check 9: introduce a leak on purpose and confirm the tests fail.

Six leaky versions of the as-of helper (common.asof_sums) are written here. Each is put in place of
the real helper in memory (common.py itself is not touched) and then:

    * the black-box leakage probe (common.leak_probe) is run on real data, as stage0_checks.py runs
      it (the player rows of 2024, 20 cut points) and with 200 cut points;
    * the study's own tests (test/predictability_diagnostic/test_order_asof.py) are run with pytest,
      in this process, and the failing tests are recorded.

The real helper is also compared with a row-by-row reading of the rule on real rows (every player
row of the 2024 round robins and of players with two events in one week, plus a random sample).

Writes audit0/leak.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_leak.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

REAL = C.asof_sums


def _frame(rows, values):
    v = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    for c in values:
        v[c] = pd.to_numeric(rows[c], errors="coerce").fillna(0.0).astype("float64")
    return v


def leak_including_the_match(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                             rnd="round_order"):
    """The round's own sums are added back: the match itself and its round (off by one round)."""
    base = REAL(rows, values, player, date, event, rnd)
    v = _frame(rows.rename(columns={player: "player_id", date: "tournament_date", event: "tournament_id",
                                    rnd: "round_order"}), values)
    own = v.groupby(["player_id", "tournament_date", "tournament_id", "round_order"])[values].transform("sum")
    return base + own.to_numpy()


def leak_same_round_others(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                           rnd="round_order"):
    """Other matches of the same round (a round-robin stage) are counted; the match itself is not."""
    base = REAL(rows, values, player, date, event, rnd)
    v = _frame(rows, values)
    own = v.groupby(["player_id", "tournament_date", "tournament_id", "round_order"])[values].transform("sum")
    return base + (own - v[values]).to_numpy()


def leak_same_week_other_events(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                                rnd="round_order"):
    """Other events of the same tournament week are counted in full."""
    base = REAL(rows, values, player, date, event, rnd)
    v = _frame(rows, values)
    day = v.groupby(["player_id", "tournament_date"])[values].transform("sum")
    own_event = v.groupby(["player_id", "tournament_date", "tournament_id"])[values].transform("sum")
    return base + (day - own_event).to_numpy()


def leak_earlier_in_order(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                          rnd="round_order"):
    """A running total over the table's order, the match itself left out: it counts matches that
    come earlier in the order but are simultaneous under the rule (same round, same week)."""
    v = _frame(rows, values)
    v["order"] = rows["order"].to_numpy()
    s = v.sort_values(["order"], kind="mergesort")
    cum = s.groupby("player_id")[values].cumsum() - s[values]
    return cum.reindex(rows.index).set_axis(rows.index)


def leak_next_match(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                    rnd="round_order"):
    """The player's next match is added (a look-ahead)."""
    base = REAL(rows, values, player, date, event, rnd)
    v = _frame(rows, values)
    v["order"] = rows["order"].to_numpy()
    nxt = v.sort_values("order", kind="mergesort").groupby("player_id")[values].shift(-1).fillna(0.0)
    return base + nxt.reindex(rows.index).to_numpy()


def leak_whole_period(rows, values, player="player_id", date="tournament_date", event="tournament_id",
                      rnd="round_order"):
    """Each player's total over the whole slice (future included)."""
    v = _frame(rows, values)
    return v.groupby("player_id")[values].transform("sum")


LEAKS = {"includes the match itself and its round": leak_including_the_match,
         "other matches of the same round (round robins)": leak_same_round_others,
         "other events of the same week": leak_same_week_other_events,
         "running total over the order (simultaneous matches earlier in the order)": leak_earlier_in_order,
         "the player's next match": leak_next_match,
         "the whole period's total": leak_whole_period}


class Recorder:
    def __init__(self):
        self.failed, self.passed = [], []

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            (self.failed if report.failed else self.passed).append(report.nodeid.split("::")[-1])


def run_tests(fn) -> dict:
    C.asof_sums = fn
    try:
        rec = Recorder()
        code = pytest.main([str(ROOT / "test" / "predictability_diagnostic" / "test_order_asof.py"), "-q", "-p",
                            "no:cacheprovider", "--no-header", "-o", "addopts="], plugins=[rec])
    finally:
        C.asof_sums = REAL
    return {"exit_code": int(code), "failed": rec.failed, "passed": len(rec.passed)}


def brute(rows: pd.DataFrame, idx: np.ndarray, col: str) -> np.ndarray:
    """The rule read row by row: the same player's matches of an earlier tournament date, or of the
    same event and date in an earlier round."""
    by_player = {p: g for p, g in rows.groupby("player_id")}
    out = []
    for i in idx:
        r = rows.loc[i]
        mine = by_player[r["player_id"]]
        seen = (mine["tournament_date"] < r["tournament_date"]) | (
            mine["tournament_date"].eq(r["tournament_date"]) & mine["tournament_id"].eq(r["tournament_id"])
            & (mine["round_order"] < r["round_order"]))
        out.append(mine.loc[seen, col].sum())
    return np.array(out, dtype=float)


def main() -> int:
    mp = C.load_match_players(["match_id", "player_id", "won"])
    season = mp[mp["tournament_date"].between("2024-01-01", "2024-12-31")].copy()
    season["won"] = season["won"].astype(float)
    m = C.load_matches(["match_id", "round"])
    season["round"] = season["match_id"].map(m.set_index("match_id")["round"])

    # the real helper against the rule, row by row, on the rows where a leak would show
    rr = season.index[season["round"].eq("RR")]
    events_per_week = season.groupby(["player_id", "tournament_date"])["tournament_id"].transform("nunique")
    two_events = season.index[events_per_week > 1]
    rest = season.index.difference(rr.union(two_events))
    rng = np.random.default_rng(0)
    sample = np.concatenate([rr, two_events, rng.choice(rest, 3000, replace=False)])
    fast = REAL(season, ["won"]).loc[sample, "won"].to_numpy()
    slow = brute(season, sample, "won")
    helper_vs_rule = {"rows_checked": int(len(sample)), "round_robin_rows": int(len(rr)),
                      "rows_of_players_with_two_events_in_a_week": int(len(two_events)),
                      "rows_differing": int((~np.isclose(fast, slow)).sum())}
    print("helper vs rule", helper_vs_rule)

    results = {"real helper": {
        "probe_20_cuts": C.leak_probe(season, lambda r: C.asof_sums(r, ["won"]), ["won"], n_cuts=20),
        "probe_200_cuts": C.leak_probe(season, lambda r: C.asof_sums(r, ["won"]), ["won"], n_cuts=200, seed=1),
        "tests": run_tests(REAL)}}
    print("real", results["real helper"])
    for name, fn in LEAKS.items():
        feature = (lambda f: (lambda r: f(r, ["won"])))(fn)
        values = feature(season)
        differs = int((~np.isclose(values.to_numpy(dtype=float), REAL(season, ["won"]).to_numpy())).any(axis=1).sum())
        results[name] = {"rows_where_the_leaky_value_differs_from_the_helper": differs,
                         "probe_20_cuts": C.leak_probe(season, feature, ["won"], n_cuts=20),
                         "probe_200_cuts": C.leak_probe(season, feature, ["won"], n_cuts=200, seed=1),
                         "tests": run_tests(fn)}
        print(name, {k: v for k, v in results[name].items()})
    A.write_json("leak.json", {"slice": "player rows of 2024 tournament weeks", "rows": int(len(season)),
                               "helper_vs_rule_row_by_row": helper_vs_rule, "results": results})
    return 0


if __name__ == "__main__":
    sys.exit(main())
