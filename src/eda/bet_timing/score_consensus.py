"""Bet timing, step 4b: the sharp-consensus inputs (consensus.py) against the venue's own line, at the venue's price.

Forecasts: the main fits' blocks and the consensus fits' blocks (fits.py --set consensus: the same training, seeds 0-3 and
settings), each symmetrised, averaged over the seeds and passed through the current best model's rule for its season
(score.final: the decided calibration for 2020-2023, both stages for 2024-2026).

Three bets. On each, every input is compared with the venue's own line on the same matches (completed and retired
matches, debut seasons out; money on completed matches):
    A  BetOnline's last line, 2020-2025: bol_close (own), ps_close, cons_close, td. Primary: last lines stamped at most an
       hour before the listed start, the nearest to the untimed Pinnacle close; every last line as a sensitivity
    B  Polymarket 24 hours out, 2025-2026, inputs known at 24 hours, BetOnline's opening quoted before that moment:
       pm_h24 (own), bol_open, cons_h24
    C  Polymarket's 30-minute price, 2025-2026: pm_m30 (own), cons_late, td; bfe_close on its own matches. The untimed
       closes may be later than the 30-minute price, so C is an upper bound

Measures (mLL; paired cluster-t intervals over four-week blocks):
    price_sharper   L(the venue's price) - L(the input price)      + = the input price is sharper than the venue's
    model_better    L(model fed its own venue) - L(model fed it)   + = the input makes the model more accurate
    edge_at_venue   L(the venue's price) - L(model fed the input)  + = the model beats the price it bets into
    money           at the venue's price (BetOnline: the owner's staking; Polymarket: $1 at the ask with the fee of the
                    moment); paired profit per 100 matches, input minus own; ROI; B also closing-line value
Writes data/studies/bet_timing/results_consensus.json and consensus_tables.md. Reads the results (score.load) only.
Run: ./python.sh src/eda/bet_timing/consensus.py --score
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
from src.eda.bet_timing import score as SS  # noqa: E402
from src.eda.tabpfn_thinking.common import ll  # noqa: E402

TAUS = (0.0, 0.02, 0.05)
NAMES = {"bol_close": "BetOnline's last line (own)", "ps_close": "Pinnacle's close",
         "cons_close": "Consensus: Pinnacle + BetOnline", "td": "The books' average close (training input)",
         "pm_h24": "Polymarket 24 h (own)", "bol_open": "BetOnline's opening (quoted earlier)",
         "cons_h24": "Consensus: Polymarket 24 h + BetOnline opening", "pm_m30": "Polymarket 30 min (own)",
         "cons_late": "Consensus: Betfair, BetOnline, Pinnacle, Polymarket (2+ available)",
         "bfe_close": "Betfair's close"}


def load() -> pd.DataFrame:
    x = SS.load()
    cal = x.attrs["calibration"]
    cf = pd.read_parquet(C.CONSENSUS_FRAME)
    cf["match_id"] = cf["match_id"].astype(str)
    x = x.merge(cf.drop(columns="season"), on="match_id", how="left", validate="one_to_one")
    e = SS.etas(C.SEASONS, price_set="consensus", blocks=C.CONSENSUS_BLOCKS)
    x = x.join(e, on="match_id")
    tour, season, spd = x["tour"].to_numpy(), x["season"].to_numpy(), x["spd_L"].to_numpy(float)
    for b in C.CONSENSUS_BLOCKS:
        if f"eta_{b}" in x:
            x[f"q_{b}"] = SS.final(x[f"eta_{b}"].to_numpy(float), tour, season, spd, cal)
    return x


def base(x: pd.DataFrame, cols: list[str]) -> np.ndarray:
    m = (~x["debut_season"].astype(bool) & x["y"].notna()).to_numpy().copy()
    for c in cols:
        m &= np.isfinite(x[c].to_numpy(float))
    return m


def compare(g: pd.DataFrame, own: str, inp: str) -> dict:
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    L = lambda c: np.asarray(ll(g[c].to_numpy(float), y))  # noqa: E731
    out = {"input": inp, "name": NAMES[inp], "matches": int(len(g)),
           "model_better": SS.mean_ci(L(f"q_{own}") - L(f"q_{inp}"), blk),
           "edge_at_venue": SS.mean_ci(L(f"p_{own}") - L(f"q_{inp}"), blk)}
    if inp != own:
        out["price_sharper"] = SS.mean_ci(L(f"p_{own}") - L(f"p_{inp}"), blk)
    return out


def money(g: pd.DataFrame, venue: str, inputs: list[str], kind: str, label: str) -> dict:
    g = g[g["status"].eq("completed").to_numpy()].reset_index(drop=True)
    blk = g["block"].to_numpy()
    out = {"matches": int(len(g))}
    at_close = venue in ("bol_close", "pm_m30")       # a bet at the close has no closing-line value beyond the margin
    for tau in TAUS if kind == "book" else TAUS[:2]:
        bets = {i: (SS.book_bets(g, venue, tau, q_col=f"q_{i}") if kind == "book"
                    else SS.pm_bets(g, venue, tau, q_col=f"q_{i}")) for i in inputs}
        own = bets[venue]
        row = {}
        for i, s in bets.items():
            row[i] = {"bets": int(s["bet"].sum()), "staked": float(s["stake"].sum()),
                      "roi": SS.ratio_boot(s["profit"].to_numpy(), s["stake"].to_numpy(), blk,
                                           SS.seed_of(label, tau, i, "roi")),
                      "profit_per_100": SS.mean_ci(s["profit"].to_numpy(), blk, 100.0)}
            if not at_close:
                row[i]["clv_roi"] = SS.ratio_boot(s["clv"].to_numpy(), s["stake"].to_numpy(), blk,
                                                  SS.seed_of(label, tau, i, "clv"))
            if i != venue:
                row[i]["minus_own_profit_per_100"] = SS.mean_ci(s["profit"].to_numpy() - own["profit"].to_numpy(), blk,
                                                                100.0)
                if not at_close:
                    row[i]["minus_own_clv_per_100"] = SS.mean_ci(s["clv"].to_numpy() - own["clv"].to_numpy(), blk,
                                                                 100.0)
        out[f"tau_{tau}"] = row
    return out


def bet(x: pd.DataFrame, mask: np.ndarray, venue: str, inputs: list[str], kind: str, label: str) -> dict:
    g = x[mask].reset_index(drop=True)
    return {"label": label, "venue": venue, "matches": int(len(g)),
            "inputs": [compare(g, venue, i) for i in [venue] + inputs],
            "money": money(g, venue, [venue] + inputs, kind, label)}


def main() -> int:
    x = load()
    res = {"bets": []}
    # A: BetOnline's last line, 2020-2025
    inputs = ["ps_close", "cons_close", "td"]
    m = base(x, [f"{p}_{b}" for b in ["bol_close"] + inputs for p in ("p", "q")]) & (x["season"] <= 2025).to_numpy()
    near = x["bol_close_near_start"].fillna(False).astype(bool).to_numpy()
    tour = x["tour"].to_numpy()
    res["bets"].append(bet(x, m & near, "bol_close", inputs, "book", "A|betonline_close|stamped_within_1h"))
    res["bets"].append(bet(x, m, "bol_close", inputs, "book", "A|betonline_close|all"))
    for t, name in (("atp", "men"), ("wta", "women")):
        res["bets"].append(bet(x, m & near & (tour == t), "bol_close", inputs, "book",
                               f"A|betonline_close|stamped_within_1h|{name}"))
    # B: Polymarket 24 hours out, with BetOnline's opening quoted before
    inputs = ["bol_open", "cons_h24"]
    m = base(x, ["p_pm_h24", "q_pm_h24", "p_bol_open_pre24", "q_bol_open", "p_cons_h24", "q_cons_h24", "fee_pm_h24",
                 "p_pm_m30"]) & x["known_pm_h24"].to_numpy(bool)
    res["bets"].append(bet(x, m, "pm_h24", inputs, "pm", "B|polymarket_24h|all"))
    # C: Polymarket's 30-minute price
    inputs = ["cons_late", "td"]
    m = base(x, ["p_pm_m30", "q_pm_m30", "p_cons_late", "q_cons_late", "p_td", "q_td", "fee_pm_m30"])
    res["bets"].append(bet(x, m, "pm_m30", inputs, "pm", "C|polymarket_30m|all"))
    m_b = m & base(x, ["p_bfe_close", "q_bfe_close"])
    res["bets"].append(bet(x, m_b, "pm_m30", ["bfe_close", "cons_late", "td"], "pm", "C|polymarket_30m|with_betfair"))
    C.write_json(C.OUT / "results_consensus.json", res)
    tables(res)
    return 0


def ci(d: dict, p: int = 2, scale: float = 1.0) -> str:
    return f"{scale * d['est']:+.{p}f} [{scale * d['lo']:+.{p}f}, {scale * d['hi']:+.{p}f}]"


def verdict(d: dict, pos: str, neg: str) -> str:
    return pos if d["lo"] > 0 else neg if d["hi"] < 0 else "tie"


def tables(res: dict) -> None:
    md = ["# Bet timing: the sharp-consensus inputs (generated by src/eda/bet_timing/score_consensus.py)", "",
          "mLL. Price sharper: + = the input price is sharper than the venue's own. Model better: + = the model fed the "
          "input is more accurate than fed the venue's own line. Edge at the venue: + = the model beats the price it "
          "bets into. Money: profit per 100 matches, input minus own (+ = the input earns more).", ""]
    for b in res["bets"]:
        md += [f"## {b['label']} ({b['matches']:,} matches)", "",
               "| Input | Price sharper than the venue's | Model better | Edge at the venue | Reading |",
               "|---|---|---|---|---|"]
        for r in b["inputs"]:
            sharp = ci(r["price_sharper"]) if "price_sharper" in r else "—"
            read = verdict(r["model_better"], "input better", "own better") if r["input"] != b["venue"] else "—"
            md.append(f"| {r['name']} | {sharp} | {ci(r['model_better']) if r['input'] != b['venue'] else '—'} | "
                      f"{ci(r['edge_at_venue'])} | {read} |")
        md += ["", "| Input | Threshold | Bets | ROI | Profit per 100 matches | Input − own, per 100 | CLV ROI | "
                   "Input − own, CLV per 100 |", "|---|---|---:|---|---|---|---|---|"]
        for tau_key, row in b["money"].items():
            if not tau_key.startswith("tau_"):
                continue
            for i, s in row.items():
                clv = f"{100 * s['clv_roi']['est']:+.1f}%" if "clv_roi" in s else "—"
                diff = ci(s["minus_own_profit_per_100"]) if "minus_own_profit_per_100" in s else "—"
                diff_clv = ci(s["minus_own_clv_per_100"]) if "minus_own_clv_per_100" in s else "—"
                md.append(f"| {NAMES[i]} | {tau_key[4:]} | {s['bets']:,} | {ci(s['roi'], 1, 100)}% | "
                          f"{ci(s['profit_per_100'])} | {diff} | {clv} | {diff_clv} |")
        md.append("")
    (C.OUT / "consensus_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {C.OUT / 'consensus_tables.md'} ({len(md)} lines)")    # the tables hold U+2212, which cp1252 lacks


if __name__ == "__main__":
    sys.exit(main())
