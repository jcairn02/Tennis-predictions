"""Stage 4: the features (stage4_features.py), the event countries (stage4_country.py) and the scoring
(stage4_rundown.py).

Each feature family is checked on a hand-made history against a row-by-row reading of the Brief's time rule: the
previous match, the history sums and their five forms, the meetings, the margin-weighted Elo, the iid model's formats.
The scoring is checked on simulated data: the Newton fits equal scikit-learn's, a season's predictions never move when
that season's or later results change, the shuffled copies stay inside their season, and the family-wide line is the
largest leave-one-out maximum. The plan's expectations are read from candidates.md itself.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic import stage4_candidates as P  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as CTRY  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as F  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402


def rows(recs):
    """Player-rows from (player, event, date, round[, value]) in any order, sorted as the table sorts them."""
    df = pd.DataFrame(recs, columns=["player_id", "tournament_id", "tournament_date", "round", "v"][:len(recs[0])])
    df["tournament_date"] = pd.to_datetime(df["tournament_date"])
    df["round_order"] = df["round"].map(C.ROUND_ORDER)
    df = df.sort_values(["tournament_date", "round_order", "tournament_id", "player_id"], kind="mergesort").reset_index(drop=True)
    df["order"] = np.arange(len(df))
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    df["pcode"] = pd.factorize(df["player_id"])[0].astype("int64")
    df["ev"] = pd.factorize(df["tournament_id"])[0]
    return df


def visible(df, i):
    """The rows the Brief's rule lets row i see (same player)."""
    r = df.iloc[i]
    return df["player_id"].eq(r["player_id"]) & ((df["tournament_date"] < r["tournament_date"]) | (
        df["tournament_date"].eq(r["tournament_date"]) & df["tournament_id"].eq(r["tournament_id"])
        & (df["round_order"] < r["round_order"])))


def random_history(seed=3, events=40, players=12):
    rng = np.random.default_rng(seed)
    recs = []
    for e in range(events):
        date = pd.Timestamp("2021-01-04") + pd.Timedelta(weeks=int(2 * e + (e % 3)))
        pool = [f"p{x}" for x in rng.permutation(players)]
        for rnd, n in (("R16", 8), ("QF", 4), ("SF", 2)):
            for p in pool[:n]:
                recs.append((p, f"E{e}", date, rnd, float(rng.integers(1, 9))))
        for p in pool[8:11]:                                       # a round robin the same week
            recs.append((p, f"R{e}", date, "RR", float(rng.integers(1, 9))))
            recs.append((p, f"R{e}", date, "RR", float(rng.integers(1, 9))))
    return rows(recs)


# ------------------------------------------------------------------------------------------------
# The previous match

def test_prev_visible_follows_the_rule_for_every_row():
    df = random_history()
    rng = np.random.default_rng(0)
    mask = rng.random(len(df)) < 0.6
    prev = F.prev_visible(df, mask)
    for i in range(len(df)):
        seen = visible(df, i) & pd.Series(mask, index=df.index)
        if not seen.any():
            assert prev[i] == -1, i
            continue
        cand = df[seen]
        same = cand[cand["tournament_date"].eq(df.loc[i, "tournament_date"])]
        want = (same if len(same) else cand[cand["tournament_date"].eq(cand["tournament_date"].max())])
        # the latest of those in the table's sort (event, round, order)
        want = want.sort_values(["ev", "round_order", "order"]).index[-1] if len(same) == 0 else \
            same.sort_values(["round_order", "order"]).index[-1]
        assert prev[i] == want, i


def test_prev_visible_equals_the_plans_previous_row_inside_the_mask():
    df = random_history(seed=5)
    mask = np.ones(len(df), dtype=bool)
    mask[::3] = False
    a = F.prev_visible(df, mask)
    b = P.previous_row(df.assign(tournament_id=df["tournament_id"]), mask)
    assert np.array_equal(a[mask], b[mask])


# ------------------------------------------------------------------------------------------------
# History sums and the five forms

def test_forms_equal_a_row_by_row_reading(monkeypatch):
    """One statistic over a hand-made two-surface history: career, 52 weeks, decayed, surface and adjusted forms equal
    sums over exactly the rows the rule lets each row see, shrunk as the plan says."""
    df = random_history(seed=7, events=45)
    rng = np.random.default_rng(1)
    n = len(df)
    df["surface"] = np.where(df["ev"] % 2 == 0, "Hard", "Clay")
    df["surf"] = df["surface"].map(F.SURF).to_numpy()
    df["tour"] = "atp"
    d = rng.integers(40, 90, n).astype("float64")
    x = rng.binomial(d.astype(int), 0.62).astype("float64")
    xa = x + rng.normal(0, 2, n)
    ok = rng.random(n) < 0.85
    means = {("atp", "all"): 0.6, ("atp", "Hard"): 0.63, ("atp", "Clay"): 0.58, ("atp", "Grass"): 0.66, ("atp", "Carpet"): 0.6,
             ("wta", "all"): 0.5, ("wta", "Hard"): 0.5, ("wta", "Clay"): 0.5, ("wta", "Grass"): 0.5, ("wta", "Carpet"): 0.5}
    ctx = {"means": {"spw": means, "spw_adj": means}, "adjusted_x": {"spw": np.where(ok, xa, 0.0)},
           "K": {(s, t, sf): K for s, K in (("spw", 300.0), ("spw_adj", 150.0)) for t in C.TOURS
                 for sf in ("all", "Hard", "Clay", "Grass")}}
    ctx["K"][("spw", "atp", "Clay")] = np.inf                      # a surface with no spread: the average for all
    monkeypatch.setattr(F, "HIST", ["spw"])
    xd = {"spw": (np.where(ok, x, 0.0), np.where(ok, d, 0.0), ok)}
    S = {"hist": F.history_sums(df.assign(player_id=df["player_id"]), xd, ctx)}
    mu_row = df["surface"].map({"Hard": 0.63, "Clay": 0.58}).to_numpy()
    for i in range(0, n, 5):
        seen = (visible(df, i) & pd.Series(ok, index=df.index)).to_numpy()
        mt = mu_row[i]
        xc = (x - d * mu_row)[seen]
        car = F.form_value(df, S, ctx, "spw", "career")
        assert car[1][i] == (d[seen].sum() > 0)
        if seen.any():
            assert car[0][i] == pytest.approx(mt + xc.sum() / (d[seen].sum() + 300.0), rel=1e-10)
        w52 = seen & (df["day"].to_numpy() >= df["day"].iloc[i] - F.WEEK52)
        v52 = F.form_value(df, S, ctx, "spw", "52 weeks")
        if w52.any():
            assert v52[0][i] == pytest.approx(mt + (x - d * mu_row)[w52].sum() / (d[w52].sum() + 300.0), rel=1e-9)
        age = df["day"].iloc[i] - df["day"].to_numpy()[seen]
        wt = np.exp2(-age / (7.0 * F.HALF_LIFE))
        dec = F.form_value(df, S, ctx, "spw", "decayed")
        if seen.any():
            assert dec[0][i] == pytest.approx(mt + (xc * wt).sum() / ((d[seen] * wt).sum() + 300.0), rel=1e-9)
        sur = F.form_value(df, S, ctx, "spw", "surface")
        same = seen & (df["surf"].to_numpy() == df["surf"].iloc[i])
        if df["surface"].iloc[i] == "Clay":
            assert sur[0][i] == pytest.approx(0.58)                  # K infinite on clay: the average
        elif same.any():
            assert sur[0][i] == pytest.approx(0.63 + (x - d * 0.63)[same].sum() / (d[same].sum() + 300.0), rel=1e-9)
        adj = F.form_value(df, S, ctx, "spw", "adjusted")
        if seen.any():
            assert adj[0][i] == pytest.approx(mt + (xa - d * mu_row)[seen].sum() / (d[seen].sum() + 150.0), rel=1e-9)


def test_on_scale_and_matchup_arithmetic():
    v = np.array([0.6, 0.4])
    assert np.allclose(F.on_scale("spw", v), np.log(v / (1 - v)))
    assert np.allclose(F.on_scale("bp_faced_pg", np.array([0.5])), np.log(0.5))
    assert np.allclose(F.on_scale("bp_over", np.array([0.01])), 0.01)
    # the server at the average against a returner at the average serves at the average
    mu = 0.62
    srv, ret = mu, 1 - mu
    p = 1 / (1 + np.exp(-(np.log(mu / (1 - mu)) + (np.log(srv / (1 - srv)) - np.log(mu / (1 - mu)))
                          - (np.log(ret / (1 - ret)) - np.log((1 - mu) / mu)))))
    assert p == pytest.approx(mu)


# ------------------------------------------------------------------------------------------------
# The iid model's formats, and the hold rate inverted

def test_iid_prob_formats():
    pa, pb = np.array([0.64, 0.58]), np.array([0.6, 0.6])
    std = F.iid_prob(pa, pb, np.array([False, True]), np.array(["TB7@6", "TB10@6"]), np.array(["standard", "standard"]))
    assert std[0] == pytest.approx(float(M.match_win(0.64, 0.6, 3)))
    assert std[1] == pytest.approx(float(M.match_win(0.58, 0.6, 5, "TB10@6")))
    mt = F.iid_prob(pa[:1], pb[:1], np.array([False]), np.array(["TB7@6"]), np.array(["match_tiebreak"]))
    s, f = float(M.set_win(0.64, 0.6)), float(M.tiebreak(0.64, 0.6, 10))
    assert mt[0] == pytest.approx(s * s + 2 * s * (1 - s) * f)


def test_serve_rate_for_hold_inverts_the_game():
    p = np.array([0.45, 0.55, 0.62, 0.7])
    assert np.allclose(F.serve_rate_for_hold(M.game(p)), p, atol=1e-9)


# ------------------------------------------------------------------------------------------------
# Meetings

def test_meetings_count_earlier_completed_meetings_of_the_same_pair():
    recs = [("a", "b", "E1", "2024-01-01", "R32", True, "completed"), ("a", "c", "E1", "2024-01-01", "R16", False, "completed"),
            ("a", "b", "E2", "2024-01-08", "R32", False, "retired"), ("a", "b", "E3", "2024-01-08", "R32", True, "completed"),
            ("a", "b", "E4", "2024-01-15", "RR", True, "completed"), ("a", "b", "E4", "2024-01-15", "RR", True, "walkover"),
            ("a", "b", "E4", "2024-01-15", "F", True, "completed")]
    out = []
    for p, o, e, dt, rnd, won, st in recs:
        out += [(p, o, e, dt, rnd, won, st), (o, p, e, dt, rnd, not won, st)]
    df = pd.DataFrame(out, columns=["player_id", "opponent_id", "tournament_id", "tournament_date", "round", "won", "status"])
    df["tournament_date"] = pd.to_datetime(df["tournament_date"])
    df["round_order"] = df["round"].map(C.ROUND_ORDER)
    df["order"] = np.repeat(np.arange(len(recs)), 2)
    df["day"] = df["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    ids = pd.factorize(pd.concat([df["player_id"], df["opponent_id"]]))[0]
    df["pcode"], df["opp_pcode"] = ids[:len(df)], ids[len(df):]
    df["played"] = df["status"].isin(["completed", "retired"]).to_numpy()
    df["surf"] = 1
    h = F.h2h_sums(df, np.full(len(df), 0.5))
    a = df["player_id"].eq("a") & df["opponent_id"].eq("b")
    got = h["car"][a.to_numpy()]
    # E1 R32: none; E2 and E3 (same week): only E1; E4 round robin: E1-E3 (3 played, won 2), never each other; the final:
    # the round robin's completed match counts, its walkover does not
    assert got[:, 1].tolist() == [0, 1, 1, 3, 3, 4]
    assert got[:, 0].tolist() == [0, 1, 1, 2, 2, 3]


# ------------------------------------------------------------------------------------------------
# The margin-weighted Elo

def elo_history(seed=2, weeks=30, players=20):
    rng = np.random.default_rng(seed)
    recs, k = [], 0
    for wk in range(weeks):
        date = pd.Timestamp("2023-01-02") + pd.Timedelta(weeks=wk)
        pool = [f"p{x}" for x in rng.permutation(players)]
        for rnd, n in (("QF", 8), ("SF", 4), ("F", 2)):
            for i in range(0, n, 2):
                recs.append({"match_id": f"m{k}", "tournament_id": f"E{wk}", "tournament_date": date, "round": rnd,
                             "match_num": str(k), "player_a_id": pool[i], "player_b_id": pool[i + 1],
                             "a_won": bool(rng.random() < 0.5), "surface": ["Hard", "Clay"][wk % 2], "status": "completed"})
                k += 1
        for i, j in ((12, 13), (12, 14), (13, 14)):
            recs.append({"match_id": f"m{k}", "tournament_id": f"R{wk}", "tournament_date": date, "round": "RR",
                         "match_num": str(k), "player_a_id": pool[i], "player_b_id": pool[j],
                         "a_won": bool(rng.random() < 0.5), "surface": "Hard", "status": "completed"})
            k += 1
    m = pd.DataFrame(recs)
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    return C.chrono_sort(m).reset_index(drop=True)


def test_weighted_elo_equals_stage1_with_unit_weights_and_scales_k():
    m = elo_history()
    h = B.history_arrays(m)
    upd = [True] * len(m)
    base = B.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"], 600, 2, 0.6)
    one = F.weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, [1.0] * len(m),
                              h["n_players"], 600, 2, 0.6)
    assert np.allclose(base, one, equal_nan=True, atol=1e-12)
    two = F.weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, [2.0] * len(m),
                              h["n_players"], 600, 2, 0.6)
    k2 = B.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"], 1200, 2, 0.6)
    assert np.allclose(two, k2, equal_nan=True, atol=1e-9)


def test_weighted_elo_survives_an_impossible_weight_and_keeps_the_values_before_it():
    """The leak probe redraws a later match's numerator and denominator independently, so a weight can reach several
    hundred; one such update carried a rating past float range and 10.0 ** x raised OverflowError (the template build
    of 16 Oct 2026). The exponent is now capped: the pass completes, and every value before the heavy match is the
    uncapped pass's, bit for bit."""
    m = elo_history(seed=5)
    h = B.history_arrays(m)
    upd = [True] * len(m)
    base = F.weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, [1.0] * len(m),
                               h["n_players"], 600, 2, 0.6)
    heavy = len(m) // 3
    w = [1.0] * len(m)
    w[heavy] = 1e6
    got = F.weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, w,
                              h["n_players"], 600, 2, 0.6)
    assert np.array_equal(got[:heavy + 1], base[:heavy + 1], equal_nan=True)
    gap = np.abs(got[:, 0] - got[:, 1]) / 400.0
    assert np.nanmax(gap) > F.EXP_CAP          # the cap was reached: without it this history raises


def test_weighted_elo_passes_the_date_and_round_probe():
    m = elo_history(seed=4)
    h = B.history_arrays(m)
    w = list(np.random.default_rng(0).uniform(0.6, 1.4, len(m)))

    def ratings(hh):
        return F.weighted_elo_pass(hh["week"], hh["event"], hh["rnd"], hh["a"], hh["b"], hh["a_won"], hh["surf"],
                                   [True] * len(m), w, hh["n_players"], 600, 2, 0.6)
    ok = B.probe_by_round(h, ratings, n_cuts=20, from_quantile=0.3)
    assert ok["protected_matches_changed"] == 0 and ok["later_matches_changed"] > 0


# ------------------------------------------------------------------------------------------------
# Scoring

def test_newton_equals_sklearn_and_copies_are_independent():
    rng = np.random.default_rng(3)
    n = 4000
    Z = np.column_stack([rng.normal(0, 1, n), rng.normal(0, 1, n), rng.normal(0, 2, n)])
    y = rng.random(n) < 1 / (1 + np.exp(-(0.8 * Z[:, 0] - 0.3 * Z[:, 1] + 0.1 * Z[:, 2])))
    want = LogisticRegression(fit_intercept=False, C=np.inf, max_iter=10000, tol=1e-12).fit(Z, y).coef_[0]
    Zc = np.stack([Z, Z[rng.permutation(n)]])
    got = R.newton(Zc, y, np.zeros((2, 3)))
    assert np.allclose(got[0], want, atol=1e-5)
    other = LogisticRegression(fit_intercept=False, C=np.inf, max_iter=10000, tol=1e-12).fit(Zc[1], y).coef_[0]
    assert np.allclose(got[1], other, atol=1e-5)


def test_walk_forward_never_sees_the_season_it_scores():
    rng = np.random.default_rng(4)
    year = np.repeat(np.arange(2010, 2020), 500)
    x = rng.normal(0, 1, len(year))
    y = rng.random(len(year)) < 1 / (1 + np.exp(-0.7 * x))
    Z = x[None, :, None].copy()
    w = R.walk(Z, y, year, list(range(2013, 2020)), None)
    y2 = y.copy()
    y2[year >= 2016] = ~y2[year >= 2016]                          # 2016 on: every result flipped
    w2 = R.walk(Z, y2, year, list(range(2013, 2020)), None)
    early = year <= 2016
    p = np.where(y, np.exp(-w["llm"][0]), 1 - np.exp(-w["llm"][0]))
    p2 = np.where(y2, np.exp(-w2["llm"][0]), 1 - np.exp(-w2["llm"][0]))
    assert np.allclose(p[early & (year >= 2013)], p2[early & (year >= 2013)])   # 2013-2016 predictions unchanged
    assert not np.allclose(p[year == 2017], p2[year == 2017])
    assert np.isnan(w["llm"][0][year < 2013]).all()


def test_copies_shuffle_within_seasons_and_move_as_a_pair():
    rng = np.random.default_rng(5)
    year = np.repeat([2013, 2014, 2015], [7, 9, 5])
    X = np.column_stack([np.arange(len(year)), 100 + np.arange(len(year))]).astype(float)
    keys = rng.random((len(year), R.COPIES))
    cp = R.shuffled(X, year, keys)
    for c in range(R.COPIES):
        for yv in (2013, 2014, 2015):
            m = year == yv
            assert sorted(cp[c, m, 0]) == sorted(X[m, 0])
        assert np.allclose(cp[c, :, 1] - cp[c, :, 0], 100)            # the two inputs move together
    assert not np.allclose(cp[0], cp[1])
    again = R.shuffled(X, year, keys)
    assert np.array_equal(cp, again)                                 # the same keys give the same copies


def test_family_line_is_the_largest_leave_one_out_maximum():
    rng = np.random.default_rng(6)
    rows = []
    M_ = rng.normal(0, 1, (5, R.COPIES))
    for i in range(5):
        rows.append({"tour": "atp", "scores": {"elo": {"groups": {"all": {"n": 100, "copies": list(M_[i]),
                                                                           "band_sd": float(M_[i].std(ddof=1))}}}}})
    got = R.family_line(rows, "atp", "elo")
    z = np.empty_like(M_)
    for c in range(R.COPIES):
        o = np.delete(M_, c, axis=1)
        z[:, c] = (M_[:, c] - o.mean(axis=1)) / o.std(axis=1, ddof=1)
    assert got["line"] == pytest.approx(z.max())
    assert got["rows"] == 5


def test_compare_counts_the_matches_that_differ_by_season_and_event(monkeypatch):
    monkeypatch.setattr(R, "score_plain", lambda f, p, cols: {})        # the scores are tested elsewhere
    f = pd.DataFrame({"tour": ["atp"] * 5 + ["wta"], "year": [2015, 2016, 2015, 2024, 2019, 2015],
                      "evaluation": [True] * 6})
    Xo = np.array([[0.1], [0.2], [0.3], [0.4], [0.5], [0.6]])
    Xn = Xo.copy()
    Xn[[0, 2, 3, 5], 0] += 1.0                                          # the last row differs but is the other tour
    Xn[4, 0] += 1e-12                                                   # below float32 precision: not a difference
    labels = np.array(["Wimbledon Q3", "Basel R32", "Wimbledon Q3", "Wimbledon Q3", "Basel R32", "Wimbledon Q3"])
    rec = R.compare(f, {"tour": "atp", "id": "x", "form": "single"}, Xo, Xn, "format recorded", labels)
    assert rec["values_differ"] == 3
    assert rec["differ_by_season"] == "2015: 2; 2024: 1"
    assert rec["differ_by_event"] == "Wimbledon Q3: 3"
    same = R.compare(f, {"tour": "atp", "id": "x", "form": "single"}, Xo, Xo.copy(), "format recorded", labels)
    assert same["values_differ"] == 0 and "differ_by_season" not in same


def test_observed_category_follows_the_plans_scale():
    band = {"n": 500, "above_band": True, "below_band": False, "lo": 0.01,
            "ci_method": "paired_four_week_cluster_t"}
    assert R.observed_category("alone", {**band, "imp": 45}) == "strong"
    assert R.observed_category("alone", {**band, "imp": 12}) == "moderate"
    assert R.observed_category("elo", {**band, "imp": 0.4}) == "small"
    assert R.observed_category("elo", {**band, "imp": 1.2}) == "clear"
    assert R.observed_category("elo", {"n": 500, "imp": 0.4, "above_band": False, "below_band": False}) == "none"
    assert R.observed_category("market", {"n": 500, "imp": -0.4, "above_band": False, "below_band": True}) == "worse"


@pytest.mark.skipif(not R.PLAN.exists(), reason="candidates.md missing")
def test_the_plans_expectations_are_read_for_every_candidate():
    cand = pd.read_csv(R.CANDIDATES)
    exp = R.plan_expectations(cand)
    assert set(exp) == set(cand["id"])
    assert R.expected_for(exp, "mu_points", "elo", "atp", "career", exp) == "clear"
    assert R.expected_for(exp, "mu_points", "elo", "wta", "career", exp) == "small"
    assert R.expected_for(exp, "tpw", "alone", "atp", "adjusted", exp) == "strong"
    assert R.expected_for(exp, "tpw", "alone", "atp", "career", exp) == "moderate"
    assert R.expected_for(exp, "rank_elo_gap", "elo", "atp", "single", exp) == R.expected_for(exp, "rank", "elo", "atp", "single", exp)
    assert R.expected_for(exp, "best_of_five", "alone", "atp", "single", exp) is None
    # the section 3.3 features read from that table's columns (feature | before | data | why | alone | elo | market | sign)
    assert exp["rating_matchup"]["alone"] == "strong" and exp["rating_matchup"]["sign"] == "+"
    assert R.expected_for(exp, "rating_matchup", "elo", "atp", "single", exp) == "clear"
    assert R.expected_for(exp, "rating_matchup", "elo", "wta", "single", exp) == "small"
    assert exp["bigpoint_return"]["alone"] == "weak" and exp["bigpoint_return"]["elo"] == "small"
    assert exp["sets_14d"]["sign"] == "?" and exp["days_since"]["sign"] == "−"


# ------------------------------------------------------------------------------------------------
# The event countries

def test_event_country_precedence_and_player_aliases():
    table = pd.DataFrame([{"tour": "atp", "event_key": "rome ch", "from_year": np.nan, "to_year": np.nan, "tournament_id": pd.NA, "country": "ITA"},
                          {"tour": "atp", "event_key": "rome ch", "from_year": 2022, "to_year": 2022, "tournament_id": "2022-2781", "country": "USA"},
                          {"tour": "atp", "event_key": "tour finals", "from_year": 2013, "to_year": 2020, "tournament_id": pd.NA, "country": "GBR"},
                          {"tour": "atp", "event_key": "tour finals", "from_year": 2021, "to_year": 2026, "tournament_id": pd.NA, "country": "ITA"},
                          {"tour": "atp", "event_key": "kingston", "from_year": np.nan, "to_year": np.nan, "tournament_id": pd.NA, "country": pd.NA}])
    table["tournament_id"] = table["tournament_id"].astype("string")
    table["country"] = table["country"].astype("string")
    m = pd.DataFrame({"tour": ["atp"] * 6, "year": [2022, 2022, 2019, 2023, 2026, 2022],
                      "tournament_id": ["2022-2151", "2022-2781", "2019-605", "2023-605", "2026-3121", "x"],
                      "tournament_name": ["Rome CH", "Rome CH", "Tour Finals", "Tour Finals", "Kingston 1", "Nowhere"]})
    got = CTRY.event_country(m, table).tolist()
    assert got[:4] == ["ITA", "USA", "GBR", "ITA"]
    assert pd.isna(got[4]) and pd.isna(got[5])
    pc = CTRY.player_country(pd.Series(["PRT", "POR", None])).tolist()
    assert pc[:2] == ["POR", "POR"] and pd.isna(pc[2])
    assert CTRY.event_key("Forli 1 CH") == "forli ch" and CTRY.event_key("'s-Hertogenbosch") == "s hertogenbosch"


@pytest.mark.skipif(not CTRY.TABLE.exists() or not C.MATCHES.exists(), reason="tables not built")
def test_every_evaluation_event_name_is_in_the_country_table():
    m = C.load_matches(["tour", "evaluation", "tournament_name"])
    ev = m[m["evaluation"]]
    keys = set(zip(ev["tour"], ev["tournament_name"].map(CTRY.event_key)))
    t = CTRY.load_table()
    assert keys <= set(zip(t["tour"], t["event_key"]))
    assert set(t["country"].dropna()) <= set("ARG AUS AUT AZE BEL BIH BOL BRA BRN BUL CAN CGO CHI CHN CIV COL CRO CZE DOM ECU EGY ESP "
                                             "EST FIN FRA GBR GEO GER GRE HKG HUN IND IRL ISR ITA JPN KAZ KOR KSA LAT LTU LUX MAR "
                                             "MAS MDA MEX MKD MON NED NZL PAK PAN PAR PER PHI POL POR PUR QAT ROU RSA RUS RWA SGP "
                                             "SLO SMR SRB SUI SVK SWE THA TPE TUN TUR UAE UKR URU USA UZB VIE AND".split())


# ------------------------------------------------------------------------------------------------
# The built tables

BUILT = R.FEATURES.exists() and R.FEATURES_SUMMARY.exists()


@pytest.mark.skipif(not BUILT, reason="stage 4 features not built")
def test_built_features_reproduce_the_plans_coverage_and_pass_the_probe():
    import json
    s = json.loads(R.FEATURES_SUMMARY.read_text(encoding="utf-8"))
    rec, plan = s["probe"]["variants"]["recorded_format"], s["probe"]["variants"]["plan"]
    assert rec["protected_changed"] == 0 and rec["open_changed"] > 0 and rec["control_protected_changed"] > 0
    # with the plan's format read from the score, only the features that use the match's format may move
    fmt = {f"{c}|{f}" for c in ("mu_points", "mu_games", "mu_components") for f in F.FORMS} | {"rating_matchup|single", "best_of_five|single"}
    assert set(plan["changed_by_column"]) <= fmt
    cov = pd.DataFrame(s["coverage_vs_plan"])
    same = cov["exists_here"] == cov["plan_present"]
    assert same.mean() > 0.9
