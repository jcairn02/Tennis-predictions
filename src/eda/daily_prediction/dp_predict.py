"""Step 7, predict: stage 2 on the price grid, the prediction file and its provenance.

Stage 2 (docs/decisions/2026-10-08-current-best-model.md, "Stage 2"; adaptive/adjust.apply, every match in mode L):
    logit q = s_tour,Y * eta + b_Y * spd_L
    eta     logit of the 16-seed mean of the symmetrised forecasts (dp_fit), at each grid price and at the own price
    spd_L   the two men's 28-day first-serve-speed forms on the match's day, from the live speed panel's rows released
            by then (serve_speed_tabpfn/live/form.py; live_panel.load(): the history plus the daily rows); 0 for women
    s, b    walk_forward on the instance's own seeds 0-3 forecasts of 2019 .. Y - 1, debut seasons out, b shrunk with
            tau 0.05 (current_best_model/compare.walk_forward, the decided fit), on the live speed feed's history column
            of the decided speed history (the corrected history plus the ATP backfill:
            infosys_atp_backfill/speed_columns_augmented.parquet, which covers every frame match of 2019-2025; since
            22 Oct 2026 with the published averages its point record contradicts repaired:
            source_reconciliation/applied/speed_columns_repaired.parquet, reached through a retrain's own table). The feed
            follows each match's day (feed_of): from 8 Oct 2026, the daily collector's first day in the live panel, the
            daily set (spd_L_D: adaptive/adjust's L_daily); before it the weekly set (spd_L_B: L_weekly), as replays of
            earlier days were predicted (the decision's "the speed history that matches the live feed"; the owner,
            14 Oct 2026). They read the results of 2019 .. Y - 1 (the decided procedure); computed once per instance,
            season and feed, cached in data/studies/daily_prediction/stage2/, and reused only while everything they
            were fitted from is unchanged (stage2_keys: the frame, the input list, the seeds 0-3 fit files and the
            TabPFN they were made with, the speed column). A run is refused when its live fit's TabPFN version, weights,
            settings or input list differ from those fits' (check_live_fit): the slope was fitted on their forecasts.
            On a retrain's instance (current_best_model/training_rows: its cut-off admits season-Y matches; the owner,
            20 Oct 2026) the GROWN set is used: the same fit on 2019 .. Y - 1 plus the admitted matches, from season
            Y's walk-forward fit, the speed column the instance's own extended table (in_season_retrain/speed_extend.py);
            predictions.csv adds stage2_set "grown" and q_a_stage2_annual (the local chance with the annual set, no
            patterns), provenance.json both records
    + b z   the combined-pattern adjustment (unpriced_leads/patterns_live.py; rules docs/studies/unpriced_leads/
            check_now_rules.md; switched on by the owner on 13 Oct 2026), added to the log-odds above. q_a is the
            prediction used. predictions.csv says both versions after it: q_a_patterns_off (stage 2 without the
            patterns), q_a_patterns_on (with them; empty while the switch is off), patterns ("on" / "off"),
            pattern_applied (False where the match has no score), pattern_shift (b z, log-odds) and pattern_z.
            curves.parquet carries q_a_patterns_off beside q_a; provenance.json gains stage2.patterns while on.
Thinking    a run made with --thinking (the owner, 20 Oct 2026; docs/decisions/2026-10-20-thinking-beside-local.md):
            TabPFN-3.5-Thinking's chance (dp_thinking: seed 0, symmetrised) takes stage 2's serve-speed term, b_Y * spd_L
            with the local model's coefficients, but never its calibration slope (speed_only; the owner, the evening of
            20 Oct 2026: "should still move with the serve speed numbers ... just not the calibration"), and is averaged
            50/50 in log-odds with the local model's stage-2 chance (log_odds_mean), at the own price and on the grid; the
            patterns, while on, are added to that average's log-odds. q_a, q_a_patterns_off and q_a_patterns_on are then
            the ensemble's, and beside them q_a_local (the local model with the patterns, its prediction in a local run),
            q_a_local_patterns_off, q_a_thinking (Thinking with the speed term), q_a_thinking_api (the API's own chance),
            ensemble ("on", or "off" when the Thinking step failed: the local model alone, the reason in provenance.json's
            thinking) and ensemble_weight_local; curves.parquet carries the four curves too.
Writes <run>/predictions.csv (one row per match: identity, the price, eta, spd_L and its speed_feed, q at the own price,
the gate and the edge bar it sets, gate_edge_bar),
<run>/curves.parquet (each match at every grid price: the price, eta, q: a re-price is a lookup) and
<run>/provenance.json (what a re-price must find unchanged).
Every "_a" figure (p_market_a, p_base_a, q_a, a re-price's p_a) is the chance of Stage 0's side A: player_a_id, whose
name is player_a. Both names come from Stage 0's own player rows by side (dp_steps.side_names), never from the
matchups CSV, whose player_a is side B whenever its id sorts higher (fixed 11 Oct 2026: the CSV's names had been
written beside side A's figures unswapped).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC
import dp_fit as FT

SPEED_COLUMN_BACKFILLED = DC.REPO / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
# the decided column since 22 Oct 2026 (serve_speed_tabpfn/live/live_panel.COLUMN_REPAIRED: the repaired speed history's;
# docs/decisions/2026-10-22-source-reconciliation-repairs.md), present with the repaired history it was built on
SPEED_COLUMN_REPAIRED = DC.REPO / "data" / "studies" / "source_reconciliation" / "applied" / "speed_columns_repaired.parquet"
SPEED_HISTORY_REPAIRED = DC.REPO / "data" / "studies" / "serve_speed_tabpfn" / "live" / "speed_panel_repaired.parquet"
SPEED_COLUMN = SPEED_COLUMN_REPAIRED if SPEED_HISTORY_REPAIRED.exists() else SPEED_COLUMN_BACKFILLED
STAGE2_SPEED = "stage2_speed_columns.parquet"   # an instance's own speed table, extended to its season's matches by its
                                                # retrain (in_season_retrain/speed_extend.py; the owner, 20 Oct 2026)
STAGE2 = DC.OUT / "stage2"
W_LOCAL = 0.5                    # the local model's weight in the ensemble with TabPFN-3.5-Thinking (the owner, 20 Oct 2026)
DAILY_FEED_FROM = "2026-10-08"   # the daily collector's first rows in the live panel (68, collected that day)
FEED_COLUMN = {"weekly": "spd_L_B", "daily": "spd_L_D"}   # each feed's history column (adjust's L_weekly, L_daily)


def _mods():
    import sys
    if str(DC.REPO) not in sys.path:
        sys.path.insert(0, str(DC.REPO))
    from src.eda.current_best_model import compare as CMP
    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.serve_speed_tabpfn.adaptive import adjust as ADJ
    return CMP, FITS, C, ADJ


def feed_of(days) -> np.ndarray:
    """Each match's live speed feed by its day (days since 1970-01-01): "daily" from DAILY_FEED_FROM, "weekly" before."""
    return np.where(np.asarray(days, dtype=np.int64) >= DC.day_of(DAILY_FEED_FROM), "daily", "weekly")


def coef_path(instance: Path, season: int, feed: str, kind: str = "annual") -> Path:
    """A season's record: <instance>_<Y>.json for the weekly set (its name since 10 Oct), <instance>_<Y>_daily.json;
    the grown sets (a retrain's, 20 Oct 2026) <instance>_<Y>_grown.json and <instance>_<Y>_grown_daily.json."""
    tag = "" if kind == "annual" else "_grown"
    return STAGE2 / (f"{instance.name}_{season}{tag}.json" if feed == "weekly"
                     else f"{instance.name}_{season}{tag}_{feed}.json")


def speed_column(instance: Path) -> Path:
    """The history column stage 2 reads for the instance: its own extended table when its retrain wrote one (it keeps
    the decided column's value of every match that column holds, as of that retrain), else the decided column
    (SPEED_COLUMN: the repaired history's since 22 Oct 2026, so an instance without its own table, built before 20 Oct,
    refits stage 2 on it if it is ever used again; the instance in use keeps its own table until the next retrain)."""
    own = Path(instance) / STAGE2_SPEED
    return own if own.exists() else SPEED_COLUMN


def fit_files(season: int, instance: Path, with_season: bool = False) -> list[Path]:
    """The fit files the coefficients are fitted from: the instance's seeds 0-3 of 2019 .. Y - 1 (with_season: also
    season Y's walk-forward fit, whose forecasts of the matches a retrain admits a grown set reads), where
    compare.seed_table finds them."""
    CMP, FITS, _, _ = _mods()
    from src.eda.serve_speed_tabpfn import forecasts as F
    P = FITS.paths(instance)
    return [F.find_fit("model", s, k, P)[1] for s in range(CMP.FIT_FROM, season + int(with_season))
            for k in CMP.SEEDS]


def list_sha256(names) -> str:
    return hashlib.sha256(json.dumps([str(n) for n in names]).encode("utf-8")).hexdigest()


def fits_model(files: list[Path]) -> dict:
    """The model the fit files were made with, one for all of them: the TabPFN version, the weights' file, the settings
    (without the seed) and the input list. torch and the card are listed, not required equal."""
    held, torches, cards = [], set(), set()
    for f in files:
        with np.load(f, allow_pickle=False) as z:
            m = json.loads(str(z["meta"]))
        held.append({"tabpfn": (m.get("versions") or {}).get("tabpfn"),
                     "checkpoint": Path(m["checkpoint"]).name if m.get("checkpoint") else None,
                     "config": {k: v for k, v in (m.get("config") or {}).items() if k != "random_state"},
                     "inputs_sha256": list_sha256(m.get("columns") or [])})
        torches.add(str((m.get("versions") or {}).get("torch")))
        cards.add(str(m.get("device")))
    kinds = {json.dumps(h, sort_keys=True) for h in held}
    if len(kinds) != 1:
        raise RuntimeError(f"{files[0].parent}: the seeds 0-3 fits were made with {len(kinds)} different TabPFN records "
                           "(version, weights, settings or inputs); refit them with one, or stage 2 would mix models")
    one = held[0]
    if one["tabpfn"] is None or one["checkpoint"] is None or not one["config"]:
        raise RuntimeError(f"{files[0].parent}: the fits do not record their TabPFN version, weights and settings, so "
                           "nothing could check that stage 2's coefficients suit the live fit")
    return {**one, "torch": sorted(torches), "devices": sorted(cards)}


def stage2_keys(season: int, instance: Path, feed: str, admitted: list[str] | None = None) -> dict:
    """Everything a season's coefficients are fitted from. A held record is reused only while all of it is unchanged
    (14 Oct 2026; before, only the frame and the speed column were checked, so an input list edited in place, or fits
    redone in the same folder, would have kept the old slope with no error). admitted: the season-Y matches a retrain
    admits (a grown set: their ids' hash and season Y's fits join the keys)."""
    _, FITS, C, _ = _mods()
    from src.eda.current_best_model import training_rows as TR
    P = FITS.paths(instance)
    files = fit_files(season, instance, with_season=bool(admitted))
    h = hashlib.sha256()
    for f in files:
        h.update(f"{f.name}:{DC.sha256(f)}\n".encode("utf-8"))
    col = speed_column(instance)
    keys = {"instance": str(instance), "frame_sha256": C.sha256_file(P.model_frame),
            "inputs_sha256": DC.sha256(P.model_inputs), "fit_files": len(files), "fits_sha256": h.hexdigest(),
            "fits_model": fits_model(files), "feed": feed, "speed_column": str(col),
            "speed_history": FEED_COLUMN[feed], "speed_column_sha256": C.sha256_file(col), "season": season}
    if admitted:
        keys.update({"set": "grown", "admitted": len(admitted), "admitted_sha256": TR.ids_sha256(admitted)})
    return keys


def check_live_fit(fit: dict, rec: dict) -> None:
    """Refuse a run whose live fit is not the model its coefficients were fitted on: the TabPFN version, the weights,
    the settings or the input list differ from the seeds 0-3 fits' (rec["keys"]["fits_model"])."""
    want = rec["keys"]["fits_model"]
    weights = sorted({Path(v["checkpoint"]).name for v in fit["seeds"].values() if v.get("checkpoint")})
    bad = []
    if (fit.get("versions") or {}).get("tabpfn") != want["tabpfn"]:
        bad.append(f"TabPFN {(fit.get('versions') or {}).get('tabpfn')} live, {want['tabpfn']} in the fits")
    if weights != [want["checkpoint"]]:
        bad.append(f"weights {weights} live, {want['checkpoint']} in the fits")
    if dict(fit.get("config") or {}) != want["config"]:
        bad.append(f"settings {fit.get('config')} live, {want['config']} in the fits")
    if list_sha256(fit.get("inputs") or []) != want["inputs_sha256"]:
        bad.append("the live fit's input list is not the fits'")
    if bad:
        raise RuntimeError("the live fit is not the model stage 2's coefficients were fitted on (" + "; ".join(bad)
                           + "): refit the instance's seeds 0-3 with the live TabPFN, or predict with theirs")


def coefficients(season: int, instance: Path = DC.INSTANCE, feed: str = "weekly", grown: bool = True) -> dict:
    """s_atp, s_wta, b_shrunk (and b, se_b) of season Y for the instance and the speed feed, from its seeds 0-3 of
    2019 .. Y - 1 and the feed's history column. When the instance's retrain admits season-Y matches
    (current_best_model/training_rows), the GROWN set (the owner, 20 Oct 2026): fitted on 2019 .. Y - 1 plus those
    matches, from season Y's walk-forward fit (2013 .. Y - 1), by the same fit; grown=False gives the annual set,
    which a grown run logs beside it. A grown set needs every admitted men's match in the speed column (the owner's
    condition 1: the instance's extended table)."""
    if feed not in FEED_COLUMN:
        raise ValueError(f"feed must be one of {sorted(FEED_COLUMN)}")
    CMP, FITS, C, _ = _mods()
    from src.eda.current_best_model import training_rows as TR
    P = FITS.paths(instance)
    admitted = TR.admitted_ids(instance, season) if grown else None
    kind = "grown" if admitted else "annual"
    keys = stage2_keys(season, instance, feed, admitted) if admitted else stage2_keys(season, instance, feed)
    path = coef_path(instance, season, feed, kind)
    if path.exists():
        held = DC.read_json(path)
        if held.get("keys") == keys:
            return held
    frame = CMP.inputs_frame(P)
    last = season if admitted else season - 1
    seasons = list(range(2019, last + 1))
    y = CMP.outcomes(P, through=last)
    p = CMP.seed_table(P, frame, seasons)
    in_season = frame.index.isin(admitted or []) & (frame["season"] == season).to_numpy()
    ids = frame.index[frame["season"].between(2019, season - 1).to_numpy() | in_season]
    info = frame.loc[ids, ["tour", "season", "debut_season"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    if info["y"].isna().any():
        raise RuntimeError(f"a result of the history ({kind} set) is missing")
    eta = pd.Series(C.lg(p.reindex(ids).mean(axis=1).to_numpy()), index=ids)
    col = FEED_COLUMN[feed]
    z = pd.read_parquet(speed_column(instance), columns=["match_id", col]).astype({"match_id": str})
    z = z.set_index("match_id")[col]
    hist = info.index[~info["debut"].to_numpy()]
    s_atp, s_wta, b_shrunk, b, se_b = CMP.walk_forward_on(eta, info, z, hist)
    what = "2019 .. Y - 1" + (f" plus {len(admitted)} season-Y matches the retrain admits" if admitted else "")
    out = {"keys": keys, "feed": feed, "set": kind, "s_atp": s_atp, "s_wta": s_wta, "b_shrunk": b_shrunk, "b_mle": b,
           "se_b": se_b, "fit": f"current_best_model/compare.walk_forward_on: {what}, seeds 0-3 mean, debut seasons "
                                f"out, b shrunk with tau 0.05, on {col}",
           "matches": int(len(hist)), "computed_at": DC.stamp()}
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


def log_odds_mean(p_local, p_thinking, w_local: float = W_LOCAL) -> np.ndarray:
    """The owner's ensemble (20 Oct 2026): the two chances averaged in log-odds, w_local the local model's weight."""
    from scipy.special import expit, logit
    a = logit(np.clip(np.asarray(p_local, dtype=float), 1e-15, 1 - 1e-15))
    b = logit(np.clip(np.asarray(p_thinking, dtype=float), 1e-15, 1 - 1e-15))
    return expit(w_local * a + (1 - w_local) * b)


def thinking_forecasts(run_dir: Path, ids) -> tuple[dict | None, dict]:
    """TabPFN-3.5-Thinking's chances of the run's matches (dp_thinking.load) and their record; None and the reason when
    the run's Thinking step failed or never ran."""
    import dp_thinking as TK
    failed = TK.folder(run_dir) / "failed.json"
    if failed.exists():
        return None, {"failed": DC.read_json(failed).get("reason")}
    th = TK.load(run_dir, ids)
    if th is None:
        return None, {"failed": "no Thinking forecast in the run (its step did not run)"}
    return th, th["record"]


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


def speed_only(coef: dict) -> dict:
    """The coefficient sets with the calibration slope at 1: stage 2's serve-speed term alone, as TabPFN-3.5-Thinking
    takes it (the owner, 20 Oct 2026 evening). b is the local model's, by season and feed: the only estimate there is
    (a walk-forward fit of Thinking's own would need a paid fit per past season), and spd_L is in neither model's
    inputs, so the term is new information to both."""
    return {k: {y: {**c, "s_atp": 1.0, "s_wta": 1.0} for y, c in sets.items()} for k, sets in coef.items()}


def apply_stage2(eta_o, eta_g, tour, seasons, feeds, spd, coef: dict) -> tuple[np.ndarray, np.ndarray]:
    """q at the own price (n) and on the grid (n, k), each feed's rows with its own coefficient set (adjust.apply takes
    one feed a call; with a single feed the numbers are that one call's)."""
    ADJ = _mods()[3]
    feeds = np.asarray(feeds)
    n, k = eta_g.shape
    q_o, q_g = np.empty(n), np.empty((n, k))
    for fd in sorted(set(feeds.tolist())):
        m = feeds == fd
        q_o[m] = ADJ.apply(eta_o[m], tour[m], seasons[m], "L", col_l=spd[m], coef=coef, feed=fd)
        q_g[m] = ADJ.apply(eta_g[m].ravel(), np.repeat(tour[m], k), np.repeat(seasons[m], k), "L",
                           col_l=np.repeat(spd[m], k), coef=coef, feed=fd).reshape(int(m.sum()), k)
    return q_o, q_g


def run(run_dir: Path, seeds: list[int], instance: Path = DC.INSTANCE, checkpoint: str | None = None,
        thinking: bool = False) -> dict:
    """thinking: the run was made with --thinking (its Thinking forecasts are averaged in when the step succeeded)."""
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
    feeds = feed_of(days)
    fit = DC.read_json(run_dir / "fit.json")
    pg, po = d["grid"].mean(axis=0), d["own"].mean(axis=0)
    eta_g, eta_o = C.lg(pg), C.lg(po)
    coef = {"L_weekly": {}, "L_daily": {}}
    coef_annual = {"L_weekly": {}, "L_daily": {}}
    rec_coef, rec_annual = {}, {}
    for Y, fd in sorted(set(zip(seasons.tolist(), feeds.tolist()))):
        c = coefficients(int(Y), instance, fd)                 # grown when the instance's retrain admits season Y
        check_live_fit(fit, c)
        coef[f"L_{fd}"][str(int(Y))] = {"s_atp": c["s_atp"], "s_wta": c["s_wta"], "b_shrunk": c["b_shrunk"]}
        rec_coef[str(int(Y)) if fd == "weekly" else f"{int(Y)}_{fd}"] = c
        if c.get("set") == "grown":                           # the owner's condition 3: the annual set logged beside
            a = coefficients(int(Y), instance, fd, grown=False)
            coef_annual[f"L_{fd}"][str(int(Y))] = {"s_atp": a["s_atp"], "s_wta": a["s_wta"], "b_shrunk": a["b_shrunk"]}
            rec_annual[str(int(Y)) if fd == "weekly" else f"{int(Y)}_{fd}"] = a
    spd, spd_rec = speed_columns(meta.reset_index(), days)
    tour = meta["tour"].to_numpy()
    n, k = pg.shape
    loc_o_off, loc_g_off = apply_stage2(eta_o, eta_g, tour, seasons, feeds, spd, coef)   # the local model's stage 2
    grown_run = bool(rec_annual)
    if grown_run:
        if len(rec_annual) != len(rec_coef):
            raise RuntimeError("a run mixing grown and annual stage-2 sets across its seasons: predict each apart")
        ann_o, _ = apply_stage2(eta_o, eta_g, tour, seasons, feeds, spd, coef_annual)
    th, th_rec = thinking_forecasts(run_dir, ids) if thinking else (None, None)
    if th is not None:                           # the owner's 50/50 ensemble in log-odds (20 Oct 2026), before the patterns
        if not np.allclose(th["own_logit"], d["own_logit"], rtol=0, atol=1e-12):
            raise RuntimeError("the Thinking forecasts were made at other own prices than the local fit's")
        # Thinking with stage 2's serve-speed term, never its calibration slope (the owner, 20 Oct 2026 evening)
        th_o, th_g = apply_stage2(C.lg(th["own"]), C.lg(th["grid"]), tour, seasons, feeds, spd, speed_only(coef))
        q_o_off = log_odds_mean(loc_o_off, th_o)
        q_g_off = log_odds_mean(loc_g_off, th_g)
    else:
        q_o_off, q_g_off = loc_o_off, loc_g_off  # stage 2 without the combined-pattern adjustment
    q_o, q_g, loc_o, loc_g = q_o_off, q_g_off, loc_o_off, loc_g_off
    pat = patterns(run_dir, ids)                 # None while the adjustment is off
    if pat is not None:
        q_o = pat["shift_fn"](q_o_off, pat["shift"])
        q_g = pat["shift_fn"](q_g_off, pat["shift"][:, None])
        loc_o = pat["shift_fn"](loc_o_off, pat["shift"])
        loc_g = pat["shift_fn"](loc_g_off, pat["shift"][:, None])
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
        "p_base_a": po, "eta": eta_o, "p_grid_read_back_a": back, "spd_L": spd, "speed_feed": feeds, "q_a": q_o,
        # the combined-pattern adjustment, said plainly: q_a is the prediction used (with the patterns when they are
        # on); the two versions beside it, the switch, and the shift (log-odds) and score behind it
        "q_a_patterns_off": q_o_off, "q_a_patterns_on": q_o if pat is not None else np.nan,
        "patterns": "on" if pat is not None else "off",
        "pattern_applied": pat["applied"] if pat is not None else False,
        "pattern_shift": pat["shift"] if pat is not None else 0.0,
        "pattern_z": pat["z_raw"] if pat is not None else np.nan,
        "gate": gate["bet"].to_numpy(), "gate_reason": gate["reason"].to_numpy(),
        # the edge a gap of a kind the training rows nearly always hold asks for (gate.EDGE_BAR, 14 Oct 2026); 0 none
        "gate_edge_bar": (gate["edge_bar"] if "edge_bar" in gate.columns else pd.Series(0.0, index=gate.index))
        .fillna(0.0).to_numpy(dtype="float64"),
        "instance": instance.name, "seeds": f"{min(seeds)}-{max(seeds)}", "checkpoint": checkpoint})
    if grown_run:           # a retrain's instance: stage 2 grown with the season (used), the annual set beside it
        pred["stage2_set"] = "grown"
        pred["q_a_stage2_annual"] = ann_o          # the local model's stage-2 chance with the annual set, no patterns
    if thinking:            # a run made with --thinking: each model beside the ensemble (q_a), and whether it is on
        pred["q_a_local"], pred["q_a_local_patterns_off"] = loc_o, loc_o_off
        pred["q_a_thinking"] = th_o if th is not None else np.nan          # with the speed term, uncalibrated
        pred["q_a_thinking_api"] = th["own"] if th is not None else np.nan  # the API's own chance
        pred["ensemble"] = "on" if th is not None else "off"
        pred["ensemble_weight_local"] = W_LOCAL if th is not None else np.nan
    pred.to_csv(run_dir / "predictions.csv", index=False)
    curves = pd.DataFrame({"match_id": np.repeat(ids, k), "odds_logit": np.tile(FT.GRID, n),
                           "p_market_a": 1 / (1 + np.exp(-np.tile(FT.GRID, n))), "p_base_a": pg.ravel(),
                           "eta": eta_g.ravel(), "q_a": q_g.ravel(), "q_a_patterns_off": q_g_off.ravel()})
    if th is not None:
        curves["q_a_local"], curves["q_a_local_patterns_off"] = loc_g.ravel(), loc_g_off.ravel()
        curves["q_a_thinking"] = th_g.ravel()
        curves["q_a_thinking_api"] = th["grid"].ravel()
    curves.to_parquet(run_dir / "curves.parquet", index=False)
    states = DC.read_json(run_dir / "states.json") if (run_dir / "states.json").exists() else {}
    prov = {"made_at": DC.stamp(), "instance": str(instance),
            "instance_frame_sha256": fit["frame_sha256"], "instance_inputs_sha256": DC.sha256(instance / "model_inputs.json"),
            "live_frame_sha256": DC.sha256(run_dir / "live_frame.parquet"), "inputs": fit["inputs"],
            "seeds": list(seeds), "tabpfn": fit["versions"],
            "tabpfn_checkpoints": sorted({v["checkpoint"] for v in fit["seeds"].values() if v.get("checkpoint")}),
            "grid": fit["grid"], "stage2": {"coefficients": rec_coef, "speed": spd_rec, "mode": "L",
                                            "feed": "+".join(sorted(set(feeds.tolist()))),
                                            "feed_rule": f"daily from {DAILY_FEED_FROM} (the daily collector's first "
                                                         "day in the live panel), weekly before (the owner, 14 Oct 2026)"},
            "checkpoint": checkpoint, "state_parts": states.get("record", {}).get("parts"),
            "layer_config_sha256": states.get("layer_config_sha256"), "code": {f.name: DC.sha256(f)
                                                                               for f in sorted(DC.HERE.glob("dp*.py"))}}
    if grown_run:
        prov["stage2"]["set"] = "grown"
        prov["stage2"]["coefficients_annual"] = rec_annual
    if pat is not None:
        prov["stage2"]["patterns"] = pat["record"]
    if thinking:
        prov["thinking"] = {"requested": True, "ensemble": "on" if th is not None else "off",
                            "weight_local": W_LOCAL if th is not None else None,
                            "rule": "logit q = W x logit(local stage 2) + (1 - W) x logit(Thinking's chance: the API's "
                                    "own, seed 0, symmetrised, plus stage 2's serve-speed term b x spd_L, never its "
                                    "calibration slope), then the patterns while on (the owner, 20 Oct 2026; the speed "
                                    "term from the evening of 20 Oct)",
                            "thinking_stage2": "the serve-speed term only (slope 1): the local model's b by season "
                                               "and feed, the same spd_L",
                            **th_rec}
    DC.write_json(run_dir / "provenance.json", prov)
    return {"matches": int(n), "q_range": [float(q_o.min()), float(q_o.max())],
            **({"ensemble": "on" if th is not None else f"off: {th_rec.get('failed')}"} if thinking else {}),
            "grid_read_back_vs_own_max_abs": float(np.nanmax(np.abs(back - po))) if np.isfinite(back).any() else None}
