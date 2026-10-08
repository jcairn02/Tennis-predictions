"""Round 0, brainstormer MECHANICS: how large are the candidate matchup terms, before any outcome is looked at?

Descriptive only. Reads pre-match IOS ratings (A and B separately) and box-score statistics of matches up to 2021.
It never reads a result (a_won, won), a price (p_mkt, odds) or anything from 2022 on. For each candidate term it
reports its spread and how much of it is a linear function of the model's 21 IOS profile inputs (7 offence
differences, 7 defence differences, 7 matchup products), i.e. what the model could not already form linearly.

    1. serve dominance of the matchup (a symmetric match character) and the iid leverage it implies
    2. the first/second-serve composition of A's serve point against B's return (C / X)
    3. the free-point shield: aces are out of the returner's reach, so a big server is less exposed to return skill
    4. cross-statistic bilinear terms (A's offence on s x B's defence on t), s != t
    5. handedness counts
    6. venue pace: is a venue's ace residual, adjusted for who served and who returned, persistent across editions?

Run: ./python.sh src/eda/feature_interactions/round0/mechanics/feature_spread.py
Writes data/studies/feature_interactions/round0/mechanics/feature_spread.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "feature_interactions" / "round0" / "mechanics"
MF = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
SF = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
CONST = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
S0M = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
S0P = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"
LEV = OUT / "iid_mechanics.json"

STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"]   # the model's IOS profile
SURF = {0.0: "Hard", 1.0: "Clay", 2.0: "Grass"}
LAST = 2021                                         # nothing after the discovery window is read


def logit(p):
    p = np.asarray(p, dtype="float64")
    return np.log(p / (1 - p))


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype="float64")))


def load() -> pd.DataFrame:
    mf = pd.read_parquet(MF, columns=["match_id", "tour", "season", "in_surface", "in_best_of", "in_level", "in_indoor"])
    mf = mf[(mf["season"] <= LAST) & mf["in_surface"].isin(list(SURF))].copy()
    mf["surface"] = mf["in_surface"].map(SURF)
    cols = ["match_id"] + [f"srf_{k}_eff_{s}_{x}" for s in STATS + ["spw"] for k in ("O", "D") for x in ("a", "b")]
    sf = pd.read_parquet(SF, columns=cols)
    df = mf.merge(sf, on="match_id", how="left")
    c = pd.read_csv(CONST)
    c = c[c["kind"].eq("surface average") & c["surface"].isin(["Hard", "Clay", "Grass"])]
    mu = c.pivot_table(index=["tour", "surface"], columns="stat", values="value").reset_index()
    keep = ["tour", "surface"] + STATS + ["spw"]
    mu = mu[keep].rename(columns={s: f"mu_{s}" for s in STATS + ["spw"]})
    df = df.merge(mu, on=["tour", "surface"], how="left")
    return df


def ols_resid(y: np.ndarray, X: np.ndarray):
    """R^2 and residual SD of y on X (with intercept)."""
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    r = y - X1 @ beta
    return float(1 - r.var() / y.var()), float(r.std()), float(y.std()), int(ok.sum())


def model_ios_matrix(df: pd.DataFrame) -> np.ndarray:
    """The model's 21 IOS profile inputs, rebuilt from the per-player values: O_A - O_B, D_A - D_B, and
    prod = O_A * (-D_B) - O_B * (-D_A), for the seven statistics."""
    cols = []
    for s in STATS:
        oa, ob = df[f"srf_O_eff_{s}_a"].to_numpy(), df[f"srf_O_eff_{s}_b"].to_numpy()
        da, db = df[f"srf_D_eff_{s}_a"].to_numpy(), df[f"srf_D_eff_{s}_b"].to_numpy()
        cols += [oa - ob, da - db, oa * (-db) - ob * (-da)]
    return np.column_stack(cols)


def pred(df, s, srv, ret):
    """Expected rate of statistic s for server srv ('a' or 'b') against returner ret: expit(mu + O - D)."""
    return pd.Series(sig(logit(df[f"mu_{s}"]) + df[f"srf_O_eff_{s}_{srv}"] - df[f"srf_D_eff_{s}_{ret}"]), index=df.index)


def leverage_ratio(pbar: np.ndarray) -> np.ndarray:
    lev = json.loads(LEV.read_text())["leverage"]
    grid = np.array(lev["pbar"])
    rel = np.array(lev["formats"]["bo3"]["leverage_relative_to_pbar_0.62"])
    return np.interp(pbar, grid, rel)


def part_dominance(df: pd.DataFrame) -> dict:
    m = logit(df["mu_spw"]) + (df["srf_O_eff_spw_a"] + df["srf_O_eff_spw_b"]
                               - df["srf_D_eff_spw_a"] - df["srf_D_eff_spw_b"]) / 2
    m = pd.Series(np.asarray(m), index=df.index)
    pbar = pd.Series(sig(m), index=df.index)
    lr = leverage_ratio(pbar.to_numpy())
    d = df.assign(m=m, pbar=pbar, lev=lr)
    out = {"overall": {}, "by_tour_surface": {}}
    for t, g in d.groupby("tour"):
        out["overall"][t] = {"n": int(len(g)), "sd_m": round(float(g["m"].std()), 4),
                             "pbar_p05_p50_p95": [round(float(x), 4) for x in g["pbar"].quantile([.05, .5, .95])],
                             "lev_p05_p50_p95": [round(float(x), 3) for x in g["lev"].quantile([.05, .5, .95])]}
    for (t, s), g in d.groupby(["tour", "surface"]):
        out["by_tour_surface"][f"{t}_{s}"] = {
            "n": int(len(g)), "sd_m_within": round(float(g["m"].std()), 4),
            "pbar_p05_p50_p95": [round(float(x), 4) for x in g["pbar"].quantile([.05, .5, .95])],
            "lev_p05_p50_p95": [round(float(x), 3) for x in g["lev"].quantile([.05, .5, .95])],
            "lev_sd": round(float(g["lev"].std()), 4)}
    # share of the variance of m that tour x surface x indoor explains (the context columns' reach)
    key = d["tour"] + "_" + d["surface"] + "_" + d["in_indoor"].fillna(-1).astype(str)
    within = d["m"] - d.groupby(key)["m"].transform("mean")
    out["share_of_var_m_explained_by_tour_surface_indoor"] = round(float(1 - within.var() / d["m"].var()), 4)
    # hold-based dominance: the sum of the two expected hold rates
    ha, hb = pred(df, "hold", "a", "b"), pred(df, "hold", "b", "a")
    out["sum_expected_holds_p05_p50_p95"] = {t: [round(float(x), 4) for x in (ha + hb)[df["tour"].eq(t)].quantile([.05, .5, .95])]
                                            for t in ("atp", "wta")}
    return out


def part_composition(df: pd.DataFrame, X: np.ndarray) -> dict:
    out = {}
    for t in ("atp", "wta"):
        g = df[df["tour"].eq(t)]
        Xg = X[df["tour"].eq(t).to_numpy()]

        def comp(srv, ret):
            fi = pred(g, "first_in", srv, ret)
            fw = pred(g, "first_won", srv, ret)
            sw = pred(g, "second_won", srv, ret)
            return fi * fw + (1 - fi) * sw

        ca, cb = comp("a", "b"), comp("b", "a")
        y = np.asarray(logit(ca) - logit(cb))
        r2, rsd, ysd, n = ols_resid(y, Xg)
        # the first-in exposure cross term alone: (1 - fi_A) x B's second-serve return minus the reverse,
        # and fi_A x B's first-serve return minus the reverse, with fi from A's own first-in offence
        fia = pred(g, "first_in", "a", "b")
        fib = pred(g, "first_in", "b", "a")
        x2 = ((1 - fia) * g["srf_D_eff_second_won_b"] - (1 - fib) * g["srf_D_eff_second_won_a"]).to_numpy()
        x1 = (fia * g["srf_D_eff_first_won_b"] - fib * g["srf_D_eff_first_won_a"]).to_numpy()
        xr2 = ols_resid(x2, Xg)
        xr1 = ols_resid(x1, Xg)
        out[t] = {"n": n, "composed_edge_logit_sd": round(ysd, 4), "r2_on_model_ios_21": round(r2, 4),
                  "residual_sd_spw_logit": round(rsd, 5), "residual_sd_match_logit_bo3_approx": round(rsd * 4.8, 4),
                  "second_exposure_term_sd": round(xr2[2], 4), "second_exposure_r2_on_model": round(xr2[0], 4),
                  "first_exposure_term_sd": round(xr1[2], 4), "first_exposure_r2_on_model": round(xr1[0], 4)}
    return out


def part_free_points(df: pd.DataFrame, X: np.ndarray) -> dict:
    """Free-point shield: aces (box score) are points the returner cannot touch. A's serve point against B:
    p = a + (1 - a) r, a = expected ace rate (IOS aces), r the rest. Calibrated so that against an average returner it
    equals the additive IOS serve-point rate and that the average elasticity to the returner's rating is 1. The term
    is the structural minus the additive serve-point log-odds, A minus B."""
    out = {}
    for t in ("atp", "wta"):
        g = df[df["tour"].eq(t)]
        Xg = X[df["tour"].eq(t).to_numpy()]
        abar = g["mu_ace"].to_numpy()
        pbar = g["mu_spw"].to_numpy()
        rbar = (pbar - abar) / (1 - abar)
        k = pbar * (1 - pbar) / ((1 - abar) * rbar * (1 - rbar))

        def corr(srv, ret):
            a0 = np.asarray(sig(logit(g["mu_ace"]) + g[f"srf_O_eff_ace_{srv}"]))      # against an average returner
            a = pred(g, "ace", srv, ret).to_numpy()
            p0 = np.asarray(sig(logit(g["mu_spw"]) + g[f"srf_O_eff_spw_{srv}"]))
            r0 = np.clip((p0 - a0) / (1 - a0), 1e-4, 1 - 1e-4)
            dret = g[f"srf_D_eff_spw_{ret}"].to_numpy() - 0.0
            r = sig(logit(r0) - k * dret)
            p_struct = a + (1 - a) * r
            p_add = pred(g, "spw", srv, ret).to_numpy()
            return logit(p_struct) - logit(p_add)

        y = corr("a", "b") - corr("b", "a")
        r2, rsd, ysd, n = ols_resid(y, Xg)
        out[t] = {"n": n, "term_sd_spw_logit": round(ysd, 5), "r2_on_model_ios_21": round(r2, 4),
                  "residual_sd_spw_logit": round(rsd, 5), "residual_sd_match_logit_bo3_approx": round(rsd * 4.8, 4),
                  "term_p01_p99": [round(float(x), 4) for x in np.nanquantile(y, [.01, .99])]}
    return out


def part_cross(df: pd.DataFrame, X: np.ndarray) -> dict:
    pairs = [("first_in", "second_won"), ("ace", "first_won"), ("df", "second_won"), ("first_won", "second_won"),
             ("second_won", "first_won"), ("ace", "hold"), ("first_in", "first_won")]
    out = {}
    for t in ("atp", "wta"):
        g = df[df["tour"].eq(t)]
        Xg = X[df["tour"].eq(t).to_numpy()]
        rows = {}
        for s, u in pairs:
            x = (g[f"srf_O_eff_{s}_a"] * (-g[f"srf_D_eff_{u}_b"]) - g[f"srf_O_eff_{s}_b"] * (-g[f"srf_D_eff_{u}_a"])).to_numpy()
            r2, rsd, ysd, n = ols_resid(x, Xg)
            rows[f"O_{s} x D_{u}"] = {"sd": round(ysd, 4), "r2_on_model_ios_21": round(r2, 4)}
        out[t] = rows
    return out


def part_hand(df: pd.DataFrame) -> dict:
    p = pd.read_parquet(S0P, columns=["match_id", "player_id", "side", "hand", "height"])
    p = p[p["match_id"].isin(df["match_id"])]
    side_counts = p["side"].value_counts().to_dict()
    w = p.pivot_table(index="match_id", columns="side", values="hand", aggfunc="first")
    w = w.reindex(df["match_id"]).reset_index()
    w = w.merge(df[["match_id", "tour"]], on="match_id", how="left")
    a, b = w.columns[1], w.columns[2]
    out = {"sides": {str(k): int(v) for k, v in side_counts.items()}}
    for t, g in w.groupby("tour"):
        ha, hb = g[a].astype(str), g[b].astype(str)
        known = ha.isin(["R", "L"]) & hb.isin(["R", "L"])
        lr = ((ha == "L") ^ (hb == "L")) & known
        ll = (ha == "L") & (hb == "L")
        out[t] = {"matches": int(len(g)), "hand_known_both": int(known.sum()), "lefty_vs_righty": int(lr.sum()),
                  "lefty_vs_lefty": int(ll.sum()), "share_lr": round(float(lr.sum() / max(known.sum(), 1)), 4),
                  "share_ll": round(float(ll.sum() / max(known.sum(), 1)), 4)}
    hp = p.dropna(subset=["height"])
    out["height_rows"] = int(len(hp))
    return out


def part_venue(df: pd.DataFrame) -> dict:
    """Venue ace residual, adjusted for both players: observed aces minus the IOS expectation, summed over a venue's
    edition (main tour, matches of the model frame up to 2021), on the log-odds scale; its correlation between
    consecutive editions of the same venue (tournament id without the year)."""
    p = pd.read_parquet(S0P, columns=["match_id", "side", "ace", "svpt", "first_won", "second_won"])
    p = p[p["match_id"].isin(df["match_id"])].copy()
    p["spw"] = p["first_won"] + p["second_won"]
    sides = sorted(p["side"].dropna().unique().tolist())
    wa = p[p["side"].eq(sides[0])].set_index("match_id")[["ace", "svpt", "spw"]].add_suffix("_a")
    wb = p[p["side"].eq(sides[1])].set_index("match_id")[["ace", "svpt", "spw"]].add_suffix("_b")
    m0 = pd.read_parquet(S0M, columns=["match_id", "tournament_id", "year", "player_a_id"])
    d = df.merge(m0, on="match_id", how="left").join(wa, on="match_id").join(wb, on="match_id")
    d = d.dropna(subset=["ace_a", "svpt_a", "ace_b", "svpt_b", "spw_a", "spw_b", "tournament_id"])
    d = d[(d["svpt_a"] > 0) & (d["svpt_b"] > 0)]
    ea = pred(d, "ace", "a", "b") * d["svpt_a"]
    eb = pred(d, "ace", "b", "a") * d["svpt_b"]
    sa = pred(d, "spw", "a", "b") * d["svpt_a"]
    sb = pred(d, "spw", "b", "a") * d["svpt_b"]
    d = d.assign(obs=d["ace_a"] + d["ace_b"], exp=ea + eb, pts=d["svpt_a"] + d["svpt_b"],
                 sobs=d["spw_a"] + d["spw_b"], sexp=sa + sb)
    d["venue"] = d["tournament_id"].astype(str).str.split("-", n=1).str[1]
    ed = d.groupby(["tour", "venue", "season", "surface"], as_index=False).agg(
        obs=("obs", "sum"), exp=("exp", "sum"), pts=("pts", "sum"), sobs=("sobs", "sum"), sexp=("sexp", "sum"),
        n=("obs", "size"))
    ed = ed[ed["n"] >= 15]
    ed["res"] = logit(ed["obs"] / ed["pts"]) - logit(ed["exp"] / ed["pts"])
    ed["sres"] = logit(ed["sobs"] / ed["pts"]) - logit(ed["sexp"] / ed["pts"])
    ed = ed.sort_values(["tour", "venue", "season"])
    out = {}
    for t, g in ed.groupby("tour"):
        g = g.copy()
        for c in ("res", "sres"):
            g[f"prev_{c}"] = g.groupby(["venue", "surface"])[c].shift(1)
        g["prev_season"] = g.groupby(["venue", "surface"])["season"].shift(1)
        h = g[(g["season"] - g["prev_season"]).isin([1, 2])].dropna(subset=["prev_res", "prev_sres"])
        out[t] = {"editions": int(len(g)), "venues": int(g["venue"].nunique()),
                  "ace_sd_edition_residual": round(float(g["res"].std()), 4),
                  "consecutive_pairs": int(len(h)),
                  "ace_corr_with_previous_edition": round(float(np.corrcoef(h["res"], h["prev_res"])[0, 1]), 4),
                  "ace_sd_by_surface": {s: round(float(x), 4) for s, x in g.groupby("surface")["res"].std().items()},
                  "spw_sd_edition_residual": round(float(g["sres"].std()), 4),
                  "spw_corr_with_previous_edition": round(float(np.corrcoef(h["sres"], h["prev_sres"])[0, 1]), 4),
                  "spw_sd_by_surface": {s: round(float(x), 4) for s, x in g.groupby("surface")["sres"].std().items()},
                  "corr_ace_res_spw_res": round(float(np.corrcoef(g["res"], g["sres"])[0, 1]), 4)}
    return out


def part_bound(df: pd.DataFrame) -> dict:
    """Upper bound on MEC-01's gain: if a forecast's log-odds r were wrong by r * (lambda_rel - 1), with lambda_rel the
    within-cell (tour x surface x indoor) leverage ratio, the correct rescaling would gain 0.5 E[p(1-p) d^2]. The price is
    not read: r is the model input ratings_iid (a strength log-odds through the iid model), a stand-in whose spread
    is wider than a price's, so the bound is generous."""
    mf = pd.read_parquet(MF, columns=["match_id", "in_ratings_iid"])
    d = df.merge(mf, on="match_id", how="left")
    m = logit(d["mu_spw"]) + (d["srf_O_eff_spw_a"] + d["srf_O_eff_spw_b"] - d["srf_D_eff_spw_a"] - d["srf_D_eff_spw_b"]) / 2
    d["lam"] = leverage_ratio(sig(np.asarray(m)))
    key = d["tour"] + "_" + d["surface"] + "_" + d["in_indoor"].fillna(-1).astype(str)
    d["lam_rel"] = d["lam"] / d.groupby(key)["lam"].transform("mean")
    out = {}
    for t, g in d.groupby("tour"):
        r = g["in_ratings_iid"].to_numpy()
        p = sig(r)
        dev = r * (g["lam_rel"].to_numpy() - 1)
        out[t] = {"sd_strength_logodds_proxy": round(float(np.std(r)), 3),
                  "sd_lam_rel_within_cell": round(float(g["lam_rel"].std()), 4),
                  "upper_bound_mLL_price_ignores_within_cell_dominance": round(float(0.5 * np.mean(p * (1 - p) * dev ** 2)) * 1000, 3),
                  "upper_bound_mLL_price_holds_half": round(float(0.5 * np.mean(p * (1 - p) * (0.5 * dev) ** 2)) * 1000, 3)}
    return out


def main():
    df = load()
    X = model_ios_matrix(df)
    res = {"note": "descriptive: pre-match features and box-score statistics of seasons <= 2021; no result or price read",
           "matches": int(len(df)),
           "dominance": part_dominance(df),
           "composition": part_composition(df, X),
           "free_points": part_free_points(df, X),
           "cross_statistic": part_cross(df, X),
           "hand": part_hand(df),
           "venue": part_venue(df),
           "mec01_bound": part_bound(df)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "feature_spread.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
