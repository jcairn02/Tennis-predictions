"""Part F, step 2: what tennis-data's PSW/PSL are after July 2025.

The odds-sources study (§ 2.1) found that tennis-data's Pinnacle column stops matching Pinnacle's own last line
(OddsTrader's timed recording, book 20) in August 2025: same price on 55-72% of matches a month to June 2025, 14% in
August and September. The column runs on to mid-January 2026. Here, month by month from October 2024:

    1. Identity (reads no result): how often PS is the same price as Pinnacle's last line and opening line at OddsTrader
       (to 7 Sep 2025), BetOnline's last line, each other OddsTrader book's last line, and tennis-data's own Bet365,
       maximum, average and Betfair columns; PS's median overround (Pinnacle's margin is about 2.8%).
    2. Timing (reads no result): the share of a book's own move, opening to last line, that PS has made. With z the
       margin-free log-odds, the slope of (z_PS - z_open) on (z_last - z_open) through the origin, on matches whose line
       moved by more than MOVE. 1 = PS sits at the last line, 0 = at the opening. Against Pinnacle's own opening and
       last line (OddsTrader, to 7 Sep 2025) and against BetOnline's (betonline_matches.parquet, every month).
    3. Accuracy (results before the seal only): PS against Pinnacle's last line (OddsTrader) and opening line, and
       against BetOnline's last line, by period.

"Same price": both sides within 0.011 in decimal odds, the OddsTrader price rounded to 2 decimals (as
odds_sources/quality.pinnacle_by_month).

Writes data/studies/source_reconciliation/odds/psx.json and psx_tables.md (aggregates only).
Run: ./python.sh src/eda/source_reconciliation/odds_psx.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.eda.source_reconciliation import odds_common as O  # noqa: E402

FROM_MONTH = "2024-10"
MOVE = 0.10                 # log-odds a book's line must move, opening to last, for the timing slope
TOL = 0.011
MIN_ROWS = 40


def american_to_decimal(a) -> np.ndarray:
    a = np.asarray(a, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(a > 0, 1 + a / 100.0, np.where(a < 0, 1 + 100.0 / np.abs(a), np.nan))


def same_price(a1, b1, a2, b2) -> np.ndarray:
    a1, b1, a2, b2 = (np.asarray(x, float) for x in (a1, b1, a2, b2))
    return (np.abs(a1 - np.round(a2, 2)) <= TOL) & (np.abs(b1 - np.round(b2, 2)) <= TOL)


def betonline_open(df: pd.DataFrame) -> pd.DataFrame:
    """BetOnline's opening and last line for side A, from betonline_matches.parquet (the pull of 7 Oct 2026), oriented
    by matching its last line to the table's (books_lines, 9 Oct 2026). Rows whose two pulls disagree are left out."""
    b = pd.read_parquet(O.BOL_MATCHES, columns=["eid", "mw_open_home", "mw_open_away", "mw_open_utc", "mw_close_home",
                                                "mw_close_away", "mw_close_uncertain", "dt_ms"])
    b = b.drop_duplicates("eid")
    x = df[["match_id", "eid", "ot8_a", "ot8_b"]].merge(b, on="eid", how="left")
    ch, ca = american_to_decimal(x["mw_close_home"]), american_to_decimal(x["mw_close_away"])
    oh, oa = american_to_decimal(x["mw_open_home"]), american_to_decimal(x["mw_open_away"])
    a_away = same_price(x["ot8_a"], x["ot8_b"], ca, ch)
    a_home = same_price(x["ot8_a"], x["ot8_b"], ch, ca)
    ok = (a_away ^ a_home) & ~x["mw_close_uncertain"].fillna(True).astype(bool).to_numpy()
    open_a = np.where(a_away, oa, oh)
    open_b = np.where(a_away, oh, oa)
    good = ok & OC.coherent(open_a, open_b)
    open_ms = (pd.to_datetime(x["mw_open_utc"], utc=True) - pd.Timestamp("1970-01-01", tz="UTC")
               ).dt.total_seconds().to_numpy(float) * 1000.0
    out = pd.DataFrame({"match_id": x["match_id"].to_numpy(),
                        "p_bolo": np.where(good, OC.devig(open_a, open_b), np.nan),
                        "bolo_hours_before": np.where(good, (x["dt_ms"].to_numpy(float) - open_ms) / 3.6e6, np.nan)})
    return out, {"rows_with_betonline_last": int(np.isfinite(df["ot8_a"].to_numpy(float)).sum()),
                 "oriented": int(ok.sum()), "both_orientations_or_none": int((np.isfinite(df["ot8_a"].to_numpy(float))
                                                                             & ~(a_away ^ a_home)).sum())}


def capture(z_src, z_open, z_last, mask) -> dict:
    """Slope of (z_src - z_open) on (z_last - z_open) through the origin, where the line moved over MOVE."""
    d = z_last - z_open
    m = mask & np.isfinite(z_src) & np.isfinite(z_open) & np.isfinite(z_last) & (np.abs(d) > MOVE)
    if m.sum() < 20:
        return {"n": int(m.sum())}
    x, yv = d[m], (z_src - z_open)[m]
    b = float((x * yv).sum() / (x * x).sum())
    # share of matches where the source is nearer the last line than the opening
    nearer_last = float((np.abs(z_src[m] - z_last[m]) < np.abs(z_src[m] - z_open[m])).mean())
    return {"n": int(m.sum()), "slope": round(b, 3), "nearer_last_share": round(nearer_last, 3)}


def identity(df: pd.DataFrame) -> dict:
    x = df[np.isfinite(df["p_ps"].to_numpy(float)) & (df["month"] >= FROM_MONTH)]
    books = [s for s in Q.closing_ot(df) if s not in ("ot20",)]
    out = {}
    for month, g in x.groupby("month"):
        if len(g) < MIN_ROWS:
            continue
        row = {"n": int(len(g)), "ps_overround_median": round(float(g["over_ps"].median()), 4)}
        for name, (ca, cb) in {"pin_last_ot20": ("ot20_a", "ot20_b"), "pin_open_ot20o": ("ot20o_a", "ot20o_b"),
                               "bfe": ("bfe_a", "bfe_b"), "b365": ("b365_a", "b365_b"), "max": ("max_a", "max_b"),
                               "avg": ("avg_a", "avg_b")}.items():
            both = np.isfinite(g[ca].to_numpy(float)) & np.isfinite(g["ps_a"].to_numpy(float))
            if both.sum() < 20:
                continue
            sp = same_price(g["ps_a"], g["ps_b"], g[ca], g[cb])[both]
            gap = np.abs(OC.lg(g["p_ps"].to_numpy(float)) - OC.lg(OC.devig(g[ca], g[cb])))[both]
            row[name] = {"n": int(both.sum()), "same_price": round(float(sp.mean()), 3),
                         "median_gap": round(float(np.median(gap)), 4)}
        best = []
        for s in books:
            both = np.isfinite(g[f"{s}_a"].to_numpy(float))
            if both.sum() < 20:
                continue
            sp = same_price(g["ps_a"], g["ps_b"], g[f"{s}_a"], g[f"{s}_b"])[both]
            gap = np.abs(OC.lg(g["p_ps"].to_numpy(float)) - OC.lg(g[f"p_{s}"].to_numpy(float)))[both]
            best.append((s, int(both.sum()), float(sp.mean()), float(np.median(gap))))
        best.sort(key=lambda r: -r[2])
        row["oddstrader_books_most_often_same_price"] = [
            {"book": s, "name": Q.name(s), "n": n, "same_price": round(sh, 3), "median_gap": round(gp, 4)}
            for s, n, sh, gp in best[:4]]
        row["bol_ot8"] = next(({"n": n, "same_price": round(sh, 3), "median_gap": round(gp, 4)}
                               for s, n, sh, gp in best if s == "ot8"), None)
        out[month] = row
    return out


def timing(df: pd.DataFrame, bolo: pd.DataFrame) -> dict:
    x = df.merge(bolo, on="match_id", how="left")
    z = {k: OC.lg(x[c].to_numpy(float)) for k, c in
         (("ps", "p_ps"), ("pin_open", "p_ot20o"), ("pin_last", "p_ot20"), ("bol_open", "p_bolo"),
          ("bol_last", "p_bol"), ("bfe", "p_bfe"), ("avg", "p_avg"), ("b365", "p_b365"), ("pm", "p_pm"))}
    out = {}
    for month in sorted(x.loc[x["month"] >= FROM_MONTH, "month"].unique()):
        m = (x["month"] == month).to_numpy()
        if m.sum() < MIN_ROWS:
            continue
        row = {"against_pinnacle_open_to_last": {s: capture(z[s], z["pin_open"], z["pin_last"], m)
                                                 for s in ("ps", "bol_last", "bfe", "avg", "b365")},
               "against_betonline_open_to_last": {s: capture(z[s], z["bol_open"], z["bol_last"], m)
                                                  for s in ("ps", "pin_last", "bfe", "avg", "b365", "pm")},
               "betonline_opening_hours_before_listed_median":
                   round(float(np.nanmedian(x.loc[m, "bolo_hours_before"])), 1)
                   if np.isfinite(x.loc[m, "bolo_hours_before"]).any() else None}
        out[month] = row
    return out


def accuracy(df: pd.DataFrame, y: np.ndarray, bolo: pd.DataFrame) -> dict:
    x = df.merge(bolo, on="match_id", how="left")
    if not (x["match_id"].to_numpy() == df["match_id"].to_numpy()).all():
        raise RuntimeError("row order changed")
    d = x["td_date"]
    periods = {"2024-10..2025-07 (PS faithful)": (d >= "2024-10-01") & (d <= "2025-07-31"),
               "2025-08-01..2025-09-07 (OddsTrader's Pinnacle known)": (d >= "2025-08-01") & (d <= "2025-09-07"),
               "2025-09-08..2026-01 (no Pinnacle)": (d >= "2025-09-08") & (d < "2026-02-01")}
    blk = x["block"].to_numpy()
    day = (x["td_date"].to_numpy("datetime64[D]") - np.datetime64("2010-01-01")).astype(int)
    out = {}
    for lab, m in periods.items():
        m = m.to_numpy()
        short = "OddsTrader" in lab            # five weeks: two four-week blocks, so match days are the clusters
        row = {"clusters": "match day" if short else "four-week block"}
        for a, b in (("p_ps", "p_ot20"), ("p_ps", "p_ot20o"), ("p_ps", "p_bol"), ("p_ps", "p_bolo"),
                     ("p_bolo", "p_bol"), ("p_ot20o", "p_ot20"), ("p_bol", "p_ot20"), ("p_ps", "p_bfe")):
            r = O.paired(x[a], x[b], y, day if short else blk, m)
            if r.get("est") is not None:
                row[f"{a[2:]}_minus_{b[2:]}"] = r
        out[lab] = row
    return out


def tables(res: dict) -> str:
    L = ["# What tennis-data's PSW/PSL are after July 2025 (generated by odds_psx.py)", "",
         "Same price: both sides within 0.011 in decimal odds. Gap: median |difference| of margin-free log-odds.", "",
         "## 1. Identity by month", "",
         "| Month | Matches | PS overround (median) | = Pinnacle last (OddsTrader) | = Pinnacle opening (OddsTrader) "
         "| = BetOnline last | Book most often the same price | = Betfair | = Bet365 | = maximum |",
         "|---|---:|---:|---|---|---|---|---|---|---|"]

    def cell(v):
        return "—" if not v else f"{v['same_price']:.0%} (gap {v['median_gap']:.3f}, n {v['n']})"

    for month, r in res["identity"].items():
        top = r["oddstrader_books_most_often_same_price"][:1]
        tb = "—" if not top else f"{top[0]['name']}: {top[0]['same_price']:.0%} (gap {top[0]['median_gap']:.3f})"
        L.append(f"| {month} | {r['n']:,} | {r['ps_overround_median']:.4f} | {cell(r.get('pin_last_ot20'))} | "
                 f"{cell(r.get('pin_open_ot20o'))} | {cell(r.get('bol_ot8'))} | {tb} | {cell(r.get('bfe'))} | "
                 f"{cell(r.get('b365'))} | {cell(r.get('max'))} |")
    L += ["", "## 2. Timing: the share of a book's opening-to-last move that each price has made", "",
          f"Slope through the origin of (z − z_open) on (z_last − z_open), matches whose line moved over {MOVE} in "
          "log-odds; 1 = at the last line, 0 = at the opening. In brackets: matches; share nearer the last line.", "",
          "| Month | PS vs Pinnacle's move | BetOnline last vs Pinnacle's move | PS vs BetOnline's move | "
          "Pinnacle last vs BetOnline's move | Betfair vs BetOnline's move | Polymarket 30 min vs BetOnline's move |",
          "|---|---|---|---|---|---|---|"]

    def cap(v):
        return "—" if not v or "slope" not in v else f"{v['slope']:.2f} ({v['n']}; {v['nearer_last_share']:.0%})"

    for month, r in res["timing"].items():
        p, b = r["against_pinnacle_open_to_last"], r["against_betonline_open_to_last"]
        L.append(f"| {month} | {cap(p['ps'])} | {cap(p['bol_last'])} | {cap(b['ps'])} | {cap(b['pin_last'])} | "
                 f"{cap(b['bfe'])} | {cap(b['pm'])} |")
    L += ["", "## 3. Accuracy against results (before the seal), mLL, + = the first named worse", "",
          "| Period | Comparison | Matches | Difference | Verdict |", "|---|---|---:|---|---|"]
    for lab, row in res["accuracy"].items():
        for k, v in row.items():
            if k == "clusters":
                continue
            pb = v.get("p_neg")
            L.append(f"| {lab} (clusters: {row['clusters']}) | {k.replace('_minus_', ' − ')} | {v['n']:,} | "
                     f"{O.fmt(v)} | {O.verdict(v)}"
                     + (f" (P(first better) {pb:.2f})" if O.verdict(v) == "unresolved" and pb is not None else "")
                     + " |")
    L += ["", "Names: ps = tennis-data PSW/PSL; ot20 = Pinnacle's last line at OddsTrader; ot20o = Pinnacle's opening "
          "line there; bol = BetOnline's last line; bolo = BetOnline's opening line; bfe = Betfair (tennis-data).", ""]
    return "\n".join(L) + "\n"


def main() -> int:
    O.OUT.mkdir(parents=True, exist_ok=True)
    df = O.load_table()
    raw = pd.read_parquet(O.TABLE, columns=["match_id", "ot8_a", "ot8_b"])    # BetOnline's last line before drop_late
    raw["match_id"] = raw["match_id"].astype(str)
    if not (raw["match_id"].to_numpy() == df["match_id"].to_numpy()).all():
        raise RuntimeError("row order")
    bolo, bolo_info = betonline_open(df.drop(columns=["ot8_a", "ot8_b"]).assign(ot8_a=raw["ot8_a"], ot8_b=raw["ot8_b"]))
    sel = (df["month"] >= FROM_MONTH).to_numpy()
    res = {"identity": identity(df[sel]), "timing": timing(df[sel], bolo), "betonline_opening_join": bolo_info}
    y = O.attach_y(df)
    res["accuracy"] = accuracy(df[sel].reset_index(drop=True), y[sel], bolo)
    res["inputs_sha256"] = O.sha_inputs()
    O.write_json(O.OUT / "psx.json", res)
    (O.OUT / "psx_tables.md").write_text(tables(res), encoding="utf-8")
    print(tables(res)[:12000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
