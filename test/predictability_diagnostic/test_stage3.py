"""Stage 3: the serve and return ratings (stage3_ratings.py) and the trait measures (stage3_traits.py).

The rating pass is proven as Stage 1's Elo was: it equals a plain match-by-match pass where no two matches
are simultaneous; it keeps the Brief's time rule on a hand-made history and against a brute-force reading of
the rule; a probe cut by date, event and round passes it and catches a match-by-match pass. On histories
simulated from the model, the ratings recover the true serve and return strengths.

The trait measures are checked on simulated players with known true rates: the split-half reliability
follows the Spearman-Brown curve, the shrinkage constants are recovered (and the binomial-only constant is
shown too small when matches vary beyond chance), the carry-over ceiling, the look-back sums (career, last
52 weeks, decayed) against a row-by-row reading of the rule, and the log loss per opportunity. The tests on
the built tables are skipped until the stage has run.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage3_ratings as SR  # noqa: E402
from src.eda.predictability_diagnostic import stage3_traits as T  # noqa: E402

K = {"var_serve": 0.04, "var_return": 0.02, "drift": 1e-4}
MU = 0.5


# ------------------------------------------------------------------------------------------------
# Synthetic histories for the rating pass

def history(rows, seed=0):
    """Matches from (match_id, event, date, round, player A, player B[, status]) in any order, sorted as the
    table sorts them, with a box score drawn at random (A and B each serve 60-90 points)."""
    rng = np.random.default_rng(seed)
    recs = []
    for i, r in enumerate(rows):
        mid, ev, date, rnd, a, b = r[:6]
        status = r[6] if len(r) > 6 else "completed"
        n_a, n_b = int(rng.integers(60, 91)), int(rng.integers(60, 91))
        recs.append({"match_id": mid, "tournament_id": ev, "tournament_date": pd.Timestamp(date), "round": rnd,
                     "match_num": str(i), "player_a_id": a, "player_b_id": b, "status": status,
                     "n_a": float(n_a), "w_a": float(rng.binomial(n_a, 0.62)), "n_b": float(n_b),
                     "w_b": float(rng.binomial(n_b, 0.62))})
    m = pd.DataFrame(recs)
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    m = C.chrono_sort(m).reset_index(drop=True)
    m["updates"] = m["status"].eq("completed")
    return m


def run(m, k=K):
    return SR.run(SR.arrays(m, np.full(len(m), MU)), k)


def random_history(seed=3, weeks=20, players=36, overlap=True):
    """Weekly events: a 16-player knockout, a round robin of four with a final, and (``overlap``) a second
    small knockout the same week that shares players with the first."""
    rng = np.random.default_rng(seed)
    rows, k = [], 0
    for wk in range(weeks):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=int(wk + (wk // 5) * 3))   # gaps: drift has work
        pool = [f"p{x}" for x in rng.permutation(players)]
        ko, rr = pool[:16], pool[16:20]
        alive = ko
        for rnd in ("R16", "QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                rows.append((f"m{k}", f"K{wk}", date, rnd, alive[i], alive[i + 1],
                             "retired" if rng.random() < 0.05 else "completed"))
                nxt.append(alive[i] if rng.random() < 0.5 else alive[i + 1])
                k += 1
            alive = nxt
        for i in range(4):
            for j in range(i + 1, 4):
                rows.append((f"m{k}", f"R{wk}", date, "RR", rr[i], rr[j]))
                k += 1
        rows.append((f"m{k}", f"R{wk}", date, "F", rr[0], rr[1]))
        k += 1
        if overlap:
            field = list(rng.choice(ko, size=4, replace=False))
            for i in (0, 2):
                rows.append((f"m{k}", f"X{wk}", date, "R32", field[i], field[i + 1]))
                k += 1
    return history(rows, seed=seed)


def sequential(m, k=K):
    """A plain pass for comparison and for the probe to catch: match by match in the table's order, every
    update applied at once (so a round robin, or another event of the week, sees the earlier matches)."""
    S, R, VS, VR, NS, NR, LW = {}, {}, {}, {}, {}, {}, {}
    out = np.zeros((len(m), 12))
    weeks = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    for i, r in enumerate(m.itertuples(index=False)):
        wk = weeks[i]
        for p in (r.player_a_id, r.player_b_id):
            if p not in S:
                S[p], R[p], VS[p], VR[p], NS[p], NR[p], LW[p] = 0.0, 0.0, k["var_serve"], k["var_return"], 0.0, 0.0, wk
            elif LW[p] != wk:
                grow = k["drift"] * (wk - LW[p]) / 7.0
                VS[p], VR[p], LW[p] = min(VS[p] + grow, k["var_serve"]), min(VR[p] + grow, k["var_return"]), wk
        a, b = r.player_a_id, r.player_b_id
        out[i] = [S[a], S[b], R[a], R[b], VS[a], VS[b], VR[a], VR[b], NS[a], NS[b], NR[a], NR[b]]
        if r.updates:
            pre = (S[a], S[b], R[a], R[b], VS[a], VS[b], VR[a], VR[b])
            for srv, ret, n, w, s, vs, rr, vr in ((a, b, r.n_a, r.w_a, pre[0], pre[4], pre[3], pre[7]),
                                                   (b, a, r.n_b, r.w_b, pre[1], pre[5], pre[2], pre[6])):
                p = 1 / (1 + math.exp(-(MU + s - rr)))
                g, h = w - n * p, n * p * (1 - p)
                den = 1 + (vs + vr) * h
                S[srv] += vs * g / den
                VS[srv] = max(VS[srv] - vs * vs * h / den, SR.VAR_FLOOR)
                NS[srv] += n
                R[ret] -= vr * g / den
                VR[ret] = max(VR[ret] - vr * vr * h / den, SR.VAR_FLOOR)
                NR[ret] += n
    return out


# ------------------------------------------------------------------------------------------------
# The update itself

def test_one_update_is_one_newton_step():
    m = history([("a", "E", "2024-01-01", "F", "P", "Q")])
    m.loc[0, ["n_a", "w_a", "n_b", "w_b"]] = [80.0, 56.0, 70.0, 40.0]
    tail = history([("z", "Z", "2024-01-08", "F", "P", "Q")])
    tail["updates"] = False
    out = run(pd.concat([m, tail], ignore_index=True), {**K, "drift": 0.0})[1]
    vs, vr = K["var_serve"], K["var_return"]
    for n, w, srv_s, ret_r, srv_vs, ret_vr in ((80, 56, out[0], out[3], out[4], out[7]), (70, 40, out[1], out[2], out[5], out[6])):
        p = 1 / (1 + math.exp(-MU))
        g, h = w - n * p, n * p * (1 - p)
        den = 1 + (vs + vr) * h
        assert srv_s == pytest.approx(vs * g / den, abs=1e-12)
        assert ret_r == pytest.approx(-vr * g / den, abs=1e-12)
        assert srv_vs == pytest.approx(vs - vs * vs * h / den, abs=1e-12)
        assert ret_vr == pytest.approx(vr - vr * vr * h / den, abs=1e-12)
    assert out[8] == 80 and out[10] == 70 and out[9] == 70 and out[11] == 80


def test_winning_the_expected_points_moves_nothing_but_the_variance():
    m = history([("a", "E", "2024-01-01", "F", "P", "Q"), ("z", "Z", "2024-01-08", "F", "P", "Q")])
    p = 1 / (1 + math.exp(-MU))
    m.loc[0, ["n_a", "w_a", "n_b", "w_b"]] = [100.0, 100 * p, 100.0, 100 * p]
    m.loc[1, "updates"] = False
    out = run(m, {**K, "drift": 0.0})[1]
    assert np.allclose(out[:4], 0.0, atol=1e-12)
    assert out[4] < K["var_serve"] and out[6] < K["var_return"]


def test_only_serve_start_minus_return_start_matters():
    """Adding one constant to a newcomer's serve and return starts shifts every rating by it and changes no
    prediction: the ratings' common level is free, so fixing the return start loses nothing."""
    m = random_history(seed=8, weeks=10)
    h = SR.arrays(m, np.full(len(m), MU))
    a = SR.run(h, {**K, "start_serve": -0.2, "start_return": 0.0})
    b = SR.run(h, {**K, "start_serve": 0.1, "start_return": 0.3})
    assert np.allclose(b[:, :4], a[:, :4] + 0.3, atol=1e-10)
    assert np.allclose(b[:, 4:], a[:, 4:], atol=1e-12)
    for x, y in zip(SR.expected_serve(a, np.full(len(m), MU)), SR.expected_serve(b, np.full(len(m), MU))):
        assert np.allclose(x, y, atol=1e-12)


def test_equals_a_plain_pass_when_no_two_matches_are_simultaneous():
    rng = np.random.default_rng(7)
    rows, k = [], 0
    for wk in range(30):
        date = pd.Timestamp("2023-01-02") + pd.Timedelta(weeks=int(wk * 2))
        alive = [f"p{x}" for x in rng.permutation(24)[:8]]
        for rnd in ("QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                rows.append((f"m{k}", f"E{wk}", date, rnd, alive[i], alive[i + 1]))
                nxt.append(alive[i] if rng.random() < 0.5 else alive[i + 1])
                k += 1
            alive = nxt
    m = history(rows, seed=1)
    assert np.allclose(run(m), sequential(m), atol=1e-12)


# ------------------------------------------------------------------------------------------------
# The time rule

def hand_made():
    return history([
        ("a1", "E1", "2024-01-08", "R32", "P", "X"),     # week 1: P plays R32 and R16
        ("a2", "E1", "2024-01-08", "R16", "X", "P"),
        ("b1", "E2", "2024-01-15", "Q1", "P", "Y"),      # week 2: P qualifies and plays the main draw
        ("b2", "E2", "2024-01-15", "Q2", "P", "Z"),
        ("b3", "E2", "2024-01-15", "R32", "Q", "P"),
        ("c1", "E3", "2024-01-15", "R32", "P", "Q"),     # week 2, another event: never visible to E2
        ("d1", "F", "2024-01-22", "RR", "P", "Q"),       # week 3: a round robin and a semi-final
        ("d2", "F", "2024-01-22", "RR", "Q", "P"),
        ("d3", "F", "2024-01-22", "RR", "P", "X"),
        ("d4", "F", "2024-01-22", "SF", "P", "Y"),
    ], seed=2)


def p_values(m, out, col):
    """P's value of an output column pair (A's column ``col``, B's ``col + 1``) at each of P's matches."""
    side_a = m["player_a_id"].eq("P").to_numpy()
    return dict(zip(m["match_id"], np.where(side_a, out[:, col], out[:, col + 1])))


def test_hand_made_points_rated_are_the_asof_helpers():
    m = hand_made()
    out = run(m)
    rows = pd.concat([m.assign(player_id=m["player_a_id"], served=m["n_a"], got=out[:, 8]),
                      m.assign(player_id=m["player_b_id"], served=m["n_b"], got=out[:, 9])])
    want = C.asof_sums(rows, ["served"])["served"].to_numpy()
    assert np.array_equal(want, rows["got"].to_numpy())


def test_hand_made_ratings_follow_the_rule():
    m = hand_made()
    s = p_values(m, run(m), 0)
    assert s["a1"] == 0.0
    assert s["c1"] == s["b1"]                        # another event of week 2 sees only week 1
    assert s["b2"] != s["b1"] and s["b3"] != s["b2"]  # qualifying counts before the main draw
    assert s["d1"] == s["d2"] == s["d3"]             # the round robin's matches never see each other
    assert s["d4"] != s["d1"]                        # the semi-final sees the round robin


def test_retirements_and_matches_without_a_box_score_move_nothing():
    m = history([("r", "E", "2024-01-01", "R32", "P", "Q", "retired"), ("c", "E2", "2024-01-08", "R32", "P", "Q")])
    out = run(m)
    assert np.allclose(out[1, :4], 0.0) and out[1, 8] == 0 and out[1, 10] == 0


def test_drift_widens_a_rating_with_time_away_up_to_a_newcomers():
    m = history([("a", "E", "2024-01-01", "F", "P", "Q"), ("b", "E2", "2024-01-15", "F", "P", "Q"),
                 ("c", "E3", "2034-01-02", "F", "P", "Q")])
    out = run(m)
    v_after_first = run(m, {**K, "drift": 0.0})[1, 4]
    assert out[1, 4] == pytest.approx(v_after_first + 2 * K["drift"], abs=1e-12)   # two weeks of drift
    assert out[2, 4] == pytest.approx(K["var_serve"]) and out[2, 6] == pytest.approx(K["var_return"])


def test_ratings_equal_a_brute_force_reading_of_the_rule():
    """For sampled matches, the pre-match values equal a fresh pass over only the matches the rule lets the
    match see (earlier weeks, and the same event's earlier rounds), read off the match itself appended
    without a result."""
    m = random_history(seed=11, weeks=12)
    out = run(m)
    rng = np.random.default_rng(0)
    for i in rng.choice(len(m), size=50, replace=False):
        r = m.iloc[i]
        seen = (m["tournament_date"] < r["tournament_date"]) | (
            m["tournament_date"].eq(r["tournament_date"]) & m["tournament_id"].eq(r["tournament_id"])
            & (m["round_order"] < r["round_order"]))
        sub = pd.concat([m[seen], m.iloc[[i]].assign(updates=False)], ignore_index=True)
        want = run(sub)[-1]
        assert np.allclose(out[i], want, atol=1e-12), r["match_id"]


def test_probe_passes_the_pass_and_catches_a_plain_pass():
    m = random_history(seed=5, weeks=14)
    h = SR.arrays(m, np.full(len(m), MU))
    ok = SR.probe_by_round(h, K, n_cuts=25, from_quantile=0.3)
    assert ok["protected_matches_changed"] == 0 and ok["later_matches_changed"] > 0

    original = SR.run
    try:
        SR.run = lambda hh, k: sequential(m.assign(w_a=hh["w_a"], w_b=hh["w_b"]), k)
        bad = SR.probe_by_round(h, K, n_cuts=25, from_quantile=0.3)
    finally:
        SR.run = original
    assert bad["protected_matches_changed"] > 0


def test_ratings_recover_true_strengths_on_a_simulated_tour():
    """Players with true serve and return strengths play weekly knockouts; serve points are binomial at the
    model's probability. After a few seasons the ratings track the true strengths closely."""
    rng = np.random.default_rng(42)
    n_pl = 48
    s_true, r_true = rng.normal(0, 0.2, n_pl), rng.normal(0, 0.14, n_pl)
    rows, k = [], 0
    for wk in range(150):
        date = pd.Timestamp("2015-01-05") + pd.Timedelta(weeks=wk)
        alive = list(rng.permutation(n_pl)[:16])
        for rnd in ("R16", "QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                a, b = alive[i], alive[i + 1]
                rows.append({"match_id": f"m{k}", "tournament_id": f"E{wk}", "tournament_date": date, "round": rnd,
                             "match_num": str(k), "player_a_id": f"p{a:02d}", "player_b_id": f"p{b:02d}",
                             "status": "completed", "n_a": 75.0, "n_b": 75.0,
                             "w_a": float(rng.binomial(75, 1 / (1 + math.exp(-(MU + s_true[a] - r_true[b]))))),
                             "w_b": float(rng.binomial(75, 1 / (1 + math.exp(-(MU + s_true[b] - r_true[a])))))})
                nxt.append(a if rng.random() < 0.5 else b)
                k += 1
            alive = nxt
    m = pd.DataFrame(rows)
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    m = C.chrono_sort(m).reset_index(drop=True)
    m["updates"] = True
    out = run(m, {"var_serve": 0.04, "var_return": 0.02, "drift": 0.0})
    last = m.groupby("player_a_id").tail(1)
    idx = last.index.to_numpy()
    who = last["player_a_id"].str[1:].astype(int).to_numpy()
    assert np.corrcoef(out[idx, 0], s_true[who])[0, 1] > 0.9
    assert np.corrcoef(out[idx, 2], r_true[who])[0, 1] > 0.85


# ------------------------------------------------------------------------------------------------
# The trait measures on simulated players with known true rates

def simulated_players(rng, units=3000, matches=24, points=70, mean=0.62, sd=0.03, match_sd=0.0, vary_points=False):
    """Player-windows with true rates around ``mean`` (spread ``sd``), each match's rate further moved by
    ``match_sd`` (opponents, conditions), and binomial points."""
    p = rng.normal(mean, sd, units)
    unit = np.repeat(np.arange(units), matches)
    d = (rng.integers(50, 100, units * matches) if vary_points else np.full(units * matches, points)).astype("float64")
    pm = np.repeat(p, matches)
    if match_sd:
        pm = np.clip(pm + rng.normal(0, match_sd, units * matches), 0.01, 0.99)
    x = rng.binomial(d.astype(int), pm).astype("float64")
    return unit, x, d


def test_split_half_follows_the_spearman_brown_curve():
    rng = np.random.default_rng(1)
    mean, sd, points = 0.62, 0.03, 70
    unit, x, d = simulated_players(rng, mean=mean, sd=sd, points=points)
    k_true = (mean * (1 - mean) - sd ** 2) / (points * sd ** 2)        # in matches
    res = T.split_half(unit, x[:, None], d[:, None], rng, n_grid=[1, 2, 4, 8, 12], draws=5)
    assert len(res) == 5
    for row in res:
        assert row["r"] == pytest.approx(row["n"] / (row["n"] + k_true), abs=0.04)
        assert row["units_per_set"] == pytest.approx(points * row["n"])
    fit = T.sb_fit([r["n"] for r in res], [r["r"] for r in res], [r["player_windows"] for r in res])
    assert fit["k"] == pytest.approx(k_true, rel=0.15)


def test_split_half_needs_two_n_matches_and_uses_disjoint_sets():
    """With one rate in every match of a window, both sets always agree; a window short of 2n matches never
    enters."""
    sizes = [10] * 40 + [3] * 40
    unit = np.repeat(np.arange(80), sizes)
    rate = np.repeat(np.linspace(0.5, 0.7, 80), sizes)
    d = np.full(len(unit), 50.0)
    res = T.split_half(unit, (rate * d)[:, None], d[:, None], np.random.default_rng(0), n_grid=[1, 2, 5, 6], draws=3)
    by_n = {r["n"]: r for r in res}
    assert by_n[1]["r"] == pytest.approx(1.0) and by_n[1]["player_windows"] == 80
    assert by_n[2]["player_windows"] == 40 and by_n[5]["player_windows"] == 40
    assert 6 not in by_n                                       # no window has 12 matches


def test_reliability_at_a_typical_season_reads_the_curve_at_half_the_season():
    k = 8.0
    curve = pd.DataFrame({"n": [1, 2, 4, 8, 16], "units_per_set": [70, 140, 280, 560, 1120],
                          "player_windows": [900, 800, 700, 600, 500]})
    curve["r"] = curve["n"] / (curve["n"] + k)
    got = T.reliability_at(curve, 16.0)                       # half a season = 8 matches, measured
    assert got["reliability"] == pytest.approx(16 / (16 + k)) and got["h"] == 8
    assert got["reliability"] == pytest.approx(2 * got["r_h"] / (1 + got["r_h"]))
    assert np.isnan(T.reliability_at(curve, 40.0)["reliability"])      # past the measured curve: not guessed


def test_sb_fit_recovers_k_and_flags_no_signal():
    n = np.array([1, 2, 4, 8, 16.0])
    assert T.sb_fit(n, n / (n + 6.5), np.ones(5))["k"] == pytest.approx(6.5, rel=1e-6)
    assert T.sb_fit(n, np.zeros(5), np.ones(5))["no_signal"]


def test_shrinkage_recovers_the_constant_from_binomial_chance():
    rng = np.random.default_rng(2)
    mean, sd = 0.62, 0.03
    unit, x, d = simulated_players(rng, units=4000, matches=30, mean=mean, sd=sd, vary_points=True)
    s = T.unit_sums(unit, x, d)
    e = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
    k_true = (mean * (1 - mean) - sd ** 2) / sd ** 2                    # in points
    assert float(e["K"]) == pytest.approx(k_true, rel=0.15)
    assert float(e["K_binomial"]) == pytest.approx(k_true, rel=0.15)
    assert float(e["mu"]) == pytest.approx(mean, abs=0.002)


def test_binomial_chance_alone_shrinks_too_little_when_matches_vary_beyond_it():
    rng = np.random.default_rng(3)
    mean, sd, msd = 0.62, 0.03, 0.05
    unit, x, d = simulated_players(rng, units=4000, matches=30, mean=mean, sd=sd, match_sd=msd, vary_points=True)
    s = T.unit_sums(unit, x, d)
    e = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
    d_w = float((d ** 2).sum() / d.sum())                                 # the points-weighted match size
    k_true = (mean * (1 - mean) - sd ** 2 - msd ** 2 + d_w * msd ** 2) / sd ** 2
    assert float(e["K"]) == pytest.approx(k_true, rel=0.15)
    assert float(e["K_binomial"]) < 0.65 * k_true
    assert float(e["s2"]) / float(e["s2_binomial"]) > 1.5                  # overdispersion


def test_bootstrap_weights_of_one_give_the_point_estimate():
    rng = np.random.default_rng(4)
    unit, x, d = simulated_players(rng, units=500, matches=10)
    s = T.unit_sums(unit, x, d)
    e = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
    b = T.eb_constants(s["D"], s["X"], s["W"], s["m"], weight=np.ones((3, len(s["D"]))))
    assert np.allclose(b["K"], float(e["K"]))


@pytest.mark.parametrize("same", [True, False])
def test_carry_over_ceiling(same):
    """Two seasons of very different samples: with the same true rate in both, the observed correlation over
    its ceiling is about 1; with unrelated true rates, about 0."""
    rng = np.random.default_rng(5)
    n, mean, sd = 4000, 0.62, 0.03
    p1 = rng.normal(mean, sd, n)
    p2 = p1 if same else rng.normal(mean, sd, n)
    d1, d2 = rng.integers(100, 4000, n).astype(float), rng.integers(100, 4000, n).astype(float)
    x1, x2 = rng.binomial(d1.astype(int), p1), rng.binomial(d2.astype(int), p2)
    K = (mean * (1 - mean) - sd ** 2) / sd ** 2
    y1, R1 = (x1 + K * mean) / (d1 + K), d1 / (d1 + K)
    y2, R2 = (x2 + K * mean) / (d2 + K), d2 / (d2 + K)
    c = T.carry(y1, y2, R1, R2)
    assert c["true_carry"] == pytest.approx(1.0 if same else 0.0, abs=0.06)
    assert 0 < c["ceiling"] < 1


def test_logloss_terms():
    x, d, f = np.array([3.0, 0.0]), np.array([10.0, 4.0]), np.array([0.25, 0.1])
    want = -(x * np.log(f) + (d - x) * np.log(1 - f))
    assert np.allclose(T.logloss_terms(x, d, f, poisson=False), want)
    lam = f * d
    want_p = -(x * np.log(lam) - lam - np.array([math.lgamma(4.0), math.lgamma(1.0)]))
    assert np.allclose(T.logloss_terms(x, d, f, poisson=True), want_p)


# ------------------------------------------------------------------------------------------------
# The look-back sums of the forecasts, against a row-by-row reading of the time rule

def player_rows(seed=9, events=45):
    """Two rows per match over two years: a knockout every other week or so, a round robin beside it, and in
    some weeks another event sharing players; a random value per row."""
    rng = np.random.default_rng(seed)
    recs, k = [], 0
    for e in range(events):
        date = pd.Timestamp("2022-01-03") + pd.Timedelta(weeks=int(2 * e + (e % 3)))
        pool = [f"p{x}" for x in rng.permutation(14)]
        for rnd, pairs in (("QF", [(0, 1), (2, 3), (4, 5), (6, 7)]), ("SF", [(0, 2), (4, 6)]), ("F", [(0, 4)])):
            for i, j in pairs:
                for p in (pool[i], pool[j]):
                    recs.append({"player_id": p, "tournament_date": date, "tournament_id": f"E{e}", "round": rnd,
                                 "v": float(rng.integers(1, 9)), "match": k})
                k += 1
        for i, j in ((8, 9), (8, 10), (9, 10)):                    # a round robin
            for p in (pool[i], pool[j]):
                recs.append({"player_id": p, "tournament_date": date, "tournament_id": f"R{e}", "round": "RR",
                             "v": float(rng.integers(1, 9)), "match": k})
            k += 1
        if e % 2:                                                   # another event the same week, shared players
            for p in (pool[0], pool[11]):
                recs.append({"player_id": p, "tournament_date": date, "tournament_id": f"X{e}", "round": "R32",
                             "v": float(rng.integers(1, 9)), "match": k})
            k += 1
    r = pd.DataFrame(recs)
    r["round_order"] = r["round"].map(C.ROUND_ORDER)
    r["day"] = r["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    r["pcode"] = pd.factorize(r["player_id"])[0]
    return r


def seen_by_rule(r, i):
    row = r.iloc[i]
    same_player = r["player_id"].eq(row["player_id"])
    return same_player & ((r["tournament_date"] < row["tournament_date"]) | (
        r["tournament_date"].eq(row["tournament_date"]) & r["tournament_id"].eq(row["tournament_id"])
        & (r["round_order"] < row["round_order"])))


def test_last_52_weeks_equals_a_row_by_row_reading():
    r = player_rows()
    V = r[["v"]].to_numpy()
    career = C.asof_sums(r, ["v"]).to_numpy()
    before = T.sums_before(r["pcode"].to_numpy(), r["day"].to_numpy(), V, r["pcode"].to_numpy(),
                           r["day"].to_numpy() - T.WEEK52)
    got = (career - before)[:, 0]
    for i in range(len(r)):
        seen = seen_by_rule(r, i) & (r["day"] >= r["day"].iloc[i] - T.WEEK52)
        assert got[i] == pytest.approx(r.loc[seen, "v"].sum()), i
    assert (career[:, 0] > got).any()                          # the window does cut something


def test_career_and_decayed_sums_equal_a_row_by_row_reading():
    r = player_rows(seed=10)
    career, decayed = T.lookback_sums(r, r[["v"]].to_numpy(), (13, 52))
    assert np.allclose(career[:, 0], C.asof_sums(r, ["v"])["v"].to_numpy())
    for i in range(0, len(r), 7):
        seen = seen_by_rule(r, i)
        assert career[i, 0] == pytest.approx(r.loc[seen, "v"].sum()), i
        age = r["day"].iloc[i] - r.loc[seen, "day"]
        for h in (13, 52):
            want = (r.loc[seen, "v"] * np.exp2(-age / (7.0 * h))).sum()
            assert decayed[h][i, 0] == pytest.approx(want, rel=1e-9, abs=1e-12), (i, h)


def test_sums_before_counts_strictly_earlier_days_only():
    pcode = np.array([0, 0, 0, 1, 1])
    day = np.array([10, 20, 20, 15, 30])
    V = np.array([[1.0], [2.0], [4.0], [8.0], [16.0]])
    got = T.sums_before(pcode, day, V, np.array([0, 0, 0, 1, 1, 2]), np.array([10, 20, 21, 15, 31, 99]))[:, 0]
    assert got.tolist() == [0.0, 1.0, 7.0, 0.0, 24.0, 0.0]


def test_all_surfaces_measures_each_match_against_its_surface():
    rows = pd.DataFrame({"tour": ["atp"] * 3, "surface": ["Clay", "Grass", None], "spw_n": [60.0, 70.0, 50.0],
                         "spw_d": [100.0, 100.0, 80.0]})
    means = {("atp", "spw", "all"): 0.62, ("atp", "spw", "Clay"): 0.60, ("atp", "spw", "Grass"): 0.66,
             ("atp", "spw", "Hard"): 0.63, ("atp", "spw", "Carpet"): 0.65}
    x, d = T.centred(rows, "spw", means, "all")
    assert np.allclose(x, [62.0, 66.0, 50.0]) and np.allclose(d, [100.0, 100.0, 80.0])
    x2, _ = T.centred(rows, "spw", means, "Clay")
    assert np.allclose(x2, rows["spw_n"])


# ------------------------------------------------------------------------------------------------
# The built tables

BUILT_RATINGS = (C.OUT / "stage3_ratings.parquet").exists()
BUILT = all((C.OUT / f).exists() for f in ("stage3_shrinkage.csv", "stage3_persistence.csv", "stage3_results.json"))


@pytest.mark.skipif(not BUILT_RATINGS, reason="stage 3 ratings not built")
def test_built_ratings_table():
    r = pd.read_parquet(C.OUT / "stage3_ratings.parquet")
    m = C.load_matches(["match_id"])
    assert len(r) == len(m) and r["match_id"].is_unique
    for c in ("serve_a", "serve_b", "return_a", "return_b", "sd_serve_a", "sd_return_b", "p_serve_a", "p_serve_b"):
        assert r[c].notna().all(), c
    assert (r[["sd_serve_a", "sd_serve_b", "sd_return_a", "sd_return_b"]] > 0).all().all()
    assert r["p_serve_a"].between(0, 1, inclusive="neither").all()


@pytest.mark.skipif(not BUILT, reason="stage 3 tables not built")
def test_built_constants_and_persistence():
    s = pd.read_csv(C.OUT / "stage3_shrinkage.csv")
    for years in ("2010-2018", "2010-2026"):
        g = s[s["years"].eq(years)]
        assert set(g["stat"]) == set(C.RATES), years
        assert len(g) == len(C.RATES) * 2 * len(T.SURFACES), years
    assert (s["K_units"] > 0).all() and (s["mean"] > 0).all()
    p = pd.read_csv(C.OUT / "stage3_persistence.csv")
    assert set(p["verdict"]) <= {"repeats", "repeats weakly", "mostly noise"}
    assert p["reliability_typical"].between(0, 1).all()
