"""Tests of the tour-pooling study's shared definitions (src/eda/tour_pooling/common.py), on the real frame (read only).

Run: ./python.sh -m pytest test/tour_pooling/test_common.py -q

Results. The frame is read without a_won. job_data is given synthetic labels (all 0) wherever only rows, columns and
queries are checked. Two checks need the true training labels (the fingerprint against the current instance's stored
fit, and the fingerprints of fits already written): they read a_won with a filter applied at read time, seasons
<= Y - 1 and tournament_date < 2026-07-29, so no sealed result is loaded.

Nothing here writes to the study's folders: every borrowsim check skips when its cache file is absent (sim_inclusion
would otherwise build and write it), and the synthetic sim_inclusion test writes to pytest's temporary folder.
Seasons 2019, 2022 and 2026 stand for the rest.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402

SEASONS = (2019, 2022, 2026)
SEALED = datetime(2026, 7, 29)                       # the proposed sealed holdout: events from 29 Jul 2026
PER_TOUR = [a for a, k in C.ARMS.items() if k == "per_tour"]
BOTH = [a for a, k in C.ARMS.items() if k == "both"]
FIT_RE = re.compile(r"^(?P<arm>[a-z0-9]+)__(?P<tour>atp|wta|both)__(?P<season>\d{4})__seed(?P<seed>\d+)\.npz$")
COMMON_SCALE = {"odds_logit", "ratings_iid", "elo_games", "points_52w", "sets_14d", "age", "age_sq", "elo_overall",
                "elo_surf_offset"}


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    f = C.load_frame()
    assert "a_won" not in f.columns
    return f


@pytest.fixture(scope="module")
def X(frame) -> pd.DataFrame:
    return SA.matrix(frame, C.base_inputs())


@pytest.fixture(scope="module")
def instance_meta() -> dict:
    with np.load(C.INSTANCE / "fits" / "model__2022__seed0.npz", allow_pickle=False) as z:
        return json.loads(str(z["meta"]))


def fake_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Synthetic labels: job_data needs a column; these tests check rows, columns and queries only."""
    return frame.assign(a_won=0)


def training_labels(frame: pd.DataFrame, last_season: int) -> pd.DataFrame:
    """The frame with a_won for seasons <= last_season only (filtered at read, never a sealed match); NaN elsewhere, so
    job_data fails loudly if it ever reads a label outside the training seasons."""
    assert last_season <= 2025
    t = pq.read_table(C.P.model_frame, columns=["match_id", "season", "tournament_date", "a_won"],
                      filters=[("season", "<=", last_season), ("tournament_date", "<", SEALED)]).to_pandas()
    assert t["season"].max() <= last_season and t["tournament_date"].max() < pd.Timestamp(SEALED)
    y = pd.Series(t["a_won"].astype(float).to_numpy(), index=t["match_id"].astype(str).to_numpy())
    return frame.assign(a_won=y.reindex(frame["match_id"].astype(str).to_numpy()).to_numpy())


def pools(frame: pd.DataFrame, tour: str, season: int):
    s, t = frame["season"].to_numpy(), frame["tour"].to_numpy()
    pool = (s >= C.TRAIN_FROM) & (s <= season - 1)
    return pool, pool & (t == tour), pool & (t != tour)


# ------------------------------------------------------------------------------------------------
# The frame and the inputs

def test_frame_tours_seasons_and_the_tour_input(frame):
    assert set(frame["tour"].unique()) == set(C.TOURS)
    assert np.array_equal(frame["in_tour"].to_numpy(float), (frame["tour"].to_numpy() == "wta").astype(float))
    assert frame["match_id"].is_unique
    assert frame["season"].min() == C.TRAIN_FROM and frame["season"].max() == 2026


def test_inputs_are_the_instances_58_in_order_and_notour_drops_only_tour():
    names = [d["name"] for d in json.loads(C.P.model_inputs.read_text(encoding="utf-8"))["inputs"]]
    assert C.base_inputs() == names and len(names) == 58 and "tour" in names
    assert C.inputs("notour") == [c for c in names if c != "tour"] and len(C.inputs("notour")) == 57
    for arm in C.ARMS:
        if arm != "notour":
            assert C.inputs(arm) == names


@pytest.mark.parametrize("arm", list(C.ARMS))
def test_the_swap_is_an_involution_for_every_arms_inputs(frame, arm):
    assert SA.check_flip(frame, C.inputs(arm), C.P)


def test_model_tours_and_mask_refusals(frame):
    for arm in PER_TOUR:
        assert C.model_tours(arm) == C.TOURS
        with pytest.raises(ValueError):
            C.train_mask(frame, arm, "both", 2022, 0)
    for arm in BOTH:
        assert C.model_tours(arm) == ("both",)
        with pytest.raises(ValueError):
            C.train_mask(frame, arm, "atp", 2022, 0)


# ------------------------------------------------------------------------------------------------
# Training rows

@pytest.mark.parametrize("season", SEASONS)
def test_both_tour_arms_train_on_the_whole_pool(frame, season):
    pool, _, _ = pools(frame, "atp", season)
    for arm in BOTH:
        for seed in C.SEEDS:
            assert np.array_equal(C.train_mask(frame, arm, "both", season, seed), pool)


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_split_is_exactly_the_own_tours_pool(frame, season, tour):
    _, own, _ = pools(frame, tour, season)
    for seed in C.SEEDS:
        assert np.array_equal(C.train_mask(frame, "split", tour, season, seed), own)


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("arm", ["borrow25", "borrow50"])
@pytest.mark.parametrize("tour", C.TOURS)
def test_borrow_keeps_every_own_row_and_exactly_its_share_of_the_other_tour(frame, season, arm, tour):
    pool, own, other = pools(frame, tour, season)
    masks = [C.train_mask(frame, arm, tour, season, k) for k in C.SEEDS]
    for m in masks:
        assert not (m & ~pool).any()                                  # 2013 .. Y - 1 only
        assert np.array_equal(m & own, own)                           # every own row
        assert int((m & other).sum()) == int(round(C.BORROW_SHARE[arm] * other.sum()))
    assert all(not np.array_equal(masks[0], m) for m in masks[1:])    # drawn anew per seed
    assert np.array_equal(masks[0], C.train_mask(frame, arm, tour, season, 0))     # reproducible


def _overlap_z(a: np.ndarray, b: np.ndarray, n: int) -> float:
    """z of the overlap of two draws of a.sum() and b.sum() rows out of the same n, if they were independent."""
    ka, kb, ov = int(a.sum()), int(b.sum()), int((a & b).sum())
    var = ka * kb * (n - ka) * (n - kb) / (n ** 2 * (n - 1))
    return (ov - ka * kb / n) / np.sqrt(var)


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_borrow25_is_nested_in_borrow50(frame, season, tour):
    """The coupled draws (amended 9 Oct 2026, red team S2): borrow25's other-tour rows are a subset of borrow50's."""
    _, _, other = pools(frame, tour, season)
    for seed in C.SEEDS:
        b25 = C.train_mask(frame, "borrow25", tour, season, seed) & other
        b50 = C.train_mask(frame, "borrow50", tour, season, seed) & other
        assert not (b25 & ~b50).any()


def test_borrow_draws_are_independent_across_seeds_and_seasons(frame):
    tour, season = "wta", 2022
    _, _, other = pools(frame, tour, season)
    n = int(other.sum())

    def drawn(arm, Y, k):
        return C.train_mask(frame, arm, tour, Y, k) & other

    z = {"seed 0 vs 1": _overlap_z(drawn("borrow50", season, 0), drawn("borrow50", season, 1), n),
         "seed 2 vs 3 (25%)": _overlap_z(drawn("borrow25", season, 2), drawn("borrow25", season, 3), n),
         "2022 vs 2023": _overlap_z(drawn("borrow50", season, 0), drawn("borrow50", season + 1, 0), n)}
    assert all(abs(v) < 6 for v in z.values()), z
    a = C.rng("borrow50", "atp", season, 0).random(4)
    assert not np.array_equal(a, C.rng("borrow50", "wta", season, 0).random(4))


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_sizectl_is_a_random_draw_of_the_whole_pool_as_large_as_the_own_tour(frame, season, tour):
    pool, own, other = pools(frame, tour, season)
    masks = [C.train_mask(frame, "sizectl", tour, season, k) for k in C.SEEDS]
    n, k = int(pool.sum()), int(own.sum())
    for m in masks:
        assert not (m & ~pool).any() and int(m.sum()) == k
        assert abs(_overlap_z(m, other, n)) < 6                  # both tours, in the pool's mix
        assert not np.array_equal(m, own)
    assert not np.array_equal(masks[0], masks[1])
    assert np.array_equal(masks[0], C.train_mask(frame, "sizectl", tour, season, 0))


# ------------------------------------------------------------------------------------------------
# Query rows and job data

@pytest.mark.parametrize("season", SEASONS)
def test_query_rows_are_the_seasons_matches_of_the_models_tours(frame, season):
    s, t = frame["season"].to_numpy(), frame["tour"].to_numpy()
    both = C.query_mask(frame, "both", season)
    assert np.array_equal(both, s == season)
    per = {tour: C.query_mask(frame, tour, season) for tour in C.TOURS}
    for tour, m in per.items():
        assert np.array_equal(m, (s == season) & (t == tour))
    assert not (per["atp"] & per["wta"]).any() and np.array_equal(per["atp"] | per["wta"], both)


@pytest.mark.parametrize("arm", [a for a in C.ARMS if a != "borrowsim"])
def test_job_data_rows_columns_and_query_order(frame, arm):
    f = fake_labels(frame)
    season, seed = 2022, 1
    cols = C.inputs(arm)
    Xa = SA.matrix(frame, cols)
    if arm == "aligned":
        Xa = C.align(Xa, frame, season)
    for tour in C.model_tours(arm):
        X_train, y_train, X_query, ids, tr = C.job_data(f, arm, tour, season, seed)
        te = C.query_mask(frame, tour, season)
        k = int(te.sum())
        assert np.array_equal(tr, C.train_mask(frame, arm, tour, season, seed))
        assert list(X_train.columns) == cols and list(X_query.columns) == cols
        assert X_train.shape == (int(tr.sum()), len(cols)) and len(y_train) == int(tr.sum())
        assert np.array_equal(X_train.to_numpy(float), Xa[tr].to_numpy(float), equal_nan=True)
        assert len(X_query) == 2 * k and ids.tolist() == frame.loc[te, "match_id"].astype(str).tolist()
        Xt = Xa[te].reset_index(drop=True)
        assert np.array_equal(X_query.iloc[:k].to_numpy(float), Xt.to_numpy(float), equal_nan=True)
        assert np.array_equal(X_query.iloc[k:].to_numpy(float), SA.flip(Xt, C.P).to_numpy(float), equal_nan=True)


def test_job_data_needs_labels_and_refuses_training_rows_of_the_predicted_season_or_later(frame, monkeypatch):
    with pytest.raises(RuntimeError, match="labels"):
        C.job_data(frame, "split", "atp", 2022, 0)
    f = fake_labels(frame)
    real = C.train_mask

    def leaky(offset):
        def mask(fr, arm, tour, Y, seed):
            m = real(fr, arm, tour, Y, seed).copy()
            m[np.flatnonzero(fr["season"].to_numpy() == Y + offset)[0]] = True
            return m
        return mask

    for offset, arm, tour in ((0, "split", "wta"), (0, "notour", "both"), (1, "borrow50", "atp"), (0, "aligned", "both")):
        monkeypatch.setattr(C, "train_mask", leaky(offset))
        with pytest.raises(RuntimeError, match="predicted season"):
            C.job_data(f, arm, tour, 2022, 0)


def test_job_data_refuses_a_training_row_from_the_sealed_holdout(frame):
    """A training row dated from 29 Jul 2026 is refused even when its season is earlier (a mis-dated or mis-seasoned
    row): one 2021 women's row is re-dated, synthetic labels, no result read."""
    f = fake_labels(frame)
    i = int(np.flatnonzero((f["season"].to_numpy() == 2021) & (f["tour"].to_numpy() == "wta"))[0])
    f.loc[i, "tournament_date"] = pd.Timestamp("2026-08-03")
    with pytest.raises(RuntimeError, match="sealed"):
        C.job_data(f, "split", "wta", 2022, 0)
    C.job_data(f, "split", "atp", 2022, 0)                          # the men's model does not train on that row


def test_the_studys_pieces_rebuild_the_current_instances_2022_fit_exactly(frame, instance_meta):
    """The pooled job built from this study's pieces (frame, matrix, pool, query, swap) carries the fingerprint the
    current instance's runner stored for 2022 seed 0: the same inputs in order, rows, labels and td query. (2025-2026
    are not comparable this way: the instance's queries there also hold the early and late blocks.)"""
    season = 2022
    with np.load(C.INSTANCE / "fits" / f"model__{season}__seed0.npz", allow_pickle=False) as z:
        ids_td = z["ids_td"].astype(str)
    f = training_labels(frame, season - 1)
    Xm = SA.matrix(f, C.base_inputs())
    tr, te = C.pool_mask(f, season), C.query_mask(f, "both", season)
    Xt = Xm[te].reset_index(drop=True)
    Xq = pd.concat([Xt, SA.flip(Xt, C.P)], ignore_index=True)
    y = f.loc[tr, "a_won"].astype("int64").to_numpy()
    assert instance_meta["columns"] == C.base_inputs()
    assert instance_meta["train_shape"] == [int(tr.sum()), 58]
    assert instance_meta["config"] == {**C.SC.CONFIG, "random_state": 0}
    assert instance_meta["model_frame_sha256"] == C.sha256_file(C.P.model_frame)
    assert np.array_equal(ids_td, f.loc[te, "match_id"].astype(str).to_numpy())
    assert C.SC.fingerprint(Xm[tr].reset_index(drop=True), y, Xq) == instance_meta["fingerprint"]


# ------------------------------------------------------------------------------------------------
# The aligned arm

def test_aligned_inputs_are_the_39_box_score_differences():
    names, kinds, _ = SA.base_inputs(C.P)
    al = C.aligned_inputs()
    assert len(al) == 39 and len(set(al)) == 39
    assert all(kinds[c] == "diff" for c in al)                 # so the swap commutes with the scaling
    assert not COMMON_SCALE & set(al)
    assert not {c for c in names if kinds[c] != "diff"} & set(al)


@pytest.mark.parametrize("season", SEASONS)
def test_align_gives_unit_sd_per_tour_over_training_rows_and_touches_nothing_else(frame, X, season):
    Xa = C.align(X, frame, season)
    pool, t = C.pool_mask(frame, season), frame["tour"].to_numpy()
    al = set(C.aligned_inputs())
    assert list(Xa.columns) == list(X.columns)
    for c in X.columns:
        a, b = Xa[c].to_numpy(float), X[c].to_numpy(float)
        if c in al:
            for tour in C.TOURS:
                assert abs(np.nanstd(a[pool & (t == tour)]) - 1.0) < 1e-9, (c, tour)
            assert np.array_equal(np.isnan(a), np.isnan(b))
        else:
            assert np.array_equal(a, b, equal_nan=True), c


@pytest.mark.parametrize("season", SEASONS)
def test_align_commutes_with_the_swap(frame, X, season):
    a = SA.flip(C.align(X, frame, season), C.P).to_numpy(float)
    b = C.align(SA.flip(X, C.P), frame, season).to_numpy(float)
    assert np.array_equal(a, b, equal_nan=True)


@pytest.mark.parametrize("season", SEASONS)
def test_align_scales_read_the_training_seasons_only(frame, season):
    base = C.align_scales(frame, season)
    g = frame.copy()
    late = g["season"].to_numpy() >= season
    for c in C.aligned_inputs():
        g.loc[late, f"in_{c}"] = g.loc[late, f"in_{c}"] * 7.0 + 3.0
    assert C.align_scales(g, season) == base
    h = frame.copy()                                           # the check can fail: a training row moves a scale
    last = h["season"].to_numpy() == season - 1
    h.loc[last, "in_form_ace"] = h.loc[last, "in_form_ace"] * 7.0
    assert C.align_scales(h, season)[("atp", "form_ace")] != base[("atp", "form_ace")]


# ------------------------------------------------------------------------------------------------
# The borrowsim arm

def _sim(tour: str, season: int):
    path = C.sim_path(tour, season)
    if not path.exists() or not path.with_suffix(".json").exists():
        pytest.skip(f"no similarity cache for {tour} {season} yet ({path.relative_to(ROOT)})")
    return pd.read_parquet(path), json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))


def test_sim_features_are_unchanged_by_the_swap_and_read_neither_tour_nor_indoor(frame):
    g = frame.copy()
    Xf = SA.flip(SA.matrix(frame, C.base_inputs()), C.P)
    for c in C.base_inputs():
        g[f"in_{c}"] = Xf[c].to_numpy()
    a = C.sim_features(frame)
    assert list(a.columns) == list(C.sim_features(g).columns)
    assert np.array_equal(a.to_numpy(float), C.sim_features(g).to_numpy(float), equal_nan=True)
    blind = frame.drop(columns=["tour", "in_tour", "in_indoor"])     # works without them, so reads neither
    assert np.array_equal(a.to_numpy(float), C.sim_features(blind).to_numpy(float), equal_nan=True)


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_borrowsim_cache_is_the_other_tours_pool_with_valid_weights(frame, season, tour):
    d, meta = _sim(tour, season)
    _, own, other = pools(frame, tour, season)
    ids = frame.loc[other, "match_id"].astype(str)
    assert d["match_id"].is_unique and len(d) == len(ids) and set(d["match_id"].astype(str)) == set(ids)
    assert d["season"].min() >= C.TRAIN_FROM and d["season"].max() <= season - 1
    pi, p = d["pi"].to_numpy(float), d["p_own"].to_numpy(float)
    assert np.isfinite(pi).all() and pi.min() >= 0 and pi.max() <= 1
    assert abs(pi.sum() - C.BORROW_SHARE["borrowsim"] * len(d)) < 0.5
    assert np.allclose(d["ratio"].to_numpy(float), p / (1 - p) * len(d) / int(own.sum()))
    assert np.allclose(pi, np.minimum(1.0, meta["kappa"] * d["ratio"].to_numpy(float)))
    assert meta["n_own"] == int(own.sum()) and meta["n_other"] == len(d)
    assert meta["train_seasons"] == [C.TRAIN_FROM, season - 1]


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_borrowsim_cache_was_built_from_todays_features_and_is_not_degenerate(frame, season, tour):
    _, meta = _sim(tour, season)
    assert meta["features"] == list(C.sim_features(frame.head(20)).columns), "stale cache: other features"
    assert meta["version"] == C.SIM_VERSION and meta["model_frame_sha256"] == C.frame_sha()
    assert meta["auc_out_of_fold"] < 0.99, "the classifier names the tour: every pi equal, i.e. a random half"
    assert meta["effective_n"] < 0.95 * meta["n_other"]


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("tour", C.TOURS)
def test_borrowsim_draw_follows_pi(frame, season, tour):
    d, _ = _sim(tour, season)
    pool, own, other = pools(frame, tour, season)
    pi = d.set_index(d["match_id"].astype(str))["pi"].reindex(frame["match_id"].astype(str)).to_numpy(float)
    sd = float(np.sqrt(np.sum(pi[other] * (1 - pi[other]))))
    masks = [C.train_mask(frame, "borrowsim", tour, season, k) for k in C.SEEDS]
    for m in masks:
        assert not (m & ~pool).any() and np.array_equal(m & own, own)
        assert abs(int((m & other).sum()) - pi[other].sum()) < 6 * sd + 1
        assert int((m & other & (pi >= 1)).sum()) == int((other & (pi >= 1)).sum())      # pi = 1: always kept
    assert not np.array_equal(masks[0], masks[1])
    assert np.array_equal(masks[0], C.train_mask(frame, "borrowsim", tour, season, 0))
    kept = np.mean([m for m in masks], axis=0)
    lo, hi = other & (pi < 0.05), other & (pi > 0.95)
    if lo.sum() > 200 and hi.sum() > 200:                     # "random < pi", not the reverse
        assert kept[lo].mean() < 0.06 and kept[hi].mean() > 0.94
    for k, m in enumerate(masks):                             # coupled with borrow50 (u < 0.5 exactly on its rows)
        half = C.train_mask(frame, "borrow50", tour, season, k) & other
        assert (m[half & (pi >= 0.5)]).all()
        assert not (m[other & ~half & (pi <= 0.5)]).any()


def test_borrowsim_draw_on_a_synthetic_pi_keeps_each_row_with_probability_pi_and_couples_with_borrow50(frame, monkeypatch):
    """The draw's logic without any cache: sim_inclusion replaced by a synthetic pi over the other tour's pool rows
    (0, 1 and values in between). Over 40 seeds a row is kept about pi of the time; pi = 0 never, pi = 1 always; on
    borrow50's rows pi >= 0.5 is always kept, and off them pi <= 0.5 never is."""
    tour, season = "atp", 2022
    _, own, other = pools(frame, tour, season)
    g = np.random.default_rng(7)
    pi = np.where(g.random(int(other.sum())) < 0.1, 0.0, g.random(int(other.sum())))
    pi[g.random(len(pi)) < 0.1] = 1.0
    fake = pd.DataFrame({"match_id": frame.loc[other, "match_id"].astype(str).to_numpy(), "pi": pi})
    monkeypatch.setattr(C, "sim_inclusion", lambda fr, t, Y: fake)
    seeds = range(40)
    kept = np.array([C.train_mask(frame, "borrowsim", tour, season, k)[other] for k in seeds], float)
    half = np.array([C.train_mask(frame, "borrow50", tour, season, k)[other] for k in seeds])
    assert np.array_equal(C.train_mask(frame, "borrowsim", tour, season, 0) & own, own)
    assert (kept[:, pi == 0] == 0).all() and (kept[:, pi == 1] == 1).all()
    assert (kept[half & (pi >= 0.5)[None, :]] == 1).all()
    assert (kept[~half & (pi <= 0.5)[None, :]] == 0).all()
    freq = kept.mean(axis=0)
    for lo, hi in ((0.01, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 0.99)):
        b = (pi > lo) & (pi < hi)
        assert abs(freq[b].mean() - pi[b].mean()) < 0.02, (lo, hi, freq[b].mean(), pi[b].mean())
    counts = kept.sum(axis=1)
    assert abs(counts.mean() - pi.sum()) < 6 * np.sqrt(np.sum(pi * (1 - pi)) / len(counts)) + 1


@pytest.mark.parametrize("season", SEASONS)
def test_borrowsim_prefers_the_most_own_like_matches(frame, season):
    """Direction (r = p_own / p_other): no women's match is best of five, so the women's model must borrow fewer men's
    best-of-five matches than best-of-three; no men's Slam match is best of three, so the men's model must borrow fewer
    women's Slam matches than other women's matches."""
    f = frame.set_index(frame["match_id"].astype(str))
    d, _ = _sim("wta", season)
    bo5 = f.loc[d["match_id"].astype(str), "in_best_of"].to_numpy() == 5
    assert d["pi"].to_numpy()[bo5].mean() < d["pi"].to_numpy()[~bo5].mean()
    d, _ = _sim("atp", season)
    slam = f.loc[d["match_id"].astype(str), "in_level"].to_numpy() == 0
    assert d["pi"].to_numpy()[slam].mean() < d["pi"].to_numpy()[~slam].mean()


def _synthetic(n: int = 1500, seed: int = 0) -> pd.DataFrame:
    """Two tours alike in everything but the favourite's strength: men's |odds| twice as wide."""
    g = np.random.default_rng(seed)
    tour = np.repeat(["atp", "wta"], n)
    cols = {"match_id": [f"m{i}" for i in range(2 * n)], "tour": tour,
            "season": g.integers(C.TRAIN_FROM, 2019, 2 * n)}
    for c in C.SIM_DIFFS:
        cols[f"in_{c}"] = g.normal(size=2 * n) * (np.where(tour == "atp", 2.0, 1.0) if c == "odds_logit" else 1.0)
    for c in C.SIM_PAIRS:                                # as the frame stores them: log(1 + a count of matches or days)
        cols[f"in_{c}_a"], cols[f"in_{c}_b"] = np.log1p(g.integers(0, 400, 2 * n)), np.log1p(g.integers(0, 400, 2 * n))
    for c in C.SIM_CONTEXT:
        cols[f"in_{c}"] = g.integers(0, 4, 2 * n).astype(float)
    return pd.DataFrame(cols)


def test_sim_inclusion_direction_target_and_determinism_on_synthetic_tours(tmp_path, monkeypatch):
    # One OpenMP thread: the booster's barriers crawl on a busy machine. Import it first, so its OpenMP runtime is loaded
    # when threadpoolctl sets the limit (sim_inclusion imports it lazily, after the limit would be set).
    from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: F401
    from threadpoolctl import threadpool_limits
    f = _synthetic()
    outs = []
    for sub in ("a", "b"):
        monkeypatch.setattr(C, "SIM", tmp_path / sub)
        with threadpool_limits(limits=1, user_api="openmp"):
            outs.append(C.sim_inclusion(f, "wta", 2019))
    d, meta = outs[0], json.loads((tmp_path / "a" / "wta__2019.json").read_text(encoding="utf-8"))
    assert d.equals(outs[1])                                                   # deterministic
    assert set(d["match_id"]) == set(f.loc[f["tour"] == "atp", "match_id"])    # the other tour's rows only
    assert abs(d["pi"].sum() - 0.5 * len(d)) < 0.5
    odds = f.set_index("match_id").loc[d["match_id"], "in_odds_logit"].abs().to_numpy()
    close, wide = odds < np.quantile(odds, 0.33), odds > np.quantile(odds, 0.67)
    assert d["pi"].to_numpy()[close].mean() > d["pi"].to_numpy()[wide].mean() + 0.2   # women-like = close matches
    assert 0.55 < meta["auc_out_of_fold"] < 0.95
    # the record is checked on read: a stale version, or a cache without its record, is refused
    rec = tmp_path / "a" / "wta__2019.json"
    stale = {**meta, "version": meta["version"] - 1}
    rec.write_text(json.dumps(stale), encoding="utf-8")
    monkeypatch.setattr(C, "SIM", tmp_path / "a")
    with pytest.raises(RuntimeError, match="stale"):
        C.sim_inclusion(f, "wta", 2019)
    rec.write_text(json.dumps({**meta, "features": meta["features"][:-1]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale"):
        C.sim_inclusion(f, "wta", 2019)
    bare = tmp_path / "c"
    bare.mkdir()
    (bare / "wta__2019.parquet").write_bytes((tmp_path / "b" / "wta__2019.parquet").read_bytes())
    monkeypatch.setattr(C, "SIM", bare)
    with pytest.raises(RuntimeError, match="no record"):
        C.sim_inclusion(f, "wta", 2019)


# ------------------------------------------------------------------------------------------------
# Known design limits (xfail strict: a fix turns them into failures, so the note is updated)

@pytest.mark.xfail(strict=True, reason="known (lead, 9 Oct 2026): in_indoor is missing for every women's match and for no "
                                       "men's training match, so notour keeps a perfect tour proxy (TabPFN 3.5 adds NaN "
                                       "indicators) and measures only the explicit flag")
def test_notour_inputs_do_not_name_the_tour_by_their_missing_values(frame):
    train = frame["season"].to_numpy() <= 2025
    wta = frame["tour"].to_numpy()[train] == "wta"
    named = [c for c in C.inputs("notour")
             if np.array_equal(np.isnan(frame[f"in_{c}"].to_numpy(float))[train], wta)]
    assert not named, f"the missing-value pattern names the tour exactly: {named}"


# ------------------------------------------------------------------------------------------------
# The runner's plan and fits already written

@pytest.mark.parametrize("arm", [a for a in C.ARMS if a != "borrowsim"])
def test_plan_trains_through_the_season_before_and_queries_the_models_tours(frame, arm):
    from src.eda.tour_pooling import fits as TF
    t = TF.plan(frame, arm, list(SEASONS), [0])
    s, tt = frame["season"].to_numpy(), frame["tour"].to_numpy()
    for r in t.itertuples():
        assert r.train_last_season == r.season - 1
        want = (s == r.season) if r.tour == "both" else (s == r.season) & (tt == r.tour)
        assert r.query_rows == int(want.sum()) and r.train_rows == r.train_atp + r.train_wta


def _fit_files() -> list[Path]:
    if not C.FITS.exists():
        return []
    return sorted(p for p in C.FITS.glob("*.npz") if FIT_RE.match(p.name)
                  and int(FIT_RE.match(p.name)["season"]) in SEASONS)


def _parse(path: Path):
    g = FIT_RE.match(path.name)
    return g["arm"], g["tour"], int(g["season"]), int(g["seed"])


def test_fits_on_disk_match_their_masks_and_the_instances_runtime(frame, instance_meta):
    files = _fit_files()
    if not files:
        pytest.skip("no tour-pooling fit of 2019, 2022 or 2026 written yet")
    frame_sha = C.sha256_file(C.P.model_frame)
    problems = []
    for path in files:
        arm, tour, season, seed = _parse(path)
        if arm == "borrowsim" and not C.sim_path(tour, season).exists():
            problems.append(f"{path.name}: a borrowsim fit without its similarity cache")
            continue
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            p, ids = z["p_td"].astype(float), z["ids_td"].astype(str)
        tr, te, cols = C.train_mask(frame, arm, tour, season, seed), C.query_mask(frame, tour, season), C.inputs(arm)
        by = frame.loc[tr].groupby(["tour", "season"]).size()
        checks = {
            "names": (meta["arm"], meta["tour"], meta["season"], meta["seed"]) == (arm, tour, season, seed),
            "columns": meta["columns"] == cols,
            "train_shape": meta["train_shape"] == [int(tr.sum()), len(cols)],
            "rows_by_tour_season": meta["train_rows_by_tour_season"] == {f"{k[0]} {int(k[1])}": int(v)
                                                                         for k, v in by.items()},
            "ids_td": np.array_equal(ids, frame.loc[te, "match_id"].astype(str).to_numpy()),
            "p_td": len(p) == 2 * len(ids) and bool(np.isfinite(p).all()) and p.min() >= 0 and p.max() <= 1,
            "config": meta["config"] == {**C.SC.CONFIG, "random_state": seed},
            "frame": meta["model_frame_sha256"] == frame_sha,
            "runtime": (meta["versions"], meta["checkpoint"], meta["device"])
            == (instance_meta["versions"], instance_meta["checkpoint"], instance_meta["device"]),
            "sim_cache": arm != "borrowsim"
            or (meta.get("draw") or {}).get("sim_cache_sha256") == C.sha256_file(C.sim_path(tour, season)),
        }
        bad = [k for k, v in checks.items() if not v]
        if bad:
            problems.append(f"{path.name}: {bad}")
    assert not problems, problems


def test_fits_on_disk_carry_the_fingerprint_of_todays_job_data(frame):
    files = _fit_files()
    if not files:
        pytest.skip("no tour-pooling fit of 2019, 2022 or 2026 written yet")
    labelled, problems = {}, []
    for path in files:
        arm, tour, season, seed = _parse(path)
        if arm == "borrowsim" and not C.sim_path(tour, season).exists():
            continue
        if season not in labelled:
            labelled[season] = training_labels(frame, season - 1)
        X_train, y_train, X_query, _, _ = C.job_data(labelled[season], arm, tour, season, seed)
        with np.load(path, allow_pickle=False) as z:
            stored = json.loads(str(z["meta"]))["fingerprint"]
        if C.SC.fingerprint(X_train, y_train, X_query) != stored:
            problems.append(path.name)
    assert not problems, f"fitted on other job data than today's code builds: {problems}"


def test_the_pooled_reproduction_fit_equals_the_instances_stored_fit():
    """This runner's pooled job (2022, seed 0) must reproduce the instance's stored forecasts (the yardstick) within the
    serve-speed harness's reproduction tolerance."""
    path = C.fit_path("pooled", "both", 2022, 0)
    if not path.exists():
        pytest.skip("the reproduction fit pooled__both__2022__seed0 is not written yet")
    with np.load(path, allow_pickle=False) as a, \
            np.load(C.INSTANCE / "fits" / "model__2022__seed0.npz", allow_pickle=False) as b:
        assert np.array_equal(a["ids_td"].astype(str), b["ids_td"].astype(str))
        diff = float(np.abs(a["p_td"].astype(float) - b["p_td"].astype(float)).max())
    assert diff <= C.SC.REPRO_TOL, f"max |p_new - p_instance| = {diff:.2e}"
