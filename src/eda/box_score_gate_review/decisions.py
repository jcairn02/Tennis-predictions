"""What a missing box score costs in betting decisions, against what a block costs (docs/studies/box_score_gate_review/).

From the replay (replay_gaps.py): per live match, the base forecast (complete data) and each scenario's (box scores
removed), both the predict step's q_a at the match's own price. The bet sheet's rule picks the side with positive
expected profit at the bookmaker's odds (diagnostics.bet_diagnostics: ev = q * odds - 1). The replay has the instance
frame's closing probability, not a bookmaker's odds, so the odds are built from it with a margin split in proportion:
odds_a = 1 / (p_a (1 + m)). Judged by the complete-data forecast (the forecast whose edges justify betting at all):
    gap cost     the expected profit lost when the gapped forecast's decision differs (a bet taken or missed), per
                 unit staked, summed over the matches with a removal
    block cost   the expected profit of the complete-data forecast's bets in those matches, all forgone by a block
Flat stakes of one unit. The decisions are always the forecasts' own (a bettor acts on the forecast as made); the
judge is the complete-data forecast, or that forecast with its edge over the market halved (truth = p + (q - p) / 2),
to check the comparison when the model's edges are overstated (a block then also avoids some bets that lose).
A third rule beside betting through and blocking: the edge buffer, a gapped match bet only if its edge clears
BUFFERS (1 point, about the 90th-percentile move of one missing round; 1.5 beside it), the margin taken against
the side. Writes data/studies/box_score_gate_review/replay/decisions.csv (gap and block costs) and
decision_rules.csv (each rule's expected profit).
Run: ./python.sh src/eda/box_score_gate_review/decisions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "data" / "studies" / "box_score_gate_review" / "replay"
SCENARIOS = ("same_event", "other_event", "all_window", "same_event_b")
BUFFERS = (0.01, 0.015)


def evs(q, p, m):
    return q / (p * (1 + m)) - 1, (1 - q) / ((1 - p) * (1 + m)) - 1


def pick(q, p, m, buffer=0.0):
    """The bet sheet's side (positive expected profit at the odds), with the forecast moved against each side by buffer."""
    a = evs(np.clip(q - buffer, 1e-9, 1.0), p, m)[0]
    b = evs(np.clip(q + buffer, 0.0, 1 - 1e-9), p, m)[1]
    return np.where(a > 0, "A", np.where(b > 0, "B", "-"))


def rules(b: pd.DataFrame, rem: pd.DataFrame) -> pd.DataFrame:
    """Expected profit (units-%, over the matches with a removal) of each rule for a gapped match: bet through, the
    buffers, a block; and of the complete-data decisions for comparison. Judged as in main()."""
    p, q0 = b["p_market_a"].to_numpy(), b["q_a"].to_numpy()
    rows = []
    for shrink in (1.0, 0.5):
        t = p + shrink * (q0 - p)
        for m in (0.025, 0.04):
            ta, tb = evs(t, p, m)
            worth = lambda k: np.where(k == "A", ta, np.where(k == "B", tb, 0.0))
            for s in SCENARIOS:
                x = pd.read_csv(R / s / "predictions.csv").astype({"match_id": str}).set_index("match_id").loc[b.index]
                q1 = x["q_a"].to_numpy()
                hit = b.index.isin(set(rem.loc[rem["scenario"].eq(s), "live_match_id"]))
                r = {"judge": "complete-data forecast" if shrink == 1 else "its edge halved", "margin": m, "scenario": s,
                     "no_gap": worth(pick(q0, p, m))[hit].sum(), "bet_through": worth(pick(q1, p, m))[hit].sum(),
                     "block": 0.0}
                for d in BUFFERS:
                    r[f"buffer_{d * 100:g}pt"] = worth(pick(q1, p, m, d))[hit].sum()
                rows.append(r)
    d = pd.DataFrame(rows)
    num = [c for c in d.columns if c not in ("judge", "margin", "scenario")]
    d[num] = (100 * d[num]).round(2)
    return d


def main() -> int:
    b = pd.read_csv(R / "base" / "predictions.csv").astype({"match_id": str}).set_index("match_id")
    rem = pd.concat([pd.read_csv(R / "removals.csv"), pd.read_csv(R / "removals_ext.csv")]).astype(str)
    p = b["p_market_a"].to_numpy()
    rows = []
    q0 = b["q_a"].to_numpy()
    for shrink in (1.0, 0.5):
        t = p + shrink * (q0 - p)                                  # the judge: what each decision is worth
        for m in (0.025, 0.04):
            a0, b0 = evs(q0, p, m)
            pick0 = np.where(a0 > 0, "A", np.where(b0 > 0, "B", "-"))
            ta, tb = evs(t, p, m)
            worth = lambda pick: np.where(pick == "A", ta, np.where(pick == "B", tb, 0.0))
            ev0 = worth(pick0)
            for s in SCENARIOS:
                x = pd.read_csv(R / s / "predictions.csv").astype({"match_id": str}).set_index("match_id").loc[b.index]
                a1, b1 = evs(x["q_a"].to_numpy(), p, m)
                pick1 = np.where(a1 > 0, "A", np.where(b1 > 0, "B", "-"))
                hit = b.index.isin(set(rem.loc[rem["scenario"].eq(s), "live_match_id"]))
                rows.append({"judge": "complete-data forecast" if shrink == 1 else "its edge halved", "margin": m,
                             "scenario": s, "matches_with_removal": int(hit.sum()),
                             "bets_complete_data": int((pick0[hit] != "-").sum()),
                             "decisions_changed": int((hit & (pick0 != pick1)).sum()),
                             "gap_cost_units_pct": round(100 * float((ev0 - worth(pick1))[hit].sum()), 2),
                             "block_cost_units_pct": round(100 * float(ev0[hit].sum()), 2)})
    d = pd.DataFrame(rows)
    d["block_over_gap"] = (d["block_cost_units_pct"] / d["gap_cost_units_pct"].replace(0, np.nan)).round(1)
    d.to_csv(R / "decisions.csv", index=False)
    pd.set_option("display.width", 200)
    print(d.to_string(index=False))
    r = rules(b, rem)
    r.to_csv(R / "decision_rules.csv", index=False)
    print()
    print("expected profit of each rule, units-% over the matches with a removal (higher is better)")
    print(r.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
