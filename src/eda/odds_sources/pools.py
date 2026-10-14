"""Odds sources, step 4: margin-free averages of several books as the model's odds input.

The owner's wish of 9 Oct 2026: "Id like to keep it as a weighted average of the sharpest books with vig extracted
ideally and then do the same live. I plan to betting on betonline, polymarket and pinnacle mostly."

Candidate inputs. Each book's price is made margin-free proportionally, then books are combined in log-odds:
    avg        the books' average close (tennis-data; the current input)
    ps, bol    Pinnacle's close (tennis-data), BetOnline's last line (OddsTrader)
    pb         Pinnacle and BetOnline averaged where both price, else the one that does (the input of the model
               retrained in the bet-timing study's section 7)
    pb_guard   pb, except where the two are more than GUARD apart and at least MIN_REF other books price the match:
               then only the one nearer the other books' median
    pin        Pinnacle's close from its two recordings: tennis-data's (up to PS_FAITHFUL_UNTIL: from August 2025 its
               PSW/PSL stop matching Pinnacle's own last line, quality.pinnacle_by_month), or OddsTrader's where
               tennis-data has none, and where the two differ by more than RECONCILE, the one nearer the other books'
               median (reads no result: a data rule)
    pin_first  pin where Pinnacle prices the match, else BetOnline
    pf         the training input of the "Pinnacle first" model (bet-timing study's fits_cons_trained.py --arm pf):
               pin_first, else the books' average
    otmed      the median of OddsTrader's books (SportsBetting.ag, BetOnline's clone, left out)
    w_pb       walk-forward weights on Pinnacle and BetOnline: a logistic fit without intercept on the seasons
               before (from 2018), normalised to sum to 1, so a weighted average rather than a recalibration
    w_pba      the same with the average as a third input

Scored as prices: log loss minus the average's (the current input) and minus Pinnacle's, mLL, on the matches where
every candidate is defined, by season, 2019-2025. Then 2026, where tennis-data's Pinnacle is gone: BetOnline with
Betfair's close, Polymarket's 30-minute price or OddsTrader's median. Calibration and drift cost as drift.py.

OddsTrader's lines stamped over 30 minutes after the listed start are dropped throughout (quality.drop_late), as the
bet-timing study dropped BetOnline's.

Reads sources.parquet; writes pools.json and pools_tables.md.
Run: ./python.sh src/eda/odds_sources/pools.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as C  # noqa: E402
from src.eda.odds_sources import drift as D  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402

GUARD = 0.5            # log-odds between Pinnacle and BetOnline above which the other books decide
RECONCILE = 0.1        # log-odds between Pinnacle's two recordings above which the other books decide
PS_FAITHFUL_UNTIL = "2025-07-31"   # tennis-data's PSW/PSL equal Pinnacle's own last line (OddsTrader's recording) on
                                   # 55-72% of matches a month to June 2025, 50% in July, 14% in August and September
                                   # (quality.pinnacle_by_month)
MIN_REF = 3
WEIGHT_FROM = 2018
EVAL_SEASONS = tuple(range(2019, 2026))
NAMES = {"avg": "Average (current input)", "ps": "Pinnacle", "bol": "BetOnline", "pb": "Pinnacle + BetOnline",
         "pb_guard": "Pinnacle + BetOnline, guarded", "otmed": "OddsTrader median", "w_pb": "Weighted P + B",
         "w_pba": "Weighted P + B + average", "pin": "Pinnacle, two recordings reconciled",
         "pin_first": "Pinnacle first, else BetOnline", "bol_bfe": "BetOnline + Betfair",
         "bol_pm": "BetOnline + Polymarket 30 min",
         "bol_otmed": "BetOnline + OddsTrader median", "bfe": "Betfair", "pm_m30": "Polymarket 30 min"}


def guarded(df: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """pb with the guard; returns the chances and how often the guard acted and whom it dropped."""
    ps, bol = df["p_ps"].to_numpy(float), df["p_bol"].to_numpy(float)
    z_ps, z_bol = C.lg(ps), C.lg(bol)
    refs = [r for r in Q.reference_names(df, "ps") if r not in ("ot8", "ot131")]
    med, n, _ = Q.reference(df, refs)
    out = C.mean_logit(np.column_stack([ps, bol]))
    both = np.isfinite(ps) & np.isfinite(bol)
    act = both & (np.abs(z_ps - z_bol) > GUARD) & (n >= MIN_REF)
    keep_ps = act & (np.abs(z_ps - med) <= np.abs(z_bol - med))
    keep_bol = act & ~keep_ps
    out = np.where(keep_ps, ps, np.where(keep_bol, bol, out))
    season = df["season"].to_numpy()
    counts = {"both": int(both.sum()), "far_apart": int((both & (np.abs(z_ps - z_bol) > GUARD)).sum()),
              "acted": int(act.sum()), "kept_pinnacle": int(keep_ps.sum()), "kept_betonline": int(keep_bol.sum()),
              "acted_by_season": {str(s): int(act[season == s].sum()) for s in sorted(np.unique(season[both]))}}
    return out, counts


def reconciled(df: pd.DataFrame, with_choice: bool = False):
    """Pinnacle's close from its two recordings (tennis-data's untimed one, up to PS_FAITHFUL_UNTIL; OddsTrader's timed
    last line, late lines already dropped), the other books deciding where they differ. Reads no result. Returns
    (chances, counts), and with_choice also the recording each chance came from ("tennis-data", "oddstrader", "")."""
    faithful = (pd.to_datetime(df["td_date"]) <= PS_FAITHFUL_UNTIL).to_numpy()
    td, ot = np.where(faithful, df["p_ps"].to_numpy(float), np.nan), df["p_ot20"].to_numpy(float)
    med, n, _ = Q.reference(df, Q.reference_names(df, "ps"))
    both = np.isfinite(td) & np.isfinite(ot)
    apart = both & (np.abs(C.lg(td) - C.lg(ot)) > RECONCILE) & (n >= MIN_REF)
    take_ot = apart & (np.abs(C.lg(ot) - med) < np.abs(C.lg(td) - med))
    out = np.where(np.isfinite(td), td, ot)
    out = np.where(take_ot, ot, out)
    season = df["season"].to_numpy()
    use_ot = take_ot | (~np.isfinite(td) & np.isfinite(ot))
    choice = np.where(use_ot, "oddstrader", np.where(np.isfinite(td), "tennis-data", ""))
    counts = {"both": int(both.sum()), "apart": int(apart.sum()), "took_oddstrader": int(take_ot.sum()),
              "oddstrader_only": int((~np.isfinite(td) & np.isfinite(ot)).sum()),
              "tennis_data_left_out_after_cutoff": int((~faithful & np.isfinite(df["p_ps"].to_numpy(float))).sum()),
              "took_oddstrader_by_season": {str(s): int(take_ot[season == s].sum())
                                            for s in sorted(np.unique(season[both]))}}
    return (out, counts, choice) if with_choice else (out, counts)


def split_verdict(df: pd.DataFrame, a: str = "ps", b: str = "bol", b_group=("ot8", "ot131"),
                  gap: float = GUARD) -> dict:
    """Where two books are more than `gap` apart in log-odds: whose price the result sided with, and the other books'
    median's (the owner's idea: on a big disagreement, trust the stable books over the outlier). The referees leave
    out both books' recordings (b_group: b's)."""
    pa, pb = df[f"p_{a}"].to_numpy(float), df[f"p_{b}"].to_numpy(float)
    refs = [r for r in Q.reference_names(df, a) if r not in b_group]
    med, n, _ = Q.reference(df, refs)
    m = np.isfinite(pa) & np.isfinite(pb) & (np.abs(C.lg(pa) - C.lg(pb)) > gap) & (n >= MIN_REF)
    y, blk = df["a_won"].to_numpy(float)[m], df["block"].to_numpy()[m]
    la, lb, lm = C.log_loss(pa[m], y), C.log_loss(pb[m], y), C.log_loss(C.ex(med[m]), y)
    sides_with_a = np.abs(C.lg(pa[m]) - med[m]) < np.abs(C.lg(pb[m]) - med[m])
    return {"n": int(m.sum()), "others_side_with_" + a: int(sides_with_a.sum()),
            f"ll_{a}_minus_{b}": C.mean_ci(la - lb, blk), f"ll_{a}_minus_others": C.mean_ci(la - lm, blk),
            f"ll_{b}_minus_others": C.mean_ci(lb - lm, blk),
            f"{a}_favourite_won": round(float(((pa[m] > 0.5) == (y == 1)).mean()), 3),
            f"{b}_favourite_won": round(float(((pb[m] > 0.5) == (y == 1)).mean()), 3)}


def weighted(df: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, dict]:
    """Walk-forward weighted average in log-odds: weights from a logistic fit (no intercept) on the seasons before,
    on the matches every column prices, normalised to sum to 1."""
    P = df[[f"p_{c}" for c in cols]].to_numpy(float)
    Z = C.lg(P)
    full = np.isfinite(Z).all(axis=1)
    y, season = df["a_won"].to_numpy(float), df["season"].to_numpy()
    out = np.full(len(df), np.nan)
    weights = {}
    for yr in sorted(np.unique(season)):
        past = full & (season < yr) & (season >= WEIGHT_FROM)
        cur = full & (season == yr)
        if past.sum() < 500 or not cur.any():
            continue
        beta, se = C.fit_logistic(Z[past], y[past])
        w = beta / beta.sum()
        out[cur] = C.ex(Z[cur] @ w)
        weights[str(yr)] = {"weights": {c: round(float(v), 3) for c, v in zip(cols, w)},
                            "slope": round(float(beta.sum()), 3), "n_fit": int(past.sum())}
    return out, weights


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = D.with_ot_median(df)
    df["p_bol"] = df["p_ot8"]
    info = {"split_ps_bol": split_verdict(df)}
    df["p_pin"], info["reconcile"] = reconciled(df)
    df["p_pin_first"] = np.where(np.isfinite(df["p_pin"]), df["p_pin"], df["p_bol"])
    df["p_pf"] = np.where(np.isfinite(df["p_pin_first"]), df["p_pin_first"], df["p_avg"])
    kind = np.where(np.isfinite(df["p_pin"]), "pinnacle", np.where(np.isfinite(df["p_bol"]), "betonline", "average"))
    info["pf_kinds_by_season"] = {f"{s}|{k}": int(v) for (s, k), v in
                                  pd.Series(kind).groupby([df["season"].to_numpy(), kind]).size().items()}
    df["p_pb"] = C.mean_logit(df[["p_ps", "p_bol"]].to_numpy(float))
    df["p_pb_guard"], info["guard"] = guarded(df)
    df["p_w_pb"], info["weights_pb"] = weighted(df, ["ps", "bol"])
    df["p_w_pba"], info["weights_pba"] = weighted(df, ["ps", "bol", "avg"])
    for name, other in (("bol_bfe", "bfe"), ("bol_pm", "pm_m30"), ("bol_otmed", "otmed")):
        df[f"p_{name}"] = C.mean_logit(df[["p_bol", f"p_{other}"]].to_numpy(float), min_count=2)
    # in-sample weights over 2018-2025 on every book with wide coverage: which ones carry information
    cols = [c for c in ["ps", "bol", "avg", "b365", "otmed"] if f"p_{c}" in df]
    Z = C.lg(df[[f"p_{c}" for c in cols]].to_numpy(float))
    m = np.isfinite(Z).all(axis=1) & df["season"].between(2018, 2025).to_numpy()
    beta, se = C.fit_logistic(Z[m], df["a_won"].to_numpy(float)[m])
    info["pooled_weights_2018_2025"] = {"n": int(m.sum()), **{c: {"beta": round(float(b), 3), "se": round(float(s), 3)}
                                                              for c, b, s in zip(cols, beta, se)}}
    return df, info


def compare(df: pd.DataFrame, cands: list[str], seasons, bases=("avg", "ps")) -> dict:
    m = df["season"].isin(seasons).to_numpy().copy()
    for c in set(cands) | set(bases):
        m &= np.isfinite(df[f"p_{c}"].to_numpy(float))
    x = df[m]
    y, blk = x["a_won"].to_numpy(float), x["block"].to_numpy()
    ll = {c: C.log_loss(x[f"p_{c}"], y) for c in set(cands) | set(bases)}
    out = {"n": int(m.sum()), "log_loss": {c: round(float(ll[c].mean()), 5) for c in cands},
           "minus": {b: {c: C.mean_ci(ll[c] - ll[b], blk) for c in cands if c != b} for b in bases}, "by_season": {}}
    for yr in sorted(x["season"].unique()):
        k = (x["season"] == yr).to_numpy()
        out["by_season"][str(yr)] = {"n": int(k.sum()), **{c: C.mean_ci(ll[c][k] - ll[bases[0]][k], blk[k])
                                                           for c in cands if c != bases[0]}}
    return out


def tables(res: dict) -> str:
    fmt = Q.fmt
    L = ["# Odds sources: averaged inputs (generated by pools.py)", "",
         "mLL, + = the candidate is worse than the named base. A price is better the lower its log loss.", ""]
    for key, title in (("main", "2019–2025, the matches where every candidate is defined"),
                       ("y2026", "2026 (no Pinnacle in tennis-data)")):
        r = res[key]
        bases = list(r["minus"])
        L += [f"## {title} ({r['n']:,} matches)", "", "| Candidate | Log loss | " +
              " | ".join(f"− {NAMES.get(b, b)}" for b in bases) + " |", "|---|---:|" + "---|" * len(bases)]
        for c, v in r["log_loss"].items():
            L.append(f"| {NAMES.get(c, c)} | {v:.4f} | " + " | ".join(
                "—" if c == b else fmt(r["minus"][b][c]) for b in bases) + " |")
        L += ["", f"By season, against {NAMES.get(bases[0], bases[0])}:", "",
              "| Season | " + " | ".join(NAMES.get(c, c) for c in r["log_loss"] if c != bases[0]) + " |",
              "|---|" + "---|" * (len(r["log_loss"]) - 1)]
        for yr, row in r["by_season"].items():
            L.append(f"| {yr} ({row['n']:,}) | " + " | ".join(fmt(row[c]) for c in r["log_loss"] if c != bases[0]) + " |")
        L.append("")
    g = res["info"]["guard"]
    sv = res["info"]["split_ps_bol"]
    rc = res["info"]["reconcile"]
    L += ["## The guard", "", f"Both priced: {g['both']:,}; more than {GUARD} apart: {g['far_apart']:,}; with "
          f"{MIN_REF} or more other books: {g['acted']:,}, keeping Pinnacle on {g['kept_pinnacle']:,} and BetOnline on "
          f"{g['kept_betonline']:,}.", "",
          f"**Who was right when Pinnacle and BetOnline were more than {GUARD} apart** ({sv['n']} matches; the other "
          f"books sided with Pinnacle on {sv['others_side_with_ps']}). Log loss, mLL, + = the first named worse: "
          f"Pinnacle − BetOnline {fmt(sv['ll_ps_minus_bol'], 0)}; Pinnacle − the other books' median "
          f"{fmt(sv['ll_ps_minus_others'], 0)}; BetOnline − the other books' median {fmt(sv['ll_bol_minus_others'], 0)}. "
          f"Favourite won: Pinnacle's {sv['ps_favourite_won']:.0%}, BetOnline's {sv['bol_favourite_won']:.0%}.", "",
          f"**Pinnacle's two recordings reconciled:** both on {rc['both']:,} matches, more than {RECONCILE} apart with "
          f"other books on {rc['apart']:,}, OddsTrader's taken on {rc['took_oddstrader']:,} "
          f"({', '.join(f'{k}: {v}' for k, v in rc['took_oddstrader_by_season'].items() if v)}); OddsTrader's only "
          f"on {rc['oddstrader_only']:,}.", "",
          "## Walk-forward weights (normalised; slope = their sum before normalising)", "",
          "| Season | Pinnacle | BetOnline | slope | Pinnacle (3) | BetOnline (3) | Average (3) | slope (3) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for yr in sorted(set(res["info"]["weights_pb"]) | set(res["info"]["weights_pba"])):
        a, b = res["info"]["weights_pb"].get(yr), res["info"]["weights_pba"].get(yr)
        ca = [f"{a['weights']['ps']:.2f}", f"{a['weights']['bol']:.2f}", f"{a['slope']:.2f}"] if a else ["—"] * 3
        cb = [f"{b['weights']['ps']:.2f}", f"{b['weights']['bol']:.2f}", f"{b['weights']['avg']:.2f}",
              f"{b['slope']:.2f}"] if b else ["—"] * 4
        L.append(f"| {yr} | " + " | ".join(ca + cb) + " |")
    pw = res["info"]["pooled_weights_2018_2025"]
    L += ["", f"Pooled 2018–2025 fit on {pw['n']:,} matches (coefficient ± standard error): " +
          "; ".join(f"{NAMES.get(c, c)} {v['beta']:+.2f} ± {v['se']:.2f}" for c, v in pw.items() if c != "n") + ".", "",
          "## Calibration slope and drift cost by season", "",
          "| Season | " + " | ".join(f"{NAMES.get(c, c)} slope | drift cost" for c in res["calibration"]) + " |",
          "|---|" + "---:|---|" * len(res["calibration"])]
    seasons = sorted({k for v in res["calibration"].values() for k in v})
    for yr in seasons:
        cells = []
        for c, rows in res["calibration"].items():
            r = rows.get(yr)
            cells += (["—", "—"] if not r else [f"{r['slope']['est']:.3f}", fmt(r.get("drift_cost"))])
        L.append(f"| {yr} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


def main() -> int:
    df = Q.drop_late(pd.read_parquet(C.SOURCES))
    df = df[df["a_won"].notna()].reset_index(drop=True)
    df, info = build(df)
    main_c = ["avg", "ps", "pin", "bol", "pb", "pb_guard", "w_pb", "w_pba", "otmed"]
    c2026 = ["avg", "bol", "otmed", "bfe", "pm_m30", "bol_bfe", "bol_pm", "bol_otmed"]
    res = {"info": info, "main": compare(df, main_c, EVAL_SEASONS),
           "y2026": compare(df, c2026, (2026,), bases=("avg", "bol")),
           "calibration": D.calibration(df, ["avg", "ps", "pin", "bol", "pb", "pin_first", "otmed"])}
    C.write_json(C.OUT / "pools.json", res)
    (C.OUT / "pools_tables.md").write_text(tables(res), encoding="utf-8")
    keep = ["pin", "pin_first", "pf", "pb", "pb_guard", "w_pb", "w_pba", "otmed"]
    df[["match_id", "season"] + [f"p_{c}" for c in keep]].to_parquet(C.OUT / "pools.parquet", index=False)
    C.log("pools.json, pools_tables.md, pools.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
