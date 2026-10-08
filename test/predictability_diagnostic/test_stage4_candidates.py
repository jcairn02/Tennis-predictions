"""The Stage 4 plan's coverage counts (stage4_candidates.py).

The plan computes nothing against results, but its counts follow the rules Stage 4's features will: the previous
match under the Brief's time rule (an earlier round of the same event first, never another event of the same week
or another match of the same round), the fatigue windows counted between event start dates, a deciding set read
from the score without asking who won, the point-by-point players linked within their own draw, and the number of
comparisons the scoring plan makes.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_candidates as S  # noqa: E402


def rows(recs):
    """Player-rows from (player, event, date, round) in any order, sorted as the table sorts them."""
    df = pd.DataFrame(recs, columns=["player_id", "tournament_id", "tournament_date", "round"])
    df["tournament_date"] = pd.to_datetime(df["tournament_date"])
    df["round_order"] = df["round"].map(C.ROUND_ORDER)
    df = df.sort_values(["tournament_date", "round_order", "tournament_id", "player_id"], kind="mergesort").reset_index(drop=True)
    df["order"] = np.arange(len(df))
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0].astype("int64")
    return df


def test_previous_row_follows_the_time_rule():
    h = rows([("x", "E1", "2024-01-01", "R32"), ("x", "E1", "2024-01-01", "R16"),
              ("x", "E2", "2024-01-08", "R32"), ("x", "E3", "2024-01-08", "R32"),     # two events in one week
              ("x", "E4", "2024-01-15", "RR"), ("x", "E4", "2024-01-15", "RR"),       # one round-robin stage
              ("x", "E4", "2024-01-15", "SF"), ("y", "E4", "2024-01-15", "SF")])
    prev = S.previous_row(h, np.ones(len(h), dtype=bool))
    at = {(r.tournament_id, r.round, r.Index): r.Index for r in h.itertuples()}
    idx = lambda ev, rnd: [i for (e, r, i) in at if e == ev and r == rnd and h.loc[i, "player_id"] == "x"]
    e1_r32, e1_r16 = idx("E1", "R32")[0], idx("E1", "R16")[0]
    assert prev[e1_r32] == -1
    assert prev[e1_r16] == e1_r32                                     # an earlier round of the same event
    assert prev[idx("E2", "R32")[0]] == e1_r16                        # not the other event of the same week
    assert prev[idx("E3", "R32")[0]] == e1_r16
    week2 = set(idx("E2", "R32") + idx("E3", "R32"))
    assert all(prev[i] in week2 for i in idx("E4", "RR"))             # never the other round-robin match
    assert prev[idx("E4", "SF")[0]] in set(idx("E4", "RR"))
    assert prev[h.index[h["player_id"].eq("y")][0]] == -1             # another player's history is not shared


def test_windows_count_between_event_start_dates():
    h = rows([("x", "E0", "2024-01-01", "R32"), ("x", "E1", "2024-01-08", "R32"), ("x", "E1", "2024-01-08", "R16"),
              ("x", "E2", "2024-01-15", "R32"), ("x", "E2", "2024-01-15", "R16"), ("x", "E3", "2024-01-15", "R32")])
    one = {"m": np.ones(len(h))}
    car = S.asof(h, one, h["pcode"].to_numpy())["m"]
    w7 = car - S.before(h, one, h["pcode"].to_numpy(), 7)["m"]
    w14 = car - S.before(h, one, h["pcode"].to_numpy(), 14)["m"]
    r16 = h.index[h["tournament_id"].eq("E2") & h["round"].eq("R16")][0]
    assert car[r16] == 4                                              # E0, E1 twice, E2's first round; not E3
    assert w7[r16] == 3                                               # E1 (7 days before) and E2's first round
    assert w14[r16] == 4                                              # and E0 (14 days before)
    e3 = h.index[h["tournament_id"].eq("E3")][0]
    assert w7[e3] == 2                                                # the same week's other event is not seen


def test_deciding_set_is_read_from_the_score_alone():
    sets = [(2, 1), (2, 0), (3, 2), (3, 1), (1, 2), (np.nan, np.nan)]
    mp = pd.DataFrame({"sets_won_n": [v for p in sets for v in p],
                       "sets_won_d": [s[0] + s[1] for s in sets for _ in (0, 1)]})
    got = S.deciding_set(mp).reshape(-1, 2)
    assert (got[:, 0] == got[:, 1]).all()                             # the same for both players
    assert got[:, 0].tolist() == [True, False, True, False, True, False]


def test_point_by_point_names_link_within_the_draw():
    draw = [("p1", ["rafael", "nadal"]), ("p2", ["karolina", "pliskova"]), ("p3", ["kristyna", "pliskova"]),
            ("p4", ["stan", "wawrinka"]), ("p5", ["alexander", "zverev"]), ("p6", ["mischa", "zverev"]),
            ("p7", ["alison", "riske", "amritraj"])]
    assert S.link_in_event("Rafael Nadal", draw) == "p1"
    assert S.link_in_event("R. Nadal", draw) == "p1"
    assert S.link_in_event("Ka. Pliskova", draw) == "p2"
    assert S.link_in_event("Kr. Pliskova", draw) == "p3"
    assert S.link_in_event("Pliskova", draw) is None                  # two candidates: no link
    assert S.link_in_event("Stanislas Wawrinka", draw) == "p4"
    assert S.link_in_event("A. Zverev", draw) == "p5"
    assert S.link_in_event("Alison Riske", draw) == "p7"
    assert S.link_in_event("", draw) is None


def test_level_groups_and_comparison_count():
    lv = pd.Series(["GS", "GS", "T250", "T500", "CH", "CH", "FIN"])
    q = pd.Series([False, True, True, False, False, True, False])
    assert S.level_group(lv, q).tolist() == ["GS", "GSQ", "TQ", "T500", "CH", "CHQ", "FIN"]
    cand = pd.DataFrame([{"id": "s", "group": "statistic", "forms": "career;52 weeks;decayed;surface;adjusted",
                          "tours": "atp;wta", "scores": "alone;elo;market"},
                         {"id": "b", "group": "single", "forms": "single", "tours": "atp", "scores": "elo;market"}])
    c = S.comparisons(cand)
    assert c["comparisons"] == 5 * 2 * 3 + 2
    assert c["rows_per_tour"] == {"atp": 6, "wta": 5}
    assert c["null_fits"] == c["comparisons"] * S.COPIES
