"""Build the study frame and the exact upload for the one TabPFN-3.5-Thinking fit.

Reads the earlier studies' tables (read-only; hashed before and after reading, so a table rewritten while this runs
is caught), keeps the main-tour matches with a supported pre-match format, and writes, in data/studies/tabpfn_thinking/:

    frame.parquet          every main-tour pool match of 2010-2026: ids, result, Elo's and the market's probabilities,
                           tournament date (for the interval blocks), split ("train" / "test" / "") for the free
                           models, tabpfn_split for the paid fit (the same, restricted to matches with odds), and
                           every input as in_<name>
    upload/X_train.parquet the paid fit's training inputs (common.TABPFN_NAMES order: the odds' log-odds, then the
                           features), float64 (categoricals as integer codes); training matches with odds
    upload/y_train.npy     1 if A won
    upload/X_query.parquet the test matches with odds, then the same matches with A and B swapped (common.flip)
    upload/query_ids.parquet  match_id and orientation (0 as stored, 1 swapped) of every query row
    manifest.json          sources and hashes, the design, the inputs, counts, coverage and the value fingerprint

Pre-match format (the feature-alpha audit's rule, docs/studies/feature_alpha_audit/format_rules.md, implemented
here for the main tour only so that this study does not import a module under edit): men's Grand Slam main draws are
best of five, everything else on the main tour best of three; the Next Gen Finals (short no-ad sets) and the three
Melbourne 2021 WTA events (a mid-event format change) are left out, as the audit leaves them out.

Indoor or outdoor (since 9 Oct 2026, src/eda/indoor_fill/status.py; docs/studies/indoor_fill/README.md): Stage 0's flag
for the men, the WTA's calendar for the women, tennis-data.co.uk's Court where those lack it. Before, the input was
Stage 0's flag for the men only, every women's row missing; --indoor-men-only builds it that way again.

Run: ./python.sh src/eda/tabpfn_thinking/build_frame.py [--indoor-men-only]    (about a minute)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.indoor_fill import status as IF  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

MELBOURNE_2021 = ("yarra valley classic", "gippsland trophy", "grampians trophy")
POOL_COLS = ["match_id", "tour", "year", "group", "evaluation", "status", "a_won", "p_elo", "p_mkt", "order"]
MATCH_COLS = ["match_id", "tournament_name", "tournament_id", "tournament_date", "surface", "indoor", "round",
              "round_order", "level", "qualifying", "best_of"]
DESCRIPTION = (
    "Professional tennis singles, ATP and WTA main tour (Grand Slams, Tour Finals, 1000, 500, 250 events), "
    "seasons 2013-2021; one row per match; player A is assigned at random, so the task is symmetric: swapping A and B "
    "negates the odds column and every difference column and flips the label. Target: 1 if player A won. Inputs are "
    "pre-match only: odds_logit, the bookmakers' closing log-odds that A wins (de-vigged average of the books), which "
    "is by far the strongest input; differences (A minus B) of rating systems (surface Elo log-odds, serve/return "
    "strength ratings, games-weighted Elo), opponent-adjusted serve/return statistics over a two-week memory, "
    "long-memory offence/defence ratings per statistic, recent load, age and surface familiarity; plus match context "
    "(tour, surface, indoor, level, best-of, round). The question is whether these inputs improve on the odds. "
    "Predictions will be for the later seasons 2022-2026 and are scored by log loss, so calibration matters.")


def source_hashes() -> dict:
    return {k: {"path": str(p.relative_to(ROOT)), "sha256": T.sha256_file(p), "bytes": p.stat().st_size,
                "mtime": pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat()} for k, p in T.SOURCES.items()}


def scheduled_best_of(m: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(best_of, supported) for main-tour rows from event metadata only, never the score."""
    name = m["tournament_name"].astype("string").str.lower().str.strip()
    tour = m["tour"].astype("string")
    nextgen = tour.eq("atp") & name.str.contains(r"next\s*gen", regex=True, na=False)
    melbourne = tour.eq("wta") & m["year"].eq(2021) & name.isin(MELBOURNE_2021)
    bo = np.where(tour.eq("atp") & m["group"].eq("GS"), 5, 3).astype(float)
    supported = ~(nextgen | melbourne).to_numpy()
    return bo, supported


def split_of(year: np.ndarray, keep: np.ndarray) -> np.ndarray:
    """"train" for the kept rows of TRAIN_YEARS, "test" from TEST_YEARS[0] on (no last season since 10 Oct 2026; it
    was TEST_YEARS[1]), else ""."""
    split = np.full(len(year), "", dtype=object)
    split[keep & (year >= T.TRAIN_YEARS[0]) & (year <= T.TRAIN_YEARS[1])] = "train"
    split[keep & (year >= T.TEST_YEARS[0])] = "test"
    return split


def indoor_codes(f: pd.DataFrame, m: pd.DataFrame, men_only: bool) -> tuple[np.ndarray, np.ndarray, dict]:
    """The indoor input per pool row and where it came from: the rule of src/eda/indoor_fill/status.py, or (men_only)
    Stage 0's flag for the men and missing for every women's row, as the frames before 9 Oct 2026 were built."""
    tour = f["tour"].to_numpy()
    if men_only:
        ind = m["indoor"].map({True: 1.0, False: 0.0}).astype("float64").to_numpy()
        return (np.where(tour == "atp", ind, np.nan), np.full(len(f), "men_only", dtype=object),
                {"rule": "men only: Stage 0's flag (before 9 Oct 2026)"})
    stage1 = T.sha256_file(IF.STAGE1)
    v, src = IF.for_matches(f["match_id"])
    if T.sha256_file(IF.STAGE1) != stage1:
        raise RuntimeError("Stage 1's odds table changed while the indoor rule read it; rerun when it is stable")
    main = f["group"].isin(T.MAIN_GROUPS).to_numpy()
    counts = pd.DataFrame({"tour": tour[main], "source": src.to_numpy()[main]}).value_counts().sort_index()
    return v, src.to_numpy(dtype=object), {
        "rule": "src/eda/indoor_fill/status.py (Stage 0's flag for the men, the WTA's calendar for the women, "
                "tennis-data.co.uk's Court where those lack it)",
        "stage1_odds_sha256": stage1,
        "main_tour_rows_by_source": {f"{t}|{s}": int(n) for (t, s), n in counts.items()},
        "main_tour_rows_unknown": int((~np.isfinite(v[main])).sum())}


def build(indoor_men_only: bool = False) -> tuple[pd.DataFrame, dict]:
    before = source_hashes()
    pool = pd.read_parquet(T.SOURCES["stage4"], columns=POOL_COLS)
    tables = {}
    for key in ("stageD", "stageD_profile"):
        cols = sorted({c for f in T.FEATURES if f["src"] == key
                       for c in (f["col"].values() if isinstance(f["col"], dict) else [f["col"]])})
        t = pd.read_parquet(T.SOURCES[key], columns=["match_id"] + cols)
        assert (t["match_id"].to_numpy() == pool["match_id"].to_numpy()).all(), f"{key} is not in the pool's order"
        tables[key] = t
    m = pd.read_parquet(T.SOURCES["stage0_matches"], columns=MATCH_COLS)
    m = m.set_index("match_id").reindex(pool["match_id"]).reset_index()
    assert m["tournament_date"].notna().all(), "every pool match needs its tournament date"
    after = source_hashes()
    changed = [k for k in before if before[k]["sha256"] != after[k]["sha256"]]
    if changed:
        raise RuntimeError(f"source tables changed while being read: {changed}; rerun when they are stable")

    f = pool.copy()
    f["tournament_date"] = pd.to_datetime(m["tournament_date"]).to_numpy()
    f["tournament_name"] = m["tournament_name"].to_numpy()
    f["tournament_id"] = m["tournament_id"].to_numpy()
    main = f["group"].isin(T.MAIN_GROUPS).to_numpy()
    meta = m.assign(tour=f["tour"], year=f["year"], group=f["group"])
    bo, supported = scheduled_best_of(meta)
    f["main"] = main
    f["format_supported"] = supported
    # the inputs
    tour = f["tour"].to_numpy()
    for spec in T.FEATURES:
        name, src, col = spec["name"], spec["src"], spec["col"]
        if src == "pool":
            f[name] = logit(np.clip(f[col].to_numpy(dtype="float64"), T.EPS, 1 - T.EPS))
        elif src in tables:
            if isinstance(col, dict):
                v = np.full(len(f), np.nan)
                for t_, c in col.items():
                    v = np.where(tour == t_, tables[src][c].to_numpy(dtype="float64"), v)
                f[name] = v
            else:
                f[name] = tables[src][col].to_numpy(dtype="float64")
    pm = f["p_mkt"].to_numpy(dtype="float64")
    f["odds_logit"] = np.where(np.isfinite(pm), logit(np.clip(pm, T.EPS, 1 - T.EPS)), np.nan)
    f["tour_code"] = f["tour"].map(T.CODES["tour"]).astype("float64")
    f["surface_code"] = m["surface"].map(T.CODES["surface"]).astype("float64").to_numpy()
    f["level_code"] = f["group"].map(T.CODES["level"]).astype("float64")
    # Stage 0 records indoor/outdoor for the men only (and for 17% of the women's 2026 matches). Until 9 Oct 2026 the
    # input was kept for the men only, so that no test row showed a pattern absent in training; since then the women's
    # comes from the WTA's calendar and tennis-data's Court (indoor_codes)
    f["indoor_code"], f["indoor_source"], indoor_info = indoor_codes(f, m, indoor_men_only)
    f["best_of_sched"] = bo
    f["round_code"] = m["round_order"].astype("float64").to_numpy()
    f["best_of_raw"] = m["best_of"].astype("float64").to_numpy()
    for name, src in (("tour", "tour_code"), ("surface", "surface_code"), ("level", "level_code"),
                      ("indoor", "indoor_code"), ("best_of", "best_of_sched"), ("round", "round_code")):
        f[f"x_{name}"] = f[src]
    year = f["year"].to_numpy()
    keep = main & supported & np.isin(f["status"].to_numpy(), ["completed", "retired"])
    f["split"] = split_of(year, keep)
    f = f[main].reset_index(drop=True)                      # the frame holds the main tour only
    return f, {"before": before, "after": after, "indoor_values": m["indoor"].astype(str).value_counts().to_dict(),
               "indoor": indoor_info,
               "excluded_unsupported": f.loc[~f["format_supported"]].groupby(["tour", "year", "tournament_name"])
                                       .size().reset_index(name="matches").to_dict("records")}


def model_matrix(f: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """The inputs in the given order under their model names (context from the x_ columns)."""
    cols = {}
    for name in names:
        cols[name] = f[f"x_{name}"] if name in T.CONTEXT else f[name]
    return pd.DataFrame(cols).astype("float64")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--indoor-men-only", action="store_true",
                    help="the indoor input as built before 9 Oct 2026: Stage 0's flag for the men, missing for the women")
    a = ap.parse_args()
    T.OUT.mkdir(parents=True, exist_ok=True)
    T.UPLOAD.mkdir(parents=True, exist_ok=True)
    f, info = build(a.indoor_men_only)
    X = model_matrix(f, T.TABPFN_NAMES)
    f = pd.concat([f, X.add_prefix("in_")], axis=1)          # the exact model inputs, kept beside the sources
    has = np.isfinite(f["odds_logit"].to_numpy())
    f["tabpfn_split"] = np.where(has, f["split"], "")
    T.log(f"frame: {len(f):,} main-tour matches; free models: train {int((f['split'] == 'train').sum()):,}, "
          f"test {int((f['split'] == 'test').sum()):,}; paid fit (with odds): train "
          f"{int((f['tabpfn_split'] == 'train').sum()):,}, test {int((f['tabpfn_split'] == 'test').sum()):,}")
    tr, te = (f["tabpfn_split"] == "train").to_numpy(), (f["tabpfn_split"] == "test").to_numpy()
    X_train = X[tr].reset_index(drop=True)
    y_train = f.loc[tr, "a_won"].astype("int64").to_numpy()
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, T.flip(X_test)], ignore_index=True)
    ids = pd.DataFrame({"match_id": np.r_[f.loc[te, "match_id"].to_numpy(), f.loc[te, "match_id"].to_numpy()],
                        "orientation": np.r_[np.zeros(te.sum(), int), np.ones(te.sum(), int)]})
    # checks: no label or identity among the inputs, the swap is an involution and negates exactly the differences
    assert not set(T.TABPFN_NAMES) & {"a_won", "match_id", "p_mkt", "status", "year"}
    assert np.allclose(T.flip(T.flip(X_test)).to_numpy(), X_test.to_numpy(), equal_nan=True)
    assert np.isfinite(X_train[T.DIFF].to_numpy()).mean() > 0.9
    assert np.isfinite(X_train["odds_logit"].to_numpy()).all() and np.isfinite(X_test["odds_logit"].to_numpy()).all()
    assert set(np.unique(y_train)) == {0, 1}
    f.to_parquet(T.OUT / "frame.parquet", index=False)
    X_train.to_parquet(T.UPLOAD / "X_train.parquet", index=False)
    np.save(T.UPLOAD / "y_train.npy", y_train)
    X_query.to_parquet(T.UPLOAD / "X_query.parquet", index=False)
    ids.to_parquet(T.UPLOAD / "query_ids.parquet", index=False)
    fp = T.fingerprint(X_train, y_train, X_query)
    counts = {k: (f[f[k] != ""].groupby([k, "tour", "year"]).size().rename("matches").reset_index()
                  .to_dict("records")) for k in ("split", "tabpfn_split")}
    coverage = {s: {c: float(np.isfinite(X[m_][c].to_numpy()).mean()) for c in T.TABPFN_NAMES}
                for s, m_ in (("train", tr), ("test", te))}
    with_odds = {t: int((te & (f["tour"] == t).to_numpy()).sum()) for t in T.TOURS}
    manifest = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "sources": info["before"],
        "design": {"population": "main tour (" + ", ".join(T.MAIN_GROUPS) + "), completed or retired, supported "
                                 "pre-match format", "train_years": T.TRAIN_YEARS, "test_years": T.TEST_YEARS,
                   "pooled_tours": True, "market_is_input": True,
                   "paid_fit_rows": "training and test matches with closing odds (the men's 2018 season has none)",
                   "query": "test rows as stored, then the same rows with A and B swapped"},
        "features": [T.ODDS] + T.FEATURES, "names": T.TABPFN_NAMES, "categorical": T.CATEGORICAL,
        "categorical_indices": [T.TABPFN_NAMES.index(c) for c in T.CATEGORICAL],
        "groups": {"odds": [T.ODDS["name"]], **T.GROUPS},
        "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
        "label_mean_train": float(y_train.mean()),
        "counts": counts, "test_with_odds": with_odds,
        "excluded_unsupported_format": info["excluded_unsupported"],
        "indoor_values_in_stage0": info["indoor_values"],
        "indoor": info["indoor"],
        "coverage": coverage,
        "best_of_raw_vs_scheduled_disagreements": int((np.isfinite(f["best_of_raw"]) &
                                                       (f["best_of_raw"] != f["best_of_sched"]) &
                                                       (f["split"] != "")).sum()),
        "fit_description": DESCRIPTION,
        "upload_sha256": {p.name: T.sha256_file(p) for p in sorted(T.UPLOAD.glob("*")) if p.is_file()},
        "input_fingerprint": fp,
    }
    T.write_json(T.OUT / "manifest.json", manifest)
    T.log(f"X_train {X_train.shape}, X_query {X_query.shape}; fingerprint {fp[:16]}...")
    T.log(f"test matches with odds: {with_odds}")
    T.log(f"excluded (unsupported format): {sum(r['matches'] for r in info['excluded_unsupported'])} matches")
    low = {c: round(v, 3) for c, v in coverage['train'].items() if v < 0.98}
    T.log(f"train coverage below 98%: {low}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
