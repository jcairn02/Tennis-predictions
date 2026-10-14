"""The current best model's serve-speed adjustment (docs/decisions/2026-10-07-speed-nudge.md, as amended by the owner on
8 Oct 2026: "I confirm 28 day memory and id love to get the speed data daily").

THE POLICY: ALWAYS MODE L, the 28-day memory.

    logit q = s_tour,Y * eta + b_Y * spd_L

    eta       the base forecast's log-odds: the local TabPFN-3.5 (58 inputs) for season Y, trained on 2013 .. Y - 1,
              symmetrised, the mean of seeds 0-15
    spd_L     clip((f28_A - f28_B) / 1.9496051535048338 km/h, -4, 4): the study's filter with a 28-day half-life on the
              speeds in hand at forecast time (spd_L_<scenario> in adaptive/columns.parquet). 0 for every woman, who
              therefore gets only her tour slope. The exact standardiser: a rounded 1.950 would break spd_L_B = spd_B_M1
    s, b      walk-forward on 2019 .. Y - 1 from the base's seeds 0-3 mean (debut seasons out), with
              src/eda/serve_speed_tabpfn/score.py's nudge_parameters, unchanged; b shrunk with tau = 0.05. The set is
              chosen by the LIVE SPEED FEED (--feed):
                weekly   L_weekly, fitted on the weekly feed's history: spd_B_M1 = spd_L_B (today's sources: weekly
                         ManTennisData, Slams after the event). Equal to the latency run's B-M1 fit. The default until a
                         daily collector runs
                daily    L_daily, fitted on the daily feed's history: spd_L_D (scenario D: non-Slam rows at lf + 2,
                         Slams after the event)

SUPERSEDED (kept behind --policy switch, 8 Oct 2026): the T/L switch of adaptive/plan.md, where a match with no late
player used the 14-day column spd_T (/ 2.223995373606193 km/h) with set T (fitted on the instant history spd_f: the
study's S9). apply() still accepts a per-match mode array for it.

Commands:
    --coefficients   fits T, L_weekly and L_daily for 2024-2026 (and the next season once the frame holds the last one
                     complete) and writes adaptive/coefficients.json. Each row reads results <= Y - 1 only. Refuses to
                     write unless T equals the study's S9 and L_weekly the latency run's B-M1 exactly
    --date D         scores every frame match whose best-estimate day is D (frame_keys.parquet `obs`) from data in hand
                     only (the base forecast, the scenario's columns, coefficients.json): always L by default, the set
                     of --feed; --policy switch for the superseded rule. Writes adaptive/scored/<D>_<scenario>_<policy>
                     _<feed>.csv. Reads no result
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

MODES = ("T", "L")
HISTORY = {"T": "spd_f", "L": "spd_B_M1"}        # the switch's two sets (score_adaptive.py); L = L_weekly
FEEDS = ("weekly", "daily")
SETS = {"T": "spd_f", "L_weekly": "spd_B_M1", "L_daily": "spd_L_D"}   # coefficient set -> its history column
FEED_SCENARIO = {"weekly": "B", "daily": "D"}    # the availability scenario whose columns match each feed
FIT_SEASONS = (2024, 2025, 2026)
EXACT = 1e-12
EPOCH = pd.Timestamp("1970-01-01")


def folder(P: C.Paths) -> Path:
    return P.out / "adaptive"


def coefficients_path(P: C.Paths) -> Path:
    return folder(P) / "coefficients.json"


def columns_path(P: C.Paths) -> Path:
    return folder(P) / "columns.parquet"


# ------------------------------------------------------------------------------------------------
# The rule

def l_set(coef: dict, feed: str = "weekly") -> dict:
    """The L coefficients for the live feed: L_weekly or L_daily (a table with only "L" serves the weekly feed)."""
    if feed not in FEEDS:
        raise ValueError(f"feed must be one of {FEEDS}")
    if f"L_{feed}" in coef:
        return coef[f"L_{feed}"]
    if feed == "weekly" and "L" in coef:
        return coef["L"]
    raise KeyError(f"no L_{feed} coefficients")


def apply(eta, tour, season, mode="L", col_t=None, col_l=None, coef: dict | None = None,
          feed: str = "weekly") -> np.ndarray:
    """q = expit(s_tour,Y eta + b_Y column), elementwise; b is the shrunk coefficient; a woman's column is taken as 0.
    DEFAULT: always mode L (col_l with the feed's L set). A per-match mode array of T and L applies the superseded switch
    (col_t with set T where T). The positional order (eta, tour, season, mode, col_t, col_l, coef) is unchanged."""
    if coef is None or col_l is None:
        raise ValueError("coef and col_l are required")
    eta = np.asarray(eta, float)
    n = len(eta)
    tour, season, mode = (np.broadcast_to(np.asarray(v), (n,)) for v in (tour, season, mode))
    col_l = np.broadcast_to(np.asarray(col_l, float), (n,))
    col_t = np.broadcast_to(np.asarray(np.nan if col_t is None else col_t, float), (n,))
    if not set(np.unique(mode)) <= set(MODES):
        raise ValueError(f"mode must be T or L, got {sorted(set(np.unique(mode)) - set(MODES))}")
    if not set(np.unique(tour)) <= set(C.TOURS):
        raise ValueError("tour must be atp or wta")
    sets = {"T": coef.get("T"), "L": l_set(coef, feed)}
    s, b = np.empty(n), np.empty(n)
    for m in MODES:
        for y in np.unique(season):
            k = (mode == m) & (season == y)
            if not k.any():
                continue
            if sets[m] is None:
                raise KeyError(f"no {m} coefficients")
            c = sets[m][str(int(y))]
            s[k] = np.where(tour[k] == "atp", c["s_atp"], c["s_wta"])
            b[k] = c["b_shrunk"]
    z = np.where(mode == "T", col_t, col_l)
    if np.isnan(z[(tour == "atp")]).any():
        raise ValueError("a man in mode T needs col_t")
    z = np.where(tour == "wta", 0.0, z)
    return expit(s * eta + b * z)


# ------------------------------------------------------------------------------------------------
# The coefficients (walk-forward, seasons < Y only)

def history_info(P: C.Paths, with_daily: bool = False) -> pd.DataFrame:
    """score.population (no result) with spd_B_M1 (latency/variants.parquet) joined and, with_daily, spd_L_D
    (adaptive/columns.parquet); spd_f is the study's column. score_adaptive joins the whole columns table itself, so the
    daily column is opt-in."""
    info = S.population(P)
    v = pd.read_parquet(P.out / "latency" / "variants.parquet", columns=["match_id", "spd_B_M1"])
    v["match_id"] = v["match_id"].astype(str)
    if v["match_id"].duplicated().any():
        raise RuntimeError("variants.parquet: duplicate match ids")
    info = info.join(v.set_index("match_id"))
    if with_daily:
        d = pd.read_parquet(columns_path(P), columns=["match_id", "spd_L_D"])
        d["match_id"] = d["match_id"].astype(str)
        info = info.join(d.set_index("match_id"))
    for c in [c for c in ("spd_B_M1", "spd_L_D") if c in info]:
        if not np.isfinite(info[c].to_numpy(float)).all():
            raise RuntimeError(f"{c} missing for some 2019-2026 frame matches")
    return info


def with_history(info: pd.DataFrame, which: str) -> pd.DataFrame:
    """The table with a set's history column in the spd_f slot (score.nudge_parameters reads it). which: a mode (T, L)
    or a set name (T, L_weekly, L_daily)."""
    col = SETS.get(which) or HISTORY[which]
    out = info.copy()
    out["spd_f"] = info[col].to_numpy(float)
    return out


def season_complete(P: C.Paths, season: int) -> bool:
    f = pd.read_parquet(P.model_frame, columns=["season", "tournament_date"])
    d = f.loc[f["season"] == season, "tournament_date"]
    return bool(len(d)) and d.max() >= pd.Timestamp(f"{season}-11-01")


def fittable(P: C.Paths, season: int) -> tuple[bool, str]:
    f = pd.read_parquet(P.model_frame, columns=["season"])
    have = set(f["season"])
    if not all(s in have for s in range(C.CALIB_FROM, season)):
        return False, f"the frame lacks part of 2019..{season - 1}"
    if not season_complete(P, season - 1):
        return False, f"the frame's {season - 1} is not complete (needs events into November)"
    return True, "history 2019.." + str(season - 1)


def fit(bank: S.Bank, info: pd.DataFrame, y: pd.Series, seasons, sets=MODES) -> dict:
    """{set: {str(Y): nudge_parameters}} for each Y: score.nudge_parameters on the set's history column (seasons
    2019 .. Y - 1 only). The default sets are the switch's T and L (score_adaptive.py)."""
    out = {}
    for m in sets:
        sc = S.Scorer(bank, with_history(info, m), y)
        out[m] = {str(Y): S.nudge_parameters(sc, Y) for Y in seasons}
    return out


def published(P: C.Paths) -> dict:
    """The parameters the 2024-2026 rows must equal: the study's S9 (T) and the latency run's B-M1 (L_weekly)."""
    study = C.read_json(P.out / "results.json")["S9_parameters"]
    lat = C.read_json(P.out / "latency" / "results_latency.json")["variants"]["spd_B_M1"]["S9_parameters"]
    return {"T": study, "L": lat}


def agreement(coef: dict, ref: dict) -> dict:
    out = {}
    for m, rows in ref.items():
        mine = coef.get(m) if m in coef else coef.get("L_weekly")
        for y, row in rows.items():
            if mine is not None and y in mine:
                out[f"{m}_{y}"] = max(abs(mine[y][k] - row[k]) for k in ("s_atp", "s_wta", "b_mle", "se_b",
                                                                        "b_shrunk"))
    return out


def standardisers(P: C.Paths) -> dict:
    """The exact km/h per unit of each column, from the builds' own metadata."""
    meta = folder(P) / "columns_meta.json"
    if meta.exists() and "standardisers_km_h" in C.read_json(meta):
        st = C.read_json(meta)["standardisers_km_h"]
        return {"T": float(st["spd_T"]), "L": float(st["spd_L"]), "source": "adaptive/columns_meta.json"}
    t = C.read_json(P.feature_meta).get("s_f")
    lat = P.out / "latency" / "variants_meta.json"
    l_sd = C.read_json(lat).get("standardisation_sd_km_h", {}).get("B_M1") if lat.exists() else None
    return {"T": t, "L": l_sd, "source": "features/speed_meta.json s_f; latency/variants_meta.json B_M1"}


def write_coefficients(P: C.Paths = C.DEFAULT, y: pd.Series | None = None) -> dict:
    seasons = list(FIT_SEASONS)
    nxt = max(FIT_SEASONS) + 1
    ok, why = fittable(P, nxt)
    while ok:                                   # every later season the frame can fit (until 10 Oct 2026: 2027 only)
        seasons.append(nxt)
        nxt += 1
        ok, why = fittable(P, nxt)
    if not columns_path(P).exists():
        raise RuntimeError("adaptive/columns.parquet (spd_L_D) is needed for L_daily")
    info = history_info(P, with_daily=True)
    bank = S.Bank(P, S.frame_index(P), require_checks=True)
    coef = fit(bank, info, S.labels(P) if y is None else y, seasons, sets=tuple(SETS))
    agree = agreement(coef, published(P))
    if len(agree) < 6 or max(agree.values()) > EXACT:
        raise RuntimeError(f"the 2024-2026 coefficients do not equal the published fits: {agree}")
    out = {"policy": "always mode L (the 28-day memory; owner's amendment of 8 Oct 2026); the L set follows the live "
                     "speed feed: L_weekly while only the weekly feed runs (the default), L_daily once a daily feed runs",
           "L_weekly": coef["L_weekly"], "L_daily": coef["L_daily"], "T": coef["T"],
           "L": coef["L_weekly"],
           "history": {"L_weekly": "spd_B_M1 = spd_L_B: today's sources (weekly ManTennisData, Slams after the event)",
                       "L_daily": "spd_L_D: scenario D (non-Slam rows at lf + 2, Slams after the event)",
                       "T": "spd_f: the instant history (the study's S9); superseded with the switch",
                       "L": "an alias of L_weekly (the switch's name)"},
           "tau": C.TAU_NUDGE, "standardised_by_km_h": standardisers(P),
           "fit": "score.nudge_parameters: logit q = s_tour eta + b z on 2019 .. Y - 1, eta the base's seeds 0-3 mean, "
                  "debut seasons out; b_shrunk = b_mle tau^2 / (tau^2 + se_b^2)",
           "applied_with": "the 16-seed mean of the base's symmetrised forecasts; b_shrunk",
           "agreement_with_published": agree, **{f"season_{s}": "fitted" for s in seasons if s > max(FIT_SEASONS)},
           f"season_{nxt}": f"not yet fittable: {why}"}
    C.write_json(coefficients_path(P), out)
    return out


def load_coefficients(P: C.Paths = C.DEFAULT) -> dict:
    return C.read_json(coefficients_path(P))


# ------------------------------------------------------------------------------------------------
# Scoring a date from data in hand

def score_date(P: C.Paths, day: str, scenario: str | None = None, policy: str = "L",
               feed: str = "weekly") -> pd.DataFrame:
    """Every frame match whose best-estimate day is `day`: the base forecast, the mode and q. policy "L" (the default):
    every match in mode L with the feed's set; "switch": the superseded T/L rule. scenario: whose columns stand for the
    speeds in hand (default: the feed's, weekly B, daily D). Reads the frame keys, the base fits, the columns and
    coefficients.json; no result."""
    if policy not in ("L", "switch"):
        raise ValueError("policy must be L or switch")
    scenario = scenario or FEED_SCENARIO[feed]
    d = (pd.Timestamp(day) - EPOCH).days
    keys = pd.read_parquet(P.out / "frame_keys.parquet", columns=["match_id", "tour", "season", "obs"])
    keys = keys[keys["obs"] == d].reset_index(drop=True)
    if keys.empty:
        return keys
    cols = [f"spd_T_{scenario}", f"spd_L_{scenario}", f"mode_{scenario}"]
    c = pd.read_parquet(columns_path(P), columns=["match_id"] + cols).set_index("match_id").reindex(keys["match_id"])
    if c.isna().any().any():
        raise RuntimeError("columns missing for some of the date's matches")
    bank = S.Bank(P, S.frame_index(P), require_checks=True)
    rows = []
    for season, g in keys.groupby("season"):
        p = bank.per_seed("model", S.SEEDS16, (int(season),), "td").reindex(g["match_id"].to_numpy())
        if p.isna().to_numpy().any():
            raise RuntimeError("base forecasts missing for some of the date's matches")
        pb = p.mean(axis=1).to_numpy()
        rows.append(g.assign(p_base=pb, eta=C.lg(pb)))
    out = pd.concat(rows, ignore_index=True)
    c = c.reindex(out["match_id"])
    coef = load_coefficients(P)
    out["policy"], out["feed"], out["scenario"] = policy, feed, scenario
    out["mode"] = "L" if policy == "L" else c[f"mode_{scenario}"].to_numpy()
    out["col_T"] = c[f"spd_T_{scenario}"].to_numpy(float)
    out["col_L"] = c[f"spd_L_{scenario}"].to_numpy(float)
    out["q"] = apply(out["eta"], out["tour"], out["season"], out["mode"], out["col_T"], out["col_L"], coef, feed=feed)
    out.insert(3, "day", day)
    path = folder(P) / "scored" / f"{day}_{scenario}_{policy}_{feed}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--coefficients", action="store_true")
    g.add_argument("--date")
    ap.add_argument("--scenario", default=None, help="whose columns stand for the speeds in hand (default: the feed's)")
    ap.add_argument("--policy", choices=("L", "switch"), default="L", help="L (decided); switch (superseded)")
    ap.add_argument("--feed", choices=FEEDS, default="weekly", help="the live speed feed: weekly (default) or daily")
    a = ap.parse_args()
    if a.coefficients:
        out = write_coefficients()
        print(json.dumps({k: out[k] for k in ("agreement_with_published",)}, indent=1))
        print({k: v for k, v in out.items() if k.startswith("season_")})
        return 0
    t = score_date(C.DEFAULT, a.date, a.scenario, a.policy, a.feed)
    print(t.to_string(index=False) if len(t) else f"no frame match on {a.date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
