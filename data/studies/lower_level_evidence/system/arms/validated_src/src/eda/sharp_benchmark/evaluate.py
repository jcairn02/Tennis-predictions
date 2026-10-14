"""Sharp benchmark for 2026, step 2: how sharp are Betfair and Polymarket next to Pinnacle, and does it drift?

Sharpness is the log loss of a venue's margin-free price for the player who won (devig.py), on completed
matches (walkovers and retirements out; retirements return as a check). A row whose winner Polymarket's
settlement contradicts is left out everywhere: in the one completed case (Rotterdam 2026, Bergs v Medjedovic)
Tennis My Life agrees with Polymarket, so tennis-data has the names the wrong way round. Each comparison
uses only the matches where every venue in it has a price:
  A. each venue in its own year (Pinnacle 2025, Betfair 2026, Polymarket 2026, and the other year each
     holds), with the market average and Bet365 on the same matches as yardsticks of how hard they were;
  B. venues on the same matches: Pinnacle with Betfair (17 Aug 2025 - 14 Jan 2026), Pinnacle with Polymarket
     (from 18 Sep 2025), Betfair with Polymarket (to 3 Aug 2026), and all three;
  C. the cross-year comparison as asked, raw and against a yardstick:
     (Betfair 2026 - average 2026) - (Pinnacle 2025 - average 2025), likewise Polymarket, and with Bet365;
  D. sensitivity: how the margin is removed (proportional, power, Shin), retirements included, Polymarket's
     price taken 60 or 10 minutes before the listed start or at it, men and women apart; and the moves in
     Polymarket's last half hour before the listed start;
  E. drift. (1) Over the calendar: each venue's log loss by month and quarter, its difference from the market
     average on the same matches, a linear trend in that difference, and how far apart the venues' prices
     are. (2) Before the match: Polymarket's log loss at each horizon from 48 hours to the close, on fixed sets
     of matches, beside Betfair's and Pinnacle's closing log loss; and on every settled Polymarket singles
     market by level of play. Betfair's own horizon curve needs its historical tick data, not on disk.

Polymarket's benchmark price is its price 30 minutes before the market's listed start, not the last price before
it. The listed start is not the actual start, and in the last half hour a few percent of markets move by tens of
points, mostly toward the eventual winner (late_moves): matches already under way. Those markets carry nearly
all of the last half hour's gain in log loss. A few others snap to exactly 0.50, an emptied book.

Intervals are 95% Poisson-bootstrap ranges over matches (2,000 draws). Comparisons on the same matches share
the bootstrap weights; comparisons between different samples use independent ones. Each comparison seeds its
own draws from what it compares, so a refresh that adds matches to one comparison leaves the others' ranges as
they were. Differences are in
milli-log-loss (thousandths of a nat); a negative "x_minus_y" means x is sharper.

Input:  data/studies/sharp_benchmark/matches.parquet, pm_markets.parquet (build.py)
Output: data/studies/sharp_benchmark/results.json

Usage:
    ./python.sh src/eda/sharp_benchmark/evaluate.py
"""
from __future__ import annotations

import json
import sys
import zlib
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.sharp_benchmark import build as BLD  # noqa: E402
from src.eda.sharp_benchmark import devig as D  # noqa: E402

DRAWS = 2000
SEED = 20261005
MILLI = 1000.0
MIN_ROWS = 30
NAMES = {"ps": "Pinnacle", "bfe": "Betfair Exchange", "pm": "Polymarket", "avg": "Market average", "b365": "Bet365"}
OWN_YEAR = [("pinnacle_2025", "ps", 2025), ("betfair_2026", "bfe", 2026), ("polymarket_2026", "pm", 2026),
            ("pinnacle_2026", "ps", 2026), ("betfair_2025", "bfe", 2025), ("polymarket_2025", "pm", 2025)]
SAME_MATCHES = [("avg", "ps", "bfe"), ("avg", "ps", "pm"), ("avg", "bfe", "pm"), ("avg", "ps", "bfe", "pm")]
LEVEL_GROUPS = {"Grand Slams": ["slam_atp", "slam_wta"], "1000s and Finals": ["t1000_atp", "t1000_wta", "finals"],
                "500s and 250s": ["t500_atp", "t500_wta", "t250_atp", "t250_wta"],
                "Qualifying": ["slam_qual", "tour_qual"], "Challenger and WTA 125": ["challenger", "wta125"],
                "ITF": ["itf_m", "itf_w", "itf_u"]}
H24 = (1440, 720, 360, 180, 60, 30, 10, 0)
H12 = (720, 360, 180, 60, 30, 10, 0)
PM_COL = "pw_pm_m30"     # Polymarket's benchmark price: 30 minutes before the listed start
LATE_THRESHOLDS = (0.05, 0.10, 0.20)


def label_ok(m: pd.DataFrame) -> pd.Series:
    """False where Polymarket settled the linked market for the other player."""
    return ~m.pm_settle_agree.eq(0.0)


def probabilities(m: pd.DataFrame, method: str = "proportional", pm_col: str = PM_COL) -> pd.DataFrame:
    """The winner's margin-free chance at each venue's close (Polymarket: pm_col); NaN where the venue has no
    coherent price."""
    out = pd.DataFrame(index=m.index)
    with np.errstate(invalid="ignore", divide="ignore"):
        for book, (w, l) in BLD.BOOKS.items():
            out[book] = np.where(m[f"ok_{book}"], D.devig(m[w].to_numpy(), m[l].to_numpy(), method), np.nan)
    out["pm"] = m[pm_col].to_numpy()
    return out


def local_rng(*key) -> np.random.Generator:
    """A bootstrap generator seeded by what is compared (venues, number of matches, dates), so a comparison keeps
    its intervals when a refresh adds data to other comparisons."""
    return np.random.default_rng([SEED] + [zlib.crc32(str(k).encode("utf-8")) for k in key])


def compare(m: pd.DataFrame, p: pd.DataFrame, mask: pd.Series, venues: list[str]) -> dict:
    """Each venue's log loss on the rows of `mask` where all of them have a price, and every paired
    difference x_minus_y (milli-log-loss) for x listed after y."""
    sel = mask & p[venues].notna().all(axis=1)
    out = {"n": int(sel.sum())}
    if out["n"] < MIN_ROWS:
        return out
    dates = m.loc[sel, "date"]
    out["dates"] = [str(dates.min().date()), str(dates.max().date())]
    ll = {v: D.log_loss(p.loc[sel, v].to_numpy()) for v in venues}
    w = D.weights(out["n"], DRAWS, local_rng("compare", *venues, out["n"], *out["dates"]))
    boot = {v: D.boot_means(w, ll[v]) for v in venues}
    out["log_loss"] = {v: D.interval(ll[v].mean(), boot[v]) for v in venues}
    out["brier"] = {v: float(D.brier(p.loc[sel, v]).mean()) for v in venues}
    out["diff_milli"] = {f"{b}_minus_{a}": D.interval(ll[b].mean() - ll[a].mean(), boot[b] - boot[a], MILLI)
                         for a, b in combinations(venues, 2)}
    return out


def unpaired(a: np.ndarray, b: np.ndarray) -> dict:
    """mean(b) - mean(a) for two different samples, independent bootstraps, in milli-log-loss."""
    rng = local_rng("unpaired", len(a), len(b), round(float(a.sum()), 9), round(float(b.sum()), 9))
    ba = D.boot_means(D.weights(len(a), DRAWS, rng), a)
    bb = D.boot_means(D.weights(len(b), DRAWS, rng), b)
    return {"n_a": int(len(a)), "n_b": int(len(b)), **D.interval(b.mean() - a.mean(), bb - ba, MILLI)}


def trend(t_years: np.ndarray, d: np.ndarray) -> dict:
    """Least-squares slope of a per-match difference on time, per year, in milli-log-loss, bootstrapped."""
    w = D.weights(len(d), DRAWS, local_rng("trend", len(d), round(float(d.sum()), 9))).astype(np.float64)
    sw = w.sum(axis=1)
    mt, md = w @ t_years / sw, w @ d / sw
    boot = (w @ (t_years * d) / sw - mt * md) / (w @ (t_years * t_years) / sw - mt * mt)
    est = np.cov(t_years, d, bias=True)[0, 1] / np.var(t_years)
    return D.interval(est, boot, MILLI)


def by_period(m: pd.DataFrame, p: pd.DataFrame, mask: pd.Series, venues: list[str], period: pd.Series) -> list[dict]:
    out = []
    for key in sorted(period[mask].dropna().unique()):
        res = compare(m, p, mask & period.eq(key), venues)
        if res["n"] >= MIN_ROWS:
            out.append({"period": key, **res})
    return out


def price_gap(p: pd.DataFrame, mask: pd.Series, a: str, b: str, period: pd.Series) -> list[dict]:
    """How far apart two venues' closing chances are on the same matches: mean absolute difference in
    percentage points, by period."""
    sel = mask & p[[a, b]].notna().all(axis=1)
    gap = (p.loc[sel, a] - p.loc[sel, b]).abs() * 100.0
    g = gap.groupby(period[sel])
    return [{"period": k, "n": int(len(v)), "mean_abs_points": float(v.mean()), "median_abs_points": float(v.median())}
            for k, v in g]


# --------------------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------------------
def own_year(m, p, completed) -> dict:
    out = {}
    for key, v, season in OWN_YEAR:
        base = completed & m.season.eq(season) & p[v].notna()
        res = compare(m, p, base, [v])
        if res["n"] < MIN_ROWS:
            out[key] = res
            continue
        res["with_yardsticks"] = compare(m, p, base, ["avg", "b365", v])
        res["by_tour"] = {t: compare(m, p, base & m.tour.eq(t), [v]) for t in ("atp", "wta")}
        out[key] = res
    return out


def same_matches(m, p, completed) -> dict:
    out = {}
    for venues in SAME_MATCHES:
        key = "_".join(venues[1:])
        res = compare(m, p, completed, list(venues))
        res["by_tour"] = {t: compare(m, p, completed & m.tour.eq(t), list(venues)) for t in ("atp", "wta")}
        res["by_season"] = {str(s): compare(m, p, completed & m.season.eq(s), list(venues)) for s in BLD.SEASONS}
        out[key] = res
    return out


def cross_year(m, p, completed) -> dict:
    """The owner's comparison: Betfair and Polymarket in 2026 against Pinnacle in 2025. Raw, then each
    venue's distance from a yardstick on its own matches, so that a harder or easier year cancels."""
    out = {}
    ll = {v: pd.Series(D.log_loss(p[v].to_numpy()), index=p.index) for v in p.columns}
    for venue in ("bfe", "pm"):
        a = completed & m.season.eq(2025) & p.ps.notna()
        b = completed & m.season.eq(2026) & p[venue].notna()
        res = {"raw": unpaired(ll["ps"][a].to_numpy(), ll[venue][b].to_numpy())}
        for yard in ("avg", "b365"):
            a_y, b_y = a & p[yard].notna(), b & p[yard].notna()
            res[f"against_{yard}"] = unpaired((ll["ps"] - ll[yard])[a_y].to_numpy(),
                                              (ll[venue] - ll[yard])[b_y].to_numpy())
        out[f"{venue}_2026_vs_ps_2025"] = res
    return out


def sensitivity(m, completed) -> dict:
    out = {"method": {}, "retirements_included": {}, "polymarket_price_time": {}}
    for method in D.METHODS:
        p = probabilities(m, method)
        out["method"][method] = {
            "pinnacle_2025": compare(m, p, completed & m.season.eq(2025), ["avg", "ps"]),
            "betfair_2026": compare(m, p, completed & m.season.eq(2026), ["avg", "bfe"]),
            "ps_bfe_same_matches": compare(m, p, completed, ["ps", "bfe"]),
            "bfe_pm_same_matches": compare(m, p, completed, ["bfe", "pm"])}
    p = probabilities(m)
    played = m.comment.isin(["Completed", "Retired"]) & label_ok(m)
    out["retirements_included"] = {"_".join(v[1:]): compare(m, p, played, list(v)) for v in SAME_MATCHES}
    out["retirements_included"]["pinnacle_2025"] = compare(m, p, played & m.season.eq(2025), ["avg", "ps"])
    out["retirements_included"]["betfair_2026"] = compare(m, p, played & m.season.eq(2026), ["avg", "bfe"])
    for h in (60, 10, 0):
        q = probabilities(m, pm_col=f"pw_pm_m{h}")
        out["polymarket_price_time"][f"{h}_min"] = {"bfe_pm": compare(m, q, completed, ["bfe", "pm"]),
                                                    "ps_pm": compare(m, q, completed, ["ps", "pm"])}
    return out


def late_moves(m: pd.DataFrame, p: pd.DataFrame, completed: pd.Series) -> dict:
    """How Polymarket's price moves in the half hour before the listed start, against the half hour before that,
    on the matches with Betfair's close: size of the moves, share toward the eventual winner, prices of exactly
    0.50 (an emptied book), and how much of the last half hour's gain in log loss the large moves carry."""
    cols = ["pw_pm_m60", "pw_pm_m30", "pw_pm_m0"]
    sel = completed & p.bfe.notna() & m[cols].notna().all(axis=1)
    x = m.loc[sel, cols]
    last, before = x.pw_pm_m0 - x.pw_pm_m30, x.pw_pm_m30 - x.pw_pm_m60   # toward the winner when positive
    ll0, ll30, llb = (D.log_loss(v.to_numpy()) for v in (x.pw_pm_m0, x.pw_pm_m30, p.loc[sel, "bfe"]))
    gain = ll30 - ll0
    q = [50, 90, 95, 99]
    out = {"n": int(sel.sum()),
           "abs_move_quantiles": {"last_30_min": dict(zip(map(str, q), np.percentile(last.abs(), q).round(4).tolist())),
                                  "60_to_30_min": dict(zip(map(str, q), np.percentile(before.abs(), q).round(4).tolist()))},
           "exactly_half_at_listed_start": int((x.pw_pm_m0.eq(0.5) & x.pw_pm_m30.ne(0.5)).sum()),
           "gain_last_30_min_milli": float(gain.mean() * MILLI), "by_threshold": []}
    for thr in LATE_THRESHOLDS:
        big = last.abs().to_numpy() > thr
        out["by_threshold"].append({
            "threshold": thr, "markets_last_30": int(big.sum()), "share_last_30": float(big.mean()),
            "toward_winner_last_30": float((last[big] > 0).mean()) if big.any() else None,
            "markets_60_to_30": int((before.abs() > thr).sum()),
            "toward_winner_60_to_30": float((before[before.abs() > thr] > 0).mean()) if (before.abs() > thr).any() else None,
            "share_of_last_30_gain": float(gain[big].sum() / gain.sum()) if gain.sum() else None,
            "pm_listed_start_minus_bfe_without_them_milli": float((ll0[~big].mean() - llb[~big].mean()) * MILLI),
            "pm_30_min_minus_bfe_without_them_milli": float((ll30[~big].mean() - llb[~big].mean()) * MILLI)})
    return out


def calendar_drift(m, p, completed) -> dict:
    month = m.date.dt.strftime("%Y-%m")
    quarter = m.date.dt.year.astype(str) + "-Q" + m.date.dt.quarter.astype(str)
    t0 = pd.Timestamp("2025-01-01")
    t_years = ((m.date - t0).dt.days / 365.25).to_numpy()
    out = {"monthly": {}, "quarterly": {}, "trend_vs_avg_per_year": {}, "price_gap_monthly": {}}
    for v in ("ps", "bfe", "pm"):
        out["monthly"][v] = by_period(m, p, completed, ["avg", v], month)
        out["quarterly"][v] = by_period(m, p, completed, ["avg", v], quarter)
        sel = completed & p[[v, "avg"]].notna().all(axis=1)
        d = D.log_loss(p.loc[sel, v].to_numpy()) - D.log_loss(p.loc[sel, "avg"].to_numpy())
        out["trend_vs_avg_per_year"][v] = {"n": int(sel.sum()), **trend(t_years[sel.to_numpy()], d)}
    out["monthly"]["bfe_pm"] = by_period(m, p, completed, ["bfe", "pm"], month)
    out["quarterly"]["bfe_pm"] = by_period(m, p, completed, ["bfe", "pm"], quarter)
    sel = completed & p[["bfe", "pm"]].notna().all(axis=1)
    d = D.log_loss(p.loc[sel, "pm"].to_numpy()) - D.log_loss(p.loc[sel, "bfe"].to_numpy())
    out["trend_pm_minus_bfe_per_year"] = {"n": int(sel.sum()), **trend(t_years[sel.to_numpy()], d)}
    for a, b in (("pm", "bfe"), ("ps", "bfe"), ("pm", "ps")):
        out["price_gap_monthly"][f"{a}_vs_{b}"] = price_gap(p, completed, a, b, month)
    return out


def horizon_curve(chances: pd.DataFrame, horizons, refs: pd.DataFrame, bench: str = "h30") -> dict:
    """Polymarket's log loss at each horizon on the rows priced at every horizon (and by every reference
    venue), with the difference from its benchmark price (30 minutes before the listed start) and from each
    reference's close, in milli-log-loss."""
    cols = [f"h{h}" for h in horizons]
    sel = chances[cols].notna().all(axis=1) & refs.notna().all(axis=1)
    out = {"n": int(sel.sum()), "horizons_min": list(horizons)}
    if out["n"] < MIN_ROWS:
        return out
    ll = {c: D.log_loss(chances.loc[sel, c].to_numpy()) for c in cols}
    ll.update({r: D.log_loss(refs.loc[sel, r].to_numpy()) for r in refs.columns})
    w = D.weights(out["n"], DRAWS, local_rng("horizon", out["n"], *horizons, *refs.columns))
    boot = {k: D.boot_means(w, v) for k, v in ll.items()}
    out["log_loss"] = {k: D.interval(v.mean(), boot[k]) for k, v in ll.items()}
    out["minus_benchmark_milli"] = {c: D.interval(ll[c].mean() - ll[bench].mean(), boot[c] - boot[bench], MILLI)
                                    for c in cols}
    out["minus_ref_close_milli"] = {r: {c: D.interval(ll[c].mean() - ll[r].mean(), boot[c] - boot[r], MILLI)
                                        for c in cols} for r in refs.columns}
    return out


def pre_match_drift(m, p, completed, pm) -> dict:
    out = {}
    chances = pd.DataFrame({f"h{h}": m[f"pw_pm_m{h}"] for h in BLD.HORIZONS}, index=m.index)
    linked = completed & m.condition_id.notna()
    for name, horizons in (("from_48h", BLD.HORIZONS), ("from_24h", H24), ("from_12h", H12)):
        out[f"linked_bfe_{name}"] = horizon_curve(chances[linked], horizons, p.loc[linked, ["bfe"]])
    out["linked_ps_from_24h"] = horizon_curve(chances[linked], H24, p.loc[linked, ["ps"]])
    out["linked_bfe_ps_from_24h"] = horizon_curve(chances[linked], H24, p.loc[linked, ["bfe", "ps"]])
    # every settled singles market, labelled by Polymarket's own settlement
    settled = pm[pm.status.eq("decisive")]
    won0 = settled.y0.eq(1.0).to_numpy()
    own = pd.DataFrame({f"h{h}": np.where(won0, settled[f"p0_m{h}"], 1.0 - settled[f"p0_m{h}"]) for h in BLD.HORIZONS},
                       index=settled.index)
    none = pd.DataFrame(index=settled.index)
    out["polymarket_by_level"] = {}
    for label, types in LEVEL_GROUPS.items():
        rows = settled.event_type.isin(types)
        out["polymarket_by_level"][label] = {
            "from_24h": horizon_curve(own[rows], H24, none[rows]),
            "from_12h": horizon_curve(own[rows], H12, none[rows])}
    return out


def polymarket_calendar(pm) -> dict:
    """Log loss of every settled singles market's benchmark price (30 minutes before the listed start) by month
    and level, Polymarket's settlement as the label. Months differ in their mix of matches, so this is a
    description, not a like-for-like trend."""
    settled = pm[pm.status.eq("decisive") & pm.p0_m30.notna()].copy()
    settled["pw"] = np.where(settled.y0.eq(1.0), settled.p0_m30, 1.0 - settled.p0_m30)
    settled["ll"] = D.log_loss(settled.pw.to_numpy())
    settled["month"] = settled.day.dt.strftime("%Y-%m")
    out = {}
    for label, types in LEVEL_GROUPS.items():
        rows = settled[settled.event_type.isin(types)]
        out[label] = [{"month": k, "n": int(len(g)), "log_loss": float(g.ll.mean()),
                       "favourite_price": float(np.maximum(g.pw, 1 - g.pw).mean())}
                      for k, g in rows.groupby("month") if len(g) >= MIN_ROWS]
    return out


def main() -> int:
    m = pd.read_parquet(BLD.OUT / "matches.parquet")
    pm = pd.read_parquet(BLD.OUT / "pm_markets.parquet")
    p = probabilities(m)
    completed = m.comment.eq("Completed") & label_ok(m)
    results = {
        "generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "rules": {"draws": DRAWS, "seed": SEED, "min_rows": MIN_ROWS, "primary_method": "proportional",
                  "polymarket_price": f"{PM_COL}: winner's price 30 minutes before the listed start",
                  "matches": "completed (tennis-data Comment = Completed)", "units": "log loss in nats; differences "
                  "in milli-log-loss; x_minus_y < 0 means x is sharper"},
        "own_year": own_year(m, p, completed),
        "same_matches": same_matches(m, p, completed),
        "cross_year": cross_year(m, p, completed),
        "sensitivity": sensitivity(m, completed),
        "late_moves": late_moves(m, p, completed),
        "calendar_drift": calendar_drift(m, p, completed),
        "pre_match_drift": pre_match_drift(m, p, completed, pm),
        "polymarket_calendar": polymarket_calendar(pm),
    }
    (BLD.OUT / "results.json").write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")

    fmt = lambda r: f"{r['est']:.4f} [{r['lo']:.4f}, {r['hi']:.4f}]"
    fmd = lambda r: f"{r['est']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]"
    print("Own year (completed matches):")
    for key, res in results["own_year"].items():
        if "log_loss" in res:
            v = next(iter(res["log_loss"]))
            y = res["with_yardsticks"]
            print(f"  {key:<16} n={res['n']:>5} {res['dates']}  LL {fmt(res['log_loss'][v])}  "
                  f"vs avg {fmd(y['diff_milli'][f'{v}_minus_avg'])}  vs b365 {fmd(y['diff_milli'][f'{v}_minus_b365'])}")
    print("Same matches:")
    for key, res in results["same_matches"].items():
        if "log_loss" in res:
            lls = "  ".join(f"{NAMES[v]} {res['log_loss'][v]['est']:.4f}" for v in res["log_loss"])
            diffs = "  ".join(f"{k} {fmd(d)}" for k, d in res["diff_milli"].items() if not k.endswith("_minus_avg"))
            print(f"  {key:<10} n={res['n']:>5} {res['dates']}  {lls}  |  {diffs}")
    print("Cross year:")
    for key, res in results["cross_year"].items():
        print(f"  {key}: raw {fmd(res['raw'])}  against avg {fmd(res['against_avg'])}  against b365 {fmd(res['against_b365'])}")
    print("Trends vs avg per year:", {k: fmd(v) for k, v in results["calendar_drift"]["trend_vs_avg_per_year"].items()})
    for key in ("linked_bfe_from_24h", "linked_bfe_from_48h"):
        cur = results["pre_match_drift"][key]
        if "log_loss" in cur:
            print(f"Polymarket by horizon ({key}, n={cur['n']}):",
                  {k: round(v["est"], 4) for k, v in cur["log_loss"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
