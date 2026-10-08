"""The study's chronological order and its as-of helper (src/eda/predictability_diagnostic/common.py).

Synthetic tests prove the rule the Brief sets (a feature for a match uses only earlier events and
earlier rounds of the same event); the tests on the built tables repeat the proof on the real order.
A deliberately leaky feature shows the leakage probe catches what it should.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

BUILT = C.MATCHES.exists() and C.MATCH_PLAYERS.exists()


def matches(rows):
    """Synthetic match rows: (match_id, tournament_id, date, round, match_num)."""
    m = pd.DataFrame(rows, columns=["match_id", "tournament_id", "tournament_date", "round", "match_num"])
    m["tournament_date"] = pd.to_datetime(m["tournament_date"])
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    return m


def player_rows(m, players):
    """Two rows per match from {match_id: (winner, loser)}, with the order of chrono_sort."""
    m = C.chrono_sort(m).reset_index(drop=True)
    m["order"] = np.arange(len(m))
    rows = []
    for r in m.itertuples():
        w, l = players[r.match_id]
        for p, won in ((w, 1), (l, 0)):
            rows.append({"match_id": r.match_id, "player_id": p, "won": won, "one": 1, "order": r.order,
                         "tournament_date": r.tournament_date, "tournament_id": r.tournament_id,
                         "round_order": r.round_order})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The order

def test_earlier_rounds_and_qualifying_come_first():
    m = matches([("f", "E1", "2024-01-08", "F", "31"), ("q2", "E1", "2024-01-08", "Q2", "2"),
                 ("r32", "E1", "2024-01-08", "R32", "1"), ("sf", "E1", "2024-01-08", "SF", "29"),
                 ("q1", "E1", "2024-01-08", "Q1", "1"), ("qf", "E1", "2024-01-08", "QF", "25"),
                 ("r16", "E1", "2024-01-08", "R16", "17"), ("prev", "E0", "2024-01-01", "F", "31")])
    order = list(C.chrono_sort(m)["match_id"])
    assert order == ["prev", "q1", "q2", "r32", "r16", "qf", "sf", "f"]


def test_round_robin_before_knockout_and_bronze_with_final():
    assert C.ROUND_ORDER["Q3"] < C.ROUND_ORDER["RR"] < C.ROUND_ORDER["R128"]
    assert C.ROUND_ORDER["SF"] < C.ROUND_ORDER["BR"] == C.ROUND_ORDER["F"]


# ------------------------------------------------------------------------------------------------
# The as-of helper on a hand-made history

def hand_made():
    m = matches([
        ("a1", "E1", "2024-01-08", "R32", "1"),    # week 1: P wins R32, loses R16
        ("a2", "E1", "2024-01-08", "R16", "9"),
        ("b1", "E2", "2024-01-15", "Q1", "1"),     # week 2: P qualifies and plays the main draw
        ("b2", "E2", "2024-01-15", "Q2", "2"),
        ("b3", "E2", "2024-01-15", "R32", "1"),
        ("c1", "E3", "2024-01-15", "R32", "1"),    # week 2, another event: Q plays R32 (never visible to E2)
        ("d1", "F", "2024-01-22", "RR", "1"),      # week 3: a round robin (three matches) and a semi-final
        ("d2", "F", "2024-01-22", "RR", "2"),
        ("d3", "F", "2024-01-22", "RR", "3"),
        ("d4", "F", "2024-01-22", "SF", "4"),
    ])
    players = {"a1": ("P", "X"), "a2": ("X", "P"), "b1": ("P", "Y"), "b2": ("P", "Z"), "b3": ("Q", "P"),
               "c1": ("P", "Q"), "d1": ("P", "Q"), "d2": ("Q", "P"), "d3": ("P", "X"), "d4": ("P", "Y")}
    return player_rows(m, players)


def test_asof_counts_only_earlier_events_and_earlier_rounds():
    rows = hand_made()
    got = C.asof_sums(rows, ["one", "won"])
    p = rows.assign(n=got["one"], w=got["won"])
    p = p[p["player_id"].eq("P")].set_index("match_id")
    expected = {  # matches before, wins before, as the Brief allows
        "a1": (0, 0), "a2": (1, 1),                 # R16 sees the same event's R32
        "b1": (2, 1), "b2": (3, 2), "b3": (4, 3),   # qualifying rounds come before the main draw
        "c1": (2, 1),                               # another event of the same week sees only week 1
        "d1": (6, 4), "d2": (6, 4), "d3": (6, 4),   # round-robin matches never see each other
        "d4": (9, 6),                               # the semi-final sees the whole round robin
    }
    for mid, (n, w) in expected.items():
        assert (p.loc[mid, "n"], p.loc[mid, "w"]) == (n, w), mid


def test_asof_never_counts_the_match_itself():
    rows = hand_made()
    got = C.asof_sums(rows, ["one"])
    first = rows.groupby("player_id")["order"].transform("min") == rows["order"]
    assert (got.loc[first, "one"] == 0).all()


# ------------------------------------------------------------------------------------------------
# Random histories: the fast helper against the definition, and the leakage probe

def random_history(seed=1, weeks=30, players=40):
    rng = np.random.default_rng(seed)
    rows, k = [], 0
    for wk in range(weeks):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=wk)
        pool = list(rng.permutation(players))
        for ev in range(2):                     # two events a week, disjoint fields
            field = pool[ev * 16:(ev + 1) * 16]
            rounds = ["R16", "QF", "SF", "F"] if ev == 0 else ["RR", "RR", "SF", "F"]
            alive = field
            for rnd in rounds:
                nxt = []
                for i in range(0, len(alive) - 1, 2):
                    a, b = alive[i], alive[i + 1]
                    w, l = (a, b) if rng.random() < 0.5 else (b, a)
                    rows.append((f"m{k}", f"E{wk}-{ev}", date, rnd, str(k), f"p{w}", f"p{l}"))
                    nxt.append(w)
                    k += 1
                alive = nxt if rnd != "RR" else alive[: max(2, len(alive) // 2)]
    m = pd.DataFrame(rows, columns=["match_id", "tournament_id", "tournament_date", "round", "match_num", "w", "l"])
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    return player_rows(m.drop(columns=["w", "l"]), {r.match_id: (r.w, r.l) for r in m.itertuples()})


def brute_force(rows, col):
    """The definition, row by row: the same player's matches of an earlier date, or of the same event
    and date in an earlier round."""
    out = []
    for r in rows.itertuples():
        mine = rows[rows["player_id"].eq(r.player_id)]
        seen = (mine["tournament_date"] < r.tournament_date) | (
            mine["tournament_date"].eq(r.tournament_date) & mine["tournament_id"].eq(r.tournament_id)
            & (mine["round_order"] < r.round_order))
        out.append(mine.loc[seen, col].sum())
    return np.array(out, dtype=float)


def test_asof_matches_the_definition():
    rows = random_history()
    sample = rows.sample(300, random_state=0)
    fast = C.asof_sums(rows, ["won"]).loc[sample.index, "won"].to_numpy()
    slow = brute_force(rows, "won")[rows.index.get_indexer(sample.index)]
    assert np.array_equal(fast, slow)


def leaky_including_self(rows):
    """Deliberately wrong: a running total that includes the match being predicted."""
    r = rows.sort_values(["order", "player_id"])
    return r.groupby("player_id")[["won"]].cumsum().reindex(rows.index)


def leaky_season_total(rows):
    """Deliberately wrong: each player's total over the whole period, future included."""
    return rows.groupby("player_id")[["won"]].transform("sum")


def test_leak_probe_passes_the_asof_helper():
    rows = random_history()
    res = C.leak_probe(rows, lambda r: C.asof_sums(r, ["won"]), ["won"], n_cuts=15)
    assert res["cuts"] == 15
    assert res["changed_before_cut"] == 0 and res["changed_at_cut"] == 0


def test_leak_probe_catches_a_feature_that_uses_the_match_itself():
    rows = random_history()
    res = C.leak_probe(rows, leaky_including_self, ["won"], n_cuts=15)
    assert res["changed_at_cut"] > 0


def test_leak_probe_catches_a_feature_that_looks_ahead():
    rows = random_history()
    res = C.leak_probe(rows, leaky_season_total, ["won"], n_cuts=15)
    assert res["changed_before_cut"] > 0


# ------------------------------------------------------------------------------------------------
# The built tables (skipped until stage0_build.py has run)

@pytest.mark.skipif(not BUILT, reason="stage0 tables not built")
def test_built_order_puts_earlier_rounds_of_every_event_first():
    m = C.load_matches(["match_id", "tour", "tournament_id", "tournament_date", "round_order", "qualifying",
                        "order", "match_num"])
    g = m.groupby(["tour", "tournament_id", "tournament_date", "round_order"])["order"].agg(["min", "max"]).reset_index()
    g = g.sort_values(["tour", "tournament_id", "tournament_date", "round_order"])
    nxt_min = g.groupby(["tour", "tournament_id", "tournament_date"])["min"].shift(-1)
    assert (g["max"] < nxt_min).where(nxt_min.notna(), True).all()
    # qualifying before the main draw of the same event
    q = m.groupby(["tour", "tournament_id", "qualifying"])["order"].agg(["min", "max"]).unstack("qualifying").dropna()
    assert (q[("max", True)] < q[("min", False)]).all()
    # one position per match
    assert m["order"].is_unique and m["match_id"].is_unique


@pytest.mark.skipif(not BUILT, reason="stage0 tables not built")
def test_built_asof_never_uses_the_match_itself_or_later():
    mp = C.load_match_players(["match_id", "player_id", "won"])
    season = mp[mp["tournament_date"].between("2023-01-01", "2023-06-30")].copy()
    season["won"] = season["won"].astype(float)
    ok = C.leak_probe(season, lambda r: C.asof_sums(r, ["won"]), ["won"], n_cuts=8)
    assert ok["changed_before_cut"] == 0 and ok["changed_at_cut"] == 0
    bad = C.leak_probe(season, leaky_including_self, ["won"], n_cuts=8)
    assert bad["changed_at_cut"] > 0


@pytest.mark.skipif(not BUILT, reason="stage0 tables not built")
def test_built_tables_hold_two_rows_per_match_and_balanced_sides():
    m = C.load_matches(["match_id", "a_won", "player_a_id", "player_b_id"])
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "side", "won"])
    assert len(mp) == 2 * len(m)
    per = mp.groupby("match_id").agg(sides=("side", lambda s: "".join(sorted(s))), wins=("won", "sum"))
    assert (per["sides"] == "AB").all() and (per["wins"] == 1).all()
    a = mp[mp["side"].eq("A")].set_index("match_id")
    assert (a.loc[m["match_id"], "player_id"].to_numpy() == m["player_a_id"].to_numpy()).all()
    assert (a.loc[m["match_id"], "won"].to_numpy() == m["a_won"].to_numpy()).all()
    share = m["a_won"].mean()
    se = (0.25 / len(m)) ** 0.5
    assert abs(share - 0.5) < 4 * se
