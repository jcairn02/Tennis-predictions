"""Rebuild the promising feature shortlist on the repaired day-level history.

Run after repair_history.py. No cached original forecast feature is imported.
Original 2010-2018 constants are frozen; short IOS half-lives remain the already
selected ATP four/WTA thirteen weeks, so this is exploratory historical repair.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

for key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(key, "2")

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_alpha_audit import repair_history as H
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage3_traits as T
from src.eda.predictability_diagnostic import stage4_features as F
from src.eda.ufc_ideas import stageB_common as B
from src.eda.ufc_ideas import stageB_adjperf as AP
from src.eda.ufc_ideas import stageB_ios as I
from src.eda.ufc_ideas import stageD_profile as D

OUT = H.OUT
FEATURES = OUT / "repair_features.parquet"
PROFILE = [f"adjperf_{s}|decayed" for s in D.ADJ_STATS] + [f"adjdef_{s}|decayed" for s in D.NO_MIRROR]
CONTEXT = ["sets_14d|single", "surface_first|single", "age|single", "age|single|2"]


def adjperf_features(rows: pd.DataFrame, means: dict, chosen: dict, typ: dict, madpop: dict) -> dict:
    """The frozen AP16 profile plus total-points form, with every history rebuilt."""
    specs = [(s, "adjperf") for s in (*D.ADJ_STATS, "tpw")] + [(s, "adjdef") for s in D.NO_MIRROR]
    ctx = AP.Ctx(rows, means, typ=typ, madpop=madpop, stats=tuple(dict.fromkeys(s for s, _ in specs)))
    wanted = sorted({(s, ch, AP.constants_for(chosen, s, ch, t)["h1"], AP.constants_for(chosen, s, ch, t)["tau"])
                     for s, ch in specs for t in C.TOURS}, key=str)
    print(f"Adjperf: {len(ctx.box_idx):,} box rows, {ctx.P.n_pairs:,} history pairs", flush=True)
    moments = ctx.moments(wanted)
    out = {}
    for s, ch in specs:
        z = np.full(len(ctx.box_idx), np.nan)
        for tour in C.TOURS:
            k = AP.constants_for(chosen, s, ch, tour)
            v, _, _ = ctx.z(s, ch, moments[(s, ch, k["h1"], k["tau"])], k["K1"], k["tau"])
            mask = ctx.tour_box == tour
            z[mask] = v[mask]
        units, ok = ctx.step3_units(s, ch)
        col = f"{ch}_{s}|decayed"
        out[col] = np.full(len(ctx.A), np.nan)
        for tour in C.TOURS:
            k = AP.constants_for(chosen, s, ch, tour)
            sums = ctx.step3([z], units, ok & (ctx.tour_box == tour), k["tau"], (k["h3"],))
            val, _ = ctx.pool_values(sums, AP.form_key("decayed", k["h3"]), 0,
                                     ctx.pool_kref(s, k["K3"], k["tau"]), exists_key="career")
            mask = rows.tour.to_numpy()[ctx.A] == tour
            out[col][mask] = val[mask]
        print(f"Built {col}", flush=True)
    return out


def context_features(rows: pd.DataFrame) -> dict:
    """Original age/surface/load definitions, now over accepted match-day history.

    Load and surface familiarity therefore describe observed dated history, not
    a claim of complete physical workload. Missing historical set totals mask
    the load feature, rather than treating an unrecorded total as zero.
    """
    A, Bi = B.pool_rows(rows)
    played = rows.played.to_numpy(dtype=bool)
    pc, day = rows.pcode.to_numpy(), rows.day.to_numpy()
    sets = rows.sets_won_d.to_numpy(dtype=float)
    values = np.column_stack([(played & ~np.isfinite(sets)).astype(float),
                              np.where(played & np.isfinite(sets), sets, 0.)])
    car, _ = T.lookback_sums(rows, values)
    old = T.sums_before(pc, day, values, pc, day - 14)
    window = car - old
    load = np.where(window[:, 0] < .5, np.log1p(np.maximum(window[:, 1], 0.)), np.nan)
    frame = rows[["tournament_date", "tournament_id", "round_order"]].copy()
    # Factorization avoids fixed-width arithmetic collisions if more years arrive.
    frame["player_id"] = pd.factorize(pd.MultiIndex.from_arrays([pc, rows.year, rows.surf]))[0]
    frame["played"] = played.astype(float)
    n = C.asof_sums(frame, ["played"]).played.to_numpy()
    first = np.where(rows.surf.to_numpy() > 0, (n < F.SURFACE_FIRST).astype(float), np.nan)
    age = rows.age.to_numpy(dtype=float)
    age = np.where((age >= F.AGE_RANGE[0]) & (age <= F.AGE_RANGE[1]), age - F.AGE_CENTRE, np.nan)
    return {"sets_14d|single": load[A] - load[Bi], "surface_first|single": first[A] - first[Bi],
            "age|single": age[A] - age[Bi], "age|single|2": age[A] ** 2 - age[Bi] ** 2}


def games_elo(rows: pd.DataFrame, constants: dict, scales: dict) -> np.ndarray:
    """Frozen games-weighted Elo; current score enters updates only after forecast."""
    A, _ = B.pool_rows(rows)
    a = rows.iloc[::2].reset_index(drop=True)
    share = F.winner_shares(rows)["games"]
    result = np.full(len(a), np.nan)
    for tour in sorted(set(a.tour)):
        ix = np.flatnonzero(a.tour.eq(tour).to_numpy())
        t = a.iloc[ix].reset_index(drop=True)
        h, k = F.elo_inputs(t), constants[tour]
        weight = np.where(np.isfinite(share[ix]), share[ix] / scales[tour], 1.)
        r = F.weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"],
                                t.status.isin(H.E.UPDATES["ret"]).tolist(), weight.tolist(), h["n_players"],
                                k["k0"], k["offset"], k["shape"])
        result[ix] = F.safe_logit(H.E.blend(r, k["w"]))
    return result[A // 2]


def rating_matchup(rows: pd.DataFrame) -> np.ndarray:
    A, Bi = B.pool_rows(rows)
    mu, serve, ret = rows.mu_logit.to_numpy(), rows.serve_own.to_numpy(), rows.return_own.to_numpy()
    pa, pb = expit(mu[A] + serve[A] - ret[Bi]), expit(mu[A] + serve[Bi] - ret[A])
    return F.safe_logit(F.scheduled_iid_prob(pa, pb, schedule_rows(rows.iloc[A])))


def schedule_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Format rules use the original edition year; evaluation uses match-day year."""
    if "original_year" not in rows:
        return rows
    return rows.assign(year=rows.original_year)


def ios_features(rows: pd.DataFrame, means: dict, typical: dict, chosen: dict) -> tuple[np.ndarray, dict]:
    """Daily IOS snapshots, using only the selected serve-points statistic."""
    sa = B.stat_arrays(rows, means, ("spw",))
    offense, defense = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
    diagnostics = {}
    for tour in sorted(set(rows.tour)):
        td = I.tour_inputs_one(rows, sa, typical, tour, "spw")
        k = chosen[tour]
        r = I.run(td, "spw", h=k["h"], kappa=k["kappa"], tau=k["tau"], mode="weekly")
        offense[td["idx"]], defense[td["idx"]] = r["O"], r["D"]
        diagnostics[tour] = {"constants": k, **r["solver"]}
        if r["solver"]["not_converged"]:
            raise RuntimeError(f"IOS solve failed to converge: {tour}: {r['solver']}")
        print(f"Built {tour} IOS over {r['solver']['snapshots']:,} match-day snapshots", flush=True)
    return I.matchup_points(schedule_rows(rows), sa, offense, defense), diagnostics


def main() -> int:
    start = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "repair_rows.parquet"
    rows = pd.read_parquet(path)
    if not rows.tournament_date.is_monotonic_increasing:
        raise ValueError("Expected repaired match-day ordering")
    A, _ = B.pool_rows(rows)
    metadata = ["match_id", "tour", "year", "evaluation", "a_won", "group", "status", "order",
                "tournament_id", "tournament_date", "match_date", "original_tournament_date", "original_order",
                "level", "qualifying", "round", "round_order", "surface", "tournament_name"]
    frame = rows.iloc[A][metadata].reset_index(drop=True).copy()
    frame["p_elo"], frame["p_mkt"] = rows.p_elo_a.to_numpy()[A], rows.p_mkt_a.to_numpy()[A]
    fmt = F.scheduled_format(schedule_rows(rows.iloc[A]))
    frame["scheduled_best_of"] = fmt.best_of.to_numpy()
    frame["scheduled_format_supported"] = fmt.supported.to_numpy()
    frame["rating_matchup|single"] = rating_matchup(rows)
    frame = frame.assign(**context_features(rows))
    ek, _, _ = H.frozen_constants()
    scale_frame = pd.read_csv(B.STAGE4_CONSTANTS)
    scale_frame = scale_frame[scale_frame.kind.eq("weighted Elo scale") & scale_frame.stat.eq("elo_games")]
    scales = dict(zip(scale_frame.tour, scale_frame.value))
    frame["elo_games|single"] = games_elo(rows, ek, scales)
    means = B.surface_means()
    chosen, typ, mad = AP.load_frozen()
    frame = frame.assign(**adjperf_features(rows, means, chosen, typ, mad))
    gc.collect()
    ios = json.loads(I.IOS_SUMMARY.read_text(encoding="utf-8"))
    ios_typ = {(r["stat"], r["tour"]): float(r["units"]) for r in ios["typical_units"]}
    ios_chosen = {r["tour"]: {"h": 4. if r["tour"] == "atp" else 13., "kappa": float(r["kappa"]), "tau": int(r["tau"])}
                  for r in ios["chosen"] if r["stat"] == "spw"}
    frame["ios_short"], ios_meta = ios_features(rows, means, ios_typ, ios_chosen)
    feature_cols = ["rating_matchup|single", "adjperf_tpw|decayed", "ios_short", "elo_games|single", *CONTEXT, *PROFILE]
    frame.to_parquet(FEATURES, index=False, compression="zstd")
    coverage = []
    for tour in C.TOURS:
        mask = frame.tour.eq(tour).to_numpy()
        for col in feature_cols:
            for since in (2010, 2019, 2022):
                sel = mask & frame.year.ge(since).to_numpy()
                coverage.append({"tour": tour, "since": since, "feature": col, "pool_matches": int(sel.sum()),
                                 "available": int((sel & np.isfinite(frame[col].to_numpy(dtype=float))).sum())})
    pd.DataFrame(coverage).to_csv(OUT / "repair_feature_coverage.csv", index=False)
    summary = {"input": str(path.relative_to(ROOT)), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "output": str(FEATURES.relative_to(ROOT)), "pool_matches": len(frame), "features": feature_cols,
               "output_sha256": hashlib.sha256(FEATURES.read_bytes()).hexdigest(),
               "original_inputs_sha256": json.loads((OUT / "repair_history_summary.json").read_text(encoding="utf-8"))["inputs_sha256"],
               "seconds": round(time.time() - start, 1), "ios": ios_meta,
               "definitions": {"profile": "Original AP16 plus adjusted total-points form; frozen constants, rebuilt history",
                               "ratings": "Fresh Elo/SR plus games-weighted Elo from repair_history rows",
                               "format": "Scheduled edition metadata gates box history and iid targets; unsupported editions excluded from box history and iid predictions",
                               "surface": "Fewer than three observed dated matches on surface this calendar season",
                               "load": "log1p observed sets over prior 14 match-date days; missing historical totals mask load",
                               "age": "A minus B age, and (age minus 25) squared difference; outside 14..50 missing"},
               "limitations": ["All undated matches omitted from history and targets",
                               "Workload and surface familiarity reflect the restricted observation universe",
                               "Provider dates with next-day availability assumption, not precise match-end timestamps",
                               "Match-day joins rely on retrospective source identity/score concordance",
                               "Frozen constants/short-IOS settings were selected in previously inspected research"]}
    B.jdump(summary, OUT / "repair_features_summary.json")
    print(f"Wrote {FEATURES}: {len(frame):,} matches in {summary['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
