"""Part A of the tour-pooling analyst's brief (docs/studies/tour_pooling/design.md): how the two tours differ in the
model's inputs, and what the borrowsim arm actually borrows. Inputs only: no result is read anywhere in this script.

1. Scales. common.align_scales(frame, 2026): each tour's SD of the aligned arm's 39 box-score inputs over its training
   rows 2013-2025, and the ratio men's SD / women's SD. The same ratio for the inputs left on common scales (the price,
   the ratings, the 52-week points, age, workload). The ratio over 2013-2021 (the 2022 model's rows) shows whether it
   is stable. For context, each tour's average level of the statistics behind them (Stage 4's surface averages,
   2010-2018: predictability_diagnostic/stage4_constants.csv).
2. borrowsim. For the 2022, 2024 and 2026 models of each tour, from the similarity cache (common.SIM, written by
   fits.py --prepare; read here, never built):
   * the classifier's out-of-fold AUC, the expected draw, its effective size (Kish: (sum pi)^2 / sum pi^2), the shares
     of other-tour rows at pi = 1 and below 0.05;
   * which situation features tell the tours apart: the same HistGradientBoosting refitted on the season's pool with
     common.sim_features (y = women), permutation importance (AUC drop, 10 repeats) on the held-out first of the five
     folds; each feature's own held-out AUC, and each group's;
   * how the borrowed rows (each other-tour match weighted by its inclusion probability pi) differ from the other
     tour's whole pool, and from the own tour's rows: by level, surface, best of, round, season, the favourite's
     strength and missing inputs (segments.segment_frame's definitions), and in each situation feature's mean.

Writes data/studies/tour_pooling/borrow_report/: scales.csv, tour_levels.csv, sim_summary.csv, sim_importance.csv,
sim_groups.csv, sim_profile.csv, sim_means.csv, tables.md (generated) and borrow_report.json. The narrative,
borrow_report.md, is the analyst's.
Run: ./python.sh src/eda/tour_pooling/borrow_report.py [--scales-only]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tour_pooling import common as C  # noqa: E402
from src.eda.tour_pooling import segments as G  # noqa: E402

OUT = C.OUT / "borrow_report"
STAGE4_CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
SCALE_SEASON, SCALE_EARLY = 2026, 2022          # align_scales(frame, Y): training rows 2013 .. Y - 1
COMMON = ("odds_logit", "elo_games", "elo_overall", "elo_surf_offset", "ratings_iid", "points_52w", "age", "age_sq",
          "sets_14d")
SIM_SEASONS = (2022, 2024, 2026)
REPEATS = 10
STAT_NAME = {"ace": "aces", "df": "double faults", "first_in": "first serves in", "first_won": "first-serve points won",
             "second_won": "second-serve points won", "hold": "service games held", "bp_saved": "break points saved",
             "bp_faced_pg": "break points faced per service game", "brk": "return games won (breaks)",
             "bp_conv": "break points converted", "rpw_first": "return points won v first serves",
             "rpw_second": "return points won v second serves"}
FAMILY = {"form_": "2-week form (opponent-adjusted z, shrunk)", "formdef_": "2-week form, held opponents to",
          "iosO_": "surface IOS offence (log-odds)", "iosD_": "surface IOS defence (log-odds)",
          "prod_": "surface IOS matchup product"}
SIM_GROUPS = {"context: surface, level, best of, round": ("surface", "level", "best_of", "round"),
              "price and rating gaps": ("abs_odds_logit", "abs_elo_games", "abs_elo_overall", "abs_ratings_iid",
                                        "abs_elo_surf_offset"),
              "age gap": ("abs_age",),
              "workload gap (sets in 14 days)": ("abs_sets_14d",),
              "surface-season pairs": ("min_surf_season", "max_surf_season", "min_surf_layoff", "max_surf_layoff")}
PROFILE_DIMS = ("level", "surface", "best_of", "round", "season", "favourite", "missing", "surface_season")


def family(c: str) -> tuple[str, str]:
    for pre, name in FAMILY.items():
        if c.startswith(pre):
            return name, STAT_NAME.get(c[len(pre):], c[len(pre):])
    if c == "adjperf_tpw_2w":
        return "2-week form (opponent-adjusted z, shrunk)", "total points won"
    if c == "ios_points_short":
        return "short-memory IOS points matchup (log-odds)", "serve and return points"
    return "common scale", c


# ------------------------------------------------------------------------------------------------
# 1. Scales

def scales(frame: pd.DataFrame) -> pd.DataFrame:
    """Per input: each tour's SD over its training rows 2013-2025 (align_scales for the 39; the same nanstd for the
    common-scale inputs), the ratio men / women, the same ratio over 2013-2021, missing shares and median |x|."""
    rows = []
    t, s = frame["tour"].to_numpy(), frame["season"].to_numpy()
    late, early = C.align_scales(frame, SCALE_SEASON), C.align_scales(frame, SCALE_EARLY)
    for c in C.aligned_inputs() + list(COMMON):
        fam, stat = family(c)
        r = {"input": c, "group": "aligned (39)" if c in C.aligned_inputs() else "common scale", "family": fam,
             "statistic": stat}
        for label, Y, sc in (("", SCALE_SEASON, late), ("_2013_2021", SCALE_EARLY, early)):
            for tour in C.TOURS:
                m = (s >= C.TRAIN_FROM) & (s <= Y - 1) & (t == tour)
                x = frame.loc[m, f"in_{c}"].to_numpy(float)
                sd = sc[(tour, c)] if (tour, c) in sc else float(np.nanstd(x))
                r[f"sd_{tour}{label}"] = sd
                if not label:
                    r[f"missing_{tour}"] = float(np.isnan(x).mean())
                    r[f"median_abs_{tour}"] = float(np.nanmedian(np.abs(x)))
            r[f"ratio_men_women{label}"] = r[f"sd_atp{label}"] / r[f"sd_wta{label}"]
        rows.append(r)
    return pd.DataFrame(rows)


def tour_levels() -> pd.DataFrame:
    """Each tour's average of the box-score statistics (Stage 4's surface averages, 2010-2018): context for the
    scales. Shares, except break points faced per service game."""
    k = pd.read_csv(STAGE4_CONSTANTS)
    k = k[k["kind"].eq("surface average") & k["stat"].isin(list(STAT_NAME) + ["spw", "rpw"])]
    p = k.pivot_table(index="stat", columns=["tour", "surface"], values="value")
    names = {**STAT_NAME, "spw": "service points won", "rpw": "return points won"}
    out = pd.DataFrame({"statistic": [names[x] for x in p.index]}, index=p.index)
    for tour in C.TOURS:
        for surf in ("all", "Hard", "Clay", "Grass"):
            if (tour, surf) in p.columns:
                out[f"{tour}_{surf.lower()}"] = p[(tour, surf)].to_numpy()
    out["years"] = "2010-2018"
    return out.reset_index()


# ------------------------------------------------------------------------------------------------
# 2. borrowsim

def sim_summary() -> pd.DataFrame:
    rows = []
    for season in C.SEASONS:
        for tour in C.TOURS:
            path = C.sim_path(tour, season)
            if not path.exists():
                continue
            meta = C.read_json(path.with_suffix(".json"))
            pi = pd.read_parquet(path)["pi"].to_numpy()
            rows.append({"model": G.TOUR_NAME[tour], "tour": tour, "season": season,
                         "train_seasons": f"{meta['train_seasons'][0]}-{meta['train_seasons'][1]}",
                         "auc_out_of_fold": meta["auc_out_of_fold"], "n_own": meta["n_own"], "n_other": meta["n_other"],
                         "expected_borrowed": float(pi.sum()), "effective_n": float(pi.sum() ** 2 / (pi ** 2).sum()),
                         "effective_share": float(pi.sum() ** 2 / (pi ** 2).sum() / len(pi)),
                         "share_pi_one": float((pi >= 1).mean()), "share_pi_below_05": float((pi < 0.05).mean()),
                         "share_pi_below_01": float((pi < 0.01).mean()), "kappa": meta["kappa"],
                         "rows_seen": meta["n_own"] + float(pi.sum()),
                         "other_share_of_rows_seen": float(pi.sum()) / (meta["n_own"] + float(pi.sum())),
                         # coupled draws (common.train_mask): borrowsim keeps u < pi, borrow50 keeps u < 0.5, the same
                         # u, so a row is in both with probability min(pi, 0.5)
                         "expected_shared_with_borrow50": float(np.minimum(pi, 0.5).sum()),
                         "shared_share_of_borrowed": float(np.minimum(pi, 0.5).sum() / pi.sum())})
    return pd.DataFrame(rows)


def _hgb():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=31, l2_regularization=1.0,
                                          random_state=0)


def sim_importance(frame: pd.DataFrame, season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(per feature, per group): the classifier refitted on the season's pool (y = women), its held-out AUC on the
    first of common.sim_inclusion's five folds, each feature's permutation importance there (AUC drop), and each
    feature's and group's own held-out AUC (a booster on that feature or group alone)."""
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    sub = frame.loc[C.pool_mask(frame, season)]
    X = C.sim_features(sub)
    y = (sub["tour"].to_numpy() == "wta").astype(int)
    tr, te = next(StratifiedKFold(5, shuffle=True, random_state=0).split(X, y))
    clf = _hgb().fit(X.iloc[tr], y[tr])
    auc_full = float(roc_auc_score(y[te], clf.predict_proba(X.iloc[te])[:, 1]))
    pim = permutation_importance(clf, X.iloc[te], y[te], scoring="roc_auc", n_repeats=REPEATS, random_state=0)

    def alone(cols) -> float:
        m = _hgb().fit(X.iloc[tr][list(cols)], y[tr])
        return float(roc_auc_score(y[te], m.predict_proba(X.iloc[te][list(cols)])[:, 1]))

    feats = pd.DataFrame({"season": season, "feature": X.columns, "auc_full_model": auc_full,
                          "perm_auc_drop": pim.importances_mean, "perm_auc_drop_sd": pim.importances_std,
                          "auc_alone": [alone([c]) for c in X.columns],
                          "mean_men": [float(np.nanmean(X.loc[y == 0, c])) for c in X.columns],
                          "mean_women": [float(np.nanmean(X.loc[y == 1, c])) for c in X.columns]})
    groups = [{"season": season, "group": g, "features": ", ".join(cols), "auc_alone": alone(cols),
               "auc_without": alone([c for c in X.columns if c not in cols]), "auc_full_model": auc_full}
              for g, cols in SIM_GROUPS.items()]
    return feats.sort_values("perm_auc_drop", ascending=False), pd.DataFrame(groups)


def sim_profile(seg: pd.DataFrame, tour: str, season: int) -> pd.DataFrame:
    """How the borrowed rows differ from the other tour's pool and from the own tour's rows, by segment cell. pool
    share = the cell's share of the other tour's training rows; borrowed share = its share of sum pi; mean pi = the
    chance that a match of the cell is borrowed; own share = the cell's share of the own tour's training rows."""
    cache = pd.read_parquet(C.sim_path(tour, season)).astype({"match_id": str}).set_index("match_id")
    other = seg.loc[cache.index]
    pi = cache["pi"].to_numpy()
    own = seg[(seg["tour"] == tour).to_numpy() & (seg["season"] >= C.TRAIN_FROM).to_numpy()
              & (seg["season"] <= season - 1).to_numpy()]
    rows = []
    for dim in PROFILE_DIMS:
        col = G.dimension_column(dim)
        v = other[col].astype(str).to_numpy()
        vo = own[col].astype(str).to_numpy()
        for cell in G.ORDER[dim] + sorted(set(v) - set(G.ORDER[dim])):
            m = v == cell
            if not m.any() and not (vo == cell).any():
                continue
            rows.append({"model": G.TOUR_NAME[tour], "season": season, "dimension": dim, "cell": cell,
                         "n_other": int(m.sum()), "pool_share": float(m.mean()),
                         "borrowed_share": float(pi[m].sum() / pi.sum()),
                         "mean_pi": float(pi[m].mean()) if m.any() else np.nan,
                         "expected_borrowed": float(pi[m].sum()), "own_share": float((vo == cell).mean())})
    return pd.DataFrame(rows)


def sim_means(frame: pd.DataFrame, tour: str, season: int) -> pd.DataFrame:
    """Each situation feature's mean: own tour's training rows, the other tour's pool, the borrowed rows (pi-weighted);
    and the shift toward the own tour = (borrowed - pool) / (own - pool)."""
    cache = pd.read_parquet(C.sim_path(tour, season)).astype({"match_id": str})
    pool = frame.loc[C.pool_mask(frame, season)]
    X = C.sim_features(pool)
    X.index = pool["match_id"].to_numpy()
    own = (pool["tour"].to_numpy() == tour)
    pi = cache.set_index("match_id")["pi"]
    Xo = X.loc[pi.index]
    w = pi.to_numpy()
    rows = []
    for c in X.columns:
        x = Xo[c].to_numpy(float)
        ok = np.isfinite(x)
        mo, mp = float(np.nanmean(X.loc[own, c])), float(np.nanmean(x))
        mb = float(np.sum(w[ok] * x[ok]) / np.sum(w[ok]))
        rows.append({"model": G.TOUR_NAME[tour], "season": season, "feature": c, "own_mean": mo, "other_pool_mean": mp,
                     "borrowed_mean": mb, "own_sd": float(np.nanstd(X.loc[own, c])),
                     "gap_pool_sd": (mp - mo) / float(np.nanstd(X.loc[own, c])) if np.nanstd(X.loc[own, c]) > 0
                     else np.nan,
                     "gap_borrowed_sd": (mb - mo) / float(np.nanstd(X.loc[own, c])) if np.nanstd(X.loc[own, c]) > 0
                     else np.nan,
                     "share_of_gap_closed": (mp - mb) / (mp - mo) if abs(mp - mo) > 1e-12 else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The generated tables

def md_table(df: pd.DataFrame, cols: list[str], fmt: dict | None = None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c in fmt and isinstance(v, (int, float, np.integer, np.floating)) and np.isfinite(v):
                cells.append(format(v, fmt[c]))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def tables_md(sc: pd.DataFrame, lv: pd.DataFrame, summ: pd.DataFrame | None, imp: pd.DataFrame | None,
              grp: pd.DataFrame | None, prof: pd.DataFrame | None, means: pd.DataFrame | None) -> str:
    out = ["# Tour pooling, Part A: the generated tables\n",
           "Generated by `src/eda/tour_pooling/borrow_report.py`. Inputs only; no result read. The narrative is "
           "[borrow_report.md](borrow_report.md).\n",
           "## 1. Scales: men's SD / women's SD over the training rows (2013–2025)\n",
           "Ratio above 1 = the input spreads wider among men's matches. `ratio 2013–21` = the same over the 2022 "
           "model's rows.\n"]
    s = sc.sort_values(["group", "ratio_men_women"], ascending=[True, False])
    out.append(md_table(s, ["input", "group", "statistic", "sd_atp", "sd_wta", "ratio_men_women",
                            "ratio_men_women_2013_2021", "missing_atp", "missing_wta"],
                        {"sd_atp": ".3f", "sd_wta": ".3f", "ratio_men_women": ".2f",
                         "ratio_men_women_2013_2021": ".2f", "missing_atp": ".1%", "missing_wta": ".1%"}) + "\n")
    out.append("## Each tour's average level (Stage 4's surface averages, 2010–2018)\n")
    out.append(md_table(lv, ["stat", "statistic", "atp_all", "wta_all", "atp_grass", "wta_grass", "atp_clay",
                             "wta_clay"],
                        {c: ".3f" for c in ("atp_all", "wta_all", "atp_grass", "wta_grass", "atp_clay",
                                            "wta_clay")}) + "\n")
    if summ is not None and len(summ):
        out.append("## 2. borrowsim: the similarity draw by model and season\n")
        out.append(md_table(summ, ["model", "season", "auc_out_of_fold", "n_own", "n_other", "expected_borrowed",
                                   "effective_n", "share_pi_one", "share_pi_below_05", "other_share_of_rows_seen"],
                            {"auc_out_of_fold": ".3f", "expected_borrowed": ",.0f", "effective_n": ",.0f",
                             "share_pi_one": ".1%", "share_pi_below_05": ".1%", "other_share_of_rows_seen": ".1%"})
                   + "\n")
    if imp is not None and len(imp):
        out.append("## What tells the tours apart (refitted classifier, held-out fold; y = women)\n")
        out.append(md_table(imp, ["season", "feature", "auc_full_model", "perm_auc_drop", "perm_auc_drop_sd",
                                  "auc_alone", "mean_men", "mean_women"],
                            {"auc_full_model": ".3f", "perm_auc_drop": ".4f", "perm_auc_drop_sd": ".4f",
                             "auc_alone": ".3f", "mean_men": ".3f", "mean_women": ".3f"}) + "\n")
    if grp is not None and len(grp):
        out.append("### By group: AUC from the group alone, and from everything but the group\n")
        out.append(md_table(grp, ["season", "group", "auc_alone", "auc_without", "auc_full_model"],
                            {"auc_alone": ".3f", "auc_without": ".3f", "auc_full_model": ".3f"}) + "\n")
    if prof is not None and len(prof):
        out.append("## What is borrowed: shares by segment cell\n")
        out.append("pool share = the cell's share of the other tour's training rows; borrowed share = its share of "
                   "the expected draw (sum of pi); mean pi = the chance a match of that cell is borrowed; own share = "
                   "the cell's share of the own tour's training rows (where the draw aims).\n")
        out.append(md_table(prof, ["model", "season", "dimension", "cell", "n_other", "pool_share", "borrowed_share",
                                   "own_share", "mean_pi"],
                            {"pool_share": ".1%", "borrowed_share": ".1%", "own_share": ".1%", "mean_pi": ".2f"})
                   + "\n")
    if means is not None and len(means):
        out.append("## What is borrowed: situation features' means\n")
        out.append("gap = (mean − own tour's mean) / own tour's SD; share of gap closed = how far the draw moves the "
                   "other tour's mean toward the own tour's (1 = all the way).\n")
        out.append(md_table(means, ["model", "season", "feature", "own_mean", "other_pool_mean", "borrowed_mean",
                                    "gap_pool_sd", "gap_borrowed_sd", "share_of_gap_closed"],
                            {"own_mean": ".3f", "other_pool_mean": ".3f", "borrowed_mean": ".3f", "gap_pool_sd": "+.2f",
                             "gap_borrowed_sd": "+.2f", "share_of_gap_closed": ".2f"}) + "\n")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scales-only", action="store_true")
    ap.add_argument("--importance-seasons", default=",".join(map(str, SIM_SEASONS)),
                    help="seasons whose classifier is refitted for the importance tables (CPU; default 2022,2024,2026)")
    a = ap.parse_args()
    imp_seasons = tuple(int(x) for x in a.importance_seasons.split(",") if x)
    OUT.mkdir(parents=True, exist_ok=True)
    frame = C.load_frame(labels=False)
    if "a_won" in frame.columns:
        raise RuntimeError("the result column must not be read here")
    sc = scales(frame)
    lv = tour_levels()
    sc.to_csv(OUT / "scales.csv", index=False)
    lv.to_csv(OUT / "tour_levels.csv", index=False)
    C.log(f"scales: {len(sc)} inputs")
    summ = imp = grp = prof = means = None
    if not a.scales_only:
        missing = [(t, y) for y in SIM_SEASONS for t in C.TOURS if not C.sim_path(t, y).exists()]
        if missing:
            raise SystemExit(f"the similarity cache lacks {missing} ({C.SIM}); it is built by fits.py --prepare")
        summ = sim_summary()
        summ.to_csv(OUT / "sim_summary.csv", index=False)
        seg = G.segment_frame(G.frame_inputs())
        parts_i, parts_g, parts_p, parts_m = [], [], [], []
        for season in SIM_SEASONS:
            if season in imp_seasons:
                fi, gi = sim_importance(frame, season)
                parts_i.append(fi)
                parts_g.append(gi)
                C.log(f"importance {season}: held-out AUC {fi['auc_full_model'].iloc[0]:.3f}")
            for tour in C.TOURS:
                parts_p.append(sim_profile(seg, tour, season))
                parts_m.append(sim_means(frame, tour, season))
        imp, grp = pd.concat(parts_i, ignore_index=True), pd.concat(parts_g, ignore_index=True)
        prof, means = pd.concat(parts_p, ignore_index=True), pd.concat(parts_m, ignore_index=True)
        imp.to_csv(OUT / "sim_importance.csv", index=False)
        grp.to_csv(OUT / "sim_groups.csv", index=False)
        prof.to_csv(OUT / "sim_profile.csv", index=False)
        means.to_csv(OUT / "sim_means.csv", index=False)
    (OUT / "tables.md").write_text(tables_md(sc, lv, summ, imp, grp, prof, means), encoding="utf-8")
    C.write_json(OUT / "borrow_report.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "frame": C.P.model_frame.relative_to(ROOT).as_posix(), "frame_sha256": C.sha256_file(C.P.model_frame),
        "similarity_cache": C.SIM.relative_to(ROOT).as_posix(), "cache_version": getattr(C, "SIM_VERSION", None),
        "sim_features": list(C.sim_features(frame.head(1))), "importance_seasons": list(imp_seasons),
        "scale_rows": f"{C.TRAIN_FROM}-{SCALE_SEASON - 1} (align_scales(frame, {SCALE_SEASON}))",
        "results_read": False})
    C.log(f"written {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
