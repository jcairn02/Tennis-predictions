"""Audit B of Stage 4, checks 4, 5 and 8: the rundown's scores reproduced by the audit's own scorer, the null band and
the family-wide line checked against the plan, A and B and the baselines checked, and every score given the market
redone with Pinnacle's close in place of the market average.

    reproduction    every row of the plan, every score (alone, given Elo, given the market), with its 20 shuffled
                    copies, by audit4_common's walk-forward (its own Newton fits; the plan's keys and shuffle, written
                    afresh), against stage4_ranking.csv: the improvement, the band's minimum, maximum, mean and spread
    the line        the family-wide line recomputed from stage4_null_copies.csv as the plan defines it (section 6), and
                    again from the audit's own copies; each row's place against it
    A and B         the baselines in Stage 4's table against Stage 1's (Elo) and the odds file (the market), match by
                    match; their log loss against who won, and against the flipped outcome; the sign of the alone fit
                    for features whose direction is fixed by construction
    same matches    the baseline is refitted and scored on the matches of the row (the reproduction shows it); the
                    forms of a statistic compared on the matches where all five exist; the leaders' gain given Elo on
                    the matches with odds of 2022-2026, beside Elo's deficit to the market on those same matches
    Pinnacle        given the market, three ways on each row: the average close as built; the average close on the
                    matches that have Pinnacle's close too; Pinnacle's close on those matches (Stage 1's normalised
                    p_pinnacle), each with its copies and its own family-wide line

Writes, in data/studies/predictability_diagnostic/audit4/:
    scoring_rows.csv    one row per tour x row: Stage 4's numbers, the audit's, and the three market scores
    scoring.json        the summary

Run: ./python.sh src/eda/predictability_diagnostic/audit4_scoring.py   (about 10 minutes with 12 workers)
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402

WORKERS = max(1, min(12, (os.cpu_count() or 2) - 2))
T0 = time.time()
KEEP = ("n", "imp", "lo", "hi", "band_min", "band_max", "band_mean", "band_sd", "z", "above_band", "below_band")
# features whose direction is fixed by how they are built: more of it means a stronger A (alone, the coefficient > 0)
STRONGER_IF_POSITIVE = ("rank|single", "rank_points|single", "elo_games|single", "elo_points|single",
                        "rating_serve|single", "rating_return|single", "rating_matchup|single", "spw|career",
                        "rpw|career", "tpw|career", "hold|career", "brk|career", "games_won|career", "sets_won|career",
                        "win|career", "mu_points|career", "mu_games|career", "mu_components|career")


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def plan_rows() -> list[dict]:
    cand = pd.read_csv(A.OUT / "stage4_candidates.csv")
    cols = set(pd.read_parquet(A.OUT / "stage4_features.parquet").columns)
    tasks = []
    for c in cand.itertuples(index=False):
        for form in c.forms.split(";"):
            col = f"{c.id}|{form}"
            for tour in c.tours.split(";"):
                tasks.append({"tour": tour, "id": c.id, "form": form, "cols": [col] + ([f"{col}|2"] if f"{col}|2" in cols else []),
                              "scores": c.scores.split(";"), "interaction": c.id == "best_of_five",
                              "first": 2019 if (tour == "wta" and c.wta_box_from_2019 == "yes") else 2013})
    return tasks


_S: dict = {}


def init_worker() -> None:
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    b = pd.read_parquet(A.OUT / "stage1_baselines.parquet", columns=["match_id", "p_pinnacle"]).set_index("match_id")
    f["p_ps"] = b["p_pinnacle"].reindex(f["match_id"]).to_numpy()
    _S["f"] = f
    _S["keys"] = A.plan_keys(len(f))


def score_row(task: dict) -> dict:
    f, keys = _S["f"], _S["keys"]
    t = f["tour"].to_numpy() == task["tour"]
    X = np.column_stack([f[c].to_numpy("float64") for c in task["cols"]])
    ex = t & np.isfinite(X).all(axis=1)
    idx = np.flatnonzero(ex)
    out = {k: task[k] for k in ("tour", "id", "form")}
    Xe = X[idx]
    out["constant"] = bool((Xe.std(axis=0) == 0).any())
    if out["constant"]:
        return out
    y, yr, ev = f["a_won"].to_numpy()[idx], f["year"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
    lg = lambda v: A.logit(np.clip(np.nan_to_num(v, nan=0.5), 1e-9, 1 - 1e-9))   # noqa: E731
    pe, pm, pp = (f[c].to_numpy("float64")[idx] for c in ("p_elo", "p_mkt", "p_ps"))
    has_m, has_p = np.isfinite(pm), np.isfinite(pp)
    k = keys[idx]
    runs = []
    for s in task["scores"]:
        if s == "alone":
            runs.append(("alone", None, None))
        elif s == "elo":
            runs.append(("elo", lg(pe), None))
        else:
            runs += [("market", lg(pm), has_m), ("market_avg_on_pinnacle", lg(pm), has_m & has_p),
                     ("pinnacle", lg(pp), has_m & has_p)]
    for name, base, sub in runs:
        if sub is not None and sub.sum() < A.MIN_TRAIN:
            continue
        r = A.score_feature(Xe, y, yr, ev, base, task["first"], sub=sub, keys=k, interaction=task["interaction"])
        g = r["all"]
        for key in KEEP:
            out[f"{name}_{key}"] = g.get(key)
        out[f"{name}_copies"] = g.get("copies")
        out[f"{name}_seasons"] = r["seasons"]
        if name == "alone" and r["coefs"]:
            out["alone_coef_last"] = r["coefs"][max(r["coefs"])][0]
    return out


def family_line(rows: list[dict], tour: str, score: str) -> dict:
    """The plan's line: each copy's standardised value (against the other 19 copies of its row), its largest over the
    rows, and the largest of the 20."""
    mats = [r[f"{score}_copies"] for r in rows if r["tour"] == tour and r.get(f"{score}_copies") is not None
            and r.get(f"{score}_band_sd") and r[f"{score}_band_sd"] > 0]
    M_ = np.array(mats)
    zs = np.empty_like(M_)
    for c in range(M_.shape[1]):
        o = np.delete(M_, c, axis=1)
        zs[:, c] = (M_[:, c] - o.mean(axis=1)) / o.std(axis=1, ddof=1)
    mx = zs.max(axis=0)
    return {"rows": int(len(M_)), "line": float(mx.max()), "copy_maxima": [float(v) for v in mx]}


def orientation(f: pd.DataFrame) -> dict:
    """The baselines in Stage 4's table, match by match, against Stage 1's files; and their log loss."""
    b = pd.read_parquet(A.OUT / "stage1_baselines.parquet", columns=["match_id", "a_won", "p_elo_surf_ret", "p_market",
                                                                     "p_pinnacle"]).set_index("match_id").reindex(f["match_id"])
    o = pd.read_parquet(A.OUT / "stage1_odds.parquet", columns=["match_id", "p_avg_a"]).set_index("match_id").reindex(f["match_id"])
    m = pd.read_parquet(A.OUT / "stage0_matches.parquet", columns=["match_id", "a_won", "player_a_id"]).set_index("match_id").reindex(f["match_id"])
    y = f["a_won"].to_numpy()
    ev = f["evaluation"].to_numpy()
    res = {"a_won_equals_stage0": bool((m["a_won"].to_numpy() == y).all()),
           "p_elo_equals_stage1": float(np.nanmax(np.abs(b["p_elo_surf_ret"].to_numpy() - f["p_elo"].to_numpy()))),
           "p_mkt_equals_odds_file": float(np.nanmax(np.abs(o["p_avg_a"].to_numpy() - f["p_mkt"].to_numpy()))),
           "p_mkt_missing_where_odds_file_has_it": int((o["p_avg_a"].notna().to_numpy() & f["p_mkt"].isna().to_numpy()).sum()),
           "a_share_won": {t: float(y[ev & (f["tour"].to_numpy() == t)].mean()) for t in ("atp", "wta")}}
    for name, p in (("elo", f["p_elo"].to_numpy("float64")), ("market", f["p_mkt"].to_numpy("float64")),
                    ("pinnacle", b["p_pinnacle"].to_numpy("float64"))):
        for t in ("atp", "wta"):
            mk = ev & (f["tour"].to_numpy() == t) & np.isfinite(p)
            pc = np.clip(p[mk], 1e-12, 1 - 1e-12)
            ll = float(np.mean(np.where(y[mk], -np.log(pc), -np.log(1 - pc))))
            llf = float(np.mean(np.where(~y[mk], -np.log(pc), -np.log(1 - pc))))
            res[f"{name}_{t}"] = {"matches": int(mk.sum()), "log_loss": ll, "log_loss_if_flipped": llf}
    return res


def same_match_forms(f: pd.DataFrame) -> list[dict]:
    """Given Elo, the five forms of each statistic and matchup scored on the matches where all five exist (no
    copies): does the best form change?"""
    cand = pd.read_csv(A.OUT / "stage4_candidates.csv")
    out = []
    for c in cand[cand["forms"].str.count(";") == 4].itertuples(index=False):
        forms = c.forms.split(";")
        for tour in c.tours.split(";"):
            t = f["tour"].to_numpy() == tour
            Xs = {fm: f[f"{c.id}|{fm}"].to_numpy("float64") for fm in forms}
            common = t & np.all([np.isfinite(v) for v in Xs.values()], axis=0)
            idx = np.flatnonzero(common)
            if len(idx) < 1000 or any(np.std(v[idx]) == 0 for v in Xs.values()):
                continue
            first = 2019 if (tour == "wta" and c.wta_box_from_2019 == "yes") else 2013
            y, yr, ev = f["a_won"].to_numpy()[idx], f["year"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
            le = A.logit(np.clip(f["p_elo"].to_numpy("float64")[idx], 1e-9, 1 - 1e-9))
            imps = {fm: A.score_feature(Xs[fm][idx][:, None], y, yr, ev, le, first)["all"]["imp"] for fm in forms}
            out.append({"tour": tour, "id": c.id, "common_matches": int(ev.sum()), **{f"imp_{fm}": v for fm, v in imps.items()},
                        "best_on_common": max(imps, key=imps.get)})
    return out


def leaders_on_odds(f: pd.DataFrame, rows: list[tuple]) -> list[dict]:
    """On the evaluation matches with odds of 2022-2026 where the row exists: log loss of raw Elo, of refitted Elo,
    of Elo plus the row (both walk-forward as built), and of the market."""
    out = []
    for tour, col in rows:
        t = f["tour"].to_numpy() == tour
        X = f[col].to_numpy("float64")
        idx = np.flatnonzero(t & np.isfinite(X))
        y, yr, ev = f["a_won"].to_numpy()[idx], f["year"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
        pe = f["p_elo"].to_numpy("float64")[idx]
        pm = f["p_mkt"].to_numpy("float64")[idx]
        le = A.logit(np.clip(pe, 1e-9, 1 - 1e-9))
        sd = X[idx].std()
        w = A.walk_forward((X[idx] / sd)[:, None], y, yr, le, 2013 if not (tour == "wta" and col.startswith(("rating", "mu_", "tpw"))) else 2019)
        sel = ev & np.isfinite(pm) & (yr >= 2022) & np.isfinite(w["llm"][0])
        ll_raw = A.loss(pe[sel], y[sel]).mean()
        ll_mkt = A.loss(pm[sel], y[sel]).mean()
        out.append({"tour": tour, "row": col, "matches": int(sel.sum()), "elo_raw": float(ll_raw),
                    "elo_refitted": float(w["llb"][sel].mean()), "elo_plus_row": float(w["llm"][0, sel].mean()),
                    "market": float(ll_mkt),
                    "market_better_than_refitted_elo_milli": float(1000 * (w["llb"][sel].mean() - ll_mkt)),
                    "row_gain_given_elo_milli": float(1000 * (w["llb"][sel].mean() - w["llm"][0, sel].mean()))})
    return out


def main() -> int:
    tasks = plan_rows()
    log(f"{len(tasks)} rows to score with {WORKERS} workers")
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker) as ex:
        for i, r in enumerate(ex.map(score_row, tasks, chunksize=1)):
            res.append(r)
            if (i + 1) % 25 == 0:
                log(f"  {i + 1} of {len(tasks)}")
    rank = pd.read_csv(A.OUT / "stage4_ranking.csv")
    st4 = json.loads((A.OUT / "stage4_results.json").read_text(encoding="utf-8"))

    # reproduction against stage4_ranking.csv
    R = pd.DataFrame([{k: v for k, v in r.items() if not k.endswith(("_copies", "_seasons"))} for r in res])
    S4 = rank.set_index(["tour", "id", "form"]).reindex(pd.MultiIndex.from_frame(R[["tour", "id", "form"]]))
    repro = {}
    for s in ("alone", "elo", "market"):
        for k in ("imp", "band_min", "band_max", "band_mean", "band_sd", "z"):
            a = pd.to_numeric(R.get(f"{s}_{k}", pd.Series(np.nan, index=R.index)), errors="coerce").to_numpy("float64")
            b = pd.to_numeric(S4[f"{s}_{k}"], errors="coerce").to_numpy("float64")
            both = np.isfinite(a) & np.isfinite(b)
            d = np.abs(a[both] - b[both])
            repro[f"{s}_{k}"] = {"rows": int(both.sum()), "max_abs_diff": float(d.max()) if both.any() else None,
                                 "rows_beyond_1e-6": int((d > 1e-6 * np.maximum(1, np.abs(b[both]))).sum()),
                                 "only_one_side": int((np.isfinite(a) != np.isfinite(b)).sum())}
        an = pd.to_numeric(R.get(f"{s}_n", pd.Series(0, index=R.index)), errors="coerce").fillna(0).to_numpy()
        bn = S4[f"{s}_scored"].fillna(0).to_numpy()
        repro[f"{s}_n_differs"] = int((an != bn).sum())
    log(f"reproduction: {repro}")

    # the family-wide line: from Stage 4's copies (stage4_null_copies.csv), and from the audit's own
    nc = pd.read_csv(A.OUT / "stage4_null_copies.csv")
    lines = {}
    for t in ("atp", "wta"):
        for s in ("alone", "elo", "market"):
            g = nc[nc["tour"].eq(t) & nc["score"].eq(s)]
            Mx = g[[f"copy_{c}" for c in range(1, 21)]].to_numpy("float64")
            sd = Mx.std(axis=1, ddof=1)
            Mx = Mx[sd > 0]
            zs = np.empty_like(Mx)
            for c in range(20):
                o = np.delete(Mx, c, axis=1)
                zs[:, c] = (Mx[:, c] - o.mean(axis=1)) / o.std(axis=1, ddof=1)
            line_from_csv = float(zs.max(axis=0).max())
            own = family_line(res, t, s)
            stored = st4["lines"][f"{t}|{s}"]["line"]
            rk = rank[rank["tour"].eq(t)]
            clears = (pd.to_numeric(rk[f"{s}_z"], errors="coerce") > stored)
            lines[f"{t}|{s}"] = {"stored": stored, "from_stage4_copies": line_from_csv, "from_audit_copies": own["line"],
                                 "rows": own["rows"], "rows_clearing_stored": int(clears.sum()),
                                 "stored_flags_agree": bool((clears == rk[f"{s}_clears_line"].astype(bool)).all()),
                                 "copy_maxima_median": float(np.median(own["copy_maxima"]))}
    log(f"lines: {lines}")

    # Pinnacle: lines and readings for the three market scores
    pin = {}
    for t in ("atp", "wta"):
        for s in ("market", "market_avg_on_pinnacle", "pinnacle"):
            pin[f"{t}|{s}"] = family_line(res, t, s)
    for r in res:
        for s in ("market", "market_avg_on_pinnacle", "pinnacle"):
            ln = pin.get(f"{r['tour']}|{s}", {}).get("line")
            z = r.get(f"{s}_z")
            r[f"{s}_clears_own_line"] = bool(z is not None and ln is not None and np.isfinite(z) and z > ln)
    P = pd.DataFrame([{k: v for k, v in r.items() if not k.endswith(("_copies", "_seasons"))} for r in res])
    keep_rank = rank[["tour", "id", "form", "elo_imp", "market_imp", "market_lo", "market_hi", "market_band_max",
                      "market_clears_line", "reading", "rank_given_elo"]].rename(columns=lambda c: c if c in ("tour", "id", "form") else f"s4_{c}")
    P = P.merge(keep_rank, on=["tour", "id", "form"], how="left")
    P.to_csv(A.AUDIT / "scoring_rows.csv", index=False)

    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    ori = orientation(f)
    log(f"orientation: {ori}")
    signs = []
    for r in res:
        col = f"{r['id']}|{r['form']}"
        if col in STRONGER_IF_POSITIVE and r.get("alone_coef_last") is not None:
            signs.append({"tour": r["tour"], "row": col, "alone_coef_2026_fit": r["alone_coef_last"]})
    forms = same_match_forms(f)
    log("forms on common matches done")
    leaders = leaders_on_odds(f, [("atp", "rating_matchup|single"), ("atp", "elo_games|single"), ("atp", "sets_14d|single"),
                                  ("atp", "mu_points|52 weeks"), ("wta", "rating_matchup|single"), ("wta", "elo_games|single"),
                                  ("wta", "sets_14d|single"), ("wta", "mu_points|52 weeks")])
    summ = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "rows": len(res),
            "reproduction": repro, "lines": lines, "pinnacle_lines": {k: {"line": v["line"], "rows": v["rows"]} for k, v in pin.items()},
            "orientation": ori, "alone_signs": signs, "forms_on_common_matches": forms, "leaders_on_odds_2022_2026": leaders,
            "seconds": round(time.time() - T0, 1)}
    A.save_json(summ, "scoring.json")
    log("wrote scoring_rows.csv and scoring.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
