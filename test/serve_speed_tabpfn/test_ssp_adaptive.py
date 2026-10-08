"""Tests of the adaptive speed memory (src/eda/serve_speed_tabpfn/adaptive/adjust.py and score_adaptive.py), on the
harness tests' synthetic stand-in world in a temporary folder, with fake latency variants, fake adaptive columns, fake
frame keys and a fake "study" and "latency run" computed independently by score.py. The real study tree is never
written; no real result is read.

    the applier: sign and mode logic, women unchanged, the season's row of coefficients
    the coefficients: equal score.nudge_parameters on each mode's history; read seasons < Y only; written only when the
    2024-2026 rows equal the published fits; the next season only when the frame holds the last one complete
    the columns are validated; --check reads no result; the date scorer reads no result
    --run reproduces S9 (A) and B-M1 (B) before writing, refuses otherwise, and runs once
    synthetic recovery: the switch wins when the truth follows the modes; a null is not rejected too often
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import adjust as J  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import score_adaptive as SA  # noqa: E402
from test_ssp_harness import ReadSpy, make_world  # noqa: E402

LATE = {"A": 0.0, "B": 0.2, "D": 0.08, "E": 0.12}


def no_labels(monkeypatch) -> None:
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))


def make_adaptive_world(root: Path, seed: int = 0) -> C.Paths:
    """The stand-in world plus: latency/variants.parquet (spd_B_M1, independent of spd_f), adaptive/columns.parquet,
    frame_keys.parquet, passed reuse checks, and the published fits (the study's S9 and the latency run's B-M1)
    computed by score.py on the stand-in labels."""
    P = make_world(root, seed=seed)
    rng = np.random.default_rng([seed, 4242])
    f = pd.read_parquet(P.feature_file, columns=["match_id", "spd_f"])
    men = f["match_id"].str.startswith("atp").to_numpy()
    n = len(f)
    m1 = np.where(men, np.clip(rng.normal(0, 1, n), -4, 4), 0.0)
    (P.out / "latency").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"match_id": f["match_id"], "spd_B_M1": m1}).to_parquet(P.out / "latency" / "variants.parquet",
                                                                          index=False)
    cols = {"match_id": f["match_id"]}
    for s, share in LATE.items():
        la = men & (rng.random(n) < share / 2)
        lb = men & (rng.random(n) < share / 2)
        cols[f"spd_T_{s}"] = f["spd_f"].to_numpy() if s == "A" else np.where(men, 0.9 * f["spd_f"] + rng.normal(0, 0.3, n), 0.0)
        cols[f"spd_L_{s}"] = m1 if s == "B" else np.where(men, m1 + rng.normal(0, 0.3, n), 0.0)
        cols[f"late_a_{s}"], cols[f"late_b_{s}"] = la, lb
        cols[f"mode_{s}"] = np.where(la | lb, "L", "T")
    J.folder(P).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(cols).to_parquet(J.columns_path(P), index=False)
    C.write_json(J.folder(P) / "columns_meta.json", {"probes_pass": True, "reads_results": False,
                                                    "columns_parquet_sha256": C.sha256_file(J.columns_path(P))})
    frame = pd.read_parquet(P.model_frame, columns=["match_id", "tour", "season", "tournament_date"])
    obs = (frame["tournament_date"] - J.EPOCH).dt.days + np.arange(len(frame)) % 5
    frame.assign(obs=obs)[["match_id", "tour", "season", "obs"]].to_parquet(P.out / "frame_keys.parquet", index=False)
    C.write_json(P.checks / "repro_check.json", {"passed": True})
    C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
    publish(P)
    return P


def publish(P: C.Paths, shift: float = 0.0) -> None:
    info = J.history_info(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    y = S.labels(P)
    rows, params = S.nudge(S.Scorer(bank, info, y))
    C.write_json(P.out / "results.json", {"S9": [{**r, "estimate": r["estimate"] + shift} for r in rows],
                                         "S9_parameters": params, "hashes": S.hashes(P, S.population(P))})
    lrows, lparams = S.nudge(S.Scorer(bank, J.with_history(info, "L"), y))
    C.write_json(P.out / "latency" / "results_latency.json",
                 {"variants": {"spd_B_M1": {"S9": lrows, "S9_parameters": lparams}}})


@pytest.fixture(scope="module")
def aworld(tmp_path_factory) -> C.Paths:
    return make_adaptive_world(tmp_path_factory.mktemp("ssp_adaptive_world"))


COEF = {"T": {"2025": {"s_atp": 0.9, "s_wta": 0.92, "b_shrunk": 0.04}},
        "L": {"2025": {"s_atp": 0.8, "s_wta": 0.92, "b_shrunk": 0.10}}}


def test_ssp_adapt_applier_signs_modes_and_women():
    eta = np.array([0.5, 0.5, 0.5, 0.5, -0.2])
    tour = np.array(["atp", "atp", "atp", "atp", "wta"])
    mode = np.array(["T", "L", "T", "L", "L"])
    col_t, col_l = np.array([1.0, 1.0, -1.0, 3.0, 5.0]), np.array([2.0, 2.0, 2.0, -1.0, 5.0])
    q = J.apply(eta, tour, 2025, mode, col_t, col_l, COEF)
    assert np.allclose(q, expit([0.9 * 0.5 + 0.04 * 1, 0.8 * 0.5 + 0.10 * 2, 0.9 * 0.5 - 0.04, 0.8 * 0.5 - 0.10,
                                 0.92 * -0.2]))
    assert q[0] > expit(0.9 * 0.5) > q[2]                                    # sign: a higher speed state helps A
    assert q[4] == pytest.approx(expit(0.92 * -0.2))                          # a woman: the tour slope only
    with pytest.raises(ValueError):
        J.apply(eta, tour, 2025, np.array(["T", "X", "T", "T", "T"]), col_t, col_l, COEF)
    with pytest.raises(KeyError):
        J.apply(eta, tour, 2024, mode, col_t, col_l, COEF)                    # no row for the season


def test_ssp_adapt_fit_equals_nudge_parameters(aworld):
    info = J.history_info(aworld)
    bank = S.Bank(aworld, S.frame_index(aworld), require_checks=False)
    y = S.labels(aworld)
    coef = J.fit(bank, info, y, S.TEST)
    for mode, col in J.HISTORY.items():
        sc = S.Scorer(bank, info.assign(spd_f=info[col]), y)
        for Y in S.TEST:
            assert coef[mode][str(Y)] == S.nudge_parameters(sc, Y), (mode, Y)
    assert coef["T"]["2026"]["s_wta"] == coef["L"]["2026"]["s_wta"]          # women's z is 0 in both histories


def test_ssp_adapt_coefficients_read_earlier_seasons_only(aworld):
    info = J.history_info(aworld).join(SA.columns(aworld))
    bank = S.Bank(aworld, S.frame_index(aworld), require_checks=False)
    y = S.labels(aworld)
    base = J.fit(bank, info, y, S.TEST)
    sc = S.Scorer(bank, info, y)
    joint = {Y: SA.joint_parameters(sc, info, "B", Y) for Y in S.TEST}
    rng = np.random.default_rng(3)
    for Y in S.TEST:
        late = (info["season"] >= Y).to_numpy()
        info2 = info.copy()
        for c in ("spd_f", "spd_B_M1", "spd_T_B", "spd_L_B"):
            info2.loc[late, c] = rng.normal(size=late.sum())
        y2 = y.copy()
        y2[late] = 1 - y2[late]
        bank2 = S.Bank(aworld, S.frame_index(aworld), require_checks=False)
        for s in range(Y, 2027):
            for k in S.SEEDS16:
                b = bank2.blocks("model", s, k)["td"]
                bank2.injected[("model", s, k)] = {"td": pd.Series(rng.random(len(b)), index=b.index)}
        assert J.fit(bank2, info2, y2, (Y,))["T"][str(Y)] == base["T"][str(Y)]
        assert J.fit(bank2, info2, y2, (Y,))["L"][str(Y)] == base["L"][str(Y)]
        assert SA.joint_parameters(S.Scorer(bank2, info2, y2), info2, "B", Y) == joint[Y]


def test_ssp_adapt_coefficients_written_only_when_published_fits_match(aworld, tmp_path):
    out = J.write_coefficients(aworld)
    assert max(out["agreement_with_published"].values()) == 0.0
    assert set(out["T"]) == set(out["L"]) == {"2024", "2025", "2026"}
    assert out["season_2027"].startswith("not yet fittable")                  # the stand-in 2026 ends in October
    P = make_adaptive_world(tmp_path, seed=1)
    publish(P, shift=0.0)
    lat = C.read_json(P.out / "latency" / "results_latency.json")
    lat["variants"]["spd_B_M1"]["S9_parameters"]["2026"]["b_shrunk"] += 1e-6
    C.write_json(P.out / "latency" / "results_latency.json", lat)
    with pytest.raises(RuntimeError, match="do not equal"):
        J.write_coefficients(P)
    assert not J.coefficients_path(P).exists()


def test_ssp_adapt_columns_are_validated(aworld, tmp_path):
    good = pd.read_parquet(J.columns_path(aworld))
    women = good["match_id"].str.startswith("wta").to_numpy()
    first_l = int(np.flatnonzero((good["mode_B"] == "L").to_numpy())[0])
    bads = {"nan": good.assign(spd_T_B=good["spd_T_B"].where(good.index != 7)),
            "women": good.assign(spd_L_D=np.where(women, 0.3, good["spd_L_D"])),
            "mode": good.assign(mode_E=np.where(good.index == 2, "X", good["mode_E"])),
            "late": good.assign(mode_B=np.where(good.index == first_l, "T", good["mode_B"])),
            "missing": good.iloc[3:]}
    for name, bad in bads.items():
        P = aworld.with_(out=tmp_path / name)
        J.folder(P).mkdir(parents=True)
        bad.to_parquet(J.columns_path(P), index=False)
        with pytest.raises(RuntimeError):
            SA.columns(P)


def test_ssp_adapt_check_and_date_read_no_result(aworld, monkeypatch):
    J.write_coefficients(aworld)
    keys = pd.read_parquet(aworld.out / "frame_keys.parquet")
    day = keys.loc[keys["season"] == 2025, "obs"].iloc[10]
    date = str((J.EPOCH + pd.Timedelta(days=int(day))).date())
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    no_labels(monkeypatch)
    out = SA.check(aworld)
    assert out["scenarios"] == ["A", "B", "D", "E"]
    assert out["reproduction_preconditions"] == {"spd_T_A_vs_spd_f": 0.0, "mode_A_all_T": True,
                                                 "spd_L_B_vs_spd_B_M1": 0.0}
    assert out["mode_shares_men"]["A"]["share_L_2024_2026"] == 0.0 and out["mode_shares_men"]["B"]["share_L_2024_2026"] > 0
    t = J.score_date(aworld, date, "B")
    assert len(t) == int((keys["obs"] == day).sum()) and set(t["mode"]) <= {"T", "L"}
    coef = J.load_coefficients(aworld)
    assert np.allclose(t["q"], J.apply(t["eta"], t["tour"], t["season"], t["mode"], t["col_T"], t["col_L"], coef))
    assert (J.folder(aworld) / "scored" / f"{date}_B_L_weekly.csv").exists()


def test_ssp_adapt_run_reproduces_then_runs_once(tmp_path):
    P = make_adaptive_world(tmp_path, seed=2)
    publish(P, shift=0.01)                                                    # a study the run cannot reproduce
    with pytest.raises(RuntimeError, match="reproductions failed"):
        SA.run(P)
    assert not (J.folder(P) / "results_adaptive.json").exists()
    publish(P)
    res = SA.run(P)
    rep = res["reproductions"]
    assert rep["passed"] and max(rep["A_switch_equals_pure_T_equals_S9"]["max_difference"].values()) <= 1e-12
    assert set(res["scenarios"]) == {"A", "B", "D", "E"} and "joint" in res["scenarios"]["D"]
    a = res["scenarios"]["A"]
    assert a["switch"]["pooled"] == a["pure_T"]["pooled"]
    assert (J.folder(P) / "results_adaptive.csv").exists()
    with pytest.raises(RuntimeError, match="once"):
        SA.run(P)


COEF2 = {"T": {"2025": {"s_atp": 0.9, "s_wta": 0.92, "b_shrunk": 0.04}},
         "L_weekly": {"2025": {"s_atp": 0.8, "s_wta": 0.92, "b_shrunk": 0.10}},
         "L_daily": {"2025": {"s_atp": 0.7, "s_wta": 0.92, "b_shrunk": 0.20}}}


def test_ssp_adapt_always_L_by_default_and_the_feed_picks_the_set():
    eta = np.array([0.5, -0.3, 0.4])
    tour = np.array(["atp", "atp", "wta"])
    col_l, col_t = np.array([1.0, -2.0, 7.0]), np.array([9.0, 9.0, 9.0])
    weekly = J.apply(eta, tour, 2025, col_l=col_l, coef=COEF2)                      # no mode: always L, weekly
    assert np.allclose(weekly, expit([0.8 * 0.5 + 0.10, 0.8 * -0.3 - 0.20, 0.92 * 0.4]))
    assert np.allclose(J.apply(eta, tour, 2025, "L", col_t, col_l, COEF2), weekly)    # col_t is ignored in mode L
    daily = J.apply(eta, tour, 2025, col_l=col_l, coef=COEF2, feed="daily")
    assert np.allclose(daily, expit([0.7 * 0.5 + 0.20, 0.7 * -0.3 - 0.40, 0.92 * 0.4]))
    assert weekly[2] == daily[2] == pytest.approx(expit(0.92 * 0.4))                   # women unchanged by the feed
    with pytest.raises(ValueError):
        J.apply(eta, tour, 2025, col_l=col_l, coef=COEF2, feed="hourly")
    only_l = {"L": COEF2["L_weekly"]}                                                 # the switch's table: weekly only
    assert np.allclose(J.apply(eta, tour, 2025, col_l=col_l, coef=only_l), weekly)
    with pytest.raises(KeyError):
        J.apply(eta, tour, 2025, col_l=col_l, coef=only_l, feed="daily")
    with pytest.raises(ValueError):                                                   # a man in T needs col_t
        J.apply(eta, tour, 2025, np.array(["T", "L", "L"]), None, col_l, COEF2)


def test_ssp_adapt_coefficient_sets_and_the_date_default(aworld):
    out = J.write_coefficients(aworld)
    pub = J.published(aworld)
    for y in ("2024", "2025", "2026"):
        assert out["L_weekly"][y] == pub["L"][y] and out["L"][y] == out["L_weekly"][y]   # L_weekly = B-M1, exactly
        assert out["T"][y] == pub["T"][y]
        assert out["L_daily"][y]["s_wta"] == out["L_weekly"][y]["s_wta"]              # women: same tour slope
    assert out["L_daily"] != out["L_weekly"] and set(out["history"]) >= {"L_weekly", "L_daily", "T"}
    keys = pd.read_parquet(aworld.out / "frame_keys.parquet")
    day = keys.loc[keys["season"] == 2026, "obs"].iloc[20]
    date = str((J.EPOCH + pd.Timedelta(days=int(day))).date())
    t = J.score_date(aworld, date)                                                    # defaults: L, weekly, scenario B
    assert set(t["mode"]) == {"L"} and set(t["policy"]) == {"L"} and set(t["feed"]) == {"weekly"}
    assert set(t["scenario"]) == {"B"}
    coef = J.load_coefficients(aworld)
    assert np.allclose(t["q"], J.apply(t["eta"], t["tour"], t["season"], col_l=t["col_L"], coef=coef))
    d = J.score_date(aworld, date, feed="daily")                                      # daily: the D columns, L_daily
    assert set(d["scenario"]) == {"D"}
    assert np.allclose(d["q"], J.apply(d["eta"], d["tour"], d["season"], col_l=d["col_L"], coef=coef, feed="daily"))
    w = t["tour"] == "wta"
    if w.any():
        assert np.allclose(t.loc[w, "q"], expit(coef["L_weekly"]["2026"]["s_wta"] * t.loc[w, "eta"]))


def test_ssp_adapt_L_daily_reads_earlier_seasons_only(aworld):
    info = J.history_info(aworld, with_daily=True)
    bank = S.Bank(aworld, S.frame_index(aworld), require_checks=False)
    y = S.labels(aworld)
    base = J.fit(bank, info, y, S.TEST, sets=("L_daily",))
    rng = np.random.default_rng(11)
    for Y in S.TEST:
        late = (info["season"] >= Y).to_numpy()
        info2 = info.copy()
        info2.loc[late, "spd_L_D"] = rng.normal(size=late.sum())
        y2 = y.copy()
        y2[late] = 1 - y2[late]
        bank2 = S.Bank(aworld, S.frame_index(aworld), require_checks=False)
        for s in range(Y, 2027):
            for k in S.SEEDS16:
                b = bank2.blocks("model", s, k)["td"]
                bank2.injected[("model", s, k)] = {"td": pd.Series(rng.random(len(b)), index=b.index)}
        assert J.fit(bank2, info2, y2, (Y,), sets=("L_daily",))["L_daily"][str(Y)] == base["L_daily"][str(Y)]


def test_ssp_adapt_real_L_weekly_equals_published_B_M1():
    path = J.coefficients_path(C.DEFAULT)
    lat = C.DEFAULT.out / "latency" / "results_latency.json"
    if not path.exists() or not lat.exists() or "L_weekly" not in C.read_json(path):
        pytest.skip("the real coefficient table with L_weekly has not been written yet")
    mine = C.read_json(path)["L_weekly"]
    pub = C.read_json(lat)["variants"]["spd_B_M1"]["S9_parameters"]
    assert all(mine[y] == pub[y] for y in ("2024", "2025", "2026"))


def test_ssp_adapt_run_refuses_an_unpassed_columns_build(tmp_path, monkeypatch):
    P = make_adaptive_world(tmp_path, seed=3)
    no_labels(monkeypatch)
    meta_path = J.folder(P) / "columns_meta.json"
    good = C.read_json(meta_path)
    for bad in ({**good, "probes_pass": False}, {**good, "reads_results": True},
                {**good, "columns_parquet_sha256": "0" * 64}):
        C.write_json(meta_path, bad)
        assert not SA.columns_status(P)["ok"]
        with pytest.raises(RuntimeError, match="columns build"):
            SA.run(P)
    C.write_json(meta_path, good)
    assert SA.columns_status(P)["ok"]


def test_ssp_adapt_synthetic_switch_recovery_and_null(aworld, monkeypatch):
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    no_labels(monkeypatch)
    sm = SA.synthetic(aworld, scenario="B", beta=0.5, reps=4, seed=5, tag="test_planted")["summary"]
    assert sm["switch"]["mean"] > 0 and sm["switch"]["reject_positive"] >= 0.75
    assert sm["switch"]["mean"] > max(sm["pure_T"]["mean"], sm["pure_L"]["mean"])
    null = SA.synthetic(aworld, scenario="B", beta=0.0, reps=6, seed=6, tag="test_null")["summary"]
    for arm in ("pure_T", "pure_L", "switch"):
        assert null[arm]["reject_positive"] <= 0.34, arm
