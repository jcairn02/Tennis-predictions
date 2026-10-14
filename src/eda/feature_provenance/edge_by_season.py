"""The current best model's stage 1 against the closing price, season by season, 2014-2024 (feature-provenance study).

Question: is the edge spread over the seasons, or does it sit in the seasons whose results shaped the inputs? The
forecasts already exist: the 58-input local TabPFN-3.5, fitted for season Y on 2013..Y-1, stored by the
feature-interactions study (data/studies/feature_interactions/local/) and the surface-rating race
(data/studies/surface_rating_race/local/, seeds 0-2, preferred where both exist; identical in 2019). Nothing is fitted
here except one-coefficient calibration slopes.

Only seasons up to 2024 are read. The frame is loaded with a season <= 2024 filter and asserted; no forecast file of
2025 or 2026 is opened. Those seasons' figures in the write-up are copied from the studies that computed them.

Conventions, as in the repo:
    symmetrise   0.5 * (p_stored + 1 - p_swapped)                          (tabpfn_thinking/common.py)
    log loss     probabilities clipped at 1e-9; logits at 1e-6            (tabpfn_thinking, serve_speed_tabpfn)
    slopes       logistic through the origin on the log-odds, one per tour, debut seasons left out
    interval     paired cluster t over four-week blocks of tournament dates from 2010-01-04

Variants (the model and the close are recalibrated the same way in each):
    wf2014_s02   slopes fitted on 2014..Y-1, seeds 0-2 for every season (the main variant: the same number of seeds
                 averaged in every season, so the eras compare like with like)
    wf2014_all   the same slopes applied to the mean over every stored seed (3 to 16 per season)
    decided      the decided rule, slopes on 2019..Y-1, seeds 0-3 (2020 onward only)
    raw          no recalibration, seeds 0-2
    inwindow_s02 pooled windows only: slopes fitted on the window itself (in-sample), seeds 0-2. A reproduction
                 check of the feature-interactions ledger (row 2: +0.33 on 2014-2021, +1.30 on 2022-2024)

Writes data/studies/feature_provenance/edge_by_season.csv (per season and tour), edge_pooled.csv (windows) and
edge_meta.json (training sizes and seeds per season).
Run: ./python.sh src/eda/feature_provenance/edge_by_season.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "feature_provenance"
FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
RACE = ROOT / "data" / "studies" / "surface_rating_race" / "local"
FI = ROOT / "data" / "studies" / "feature_interactions" / "local"
SEASONS = list(range(2014, 2025))
LAST_SEASON = 2024
BLOCK_ORIGIN = np.datetime64("2010-01-04")
WINDOWS = {"2015-2019": range(2015, 2020), "2020-2021": range(2020, 2022), "2015-2021": range(2015, 2022),
           "2022-2024": range(2022, 2025), "2020-2024": range(2020, 2025), "2014-2021": range(2014, 2022)}


def lg(p):
    return logit(np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6))


def log_loss(p, y):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return np.where(np.asarray(y, bool), -np.log(p), -np.log(1 - p))


def paired(d, clusters):
    """Mean of d in milli-units with a cluster t interval (clusters = four-week blocks)."""
    d = np.asarray(d, float)
    labels, ix = np.unique(clusters, return_inverse=True)
    n, g = len(d), len(labels)
    m = d.mean()
    infl = np.bincount(ix, weights=d - m)
    se = np.sqrt(g / (g - 1) * np.dot(infl, infl)) / n
    r = student_t.ppf(0.975, g - 1) * se
    return 1000 * m, 1000 * (m - r), 1000 * (m + r), g


def fit_slope(z, y, iters=100):
    """Logistic regression through the origin: P = expit(b * z)."""
    b = 0.0
    for _ in range(iters):
        p = expit(z * b)
        step = float(np.clip((np.dot(z, y - p) - 1e-8 * b) / (np.dot(z * z, p * (1 - p)) + 1e-8), -4, 4))
        b += step
        if abs(step) < 1e-12:
            break
    return b


def load_frame() -> pd.DataFrame:
    tab = pq.read_table(FRAME, columns=["match_id", "tour", "season", "tournament_date", "a_won", "p_mkt",
                                        "debut_season"], filters=[("season", "<=", LAST_SEASON)])
    f = tab.to_pandas()
    assert f["season"].max() <= LAST_SEASON, "a season after 2024 was read"
    assert f["tournament_date"].max() <= pd.Timestamp(f"{LAST_SEASON}-12-31"), "a match after 2024 was read"
    f = f[f["season"] >= SEASONS[0]].copy()
    f["match_id"] = f["match_id"].astype(str)
    assert f["p_mkt"].notna().all()
    f["y"] = f["a_won"].astype(float)
    f["debut"] = f["debut_season"].astype(bool)
    f["block"] = (f["tournament_date"].to_numpy().astype("datetime64[D]") - BLOCK_ORIGIN).astype(int) // 28
    return f.set_index("match_id")


def load_forecast(folder: Path, season: int, seed: int):
    path = folder / f"model__{season}__seed{seed}.npz"
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        p, ids = z["p_td"].astype(float), z["ids_td"].astype(str)
    k = len(ids)
    assert len(p) == 2 * k and meta["season"] == season and meta["seed"] == seed
    return pd.Series(0.5 * (p[:k] + 1 - p[k:]), index=ids), meta


def forecasts(f: pd.DataFrame):
    """Per season: a matches x seeds table of symmetrised forecasts, and the training sizes and seeds used."""
    per_season, meta_out = {}, {}
    for s in SEASONS:
        cols, info = {}, []
        for k in range(16):
            r = load_forecast(RACE, s, k) if k <= 2 else None
            source = "surface_rating_race"
            if r is None:
                r, source = load_forecast(FI, s, k), "feature_interactions"
            if r is None:
                continue
            cols[k] = r[0]
            info.append({"seed": k, "source": source, "train_shape": list(r[1]["train_shape"])})
        table = pd.DataFrame(cols)
        ids = f.index[f["season"] == s]
        assert set(table.index) == set(ids), f"{s}: forecast ids differ from the frame's"
        table = table.reindex(ids)
        assert not table.isna().any().any() and {0, 1, 2} <= set(table.columns)
        per_season[s] = table
        meta_out[s] = {"seeds": sorted(cols), "training_rows": sorted({i["train_shape"][0] for i in info}),
                       "sources": sorted({i["source"] for i in info})}
    return per_season, meta_out


def slopes(f, col, start, season):
    """One slope per tour for column col, fitted on seasons start..season-1, debut seasons left out."""
    out = {}
    for t in ("atp", "wta"):
        m = (f["season"] >= start) & (f["season"] < season) & ~f["debut"] & (f["tour"] == t)
        out[t] = fit_slope(lg(f.loc[m, col]), f.loc[m, "y"].to_numpy()) if m.sum() >= 1000 else np.nan
    return out


def recalibrated(rows, col, sl):
    return expit(np.where(rows["tour"] == "atp", sl["atp"], sl["wta"]) * lg(rows[col]))


def variant_probs(f, rows, variant):
    """The model's and the close's probabilities for rows of one season under a variant."""
    s = int(rows["season"].iloc[0])
    if variant == "raw":
        return rows["p02"].to_numpy(), rows["p_mkt"].to_numpy()
    if variant in ("wf2014_s02", "wf2014_all"):
        if s < 2015:
            return None
        sm, sc = slopes(f, "p02", 2014, s), slopes(f, "p_mkt", 2014, s)
        col = "p02" if variant == "wf2014_s02" else "p_all"
        return recalibrated(rows, col, sm), recalibrated(rows, "p_mkt", sc)
    if variant == "decided":
        if s < 2020:
            return None
        sm, sc = slopes(f, "p03", 2019, s), slopes(f, "p_mkt", 2019, s)
        return recalibrated(rows, "p03", sm), recalibrated(rows, "p_mkt", sc)
    raise ValueError(variant)


def score(rows, q_model, q_close):
    d = log_loss(q_close, rows["y"]) - log_loss(q_model, rows["y"])
    est, lo, hi, g = paired(d, rows["block"].to_numpy())
    return {"matches": len(rows), "blocks": g, "ll_model": float(log_loss(q_model, rows["y"]).mean()),
            "ll_close": float(log_loss(q_close, rows["y"]).mean()), "gain": est, "lo": lo, "hi": hi,
            "reading": "model better" if lo > 0 else ("close better" if hi < 0 else "tie")}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    f = load_frame()
    per_season, meta = forecasts(f)
    f["p02"] = pd.concat([per_season[s][[0, 1, 2]].mean(axis=1) for s in SEASONS]).reindex(f.index)
    f["p_all"] = pd.concat([per_season[s].mean(axis=1) for s in SEASONS]).reindex(f.index)
    p03 = [per_season[s][[0, 1, 2, 3]].mean(axis=1) for s in SEASONS if 3 in per_season[s].columns]
    f["p03"] = pd.concat(p03).reindex(f.index)
    scored = f[~f["debut"]]

    variants = ("wf2014_s02", "wf2014_all", "decided", "raw")
    rows_out = []
    for s in SEASONS:
        for tour in ("both", "atp", "wta"):
            rows = scored[(scored["season"] == s) & ((scored["tour"] == tour) if tour != "both" else True)]
            if rows.empty:
                continue
            for v in variants:
                full = scored[scored["season"] == s]
                probs = variant_probs(f, full, v)
                if probs is None:
                    continue
                keep = (full["tour"] == tour).to_numpy() if tour != "both" else np.ones(len(full), bool)
                rows_out.append({"season": s, "tour": tour, "variant": v,
                                 **score(full[keep], probs[0][keep], probs[1][keep])})
    by_season = pd.DataFrame(rows_out)

    pooled_out = []
    for label, seasons in WINDOWS.items():
        for v in variants:
            parts = [scored[scored["season"] == s] for s in seasons]
            probs = [variant_probs(f, p, v) for p in parts]
            if any(pr is None for pr in probs):
                continue
            rows = pd.concat(parts)
            qm, qc = np.concatenate([p[0] for p in probs]), np.concatenate([p[1] for p in probs])
            for tour in ("both", "atp", "wta"):
                keep = (rows["tour"] == tour).to_numpy() if tour != "both" else np.ones(len(rows), bool)
                if keep.sum() == 0:
                    continue
                pooled_out.append({"window": label, "tour": tour, "variant": v,
                                   **score(rows[keep], qm[keep], qc[keep])})
    for label in ("2014-2021", "2022-2024"):         # the reproduction check: slopes fitted on the window itself
        rows = scored[scored["season"].isin(WINDOWS[label])]
        sm = {t: fit_slope(lg(rows.loc[rows["tour"] == t, "p02"]), rows.loc[rows["tour"] == t, "y"].to_numpy())
              for t in ("atp", "wta")}
        sc = {t: fit_slope(lg(rows.loc[rows["tour"] == t, "p_mkt"]), rows.loc[rows["tour"] == t, "y"].to_numpy())
              for t in ("atp", "wta")}
        pooled_out.append({"window": label, "tour": "both", "variant": "inwindow_s02",
                           **score(rows, recalibrated(rows, "p02", sm), recalibrated(rows, "p_mkt", sc))})
    pooled = pd.DataFrame(pooled_out)

    by_season.to_csv(OUT / "edge_by_season.csv", index=False)
    pooled.to_csv(OUT / "edge_pooled.csv", index=False)
    (OUT / "edge_meta.json").write_text(json.dumps(
        {"seasons": SEASONS, "last_season_read": LAST_SEASON, "frame": str(FRAME.relative_to(ROOT)),
         "per_season": {str(s): m for s, m in meta.items()},
         "units": "gain in milli-log-loss per match, close minus model: positive = the model is better; "
                  "a 95% interval spanning 0 is a tie"}, indent=1))

    with pd.option_context("display.width", 250, "display.max_rows", 400):
        show = by_season[(by_season["variant"] == "wf2014_s02")]
        print(show.round(3).to_string(index=False))
        print(pooled[pooled["variant"].isin(["wf2014_s02", "decided", "inwindow_s02"])].round(3).to_string(index=False))
        print({s: (m["seeds"][0], m["seeds"][-1], m["training_rows"]) for s, m in meta.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
