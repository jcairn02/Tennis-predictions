"""Targeted chronology sensitivity tests: date mapping and history visibility."""
import numpy as np
import pandas as pd

from src.eda.feature_alpha_audit.chronology import calendar_monday, normalize_rows, frozen_profile, D, AP
from src.eda.ufc_ideas import stageB_common as B


def test_calendar_week_includes_sunday_and_year_boundary():
    got = calendar_monday(pd.Series(pd.to_datetime(["2026-09-28", "2026-10-02", "2026-10-04", "2026-01-01"])))
    assert list(got.dt.strftime("%Y-%m-%d")) == ["2026-09-28", "2026-09-28", "2026-09-28", "2025-12-29"]


def test_normalized_pairs_block_midweek_other_event_keep_earlier_round():
    records = []
    for i, (day, event, rnd, opponent) in enumerate([(0, "E1", 13, "P2"), (2, "E2", 13, "P3"), (2, "E2", 14, "P4")]):
        for j, player in enumerate(["P1", opponent]):
            records.append({"match_id": str(i), "order": i, "player_id": player, "surface": "Hard",
                            "level": "T250", "qualifying": False, "tournament_id": event, "round_order": rnd,
                            "tournament_date": pd.Timestamp("2016-01-04") + pd.Timedelta(days=day),
                            "status": "completed", "format": "standard", "year": 2016, "won": j == 0})
    rows = B.F.prepare(pd.DataFrame(records))
    norm = normalize_rows(rows)
    assert np.array_equal(rows["match_id"], norm["match_id"])
    assert np.array_equal(rows["year"], norm["year"])
    assert (norm["day"] == norm["day"].iloc[0]).all()
    pairs = B.PairIndex(norm, np.arange(len(norm)))
    got = {(int(pairs.order[i]), int(pairs.order[j]))
           for ii, jj, _ in pairs.chunks() for i, j in zip(ii, jj)}
    assert (2, 0) not in got
    assert (4, 0) not in got
    assert (4, 2) in got


def test_restricted_profile_matches_original_builder():
    records = []
    for i in range(4):
        for j, player in enumerate(["P1", "P2"]):
            row = {"match_id": str(i), "order": i, "player_id": player, "surface": "Hard", "tour": "atp",
                   "level": "T250", "qualifying": False, "tournament_id": str(i), "round_order": 13,
                   "tournament_date": pd.Timestamp("2016-01-04") + pd.Timedelta(days=7 * i),
                   "status": "completed", "format": "standard", "year": 2016, "won": j == 0}
            for s in B.C.RATES:
                row[f"{s}_n"], row[f"{s}_d"] = 10.0 + i + 3 * j, 50.0
            records.append(row)
    rows = B.F.prepare(pd.DataFrame(records))
    stats = D.ADJ_STATS
    means = {s: {(t, sf): .5 for t in B.C.TOURS for sf in ("all", "Hard", "Clay", "Grass", "Carpet")} for s in stats}
    typ = {(s, t): 50.0 for s in stats for t in B.C.TOURS}
    mad = {(s, ch, t, 0): .4 for s in stats for ch in AP.CHANNELS for t in B.C.TOURS}
    chosen = {(t, s): {"h1": 52., "K1": 2., "tau": 0, "h3": 2., "K3": 10.}
              for t in B.C.TOURS for s in AP.CORE}
    ctx = AP.Ctx(rows, means, typ=typ, madpop=mad, stats=stats)
    got = frozen_profile(ctx, chosen)
    reference = AP.build(ctx, chosen)["features"]
    for col, values in got.items():
        assert np.isfinite(values).any()
        np.testing.assert_allclose(values, reference[col], rtol=0, atol=1e-14, equal_nan=True)
