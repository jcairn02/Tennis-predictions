"""Step 7, predict: stage 2 on the price grid, the prediction file and its provenance.

Stage 2 (docs/decisions/2026-10-08-current-best-model.md, "Stage 2"; adaptive/adjust.apply, every match in mode L):
    logit q = s_tour,Y * eta + b_Y * spd_L
    eta     logit of the 16-seed mean of the symmetrised forecasts (dp_fit), at each grid price and at the own price
    spd_L   the two men's 28-day first-serve-speed forms on the match's day, from the live speed panel's rows released
            by then (serve_speed_tabpfn/live/form.py; live_panel.load(): the history plus the daily rows); 0 for women
    s, b    walk_forward on the instance's own seeds 0-3 forecasts of 2019 .. Y - 1, debut seasons out, b shrunk with
            tau 0.05 (current_best_model/compare.walk_forward, the decided fit), on the weekly feed's history column
            spd_L_B of the decided speed history (the corrected history plus the ATP backfill:
            infosys_atp_backfill/speed_columns_augmented.parquet, which covers every frame match of 2019-2025). They read
            the results of 2019 .. Y - 1 (the decided procedure); computed once per instance and season, cached in
            data/studies/daily_prediction/stage2/
    + b z   the combined-pattern adjustment (unpriced_leads/patterns_live.py; rules docs/studies/unpriced_leads/
            check_now_rules.md; switched on by the owner on 13 Oct 2026), added to the log-odds above. q_a is the
            prediction used. predictions.csv says both versions after it: q_a_patterns_off (stage 2 without the
            patterns), q_a_patterns_on (with them; empty while the switch is off), patterns ("on" / "off"),
            pattern_applied (False where the match has no score), pattern_shift (b z, log-odds) and pattern_z.
            curves.parquet carries q_a_patterns_off beside q_a; provenance.json gains stage2.patterns while on.
Writes <run>/predictions.csv (one row per match: identity, the price, eta, spd_L, q at the own price, the gate),
<run>/curves.parquet (each match at every grid price: the price, eta, q: a re-price is a lookup) and
<run>/provenance.json (what a re-price must find unchanged).
Every "_a" figure (p_market_a, p_base_a, q_a, a re-price's p_a) is the chance of Stage 0's side A: player_a_id, whose
name is player_a. Both names come from Stage 0's own player rows by side (dp_steps.side_names), never from the
matchups CSV, whose player_a is side B whenever its id sorts higher (fixed 11 Oct 2026: the CSV's names had been
written beside side A's figures unswapped).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC
import dp_fit as FT

SPEED_COLUMN = DC.REPO / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
STAGE2 = DC.OUT / "stage2"


def _mods():
    import sys
    if str(DC.REPO) not in sys.path:
        sys.path.insert(0, str(DC.REPO))
    from src.eda.current_best_model import compare as CMP
    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.serve_speed_tabpfn.adaptive import adjust as ADJ
    return CMP, FITS, C, ADJ


def coefficients(season: int, instance: Path = DC.INSTANCE) -> dict:
    """s_atp, s_wta, b_shrunk (and b, se_b) of season Y for the instance, from its seeds 0-3 of 2019 .. Y - 1."""
    CMP, FITS, C, _ = _mods()
    P = FITS.paths(instance)
    keys = {"instance": str(instance), "frame_sha256": C.sha256_file(P.model_frame),
            "speed_column": str(SPEED_COLUMN), "speed_column_sha256": C.sha256_file(SPEED_COLUMN), "season": season}
    path = STAGE2 / f"{instance.name}_{season}.json"
    if path.exists():
        held = DC.read_json(path)
        if held.get("keys") == keys:
            return held
    frame = CMP.inputs_frame(P)
    seasons = list(range(2019, season))
    y = CMP.outcomes(P, through=season - 1)
    p = CMP.seed_table(P, frame, seasons)
    ids = frame.index[frame["season"].between(2019, season - 1).to_numpy()]
    info = frame.loc[ids, ["tour", "season", "debut_season"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    if info["y"].isna().any():
        raise RuntimeError("a result of 2019 .. Y - 1 is missing")
    eta = pd.Series(C.lg(p.reindex(ids).mean(axis=1).to_numpy()), index=ids)
    z = pd.read_parquet(SPEED_COLUMN, columns=["match_id", "spd_L_B"]).astype({"match_id": str})
    z = z.set_index("match_id")["spd_L_B"]
    s_atp, s_wta, b_shrunk, b, se_b = CMP.walk_forward(eta, info, z, (season,))[season]
    out = {"keys": keys, "s_atp": s_atp, "s_wta": s_wta, "b_shrunk": b_shrunk, "b_mle": b, "se_b": se_b,
           "fit": "current_best_model/compare.walk_forward: 2019 .. Y - 1, seeds 0-3 mean, debut seasons out, "
                  "b shrunk with tau 0.05", "matches": int((~info["debut"]).sum()), "computed_at": DC.stamp()}
    DC.write_json(path, out)
    return out


def patterns(run_dir: Path, ids) -> dict | None:
    """The combined-pattern adjustment's z and shift for the run's matches; None while it is off."""
    import sys
    if str(DC.REPO) not in sys.path:
        sys.path.insert(0, str(DC.REPO))
    from src.eda.unpriced_leads import patterns_live as PL
    out = PL.for_run(run_dir, ids)
    if out is not None:
        out["shift_fn"] = PL.shift
    return out


def speed_columns(meta: pd.DataFrame, days: np.ndarray) -> tuple[np.ndarray, dict]:
    """spd_L of each live match on its day (side A minus side B), 0 for women."""
    from src.eda.serve_speed_tabpfn.live import form as SF
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    panel = LP.load()
    out = np.zeros(len(meta))
    men = meta["tour"].eq("atp").to_numpy()
    for d in sorted(set(days[men].tolist())):
        sel = men & (days == d)
        players = sorted(set(meta.loc[sel, "player_a_id"]) | set(meta.loc[sel, "player_b_id"]))
        form = SF.form_as_of(int(d), panel, players=players)
        out[sel] = SF.spd_L_from_form(form, meta.loc[sel, "player_a_id"].to_numpy(), meta.loc[sel, "player_b_id"].to_numpy())
    return out, {"panel": str(LP.LC.OUT / LP.LC.PANEL_LIVE.name), "panel_sha256": DC.sha256(LP.LC.OUT / LP.LC.PANEL_LIVE.name),
                 "standardiser_km_h": float(SF.SD_L), "clip": float(SF.CLIP)}


def run(run_dir: Path, seeds: list[int], instance: Path = DC.INSTANCE, checkpoint: str | None = None) -> dict:
    CMP, FITS, C, ADJ = _mods()
    d = FT.load(run_dir, seeds)
    ids = d["match_id"]
    meta = pd.read_parquet(run_dir / "live_meta.parquet").astype({"match_id": str}).set_index("match_id").loc[ids]
    s0 = pd.read_parquet(run_dir / "live_stage0.parquet").astype({"match_id": str}).set_index("match_id").loc[ids]
    if not {"player_a_name", "player_b_name"} <= set(s0.columns):
        raise RuntimeError("live_stage0.parquet has no side names (written before 11 Oct 2026): run the states step "
                           "again; the matchups CSV's names are never used (they may be the other side's)")
    meta = meta.drop(columns=["player_a", "player_b"], errors="ignore").join(
        s0[["player_a_id", "player_b_id", "player_a_name", "player_b_name"]])
    days = np.array([DC.day_of(x) for x in meta["day"]], dtype=np.int64)
    seasons = pd.to_datetime(meta["day"]).dt.year.to_numpy()
    pg, po = d["grid"].mean(axis=0), d["own"].mean(axis=0)
    eta_g, eta_o = C.lg(pg), C.lg(po)
    coef = {"L_weekly": {}}
    rec_coef = {}
    for Y in sorted(set(seasons.tolist())):
        c = coefficients(int(Y), instance)
        coef["L_weekly"][str(int(Y))] = {"s_atp": c["s_atp"], "s_wta": c["s_wta"], "b_shrunk": c["b_shrunk"]}
        rec_coef[str(int(Y))] = c
    spd, spd_rec = speed_columns(meta.reset_index(), days)
    tour = meta["tour"].to_numpy()
    q_o = ADJ.apply(eta_o, tour, seasons, "L", col_l=spd, coef=coef, feed="weekly")
    n, k = pg.shape
    q_g = ADJ.apply(eta_g.ravel(), np.repeat(tour, k), np.repeat(seasons, k), "L", col_l=np.repeat(spd, k),
                    coef=coef, feed="weekly").reshape(n, k)
    q_o_off, q_g_off = q_o, q_g                  # stage 2 without the combined-pattern adjustment
    pat = patterns(run_dir, ids)                 # None while the adjustment is off
    if pat is not None:
        q_o = pat["shift_fn"](q_o, pat["shift"])
        q_g = pat["shift_fn"](q_g, pat["shift"][:, None])
    gate = pd.read_csv(run_dir / "gate.csv").astype({"match_id": str}).set_index("match_id").reindex(ids)
    pr = pd.read_parquet(run_dir / "prices.parquet").astype({"match_id": str}).set_index("match_id").reindex(ids)
    back = FT.interp(d["own_logit"], pg)
    pred = pd.DataFrame({
        "match_id": ids, "tour": tour, "tournament": meta["tournament_name"].to_numpy(), "round": meta["round"].to_numpy(),
        "player_a_id": meta["player_a_id"].to_numpy(), "player_b_id": meta["player_b_id"].to_numpy(),
        "player_a": meta["player_a_name"].to_numpy(), "player_b": meta["player_b_name"].to_numpy(),
        "day": meta["day"].astype(str).to_numpy(), "price_source": pr["source"].to_numpy(),
        "price_recorded_at": pr["recorded_at"].to_numpy(),
        "price_quoted_at": pr["quoted_at"].to_numpy() if "quoted_at" in pr.columns else None,
        "p_market_a": pr["p_a"].to_numpy(dtype="float64"),
        "p_base_a": po, "eta": eta_o, "p_grid_read_back_a": back, "spd_L": spd, "q_a": q_o,
        # the combined-pattern adjustment, said plainly: q_a is the prediction used (with the patterns when they are
        # on); the two versions beside it, the switch, and the shift (log-odds) and score behind it
        "q_a_patterns_off": q_o_off, "q_a_patterns_on": q_o if pat is not None else np.nan,
        "patterns": "on" if pat is not None else "off",
        "pattern_applied": pat["applied"] if pat is not None else False,
        "pattern_shift": pat["shift"] if pat is not None else 0.0,
        "pattern_z": pat["z_raw"] if pat is not None else np.nan,
        "gate": gate["bet"].to_numpy(), "gate_reason": gate["reason"].to_numpy(),
        "instance": instance.name, "seeds": f"{min(seeds)}-{max(seeds)}", "checkpoint": checkpoint})
    pred.to_csv(run_dir / "predictions.csv", index=False)
    curves = pd.DataFrame({"match_id": np.repeat(ids, k), "odds_logit": np.tile(FT.GRID, n),
                           "p_market_a": 1 / (1 + np.exp(-np.tile(FT.GRID, n))), "p_base_a": pg.ravel(),
                           "eta": eta_g.ravel(), "q_a": q_g.ravel(), "q_a_patterns_off": q_g_off.ravel()})
    curves.to_parquet(run_dir / "curves.parquet", index=False)
    fit = DC.read_json(run_dir / "fit.json")
    states = DC.read_json(run_dir / "states.json") if (run_dir / "states.json").exists() else {}
    prov = {"made_at": DC.stamp(), "instance": str(instance),
            "instance_frame_sha256": fit["frame_sha256"], "instance_inputs_sha256": DC.sha256(instance / "model_inputs.json"),
            "live_frame_sha256": DC.sha256(run_dir / "live_frame.parquet"), "inputs": fit["inputs"],
            "seeds": list(seeds), "tabpfn": fit["versions"],
            "tabpfn_checkpoints": sorted({v["checkpoint"] for v in fit["seeds"].values() if v.get("checkpoint")}),
            "grid": fit["grid"], "stage2": {"coefficients": rec_coef, "speed": spd_rec, "mode": "L", "feed": "weekly"},
            "checkpoint": checkpoint, "state_parts": states.get("record", {}).get("parts"),
            "layer_config_sha256": states.get("layer_config_sha256"), "code": {f.name: DC.sha256(f)
                                                                               for f in sorted(DC.HERE.glob("dp*.py"))}}
    if pat is not None:
        prov["stage2"]["patterns"] = pat["record"]
    DC.write_json(run_dir / "provenance.json", prov)
    return {"matches": int(n), "q_range": [float(q_o.min()), float(q_o.max())],
            "grid_read_back_vs_own_max_abs": float(np.nanmax(np.abs(back - po))) if np.isfinite(back).any() else None}
