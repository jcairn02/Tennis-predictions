"""Rebuild the 54-input model's 53 sporting inputs on the FULL history (every one of the 872,704 matches), leak-proof.

History and data
    Stage 0's matches and players with the feature-alpha repair's deterministic corrections (repair_data.repair_tables:
    canonical player identities, match-tiebreak scores, invalid box scores, implausible durations). Nothing is dropped
    for lack of a match day.

Which box scores enter history
    Completed matches whose SCHEDULED format is supported (the repair's rule), plus ITF and team matches whose OWN score
    shows the standard format. Stage 0's format label is not used: it classifies a whole event from all its scores,
    later rounds included.

One-player-at-a-time inputs (Elo, games-weighted Elo, serve/return ratings, the adjperf/adjdef profile and total-points
form, sets over 14 days, first matches on a surface, age, the 52-week points matchup)
    The earlier studies' kernels on the tournament-week-and-round clock. For them that clock never lets a result reach
    a match played before it: they follow each player's own sequence (and his opponents' own sequences at the times
    they met), and nobody plays two events at once. The real-date probe (probe.py) checks this.

Solved-together inputs (IOS offence/defence on seven statistics, their matchup products, the short-memory IOS points
matchup)
    ios_time.run_timed on the leak-proof timeline of timing.parquet: a result enters the solve the day after its latest
    possible finish; each match reads the solve of its earliest possible start. The constants (Stage B's h, kappa, tau,
    the typical units, the short memory's half-lives) are the IOS constants registry's version in effect
    (src/eda/ios_constants/registry.py), recorded in ios_features_summary.json.

Match-probability conversions (serve/return ratings, the points matchups) use the scheduled format only.

Writes data/studies/match_timing/leakproof_features.parquet (one row per Stage 4 pool match, A - B inputs) and
leakproof_features_summary.json.

Run: ./python.sh src/eda/match_timing/rebuild.py   (set MATCH_TIMING_WORKERS, default 4)
"""
from __future__ import annotations

import gc
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.ios_constants import registry as IC  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import ios_time as IT  # noqa: E402
from src.eda.feature_alpha_audit import repair_history as H  # noqa: E402
from src.eda.feature_alpha_audit import repair_features as RF  # noqa: E402
from src.eda.feature_alpha_audit.repair_data import repair_tables  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402
from src.eda.predictability_diagnostic import stage3_traits as T  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as F  # noqa: E402
from src.eda.predictability_diagnostic.stage0_build import short_like, tokens_of  # noqa: E402
from src.eda.ufc_ideas import stageB_adjperf as AP  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402
from src.eda.ufc_ideas import stageB_ios as I  # noqa: E402
from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  # noqa: E402   # lower_level_evidence C2 (sandbox only)

WORKERS = int(os.environ.get("MATCH_TIMING_WORKERS", "4"))
PROFILE_IOS = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")


# ------------------------------------------------------------------------------------------------
# Rows

def own_score_standard(scores: pd.Series) -> np.ndarray:
    """True where a match's OWN score shows the standard format: no short sets, no bracketed match tiebreak."""
    cache = {}

    def one(s):
        if s not in cache:
            toks = tokens_of(str(s))[0]
            cache[s] = bool(toks) and not short_like(toks) and not any(br for *_, br in toks)
        return cache[s]
    return np.array([one(s) for s in scores.fillna("")], dtype=bool)


def build_rows(matches: pd.DataFrame, players: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    """repair_history.build_rows on every match (no date filter), with the own-score rule for ITF and team history."""
    keep = players.drop(columns=[c for c in players if c != "match_id" and c in matches])
    rows = keep.merge(matches, on="match_id", how="inner", validate="many_to_one")
    rows = rows.sort_values(["order", "side"], kind="stable").reset_index(drop=True)
    if len(rows) != 2 * len(matches) or not rows.side.iloc[::2].eq("A").all() or not rows.side.iloc[1::2].eq("B").all():
        raise ValueError("Expected exactly A then B for every match")
    a_dates = rows["tournament_date"].iloc[::2]
    if not a_dates.is_monotonic_increasing:
        raise ValueError("Matches must be in the table's chronological order")
    rows["p_mkt_a"] = rows.match_id.map(odds.set_index("match_id").p_avg_a).to_numpy()
    rows["box_stat_from"] = np.where(rows.tour.eq("wta"), C.WTA_BOX_FROM, C.EVAL_YEARS[0])
    rows["observed_format"] = rows["format"]
    schedule = F.scheduled_format(rows)
    own = own_score_standard(rows["score"])
    unmapped = schedule["reason"].eq("unmapped_event_rules").to_numpy() & rows["level"].isin(["ITF", "TEAM"]).to_numpy()
    supported = schedule["supported"].to_numpy() | (unmapped & own)
    rows["history_format_supported"] = supported
    rows["history_format_reason"] = np.where(schedule["supported"], schedule["reason"],
                                             np.where(unmapped & own, "own_score_standard", schedule["reason"]))
    rows["format"] = np.where(supported, "standard", "unknown")
    rows["nonstandard_format"] = ~supported
    rows["original_tournament_date"] = rows["tournament_date"]     # the repair's rating output reads these two
    rows["match_date"] = pd.NaT
    return F.prepare(rows)


# ------------------------------------------------------------------------------------------------
# The 52-week points matchup (Stage 4's mu_points | 52 weeks) on the rebuilt rows

def points_52w(rows: pd.DataFrame) -> np.ndarray:
    """A's serve points won against B's return points won over the last 52 weeks (and the reverse), each shrunk toward
    the tour's surface average with Stage 3's constants, through the iid model with the scheduled format."""
    s3 = json.loads(F.STAGE3.read_text(encoding="utf-8"))
    means = {}
    for r in s3["surface_means"]:
        means.setdefault(r["stat"], {})[(r["tour"], r["surface"])] = float(r["mean"])
    shr = pd.read_csv(F.SHRINKAGE)
    shr = shr[shr["years"].eq("2010-2018") & shr["surface"].eq("all")]
    K = {(r.stat, r.tour): float(r.K_units) for r in shr.itertuples(index=False)}
    xd = F.stat_xd(rows)
    tour = rows["tour"].to_numpy()
    pc, day = rows["pcode"].to_numpy(), rows["day"].to_numpy()
    val, ex = {}, {}
    for s in ("spw", "rpw"):
        x, d, ok = xd[s]
        mu = F.mu_of_rows(rows, means[s])
        V = np.column_stack([np.where(ok, x - d * mu, 0.0), d])
        car, _ = T.lookback_sums(rows, V)
        bef = T.sums_before(pc, day, V, pc, day - F.WEEK52)
        sx, sd = car[:, 0] - bef[:, 0], car[:, 1] - bef[:, 1]
        k = np.where(tour == "atp", K[(s, "atp")], K[(s, "wta")])
        val[s], ex[s] = mu + sx / (sd + k), sd > 0.5
    A, Bi = B.pool_rows(rows)
    exists = ex["spw"][A] & ex["spw"][Bi] & ex["rpw"][A] & ex["rpw"][Bi]
    mu = np.clip(F.mu_of_rows(rows, means["spw"]), F.SHARE_CLIP, 1 - F.SHARE_CLIP)

    def comb(srv, ret):
        m = mu[srv]
        return expit(logit(m) + (F.safe_logit(val["spw"][srv]) - logit(m))
                     - (F.safe_logit(val["rpw"][ret]) - logit(1 - m)))
    pa, pb = comb(A, Bi), comb(Bi, A)
    p = F.scheduled_iid_prob(pa, pb, RF.schedule_rows(rows.iloc[A]))
    return np.where(exists, F.safe_logit(p), np.nan)


# ------------------------------------------------------------------------------------------------
# IOS on the leak-proof timeline (parallel over tour x statistic)

_INPUTS: dict = {}


def _init(inputs: dict) -> None:
    global _INPUTS
    _INPUTS = inputs


def _ios_task(args):
    tour, stat, h, kappa, tau, label = args
    t0 = time.time()
    d = _INPUTS[tour]
    r = _LLEIOS.run_timed(d["td"], stat, h, kappa, tau, d["es"], d["lf"], d["obs"], label=label)  # lower_level_evidence C2 (sandbox only)
    return {"tour": tour, "stat": stat, "label": label, "O": r["O"], "D": r["D"], "solver": r["solver"],
            "seconds": round(time.time() - t0, 1)}


def ios_constants() -> tuple[dict, dict]:
    """Stage B's (h, kappa, tau) per (tour, statistic) and the typical units per (statistic, tour): the IOS constants
    registry's version in effect (no longer stageB_ios_summary.json, which a re-run of the study rewrites)."""
    return IC.ios_constants()


def ios_features(rows: pd.DataFrame, timing: pd.DataFrame) -> tuple[dict, dict]:
    constants = IC.current()
    chosen, typ = IC.ios_constants(constants)
    short_h = IC.short_h(constants)      # the short-memory IOS points matchup (from Stage B's diagnostic rows)
    means = B.surface_means()
    stats = tuple(dict.fromkeys(("spw",) + PROFILE_IOS))
    sa = B.stat_arrays(rows, means, stats)
    tm = timing.set_index("match_id")
    es = rows["match_id"].map(tm["es"]).to_numpy(dtype=float)
    lf = rows["match_id"].map(tm["lf"]).to_numpy(dtype=float)
    obs = rows["match_id"].map(tm["obs"]).to_numpy(dtype=float)
    if not (np.isfinite(es).all() and np.isfinite(lf).all() and np.isfinite(obs).all()):
        raise ValueError("Every match needs es, lf and obs in timing.parquet")
    inputs = {}
    for t in C.TOURS:
        td = IT.tour_inputs(rows, sa, typ, t, stats)
        td = _LLEIOS.annotate_td(td, rows)  # lower_level_evidence C2 (sandbox only)
        idx = td["idx"]
        inputs[t] = {"td": td, "es": es[idx], "lf": lf[idx], "obs": obs[idx]}
    tasks = [(t, s, chosen[(t, s)]["h"], chosen[(t, s)]["kappa"], chosen[(t, s)]["tau"], "tuned")
             for t in C.TOURS for s in PROFILE_IOS]
    tasks += [(t, "spw", short_h[t], chosen[(t, "spw")]["kappa"], chosen[(t, "spw")]["tau"], "short") for t in C.TOURS]
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init, initargs=(inputs,)) as ex:
        for r in ex.map(_ios_task, tasks, chunksize=1):
            res[(r["tour"], r["stat"], r["label"])] = r
            MT.log(f"  IOS {r['tour']} {r['stat']} ({r['label']}): {r['seconds']}s, {r['solver']['snapshots']:,} daily "
                   f"snapshots, mean PCG iterations {r['solver']['iterations_mean']:.1f}, "
                   f"not converged {r['solver']['not_converged']}")
    O, D = {}, {}
    for (t, s, label), r in res.items():
        if r["solver"]["not_converged"]:
            raise RuntimeError(f"IOS solve failed to converge: {t} {s} {label}")
        key = (s, label)
        O.setdefault(key, np.full(len(rows), np.nan))[inputs[t]["td"]["idx"]] = r["O"]
        D.setdefault(key, np.full(len(rows), np.nan))[inputs[t]["td"]["idx"]] = r["D"]
    A, Bi = B.pool_rows(rows)
    out = {}
    for s in PROFILE_IOS:
        o, d = O[(s, "tuned")], D[(s, "tuned")]
        out[f"ios_O_{s}|single"] = o[A] - o[Bi]
        out[f"ios_D_{s}|single"] = d[A] - d[Bi]
        out[f"prod_{s}|single"] = o[A] * (-d[Bi]) - o[Bi] * (-d[A])
    out["ios_short"] = I.matchup_points(RF.schedule_rows(rows), sa, O[("spw", "short")], D[("spw", "short")])
    meta = {f"{t}|{s}|{label}": {**r["solver"], "seconds": r["seconds"]} for (t, s, label), r in res.items()}
    return out, meta


# ------------------------------------------------------------------------------------------------

PERPLAYER = MT.OUT / "perplayer_features.parquet"     # the timing-independent part, cached
IOSFEAT = MT.OUT / "ios_features.parquet"             # the timing-dependent part


def features_from_tables(matches: pd.DataFrame, players: pd.DataFrame, odds: pd.DataFrame, timing: pd.DataFrame,
                         with_ios: bool = True, per_player: bool = True) -> pd.DataFrame:
    """Every input for the pool matches of the given tables (the probe calls this on slices of history, with some
    results changed). Same steps as main(): repair corrections, rows, ratings, per-player inputs, IOS on ``timing``."""
    matches, players, _ = repair_tables(matches, players)
    rows = build_rows(matches, players, odds)
    A, Bi = B.pool_rows(rows)
    frame = rows.iloc[A][["match_id"]].reset_index(drop=True).copy()
    if per_player:
        rows, _, _ = H.rebuild_ratings(rows)
        frame["p_elo"] = rows.p_elo_a.to_numpy()[A]
        frame["rating_matchup|single"] = RF.rating_matchup(rows)
        frame = frame.assign(**RF.context_features(rows))
        ek, _, _ = H.frozen_constants()
        sc = pd.read_csv(B.STAGE4_CONSTANTS)
        sc = sc[sc.kind.eq("weighted Elo scale") & sc.stat.eq("elo_games")]
        frame["elo_games|single"] = RF.games_elo(rows, ek, dict(zip(sc.tour, sc.value)))
        frame["mu_points|52 weeks"] = points_52w(rows)
        means = B.surface_means()
        chosen, typ, mad = AP.load_frozen()
        frame = frame.assign(**RF.adjperf_features(rows, means, chosen, typ, mad))
    if with_ios:
        ios, _ = ios_features(rows, timing)
        frame = frame.assign(**ios)
    return frame


def load_full_rows() -> tuple[pd.DataFrame, int, dict]:
    MT.log("loading matches, players and odds; applying the repair's data corrections")
    matches = C.load_matches()
    players = pd.read_parquet(C.MATCH_PLAYERS)
    odds = pd.read_parquet(E.ODDS)
    matches, players, data_audit = repair_tables(matches, players)
    rows = build_rows(matches, players, odds)
    del players
    gc.collect()
    MT.log(f"rows: {len(rows):,} player-matches; box history eligible "
           f"{int(rows['box_hist'].sum()):,}; ITF/team own-score standard "
           f"{int((rows['history_format_reason'] == 'own_score_standard').sum()):,}")
    return rows, len(matches), data_audit


def part_ios() -> dict:
    """The solved-together inputs on the current timing.parquet (rerun whenever the timeline changes)."""
    start = time.time()
    constants = IC.pin()                 # one version for the whole part, whatever the registry's pointer does meanwhile
    MT.log(f"IOS constants {constants['id']} ({constants['sha256'][:12]}, {constants['selected_by']})")
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"])
    rows, _, _ = load_full_rows()
    A, _ = B.pool_rows(rows)
    ios, ios_meta = ios_features(rows, timing)
    frame = pd.DataFrame({"match_id": rows["match_id"].to_numpy()[A], **ios})
    frame.to_parquet(IOSFEAT, index=False, compression="zstd")
    meta = {"ios": ios_meta, "ios_constants": IC.record(constants), "timing_input_sha256": MT.sha256(MT.TIMING),
            "seconds": round(time.time() - start, 1)}
    meta = _LLEIOS.stamp(meta)  # lower_level_evidence C2 (sandbox only)
    MT.jdump(meta, MT.OUT / "ios_features_summary.json")
    MT.log(f"wrote {IOSFEAT.name}")
    return meta


def part_merge() -> int:
    per = pd.read_parquet(PERPLAYER)
    ios = pd.read_parquet(IOSFEAT)
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "exact", "window_basis"])
    if not per["match_id"].equals(ios["match_id"]):
        raise ValueError("per-player and IOS parts are not in the same pool order")
    frame = pd.concat([per, ios.drop(columns="match_id")], axis=1).merge(timing, on="match_id", how="left")
    frame.to_parquet(MT.FEATURES, index=False, compression="zstd")
    cols = [c for c in frame.columns if "|" in c or c == "ios_short"]
    summary = json.loads((MT.OUT / "perplayer_features_summary.json").read_text(encoding="utf-8"))
    summary.update({"ios": json.loads((MT.OUT / "ios_features_summary.json").read_text(encoding="utf-8")),
                    "features": cols, "pool_matches": len(frame),
                    "coverage": {c: float(np.isfinite(frame[c].to_numpy(dtype=float)).mean()) for c in cols},
                    "output_sha256": MT.sha256(MT.FEATURES)})
    MT.jdump(summary, MT.OUT / "leakproof_features_summary.json")
    MT.log(f"wrote {MT.FEATURES.name}: {len(frame):,} pool matches, {len(cols)} inputs")
    return 0


def main() -> int:
    part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else "all"
    MT.OUT.mkdir(parents=True, exist_ok=True)
    if part == "ios":
        part_ios()
        return 0
    if part == "merge":
        return part_merge()
    start = time.time()
    rows, n_matches, data_audit = load_full_rows()
    rows, ratings, rating_meta = H.rebuild_ratings(rows)
    MT.log(f"Elo and serve/return ratings rebuilt ({rating_meta['rating_updates']:,} rating updates)")
    A, Bi = B.pool_rows(rows)
    meta_cols = ["match_id", "tour", "year", "evaluation", "a_won", "group", "status", "order", "tournament_id",
                 "tournament_date", "level", "qualifying", "round", "round_order", "surface", "tournament_name"]
    frame = rows.iloc[A][[c for c in meta_cols if c in rows]].reset_index(drop=True).copy()
    frame["p_elo"], frame["p_mkt"] = rows.p_elo_a.to_numpy()[A], rows.p_mkt_a.to_numpy()[A]
    frame["rating_matchup|single"] = RF.rating_matchup(rows)
    frame = frame.assign(**RF.context_features(rows))
    ek, _, _ = H.frozen_constants()
    sc = pd.read_csv(B.STAGE4_CONSTANTS)
    sc = sc[sc.kind.eq("weighted Elo scale") & sc.stat.eq("elo_games")]
    frame["elo_games|single"] = RF.games_elo(rows, ek, dict(zip(sc.tour, sc.value)))
    MT.log("ratings, load, surface, age and games-weighted Elo built")
    frame["mu_points|52 weeks"] = points_52w(rows)
    MT.log("52-week points matchup built")
    means = B.surface_means()
    chosen, typ, mad = AP.load_frozen()
    frame = frame.assign(**RF.adjperf_features(rows, means, chosen, typ, mad))
    gc.collect()
    MT.log("adjperf/adjdef profile and total-points form built")
    frame.to_parquet(PERPLAYER, index=False, compression="zstd")
    feature_cols = [c for c in frame.columns if "|" in c]
    summary = {"pool_matches": len(frame), "history_matches": n_matches, "per_player_features": feature_cols,
               "data_repairs": {k: v for k, v in data_audit.items() if not isinstance(v, list)},
               "ratings": rating_meta,
               "box_history": {"eligible_rows": int(rows["box_hist"].sum()),
                               "own_score_standard_rows": int((rows["history_format_reason"] == "own_score_standard").sum())},
               "seconds": round(time.time() - start, 1)}
    MT.jdump(summary, MT.OUT / "perplayer_features_summary.json")
    MT.log(f"wrote {PERPLAYER.name}: {len(frame):,} pool matches, {len(feature_cols)} per-player inputs")
    if part == "all":
        del rows
        gc.collect()
        part_ios()
        return part_merge()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
