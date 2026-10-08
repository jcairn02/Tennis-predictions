"""Stage 3, part 4: would the pipeline see an edge if there were one? A planted-signal test.

Stage 2 found no gain on the closing odds. That is informative only if the features could have shown a gain of the
size that matters. Here a gain of known size is planted, and the pipeline is asked to find it:

    1. For a statistic, each player's "true" value, known to nobody before the match: their rate over their whole career
       (every match carrying the statistic, before and after), or over the same calendar season. Shrunk with Stage 2's
       K and put on the features' scale (log-odds; speeds as they are), A - B, less the part the closing odds already
       price (the residual of a least-squares fit on their log-odds), standardised.
    2. Synthetic results on the matches with odds where the Stage 2 feature exists (the harness's rows: the 2011-2012
       matches with odds train, as there): A wins with probability expit(logit(closing odds) + beta x true), beta set
       so that knowing the truth is worth G milli-log-loss over the odds (G = beta^2 v / 2, v the average of
       p (1 - p)): G = 0 (no edge), 0.25, 0.5, 1 and 2, each with 10 random draws.
    3. The earlier studies' walk-forward fit (stage4_rundown.walk), given the odds, scores (a) the truth itself, the
       oracle, and (b) the actual pre-match feature of Stage 2, on the same synthetic results and the evaluation
       matches. Recovery is (b) over (a); detection is how often a 95% interval lies above zero (Stage 2's own bar, the
       shuffled-copy line, is higher).

Recovery should be close to the squared partial correlation of feature and truth given the odds, which is reported
beside it. The depth table gives that correlation by how much shot data the two players had in the feature's memory
(the smaller of the two denominators): what more data per player would buy. A profile is planted too: the truth is the
equal-weight sum of the core statistics' true values, and the 10-input core profile has to find it, with the harness's
fit and with the ridge-penalised walk of stage3_profiles.py.

The features' denominators are rebuilt with Stage 2's code (stage2_features.build), and the rebuilt A - B values are
checked against stage2_features.parquet. The real results are never read: every outcome here is synthetic.

Run:  ./python.sh src/eda/shot_level/stage3_planted.py   (about ten minutes)
Writes data/studies/shot_level/stage3_planted.csv (one row per statistic, truth, gain and tour),
stage3_planted_depth.csv (partial correlation by depth) and stage3_planted.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stage2_features as F  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402
from src.eda.shot_level.stage3_profiles import ridge_walk  # noqa: E402

GAINS = (0.0, 0.25, 0.5, 1.0, 2.0)
DRAWS = 10
SEED = 20261002
SINGLES = [("srv_quick", "w52"), ("ret_quick", "w52"), ("rally9", "w52"), ("winner_rate", "w52"), ("error_rate", "w52"),
           ("spd1", "w52"), ("net_won", "w52"), ("consolidate", "w52"), ("winner_rate", "dec2"), ("spd1", "dec2")]
CORE = ["srv_quick", "ret_quick", "rally5", "rally9", "ret_inplay", "winner_rate", "error_rate", "ue_share", "net_rate",
        "net_won"]
DEPTH_BINS = 4


def truths(stat: str, K: dict, st: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Each player's true value of a statistic: career (index player_id) and season (index (player_id, year)), on the
    features' scale, shrunk with the statistic's K toward the tour's average. st: Stage 1 rows with player_id, tour and
    year joined."""
    x = st[st[f"{stat}_d"] > 0]
    out = []
    for keys in (["player_id"], ["player_id", "year"]):
        g = x.groupby(keys + ["tour"])[[f"{stat}_n", f"{stat}_d"]].sum().reset_index()
        vals = []
        for t in C.TOURS:
            h = g[g["tour"] == t]
            k = K[f"{stat}|{t}|off"]
            assert np.isfinite(k), (stat, t)
            mu = h[f"{stat}_n"].sum() / h[f"{stat}_d"].sum()
            r = ((h[f"{stat}_n"] + k * mu) / (h[f"{stat}_d"] + k)).to_numpy()
            v = r if stat in T.LEVEL else logit(np.clip(r, 1e-4, 1 - 1e-4))
            idx = pd.MultiIndex.from_frame(h[keys]) if len(keys) > 1 else pd.Index(h["player_id"])
            vals.append(pd.Series(v, index=idx))
        s = pd.concat(vals)
        out.append(s[~s.index.duplicated(keep=False)])
    return out[0], out[1]


def residual(v: np.ndarray, lb: np.ndarray) -> np.ndarray:
    """v (n,) or (n, q) less its least-squares fit on lb, without an intercept (both are A - B quantities)."""
    v2 = v if v.ndim == 2 else v[:, None]
    out = v2 - lb[:, None] * ((lb @ v2) / (lb @ lb))[None, :]
    return out if v.ndim == 2 else out[:, 0]


def partial_corr(X: np.ndarray, truth: np.ndarray, lb: np.ndarray) -> float:
    """The correlation of the truth with its best linear prediction from the inputs, both net of the odds' log-odds."""
    Xr, tr = residual(X, lb), residual(truth, lb)
    fit = Xr @ np.linalg.lstsq(Xr, tr, rcond=None)[0]
    return float(np.corrcoef(fit, tr)[0, 1])


def score(Z_feat: np.ndarray, y: np.ndarray, year: np.ndarray, lb: np.ndarray, ev: np.ndarray,
          method: str = "harness") -> tuple[float, float]:
    """The walk-forward gain (milli-log-loss) of the inputs over the recalibrated odds on the evaluation matches, and its
    standard error (independent matches: the synthetic results are drawn independently). 'harness': the earlier
    studies' unpenalised walk, seasons 2013-2026; 'ridge': stage3_profiles.ridge_walk."""
    if method == "ridge":
        w = ridge_walk(Z_feat, lb, y, year, list(range(int(year.min()) + 1, C.EVAL_YEARS[-1] + 1)))
        d = w["llb"] - w["llm"]
    else:
        sd = Z_feat.std(axis=0)
        sd[sd == 0] = 1.0
        Z = np.concatenate([lb[:, None], Z_feat / sd], axis=1)[None]
        w = R.walk(np.ascontiguousarray(Z), y, year, list(C.EVAL_YEARS), lb)
        d = (w["llb"][None, :] - w["llm"])[0]
    d = d[np.isfinite(d) & ev]
    return 1000 * d.mean(), 1000 * d.std(ddof=1) / np.sqrt(len(d))


def depths(cols: list[str], stats: list[str], K: dict, pool: pd.DataFrame) -> dict:
    """Per pool match, the smaller of the two players' denominators in each feature's memory, from Stage 2's own
    builder; the rebuilt A - B values must equal the stored features."""
    rows = F.load_rows()
    Kt = {tuple(k.split("|")): v for k, v in K.items()}
    vals, dens = F.build(rows, F.averages(rows), Kt, stats=stats)
    pos = pd.Series(np.arange(len(rows)), index=pd.MultiIndex.from_arrays([rows["match_id"], rows["side"]]))
    ia = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "A")])).to_numpy().astype(int)
    ib = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "B")])).to_numpy().astype(int)
    out = {}
    for c in cols:
        ok = (dens[c][ia] > 0) & (dens[c][ib] > 0)
        rebuilt = np.where(ok, vals[c][ia] - vals[c][ib], np.nan)
        stored = pool[c].to_numpy(dtype="float64")
        assert (np.isfinite(rebuilt) == np.isfinite(stored)).all(), c
        assert np.nanmax(np.abs(rebuilt - stored)) < 1e-3, c
        out[c] = np.minimum(dens[c][ia], dens[c][ib])
    return out


def main() -> int:
    K = json.loads((S.OUT / "stage2_constants.json").read_text(encoding="utf-8"))["K"]
    needed = sorted({s for s, _ in SINGLES} | set(CORE))
    cols = sorted({f"{s}|off|{f}" for s, f in SINGLES} | {f"{s}|off|w52" for s in CORE})
    feats = pd.read_parquet(S.OUT / "stage2_features.parquet",
                            columns=["match_id", "tour", "year", "evaluation", "p_mkt"] + cols)
    sp = C.load_match_players(["match_id", "player_id", "side"], match_columns=["tour", "year"])
    sp = sp[["match_id", "side", "player_id", "tour", "year"]]
    ids = sp.pivot(index="match_id", columns="side", values="player_id")
    feats["pa"] = ids["A"].reindex(feats["match_id"]).to_numpy()
    feats["pb"] = ids["B"].reindex(feats["match_id"]).to_numpy()
    st = pd.read_parquet(S.OUT / "stage1_match_stats.parquet",
                         columns=["match_id", "side"] + [f"{s}_{k}" for s in needed for k in "nd"])
    st = st.merge(sp, on=["match_id", "side"], how="inner", validate="one_to_one")
    S.log(f"{len(st)} player-matches with shot statistics; true values of {len(needed)} statistics")
    true_vals = {s: truths(s, K, st) for s in needed}
    S.log("denominators per memory (Stage 2's builder), checked against the stored features")
    depth = depths(cols, needed, K, feats)
    rng = np.random.default_rng(SEED)
    rows, drows = [], []
    jobs = [(s, f, [f"{s}|off|{f}"], [s], ("harness",)) for s, f in SINGLES] + \
           [("core profile", "w52", [f"{s}|off|w52" for s in CORE], CORE, ("harness", "ridge"))]
    for name, form, cols_j, stats_used, methods in jobs:
        for t in C.TOURS:
            gi = np.flatnonzero((feats["tour"].eq(t) & feats["p_mkt"].notna()).to_numpy())
            g = feats.iloc[gi]
            yr_all = g["year"].to_numpy()
            assert (np.diff(yr_all) >= 0).all()
            ev_all = g["evaluation"].to_numpy().astype(bool)
            X_all = g[cols_j].to_numpy(dtype="float64")
            lb_all = logit(np.clip(g["p_mkt"].to_numpy(dtype="float64"), 1e-6, 1 - 1e-6))
            for kind in ("career", "season"):
                parts = []
                for s in stats_used:
                    car, sea = true_vals[s]
                    if kind == "career":
                        za, zb = car.reindex(g["pa"]).to_numpy(), car.reindex(g["pb"]).to_numpy()
                    else:
                        za = sea.reindex(pd.MultiIndex.from_arrays([g["pa"], g["year"]])).to_numpy()
                        zb = sea.reindex(pd.MultiIndex.from_arrays([g["pb"], g["year"]])).to_numpy()
                    dz = za - zb
                    parts.append(dz / np.nanstd(dz))
                truth = np.column_stack(parts).sum(axis=1)          # missing where any part is missing
                has_truth = np.isfinite(truth)
                ok = has_truth & np.isfinite(X_all).all(axis=1)
                if ok.sum() < 3000:
                    continue
                X, yr, lb, ev = X_all[ok], yr_all[ok], lb_all[ok], ev_all[ok]
                tr = residual(truth[ok], lb)
                tr = (tr - tr.mean()) / tr.std()
                p = expit(lb)
                v = float((p * (1 - p)).mean())
                corr = partial_corr(X[ev], tr[ev], lb[ev])
                base = {"statistic": name, "form": form, "inputs": len(cols_j), "tour": t, "truth": kind,
                        "matches": int(ev.sum()), "matches_fitted": int(ok.sum()),
                        "matches_with_truth": int((has_truth & ev_all).sum()),
                        "feature_coverage": float(ev.sum() / (has_truth & ev_all).sum()),
                        "truth_r2_on_odds": float(1 - (residual(truth[ok], lb) ** 2).sum() / (truth[ok] ** 2).sum()),
                        "partial_corr": corr, "partial_corr_sq": corr ** 2}
                for G in GAINS:
                    beta = np.sqrt(2 * G / 1000 / v)
                    orac, odet = [], 0
                    feat = {mth: [] for mth in methods}
                    det = {mth: 0 for mth in methods}
                    for _ in range(DRAWS):
                        y = rng.random(len(lb)) < expit(lb + beta * tr)
                        go, se_o = score(tr[:, None], y, yr, lb, ev)
                        orac.append(go)
                        odet += int(go - 1.96 * se_o > 0)
                        for mth in methods:
                            gf, se = score(X, y, yr, lb, ev, mth)
                            feat[mth].append(gf)
                            det[mth] += int(gf - 1.96 * se > 0)
                    for mth in methods:
                        rows.append({**base, "method": mth, "planted_gain": G, "oracle_gain": float(np.mean(orac)),
                                     "oracle_detected_share": odet / DRAWS, "feature_gain": float(np.mean(feat[mth])),
                                     "feature_gain_sd": float(np.std(feat[mth], ddof=1)),
                                     "recovery": float(np.mean(feat[mth]) / np.mean(orac)) if G > 0 else np.nan,
                                     "detected_share": det[mth] / DRAWS})
                for mth in methods:
                    S.log(f"  {name} {form} {t} {kind} {mth}: {ev.sum()} matches, partial corr {corr:.2f} "
                          f"(sq {corr ** 2:.2f}); " + ", ".join(
                              f"G={r['planted_gain']}: {r['feature_gain']:.2f} of {r['oracle_gain']:.2f} "
                              f"(det {r['detected_share']:.0%})" for r in rows
                              if (r["statistic"], r["form"], r["tour"], r["truth"], r["method"]) == (name, form, t, kind, mth)))
                # what more data per player buys: the partial correlation by the smaller denominator in the memory
                if len(cols_j) == 1 and form == "w52":
                    dp = depth[cols_j[0]][gi][ok][ev]
                    Xe, te, le = X[ev], tr[ev], lb[ev]
                    edges = np.quantile(dp, np.linspace(0, 1, DEPTH_BINS + 1))
                    b = np.clip(np.searchsorted(edges, dp, "right") - 1, 0, DEPTH_BINS - 1)
                    for q in range(DEPTH_BINS):
                        m = b == q
                        c = partial_corr(Xe[m], te[m], le[m])
                        drows.append({"statistic": name, "form": form, "tour": t, "truth": kind, "quartile": q + 1,
                                      "matches": int(m.sum()), "depth_min": float(dp[m].min()),
                                      "depth_median": float(np.median(dp[m])), "depth_max": float(dp[m].max()),
                                      "partial_corr": c, "partial_corr_sq": c ** 2})
    out = pd.DataFrame(rows)
    out.to_csv(S.OUT / "stage3_planted.csv", index=False)
    pd.DataFrame(drows).to_csv(S.OUT / "stage3_planted_depth.csv", index=False)
    (S.OUT / "stage3_planted.json").write_text(json.dumps({"gains": GAINS, "draws": DRAWS, "seed": SEED, "rows": rows,
                                                           "depth": drows}, indent=1), encoding="utf-8")
    S.log(f"wrote stage3_planted.csv ({len(out)} rows) and stage3_planted_depth.csv ({len(drows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
