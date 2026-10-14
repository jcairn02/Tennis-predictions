"""Stage 2, part 3: the numbers the Stage 2 write-up quotes, from the rundown (stage2_ranking.csv, stage2_results.json).

    best_by_statistic   per tour and statistic, the version with the largest gain on the closing odds, with its gains
                        alone and given Elo, its scored matches and the harness's reading
    clustered           for the profiles and the strongest single rows: the gain on the odds (and on the extra bases)
                        recomputed match by match through the same walk-forward fit, with a 95% interval clustered by the
                        tournament's calendar week (the feature-alpha audit's method), beside the harness's interval
    redundancy          per single feature, how much of it the closing odds and surface Elo explain together (R squared of
                        the A - B feature on their log-odds, on the matches with odds): a pre-match quantity, no result
    families            per tour and family, the best single row and the profiles

Run:  ./python.sh src/eda/shot_level/stage2_summary.py
Writes data/studies/shot_level/stage2_summary.json and stage2_clustered.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

TOP = 8


def per_match(f: pd.DataFrame, cols: list[str], tour: str, base_col: str, first: int = C.EVAL_YEARS[0]) -> pd.DataFrame:
    """The real feature's per-match log-loss improvement over the base (walk-forward, as the harness fits it), on the
    scored evaluation matches: match_id, year, week, d (nats)."""
    tt = f["tour"].to_numpy() == tour
    X = np.column_stack([f[c].to_numpy(dtype="float64") for c in cols])
    ex = tt & np.isfinite(X).all(axis=1)
    idx = np.flatnonzero(ex)
    Xe = X[idx]
    sd = Xe.std(axis=0)
    Xs = Xe / np.where(sd > 0, sd, 1.0)
    year, y, ev = f["year"].to_numpy()[idx], f["a_won"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
    p = f[base_col].to_numpy(dtype="float64")[idx]
    has = np.isfinite(p)
    lb = logit(np.clip(np.nan_to_num(p, nan=0.5), 1e-9, 1 - 1e-9))
    seasons = list(range(first, C.EVAL_YEARS[-1] + 1))
    Z = np.concatenate([lb[has][:, None], Xs[has]], axis=1)[None]
    w = R.walk(np.ascontiguousarray(Z), y[has], year[has], seasons, lb[has])
    d = (w["llb"][None, :] - w["llm"])[0]
    m = np.isfinite(d) & ev[has]
    rows = idx[has][m]
    return pd.DataFrame({"row": rows, "match_id": f["match_id"].to_numpy()[rows], "year": year[has][m], "d": d[m]})


def clustered_interval(d: np.ndarray, cluster: np.ndarray) -> tuple[float, float, float, int]:
    """Mean and 95% interval of d (milli-log-loss), the standard error clustered by ``cluster``."""
    n = len(d)
    if n < 2:
        return np.nan, np.nan, np.nan, 0
    mean = d.mean()
    g = pd.Series(d - mean).groupby(cluster).sum()
    G = len(g)
    se = np.sqrt((g ** 2).sum() * G / max(G - 1, 1)) / n
    return 1000 * mean, 1000 * (mean - 1.96 * se), 1000 * (mean + 1.96 * se), int(G)


def main() -> int:
    rank = pd.read_csv(S.OUT / "stage2_ranking.csv")
    frame = pd.read_parquet(S.OUT / "stage2_frame.parquet")
    weeks = C.load_matches(["match_id", "tournament_date"]).set_index("match_id")["tournament_date"]
    wk = weeks.reindex(frame["match_id"]).dt.to_period("W-SUN").astype(str).to_numpy()
    cat = {(c["tour"], c["id"], c["form"]): c for c in json.loads((S.OUT / "stage2_catalog.json").read_text(encoding="utf-8"))}
    singles = rank[~rank["id"].str.startswith(("profile_", "rally_edge"))].copy()
    singles["statistic"] = singles["id"].str.split("|").str[0]
    best = (singles.sort_values("market_imp", ascending=False).groupby(["tour", "statistic"]).head(1)
            .sort_values(["tour", "market_imp"], ascending=[True, False]))
    keep = ["tour", "statistic", "id", "form", "alone_imp", "elo_imp", "elo_lo", "elo_hi", "market_imp", "market_lo",
            "market_hi", "market_scored", "market_clears_line", "elo_clears_line", "reading", "group"]
    out = {"best_by_statistic": best[keep].to_dict("records")}
    # clustered intervals: every profile and the strongest single rows per tour
    todo = []
    for t in C.TOURS:
        pr = rank[(rank["tour"] == t) & rank["id"].str.startswith("profile_")]
        sg = singles[singles["tour"] == t].sort_values("market_imp", ascending=False).head(TOP)
        for _, r in pd.concat([pr, sg, rank[(rank["tour"] == t) & rank["id"].eq("rally_edge")]]).iterrows():
            todo.append(r)
    rows = []
    for r in todo:
        c = cat[(r["tour"], r["id"], r["form"])]
        bases = {"market": "p_mkt", "elo": "p_elo"}
        for b in c.get("extra_bases", []):
            bases[b] = "p_mktbox" if b == "mktbox" else "p_elobox"
        for bname, bcol in bases.items():
            pm = per_match(frame, c["inputs"], r["tour"], bcol)
            if pm.empty:
                continue
            mean, lo, hi, G = clustered_interval(pm["d"].to_numpy(), wk[pm["row"].to_numpy()])
            rec = {"tour": r["tour"], "id": r["id"], "form": r["form"], "inputs": len(c["inputs"]), "base": bname,
                   "n": int(len(pm)), "imp": mean, "lo_week": lo, "hi_week": hi, "weeks": G}
            for w0, w1, name in ((2022, 2026, "2022_26"), (2019, 2026, "2019_26")):
                mm = pm["year"].between(w0, w1).to_numpy()
                m2, l2, h2, _ = clustered_interval(pm["d"].to_numpy()[mm], wk[pm["row"].to_numpy()[mm]])
                rec.update({f"imp_{name}": m2, f"lo_{name}": l2, f"hi_{name}": h2, f"n_{name}": int(mm.sum())})
            rows.append(rec)
    cl = pd.DataFrame(rows)
    cl.to_csv(S.OUT / "stage2_clustered.csv", index=False)
    out["clustered"] = cl.to_dict("records")
    # redundancy in feature space
    red = []
    mkt = frame["evaluation"].astype(bool) & frame["p_mkt"].notna()
    lm = logit(np.clip(frame["p_mkt"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
    le = logit(np.clip(frame["p_elo"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
    for c in [x for x in frame.columns if x.count("|") == 2 and not x.startswith(("adjperf_", "adjdef_"))]:
        for t in C.TOURS:
            m = (mkt & frame["tour"].eq(t) & frame[c].notna()).to_numpy()
            if m.sum() < 300:
                continue
            x = frame[c].to_numpy(dtype="float64")[m]
            if x.std() == 0:
                red.append({"feature": c, "tour": t, "n": int(m.sum()), "r2_market_elo": None, "r2_market": None})
                continue
            Z = np.column_stack([lm[m], le[m]])
            beta, *_ = np.linalg.lstsq(Z, x, rcond=None)      # A - B features and log-odds are both antisymmetric
            r2 = 1 - ((x - Z @ beta) ** 2).sum() / (x ** 2).sum()
            b1, *_ = np.linalg.lstsq(lm[m][:, None], x, rcond=None)
            r2m = 1 - ((x - lm[m] * b1[0]) ** 2).sum() / (x ** 2).sum()
            red.append({"feature": c, "tour": t, "n": int(m.sum()), "r2_market_elo": float(r2), "r2_market": float(r2m)})
    out["redundancy"] = red
    out["counts"] = {t: {"single_rows": int((singles["tour"] == t).sum()),
                         "profiles": int(((rank["tour"] == t) & rank["id"].str.startswith("profile_")).sum()),
                         "constant": int(((rank["tour"] == t) & rank["constant"]).sum()),
                         "market_clears_line": int(((rank["tour"] == t) & rank["market_clears_line"].fillna(False)).sum()),
                         "elo_clears_line": int(((rank["tour"] == t) & rank["elo_clears_line"].fillna(False)).sum()),
                         "market_positive": int(((rank["tour"] == t) & (rank["market_imp"] > 0)).sum()),
                         "readings": rank[rank["tour"] == t]["reading"].value_counts().to_dict()}
                     for t in C.TOURS}
    lines = json.loads((S.OUT / "stage2_results.json").read_text(encoding="utf-8"))["lines"]
    out["family_lines"] = lines
    (S.OUT / "stage2_summary.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    with pd.option_context("display.width", 260, "display.max_rows", 200):
        print(best[keep].round(3).to_string())
        print(cl.round(3).to_string())
        print(json.dumps(out["counts"], indent=1))
        rd = pd.DataFrame(red)
        print(rd.sort_values("r2_market_elo", ascending=False).head(12).round(3).to_string())
        print(rd.sort_values("r2_market_elo").head(12).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
