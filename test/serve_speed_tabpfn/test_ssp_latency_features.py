"""Tests of the latency variants (latency/plan.md; src/eda/serve_speed_tabpfn/latency/features_latency.py).

Run: ./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_latency_features.py -q
They read the built outputs (data/studies/serve_speed_tabpfn/latency/) and recompute parts on subsets. No match result
is read anywhere (box scores with an explicit column list).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

META = json.loads(FL.META.read_text(encoding="utf-8")) if FL.META.exists() else None
pytestmark = pytest.mark.skipif(META is None, reason="latency variants not built yet")
NAMES = ["A_M0", "Astrict_M0", "L1_M0", "L3_M0", "L7_M0", "L14_M0", "B_M0", "B_M1", "B_M2", "L7_M1", "L7_M2"]


@pytest.fixture(scope="module")
def ctx():
    p = FL.load_panel()
    keys = P.load_frame_keys()
    t = F.side_targets(keys)
    tm = t[t["tour"].eq("atp")].reset_index(drop=True)
    avail = FL.load_availability()
    rd = FL.release_days(p, avail)
    v = pd.read_parquet(FL.VARIANTS)
    return {"p": p, "keys": keys, "tm": tm, "rd": rd, "v": v, "avail": avail}


def test_ssp_lat_columns_complete(ctx):
    v = ctx["v"]
    assert len(v) == 63737 and v["match_id"].is_unique
    assert [c for c in v.columns if c != "match_id"] == [f"spd_{n}" for n in NAMES]
    tour = v["match_id"].map(ctx["keys"].set_index("match_id")["tour"])
    for c in v.columns[1:]:
        assert v[c].notna().all() and (v[c].abs() <= 4.0).all(), c
        assert (v.loc[tour.eq("wta"), c] == 0).all(), c


def test_ssp_lat_A_reproduces_spd_f_exactly(ctx):
    s = pd.read_parquet(F.FEATURES, columns=["match_id", "spd_f"]).set_index("match_id")["spd_f"]
    v = ctx["v"].set_index("match_id")["spd_A_M0"]
    assert (v.reindex(s.index).to_numpy() == s.to_numpy()).all()
    assert META["standardisation_sd_km_h"]["A_M0"] == json.loads(F.META.read_text(encoding="utf-8"))["s_f"]


def test_ssp_lat_standardisation(ctx):
    v = ctx["v"].set_index("match_id")
    k = ctx["keys"].set_index("match_id")
    men = (k["tour"].eq("atp") & k["season"].between(2022, 2023)).reindex(v.index)
    for n in NAMES:
        sd = float(v.loc[men.to_numpy(), f"spd_{n}"].std(ddof=1))
        assert 0.93 < sd <= 1.0 + 1e-9, (n, sd)         # 1 before clipping at +-4
        assert META["standardisation_sd_km_h"][n] > 0


def test_ssp_lat_release_rule_honoured(ctx):
    """Every history row of a lagged / B side is released by the side's es and is own history (earlier event or
    earlier round); nowcast rows are unreleased speeds whose box score is released."""
    p, tm, rd = ctx["p"], ctx["tm"], ctx["rd"]
    rng = np.random.default_rng(1)
    S = tm.iloc[rng.choice(len(tm), 3000, replace=False)].reset_index(drop=True)
    box = FL.box_table("atp")
    W = FL.nowcast_inputs(FL.box_deviations(p, box), META["nowcast"]["fit"])
    for scen in ("B", "L7", "L1"):
        rel = rd[scen].to_numpy(np.int64)
        h = FL.histories_rel(p, S, rel, rd["box"].to_numpy(np.int64), np.isfinite(W))
        idx, nc = h["idx"], h["nc"]
        ok = idx >= 0
        rr = rel[np.maximum(idx, 0)]
        es = S["es"].to_numpy(float)[:, None]
        assert (rr[ok & ~nc] <= es.repeat(idx.shape[1], 1)[ok & ~nc]).all()
        assert (rr[ok & nc] > es.repeat(idx.shape[1], 1)[ok & nc]).all()
        br = rd["box"].to_numpy(np.int64)[np.maximum(idx, 0)]
        assert (br[ok & nc] <= es.repeat(idx.shape[1], 1)[ok & nc]).all()
        assert np.isfinite(W[idx[ok & nc]]).all()
        td = p["tdate"].to_numpy(float)[np.maximum(idx, 0)]
        tid = p["tournament_id"].astype(str).to_numpy()[np.maximum(idx, 0)]
        ro = p["round_order"].to_numpy(float)[np.maximum(idx, 0)]
        earlier = (td < S["tdate"].to_numpy(float)[:, None]) | (
            (tid == S["tournament_id"].astype(str).to_numpy()[:, None]) & (ro < S["round_order"].to_numpy(float)[:, None]))
        assert earlier[ok].all()


def test_ssp_lat_filter_without_nowcast_is_features_kalman(ctx):
    rng = np.random.default_rng(2)
    nt, H = 400, 12
    Z = rng.normal(190, 6, (nt, H))
    Z[:, 8:] = np.nan
    R = rng.uniform(8, 15, (nt, H))
    DAY = np.cumsum(rng.integers(0, 9, (nt, H)), axis=1).astype(float) + 19000
    tday = DAY[:, 7] + rng.integers(0, 20, nt)
    a = FL.kalman_nc(Z, R, DAY, tday, FL.MEN, np.zeros((nt, H), bool), np.full((nt, H), np.nan), 0.9)
    b = F.kalman(Z, R, DAY, tday, FL.MEN)
    for c in ("f_hat", "f_sd", "L_hat"):
        assert np.array_equal(a[c], b[c], equal_nan=True)


def test_ssp_lat_nowcast_rows_need_a_known_level():
    """A nowcast row before any released speed does not enter (the diffuse level is unknown); one after does."""
    Z = np.array([[np.nan, 190.0, np.nan], [190.0, np.nan, np.nan]])
    NC = np.array([[True, False, False], [False, True, False]])
    W = np.array([[3.0, np.nan, np.nan], [np.nan, 3.0, np.nan]])
    R = np.array([[30.0, 10.0, np.nan], [10.0, 30.0, np.nan]])
    DAY = np.array([[19000.0, 19003.0, np.nan], [19000.0, 19003.0, np.nan]])
    r = FL.kalman_nc(Z, R, DAY, np.array([19004.0, 19004.0]), FL.MEN, NC, W, 0.93)
    alone = F.kalman(np.array([[190.0]]), np.array([[10.0]]), np.array([[19003.0]]), np.array([19004.0]), FL.MEN)
    assert np.isclose(r["f_hat"][0], alone["f_hat"][0], atol=1e-12)         # the leading nowcast was skipped
    assert r["f_hat"][1] > 0                                                  # +3 km/h box-implied deviation entered


def test_ssp_lat_nowcast_design_frozen_on_le_2022():
    nc = META["nowcast"]
    assert nc["fit"]["rows_tune"] > 5000 and nc["fit"]["rows_check"] > 3000
    assert set(nc["fit"]["coef"]) == {"c0", "a_f", *FL.DEV}
    assert "won" not in FL.BOX_COLS and not ({"sets_won_n", "games_won_n"} & set(FL.BOX_COLS))
    for s in ("B", "L7"):
        m2 = META["m2"][s]
        assert m2["R_nc"] == pytest.approx(m2["mult"] * nc["fit"]["resid_var_tune"])
        assert "info_gain_check_2023" in m2["at_best"]
        assert META["m1"][s]["hl"] in FL.HL_GRID


def test_ssp_lat_probe_b_records():
    pr = META["probes"]
    assert set(pr) >= {"B_M0", "B_M2"} and META["probes_pass"] is True
    for k, r in pr.items():
        assert r["pass"] and r["moved"] == 0 and r["leaky_control_moved"] > 0 and r["days"] >= 15, k
        assert r["tolerance"] <= 1e-12 and "g_sum" in r["values_checked"]


def test_ssp_lat_probe_b_machinery(ctx):
    """A small re-run of Probe B (B with the nowcast, two days, 2,000 men's sides): nothing moves; the leak does."""
    rng = np.random.default_rng(4)
    tm = ctx["tm"]
    sub = tm.iloc[np.sort(rng.choice(len(tm), 2000, replace=False))].reset_index(drop=True)
    box = FL.box_table("atp")
    fit = META["nowcast"]["fit"]
    days = [float((pd.Timestamp(d) - pd.Timestamp("1970-01-01")).days) for d in ("2024-07-10", "2025-06-04")]
    r = FL.probe_b_latency("B_M2", "B", ctx["p"], ctx["rd"], sub, FL.MEN,
                           {"fit": fit, "box": box, "box_rel": FL.box_release_of(box, ctx["avail"]),
                            "R": META["m2"]["B"]["R_nc"]}, days)
    assert r["moved"] == 0 and r["leaky_control_moved"] > 0


def test_ssp_lat_flip_negates(ctx):
    """Exchanging A and B negates a variant's column exactly (B with the nowcast, 300 men's matches)."""
    keys = ctx["keys"]
    k = keys[keys["tour"].eq("atp") & keys["season"].ge(2022)].sample(300, random_state=3)
    flip = k.copy()
    flip["player_a_id"], flip["player_b_id"] = k["player_b_id"].to_numpy(), k["player_a_id"].to_numpy()
    p, rd = ctx["p"], ctx["rd"]
    box = FL.box_table("atp")
    W = FL.nowcast_inputs(FL.box_deviations(p, box), META["nowcast"]["fit"])
    S = FL.Scenario("B", p, rd["B"].to_numpy(np.int64), rd["box"].to_numpy(np.int64))
    nc = {"W": W, "R": META["m2"]["B"]["R_nc"], "a": META["nowcast"]["fit"]["coef"]["a_f"]}
    out = {}
    for lab, kk in (("orig", k), ("flip", flip)):
        t = F.side_targets(kk)
        sv = FL.side_values_v(S, t, FL.MEN, nowcast=nc)
        d = FL.frame_differences(sv, t)
        out[lab] = np.clip(d["d"].to_numpy() / META["standardisation_sd_km_h"]["B_M2"], -4, 4)
    assert (out["flip"] == -out["orig"]).all()
    stored = ctx["v"].set_index("match_id").loc[k["match_id"], "spd_B_M2"].to_numpy()
    assert np.array_equal(stored, out["orig"])
