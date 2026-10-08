"""Stage 2: the iid point model (stage2_iid.py) and the anatomy of a win (stage2_anatomy.py).

The model is checked against a brute-force reading of the scoring rules, against itself with the serving
order reversed, and against a point-by-point simulation. The Grand Slams' deciding-set rules are checked
for coverage and for the lookups that matter. The analysis's identities (the points-edge split, the
break-point bookkeeping, the expected tiebreaks) are checked on hand-made matches. The tests on the
built tables are skipped until the stage has run.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_anatomy as A  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402

RNG = np.random.default_rng(11)
PA, PB = RNG.uniform(0.35, 0.9, 400), RNG.uniform(0.35, 0.9, 400)


# ------------------------------------------------------------------------------------------------
# Brute-force references, written from the rules without the closed forms

def game_brute(p: float) -> float:
    """Points to four, won by two, read as a walk over every score, 400 points deep (the chance of a game
    still going after that is below 1e-50)."""
    prob = {(0, 0): 1.0}
    won = 0.0
    for _ in range(400):
        nxt = {}
        for (i, j), r in prob.items():
            for ni, nj, pr in ((i + 1, j, p), (i, j + 1, 1 - p)):
                if ni >= 4 and ni - nj >= 2:
                    won += r * pr
                elif nj >= 4 and nj - ni >= 2:
                    continue
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0) + r * pr
        prob = nxt
    return won


def set_brute(pa: float, pb: float, tb_at, tb_points: int, a_first: bool = True) -> float:
    """A set played game by game with no closure, 3,000 games deep: an advantage set simply goes on (the
    chance it is still going after that is below 1e-30 for these serve rates)."""
    ga, gb = M.game(pa), M.game(pb)
    prob = {(0, 0): 1.0}
    won = 0.0
    for _ in range(3000):
        nxt = {}
        for (i, j), r in prob.items():
            if tb_at is not None and i == tb_at and j == tb_at:
                won += r * float(M.tiebreak(pa, pb, tb_points, a_first=a_first))
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = ga if a_serves else 1 - gb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= 6 and abs(ni - nj) >= 2:
                    won += r * pr if ni > nj else 0.0
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0) + r * pr
        prob = nxt
    return won


# ------------------------------------------------------------------------------------------------
# The iid model

def test_game_matches_the_brute_force_walk_and_a_known_value():
    for p in (0.3, 0.5, 0.6, 0.72, 0.9):
        assert float(M.game(p)) == pytest.approx(game_brute(p), abs=1e-12)
    assert float(M.game(0.6)) == pytest.approx(0.735729, abs=1e-6)       # the textbook value
    assert float(M.game(0.5)) == pytest.approx(0.5)


@pytest.mark.parametrize("rule", list(M.SET_RULES))
def test_set_matches_the_brute_force_walk(rule):
    tb_at, tb_points = M.SET_RULES[rule]
    for pa, pb in ((0.62, 0.58), (0.7, 0.71), (0.55, 0.66), (0.8, 0.79)):
        assert float(M.set_win(pa, pb, rule)) == pytest.approx(set_brute(pa, pb, tb_at, tb_points), abs=1e-9)


@pytest.mark.parametrize("target", [7, 10])
def test_who_serves_first_does_not_change_a_tiebreak(target):
    assert np.allclose(M.tiebreak(PA, PB, target, True), M.tiebreak(PA, PB, target, False), atol=1e-12)


@pytest.mark.parametrize("rule", list(M.SET_RULES))
def test_who_serves_first_does_not_change_a_set_so_sets_are_independent(rule):
    assert np.allclose(M.set_win(PA, PB, rule, True), M.set_win(PA, PB, rule, False), atol=1e-12)


@pytest.mark.parametrize("rule", list(M.SET_RULES))
def test_symmetry(rule):
    assert np.allclose(M.set_win(PA, PB, rule) + M.set_win(PB, PA, rule), 1, atol=1e-12)
    assert np.allclose(M.match_win(PA, PB, 5, rule) + M.match_win(PB, PA, 5, rule), 1, atol=1e-12)
    assert np.allclose(M.match_win(PA, PA, 3, rule), 0.5, atol=1e-12)
    assert np.allclose(M.tiebreak(PA, PA, 10), 0.5, atol=1e-12)


def test_match_grows_with_the_serve_rate_and_with_length():
    p = np.linspace(0.5, 0.8, 31)
    m3, m5 = M.match_win(p, 0.6, 3), M.match_win(p, 0.6, 5)
    assert np.all(np.diff(m3) > 0) and np.all(np.diff(m5) > 0)
    better = p > 0.6
    assert np.all(m5[better] > m3[better])                     # a longer match favours the better server


def test_best_of_three_from_set_probabilities():
    s = M.set_win(PA, PB)
    f = M.set_win(PA, PB, "ADV")
    assert np.allclose(M.match_win(PA, PB, 3, "ADV"), s * s + 2 * s * (1 - s) * f, atol=1e-12)


def test_match_win_by_equals_row_by_row():
    bo = np.where(RNG.random(len(PA)) < 0.5, 3, 5)
    rules = RNG.choice(list(M.SET_RULES), len(PA))
    got = M.match_win_by(PA, PB, bo, rules)
    want = np.array([float(M.match_win(a, b, o, r)) for a, b, o, r in zip(PA, PB, bo, rules)])
    assert np.allclose(got, want, atol=1e-12)


@pytest.mark.parametrize("bo,rule,pa,pb", [(3, "TB7@6", 0.64, 0.6), (5, "ADV", 0.66, 0.63), (5, "TB7@12", 0.7, 0.69),
                                           (3, "TB10@6", 0.57, 0.6)])
def test_simulation_agrees_with_the_exact_chance(bo, rule, pa, pb):
    n = 60000
    sim = M.simulate(np.full(n, pa), np.full(n, pb), bo, rule, seed=5)
    p = float(M.match_win(pa, pb, bo, rule))
    assert abs(sim["a_won"].mean() - p) < 4 * np.sqrt(p * (1 - p) / n)
    rate = sim["won"].sum(axis=0) / sim["served"].sum(axis=0)
    assert rate == pytest.approx([pa, pb], abs=0.003)


def test_simulated_scores_obey_the_rules():
    """Every simulated match ends with a winner who served and received; best of five needs 3 sets, which
    takes at least 18 games, so at least 72 points."""
    sim = M.simulate(np.full(2000, 0.62), np.full(2000, 0.62), 5, "TB10@6", seed=2)
    pts = sim["served"].sum(axis=1)
    assert (sim["served"] > 0).all() and pts.min() >= 72


def test_simulated_break_points_and_tiebreaks_are_counted_by_the_rules():
    """A never wins a point on serve and B always does: 6-0 6-0, one break point per A service game (at 0-40),
    none saved, none for B, no tiebreak. Two equal big servers: nearly every set reaches a tiebreak."""
    sim = M.simulate(np.zeros(50), np.ones(50), 3, "TB7@6", seed=1)
    assert (~sim["a_won"]).all()
    assert (sim["bp_faced"][:, 0] == 6).all() and (sim["bp_saved"][:, 0] == 0).all() and (sim["bp_faced"][:, 1] == 0).all()
    assert (sim["tiebreaks"] == 0).all() and not sim["deciding_tb"].any()
    sim = M.simulate(np.full(400, 0.97), np.full(400, 0.97), 3, "TB7@6", seed=1)
    assert sim["tiebreaks"].mean() > 1.9 and (sim["tiebreaks"][sim["deciding_tb"]] >= 1).all()
    assert sim["deciding_tb"].mean() > 0.4


def test_break_points_saved_match_the_true_rate_but_not_the_measured_one():
    """Under the iid model a break point is won by the server with the true serve rate, so saves average the
    break points faced times that rate. Against the rate measured in the same match they look too many: a player
    who faces many break points has usually had an unlucky day on serve, which lowers the measured rate."""
    n = 40000
    pa, pb = RNG.uniform(0.55, 0.72, n), RNG.uniform(0.55, 0.72, n)
    sim = M.simulate(pa, pb, 3, "TB7@6", seed=9)
    faced, saved = sim["bp_faced"][:, 0], sim["bp_saved"][:, 0]
    measured = sim["won"][:, 0] / sim["served"][:, 0]
    true_gap = saved - faced * pa
    se = true_gap.std() / np.sqrt(n)
    assert abs(true_gap.mean()) < 4 * se
    assert (saved - faced * measured).mean() > 10 * se


def test_denoised_rates_shrink_toward_the_mean_and_keep_the_true_spread():
    rng = np.random.default_rng(3)
    n = 20000
    true = rng.normal(0.62, 0.07, (n, 2)).clip(0.3, 0.9)
    pts = rng.integers(50, 120, (n, 2))
    measured = rng.binomial(pts, true) / pts
    t = pd.DataFrame({"pa": measured[:, 0], "pb": measured[:, 1], "svpt_a": pts[:, 0], "svpt_b": pts[:, 1],
                      "tour": "atp", "surface": "Hard"})
    a, b, prior = A.denoised_rates(t, np.random.default_rng(4))
    drawn = np.concatenate([a, b])
    assert drawn.std() == pytest.approx(true.std(), rel=0.05)
    assert drawn.std() < measured.std()
    assert prior[0]["true_share_of_var"] < 1


def test_tiebreak_target():
    assert M.tiebreak_target(["TB7@6", "TB10@6", "TB7@12", "ADV"]).tolist() == [7, 10, 7, 7]


# ------------------------------------------------------------------------------------------------
# The Grand Slams' deciding-set rules

def test_the_rules_cover_every_slam_draw_and_year_once():
    r = M.slam_rules()
    for (slam, draw), g in r.groupby(["slam", "draw"]):
        years = sorted(y for row in g.itertuples() for y in range(row.first_year, row.last_year + 1))
        assert years == list(range(2010, 2027)), (slam, draw)
    assert set(r["slam"]) == {"AO", "RG", "WIM", "USO"} and set(r["draw"]) == {"main", "qualifying"}


@pytest.mark.parametrize("name,year,qual,rule", [
    ("Australian Open", 2018, False, "ADV"), ("Australian Open", 2019, False, "TB10@6"),
    ("Australian Open", 2018, True, "TB7@6"), ("Doha Aus Open Qualies", 2021, True, "TB10@6"),
    ("Roland Garros", 2021, False, "ADV"), ("Roland Garros", 2022, False, "TB10@6"),
    ("Roland Garros", 2016, True, "ADV"), ("Roland Garros", 2017, True, "TB7@6"),
    ("Wimbledon", 2018, False, "ADV"), ("Wimbledon", 2019, False, "TB7@12"), ("Wimbledon", 2021, True, "TB7@12"),
    ("Wimbledon", 2022, False, "TB10@6"), ("US Open", 2021, False, "TB7@6"), ("Us Open", 2023, True, "TB10@6")])
def test_rule_lookups(name, year, qual, rule):
    got = M.deciding_set_rule(pd.Series(["GS"]), pd.Series([name]), pd.Series([year]), pd.Series([qual]))
    assert got.iloc[0] == rule


def test_non_slams_play_a_tiebreak_at_six_all_and_unknown_slams_fail():
    got = M.deciding_set_rule(pd.Series(["T1000", "CH"]), pd.Series(["Miami", "Biella"]), pd.Series([2019, 2021]),
                              pd.Series([False, True]))
    assert got.tolist() == ["TB7@6", "TB7@6"]
    assert M.slam_of("Doha Aus Open Qualies") == "AO" and M.slam_of("Us Open") == "USO"
    with pytest.raises(ValueError):
        M.deciding_set_rule(pd.Series(["GS"]), pd.Series(["Somewhere Open"]), pd.Series([2020]), pd.Series([False]))


# ------------------------------------------------------------------------------------------------
# The analysis's identities, on hand-made matches

def hand_made(n=500, seed=4) -> pd.DataFrame:
    """Valid random box scores: counts consistent with each other."""
    rng = np.random.default_rng(seed)
    out = {}
    for s in ("a", "b"):
        svpt = rng.integers(40, 160, n)
        first_in = (svpt * rng.uniform(0.5, 0.75, n)).astype(int)
        second = svpt - first_in
        df = (second * rng.uniform(0, 0.2, n)).astype(int)
        ace = (first_in * rng.uniform(0, 0.2, n)).astype(int)
        first_won = ace + ((first_in - ace) * rng.uniform(0.5, 0.8, n)).astype(int)
        second_won = ((second - df) * rng.uniform(0.4, 0.7, n)).astype(int)
        faced = rng.integers(0, 15, n)
        out.update({f"svpt_{s}": svpt, f"first_in_{s}": first_in, f"df_{s}": df, f"ace_{s}": ace,
                    f"first_won_{s}": first_won, f"second_won_{s}": second_won, f"bp_faced_{s}": faced,
                    f"bp_saved_{s}": (faced * rng.uniform(0, 1, n)).astype(int)})
    t = pd.DataFrame(out).astype("float64")
    for s, o in (("a", "b"), ("b", "a")):
        t[f"spw_n_{s}"] = t[f"first_won_{s}"] + t[f"second_won_{s}"]
        t[f"spw_d_{s}"] = t[f"svpt_{s}"]
    t["tpw_n_a"] = t["spw_n_a"] + t["svpt_b"] - t["spw_n_b"]
    t["tpw_d_a"] = t["svpt_a"] + t["svpt_b"]
    t["best_of"] = np.where(rng.random(n) < 0.3, 5, 3)
    t["rule"] = rng.choice(["TB7@6", "TB10@6", "TB7@12", "ADV"], n)
    t["tb_won_d_a"] = rng.integers(0, 3, n).astype(float)
    t["tb_won_n_a"] = np.minimum(t["tb_won_d_a"], rng.integers(0, 3, n))
    t["deciding_tb"] = (t["tb_won_d_a"] > 0) & (rng.random(n) < 0.3)
    t["a_won"] = rng.random(n) < 0.5
    return t


def test_the_points_edge_splits_exactly():
    t = A.add_components(A.add_model_columns(hand_made()))
    parts = [f"c_{k}" for k in A.COMPONENT_NAMES]
    assert np.allclose(t[parts].sum(axis=1), t["edge_a"], atol=1e-12)
    assert (t["tpw_n_a"] / t["tpw_d_a"]).sub(t["tpw_a"]).abs().max() < 1e-15


def test_break_point_bookkeeping():
    t = A.add_model_columns(hand_made())
    conv_over_a = (t["bp_faced_b"] - t["bp_saved_b"]) - t["bp_faced_b"] * (1 - t["pb"])
    assert np.allclose(conv_over_a, -t["bp_save_over_b"], atol=1e-12)
    assert np.allclose(t["bp_net_a"], t["bp_save_over_a"] + conv_over_a, atol=1e-12)


def test_expected_tiebreaks_use_the_deciding_sets_length():
    t = A.add_model_columns(hand_made())
    p7, p10 = M.tiebreak(t["pa"], t["pb"], 7), M.tiebreak(t["pa"], t["pb"], 10)
    ten = t["deciding_tb"] & t["rule"].eq("TB10@6")
    want = t["tb_won_d_a"] * p7 + np.where(ten, p10 - p7, 0.0)
    assert np.allclose(t["tb_exp_a"], want, atol=1e-12)


def test_shapley_shares_add_to_r2_and_equal_each_r2_when_inputs_are_independent():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20000, 3))
    y = X @ np.array([1.0, 0.5, 0.0]) + rng.normal(size=20000)
    r2, shap = A.shapley_r2(X, y)
    assert sum(shap) == pytest.approx(r2, abs=1e-12)
    singles = [A.shapley_r2(X[:, [j]], y)[0] for j in range(3)]
    assert shap == pytest.approx(singles, abs=0.01)


def test_oof_logit_has_no_intercept_and_is_symmetric():
    rng = np.random.default_rng(1)
    x = rng.normal(size=4000)
    y = rng.random(4000) < 1 / (1 + np.exp(-1.5 * x))
    p, coef = A.oof_logit(x, y)
    assert coef[0] == pytest.approx(1.5, abs=0.15)
    p0, _ = A.oof_logit(np.zeros(4000), y)
    assert np.allclose(p0, 0.5)


# ------------------------------------------------------------------------------------------------
# The point-by-point part (stage2_pbp.py)

from src.eda.predictability_diagnostic import stage2_pbp as P  # noqa: E402


def play(points, need=2, rule="TB7@6", state=P.START):
    """Apply (server is player 1, player 1 won) pairs; return the last advance() result."""
    out = None
    for s1, w1 in points:
        out = P.advance(state, s1, w1, need, rule)
        state = out[0]
    return out


def test_advance_counts_games_sets_and_who_serves():
    state, shown, over, next1 = play([(True, True)] * 4)                       # a love hold
    assert shown == (1, 0) and state[:6] == (0, 0, 1, 0, 0, 0) and next1 is False and not over
    state, shown, over, next1 = play([(True, False)] * 3)                      # 0-40: still player 1's game
    assert state[4:6] == (0, 3) and next1 is True
    # twelve holds bring 6-6 and a tiebreak, its first point served by the next game's server (player 1)
    holds = [(g % 2 == 0, g % 2 == 0) for g in range(12) for _ in range(4)]
    state, shown, over, next1 = play(holds)
    assert state[2:4] == (6, 6) and state[6] is True and next1 is True and state[7] is True
    # player 1 wins the tiebreak 7-0 on the 1-2-2 rotation: the set is player 1's and player 2 serves next
    tb = [(P.M._tb_first_serves(k), True) for k in range(7)]
    state, shown, over, next1 = play(holds + tb)
    assert shown == (7, 6) and state[:4] == (1, 0, 0, 0) and state[6] is False and next1 is False
    # two sets to love end a best-of-three match
    love_set = [(g % 2 == 0, True) for g in range(6) for _ in range(4)]
    out = play(love_set + love_set)
    assert out[2] is True and out[0][:2] == (2, 0)


def test_the_chance_from_the_start_is_the_match_chance():
    for p1, p2, bo, rule in ((0.64, 0.6, 5, "ADV"), (0.58, 0.61, 3, "TB10@6"), (0.7, 0.69, 5, "TB7@12"), (0.62, 0.62, 3, "TB7@6")):
        ch = P.Chances(p1, p2, bo, rule)
        for next1 in (True, False):
            assert ch.value(P.START, next1) == pytest.approx(float(M.match_win(p1, p2, bo, rule)), abs=1e-12)


def test_the_chance_is_consistent_point_by_point():
    """Before any point, the chance equals the server's chance-weighted average of the chances after it; and a
    point's importance is never negative. Checked along random matches under every rule."""
    rng = np.random.default_rng(8)
    for rule, bo in (("ADV", 5), ("TB7@12", 5), ("TB10@6", 3), ("TB7@6", 3)):
        p1, p2 = 0.66, 0.61
        ch = P.Chances(p1, p2, bo, rule)
        need = (bo + 1) // 2
        for _ in range(20):
            state, next1, over = P.START, bool(rng.random() < 0.5), False
            while not over:
                s = p1 if next1 else 1 - p2                       # player 1 wins this point
                up, down = P.advance(state, next1, True, need, rule), P.advance(state, next1, False, need, rule)
                before = ch.value(state, next1)
                after = s * ch.value(up[0], up[3]) + (1 - s) * ch.value(down[0], down[3])
                assert before == pytest.approx(after, abs=1e-12)
                assert ch.importance(state, next1) >= -1e-15
                won = rng.random() < s
                state, _, over, next1 = up if won else down


def test_replay_keeps_a_clean_match_and_drops_a_broken_one():
    """A 6-0 6-0 written as the files write it is kept; the same with one point's winner flipped is not."""
    rows, state = [], P.START
    for g in range(12):                                   # player 1 wins every point; the serve alternates by game
        srv1 = g % 2 == 0
        for _ in range(4):
            new, shown, over, nxt = P.advance(state, srv1, True, 2, "TB7@6")
            s1, s2 = P.score_tokens(new[4], new[5], False) if new[4] + new[5] else ("0", "0")
            rows.append({"match_id": "2015-usopen-2101", "_row": len(rows), "PointWinner": 1, "PointServer": 1 if srv1 else 2,
                         "SetNo": state[0] + state[1] + 1, "P1GamesWon": shown[0], "P2GamesWon": shown[1],
                         "P1Score": s1, "P2Score": s2, "player1": "A", "player2": "B", "year": 2015,
                         "tournament_name": "US Open", "tour": "wta"})
            state = new
    assert over and rows[-1]["P1GamesWon"] == 6 and rows[-1]["SetNo"] == 2
    good = pd.DataFrame(rows)
    pts, status = P.replay_all(good)
    assert status["kept"].all() and len(pts) == 48 and bool(status["p1_won"].iat[0]) is True
    bad = good.copy()
    bad.loc[5, "PointWinner"] = 2                         # one point credited to the other player
    _, status = P.replay_all(bad)
    assert not status["kept"].any()


# ------------------------------------------------------------------------------------------------
# The built tables

BUILT = A.TABLE.exists() and A.RESULTS.exists()


@pytest.mark.skipif(not BUILT, reason="Stage 2 has not been run")
def test_built_table_identities():
    t = pd.read_parquet(A.TABLE)
    parts = [f"c_{k}" for k in A.COMPONENT_NAMES]
    ok = t[parts].notna().all(axis=1)
    assert np.allclose(t.loc[ok, parts].sum(axis=1), t.loc[ok, "edge_a"], atol=1e-12)
    assert t["p_floor"].between(0, 1).all() and t["match_id"].is_unique
    assert set(t["best_of"]) <= {3, 5} and (t.loc[t["tour"].eq("wta"), "year"] >= C.WTA_BOX_FROM).all()
    assert (t["n_tb"] >= t["deciding_tb"].astype(int)).all()


@pytest.mark.skipif(not BUILT, reason="Stage 2 has not been run")
def test_built_results_are_consistent():
    r = json.loads(A.RESULTS.read_text(encoding="utf-8"))
    t = pd.read_parquet(A.TABLE)
    last = r["population"]["steps"][-1]
    assert last["atp"] == int(t["tour"].eq("atp").sum()) and last["wta"] == int(t["tour"].eq("wta").sum())
    assert not r["rules_check"]["inconsistent"]
    imp = pd.read_csv(A.IMPACT)
    for tour in C.TOURS:
        assert set(C.RATES) <= set(imp.loc[imp["tour"].eq(tour) & imp["best_of"].astype(str).eq("all"), "rate"])
