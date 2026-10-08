"""R1 design look of the integration strategist: the fit noise of the local TabPFN-3.5 arms, from saved forecasts only.

No match result is read (forecast files carry probabilities and match ids only). Seasons 2019-2023 only.

    seed noise      the base model "model" (58 inputs) has seeds 0-15 for 2019-2023 (seeds 0-2 in the rating race's
                    folder, 3-15 in feature interactions'; 2019 has all 16 in feature interactions'): the per-match SD of
                    the symmetrised log-odds across seeds, and the RMS gap between disjoint k-seed means
    calibration     is a 4-seed mean's log-odds a fixed multiple of the 16-seed mean's? (slope of one on the other, no
                    outcome): decides whether arms can be calibrated on fewer seeds than they are scored with
    column noise    how far an arm with extra columns moves from the base with the SAME seeds, against two disjoint seed
                    sets of the base itself: B-INJ's 3 columns ("binj", seeds 0-2), the 17 level sums ("levels",
                    seeds 0-5), and the surface-IOS study's single column and its permuted placebo ("snet1",
                    "snet1_perm" against that study's "base", seeds 0-3)
    p(1-p)          the mean of p(1 - p) of the men's base forecast (power input)

Writes data/studies/serve_speed_tabpfn/design/strategist_noise.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_noise.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
FI = ROOT / "data" / "studies" / "feature_interactions" / "local"
RACE = ROOT / "data" / "studies" / "surface_rating_race" / "local"
SIOS = ROOT / "data" / "studies" / "surface_ios"
SEASONS = range(2019, 2024)
EPS = 1e-6


def lg(p):
    return logit(np.clip(np.asarray(p, float), EPS, 1 - EPS))


def sym(p_orig, p_flip):
    return 0.5 * (np.asarray(p_orig, float) + 1.0 - np.asarray(p_flip, float))


def harness_eta(arm: str, season: int, seed: int) -> pd.Series | None:
    """Symmetrised log-odds of one saved harness fit (feature interactions' folder first, then the race's)."""
    for d in (FI, RACE):
        p = d / f"{arm}__{season}__seed{seed}.npz"
        if p.exists():
            with np.load(p, allow_pickle=False) as z:
                pr, ids = z["p_td"], z["ids_td"].astype(str)
            k = len(ids)
            return pd.Series(lg(sym(pr[:k], pr[k:])), index=ids)
    return None


def sios_eta(arm: str, season: int, seed: int) -> pd.Series | None:
    slot = f"{arm}_s{seed}_{season}"
    p = SIOS / "local" / f"{slot}.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        pr = z["p_a"]
    ids = pd.read_parquet(SIOS / "uploads" / slot / "query_ids.parquet")["match_id"].astype(str).to_numpy()
    n = len(ids) // 2
    return pd.Series(lg(sym(pr[:n], pr[n:])), index=ids[:n])


def matrix(loader, arm: str, seeds) -> pd.DataFrame:
    """Rows: matches of SEASONS; columns: seeds (symmetrised log-odds)."""
    parts = []
    for s in SEASONS:
        cols = {k: loader(arm, s, k) for k in seeds}
        if any(v is None for v in cols.values()):
            missing = [k for k, v in cols.items() if v is None]
            raise FileNotFoundError(f"{arm} {s}: seeds {missing}")
        parts.append(pd.DataFrame(cols).assign(season=s))
    m = pd.concat(parts)
    m["tour"] = np.where(m.index.str.startswith("wta"), "wta", "atp")
    return m


def rms(v) -> float:
    v = np.asarray(v, float)
    return float(np.sqrt(np.nanmean(v ** 2)))


def seed_block(m: pd.DataFrame, seeds) -> dict:
    E = m[list(seeds)].to_numpy(float)
    out = {"matches": int(len(m)), "seeds": len(seeds),
           "sd_across_seeds_rms": rms(E.std(axis=1, ddof=1)),
           "sd_across_seeds_median": float(np.median(E.std(axis=1, ddof=1)))}
    for k in (1, 2, 4, 8):
        if 2 * k <= E.shape[1]:
            out[f"rms_gap_disjoint_{k}_seed_means"] = rms(E[:, :k].mean(1) - E[:, k:2 * k].mean(1))
    if E.shape[1] >= 16:
        e4, e16 = E[:, :4].mean(1), E.mean(1)
        out["slope_eta16_on_eta4"] = float(np.dot(e4, e16) / np.dot(e4, e4))
        out["rms_eta4_minus_eta16"] = rms(e4 - e16)
        p = 1 / (1 + np.exp(-e16))
        out["mean_p1mp_16seed"] = float(np.mean(p * (1 - p)))
        out["sd_eta16"] = float(e16.std())
    return out


def arm_vs_base(arm_m: pd.DataFrame, base_m: pd.DataFrame, seeds, ref_seeds=None) -> dict:
    """RMS of eta_arm - eta_base with the same seeds; the base's own disjoint-seed gap as reference; the share of the
    per-seed noise the two fits share (common random numbers)."""
    j = arm_m[list(seeds)].join(base_m[list(seeds)], lsuffix="_arm", rsuffix="_base", how="inner")
    A = j[[f"{k}_arm" for k in seeds]].to_numpy(float)
    B = j[[f"{k}_base" for k in seeds]].to_numpy(float)
    dev = A.mean(1) - B.mean(1)
    na, nb = A - A.mean(1, keepdims=True), B - B.mean(1, keepdims=True)
    out = {"matches": int(len(j)), "seeds": list(seeds), "rms_dev_same_seeds": rms(dev),
           "corr_seed_noise_arm_base_same_seed": float(np.corrcoef(na.ravel(), nb.ravel())[0, 1]),
           "rms_single_seed_dev_same_seed": rms((A - B).ravel())}
    if ref_seeds is not None:
        R = base_m.loc[j.index, list(ref_seeds)].to_numpy(float)
        ref = B.mean(1) - R.mean(1)
        out["rms_base_disjoint_seed_means_ref"] = rms(ref)
        out["excess_rms_structural"] = float(np.sqrt(max(rms(dev) ** 2 - rms(ref) ** 2, 0.0)))
    return out


def main() -> int:
    res = {"rules": "forecasts only, 2019-2023; no match result read"}
    base = matrix(harness_eta, "model", range(16))
    res["model_seed_noise"] = {t: seed_block(base[base["tour"] == t], range(16)) for t in ("atp", "wta")}
    binj = matrix(harness_eta, "binj", range(3))
    res["binj_vs_model"] = {t: arm_vs_base(binj[binj["tour"] == t], base[base["tour"] == t], range(3), range(3, 6))
                            for t in ("atp", "wta")}
    levels = matrix(harness_eta, "levels", range(6))
    res["levels_vs_model"] = {t: arm_vs_base(levels[levels["tour"] == t], base[base["tour"] == t], range(6),
                                             range(6, 12)) for t in ("atp", "wta")}
    sb = matrix(sios_eta, "base", range(4))
    for arm in ("snet1_perm", "snet1", "sprof"):
        a = matrix(sios_eta, arm, range(4))
        res[f"sios_{arm}_vs_base"] = {t: arm_vs_base(a[a["tour"] == t], sb[sb["tour"] == t], range(4))
                                      for t in ("atp", "wta")}
    res["sios_base_seed_noise"] = {t: seed_block(sb[sb["tour"] == t], range(4)) for t in ("atp", "wta")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strategist_noise.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
