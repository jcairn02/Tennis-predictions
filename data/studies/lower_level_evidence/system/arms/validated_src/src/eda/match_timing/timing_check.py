"""Do the windows hold the true days? Out-of-sample coverage of timing.py's windows on exactly dated matches.

The windows of timing.py come from the exact days of each class (plus the researched rules). To see how often a window
would be wrong for a match whose day we do NOT know, the exactly dated matches are split by event into two halves (a
hash of the tournament id): class windows are computed from one half, combined with the rules exactly as timing.py
combines them, and tested on the other half; then the halves swap.

Both ways a window can miss are leak risks for the solved-together (IOS) inputs:
    true day AFTER the window's latest finish    the result is released into other matches' ratings too early
    true day BEFORE the window's earliest start  the match's own ratings are read from a solve made after it was played
Inside the window, the only cost is delay: the match's ratings are read earlier than needed, and its result reaches
others later than it could. That delay is measured too.

The event-shift rule (timing.EVENT_SHIFT_MIN) is tested the same way, each match reading its event's shift from the
other rounds of its event only, as an undated match of a partly dated event would.

Also: the agreement between sources where a match has several exact days.

Writes data/studies/match_timing/timing_check.json and timing_check_classes.csv.
Run after timing.py: ./python.sh src/eda/match_timing/timing_check.py
"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import timing as TM  # noqa: E402


def windows_from(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """timing.py's class/rule window for each test match, its class windows estimated on ``train`` only; also the
    class's typical day (the event-shift rule's reference)."""
    fine = ["tour", "level", "phase", "round", "era"]
    off = (train["exact_lo"] + train["exact_hi"]) / 2 - train["anchor"]
    w_f = {k: off[g.index].to_numpy() for k, g in train.groupby(fine)}
    w_c = {k: off[g.index].to_numpy() for k, g in train.groupby(fine[:4])}
    keys = list(zip(*[test[c] for c in fine]))
    elo = np.full(len(test), np.nan)
    ehi = np.full(len(test), np.nan)
    med = np.full(len(test), np.nan)
    cache = {}
    for i, key in enumerate(keys):
        if key not in cache:
            d = w_f.get(key)
            if d is None or len(d) < TM.MIN_CLASS:
                d = w_c.get(key[:4])
            cache[key] = TM._window(d) if d is not None and len(d) >= TM.MIN_CLASS else None
        w = cache[key]
        if w is not None:
            elo[i], ehi[i], med[i] = w["lo"], w["hi"], w["median"]
    rlo, rhi, named = TM.rule_windows(test)
    has_rule = np.isfinite(rlo) & np.isfinite(rhi)
    emp = np.isfinite(elo)
    lo = np.where(named & has_rule, rlo, np.where(emp, np.fmin(elo, rlo), rlo))
    hi = np.where(named & has_rule, rhi, np.where(emp, np.fmax(ehi, rhi), rhi))
    typ = np.where(named & has_rule, (rlo + rhi) / 2, med)
    a = test["anchor"].to_numpy()
    return a + lo, a + hi, a + typ


def main() -> int:
    t = pd.read_parquet(MT.TIMING)
    links = TM.load_links()
    ex, L = TM.exact_days(t[["match_id", "tournament_date"]], links)
    m = t[t["exact"]].drop(columns=[c for c in ("exact_lo", "exact_hi") if c in t]).merge(
        ex[["match_id", "exact_lo", "exact_hi"]], on="match_id", how="inner")
    m["era"] = TM.era_of(m["year"]).to_numpy()
    m["phase"] = np.where(m["qualifying"].astype(bool), "qual", "main")
    m["half"] = m["tournament_id"].astype(str).map(lambda s: zlib.crc32(s.encode()) % 2).to_numpy()
    m["ev"] = m["tour"].astype(str) + "|" + m["tournament_id"].astype(str) + "|" + m["tournament_date"].astype(str)
    recs = []
    for test_half in (0, 1):
        train = m[m["half"] != test_half]
        test = m[m["half"] == test_half].copy()
        es, lf, typ = windows_from(train, test)
        test["w_es"], test["w_lf"] = es, lf
        # the event-shift rule as an undated match of a partly dated event meets it: the shift is read from the OTHER
        # rounds of its event
        mid = ((test["exact_lo"] + test["exact_hi"]) / 2).to_numpy()
        sh = np.nan_to_num(TM.event_shift(test["ev"].to_numpy(), test["round"].to_numpy(), mid - typ,
                                          exclude_own_round=True))
        use = np.abs(np.round(sh)) >= TM.EVENT_SHIFT_MIN
        test["shifted"] = use
        test["s_es"] = np.where(use, np.fmin(es, es + np.floor(sh)), es)
        test["s_lf"] = np.where(use, np.fmax(lf, lf + np.ceil(sh)), lf)
        test = test[np.isfinite(es) & np.isfinite(lf)]
        test["after_window"] = test["exact_hi"] > test["w_lf"]
        test["before_window"] = test["exact_lo"] < test["w_es"]
        test["width"] = test["w_lf"] - test["w_es"] + 1
        test["release_delay"] = (test["w_lf"] - test["exact_hi"]).clip(lower=0)
        test["read_early_by"] = (test["exact_lo"] - test["w_es"]).clip(lower=0)
        recs.append(test)
    R = pd.concat(recs)
    R["missed"] = R["after_window"] | R["before_window"]
    R["missed_with_shift"] = (R["exact_hi"] > R["s_lf"]) | (R["exact_lo"] < R["s_es"])
    S2 = R[R["shifted"]]
    shift_check = {
        "matches_the_shift_applies_to": int(len(S2)),
        "missed_share_class_windows": float(S2["missed"].mean()) if len(S2) else None,
        "missed_share_with_shift": float(S2["missed_with_shift"].mean()) if len(S2) else None,
        "all_tested_missed_share_with_shift": float(R["missed_with_shift"].mean()),
        "median_added_width_days": float(((S2["s_lf"] - S2["s_es"]) - (S2["w_lf"] - S2["w_es"])).median())
        if len(S2) else None}
    by = (R.groupby(["tour", "level", "phase"])
          .agg(tested=("match_id", "size"), missed=("missed", "mean"), after_window=("after_window", "mean"),
               before_window=("before_window", "mean"), median_width=("width", "median"),
               median_release_delay=("release_delay", "median"), median_read_early_by=("read_early_by", "median"))
          .reset_index())
    by.to_csv(MT.OUT / "timing_check_classes.csv", index=False)
    # sibling windows, leave one out: each dated match's window from the OTHER dated matches of its event and round
    g = m.groupby(["ev", "round"])
    n = g["exact_lo"].transform("size")
    lo_sorted = g["exact_lo"].transform(lambda s: s.nsmallest(2).iloc[-1] if len(s) > 1 else np.nan)
    lo_min = g["exact_lo"].transform("min")
    lo_count_min = g["exact_lo"].transform(lambda s: (s == s.min()).sum())
    hi_max = g["exact_hi"].transform("max")
    hi_second = g["exact_hi"].transform(lambda s: s.nlargest(2).iloc[-1] if len(s) > 1 else np.nan)
    hi_count_max = g["exact_hi"].transform(lambda s: (s == s.max()).sum())
    loo_lo = np.where((m["exact_lo"] == lo_min) & (lo_count_min == 1), lo_sorted, lo_min)
    loo_hi = np.where((m["exact_hi"] == hi_max) & (hi_count_max == 1), hi_second, hi_max)
    others = n - 1
    margin = np.where(others >= 3, 1, 2)
    S = m.assign(s_es=loo_lo - margin, s_lf=loo_hi + margin, others=others, span=loo_hi - loo_lo)
    S = S[(S["others"] >= 1) & (S["span"] <= TM.SIBLING_SPAN)]
    S["after_window"] = S["exact_hi"] > S["s_lf"]
    S["before_window"] = S["exact_lo"] < S["s_es"]
    S["missed"] = S["after_window"] | S["before_window"]
    S["width"] = S["s_lf"] - S["s_es"] + 1
    sib = (S.groupby(["tour", "level", "phase"]).agg(tested=("match_id", "size"), missed=("missed", "mean"),
                                                     median_width=("width", "median")).reset_index())
    sib.to_csv(MT.OUT / "timing_check_siblings.csv", index=False)
    R["miss_days"] = np.where(R["after_window"], R["exact_hi"] - R["w_lf"],
                              np.where(R["before_window"], R["w_es"] - R["exact_lo"], 0))
    worst = R[R["missed"]].sort_values("miss_days", ascending=False)
    multi = L[L["usable"]].groupby("match_id").agg(n=("source", "nunique"), span=("day", lambda s: s.max() - s.min()))
    multi = multi[multi["n"] >= 2]
    out = {"tested_matches": len(R), "missed_share": float(R["missed"].mean()),
           "after_window_share": float(R["after_window"].mean()), "before_window_share": float(R["before_window"].mean()),
           "missed_by_days": worst["miss_days"].clip(upper=10).value_counts().sort_index().to_dict(),
           "worst_misses": worst.head(30)[["match_id", "level", "round", "miss_days", "after_window"]].to_dict("records"),
           "by_class": by.round(5).to_dict("records"),
           "event_shift_leave_one_round_out": shift_check,
           "sibling_windows_leave_one_out": {"tested": int(len(S)), "missed_share": float(S["missed"].mean()),
                                             "after_window_share": float(S["after_window"].mean()),
                                             "before_window_share": float(S["before_window"].mean()),
                                             "median_width": float(S["width"].median()),
                                             "by_class": sib.round(5).to_dict("records")},
           "multi_source_matches": int(len(multi)),
           "multi_source_same_day_share": float((multi["span"] == 0).mean()) if len(multi) else None,
           "multi_source_within_1_day_share": float((multi["span"] <= 1).mean()) if len(multi) else None}
    MT.jdump(out, MT.OUT / "timing_check.json")
    MT.log(f"windows tested out of sample on {len(R):,} exactly dated matches: missed {out['missed_share']:.4%} "
           f"(after the window {out['after_window_share']:.4%}, before it {out['before_window_share']:.4%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
