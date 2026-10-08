"""Anchor on the closing odds, nudge with features: which way of using the odds works, and with what.

Men's main tour. For each anchor (average closing, Pinnacle closing) and each nudge set, annual
expanding logistic fits (ridge on the nudges picked on the prior two seasons, as the audit does):
  offset  logit p = logit(market) + sum g x      (anchor slope fixed at 1)
  free    logit p = b logit(market) + sum g x    (anchor slope unpenalized)
  stack   logit p = b logit(market) + c logit(sporting forecast)  -- a two-input meta-combiner
Then encompassing regressions (does a sporting forecast carry anything the market lacks?) and the
2026 test with the one TabPFN forecast. Run: ./python.sh src/eda/market_anchoring/anchor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C

WINDOWS = {"2019_2025": (2019, 2025), "2022_2025": (2022, 2025), "2026": (2026, 2026), "2019_2026": (2019, 2026)}
NUDGES = {
    "elo_blend": ["elo_logit"],
    "elo_overall": ["elo_overall"],
    "elo_surface_gap": ["elo_surface_gap"],
    "elo_overall_and_gap": ["elo_overall", "elo_surface_gap"],
    "strong9": C.STRONG,
    "frontier_surface4": C.FEATURE_GROUPS["surface_specialization"],
    "sports36": C.SPORTS,
    "profile16": C.PROFILE,
    "profile16_context": C.PROFILE + [C.E.SR] + C.E.CONTEXT,
    "sports36_profile16": C.SPORTS + C.PROFILE,
}


def window_mask(frame, name):
    lo, hi = WINDOWS[name]
    return frame.year.between(lo, hi).to_numpy()


def nudge_runs(frame):
    rows, preds = [], {}
    for anchor, column in (("average", "p_avg_a"), ("pinnacle", "p_ps_a")):
        raw = frame[column].to_numpy(dtype=float)
        cal = C.calibrated(frame, column)
        preds[f"{anchor}|raw"], preds[f"{anchor}|calibrated"] = raw, cal
        for name, cols in NUDGES.items():
            for form, fixed in (("offset", True), ("free", False)):
                p = C.walk(frame, cols, column, fixed)
                preds[f"{anchor}|{name}|{form}"] = p
                for window in WINDOWS:
                    mask = window_mask(frame, window) & np.isfinite(p) & np.isfinite(cal)
                    if anchor == "pinnacle" and window in ("2026", "2019_2026"):
                        continue
                    for ref_name, ref in (("raw", raw), ("calibrated", cal)):
                        rows.append({"anchor": anchor, "nudge": name, "form": form, "window": window,
                                     "versus": f"{ref_name} {anchor}", **C.gain(frame, p, ref, mask)})
            print(f"{anchor} {name}", flush=True)
    return pd.DataFrame(rows), preds


def stack_runs(frame, preds):
    """Two-input combiner of the market and the annual out-of-sample sporting forecast."""
    rows = []
    g = frame.copy()
    g["sport36_logit"] = C.clip_logit(g.p_sport36)
    g["sport9_logit"] = C.clip_logit(g.p_sport9)
    for anchor, column in (("average", "p_avg_a"), ("pinnacle", "p_ps_a")):
        raw = g[column].to_numpy(dtype=float)
        cal = preds[f"{anchor}|calibrated"]
        for name, cols in (("stack_sport36", ["sport36_logit"]), ("stack_sport9", ["sport9_logit"])):
            # Forecasts exist from 2019, so stacks train from 2019 and score from 2020.
            p = C.walk(g, cols, column, False, train_from=2019)
            preds[f"{anchor}|{name}|free"] = p
            for window in ("2019_2025", "2022_2025", "2026", "2019_2026"):
                if anchor == "pinnacle" and window in ("2026", "2019_2026"):
                    continue
                mask = window_mask(g, window) & g.year.ge(2020).to_numpy() & np.isfinite(p)
                for ref_name, ref in (("raw", raw), ("calibrated", cal)):
                    rows.append({"anchor": anchor, "nudge": name, "form": "free", "window": window + "_from2020",
                                 "versus": f"{ref_name} {anchor}", **C.gain(g, p, ref, mask)})
    return pd.DataFrame(rows)


def encompassing(frame):
    """y ~ b logit(market) + c logit(sporting) by year: c > 0 means the forecast adds to the market."""
    out = []
    for anchor, column in (("average", "mkt_avg"), ("pinnacle", "mkt_ps")):
        for sport in ("p_sport36", "p_sport9"):
            for label, years in [("2019_2025", range(2019, 2026)), ("2026", [2026])] + [(str(y), [y]) for y in range(2019, 2027)]:
                g = frame[frame.year.isin(list(years)) & np.isfinite(frame[column]) & np.isfinite(frame[sport])]
                if len(g) < 200:
                    continue
                x = np.column_stack([g[column], C.clip_logit(g[sport])])
                beta, se = C.cluster_logit(x, g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
                out.append({"anchor": anchor, "sport": sport, "years": label, "n": len(g),
                            "market_coef": beta[0], "market_se": se[0], "sport_coef": beta[1], "sport_se": se[1],
                            "sport_z": beta[1] / se[1]})
    # 2026: the one TabPFN fit and its logistic twin
    g = frame[frame.year.eq(2026)]
    for sport in ("tabpfn", "p_sport36"):
        x = np.column_stack([g.mkt_avg, C.clip_logit(g[sport])])
        beta, se = C.cluster_logit(x, g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
        out.append({"anchor": "average", "sport": sport, "years": "2026_tabpfn_rows", "n": len(g),
                    "market_coef": beta[0], "market_se": se[0], "sport_coef": beta[1], "sport_se": se[1],
                    "sport_z": beta[1] / se[1]})
    return pd.DataFrame(out)


def tabpfn_2026(frame, preds):
    """Stack the 2026 TabPFN forecast on the average closing price.

    (a) weights learned on 2019-2025 with the logistic 36-input forecast in TabPFN's slot (a proxy:
        TabPFN has no out-of-sample history); (b) weights cross-fitted inside 2026, leaving out one
        four-week block at a time.
    """
    y = frame.a_won.to_numpy(dtype=float)
    test = frame.year.eq(2026).to_numpy()
    train = frame.year.between(2019, 2025).to_numpy() & np.isfinite(frame.mkt_avg) & np.isfinite(frame.p_sport36)
    xt = np.column_stack([frame.mkt_avg[train], C.clip_logit(frame.p_sport36[train])])
    beta = C.P.fit_logistic(xt, y[train], np.zeros(train.sum()), np.zeros(2))
    rows, out = [], {}
    raw, cal = frame.p_avg_a.to_numpy(), preds["average|calibrated"]
    for sport in ("tabpfn", "p_sport36"):
        x = np.column_stack([frame.mkt_avg, C.clip_logit(frame[sport])])
        p = np.full(len(frame), np.nan)
        p[test] = expit(x[test] @ beta)
        out[f"stack_pre2026_weights|{sport}"] = p
        # cross-fitted within 2026
        q = np.full(len(frame), np.nan)
        blocks = frame.block4week.to_numpy()
        for b in np.unique(blocks[test]):
            fit = test & (blocks != b)
            hold = test & (blocks == b)
            bb = C.P.fit_logistic(x[fit], y[fit], np.zeros(fit.sum()), np.zeros(2))
            q[hold] = expit(x[hold] @ bb)
        out[f"stack_crossfit2026|{sport}"] = q
    out["sport_alone|tabpfn"] = frame.tabpfn.to_numpy()
    out["sport_alone|p_sport36"] = frame.p_sport36.to_numpy()
    for name, p in out.items():
        for ref_name, ref in (("raw average", raw), ("calibrated average", cal)):
            rows.append({"model": name, "versus": ref_name, **C.gain(frame, p, ref, test)})
    return pd.DataFrame(rows), {"pre2026_weights": {"market": beta[0], "sport": beta[1],
                                                    "train_rows": int(train.sum())}}


def main():
    C.OUT.mkdir(parents=True, exist_ok=True)
    frame = C.load_atp()
    print(f"{len(frame):,} men's matches, {frame.year.min()}-{frame.year.max()}", flush=True)
    results, preds = nudge_runs(frame)
    stacks = stack_runs(frame, preds)
    enc = encompassing(frame)
    tab, meta = tabpfn_2026(frame, preds)
    pd.concat([results, stacks], ignore_index=True).to_csv(C.OUT / "anchor_results.csv", index=False)
    enc.to_csv(C.OUT / "anchor_encompassing.csv", index=False)
    tab.to_csv(C.OUT / "anchor_tabpfn2026.csv", index=False)
    save = frame[["match_id", "year", "tournament_date", "surface", "a_won", "block4week"]].copy()
    for name, p in preds.items():
        save[name] = p
    save.to_parquet(C.OUT / "anchor_predictions.parquet", index=False)
    C.write_json(C.OUT / "anchor_summary.json", {
        "rows": len(frame), "years": [int(frame.year.min()), int(frame.year.max())],
        "nudge_sets": NUDGES, "windows": WINDOWS, "tabpfn": meta,
        "method": "annual expanding fits from 2013 (stacks from 2019); ridge on nudges picked on prior two "
                  "seasons; anchor slope fixed (offset) or unpenalized (free); no intercept; 4-week clustered "
                  "paired intervals",
        "limits": ["Closing prices from tennis-data.co.uk, not timestamped executable quotes",
                   "Pinnacle ends 13 Jan 2026; 2026 uses the average closing price",
                   "Seasons 2019-2026 were inspected by earlier studies; not an untouched holdout"]})
    show = pd.concat([results, stacks])
    show = show[show.versus.str.startswith("calibrated")]
    print(show.pivot_table(index=["nudge", "form"], columns=["anchor", "window"], values="gain_mll").round(2).to_string())
    print(enc[enc.years.isin(["2019_2025", "2026", "2026_tabpfn_rows"])].round(3).to_string())
    print(tab.round(3).to_string())


if __name__ == "__main__":
    main()
