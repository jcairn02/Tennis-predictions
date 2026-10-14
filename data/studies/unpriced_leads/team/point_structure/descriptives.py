"""Point-structure analyst (unpriced_leads, B2): descriptive sizes for the memo. Not a screen.

Blinding: per-player residual sums use outcomes (tiebreaks won, break points saved) of seasons <= 2024 ONLY,
filtered before any outcome column is touched. 2025-2026 rows are read only for outcome-free counts
(has_box, tiebreaks played: symmetric, reveals no winner). Nothing is compared with a match result or a price.

Run: ./python.sh data/studies/unpriced_leads/team/point_structure/descriptives.py
Writes descriptives.json beside this file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402

OUT = Path(__file__).with_name("descriptives.json")
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
FRAME = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "model_frame.parquet"


def outcome_free_counts() -> dict:
    """2013-2026: box-score coverage and tiebreaks played (symmetric), main tour vs all evaluation levels."""
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "has_box", "status"])
    # sealed matches (from 29 Jul 2026) are dropped before anything else is read: only matches whose latest possible
    # finish (the clock's lf, days since 1970) is before 29 Jul 2026 are kept (added after a first run that counted
    # them; disclosed in the memo)
    t = pd.read_parquet(ROOT / "data" / "studies" / "match_timing" / "timing.parquet", columns=["match_id", "lf"])
    cut = float((pd.Timestamp("2026-07-29") - pd.Timestamp("1970-01-01")).days)
    m = m.merge(t, on="match_id", how="left")
    m = m[np.isfinite(m.lf.to_numpy(float)) & (m.lf.to_numpy(float) < cut)].drop(columns="lf")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "tb_won_d"])
    p = p[p.side == "A"][["match_id", "tb_won_d"]]
    m = m[m.year >= 2013].merge(p, on="match_id", how="left")
    main = m.level.isin(["GS", "T1000", "T500", "T250", "FIN"]) & ~m.qualifying
    out = {}
    for tour in ("atp", "wta"):
        g = m[(m.tour == tour) & main & m.has_box]
        out[tour] = {
            "main_tour_box_matches_by_season": g.groupby("year").size().to_dict(),
            "main_tour_tiebreaks_per_match_by_season": g.groupby("year").tb_won_d.mean().round(3).to_dict(),
            "main_tour_share_with_tiebreak_by_season": g.assign(t=g.tb_won_d > 0).groupby("year").t.mean().round(3).to_dict(),
        }
    return out


def luck_sizes() -> dict:
    """Seasons 2013-2024 only. Per player-season, on the matches Stage 2 analysed (men every evaluation level;
    women from 2019): the tiebreak residual sum, its spread across player-seasons, and the spread pure iid luck
    implies (sqrt of the sum of pi(1 - pi) over tiebreaks played). Same for break points saved above expectation."""
    cols = ["match_id", "tour", "year", "level_group", "player_id_a", "player_id_b", "pa", "pb", "n_tb",
            "deciding_tb", "rule", "best_of", "tb_exp_a", "tb_over_a", "bp_faced_a", "bp_faced_b",
            "bp_save_over_a", "bp_save_over_b"]
    s = pd.read_parquet(S0 / "stage2_matches.parquet", columns=["year"])
    keep = (s.year <= 2024).to_numpy()              # blinding: the filter comes before any outcome column is read
    d = pd.read_parquet(S0 / "stage2_matches.parquet", columns=cols)[keep].reset_index(drop=True)
    assert int(d.year.max()) <= 2024
    d = d[d.year >= 2013]
    # iid variance of tiebreak wins at the match's own serve rates (7-point; the deciding 10-point ones approximated
    # by the 7-point probability, a small effect on the variance)
    pi = I.tiebreak(d.pa.to_numpy(float), d.pb.to_numpy(float), 7, True)
    d["tb_var"] = d.n_tb.to_numpy(float) * pi * (1 - pi)
    s_a = d.pa.to_numpy(float)
    s_b = d.pb.to_numpy(float)
    d["bp_var_a"] = d.bp_faced_a.to_numpy(float) * s_a * (1 - s_a)
    d["bp_var_b"] = d.bp_faced_b.to_numpy(float) * s_b * (1 - s_b)
    rows = []
    for side, oth in (("a", "b"), ("b", "a")):
        sign = 1.0 if side == "a" else -1.0
        rows.append(pd.DataFrame({
            "tour": d.tour, "year": d.year, "player": d[f"player_id_{side}"],
            "tb_over": sign * d.tb_over_a, "tb_var": d.tb_var, "n_tb": d.n_tb,
            "bp_over": d[f"bp_save_over_{side}"], "bp_var": d[f"bp_var_{side}"], "bp_faced": d[f"bp_faced_{side}"],
            "matches": 1.0}))
    L = pd.concat(rows, ignore_index=True)
    g = L.groupby(["tour", "year", "player"]).sum(numeric_only=True).reset_index()
    out = {}
    for tour in ("atp", "wta"):
        x = g[(g.tour == tour) & (g.matches >= 40)]
        out[tour] = {
            "player_seasons_40plus": int(len(x)),
            "median_matches": float(x.matches.median()),
            "median_tiebreaks_played": float(x.n_tb.median()),
            "sd_tiebreak_residual_sum": round(float(x.tb_over.std()), 3),
            "rms_iid_sd_tiebreak": round(float(np.sqrt(x.tb_var.mean())), 3),
            "median_bp_faced": float(x.bp_faced.median()),
            "sd_bp_saved_residual_sum": round(float(x.bp_over.std()), 3),
            "rms_iid_sd_bp_saved": round(float(np.sqrt(x.bp_var.mean())), 3),
            "corr_tb_over_bp_over": round(float(np.corrcoef(x.tb_over, x.bp_over)[0, 1]), 3),
        }
    return out


def tiebreak_swing() -> dict:
    """Match-win swing of one tiebreak under iid, best of three, both players serving at p (no outcome)."""
    res = {}
    for p in (0.60, 0.64, 0.68, 0.72):
        s = float(I.set_win(np.array([p]), np.array([p]))[0])          # P(win a set) = 0.5 here
        # set 1 tiebreak: win -> P(win 1 of the next up-to-2 sets) ; lose -> P(win both)
        win1, lose1 = 1 - (1 - s) ** 2, s ** 2
        # set 2 at 1-0 up: win -> 1 ; lose -> s.   at 0-1 down: win -> s ; lose -> 0
        sw2 = 0.5 * ((1 - s) + s)
        res[str(p)] = {"set1_swing": round(win1 - lose1, 3), "set2_swing": round(sw2, 3), "set3_swing": 1.0}
    return res


def main() -> int:
    out = {"outcome_free_counts": outcome_free_counts(), "luck_sizes_2013_2024": luck_sizes(),
           "tiebreak_match_swing_iid_bo3": tiebreak_swing()}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["luck_sizes_2013_2024"], indent=1))
    print(json.dumps(out["tiebreak_match_swing_iid_bo3"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
