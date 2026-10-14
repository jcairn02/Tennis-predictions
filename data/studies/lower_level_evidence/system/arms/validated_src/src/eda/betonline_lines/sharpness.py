"""How sharp are BetOnline's tennis closing lines next to Pinnacle's, and how much margin does each charge?

Seasons 2024 and 2025 of the tennis-data.co.uk files (main tour), where both books have a close:
  * Pinnacle: tennis-data's PSW/PSL, "generally the most recent before play starts" (the provider's claim; the
    odds carry no time).
  * BetOnline: the last line OddsTrader recorded (src/ingest/oddstrader.py, betonline_matches.parquet). A close
    the adapter flags uncertain (stamped over 30 minutes after the listed start, or not a two-sided market) is
    left out, and added back as a check.
  * Bet365 and the market average (AvgW/AvgL) come along as yardsticks on the same matches.

Sharpness follows the sharp-benchmark study (src/eda/sharp_benchmark/): the log loss of the winner's chance with
the margin removed proportionally (the project's convention; power and Shin as checks), on completed matches
(retirements return as a check). A pair outside overround 1.00-1.20 is not a coherent quote. Each comparison uses
only matches where every book in it has a price; 95% ranges come from 2,000 Poisson-bootstrap draws shared within
a comparison (evaluate.compare). Differences are in milli-log-loss; a negative "bol_minus_ps" means BetOnline is
sharper. Lower log loss is better.

Linking: the sharp benchmark's linker (surname span + first initial of each player, same tour, OddsTrader's listed
start 3 days before to 2 days after tennis-data's match day; one row per match and one match per row). It also
says which OddsTrader side won.

Margin: each book's overround minus one, (1/o_w + 1/o_l) - 1, on the same matches: overall, by year and tour,
and by how strong the favourite is (Pinnacle's margin-free chance), with BetOnline's relative to Pinnacle's.

Writes, in data/studies/betonline_lines/:
    sharpness.json            aggregates only (this repository is public)
    sharpness_matches.parquet one row per tennis-data row with both books' prices (gitignored by *.parquet)

Usage:
    ./python.sh src/eda/betonline_lines/sharpness.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.sharp_benchmark import build as BLD  # noqa: E402
from src.eda.sharp_benchmark import devig as D  # noqa: E402
from src.eda.sharp_benchmark import evaluate as EV  # noqa: E402

BETONLINE = ROOT / "data" / "dump" / "odds" / "oddstrader" / "betonline_matches.parquet"
OUT = ROOT / "data" / "studies" / "betonline_lines"
SEASONS = (2024, 2025)
FAVOURITE_BINS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


# --------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------
def load_tennis_data(seasons=SEASONS) -> pd.DataFrame:
    """The sharp benchmark's loader and cleaning (BLD.load_td), for these seasons."""
    saved = BLD.SEASONS
    BLD.SEASONS = tuple(seasons)
    try:
        return BLD.load_td()
    finally:
        BLD.SEASONS = saved


def american_to_decimal(ap) -> np.ndarray:
    ap = np.asarray(ap, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ap > 0, 1.0 + ap / 100.0, 1.0 + 100.0 / np.abs(ap))


def betonline_markets(path: Path = BETONLINE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """BetOnline's played singles, and the same as the market frame BLD.link expects (eid as condition_id;
    name_a is OddsTrader's away side, so a_won says whether the away side won)."""
    bo = pd.read_parquet(path)
    bo = bo[bo["es"].isin(["complete", "retired"])].reset_index(drop=True)
    full = lambda first, last: (first.fillna("") + " " + last.fillna("")).str.strip()  # noqa: E731
    frame = pd.DataFrame({
        "condition_id": bo["eid"], "tour": bo["tour"].str.lower(),
        "day": pd.to_datetime(bo["dt_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize(),
        "name_a": full(bo["away_first"], bo["away_last"]), "name_b": full(bo["home_first"], bo["home_last"]),
        "has_close": bo["mw_close_home"].notna() & bo["mw_close_away"].notna(), "volume": 0.0})
    return bo, frame


def attach_betonline(td: pd.DataFrame, bo: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """BetOnline's opening and closing decimal odds for each tennis-data row's winner and loser, with flags."""
    lk = links.rename(columns={"condition_id": "eid", "gap": "bol_link_gap"}).merge(bo, on="eid", how="left")
    away_won = lk["a_won"].astype(bool).to_numpy()
    for kind in ("open", "close"):
        home, away = lk[f"mw_{kind}_home"].to_numpy(dtype=float), lk[f"mw_{kind}_away"].to_numpy(dtype=float)
        lk[f"BOL{kind[0].upper()}W"] = american_to_decimal(np.where(away_won, away, home))
        lk[f"BOL{kind[0].upper()}L"] = american_to_decimal(np.where(away_won, home, away))
    keep = ["td_id", "eid", "bol_link_gap", "a_won", "mw_close_uncertain", "mw_open_uncertain",
            "mw_close_after_listed_min", "BOLOW", "BOLOL", "BOLCW", "BOLCL"]
    m = td.merge(lk[keep], on="td_id", how="left")
    for tag, (w, l), flag in (("bol", ("BOLCW", "BOLCL"), "mw_close_uncertain"),
                              ("bolo", ("BOLOW", "BOLOL"), "mw_open_uncertain")):
        s = 1.0 / m[w] + 1.0 / m[l]
        m[f"overround_{tag}"] = s
        coherent = m[w].notna() & m[l].notna() & s.between(*BLD.OVERROUND_OK)
        m[f"ok_{tag}_any"] = coherent
        m[f"ok_{tag}"] = coherent & ~m[flag].fillna(False).astype(bool)
    return m


PAIRS = {"ps": ("PSW", "PSL"), "b365": ("B365W", "B365L"), "avg": ("AvgW", "AvgL"), "bol": ("BOLCW", "BOLCL"),
         "bolo": ("BOLOW", "BOLOL")}


def probabilities(m: pd.DataFrame, method: str = "proportional", flagged: bool = False) -> pd.DataFrame:
    """The winner's margin-free chance at each book; NaN where the book has no coherent price. With flagged,
    BetOnline's uncertain closes count too."""
    out = pd.DataFrame(index=m.index)
    with np.errstate(invalid="ignore", divide="ignore"):
        for book, (w, l) in PAIRS.items():
            ok = m[f"ok_{book}_any"] if flagged and book in ("bol", "bolo") else m[f"ok_{book}"]
            out[book] = np.where(ok, D.devig(m[w].to_numpy(), m[l].to_numpy(), method), np.nan)
    return out


# --------------------------------------------------------------------------------------
# margins
# --------------------------------------------------------------------------------------
def margins(m: pd.DataFrame, mask: pd.Series, books=("ps", "bol", "b365", "avg")) -> dict:
    """Margin (overround - 1) of each book on the rows of mask where all of them are coherent; BetOnline's
    relative to Pinnacle's with paired 95% ranges."""
    sel = mask & pd.concat([m[f"ok_{b}"] for b in books], axis=1).all(axis=1)
    out = {"n": int(sel.sum())}
    if out["n"] < EV.MIN_ROWS:
        return out
    margin = {b: (m.loc[sel, f"overround_{b}"].to_numpy() - 1.0) for b in books}
    out["mean_pct"] = {b: round(100 * float(v.mean()), 3) for b, v in margin.items()}
    out["median_pct"] = {b: round(100 * float(np.median(v)), 3) for b, v in margin.items()}
    if "bol" in books and "ps" in books:
        w = D.weights(out["n"], EV.DRAWS, EV.local_rng("margin", *books, out["n"]))
        mb, mp = D.boot_means(w, margin["bol"]), D.boot_means(w, margin["ps"])
        out["bol_minus_ps_pp"] = D.interval(margin["bol"].mean() - margin["ps"].mean(), mb - mp, 100.0)
        out["bol_over_ps_ratio"] = D.interval(margin["bol"].mean() / margin["ps"].mean(), mb / mp)
        out["bol_wider_share"] = round(float((margin["bol"] > margin["ps"]).mean()), 4)
    return out


def chance_gap(p: pd.DataFrame, mask: pd.Series, a: str = "ps", b: str = "bol") -> dict:
    """How far apart two books' margin-free chances are, in percentage points."""
    sel = mask & p[[a, b]].notna().all(axis=1)
    gap = 100 * (p.loc[sel, b] - p.loc[sel, a]).abs()
    return {"n": int(sel.sum()), "mean_pp": round(float(gap.mean()), 3), "median_pp": round(float(gap.median()), 3),
            "p90_pp": round(float(gap.quantile(0.9)), 3), "share_over_2pp": round(float((gap > 2).mean()), 4),
            "share_over_5pp": round(float((gap > 5).mean()), 4)}


SHOP_PAIRS = {"ps": ("PSW", "PSL"), "bol": ("BOLCW", "BOLCL"), "b365": ("B365W", "B365L")}
SAME_PRICE = 0.005  # decimal odds closer than this count as the same price (tennis-data quotes two decimals)


def line_shopping(m: pd.DataFrame, mask: pd.Series, books=("ps", "bol")) -> dict:
    """The market made of the best price on each side across `books`, each side free to come from another book.

    Its margin, 1/best_w + 1/best_l - 1, can never exceed the cheaper book's own: it equals it when one book has
    the best price on both sides, and is strictly lower only when the books split the two sides. Below zero is an
    arbitrage on paper. Also: for each side (Pinnacle's favourite and underdog), which book has the better price,
    and how much the best price beats Pinnacle's, in percent of the odds."""
    sel = mask & pd.concat([m[f"ok_{b}"] for b in books], axis=1).all(axis=1)
    out = {"n": int(sel.sum()), "books": list(books)}
    if out["n"] < EV.MIN_ROWS:
        return out
    x = m.loc[sel]
    w = np.column_stack([x[SHOP_PAIRS[b][0]].to_numpy(dtype=float) for b in books])
    lo = np.column_stack([x[SHOP_PAIRS[b][1]].to_numpy(dtype=float) for b in books])
    best_w, best_l = w.max(axis=1), lo.max(axis=1)
    best = 1.0 / best_w + 1.0 / best_l - 1.0
    own = {b: 1.0 / w[:, k] + 1.0 / lo[:, k] - 1.0 for k, b in enumerate(books)}
    cheapest = np.column_stack(list(own.values())).min(axis=1)
    one_book = np.zeros(len(x), dtype=bool)
    for k in range(len(books)):
        one_book |= (w[:, k] >= best_w - SAME_PRICE) & (lo[:, k] >= best_l - SAME_PRICE)
    split = ~one_book
    out["mean_pct"] = {**{b: round(100 * float(v.mean()), 3) for b, v in own.items()}, "best_of": round(100 * float(best.mean()), 3)}
    out["median_pct"] = {**{b: round(100 * float(np.median(v)), 3) for b, v in own.items()},
                         "best_of": round(100 * float(np.median(best)), 3)}
    wts = D.weights(out["n"], EV.DRAWS, EV.local_rng("shop", *books, out["n"]))
    out["best_of_minus_ps_pp"] = D.interval(best.mean() - own["ps"].mean(),
                                            D.boot_means(wts, best) - D.boot_means(wts, own["ps"]), 100.0)
    out["best_of_minus_cheapest_book_pp"] = round(100 * float((best - cheapest).mean()), 3)
    out["split_share"] = round(float(split.mean()), 4)
    out["best_of_when_split_mean_pct"] = round(100 * float(best[split].mean()), 3) if split.any() else None
    out["below_zero_share"] = round(float((best < 0).mean()), 4)
    # sides: Pinnacle's favourite and underdog (higher and lower implied chance at Pinnacle)
    fav_is_w = (1.0 / x["PSW"]).to_numpy() >= (1.0 / x["PSL"]).to_numpy()
    for side, pick in (("favourite", fav_is_w), ("underdog", ~fav_is_w)):
        odds = np.where(pick[:, None], w, lo)  # this side's odds at each book
        ps, top = odds[:, list(books).index("ps")], odds.max(axis=1)
        entry = {"best_beats_ps_share": round(float((top > ps + SAME_PRICE).mean()), 4),
                 "mean_gain_vs_ps_pct": round(100 * float((top / ps - 1.0).mean()), 3)}
        if "bol" in books:
            bol = odds[:, list(books).index("bol")]
            entry["betonline_better_share"] = round(float((bol > ps + SAME_PRICE).mean()), 4)
            entry["pinnacle_better_share"] = round(float((ps > bol + SAME_PRICE).mean()), 4)
        out[side] = entry
    return out


def favourite_strength(m: pd.DataFrame, p: pd.DataFrame) -> pd.Series:
    """Pinnacle's margin-free chance of the favourite, binned."""
    fav = np.maximum(p["ps"], 1.0 - p["ps"])
    return pd.cut(fav, FAVOURITE_BINS, right=False, include_lowest=True).astype(str).where(fav.notna())


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def summary_line(res: dict, x: str = "bol", y: str = "ps") -> str:
    if "diff_milli" not in res:
        return f"n={res['n']}"
    d = res["diff_milli"].get(f"{x}_minus_{y}") or {k: -v for k, v in res["diff_milli"][f"{y}_minus_{x}"].items()}
    ll = res["log_loss"]
    return (f"n={res['n']:,} {x}={ll[x]['est']:.4f} {y}={ll[y]['est']:.4f} "
            f"{x}-{y}={d['est']:+.1f} ({d['lo']:+.1f} to {d['hi']:+.1f})")


def main() -> int:
    td = load_tennis_data()
    bo, frame = betonline_markets()
    links = BLD.link(td, frame)
    m = attach_betonline(td, bo, links)
    m["season"] = m["season"].astype(int)
    completed = m["comment"].eq("Completed")
    played = m["comment"].isin(["Completed", "Retired"])
    in_seasons = m["season"].isin(SEASONS)
    p = probabilities(m)

    res: dict = {"generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                 "rules": {"seasons": list(SEASONS), "primary_method": "proportional", "draws": EV.DRAWS,
                           "overround_ok": list(BLD.OVERROUND_OK), "link_window_days": list(BLD.WINDOW),
                           "betonline_close": "last OddsTrader line; uncertain closes out (in as a check)"}}
    rows = m[in_seasons]
    res["linking"] = {
        "tennis_data_rows": int(len(rows)), "linked": int(rows["eid"].notna().sum()),
        "by_season_tour": json.loads(rows.assign(linked=rows["eid"].notna()).groupby(["season", "tour"])
                                     .agg(rows=("linked", "size"), linked=("linked", "sum")).reset_index()
                                     .to_json(orient="records")),
        "coherent_closes": {b: int((rows[f"ok_{b}"]).sum()) for b in ("ps", "bol", "b365", "avg")},
        "betonline_close_flagged_uncertain": int((rows["ok_bol_any"] & ~rows["ok_bol"]).sum()),
        "gap_days": {int(k): int(v) for k, v in rows["bol_link_gap"].dropna().astype(int).value_counts().sort_index().items()}}

    base = completed & in_seasons
    res["closing_sharpness"] = {"all": EV.compare(m, p, base, ["ps", "bol"])}
    for season in SEASONS:
        res["closing_sharpness"][str(season)] = EV.compare(m, p, base & m["season"].eq(season), ["ps", "bol"])
        for tour in ("atp", "wta"):
            res["closing_sharpness"][f"{season} {tour}"] = EV.compare(
                m, p, base & m["season"].eq(season) & m["tour"].eq(tour), ["ps", "bol"])
    for tour in ("atp", "wta"):
        res["closing_sharpness"][tour] = EV.compare(m, p, base & m["tour"].eq(tour), ["ps", "bol"])
    res["with_yardsticks"] = {"all": EV.compare(m, p, base, ["avg", "b365", "ps", "bol"])}
    for season in SEASONS:
        res["with_yardsticks"][str(season)] = EV.compare(m, p, base & m["season"].eq(season), ["avg", "b365", "ps", "bol"])

    checks = {}
    for method in ("power", "shin"):
        pm_ = probabilities(m, method)
        checks[method] = {str(s): EV.compare(m, pm_, base & m["season"].eq(s), ["ps", "bol"]) for s in SEASONS}
        checks[method]["all"] = EV.compare(m, pm_, base, ["ps", "bol"])
    checks["retirements_included"] = EV.compare(m, p, played & in_seasons, ["ps", "bol"])
    checks["uncertain_closes_included"] = EV.compare(m, probabilities(m, flagged=True), base, ["ps", "bol"])
    checks["betonline_opening"] = EV.compare(m, p, base, ["ps", "bol", "bolo"])
    res["checks"] = checks
    res["line_shopping"] = {"ps_bol": line_shopping(m, base),
                            **{f"ps_bol {s}": line_shopping(m, base & m["season"].eq(s)) for s in SEASONS},
                            "ps_bol_b365": line_shopping(m, base, ("ps", "bol", "b365"))}
    res["chance_gap_bol_vs_ps"] = {"all": chance_gap(p, base),
                                   **{str(s): chance_gap(p, base & m["season"].eq(s)) for s in SEASONS}}

    fav = favourite_strength(m, p)
    res["margins"] = {"all": margins(m, base),
                      **{str(s): margins(m, base & m["season"].eq(s)) for s in SEASONS},
                      **{t: margins(m, base & m["tour"].eq(t)) for t in ("atp", "wta")},
                      "by_favourite_chance": {b: margins(m, base & fav.eq(b)) for b in sorted(fav.dropna().unique())},
                      "betonline_opening_vs_close": margins(m, base, books=("bolo", "bol"))}

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["td_id", "tour", "season", "date", "tournament", "round", "winner", "loser", "comment", "eid",
            "bol_link_gap", "a_won", "PSW", "PSL", "B365W", "B365L", "AvgW", "AvgL", "BOLOW", "BOLOL", "BOLCW", "BOLCL",
            "ok_ps", "ok_bol", "ok_bol_any", "ok_bolo", "mw_close_uncertain", "mw_close_after_listed_min"]
    m.loc[in_seasons, cols].to_parquet(OUT / "sharpness_matches.parquet", index=False)
    (OUT / "sharpness.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    print("linking:", {k: res["linking"][k] for k in ("tennis_data_rows", "linked", "coherent_closes",
                                                      "betonline_close_flagged_uncertain")})
    for key, r in res["closing_sharpness"].items():
        print(f"closing {key:9s}", summary_line(r))
    for key in ("power", "shin"):
        print(f"{key:9s} all     ", summary_line(checks[key]["all"]))
    print("retirements in   ", summary_line(checks["retirements_included"]))
    print("uncertain in     ", summary_line(checks["uncertain_closes_included"]))
    print("opening vs close ", summary_line(checks["betonline_opening"], "bolo", "bol"))
    for key, r in res["margins"].items():
        if key == "by_favourite_chance":
            for b, rr in r.items():
                print(f"margin fav {b}", rr.get("n"), rr.get("mean_pct"), rr.get("bol_over_ps_ratio"))
        else:
            print(f"margin {key}", r.get("n"), r.get("mean_pct"), r.get("bol_minus_ps_pp"), r.get("bol_over_ps_ratio"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
