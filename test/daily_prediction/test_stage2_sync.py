"""Stage 2 kept in sync with the model under it, and the speed feed by the match's day (part 4, 14 Oct 2026).

    * a stage-2 record is reused only while everything it was fitted from is unchanged: the frame, the input list, the
      seeds 0-3 fit files and the TabPFN they were made with, the speed column and the feed's history column
    * fits made with mixed or unrecorded TabPFN records are refused
    * a run is refused when its live fit's TabPFN version, weights, settings or input list differ from those fits'
    * a match from 8 Oct 2026 (the daily collector's first day in the live panel) takes the daily set, an earlier one
      the weekly set; with one feed the numbers are adjust.apply's single call, bit for bit
Fast: no GPU, no build tree, no repository data (a fake instance in tmp_path).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

from conftest import ROOT

import dp_common as DC
import dp_predict as PR

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKPOINT = "C:/Users/x/AppData/Roaming/tabpfn/tabpfn-v3.5-20260909.safetensors"
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
COLUMNS = ("odds_logit", "elo_games")


def write_fit(path: Path, season: int, seed: int, version: str | None = "9.1.0", p: float = 0.5,
              checkpoint: str = CHECKPOINT, columns=COLUMNS) -> None:
    meta = {"arm": "model", "season": season, "seed": seed, "config": {**CONFIG, "random_state": seed},
            "versions": {"tabpfn": version, "torch": "2.11.0+cu128"}, "checkpoint": checkpoint,
            "device": "a card", "columns": list(columns)}
    np.savez(path, meta=json.dumps(meta), p_td=np.array([p, 1 - p]), ids_td=np.array(["m1"]))


def fake_instance(root: Path, version: str | None = "9.1.0") -> Path:
    inst = root / "template_fake"
    (inst / "fits").mkdir(parents=True)
    pd.DataFrame({"match_id": ["m1"], "season": [2019]}).to_parquet(inst / "model_frame.parquet")
    (inst / "model_inputs.json").write_text(json.dumps({"inputs": [{"name": c} for c in COLUMNS]}), encoding="utf-8")
    for s in (2019, 2020):
        for k in range(4):
            write_fit(inst / "fits" / f"model__{s}__seed{k}.npz", s, k, version)
    return inst


@pytest.fixture
def speed(tmp_path, monkeypatch) -> Path:
    f = tmp_path / "speed.parquet"
    pd.DataFrame({"match_id": ["m1"], "spd_L_B": [0.5], "spd_L_D": [0.7]}).to_parquet(f)
    monkeypatch.setattr(PR, "SPEED_COLUMN", f)
    return f


def test_feed_follows_the_match_day():
    days = [DC.day_of(d) for d in ("2026-07-15", "2026-10-07", "2026-10-08", "2026-10-14")]
    assert PR.feed_of(days).tolist() == ["weekly", "weekly", "daily", "daily"]
    inst = Path("x") / "template_2026-10-14"
    assert PR.coef_path(inst, 2026, "weekly").name == "template_2026-10-14_2026.json"      # its name since 10 Oct
    assert PR.coef_path(inst, 2026, "daily").name == "template_2026-10-14_2026_daily.json"
    ADJ = PR._mods()[3]
    assert PR.FEED_COLUMN["daily"] == ADJ.SETS["L_daily"]
    assert PR.FEED_COLUMN["weekly"] == "spd_L_B"                                         # adjust: spd_B_M1 = spd_L_B


def test_stage2_keys_see_every_input_of_the_fit(tmp_path, speed):
    inst = fake_instance(tmp_path)
    k0 = PR.stage2_keys(2021, inst, "weekly")
    assert k0 == PR.stage2_keys(2021, inst, "weekly")                     # nothing changed: the record would be reused
    assert k0["fit_files"] == 8 and k0["speed_history"] == "spd_L_B"
    assert {k: k0["fits_model"][k] for k in ("tabpfn", "checkpoint", "config")} == {
        "tabpfn": "9.1.0", "checkpoint": "tabpfn-v3.5-20260909.safetensors", "config": CONFIG}
    kd = PR.stage2_keys(2021, inst, "daily")                              # the daily set is a record of its own
    assert kd["speed_history"] == "spd_L_D" and kd["feed"] == "daily" and kd != k0

    mi = inst / "model_inputs.json"                                       # the input list edited in place
    held = mi.read_bytes()
    mi.write_text(json.dumps({"inputs": [{"name": "odds_logit"}]}), encoding="utf-8")
    assert PR.stage2_keys(2021, inst, "weekly")["inputs_sha256"] != k0["inputs_sha256"]
    mi.write_bytes(held)

    f = inst / "fits" / "model__2020__seed3.npz"                          # one fit redone in place, same TabPFN
    held = f.read_bytes()
    write_fit(f, 2020, 3, p=0.6)
    k1 = PR.stage2_keys(2021, inst, "weekly")
    assert k1["fits_sha256"] != k0["fits_sha256"] and k1["fits_model"] == k0["fits_model"]
    f.write_bytes(held)
    assert PR.stage2_keys(2021, inst, "weekly") == k0

    pd.DataFrame({"match_id": ["m1"], "spd_L_B": [0.6], "spd_L_D": [0.7]}).to_parquet(speed)   # the speed column rewritten
    assert PR.stage2_keys(2021, inst, "weekly")["speed_column_sha256"] != k0["speed_column_sha256"]

    for s in (2019, 2020):                                                # every fit redone after a TabPFN upgrade
        for k in range(4):
            write_fit(inst / "fits" / f"model__{s}__seed{k}.npz", s, k, version="9.2.0")
    k2 = PR.stage2_keys(2021, inst, "weekly")
    assert k2["fits_model"]["tabpfn"] == "9.2.0" and k2["fits_sha256"] != k0["fits_sha256"]
    write_fit(inst / "fits" / "model__2019__seed0.npz", 2019, 0, version="9.1.0")   # mixed: refused
    with pytest.raises(RuntimeError, match="different TabPFN records"):
        PR.stage2_keys(2021, inst, "weekly")


def test_fits_without_their_tabpfn_record_are_refused(tmp_path, speed):
    inst = fake_instance(tmp_path, version=None)
    with pytest.raises(RuntimeError, match="do not record"):
        PR.stage2_keys(2021, inst, "weekly")


def test_a_held_record_is_reused_only_while_its_keys_hold(tmp_path, monkeypatch):
    monkeypatch.setattr(PR, "STAGE2", tmp_path / "stage2")
    keys = {"season": 2026, "feed": "daily", "fits_sha256": "a"}
    monkeypatch.setattr(PR, "stage2_keys", lambda season, instance, feed: dict(keys))
    inst = tmp_path / "template_x"
    DC.write_json(PR.coef_path(inst, 2026, "daily"), {"keys": dict(keys), "s_atp": 0.9, "s_wta": 0.92, "b_shrunk": 0.04})
    assert PR.coefficients(2026, inst, "daily")["s_atp"] == 0.9            # unchanged: reused, nothing refitted

    def refit(*args, **kwargs):
        raise LookupError("refit")
    monkeypatch.setattr(PR._mods()[0], "inputs_frame", refit)
    keys["fits_sha256"] = "b"                                             # a fit file changed: fitted again
    with pytest.raises(LookupError, match="refit"):
        PR.coefficients(2026, inst, "daily")
    with pytest.raises(ValueError):
        PR.coefficients(2026, inst, "hourly")


def test_the_live_fit_must_be_the_model_the_coefficients_were_fitted_on():
    rec = {"keys": {"fits_model": {"tabpfn": "9.1.0", "checkpoint": "tabpfn-v3.5-20260909.safetensors",
                                   "config": dict(CONFIG), "inputs_sha256": PR.list_sha256(COLUMNS)}}}

    def fit(**over) -> dict:
        f = {"versions": {"tabpfn": "9.1.0", "torch": "2.11.0+cu128"}, "config": dict(CONFIG), "inputs": list(COLUMNS),
             "seeds": {"2026_0": {"checkpoint": CHECKPOINT}, "2026_1": {"checkpoint": CHECKPOINT}}}
        f.update(over)
        return f
    PR.check_live_fit(fit(), rec)                                         # the same model: passes
    PR.check_live_fit(fit(versions={"tabpfn": "9.1.0", "torch": "2.12.0"}), rec)    # torch alone: listed, not required
    for bad in ({"versions": {"tabpfn": "9.2.0"}}, {"config": {**CONFIG, "n_estimators": 16}},
                {"inputs": ["odds_logit"]}, {"seeds": {"2026_0": {"checkpoint": "C:/w/tabpfn-v3.6.safetensors"}}},
                {"seeds": {"2026_0": {"checkpoint": CHECKPOINT}, "2026_1": {"checkpoint": "C:/w/other.safetensors"}}}):
        with pytest.raises(RuntimeError, match="not the model"):
            PR.check_live_fit(fit(**bad), rec)


def test_each_feed_gets_its_own_set():
    ADJ = PR._mods()[3]
    coef = {"L_weekly": {"2026": {"s_atp": 0.90, "s_wta": 0.92, "b_shrunk": 0.037}},
            "L_daily": {"2026": {"s_atp": 0.95, "s_wta": 0.97, "b_shrunk": 0.05}}}
    rng = np.random.default_rng(0)
    n, k = 6, 5
    eta_o, eta_g = rng.normal(size=n), rng.normal(size=(n, k))
    tour = np.array(["atp", "wta", "atp", "atp", "wta", "atp"])
    seasons = np.full(n, 2026)
    spd = np.array([1.0, 0.0, -2.0, 0.5, 0.0, 3.0])
    feeds = np.array(["weekly", "weekly", "daily", "daily", "daily", "weekly"])
    q_o, q_g = PR.apply_stage2(eta_o, eta_g, tour, seasons, feeds, spd, coef)
    for i in range(n):
        c = coef[f"L_{feeds[i]}"]["2026"]
        s = c["s_atp"] if tour[i] == "atp" else c["s_wta"]
        z = spd[i] if tour[i] == "atp" else 0.0
        assert q_o[i] == pytest.approx(expit(s * eta_o[i] + c["b_shrunk"] * z), rel=1e-12)
        assert q_g[i] == pytest.approx(expit(s * eta_g[i] + c["b_shrunk"] * z), rel=1e-12)
    one = np.full(n, "weekly")                                            # one feed: adjust.apply's numbers exactly
    q1, g1 = PR.apply_stage2(eta_o, eta_g, tour, seasons, one, spd, coef)
    assert np.array_equal(q1, ADJ.apply(eta_o, tour, seasons, "L", col_l=spd, coef=coef, feed="weekly"))
    assert np.array_equal(g1, ADJ.apply(eta_g.ravel(), np.repeat(tour, k), np.repeat(seasons, k), "L",
                                        col_l=np.repeat(spd, k), coef=coef, feed="weekly").reshape(n, k))


def test_the_notebook_labels_each_record_by_season_and_feed():
    from src.pipeline import train as T
    inst = Path("x") / "template_2026-10-14"
    assert T._stage2_label(Path("s") / "template_2026-10-14_2026.json", inst) == "2026"
    assert T._stage2_label(Path("s") / "template_2026-10-14_2026_daily.json", inst) == "2026 daily"
