"""Fixed, market-free predictive frontier features on repaired dated history.

The rolling states below use STRICTLY EARLIER DAYS: every forecast on a day is
emitted before any observation from that day updates a state. The supplied
pre-match SR/Elo ratings retain the repaired upstream policy (earlier dates plus
strictly earlier same-event rounds). No current score, status, box availability,
or market quote enters a forecast. Constants are fixed before outcome testing.

Run: ./python.sh -m src.eda.predictive_frontier.features
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
REPAIRS = ROOT / "data/studies/feature_alpha_audit/repairs"
OUT = ROOT / "data/studies/predictive_frontier"
FEATURES = OUT / "frontier_features.parquet"
HALF_LIVES = np.array([28., 182.])
POINT_PRIOR = 200.
SURFACE_PRIOR = 400.
EVENT_PRIOR = 800.
RETIREMENT_PRIOR = 5.

FEATURE_GROUPS = {
    "innovations": ["pf_serve_28", "pf_return_28", "pf_serve_182", "pf_return_182",
                    "pf_serve_momentum", "pf_return_momentum", "pf_box_seen_diff",
                    "pf_box_unknown_elo"],
    "surface_specialization": ["pf_surface_serve", "pf_surface_return",
                               "pf_surface_evidence_diff", "pf_surface_unknown_elo"],
    "reliability": ["pf_evidence_diff", "pf_uncertainty_elo", "pf_uncertainty_sr",
                    "pf_instability_diff", "pf_instability_elo"],
    "recovery": ["pf_rest_diff", "pf_inactivity_elo", "pf_retired_loss_recent",
                 "pf_retired_loss_rate", "pf_history_seen_diff", "pf_history_unknown_elo"],
    "event_speed": ["pf_event_speed_style", "pf_event_speed_elo",
                    "pf_event_evidence_style", "pf_event_unknown_elo"],
}
FEATURE_COLUMNS = [name for group in FEATURE_GROUPS.values() for name in group]
DEFINITIONS = {
    "innovations": "Serve wins minus n*expit(mu+own serve-opponent return); return wins minus n*(1-expit(mu+opponent serve-own return)). Each player/channel has exponentially decayed sums S,N at 28 and 182 days; S/(N+200), plus short-minus-long. Box-seen difference and mean unknown indicator times Elo distinguish no observed eligible history from neutral residuals.",
    "surface_specialization": "182-day surface mean partially pooled toward global innovation: (S_surface+400*global)/(N_surface+400)-global. Unknown surface is neutral with coverage control. Surface evidence difference uses log1p of serve+return points; mean absence of surface observations interacts with Elo.",
    "reliability": "182-day observed eligible point exposure log1p difference; symmetric mean 400/(400+serve+return exposure) times Elo logit and SR strength. Excess residual dispersion estimates max(0,[sum n*(observed rate-expected)^2 - expected*(1-expected)]/(N+200) - pooled mean^2); channel sum gives difference and symmetric interaction with Elo. This approximates binomial-noise correction, not calibrated posterior uncertainty.",
    "recovery": "Observed prior completed/retired matches only. Rest is log1p(min(days since last observed played match,365)); absence score clip((gap-28)/154,0,1) interacts symmetrically with Elo. Last observed retired loss decays at 28 days; 182-day retired-loss count/(played count+5) supplies recurrent observation rate. History coverage remains explicit. Rest/absence describe the restricted dated universe, not verified inactivity or injury.",
    "event_speed": "Current-edition prior-day service residual total/(service points+800), multiplied by signed serve-versus-return style contrast and Elo logit. Current edition keys include tour,tournament_id,surface. Evidence fraction N/(N+800) times style and event-unobserved times Elo distinguish neutral and unknown conditions. This is an inferred playing-condition proxy, not measured court speed.",
}


def _validate(rows: pd.DataFrame) -> None:
    required = {"match_id", "side", "tour", "player_id", "day", "surface", "tournament_id",
                "status", "won", "spw_n", "spw_d", "history_format_supported", "serve_own",
                "return_own", "mu_logit", "p_elo_a"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if len(rows) % 2 or not rows.side.iloc[::2].eq("A").all() or not rows.side.iloc[1::2].eq("B").all():
        raise ValueError("Expected adjacent A,B rows")
    if not np.array_equal(rows.match_id.to_numpy()[::2], rows.match_id.to_numpy()[1::2]):
        raise ValueError("A/B pair match IDs differ")
    if rows.match_id.iloc[::2].duplicated().any():
        raise ValueError("Duplicate match IDs")
    day = rows.day.to_numpy(dtype=float)
    if not np.isfinite(day).all() or np.any(np.diff(day) < 0) or np.any(day != np.floor(day)):
        raise ValueError("Expected sorted integer provider match days")
    for column in ("day", "tour", "surface", "tournament_id", "p_elo_a", "status", "history_format_supported"):
        a, b = rows[column].iloc[::2].reset_index(drop=True), rows[column].iloc[1::2].reset_index(drop=True)
        if not a.equals(b):
            raise ValueError(f"A/B pair metadata differs: {column}")
    if rows[["tour", "player_id", "match_id", "tournament_id"]].isna().any().any():
        raise ValueError("Missing identity metadata")
    if (rows.player_id.to_numpy()[::2] == rows.player_id.to_numpy()[1::2]).any():
        raise ValueError("A player cannot oppose themselves")
    rating = rows[["serve_own", "return_own", "mu_logit", "p_elo_a"]].to_numpy(dtype=float)
    if not np.isfinite(rating).all() or not ((rating[:, 3] > 0) & (rating[:, 3] < 1)).all():
        raise ValueError("Pre-match ratings must be finite with interior Elo probabilities")


def build_features(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return one row per input match plus immutable-definition/coverage metadata.

    Only match-level output is returned; side orientation follows input A/B.
    Every numeric feature reverses sign when all A/B labels are exchanged.
    """
    rows = rows.reset_index(drop=True)
    _validate(rows)
    n = len(rows)
    if not n:
        return pd.DataFrame(columns=["match_id", *FEATURE_COLUMNS]), {"matches": 0}
    mate = np.arange(n) ^ 1
    pc, players = pd.factorize(pd.MultiIndex.from_frame(rows[["tour", "player_id"]]))
    surface = rows.surface.astype("string").fillna("unknown").to_numpy(dtype=str)
    surface_known = np.isin(surface, ["Hard", "Clay", "Grass", "Carpet"])
    sc, surfaces = pd.factorize(pd.MultiIndex.from_arrays([pc, surface]))
    ec, events = pd.factorize(pd.MultiIndex.from_arrays([rows.tour, rows.tournament_id, surface]))
    day = rows.day.to_numpy(dtype=int)
    serve = rows.serve_own.to_numpy(dtype=float)
    ret = rows.return_own.to_numpy(dtype=float)
    expected_serve = expit(rows.mu_logit.to_numpy(dtype=float) + serve - ret[mate])
    # Derived mirror is consistent even when source rpw fields were absent.
    points = np.column_stack([rows.spw_d.to_numpy(dtype=float), rows.spw_d.to_numpy(dtype=float)[mate]])
    wins = np.column_stack([rows.spw_n.to_numpy(dtype=float),
                            rows.spw_d.to_numpy(dtype=float)[mate] - rows.spw_n.to_numpy(dtype=float)[mate]])
    expected = np.column_stack([expected_serve, 1 - expected_serve[mate]])
    valid = np.isfinite(points).all(axis=1) & np.isfinite(wins).all(axis=1)
    valid &= (points > 0).all(axis=1) & (wins >= 0).all(axis=1) & (wins <= points).all(axis=1)
    primitive = [c for c in ("ace", "df", "svpt", "first_in", "first_won", "second_won",
                              "sv_gms", "bp_saved", "bp_faced") if c in rows]
    if primitive:
        raw = rows[primitive].to_numpy(dtype=float)
        invalid_raw = ((raw < 0) | np.isinf(raw)).any(axis=1)
        valid &= ~invalid_raw & ~invalid_raw[mate]
    valid &= rows.status.eq("completed").to_numpy() & rows.history_format_supported.to_numpy(dtype=bool)
    valid &= valid[mate]  # Drop both sides of every unusable box.
    played = rows.status.isin(["completed", "retired"]).to_numpy()
    retired_loss = rows.status.eq("retired").to_numpy() & ~rows.won.to_numpy(dtype=bool)

    # Each player has (half-life, channel) residual and exposure arrays. A state
    # is lazily aged to the FORECAST day, including a long gap with no matches.
    residual = np.zeros((len(players), 2, 2))
    exposure = np.zeros_like(residual)
    dispersion = np.zeros((len(players), 2))
    player_clock = np.full(len(players), day[0], dtype=int)
    surface_residual = np.zeros((len(surfaces), 2))
    surface_exposure = np.zeros_like(surface_residual)
    surface_clock = np.full(len(surfaces), day[0], dtype=int)
    event_residual, event_exposure = np.zeros(len(events)), np.zeros(len(events))
    has_box = np.zeros(len(players), dtype=bool)
    has_surface = np.zeros(len(surfaces), dtype=bool)
    last_played = np.full(len(players), -1, dtype=int)
    last_retired_loss = np.zeros(len(players), dtype=bool)
    played_count, retired_count = np.zeros(len(players)), np.zeros(len(players))

    # Per-side snapshots. Symmetric uncertainty is combined with signed current
    # strength only after all snapshots are produced.
    innov = np.zeros((n, 2, 2))
    specialize = np.zeros((n, 2))
    history = np.zeros((n, 12))
    event = np.zeros((n, 3))
    boundaries = np.r_[0, np.flatnonzero(np.diff(day)) + 1, n]
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        current = day[start]
        active_p = np.unique(pc[start:stop])
        factors = np.exp2(-(current - player_clock[active_p])[:, None] / HALF_LIVES)
        residual[active_p] *= factors[:, :, None]
        exposure[active_p] *= factors[:, :, None]
        dispersion[active_p] *= factors[:, 1, None]
        played_count[active_p] *= factors[:, 1]
        retired_count[active_p] *= factors[:, 1]
        player_clock[active_p] = current
        active_s = np.unique(sc[start:stop])
        sf = np.exp2(-(current - surface_clock[active_s]) / HALF_LIVES[1])
        surface_residual[active_s] *= sf[:, None]
        surface_exposure[active_s] *= sf[:, None]
        surface_clock[active_s] = current

        # Snapshot every row before the day's first update, independent of row
        # order or same-day event/round identity.
        for i in range(start, stop):
            p, s, e = pc[i], sc[i], ec[i]
            pooled = residual[p] / (exposure[p] + POINT_PRIOR)
            innov[i] = pooled
            surface_mean = (surface_residual[s] + SURFACE_PRIOR * pooled[1]) / (surface_exposure[s] + SURFACE_PRIOR)
            specialize[i] = (surface_mean - pooled[1]) if surface_known[i] else 0.
            n_long = exposure[p, 1].sum()
            excess = np.maximum(0., dispersion[p] / (exposure[p, 1] + POINT_PRIOR) - pooled[1] ** 2).sum()
            seen = last_played[p] >= 0
            gap = float(current - last_played[p]) if seen else 0.
            history[i] = [float(has_box[p]), np.log1p(n_long), 2 * POINT_PRIOR / (2 * POINT_PRIOR + n_long),
                          excess, np.log1p(surface_exposure[s].sum()) if surface_known[i] else 0.,
                          float(has_surface[s] and surface_known[i]),
                          np.log1p(min(gap, 365.)) if seen else 0.,
                          np.clip((gap - 28.) / 154., 0., 1.) if seen else 0.,
                          float(last_retired_loss[p]) * np.exp2(-gap / HALF_LIVES[0]) if seen else 0.,
                          retired_count[p] / (played_count[p] + RETIREMENT_PRIOR), float(seen), n_long]
            event[i] = [event_residual[e] / (event_exposure[e] + EVENT_PRIOR),
                        event_exposure[e] / (event_exposure[e] + EVENT_PRIOR), float(event_exposure[e] > 0)]

        # Aggregate updates only after all same-day forecasts. Repeated same-day
        # players have ambiguous final observed status: OR the retired losses.
        for i in range(start, stop):
            p, s, e = pc[i], sc[i], ec[i]
            if played[i]:
                last_retired_loss[p] = retired_loss[i] if last_played[p] != current else (last_retired_loss[p] or retired_loss[i])
                last_played[p] = current
                played_count[p] += 1.
                retired_count[p] += float(retired_loss[i])
            if not valid[i]:
                continue
            error = wins[i] - points[i] * expected[i]
            residual[p] += error[None, :]
            exposure[p] += points[i][None, :]
            dispersion[p] += error ** 2 / points[i] - expected[i] * (1 - expected[i])
            has_box[p] = True
            if surface_known[i]:
                surface_residual[s] += error
                surface_exposure[s] += points[i]
                has_surface[s] = True
            # Each side contributes only its own service observation once.
            event_residual[e] += error[0]
            event_exposure[e] += points[i, 0]

    a, b = np.arange(0, n, 2), np.arange(1, n, 2)
    diff = lambda arr: arr[a] - arr[b]
    avg = lambda arr: (arr[a] + arr[b]) / 2
    strength = logit(np.clip(rows.p_elo_a.to_numpy(dtype=float)[a], 1e-6, 1 - 1e-6))
    sr_strength = diff(serve + ret)
    style = diff(serve - ret)
    d = {"match_id": rows.match_id.to_numpy()[a]}
    for channel, label in enumerate(("serve", "return")):
        d[f"pf_{label}_28"] = diff(innov[:, 0, channel])
        d[f"pf_{label}_182"] = diff(innov[:, 1, channel])
        d[f"pf_{label}_momentum"] = diff(innov[:, 0, channel] - innov[:, 1, channel])
        d[f"pf_surface_{label}"] = diff(specialize[:, channel])
    d.update({"pf_box_seen_diff": diff(history[:, 0]), "pf_box_unknown_elo": (1 - avg(history[:, 0])) * strength,
              "pf_surface_evidence_diff": diff(history[:, 4]), "pf_surface_unknown_elo": (1 - avg(history[:, 5])) * strength,
              "pf_evidence_diff": diff(history[:, 1]), "pf_uncertainty_elo": avg(history[:, 2]) * strength,
              "pf_uncertainty_sr": avg(history[:, 2]) * sr_strength, "pf_instability_diff": diff(history[:, 3]),
              "pf_instability_elo": avg(history[:, 3]) * strength,
              "pf_rest_diff": diff(history[:, 6]), "pf_inactivity_elo": avg(history[:, 7]) * strength,
              "pf_retired_loss_recent": diff(history[:, 8]), "pf_retired_loss_rate": diff(history[:, 9]),
              "pf_history_seen_diff": diff(history[:, 10]), "pf_history_unknown_elo": (1 - avg(history[:, 10])) * strength,
              "pf_event_speed_style": event[a, 0] * style, "pf_event_speed_elo": event[a, 0] * strength,
              "pf_event_evidence_style": event[a, 1] * style, "pf_event_unknown_elo": (1 - event[a, 2]) * strength})
    frame = pd.DataFrame(d)[["match_id", *FEATURE_COLUMNS]]
    if not np.isfinite(frame[FEATURE_COLUMNS].to_numpy()).all():
        raise RuntimeError("Feature construction produced a nonfinite value")
    coverage = pd.DataFrame({"tour": rows.tour.to_numpy()[a], "year": pd.to_datetime(day[a], unit="D").year,
                             "matches": 1, "eligible_current_boxes": valid[a].astype(int),
                             "both_box_histories": (history[a, 0] * history[b, 0]).astype(int),
                             "both_surface_histories": (history[a, 5] * history[b, 5]).astype(int),
                             "prior_event_box": event[a, 2].astype(int),
                             "both_observed_played_histories": (history[a, 10] * history[b, 10]).astype(int)})
    meta = {"matches": len(frame), "player_rows": n, "feature_groups": FEATURE_GROUPS,
            "constants": {"half_life_days": HALF_LIVES.tolist(), "point_prior": POINT_PRIOR,
                          "surface_prior": SURFACE_PRIOR, "event_prior": EVENT_PRIOR,
                          "retirement_prior": RETIREMENT_PRIOR},
            "definitions": DEFINITIONS,
            "history_policy": "New rolling states: strictly earlier provider dates, including same-event exclusion on forecast day. Upstream supplied pre-match ratings retain repaired same-event strictly-earlier-round allowance.",
            "outcome_blind_forecast": "Current score, won/status, point counts, box validity and market quote are read for later updates only. No market input is used anywhere.",
            "missingness": "Neutral zero innovation/no observed event; every family has coverage/exposure or unknown-by-strength controls. Flags reverse sign or multiply signed current strength. Equal unknown players at zero strength cannot produce directional advantage.",
            "coverage_by_tour_year": coverage.groupby(["tour", "year"], sort=True).sum().reset_index().to_dict("records"),
            "limitations": ["Provider match dates are not exact end times.",
                            "Upstream repaired dates omit most ATP 2018 matches; new rolling states decay across that observation gap.",
                            "Observed rest and retirement outcomes are neither complete workload nor diagnoses.",
                            "No longitudinal injury records or measured court/weather conditions are added.",
                            "2026 history is partial and prior periods have already been inspected."]}
    return frame, meta


def main() -> int:
    started = time.time()
    source = REPAIRS / "repair_rows.parquet"
    pool_path = REPAIRS / "repair_features.parquet"
    rows = pd.read_parquet(source)
    print(f"Building frontier features from {len(rows):,} repaired player rows", flush=True)
    frame, meta = build_features(rows)
    pool = pd.read_parquet(pool_path, columns=["match_id"])
    if pool.match_id.duplicated().any():
        raise ValueError("Repaired feature pool contains duplicate matches")
    frame = pool.merge(frame, on="match_id", how="left", validate="one_to_one", sort=False)
    if frame[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("A repaired pool match has no frontier features")
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(FEATURES, index=False, compression="zstd")
    meta.update({"pool_matches": len(frame), "pool_order_exact": frame.match_id.equals(pool.match_id),
                 "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, pool_path)},
                 "output": str(FEATURES.relative_to(ROOT)), "output_sha256": hashlib.sha256(FEATURES.read_bytes()).hexdigest(),
                 "seconds": round(time.time() - started, 2)})
    (OUT / "frontier_features_summary.json").write_text(json.dumps(meta, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {len(frame):,} matches / {len(FEATURE_COLUMNS)} features in {meta['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
