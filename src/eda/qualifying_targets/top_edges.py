"""Part 2 (the owner's request of 22 Oct 2026, 10:30; process_log.md Part 2): bet only the top 40% of predicted edges on
qualifying, with the current best model and its offset, at Pinnacle's close and at BetOnline's close.

The forecast: today's model (Part 1's arm M0, whose fits are the live instance's) with stage 2, the per-tour slope plus
the speed offset b * spd_L, fitted walk-forward on qualifying (score.model, as in Part 1). The matches: Part 1's scored
qualifying matches (2020-2026, debut seasons out). At each book's closing odds (margin included):
    bets       the side with EV = q * d - 1 > 0, if any (Part 1's rule)
    top 40%    the 40% of those bets with the highest EV (the cut: the 60th percentile of the bets' EV over 2020-2026)
ROI per unit staked, with Part 1's interval (2,000 bootstrap draws of 4-week blocks).

Checks, one line each: the cut set in advance (each season's from the earlier seasons' bets, 2021-2026); ranking by the
edge in probability points (q - 1/d); the live instance's own stage 2 (fitted on main draws) applied to qualifying; the
other 60% of the bets; the top 40% of all priced matches instead of the bets.

Writes data/studies/qualifying_targets/top_edges.json and top_edges.csv.
Run: ./python.sh src/eda/qualifying_targets/top_edges.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import score as S  # noqa: E402

SHARE = 0.40
VENUES = {"pinnacle": ("pin_a", "pin_b"), "betonline": ("bol_a", "bol_b")}


def forecasts() -> tuple[pd.DataFrame, pd.Index, dict]:
    info, z = S.qual_info()
    m0 = S.model(S.seed_table("M0", "qual"), info, z)
    keep = ~info["debut"].to_numpy() & info["season"].isin(S.TEST).to_numpy()
    ids = info.index[keep]
    minfo, mz = S.main_info()
    mm = S.model(S.seed_table("M0", "main"), minfo, mz)          # the instance's stage 2, fitted on main draws
    return info, ids, {"qualifying stage 2": S.fc(m0, "s2", info, ids)[0],
                       "main-draw stage 2": CMP.forecasts(m0["p"], info, mm["s2"], z, ids)[0],
                       "_params": {"qualifying": m0["s2"], "main draw": mm["s2"]}}


def candidates(info: pd.DataFrame, ids: pd.Index, q: np.ndarray, venue: str) -> pd.DataFrame:
    ca, cb = VENUES[venue]
    d_a, d_b = info.loc[ids, ca].to_numpy(float), info.loc[ids, cb].to_numpy(float)
    ok = np.isfinite(d_a) & np.isfinite(d_b)
    ev_a, ev_b = q * d_a - 1, (1 - q) * d_b - 1
    on_a, on_b = ok & (ev_a > 0), ok & (ev_b > 0)
    if (on_a & on_b).any():
        raise SystemExit("both sides +EV: incoherent odds")
    y = info.loc[ids, "y"].to_numpy(float)
    d = np.where(on_a, d_a, np.where(on_b, d_b, np.nan))
    qs = np.where(on_a, q, np.where(on_b, 1 - q, np.nan))
    won = np.where(on_a, y == 1, np.where(on_b, y == 0, False))
    best_ev = np.where(ok, np.fmax(ev_a, ev_b), np.nan)          # for "top 40% of all priced matches"
    return pd.DataFrame({"priced": ok, "bet": on_a | on_b, "ev": np.where(on_a, ev_a, np.where(on_b, ev_b, np.nan)),
                         "pts": qs - 1 / d, "odds": d, "won": won, "best_ev": best_ev,
                         "profit": np.where(on_a | on_b, np.where(won, d - 1, -1.0), 0.0),
                         "season": info.loc[ids, "season"].to_numpy(), "tour": info.loc[ids, "tour"].to_numpy(),
                         "kind": info.loc[ids, "kind"].to_numpy(), "block": info.loc[ids, "block"].to_numpy()},
                        index=ids)


def roi(df: pd.DataFrame, sel: np.ndarray) -> dict:
    """ROI of the selected bets, with Part 1's bootstrap: 2,000 draws of the population's 4-week blocks."""
    sel = np.asarray(sel, bool) & df["bet"].to_numpy()
    n = int(sel.sum())
    if n == 0:
        return {"bets": 0}
    profit = np.where(sel, df["profit"].to_numpy(), 0.0)
    labels, ix = np.unique(df["block"].to_numpy(), return_inverse=True)
    pb, nb = np.bincount(ix, weights=profit), np.bincount(ix, weights=sel.astype(float))
    rng = np.random.default_rng(S.BOOT_SEED)
    w = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=S.N_BOOT)
    num, den = w @ pb, w @ nb
    r = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    s = df[sel]
    return {"bets": n, "share_of_bets": float(n / max(1, int(df["bet"].sum()))), "roi": float(profit.sum() / n),
            "roi_lo": float(np.nanquantile(r, 0.025)), "roi_hi": float(np.nanquantile(r, 0.975)),
            "p_roi_positive": float(np.nanmean(r > 0)), "profit": float(profit.sum()), "won": int(s["won"].sum()),
            "mean_odds": float(s["odds"].mean()), "mean_ev": float(s["ev"].mean()), "min_ev": float(s["ev"].min()),
            "on_favourite": int((s["odds"] < 2.0).sum())}


def walk_forward_cut(df: pd.DataFrame, col: str) -> np.ndarray:
    """Each season's cut from the earlier seasons' bets only (seasons 2021 on; 2020 has no earlier season)."""
    sel = np.zeros(len(df), bool)
    for Y in sorted(df["season"].unique()):
        prior = df["bet"].to_numpy() & (df["season"].to_numpy() < Y)
        if Y < 2021 or not prior.any():
            continue
        cut = np.quantile(df.loc[prior, col].to_numpy(float), 1 - SHARE)
        sel |= (df["season"].to_numpy() == Y) & df["bet"].to_numpy() & (df[col].to_numpy(float) >= cut)
    return sel


def readings(df: pd.DataFrame, venue: str, forecast: str, full: bool) -> list[dict]:
    rows = []
    bet = df["bet"].to_numpy()
    cut = np.quantile(df.loc[bet, "ev"].to_numpy(float), 1 - SHARE)
    top = bet & (df["ev"].to_numpy(float) >= cut)
    base = {"venue": venue, "forecast": forecast, "ev_cut": float(cut)}
    rows.append({**base, "rule": "all +EV bets", "population": "all", **roi(df, bet)})
    rows.append({**base, "rule": "top 40% by EV", "population": "all", **roi(df, top)})
    if not full:
        return rows
    rows.append({**base, "rule": "other 60% of the bets", "population": "all", **roi(df, bet & ~top)})
    for name, mask in (("2020-2024", df["season"].between(2020, 2024)), ("2025-2026", df["season"].between(2025, 2026)),
                       ("men", df["tour"] == "atp"), ("women", df["tour"] == "wta"),
                       ("Slam qualifying", df["kind"] == "GSQ"), ("tour qualifying", df["kind"] == "TQ")):
        rows.append({**base, "rule": "top 40% by EV", "population": name, **roi(df, top & mask.to_numpy())})
    late = (df["season"] >= 2021).to_numpy()
    rows.append({**base, "rule": "all +EV bets", "population": "2021-2026", **roi(df, bet & late)})
    rows.append({**base, "rule": "top 40% by EV", "population": "2021-2026", **roi(df, top & late)})
    rows.append({**base, "rule": "top 40% by EV, cut set in advance", "population": "2021-2026",
                 **roi(df, walk_forward_cut(df, "ev"))})
    cut_p = np.quantile(df.loc[bet, "pts"].to_numpy(float), 1 - SHARE)
    rows.append({**base, "rule": "top 40% by edge in points", "population": "all",
                 **roi(df, bet & (df["pts"].to_numpy(float) >= cut_p))})
    pr = df["priced"].to_numpy()
    cut_all = np.quantile(df.loc[pr, "best_ev"].to_numpy(float), 1 - SHARE)
    rows.append({**base, "rule": "top 40% of all priced matches by EV", "population": "all",
                 **roi(df, bet & (df["best_ev"].to_numpy(float) >= cut_all))})
    return rows


def main() -> int:
    info, ids, q = forecasts()
    params = q.pop("_params")
    rows = []
    for venue in VENUES:
        for forecast, qq in q.items():
            df = candidates(info, ids, qq, venue)
            rows += readings(df, venue, forecast, full=True)       # both versions in full since 10:41
    t = pd.DataFrame(rows)
    t.to_csv(C.OUT / "top_edges.csv", index=False)
    C.write_json(C.OUT / "top_edges.json", {"share": SHARE, "rows": t.to_dict("records"),
                                            "stage2_params": {k: {str(Y): v for Y, v in p.items()}
                                                              for k, p in params.items()}})
    t["roi_ci"] = t.apply(lambda r: (f"{100 * r['roi']:+.1f}% [{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}] "
                                     f"P{r['p_roi_positive']:.2f} n={int(r['bets'])}") if r.get("bets") else "", axis=1)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print(t.pivot_table(index=["forecast", "rule", "population"], columns="venue", values="roi_ci",
                        aggfunc="first").to_string())
    print(t[t["rule"] == "top 40% by EV"][["venue", "forecast", "population", "ev_cut", "mean_ev", "min_ev",
                                          "mean_odds", "on_favourite", "won", "profit"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
