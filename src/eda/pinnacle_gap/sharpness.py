"""Which is sharper: Pinnacle's last price on TennisExplorer or BetOnline's close? (the owner, 22 Oct 2026: "Whats
sharper. Pinnacles "last price" for 2026 or betonline for 2026? That is ultimately what matters", then "*betonline close")

Reads results. "Sharper" = the lower log loss of the margin-free price against the result, on the same matches.
Differences in mLL (thousandths of a nat), "A - B": + = A worse; 95% intervals over four-week blocks (the odds study's
mean_ci); "better" / "worse" only when the interval clears 0, else "unresolved" with P(A better).

Prices:
    te_all    TennisExplorer's last Pinnacle price, every coherent row (the declared primary's, 21 Oct 18:44)
    te_rule   the price the model will use (odds_input.py, rule 2026-10-21): time-stamped rows only, the site's own
              errors left out (computed with Pinnacle's other recordings blanked, so it exists before Nov 2025 too)
    bol       BetOnline's close: OddsTrader's last line, lines stamped over 30 minutes after the listed start dropped
    ps        Pinnacle's own close (tennis-data's PSW/PSL), up to 23 Jul 2025 (the overlap's referee)
Readings: the declared primary (Nov 2025 - Oct 2026, te_all - bol); 2026 alone (the owner's framing); te_rule - bol;
by tour; the overlap of 1 Jan - 23 Jul 2025 (each against ps); the encompassing weights (a logistic fit of the result
on both log-odds, no intercept, cluster-robust by block).
Writes data/studies/pinnacle_gap/sharpness.json and sharpness_tables.md (aggregates only).

    ./python.sh src/eda/pinnacle_gap/sharpness.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import odds_input as O  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.ingest import tennisexplorer as TEI  # noqa: E402

INST = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-21b"
OUT = ROOT / "data" / "studies" / "pinnacle_gap"


def verdict(ci: dict, a: str) -> str:
    if ci["est"] is None or ci["blocks"] < 2:
        return "—"
    if ci["hi"] < 0:
        return f"{a} better"
    if ci["lo"] > 0:
        return f"{a} worse"
    se = (ci["hi"] - ci["lo"]) / (2 * student_t.ppf(0.975, ci["blocks"] - 1))
    return f"unresolved (P({a} better) {norm.cdf(-ci['est'] / se):.2f})"


def encompassing(z1: np.ndarray, z2: np.ndarray, y: np.ndarray, blocks: np.ndarray) -> dict:
    """Weights of a logistic fit of the result on both log-odds (no intercept: side A is random), with a
    cluster-robust (by block) covariance. 1 and 0 = the first carries everything the second does, and more."""
    Z = np.column_stack([z1, z2])
    beta, _ = OC.fit_logistic(Z, y)
    p = 1.0 / (1.0 + np.exp(-(Z @ beta)))
    H = (Z * (p * (1 - p))[:, None]).T @ Z
    labels, ix = np.unique(blocks, return_inverse=True)
    G = len(labels)
    S = np.zeros((G, 2))
    np.add.at(S, ix, Z * (y - p)[:, None])
    Hi = np.linalg.inv(H)
    V = Hi @ (G / (G - 1) * S.T @ S) @ Hi
    se = np.sqrt(np.diag(V))
    q = student_t.ppf(0.975, G - 1)
    return {"w1": float(beta[0]), "w1_lo": float(beta[0] - q * se[0]), "w1_hi": float(beta[0] + q * se[0]),
            "w2": float(beta[1]), "w2_lo": float(beta[1] - q * se[1]), "w2_hi": float(beta[1] + q * se[1]),
            "n": int(len(y)), "blocks": int(G)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = pd.read_parquet(INST / "odds_sources.parquet")
    fr = pd.read_parquet(INST / "model_frame.parquet", columns=["match_id", "tour", "season", "tournament_date", "a_won"])
    link, how = TEI.link_frame(INST / "model_frame.parquet", dt.date(2025, 1, 1))
    te = O.te_columns(link)
    s = src.drop(columns=[c for c in src.columns if c.startswith("tex_")]).merge(te, on="match_id", how="left")
    # the rule's price wherever the site has one: Pinnacle's other recordings blanked, the rule's start moved back
    s2 = s.copy()
    for c in ("ps_a", "ps_b", "p_ps", "ot20_a", "ot20_b", "p_ot20"):
        s2[c] = np.nan
    keep_from = O.TE_FROM
    O.TE_FROM = "2025-01-01"
    try:
        rule = O.construct(s2).set_index("match_id")
    finally:
        O.TE_FROM = keep_from
    dl = Q.drop_late(s).set_index("match_id")
    d = fr.astype({"match_id": str}).set_index("match_id")
    d["day"] = pd.to_datetime(dl["tex_date"].reindex(d.index)).fillna(d["tournament_date"])
    te_a, te_b = dl["tex_a"].reindex(d.index), dl["tex_b"].reindex(d.index)
    d["p_te_all"] = np.where(OC.coherent(te_a, te_b), OC.devig(te_a, te_b), np.nan)
    r = rule.reindex(d.index)
    d["p_te_rule"] = np.where(r["odds_input"] == O.K_TE, r["p_input"], np.nan)
    bol_a, bol_b = dl["ot8_a"].reindex(d.index), dl["ot8_b"].reindex(d.index)
    d["p_bol"] = np.where(OC.coherent(bol_a, bol_b), OC.devig(bol_a, bol_b), np.nan)
    ps_a, ps_b = dl["ps_a"].reindex(d.index), dl["ps_b"].reindex(d.index)
    faithful = pd.to_datetime(dl["td_date"].reindex(d.index)) <= pd.Timestamp("2025-07-23")
    d["p_ps"] = np.where(OC.coherent(ps_a, ps_b) & faithful, OC.devig(ps_a, ps_b), np.nan)
    d["over_te"] = 1 / te_a + 1 / te_b - 1
    d["over_bol"] = 1 / bol_a + 1 / bol_b - 1
    y = d["a_won"].astype(float).to_numpy()
    for k in ("te_all", "te_rule", "bol", "ps"):
        d[f"ll_{k}"] = OC.log_loss(d[f"p_{k}"], y)
    d["block"] = OC.blocks(d["day"].values.astype("datetime64[D]"))
    when = pd.to_datetime(d["tournament_date"])

    rows, res = [], {"instance": str(INST.relative_to(ROOT)), "link": how}

    def reading(label: str, mask, a: str, b: str, kind: str):
        m = mask & d[f"p_{a}"].notna() & d[f"p_{b}"].notna()
        x = d[m]
        ci = OC.mean_ci((x[f"ll_{a}"] - x[f"ll_{b}"]).to_numpy(), x["block"].to_numpy())
        row = {"reading": label, "kind": kind, "a": a, "b": b, **ci, "verdict": verdict(ci, a),
               "ll_a": float(x[f"ll_{a}"].mean() * 1000) if len(x) else None,
               "ll_b": float(x[f"ll_{b}"].mean() * 1000) if len(x) else None,
               "margin_a": float(x[f"over_{a[:2] if a.startswith('te') else a}"].median()) if a.startswith("te") and len(x)
               else None}
        rows.append(row)
        return row

    gap = when >= "2025-11-01"
    y26 = when >= "2026-01-01"
    reading("Nov 2025 - Oct 2026 (declared primary)", gap, "te_all", "bol", "primary")
    reading("2026 (Jan - Oct)", y26, "te_all", "bol", "secondary")
    reading("Nov 2025 - Oct 2026, the price the model will use", gap, "te_rule", "bol", "secondary")
    reading("2026 (Jan - Oct), the price the model will use", y26, "te_rule", "bol", "secondary")
    for tour in ("atp", "wta"):
        reading(f"Nov 2025 - Oct 2026, {tour.upper()}, the price the model will use", gap & (d["tour"] == tour),
                "te_rule", "bol", "flag")
    ov = (when >= "2025-01-01") & (pd.to_datetime(d["day"]) <= "2025-07-23")
    tri = ov & d["p_te_rule"].notna() & d["p_bol"].notna() & d["p_ps"].notna()
    reading("1 Jan - 23 Jul 2025: the site's last price - Pinnacle's own close", tri, "te_rule", "ps", "flag")
    reading("1 Jan - 23 Jul 2025: BetOnline's close - Pinnacle's own close", tri, "bol", "ps", "flag")
    reading("1 Jan - 23 Jul 2025: the site's last price - BetOnline's close", tri, "te_rule", "bol", "flag")
    res["readings"] = rows
    m = gap & d["p_te_rule"].notna() & d["p_bol"].notna()
    x = d[m]
    res["encompassing_nov2025_oct2026"] = encompassing(OC.lg(x["p_te_rule"]), OC.lg(x["p_bol"]),
                                                       x["a_won"].astype(float).to_numpy(), x["block"].to_numpy())
    res["margins_nov2025_oct2026"] = {"te_median": float(x["over_te"].median()), "bol_median": float(x["over_bol"].median())}
    OC.write_json(OUT / "sharpness.json", res)

    md = ["# Which is sharper: Pinnacle's last price (TennisExplorer) or BetOnline's close?", "",
          "Written by `src/eda/pinnacle_gap/sharpness.py`. Log loss in mLL (thousandths of a nat): lower is sharper. "
          "\"A − B\": + = A worse. 95% intervals over four-week blocks. Reads results.", "",
          "| Reading | A | B | Matches | A's log loss | B's log loss | A − B | Verdict |", "|---|---|---|---:|---:|---:|---|---|"]
    names = {"te_all": "site's Pinnacle (all rows)", "te_rule": "site's Pinnacle (as the model uses it)",
             "bol": "BetOnline's close", "ps": "Pinnacle's own close"}
    for r_ in rows:
        est = "—" if r_["est"] is None else f"{r_['est']:+.2f} [{r_['lo']:+.2f}, {r_['hi']:+.2f}]"
        md.append(f"| {r_['reading']} | {names[r_['a']]} | {names[r_['b']]} | {r_['n']:,} | "
                  f"{r_['ll_a']:.1f} | {r_['ll_b']:.1f} | {est} | {r_['verdict']} |")
    e = res["encompassing_nov2025_oct2026"]
    md += ["", f"**Encompassing, Nov 2025 – Oct 2026** ({e['n']:,} matches): the result fitted on both prices' log-odds. "
           f"Weight on the site's Pinnacle {e['w1']:.2f} [{e['w1_lo']:.2f}, {e['w1_hi']:.2f}], on BetOnline's close "
           f"{e['w2']:.2f} [{e['w2_lo']:.2f}, {e['w2_hi']:.2f}] (1 and 0: the first carries everything the second does).",
           "", f"Margins, median: the site's Pinnacle {res['margins_nov2025_oct2026']['te_median']:.2%}, BetOnline "
           f"{res['margins_nov2025_oct2026']['bol_median']:.2%}."]
    (OUT / "sharpness_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
