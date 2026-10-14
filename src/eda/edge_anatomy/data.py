"""The edge-anatomy study's analysis table: the current instance's final forecasts beside its price, inputs and results.

The current instance (data/studies/current_best_model/template_2026-10-10/, read-only), through the decided recipe as
src/eda/pinnacle_first/backtest.py applies it (the worked example the instance's README names):
    * the forecast is the 16-seed mean of the stored fits;
    * the per-tour calibration slopes and the men's serve-speed coefficient b are fitted walk-forward on 2019 .. Y - 1
      from seeds 0-3 (compare.walk_forward), debut seasons out, b shrunk with tau 0.05;
    * the price is the frame's own odds input (Pinnacle first), margin-free, recalibrated walk-forward with one slope
      per tour (compare.close_forecast).
Matches: the frame's seasons 2019-2026, played before 29 Jul 2026 (the proposed sealed holdout is never read: rows from
that day are filtered out before the result column is read), with a value in the speed column (the 40 men's matches of
June 2026 whose ids changed at the 7 Oct rebuild have none and are left out, as in the backtest).

Writes data/studies/edge_anatomy/analysis.parquet (one row per match, seasons 2020-2026 scored, 2019 kept for fits),
seeds.parquet (the instance's per-seed symmetrised forecasts, seeds 0-15) and data_facts.json.
Run: ./python.sh src/eda/edge_anatomy/data.py
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
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

C = CMP.C
SEASONS = tuple(range(2020, 2027))
SURFACE = {0.0: "hard", 1.0: "clay", 2.0: "grass", 3.0: "carpet"}
ROUND = {10.0: "RR", 11.0: "R128", 12.0: "R64", 13.0: "R32", 14.0: "R16", 15.0: "QF", 16.0: "SF", 17.0: "F"}


def outcomes(P: C.Paths) -> pd.Series:
    f = pd.read_parquet(P.model_frame, columns=["match_id", "tournament_date", "a_won"],
                        filters=[("tournament_date", "<", E.SEALED_FROM)])
    if len(f) and f["tournament_date"].max() >= E.SEALED_FROM:
        raise RuntimeError("a result from the sealed holdout was read")
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def speed() -> pd.Series:
    s = pd.read_parquet(E.SPEED, columns=["match_id", "spd_L_B"])
    return s.astype({"match_id": str}).set_index("match_id")["spd_L_B"]


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    _, P, _ = CMP.candidate(str(E.INSTANCE))
    frame = CMP.inputs_frame(P)
    y = outcomes(P)
    z = speed()
    keep = (frame["season"].between(2019, max(SEASONS)) & (frame["tournament_date"] < E.SEALED_FROM)).to_numpy()
    ids = frame.index[keep]
    no_speed = ids[~np.isfinite(z.reindex(ids).to_numpy(float))]
    ids = ids.difference(no_speed, sort=False)
    if y.reindex(ids).isna().any():
        raise RuntimeError("a scored match lacks its result")
    info = frame.loc[ids, ["tour", "season", "tournament_date", "debut_season", "odds_input", "p_mkt",
                           "p_mkt_avg"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    info["spd"] = z.reindex(ids).to_numpy(float)
    info["level"] = frame.loc[ids, "in_level"].map(CMP.LEVELS).to_numpy()
    info["surface_name"] = frame.loc[ids, "in_surface"].map(SURFACE).to_numpy()
    info["round_name"] = frame.loc[ids, "in_round"].map(ROUND).to_numpy()
    seasons = tuple(range(2019, max(SEASONS) + 1))
    p16, _ = F.seed_table("model", seasons, tuple(range(16)), F.FrameIndex(frame.reset_index()[["match_id", "season"]]),
                          P, "td", require_checks=True)
    p16 = p16.reindex(info.index)
    if p16.isna().any().any():
        raise RuntimeError("forecasts are missing for some matches")
    eta4 = pd.Series(C.lg(p16[[0, 1, 2, 3]].mean(axis=1).to_numpy()), index=p16.index)
    par_both = CMP.walk_forward(eta4, info, z, SEASONS)
    par_s1 = CMP.walk_forward(eta4, info, None, SEASONS)
    test = info.index[info["season"].isin(SEASONS).to_numpy()]
    q_both, _ = CMP.forecasts(p16, info, par_both, z, test)
    q_s1, _ = CMP.forecasts(p16, info, par_s1, None, test)
    q_close, _ = CMP.close_forecast(info, "p_mkt", SEASONS, test)
    q_avg, _ = CMP.close_forecast(info, "p_mkt_avg", SEASONS, test)
    out = info.copy()
    out["eta16"] = C.lg(p16.mean(axis=1).to_numpy())
    for name, v in (("q_full", q_both), ("q_full_s1", q_s1), ("q_close", q_close), ("q_avg_close", q_avg)):
        out[name] = np.nan
        out.loc[test, name] = v
    books = pd.read_parquet(E.INSTANCE / "book_prices.parquet").astype({"match_id": str}).set_index("match_id")
    for c in ("pin_a", "pin_b", "bol_a", "bol_b"):
        out[c] = books[c].reindex(out.index).to_numpy(float)
    names = E.input_names()
    for n in names:
        out[f"in_{n}"] = frame.loc[ids, f"in_{n}"].to_numpy(float)
    facts = {"matches_2019_on": int(len(out)), "scored_2020_on": int(len(test)),
             "left_out_without_speed_value": int(len(no_speed)),
             "by_season_tour": {f"{s}|{t}": int(n) for (s, t), n in out.groupby(["season", "tour"]).size().items()},
             "coefficients_both_stages": {str(k): v for k, v in par_both.items()},
             "coefficients_stage1": {str(k): v for k, v in par_s1.items()},
             "odds_input_by_season": {f"{s}|{k}": int(n) for (s, k), n in
                                      out.groupby(["season", "odds_input"]).size().items()},
             "last_date": str(out["tournament_date"].max().date())}
    seeds = p16.copy()
    seeds.columns = [f"s{k}" for k in seeds.columns]
    return out, seeds, facts


def main() -> int:
    out, seeds, facts = build()
    E.OUT.mkdir(parents=True, exist_ok=True)
    out.reset_index().rename(columns={"index": "match_id"}).to_parquet(E.OUT / "analysis.parquet", index=False)
    seeds.reset_index().rename(columns={"index": "match_id"}).to_parquet(E.OUT / "seeds.parquet", index=False)
    E.write_json(E.OUT / "data_facts.json", facts)
    E.log(f"analysis.parquet: {len(out):,} matches; scored from 2020: {facts['scored_2020_on']:,}; "
          f"left out without speed: {facts['left_out_without_speed_value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
