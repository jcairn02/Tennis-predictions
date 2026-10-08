"""Item C: the serve-speed change residual screen, exactly as pre-registered in
data/studies/point_sequence/speed_prereg.md. The script refuses to run unless that file's SHA-256 equals the one recorded
in speed_prereg.sha256 before any estimate.

Model: logit P(A wins) = logit(benchmark) + beta * x_std, no intercept; benchmarks = the 54-input model's walk-forward
forecast and the close, each recalibrated prequentially (diag_edge_split.prequential: one slope per tour on logit,
fitted on earlier seasons). Positive beta = the player whose recent first-serve speed rose more against his own 52-week
norm than his opponent's wins more often than the benchmark says. Wald 95% interval; four-week-block bootstrap check.
Implied gain: walk-forward beta (earlier seasons only), mLL = 1000 x (LL benchmark - LL benchmark + feature), positive =
feature better.

Run: ./python.sh src/eda/point_sequence/speed_screen.py
Writes data/studies/point_sequence/speed_results.json and speed_estimates.csv.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "point_sequence"
PREREG = OUT / "speed_prereg.md"
HASHFILE = OUT / "speed_prereg.sha256"
FEATURES = OUT / "speed_features.parquet"
RESULTS = OUT / "speed_results.json"
ESTIMATES = OUT / "speed_estimates.csv"
WF = ROOT / "data" / "studies" / "meta_stack" / "walkforward.parquet"
LAST_YEAR = 2024
# scales fixed in the pre-registration (pooled SD over both windows' analysable matches, feature only)
SCALE = {("x_raw", "atp"): 5.998, ("x_raw", "wta"): 4.942, ("x_evt", "atp"): 5.904, ("x_evt", "wta"): 4.884,
         ("x_shot", "atp"): 6.247, ("x_shot", "wta"): 8.832}
CLIP = 4.0
BOOT = 2000
MIN_TRAIN = 300
SEED = 20261006


def check_hash() -> str:
    if not HASHFILE.exists() or not PREREG.exists():
        sys.exit(f"REFUSED: {HASHFILE.name} or {PREREG.name} is missing")
    want = HASHFILE.read_text(encoding="utf-8").split()[0].strip().lower()
    got = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if got != want:
        sys.exit(f"REFUSED: {PREREG.name} SHA-256 {got} differs from the recorded {want}")
    return got


def subset(d: pd.DataFrame, tour: str, window: str) -> pd.DataFrame:
    """The pre-registered subsets (section 4)."""
    if tour == "atp":
        if window == "discovery":
            return d[(d["tour"] == "atp") & d["year"].between(2015, 2021) & ((d["level"] == "GS") | (d["year"] == 2021))]
        return d[(d["tour"] == "atp") & d["year"].between(2022, 2024)]
    yrs = (2015, 2021) if window == "discovery" else (2022, 2024)
    return d[(d["tour"] == "wta") & d["year"].between(*yrs) & (d["level"] == "GS")]


def frame() -> pd.DataFrame:
    from src.eda.point_sequence import diag_edge_split as S
    wf = pd.read_parquet(WF, columns=["match_id", "tour", "year", "tournament_date", "a_won", "p_mkt", "p_base"],
                         filters=[("year", "<=", LAST_YEAR)])
    wf = wf[wf["p_mkt"].notna() & wf["p_base"].notna()].reset_index(drop=True)
    wf["p_model"] = S.prequential(wf, "p_base")
    wf["p_market"] = S.prequential(wf, "p_mkt")
    f = pd.read_parquet(FEATURES, columns=["match_id", "level", "round", "x_raw", "x_evt", "x_shot"])
    return wf.merge(f, on="match_id", how="left")


def newton(off, x, y, w=None, b0=0.0) -> tuple[float, float]:
    w = np.ones(len(y)) if w is None else w
    b = b0
    for _ in range(100):
        p = expit(off + b * x)
        g, h = np.sum(w * x * (y - p)), np.sum(w * x * x * p * (1 - p))
        if h <= 0:
            return np.nan, np.nan
        step = g / h
        b += step
        if abs(step) < 1e-12:
            break
    p = expit(off + b * x)
    return float(b), float(1 / np.sqrt(np.sum(w * x * x * p * (1 - p))))


def blocks(dates) -> np.ndarray:
    from src.eda.tabpfn_thinking import common as T
    return T.blocks(np.asarray(dates), 28)


def fit(g: pd.DataFrame, bench: str, col: str, rng: np.random.Generator, boot: int = BOOT) -> dict:
    y = g["a_won"].astype(float).to_numpy()
    off = logit(np.clip(g[bench].to_numpy(), 1e-9, 1 - 1e-9))
    x = g["xs"].to_numpy(float)
    b, se = newton(off, x, y)
    blk = blocks(g["tournament_date"])
    ub, inv = np.unique(blk, return_inverse=True)
    bs = np.empty(boot)
    for r in range(boot):
        cnt = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))
        bs[r], _ = newton(off, x, y, w=cnt[inv].astype(float), b0=b)
    lo, hi = b - 1.96 * se, b + 1.96 * se
    return {"feature": col, "benchmark": bench, "matches": int(len(g)), "blocks": int(len(ub)), "beta": b, "se": se,
            "lo": lo, "hi": hi, "block_lo": float(np.nanpercentile(bs, 2.5)),
            "block_hi": float(np.nanpercentile(bs, 97.5)),
            "verdict": ("speed rise wins more than the benchmark says" if lo > 0 else
                        "speed rise wins less than the benchmark says" if hi < 0 else "tie")}


def implied_gain(all_rows: pd.DataFrame, tour: str, window: str, bench: str) -> dict:
    """Walk-forward: beta for season s fitted on every earlier season's analysable matches (from 2015, subset rules
    of the pre-registration), scored on season s; mLL positive = feature better."""
    from src.eda.tabpfn_thinking import common as T
    hist = pd.concat([subset(all_rows, tour, "discovery"), subset(all_rows, tour, "replication")])
    hist = hist[hist["xs"].notna()]
    target = subset(all_rows, tour, window)
    scored, unscored = [], []
    for s in sorted(target["year"].unique()):
        tr = hist[hist["year"] < s]
        te = target[(target["year"] == s) & target["xs"].notna()]
        if len(tr) < MIN_TRAIN or te.empty:
            unscored.append(int(s))
            continue
        b, _ = newton(logit(np.clip(tr[bench].to_numpy(), 1e-9, 1 - 1e-9)), tr["xs"].to_numpy(float),
                      tr["a_won"].astype(float).to_numpy())
        p0 = te[bench].to_numpy()
        p1 = expit(logit(np.clip(p0, 1e-9, 1 - 1e-9)) + b * te["xs"].to_numpy(float))
        scored.append(te.assign(ll0=T.ll(p0, te["a_won"].to_numpy()), ll1=T.ll(p1, te["a_won"].to_numpy()), b_wf=b))
    if not scored:
        return {"scored_seasons": [], "unscored_seasons": unscored}
    sc = pd.concat(scored)
    cmp_ = T.compare(sc["ll0"].to_numpy(), sc["ll1"].to_numpy(), sc["tournament_date"].to_numpy())
    frame_n = int(len(target[target["year"].isin(sc["year"].unique())]))
    return {"scored_seasons": sorted(int(v) for v in sc["year"].unique()), "unscored_seasons": unscored,
            "matches_scored": int(len(sc)), "gain_mll": cmp_["gain"], "lo": cmp_["lo"], "hi": cmp_["hi"],
            "frame_matches_in_scored_seasons": frame_n,
            "gain_mll_diluted": float(1000 * (sc["ll0"] - sc["ll1"]).sum() / frame_n) if frame_n else None,
            "betas_by_season": {int(k): float(v) for k, v in sc.groupby("year")["b_wf"].first().items()}}


def main() -> int:
    digest = check_hash()
    f = frame()
    rng = np.random.default_rng(SEED)
    res: dict = {"prereg_sha256": digest,
                 "key": "beta: log-odds per SD of x = xA - xB (2-week minus 52-week mean first-serve speed, km/h), "
                        "given the benchmark as an offset; positive = the player whose recent first-serve speed rose "
                        "more against his own norm wins more often than the benchmark says; tie when the Wald 95% "
                        "interval spans 0. mLL gains: positive = the feature better.",
                 "fits": {}, "implied_gain": {}, "coverage": {}, "deviations_after_estimation": []}
    rows = []
    for col in ("x_raw", "x_evt", "x_shot", "x_raw_unclipped"):
        src = "x_raw" if col == "x_raw_unclipped" else col
        d = f.copy()
        sc = d["tour"].map({"atp": SCALE[(src, "atp")], "wta": SCALE[(src, "wta")]})
        d["xs"] = d[src] / sc
        if col != "x_raw_unclipped":
            d["xs"] = d["xs"].clip(-CLIP, CLIP)
        for tour in ("atp", "wta"):
            for w in ("discovery", "replication"):
                g0 = subset(d, tour, w)
                g = g0[g0["xs"].notna() & g0["p_model"].notna() & g0["p_market"].notna()]
                if col == "x_raw":
                    res["coverage"][f"{tour}|{w}"] = {"frame_matches": int(len(g0)), "with_feature": int(len(g)),
                                                      "share": round(len(g) / max(len(g0), 1), 3)}
                for bench in ("p_model", "p_market"):
                    r = fit(g, bench, col, rng)
                    r.update({"tour": tour, "window": w})
                    res["fits"][f"{col}|{tour}|{w}|{bench}"] = r
                    rows.append(r)
                    if col in ("x_raw", "x_evt", "x_shot"):
                        res["implied_gain"][f"{col}|{tour}|{w}|{bench}"] = implied_gain(d, tour, w, bench)
        if col == "x_raw":
            # per-season betas and the men's replication split by level (descriptive)
            for tour in ("atp", "wta"):
                for w in ("discovery", "replication"):
                    g = subset(d, tour, w)
                    g = g[g["xs"].notna()]
                    for yr, gy in g.groupby("year"):
                        for bench in ("p_model", "p_market"):
                            b, se = newton(logit(np.clip(gy[bench].to_numpy(), 1e-9, 1 - 1e-9)),
                                           gy["xs"].to_numpy(float), gy["a_won"].astype(float).to_numpy())
                            rows.append({"feature": "x_raw by season", "tour": tour, "window": w, "benchmark": bench,
                                         "season": int(yr), "matches": int(len(gy)), "beta": b, "se": se,
                                         "lo": b - 1.96 * se, "hi": b + 1.96 * se})
            g = subset(d, "atp", "replication")
            g = g[g["xs"].notna()]
            for lab, gg in (("Slams", g[g["level"] == "GS"]), ("non-Slam", g[g["level"] != "GS"])):
                for bench in ("p_model", "p_market"):
                    r = fit(gg, bench, "x_raw", rng, boot=500)
                    r.update({"tour": "atp", "window": f"replication {lab}"})
                    res["fits"][f"x_raw|atp|replication {lab}|{bench}"] = r
                    rows.append(r)
    prim_r = res["fits"]["x_raw|atp|replication|p_model"]
    prim_d = res["fits"]["x_raw|atp|discovery|p_model"]
    rule = {"replication_beta_positive_wald_above_0": bool(prim_r["beta"] > 0 and prim_r["lo"] > 0),
            "discovery_same_sign": bool(prim_d["beta"] > 0)}
    rule["pass"] = bool(all(rule.values()))
    rule["fragile"] = bool(rule["pass"] and prim_r["block_lo"] <= 0)
    res["pass_rule"] = rule
    pd.DataFrame(rows).to_csv(ESTIMATES, index=False)
    RESULTS.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    show = pd.DataFrame([v for k, v in res["fits"].items()])[["feature", "tour", "window", "benchmark", "matches",
                                                               "beta", "lo", "hi", "block_lo", "block_hi", "verdict"]]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(show.round(4).to_string(index=False))
        print(json.dumps(res["implied_gain"], indent=1, default=float))
        print(json.dumps(res["coverage"], indent=1))
        print("pass rule:", rule)
    return 0


if __name__ == "__main__":
    sys.exit(main())
