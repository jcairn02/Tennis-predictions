"""Bet timing, step 4: a consensus of the sharp lines available at the moment of the bet as the model's odds input,
instead of the venue's own line. The owner's follow-up of 8 Oct 2026: "Would it make sense to use the aggregate of the
vig-removed sharpest lines available at the time of betting for input? not simply the current line? As thats prob
sharper than the current line?"

The consensus is the mean of the margin-free log-odds (proportional de-vig, as the model's own input) of the sharp
prices available at the moment, with equal weights. Three bets, each with its own inputs:

    at BetOnline's last line, 2020-2025       bol_close (the venue's own line), ps_close (Pinnacle's close: tennis-data's
                                              PSW/PSL as Stage 1 linked them; untimed, "generally the most recent
                                              before play"; it stops on 13-14 Jan 2026), cons_close (the mean of the
                                              two), td (the books' average close, the model's training input)
    at Polymarket 24 hours out, 2025-2026     pm_h24 (the venue's own price), bol_open (BetOnline's opening line, only
                                              where it was quoted before the 24-hour moment), cons_h24 (the mean of
                                              the two)
    at Polymarket's 30-minute price           pm_m30 (the venue's own), bfe_close (Betfair's close: tennis-data's
                                              BFEW/BFEL, from Aug 2025, untimed), cons_late (the mean of every one
                                              available of Betfair's close, BetOnline's last line, Pinnacle's close and
                                              Polymarket's 30-minute price; at least two), td

Timing. At the close every price stands for the market at the start, but tennis-data's closes carry no time: where one
was taken after the venue's price it knows more than a bettor at that moment (look-ahead). BetOnline's last line is
timed, so the BetOnline comparison is also run on last lines stamped within an hour before the listed start; Polymarket's
30-minute price is earlier than the untimed closes, so that comparison is an upper bound. The 24-hour comparison is
timed throughout.

    --frame   writes data/studies/bet_timing/consensus_frame.parquet (gitignored) and consensus_counts.json
              (reads no result except A's orientation, as frame.py)
    --score   after fits.py --set consensus: writes results_consensus.json and consensus_tables.md

Run: ./python.sh src/eda/bet_timing/consensus.py --frame
     bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits.py --run --set consensus
     ./python.sh src/eda/bet_timing/consensus.py --score
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402

NEW_BLOCKS = C.CONSENSUS_BLOCKS
LATE_PARTS = ("bfe_close", "bol_close", "ps_close", "pm_m30")
NEAR_START_H = 1.0          # BetOnline's last line stamped at most this many hours before the listed start


def mean_logit(cols: list[np.ndarray], min_count: int) -> np.ndarray:
    """expit of the mean of the available log-odds (NaN where fewer than min_count are available)."""
    z = C.lg(np.column_stack(cols))                          # NaN stays NaN
    n = np.isfinite(z).sum(axis=1)
    total = np.where(np.isfinite(z), z, 0.0).sum(axis=1)
    m = np.divide(total, n, out=np.full(len(n), np.nan), where=n > 0)
    return np.where(n >= min_count, C.ex(m), np.nan)


def build() -> int:
    from src.eda.bet_timing import frame as F
    rows = F.model_rows()
    x = pd.read_parquet(C.FRAME)
    x["match_id"] = x["match_id"].astype(str)
    s1 = pd.read_parquet(C.STAGE1, columns=["match_id", "ps_a", "ps_b", "ps_coherent"])
    s1["match_id"] = s1["match_id"].astype(str)
    x = x.merge(s1, on="match_id", how="left", validate="one_to_one")
    ok = x["ps_coherent"].fillna(False).astype(bool).to_numpy()
    x["p_ps_close"] = np.where(ok, C.devig(x["ps_a"], x["ps_b"]), np.nan)
    # Betfair's close from the sharp benchmark's table, linked and oriented as frame.polymarket links Polymarket
    sb = pd.read_parquet(C.SHARP, columns=["tour", "date", "winner", "loser", "BFEW", "BFEL", "ok_bfe"])
    sb["td_date"] = pd.to_datetime(sb["date"]).dt.normalize()
    sb = sb.drop(columns="date").rename(columns={"winner": "td_winner", "loser": "td_loser"})
    sb["td_winner"], sb["td_loser"] = sb["td_winner"].astype(str), sb["td_loser"].astype(str)
    sb = sb[~sb.duplicated(F.KEY, keep=False)]
    o = rows[["match_id", "a_is_w"] + F.KEY].merge(sb, on=F.KEY, how="left", validate="one_to_one")
    a = o["a_is_w"].to_numpy(bool)
    bw, bl = o["BFEW"].to_numpy(float), o["BFEL"].to_numpy(float)
    good = o["ok_bfe"].fillna(False).astype(bool).to_numpy()
    bfe = pd.Series(np.where(good, C.devig(np.where(a, bw, bl), np.where(a, bl, bw)), np.nan),
                    index=o["match_id"].astype(str))
    x["p_bfe_close"] = bfe.reindex(x["match_id"]).to_numpy()
    # the consensuses
    x["p_cons_close"] = mean_logit([x["p_ps_close"].to_numpy(float), x["p_bol_close"].to_numpy(float)], 2)
    before = (x["ok_bol_open"].astype(bool) & (x["t_bol_open"] <= x["t_pm_h24"])).to_numpy()
    x["p_bol_open_pre24"] = np.where(before, x["p_bol_open"], np.nan)
    x["p_cons_h24"] = mean_logit([x["p_bol_open_pre24"].to_numpy(float), x["p_pm_h24"].to_numpy(float)], 2)
    late = [x[f"p_{b}"].to_numpy(float) for b in LATE_PARTS]
    x["p_cons_late"] = np.where(x["season"].to_numpy() >= 2025, mean_logit(late, 2), np.nan)
    x["n_cons_late"] = np.isfinite(np.column_stack(late)).sum(axis=1)
    x["bol_close_near_start"] = (x["h_bol_close"] <= NEAR_START_H).to_numpy() & x["ok_bol_close"].to_numpy(bool)
    keep = ["match_id", "season"] + [f"p_{b}" for b in NEW_BLOCKS] + ["p_bol_open_pre24", "n_cons_late",
                                                                      "bol_close_near_start"]
    out = x[keep]
    out.to_parquet(C.CONSENSUS_FRAME, index=False)
    counts = {"matches": int(len(out)),
              "priced": {b: {str(s): int(v) for s, v in out.groupby("season")[f"p_{b}"].count().items()}
                         for b in NEW_BLOCKS},
              "bol_open_before_pm_h24": int(np.isfinite(out["p_bol_open_pre24"]).sum()),
              "cons_late_parts": {str(k): int(v) for k, v in
                                  out.loc[np.isfinite(out["p_cons_late"]), "n_cons_late"].value_counts().items()},
              "bol_close_near_start": int(out["bol_close_near_start"].sum())}
    C.write_json(C.OUT / "consensus_counts.json", counts)
    C.log(f"consensus_frame.parquet: {counts}")
    return 0


if __name__ == "__main__":
    if "--frame" in sys.argv:
        sys.exit(build())
    if "--score" in sys.argv:
        from src.eda.bet_timing import score_consensus
        sys.exit(score_consensus.main())
    print(__doc__)
    sys.exit(2)
