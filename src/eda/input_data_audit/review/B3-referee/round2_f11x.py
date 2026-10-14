"""B3-referee, round 2 (F11x): three reversed average-odds rows outside the model frame, refereed against every book
on the raw tennis-data row and against the ranks, with the proposed exchange (AvgW/AvgL and MaxW/MaxL) simulated.

Read-only on the repo; writes data/studies/input_data_audit/fixes/B3-referee/round2.json.

Per row: the live (7 Oct) Stage 1 link (td_file, td_row, link type, same set scores, round and rank agreement), every
odds pair present on the raw row (any column pair ending in W/L that is not a score or rank), p(winner) by each, the
ranks, the result; then the exchange: Avg and Max after it, against each book (Avg inside the books' range per side;
Max at or above every book per side; Avg at or below Max per side; overround unchanged).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
S1 = ROOT / "data/studies/predictability_diagnostic/stage1_odds.parquet"
IDS = ["atp|2010-560|SF|atp:103819|atp:104925", "atp|2011-424|F|atp:104269|atp:105683",
       "atp|2011-520|F|atp:103819|atp:104745"]
NOT_BOOKS = {"W1", "W2", "W3", "W4", "W5", "WRank", "WPts", "Wsets"}


def num(x):
    v = pd.to_numeric(pd.Series([x]), errors="coerce").iloc[0]
    return v if pd.notna(v) and v > 1.0 else np.nan


def main() -> None:
    s1 = pd.read_parquet(S1)
    p = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet",
                        columns=["match_id", "side", "player_name", "rank", "won"])
    m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                        columns=["match_id", "score", "status", "tournament_name", "round"])
    out = []
    for mid in IDS:
        a = s1[s1.match_id.eq(mid)].iloc[0]
        raw = pd.read_parquet(ROOT / a.td_file).iloc[int(a.td_row)]
        books = sorted({c[:-1] for c in raw.index if c.endswith("W") and c not in NOT_BOOKS and f"{c[:-1]}L" in raw.index})
        prices = {}
        for b in books:
            w, l_ = num(raw[f"{b}W"]), num(raw[f"{b}L"])
            if np.isfinite(w) and np.isfinite(l_):
                prices[b] = (w, l_, round((1 / w) / (1 / w + 1 / l_), 4))
        indep = {b: v for b, v in prices.items() if b not in ("Avg", "Max")}
        aw, al, pa = prices["Avg"]
        mw, ml, pm = prices["Max"]
        opp = [b for b, v in indep.items() if (v[2] - 0.5) * (pa - 0.5) < 0]
        lo_w, hi_w = min(v[0] for v in indep.values()), max(v[0] for v in indep.values())
        lo_l, hi_l = min(v[1] for v in indep.values()), max(v[1] for v in indep.values())
        # after exchanging Avg and Max
        nw, nl, nmw, nml = al, aw, ml, mw
        checks = {
            "books_on_row": sorted(indep), "books_opposing_avg": opp,
            "books_p_winner_range": [min(v[2] for v in indep.values()), max(v[2] for v in indep.values())],
            "avg_p_winner_stored": pa, "max_p_winner_stored": pm,
            "avg_p_winner_after": round(1 - pa, 4),
            "max_stored_below_a_book": bool(mw < hi_w - 1e-9 or ml < hi_l - 1e-9),
            "after_avg_within_book_range_w": bool(lo_w - 0.15 <= nw <= hi_w + 0.15),
            "after_avg_within_book_range_l": bool(lo_l - 0.15 <= nl <= hi_l + 0.15),
            "after_max_ge_every_book": bool(nmw >= hi_w - 1e-9 and nml >= hi_l - 1e-9),
            "after_avg_le_max_both_sides": bool(nw <= nmw and nl <= nml),
            "overround_avg": round(1 / aw + 1 / al, 4),
        }
        pp = p[p.match_id.eq(mid)].set_index("side")
        mm = m[m.match_id.eq(mid)].iloc[0]
        winner = pp[pp.won].iloc[0]
        loser = pp[~pp.won].iloc[0]
        rec = {"match_id": mid, "td_file": a.td_file, "td_row": int(a.td_row), "link": a.link,
               "same_set_scores": bool(a.same_set_scores), "round_agrees": a.round_agrees,
               "rank_agrees_a": bool(a.rank_agrees_a), "rank_agrees_b": bool(a.rank_agrees_b),
               "stage0": f"{winner.player_name} ({winner['rank']:.0f}) d. {loser.player_name} ({loser['rank']:.0f}) {mm.score}",
               "raw": {"Tournament": raw.get("Tournament"), "Date": str(raw.get("Date")), "Round": raw.get("Round"),
                       "Winner": raw.get("Winner"), "WRank": raw.get("WRank"), "Loser": raw.get("Loser"),
                       "LRank": raw.get("LRank"), "Comment": raw.get("Comment"),
                       "prices_W_L_pWinner": {b: list(v) for b, v in prices.items()}},
               "checks": checks}
        out.append(rec)
    (OUT / "round2_evidence.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
