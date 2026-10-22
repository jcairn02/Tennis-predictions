"""The lead's re-check of subagent 5's headline (Part F): on the training rows without a faithful Pinnacle close
(August 2025 on), the equal log-odds average of BetOnline, Betfair and Polymarket (30 minutes before the start),
"sharp3", against today's stand-in.

Independent of the subagent's scorer: sharp3 is rebuilt here from its three member prices (the subagent's per-match
table, data/studies/source_reconciliation/odds/gap_prices.parquet), the stand-in is checked against the model's own
input (the template's odds_sources.parquet, p_mkt), results are read from the template's table only for matches whose
tournament date and match day both fall before the seal (29 Jul 2026), and the interval clusters on four-week blocks
counted here from 1 Aug 2025.

Writes data/studies/source_reconciliation/odds/lead_check.json. Run: ./python.sh src/eda/source_reconciliation/lead_check_odds.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402

ODDS = C.OUT / "odds"
TEMPLATE = C.STUDIES / "current_best_model" / "template_2026-10-14" / "odds_sources.parquet"


def logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def mean_logit(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    z = logit(frame[cols].to_numpy(dtype="float64"))
    z = np.where(np.isfinite(frame[cols].to_numpy(dtype="float64")), z, np.nan)
    m = np.nanmean(z, axis=1)
    return pd.Series(1 / (1 + np.exp(-m)), index=frame.index)


def ll(p, y):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def clustered(d: np.ndarray, groups: np.ndarray) -> tuple[float, float, float, int]:
    """Mean of d with a cluster-robust 95% interval (normal), in mLL."""
    est = d.mean()
    g = pd.Series(d - est).groupby(groups).sum()
    se = np.sqrt((g ** 2).sum()) / len(d)
    G = len(g)
    se *= np.sqrt(G / (G - 1)) if G > 1 else 1
    return 1000 * est, 1000 * (est - 1.96 * se), 1000 * (est + 1.96 * se), G


def main() -> int:
    gp = pd.read_parquet(ODDS / "gap_prices.parquet")
    tpl = ds.dataset(TEMPLATE).to_table(columns=["match_id", "tournament_date", "td_date", "a_won", "p_mkt"]).to_pandas()
    tpl["tournament_date"] = pd.to_datetime(tpl["tournament_date"])
    tpl["td_date"] = pd.to_datetime(tpl["td_date"])
    j = gp.drop(columns=["tournament_date", "td_date"]).merge(tpl, on="match_id", how="left", validate="one_to_one")
    out = {"gap_rows": int(len(j))}
    # today's rule against the model's own input, on every gap row (no result needed): the applied frame's odds input
    # (model_frame.parquet; model_frame_chain.parquet and odds_sources' p_mkt hold the books' average the chain built
    # before odds_input.py --apply replaced it)
    frame = pd.read_parquet(TEMPLATE.parent / "model_frame.parquet", columns=["match_id", "in_odds_logit"])
    fj = j[["match_id", "p_rule_today"]].merge(frame, on="match_id", how="left")
    diff = (np.log(fj["p_rule_today"] / (1 - fj["p_rule_today"])) - fj["in_odds_logit"]).abs()
    out["rule_today_equals_model_input"] = {"rows": int(diff.notna().sum()), "max_abs_logit_diff": float(diff.max())}
    pre = (j["tournament_date"] < C.SEAL) & (j["td_date"] < C.SEAL)
    s = j[pre & j["a_won"].notna()].copy()
    out["scored_rows"] = int(len(s))
    s["y"] = s["a_won"].astype(float)
    s["sharp3_lead"] = mean_logit(s, ["p_bol", "p_bfe", "p_pm"])
    s["sharp3_lead"] = s["sharp3_lead"].fillna(s["p_avg"])
    agree = (s["sharp3_lead"] - s["p_rule_sharp3"]).abs()
    out["sharp3_rebuilt_vs_subagent"] = {"max_abs_diff": float(agree.max())}
    block = ((s["td_date"] - pd.Timestamp("2025-08-01")).dt.days // 28).to_numpy()
    week = ((s["td_date"] - pd.Timestamp("2025-08-01")).dt.days // 7).to_numpy()
    base = ll(s["p_rule_today"].to_numpy(), s["y"].to_numpy())
    readings = {}
    for name, col in (("sharp3", "sharp3_lead"), ("bol_bfe_rule", "p_rule_bol_bfe"), ("bol_pm_rule", "p_rule_bol_pm"),
                      ("sharp4", "p_rule_sharp4")):
        d = ll(s[col].to_numpy(), s["y"].to_numpy()) - base
        est, lo, hi, G = clustered(d, block)
        _, wlo, whi, W = clustered(d, week)
        readings[name] = {"est_mLL": round(est, 3), "ci_4wk": [round(lo, 3), round(hi, 3)], "blocks": G,
                          "ci_week": [round(wlo, 3), round(whi, 3)], "weeks": W,
                          "blocks_negative": int((pd.Series(d).groupby(block).mean() < 0).sum())}
        for label, mask in (("men", s["tour"].eq("atp")), ("women", s["tour"].eq("wta")),
                            ("2025", s["td_date"].dt.year.eq(2025)), ("2026", s["td_date"].dt.year.eq(2026))):
            mk = mask.to_numpy()
            e, l, h, g = clustered(d[mk], block[mk])
            readings[name][label] = {"n": int(mk.sum()), "est_mLL": round(e, 3), "ci_4wk": [round(l, 3), round(h, 3)]}
    out["readings_minus_today_plus_is_worse"] = readings
    out["base_log_loss"] = round(float(base.mean()), 5)
    C.write_json(ODDS / "lead_check.json", out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
