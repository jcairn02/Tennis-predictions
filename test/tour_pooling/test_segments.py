"""Tests of the tour-pooling segment analysis (src/eda/tour_pooling/segments.py): synthetic tables only.

The sealed holdout's rows are dropped while the forecasts are read; the frame's result column is never selected; the
segments follow the declared definitions (indoor left out of the missing count, round robins with the late rounds, the
favourite thirds per tour); + = the arm (pooled) better than split; a model against itself reads exactly 0; a planted
effect is found where it was planted and nowhere else; Benjamini-Hochberg matches a hand computation.

Run: ./python.sh -m pytest test/tour_pooling -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tour_pooling import segments as G  # noqa: E402

NAMES = G.input_names()                          # the instance's 58 inputs (model_inputs.json; no result)
CONTEXT = {"tour", "surface", "level", "indoor", "best_of", "round"}


def make_frame(seed: int = 0, per_week: int = 6) -> pd.DataFrame:
    """A frame of inputs like frame_inputs(): both tours, a tournament every Monday 2019-2026, per_week matches each."""
    rng = np.random.default_rng(seed)
    mondays = pd.date_range("2019-01-07", "2026-12-28", freq="7D")
    rows = []
    for tour in ("atp", "wta"):
        for d in mondays:
            for i in range(per_week):
                rows.append({"match_id": f"{tour}|{d.date()}|{i}", "tour": tour, "season": d.year,
                             "tournament_date": d})
    f = pd.DataFrame(rows).set_index("match_id")
    n = len(f)
    wta = (f["tour"] == "wta").to_numpy()
    for c in NAMES:
        if c not in CONTEXT and c not in ("surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"):
            f[f"in_{c}"] = rng.normal(size=n)
    f["in_tour"] = wta.astype(float)
    f["in_surface"] = rng.choice([0.0, 1.0, 2.0], size=n, p=[0.5, 0.3, 0.2])
    f["in_level"] = rng.choice([0.0, 2.0, 3.0, 4.0], size=n)
    f["in_best_of"] = np.where(~wta & (f["in_level"].to_numpy() == 0), 5.0, 3.0)
    f["in_round"] = rng.choice([11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0], size=n)
    f["in_indoor"] = np.where(wta, np.nan, rng.choice([0.0, 1.0], size=n))
    for side in ("a", "b"):
        f[f"in_surf_season_{side}"] = np.log1p(rng.poisson(3, size=n)).astype(float)
        f[f"in_surf_layoff_{side}"] = np.log1p(rng.integers(1, 200, size=n)).astype(float)
    return f


def make_forecasts(f: pd.DataFrame, seed: int = 1, plant: tuple[str, str] | None = ("wta", "grass"),
                   identical: bool = False, extra: tuple[str, ...] = ()) -> pd.DataFrame:
    """Scored rows (2019 .. 28 Jul 2026) in the scorer's layout. Outside the planted cell pooled = split exactly; inside
    it split is much noisier (pooled better). Seeds 0-3 share their noise across the models. Each name in extra is one
    more model with its own independent noise everywhere."""
    rng = np.random.default_rng(seed)
    g = f[f["tournament_date"] < G.SEALED_FROM].copy()
    n = len(g)
    eta = rng.normal(scale=1.0, size=n)
    y = (rng.random(n) < expit(eta)).astype(float)
    base_noise = rng.normal(scale=0.3, size=n)
    lg_pooled = eta + base_noise
    lg_split = lg_pooled.copy()
    if plant is not None and not identical:
        m = (g["tour"].to_numpy() == plant[0]) & (g["in_surface"].to_numpy() == {"hard": 0, "clay": 1, "grass": 2}[plant[1]])
        lg_split[m] = eta[m] + rng.normal(scale=1.2, size=int(m.sum()))
    out = pd.DataFrame({"match_id": g.index, "tour": g["tour"].to_numpy(), "season": g["season"].to_numpy(),
                        "tournament_date": g["tournament_date"].to_numpy(), "debut": False, "level": "x", "y": y})
    dates = g["tournament_date"].to_numpy()
    out["block"] = G.C.SC.blocks(dates, 28)
    out["week"] = G.C.SC.blocks(dates, 7)
    seed_noise = rng.normal(scale=0.05, size=(n, 4))
    models = [("pooled", lg_pooled), ("split", lg_split)] + [(e, eta + rng.normal(scale=0.4, size=n)) for e in extra]
    for name, lg in models:
        qk = expit(lg[:, None] + seed_noise)
        out[f"q_{name}"] = qk.mean(axis=1)
        out[f"q1_{name}"] = qk.mean(axis=1)
        for k in range(4):
            out[f"q_{name}_s{k}"] = qk[:, k]
    out["q_close"] = expit(eta)
    return out


@pytest.fixture(scope="module")
def frame():
    return make_frame()


@pytest.fixture(scope="module")
def seg(frame):
    return G.segment_frame(frame, NAMES)


def write(df: pd.DataFrame, path: Path) -> Path:
    df.to_parquet(path, index=False)
    return path


# ------------------------------------------------------------------------------------------------

def test_bh_matches_a_hand_computation():
    q = G.bh([0.01, 0.04, 0.03, 0.20, np.nan])
    assert np.allclose(q[:4], [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.20])
    assert np.isnan(q[4])


def test_frame_inputs_never_selects_the_result(tmp_path, frame):
    f = frame.head(50).reset_index()
    f["a_won"] = 1
    got = G.frame_inputs(write(f, tmp_path / "frame.parquet"))
    assert "a_won" not in got.columns and got.index.name == "match_id"


def test_segment_definitions(frame):
    f = frame.head(8).copy()
    i = f.index
    f.loc[i[0], "tour"], f.loc[i[0], "in_indoor"] = "wta", np.nan        # all observed but indoor -> none
    f.loc[i[1], [f"in_{c}" for c in NAMES[9:21]]] = np.nan              # 12 inputs missing -> >10
    f.loc[i[2], ["in_round", "in_level", "in_surface"]] = [10.0, 1.0, 3.0]   # round robin, Finals, carpet
    f.loc[i[3], "in_round"] = 14.0
    f.loc[i[4], "in_round"] = 15.0
    f.loc[i[5], ["in_surf_season_a", "in_surf_season_b"]] = [2.0, 0.0]
    f.loc[i[6], ["in_surf_season_a", "in_surf_season_b"]] = [1.0, 1.5]
    cuts = {"atp": (0.5, 1.0), "wta": (0.4, 0.8)}
    f.loc[i[7], ["tour", "in_odds_logit"]] = ["wta", -0.9]
    s = G.segment_frame(f, NAMES, cuts=cuts)
    assert s.loc[i[0], "missing"] == "none" and s.loc[i[0], "n_missing_with_indoor"] == 1
    assert s.loc[i[1], "missing"] == ">10" and s.loc[i[1], "n_missing"] == 12
    assert s.loc[i[2], "round"] == "QF on (and RR)" and s.loc[i[2], "level"] == "Finals"
    assert s.loc[i[2], "surface"] == "hard"
    assert s.loc[i[3], "round"] == "R128-R16" and s.loc[i[4], "round"] == "QF on (and RR)"
    assert s.loc[i[5], "surface_season"] == "first on surface"
    assert s.loc[i[6], "surface_season"] == "not first"
    assert s.loc[i[7], "favourite"] == "heavy third"                   # |-0.9| > the women's 0.8
    assert s.attrs["favourite_cuts"] == cuts


def test_favourite_thirds_are_per_tour(frame):
    f = frame.copy()
    f.loc[f["tour"] == "wta", "in_odds_logit"] *= 3                     # women's prices three times as spread
    s = G.segment_frame(f, NAMES)
    for tour in ("atp", "wta"):
        m = (s["tour"] == tour) & s["season"].between(2019, 2026)
        share = s.loc[m, "favourite"].value_counts(normalize=True)
        assert np.allclose(share.to_numpy(), 1 / 3, atol=0.01)
    assert s.attrs["favourite_cuts"]["wta"][0] == pytest.approx(3 * s.attrs["favourite_cuts"]["atp"][0], rel=0.1)


def test_sealed_rows_are_dropped_while_reading(tmp_path, frame):
    fc = make_forecasts(frame)
    sealed = make_forecasts(frame).head(30).copy()
    sealed["match_id"] = [f"sealed{k}" for k in range(30)]
    sealed["tournament_date"] = pd.Timestamp("2026-08-30")
    sealed["y"] = np.nan
    both = pd.concat([fc, sealed], ignore_index=True)
    got = G.load_forecasts(write(both, tmp_path / "fc.parquet"))
    assert len(got) == len(fc) and got["y"].notna().all()
    both["tournament_date"] = both["tournament_date"].dt.strftime("%Y-%m-%d")      # stored as text: still filtered
    got = G.load_forecasts(write(both, tmp_path / "fc_text.parquet"))
    assert len(got) == len(fc)


def test_a_model_against_itself_reads_exactly_zero(tmp_path, frame, seg):
    fc = make_forecasts(frame, identical=True)
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    assert (t["estimate"] == 0).all()
    ref = t[t["reference_row"]].iloc[0]
    assert ref["lo"] == 0 and ref["hi"] == 0 and ref["reading"] == "unresolved"
    assert not t["read"].any()                                           # P(better) undefined: nothing to flag


def test_a_planted_effect_is_found_where_planted(tmp_path, frame, seg):
    fc = make_forecasts(frame, plant=("wta", "grass"))
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    t = t[t["comparison"] == "pooled vs split"]
    assert t["direction"].iloc[0].startswith("+ = pooled better")
    for w in ("W1", "W2"):
        cell = t[(t["window"] == w) & (t["tour"] == "women") & (t["dimension"] == "surface") & (t["cell"] == "grass")]
        r = cell.iloc[0]
        assert r["estimate"] > 0 and r["reading"] == "better" and r["read"] and r["q_bh"] < 0.01
        assert r["seed_term"] == "paired"
        men = t[(t["window"] == w) & (t["tour"] == "men")]
        assert (men["estimate"] == 0).all()                              # pooled = split for men
        clay = t[(t["window"] == w) & (t["tour"] == "women") & (t["cell"] == "clay")]
        assert (clay["estimate"] == 0).all()
    led = G.leads(t)
    assert set(led["tour"]) == {"women"} and "grass" in set(led["cell"])
    md = (tmp_path / "out" / "segments.md").read_text(encoding="utf-8")
    assert "+ = pooled better" in md and "flag, not a verdict" in md
    # the effect is planted in every season, so the seasons outside each window read it too
    out = pd.read_csv(tmp_path / "out" / "leads.csv")
    grass = out[(out["cell"] == "grass") & (out["comparison"] == "pooled vs split")]
    assert set(grass["outside_seasons"]) == {"2020-2021", "2025-2026"}
    assert (grass["outside_estimate"] > 0).all() and (grass["outside_matches"] > 0).all()


def test_windows_and_debut(tmp_path, frame, seg):
    fc = make_forecasts(frame)
    fc.loc[fc["season"] == 2023, "debut"] = True
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    seasons_w1 = set(t[(t["window"] == "W1") & (t["dimension"] == "season")]["cell"])
    seasons_w2 = set(t[(t["window"] == "W2") & (t["dimension"] == "season")]["cell"])
    assert seasons_w1 == {"2022", "2024", "2025", "2026"}
    assert seasons_w2 == {"2020", "2021", "2022", "2024"}


def test_twin_cells_are_counted_once(tmp_path, frame, seg):
    fc = make_forecasts(frame)
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    r = t[(t["tour"] == "women") & (t["dimension"] == "best_of")]
    assert set(r["cell"]) == {"best of 3"} and (r["duplicate_of"] == "all: all").all() and not r["read"].any()
    men5 = t[(t["tour"] == "men") & (t["dimension"] == "best_of") & (t["cell"] == "best of 5")]
    assert (men5["duplicate_of"] == "level: Slams").all() and not men5["read"].any()
    slam = t[(t["dimension"] == "slam") & (t["cell"] == "Slam")]
    assert (slam["duplicate_of"] == "level: Slams").all()
    assert (t.loc[t["dimension"] == "level", "duplicate_of"] == "").all()
    for (w, c), g in t.groupby(["window", "comparison"]):                 # BH families: one per window and comparison
        assert (g["family_size"] == g["read"].sum()).all()


def test_composition_plus_size_adds_up(tmp_path, frame, seg):
    fc = make_forecasts(frame, extra=("sizectl", "borrow50", "borrowsim"))
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    assert {"pooled vs split", "sizectl vs split", "pooled vs sizectl", "borrowsim vs borrow50"} <= set(t["comparison"])
    key = ["window", "tour", "dimension", "cell"]
    e = {c: t[t["comparison"] == c].set_index(key)["estimate"] for c in
         ("pooled vs split", "sizectl vs split", "pooled vs sizectl")}
    assert np.allclose(e["pooled vs split"], e["sizectl vs split"] + e["pooled vs sizectl"].loc[e["pooled vs split"].index])
    d = t[t["comparison"] == "borrowsim vs borrow50"]["direction"].iloc[0]
    assert d.startswith("+ = borrowsim better than borrow50")
    md = (tmp_path / "out" / "segments.md").read_text(encoding="utf-8")
    assert "composition + size" in md and "Borrowsim vs borrow50 by segment" in md


def test_an_arm_without_seeds_is_scored_unpaired(tmp_path, frame, seg):
    fc = make_forecasts(frame)
    fc["q_blend"] = fc["q_pooled"]
    t = G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
    b = t[t["comparison"] == "blend vs split"]
    assert len(b) and set(b["seed_term"]) == {"unpaired"}
    p = t[t["comparison"] == "pooled vs split"].set_index(["window", "tour", "dimension", "cell"])["estimate"]
    q = b.set_index(["window", "tour", "dimension", "cell"])["estimate"]
    assert np.allclose(p.loc[q.index], q)                               # the same forecasts, the same estimate


def test_only_declared_comparisons_are_made():
    present = ["pooled", "split", "notour", "borrow50", "blend", "reference"]
    assert G.comparisons(present) == [("split", "pooled"), ("split", "borrow50"), ("split", "blend")]
    assert G.comparisons(["pooled", "notour"]) == []
    full = ["pooled", "split", "borrow50", "borrowsim", "sizectl"]
    assert G.comparisons(full) == [("split", "pooled"), ("split", "borrow50"), ("split", "borrowsim"),
                                   ("borrow50", "borrowsim"), ("split", "sizectl"), ("sizectl", "pooled")]
    assert G.direction("sizectl", "pooled").startswith("+ = pooled better than sizectl")


def test_scored_matches_must_be_in_the_frame(tmp_path, frame, seg):
    fc = make_forecasts(frame)
    fc.loc[0, "match_id"] = "not-a-frame-match"
    with pytest.raises(RuntimeError, match="not in the instance frame"):
        G.run(write(fc, tmp_path / "fc.parquet"), tmp_path / "out", seg=seg)
