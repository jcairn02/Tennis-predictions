"""Sharp versus casual money per event type, with market-clustered bootstrap intervals.

Money = stake on contested fills (trade price 5-95c): the most a party can lose on the bet (shares x price of
the outcome it backs), counting both sides of every fill. Each dollar carries its wallet's tier for that market,
assigned from the wallet's other matches only (classify.py).

Event types come from build_positions.py. A type is reported on its own when it has at least MIN_MARKETS
decisive markets and the 95% intervals of its sharp, professional and casual shares are no wider than
+/- MAX_HALF_WIDTH; otherwise it is pooled with the other failing types of its parent group, and a pool that
still fails joins its smallest passing sibling (or the whole parent group).

Intervals: Poisson bootstrap over markets (every market's fills move together), B draws, percentile 95%.

Inputs:  data/studies/polymarket_sharp_money/{scored_positions,markets}.parquet
Output:  data/studies/polymarket_sharp_money/composition.json

Usage:
    ./python.sh src/eda/polymarket_sharp_money/composition.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_positions import EVENT_TYPES  # noqa: E402
from classify import TIER_LABELS, TIERS  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
B = 1000
SEED = 20260925
MIN_MARKETS = 150
MAX_HALF_WIDTH = 0.05
HEADLINE = {"sharp": ["winning"], "professional": ["heavy"], "casual": ["new", "occasional"]}
TYPE_ORDER = ["slam_atp", "slam_wta", "finals", "t1000_atp", "t1000_wta", "t500_atp", "t500_wta", "t250_atp",
              "t250_wta", "slam_qual", "tour_qual", "challenger", "wta125", "itf_m", "itf_w", "itf_u", "doubles",
              "juniors", "team_exhib"]
PARENT_LABELS = {"slam": "Grand Slam main draws", "tour_top": "Masters/WTA 1000 and Finals",
                 "tour_mid": "500 and 250 events", "qualifying": "Qualifying (Slam and tour)",
                 "lower": "Challenger, WTA 125 and ITF", "other": "Doubles, juniors, team events"}
SUMS = ["stake", "net", "gross", "fee", "rebate", "stake_taker", "net_taker", "stake_pre", "stake_taker_pre",
        "net_taker_pre", "mo5m", "mo60m", "clv", "mo5m_taker", "mo60m_taker", "clv_taker", "stake_all", "fee_taker"]


class Cube:
    """Market x tier sums of every quantity in SUMS for one set of markets, with shared bootstrap weights."""

    def __init__(self, rows: pd.DataFrame, rng: np.random.Generator):
        codes, self.markets = pd.factorize(rows.condition_id)
        tiers = pd.Categorical(rows.tier, categories=TIERS).codes
        m, t = len(self.markets), len(TIERS)
        self.sums = {}
        for name in SUMS:
            flat = np.bincount(codes * t + tiers, weights=rows[name].to_numpy(), minlength=m * t)
            self.sums[name] = flat.reshape(m, t)
        self.w = rng.poisson(1.0, size=(B, m)).astype(float)
        self.wallets = rows.groupby("tier").proxy_wallet.nunique().reindex(TIERS).fillna(0).astype(int)

    def total(self, name: str, tiers=None, boot: bool = False):
        cube = self.sums[name] if tiers is None else self.sums[name][:, [TIERS.index(x) for x in tiers]]
        per_market = cube.sum(axis=1)
        return self.w @ per_market if boot else per_market.sum()

    def ratio(self, num: str, den: str, tiers=None, den_tiers="same") -> dict:
        dt = tiers if den_tiers == "same" else den_tiers
        point = self.total(num, tiers) / self.total(den, dt) if self.total(den, dt) else float("nan")
        boot = self.total(num, tiers, boot=True) / self.total(den, dt, boot=True)
        lo, hi = np.nanpercentile(boot, [2.5, 97.5]) if np.isfinite(boot).any() else (np.nan, np.nan)
        return {"est": float(point), "lo": float(lo), "hi": float(hi)}


def group_stats(rows: pd.DataFrame, rng: np.random.Generator) -> dict:
    cube = Cube(rows, rng)
    out = {"markets": int(len(cube.markets)), "wallets": int(rows.proxy_wallet.nunique()),
           "stake": float(cube.total("stake")), "stake_all_fills": float(cube.total("stake_all")),
           "median_stake_per_market": float(np.median(cube.sums["stake"].sum(axis=1))),
           "fees_per_100": 100 * cube.total("fee") / cube.total("stake"),
           "pre_start_share": cube.ratio("stake_pre", "stake"), "taker_share": cube.ratio("stake_taker", "stake")}
    out["share"] = {t: cube.ratio("stake", "stake", [t], None) for t in TIERS}
    out["headline"] = {k: cube.ratio("stake", "stake", v, None) for k, v in HEADLINE.items()}
    out["taker_money_share"] = {k: cube.ratio("stake_taker", "stake_taker", v, None) for k, v in HEADLINE.items()}
    out["pre_start_money_share"] = {k: cube.ratio("stake_pre", "stake_pre", v, None) for k, v in HEADLINE.items()}
    out["tier"] = {}
    for t in TIERS:
        stake = cube.total("stake", [t])
        out["tier"][t] = {"stake": float(stake), "wallets": int(cube.wallets[t]),
                          "roi_net": cube.ratio("net", "stake", [t]) if stake > 0 else None,
                          "roi_gross": cube.ratio("gross", "stake", [t]) if stake > 0 else None,
                          "fee_per_stake": float(cube.total("fee", [t]) / stake) if stake > 0 else None,
                          "mo5m": cube.ratio("mo5m", "stake", [t]) if stake > 0 else None,
                          "mo60m": cube.ratio("mo60m", "stake", [t]) if stake > 0 else None,
                          "clv": (cube.ratio("clv", "stake_pre", [t]) if cube.total("stake_pre", [t]) > 0 else None),
                          "taker_share": float(cube.total("stake_taker", [t]) / stake) if stake > 0 else None}
    for k, v in HEADLINE.items():
        out[f"roi_net_{k}"] = cube.ratio("net", "stake", v)
        out[f"mo60m_{k}"] = cube.ratio("mo60m", "stake", v)
    # dollars won or lost by casual money per $100 of all money traded in the event type
    out["casual_net_per_100"] = {k: 100 * v for k, v in cube.ratio("net", "stake", HEADLINE["casual"], None).items()}
    # who funds whom: each tier's net result per $100 of all money (sums to minus fees net of rebates)
    out["net_per_100"] = {t: {k: 100 * v for k, v in cube.ratio("net", "stake", [t], None).items()} for t in TIERS}
    out["fees_net_of_rebates_per_100"] = 100 * (cube.total("fee") - cube.total("rebate")) / cube.total("stake")
    top = rows.groupby("proxy_wallet").stake.sum().sort_values(ascending=False)
    out["top10_wallet_share"] = float(top.head(10).sum() / top.sum())
    return out


def passes(stats: dict) -> bool:
    if stats["markets"] < MIN_MARKETS:
        return False
    return all((v["hi"] - v["lo"]) / 2 <= MAX_HALF_WIDTH for v in stats["headline"].values())


def merge_groups(rows: pd.DataFrame, rng_seed: int) -> tuple[list[dict], list[dict]]:
    """Apply the sample-size rule; returns (reported groups with stats, merge log)."""
    fine = {}
    for t in TYPE_ORDER:
        sub = rows[rows.event_type == t]
        if len(sub):
            fine[t] = group_stats(sub, np.random.default_rng(rng_seed))
    log, groups = [], []
    parents = {}
    for t in fine:
        parents.setdefault(EVENT_TYPES[t][1], []).append(t)
    for parent, members in parents.items():
        ok = [t for t in members if passes(fine[t])]
        bad = [t for t in members if t not in ok]
        units = [[t] for t in ok]
        if bad:
            pool = group_stats(rows[rows.event_type.isin(bad)], np.random.default_rng(rng_seed))
            if len(bad) > 1 and passes(pool):
                units.append(bad)
                log.append({"types": bad, "action": "pooled", "reason": "each failed the sample rule; the pool passes"})
            elif ok:
                target = min(ok, key=lambda t: fine[t]["markets"])
                units = [u for u in units if u != [target]] + [[target] + bad]
                log.append({"types": bad, "action": f"merged into {target}",
                            "reason": "failed the sample rule alone and pooled"})
            else:
                units = [members]
                log.append({"types": members, "action": "whole parent group", "reason": "no member passes alone"})
        for unit in units:
            stats = fine[unit[0]] if len(unit) == 1 else group_stats(rows[rows.event_type.isin(unit)],
                                                                     np.random.default_rng(rng_seed))
            label = " + ".join(EVENT_TYPES[t][0] for t in unit)
            groups.append({"key": "+".join(unit), "types": unit, "label": label, "parent": parent,
                           "parent_label": PARENT_LABELS[parent], "passes_rule": passes(stats), **stats})
    order = {t: i for i, t in enumerate(TYPE_ORDER)}
    groups.sort(key=lambda g: min(order[t] for t in g["types"]))
    for t, s in fine.items():
        s["passes_rule"] = passes(s)
    return groups, log, fine


def reliability(rows: pd.DataFrame) -> dict:
    """How far a wallet's record in one half of the matches (folds 0-1) predicts the other half (folds 2-4):
    precision-weighted correlation of net returns, and the other-half results of wallets 2+ standard errors
    above or below zero in the first half."""
    def half(sel):
        return rows[sel].groupby("proxy_wallet").agg(n=("condition_id", "size"), stake=("stake", "sum"),
                                                     net=("net", "sum"), var=("var_qv", "sum"))
    a, b = half(rows.fold <= 1), half(rows.fold >= 2)
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    j = j[(j.var_a > 0) & (j.var_b > 0)]
    j["e_a"], j["e_b"] = j.net_a / j.stake_a, j.net_b / j.stake_b
    j["z_a"], j["z_b"] = j.net_a / np.sqrt(j.var_a), j.net_b / np.sqrt(j.var_b)
    out = []
    for lo in (5, 20, 50, 100):
        k = j[(j.n_a >= lo) & (j.n_b >= lo)]
        if len(k) < 30:
            continue
        w = 1.0 / (k.var_a / k.stake_a ** 2 + k.var_b / k.stake_b ** 2)
        c = np.cov(k.e_a, k.e_b, aweights=w)
        row = {"min_markets_each_half": lo, "wallets": int(len(k)), "stake_share": float(k.stake_b.sum() / b.stake.sum()),
               "corr_return": float(c[0, 1] / np.sqrt(c[0, 0] * c[1, 1])),
               "corr_z": float(np.corrcoef(k.z_a, k.z_b)[0, 1]), "var_z_first_half": float(k.z_a.var())}
        for name, sel in (("up2", k.z_a >= 2), ("down2", k.z_a <= -2), ("middle", k.z_a.abs() < 2)):
            row[name] = {"wallets": int(sel.sum()),
                         "second_half_return": float(k[sel].net_b.sum() / k[sel].stake_b.sum()) if sel.any() else None,
                         "second_half_mean_z": float(k[sel].z_b.mean()) if sel.any() else None}
        out.append(row)
    return {"halves": "folds 0-1 vs folds 2-4", "rows": out}


def monthly_mix(rows: pd.DataFrame, markets: pd.DataFrame) -> list[dict]:
    m = rows.merge(markets[["condition_id", "month"]], on="condition_id")
    g = m.groupby(["month", "tier"]).stake.sum().unstack(fill_value=0.0)
    g = g.div(g.sum(axis=1), axis=0)
    return [{"month": idx, **{t: float(g.loc[idx].get(t, 0.0)) for t in TIERS}} for idx in g.index]


def main() -> int:
    rows = pd.read_parquet(STUDY / "scored_positions.parquet")
    markets = pd.read_parquet(STUDY / "markets.parquet")
    markets["month"] = pd.to_datetime(markets.sport_date, utc=True, errors="coerce").dt.strftime("%Y-%m")
    rows = rows.merge(markets[["condition_id", "event_type"]], on="condition_id", how="inner")
    for col in SUMS:
        rows[col] = rows[col].fillna(0.0)

    overall = group_stats(rows, np.random.default_rng(SEED))
    groups, merges, fine = merge_groups(rows, SEED)
    lower_start = markets.loc[markets.event_type.isin(["itf_m", "itf_w", "itf_u"]), "sport_date"].min()
    common = rows[rows.condition_id.isin(markets.loc[markets.sport_date >= lower_start, "condition_id"])]
    common_groups = []
    for g in groups:
        sub = common[common.event_type.isin(g["types"])]
        if sub.condition_id.nunique() >= 30:
            s = group_stats(sub, np.random.default_rng(SEED))
            common_groups.append({"key": g["key"], "label": g["label"], "markets": s["markets"],
                                  "headline": s["headline"], "roi_net_casual": s["roi_net_casual"]})
    used = markets[markets.condition_id.isin(rows.condition_id)]
    dates = pd.to_datetime(used.sport_date, utc=True, errors="coerce")
    itf = used[used.event_type.isin(["itf_m", "itf_w", "itf_u"])]
    known = int(itf.event_type.isin(["itf_m", "itf_w"]).sum())
    out = {
        "generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "itf_gender_note": f"found for {known:,} of {len(itf):,} ITF markets, {known / max(len(itf), 1):.0%}",
        "window_start": dates.min().strftime("%d %b %Y").lstrip("0"),
        "window_end": dates.max().strftime("%d %b %Y").lstrip("0"),
        "rules": {"min_markets": MIN_MARKETS, "max_half_width": MAX_HALF_WIDTH, "bootstrap_draws": B, "seed": SEED,
                  "headline_tiers": HEADLINE},
        "tiers": [{"key": t, "label": TIER_LABELS[t]} for t in TIERS],
        "overall": overall, "groups": groups, "merges": merges, "fine_types": fine,
        "common_window": {"start": str(lower_start)[:10], "groups": common_groups},
        "monthly_mix": monthly_mix(rows, markets),
        "reliability": reliability(rows),
    }
    (STUDY / "composition.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for g in groups:
        h = g["headline"]
        print(f"{g['label'][:44]:<44} {g['markets']:>6} mkts  sharp {h['sharp']['est']:.3f}  "
              f"pro {h['professional']['est']:.3f}  casual {h['casual']['est']:.3f}  "
              f"casual ROI {g['roi_net_casual']['est']:+.3f}  pass={g['passes_rule']}")
    print("merges:", json.dumps(merges))
    return 0


if __name__ == "__main__":
    sys.exit(main())
