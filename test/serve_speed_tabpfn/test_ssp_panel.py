"""Tests T-P1 to T-P8 of design/2_audit.md (C7), plus checks of the fixed panel API, for
src/eda/serve_speed_tabpfn/panel.py. They read the built outputs: run
    ./python.sh src/eda/serve_speed_tabpfn/panel.py
first, then
    ./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_panel.py -q
No test reads a match result.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402

# an independent list of result-like names (the module's own list is not trusted here)
RESULT_LIKE = {"a_won", "won", "winner", "winner_id", "loser", "loser_id", "score", "sets", "games", "sets_won",
               "games_won", "status_detail", "minutes", "match_winner", "winner_team", "p_mkt", "in_odds_logit"}
API_COLUMNS = ["match_id", "side", "player_id", "tour", "year", "level", "qualifying", "tournament_id", "tdate",
               "round_order", "es", "lf", "obs", "y", "n", "basis", "edition", "family", "source", "use",
               "drop_reason"]


@pytest.fixture(scope="module")
def panel_all() -> pd.DataFrame:
    assert P.PANEL.exists(), "build the panel first: ./python.sh src/eda/serve_speed_tabpfn/panel.py"
    return P.load_panel(use_only=False)


@pytest.fixture(scope="module")
def panel_use(panel_all) -> pd.DataFrame:
    return panel_all[panel_all["use"]].reset_index(drop=True)


@pytest.fixture(scope="module")
def records() -> pd.DataFrame:
    assert P.RECORDS.exists()
    return pd.read_parquet(P.RECORDS)


@pytest.fixture(scope="module")
def frame_keys() -> pd.DataFrame:
    assert P.FRAME_KEYS.exists()
    return P.load_frame_keys()


# ------------------------------------------------------------------------------------------------
def test_tp1_one_row_per_player_match_and_no_result_columns(panel_all, records, frame_keys):
    """T-P1: one row per (match_id, side); no column list names a result. ('result' in the MatchBeats point list is
    the point's ending code: A, W, FE, UE, DF.)"""
    assert not panel_all.duplicated(["match_id", "side"]).any()
    for name in ("S0_COLS", "S0_PRE_COLS", "TIMING_COLS", "FRAME_COLS", "SPEEDS_COLS", "LINK_COLS", "POINT_COLS",
                 "INFO_SLAMS_COLS", "AO_STATS_COLS"):
        cols = set(getattr(P, name))
        assert not cols & RESULT_LIKE, (name, cols & RESULT_LIKE)
    for df in (panel_all, records, frame_keys):
        assert not set(df.columns) & RESULT_LIKE
    src = inspect.getsource(P)
    assert "a_won" not in src.replace('"a_won", "won"', "")      # the module names a_won only in its own block list


def test_api_columns_and_types(panel_all, panel_use):
    for c in API_COLUMNS:
        assert c in panel_all.columns, c
    for c in ("tdate", "es", "lf", "obs", "n", "round_order"):
        assert pd.api.types.is_integer_dtype(panel_all[c]), c
    assert panel_all["use"].dtype == bool
    assert set(panel_all["tour"]) <= {"atp", "wta"}
    assert set(panel_all["basis"]) <= {"pts", "ks"}
    assert (panel_use["drop_reason"] == "").all()
    assert (panel_all.loc[~panel_all["use"], "drop_reason"] != "").all()
    # the clock: es <= obs <= lf for every use row; ks-first at tour level, points first at the Slams
    assert ((panel_use["es"] <= panel_use["obs"]) & (panel_use["obs"] <= panel_use["lf"])).all()
    non_slam_both = panel_use[panel_use["level"].ne("GS") & panel_use["spd1_ks"].notna()]
    assert (non_slam_both["basis"] == "ks").all()
    slam_pts = panel_use[panel_use["level"].eq("GS") & panel_use["spd1_pts"].notna()]
    assert (slam_pts["kind"] == "point_mean").all()
    # harmonisation: key statistics - 0.5, AO match centre + 0.5, point means as they are
    for kind, shift in (("keystat", -0.5), ("mc_floor", 0.5), ("point_mean", 0.0)):
        k = panel_all[panel_all["kind"].eq(kind)]
        assert np.allclose(k["y"] - k["y_raw"], shift)
    # loading with use_only gives the use rows
    assert len(P.load_panel()) == len(panel_use)


def test_tp2_copies_agree(records):
    """T-P2: slam_pbp - slamtracker sd < 0.1; ManTennisData equals the handoff on >= 99.8% of shared rows."""
    v = records[records["valid"]]
    a = v[v["source"].eq("slam_pbp")][["match_id", "side", "y"]]
    b = v[v["source"].eq("slamtracker")][["match_id", "side", "y"]]
    j = a.merge(b, on=["match_id", "side"])
    assert len(j) > 2000
    assert float((j["y_x"] - j["y_y"]).std()) < 0.1
    m = v[v["source"].eq("mantennisdata")][["match_id", "side", "y_raw"]]
    h = v[v["source"].eq("handoff_ks")][["match_id", "side", "y_raw"]]
    k = m.merge(h, on=["match_id", "side"])
    assert len(k) > 10000
    assert float((np.abs(k["y_raw_x"] - k["y_raw_y"]) < 1e-9).mean()) >= 0.998


def test_tp3_ceiling_rule(records):
    """T-P3: KS = ceil(point mean) on >= 75% of complete point tables, seasons <= 2023."""
    ks = records[records["valid"] & records["source"].eq("mantennisdata")][["match_id", "side", "y_raw", "ks_first_in",
                                                                            "year_s0"]]
    pt = records[records["source"].eq("infosys") & records["linked"]][["match_id", "side", "y_raw", "f1", "n1"]]
    j = ks.merge(pt, on=["match_id", "side"], suffixes=("_ks", "_pt"))
    j = j[j["year_s0"] <= 2023]
    complete = j[(j["f1"] == j["ks_first_in"]) & (j["n1"] == j["f1"])]
    assert len(complete) > 1000
    share = float((complete["y_raw_ks"] == np.ceil(complete["y_raw_pt"] - 1e-9)).mean())
    assert share >= 0.75, share


def test_tp4_presence_reproduces_n2(panel_all):
    """T-P4: both-sides 14-day presence on Stage 0's main-tour main draws equals the acquisition's N2 counts within 1%
    or 5 matches in every tour x year x Slam cell."""
    v = P.validation_n2(panel_all)
    assert len(v) == 48
    assert v["N2_slams"].notna().all()
    assert v["ok"].all(), v[~v["ok"]].to_string()


def test_tp5_qf_mislinks_dropped_and_draw_never_read(records, panel_use):
    """T-P5: every QF-labelled ManTennisData row linked to a non-QF Stage 0 match is dropped (10); `draw` is never
    read from speeds.parquet."""
    q = records[records["source"].eq("mantennisdata") & records["round_src"].eq("QF") & records["linked"]
                & records["round_s0"].ne("QF")]
    assert len(q) == 10
    assert (~q["valid"]).all() and (q["invalid_reason"] == "mislink_round").all()
    # no use row carries a mislinked record (the match's own ManTennisData record may still be used)
    used = panel_use[panel_use["source"].eq("mantennisdata")]
    hit = used.merge(q[["match_id", "side", "source_key"]], on=["match_id", "side", "source_key"])
    assert hit.empty
    # every ManTennisData row whose round differs from Stage 0's is invalid
    rm = records[records["source"].eq("mantennisdata") & records["linked"] & records["round_src"].notna()
                 & (records["round_src"] != records["round_s0"])]
    assert (~rm["valid"]).all()
    assert "draw" not in P.SPEEDS_COLS
    src = inspect.getsource(P)
    assert src.count("read_parquet(SPEEDS") == 1
    assert "read_parquet(SPEEDS, columns=SPEEDS_COLS)" in src


def test_tp6_ao_2026(panel_use):
    """T-P6: AO 2026 holds >= 470 rows per tour."""
    ao = panel_use[panel_use["slam"].eq("AO") & panel_use["year"].eq(2026)]
    counts = ao.groupby("tour").size()
    assert counts.get("atp", 0) >= 470 and counts.get("wta", 0) >= 470, counts.to_dict()


def _cut_days(frame_keys: pd.DataFrame, tour: str, k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    d = np.unique(frame_keys.loc[frame_keys["tour"].eq(tour) & frame_keys["season"].between(2014, 2026), "es"])
    return np.sort(rng.choice(d, k, replace=False))


def _cut_days_in_events(panel_use: pd.DataFrame, tour: str, k: int, seed: int) -> np.ndarray:
    """Cut days inside timed events: the day before a timed match whose event started at least two days earlier, so
    rows that began by the cut but surely finished after it exist (the leaky control has something to leak)."""
    rng = np.random.default_rng(seed)
    q = panel_use[panel_use["tour"].eq(tour) & panel_use["year"].between(2014, 2026)
                  & (panel_use["es"] - panel_use["tdate"] >= 2)]
    d = np.unique(q["es"].to_numpy() - 1)
    return np.sort(rng.choice(d, k, replace=False))


def test_tp7_asof_offsets_ignore_later_speeds(panel_use, frame_keys):
    """T-P7: gamma(D) is unchanged for D = C, C - 1, C - 7 and C - 100 when the speeds of rows with es > C are noised
    (25 cut days C inside timed events, 13 men's and 12 women's, 2014-2026). Leaky control: the same fit admitting rows
    by tournament start (tdate <= D) moves gamma(C) in at least 80% of the cuts."""
    rng = np.random.default_rng(7)
    cuts = [("atp", c) for c in _cut_days_in_events(panel_use, "atp", 13, 1)] + \
           [("wta", c) for c in _cut_days_in_events(panel_use, "wta", 12, 2)]
    assert len(cuts) == 25
    clean = {t: P.EditionOffsets(panel_use, t, cache=False) for t in ("atp", "wta")}
    leaky_moved = 0
    for tour, c in cuts:
        noisy = panel_use.copy()
        late = noisy["es"] > c
        noisy.loc[late, "y"] = rng.uniform(100, 250, int(late.sum()))
        eo = P.EditionOffsets(noisy, tour, cache=False)
        for d in (c, c - 1, c - 7, c - 100):
            assert np.array_equal(eo.at(int(d)).to_numpy(), clean[tour].at(int(d)).to_numpy()), (tour, c, d)
        lk_clean = P.EditionOffsets(panel_use, tour, cache=False, release="tdate")
        lk_noisy = P.EditionOffsets(noisy, tour, cache=False, release="tdate")
        if not np.allclose(lk_clean.at(int(c)).to_numpy(), lk_noisy.at(int(c)).to_numpy(), atol=1e-9, rtol=0):
            leaky_moved += 1
    assert leaky_moved >= 0.8 * len(cuts), leaky_moved


def test_tp8_frame_join(frame_keys):
    """T-P8: one-to-one with all 63,737 frame matches; 21 flips and 67 conflicts flagged (id_conflict marks all 88);
    sides follow the frame's own pre-rebuild ids."""
    fk = frame_keys
    assert len(fk) == 63737 and fk["match_id"].is_unique
    frame = pd.read_parquet(P.MODEL_FRAME, columns=["match_id"])
    assert set(fk["match_id"]) == set(frame["match_id"])
    assert int(fk["flipped"].sum()) == 21
    assert int((fk["id_conflict"] & ~fk["flipped"]).sum()) == 67
    assert int(fk["id_conflict"].sum()) == 88
    pre = pd.read_parquet(P.pre_rebuild_stage0(), columns=["match_id", "player_a_id", "player_b_id"])
    j = fk.merge(pre, on="match_id", suffixes=("", "_pre"), validate="one_to_one")
    assert (j["player_a_id"] == j["player_a_id_pre"]).all() and (j["player_b_id"] == j["player_b_id_pre"]).all()
    s0 = pd.read_parquet(P.S0, columns=["match_id"])
    assert fk["rebuilt_id"].isin(set(s0["match_id"])).all()
    assert int((fk["rebuilt_id"] != fk["match_id"]).sum()) == 40
    for c in ("es", "lf", "obs", "tdate", "round_order"):
        assert pd.api.types.is_integer_dtype(fk[c]), c
    assert ((fk["es"] <= fk["obs"]) & (fk["obs"] <= fk["lf"])).all()
    # the 88 are all women's 2026
    conf = fk[fk["id_conflict"]]
    assert set(conf["tour"]) == {"wta"} and set(conf["season"]) == {2026}


def test_edition_offsets_api(panel_use, frame_keys):
    """The fixed API: at(day) covers every edition of the tour; unreleased editions take their family's unweighted
    in-window mean, else 0; fewer than 50 rows give all 0; gamma() is the vectorised lookup; the disk cache equals a
    fresh fit."""
    for tour in ("atp", "wta"):
        eo = P.EditionOffsets(panel_use, tour)
        fresh = P.EditionOffsets(panel_use, tour, cache=False)
        assert eo._disk is not None, "the snapshot cache should match the built panel"
        eds = set(panel_use.loc[panel_use["tour"].eq(tour), "edition"])
        for d in _cut_days(frame_keys, tour, 20, 11):
            s = eo.at(int(d))
            assert set(s.index) == eds and np.isfinite(s.to_numpy()).all()
            assert np.allclose(s.to_numpy(), fresh.at(int(d)).to_numpy(), atol=1e-12, rtol=0)
            # unreleased editions: family mean of the in-window fitted editions, else 0
            eu, g, n_e, fu, fm = fresh.fit(int(d))
            fitted = set(eo.editions[eu])
            fam_mean = dict(zip(eo.families[fu], fm))
            others = [e for e in s.index if e not in fitted]
            fam = dict(zip(eo.editions, eo.ed_family))
            exp = np.array([fam_mean.get(fam[e], 0.0) for e in others])
            assert np.allclose(s[others].to_numpy(), exp, atol=1e-12, rtol=0)
            # the family means are unweighted means of the fitted editions' gammas
            for f_, m_ in fam_mean.items():
                members = [i for i, e in enumerate(eo.editions[eu]) if fam[e] == f_]
                assert abs(np.mean(g[members]) - m_) < 1e-12
            ix = np.array(list(s.index[:50]) + ["not-an-edition"])
            got = eo.gamma(ix, int(d))
            assert np.allclose(got[:-1], s.iloc[:50].to_numpy()) and got[-1] == 0.0
        assert (eo.at(14000).to_numpy() == 0).all()                 # before any data: fewer than 50 rows
