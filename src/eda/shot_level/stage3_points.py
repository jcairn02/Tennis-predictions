"""Stage 3, part 2: is there predictive information in the shot-level data at all? Scored on points, not matches.

A match's result is noisy: one bit per match. Its serve points are not: about 80 a player. If the shot-level history
of the two players says anything about how the coming match will be played, it should first show in how many serve
points each player wins. This diagnostic asks exactly that, with far more power than the match-level rundown.

For every pool match with a box score, two server rows: side A serving to B, and B serving to A. The target is the
server's serve points won out of points served in that match (Stage 0's box score). The models are binomial logistic
regressions on those counts, fitted walk-forward by season (season Y fitted on earlier seasons), scored per serve point
on the evaluation matches:

    M1  the earlier study's pre-match serve-point forecast (the serve/return ratings, p_serve_a / p_serve_b) recalibrated:
        an intercept and its log-odds
    M2  M1 + box-score recent form: the server's serve points won and the returner's return points won, each in three
        memories (two-week half-life, 52 weeks, career; Stage 0's box counts, the shot statistics' machinery)
    M3  M1 + the shot-level features: the server's serve-side traits, the returner's return-side traits, and both
        players' rally and ending traits, in two memories (two-week half-life and 52 weeks)
    M4  M2 + the shot-level features

The gains M3 - M1 and M4 - M2 measure what the shot data says about the coming match's points beyond the box scores.
The point forecasts are then turned into match probabilities through the earlier study's iid model (stage2_iid), and
the match-level gain of M4's over M2's is scored on the matches with odds, alone and as a feature given the closing odds.

Run:  ./python.sh src/eda/shot_level/stage3_points.py
Writes data/studies/shot_level/stage3_points.json and stage3_points_seasons.csv.
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
from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402

FORMS = ("w52", "dec2")
BOX = [("srv", f"spw|box|{f}") for f in ("w52", "dec2", "career")] + [("ret", f"rpw|box|{f}") for f in ("w52", "dec2", "career")]
SHOT = ([("srv", f"{s}|{f}") for f in FORMS for s in ("srv_quick|off", "srv_quick|adj", "ret_inplay|def", "spd1|off",
                                                       "spd2|off", "t_share|off", "wide_share|off", "net_rate|off")]
        + [("ret", f"{s}|{f}") for f in FORMS for s in ("ret_quick|off", "ret_quick|adj", "ret_inplay|off",
                                                         "ret_inplay|adj", "deep_ret|off", "srv_quick|def")]
        + [(side, f"{s}|{f}") for side in ("srv", "ret") for f in FORMS
           for s in ("rally5|off", "rally9|off", "winner_rate|off", "error_rate|off", "ue_share|off", "w_ratio|off",
                     "net_won|off")])
FIRST_SCORED = 2014


def server_rows(sides: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match with a box score and the ratings' forecasts: the server's counts, the base forecast, and the
    server's and returner's values of every input."""
    ok = (sides["A_spw_d"] > 0) & (sides["B_spw_d"] > 0) & sides["p_serve_a"].notna() & sides["p_serve_b"].notna()
    s = sides[ok]
    parts = []
    for srv, ret in (("A", "B"), ("B", "A")):
        d = pd.DataFrame({"match_id": s["match_id"].to_numpy(), "tour": s["tour"].to_numpy(), "year": s["year"].to_numpy(),
                          "evaluation": s["evaluation"].to_numpy(), "date": s["tournament_date"].to_numpy(),
                          "server": srv, "x": s[f"{srv}_spw_n"].to_numpy(), "d": s[f"{srv}_spw_d"].to_numpy(),
                          "base": s["p_serve_a" if srv == "A" else "p_serve_b"].to_numpy()})
        for role, name in BOX + SHOT:
            who = srv if role == "srv" else ret
            d[f"{role}|{name}"] = s[f"{who}|{name}"].to_numpy(dtype="float64")
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def fit_binomial(Z: np.ndarray, x: np.ndarray, d: np.ndarray, iters: int = 50, ridge: float = 1e-6) -> np.ndarray:
    """Binomial logistic regression on counts (x successes of d), Newton steps with a tiny ridge."""
    b = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = expit(Z @ b)
        g = Z.T @ (x - d * p) - ridge * b
        H = (Z.T * (d * p * (1 - p))) @ Z + ridge * np.eye(Z.shape[1])
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return b


def design(df: pd.DataFrame, cols: list[str], mean: np.ndarray | None = None, sd: np.ndarray | None = None):
    X = df[cols].to_numpy(dtype="float64") if cols else np.zeros((len(df), 0))
    if mean is None:
        mean, sd = X.mean(axis=0), X.std(axis=0)
        sd[sd == 0] = 1.0
    lb = logit(np.clip(df["base"].to_numpy(dtype="float64"), 1e-6, 1 - 1e-6))
    Z = np.column_stack([np.ones(len(df)), lb, (X - mean) / sd]) if cols else np.column_stack([np.ones(len(df)), lb])
    return Z, mean, sd


def walk(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Walk-forward point forecasts: season Y from a fit on earlier seasons (scaled on the training rows)."""
    out = np.full(len(df), np.nan)
    yr = df["year"].to_numpy()
    for Y in range(FIRST_SCORED, C.EVAL_YEARS[-1] + 1):
        tr, te = yr < Y, yr == Y
        if tr.sum() < 1000 or te.sum() == 0:
            continue
        Ztr, mean, sd = design(df[tr], cols)
        b = fit_binomial(Ztr, df["x"].to_numpy()[tr], df["d"].to_numpy()[tr])
        Zte, _, _ = design(df[te], cols, mean, sd)
        out[te] = expit(Zte @ b)
    return out


def point_ll(p: np.ndarray, x: np.ndarray, d: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(x * np.log(p) + (d - x) * np.log(1 - p))


def clustered(gain_sum: np.ndarray, units: np.ndarray, cluster: np.ndarray) -> tuple[float, float, float]:
    """A ratio estimate (sum of log-loss gains / sum of points), milli-log-loss per point, with a cluster-robust 95%
    interval (linearised)."""
    tot_u = units.sum()
    mean = gain_sum.sum() / tot_u
    resid = pd.Series(gain_sum - mean * units).groupby(cluster).sum().to_numpy()
    G = len(resid)
    se = np.sqrt((resid ** 2).sum() * G / max(G - 1, 1)) / tot_u
    return 1000 * mean, 1000 * (mean - 1.96 * se), 1000 * (mean + 1.96 * se)


def main() -> int:
    sides = pd.read_parquet(S.OUT / "stage3_sides.parquet")
    rows = server_rows(sides)
    S.log(f"{len(rows)} server rows, {int(rows['d'].sum()):,} serve points")
    models = {"M1": [], "M2": [f"{r}|{n}" for r, n in BOX], "M3": [f"{r}|{n}" for r, n in SHOT],
              "M4": [f"{r}|{n}" for r, n in BOX + SHOT]}
    res = {"inputs": {k: v for k, v in models.items()}, "points": {}, "seasons": [], "match": {}}
    season_rows = []
    preds = {}
    for t in C.TOURS:
        df = rows[rows["tour"] == t].reset_index(drop=True)
        P = {m: walk(df, cols) for m, cols in models.items()}
        preds[t] = (df, P)
        sc = df["evaluation"].to_numpy(dtype=bool) & np.isfinite(P["M1"])
        x, d = df["x"].to_numpy(), df["d"].to_numpy()
        ll = {m: point_ll(P[m], x, d) for m in models}
        wk = (pd.to_datetime(df["date"]).dt.to_period("W-SUN").astype(str)).to_numpy()
        for a, b, label in (("M1", "M2", "box form over the ratings"), ("M1", "M3", "shot features over the ratings"),
                            ("M2", "M4", "shot features over the ratings and box form")):
            g = ll[a] - ll[b]
            for w0, w1, wname in ((FIRST_SCORED, 2026, "all"), (2019, 2026, "2019_26"), (2022, 2026, "2022_26")):
                m = sc & (df["year"].to_numpy() >= w0) & (df["year"].to_numpy() <= w1)
                mean, lo, hi = clustered(g[m], d[m], wk[m])
                res["points"][f"{t}|{b}-{a}|{wname}"] = {"label": label, "gain_per_point_milli": mean, "lo": lo, "hi": hi,
                                                        "serve_points": int(d[m].sum()), "server_rows": int(m.sum())}
            for Y in range(FIRST_SCORED, 2027):
                m = sc & (df["year"].to_numpy() == Y)
                if m.sum():
                    season_rows.append({"tour": t, "season": Y, "comparison": f"{b}-{a}",
                                        "gain_per_point_milli": 1000 * g[m].sum() / d[m].sum(), "serve_points": int(d[m].sum())})
        # how big the inputs' effects are: the spread of M4's forecasts around M2's, per point
        dl = logit(np.clip(P["M4"], 1e-6, 1 - 1e-6)) - logit(np.clip(P["M2"], 1e-6, 1 - 1e-6))
        res["points"][f"{t}|spread_M4_vs_M2_logit_sd"] = float(np.nanstd(dl[sc]))
        S.log(f"  {t}: " + ", ".join(f"{k.split('|')[1]} {v['gain_per_point_milli']:+.3f}" for k, v in res["points"].items()
                                       if k.startswith(t) and k.endswith("|all") and isinstance(v, dict)))
    pd.DataFrame(season_rows).to_csv(S.OUT / "stage3_points_seasons.csv", index=False)
    # from points to matches: iid match probabilities from each model's two serve forecasts
    frames = []
    for t in C.TOURS:
        df, P = preds[t]
        for m in ("M2", "M4"):
            df[f"p_{m}"] = P[m]
        frames.append(df)
    allr = pd.concat(frames, ignore_index=True)
    a = allr[allr["server"] == "A"].set_index("match_id")
    b = allr[allr["server"] == "B"].set_index("match_id")
    both = a.index.intersection(b.index)
    mt = sides.set_index("match_id").loc[both]
    bo = np.where(mt["best_of"].to_numpy() == 5, 5, 3)
    rule = np.full(len(both), I.STANDARD, dtype=object)
    match = pd.DataFrame({"match_id": both, "tour": mt["tour"].to_numpy(), "year": mt["year"].to_numpy(),
                          "a_won": mt["a_won"].to_numpy(), "p_mkt": mt["p_mkt"].to_numpy(), "p_elo": mt["p_elo"].to_numpy(),
                          "evaluation": mt["evaluation"].to_numpy(), "date": mt["tournament_date"].to_numpy()})
    for m in ("M2", "M4"):
        pa, pb = a.loc[both, f"p_{m}"].to_numpy(), b.loc[both, f"p_{m}"].to_numpy()
        ok = np.isfinite(pa) & np.isfinite(pb)
        pm = np.full(len(both), np.nan)
        pm[ok] = I.match_win_by(pa[ok], pb[ok], bo[ok], rule[ok])
        match[f"p_iid_{m}"] = pm
    y = match["a_won"].to_numpy().astype(bool)

    def mll(p):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.where(y, np.log(p), np.log(1 - p))
    for t in C.TOURS:
        m = (match["tour"].eq(t) & match["evaluation"] & match["p_iid_M2"].notna() & match["p_iid_M4"].notna()).to_numpy()
        g = mll(match["p_iid_M2"].to_numpy()) - mll(match["p_iid_M4"].to_numpy())
        wk = pd.to_datetime(match["date"]).dt.to_period("W-SUN").astype(str).to_numpy()
        for label, mm in (("all matches", m), ("matches with odds", m & match["p_mkt"].notna().to_numpy())):
            mean, lo, hi = clustered(g[mm], np.ones(mm.sum()), wk[mm])
            res["match"][f"{t}|iid M4 over iid M2|{label}"] = {"gain_milli": mean, "lo": lo, "hi": hi, "n": int(mm.sum())}
        # the point models' increment as a feature given the closing odds (the harness's walk, one input)
        mo = m & match["p_mkt"].notna().to_numpy()
        feat = logit(np.clip(match["p_iid_M4"].to_numpy(), 1e-6, 1 - 1e-6)) - logit(np.clip(match["p_iid_M2"].to_numpy(), 1e-6, 1 - 1e-6))
        for base_name, base_col in (("odds", "p_mkt"), ("elo", "p_elo")):
            mm = mo if base_name == "odds" else m
            lb = logit(np.clip(match[base_col].to_numpy(dtype="float64")[mm], 1e-9, 1 - 1e-9))
            Z = np.column_stack([lb, feat[mm] / np.nanstd(feat[mm])])[None]
            yr = match["year"].to_numpy()[mm]
            w = R.walk(np.ascontiguousarray(Z), y[mm], yr, list(range(FIRST_SCORED + 1, 2027)), lb)
            dd = (w["llb"][None, :] - w["llm"])[0]
            okd = np.isfinite(dd)
            mean, lo, hi = clustered(dd[okd], np.ones(okd.sum()), wk[mm][okd])
            res["match"][f"{t}|point-model increment given {base_name}"] = {"gain_milli": mean, "lo": lo, "hi": hi, "n": int(okd.sum())}
    (S.OUT / "stage3_points.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for k, v in res["points"].items():
        print(k, v if not isinstance(v, dict) else {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    for k, v in res["match"].items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
