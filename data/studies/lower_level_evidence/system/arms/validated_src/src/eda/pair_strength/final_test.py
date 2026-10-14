"""The one-shot test of the reversed I-084 on 2025-2026 (docs/studies/pair_strength/preregistration.md), run ONCE after
the pre-registration is hashed. Nothing in this module may change after that hash.

Population: the model frame's 2025-2026 main-tour matches, debut seasons out (the feature-interactions final test's
8,520). The base eta: the current best's raw out-of-sample log-odds, the seed mean of every seed available (0-15).
The modulator s: the pair's overall Elo sum R_A + R_B (Elo pieces, the ratings of the model's elo_overall input),
centred and divided by its SD per tour with constants fixed on the development rows 2014-2021 (debut seasons out).

TWO PRIMARY HYPOTHESES, one-sided, family-wise 5% by Holm (the smaller p against 0.025, then the larger against 0.05):
H1 (the lead; b < 0, "the forecast's slope falls with pair strength"):
    logit P(A wins) = sum_{tour, season} a eta + sum_tour c eta^3 + sum_tour m eta|eta| + b (s eta), no intercept;
    b's variance the largest of the four-week-block, shared-player and union clustered variances; t on G - 1 degrees
    of freedom (G four-week blocks).
H2 (inclusion in the model): the TabPFN arm "elosum" (the 58 inputs plus R_A + R_B; seeds 0-7) has a lower log loss
    than the current best (seeds 0-7), each deployed with the decided calibration (one slope per tour fitted on the
    arm's own out-of-sample forecasts of 2019 .. Y-1; the model's history with every seed available, the arm's with
    seeds 0-2 in 2019-2024 and 0-7 in 2025); paired mean log-loss difference with the four-week-block cluster SE, t on
    G - 1 degrees of freedom.
EFFECT SIZES: H2's paired gain itself; for H1, the walk-forward layer "lin" (a slope per tour plus b_tour elo_sum x eta)
    against "B14" (a slope per tour), each fitted on the base's out-of-sample forecasts of 2014 .. Y-1 and applied to
    Y = 2025, 2026; paired log loss, mLL per match, positive = the second-named better; 95% interval over four-week
    blocks.
SECONDARIES (descriptive): H1 by tour and by season; the price base (the de-vigged average close); the weakest-fifth
    form (1[elo_sum <= the tour's 20th percentile of 2014-2024] x eta); the layers lin_pooled and q1 against B14 and lin
    against the decided calibration B (2019 .. Y-1); Polymarket (matches with a price 24 hours before the listed
    start): the coefficient on the 24-hour price, the 30-minute price and the model fed the 24-hour price; H2 by tour
    and by season; H2's encompassing coefficient with disjoint seeds (base: the model's seeds 8-15; deviation: arm
    0-7 minus model 0-7); the arm's own H1 coefficient; both arms fed the 24-hour Polymarket price.

    ./python.sh src/eda/pair_strength/final_test.py --check     # result-free: population, constants, hashes
    ./python.sh src/eda/pair_strength/final_test.py --run       # ONCE, after the pre-registration's hash
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.feature_interactions import common as FC  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = C.OUT / "final"
TEST = (2025, 2026)
HIST_FROM = 2014
SEEDS_ALL = tuple(range(16))
ARM, ARM_SEEDS = "elosum", tuple(range(8))
PIECES = ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet"
FOLDERS = (FC.LOCAL, FC.RACE_LOCAL)                 # the current best's forecasts (arm "model")
INPUT_FILES = {"MODEL_FRAME_SHA256": FC.MODEL_FRAME, "PIECES_SHA256": PIECES, "STAGE0_SHA256": S.PRE_REBUILD_STAGE0,
               "EARLY_SHA256": FC.EARLY}


# ------------------------------------------------------------------------------------------------ frames

def _elo_sum(ids: pd.Series) -> np.ndarray:
    p = pd.read_parquet(PIECES, columns=["match_id", "R_a", "R_b"])
    p["match_id"] = p["match_id"].astype(str)
    g = pd.DataFrame({"match_id": ids.astype(str).to_numpy()}).merge(p, on="match_id", how="left", validate="one_to_one")
    return (g["R_a"] + g["R_b"]).to_numpy(float)


def frame(seasons, with_results: bool, with_players: bool = True) -> pd.DataFrame:
    """The model frame's matches of the given seasons, debut seasons out, with the Elo sum and four-week blocks. The
    result column is read only when with_results is True."""
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "in_odds_logit"]
    f = pd.read_parquet(FC.MODEL_FRAME, columns=cols + (["a_won"] if with_results else []))
    f = f[f["season"].isin(list(seasons)) & ~f["debut_season"].astype(bool)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    if with_players:
        s0 = pd.read_parquet(S.PRE_REBUILD_STAGE0, columns=["match_id", "player_a_id", "player_b_id"])
        s0["match_id"] = s0["match_id"].astype(str)
        f = f.merge(s0, on="match_id", how="left", validate="one_to_one")
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    f["pr_elo_sum"] = _elo_sum(f["match_id"])
    return f


def constants() -> dict:
    """Result-free constants from the development rows: per tour, the Elo sum's mean and SD on 2014-2021 and its 20th
    percentile on 2014-2024 (debut seasons out)."""
    d = frame(range(2014, 2025), with_results=False, with_players=False)
    out = {}
    for t in C.TOURS:
        m = (d["tour"] == t).to_numpy()
        disc = m & (d["season"] <= 2021).to_numpy()
        v = d["pr_elo_sum"].to_numpy(float)
        out[t] = {"mean": float(v[disc].mean()), "sd": float(v[disc].std()), "q20": float(np.quantile(v[m], 0.2))}
    return out


def standardise(f: pd.DataFrame, K: dict) -> np.ndarray:
    v = f["pr_elo_sum"].to_numpy(float)
    t = f["tour"].to_numpy()
    out = np.full(len(f), np.nan)
    for tour in C.TOURS:
        m = t == tour
        out[m] = (v[m] - K[tour]["mean"]) / K[tour]["sd"]
    return out


def weakest_fifth(f: pd.DataFrame, K: dict) -> np.ndarray:
    v, t = f["pr_elo_sum"].to_numpy(float), f["tour"].to_numpy()
    return np.where(t == "atp", v <= K["atp"]["q20"], v <= K["wta"]["q20"]).astype(float)


def population(with_results: bool) -> pd.DataFrame:
    f = frame(TEST, with_results)
    ep = pd.read_parquet(FC.EARLY, columns=["match_id", "p_early_a", "p_close_a", "all_early", "clean"])
    ep["match_id"] = ep["match_id"].astype(str)
    f = f.merge(ep, on="match_id", how="left", validate="one_to_one")
    for c in ("all_early", "clean"):
        f[c] = f[c].fillna(False).astype(bool)
    return f


def population_hash(f: pd.DataFrame) -> str:
    return hashlib.sha256("\n".join(sorted(f["match_id"].astype(str))).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ forecasts

def _load(arm: str, season: int, seed: int) -> Path | None:
    if arm == ARM:
        p = C.LOCAL / f"{arm}__{season}__seed{seed}.npz"
        return p if p.exists() else None
    for folder in FOLDERS:
        p = folder / f"{arm}__{season}__seed{seed}.npz"
        if p.exists():
            return p
    return None


def eta(arm: str, seeds, seasons, block: str = "td") -> pd.Series:
    """Raw log-odds by match id: the symmetrised seed mean of the given seeds that exist in each season."""
    parts = []
    for s in seasons:
        per = []
        for k in seeds:
            path = _load(arm, s, k)
            if path is None:
                continue
            with np.load(path, allow_pickle=False) as z:
                p, ids = z[f"p_{block}"], z[f"ids_{block}"]
                n = len(ids)
                per.append(pd.Series(T.symmetrize(p[:n], p[n:]), index=ids.astype(str)))
        if not per:
            raise FileNotFoundError(f"{arm} {s}: no forecast file")
        m = pd.concat(per, axis=1).mean(axis=1)
        parts.append(pd.Series(C.lg(m.to_numpy()), index=m.index))
    return pd.concat(parts)


# ------------------------------------------------------------------------------------------------ the tests

def coef(f: pd.DataFrame, e: np.ndarray, mod: np.ndarray, rows: np.ndarray | None = None, name: str = "s",
         expect: str = "-") -> dict:
    """b on mod * eta with the screen's nuisance; t on G - 1; the one-sided p in the expected direction (H1's "-" for
    the pair-strength modulator: flatter for strong pairs; "+" for the weakest-fifth indicator: steeper for weak
    pairs) and the two-sided p."""
    rows = np.ones(len(f), bool) if rows is None else np.asarray(rows, bool)
    rows = rows & np.isfinite(e)
    r = C.slope_fit(f, rows, e, {name: mod})
    t_ = r["terms"][name]
    G = int(len(np.unique(f["block"].to_numpy()[rows])))
    q = student_t.ppf(0.975, G - 1)
    p_exp = student_t.cdf(t_["z"], G - 1) if expect == "-" else student_t.sf(t_["z"], G - 1)
    return {"b": t_["b"], "se": t_["se"], "t": t_["z"], "df": G - 1, "expected_sign": expect,
            "p_one_sided_expected": float(p_exp), "p_two_sided": float(2 * student_t.sf(abs(t_["z"]), G - 1)),
            "lo": t_["b"] - q * t_["se"], "hi": t_["b"] + q * t_["se"], "n": int(rows.sum()), "blocks": G}


def layer_design(f: pd.DataFrame, e: np.ndarray, spec: str, train: pd.DataFrame | None, q20: dict | None) -> np.ndarray:
    tour = f["tour"].to_numpy()
    es = f["pr_elo_sum"].to_numpy(float) / 1000.0 - 4.4
    cols = [np.where(tour == t, e, 0.0) for t in C.TOURS]
    if spec == "lin":
        cols += [np.where(tour == t, es * e, 0.0) for t in C.TOURS]
    elif spec == "lin_pooled":
        cols.append(es * e)
    elif spec == "q1":
        v = f["pr_elo_sum"].to_numpy(float)
        q = np.where(tour == "atp", v <= q20["atp"], v <= q20["wta"]).astype(float)
        cols += [np.where(tour == t, q * e, 0.0) for t in C.TOURS]
    return np.column_stack(cols)


def history(seasons) -> pd.DataFrame:
    """The base's out-of-sample forecasts (every available seed) and results of earlier seasons."""
    h = frame(seasons, with_results=True, with_players=False)
    h["eta"] = h["match_id"].map(eta("model", SEEDS_ALL, seasons)).to_numpy(float)
    if not np.isfinite(h["eta"]).all():
        raise RuntimeError("history matches without a base forecast")
    return h


def layers(f: pd.DataFrame, z: np.ndarray) -> tuple[dict, dict]:
    """Per test season Y: B (one slope per tour on 2019 .. Y-1) and the layers B14, lin, lin_pooled, q1 (2014 .. Y-1);
    the weakest fifth's edges from the training rows."""
    P = {k: np.full(len(f), np.nan) for k in ("B", "B14", "lin", "lin_pooled", "q1")}
    params = {}
    for Y in TEST:
        h = history(range(HIST_FROM, Y))
        k = (f["season"] == Y).to_numpy()
        g = f[k].reset_index(drop=True)
        q20 = {t: float(np.quantile(h.loc[h["tour"] == t, "pr_elo_sum"], 0.2)) for t in C.TOURS}
        yh, eh = h["a_won"].to_numpy(float), h["eta"].to_numpy(float)
        params[Y] = {"fitted_on": [HIST_FROM, Y - 1], "q20": q20}
        for spec in ("B14", "lin", "lin_pooled", "q1"):
            beta, _, _ = S.fit(layer_design(h, eh, spec, h, q20), yh)
            P[spec][k] = expit(layer_design(g, z[k], spec, h, q20) @ beta)
            params[Y][spec] = [float(b) for b in beta]
        h19 = (h["season"] >= C.CALIB_FROM).to_numpy()
        beta, _, _ = S.fit(layer_design(h[h19], eh[h19], "B14", None, None), yh[h19])
        P["B"][k] = expit(layer_design(g, z[k], "B14", None, None) @ beta)
        params[Y]["B"] = [float(b) for b in beta]
    return P, params


def paired(f: pd.DataFrame, pa: np.ndarray, pb: np.ndarray, rows: np.ndarray | None = None) -> dict:
    """pb against pa, mLL per match, positive = pb has the lower log loss (better), four-week-block interval."""
    rows = np.ones(len(f), bool) if rows is None else rows
    ok = rows & np.isfinite(pa) & np.isfinite(pb)
    y = f["a_won"].to_numpy(bool)[ok]
    c = T.compare(T.ll(np.asarray(pa)[ok], y), T.ll(np.asarray(pb)[ok], y), f.loc[ok, "tournament_date"].to_numpy())
    return {"n": int(c["n"]), "gain": float(c["gain"]), "lo": float(c["lo"]), "hi": float(c["hi"])}


def paired_test(f: pd.DataFrame, pa: np.ndarray, pb: np.ndarray, rows: np.ndarray | None = None) -> dict:
    """pb against pa: mean log-loss difference (pa - pb, mLL; positive = pb better), four-week-block cluster SE, t on
    G - 1, one-sided p for pb better; the same mean and interval as tabpfn_thinking.common.compare."""
    rows = np.ones(len(f), bool) if rows is None else rows
    ok = rows & np.isfinite(pa) & np.isfinite(pb)
    y = f["a_won"].to_numpy(bool)[ok]
    d = T.ll(np.asarray(pa)[ok], y) - T.ll(np.asarray(pb)[ok], y)
    labels, ix = np.unique(f["block"].to_numpy()[ok], return_inverse=True)
    G, n = len(labels), len(d)
    infl = np.bincount(ix, weights=d - d.mean())
    se = float(np.sqrt(G / (G - 1) * np.dot(infl, infl)) / n)
    tval = float(d.mean() / se)
    q = student_t.ppf(0.975, G - 1)
    return {"n": int(n), "gain": 1000 * float(d.mean()), "lo": 1000 * float(d.mean() - q * se),
            "hi": 1000 * float(d.mean() + q * se), "t": tval, "df": G - 1,
            "p_one_sided_second_better": float(student_t.sf(tval, G - 1))}


def deployed_arms(f: pd.DataFrame, block: str = "td") -> dict:
    """The model (seeds 0-7) and the elosum arm (seeds 0-7), each with the decided calibration (one slope per tour on
    its own out-of-sample forecasts of 2019 .. Y-1): calibrated probabilities and raw log-odds. With block "early",
    both arms fed the 24-hour Polymarket price (rows without it are NaN)."""
    out = {}
    for arm, hist_seeds in (("model", SEEDS_ALL), (ARM, ARM_SEEDS)):
        za = f["match_id"].map(eta(arm, ARM_SEEDS, TEST, block=block)).to_numpy(float)
        p = np.full(len(f), np.nan)
        for Y in TEST:
            h = frame(range(C.CALIB_FROM, Y), with_results=True, with_players=False)
            h["eta"] = h["match_id"].map(eta(arm, hist_seeds, range(C.CALIB_FROM, Y))).to_numpy(float)
            beta, _, _ = S.fit(layer_design(h, h["eta"].to_numpy(float), "B14", None, None), h["a_won"].to_numpy(float))
            k = (f["season"] == Y).to_numpy() & np.isfinite(za)
            p[k] = expit(layer_design(f[k].reset_index(drop=True), za[k], "B14", None, None) @ beta)
        out[arm] = {"p": p, "eta": za}
    return out


def holm(p1: float, p2: float, alpha: float = 0.05) -> dict:
    order = sorted([("H1", p1), ("H2", p2)], key=lambda t: t[1])
    out, go = {}, True
    for i, (name, p) in enumerate(order):
        level = alpha / (2 - i)
        go = go and (p < level)
        out[name] = {"p_one_sided": p, "holm_level": level, "rejected": bool(go)}
    return out


def primary(f: pd.DataFrame, K: dict) -> dict:
    z = f["match_id"].map(eta("model", SEEDS_ALL, TEST)).to_numpy(float)
    h1 = coef(f, z, standardise(f, K))
    A = deployed_arms(f)
    h2 = paired_test(f, A["model"]["p"], A[ARM]["p"])
    return {"H1": h1, "H2": h2, "holm": holm(h1["p_one_sided_expected"], h2["p_one_sided_second_better"])}


def effect(f: pd.DataFrame) -> dict:
    z = f["match_id"].map(eta("model", SEEDS_ALL, TEST)).to_numpy(float)
    P, params = layers(f, z)
    return {"lin_vs_B14": paired(f, P["B14"], P["lin"]),
            "lin_pooled_vs_B14": paired(f, P["B14"], P["lin_pooled"]),
            "q1_vs_B14": paired(f, P["B14"], P["q1"]),
            "lin_vs_B": paired(f, P["B"], P["lin"]),
            "B14_vs_B": paired(f, P["B"], P["B14"]),
            "lin_vs_B14_by": {name: paired(f, P["B14"], P["lin"], m) for name, m in
                              (("atp", (f["tour"] == "atp").to_numpy()), ("wta", (f["tour"] == "wta").to_numpy()),
                               ("2025", (f["season"] == 2025).to_numpy()), ("2026", (f["season"] == 2026).to_numpy()))},
            "parameters": params}


def secondaries(f: pd.DataFrame, K: dict) -> dict:
    out = {}
    z = f["match_id"].map(eta("model", SEEDS_ALL, TEST)).to_numpy(float)
    s = standardise(f, K)
    out["by_subset"] = {name: coef(f, z, s, m) for name, m in
                        (("atp", (f["tour"] == "atp").to_numpy()), ("wta", (f["tour"] == "wta").to_numpy()),
                         ("2025", (f["season"] == 2025).to_numpy()), ("2026", (f["season"] == 2026).to_numpy()))}
    out["price_base"] = coef(f, f["in_odds_logit"].to_numpy(float), s)
    out["weakest_fifth"] = coef(f, z, weakest_fifth(f, K), name="q1", expect="+")
    # Polymarket: matches with both prices, every match with a 24-hour price (debut seasons out)
    pm = (f["all_early"] & np.isfinite(f["p_early_a"]) & np.isfinite(f["p_close_a"])).to_numpy()
    g = f[pm].reset_index(drop=True)
    sg = standardise(g, K)
    z_early = g["match_id"].map(eta("model", SEEDS_ALL, TEST, block="early")).to_numpy(float)
    out["polymarket"] = {"price_24h": coef(g, C.lg(g["p_early_a"].to_numpy(float)), sg),
                         "price_30min": coef(g, C.lg(g["p_close_a"].to_numpy(float)), sg),
                         "model_fed_24h": coef(g, z_early, sg)}
    # H2's secondaries: by subset, encompassing with disjoint seeds, the arm's own H1 coefficient, the 24-hour price
    A = deployed_arms(f)
    out["H2_by_subset"] = {name: paired_test(f, A["model"]["p"], A[ARM]["p"], m) for name, m in
                           (("atp", (f["tour"] == "atp").to_numpy()), ("wta", (f["tour"] == "wta").to_numpy()),
                            ("2025", (f["season"] == 2025).to_numpy()), ("2026", (f["season"] == 2026).to_numpy()))}
    from src.eda.feature_interactions import tabpfn_tests as TT
    base = f["match_id"].map(eta("model", tuple(range(8, 16)), TEST)).to_numpy(float)
    out["H2_encompassing_disjoint_seeds"] = TT.encompassing(f, base, A[ARM]["eta"] - A["model"]["eta"])
    out["arm_H1_coefficient"] = coef(f, A[ARM]["eta"], s)
    out["model_seeds0_7_H1_coefficient"] = coef(f, A["model"]["eta"], s)
    E = deployed_arms(f, block="early")
    out["H2_fed_24h_price"] = paired_test(f, E["model"]["p"], E[ARM]["p"], pm)
    return out


# ------------------------------------------------------------------------------------------------ hashes and the run

def code_hash() -> str:
    files = ["src/eda/pair_strength/final_test.py", "src/eda/pair_strength/common.py",
             "src/eda/feature_interactions/screen.py", "src/eda/feature_interactions/common.py",
             "src/eda/tabpfn_thinking/common.py"]
    h = hashlib.sha256()
    for rel in files:
        h.update(rel.encode())
        h.update(C.sha256_file(ROOT / rel).encode())
    return h.hexdigest()


def forecast_hash() -> str:
    h = hashlib.sha256()
    for folder, arm in ((FC.LOCAL, "model"), (FC.RACE_LOCAL, "model"), (C.LOCAL, ARM)):
        for path in sorted(folder.glob(f"{arm}__*__seed*.npz")):
            h.update(f"{folder.name}/{path.name}".encode())
            h.update(C.sha256_file(path).encode())
    return h.hexdigest()


def reg_line(reg: str, key: str) -> str | None:
    return next((ln.split(":", 1)[1].strip().strip("`") for ln in reg.splitlines() if ln.startswith(f"{key}:")), None)


def check() -> int:
    """Result-free: the population's size and hash, the constants, the forecasts' coverage, every hash."""
    warnings.simplefilter("ignore")
    f = population(with_results=False)
    K = constants()
    z = f["match_id"].map(eta("model", SEEDS_ALL, TEST)).to_numpy(float)
    za = f["match_id"].map(eta(ARM, ARM_SEEDS, TEST)).to_numpy(float)
    pm = (f["all_early"] & np.isfinite(f["p_early_a"]) & np.isfinite(f["p_close_a"])).to_numpy()
    seeds = {s: [k for k in SEEDS_ALL if _load("model", s, k)] for s in range(HIST_FROM, 2027)}
    out = {"population_matches": int(len(f)), "population_sha256": population_hash(f),
           "by_tour": f.groupby("tour").size().to_dict(), "by_season": f.groupby("season").size().to_dict(),
           "blocks": int(f["block"].nunique()), "constants": K, "coverage_elo_sum": float(np.isfinite(f["pr_elo_sum"]).mean()),
           "coverage_model": float(np.isfinite(z).mean()), "coverage_arm": float(np.isfinite(za).mean()),
           "polymarket_rows": int(pm.sum()), "model_seeds_by_season": seeds,
           "arm_seeds_by_season": {s: [k for k in range(8) if _load(ARM, s, k)] for s in range(2014, 2027)},
           "code_sha256": code_hash(), "forecasts_sha256": forecast_hash(),
           **{k.lower(): C.sha256_file(v) for k, v in INPUT_FILES.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "check.json", out)
    C.log(json.dumps(out, default=str)[:1200])
    return 0


def dry_run(seed: int = 7) -> int:
    """The whole run on SYNTHETIC test-season outcomes (drawn from expit(0.9 eta), eta the model's 16-seed forecast),
    real development results: every code path the run takes, with no 2025-2026 result read. Writes dry_run.json."""
    warnings.simplefilter("ignore")
    global frame
    real_frame = frame
    rng = np.random.default_rng(seed)
    z_test = eta("model", SEEDS_ALL, TEST)
    draws: dict[str, bool] = {}

    def synthetic_frame(seasons, with_results: bool, with_players: bool = True) -> pd.DataFrame:
        seasons = list(seasons)
        g = real_frame(seasons, with_results=False, with_players=with_players)
        if not with_results:
            return g
        dev = [s for s in seasons if s not in TEST]
        y = pd.Series(np.nan, index=g.index, dtype=object)
        if dev:
            r = real_frame(dev, with_results=True, with_players=False)[["match_id", "a_won"]].set_index("match_id")
            y = g["match_id"].map(r["a_won"]).astype(object)
        test = g["season"].isin(TEST).to_numpy()
        for mid in g.loc[test, "match_id"]:
            if mid not in draws:
                draws[mid] = bool(rng.random() < expit(0.9 * z_test[mid]))
        y[test] = g.loc[test, "match_id"].map(draws).to_numpy()
        g["a_won"] = y.astype(bool)
        return g

    frame = synthetic_frame
    try:
        K = constants()
        f = population(with_results=True)
        res = {"synthetic": True, "primary": primary(f, K), "effect": effect(f), "secondaries": secondaries(f, K)}
    finally:
        frame = real_frame
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "dry_run.json", res)
    C.log("dry run (synthetic test outcomes) complete: " + json.dumps(res["primary"], default=float)[:900])
    return 0


def run() -> int:
    warnings.simplefilter("ignore")
    reg_path = C.DOCS / "preregistration.md"
    reg = reg_path.read_text(encoding="utf-8")
    for key, path in INPUT_FILES.items():                     # every input checked before any result is loaded
        if reg_line(reg, key) != C.sha256_file(path):
            raise SystemExit(f"{key}: {path.name} differs from the pre-registered file")
    if reg_line(reg, "CODE_SHA256") != code_hash():
        raise SystemExit("the code differs from the pre-registered code")
    if reg_line(reg, "FORECASTS_SHA256") != forecast_hash():
        raise SystemExit("the forecast files differ from the pre-registered ones")
    K = constants()
    if reg_line(reg, "CONSTANTS_JSON") != json.dumps(K, sort_keys=True):
        raise SystemExit("the modulator's constants differ from the pre-registered ones")
    f = population(with_results=True)                         # the results are loaded only now
    if population_hash(f) != reg_line(reg, "POPULATION_SHA256"):
        raise SystemExit("the population differs from the pre-registered one")
    if f["a_won"].isna().any():
        raise SystemExit("missing results in the test population")
    res = {"preregistration_sha256": C.sha256_file(reg_path), "primary": primary(f, K)}
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "final_primary.json", res)             # the primaries on disk before anything else
    C.log(json.dumps(res["primary"], default=float)[:1500])
    for key, fn in (("effect", lambda: effect(f)), ("secondaries", lambda: secondaries(f, K))):
        try:                                                   # a failed secondary never loses the rest
            res[key] = fn()
        except Exception as exc:                               # noqa: BLE001
            res[key] = {"error": repr(exc)}
    res["key"] = ("H1 b: change in the slope on eta per SD of pair strength; negative = flatter for strong pairs; "
                  "one-sided p for b < 0 on t(G - 1). H2 and every gain: mLL per match, positive = the second-named (the "
                  "elosum arm, or as named) has the lower log loss (better); 95% intervals over four-week blocks; "
                  "spanning 0 = tie. Holm over H1 and H2 at one-sided family-wise 5%")
    C.write_json(OUT / "final_results.json", res)
    C.log("written final_results.json")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if "--dry-run" in sys.argv:
        sys.exit(dry_run())
    if "--run" in sys.argv:
        sys.exit(run())
    raise SystemExit("--check, --dry-run or --run")
