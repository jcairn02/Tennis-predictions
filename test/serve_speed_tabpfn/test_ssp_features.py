"""Tests of the speed-state build (C3) and its probes (C7: T-F1 to T-F6), serve-speed TabPFN study.

Run: ./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_features.py -q
They read the built outputs (data/studies/serve_speed_tabpfn/features/) and recompute parts on subsets with the same
panel the build used (the engineer's panel.py; the development stand-in only if the build says so). No match result is
read anywhere.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402

META = json.loads(F.META.read_text(encoding="utf-8")) if F.META.exists() else None
pytestmark = pytest.mark.skipif(META is None, reason="features not built yet")


@pytest.fixture(scope="module")
def P():
    return F.panel_module(META["standin_panel"])


@pytest.fixture(scope="module")
def built(P):
    """The panel, frame keys and targets the build used, plus the stored columns."""
    p = F.prepare_panel(P.load_panel(use_only=True))
    keys = P.load_frame_keys()
    t = F.side_targets(keys)
    offsets = {tour: P.EditionOffsets(p, tour) for tour in ("atp", "wta")}
    m = pd.read_parquet(F.FEATURES)
    return {"p": p, "keys": keys, "t": t, "offsets": offsets, "m": m}


def test_ssp_meta_real_panel_and_hashes():
    if (ROOT / "src" / "eda" / "serve_speed_tabpfn" / "panel.py").exists() and F.PANEL_FILE.exists():
        assert META["standin_panel"] is False, "the final build must run on the engineer's panel"
        assert META["panel_sha256"] == F.sha256(F.PANEL_FILE)
    assert META["features_parquet_sha256"] == F.sha256(F.FEATURES)
    assert META["features_py_sha256"] == F.sha256(Path(F.__file__))
    assert META["reads_results"] is False


def test_ssp_one_row_per_frame_match_and_no_nan(built):
    m = built["m"]
    frame = pd.read_parquet(ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet",
                            columns=["match_id", "tour", "season"])
    assert len(m) == len(frame) == 63737
    assert m["match_id"].is_unique and set(m["match_id"]) == set(frame["match_id"])
    assert m["spd_f"].notna().all() and m["spd_f_all"].notna().all()
    assert (m.loc[m["tour"].eq("wta"), "spd_f"] == 0).all()
    assert m.loc[m["tour"].eq("wta"), "spd_raw"].isna().all()
    for c in ("spd_f", "spd_f_all", "spd_raw"):
        assert (m[c].dropna().abs() <= F.CLIP).all()
    men = m["tour"].eq("atp")
    assert (m.loc[men, "spd_f"] == m.loc[men, "spd_f_all"]).all()


def test_ssp_t_f1_filter_equals_independent_references(built):
    """T-F1: my filter against the auditor's vectorised filter (auditor_lib.kalman_batch) on the same centred rows of
    2,000 random targets (1e-9), and against the design-phase scalar filter (modeller_state.kalman) on 200."""
    from src.eda.serve_speed_tabpfn.design import auditor_lib as AL
    from src.eda.serve_speed_tabpfn.design import modeller_state as MS
    p, t, offsets = built["p"], built["t"], built["offsets"]
    rng = np.random.default_rng(11)
    ok = np.flatnonzero(t["es"].notna().to_numpy())
    S = t.iloc[rng.choice(ok, 2000, replace=False)].reset_index(drop=True)
    h = F.histories(p, S)
    G = F.snapshot_gammas(p, S, h["idx"], offsets)
    idx = h["idx"]
    okk = idx >= 0
    safe = np.maximum(idx, 0)
    Z = np.where(okk, p["y"].to_numpy(float)[safe] - G, np.nan)
    DAY = np.where(okk, p["obs"].to_numpy(float)[safe], np.nan)
    assert okk.any(1).sum() > 500
    for tour, prm in F.CONST.items():
        sel = np.flatnonzero(S["tour"].eq(tour).to_numpy())
        nu = np.where(p["basis"].astype(str).eq("ks").to_numpy(), prm["nu_ks"], prm["nu_pts"])
        rr = nu + prm["sigma"] ** 2 / p["n"].to_numpy(float)
        R = np.where(okk[sel], rr[safe[sel]], np.nan)
        mine = F.kalman(Z[sel], R, DAY[sel], S["es"].to_numpy(float)[sel], prm)
        ref = AL.kalman_batch(Z[sel], R, DAY[sel], S["es"].to_numpy(float)[sel],
                              {"hl": prm["hl"], "s2f": prm["s2f"], "q": prm["q"], "c": prm["c"]})
        for c in ("f_hat", "f_sd", "L_hat"):
            a, b = mine[c], ref[c]
            both = ~(np.isnan(a) & np.isnan(b))
            assert np.nanmax(np.abs(a[both] - b[both])) <= 1e-9, (tour, c)
        # the scalar R1 filter, target by target, fed the same centred rows (the target's obs set to its es)
        sub = sel[okk[sel].any(1)][:100]
        for i in sub:
            rows = idx[i][idx[i] >= 0]
            mini = pd.DataFrame({"tour": tour, "player_id": "x", "tdate": np.arange(len(rows)), "tournament_id": "h",
                                 "round_order": 1, "obs": p["obs"].to_numpy(float)[rows],
                                 "z": Z[i, :len(rows)], "R": rr[rows]})
            tgt = pd.DataFrame({"tour": [tour], "player_id": ["x"], "tdate": [len(rows)], "tournament_id": ["t"],
                                "round_order": [1], "obs": [S["es"].iloc[i]]})
            r = MS.kalman(mini, tgt, {"hl": prm["hl"], "s2f": prm["s2f"], "q": prm["q"], "c": prm["c"]}).iloc[0]
            j = int(np.flatnonzero(sel == i)[0])
            assert abs(r["f_hat"] - mine["f_hat"][j]) <= 1e-9
            assert abs(r["f_sd"] - mine["f_sd"][j]) <= 1e-9


def test_ssp_t_f2_probe_a_recorded_and_passing():
    a = META["probes"]["A"]
    assert a["pass"] is True
    assert a["cuts"] >= 25 and a["cuts_2024_26"] >= 10 and a["sides"] >= 4900
    assert a["moved_before_cut"] == 0 and a["moved_at_cut"] == 0
    assert a["leaky_control_cuts_moved"] >= math.ceil(0.8 * a["cuts"])
    assert a["tolerance"] <= 1e-12


def test_ssp_t_f2_probe_a_machinery(built):
    """A small re-run of Probe A (3 cuts, about 800 sides): nothing before or at a cut moves; the leaky control does."""
    B = {"p": built["p"], "t": built["t"], "offsets": built["offsets"]}
    r = F.probe_a(B, n_sides=2100, n_cuts=3, n_late=2, seed=5)
    assert r["moved_before_cut"] == 0 and r["moved_at_cut"] == 0
    assert r["leaky_control_cuts_moved"] >= 2


def test_ssp_t_f3_probe_b_recorded_and_passing():
    b = META["probes"]["B"]
    assert b["pass"] is True
    assert b["days"] >= 25 and b["moved"] == 0 and b["leaky_control_moved"] > 0
    kinds = {r["kind"] for r in b["per_day"]}
    assert {"timing_probe", "slam_2nd_wed", "random"} <= kinds
    dates = {r["date"] for r in b["per_day"]}
    assert {"2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14"} <= dates
    assert "g_sum" in b["values_checked"] and "f_hat" in b["values_checked"]


def test_ssp_t_f4_constants_and_s_f(built):
    assert F.MEN == {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365.0, "c": 2.0, "nu_pts": 7.0, "nu_ks": 8.0, "sigma": 13.49}
    assert F.WOMEN == {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365.0, "c": 4.0, "nu_pts": 14.0, "nu_ks": 10.0,
                       "sigma": 10.72}
    assert F.C2_FROZEN == {"tau2": 22.0, "s": 12.4, "K": 25.0, "window_days": 364}
    assert F.WINDOW == 364.0 and F.RAW_SD == 5.998 and F.CLIP == 4.0 and F.SF_SEASONS == (2022, 2023)
    c = META["constants"]
    assert c["men"] == F.MEN and c["women_A3_only"] == F.WOMEN and c["c2_frozen"] == F.C2_FROZEN
    for k, v in c["c2_from_panel_module"].items():          # whatever the panel module exposes must equal C2
        frozen = {"TAU2": 22.0, "S_SERVE": 12.4, "K_PRIOR": 25.0, "WINDOW": 364.0}[k]
        assert float(v) == frozen, k
    m = built["m"]
    men = m["tour"].eq("atp") & m["season"].between(2022, 2023)
    s_f = float(m.loc[men, "spd_f_unclipped_km_h"].std(ddof=1))
    assert abs(s_f - META["s_f"]) < 1e-12
    assert 1.5 < s_f < 3.0
    assert m.loc[m["season"] > 2023, "season"].min() == 2024           # later values exist, but s_f reads <= 2023
    d = m["spd_f_unclipped_km_h"]
    assert np.allclose(m.loc[m["tour"].eq("atp"), "spd_f"], np.clip(d[m["tour"].eq("atp")] / s_f, -4, 4), atol=0)


def test_ssp_t_f5_flip_negates_all_three_columns(built):
    """T-F5: the same matches rebuilt with A and B exchanged give exactly the negated columns (NaN where NaN)."""
    rng = np.random.default_rng(3)
    keys, m = built["keys"], built["m"].set_index("match_id")
    sel = []
    for tour in ("atp", "wta"):
        k = keys[keys["tour"].eq(tour)]
        sel.append(k.sample(300, random_state=1))
        x = m.loc[k["match_id"]]
        sel.append(k[x["spd_raw"].notna().to_numpy()].sample(100, random_state=2) if tour == "atp" else k.head(0))
    sub = pd.concat(sel).drop_duplicates("match_id").reset_index(drop=True)
    flip = sub.copy()
    flip["player_a_id"], flip["player_b_id"] = sub["player_b_id"].to_numpy(), sub["player_a_id"].to_numpy()
    t = F.side_targets(flip)
    sv = F.side_values(built["p"], t, built["offsets"])
    mm, _ = F.columns(t, sv, META["s_f"])
    mm = mm.set_index("match_id")
    orig = m.loc[mm.index]
    for c in ("spd_f", "spd_f_all", "spd_raw"):
        a, b = mm[c].to_numpy(float), orig[c].to_numpy(float)
        assert (np.isnan(a) == np.isnan(b)).all(), c
        ok = ~np.isnan(a)
        assert (a[ok] == -b[ok]).all(), c
    assert rng is not None


def test_ssp_t_f6_coverage_table(built):
    m = built["m"]
    cov = pd.DataFrame(META["coverage"])
    assert int(cov["matches"].sum()) == len(m)
    want = m.groupby(["tour", "season"]).size().rename("n").reset_index()
    j = cov.merge(want, on=["tour", "season"])
    assert (j["matches"] == j["n"]).all() and len(j) == len(want)
    for _, r in cov.iterrows():
        g = m[m["tour"].eq(r["tour"]) & m["season"].eq(r["season"])]
        assert r["spd_f_nonzero"] == int((g["spd_f"] != 0).sum())
        assert r["spd_raw_present"] == int(g["spd_raw"].notna().sum())
        assert r["both_timed_28d"] == int(((g["k28_a"] > 0) & (g["k28_b"] > 0)).sum())
    men = cov[cov["tour"].eq("atp")]
    assert (men.loc[men["season"] >= 2022, "either_timed_28d"] > 0.5 * men.loc[men["season"] >= 2022, "matches"]).all()


def test_ssp_side_diagnostics_consistent(built):
    m = built["m"]
    for s in ("a", "b"):
        none = m[f"hist_{s}"].eq(0)
        assert (m.loc[none, f"f_hat_{s}"] == 0).all()
        assert np.allclose(m.loc[none, f"f_sd_{s}"], math.sqrt(12.0))
        assert m.loc[none, f"L_hat_{s}"].isna().all()
        assert (m[f"k14_{s}"] <= m[f"k28_{s}"]).all() and (m[f"k28_{s}"] <= m[f"hist_{s}"]).all()
        assert (m[f"ks28_{s}"] + m[f"pts28_{s}"] == m[f"k28_{s}"]).all()
        # an earlier round's best-estimate day can fall after the later round's earliest start (clock windows), so
        # the age can be slightly negative; the projection then does not decay (max(es - obs, 0))
        assert (m.loc[~none, f"last_age_{s}"] >= -14).all()
        assert (m.loc[m[f"k14_{s}"] > 0, f"last_age_{s}"] <= 14).all()
