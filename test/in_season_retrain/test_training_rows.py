"""The in-season retrain's rule (the owner, 20 Oct 2026): the training rows, the cut-off record, stage 2's grown set.

Run: ./python.sh -m pytest test/in_season_retrain -q
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "eda" / "daily_prediction"))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import training_rows as TR  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-16"
needs_instance = pytest.mark.skipif(not (INSTANCE / "model_frame.parquet").exists(), reason="no 16 Oct instance")


def _frame():
    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import arms as A
    P = FITS.paths(INSTANCE)
    return A.load_frame([], P, labels=True), A.arm_inputs("model", P), A


@needs_instance
def test_without_a_record_the_rows_are_the_season_rule():
    frame, cols, A = _frame()
    assert TR.read_cutoff(INSTANCE) is None
    for season in (2025, 2026):
        got, want = TR.job_data(frame, cols, season, INSTANCE), A.job_data(frame, cols, season)
        pd.testing.assert_frame_equal(got[0], want[0])
        assert np.array_equal(got[1], want[1]) and np.array_equal(got[3], want[3])


def _tmp_instance(tmp_path: Path, fits_seasons=()) -> Path:
    inst = tmp_path / "template_test"
    inst.mkdir()
    for f in ("model_frame.parquet", "model_inputs.json"):
        shutil.copy2(INSTANCE / f, inst / f)
    if fits_seasons:
        (inst / "fits").mkdir()
        for s in fits_seasons:
            for k in range(4):
                shutil.copy2(INSTANCE / "fits" / f"model__{s}__seed{k}.npz", inst / "fits" / f"model__{s}__seed{k}.npz")
    return inst


@needs_instance
def test_the_record_admits_exactly_the_results_that_count_by_the_cutoff(tmp_path):
    inst = _tmp_instance(tmp_path)
    rec = TR.write_cutoff(inst, "2026-07-01")
    frame, cols, A = _frame()
    clock = pd.read_parquet(TR.TIMING, columns=["match_id", "lf"]).astype({"match_id": str}).set_index("match_id")["lf"]
    s26 = frame[frame["season"] == 2026]
    want = sorted(s26.loc[(clock.reindex(s26["match_id"].astype(str)).to_numpy() + 1
                           <= TR.day_number("2026-07-01")), "match_id"].astype(str))
    assert rec["ids"] == want and rec["admitted"] == len(want) > 0
    X, y, Xt, test_ids = TR.job_data(frame, cols, 2026, inst)
    assert len(X) == len(A.job_data(frame, cols, 2026)[0]) + len(want) == rec["train_rows"]
    assert set(map(str, test_ids)).isdisjoint(want)
    assert TR.job_data(frame, cols, 2025, inst)[0].shape == A.job_data(frame, cols, 2025)[0].shape   # other seasons
    # an altered list, or a frame changed after the record, is refused
    bad = json.loads((inst / TR.CUTOFF_FILE).read_text(encoding="utf-8"))
    bad["ids"] = bad["ids"][1:]
    (inst / TR.CUTOFF_FILE).write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        TR.admitted_ids(inst, 2026)
    TR.write_cutoff(inst, "2026-07-01")
    with open(inst / "model_frame.parquet", "ab") as f:
        f.write(b"\0")
    with pytest.raises(RuntimeError, match="another frame"):
        TR.admitted_ids(inst, 2026)


def test_walk_forward_on_equals_walk_forward():
    rng = np.random.default_rng(1)
    n = 4000
    ids = pd.Index([f"m{i}" for i in range(n)])
    info = pd.DataFrame({"tour": np.where(rng.random(n) < 0.5, "atp", "wta"), "season": rng.integers(2019, 2026, n),
                         "debut": rng.random(n) < 0.05}, index=ids)
    eta = pd.Series(rng.normal(0, 1, n), index=ids)
    z = pd.Series(np.where(info["tour"] == "atp", rng.normal(0, 1, n), 0.0), index=ids)
    info["y"] = (rng.random(n) < 1 / (1 + np.exp(-(0.9 * eta + 0.05 * z)))).astype(float)
    for Y in (2023, 2026):
        hist = info.index[(info["season"] < Y) & ~info["debut"]]
        assert CMP.walk_forward_on(eta, info, z, hist) == CMP.walk_forward(eta, info, z, (Y,))[Y]


@needs_instance
def test_the_grown_stage2_set(tmp_path, monkeypatch):
    """A copy of the 16 Oct instance with a cut-off and its extended speed table: the grown set reads the admitted
    matches; the annual set beside it equals the engine's held record of the instance itself."""
    import dp_predict as PR
    from src.eda.in_season_retrain import speed_extend as SE
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    monkeypatch.setattr(PR, "STAGE2", tmp_path / "stage2")
    # the held record below was fitted on the backfilled history's column, before the speed repair of 22 Oct 2026
    # (docs/decisions/2026-10-22-source-reconciliation-repairs.md): the extended table is built on that pair here
    monkeypatch.setattr(SE, "decided", lambda: (LP.BACKFILLED, LP.COLUMN_BACKFILLED))
    inst = _tmp_instance(tmp_path, fits_seasons=range(2019, 2027))
    rec = TR.write_cutoff(inst, "2026-10-01")
    with pytest.raises(SystemExit, match="speed column lacks"):              # condition 1: no grown set without it
        PR.coefficients(2026, inst, "daily")
    ext = SE.run(inst, 2026)
    assert ext["check_passed"] and ext["missing_after"] == 0
    grown = PR.coefficients(2026, inst, "daily")
    annual = PR.coefficients(2026, inst, "daily", grown=False)
    assert grown["set"] == "grown" and grown["keys"]["admitted"] == rec["admitted"]
    held = json.loads((ROOT / "data" / "studies" / "daily_prediction" / "stage2"
                       / "template_2026-10-16_2026_daily.json").read_text(encoding="utf-8"))
    for k in ("s_atp", "s_wta", "b_shrunk", "b_mle", "se_b"):
        assert annual[k] == held[k], k                                     # the annual set unchanged, bit for bit
    assert grown["matches"] > annual["matches"]
    assert grown["b_shrunk"] != annual["b_shrunk"]
