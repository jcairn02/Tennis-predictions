"""Adversarial actual-day ordering checks for every retained rating/form path."""
import numpy as np
import pandas as pd

from src.eda.feature_alpha_audit import repair_history as H
from src.eda.feature_alpha_audit.chronology import AP, D, frozen_profile
from src.eda.ufc_ideas import stageB_common as B
from src.eda.ufc_ideas import stageB_ios as I


def history():
    matches, players, odds = [], [], []
    # old event-start ordering places LONG's final before OVERLAP's first round.
    spec = [("warm", "WARM", 0, 1, 10, "a", "b"),
            ("future", "LONG", 2, 12, 20, "a", "b"),
            ("target", "OVERLAP", 6, 8, 10, "a", "c"),
            ("same_other", "OTHER", 6, 8, 10, "a", "d"),
            ("later_round", "OVERLAP", 6, 8, 11, "a", "c"),
            ("after", "AFTER", 19, 20, 10, "a", "b")]
    start = pd.Timestamp("2016-01-01")
    for order, (mid, event, event_day, match_day, rnd, pa, pb) in enumerate(spec):
        matches.append({"match_id": mid, "tour": "atp", "year": 2016, "level": "T250", "qualifying": False,
                        "evaluation": True, "round_order": rnd, "tournament_date": start + pd.Timedelta(days=event_day),
                        "tournament_id": event, "order": order, "surface": "Hard", "status": "completed",
                        "format": "standard", "has_box": True, "player_a_id": pa, "player_b_id": pb,
                        "a_won": True, "best_of": 3, "tournament_name": event, "round": "R32"})
        odds.append({"match_id": mid, "td_date": start + pd.Timedelta(days=match_day), "td_redated": False,
                     "link": "name_pair", "round_agrees": "yes", "same_set_scores": True, "p_avg_a": .6})
        for side, pid, oid in [("A", pa, pb), ("B", pb, pa)]:
            r = {"match_id": mid, "side": side, "player_id": pid, "opponent_id": oid, "won": side == "A",
                 "age": {"a": 29., "b": 30., "c": 21., "d": 27.}[pid]}
            for s in B.C.RATES:
                r[f"{s}_n"], r[f"{s}_d"] = (32. if side == "A" else 24.), 50.
            r["sets_won_n"], r["sets_won_d"] = (2. if side == "A" else 0.), 2.
            players.append(r)
    return pd.DataFrame(matches), pd.DataFrame(players), pd.DataFrame(odds)


def rows_and_constants():
    matches, players, odds = history()
    selected, _ = H.select_dated_matches(matches, odds)
    rows = H.build_rows(selected, players, odds)
    elo = {"atp": {"k0": 250., "offset": 5., "shape": .4, "w": .3}}
    sr = {"atp": {"var_serve": .02, "var_return": .005, "drift": .0002}}
    mu = {("atp", "all"): .4, ("atp", "Hard"): .4}
    return rows, elo, sr, mu


def test_date_evidence_fails_closed_and_preserves_event_identity():
    matches, players, odds = history()
    odds.loc[odds.match_id.eq("future"), "td_date"] = pd.NaT
    odds.loc[odds.match_id.eq("same_other"), "td_redated"] = True
    odds.loc[odds.match_id.eq("after"), "round_agrees"] = "no"
    selected, audit = H.select_dated_matches(matches, odds)
    assert set(selected.match_id) == {"warm", "target", "later_round"}
    assert audit.set_index("match_id").at["future", "reason"] == "no_match_day"
    assert selected.tournament_date.is_monotonic_increasing
    assert selected.loc[selected.match_id.eq("target"), "original_tournament_date"].iloc[0] == pd.Timestamp("2016-01-07")
    assert selected.loc[selected.match_id.isin(["target", "later_round"]), "tournament_id"].nunique() == 1
    rows = H.build_rows(selected, players, odds)
    assert rows.side.tolist() == ["A", "B"] * 3
    assert rows.match_id.iloc[::2].tolist() == selected.match_id.tolist()


def test_pairs_use_match_days_and_only_earlier_rounds_on_same_day():
    rows, *_ = rows_and_constants()
    p = B.PairIndex(rows, np.arange(len(rows)))
    got = {(rows.match_id.iloc[p.order[t]], rows.match_id.iloc[p.order[s]])
           for tt, ss, _ in p.chunks() for t, s in zip(tt, ss)}
    assert ("target", "future") not in got
    assert ("target", "warm") in got
    assert ("target", "same_other") not in got
    assert ("later_round", "target") in got
    assert ("later_round", "same_other") not in got
    assert ("after", "future") in got


def test_retrospective_whole_event_format_cannot_change_history_eligibility():
    matches, players, odds = history()
    changed = matches.copy()
    # Simulate a later score causing Stage 0 to reclassify entire prior events.
    changed.loc[changed.tournament_id.isin(["WARM", "LONG"]), "format"] = "match_tiebreak"
    first, _ = H.select_dated_matches(matches, odds)
    second, _ = H.select_dated_matches(changed, odds)
    original_rows, new_rows = H.build_rows(first, players, odds), H.build_rows(second, players, odds)
    assert original_rows.observed_format.ne(new_rows.observed_format).any()
    for column in ("format", "box_hist", "history_format_supported"):
        np.testing.assert_array_equal(original_rows[column], new_rows[column])
    _, elo, sr, mu = rows_and_constants()
    _, before, _ = H.rebuild_ratings(original_rows, elo, sr, mu)
    _, after, _ = H.rebuild_ratings(new_rows, elo, sr, mu)
    np.testing.assert_array_equal(before[["serve_a", "serve_b", "return_a", "return_b"]],
                                  after[["serve_a", "serve_b", "return_a", "return_b"]])


def test_unsupported_edition_excluded_from_box_history_regardless_of_observed_score():
    matches, players, odds = history()
    matches["tour"], matches["year"], matches["tournament_name"] = "wta", 2021, "Grampians Trophy"
    matches["tournament_date"] = matches.tournament_date.map(lambda d: d.replace(year=2021))
    odds["td_date"] = odds.td_date.map(lambda d: d.replace(year=2021))
    matches.loc[matches.match_id.eq("future"), "format"] = "match_tiebreak"
    selected, _ = H.select_dated_matches(matches, odds)
    rows = H.build_rows(selected, players, odds)
    assert set(rows.observed_format) == {"standard", "match_tiebreak"}
    assert not rows.history_format_supported.any()
    assert not rows.box_hist.any()


def test_mutating_overlapping_event_future_result_cannot_change_elo_or_sr():
    rows, elo, sr, mu = rows_and_constants()
    changed = rows.copy()
    hit = changed.match_id.eq("future")
    changed.loc[hit, "won"] = ~changed.loc[hit, "won"]
    changed.loc[hit, "spw_n"] = changed.loc[hit, "spw_d"] - changed.loc[hit, "spw_n"]
    _, before, _ = H.rebuild_ratings(rows, elo, sr, mu)
    _, after, _ = H.rebuild_ratings(changed, elo, sr, mu)
    columns = ["p_elo", "serve_a", "serve_b", "return_a", "return_b"]
    protected = before.match_id.isin(["warm", "target", "same_other", "later_round", "future"])
    np.testing.assert_array_equal(before.loc[protected, columns], after.loc[protected, columns])
    assert not np.allclose(before.loc[~protected, columns], after.loc[~protected, columns])


def test_mutating_overlap_future_box_cannot_change_adjperf_or_ios():
    rows, *_ = rows_and_constants()
    changed = rows.copy()
    hit = changed.match_id.eq("future")
    for s in B.C.RATES:
        changed.loc[hit, f"{s}_n"] = changed.loc[hit, f"{s}_d"] - changed.loc[hit, f"{s}_n"]
    means = {s: {(t, sf): .5 for t in B.C.TOURS for sf in ("all", "Hard", "Clay", "Grass", "Carpet")} for s in B.STATS}
    typ = {(s, t): 50. for s in B.STATS for t in B.C.TOURS}
    mad = {(s, ch, t, 0): .4 for s in D.ADJ_STATS for ch in AP.CHANNELS for t in B.C.TOURS}
    chosen = {(t, s): {"h1": 52., "K1": 2., "tau": 0, "h3": 2., "K3": 10.}
              for t in B.C.TOURS for s in AP.CORE}
    ctx = AP.Ctx(rows, means, typ=typ, madpop=mad, stats=D.ADJ_STATS)
    ctx2 = AP.Ctx(changed, means, typ=typ, madpop=mad, stats=D.ADJ_STATS)
    f1, f2 = frozen_profile(ctx, chosen), frozen_profile(ctx2, chosen)
    protected = rows.match_id.to_numpy()[ctx.A] != "after"
    for c in f1:
        np.testing.assert_allclose(f1[c][protected], f2[c][protected], atol=1e-12, equal_nan=True)
    assert not np.isclose(f1["adjperf_first_won|decayed"][-1], f2["adjperf_first_won|decayed"][-1])
    results = []
    for r in (rows, changed):
        td = I.tour_inputs(r, B.stat_arrays(r, means), typ, "atp")
        results.append(I.run(td, "spw", h=4., kappa=1., tau=1))
    protected_rows = rows.match_id.ne("after").to_numpy()
    for c in ("O", "D"):
        np.testing.assert_allclose(results[0][c][protected_rows], results[1][c][protected_rows], atol=1e-10)
    assert not np.allclose(results[0]["O"][~protected_rows], results[1]["O"][~protected_rows])
