"""P9 point details: the harness's calibration (brief 03: placebos, a planted signal, the resolution table).

Every reading below uses only the bases, placebo columns and synthetic results; no candidate statistic is read.

    placebos   200 random N(0, 1) columns (full coverage), 200 more with missing values by level (present with
               probability 0.95 at the 1000s and the Finals, 0.57 at the 500s and 250s, 0.5 at the Slams, 0.30 at
               Challengers: the shape of P9's rally-length coverage), and the nuisance columns: a hash of the match id
               (a fixed N(0, 1) per match), the opposite player's index (player B's rank among the population's player
               ids, standardised) and the two players' index difference (A - B). Each through every population and
               base, raw and (tour level) new part, both variants; the coverage placebos also with the missing
               indicator. Their z should look like N(0, 1) and their cross-fitted gains should centre slightly below 0.
    planted    synthetic results y* ~ Bernoulli(expit(L + g x)) with L the base's log-odds and x a fresh N(0, 1)
               column, g set so that the true model beats the base by 0.25, 0.5, 1 or 2 mLL in expectation (the
               Kullback-Leibler gain over the population's L, by Gauss-Hermite quadrature). 200 draws per gain,
               population and base; detection rates of: the one-sided z test at 5% in the declared direction, the
               two-sided z test at 5%, and the cross-fitted gain read "better".
    resolution per population and base, the minimum detectable effect of one standardised feature at 80% power and a
               two-sided 5% test: b = (z_0.975 + z_0.80) x the placebos' median clustered se (per SD), its mLL
               equivalent (the same quadrature), and the empirical ones read off the planted-signal power curves
               (the z test and the cross-fitted gain), interpolated in log gain.

Writes data/studies/p9_point_details/harness/: placebos.csv.gz (every reading), placebo_summary.csv, planted.csv.gz,
planted_summary.csv, resolution.csv, calibration.json.
Run: ./python.sh src/eda/p9_point_details/harness_calibrate.py [--workers 4] [--placebos 200] [--reps 200]
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # small matrices; several workers must not each take every core

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.special import expit  # noqa: E402
from scipy.stats import kstest, norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import harness as H  # noqa: E402

OUT = H.HARNESS
SEED = 20261028
GAINS = (0.25, 0.5, 1.0, 2.0)
TOUR_POPS = ("tour", "tour_main", "tour_qual")
COMBOS = [(p, b) for p in H.POPULATIONS for b in H.BASES if b == "price" or p in TOUR_POPS]
COVERAGE = {"T1000": 0.95, "FIN": 0.95, "T500": 0.57, "T250": 0.57, "GS": 0.50, "CH": 0.30}
Z_A, Z_B = float(norm.ppf(0.975)), float(norm.ppf(0.80))
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(40)
GH_W = GH_W / GH_W.sum()
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Gains of a planted signal (expected, Kullback-Leibler)

def kl_gain(L: np.ndarray, g: float) -> float:
    """1000 x the mean over matches and x ~ N(0, 1) of KL(Bern(expit(L + g x)) || Bern(expit(L))): the expected log
    loss by which the true model beats the base, mLL per match."""
    p = expit(L)[:, None]
    q = expit(L[:, None] + g * GH_X[None, :])
    with np.errstate(divide="ignore", invalid="ignore"):
        kl = q * np.log(q / p) + (1 - q) * np.log((1 - q) / (1 - p))
    return 1000.0 * float((np.nan_to_num(kl) @ GH_W).mean())


def gamma_for(L: np.ndarray, gain: float) -> float:
    lo, hi = 0.0, 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if kl_gain(L, mid) < gain else (lo, mid)
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------------
# Placebo columns (outcome-free)

def hash_normal(keys: pd.Series, salt: str) -> np.ndarray:
    u = np.array([int.from_bytes(hashlib.sha256(f"{salt}|{k}".encode()).digest()[:8], "big") for k in keys],
                 dtype=np.float64)
    return norm.ppf((u + 0.5) / 2.0 ** 64)


def placebo_columns(pop: pd.DataFrame, n: int, seed: int) -> dict[str, pd.Series]:
    rng = np.random.default_rng(seed)
    ids = pop["match_id"].to_numpy()
    cols = {f"random_{i:03d}": pd.Series(rng.standard_normal(len(pop)), index=ids) for i in range(n)}
    pres = pop["level"].map(COVERAGE).fillna(0.5).to_numpy(float)
    for i in range(n):
        x = rng.standard_normal(len(pop))
        x[rng.random(len(pop)) >= pres] = np.nan
        cols[f"coverage_{i:03d}"] = pd.Series(x, index=ids)
    allp = pd.Index(sorted(set(pop["player_a_id"]) | set(pop["player_b_id"])))
    rank = pd.Series(np.arange(len(allp), dtype=float), index=allp)
    ra, rb = rank.reindex(pop["player_a_id"]).to_numpy(), rank.reindex(pop["player_b_id"]).to_numpy()
    cols["nuisance_hash_match_id"] = pd.Series(hash_normal(pop["match_id"], "p9-harness"), index=ids)
    cols["nuisance_opponent_index"] = pd.Series((rb - rb.mean()) / rb.std(), index=ids)
    d = ra - rb
    cols["nuisance_index_difference"] = pd.Series(d / np.sqrt(np.mean(d ** 2)), index=ids)
    return cols


def _placebo_chunk(args) -> pd.DataFrame:
    names, n, seed = args
    pop = H.load_population()
    inputs = H.load_inputs()
    cols = placebo_columns(pop, n, seed)
    caches: dict = {}
    out = []
    for name in names:
        r = H.score(pop, cols[name], 1, H.POPULATIONS, tuple(H.BASES), False, True, inputs, caches=caches)
        r.insert(0, "placebo", name)
        out.append(r)
    return pd.concat(out, ignore_index=True)


def run_placebos(n: int, workers: int) -> pd.DataFrame:
    pop = H.load_population()
    names = list(placebo_columns(pop.head(50), n, SEED).keys())
    chunks = [names[i::workers] for i in range(workers)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_placebo_chunk, [(c, n, SEED) for c in chunks]))
    return pd.concat(parts, ignore_index=True)


def placebo_summary(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["kind"] = np.where(t["placebo"].str.startswith("random"), "random",
                         np.where(t["placebo"].str.startswith("coverage"), "coverage", t["placebo"]))
    keys = ["kind", "population", "base", "part", "variant", "missing"]
    rows = []
    for k, g in t.groupby(keys):
        z = g["z"].to_numpy(float)
        z = z[np.isfinite(z)]
        r = dict(zip(keys, k))
        r.update({"placebos": int(len(g)), "matches_median": float(g["matches"].median()),
                  "coverage_mean": float(g["coverage"].mean()), "z_mean": float(z.mean()) if len(z) else np.nan,
                  "z_sd": float(z.std(ddof=1)) if len(z) > 1 else np.nan,
                  "share_abs_z_over_1.96": float((np.abs(z) > 1.96).mean()) if len(z) else np.nan,
                  "share_one_sided_p_le_0.05": float((g["p_one_sided"] <= 0.05).mean()),
                  "ks_p_vs_normal": float(kstest(z, "norm").pvalue) if len(z) > 5 else np.nan,
                  "gain_mean": float(g["gain_mll"].mean()), "gain_median": float(g["gain_mll"].median()),
                  "gain_sd": float(g["gain_mll"].std(ddof=1)) if len(g) > 1 else np.nan,
                  "share_better": float((g["reading"] == "better").mean()),
                  "share_worse": float((g["reading"] == "worse").mean()),
                  "p_better_mean": float(g["p_better"].mean()), "se_per_rms_median": float(g["se_per_rms"].median()),
                  "se_boot_median": float(g["se_boot"].median())})
        if len(g) == 1:
            r.update({"z": float(g["z"].iloc[0]), "gain": float(g["gain_mll"].iloc[0]),
                      "lo": float(g["lo"].iloc[0]), "hi": float(g["hi"].iloc[0]), "reading": g["reading"].iloc[0]})
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The planted signal

def _planted_combo(args) -> pd.DataFrame:
    population, base, reps, seed = args
    pop = H.load_population()
    rows = H.scored_rows(pop, population, base)
    L = rows[H.BASES[base]].to_numpy(float)
    week = H.blocks(rows["tournament_date"].to_numpy(), 7)
    block = H.blocks(rows["tournament_date"].to_numpy(), 28)
    cells = H.cells_of(rows)
    rng = np.random.default_rng([seed, H.POPULATIONS.index(population), list(H.BASES).index(base)])
    out = []
    for gain in (0.0,) + GAINS:
        gam = gamma_for(L, gain) if gain > 0 else 0.0
        for r in range(reps):
            x = rng.standard_normal(len(rows))
            y = (rng.random(len(rows)) < expit(L + gam * x)).astype(float)
            xs = x / H.rms(x)
            rec = {"population": population, "base": base, "gain_true": gain, "gamma": gam, "rep": r,
                   "matches": int(len(rows))}
            for v in H.VARIANTS:
                zt = H.z_test(y, L, xs, week, v, 1, cells=cells)
                gt = H.gain_test(y, L, xs, block, v, n_boot=1000, cells=cells)
                rec.update({f"z_{v}": zt["z"], f"p1_{v}": zt["p_one_sided"], f"p2_{v}": zt["p_two_sided"],
                            f"gain_{v}": gt["gain"], f"lo_{v}": gt["lo"], f"hi_{v}": gt["hi"],
                            f"reading_{v}": gt["reading"]})
            out.append(rec)
    return pd.DataFrame(out)


def run_planted(reps: int, workers: int) -> pd.DataFrame:
    jobs = [(p, b, reps, SEED) for p, b in COMBOS]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_planted_combo, jobs))
    return pd.concat(parts, ignore_index=True)


def planted_summary(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (pop, base, g), d in t.groupby(["population", "base", "gain_true"]):
        r = {"population": pop, "base": base, "gain_true": g, "gamma_per_sd": float(d["gamma"].iloc[0]),
             "reps": int(len(d)), "matches": int(d["matches"].iloc[0])}
        for v in H.VARIANTS:
            r.update({f"detect_z_one_sided_5pct_{v}": float((d[f"p1_{v}"] <= 0.05).mean()),
                      f"detect_z_two_sided_5pct_{v}": float((d[f"p2_{v}"] <= 0.05).mean()),
                      f"detect_mll_better_{v}": float((d[f"reading_{v}"] == "better").mean()),
                      f"gain_crossfit_mean_{v}": float(d[f"gain_{v}"].mean()),
                      f"z_mean_{v}": float(d[f"z_{v}"].mean())})
        rows.append(r)
    return pd.DataFrame(rows)


def mde_from_power(gains: np.ndarray, power: np.ndarray, target: float = 0.80) -> float:
    """The gain at which power reaches the target, interpolated linearly in log gain; NaN-coded bounds as +-inf."""
    g, p = np.asarray(gains, float), np.asarray(power, float)
    if p[-1] < target:
        return np.inf
    if p[0] >= target:
        return -np.inf
    i = int(np.argmax(p >= target))
    x0, x1, y0, y1 = np.log(g[i - 1]), np.log(g[i]), p[i - 1], p[i]
    return float(np.exp(x0 + (target - y0) * (x1 - x0) / (y1 - y0))) if y1 > y0 else float(g[i])


def resolution(plac: pd.DataFrame, plant: pd.DataFrame) -> pd.DataFrame:
    pop = H.load_population()
    ps = plant.copy()
    rows = []
    for population, base in COMBOS:
        sel = H.scored_rows(pop, population, base)
        L = sel[H.BASES[base]].to_numpy(float)
        for v in H.VARIANTS:
            g = plac[(plac["kind"] == "random") & (plac["population"] == population) & (plac["base"] == base)
                     & (plac["part"] == "raw") & (plac["variant"] == v) & (plac["missing"] == "subset")]
            se = float(g["se_per_rms_median"].iloc[0])
            b_mde = (Z_A + Z_B) * se
            d = ps[(ps["population"] == population) & (ps["base"] == base) & (ps["gain_true"] > 0)] \
                .sort_values("gain_true")
            gz = mde_from_power(d["gain_true"].to_numpy(), d[f"detect_z_two_sided_5pct_{v}"].to_numpy())
            gm = mde_from_power(d["gain_true"].to_numpy(), d[f"detect_mll_better_{v}"].to_numpy())
            rows.append({"population": population, "base": base, "variant": v, "matches": int(len(sel)),
                         "weeks": int(len(np.unique(H.blocks(sel["tournament_date"].to_numpy(), 7)))),
                         "blocks": int(len(np.unique(H.blocks(sel["tournament_date"].to_numpy(), 28)))),
                         "se_b_per_sd": se, "mde_b_per_sd": b_mde, "mde_mll_analytic": kl_gain(L, b_mde),
                         "mde_mll_planted_z": gz, "mde_mll_planted_crossfit_better": gm,
                         "null_gain_mean": float(g["gain_mean"].iloc[0]), "null_gain_sd": float(g["gain_sd"].iloc[0]),
                         "null_se_boot_median": float(g["se_boot_median"].iloc[0])})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# A larger null check of the z test's standard error (z only, the price base)

def _null_chunk(args) -> pd.DataFrame:
    population, n, seed = args
    pop = H.load_population()
    rows = H.scored_rows(pop, population, "price")
    y, L = rows["a_won"].to_numpy(float), rows["price_logit"].to_numpy(float)
    week = H.blocks(rows["tournament_date"].to_numpy(), 7)
    block = H.blocks(rows["tournament_date"].to_numpy(), 28)
    cells = H.cells_of(rows)
    rng = np.random.default_rng([seed, 7, H.POPULATIONS.index(population)])
    out = []
    for i in range(n):
        x = rng.standard_normal(len(rows))
        X, off = H.design(L, x, "free", cells=cells)
        b, p, Hs = H.fit_logit(X, y, off)
        j = X.shape[1] - 1
        se_model = float(np.sqrt(np.linalg.inv(Hs)[j, j]))
        se_week = float(np.sqrt(H.cluster_cov(X, y, p, Hs, week)[j, j]))
        se_block = float(np.sqrt(H.cluster_cov(X, y, p, Hs, block)[j, j]))
        out.append({"population": population, "draw": i, "b": float(b[j]), "se_model": se_model,
                    "se_week": se_week, "se_block": se_block})
    return pd.DataFrame(out)


def null_check(n: int, workers: int) -> pd.DataFrame:
    """n random N(0, 1) columns per population against the price ("free" variant): z with the week-clustered se (the
    harness's), with the 4-week-block-clustered se, and with the model-based se (no clustering). For a column drawn
    independently of everything, each z should have SD 1; the SD of b over draws against each se's median says which
    se is calibrated."""
    jobs = [(p, n, SEED) for p in H.POPULATIONS]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        t = pd.concat(list(ex.map(_null_chunk, jobs)), ignore_index=True)
    rows = []
    for p, g in t.groupby("population", sort=False):
        r = {"population": p, "draws": int(len(g)), "sd_of_b": float(g["b"].std(ddof=1))}
        for s in ("se_model", "se_week", "se_block"):
            z = g["b"] / g[s]
            r.update({f"{s}_median": float(g[s].median()), f"z_sd_{s[3:]}": float(z.std(ddof=1)),
                      f"share_abs_z_over_1.96_{s[3:]}": float((z.abs() > 1.96).mean()),
                      f"ks_p_{s[3:]}": float(kstest(z, "norm").pvalue)})
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--placebos", type=int, default=200)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--null-check", type=int, metavar="N",
                    help="only the larger null check of the z test's se: N random columns per population")
    a = ap.parse_args(argv)
    workers = max(1, min(4, a.workers))                     # the shared machine: at most 4 worker processes
    if a.null_check:
        t = null_check(a.null_check, workers)
        t.to_csv(OUT / "null_check.csv", index=False)
        pd.set_option("display.width", 250)
        print(t.round(4).to_string(index=False))
        return 0
    log(f"placebos: {a.placebos} random + {a.placebos} with missing values + 3 nuisance columns, {workers} workers")
    t = run_placebos(a.placebos, workers)
    t.to_csv(OUT / "placebos.csv.gz", index=False)
    ps = placebo_summary(t)
    ps.to_csv(OUT / "placebo_summary.csv", index=False)
    log(f"planted signal: {len(COMBOS)} populations x bases, gains {GAINS} and 0, {a.reps} draws each")
    pt = run_planted(a.reps, workers)
    pt.to_csv(OUT / "planted.csv.gz", index=False)
    pls = planted_summary(pt)
    pls.to_csv(OUT / "planted_summary.csv", index=False)
    res = resolution(ps, pls)
    res.to_csv(OUT / "resolution.csv", index=False)
    facts = {"seed": SEED, "placebos": a.placebos, "planted_reps": a.reps, "gains_mll": list(GAINS),
             "coverage_placebo_presence": COVERAGE, "workers": workers, "seconds": round(time.time() - T0, 1),
             "population_sha256": H.hashlib.sha256((H.POP).read_bytes()).hexdigest()}
    (OUT / "calibration.json").write_text(json.dumps(facts, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    log("done")
    print(res.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
