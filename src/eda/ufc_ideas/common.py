"""Shared harness for the study "ideas borrowed from UFC-predictions" (src/eda/ufc_ideas/).

Every stage of this study builds pre-match features for the same pool of matches as the predictability
diagnostic's Stage 4 (data/studies/predictability_diagnostic/stage4_features.parquet: every evaluation-level
singles match of 2010-2026, completed or retired, one row per match, side A random) and scores them with the
corrected protocol in that study's Stage 4 rundown. Historical archived point estimates remain comparable;
uncertainty intervals and evidence labels must be regenerated with this revision:

    walk-forward    for each season Y from 2013 (the women's box-score rows from 2019): a logistic regression
                    without an intercept fitted on the pool matches of 2010 to Y - 1 on which the feature exists,
                    scored on season Y's evaluation matches; a season is skipped when fewer than 300 training
                    matches exist, or fewer than 300 on which the feature is not zero
    scores          "alone" (the feature against a coin), "elo" (added to Stage 1's surface Elo, against surface
                    Elo refitted on the same matches), "market" (added to the closing odds, main-tour matches with
                    odds); a stage may add bases of its own (e.g. "bt": added to the Bradley-Terry rating)
    shuffle band    20 copies of the feature shuffled within each season, through the same fits; descriptive only
    family line     a shuffled-feature heuristic, not a calibrated conditional test or family-wise error control
    uncertainty     paired four-week cluster t interval, plus calendar-week sensitivity; pointwise, post-selection
    reading         exploratory finding (positive clustered lower bound, clears heuristic line, positive in 3+ eras),
                    possible (positive point estimate above its own descriptive band),
                    no sign, worse; sizes: small (< 1 milli-log-loss) or clear (>= 1) given a base, and
                    weak (< 10) / moderate (10-40) / strong (>= 40) alone

Shared functions come from the corrected stage4_rundown. Feature scaling is training-only inside walk.
Raw-baseline and slope-recalibrated comparisons are separately labelled in the output. The post-2018 windows
avoid the feature-constant tuning years but remain historically selected exploratory samples, not new holdouts.

Use:
    pool = load_pool()                                  # the 255,123 pool matches, in the table's order
    frame = pool.assign(**{"bt|single": feat_a_minus_b, ...})
    frame.to_parquet(OUT / "stageA_features.parquet")
    tasks = [task("atp", "bt", "single", "Bradley-Terry rating", "rating", ["bt|single"]), ...]
    res = rundown(OUT / "stageA_features.parquet", tasks, OUT / "stageA")   # writes stageA_ranking.csv etc.
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
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402

OUT = ROOT / "data" / "studies" / "ufc_ideas"
DOCS = ROOT / "docs" / "studies" / "ufc_ideas"
PD_OUT = C.OUT                                   # the predictability diagnostic's tables
STAGE4_FEATURES = PD_OUT / "stage4_features.parquet"
STAGE4_RANKING = PD_OUT / "stage4_ranking.csv"

POOL_COLS = ["match_id", "tour", "year", "group", "evaluation", "status", "a_won", "p_elo", "p_mkt", "order", "era"]
DEFAULT_BASES = {"alone": None, "elo": "p_elo", "market": "p_mkt"}
COPIES = R.COPIES
SEED = R.SEED
MIN_TRAIN = R.MIN_TRAIN
WINDOWS = R.WINDOWS
ERAS = R.ERAS
LEVEL_GROUPS = R.LEVEL_GROUPS
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The pool

def load_pool(extra: list[str] | None = None) -> pd.DataFrame:
    """The Stage 4 pool: one row per evaluation-level match of 2010-2026 (completed or retired), in the table's
    order, with the result, surface Elo's and the market's probabilities, the level group and the era. ``extra``
    adds Stage 4 feature columns (e.g. "rating_matchup|single") for comparisons."""
    cols = POOL_COLS + [c for c in (extra or []) if c not in POOL_COLS]
    f = pd.read_parquet(STAGE4_FEATURES, columns=cols)
    f["tournament_date"] = R.cluster_dates(f)
    f["era"] = f["era"].astype(object).fillna("").astype(str)
    return f


def pool_matches() -> pd.DataFrame:
    """The pool matches joined to Stage 0's match table (one row per match, the pool's order): tournament keys,
    players, surface, status, format, score, minutes."""
    pool = load_pool()
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "round", "round_order",
                        "surface", "best_of", "format", "status", "minutes", "tournament_id", "tournament_name",
                        "tournament_date", "player_a_id", "player_b_id", "a_won", "has_box"])
    m = m.set_index("match_id").reindex(pool["match_id"]).reset_index()
    assert m["match_id"].notna().all()
    return m


def task(tour: str, cid: str, form: str, name: str, group: str, cols: list[str], scores=("alone", "elo", "market"),
         wta_box_from_2019: bool = False, interaction: bool = False, bases: dict | None = None) -> dict:
    """One row to score: a candidate in one form, for one tour. ``bases`` maps each score name to the column of the
    baseline probability (None for a coin); the default is alone / elo / market."""
    b = dict(DEFAULT_BASES)
    if bases:
        b.update(bases)
    return {"tour": tour, "id": cid, "form": form, "name": name, "group": group, "cols": list(cols),
            "scores": list(scores), "bases": {s: b[s] for s in scores},
            "from": C.WTA_BOX_FROM if (tour == "wta" and wta_box_from_2019) else C.EVAL_YEARS[0],
            "interaction": bool(interaction)}


# ------------------------------------------------------------------------------------------------
# Scoring one row (stage4_rundown.score_row with any base column)

_D: dict = {}


def init_worker(path: str) -> None:
    f = pd.read_parquet(path)
    f["tournament_date"] = R.cluster_dates(f)
    f["era"] = f["era"].astype(object).fillna("").astype(str)
    _D["f"] = f
    _D["keys"] = np.random.default_rng(SEED).random((len(f), COPIES))
    for t in C.TOURS:
        _D[t] = np.flatnonzero(f["tour"].to_numpy() == t)


def base_logit(f: pd.DataFrame, col: str | None, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The log-odds of a baseline probability column on the rows idx, and where it exists."""
    if col is None:
        return np.zeros(len(idx)), np.ones(len(idx), dtype=bool)
    p = f[col].to_numpy(dtype="float64")[idx]
    has = np.isfinite(p)
    return logit(np.clip(np.nan_to_num(p, nan=0.5), 1e-9, 1 - 1e-9)), has


def score_row(t: dict) -> dict:
    f = _D["f"]
    idx_t = _D[t["tour"]]
    year_all = f["year"].to_numpy()[idx_t]
    X = np.column_stack([f[c].to_numpy(dtype="float64")[idx_t] for c in t["cols"]])
    exists = np.isfinite(X).all(axis=1)
    idx = idx_t[exists]
    Xe = X[exists]
    year = year_all[exists]
    assert (np.diff(year) >= 0).all()
    y = f["a_won"].to_numpy()[idx]
    ev = f["evaluation"].to_numpy()[idx]
    era = f["era"].astype(object).to_numpy()[idx]
    group = f["group"].to_numpy()[idx]
    dates = R.cluster_dates(f)[idx]
    first = t["from"]
    seasons = list(range(first, C.EVAL_YEARS[-1] + 1))
    out = {k: t[k] for k in ("tour", "id", "form", "name", "group", "from", "cols", "bases")}
    sd = Xe.std(axis=0)
    out["constant"] = bool((sd == 0).any())
    ev_t = f["evaluation"].to_numpy()[idx_t] & (year_all >= first)
    out["eligible"], out["exists"] = {}, {}
    for s, col in t["bases"].items():
        _, has_t = base_logit(f, col, idx_t)
        out["eligible"][s] = int((ev_t & has_t).sum())
        out["exists"][s] = int((ev_t & has_t & exists).sum())
    era_t, grp_t = f["era"].to_numpy()[idx_t], f["group"].to_numpy()[idx_t]
    gm_t = {"all": np.ones(len(idx_t), dtype=bool)}
    for w, (a, b) in WINDOWS.items():
        gm_t[w] = (year_all >= a) & (year_all <= b)
    for e in ERAS:
        gm_t[e] = era_t == e
    for g in LEVEL_GROUPS:
        gm_t[g] = grp_t == g
    for Y in seasons:
        gm_t[f"season {Y}"] = year_all == Y
    out["eligible_by_group"] = {}
    for g, m in gm_t.items():
        out["eligible_by_group"][g] = {}
        for s, col in t["bases"].items():
            _, has_t = base_logit(f, col, idx_t)
            out["eligible_by_group"][g][s] = int((ev_t & has_t & m).sum())
    out["scores"] = {}
    if out["constant"]:
        return out
    Xs = Xe  # walk() owns the training-only scales
    keys = _D["keys"][idx]
    copies = R.shuffled(Xs, year, keys)
    allX = np.concatenate([Xs[None], copies], axis=0)
    groups_t = {"all": np.ones(len(idx), dtype=bool)}
    for w, (a, b) in WINDOWS.items():
        groups_t[w] = (year >= a) & (year <= b)
    for e in ERAS:
        groups_t[e] = era == e
    for g in LEVEL_GROUPS:
        groups_t[g] = group == g
    for Y in seasons:
        groups_t[f"season {Y}"] = year == Y
    for score, col in t["bases"].items():
        lb, has = base_logit(f, col, idx)
        sub = has
        if sub.sum() < MIN_TRAIN:
            continue
        ys, yr = y[sub], year[sub]
        if col is None:
            Z, base = allX[:, sub, :], None
        elif t["interaction"]:
            base = lb[sub]
            Z = np.concatenate([np.broadcast_to(base[None, :, None], (COPIES + 1, len(base), 1)),
                                allX[:, sub, :] * base[None, :, None]], axis=2)
        else:
            base = lb[sub]
            Z = np.concatenate([np.broadcast_to(base[None, :, None], (COPIES + 1, len(base), 1)), allX[:, sub, :]], axis=2)
        Z = np.ascontiguousarray(Z)
        w = R.walk(Z, ys, yr, seasons, base)
        d = w["llb"][None, :] - w["llm"]
        scored = np.isfinite(d[0]) & ev[sub]
        res = {"seasons_scored": w["scored"], "skipped_seasons": w["skipped"],
               "not_scored_for_training": int(sum(v["matches"] for v in w["skipped"].values())), "groups": {},
               "separated_real": w["separated_real"], "separated_copies": w["separated_copies"], "coefs": w["coefs"]}
        for gname, gm in groups_t.items():
            res["groups"][gname] = R.summarize(d, scored & gm[sub], dates[sub], w["llraw"] - w["llm"][0])
        if col is not None:                                   # direction: the model refitted inside each group
            dirs = {}
            for gname, gm in groups_t.items():
                if gname in WINDOWS or gname.startswith("season "):
                    continue
                m = scored & gm[sub]
                if m.sum() < 30 or (Z[0][m][:, 1:].std(axis=0) == 0).any():
                    continue
                direction_z = Z[0][m].copy()
                direction_z[:, 1:] /= direction_z[:, 1:].std(axis=0)
                b, se = R.fit_se(direction_z, ys[m])
                dirs[gname] = {"n": int(m.sum()), "coef": [float(v) for v in b[1:]], "lo": [float(v) for v in (b - 1.96 * se)[1:]],
                               "hi": [float(v) for v in (b + 1.96 * se)[1:]], "base_coef": float(b[0])}
            res["direction"] = dirs
        out["scores"][score] = res
    return out


# ------------------------------------------------------------------------------------------------
# The rundown: every task, the family line, the reading, the files

def reading_of(rec: dict, r: dict, key: str = "elo") -> str:
    e = r["scores"].get(key)
    if r["constant"]:
        return "no information (constant)"
    if not e or e["groups"]["all"].get("n", 0) == 0:
        return "not scored"
    g = e["groups"]["all"]
    positive = g.get("imp", 0) > 0
    if (rec[f"{key}_clears_line"] and positive and g.get("lo", np.nan) > 0
            and g.get("ci_method") == "paired_four_week_cluster_t" and rec["eras_positive"] >= 3):
        return "finding"
    if rec[f"{key}_above_band"] and positive:
        return "possible"
    if rec[f"{key}_below_band"] or g.get("imp", 0) < 0:
        return "worse"
    return "no sign"


def rundown(frame_path: Path, tasks: list[dict], prefix: Path, workers: int | None = None,
            reading_base: str = "elo") -> dict:
    """Score every task on the frame at ``frame_path`` (the pool columns plus the feature columns) and write
    <prefix>_ranking.csv (one row per task), <prefix>_results.csv (one row per task x score x group),
    <prefix>_null_copies.csv and <prefix>_results.json (every row's full result and the family lines).
    Returns {"rows": [...], "lines": {...}, "ranking": DataFrame}."""
    workers = workers or max(1, min(6, (os.cpu_count() or 2) - 2))
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    log(f"{len(tasks)} rows to score with {workers} workers")
    results = []
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker, initargs=(str(frame_path),)) as ex:
        for i, r in enumerate(ex.map(score_row, tasks, chunksize=1)):
            results.append(r)
            if (i + 1) % 25 == 0:
                log(f"  scored {i + 1} of {len(tasks)}")
    scores = sorted({s for r in results for s in r["bases"]}, key=lambda s: (s != "alone", s != "elo", s != "market", s))
    lines = {f"{t}|{s}": R.family_line(results, t, s) for t in C.TOURS for s in scores
             if sum(1 for r in results if r["tour"] == t and s in r["scores"]) >= 2}
    ranking, long, copies = [], [], []
    for r in results:
        base = {k: r[k] for k in ("tour", "id", "form", "name", "group")}
        rec = {**base, "inputs": len(r["cols"]), "scored_from": r["from"], "constant": r["constant"]}
        for s in scores:
            if s not in r["bases"]:
                continue
            sc = r["scores"].get(s)
            g = sc["groups"]["all"] if sc else {}
            rec[f"{s}_eligible"] = r["eligible"][s]
            rec[f"{s}_exists"] = r["exists"][s]
            rec[f"{s}_scored"] = g.get("n", 0)
            rec[f"{s}_coverage"] = g.get("n", 0) / r["eligible"][s] if r["eligible"][s] else np.nan
            for k in R.SUMMARY_METRICS:
                rec[f"{s}_{k}"] = g.get(k, np.nan)
            rec[f"{s}_above_band"] = g.get("above_band")
            rec[f"{s}_below_band"] = g.get("below_band")
            ln = lines.get(f"{r['tour']}|{s}")
            rec[f"{s}_clears_line"] = R.clears_heuristic_line(g, ln)
            rec[f"{s}_observed"] = R.observed_category(s if s == "alone" else "elo", g) if not r["constant"] else "none (constant)"
            for w in WINDOWS:
                gw = sc["groups"].get(w, {}) if sc else {}
                rec[f"{s}_{w}"] = gw.get("imp", np.nan)
                rec[f"{s}_{w}_n"] = gw.get("n", 0)
            if sc:
                rec[f"{s}_not_scored_for_training"] = sc["not_scored_for_training"]
                rec[f"{s}_skipped_seasons"] = "; ".join(
                    f"{yv} ({v['matches']} matches; training {v['training']}, non-zero {v['training_nonzero']})"
                    for yv, v in sc["skipped_seasons"].items())
                rec[f"{s}_separated_real"] = sc["separated_real"]
                rec[f"{s}_separated_copies"] = sc["separated_copies"]
                d_all = sc.get("direction", {}).get("all")
                rec[f"{s}_coef"] = d_all["coef"][0] if d_all else np.nan
                rec[f"{s}_coef_lo"] = d_all["lo"][0] if d_all else np.nan
                rec[f"{s}_coef_hi"] = d_all["hi"][0] if d_all else np.nan
                for gname, gg in sc["groups"].items():
                    if gg.get("n", 0) == 0:
                        continue
                    kind = ("all" if gname == "all" else "window" if gname in WINDOWS else "era" if gname in ERAS
                            else "season" if gname.startswith("season ") else "level")
                    elig = r["eligible_by_group"][gname][s]
                    row = {**base, "score": s, "group_kind": kind, "group_name": gname, "eligible": elig,
                           "coverage": gg["n"] / elig if elig else np.nan,
                           **{k: gg.get(k) for k in ("n", *R.SUMMARY_METRICS, "above_band", "below_band", "directional")}}
                    if kind == "season":
                        cf = sc["coefs"].get(int(gname.split()[1]))
                        if cf:
                            row.update({"walk_coef": cf["feature"][0], "walk_base_in_model": cf["base_in_model"],
                                        "walk_base_alone": cf["base_alone"]})
                    dr = sc.get("direction", {}).get(gname)
                    if dr:
                        row.update({"coef": dr["coef"][0], "coef_lo": dr["lo"][0], "coef_hi": dr["hi"][0]})
                    long.append(row)
                gall = sc["groups"]["all"]
                if gall.get("n", 0):
                    copies.append({**base, "score": s, **{f"copy_{c + 1}": v for c, v in enumerate(gall["copies"])}})
        e = r["scores"].get(reading_base)
        eras_pos = [x for x in ERAS if e and e["groups"].get(x, {}).get("n", 0) and e["groups"][x]["imp"] > 0]
        rec["eras_scored"] = len([x for x in ERAS if e and e["groups"].get(x, {}).get("n", 0)])
        rec["eras_positive"] = len(eras_pos)
        d_all = (e or {}).get("direction", {}).get("all")
        rec["sign_observed"] = (None if not d_all else ("+" if d_all["lo"][0] > 0 else ("−" if d_all["hi"][0] < 0 else "unclear")))
        rec["reading"] = reading_of(rec, r, reading_base) if reading_base in r["bases"] else "not read"
        ranking.append(rec)
    rank = pd.DataFrame(ranking)
    if f"{reading_base}_imp" in rank:
        rank["rank_given_base"] = rank.groupby("tour")[f"{reading_base}_imp"].rank(ascending=False, method="first")
        rank = rank.sort_values(["tour", "rank_given_base"]).reset_index(drop=True)
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    rank.to_csv(f"{prefix}_ranking.csv", index=False)
    pd.DataFrame(long).to_csv(f"{prefix}_results.csv", index=False)
    pd.DataFrame(copies).to_csv(f"{prefix}_null_copies.csv", index=False)
    Path(f"{prefix}_results.json").write_text(json.dumps({"rows": results, "lines": lines, "scores": scores,
                                                          "evaluation_protocol": R.EVALUATION_PROTOCOL,
                                                          "reading_base": reading_base,
                                                          "frame": str(frame_path)}, default=float),
                                              encoding="utf-8")
    log(f"wrote {prefix}_ranking.csv ({len(rank)} rows), _results.csv, _null_copies.csv, _results.json")
    return {"rows": results, "lines": lines, "ranking": rank}


def score_plain(f: pd.DataFrame, t: dict) -> dict:
    """The real feature's scores over all its scored seasons (no copies), for quick checks and leak checks."""
    tt = f["tour"].to_numpy() == t["tour"]
    X = np.column_stack([f[c].to_numpy(dtype="float64") for c in t["cols"]])
    ex = tt & np.isfinite(X).all(axis=1)
    idx = np.flatnonzero(ex)
    Xe = X[idx]
    Xs = Xe
    dates = R.cluster_dates(f)[idx]
    year, y, ev = f["year"].to_numpy()[idx], f["a_won"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
    seasons = list(range(t["from"], C.EVAL_YEARS[-1] + 1))
    out = {}
    for score, col in t["bases"].items():
        lb, has = base_logit(f, col, idx)
        sub = has
        if col is None:
            Z, base = Xs[sub][None], None
        elif t.get("interaction"):
            base = lb[sub]
            Z = np.concatenate([base[:, None], Xe[sub] * base[:, None]], axis=1)[None]
        else:
            base = lb[sub]
            Z = np.concatenate([base[:, None], Xs[sub]], axis=1)[None]
        w = R.walk(np.ascontiguousarray(Z), y[sub], year[sub], seasons, base)
        d = (w["llb"][None, :] - w["llm"])
        m = np.isfinite(d[0]) & ev[sub]
        out[score] = {**R.summarize(d, m, dates[sub], w["llraw"] - w["llm"][0]), "coefs": w["coefs"]}
    return out


def stage4_reference(ids: list[str] | None = None) -> pd.DataFrame:
    """The earlier study's ranking (stage4_ranking.csv), for side-by-side comparisons."""
    r = pd.read_csv(STAGE4_RANKING)
    return r if ids is None else r[r["id"].isin(ids)]
