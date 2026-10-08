"""Stage 1: the odds link (stage1_odds.py) and the baselines (stage1_baselines.py).

The Elo pass is proven three ways on synthetic histories: it equals the inherited scaffold
src/ratings/elo.py where no two matches are simultaneous; it keeps the Brief's time rule on a
hand-made history and against a brute-force reading of the rule; and a probe cut by date, event and
round passes it while catching a row-by-row Elo like the scaffold's. The tests on the built tables
are skipped until the stage has run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402
from src.eda.predictability_diagnostic import stage1_odds as O  # noqa: E402
from src.ratings import elo as scaffold  # noqa: E402

K = {"k0": 250.0, "offset": 5.0, "shape": 0.4}


# ------------------------------------------------------------------------------------------------
# Synthetic histories

def history(rows, surfaces=None):
    """Matches from (match_id, event, date, round, winner, loser[, status]) in any order, sorted as the
    table sorts them, with side A = the winner in odd rows so both sides occur."""
    recs = []
    for i, r in enumerate(rows):
        mid, ev, date, rnd, w, l = r[:6]
        status = r[6] if len(r) > 6 else "completed"
        a, b = (w, l) if i % 2 == 0 else (l, w)
        recs.append({"match_id": mid, "tournament_id": ev, "tournament_date": pd.Timestamp(date), "round": rnd,
                     "match_num": str(i), "player_a_id": a, "player_b_id": b, "a_won": a == w, "status": status,
                     "surface": (surfaces or {}).get(ev, "Hard")})
    m = pd.DataFrame(recs)
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    m = C.chrono_sort(m).reset_index(drop=True)
    m["order"] = np.arange(len(m))
    return m


def run(m, rule="ret", k=K, surface=True):
    return E.run_elo(E.history_arrays(m), m["status"], rule, k, surface=surface)


def random_history(seed=3, weeks=24, players=36, overlap=True):
    """Weekly events: a 16-player knockout, a round robin of four with a final, and (``overlap``) a
    second small knockout the same week that shares players with the first."""
    rng = np.random.default_rng(seed)
    rows, k = [], 0
    for wk in range(weeks):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=wk)
        pool = [f"p{x}" for x in rng.permutation(players)]
        ko, rr = pool[:16], pool[16:20]
        alive = ko
        for rnd in ("R16", "QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                w, l = (alive[i], alive[i + 1]) if rng.random() < 0.5 else (alive[i + 1], alive[i])
                rows.append((f"m{k}", f"K{wk}", date, rnd, w, l, "retired" if rng.random() < 0.05 else "completed"))
                nxt.append(w)
                k += 1
            alive = nxt
        wins = {p: 0 for p in rr}
        for i in range(4):
            for j in range(i + 1, 4):
                w, l = (rr[i], rr[j]) if rng.random() < 0.5 else (rr[j], rr[i])
                wins[w] += 1
                rows.append((f"m{k}", f"R{wk}", date, "RR", w, l))
                k += 1
        top = sorted(rr, key=lambda p: -wins[p])[:2]
        rows.append((f"m{k}", f"R{wk}", date, "F", top[0], top[1]))
        k += 1
        if overlap:                                  # players of the knockout also play here, same week
            field = list(rng.choice(ko, size=4, replace=False))
            for i in (0, 2):
                w, l = (field[i], field[i + 1]) if rng.random() < 0.5 else (field[i + 1], field[i])
                rows.append((f"m{k}", f"X{wk}", date, "R32", w, l))
                k += 1
    return history(rows, surfaces={f"R{w}": "Clay" for w in range(weeks)})


# ------------------------------------------------------------------------------------------------
# The inherited scaffold, src/ratings/elo.py

def test_formulas_are_the_scaffolds():
    for n in (0, 3, 40, 900):
        assert E.k_factor(n, **K) == pytest.approx(scaffold.k_factor(n, **K))
    assert E.expected(1600.0, 1450.0) == pytest.approx(scaffold.expected_score(1600.0, 1450.0))


def test_equals_the_scaffold_when_no_two_matches_are_simultaneous():
    """One knockout a week, one match per player per round: the time rule and a row-by-row pass agree."""
    rng = np.random.default_rng(7)
    rows, k = [], 0
    for wk in range(30):
        date = pd.Timestamp("2023-01-02") + pd.Timedelta(weeks=wk)
        alive = [f"p{x}" for x in rng.permutation(24)[:8]]
        for rnd in ("QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                w, l = (alive[i], alive[i + 1]) if rng.random() < 0.5 else (alive[i + 1], alive[i])
                rows.append((f"m{k}", f"E{wk}", date, rnd, w, l))
                nxt.append(w)
                k += 1
            alive = nxt
    m = history(rows, surfaces={f"E{w}": ("Clay" if w % 3 else "Grass") for w in range(30)})
    out = run(m)
    for w in (0.0, 0.3, 1.0):
        ref = scaffold.SurfaceBlendElo(surface_weight=w, **K)
        winners = np.where(m["a_won"], m["player_a_id"], m["player_b_id"])
        losers = np.where(m["a_won"], m["player_b_id"], m["player_a_id"])
        df = pd.DataFrame({"tourney_date": m["tournament_date"], "winner_name": winners, "loser_name": losers,
                           "surface": m["surface"]})
        p_winner = ref.fit(df)["p_winner"].to_numpy()
        ours = E.blend(out, w)
        ours_winner = np.where(m["a_won"], ours, 1 - ours)
        assert np.allclose(ours_winner, p_winner, atol=1e-12)


def test_the_scaffold_lets_a_round_robin_see_itself():
    """elo.py's row-by-row fit gives a round robin's later match a rating that includes an earlier one."""
    m = history([("a", "F", "2024-01-01", "RR", "P", "Q"), ("b", "F", "2024-01-01", "RR", "P", "X")])
    ref = scaffold.SurfaceBlendElo(surface_weight=0.0, **K)
    p = ref.fit(pd.DataFrame({"tourney_date": m["tournament_date"], "winner_name": ["P", "P"],
                              "loser_name": ["Q", "X"], "surface": "Hard"}))["p_winner"].to_numpy()
    assert p[0] == pytest.approx(0.5) and p[1] > 0.5            # the scaffold: the second saw the first
    out = run(m)
    assert out[0, 0] == out[1, 0] or out[0, 1] == out[1, 1]     # ours: P is 1500 in both
    assert set(out[:, :2].ravel()) == {E.START}


# ------------------------------------------------------------------------------------------------
# The time rule

def hand_made():
    return history([
        ("a1", "E1", "2024-01-08", "R32", "P", "X"),     # week 1: P wins R32, loses R16
        ("a2", "E1", "2024-01-08", "R16", "X", "P"),
        ("b1", "E2", "2024-01-15", "Q1", "P", "Y"),      # week 2: P qualifies and plays the main draw
        ("b2", "E2", "2024-01-15", "Q2", "P", "Z"),
        ("b3", "E2", "2024-01-15", "R32", "Q", "P"),
        ("c1", "E3", "2024-01-15", "R32", "P", "Q"),     # week 2, another event: never visible to E2
        ("d1", "F", "2024-01-22", "RR", "P", "Q"),       # week 3: a round robin and a semi-final
        ("d2", "F", "2024-01-22", "RR", "Q", "P"),
        ("d3", "F", "2024-01-22", "RR", "P", "X"),
        ("d4", "F", "2024-01-22", "SF", "P", "Y"),
    ])


def p_values(m, out, col):
    """P's value of an output column at each of P's matches, by match id."""
    side_a = m["player_a_id"].eq("P").to_numpy()
    return dict(zip(m["match_id"], np.where(side_a, out[:, col], out[:, col + 1])))


def test_hand_made_counts_are_the_asof_helpers():
    m = hand_made()
    out = run(m)
    n = {k: v for k, v in p_values(m, out, 2).items() if k in {"a1", "a2", "b1", "b2", "b3", "c1", "d1", "d2", "d3", "d4"}}
    assert n == {"a1": 0, "a2": 1, "b1": 2, "b2": 3, "b3": 4, "c1": 2, "d1": 6, "d2": 6, "d3": 6, "d4": 9}


def test_hand_made_ratings_follow_the_rule():
    m = hand_made()
    r = p_values(m, run(m), 0)
    assert r["a1"] == E.START
    assert r["c1"] == r["b1"]                        # another event of week 2 sees only week 1
    assert r["b2"] > r["b1"] and r["b3"] > r["b2"]   # qualifying wins count before the main draw
    assert r["d1"] == r["d2"] == r["d3"]             # the round robin's matches never see each other
    assert r["d4"] != r["d1"]                        # the semi-final sees the round robin


def test_counts_equal_the_asof_helper_on_random_histories():
    m = random_history()
    out = run(m)
    rows = pd.concat([m.assign(player_id=m["player_a_id"], n=out[:, 2]), m.assign(player_id=m["player_b_id"], n=out[:, 3])])
    rows["one"] = rows["status"].isin(E.UPDATES["ret"]).astype(float)
    got = C.asof_sums(rows, ["one"])["one"].to_numpy()
    assert np.array_equal(got, rows["n"].to_numpy())


def final_rating(m, player, rule="ret"):
    """A player's rating after all of ``m``: read off a dummy match a week after the last one."""
    last = m["tournament_date"].max() + pd.Timedelta(weeks=1)
    tail = pd.DataFrame([{"match_id": "zz", "tournament_id": "ZZ", "tournament_date": last, "round": "F",
                          "round_order": C.ROUND_ORDER["F"], "match_num": "0", "player_a_id": player,
                          "player_b_id": "__dummy__", "a_won": True, "status": "walkover", "surface": "Hard"}])
    mm = pd.concat([m, tail], ignore_index=True)
    return run(mm, rule)[-1, 0]


@pytest.mark.parametrize("rule", ["ret", "noret"])
def test_ratings_equal_a_brute_force_reading_of_the_rule(rule):
    """For sampled matches, the pre-match rating equals a fresh pass over only the matches the rule
    lets the match see (earlier weeks, and the same event's earlier rounds)."""
    m = random_history(seed=11, weeks=10)
    out = run(m, rule)
    rng = np.random.default_rng(0)
    for i in rng.choice(len(m), size=40, replace=False):
        r = m.iloc[i]
        seen = (m["tournament_date"] < r["tournament_date"]) | (
            m["tournament_date"].eq(r["tournament_date"]) & m["tournament_id"].eq(r["tournament_id"])
            & (m["round_order"] < r["round_order"]))
        sub = m[seen]
        want = final_rating(sub, r["player_a_id"], rule) if len(sub) else E.START
        assert out[i, 0] == pytest.approx(want, abs=1e-9), r["match_id"]


def test_walkovers_never_move_ratings_and_retirements_only_when_counted():
    m = history([("w", "E", "2024-01-01", "R32", "P", "Q", "walkover"), ("r", "E", "2024-01-01", "R16", "P", "X", "retired"),
                 ("c", "E2", "2024-01-08", "R32", "P", "Y")])
    ret, noret = run(m, "ret"), run(m, "noret")
    assert p_values(m, ret, 0)["r"] == E.START                      # the walkover moved nothing
    assert p_values(m, ret, 0)["c"] > E.START                       # the retirement win counted...
    assert p_values(m, noret, 0)["c"] == E.START                    # ...or was skipped
    assert p_values(m, ret, 2)["c"] == 1 and p_values(m, noret, 2)["c"] == 0


def test_surface_ratings_move_only_on_their_surface():
    m = history([("a", "E1", "2024-01-01", "F", "P", "Q"), ("b", "E2", "2024-01-08", "F", "P", "Q")],
                surfaces={"E1": "Clay", "E2": "Grass"})
    out = run(m)
    assert out[1, 4] == E.START and out[1, 5] == E.START          # grass ratings untouched by clay
    assert out[1, 0] != E.START                                    # the overall rating moved


# ------------------------------------------------------------------------------------------------
# The probe cut by date, event and round

def sequential_elo(h, k=K):
    """A leaky pass for the probe to catch: row by row, as src/ratings/elo.py updates."""
    R, out = {}, np.zeros((len(h["a"]), 2))
    for i, (a, b, aw) in enumerate(zip(h["a"], h["b"], h["a_won"])):
        ra, rb = R.get(a, E.START), R.get(b, E.START)
        out[i] = ra, rb
        s = (1.0 if aw else 0.0) - E.expected(ra, rb)
        R[a], R[b] = ra + E.k_factor(0, **k) * s, rb - E.k_factor(0, **k) * s
    return out


def test_probe_passes_the_pass_and_catches_a_row_by_row_elo():
    m = random_history(seed=5, weeks=16)
    h = E.history_arrays(m)
    upd = m["status"].isin(E.UPDATES["ret"]).tolist()

    def ours(hh):
        return E.elo_pass(hh["week"], hh["event"], hh["rnd"], hh["a"], hh["b"], hh["a_won"], hh["surf"], upd,
                          hh["n_players"], **K)

    ok = E.probe_by_round(h, ours, n_cuts=30, from_quantile=0.3)
    assert ok["protected_matches_changed"] == 0 and ok["later_matches_changed"] > 0
    bad = E.probe_by_round(h, sequential_elo, n_cuts=30, from_quantile=0.3)
    assert bad["protected_matches_changed"] > 0


# ------------------------------------------------------------------------------------------------
# Rank and points

def test_rank_regressions_use_earlier_seasons_only(monkeypatch):
    rng = np.random.default_rng(2)
    rows = []
    for y in range(2010, 2016):
        for i in range(400):
            ra, rb = rng.integers(1, 500, size=2)
            rows.append({"match_id": f"{y}-{i}", "tour": "atp", "year": y, "level": "T250", "status": "completed",
                         "evaluation": y >= 2013, "a_won": bool(rng.random() < 1 / (1 + (ra / rb) ** 0.9)),
                         "rank_a": float(ra), "rank_b": float(rb), "pts_a": 1000.0 / ra, "pts_b": 1000.0 / rb})
    m = pd.DataFrame(rows)
    monkeypatch.setattr(E, "rank_inputs", lambda mm: mm[["rank_a", "rank_b", "pts_a", "pts_b"]])
    monkeypatch.setattr(C, "TOURS", ("atp",))
    base, fits, _ = E.rank_models(m)
    flipped = m.copy()
    late = flipped["year"].eq(2015)
    flipped.loc[late, "a_won"] = ~flipped.loc[late, "a_won"]
    again, _, _ = E.rank_models(flipped)
    early = m["year"] <= 2015
    assert np.allclose(base.loc[early, "p_rank"].fillna(-1), again.loc[early, "p_rank"].fillna(-1))
    assert base.loc[m["year"] < 2013, "p_rank"].isna().all()
    assert (fits.query("input == 'rank'")["coefficient"] > 0).all()


def test_unranked_rank_is_one_below_the_worst_of_earlier_seasons():
    m = pd.DataFrame({"tour": ["atp"] * 3 + ["wta"] * 3, "year": [2010, 2011, 2012] * 2})
    r = pd.DataFrame({"rank_a": [900.0, 1200.0, 1000.0, 500, 700, 600], "rank_b": [5.0, 7, np.nan, 1, 2, 3]})
    got = E.unranked_rank(m, r)
    assert got[("atp", 2010)] == 901 and got[("atp", 2011)] == 901 and got[("atp", 2012)] == 1201
    assert got[("wta", 2012)] == 701


# ------------------------------------------------------------------------------------------------
# The odds link

def test_a_sunday_final_links_to_its_own_event_not_the_next_weeks():
    """scan.py's nearest week would take the next Monday's match (1 day) over its own event (6 days)."""
    c = pd.DataFrame({"ri": [0, 0], "li": [10, 11], "gap": [-1, 6]})
    c["sc"], c["rd"], c["dist"] = [False, True], [0, 2], c["gap"].abs()
    kept, amb, lost = O.pick(c)
    assert kept.set_index("ri").loc[0, "li"] == 11 and len(amb) == 0


def test_equal_candidates_are_ambiguous_and_a_match_takes_one_row():
    c = pd.DataFrame({"ri": [0, 0, 1, 2], "li": [5, 6, 7, 7], "gap": [2, 2, 1, 3]})
    c["sc"], c["rd"], c["dist"] = [True, True, True, True], [2, 2, 2, 2], c["gap"].abs()
    kept, amb, lost = O.pick(c)
    assert list(amb) == [0]
    assert kept.set_index("li").loc[7, "ri"] == 1 and list(lost) == [2]


@pytest.mark.parametrize("td_round, s0_round, s0_no, want", [
    (1, "R128", 1.0, 2), (1, "R32", 1.0, 2), (2, "R32", 1.0, 0), ("QF", "QF", np.nan, 2), ("F", "SF", np.nan, 0),
    ("RR", "RR", np.nan, 2), (np.nan, "R16", 2.0, 1), (3, "QF", np.nan, 0)])
def test_round_agreement(td_round, s0_round, s0_no, want):
    assert O.round_agrees(td_round, s0_round, s0_no) == want


def test_quotes_and_normalisation():
    a, b = pd.Series([1.50, 1.00, 3.0, 5.05]), pd.Series([2.60, 9.0, np.nan, 17.0])
    ok = O.coherent(a.where(a > 1.0), b)
    assert list(ok) == [True, False, False, False]          # 1.00 is not a quote; 5.05 v 17.0 is incoherent
    p = (1 / a) / (1 / a + 1 / b)
    assert p[0] + (1 / b[0]) / (1 / a[0] + 1 / b[0]) == pytest.approx(1.0)


def test_dates_outside_their_files_season():
    d = pd.to_datetime(pd.Series(["2012-10-01", "2012-12-30", "2013-06-01", "2029-07-20"]))
    s = pd.Series([2013, 2013, 2013, 2026])
    assert list(O.outside_season(d, s)) == [True, False, False, True]


# ------------------------------------------------------------------------------------------------
# The built tables (skipped until the stage has run)

BUILT = (C.OUT / "stage1_odds.parquet").exists() and (C.OUT / "stage1_baselines.parquet").exists()


@pytest.mark.skipif(not BUILT, reason="stage 1 tables not built")
def test_built_odds_table():
    o = pd.read_parquet(C.OUT / "stage1_odds.parquet")
    assert o["match_id"].is_unique
    lk = o[o["link"].ne("none")]
    assert not lk.duplicated(["td_file", "td_row"]).any()                 # one match per tennis-data row
    p = o["p_avg_a"].dropna()
    assert ((p > 0) & (p < 1)).all()
    assert o.loc[o["p_avg_a"].notna(), "overround_avg"].between(*O.OVERROUND_OK).all()
    assert o.loc[o["link"].eq("none"), "p_avg_a"].isna().all()


@pytest.mark.skipif(not BUILT, reason="stage 1 tables not built")
def test_built_baselines_table():
    b = pd.read_parquet(C.OUT / "stage1_baselines.parquet")
    m = C.load_matches(["match_id", "evaluation"])
    assert len(b) == len(m) and b["match_id"].is_unique
    ev = b[b["evaluation"]]
    for col in ("p_coin", "p_rank", "p_points", "p_elo_ret", "p_elo_noret", "p_elo_surf_ret", "p_elo_surf_noret"):
        assert ev[col].notna().all(), col
        assert ev[col].between(0, 1, inclusive="neither").all(), col
    assert b["p_elo_ret"].notna().all()
    assert b.loc[~b["evaluation"], ["p_rank", "p_market"]].isna().all().all()
