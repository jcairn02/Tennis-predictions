"""The closing market by surface and by point in the surface season (men's main tour).

  1. Market log loss and calibration slope by surface; the sporting forecasts' gap to the market.
  2. Where the anchored nudges gain: profile + context on the market, split by surface and timing.
  3. Surface Elo's specialisation term against the market's residual, inside early-surface-season
     matches (either player with fewer than three observed matches on the surface this season).
Run after anchor.py: ./python.sh src/eda/market_anchoring/market_surface.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C


def calibration(frame: pd.DataFrame, mask, column: str) -> dict:
    g = frame[mask & np.isfinite(frame[column])]
    if len(g) < 200:
        return {}
    beta, se = C.cluster_logit(g[[column]].to_numpy(), g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
    return {"slope": float(beta[0]), "slope_se": float(se[0])}


def by_surface(frame: pd.DataFrame, preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    early = frame["surface_first|single"].abs().gt(0) | frame.surface_first_any.astype(bool)
    subsets = {"all": np.ones(len(frame), dtype=bool)}
    for s in ("Hard", "Clay", "Grass"):
        subsets[s] = frame.surface.eq(s).to_numpy()
        subsets[f"{s} early-season"] = (frame.surface.eq(s) & early).to_numpy()
        subsets[f"{s} rest of season"] = (frame.surface.eq(s) & ~early).to_numpy()
    y = frame.a_won.to_numpy(dtype=float)
    for name, sub in subsets.items():
        for window, (lo, hi) in {"2013_2025": (2013, 2025), "2019_2026": (2019, 2026)}.items():
            m = sub & frame.year.between(lo, hi).to_numpy() & np.isfinite(frame.p_avg_a.to_numpy())
            row = {"subset": name, "window": window, "n": int(m.sum()),
                   "ll_average": float(C.ll(y[m], frame.p_avg_a[m]).mean()),
                   "ll_elo": float(C.ll(y[m], frame.p_elo[m]).mean()),
                   **{f"avg_{k}": v for k, v in calibration(frame, m, "mkt_avg").items()}}
            mp = m & np.isfinite(frame.p_ps_a.to_numpy())
            row.update({"n_ps": int(mp.sum()), "ll_pinnacle": float(C.ll(y[mp], frame.p_ps_a[mp]).mean()),
                        **{f"ps_{k}": v for k, v in calibration(frame, mp, "mkt_ps").items()}})
            if window == "2019_2026":
                q = m & np.isfinite(frame.p_sport36.to_numpy())
                row["sport36_minus_average_mll"] = C.gain(frame, frame.p_sport36, frame.p_avg_a, q)["gain_mll"]
                nud = preds["average|profile16_context|free"].to_numpy()
                cal = preds["average|calibrated"].to_numpy()
                g = C.gain(frame, nud, cal, m & np.isfinite(nud))
                row.update({"profile_context_gain_mll": g["gain_mll"], "profile_context_lo": g["lo_mll"],
                            "profile_context_hi": g["hi_mll"]})
                for key in ("elo_blend", "elo_surface_gap"):
                    p = preds[f"average|{key}|free"].to_numpy()
                    row[f"{key}_gain_mll"] = C.gain(frame, p, cal, m & np.isfinite(p))["gain_mll"]
            rows.append(row)
    return pd.DataFrame(rows)


def residual_tests(frame: pd.DataFrame) -> pd.DataFrame:
    """y ~ b logit(market) + c x for surface terms, inside subsets (cluster-robust z for c)."""
    out = []
    early = frame["surface_first|single"].abs().gt(0) | frame.surface_first_any.astype(bool)
    for market in ("mkt_avg", "mkt_ps"):
        for term in ("elo_surface_gap", "elo_overall", "pf_surface_serve", "pf_surface_return"):
            for name, sub in {"all": np.ones(len(frame), dtype=bool),
                              "clay": frame.surface.eq("Clay").to_numpy(), "grass": frame.surface.eq("Grass").to_numpy(),
                              "hard": frame.surface.eq("Hard").to_numpy(),
                              "clay early": (frame.surface.eq("Clay") & early).to_numpy(),
                              "grass early": (frame.surface.eq("Grass") & early).to_numpy()}.items():
                g = frame[sub & frame.year.between(2013, 2025).to_numpy() & np.isfinite(frame[market])]
                x = np.column_stack([g[market], g[term]])
                beta, se = C.cluster_logit(x, g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
                out.append({"market": market, "term": term, "subset": name, "n": len(g),
                            "market_coef": beta[0], "term_coef": beta[1], "term_se": se[1], "z": beta[1] / se[1]})
    return pd.DataFrame(out)


def main():
    frame = C.load_atp()
    # surface_first|single is A minus B, so equal flags cancel; recover "either player early" from the rows.
    rows = pd.read_parquet(C.REPAIRS / "repair_rows.parquet", columns=["match_id", "player_id", "year", "surface",
                                                                        "day", "played"])
    rows = rows.assign(n=1)
    rows["seen"] = rows.groupby(["player_id", "year", "surface"]).cumcount()
    # strictly earlier days: subtract same-day matches counted before this one
    same_day = rows.groupby(["player_id", "year", "surface", "day"]).cumcount()
    rows["prior"] = rows.seen - same_day
    flag = rows.assign(early=rows.prior.lt(3)).groupby("match_id").early.any()
    frame["surface_first_any"] = frame.match_id.map(flag).fillna(False)
    preds = pd.read_parquet(C.OUT / "anchor_predictions.parquet")
    if not (preds.match_id.to_numpy() == frame.match_id.to_numpy()).all():
        raise ValueError("anchor predictions are not in frame order")
    table = by_surface(frame, preds)
    table.to_csv(C.OUT / "market_by_surface.csv", index=False)
    tests = residual_tests(frame)
    tests.to_csv(C.OUT / "surface_residual_tests.csv", index=False)
    pd.set_option("display.width", 250)
    print(table.round(4).to_string())
    print(tests.round(3).to_string())


if __name__ == "__main__":
    main()
