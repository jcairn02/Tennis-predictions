"""Tests of the paired seed term (serve_speed_tabpfn/score.paired_stats, matched_seeds) and compare.py's reading of it.

docs/studies/adoption_framework/checklist.md, item 1. Arms run with the same seed indices share their seed noise; the
unpaired term (both arms' seed variances added) counts it twice. Synthetic and offline:
    * identical arms, paired: an estimate of exactly 0 with a zero-width interval (unpaired, they got an interval);
    * on a toy example, the paired seed term is var(seed_ll_base - seed_ll_arm, ddof 1) / K, in the block and the week
      intervals alike;
    * with the argument off, the old interval is reproduced bit for bit (old_paired_stats below is the function as it
      was before 9 Oct 2026), and the paired call keeps the old values under *_unpaired;
    * unequal seed sets are refused when paired; a price (no seeds) keeps the unpaired term in compare.py;
    * compare.py reads "better" / "worse" / "unresolved" and p_better = the t CDF of estimate / se on blocks - 1.
The real-data cases (the reference against itself; the published model_rebuild rows) are in test_current_best_model.py.

Run: ./python.sh -m pytest test/current_best_model -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as G  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OLD_KEYS = ("matches", "estimate", "lo", "hi", "se", "se_block", "v_seed_base", "v_seed_arm", "blocks",
            "lo_block_only", "hi_block_only", "lo_week", "hi_week", "weeks")


def old_paired_stats(ll_base, ll_arm, seed_ll_base, seed_ll_arm, block, week) -> dict:
    """score.paired_stats as it was before 9 Oct 2026, verbatim."""
    d = 1000 * (np.asarray(ll_base) - np.asarray(ll_arm))
    g = float(d.mean())
    v_base = float(np.var(seed_ll_base, ddof=1) / len(seed_ll_base)) if len(seed_ll_base) > 1 else 0.0
    v_arm = float(np.var(seed_ll_arm, ddof=1) / len(seed_ll_arm)) if len(seed_ll_arm) > 1 else 0.0
    se_b, Gb = S.cluster_se(d, block)
    se_w, Gw = S.cluster_se(d, week)
    tb, tw = student_t.ppf(0.975, Gb - 1), student_t.ppf(0.975, Gw - 1)
    se = np.sqrt(se_b ** 2 + v_base + v_arm)
    sew = np.sqrt(se_w ** 2 + v_base + v_arm)
    return {"matches": int(len(d)), "estimate": g, "lo": g - tb * se, "hi": g + tb * se, "se": float(se),
            "se_block": se_b, "v_seed_base": v_base, "v_seed_arm": v_arm, "blocks": Gb,
            "lo_block_only": g - tb * se_b, "hi_block_only": g + tb * se_b,
            "lo_week": g - tw * sew, "hi_week": g + tw * sew, "weeks": Gw}


def toy(seed: int = 0, n: int = 3000, k: int = 4):
    """Outcomes, two arms' per-seed forecasts (n x k) and 4-week blocks and weeks. Seed k's noise is shared by both
    arms (as TabPFN's random state k is), plus a little of each arm's own."""
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.5).astype(float)
    eta = rng.normal(0, 1, n)
    shared = rng.normal(0, 0.05, (n, k))
    qk_base = expit(eta[:, None] + shared + rng.normal(0, 0.01, (n, k)))
    qk_arm = expit(0.97 * eta[:, None] + shared + rng.normal(0, 0.01, (n, k)))
    day = rng.integers(0, 3 * 365, n)
    return y, qk_base, qk_arm, day // 28, day // 7


def losses(y, qk_base, qk_arm, block, week) -> tuple:
    """paired_stats' arguments: per-match losses of the seed means, then 1000 x each seed's mean loss."""
    return (SC.ll(qk_base.mean(axis=1), y), SC.ll(qk_arm.mean(axis=1), y), S.seed_loss(qk_base, y),
            S.seed_loss(qk_arm, y), block, week)


def frame(y, block, week) -> pd.DataFrame:
    return pd.DataFrame({"y": y, "block": block, "week": week}, index=[f"m{i}" for i in range(len(y))])


def test_identical_arms_give_zero_and_a_zero_width_interval():
    y, qb, _, block, week = toy()
    r = S.paired_stats(*losses(y, qb, qb, block, week), matched_seeds=True)
    assert r["estimate"] == 0 and r["se"] == 0 and r["v_seed"] == 0
    assert r["lo"] == r["hi"] == 0 and r["lo_week"] == r["hi_week"] == 0
    assert r["lo_unpaired"] < 0 < r["hi_unpaired"]          # unpaired, the same noise was counted twice


def test_compare_reads_identical_forecasts_as_exactly_zero():
    y, qb, _, block, week = toy()
    info = frame(y, block, week)
    out = G.paired(info, info.index, (qb.mean(axis=1), qb), (qb.mean(axis=1), qb))
    assert out["estimate"] == 0 and out["lo"] == 0 and out["hi"] == 0 and out["seed_term"] == "paired"
    assert out["reading"] == "unresolved" and np.isnan(out["p_better"])


def test_paired_seed_term_is_the_variance_of_the_seed_differences_over_k():
    y, qb, qa, block, week = toy()
    llb, lla = SC.ll(qb.mean(axis=1), y), SC.ll(qa.mean(axis=1), y)
    sb = np.array([700.0, 700.4, 699.6, 700.2])
    sa = sb + np.array([0.1, -0.1, 0.1, -0.1])                # d = sb - sa = -0.1, +0.1, -0.1, +0.1
    r = S.paired_stats(llb, lla, sb, sa, block, week, matched_seeds=True)
    assert r["v_seed"] == np.var(sb - sa, ddof=1) / 4 and np.isclose(r["v_seed"], 0.04 / 3 / 4)
    assert np.isclose(r["v_seed_base"] + r["v_seed_arm"], 0.045)    # what the unpaired term adds instead
    tb = student_t.ppf(0.975, r["blocks"] - 1)
    assert np.isclose(r["se"] ** 2, r["se_block"] ** 2 + 0.04 / 3 / 4)
    assert np.isclose((r["hi"] - r["lo"]) / (2 * tb), np.sqrt(r["se_block"] ** 2 + 0.04 / 3 / 4))
    se_w, weeks = S.cluster_se(1000 * (llb - lla), week)
    tw = student_t.ppf(0.975, weeks - 1)
    assert np.isclose((r["hi_week"] - r["lo_week"]) / (2 * tw), np.sqrt(se_w ** 2 + 0.04 / 3 / 4))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_off_by_default_reproduces_the_old_interval_exactly(seed):
    args = losses(*toy(seed))
    old, new, on = old_paired_stats(*args), S.paired_stats(*args), S.paired_stats(*args, matched_seeds=True)
    assert all(new[k] == old[k] for k in OLD_KEYS)            # bit for bit
    assert new["seed_term"] == "unpaired" and on["seed_term"] == "paired"
    kept = ("se_unpaired", "lo_unpaired", "hi_unpaired", "lo_week_unpaired", "hi_week_unpaired")
    assert [on[k] for k in kept] == [old[k] for k in ("se", "lo", "hi", "lo_week", "hi_week")]
    assert on["estimate"] == old["estimate"] and on["lo_block_only"] == old["lo_block_only"]
    seedless = args[:2] + (np.zeros(1), np.zeros(1)) + args[4:]   # the callers that pass no seeds
    assert all(S.paired_stats(*seedless)[k] == old_paired_stats(*seedless)[k] for k in OLD_KEYS)


def test_paired_refuses_unequal_seed_sets():
    llb, lla, sb, sa, block, week = losses(*toy())
    with pytest.raises(ValueError):
        S.paired_stats(llb, lla, sb, sa[:3], block, week, matched_seeds=True)


def test_a_price_has_no_seeds_so_its_rows_stay_unpaired():
    y, qb, qa, block, week = toy()
    info = frame(y, block, week)
    price, model = (qb.mean(axis=1), qb.mean(axis=1)[:, None]), (qa.mean(axis=1), qa)
    out = G.paired(info, info.index, price, model, matched=False)
    assert out["seed_term"] == "unpaired" and out["lo"] == out["lo_unpaired"] and out["hi"] == out["hi_unpaired"]
    with pytest.raises(ValueError):
        G.paired(info, info.index, price, model)


def test_p_better_is_the_t_cdf_on_blocks_minus_1():
    assert G.p_better(0.0142, 0.0102, 55) == pytest.approx(student_t.cdf(0.0142 / 0.0102, 54))
    assert G.p_better(-0.2641, 0.1618, 55) == pytest.approx(student_t.cdf(-0.2641 / 0.1618, 54))
    assert np.isnan(G.p_better(0.0, 0.0, 55))
    assert G.p_better(0.3, 0.0, 55) == 1.0 and G.p_better(-0.3, 0.0, 55) == 0.0
