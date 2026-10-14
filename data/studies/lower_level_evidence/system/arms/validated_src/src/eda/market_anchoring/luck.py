"""Conversion luck from end-of-match statistics, as nudges on the closing odds (men's main tour).

Per match, from the box score alone:
  hold luck   (games held - service games x G(p)) / service games, p = the player's serve points won rate
  break luck  (breaks - return games x (1 - G(r))) / return games, r = the opponent's serve points won rate
G is the iid game-win probability with deuce. Positive means more games than the points imply.
Each player's history is decayed (half-life 365 days) and shrunk (5 matches) under the strictly-earlier-day
rule; features are A minus B. Hypothesis fixed before scoring: the market over-credits converting points
into games, so given the odds the coefficients are negative.
Run after anchor.py: ./python.sh src/eda/market_anchoring/luck.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C
from src.eda.market_anchoring import surface_stats as S

HALF, K = 365.0, 5.0
WINDOWS = {"2019_2025": (2019, 2025), "2026": (2026, 2026), "2019_2026": (2019, 2026)}


def game_win(p: np.ndarray) -> np.ndarray:
    q = 1 - p
    return p**4 * (1 + 4 * q + 10 * q**2) + 20 * p**3 * q**3 * p**2 / (1 - 2 * p * q)


def luck_features(rows: pd.DataFrame) -> pd.DataFrame:
    mate = np.arange(len(rows)) ^ 1
    eligible = (rows.has_box & rows.status.eq("completed") & rows.history_format_supported).to_numpy()
    spw = rows.spw_n.to_numpy(float) / rows.spw_d.to_numpy(float)
    opp_spw = spw[mate]
    hold_n, hold_d = rows.hold_n.to_numpy(float), rows.hold_d.to_numpy(float)
    brk_n, brk_d = rows.brk_n.to_numpy(float), rows.brk_d.to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ok_h = eligible & np.isfinite(hold_n) & (hold_d > 0) & np.isfinite(spw) & (spw > 0) & (spw < 1)
        ok_b = eligible & np.isfinite(brk_n) & (brk_d > 0) & np.isfinite(opp_spw) & (opp_spw > 0) & (opp_spw < 1)
        hold_luck = np.where(ok_h, (hold_n - hold_d * game_win(np.clip(spw, 1e-6, 1 - 1e-6))) / hold_d, 0.0)
        break_luck = np.where(ok_b, (brk_n - brk_d * (1 - game_win(np.clip(opp_spw, 1e-6, 1 - 1e-6)))) / brk_d, 0.0)
    values = np.column_stack([hold_luck, break_luck])
    weights = np.column_stack([np.where(ok_h, np.minimum(hold_d / 10.0, 3.0), 0.0),
                               np.where(ok_b, np.minimum(brk_d / 10.0, 3.0), 0.0)])
    player = pd.factorize(pd.MultiIndex.from_arrays([rows.tour, rows.player_id]))[0]
    s, n = S.decayed_snapshot(player, rows.day.to_numpy(), weights * values, weights, HALF)
    level = s / (n + K)
    a, b = np.arange(0, len(rows), 2), np.arange(1, len(rows), 2)
    return pd.DataFrame({"match_id": rows.match_id.to_numpy()[a], "hold_luck": level[a, 0] - level[b, 0],
                         "break_luck": level[a, 1] - level[b, 1]}), {
        "per_match_mean": [float(hold_luck[ok_h].mean()), float(break_luck[ok_b].mean())],
        "per_match_sd": [float(hold_luck[ok_h].std()), float(break_luck[ok_b].std())],
        "rows": [int(ok_h.sum()), int(ok_b.sum())]}


def main():
    rows = pd.read_parquet(S.ROWS)
    feats, desc = luck_features(rows)
    frame = C.load_atp().merge(feats, on="match_id", how="left", validate="one_to_one")
    cal = C.calibrated(frame, "p_avg_a")
    base = C.PROFILE + [C.E.SR] + C.E.CONTEXT
    nud = C.walk(frame, base, "p_avg_a", False)
    out = []
    for anchor, column in (("average", "p_avg_a"), ("pinnacle", "p_ps_a")):
        cal = C.calibrated(frame, column)
        nud = C.walk(frame, base, column, False)
        for name, cols, ref_name, ref in (("luck2", ["hold_luck", "break_luck"], "calibrated", cal),
                                          ("profile+context+luck2", base + ["hold_luck", "break_luck"],
                                           "profile+context", nud)):
            p = C.walk(frame, cols, column, False)
            for window, (lo, hi) in WINDOWS.items():
                if anchor == "pinnacle" and hi == 2026:
                    continue
                out.append({"anchor": anchor, "model": name, "versus": f"{ref_name} {anchor}", "window": window,
                            **C.gain(frame, p, ref, frame.year.between(lo, hi).to_numpy() & np.isfinite(ref))})
    res = pd.DataFrame(out)
    res.to_csv(C.OUT / "luck_results.csv", index=False)
    g = frame[frame.year.between(2013, 2025) & np.isfinite(frame.mkt_avg)]
    x = np.column_stack([g.mkt_avg, g.hold_luck / C.P.rms_scale(g[["hold_luck"]].to_numpy())[0],
                         g.break_luck / C.P.rms_scale(g[["break_luck"]].to_numpy())[0]])
    beta, se = C.cluster_logit(x, g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
    coef = {"terms": ["market log-odds", "hold_luck per RMS", "break_luck per RMS"], "coef": beta.tolist(),
            "se": se.tolist(), "n": len(g), "years": "2013-2025", "per_match": desc}
    C.write_json(C.OUT / "luck_summary.json", coef)
    pd.set_option("display.width", 200)
    print(res.round(3).to_string())
    print(coef)


if __name__ == "__main__":
    main()
