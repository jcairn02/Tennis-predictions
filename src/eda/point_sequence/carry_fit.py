"""B1, finishing-form carry-over: the pre-registered difference in differences (data/studies/point_sequence/
carry_prereg.md is the binding operationalisation; this module implements it).

Model. One binomial GLM on stacked rows, two per triple: the forward row (serve points won in t+1) and the reverse row
(serve points won in t-1). Each row: y won of n served, offset = logit of the endpoint's pre-match p_serve, and
direction-specific coefficients on
    tour intercepts (atp, wta),
    E = set-1 serve-point residual of match t, L = late-set residual of match t (both per 10 percentage points),
    form = box-score serve form as of t-1 (per 10 percentage points; the same value in both directions),
    gap2 = 1{1 < endpoint gap <= 2 days}, gap3 = 1{2 < gap <= 3}   (the endpoint gap: t -> t+1 forward, t-1 -> t
    reverse; reference: one day or less).
Delta = (b_L - b_E)_forward - (b_L - b_E)_reverse: positive = late form carries forward more than backward. Units:
endpoint serve-point log-odds per 10 percentage points of set residual.

Inference. Newton-Raphson maximum likelihood; covariance clustered by player (the triple's player) with the CR1 factor
G/(G-1) * (N-1)/(N-K); Wald 95% interval. Check: a player-cluster bootstrap (multinomial cluster weights), percentile
interval.

Placebos: the replay null (carry_sim.replay_triples; primary de-noising toward the frozen tour x surface prior, and a
player-centred variant) and the EARLY/LATE label swap. Secondary: fade by forward gap; pre-declared sensitivities.

Run: ./python.sh src/eda/point_sequence/carry_fit.py [--replays 50] [--replays-player 20] [--boot 999] [--swaps 500]
     [--workers 4]   (at most 4 worker processes, CPU only)
Writes data/studies/point_sequence/carry_results.json, carry_estimates.csv, carry_replay_null.csv,
carry_label_swap.csv.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import carry_sim as S  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
TRIPLES = OUT / "carry_triples.parquet"
RESULTS = OUT / "carry_results.json"
ESTIMATES = OUT / "carry_estimates.csv"
REPLAY_NULL = OUT / "carry_replay_null.csv"
LABEL_SWAP = OUT / "carry_label_swap.csv"
SCALE = 10.0                     # exposures and form per 10 percentage points (a share times 10)
SEED = 20261006
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Binomial GLM with offset, clustered covariance

def fit_binomial(y, n, off, X, w=None, beta0=None, max_iter=100, tol=1e-10) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Maximum likelihood of y ~ Binomial(n, expit(off + X b)), optional row weights w. Returns b, the information
    matrix H = X' diag(w n mu (1 - mu)) X, and mu."""
    y = np.asarray(y, float)
    n = np.asarray(n, float)
    off = np.asarray(off, float)
    X = np.asarray(X, float)
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    b = np.zeros(X.shape[1]) if beta0 is None else np.array(beta0, float)
    for _ in range(max_iter):
        mu = expit(off + X @ b)
        g = X.T @ (w * (y - n * mu))
        H = (X * (w * n * mu * (1 - mu))[:, None]).T @ X
        step = np.linalg.solve(H, g)
        # step halving if the log-likelihood falls (rare: offsets keep the problem well conditioned)
        ll0 = loglik(y, n, off, X, b, w)
        t = 1.0
        while t > 1e-4 and loglik(y, n, off, X, b + t * step, w) < ll0 - 1e-9:
            t /= 2
        b = b + t * step
        if np.max(np.abs(t * step)) < tol:
            break
    mu = expit(off + X @ b)
    H = (X * (w * n * mu * (1 - mu))[:, None]).T @ X
    return b, H, mu


def loglik(y, n, off, X, b, w) -> float:
    eta = off + X @ b
    return float(np.sum(w * (y * eta - n * np.logaddexp(0.0, eta))))


def cluster_cov(y, n, X, mu, H, codes) -> np.ndarray:
    """CR1 sandwich: H^-1 (sum_g S_g S_g') H^-1 * G/(G-1) * (N-1)/(N-K), S_g the score summed within cluster g."""
    U = X * (np.asarray(y, float) - np.asarray(n, float) * mu)[:, None]
    G = int(codes.max()) + 1
    Sg = np.zeros((G, X.shape[1]))
    np.add.at(Sg, codes, U)
    Hi = np.linalg.inv(H)
    N, K = X.shape
    return Hi @ (Sg.T @ Sg) @ Hi * (G / (G - 1)) * ((N - 1) / (N - K))


# ------------------------------------------------------------------------------------------------
# The stacked design

def design(tri: pd.DataFrame, exp=("rE", "rL"), endpoint: str = "serve", form: str = "primary",
           extra: tuple = (), gap_by_fwd: bool = False) -> dict:
    """Stacked rows (forward block, then reverse block, the same triples in the same order) and their columns.

    endpoint "serve": y = serve points won, offset logit(p_serve); "return": return points won, offset
    logit(1 - opponent's p_serve). form "primary": the form as of t-1 in both blocks; "literal": as of each endpoint
    (t+1 forward, t-1 reverse; a sensitivity); "none". extra: further match-t columns entered (scaled) in both blocks.
    gap_by_fwd: E and L interacted with the triple's forward-gap class (1 day / 2 days / 3 days) in both blocks."""
    T = len(tri)
    tour_atp = (tri["tour"].to_numpy() == "atp").astype(float)
    E = tri[exp[0]].to_numpy(float) * SCALE
    L = tri[exp[1]].to_numpy(float) * SCALE
    blocks = {}
    for d, k, gap in (("fwd", "p", "gap_fwd"), ("rev", "m", "gap_rev")):
        if endpoint == "serve":
            y, n = tri[f"sv_w_{k}"].to_numpy(float), tri[f"sv_n_{k}"].to_numpy(float)
            off = logit(tri[f"ps_{k}"].to_numpy(float))
        else:
            y, n = tri[f"rt_w_{k}"].to_numpy(float), tri[f"rt_n_{k}"].to_numpy(float)
            off = logit(1 - tri[f"pso_{k}"].to_numpy(float))
        g = tri[gap].to_numpy(float)
        cols = {"int_atp": tour_atp, "int_wta": 1 - tour_atp}
        if gap_by_fwd:
            gc = gap_class(tri["gap_fwd"].to_numpy(float))
            for c in (1, 2, 3):
                cols[f"E_g{c}"] = E * (gc == c)
                cols[f"L_g{c}"] = L * (gc == c)
        else:
            cols["E"] = E
            cols["L"] = L
        if form == "primary":
            cols["form"] = tri["form_m"].to_numpy(float) * SCALE
        elif form == "literal":
            cols["form"] = tri["form_p_lit" if d == "fwd" else "form_m"].to_numpy(float) * SCALE
        for c in extra:
            cols[c] = tri[c].to_numpy(float) * SCALE
        cols["gap2"] = ((g > 1) & (g <= 2)).astype(float)
        cols["gap3"] = ((g > 2) & (g <= 3)).astype(float)
        blocks[d] = (y, n, off, cols)
    names = [f"{d}:{c}" for d in ("fwd", "rev") for c in blocks[d][3]]
    p = len(names)
    X = np.zeros((2 * T, p))
    j = 0
    for b, d in enumerate(("fwd", "rev")):
        for c, v in blocks[d][3].items():
            X[b * T:(b + 1) * T, j] = v
            j += 1
    y = np.concatenate([blocks["fwd"][0], blocks["rev"][0]])
    n = np.concatenate([blocks["fwd"][1], blocks["rev"][1]])
    off = np.concatenate([blocks["fwd"][2], blocks["rev"][2]])
    codes = pd.factorize(tri["player_id"])[0]
    codes = np.concatenate([codes, codes])
    # drop all-zero columns (e.g. an empty gap class or a tour absent from the subset)
    keep = np.abs(X).sum(axis=0) > 0
    return {"y": y, "n": n, "off": off, "X": X[:, keep], "names": [nm for nm, k in zip(names, keep) if k],
            "codes": codes, "T": T}


def gap_class(g: np.ndarray) -> np.ndarray:
    return np.where(g <= 1, 1, np.where(g <= 2, 2, 3))


def contrast(names: list[str], terms: dict[str, float]) -> np.ndarray:
    c = np.zeros(len(names))
    for t, v in terms.items():
        if t in names:
            c[names.index(t)] = v
        else:
            return np.full(len(names), np.nan)
    return c


def delta_terms(suffix: str = "") -> dict[str, float]:
    return {f"fwd:L{suffix}": 1.0, f"fwd:E{suffix}": -1.0, f"rev:L{suffix}": -1.0, f"rev:E{suffix}": 1.0}


def estimate(D: dict, contrasts: dict[str, dict] | None = None, beta0=None) -> dict:
    b, H, mu = fit_binomial(D["y"], D["n"], D["off"], D["X"], beta0=beta0)
    V = cluster_cov(D["y"], D["n"], D["X"], mu, H, D["codes"])
    out = {"names": D["names"], "beta": b, "V": V, "T": D["T"], "players": int(D["codes"].max()) + 1}
    contrasts = contrasts or {"delta": delta_terms()}
    out["contrasts"] = {}
    for k, terms in contrasts.items():
        c = contrast(D["names"], terms)
        if np.isnan(c).any():
            continue
        est, se = float(c @ b), float(np.sqrt(c @ V @ c))
        out["contrasts"][k] = {"est": est, "se": se, "lo": est - 1.96 * se, "hi": est + 1.96 * se,
                               "z": est / se if se > 0 else np.nan}
    return out


def standard_contrasts(suffix: str = "") -> dict[str, dict]:
    return {"delta": delta_terms(suffix),
            "fwd_L_minus_E": {f"fwd:L{suffix}": 1.0, f"fwd:E{suffix}": -1.0},
            "rev_L_minus_E": {f"rev:L{suffix}": 1.0, f"rev:E{suffix}": -1.0},
            "fwd_E": {f"fwd:E{suffix}": 1.0}, "fwd_L": {f"fwd:L{suffix}": 1.0},
            "rev_E": {f"rev:E{suffix}": 1.0}, "rev_L": {f"rev:L{suffix}": 1.0}}


def bootstrap_delta(D: dict, beta_hat: np.ndarray, B: int, seed: int, terms: dict | None = None) -> np.ndarray:
    """Player-cluster bootstrap of Delta: each replicate weights every player's rows by a multinomial count."""
    rng = np.random.default_rng(seed)
    G = int(D["codes"].max()) + 1
    c = contrast(D["names"], terms or delta_terms())
    out = np.empty(B)
    for r in range(B):
        cnt = rng.multinomial(G, np.full(G, 1.0 / G))
        w = cnt[D["codes"]].astype(float)
        b, _, _ = fit_binomial(D["y"], D["n"], D["off"], D["X"], w=w, beta0=beta_hat)
        out[r] = c @ b
    return out


def swap_labels(tri: pd.DataFrame, rng: np.random.Generator, exp=("rE", "rL")) -> pd.DataFrame:
    """EARLY and LATE exchanged at random (probability 1/2 per triple, the same in both directions)."""
    s = rng.random(len(tri)) < 0.5
    out = tri.copy()
    e, l_ = tri[exp[0]].to_numpy(), tri[exp[1]].to_numpy()
    out[exp[0]] = np.where(s, l_, e)
    out[exp[1]] = np.where(s, e, l_)
    return out


def replayed_exposures(tri: pd.DataFrame, rep: pd.DataFrame) -> pd.DataFrame:
    """The triple table with match t's set-1 and late-set residuals recomputed from a replay (against the same
    pre-match p_serve)."""
    out = tri.copy()
    ps, pr = tri["ps_t"].to_numpy(float), 1 - tri["pso_t"].to_numpy(float)
    out["rE"] = (rep["w1"] - rep["n1"] * ps) / rep["n1"]
    out["rL"] = (rep["wL"] - rep["nL"] * ps) / rep["nL"]
    out["retE"] = ((rep["on1"] - rep["ow1"]) - rep["on1"] * pr) / rep["on1"]
    out["retL"] = ((rep["onL"] - rep["owL"]) - rep["onL"] * pr) / rep["onL"]
    return out


# ------------------------------------------------------------------------------------------------
# Replay null (worker)

def _replay_job(args) -> list[dict]:
    path, windows, prior_records, dev_records, seeds, mode = args
    tri_all = pd.read_parquet(path)
    prior = pd.DataFrame(prior_records)
    dev_prior = pd.DataFrame(dev_records)
    rows = []
    for seed in seeds:
        for wname in windows:
            tri = tri_all[tri_all["window"] == wname].reset_index(drop=True)
            rep, info = S.replay_triples(tri, prior, seed=seed * 7 + (0 if wname == "discovery" else 1)
                                         + (0 if mode == "tour_mean" else 100_000), mode=mode, dev_prior=dev_prior)
            rt = replayed_exposures(tri, rep)
            bad = rt[["rE", "rL"]].isna().any(axis=1)
            rt = rt[~bad].reset_index(drop=True)
            res = estimate(design(rt), standard_contrasts())
            row = {"mode": mode, "window": wname, "seed": seed, "rounds": info["rounds"],
                   "never_matched": info["never_matched"], "dropped_empty_set": int(bad.sum()),
                   "corr_rE_rL": float(np.corrcoef(rt["rE"], rt["rL"])[0, 1]),
                   "sd_rE": float(rt["rE"].std()), "sd_rL": float(rt["rL"].std())}
            for k, v in res["contrasts"].items():
                row[f"{k}"] = v["est"]
                row[f"{k}_se"] = v["se"]
            rows.append(row)
    return rows


# ------------------------------------------------------------------------------------------------

def summarise(res: dict) -> dict:
    out = {"triples": res["T"], "players": res["players"],
           "coefficients": {nm: {"est": float(b), "se": float(np.sqrt(res["V"][i, i]))}
                            for i, (nm, b) in enumerate(zip(res["names"], res["beta"]))}}
    out.update({k: v for k, v in res["contrasts"].items()})
    return out


def run_main(args) -> None:
    tri = pd.read_parquet(TRIPLES)
    tri = tri[tri["window"].isin(["discovery", "replication"])].reset_index(drop=True)
    results: dict = {"settings": {"scale": "per 10 percentage points of set residual",
                                  "units": "endpoint serve-point log-odds", "replays": args.replays,
                                  "bootstrap": args.boot, "swaps": args.swaps, "seed": SEED}}
    est_rows = []

    def record(label, window, res, extra=None):
        s = summarise(res)
        for k in ("delta", "fwd_L_minus_E", "rev_L_minus_E", "fwd_E", "fwd_L", "rev_E", "rev_L"):
            if k in s:
                est_rows.append({"analysis": label, "window": window, "quantity": k, "triples": s["triples"],
                                 "players": s["players"], **{q: s[k][q] for q in ("est", "se", "lo", "hi", "z")},
                                 **(extra or {})})
        return s

    # ---- primary: discovery and replication, pooled tours
    prim = {}
    for w in ("discovery", "replication"):
        d = tri[tri["window"] == w].reset_index(drop=True)
        D = design(d)
        res = estimate(D, standard_contrasts())
        prim[w] = (D, res)
        results[f"primary_{w}"] = record("primary", w, res)
        log(f"primary {w}: Delta {res['contrasts']['delta']['est']:+.4f} "
            f"[{res['contrasts']['delta']['lo']:+.4f}, {res['contrasts']['delta']['hi']:+.4f}] n={res['T']}")

    # ---- bootstrap check (discovery and replication)
    for w in ("discovery", "replication"):
        D, res = prim[w]
        bs = bootstrap_delta(D, res["beta"], args.boot, SEED + (1 if w == "discovery" else 2))
        results[f"primary_{w}"]["delta_bootstrap"] = {
            "replicates": int(len(bs)), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "sd": float(bs.std(ddof=1)), "share_above_0": float((bs > 0).mean())}
        log(f"bootstrap {w}: {results[f'primary_{w}']['delta_bootstrap']}")

    # ---- label-swap placebo
    swap_rows = []
    rng = np.random.default_rng(SEED + 3)
    for w in ("discovery", "replication"):
        d = tri[tri["window"] == w].reset_index(drop=True)
        beta0 = prim[w][1]["beta"]
        for s in range(args.swaps):
            dd = swap_labels(d, rng)
            Dd = design(dd)
            b, _, _ = fit_binomial(Dd["y"], Dd["n"], Dd["off"], Dd["X"], beta0=beta0)
            swap_rows.append({"window": w, "swap": s, "delta": float(contrast(Dd["names"], delta_terms()) @ b)})
    sw = pd.DataFrame(swap_rows)
    sw.to_csv(LABEL_SWAP, index=False)
    for w in ("discovery", "replication"):
        x = sw.loc[sw["window"] == w, "delta"].to_numpy()
        obs = results[f"primary_{w}"]["delta"]["est"]
        results[f"label_swap_{w}"] = {"swaps": int(len(x)), "mean": float(x.mean()), "sd": float(x.std(ddof=1)),
                                      "q025": float(np.percentile(x, 2.5)), "q975": float(np.percentile(x, 97.5)),
                                      "observed": obs,
                                      "perm_p_two_sided": float((1 + (np.abs(x) >= abs(obs)).sum()) / (len(x) + 1))}
        log(f"label swap {w}: {results[f'label_swap_{w}']}")

    # ---- replay null: primary (tour x surface de-noising, as specified) and the player-centred variant
    prior = S.frozen_prior()
    dev_prior = S.frozen_deviation_prior()
    results["replay_prior"] = prior.to_dict(orient="records")
    results["replay_deviation_prior"] = dev_prior.to_dict(orient="records")
    rows = []
    for mode, R_mode in (("tour_mean", args.replays), ("player", args.replays_player)):
        seeds = list(range(1, R_mode + 1))
        chunks = [seeds[i::args.workers] for i in range(args.workers)]
        jobs = [(str(TRIPLES), ("discovery", "replication"), prior.to_dict(orient="records"),
                 dev_prior.to_dict(orient="records"), ch, mode) for ch in chunks if ch]
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for part in ex.map(_replay_job, jobs):
                rows += part
    rn = pd.DataFrame(rows).sort_values(["mode", "window", "seed"])
    rn.to_csv(REPLAY_NULL, index=False)
    for mode in ("tour_mean", "player"):
        for w in ("discovery", "replication"):
            sel = (rn["mode"] == mode) & (rn["window"] == w)
            x = rn.loc[sel, "delta"].to_numpy()
            se_x = rn.loc[sel, "delta_se"].to_numpy()
            obs = results[f"primary_{w}"]["delta"]
            R = len(x)
            mean, sd = float(x.mean()), float(x.std(ddof=1))
            band = max(1.96 * sd / np.sqrt(R), 0.25 * obs["se"])
            d = tri[tri["window"] == w]
            key = f"replay_null_{w}" if mode == "tour_mean" else f"replay_null_player_{w}"
            results[key] = {
                "mode": mode, "replays": R, "mean": mean, "sd": sd, "q025": float(np.percentile(x, 2.5)),
                "q975": float(np.percentile(x, 97.5)), "mean_se_within_replay": float(se_x.mean()),
                "share_replays_ci_excluding_0": float((np.abs(x / se_x) > 1.96).mean()),
                "acceptance_band_half_width": band, "inside_null": bool(abs(mean) <= band),
                "observed": obs["est"], "observed_z_vs_replay": float((obs["est"] - mean) / sd) if sd > 0 else None,
                "observed_percentile_in_replay": float((x < obs["est"]).mean()),
                **{f"{k}_mean": float(rn.loc[sel, k].mean()) for k in
                   ("fwd_L_minus_E", "rev_L_minus_E", "fwd_E", "fwd_L", "rev_E", "rev_L", "corr_rE_rL", "sd_rE",
                    "sd_rL")},
                "real_corr_rE_rL": float(np.corrcoef(d["rE"], d["rL"])[0, 1]),
                "real_sd_rE": float(d["rE"].std()), "real_sd_rL": float(d["rL"].std()),
                "never_matched_total": int(rn.loc[sel, "never_matched"].sum()),
                "dropped_empty_set_total": int(rn.loc[sel, "dropped_empty_set"].sum())}
            log(f"{key}: {results[key]}")

    # ---- pass rule
    disc, repl = results["primary_discovery"]["delta"], results["primary_replication"]["delta"]
    rule = {"discovery_delta_positive_ci_excludes_0": bool(disc["est"] > 0 and disc["lo"] > 0),
            "replay_placebo_inside_null": results["replay_null_discovery"]["inside_null"],
            "replication_same_sign": bool(repl["est"] > 0)}
    rule["pass"] = bool(all(rule.values()))
    results["pass_rule"] = rule
    log(f"pass rule: {rule}")

    # ---- secondary: fade by forward gap
    for w in ("discovery", "replication"):
        d = tri[tri["window"] == w].reset_index(drop=True)
        D = design(d, gap_by_fwd=True)
        cons = {f"delta_gap{c}": delta_terms(f"_g{c}") for c in (1, 2, 3)}
        cons["fade_1_minus_3"] = {**delta_terms("_g1"), **{k: -v for k, v in delta_terms("_g3").items()}}
        res = estimate(D, cons)
        counts = pd.Series(gap_class(d["gap_fwd"].to_numpy())).value_counts().sort_index().to_dict()
        results[f"fade_{w}"] = {**res["contrasts"], "triples_by_fwd_gap_class": {int(k): int(v) for k, v in
                                                                                 counts.items()}}
        for k, v in res["contrasts"].items():
            est_rows.append({"analysis": "fade_by_forward_gap", "window": w, "quantity": k, "triples": res["T"],
                             "players": res["players"], **{q: v[q] for q in ("est", "se", "lo", "hi", "z")}})
        log(f"fade {w}: " + ", ".join(f"{k} {v['est']:+.4f} [{v['lo']:+.4f}, {v['hi']:+.4f}]"
                                       for k, v in res["contrasts"].items()))

    # ---- pre-declared sensitivities and breakdowns (descriptive)
    def sens(label, sub_fn=None, **kw):
        for w in ("discovery", "replication"):
            d = tri[tri["window"] == w]
            if sub_fn is not None:
                d = d[sub_fn(d)]
            d = d.reset_index(drop=True)
            if len(d) < 200:
                continue
            res = estimate(design(d, **kw), standard_contrasts())
            s = record(label, w, res)
            results.setdefault("sensitivity", {}).setdefault(label, {})[w] = {
                k: s[k] for k in ("delta", "fwd_L_minus_E", "rev_L_minus_E") if k in s} | {"triples": s["triples"]}

    sens("men", lambda d: d["tour"].eq("atp"))
    sens("women", lambda d: d["tour"].eq("wta"))
    sens("best_of_3", lambda d: d["bo"].eq(3))
    sens("best_of_5", lambda d: d["bo"].eq(5))
    sens("tour_level_main_draw", lambda d: d["map_level"].isin(["GS", "T1000", "T500", "T250"]))
    sens("qualifying_challenger_itf", lambda d: ~d["map_level"].isin(["GS", "T1000", "T500", "T250"]))
    sens("t_plus_1_won (symmetric outcome selection)", lambda d: d["won_p"].astype(bool))
    sens("strict_sequences", lambda d: d["strict"].astype(bool))
    sens("exact_days", lambda d: d["exact_m"].astype(bool) & d["exact_t"].astype(bool) & d["exact_p"].astype(bool))
    sens("whole_match_residual_control", extra=("r_tot",))
    sens("audit_literal_form", form="literal")
    sens("no_form_control", form="none")
    sens("return_points (exploratory)", exp=("retE", "retL"), endpoint="return", form="none")

    pd.DataFrame(est_rows).to_csv(ESTIMATES, index=False)
    RESULTS.write_text(json.dumps(results, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {RESULTS.name}, {ESTIMATES.name}, {REPLAY_NULL.name}, {LABEL_SWAP.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", type=int, default=50)
    ap.add_argument("--replays-player", dest="replays_player", type=int, default=20)
    ap.add_argument("--boot", type=int, default=999)
    ap.add_argument("--swaps", type=int, default=500)
    ap.add_argument("--workers", type=int, default=4)
    run_main(ap.parse_args())
