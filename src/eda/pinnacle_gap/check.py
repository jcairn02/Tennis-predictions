"""Pinnacle's closes from TennisExplorer for the missing months: coverage, recording quality, timing, and accuracy
against BetOnline's close (the current stand-in). Research for docs/research/pinnacle-gap/; not a model change.

Reads the adapter's staged tables (src/ingest/tennisexplorer.py: link.parquet, odds.parquet, matches.parquet), the
current instance's frame and book prices, and the odds-sources study's table (tennis-data's and OddsTrader's Pinnacle).
Writes data/studies/pinnacle_gap/check.json and check_tables.md: aggregates only (no raw prices; the repository is
public).

Conventions as the odds-sources study (docs/studies/odds_sources/README.md): prices margin-free (proportional);
"the same price" = both sides within 0.01 (TennisExplorer shows two decimals); log-odds gaps in absolute value;
a gross disagreement = over 1.0 in log-odds and 10 points of chance from the median of at least 3 other books that
agree among themselves (IQR under 0.35), a mirror = within 0.35 of that median's mirror. Accuracy in mLL (thousandths
of a nat), "A - B": + = A worse; 95% intervals over four-week blocks; "unresolved" with P(A better) when the interval
spans 0. The accuracy rows read results: they are source checks, logged as looks in the process log.

    ./python.sh src/eda/pinnacle_gap/check.py [--instance data/studies/current_best_model/template_2026-10-21b]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm as normal

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as OC  # noqa: E402

TE = ROOT / "data" / "dump" / "odds" / "tennisexplorer"
OUT = ROOT / "data" / "studies" / "pinnacle_gap"
INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-21b"
SAME = 0.0101
EXCLUDE_REFEREE = {"Pinnacle", "Betfair Exchange"}


def lo(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log((1 / a) / (1 / b))


def same(a1, b1, a2, b2):
    return (np.abs(np.asarray(a1, float) - np.asarray(a2, float)) <= SAME) & \
           (np.abs(np.asarray(b1, float) - np.asarray(b2, float)) <= SAME)


def verdict(ci: dict) -> str:
    if ci["est"] is None or ci["n"] < 2:
        return "—"
    if ci["lo"] > 0:
        return "worse"
    if ci["hi"] < 0:
        return "better"
    se = (ci["hi"] - ci["lo"]) / (2 * 1.96)
    return f"unresolved (P(better) {normal.cdf(-ci['est'] / se):.2f})" if se > 0 else "unresolved"


def fmt_ci(ci: dict) -> str:
    if ci["est"] is None:
        return "—"
    return f"{ci['est']:+.2f} [{ci['lo']:+.2f}, {ci['hi']:+.2f}], {verdict(ci)} (n {ci['n']:,})"


def load(instance: Path) -> pd.DataFrame:
    fr = pd.read_parquet(instance / "model_frame.parquet",
                         columns=["match_id", "tour", "season", "tournament_date", "a_won", "odds_input", "p_mkt",
                                  "p_mkt_avg"])
    bp = pd.read_parquet(instance / "book_prices.parquet",
                         columns=["match_id", "pin_a", "pin_b", "bol_a", "bol_b", "bol_after_listed_min"])
    d = fr.merge(bp, on="match_id", how="left")
    src = pd.read_parquet(ROOT / "data" / "studies" / "odds_sources" / "sources.parquet",
                          columns=["match_id", "td_date", "ps_a", "ps_b", "ot20_a", "ot20_b", "after_ot20_min"])
    d = d.merge(src, on="match_id", how="left")
    ln = pd.read_parquet(TE / "link.parquet")
    ln = ln.rename(columns={"pin_a": "te_a", "pin_b": "te_b", "pin_open_a": "te_open_a", "pin_open_b": "te_open_b",
                            "pin_open_t": "te_open_t", "pin_last_t": "te_last_t", "pin_n_moves": "te_n_moves"})
    d = d.merge(ln, on="match_id", how="left")
    d["month"] = d.tournament_date.dt.strftime("%Y-%m")
    d["day"] = pd.to_datetime(d.te_date).fillna(d.tournament_date)
    d["block"] = OC.blocks(d.day.values.astype("datetime64[D]"))
    return d


def referee(d: pd.DataFrame) -> pd.DataFrame:
    """Per linked match: the median log-odds (for A) of TennisExplorer's other books and their IQR."""
    od = pd.read_parquet(TE / "odds.parquet", columns=["te_id", "book", "k1_last", "k2_last"])
    od = od[~od.book.isin(EXCLUDE_REFEREE)].copy()
    od["z"] = lo(od.k1_last, od.k2_last)
    od = od[np.isfinite(od.z)]
    g = od.groupby("te_id").z
    ref = pd.DataFrame({"ref_n": g.size(), "ref_med": g.median(),
                        "ref_iqr": g.quantile(0.75) - g.quantile(0.25)})
    x = d[["match_id", "te_id", "a_is_p2"]].dropna(subset=["te_id"]).join(ref, on="te_id")
    x["ref_med"] = np.where(x.a_is_p2.astype(bool), -x.ref_med, x.ref_med)
    return x.set_index("match_id")[["ref_n", "ref_med", "ref_iqr"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=Path, default=INSTANCE)
    ap.add_argument("--no-accuracy", action="store_true", help="skip § 5 (the only part that reads results)")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = load(a.instance)
    d = d.join(referee(d), on="match_id")
    res, md = {"instance": str(a.instance.relative_to(ROOT)), "te_link_rows": int(d.te_id.notna().sum())}, []
    have_te = d.te_a.notna() & d.te_b.notna()
    d["te_coherent"] = have_te & OC.coherent(d.te_a, d.te_b)
    d["z_te"] = lo(d.te_a, d.te_b)
    d["p_te"] = OC.devig(d.te_a, d.te_b)

    # --- 1. coverage ------------------------------------------------------------------------------------------
    gap = d[d.tournament_date >= "2025-08-01"]
    cov = gap.groupby(["month"]).agg(frame=("match_id", "size"), linked=("te_id", lambda s: int(s.notna().sum())),
                                     pinnacle=("te_coherent", "sum"))
    cov = cov.astype(int)
    cov["share"] = (cov.pinnacle / cov.frame).round(3)
    by_src = gap.groupby("odds_input").agg(frame=("match_id", "size"), pinnacle=("te_coherent", "sum"))
    res["coverage_by_month"] = cov.reset_index().to_dict("records")
    res["coverage_by_current_source"] = by_src.reset_index().to_dict("records")
    md += ["## 1. Coverage of the frame's matches from August 2025", "",
           "| Month | Frame matches | Linked to TennisExplorer | With a Pinnacle price | Share |", "|---|---:|---:|---:|---:|"]
    md += [f"| {m} | {r.frame:,} | {r.linked:,} | {int(r.pinnacle):,} | {r.share:.1%} |" for m, r in cov.iterrows()]
    tot = cov.sum()
    md += [f"| **All** | **{int(tot.frame):,}** | **{int(tot.linked):,}** | **{int(tot.pinnacle):,}** | "
           f"**{tot.pinnacle / tot.frame:.1%}** |", "", "By the source the current instance uses there:", "",
           "| Current odds input | Frame matches | With a TennisExplorer Pinnacle price |", "|---|---:|---:|"]
    md += [f"| {k} | {r.frame:,} | {int(r.pinnacle):,} |" for k, r in by_src.iterrows()]
    md.append("")

    # --- 2. agreement with the other Pinnacle records ----------------------------------------------------------
    rows = []
    for name, ca, cb, keep in (("tennis-data PSW/PSL", "ps_a", "ps_b", d.ps_a.notna()),
                               ("OddsTrader book 20 (stamped <= 30 min after the start)", "ot20_a", "ot20_b",
                                d.ot20_a.notna() & ~(d.after_ot20_min > 30))):
        x = d[have_te & keep]
        for m, g in x.groupby("month"):
            gap_z = np.abs(g.z_te - lo(g[ca], g[cb]))
            rows.append({"against": name, "month": m, "n": len(g),
                         "same": float(same(g.te_a, g.te_b, g[ca], g[cb]).mean()),
                         "median_gap": float(np.nanmedian(gap_z)), "over_0.1": float((gap_z > 0.1).mean()),
                         "over_1.0_per_1000": float((gap_z > 1.0).mean() * 1000)})
    agr = pd.DataFrame(rows)
    res["agreement"] = agr.to_dict("records")
    md += ["## 2. TennisExplorer's last Pinnacle price against the other recordings of Pinnacle", "",
           "| Against | Month | Matches | Same price | Median gap (log-odds) | Gap over 0.1 | Over 1.0, per 1,000 |",
           "|---|---|---:|---:|---:|---:|---:|"]
    md += [f"| {r.against} | {r.month} | {r.n:,} | {r.same:.0%} | {r.median_gap:.3f} | {r.over_01:.1%} | "
           f"{r.over_10:.1f} |" for r in agr.rename(columns={"over_0.1": "over_01", "over_1.0_per_1000": "over_10"}).itertuples()]
    md.append("")

    # --- 3. timing and margins ---------------------------------------------------------------------------------
    t = d[have_te].copy()
    t["start"] = pd.to_datetime(t.start_utc, utc=True)
    t["last"] = pd.to_datetime(t.te_last_t, utc=True)
    t["open"] = pd.to_datetime(t.te_open_t, utc=True)
    t["min_before"] = (t.start - t["last"]).dt.total_seconds() / 60
    t["open_h_before"] = (t.start - t["open"]).dt.total_seconds() / 3600
    t["untimed"] = t.te_open_t.isna() & t.te_n_moves.fillna(0).eq(0)     # no change table at all: no time shown
    t["margin"] = 1 / t.te_a + 1 / t.te_b - 1
    t["q"] = t.tournament_date.dt.to_period("Q").astype(str)
    tim = t.groupby("q").agg(n=("match_id", "size"), untimed=("untimed", "mean"),
                             moves_median=("te_n_moves", "median"),
                             last_min_before_median=("min_before", "median"),
                             last_min_before_p90=("min_before", lambda s: s.quantile(0.9)),
                             after_start=("min_before", lambda s: float((s < 0).mean())),
                             open_h_before_median=("open_h_before", "median"),
                             margin_median=("margin", "median"))
    res["timing"] = tim.reset_index().to_dict("records")
    md += ["## 3. Timing and margin of TennisExplorer's Pinnacle prices (linked frame matches)", "",
           "| Quarter | Matches | No time shown (untimed) | Price changes recorded (both sides), median | Last change before the listed start, "
           "median min (90th pct) | Last change after the start | Opening, median h before | Margin, median |",
           "|---|---:|---:|---:|---|---:|---:|---:|"]
    md += [f"| {q} | {int(r.n):,} | {r.untimed:.0%} | {r.moves_median:.0f} | {r.last_min_before_median:.0f} "
           f"({r.last_min_before_p90:.0f}) | {r.after_start:.1%} | {r.open_h_before_median:.0f} | {r.margin_median:.2%} |"
           for q, r in tim.iterrows()]
    md.append("")

    # --- 4. gross disagreements with the site's other books ------------------------------------------------------
    g4 = d[have_te & (d.ref_n >= 3) & (d.ref_iqr < 0.35)].copy()
    dz = np.abs(g4.z_te - g4.ref_med)
    dp = np.abs(OC.ex(g4.z_te) - OC.ex(g4.ref_med))
    g4["gross"] = (dz > 1.0) & (dp > 0.10)
    g4["mirror"] = g4.gross & (np.abs(g4.z_te + g4.ref_med) < 0.35)
    gr = g4.groupby(g4.tournament_date.dt.year).agg(n=("match_id", "size"), gross=("gross", "sum"),
                                                     mirror=("mirror", "sum"))
    gr["per_1000"] = gr.gross / gr.n * 1000
    res["gross"] = gr.reset_index().to_dict("records")
    res["gross_rows"] = g4[g4.gross][["match_id", "te_id", "month"]].to_dict("records")
    # The same test turned round: tennis-data's average (the frame's p_mkt_avg) and the instance's own odds input
    # (p_mkt) against the site's books. A mirror here is a swapped tennis-data row or a swapped link of ours.
    sw = []
    for name, col in (("tennis-data's average", "p_mkt_avg"), ("the instance's odds input", "p_mkt")):
        z = OC.lg(g4[col])
        gross = (np.abs(z - g4.ref_med) > 1.0) & (np.abs(g4[col] - OC.ex(g4.ref_med)) > 0.10)
        mirror = gross & (np.abs(z + g4.ref_med) < 0.35)
        for _, r in g4[mirror].iterrows():
            sw.append({"price": name, "match_id": r.match_id, "te_id": int(r.te_id), "month": r.month,
                       "odds_input": r.odds_input, "p_price": float(r[col]), "p_site_books": float(OC.ex(r.ref_med)),
                       "p_site_pinnacle": float(r.p_te) if pd.notna(r.p_te) else None})
        res[f"mirrors_{col}"] = {"matches": int(len(g4)), "gross": int(gross.sum()), "mirrors": int(mirror.sum())}
    res["mirror_rows"] = sw
    md += ["## 4. Gross disagreements with TennisExplorer's other books", "",
           "| Season | Matches with a referee | Gross | Of them mirrors | Per 1,000 |", "|---|---:|---:|---:|---:|"]
    md += [f"| {y} | {int(r.n):,} | {int(r.gross)} | {int(r.mirror)} | {r.per_1000:.2f} |" for y, r in gr.iterrows()]
    md += ["", "The other way round: prices on our side that are the mirror image of the site's books "
           "(a swapped tennis-data row, or a swapped link of ours):", "",
           "| Price | Matches with a referee | Gross | Of them mirrors |", "|---|---:|---:|---:|"]
    md += [f"| {n} | {res[f'mirrors_{c}']['matches']:,} | {res[f'mirrors_{c}']['gross']} | {res[f'mirrors_{c}']['mirrors']} |"
           for n, c in (("tennis-data's average", "p_mkt_avg"), ("the instance's odds input", "p_mkt"))]
    if sw:
        md += ["", "| Price | Match | Month | Current input's source | Its chance for A | The site's books | The site's Pinnacle |",
               "|---|---|---|---|---:|---:|---:|"]
        md += [f"| {r['price']} | `{r['match_id']}` | {r['month']} | {r['odds_input']} | {r['p_price']:.2f} | "
               f"{r['p_site_books']:.2f} | {r['p_site_pinnacle'] if r['p_site_pinnacle'] is None else round(r['p_site_pinnacle'], 2)} |"
               for r in sw]
    md.append("")

    # --- 5. accuracy (reads results) -----------------------------------------------------------------------------
    acc = []
    y = d.a_won.astype(float)
    d["ll_te"] = OC.log_loss(d.p_te, y)
    clean_bol = d.bol_a.notna() & ~(d.bol_after_listed_min > 30)
    d["ll_bol"] = OC.log_loss(OC.devig(d.bol_a, d.bol_b), y)
    d["ll_ps"] = OC.log_loss(OC.devig(d.ps_a, d.ps_b), y)
    d["ll_avg"] = OC.log_loss(d.p_mkt_avg, y)
    # The declared primary (21 Oct 2026, before any accuracy was read): Nov 2025 - Oct 2026, TennisExplorer's Pinnacle
    # against BetOnline's clean close. The overlap stops on 23 Jul 2025: tennis-data's column is Pinnacle's own close
    # only to the API's closure (process log, 18:33).
    periods = (("Nov 2025 - Oct 2026 (primary)", "2025-11-01", "2026-12-31"),
               ("Aug-Oct 2025 (mostly untimed)", "2025-08-01", "2025-10-31"),
               ("the gap, Aug 2025 on", "2025-08-01", "2026-12-31"),
               ("the overlap, 1 Jan - 23 Jul 2025", "2025-01-01", "2025-07-23"))
    for label, lo_d, hi_d in (() if a.no_accuracy else periods):
        w = d[(d.tournament_date >= lo_d) & (d.tournament_date <= hi_d) & d.te_coherent]
        for other, col, keep in (("BetOnline's close", "ll_bol", clean_bol), ("the books' average", "ll_avg",
                                                                              d.p_mkt_avg.notna()),
                                 ("tennis-data's Pinnacle", "ll_ps", d.ps_a.notna())):
            x = w[keep.loc[w.index]]
            if len(x) < 30:
                continue
            ci = OC.mean_ci((x.ll_te - x[col]).values, x.block.values)
            acc.append({"period": label, "against": other, **ci, "verdict": verdict(ci)})
    res["accuracy"] = acc
    md += ["## 5. Accuracy: TennisExplorer's Pinnacle against the other prices (reads results)", "",
           "mLL, TennisExplorer's Pinnacle − the other price (+ = TennisExplorer's Pinnacle worse), same matches.", "",
           "| Period | Against | TennisExplorer − it |", "|---|---|---|"]
    md += [f"| {r['period']} | {r['against']} | {fmt_ci(r)} |" for r in acc]
    md.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    OC.write_json(OUT / "check.json", res)
    (OUT / "check_tables.md").write_text("# Pinnacle from TennisExplorer: check tables\n\nWritten by "
                                         "`src/eda/pinnacle_gap/check.py`.\n\n" + "\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
