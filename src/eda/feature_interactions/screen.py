"""The shared EDA screen, as adopted in docs/studies/feature_interactions/plan.md (the configuration critique's
section 6, round0/team_critique.md).

Population: the model frame's matches of 2014-2024, debut seasons out, one row per match in its stored orientation
(side A = Stage 0's player_a_id, from the pre-rebuild copy that matches the frame). Seasons 2025-2026 are dropped on load
and asserted absent: no screen can read them.

The base log-odds eta is the current best model's walk-forward out-of-sample forecast (arm "model", the 58 inputs, seeds
0-2, symmetrised, raw; "model") or the de-vigged closing price ("market", the owner's ranking lens; reported, never
gating).

The test of a hypothesis (one primary column x, antisymmetric):
    logit P(A wins) = sum_{tour, season} a * eta + sum_tour c * eta^3 + sum_j g_j * control_j + b * x
no intercept (side A is random). The statistic is the z of b with a sandwich variance clustered over four-week blocks
and shared players together (dyadic); block-only and player-only variances are computed too and the largest of the
three is used. Fitted separately on 2014-2021 (z1) and 2022-2024 (z2); z_joint = (sqrt(n1) z1 + sqrt(n2) z2) /
sqrt(n1 + n2). Preprocessing fixed on the discovery rows without results: x and the controls are scaled by their SD
(never centred: they are antisymmetric), x is clipped at the 99th percentile of |x|, missing values become 0.

Gates (plan.md): filter z1 > 1 in the declared direction; replication z2 > 0.67 in the same direction; weighted Holm
(claims, one-sided 5%) and weighted BH (bundle eligibility, q = 0.10) on the joint p-values, a filtered-out hypothesis
counting p = 1.

Placebos: P1 shuffles x within tour x season x surface x eta-decile (the empirical spread of z widens the standard error
when above 1.10); P2 for fixed player traits, a permutation of the traits across players within tour through the
hypothesis's own builder (the p-value of z_joint).

Effect sizes, reported and never gating, in milli-log-loss (positive = the hypothesis lowers the log loss): leave-one-
season-out on 2014-2021 and forward on 2022-2024 (fitted on 2014-2021), each with a free slope per tour (a season slope
cannot be fitted for a season held out), the cubic and the controls; 95% intervals over four-week blocks.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

from src.eda.feature_interactions import common as C
from src.eda.tabpfn_thinking import common as T

PRE_REBUILD_STAGE0 = (C.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" /
                      "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")
CLIP_Q = 0.99
P1_WIDEN_AT = 1.10
N_P2_EXT = 20_000          # permutations drawn afresh when the first 1,000 give p <= 0.01 (verifier B2)


# ------------------------------------------------------------------------------------------------
# The frame

def oos_model_forecast(arm: str = "model", seeds=C.SEEDS) -> pd.Series:
    """P(A wins) of the arm's out-of-sample walk-forward forecasts for 2014-2024 by match id: symmetrised, seed mean.
    2014-2018 are this study's fits; 2019-2024 the rating race's where they exist (they are identical: plan.md, M1)."""
    parts = []
    for season in C.DISCOVERY + C.REPLICATION:
        per = []
        for seed in seeds:
            name = f"{arm}__{season}__seed{seed}.npz"
            path = C.RACE_LOCAL / name if (season >= 2019 and (C.RACE_LOCAL / name).exists()) else C.LOCAL / name
            if not path.exists():
                raise FileNotFoundError(path)
            with np.load(path, allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"]
                k = len(ids)
                per.append(pd.Series(T.symmetrize(p[:k], p[k:]), index=ids.astype(str)))
        parts.append(pd.concat(per, axis=1).mean(axis=1))
    s = pd.concat(parts)
    if s.index.duplicated().any():
        raise RuntimeError("duplicate match ids across seasons")
    return s


def load(with_model: bool = True) -> pd.DataFrame:
    """The screen's frame: identifiers, players, result, the base log-odds, blocks, eta-deciles and the model's 58 inputs
    (in_<name>), 2014-2024, debut seasons out."""
    f = pd.read_parquet(C.MODEL_FRAME)
    f = f[f["season"].between(C.DISCOVERY[0], C.REPLICATION[-1])].reset_index(drop=True)
    assert f["season"].max() <= C.REPLICATION[-1], "the test seasons must never reach the screen"
    f = f[~f["debut_season"].astype(bool)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    s0 = pd.read_parquet(PRE_REBUILD_STAGE0, columns=["match_id", "player_a_id", "player_b_id", "a_won"])
    s0["match_id"] = s0["match_id"].astype(str)
    f = f.merge(s0.rename(columns={"a_won": "a_won_s0"}), on="match_id", how="left", validate="one_to_one")
    if f["a_won_s0"].isna().any() or not (f["a_won"].astype(bool) == f["a_won_s0"].astype(bool)).all():
        raise RuntimeError("side A disagrees with Stage 0's player_a_id, or a match is missing from Stage 0")
    f = f.drop(columns=["a_won_s0"])
    f["z_market"] = f["in_odds_logit"].to_numpy(dtype=float)
    if with_model:
        s = oos_model_forecast()
        f["z_model"] = C.lg(f["match_id"].map(s).to_numpy(dtype=float))
        if not np.isfinite(f["z_model"]).all():
            raise RuntimeError(f"{int((~np.isfinite(f['z_model'])).sum())} matches without a model forecast")
    f["window"] = np.where(f["season"] <= C.DISCOVERY[-1], "discovery", "replication")
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    return f


# ------------------------------------------------------------------------------------------------
# Fitting and variance

def fit(Z: np.ndarray, y: np.ndarray, pen: np.ndarray | None = None, max_iter: int = 80, tol: float = 1e-10):
    """Maximum likelihood (ridge pen per column, default a negligible 1e-8), no intercept. Returns (beta, p, H)."""
    k = Z.shape[1]
    pen = np.full(k, 1e-8) if pen is None else np.asarray(pen, float)
    beta = np.zeros(k)
    for _ in range(max_iter):
        p = expit(Z @ beta)
        g = Z.T @ (y - p) - pen * beta
        H = (Z.T * (p * (1 - p))) @ Z + np.diag(pen)
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        beta += step
        if np.abs(step).max() < tol:
            break
    p = expit(Z @ beta)
    H = (Z.T * (p * (1 - p))) @ Z + np.diag(pen)
    return beta, p, H


def _sum_sq_by(u: np.ndarray, keys: np.ndarray) -> float:
    _, ix = np.unique(keys, return_inverse=True)
    s = np.bincount(ix, weights=u)
    return float(np.dot(s, s))


def clustered_variances(u: np.ndarray, block: np.ndarray, pa: np.ndarray, pb: np.ndarray) -> dict:
    """Variance of a scalar estimator with influence terms u_i, clustered (a) by four-week block, (b) by shared player
    (dyadic: pairs of matches sharing at least one player), (c) by either. Small-sample factor G/(G - 1), G = blocks."""
    G = len(np.unique(block))
    corr = G / (G - 1) if G > 1 else np.nan
    v_block = _sum_sq_by(u, block)
    pa, pb = np.asarray(pa, str), np.asarray(pb, str)
    players = np.r_[pa, pb]
    uu = np.r_[u, u]
    pair = np.where(pa < pb, np.char.add(np.char.add(pa, "|"), pb), np.char.add(np.char.add(pb, "|"), pa))
    v_player = _sum_sq_by(uu, players) - _sum_sq_by(u, pair)
    bk = np.r_[block, block].astype(str)
    v_both = _sum_sq_by(uu, np.char.add(np.char.add(players.astype(str), "#"), bk)) - \
        _sum_sq_by(u, np.char.add(np.char.add(pair.astype(str), "#"), block.astype(str)))
    v_union = v_block + v_player - v_both
    return {"block": corr * v_block, "player": corr * v_player, "union": corr * v_union}


# ------------------------------------------------------------------------------------------------
# Hypotheses

@dataclass
class Hypothesis:
    hid: str
    x: np.ndarray                              # primary column, antisymmetric, NaN allowed (n,)
    controls: np.ndarray | None = None         # (n, m) antisymmetric controls (the type's marginality set and more)
    control_names: list = field(default_factory=list)
    sign: str = "+"                            # "+", "-" or "two"
    weight: float = 1.0
    trait: str = "none"                        # "none" | "slow" | "fixed" (M4)
    permute: object = None                     # fixed traits: callable(rng) -> x with traits permuted within tour
    family: str = ""
    kind: str = ""                             # S W X C U M
    note: str = ""


@dataclass
class Prep:
    """Preprocessing fixed on the discovery rows without results."""
    x_clip: float
    x_sd: float
    c_sd: np.ndarray
    cube_sd: dict


def prepare(f: pd.DataFrame, h: Hypothesis, base: str) -> tuple[np.ndarray, np.ndarray | None, Prep]:
    disc = (f["window"] == "discovery").to_numpy()
    x = np.asarray(h.x, float).copy()
    clip = float(np.nanquantile(np.abs(x[disc]), CLIP_Q)) if np.isfinite(x[disc]).any() else 1.0
    clip = clip if clip > 0 else 1.0
    x = np.clip(x, -clip, clip)
    sd = float(np.nanstd(x[disc])) or 1.0
    xs = np.nan_to_num(x / sd, nan=0.0)
    Cs, csd = None, np.zeros(0)
    if h.controls is not None and np.asarray(h.controls).size:
        Cm = np.asarray(h.controls, float).reshape(len(f), -1)
        csd = np.nanstd(Cm[disc], axis=0)
        csd = np.where(np.isfinite(csd) & (csd > 0), csd, 1.0)
        Cs = np.nan_to_num(Cm / csd, nan=0.0)
    eta = f[f"z_{base}"].to_numpy(float)
    cube_sd = {t: float(np.std(eta[disc & (f["tour"] == t).to_numpy()] ** 3)) or 1.0 for t in C.TOURS}
    return xs, Cs, Prep(clip, sd, csd, cube_sd)


def nuisance(f: pd.DataFrame, rows: np.ndarray, base: str, per_season: bool, prep: Prep) -> np.ndarray:
    eta = f[f"z_{base}"].to_numpy(float)[rows]
    tour = f["tour"].to_numpy()[rows]
    season = f["season"].to_numpy()[rows]
    cols = []
    keys = sorted(set(zip(tour, season))) if per_season else [(t, None) for t in C.TOURS]
    for t, s in keys:
        m = (tour == t) if s is None else ((tour == t) & (season == s))
        if m.any() or s is None:                 # one slope per tour: both columns always (a held-out season may lack a tour)
            cols.append(np.where(m, eta, 0.0))
    for t in C.TOURS:
        cols.append(np.where(tour == t, eta ** 3 / prep.cube_sd[t], 0.0))
    return np.column_stack(cols)


def coef_test(f: pd.DataFrame, rows: np.ndarray, xs: np.ndarray, Cs: np.ndarray | None, base: str, prep: Prep) -> dict:
    """b, its variances and z on the given rows (per tour x season slopes, the cubic, the controls)."""
    N = nuisance(f, rows, base, True, prep)
    parts = [N] + ([Cs[rows]] if Cs is not None else []) + [xs[rows][:, None]]
    Z = np.column_stack(parts)
    y = f["a_won"].to_numpy(float)[rows]
    beta, p, H = fit(Z, y)
    j = Z.shape[1] - 1
    a_j = np.linalg.solve(H, np.eye(Z.shape[1])[j])
    u = (y - p) * (Z @ a_j)
    v = clustered_variances(u, f["block"].to_numpy()[rows], f["player_a_id"].to_numpy(str)[rows],
                            f["player_b_id"].to_numpy(str)[rows])
    model_var = float(a_j[j])
    var = max(v["union"], v["block"], v["player"])
    return {"b": float(beta[j]), "se": float(np.sqrt(var)), "z": float(beta[j] / np.sqrt(var)),
            "se_model": float(np.sqrt(model_var)), "se_block": float(np.sqrt(v["block"])),
            "se_player": float(np.sqrt(max(v["player"], 0))), "se_union": float(np.sqrt(max(v["union"], 0))),
            "n": int(rows.sum())}


def _vsum_sq_by(U: np.ndarray, keys: np.ndarray) -> np.ndarray:
    _, ix = np.unique(keys, return_inverse=True)
    S = np.zeros((ix.max() + 1, U.shape[1]))
    np.add.at(S, ix, U)
    return S.T @ S


def clustered_cov(U: np.ndarray, block: np.ndarray, pa: np.ndarray, pb: np.ndarray) -> dict:
    """The k x k analogue of clustered_variances for influence vectors U (n, k)."""
    G = len(np.unique(block))
    corr = G / (G - 1)
    pa, pb = np.asarray(pa, str), np.asarray(pb, str)
    players = np.r_[pa, pb]
    UU = np.r_[U, U]
    pair = np.where(pa < pb, np.char.add(np.char.add(pa, "|"), pb), np.char.add(np.char.add(pb, "|"), pa))
    v_block = _vsum_sq_by(U, block)
    v_player = _vsum_sq_by(UU, players) - _vsum_sq_by(U, pair)
    bk = np.r_[block, block].astype(str)
    v_both = _vsum_sq_by(UU, np.char.add(np.char.add(players.astype(str), "#"), bk)) - \
        _vsum_sq_by(U, np.char.add(np.char.add(pair.astype(str), "#"), block.astype(str)))
    return {"block": corr * v_block, "player": corr * v_player, "union": corr * (v_block + v_player - v_both)}


def f_pvalue(W: float, k: int, G: int) -> float:
    """Wald statistic W on k df with G clusters, referred to F(k, G - k) (the Hotelling small-sample reference)."""
    from scipy.stats import f as f_dist
    return float(f_dist.sf(W / k * (G - k) / (G - 1), k, G - k))


def coef_test_multi(f: pd.DataFrame, rows: np.ndarray, Xs: np.ndarray, Cs: np.ndarray | None, base: str,
                    prep: Prep) -> dict:
    """The k coefficients of the block's columns Xs (n, k), their clustered covariance (the largest of block, player
    and union by trace) and the Wald statistic."""
    from scipy.stats import chi2
    N = nuisance(f, rows, base, True, prep)
    parts = [N] + ([Cs[rows]] if Cs is not None else []) + [Xs[rows]]
    Z = np.column_stack(parts)
    y = f["a_won"].to_numpy(float)[rows]
    beta, p, H = fit(Z, y)
    k = Xs.shape[1]
    J = np.arange(Z.shape[1] - k, Z.shape[1])
    A = np.linalg.solve(H, np.eye(Z.shape[1])[:, J])          # columns of H^-1 for the block
    U = (y - p)[:, None] * (Z @ A)
    covs = clustered_cov(U, f["block"].to_numpy()[rows], f["player_a_id"].to_numpy(str)[rows],
                         f["player_b_id"].to_numpy(str)[rows])
    b = beta[J]
    Ws = {nm: float(b @ np.linalg.solve(m, b)) for nm, m in covs.items()}
    name = min(Ws, key=Ws.get)                   # the most conservative of the three (verifier B8)
    V, W = covs[name], Ws[name]
    G = len(np.unique(f["block"].to_numpy()[rows]))
    return {"b": b, "V": V, "W": W, "p": f_pvalue(W, k, G), "k": k, "G": G, "n": int(rows.sum()), "cov": name}


def run_wald(f: pd.DataFrame, hid: str, X: np.ndarray, controls: np.ndarray | None, base: str = "model",
             n_p1: int = 200, seed: int = 20261006, weight: float = 0.5, note: str = "", trait: str = "none") -> dict:
    """A k-column block with a two-sided member: Wald tests on 2014-2021 (filter p1 < 0.3173, the 1-df |z| > 1),
    on 2014-2024 pooled (the joint p), and replication as the one-sided z of the 2022-2024 coefficients along the
    discovery direction (> 0.67). P1 permutes the block's rows jointly; the mean of the null Wald statistic over k
    widens the covariance when above 1.10^2."""
    from scipy.stats import chi2
    disc = (f["window"] == "discovery").to_numpy()
    rep = (f["window"] == "replication").to_numpy()
    allw = disc | rep
    X = np.asarray(X, float).reshape(len(f), -1)
    Xs = np.empty_like(X)
    for j in range(X.shape[1]):
        h = Hypothesis(hid, X[:, j], None)
        Xs[:, j], _, prep = prepare(f, h, base)
    _, Cs, prep = prepare(f, Hypothesis(hid, X[:, 0], controls), base)
    r1 = coef_test_multi(f, disc, Xs, Cs, base, prep)
    r2 = coef_test_multi(f, rep, Xs, Cs, base, prep)
    rj = coef_test_multi(f, allw, Xs, Cs, base, prep)
    widen = 1.0
    out = {"hid": hid, "base": base, "sign": "two", "weight": weight, "wald_k": r1["k"], "note": note}
    if n_p1:
        rng = np.random.default_rng(seed)
        g = strata(f, base)
        null = []
        for _ in range(n_p1):
            order = permute_within(np.arange(len(f), dtype=float), g, rng).astype(int)
            null.append(coef_test_multi(f, disc, Xs[order], Cs, base, prep)["W"])
        m = float(np.mean(null)) / r1["k"]
        out.update({"p1_null_mean_per_df": m})
        widen = m if m > P1_WIDEN_AT ** 2 else 1.0
    if trait in ("slow", "fixed"):        # player traits: the covariance x 1.25 (plan.md, decision of 6 Oct, 23:10)
        widen = max(widen, 1.25)
    out["widen"] = widen
    out["trait"] = trait
    W1, Wj = r1["W"] / widen, rj["W"] / widen
    d = r1["b"]
    z_rep = float((d @ r2["b"]) / np.sqrt(d @ r2["V"] @ d)) / np.sqrt(widen)      # a scalar contrast (verifier B8)
    p1 = f_pvalue(W1, r1["k"], r1["G"])
    out.update({"W1": W1, "p1": p1, "W_joint": Wj, "p_joint": f_pvalue(Wj, rj["k"], rj["G"]),
                "z_rep_along_disc": z_rep, "b1": json.dumps(np.round(r1["b"], 5).tolist()),
                "b2": json.dumps(np.round(r2["b"], 5).tolist()), "n1": r1["n"], "n2": r2["n"],
                "filter_pass": bool(p1 < 0.3173), "replicates": bool(z_rep > 0.67)})
    return out


def joint_z(z1: float, z2: float, n1: int, n2: int) -> float:
    return (np.sqrt(n1) * z1 + np.sqrt(n2) * z2) / np.sqrt(n1 + n2)


def oriented(z: float, sign: str) -> float:
    return z if sign == "+" else (-z if sign == "-" else abs(z))


def p_value(z: float, sign: str) -> float:
    return float(2 * norm.sf(abs(z))) if sign == "two" else float(norm.sf(oriented(z, sign)))


# ------------------------------------------------------------------------------------------------
# Effect sizes (out-of-sample log loss; never gating)

def _oos(f, rows_fit, rows_pred, xs, Cs, base, prep, with_x: bool):
    def design(rows):
        parts = [nuisance(f, rows, base, False, prep)] + ([Cs[rows]] if Cs is not None else [])
        if with_x:
            parts.append(xs[rows][:, None])
        return np.column_stack(parts)
    y = f["a_won"].to_numpy(float)
    beta, _, _ = fit(design(rows_fit), y[rows_fit])
    return expit(design(rows_pred) @ beta)


def effect_sizes(f: pd.DataFrame, xs: np.ndarray, Cs: np.ndarray | None, base: str, prep: Prep) -> list[dict]:
    season = f["season"].to_numpy()
    disc = np.isin(season, C.DISCOVERY)
    rep = np.isin(season, C.REPLICATION)
    p0 = np.full(len(f), np.nan)
    p1 = np.full(len(f), np.nan)
    for s in C.DISCOVERY:
        pr = season == s
        if pr.any():
            p0[pr] = _oos(f, disc & ~pr, pr, xs, Cs, base, prep, False)
            p1[pr] = _oos(f, disc & ~pr, pr, xs, Cs, base, prep, True)
    p0[rep] = _oos(f, disc, rep, xs, Cs, base, prep, False)
    p1[rep] = _oos(f, disc, rep, xs, Cs, base, prep, True)
    y = f["a_won"].to_numpy(bool)
    out = []
    for window, wm in (("discovery", disc), ("replication", rep)):
        for tour in ("both", "atp", "wta"):
            k = wm & (np.ones(len(f), bool) if tour == "both" else (f["tour"] == tour).to_numpy())
            c = T.compare(T.ll(p0[k], y[k]), T.ll(p1[k], y[k]), f.loc[k, "tournament_date"].to_numpy())
            out.append({"window": window, "tour": tour, "matches": c["n"], "gain": c["gain"], "lo": c["lo"],
                        "hi": c["hi"]})
    return out


# ------------------------------------------------------------------------------------------------
# Placebos

def strata(f: pd.DataFrame, base: str) -> np.ndarray:
    eta = f[f"z_{base}"].to_numpy(float)
    key = f["tour"].astype(str) + "|" + f["season"].astype(str) + "|" + f["in_surface"].astype(str)
    dec = pd.Series(eta).groupby([f["tour"].to_numpy(), f["season"].to_numpy()]).transform(
        lambda s: pd.qcut(s.rank(method="first"), 10, labels=False)).to_numpy()
    return pd.factorize(key + "|" + pd.Series(dec).astype(str))[0]


def permute_within(x: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = x.copy()
    order = np.argsort(groups, kind="stable")
    g = groups[order]
    starts = np.r_[0, np.flatnonzero(np.diff(g)) + 1, len(g)]
    for a, b in zip(starts[:-1], starts[1:]):
        ix = order[a:b]
        out[ix] = x[rng.permutation(ix)]
    return out


# ------------------------------------------------------------------------------------------------
# One hypothesis, end to end

def run(f: pd.DataFrame, h: Hypothesis, base: str = "model", n_p1: int = 200, n_p2: int = 1000,
        seed: int = 20261006, sizes: bool = True) -> dict:
    disc = (f["window"] == "discovery").to_numpy()
    rep = (f["window"] == "replication").to_numpy()
    xs, Cs, prep = prepare(f, h, base)
    r1 = coef_test(f, disc, xs, Cs, base, prep)
    r2 = coef_test(f, rep, xs, Cs, base, prep)
    out = {"hid": h.hid, "family": h.family, "kind": h.kind, "base": base, "sign": h.sign, "weight": h.weight,
           "trait": h.trait, "controls": json.dumps(h.control_names), "note": h.note,
           "coverage_disc": float(np.isfinite(np.asarray(h.x, float)[disc]).mean()),
           "coverage_rep": float(np.isfinite(np.asarray(h.x, float)[rep]).mean())}
    for tag, r in (("1", r1), ("2", r2)):
        out.update({f"{k}{tag}": v for k, v in r.items()})
    widen = 1.0
    rng = np.random.default_rng(seed)
    if n_p1:
        g = strata(f, base)
        null = []
        for _ in range(n_p1):
            xp = permute_within(xs, g, rng)
            null.append(coef_test(f, disc, xp, Cs, base, prep)["z"])
        sd = float(np.std(null, ddof=1))
        out.update({"p1_null_sd": sd, "p1_null_mean": float(np.mean(null))})
        widen = sd if sd > P1_WIDEN_AT else 1.0
    if h.trait == "slow":
        widen = max(widen, np.sqrt(1.25))
    out["widen"] = widen
    z1, z2 = r1["z"] / widen, r2["z"] / widen
    zj = joint_z(z1, z2, r1["n"], r2["n"])
    out.update({"z1_adj": z1, "z2_adj": z2, "z_joint": zj, "p_joint": p_value(zj, h.sign),
                "filter_pass": bool(oriented(z1, h.sign) > 1.0),
                "replicates": bool(oriented(z2, h.sign) > 0.67 and (h.sign != "two" or np.sign(z2) == np.sign(z1)))})
    if h.permute is not None and n_p2:
        # a fixed trait: the permutation p is folded into p_joint (M4). Any other trait with trait columns (B7, B9a:
        # height enters only some members, checkpoint 1 R-6): the permutation is a diagnostic, never folded, never
        # extended
        z_raw = oriented(joint_z(r1["z"], r2["z"], r1["n"], r2["n"]), h.sign)     # unwidened (verifier B7)

        def perm_null(n):
            vals = []
            for _ in range(n):
                xp_out = h.permute(rng)
                xp, Cp = (xp_out if isinstance(xp_out, tuple) else (xp_out, h.controls))
                hp = Hypothesis(h.hid, xp, Cp, h.control_names, h.sign)
                xsp, Csp, prp = prepare(f, hp, base)
                a = coef_test(f, disc, xsp, Csp, base, prp)["z"]
                b = coef_test(f, rep, xsp, Csp, base, prp)["z"]
                vals.append(oriented(joint_z(a, b, r1["n"], r2["n"]), h.sign))
            return np.asarray(vals)
        fold = h.trait == "fixed"
        null = perm_null(n_p2)
        p2 = float((1 + (null >= z_raw).sum()) / (1 + len(null)))
        if fold and p2 <= 0.01:                          # a fresh, larger set near a claim (verifier B2)
            null = perm_null(N_P2_EXT)
            p2 = float((1 + (null >= z_raw).sum()) / (1 + len(null)))
        out.update({"p2_perm": p2, "p2_n": int(len(null)), "p2_sd": float(np.std(null, ddof=1)), "p2_folded": fold})
        if fold:
            out["p_joint"] = max(out["p_joint"], p2)
    if sizes:
        for r in effect_sizes(f, xs, Cs, base, prep):
            key = f"{r['window'][:4]}_{r['tour']}"
            out.update({f"gain_{key}": r["gain"], f"lo_{key}": r["lo"], f"hi_{key}": r["hi"]})
    return out


# ------------------------------------------------------------------------------------------------
# Multiplicity

def weighted_holm(p: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Adjusted p-values of the weighted Holm procedure (weights normalised to mean 1): reject H_i at level alpha when
    the step-down on p_i / w_i passes."""
    p = np.asarray(p, float)
    w = np.asarray(w, float)
    w = w / w.mean()
    q = np.minimum(1.0, p / w)
    order = np.argsort(q)
    m = len(p)
    adj = np.empty(m)
    run_max = 0.0
    remaining = w.sum()
    for j in order:
        run_max = max(run_max, min(1.0, p[j] * remaining / w[j]))
        adj[j] = run_max
        remaining -= w[j]
    return adj


def weighted_bh(p: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Adjusted p-values (q-values) of BH on p_i / w_i, weights normalised to mean 1 (Genovese, Roeder, Wasserman)."""
    w = np.asarray(w, float)
    q = np.minimum(1.0, np.asarray(p, float) / (w / w.mean()))
    m = len(q)
    order = np.argsort(q)
    adj = np.empty(m)
    prev = 1.0
    for rank in range(m, 0, -1):
        j = order[rank - 1]
        prev = min(prev, q[j] * m / rank)
        adj[j] = prev
    return adj
