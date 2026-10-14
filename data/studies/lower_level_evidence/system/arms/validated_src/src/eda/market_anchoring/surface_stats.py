"""Surface statistics: how large and stable players' surface deviations are, and whether the odds price them.

Part 1 (both tours, descriptive). Per player, season and surface, each box-score statistic relative to
the tour's average on that surface. The clay-minus-hard and grass-minus-hard deviation of a player in
one season is correlated with the next season's; so is the player's all-surface level.
Part 2 (both tours). Pre-match features under the strictly-earlier-day rule, per statistic:
  level    L = S_all / (N_all + 5)                 decayed, half-life 365 days, shrunk to the tour average
  surface  M = (S_surf + 8 L) / (N_surf + 8)       decayed, half-life 730 days, shrunk to the level
  dev      M - L                                   the player's surface deviation
Each enters as A minus B. Constants fixed before scoring; no opponent adjustment.
Part 3 (men). The anchor harness: these as nudges on the closing odds, alone and beyond the profile.
Run: ./python.sh src/eda/market_anchoring/surface_stats.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C

ROWS = C.REPAIRS / "repair_rows.parquet"
# name: (numerator, denominator, taken from the opponent's row)
STATS = {"ace": ("ace_n", "ace_d", False), "df": ("df_n", "df_d", False),
         "first_in": ("first_in_n", "first_in_d", False), "first_won": ("first_won_n", "first_won_d", False),
         "second_won": ("second_won_n", "second_won_d", False), "spw": ("spw_n", "spw_d", False),
         "hold": ("hold_n", "hold_d", False), "rpw": ("rpw_n", "rpw_d", False), "brk": ("brk_n", "brk_d", False),
         "rpw_first": ("first_won_n", "first_won_d", True), "rpw_second": ("second_won_n", "second_won_d", True),
         "ace_against": ("ace_n", "ace_d", True)}
COMPLEMENT = {"rpw_first", "rpw_second"}       # opponent's points won on serve -> my return points won
HALF_ALL, HALF_SURF, K_ALL, K_SURF = 365.0, 730.0, 5.0, 8.0
MIN_UNITS = 4.0                                # Part 1: match-units per surface and season
WINDOWS = {"2019_2025": (2019, 2025), "2026": (2026, 2026), "2019_2026": (2019, 2026)}


def stat_table(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Centred log-odds values c, weights w (match-units) and eligibility, one column per statistic."""
    n_rows = len(rows)
    mate = np.arange(n_rows) ^ 1
    eligible = (rows.has_box & rows.status.eq("completed") & rows.history_format_supported).to_numpy()
    c = np.zeros((n_rows, len(STATS)))
    w = np.zeros_like(c)
    ok = np.zeros(c.shape, dtype=bool)
    tour, surface, year = rows.tour.to_numpy(), rows.surface.fillna("unknown").to_numpy(), rows.year.to_numpy()
    for j, (name, (num, den, opp)) in enumerate(STATS.items()):
        n = rows[num].to_numpy(dtype=float)
        d = rows[den].to_numpy(dtype=float)
        if opp:
            n, d = n[mate], d[mate]
        if name in COMPLEMENT:
            n = d - n
        good = eligible & np.isfinite(n) & np.isfinite(d) & (d > 0) & (n >= 0) & (n <= d)
        value = np.where(good, logit((np.where(good, n, 0) + 0.5) / (np.where(good, d, 0) + 1)), np.nan)
        frame = pd.DataFrame({"tour": tour, "surface": surface, "v": value, "d": d, "good": good & (year <= 2018)})
        sub = frame[frame.good]
        mu = ((sub.v * sub.d).groupby([sub.tour, sub.surface]).sum()
              / sub.d.groupby([sub.tour, sub.surface]).sum()).to_dict()
        overall = ((sub.v * sub.d).groupby(sub.tour).sum() / sub.d.groupby(sub.tour).sum()).to_dict()
        mus = np.array([mu.get((t, s), overall[t]) for t, s in zip(tour, surface)])
        med = frame[good].groupby("tour").d.median().to_dict()
        units = np.minimum(np.where(good, d, 0) / np.array([med[t] for t in tour]), 3.0)
        c[:, j] = np.where(good, value - mus, 0.0)
        w[:, j] = np.where(good, units, 0.0)
        ok[:, j] = good
    return c, w, ok


def decayed_snapshot(key: np.ndarray, day: np.ndarray, wv: np.ndarray, w: np.ndarray, half_life: float):
    """Decayed sums of w*c and w over the same key's rows on strictly earlier days (rows sorted by day)."""
    n, k = wv.shape
    keys = int(key.max()) + 1
    S, N, T = np.zeros((keys, k)), np.zeros((keys, k)), np.zeros(keys)
    out_s, out_n = np.empty((n, k)), np.empty((n, k))
    cuts = np.flatnonzero(np.diff(day)) + 1
    for start, stop in zip(np.r_[0, cuts], np.r_[cuts, n]):
        t = day[start]
        ks = key[start:stop]
        f = np.exp2(-(t - T[ks]) / half_life)[:, None]
        out_s[start:stop], out_n[start:stop] = S[ks] * f, N[ks] * f
        uk = np.unique(ks)
        fu = np.exp2(-(t - T[uk]) / half_life)[:, None]
        S[uk] *= fu
        N[uk] *= fu
        T[uk] = t
        np.add.at(S, ks, wv[start:stop])
        np.add.at(N, ks, w[start:stop])
    return out_s, out_n


def features(rows: pd.DataFrame, c: np.ndarray, w: np.ndarray) -> pd.DataFrame:
    day = rows.day.to_numpy()
    if np.any(np.diff(day) < 0):
        raise ValueError("Rows must be sorted by match day")
    player = pd.factorize(pd.MultiIndex.from_arrays([rows.tour, rows.player_id]))[0]
    psurf = pd.factorize(pd.MultiIndex.from_arrays([player, rows.surface.fillna("unknown")]))[0]
    s_all, n_all = decayed_snapshot(player, day, w * c, w, HALF_ALL)
    s_srf, n_srf = decayed_snapshot(psurf, day, w * c, w, HALF_SURF)
    level = s_all / (n_all + K_ALL)
    surf = (s_srf + K_SURF * level) / (n_srf + K_SURF)
    dev = surf - level
    a, b = np.arange(0, len(rows), 2), np.arange(1, len(rows), 2)
    out = {"match_id": rows.match_id.to_numpy()[a]}
    for j, name in enumerate(STATS):
        out[f"ss_level_{name}"] = level[a, j] - level[b, j]
        out[f"ss_surf_{name}"] = surf[a, j] - surf[b, j]
        out[f"ss_dev_{name}"] = dev[a, j] - dev[b, j]
    units = n_srf[:, list(STATS).index("spw")]
    out["ss_surface_evidence"] = np.log1p(units[a]) - np.log1p(units[b])
    return pd.DataFrame(out)


def persistence(rows: pd.DataFrame, c: np.ndarray, w: np.ndarray) -> pd.DataFrame:
    """Season-to-season stability of each player's surface deviation and of their all-surface level."""
    out = []
    base = pd.DataFrame({"tour": rows.tour.to_numpy(), "player": rows.player_id.to_numpy(),
                         "year": rows.year.to_numpy(), "surface": rows.surface.fillna("unknown").to_numpy()})
    for j, name in enumerate(STATS):
        g = base.assign(wc=w[:, j] * c[:, j], w=w[:, j])
        g = g[g.w > 0]
        by = g.groupby(["tour", "player", "year", "surface"])[["wc", "w"]].sum()
        by["m"] = by.wc / by.w
        wide_m = by.m.unstack("surface")
        wide_w = by.w.unstack("surface")
        lvl = g.groupby(["tour", "player", "year"])[["wc", "w"]].sum()
        lvl = (lvl.wc / lvl.w).where(lvl.w >= 2 * MIN_UNITS)
        for tour in ("atp", "wta"):
            for other in ("Clay", "Grass"):
                good = (wide_w.get(other, 0) >= MIN_UNITS) & (wide_w.get("Hard", 0) >= MIN_UNITS)
                dev = (wide_m[other] - wide_m["Hard"]).where(good).loc[tour].dropna()
                nxt = dev.rename(lambda y: y - 1, level="year")
                pair = pd.concat([dev.rename("t"), nxt.rename("t1")], axis=1, join="inner")
                lv = lvl.loc[tour].dropna()
                lpair = pd.concat([lv.rename("t"), lv.rename(lambda y: y - 1, level="year").rename("t1")],
                                  axis=1, join="inner")
                cov_d = float(np.cov(pair.t, pair.t1)[0, 1]) if len(pair) > 20 else np.nan
                cov_l = float(np.cov(lpair.t, lpair.t1)[0, 1])
                out.append({"tour": tour, "stat": name, "contrast": f"{other} - Hard", "pairs": len(pair),
                            "deviation_r": float(pair.t.corr(pair.t1)) if len(pair) > 20 else np.nan,
                            "level_pairs": len(lpair), "level_r": float(lpair.t.corr(lpair.t1)),
                            "stable_sd_deviation": float(np.sqrt(max(cov_d, 0))) if np.isfinite(cov_d) else np.nan,
                            "stable_sd_level": float(np.sqrt(max(cov_l, 0))),
                            "mean_deviation": float(pair.t.mean()) if len(pair) else np.nan})
    t = pd.DataFrame(out)
    t["deviation_to_level_sd"] = t.stable_sd_deviation / t.stable_sd_level
    return t


def nudges(feats: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    frame = C.load_atp().merge(feats, on="match_id", how="left", validate="one_to_one")
    names = list(STATS)
    sets = {"ss_dev12": [f"ss_dev_{s}" for s in names], "ss_surf12": [f"ss_surf_{s}" for s in names],
            "ss_level12": [f"ss_level_{s}" for s in names]}
    base = C.PROFILE + [C.E.SR] + C.E.CONTEXT
    rows, preds = [], {}
    for anchor, column in (("average", "p_avg_a"), ("pinnacle", "p_ps_a")):
        cal = C.calibrated(frame, column)
        ref_base = C.walk(frame, base, column, False)
        preds[f"{anchor}|profile16_context"] = ref_base
        for name, cols in sets.items():
            for label, model_cols, ref_label, ref in ((name, cols, "calibrated", cal),
                                                       (f"profile16_context+{name}", base + cols,
                                                        "profile16_context", ref_base)):
                p = C.walk(frame, model_cols, column, False)
                preds[f"{anchor}|{label}"] = p
                for window, (lo, hi) in WINDOWS.items():
                    if anchor == "pinnacle" and hi == 2026:
                        continue
                    mask = frame.year.between(lo, hi).to_numpy() & np.isfinite(ref)
                    rows.append({"anchor": anchor, "model": label, "versus": f"{ref_label} {anchor}",
                                 "window": window, **C.gain(frame, p, ref, mask)})
            print(f"{anchor} {name}", flush=True)
    # Market-free check: do the surface statistics carry signal the Elo-based nine lack?
    p9 = C.walk(frame, C.STRONG, None, True)
    for name, cols in sets.items():
        p = C.walk(frame, C.STRONG + cols, None, True)
        for window, (lo, hi) in WINDOWS.items():
            rows.append({"anchor": "none", "model": f"strong9+{name}", "versus": "strong9 (no market)",
                         "window": window, **C.gain(frame, p, p9, frame.year.between(lo, hi).to_numpy())})
    return pd.DataFrame(rows), {"frame": frame, "preds": preds}


def main():
    C.OUT.mkdir(parents=True, exist_ok=True)
    rows = pd.read_parquet(ROWS)
    if not (rows.match_id.iloc[::2].to_numpy() == rows.match_id.iloc[1::2].to_numpy()).all():
        raise ValueError("Expected A/B row pairs")
    c, w, ok = stat_table(rows)
    persist = persistence(rows, c, w)
    persist.to_csv(C.OUT / "surface_persistence.csv", index=False)
    print(persist.round(3).to_string(), flush=True)
    feats = features(rows, c, w)
    check = rows.iloc[::2][["match_id", "won"]].merge(
        pd.read_parquet(C.TABPFN / "frame.parquet", columns=["match_id", "a_won"]), on="match_id")
    if not (check.won.astype(bool) == check.a_won.astype(bool)).all():
        raise ValueError("Row side A is not the frame's player A")
    feats.to_parquet(C.OUT / "surface_stat_features.parquet", index=False)
    results, extra = nudges(feats)
    results.to_csv(C.OUT / "surface_stat_results.csv", index=False)
    save = extra["frame"][["match_id", "year", "surface", "a_won"]].copy()
    for k, v in extra["preds"].items():
        save[k] = v
    save.to_parquet(C.OUT / "surface_stat_predictions.parquet", index=False)
    C.write_json(C.OUT / "surface_stat_summary.json", {
        "stats": {k: list(v) for k, v in STATS.items()}, "half_life_days": {"level": HALF_ALL, "surface": HALF_SURF},
        "shrinkage_match_units": {"level": K_ALL, "surface": K_SURF}, "min_units_part1": MIN_UNITS,
        "centring": "log-odds of (n+1/2)/(d+1) minus the tour's 2010-2018 average on the match's surface",
        "history": "repaired dated main-tour rows; completed, supported-format, box-score matches; strictly earlier days",
        "limits": ["No opponent adjustment", "Main-tour history only (no Challengers/qualifying)",
                   "Seasons 2019-2026 previously inspected; constants fixed before this run"]})
    r = results.copy()
    r["ci"] = r.apply(lambda x: f"{x.gain_mll:+.2f} [{x.lo_mll:+.2f}, {x.hi_mll:+.2f}] n={x.n}", axis=1)
    print(r.pivot_table(index=["model", "versus"], columns=["anchor", "window"], values="ci", aggfunc="first").to_string())


if __name__ == "__main__":
    main()
