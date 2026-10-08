"""The final test (round 5), run ONCE on the frozen 2025-2026 match list after the pre-registration
(docs/studies/feature_interactions/preregistration.md) is hashed. Nothing in this module may be changed after that hash.

The arms (plan.md, "M2: what the rules gave"):
    B   the current best: the 58-input local TabPFN-3.5 ("model"), raw log-odds eta_B; deployed with the decided
        calibration: one slope per tour on eta_B, refitted each season on every earlier out-of-sample season from 2019
    F   the bundle: B plus the nudge layer logit P_F = s_tour eta_B + b x, x = B-INJ's frozen screen column as built
        (clipped at the 99th percentile of |x| on the screen's 2014-2021 rows, divided by its SD there, missing -> 0),
        fitted by maximum likelihood (no intercept; s per tour, b pooled) walk-forward on B's out-of-sample forecasts of
        every season from 2014 to the season before (the seed mean of every seed available in each season)

Primary (plan.md M9, two-sided 95% interval on b as the reading):
    logit P(A wins) = sum_{tour, season} a eta_B[0-7] + sum_tour c eta_B[0-7]^3 + b dev,
    dev = logit P_F[8-15] - logit P_B[8-15], each arm deployed (F with its nudge layer, B with its calibration), from the
    seed means of seeds 8-15, disjoint from the offset's seeds 0-7; the union-clustered variance (four-week blocks and
    shared players, the largest of three), t on G - 1 degrees of freedom (tabpfn_tests.encompassing)
Effect size: F against B deployed, seed means of 0-15, paired log loss in mLL (positive = F better), four-week blocks.
Secondaries (descriptive): each tour and season; the matches neither player of which has a Tennis My Life first-serve
row in his own box-score history of the 104 weeks before (the exposure of round2/feasibility_round2.md section 4);
the Polymarket subset (every match with a price 24 hours before the listed start, debut seasons out, and the clean
event openers): F and B fed that price, each against it, and the move of the price between 24 hours and 30 minutes on
the nudge's term b x (OLS without intercept, four-week clusters); and B-INJ's column deployment (the TabPFN arm binj,
seeds 0-7) against B, each with the decided calibration.

    ./python.sh src/eda/feature_interactions/final_test.py --check     # result-free: population, inputs, hashes
    ./python.sh src/eda/feature_interactions/final_test.py --run       # ONCE, after the pre-registration's hash
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = C.OUT / "final"
X_FILE = OUT / "binj_x.parquet"                 # B-INJ's frozen screen column, 2013-2026 (built by build_x)
TEST = (2025, 2026)
NUDGE_FROM = 2014
SEEDS_ALL = tuple(range(16))
OFFSET, DEVIATION = tuple(range(8)), tuple(range(8, 16))


# ------------------------------------------------------------------------------------------------
# Inputs

def build_x() -> pd.DataFrame:
    """B-INJ's screen column for every model-frame match, 2013-2026, from the frozen builder (no result read); the 2013-
    2024 rows must equal the frozen screen column (checked by g5_build on the deployment columns; here on x)."""
    from src.eda.feature_interactions import screen_batch as B
    from src.eda.feature_interactions.g5_build import spec_of
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    spec = spec_of("B-INJ")
    L = long_table()
    P = panel(max_season=2026).drop(columns=["a_won"])
    r = B.evaluate(spec, P.assign(**spec["prepare"](P, L)))
    out = pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(), "season": P["season"].to_numpy(),
                        "x": np.asarray(r["x"], float)})
    P24 = out[out["season"] <= 2024]
    frozen = pd.read_csv(B.HYP / "hypothesis_table.csv").set_index("hid").loc["B-INJ", "x_sha256"]
    if B.sha_array(P24["x"].to_numpy()) != frozen:
        raise RuntimeError("B-INJ's 2026 build does not reproduce the frozen 2013-2024 screen column")
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(X_FILE, index=False)
    return out


def x_scaled(x: pd.Series) -> pd.Series:
    """The screen's preprocessing of x, constants fixed on the screen's 2014-2021 rows (debut seasons out)."""
    f = S.load(with_model=False)
    disc = f[f["window"] == "discovery"]["match_id"]
    xd = x.reindex(disc).to_numpy(float)
    clip = float(np.nanquantile(np.abs(xd), S.CLIP_Q))
    sd = float(np.nanstd(np.clip(xd, -clip, clip)))
    return (x.clip(-clip, clip) / sd).fillna(0.0)


def population() -> pd.DataFrame:
    f = TT.frame(TEST)
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a", "clean", "all_early"])
    ep["match_id"] = ep["match_id"].astype(str)
    f = f.merge(ep, on="match_id", how="left", validate="one_to_one")
    for c in ("has_early", "clean", "all_early"):
        f[c] = f[c].fillna(False).astype(bool)
    return f


def population_hash(f: pd.DataFrame) -> str:
    return hashlib.sha256("\n".join(sorted(f["match_id"].astype(str))).encode()).hexdigest()


def tml_exposed(match_ids: pd.Series) -> np.ndarray:
    """True where either player has a Tennis My Life men's Grand Slam box-score row dated from 1 Aug 2025 in his own
    history of the 104 weeks up to the match, its own event included (round2/feasibility_round2.md section 4; frozen pre-rebuild Stage 0)."""
    from src.eda.feature_interactions.panel import SOURCES
    m = pd.read_parquet(SOURCES["stage0_matches"], columns=["match_id", "tour", "level", "tournament_date", "source",
                                                             "has_box", "player_a_id", "player_b_id"])
    m["match_id"] = m["match_id"].astype(str)
    d = pd.to_datetime(m["tournament_date"])
    bad = (m["source"].eq("tml") & m["has_box"].fillna(False).astype(bool) & m["tour"].eq("atp") & m["level"].eq("GS")
           & (d >= "2025-08-01"))
    faulty = pd.concat([m.loc[bad, ["player_a_id"]].rename(columns={"player_a_id": "p"}).assign(day=d[bad]),
                        m.loc[bad, ["player_b_id"]].rename(columns={"player_b_id": "p"}).assign(day=d[bad])])
    q = m.set_index("match_id").reindex(match_ids.astype(str))
    qd = pd.to_datetime(q["tournament_date"]).to_numpy()
    out = np.zeros(len(q), bool)
    for side in ("player_a_id", "player_b_id"):
        for p, g in faulty.groupby("p"):
            k = (q[side].to_numpy() == p)
            if k.any():
                days = g["day"].to_numpy()
                for i in np.flatnonzero(k):
                    out[i] |= bool(((days <= qd[i]) & (days >= qd[i] - np.timedelta64(728, "D"))).any())
    return out


# ------------------------------------------------------------------------------------------------
# The arms

def eta(seeds, seasons, block: str = "td") -> pd.Series:
    """Raw log-odds of the base by match id: the seed mean of the given seeds that exist in each season."""
    parts = []
    for s in seasons:
        have = [k for k in seeds if (C.LOCAL / f"model__{s}__seed{k}.npz").exists()
                or (C.RACE_LOCAL / f"model__{s}__seed{k}.npz").exists()]
        parts.append(TT.forecasts("model", have, [s], block=block))
    return pd.Series(C.lg(pd.concat(parts).to_numpy()), index=pd.concat(parts).index)


def history_frame(seasons) -> pd.DataFrame:
    """The base's out-of-sample forecasts and results of earlier seasons (the nudge's and the calibration's data)."""
    f = TT.frame(seasons, with_players=False)
    f["eta"] = f["match_id"].map(eta(SEEDS_ALL, seasons)).to_numpy(float)
    return f


def fit_nudge(h: pd.DataFrame, xs: pd.Series) -> dict:
    """logit P = s_tour eta + b x, maximum likelihood, no intercept."""
    z = h["eta"].to_numpy(float)
    x = h["match_id"].map(xs).to_numpy(float)
    atp = (h["tour"] == "atp").to_numpy()
    Z = np.column_stack([np.where(atp, z, 0.0), np.where(~atp, z, 0.0), x])
    beta, _, _ = S.fit(Z, h["a_won"].to_numpy(float))
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "b": float(beta[2]), "n": int(len(h))}


def fit_slopes(h: pd.DataFrame) -> dict:
    """B14 (checkpoint 2, R-A): logit P = s'_tour eta, fitted exactly like F's nudge (maximum likelihood, no intercept, one
    slope per tour, seasons 2014 to Y - 1, the same seed means) but without x."""
    z = h["eta"].to_numpy(float)
    atp = (h["tour"] == "atp").to_numpy()
    beta, _, _ = S.fit(np.column_stack([np.where(atp, z, 0.0), np.where(~atp, z, 0.0)]), h["a_won"].to_numpy(float))
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "n": int(len(h))}


def fit_calibration(h: pd.DataFrame) -> dict:
    out = {}
    for t in C.TOURS:
        k = (h["tour"] == t).to_numpy() & (h["season"] >= C.CALIB_FROM).to_numpy()
        beta, _ = T.fit_logistic(h.loc[k, ["eta"]].to_numpy(), h.loc[k, "a_won"].to_numpy(float))
        out[t] = float(beta[0])
    return out


def deployed(f: pd.DataFrame, z: np.ndarray, xs: pd.Series, params: dict, b14: bool = False):
    """(logit P_B, logit P_F) for the rows of f with base log-odds z, each season's parameters in params[season]; with
    b14, also logit P_B14 (the nudge's slopes without x)."""
    lb, lf, l14 = np.full(len(f), np.nan), np.full(len(f), np.nan), np.full(len(f), np.nan)
    x = f["match_id"].map(xs).to_numpy(float)
    for s, p in params.items():
        k = (f["season"] == s).to_numpy()
        atp = (f["tour"] == "atp").to_numpy()
        lb[k] = np.where(atp, p["cal"]["atp"], p["cal"]["wta"])[k] * z[k]
        lf[k] = np.where(atp, p["nudge"]["s_atp"], p["nudge"]["s_wta"])[k] * z[k] + p["nudge"]["b"] * x[k]
        l14[k] = np.where(atp, p["b14"]["s_atp"], p["b14"]["s_wta"])[k] * z[k]
    return (lb, lf, l14) if b14 else (lb, lf)


def parameters(xs: pd.Series) -> dict:
    """Per test season: the base's calibration (from 2019) and the nudge (from 2014), on every earlier season."""
    out = {}
    for s in TEST:
        h = history_frame(range(NUDGE_FROM, s))
        out[s] = {"cal": fit_calibration(h), "nudge": fit_nudge(h, xs), "b14": fit_slopes(h),
                  "fitted_on": [NUDGE_FROM, s - 1]}
    return out


# ------------------------------------------------------------------------------------------------
# The test

def primary(f: pd.DataFrame, xs: pd.Series, params: dict) -> dict:
    z0 = f["match_id"].map(eta(OFFSET, TEST)).to_numpy(float)
    z8 = f["match_id"].map(eta(DEVIATION, TEST)).to_numpy(float)
    lb, lf = deployed(f, z8, xs, params)
    return TT.encompassing(f, z0, lf - lb)


def effect(f: pd.DataFrame, xs: pd.Series, params: dict, rows: np.ndarray | None = None) -> dict:
    """Three paired gains (mLL, positive = the second-named better), additive per match: F vs B14 (B-INJ's part; the
    effect size read), B14 vs B (the calibration window's part), F vs B (the deployment gain = the sum)."""
    z = f["match_id"].map(eta(SEEDS_ALL, TEST)).to_numpy(float)
    lb, lf, l14 = deployed(f, z, xs, params, b14=True)
    return {"F_vs_B14": TT.paired_gain(f, expit(l14), expit(lf), rows),
            "B14_vs_B": TT.paired_gain(f, expit(lb), expit(l14), rows),
            "F_vs_B": TT.paired_gain(f, expit(lb), expit(lf), rows)}


def polymarket(f: pd.DataFrame, xs: pd.Series, params: dict) -> list[dict]:
    rows = []
    for pop, mask in (("early_all", f["all_early"].to_numpy()), ("early_clean", f["clean"].to_numpy())):
        g = f[mask & np.isfinite(f["p_early_a"]).to_numpy() & np.isfinite(f["p_close_a"]).to_numpy()]
        g = g.reset_index(drop=True)
        z = g["match_id"].map(eta(SEEDS_ALL, TEST, block="early")).to_numpy(float)
        lb, lf = deployed(g, z, xs, params)
        price = g["p_early_a"].to_numpy(float)
        for name, pa, pb in (("F vs B, both fed the 24-hour price", expit(lb), expit(lf)),
                             ("B vs the 24-hour price", price, expit(lb)), ("F vs the 24-hour price", price, expit(lf))):
            c = TT.paired_gain(g, pa, pb)
            rows.append({"population": pop, "comparison": name, "matches": c["n"], "gain": c["gain"], "lo": c["lo"],
                         "hi": c["hi"]})
        # the move from 24 hours to 30 minutes on the nudge's term
        M = C.lg(g["p_close_a"]) - C.lg(g["p_early_a"])
        x = g["match_id"].map(xs).to_numpy(float)
        bx = np.array([params[s]["nudge"]["b"] for s in g["season"]]) * x
        ok = np.isfinite(M) & np.isfinite(bx)
        from src.eda.surface_elo_pieces.early_price_score import ols_cluster
        r = ols_cluster(M[ok], bx[ok][:, None], T.blocks(g.loc[ok, "tournament_date"].to_numpy(), 28))
        rows.append({"population": pop, "comparison": "move 24 h -> 30 min on b x (slope)", "matches": r["n"],
                     "gain": r["beta"][0], "lo": r["lo"][0], "hi": r["hi"][0]})
    return rows


def eta_arm(arm: str, seeds, seasons, block: str = "td") -> pd.Series:
    """Raw log-odds of an arm by match id: the seed mean of the given seeds that exist in each season."""
    parts = []
    for s in seasons:
        have = [k for k in seeds if (C.LOCAL / f"{arm}__{s}__seed{k}.npz").exists()
                or (arm == "model" and (C.RACE_LOCAL / f"model__{s}__seed{k}.npz").exists())]
        p = TT.forecasts(arm, have, [s], block=block)
        parts.append(pd.Series(C.lg(p.to_numpy()), index=p.index))
    return pd.concat(parts)


def column_arm(f: pd.DataFrame) -> list[dict]:
    """Descriptive secondary: B-INJ's column deployment (the TabPFN arm `binj`, the 58 inputs plus its three frozen
    columns, seeds 0-7) against B (seeds 0-7), each deployed with the decided calibration: one slope per tour fitted on
    the arm's own out-of-sample forecasts of every earlier season from 2019 (binj: seeds 0-2 in 2019-2024, 0-7 in 2025)."""
    cal = {}
    for arm in ("binj", "model"):
        z = f["match_id"].map(eta_arm(arm, range(8), TEST)).to_numpy(float)
        p = np.full(len(f), np.nan)
        for s in TEST:
            h = TT.frame(range(C.CALIB_FROM, s), with_players=False)
            h["eta"] = h["match_id"].map(eta_arm(arm, range(16), range(C.CALIB_FROM, s))).to_numpy(float)
            sl = fit_calibration(h)
            k = (f["season"] == s).to_numpy()
            atp = (f["tour"] == "atp").to_numpy()
            p[k] = expit(np.where(atp, sl["atp"], sl["wta"])[k] * z[k])
        cal[arm] = p
    rows = []
    for name, mask in (("both", np.ones(len(f), bool)), ("atp", (f["tour"] == "atp").to_numpy()),
                       ("wta", (f["tour"] == "wta").to_numpy())):
        c = TT.paired_gain(f, cal["model"], cal["binj"], mask)
        rows.append({"tour": name, "comparison": "column arm binj vs B (seeds 0-7 each, decided calibration)",
                     "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"]})
    return rows


INPUT_FILES = {"MODEL_FRAME_SHA256": C.MODEL_FRAME, "STAGE0_MATCHES_SHA256": S.PRE_REBUILD_STAGE0}


def reg_line(reg: str, key: str) -> str | None:
    return next((ln.split(":", 1)[1].strip() for ln in reg.splitlines() if ln.startswith(f"{key}:")), None)


def run() -> int:
    warnings.simplefilter("ignore")
    reg_path = C.DOCS / "preregistration.md"
    reg = reg_path.read_text(encoding="utf-8")
    for key, path in INPUT_FILES.items():                       # every input checked before any result is loaded
        if reg_line(reg, key) != C.sha256_file(path):
            raise SystemExit(f"{key}: {path.name} differs from the pre-registered file")
    for key, path in (("BINJ_X_SHA256", X_FILE), ("EARLY_SHA256", C.EARLY)):
        want_k = next((ln.split(":", 1)[1].strip() for ln in reg.splitlines() if ln.startswith(f"{key}:")), None)
        if want_k != C.sha256_file(path):
            raise SystemExit(f"{key}: {path.name} differs from the pre-registered file")
    code = next((ln.split(":", 1)[1].strip() for ln in reg.splitlines() if ln.startswith("FINAL_TEST_CODE_SHA256:")), None)
    if code != code_hash():
        raise SystemExit("the final test's code differs from the pre-registered code")
    fc = next((ln.split(":", 1)[1].strip() for ln in reg.splitlines() if ln.startswith("FORECASTS_SHA256:")), None)
    if fc != forecast_hash():
        raise SystemExit("the forecast files differ from the pre-registered ones")
    f = population()                                            # the results are loaded only now
    if population_hash(f) != reg_line(reg, "POPULATION_SHA256"):
        raise SystemExit("the population differs from the pre-registered one")
    if f["a_won"].isna().any():
        raise SystemExit("missing results in the test population")
    x = pd.read_parquet(X_FILE).set_index("match_id")["x"]
    xs = x_scaled(x)
    params = parameters(xs)
    res = {"preregistration_sha256": C.sha256_file(reg_path), "primary": primary(f, xs, params),
           "effect": effect(f, xs, params), "parameters": params}
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "final_primary.json", res)                  # the primary on disk before any secondary
    C.log(json.dumps({"primary": res["primary"], "effect": res["effect"]}, default=float)[:600])
    sub = []
    masks = {"atp": lambda: (f["tour"] == "atp").to_numpy(), "wta": lambda: (f["tour"] == "wta").to_numpy(),
             "2025": lambda: (f["season"] == 2025).to_numpy(), "2026": lambda: (f["season"] == 2026).to_numpy(),
             "TML-clean": lambda: ~tml_exposed(f["match_id"])}
    for name, mask_fn in masks.items():
        try:                                                         # a failed secondary never loses the rest
            g = f[mask_fn()].reset_index(drop=True)
            sub.append({"subset": name, "matches": int(len(g)), "primary": primary(g, xs, params),
                        "effect": effect(g, xs, params)})
        except Exception as exc:
            sub.append({"subset": name, "error": repr(exc)})
    res["subsets"] = sub
    for key, fn in (("polymarket", lambda: polymarket(f, xs, params)), ("column_arm", lambda: column_arm(f))):
        try:
            res[key] = fn()
        except Exception as exc:
            res[key] = {"error": repr(exc)}
    res["key"] = ("b: coefficient of the bundle's deviation (positive = the bundle adds information; the two-sided 95% "
                  "interval is the reading); gains in mLL, positive = the bundle has the lower log loss (better); "
                  "intervals over four-week blocks; spanning 0 = tie")
    C.write_json(OUT / "final_results.json", res)
    C.log(json.dumps({"primary": res["primary"], "effect": res["effect"]}, default=float)[:600])
    return 0


def forecast_hash() -> str:
    """SHA-256 over every forecast file the run can read: arms `model` and `binj`, this study's folder and the race's."""
    h = hashlib.sha256()
    for folder in (C.LOCAL, C.RACE_LOCAL):
        for arm in ("model", "binj"):
            for path in sorted(folder.glob(f"{arm}__*__seed*.npz")):
                h.update(path.name.encode())
                h.update(C.sha256_file(path).encode())
    return h.hexdigest()


def code_hash() -> str:
    """SHA-256 over the code the run executes: this module and the harness modules it imports."""
    files = ["final_test.py", "tabpfn_tests.py", "screen.py", "common.py", "panel.py", "history.py", "g5_build.py",
             "screen_batch.py"]
    h = hashlib.sha256()
    for name in files:
        h.update(name.encode())
        h.update(C.sha256_file(ROOT / "src" / "eda" / "feature_interactions" / name).encode())
    for rel in ("src/eda/tabpfn_thinking/common.py", "src/eda/surface_elo_pieces/early_price_score.py"):
        h.update(rel.encode())                                  # imported from other studies (checkpoint 2, R-B)
        h.update(C.sha256_file(ROOT / rel).encode())
    return h.hexdigest()


def check() -> int:
    """Result-free: the population's count and hash, the x file, the parameters' availability (no result read)."""
    warnings.simplefilter("ignore")
    f = population().drop(columns=["a_won"])
    x = build_x() if not X_FILE.exists() else pd.read_parquet(X_FILE)
    xs = x_scaled(x.set_index("match_id")["x"])
    cover = float(np.isfinite(f["match_id"].map(xs).to_numpy(float)).mean())
    seeds = {s: [k for k in SEEDS_ALL if (C.LOCAL / f"model__{s}__seed{k}.npz").exists()
                 or (C.RACE_LOCAL / f"model__{s}__seed{k}.npz").exists()] for s in range(NUDGE_FROM, 2027)}
    out = {"population_matches": int(len(f)), "population_sha256": population_hash(f),
           "by_tour": f.groupby("tour").size().to_dict(), "by_season": f.groupby("season").size().to_dict(),
           "x_file_sha256": C.sha256_file(X_FILE), "x_coverage_test": cover,
           "x_nonzero_test": float((f["match_id"].map(xs).to_numpy(float) != 0).mean()),
           "seeds_by_season": seeds, "polymarket_early_all": int(f["all_early"].sum()),
           "polymarket_clean": int(f["clean"].sum()), "tml_exposed": int(tml_exposed(f["match_id"]).sum()),
           "early_sha256": C.sha256_file(C.EARLY), "code_sha256": code_hash(), "forecasts_sha256": forecast_hash(),
           **{k.lower(): C.sha256_file(v) for k, v in INPUT_FILES.items()}}
    C.write_json(OUT / "check.json", out)
    C.log(json.dumps(out, default=str)[:900])
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if "--run" in sys.argv:
        sys.exit(run())
    raise SystemExit("--check or --run")
