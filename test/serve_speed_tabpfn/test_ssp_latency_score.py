"""Tests of the latency follow-up's outcome scorer (src/eda/serve_speed_tabpfn/latency/score_latency.py), on the
harness tests' synthetic stand-in world in a temporary folder, plus a fake variants.parquet. The real study tree is never
written and the real variants file is never read.

    the variants are validated (never NaN, women 0, one row per frame match)
    --check is result-free and lists the variants
    with spd_f (and an identical spd_A_M0) the scorer reproduces score.py's S9 and S0 exactly
    --synthetic never selects a_won, recovers a planted beta and does not reject a null too often
    --run reproduces the "study" (computed independently by score.py) before writing, refuses a mismatch and runs once
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
from src.eda.serve_speed_tabpfn.latency import score_latency as LT  # noqa: E402
from test_ssp_harness import ReadSpy, make_world  # noqa: E402


def write_variants(P: C.Paths, seed: int = 0, **override) -> pd.DataFrame:
    """spd_A_M0 = spd_f exactly; spd_B_M0 a delayed, attenuated copy; spd_B_M2 close to spd_f; spd_L7_M0 noise.
    Its own seed stream: make_world draws the base's log-odds first from default_rng(seed), and the same seed here would
    make the first noise draw a scaled copy of them (a variant collinear with the base)."""
    rng = np.random.default_rng([seed, 777])
    f = pd.read_parquet(P.feature_file, columns=["match_id", "spd_f"])
    men = f["match_id"].str.startswith("atp").to_numpy()
    n = len(f)
    v = pd.DataFrame({"match_id": f["match_id"], "spd_A_M0": f["spd_f"],
                      "spd_B_M0": np.where(men, 0.6 * f["spd_f"] + rng.normal(0, 0.8, n), 0.0),
                      "spd_B_M2": np.where(men, f["spd_f"] + rng.normal(0, 0.3, n), 0.0),
                      "spd_L7_M0": np.where(men, rng.normal(0, 1, n), 0.0),
                      "diagnostic_not_a_variant": rng.normal(size=n)})
    for k, val in override.items():
        v[k] = val
    LT.folder(P).mkdir(parents=True, exist_ok=True)
    v.to_parquet(LT.variants_path(P), index=False)
    (LT.folder(P) / "plan.md").write_text("fixed plan (stand-in)\n", encoding="utf-8")
    return v


@pytest.fixture(scope="module")
def lworld(tmp_path_factory) -> C.Paths:
    P = make_world(tmp_path_factory.mktemp("ssp_latency_world"))
    write_variants(P)
    return P


def fake_outcomes(P: C.Paths, beta: float = 0.3, seed: int = 4) -> tuple[pd.DataFrame, pd.Series, S.Bank]:
    info = LT.population(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index).to_numpy()
    rng = np.random.default_rng(seed)
    y = pd.Series((rng.random(len(info)) < expit(0.9 * eta + beta * info["spd_f"].to_numpy())).astype(float),
                  index=info.index)
    return info, y, bank


def test_ssp_lat_variants_are_validated(lworld, tmp_path):
    cols = LT.variant_columns(lworld)
    assert cols == ["spd_A_M0", "spd_B_M0", "spd_B_M2", "spd_L7_M0"]            # the diagnostic is not a variant
    good = pd.read_parquet(LT.variants_path(lworld))
    women = good["match_id"].str.startswith("wta").to_numpy()
    for name, bad in (("nan", good.assign(spd_B_M0=good["spd_B_M0"].where(good.index != 3))),
                      ("women", good.assign(spd_B_M2=np.where(women, 0.5, good["spd_B_M2"]))),
                      ("missing", good.iloc[5:]), ("duplicate", pd.concat([good, good.iloc[:1]]))):
        P = lworld.with_(out=tmp_path / name)
        LT.folder(P).mkdir(parents=True)
        bad.to_parquet(LT.variants_path(P), index=False)
        with pytest.raises(RuntimeError):
            LT.population(P)


def test_ssp_lat_check_is_result_free(lworld, monkeypatch):
    study_results(lworld)                       # setup (stand-in labels); the check itself reads only its hashes
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    out = LT.check(lworld)
    assert out["variants"] == ["spd_A_M0", "spd_B_M0", "spd_B_M2", "spd_L7_M0"]
    assert out["headline_present"] == {"spd_B_M0": True, "spd_B_M2": True} and out["a_variant_present"]
    vals = out["values_men_2024_2026"]
    assert vals["spd_A_M0"]["max_abs_diff_from_spd_f"] == 0 and vals["spd_A_M0"]["corr_with_spd_f"] == pytest.approx(1)
    assert out["population_equals_study"] and all(out["same_inputs_as_the_study"].values())
    assert (LT.folder(lworld) / "check_latency.json").exists()


def test_ssp_lat_reference_reproduces_score_py_exactly(lworld):
    info, y, bank = fake_outcomes(lworld)
    sc = S.Scorer(bank, info, y)
    rows, params = S.nudge(sc)
    s0 = S.information(sc, "spd_f", S.TEST)
    for col in (LT.REFERENCE, "spd_A_M0"):
        r = LT.score_variant(bank, info, y, col)
        for label in ("S9_shrunk", "S9_mle"):
            assert LT.gain(r, label) == next(x["estimate"] for x in rows if x["cid"] == label)
        assert r["S0"]["estimate"] == s0["estimate"] and r["S9_parameters"] == params
    by = LT.score_variant(bank, info, y, "spd_B_M2")["S9_by_season"]
    assert [x["cid"] for x in by] == [f"S9_{v}_{s}" for v in ("shrunk", "mle") for s in S.TEST]


def test_ssp_lat_signs_and_shares(lworld):
    info, y, bank = fake_outcomes(lworld, beta=0.4)
    res = LT.evaluate(bank, info, y, LT.variant_columns(lworld))
    ref = res["reference"]
    assert LT.gain(ref, "S9_shrunk") > 0 and ref["S0"]["lo"] > 0                 # the planted signal is found
    a0 = res["variants"]["spd_A_M0"]
    assert a0["share_of_A"]["S9_shrunk"] == pytest.approx(1.0)
    noise = res["variants"]["spd_L7_M0"]
    assert noise["S0"]["lo"] <= 0 <= noise["S0"]["hi"] or abs(noise["S0"]["estimate"]) < 0.1
    near = res["variants"]["spd_B_M2"]
    assert near["share_of_A"]["S9_shrunk"] == pytest.approx(LT.gain(near, "S9_shrunk") / LT.gain(ref, "S9_shrunk"))
    assert near["S0"]["unit"].startswith("log-odds per unit of spd_B_M2")
    t = LT.table(res)
    assert set(t["endpoint"]) >= {"S9_shrunk", "S9_mle", "S0", "S9_shrunk_2024"} and t["headline"].any()


def test_ssp_lat_synthetic_recovers_and_never_reads_a_won(lworld, monkeypatch):
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    out = LT.synthetic(lworld, plant="spd_B_M2", beta=0.4, reps=8, seed=2, tag="test_planted")
    sm = out["summary"]["spd_B_M2"]
    assert abs(sm["S0_b_mean"] - 0.4) < 0.08 and sm["S0_covers_beta"] >= 0.6
    null = LT.synthetic(lworld, plant="spd_B_M2", beta=0.0, reps=12, seed=3, tag="test_null")["summary"]
    for col, s in null.items():
        assert s["S0_reject_two_sided"] <= 0.34 and s["S9_reject_positive"] <= 0.34, col   # loose: 12 replicates


def study_results(P: C.Paths, nudge_shift: float = 0.0) -> dict:
    """The 'study' as score.py computes it, independently of the latency scorer, with the stand-in labels."""
    info = S.population(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    sc = S.Scorer(bank, info, S.labels(P))
    rows, params = S.nudge(sc)
    rows = [{**r, "estimate": r["estimate"] + nudge_shift} for r in rows]
    out = {"S9": rows, "S9_parameters": params, "S0": S.information(sc, "spd_f", S.TEST),
           "hashes": S.hashes(P, info)}
    C.write_json(P.out / "results.json", out)
    return out


def test_ssp_lat_run_reproduces_then_runs_once(lworld, tmp_path):
    P = make_world(tmp_path)
    write_variants(P)
    C.write_json(P.checks / "repro_check.json", {"passed": True})
    C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
    study_results(P, nudge_shift=0.01)                                           # a "study" the harness cannot match
    with pytest.raises(RuntimeError, match="does not reproduce"):
        LT.run(P)
    assert not (LT.folder(P) / "results_latency.json").exists()
    study_results(P)
    res = LT.run(P)
    assert res["reproduction"]["passed"] and max(abs(v) for v in res["reproduction"]["differences"].values()) == 0
    assert set(res["variants"]) == {"spd_A_M0", "spd_B_M0", "spd_B_M2", "spd_L7_M0"}
    assert (LT.folder(P) / "results_latency.csv").exists()
    with pytest.raises(RuntimeError, match="once"):
        LT.run(P)


def test_ssp_lat_run_refuses_changed_inputs(tmp_path, monkeypatch):
    P = make_world(tmp_path)
    write_variants(P)
    C.write_json(P.checks / "repro_check.json", {"passed": True})
    C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
    study = study_results(P)
    study["hashes"]["FEATURE_SHA256"] = "0" * 64
    C.write_json(P.out / "results.json", study)
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    with pytest.raises(RuntimeError, match="differ from the study"):
        LT.run(P)
