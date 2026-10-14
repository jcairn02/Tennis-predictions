"""Odds sources, step 2: recording flaws in each source's closing prices.

The owner's idea of 9 Oct 2026: "If we use them as history and some matches show -600/+400 while the oddsportal has it
-110/-110 it shows that there may be some data issues and we may want to use the more stable books rather than the
outlier."

    1. Pinnacle recorded twice: tennis-data's untimed close and the last line OddsTrader recorded (book 20), 2018-2025.
       How often they agree; where they disagree, which one the other books side with and which one the result does.
    2. Each source against the others: for every match, the median margin-free log-odds of the other books. Never the
       source's own other recording or its clone (Pinnacle twice; Bet365 three times; BetOnline and SportsBetting.ag),
       never the maximum, Polymarket or an opening line. How far each source sits from it; how often it is grossly off
       (over GROSS in log-odds while the others agree within AGREE); how often it is their mirror image (the sides
       exchanged); and who was right when it was grossly off.
    3. Late stamps: OddsTrader's last lines stamped after the listed start. Are they in-play prices, more right than
       the closes around them?

Reads data/studies/odds_sources/sources.parquet; writes quality.json and quality_tables.md.
Run: ./python.sh src/eda/odds_sources/quality.py
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as C  # noqa: E402

GROSS = 1.0       # log-odds from the others' median: 50% against 73%, 80% against 92%; -600/+400 against -110/-110 is 1.45
GROSS_PP = 0.10   # ... and at least 10 points of chance apart (98% against 93% is 1.3 in log-odds but not a recording error)
AGREE = 0.35      # the others' interquartile range of log-odds must be below this for a gross disagreement to count
SWAP = 0.35       # a gross source this close to the mirror image of the others' median has its two sides exchanged
MIN_REF = 3       # other books needed for a median
SAME_BOOK = ({"ps", "ot20"}, {"b365", "ot5", "ot106"}, {"ot8", "ot131"})
NAMED = {"avg": "Market average (OddsPortal via tennis-data)", "max": "Market maximum", "ps": "Pinnacle (tennis-data)",
         "b365": "Bet365 (tennis-data)", "bfe": "Betfair exchange (tennis-data)", "ex": "Expekt (tennis-data)",
         "lb": "Ladbrokes (tennis-data)", "pm_m30": "Polymarket, 30 min before", "ot8": "BetOnline (OddsTrader)",
         "ot20": "Pinnacle (OddsTrader)", "ot131": "SportsBetting.ag (OddsTrader)", "ot10": "Bookmaker (OddsTrader)",
         "ot9": "Bovada (OddsTrader)", "ot44": "Heritage (OddsTrader)", "ot16": "JustBet (OddsTrader)",
         "ot29": "Everygame (OddsTrader)", "ot82": "MyBookie (OddsTrader)", "ot122": "SBK (OddsTrader)",
         "ot123": "BetAnything (OddsTrader)", "ot130": "Bet105 (OddsTrader)", "ot5": "Bet365 (OddsTrader)",
         "ot106": "Bet365, id 106 (OddsTrader)"}
LATE_BINS = [-np.inf, -60.0, 0.0, 30.0, 120.0, np.inf]
LATE_LABELS = ["over 1 h before", "within 1 h before", "0-30 min after", "30-120 min after", "over 2 h after"]
LATE_MIN = 30.0   # an OddsTrader line stamped later than this after the listed start may be in-play (the adapter's
                  # rule for BetOnline's closes); dropped wherever OddsTrader's books referee or are averaged


def name(s: str) -> str:
    if s in NAMED:
        return NAMED[s]
    if s.startswith("ot"):
        return f"OddsTrader book {s[2:].rstrip('o')}" + (" (opening)" if s.endswith("o") else "")
    return s


TD_REFEREES = ("avg", "ps", "b365", "ex", "lb", "bfe")      # tennis-data's closes that can referee


def source_names(df: pd.DataFrame) -> list[str]:
    return [c[2:] for c in df.columns if c.startswith("p_") and c != "p_mkt"]


def is_ot_book(s: str) -> bool:
    """An OddsTrader book's last line (ot<id>; not its opening, ot<id>o, nor anything derived)."""
    return re.fullmatch(r"ot\d+", s) is not None


def closing_ot(df: pd.DataFrame) -> list[str]:
    return [s for s in source_names(df) if is_ot_book(s)]


def drop_late(df: pd.DataFrame, minutes: float = LATE_MIN) -> pd.DataFrame:
    """A copy with every OddsTrader line stamped more than `minutes` after the listed start removed."""
    df = df.copy()
    for s in [c[2:] for c in df.columns if c.startswith("p_ot")]:
        late = (df[f"after_{s}_min"] > minutes).to_numpy()
        for col in (f"p_{s}", f"{s}_a", f"{s}_b", f"over_{s}"):
            df.loc[late, col] = np.nan
    return df


def reference_names(df: pd.DataFrame, s: str) -> list[str]:
    """The books that referee source s: tennis-data's closes and OddsTrader's last lines, less s's own group."""
    group = next((g for g in SAME_BOOK if s in g), {s})
    return [r for r in source_names(df) if (r in TD_REFEREES or is_ot_book(r)) and r not in group]


def reference(df: pd.DataFrame, names: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Median log-odds of these sources, how many are priced, and their interquartile range."""
    Z = C.lg(df[[f"p_{r}" for r in names]].to_numpy(float))
    n = np.isfinite(Z).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(Z, axis=1)
        q75, q25 = np.nanpercentile(Z, [75, 25], axis=1)
    return med, n, q75 - q25


def outcome(p_src, z_ref, y, blk) -> dict:
    """Who the result sided with: the source's log loss minus the others' median's (mLL; + = the source was worse),
    and, where the two pick different favourites, the share won by the source's favourite."""
    p_src, z_ref, y = np.asarray(p_src, float), np.asarray(z_ref, float), np.asarray(y, float)
    d = C.log_loss(p_src, y) - C.log_loss(C.ex(z_ref), y)
    split = (p_src > 0.5) != (z_ref > 0)
    out = {"ll_minus_others": C.mean_ci(d, blk) if len(d) >= 2 else None, "favourites_differ": int(split.sum())}
    if split.any():
        out["source_favourite_won"] = round(float(((p_src[split] > 0.5) == (y[split] == 1)).mean()), 3)
    return out


def disagreement(df: pd.DataFrame, s: str, ref_df: pd.DataFrame | None = None) -> dict:
    """The source as recorded in df against the other books' median in ref_df (default df)."""
    p = df[f"p_{s}"].to_numpy(float)
    ref_df = df if ref_df is None else ref_df
    med, n, iqr = reference(ref_df, reference_names(ref_df, s))
    sel = np.isfinite(p) & (n >= MIN_REF)
    z = C.lg(p)
    d = np.where(sel, z - med, np.nan)
    gross = sel & (np.abs(d) > GROSS) & (np.abs(p - C.ex(med)) > GROSS_PP) & (iqr < AGREE)
    swap = gross & (np.abs(z + med) < SWAP)
    y, blk, season = df["a_won"].to_numpy(float), df["block"].to_numpy(), df["season"].to_numpy()
    raw = df[f"raw_{s}"].to_numpy(bool) if f"raw_{s}" in df else np.isfinite(p)

    def summary(mask) -> dict:
        m = mask & sel
        k = int(m.sum())
        if k == 0:
            return {"n": 0}
        a = np.abs(d[m])
        quoted = mask & raw
        return {"n": k, "median_abs": round(float(np.median(a)), 4), "share_over_0_5": round(float((a > 0.5).mean()), 4),
                "gross_per_1000": round(1000 * float(gross[m].mean()), 2), "gross": int(gross[m].sum()),
                "swapped": int(swap[m].sum()),
                "incoherent_per_1000": round(1000 * float((quoted & ~np.isfinite(p)).sum() / max(quoted.sum(), 1)), 2)}

    out = {"source": s, "name": name(s), "reference": reference_names(df, s), **summary(np.ones(len(df), bool)),
           "by_season": {str(y_): summary(season == y_) for y_ in sorted(np.unique(season[sel]))}}
    g = gross
    out["gross_outcome"] = outcome(p[g], med[g], y[g], blk[g]) if g.sum() >= 2 else None
    ng = swap
    out["swapped_outcome"] = outcome(p[ng], med[ng], y[ng], blk[ng]) if ng.sum() >= 2 else None
    out["all_outcome"] = outcome(p[sel], med[sel], y[sel], blk[sel])
    if f"after_{s}_min" in df:
        after = df[f"after_{s}_min"].to_numpy(float)
        out["stamped_after_listed_min"] = {"all_median": round(float(np.nanmedian(after[sel])), 1),
                                           "gross_median": round(float(np.nanmedian(after[gross])), 1) if gross.any()
                                           else None,
                                           "share_over_late_min": round(float((after[sel] > LATE_MIN).mean()), 4)}
    out["_flags"] = (gross, swap, med)
    return out


def pinnacle_pair(df: pd.DataFrame, ref_df: pd.DataFrame) -> dict:
    """tennis-data's Pinnacle close against OddsTrader's last Pinnacle line on the same matches, both as recorded;
    the other books' median from ref_df."""
    a, b = df["p_ps"].to_numpy(float), df["p_ot20"].to_numpy(float)
    both = np.isfinite(a) & np.isfinite(b)
    d = C.lg(a) - C.lg(b)
    same = both & (np.abs(df["ps_a"] - df["ot20_a"].round(2)) <= 0.011).to_numpy() & \
        (np.abs(df["ps_b"] - df["ot20_b"].round(2)) <= 0.011).to_numpy()
    med, n, _ = reference(ref_df, reference_names(ref_df, "ps"))
    y, blk, season = df["a_won"].to_numpy(float), df["block"].to_numpy(), df["season"].to_numpy()
    after = df["after_ot20_min"].to_numpy(float)

    def stats(mask) -> dict:
        m = mask & both
        k = int(m.sum())
        if k == 0:
            return {"n": 0}
        x = np.abs(d[m])
        return {"n": k, "same_price": round(float(same[m].mean()), 4), "median_abs": round(float(np.median(x)), 4),
                "p90_abs": round(float(np.quantile(x, 0.9)), 4), "share_over_0_25": round(float((x > 0.25).mean()), 4),
                "share_over_0_5": round(float((x > 0.5).mean()), 4), "over_1_per_1000": round(1000 * float((x > 1).mean()), 2),
                "ot20_after_listed_median_min": round(float(np.nanmedian(after[m])), 1),
                "ll_td_minus_ot": C.mean_ci(C.log_loss(a[m], y[m]) - C.log_loss(b[m], y[m]), blk[m])}

    out = {"all": stats(np.ones(len(df), bool)), "by_season": {str(s): stats(season == s) for s in
                                                                sorted(np.unique(season[both]))}}
    big = both & (np.abs(d) > GROSS) & (np.abs(a - b) > GROSS_PP) & (n >= MIN_REF)
    da, db = np.abs(C.lg(a) - med), np.abs(C.lg(b) - med)
    events = df["match_id"].str.split("|").str[1].to_numpy()
    out["gross"] = {
        "n": int(big.sum()),
        "events": pd.Series(events[big]).value_counts().head(8).to_dict(),
        "tennis_data_off": int((big & (da > 0.5) & (db <= 0.5)).sum()),
        "oddstrader_off": int((big & (db > 0.5) & (da <= 0.5)).sum()),
        "both_off": int((big & (da > 0.5) & (db > 0.5)).sum()),
        "ot20_after_listed_median_min": round(float(np.nanmedian(after[big])), 1) if big.any() else None,
        "ot20_stamped_late": int((big & (after > LATE_MIN)).sum()),
        "ll_td_minus_ot": C.mean_ci(C.log_loss(a[big], y[big]) - C.log_loss(b[big], y[big]), blk[big])
        if big.sum() >= 2 else None}
    return out


def pinnacle_by_month(df: pd.DataFrame) -> list[dict]:
    """tennis-data's Pinnacle close against OddsTrader's Pinnacle line (late lines dropped), month by month: the share
    of matches where they are the same price, and the median gap. Reads no result."""
    both = df["p_ps"].notna() & df["p_ot20"].notna()
    x = df[both].assign(month=pd.to_datetime(df.loc[both, "td_date"]).dt.to_period("M").astype(str))
    same = (np.abs(x["ps_a"] - x["ot20_a"].round(2)) <= 0.011) & (np.abs(x["ps_b"] - x["ot20_b"].round(2)) <= 0.011)
    gap = pd.Series(np.abs(C.lg(x["p_ps"]) - C.lg(x["p_ot20"])), index=x.index)
    g = pd.DataFrame({"month": x["month"], "same": same, "gap": gap}).groupby("month")
    return [{"month": m, "n": int(len(v)), "same_price": round(float(v["same"].mean()), 3),
             "median_gap": round(float(v["gap"].median()), 4)} for m, v in g]


def late_stamps(df: pd.DataFrame, s: str, ref_df: pd.DataFrame) -> dict:
    """The source's last lines by when they were stamped against OddsTrader's listed start: distance from the others'
    median and log loss against it (an in-play price would be much more right than the others)."""
    p = df[f"p_{s}"].to_numpy(float)
    med, n, _ = reference(ref_df, reference_names(ref_df, s))
    after = df[f"after_{s}_min"].to_numpy(float)
    sel = np.isfinite(p) & (n >= MIN_REF) & np.isfinite(after)
    cut = pd.cut(after, LATE_BINS, labels=LATE_LABELS)
    y, blk = df["a_won"].to_numpy(float), df["block"].to_numpy()
    out = {}
    for lab in LATE_LABELS:
        m = sel & (cut == lab)
        if m.sum() < 20:
            out[lab] = {"n": int(m.sum())}
            continue
        out[lab] = {"n": int(m.sum()), "median_abs": round(float(np.median(np.abs(C.lg(p[m]) - med[m]))), 4),
                    "ll_minus_others": C.mean_ci(C.log_loss(p[m], y[m]) - C.log_loss(C.ex(med[m]), y[m]), blk[m])}
    return out


def examples(df: pd.DataFrame, s: str, flags, k: int = 8) -> list[dict]:
    """The largest gross disagreements of a source, as chances (no raw OddsTrader prices)."""
    gross, swap, med = flags
    idx = np.flatnonzero(gross)
    if not len(idx):
        return []
    z = C.lg(df[f"p_{s}"].to_numpy(float))
    order = idx[np.argsort(-np.abs(z[idx] - med[idx]))][:k]
    rows = []
    for i in order:
        r = df.iloc[i]
        rows.append({"match_id": r["match_id"], "date": str(r["td_date"])[:10], "round": r["td_round"],
                     "chance_A_source": round(float(r[f"p_{s}"]), 3), "chance_A_others": round(float(C.ex(med[i])), 3),
                     "chance_A_avg": None if pd.isna(r["p_avg"]) else round(float(r["p_avg"]), 3),
                     "a_won": int(r["a_won"]), "swapped": bool(swap[i])})
    return rows


def fmt(ci: dict | None, digits: int = 2) -> str:
    if not ci or ci.get("est") is None:
        return "—"
    return f"{ci['est']:+.{digits}f} [{ci['lo']:+.{digits}f}, {ci['hi']:+.{digits}f}]"


def tables(res: dict) -> str:
    lines = ["# Odds sources: recording quality (generated by quality.py)", "",
             f"Gross: over {GROSS} in log-odds and over {GROSS_PP:.0%} in chance from the median of at least {MIN_REF} "
             f"other books that agree within {AGREE} (interquartile range). Swapped: gross, and within {SWAP} of the "
             "others' mirror image. "
             "mLL: the source's log loss minus the others' median's, + = the source was worse.", "",
             "## 1. Pinnacle recorded twice (tennis-data against OddsTrader)", "",
             "| Season | Matches | Same price | Median gap (log-odds) | Gap over 0.5 | Over 1.0 per 1,000 | "
             "tennis-data − OddsTrader, mLL |", "|---|---:|---:|---:|---:|---:|---|"]
    pp = res["pinnacle_pair"]
    for s, v in list(pp["by_season"].items()) + [("all", pp["all"])]:
        if v["n"]:
            lines.append(f"| {s} | {v['n']:,} | {v['same_price']:.1%} | {v['median_abs']:.3f} | {v['share_over_0_5']:.2%} | "
                         f"{v['over_1_per_1000']:.1f} | {fmt(v['ll_td_minus_ot'])} |")
    g = pp["gross"]
    lines += ["", f"Gaps over {GROSS} in log-odds and {GROSS_PP:.0%} in chance, with at least {MIN_REF} other books: "
              f"{g['n']} (events: {', '.join(f'{k} {v}' for k, v in g['events'].items())}). tennis-data's off the others "
              f"(over 0.5) and OddsTrader's not: {g['tennis_data_off']}; OddsTrader's off and tennis-data's not: "
              f"{g['oddstrader_off']}; both off: {g['both_off']}. OddsTrader's line stamped a median "
              f"{g['ot20_after_listed_median_min']} min after the listed start. tennis-data − OddsTrader on them: "
              f"{fmt(g['ll_td_minus_ot'])} mLL.", "",
             "### By month from October 2024 (OddsTrader's lines stamped over 30 min late dropped)", "",
             "| Month | Matches | Same price | Median gap |", "|---|---:|---:|---:|"]
    lines += [f"| {r['month']} | {r['n']:,} | {r['same_price']:.0%} | {r['median_gap']:.4f} |"
              for r in res["pinnacle_by_month"] if r["month"] >= "2024-10" and r["n"] >= 40]
    lines += ["", "## 2. Each source against the median of the other books", "",
             "| Source | Matches | Median gap | Gap over 0.5 | Gross per 1,000 | Gross | Swapped | Incoherent quotes per "
             "1,000 | Gross: source − others, mLL | Gross, favourites differ: source's won | Gross stamped, min after "
             f"listed start (median) | Gross per 1,000, lines over {LATE_MIN:.0f} min late dropped |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"]
    for s in res["order"]:
        v = res["sources"][s]
        go = v.get("gross_outcome") or {}
        won = go.get("source_favourite_won")
        won_text = "—" if won is None else f"{won:.0%} of {go['favourites_differ']}"
        stamp = (v.get("stamped_after_listed_min") or {}).get("gross_median")
        wl = (v.get("without_late") or {}).get("gross_per_1000")
        lines.append(f"| {v['name']} | {v['n']:,} | {v['median_abs']:.3f} | {v['share_over_0_5']:.2%} | "
                     f"{v['gross_per_1000']:.2f} | {v['gross']} | {v['swapped']} | {v['incoherent_per_1000']:.2f} | "
                     f"{fmt(go.get('ll_minus_others'), 0)} | {won_text} | {'—' if stamp is None else stamp} | "
                     f"{'—' if wl is None else f'{wl:.2f}'} |")
    lines += ["", "### By season: gross per 1,000 (matches)", ""]
    seasons = sorted({s for v in res["sources"].values() for s in v["by_season"]})
    key = [s for s in res["order"] if s in ("ps", "ot20", "ot8", "avg", "b365")]
    lines += ["| Season | " + " | ".join(name(s) for s in key) + " |", "|---|" + "---:|" * len(key)]
    for y in seasons:
        cells = []
        for s in key:
            v = res["sources"][s]["by_season"].get(y, {"n": 0})
            cells.append("—" if not v["n"] else f"{v['gross_per_1000']:.1f} ({v['n']:,})")
        lines.append(f"| {y} | " + " | ".join(cells) + " |")
    lines += ["", "## 3. OddsTrader's last lines by when they were stamped", ""]
    for s, v in res["late"].items():
        lines += [f"**{name(s)}**", "", "| Stamped | Lines | Median gap | Source − others, mLL |", "|---|---:|---:|---|"]
        for lab, x in v.items():
            lines.append(f"| {lab} | {x['n']:,} | {x.get('median_abs', float('nan')):.3f} | "
                         f"{fmt(x.get('ll_minus_others'))} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    df = pd.read_parquet(C.SOURCES)
    df = df[df["a_won"].notna()].reset_index(drop=True)
    clean = drop_late(df)                   # the referees: OddsTrader's lines stamped late removed
    tested = [s for s in ["ps", "ot20", "ot8", "avg", "b365", "bfe", "ex", "lb", "pm_m30"] if f"p_{s}" in df]
    tested += [s for s in closing_ot(df) if s not in tested]
    res = {"thresholds": {"gross": GROSS, "gross_pp": GROSS_PP, "agree": AGREE, "swap": SWAP, "min_reference": MIN_REF,
                          "late_min": LATE_MIN},
           "pinnacle_pair": pinnacle_pair(df, clean), "pinnacle_by_month": pinnacle_by_month(clean),
           "sources": {}, "examples": {}}
    for s in tested:
        r = disagreement(df, s, clean)
        flags = r.pop("_flags")
        if r.get("n", 0) == 0:
            continue
        if s.startswith("ot"):              # the same book with its late lines dropped
            k = disagreement(clean, s, clean)
            k.pop("_flags")
            r["without_late"] = {"n": k.get("n", 0), "gross_per_1000": k.get("gross_per_1000"),
                                 "gross_outcome": k.get("gross_outcome")}
        res["sources"][s] = r
        if s in ("ps", "ot20", "ot8", "avg", "b365"):
            res["examples"][s] = examples(df, s, flags)
    res["order"] = [s for s in tested if s in res["sources"]]
    res["late"] = {s: late_stamps(df, s, clean) for s in ("ot8", "ot20") if f"after_{s}_min" in df}
    C.write_json(C.OUT / "quality.json", res)
    (C.OUT / "quality_tables.md").write_text(tables(res), encoding="utf-8")
    C.log(f"quality.json, quality_tables.md: {len(res['sources'])} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
