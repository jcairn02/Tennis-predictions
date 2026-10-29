"""U-126 refreshed, 14 Oct 2026 (the owner: "Add an input to the candidate-feature list saying how much data stands
behind each player's recent form"): for every match, how much box-score evidence stands behind each player's two-week
form, exactly as the current best model weighs it. For the feature pool only (the feature universe); a selection round
decides whether it enters the model.

Per match and player (A = Stage 0's player_a_id):
    sw   Sigma w, the denominator of Stage B's two-week form (stageB_adjperf step 3, through the level layer's
         forms_step3, as stageB_adjperf.build and the daily engine compute it): over the player's earlier box-score
         matches under Stage B's time rule (events of earlier tournament weeks, and the same event's earlier rounds;
         never the match itself, its own round, or another event of the same week), each weighs
         2^(-age / 2 weeks), the age from tournament date to tournament date, times the level layer's exchange rate
         for men (fitted per season, statistic and level, capped at 1; ITF and ITF-qualifying box rows 0; main tour and
         team events 1). Women: 1. Stage B's tau is 0, so a main-tour match weighs 1 and sw is a decayed match count.
         A box-score match is a completed, standard-format match whose statistic's counts exist (retirements and
         walkovers never count). sw is 0 without one: the form does not exist. It is also exactly 0 where the last box
         score is over about two years old and the row is itself a box row (the as-of sums' (a + b) - b cancels; the
         true value is below 1e-16): 48 of the 13 Oct frame's 134,452 player-rows, whose form exists and is about 0.
         The statistic is tpw, total points won (the model's adjperf_tpw_2w): its mask is the broadest of the 17 forms
         (every box score with point counts). The checks measure how the other 16 forms' masks and layer weights differ.
    r    sw / (sw + K3), K3 = tpw's (10 men, 20 women; the layer's pinned constants): the share of the raw two-week
         mean that adjperf_tpw_2w keeps after shrinkage. The serve-skill forms (spw's K3, also 10 / 20) shrink with the
         same K3; the return-skill forms (K3 160) much more.
    r_diff = r_a - r_b.

How it reads a template's build tree: read only, as the daily engine reads a base tree (dp_common.use_tree and
layer_config_for, re-implemented here so this module imports nothing from the daily engine): the tree first on
sys.path, so `src` is the tree's code and its ROOT-relative paths are the tree's tables; no bytecode written; the
tree's resolved layer config copied to form_evidence/layer_copies/ with record_dir null and stage0_matches pinned to
the tree's Stage 0. Stage 4's loader reads Stage 0's players table, result included; the result is blanked at once
(every row False) and nothing reads it: check (b) reproduces the model's own adjperf_tpw_2w bit for bit.

Writes data/studies/feature_universe/form_evidence/:
    <instance>.parquet         the instance's frame population (its model_frame_chain.parquet): match_id, tour, season,
                               player_a_id, player_b_id (the tree's Stage 0 sides, as the frame's), sw_a, sw_b, r_a,
                               r_b, r_diff
    store_columns.parquet      (--store) the feature store's population, the frozen 63,737 matches with the sides of
                               the pre-rebuild Stage 0 (the store's side A), the same columns, plus the instance; read by
                               build_store.py --append-fe
    <instance>_checks.json     the sources and their hashes, and the checks (none relates anything to a match result):
                               (b) the denominator: the model's adjperf_tpw_2w recomputed from sw and compared with the
                                   frame's, and sw recounted independently on a sample from the box rows;
                               (c) the time rule: a cut probe on sw, with a leaky control;
                               masks: the 17 forms' own sw against tpw's;
                               (e) coverage, level and level mix of sw by tour and season;
                               (a) against U-126's 7 Oct build (the store's fp__f07 s0 and fp__f13 shr), with the
                                   difference split into the layer's weights and the tables;
                               (d) near copies: the largest |r| against every store column and the model's inputs
    layer_copies/<tree>.json   the read-only copy of the tree's layer config
No fit; no outcome.

Run: ./python.sh src/eda/feature_universe/form_evidence.py [--store]      (the master notebook's selected instance and
                                                                          its build tree, as the daily engine reads)
     ./python.sh src/eda/feature_universe/form_evidence.py --tree <build tree> --instance <its instance>   (another one)
The outputs of 14 Oct 2026 were built on template_2026-10-13 in C:/Users/zerom/tnr_gaps (the store's columns, with
--store) and on template_2026-10-14 in C:/Users/zerom/tnr_tpl1014. Both trees were deleted on 22 Oct 2026 (the owner;
docs/studies/cleanup_inventory/process_log.md § 9d), so those outputs cannot be rebuilt as they were; a re-run reads a
current instance's tree, and its values may differ.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[3]
FU = REPO / "data" / "studies" / "feature_universe"
OUT = FU / "form_evidence"
STORE = FU / "store.parquet"
STORE_POPULATION = REPO / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"   # its rows
STORE_SIDES = (REPO / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data"
               / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")       # the store's side A
OLD_BOX = REPO / "data" / "studies" / "ufc_ideas" / "stageB_adj.parquet"                  # what the 7 Oct s0 counted
INSTANCES = REPO / "data" / "studies" / "current_best_model"
LAYER_BUILD = Path("data") / "studies" / "current_best_model" / "level_layer" / "this_build" / "build_config.json"
STAGE0 = Path("data") / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
TIMING = Path("data") / "studies" / "match_timing" / "timing.parquet"
SELECTED = REPO / "data" / "studies" / "master_pipeline" / "selected_instance.json"   # the master notebook's selection
STAT, CHANNEL = "tpw", "adjperf"
TOURS = ("atp", "wta")
RESULT_NAMES = {"a_won", "won", "y", "winner", "result"}
OLD = {"s0": "fp__f07_evidence_age__f07_s0", "shr": "fp__f13_uncertainty__shr"}
PERIODS = ((2013, 2021), (2022, 2024), (2025, 2026))
MAIN_LEVELS = ("MAIN", "TEAM")
ITF_LEVELS = ("ITF", "ITFQ")
SEED = 20261014
COLUMNS = ["sw_a", "sw_b", "r_a", "r_b", "r_diff"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")
    os.replace(part, path)


# ------------------------------------------------------------------------------------------------
# The tree (read only)

def enter_tree(tree: Path) -> dict:
    """The tree first on sys.path, no bytecode, LLE_LAYER = a read-only copy of the tree's resolved layer config."""
    tree = Path(tree).resolve()
    if not (tree / "src" / "eda").is_dir():
        raise SystemExit(f"{tree} is not a build tree (no src/eda)")
    if "src" in sys.modules:
        raise RuntimeError("`src` was imported before the tree was entered")
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(tree))
    sys.path.insert(1, str(tree / "src" / "eda" / "prediction_pipeline"))
    src = tree / LAYER_BUILD
    cfg = json.loads(src.read_text(encoding="utf-8"))
    cfg["record_dir"] = None
    cfg["stage0_matches"] = str(tree / STAGE0)
    cfg["read_only_copy_of"] = {"path": str(src), "sha256": sha256(src)}
    copy = OUT / "layer_copies" / f"{tree.name}.json"
    copy.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=1)
    if not copy.exists() or copy.read_text(encoding="utf-8") != text:
        copy.write_text(text, encoding="utf-8")
    held = os.environ.get("LLE_LAYER", "").strip()
    if held and Path(held).resolve() != copy.resolve():
        raise SystemExit(f"LLE_LAYER is set to {held}, not this tree's copy {copy}")
    os.environ["LLE_LAYER"] = str(copy)
    return {"tree": str(tree), "layer_config": str(src), "layer_config_sha256": sha256(src),
            "layer_config_copy": str(copy), "stage0_sha256": sha256(tree / STAGE0),
            "timing_sha256": sha256(tree / TIMING)}


def modules(tree: Path):
    LL = importlib.import_module("src.eda.lower_level_evidence.level_layer")
    AP = importlib.import_module("src.eda.ufc_ideas.stageB_adjperf")
    B = importlib.import_module("src.eda.ufc_ideas.stageB_common")
    FS = importlib.import_module("forms_state")
    for m in (LL, AP, B, FS):
        if not Path(m.__file__).resolve().is_relative_to(Path(tree).resolve()):
            raise RuntimeError(f"{m.__name__} was imported from {m.__file__}, not the tree {tree}")
    return LL, AP, B, FS


def code_hashes(tree: Path) -> dict:
    names = ["src/eda/ufc_ideas/stageB_adjperf.py", "src/eda/ufc_ideas/stageB_common.py",
             "src/eda/lower_level_evidence/level_layer.py", "src/eda/predictability_diagnostic/stage4_features.py",
             "src/eda/predictability_diagnostic/stage3_traits.py", "src/eda/predictability_diagnostic/common.py",
             "src/eda/prediction_pipeline/forms_state.py"]
    return {n: {"tree": sha256(Path(tree) / n), "repository_equal": sha256(Path(tree) / n) == sha256(REPO / n)}
            for n in names}


# ------------------------------------------------------------------------------------------------
# Stage B's step 3, as the builder calls it

def step3(LL, AP, ctx, chosen, s: str, ch: str, zs=(), keep=None, layer: bool = True) -> np.ndarray:
    """Step-3 sums at every row of ctx.U for (s, ch), per tour as stageB_adjperf.build calls them: the level layer's
    forms_step3 (layer False: the builder's own Ctx.step3, the layer's weights off). Columns: sum w z_j for each z in
    zs, then sum w (the decayed half-life), then the career count of rows that make the form exist. keep (box order)
    removes box rows (the checks' decompositions and the probe)."""
    units, ok = ctx.step3_units(s, ch)
    if keep is not None:
        ok = ok & keep
    k = len(zs)
    tour_u = ctx.rows["tour"].to_numpy()[ctx.U]
    out = np.full((len(ctx.U), k + 2), np.nan)
    for t in TOURS:
        c = AP.constants_for(chosen, s, ch, t)
        okt = ok & (ctx.tour_box == t)
        if layer:
            sums = LL.forms_step3(ctx, s, ch, list(zs), units, okt, c["tau"], (c["h3"],))
        else:
            sums = ctx.step3(list(zs), units, okt, c["tau"], (c["h3"],))
        fk = AP.form_key("decayed", c["h3"])
        m = tour_u == t
        out[m, :k + 1] = sums[fk][m, :k + 1]
        out[m, k + 1] = sums["career"][m, k + 1]
    return out


def k3_of(AP, ctx, chosen) -> dict:
    """K3 in weight units per tour (K3 x u_typ^tau), as Ctx.pool_kref forms it."""
    out = {}
    for t in TOURS:
        c = AP.constants_for(chosen, STAT, CHANNEL, t)
        out[t] = float(c["K3"] * ctx.typ[(STAT, t)] ** c["tau"]) if c["tau"] else float(c["K3"])
    return out


# ------------------------------------------------------------------------------------------------
# Small helpers

def by_period(season) -> np.ndarray:
    s = np.asarray(season)
    return np.select([s <= 2021, s <= 2024], ["2013-2021", "2022-2024"], "2025-2026")


def cross_corr(Y: np.ndarray, X: np.ndarray, min_rows: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """Pairwise-complete Pearson correlations of the columns of Y (n, q) with those of X (n, p), NaN = missing (the
    store hygiene's near_duplicates, across two blocks)."""
    def centred(A):
        M = np.isfinite(A)
        mean = np.nanmean(np.where(M, A, np.nan), axis=0)
        return np.where(M, A - mean, 0.0), M.astype(float)
    Y0, My = centred(Y)
    X0, Mx = centred(X)
    n = My.T @ Mx
    sy, sx = Y0.T @ Mx, My.T @ X0
    syy, sxx = (Y0 ** 2).T @ Mx, My.T @ (X0 ** 2)
    sxy = Y0.T @ X0
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (n * sxy - sy * sx) / np.sqrt((n * syy - sy ** 2) * (n * sxx - sx ** 2))
    r[n < min_rows] = np.nan
    return r, n


def top_abs(names: list[str], r: np.ndarray, n: np.ndarray, k: int = 6) -> list[dict]:
    o = np.argsort(-np.nan_to_num(np.abs(r), nan=-1.0))[:k]
    return [{"column": names[j], "r": round(float(r[j]), 4), "rows": int(n[j])} for j in o if np.isfinite(r[j])]


def read_frame(instance: str) -> pd.DataFrame:
    """The instance's chain frame: keys and the model's inputs, never a result column."""
    path = INSTANCES / instance / "model_frame_chain.parquet"
    names = pq.read_schema(path).names
    cols = ["match_id", "tour", "season", "tournament_date"] + [c for c in names if c.startswith("in_")]
    if set(cols) & RESULT_NAMES:
        raise ValueError("a result column was requested")
    f = pd.read_parquet(path, columns=cols)
    f["match_id"] = f["match_id"].astype(str)
    if f["match_id"].duplicated().any():
        raise ValueError(f"{path}: duplicated match ids")
    return f


def summary(v: np.ndarray) -> dict:
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0}
    q = np.quantile(v, [0.0, 0.1, 0.5, 0.9, 1.0])
    return {"n": int(len(v)), "mean": round(float(v.mean()), 4), "min": round(float(q[0]), 6),
            "p10": round(float(q[1]), 4), "median": round(float(q[2]), 4), "p90": round(float(q[3]), 4),
            "max": round(float(q[4]), 4), "share_zero": round(float((v == 0).mean()), 4)}


# ------------------------------------------------------------------------------------------------
# The checks

def check_denominator(ctx, frame: pd.DataFrame, pos: np.ndarray, S: np.ndarray, K3u: np.ndarray) -> dict:
    """(b) The model's adjperf_tpw_2w from sw: v = sum w z / (sw + K3) where the form exists (Ctx.pool_values), A - B,
    stored float32 as the builder stores it, against the instance frame's in_adjperf_tpw_2w on every frame match."""
    swz, sw, cnt = S[:, 0], S[:, 1], S[:, 2]
    ex = cnt > 0.5
    v = np.where(ex, swz / (sw + K3u), np.nan)
    ia, ib = ctx.ia[pos], ctx.ib[pos]
    both = ex[ia] & ex[ib]
    mine = np.where(both, v[ia] - v[ib], np.nan).astype("float32").astype("float64")
    ref = frame["in_adjperf_tpw_2w"].to_numpy(dtype="float64")
    na, nb = np.isnan(mine), np.isnan(ref)
    fin = ~na & ~nb
    fu = np.unique(np.r_[ia, ib])
    return {"frame_matches": int(len(ref)), "nan_pattern_equal": bool(np.array_equal(na, nb)),
            "bitwise_equal": int(np.sum(mine[fin] == ref[fin]) + np.sum(na & nb)),
            "max_abs_diff": float(np.max(np.abs(mine[fin] - ref[fin]))) if fin.any() else 0.0,
            # the as-of sums subtract the row's own week from a running sum: where the last box score is over about
            # two years old and the row is itself a box row, sum w cancels to exactly 0 (its true value is < 1e-16)
            "frame_player_rows": int(len(fu)),
            "exists_but_sw_zero": int((ex[fu] & (sw[fu] == 0)).sum()),
            "sw_positive_but_not_exists": int((~ex[fu] & (sw[fu] > 0)).sum()),
            "no_earlier_box_score": int((~ex[fu]).sum()),
            "smallest_positive_sw": float(sw[fu][sw[fu] > 0].min()), "negative_sw": int((sw < 0).sum())}


def check_recount(ctx, LL, cfg, sw: np.ndarray, frame_u: np.ndarray, n: int, rng) -> dict:
    """(b) sw recounted on a sample of the frame's player-rows straight from the box rows: the player's earlier
    box-score rows (earlier tournament date, or the same event's earlier round), each 2^(-(d0 - d) / 14 days) x the
    layer's weight of its row (level_layer.weights for tpw, the function forms_step3 calls)."""
    rows = ctx.rows
    bi = ctx.box_idx
    units, ok = ctx.step3_units(STAT, CHANNEL)
    K = LL._box_keys(ctx, cfg)
    rw = LL.weights(cfg, STAT, K["tour"], K["bucket"], K["season"], "box", valid=ok)
    pc = rows["pcode"].to_numpy()
    day = rows["day"].to_numpy().astype("int64")
    tid = rows["tournament_id"].astype(str).to_numpy()
    rnd = rows["round_order"].to_numpy()
    pcb = pc[bi]
    order = np.argsort(pcb, kind="stable")
    starts = np.searchsorted(pcb[order], np.arange(pc.max() + 2))
    pick = rng.choice(frame_u, size=min(n, len(frame_u)), replace=False)
    gaps, worst = [], None
    for u in pick:
        r = ctx.U[u]
        p = pc[r]
        js = bi[order[starts[p]:starts[p + 1]]]
        jb = order[starts[p]:starts[p + 1]]                       # box positions
        vis = (day[js] < day[r]) | ((day[js] == day[r]) & (tid[js] == tid[r]) & (rnd[js] < rnd[r]))
        w = np.where(ok[jb] & vis, rw[jb] * np.exp2(-(day[r] - day[js]) / 14.0), 0.0)
        mine = float(w.sum())
        gap = abs(mine - sw[u]) / max(1.0, abs(mine))
        gaps.append(gap)
        if worst is None or gap > worst["relative_gap"]:
            worst = {"match_id": str(rows["match_id"].to_numpy()[r]), "player_id": str(rows["player_id"].to_numpy()[r]),
                     "recount": mine, "stored": float(sw[u]), "relative_gap": gap}
    tour_b = np.asarray(K["tour"]).astype(str)
    bucket = np.asarray(K["bucket"]).astype(str)
    w_by = {}
    for t in TOURS:
        for b in sorted(set(bucket[(tour_b == t) & ok])):
            m = (tour_b == t) & ok & (bucket == b)
            w_by[f"{t}|{b}"] = {"rows": int(m.sum()), "min": float(rw[m].min()), "mean": round(float(rw[m].mean()), 4),
                                "max": float(rw[m].max())}
    return {"sampled_player_rows": int(len(pick)), "max_relative_gap": float(max(gaps)), "worst": worst,
            "layer_weight_by_tour_level": w_by}


def cut_probe(LL, AP, ctx, chosen, base: np.ndarray, own_w_u: np.ndarray, n_cuts: int, rng) -> dict:
    """(c) The time rule, on sw itself (stageB_adjperf.probe's cut, on box availability): at each cut (a random pool
    match of 2014-2026), every box row the cut may not see (later weeks; in the cut's week, other events, and the cut
    event's rounds from the cut's on) loses its box score; sw is recomputed. Protected rows (earlier weeks, and the cut
    event's rounds up to the cut's) must not move; a leaky control (sw counting the row's own box score) must."""
    rows = ctx.rows
    U, bi = ctx.U, ctx.box_idx
    day, ev, rnd = (rows[c].to_numpy() for c in ("day", "ev", "round_order"))
    yr = rows["year"].to_numpy()
    cand = ctx.A[(yr[ctx.A] >= 2014)]
    res = {"cuts": 0, "protected_checked": 0, "protected_changed": 0, "protected_changed_bitwise": 0, "later_rows": 0,
           "later_changed": 0, "control_protected_changed": 0, "largest_protected_difference": 0.0,
           "tolerance": "protected_changed counts moves beyond 1e-12; protected_changed_bitwise also counts the as-of "
                        "sums' rounding at the cut's own week ((a + b) - b against a, when the row's own box score is "
                        "removed)"}
    for c in rng.choice(cand, size=n_cuts, replace=False):
        later_b = (day[bi] > day[c]) | ((day[bi] == day[c]) & ((ev[bi] != ev[c]) | (rnd[bi] >= rnd[c])))
        prot = (day[U] < day[c]) | ((day[U] == day[c]) & (ev[U] == ev[c]) & (rnd[U] <= rnd[c]))
        S1 = step3(LL, AP, ctx, chosen, STAT, CHANNEL, (), keep=~later_b)[:, 0]
        lost_own = np.zeros(len(U), dtype=bool)
        lost_own[ctx.u_pos_box] = later_b
        ctl0, ctl1 = base + own_w_u, S1 + np.where(lost_own, 0.0, own_w_u)
        moved = np.abs(S1 - base) > 1e-12
        res["cuts"] += 1
        res["protected_checked"] += int(prot.sum())
        res["protected_changed"] += int((prot & moved).sum())
        res["protected_changed_bitwise"] += int((prot & (S1 != base)).sum())
        res["later_rows"] += int((~prot).sum())
        res["later_changed"] += int((~prot & moved).sum())
        res["control_protected_changed"] += int((prot & (np.abs(ctl1 - ctl0) > 1e-12)).sum())
        if (prot & (S1 != base)).any():
            res["largest_protected_difference"] = max(res["largest_protected_difference"],
                                                      float(np.max(np.abs(S1 - base)[prot])))
        log(f"  probe cut {res['cuts']}: protected changed {res['protected_changed']} (bitwise "
            f"{res['protected_changed_bitwise']}), later changed {res['later_changed']}, control caught at "
            f"{res['control_protected_changed']}")
    return res


def check_masks(LL, AP, ctx, chosen, sw: np.ndarray, ia: np.ndarray, ib: np.ndarray, season, tour) -> dict:
    """The 17 forms' own sw (their statistic's box mask and, for men, the layer's weight of that statistic) against
    tpw's, on the frame's player-rows: the share that differ, the mean ratio, and where tpw's form exists but the
    statistic's does not."""
    base = np.r_[sw[ia], sw[ib]]
    per = np.r_[by_period(season), by_period(season)]
    tr = np.r_[tour, tour]
    out = {}
    for s, ch in LL.FORM_SPECS:
        S = step3(LL, AP, ctx, chosen, s, ch, ())
        v = np.r_[S[ia, 0], S[ib, 0]]
        rec = {}
        for t in TOURS:
            for p in ("2013-2021", "2022-2024", "2025-2026"):
                m = (tr == t) & (per == p)
                gap = np.abs(v[m] - base[m])
                d = gap > 1e-9 * np.maximum(1.0, np.abs(base[m]))
                pos = base[m] > 0
                rec[f"{t}|{p}"] = {"share_differs": round(float(d.mean()), 4),
                                   "share_differs_by_0.25": round(float((gap > 0.25).mean()), 4),
                                   "mean_abs_diff": round(float(gap.mean()), 4),
                                   "mean_ratio": round(float(v[m][pos].sum() / base[m][pos].sum()), 4) if pos.any() else None,
                                   "corr": round(float(np.corrcoef(v[m], base[m])[0, 1]), 4),
                                   "tpw_exists_this_not": round(float(((base[m] > 0) & (v[m] == 0)).mean()), 4)}
        out[f"{ch}_{s}"] = rec
        log(f"  mask {ch}_{s}: {rec['atp|2013-2021']} / {rec['wta|2013-2021']}")
    return out


def coverage_table(frame: pd.DataFrame, cols: dict) -> list[dict]:
    """(e) By tour and season: matches, the share where both players' form exists (sw > 0), the mean sw and r, and
    the level mix of sw (main tour and team events; lower levels without ITF; ITF)."""
    out = []
    t, s = frame["tour"].to_numpy(), frame["season"].to_numpy()
    for tour in TOURS:
        for season in sorted(set(s[t == tour])):
            m = (t == tour) & (s == season)
            sa, sb = cols["sw_a"][m], cols["sw_b"][m]
            tot = np.r_[sa, sb].sum()
            out.append({"tour": tour, "season": int(season), "matches": int(m.sum()),
                        "both_exist": round(float(((sa > 0) & (sb > 0)).mean()), 4),
                        "finite": round(float((np.isfinite(sa) & np.isfinite(sb)).mean()), 4),
                        "mean_sw": round(float(np.r_[sa, sb].mean()), 4),
                        "median_sw": round(float(np.median(np.r_[sa, sb])), 4),
                        "mean_r": round(float(np.r_[cols["r_a"][m], cols["r_b"][m]].mean()), 4),
                        "share_main": round(float(np.r_[cols["main_a"][m], cols["main_b"][m]].sum() / tot), 4) if tot > 0 else None,
                        "share_lower_non_itf": round(float(np.r_[cols["low_a"][m], cols["low_b"][m]].sum() / tot), 4) if tot > 0 else None,
                        "share_itf": round(float(np.r_[cols["itf_a"][m], cols["itf_b"][m]].sum() / tot), 4) if tot > 0 else None,
                        "mean_sw_without_layer": round(float(np.r_[cols["nl_a"][m], cols["nl_b"][m]].mean()), 4)})
    return out


def check_old(store_cols: pd.DataFrame, store: pd.DataFrame, top: int = 10) -> dict:
    """(a) Against U-126's 7 Oct build on the store's population: s0 (fp__f07, the decayed count of box rows with a
    finite tpw z in the 2 Oct Stage B table, no layer) and shr (fp__f13, its own build of W / (W + K3)). The
    difference new - s0 splits into the layer's weights (new - the same count without the layer, on today's tables)
    and the tables (without the layer - s0)."""
    out = {}
    tour = np.r_[store["tour"].to_numpy(), store["tour"].to_numpy()]
    per = np.r_[by_period(store["season"]), by_period(store["season"])]
    new = np.r_[store_cols["sw_a"], store_cols["sw_b"]]
    nl = np.r_[store_cols["nl_a"], store_cols["nl_b"]]
    s0 = np.r_[store[f"{OLD['s0']}_a"], store[f"{OLD['s0']}_b"]]
    shr = np.r_[store[f"{OLD['shr']}_a"], store[f"{OLD['shr']}_b"]]
    rnew = np.r_[store_cols["r_a"], store_cols["r_b"]]
    ok = np.isfinite(new) & np.isfinite(s0)

    def corr(a, b, m):
        m = m & np.isfinite(a) & np.isfinite(b)
        return round(float(np.corrcoef(a[m], b[m])[0, 1]), 5) if m.sum() > 2 else None
    out["corr_sw_s0"] = {"all": corr(new, s0, ok)}
    out["corr_sw_without_layer_s0"] = {"all": corr(nl, s0, ok)}
    out["corr_r_shr"] = {"all": corr(rnew, shr, ok)}
    for t in TOURS:
        for p in ("2013-2021", "2022-2024", "2025-2026"):
            m = ok & (tour == t) & (per == p)
            key = f"{t}|{p}"
            out["corr_sw_s0"][key] = corr(new, s0, m)
            out["corr_sw_without_layer_s0"][key] = corr(nl, s0, m)
            out["corr_r_shr"][key] = corr(rnew, shr, m)
    d = new - s0
    out["player_rows"] = int(ok.sum())
    out["share_abs_diff_over_0.01"] = round(float((np.abs(d[ok]) > 0.01).mean()), 4)
    out["share_abs_diff_over_0.5"] = round(float((np.abs(d[ok]) > 0.5).mean()), 4)
    out["mean_diff"] = round(float(d[ok].mean()), 5)
    out["by_tour_period"] = {}
    for t in TOURS:
        for p in ("2013-2021", "2022-2024", "2025-2026"):
            m = ok & (tour == t) & (per == p)
            dl, dt_ = (new - nl)[m], (nl - s0)[m]
            out["by_tour_period"][f"{t}|{p}"] = {
                "rows": int(m.sum()), "mean_new": round(float(new[m].mean()), 4), "mean_s0": round(float(s0[m].mean()), 4),
                "share_differs": round(float((np.abs(d[m]) > 1e-6).mean()), 4),
                "layer_part_mean": round(float(dl.mean()), 4), "layer_part_share_nonzero": round(float((np.abs(dl) > 1e-9).mean()), 4),
                "tables_part_mean": round(float(dt_.mean()), 4), "tables_part_share_nonzero": round(float((np.abs(dt_) > 1e-6).mean()), 4)}
    ids = np.r_[store["match_id"].to_numpy(), store["match_id"].to_numpy()]
    pid = np.r_[store_cols["player_a_id"].to_numpy(), store_cols["player_b_id"].to_numpy()]
    seas = np.r_[store["season"].to_numpy(), store["season"].to_numpy()]

    def listing(score: np.ndarray) -> list[dict]:
        o = np.argsort(-np.where(ok, np.abs(score), -1.0))[:top]
        return [{"match_id": str(ids[j]), "player_id": str(pid[j]), "tour": str(tour[j]), "season": int(seas[j]),
                 "sw_new": round(float(new[j]), 4), "sw_without_layer": round(float(nl[j]), 4),
                 "s0_7oct": round(float(s0[j]), 4), "layer_part": round(float(new[j] - nl[j]), 4),
                 "tables_part": round(float(nl[j] - s0[j]), 4)} for j in o]
    out["largest"] = listing(d)
    out["largest_layer_part"] = listing(new - nl)
    out["largest_tables_part"] = listing(nl - s0)
    return out


def explain_tables(largest: list[dict], rows: pd.DataFrame, box_ok: pd.DataFrame, k: int = 5) -> list[dict]:
    """For the largest table differences: the player's box rows of the last eight weeks before the match that one
    build counts and the other does not (today's tree: completed, standard format, tpw counts; 2 Oct: a finite tpw z)."""
    old = pd.read_parquet(OLD_BOX, columns=["match_id", "player_id", "z_adjperf_tpw"])
    old = old[np.isfinite(old["z_adjperf_tpw"].to_numpy(float))]
    old_keys = set(zip(old["match_id"].astype(str), old["player_id"].astype(str)))
    new_keys = set(zip(box_ok["match_id"], box_ok["player_id"]))
    info = rows[["match_id", "player_id", "tournament_date", "level", "round"]].copy()
    info["match_id"], info["player_id"] = info["match_id"].astype(str), info["player_id"].astype(str)
    out = []
    for rec in sorted(largest, key=lambda r: -abs(r["tables_part"]))[:k]:
        me = info[(info["match_id"] == rec["match_id"]) & (info["player_id"] == rec["player_id"])]
        if me.empty:
            continue
        d0 = pd.Timestamp(me["tournament_date"].iloc[0])
        h = info[(info["player_id"] == rec["player_id"]) & (pd.to_datetime(info["tournament_date"]) >= d0 - pd.Timedelta(days=56))
                 & (pd.to_datetime(info["tournament_date"]) <= d0)]
        only_new, only_old = [], []
        for r in h.itertuples(index=False):
            key = (r.match_id, r.player_id)
            if key == (rec["match_id"], rec["player_id"]):
                continue
            a, b = key in new_keys, key in old_keys
            if a != b:
                (only_new if a else only_old).append(f"{r.match_id} ({pd.Timestamp(r.tournament_date).date()}, {r.level}, {r.round})")
        out.append({**rec, "box_rows_only_today": only_new[:8], "box_rows_only_2_oct": only_old[:8]})
    return out


def near_copies(new: dict, store: pd.DataFrame, store_names: list[str], frame: pd.DataFrame, frame_new: dict) -> dict:
    """(d) The largest |r| of each new column against every store column (store population) and every model input
    (the instance frame's population; the 58 chain inputs, in_sets_14d among them)."""
    out = {"store": {}, "model_inputs": {}}
    X = store[store_names].to_numpy(dtype="float64")
    X = np.where(np.isfinite(X), X, np.nan)
    Y = np.column_stack([new[c] for c in new])
    r, n = cross_corr(Y, X)
    for i, c in enumerate(new):
        out["store"][c] = top_abs(store_names, r[i], n[i])
    names = [c for c in frame.columns if c.startswith("in_")]
    X = frame[names].to_numpy(dtype="float64")
    Y = np.column_stack([frame_new[c] for c in frame_new])
    r, n = cross_corr(Y, X)
    for i, c in enumerate(frame_new):
        out["model_inputs"][c] = top_abs(names, r[i], n[i])
    return out


# ------------------------------------------------------------------------------------------------

def selected_instance() -> tuple[str | None, str | None]:
    """The instance and build tree the master notebook selected (the daily engine reads the same file): the default
    since 22 Oct 2026. Before, it was template_2026-10-13 and its tree C:/Users/zerom/tnr_gaps, deleted that day."""
    try:
        sel = json.loads(SELECTED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    return sel.get("instance"), sel.get("tree")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", help="a template's build tree, with --instance (default: both from the master notebook's "
                                   "selection)")
    ap.add_argument("--instance", help="the instance built in that tree")
    ap.add_argument("--store", action="store_true", help="also write store_columns.parquet (the store's population)")
    ap.add_argument("--probe-cuts", type=int, default=8)
    ap.add_argument("--sample", type=int, default=400)
    a = ap.parse_args()
    if (a.tree is None) != (a.instance is None):
        ap.error("give --tree and --instance together: the tree's tables are that instance's build")
    if a.tree is None:
        a.instance, a.tree = selected_instance()
        if not (a.instance and a.tree):
            ap.error(f"no selection in {SELECTED}: give --tree and --instance")
    rng = np.random.default_rng(SEED)
    tree = Path(a.tree).resolve()
    sources = enter_tree(tree)
    LL, AP, B, FS = modules(tree)
    cfg = LL.config()
    chosen = FS.pinned_constants()
    sources["code"] = code_hashes(tree)
    sources["pinned_constants"] = {f"{t}|{s}": v for (t, s), v in sorted(chosen.items())}
    frame_path = INSTANCES / a.instance / "model_frame_chain.parquet"
    sources["frame"] = {"path": str(frame_path), "sha256": sha256(frame_path)}
    log(f"tree {tree}; instance {a.instance}; layer {sources['layer_config_copy']}")

    rows, _ = B.load_rows()
    rows["won"] = False                                       # the result, blanked before anything reads the rows
    ctx = AP.Ctx(rows, B.surface_means())
    log(f"Stage B context: {len(rows):,} player rows, {len(ctx.box_idx):,} box rows, {len(ctx.A):,} pool matches, "
        f"U {len(ctx.U):,}")
    K3 = k3_of(AP, ctx, chosen)
    tour_u = rows["tour"].to_numpy()[ctx.U]
    K3u = np.where(tour_u == "atp", K3["atp"], K3["wta"])

    # the column: the model's own step 3 for tpw, with the model's own z (for check b)
    zt = LL.forms_z(ctx, chosen, {(STAT, CHANNEL): np.full(len(ctx.box_idx), np.nan)})[(STAT, CHANNEL)]
    S = step3(LL, AP, ctx, chosen, STAT, CHANNEL, [zt])
    sw = S[:, 1]
    log("sw built (tpw, the layer's forms_step3)")

    frame = read_frame(a.instance)
    pool_ids = rows["match_id"].to_numpy()[ctx.A].astype(str)
    pos = pd.Index(pool_ids).get_indexer(frame["match_id"])
    if (pos < 0).any():
        raise RuntimeError(f"{int((pos < 0).sum())} frame matches are not in Stage B's pool")
    ia, ib = ctx.ia[pos], ctx.ib[pos]
    pid = rows["player_id"].astype(str).to_numpy()
    s0t = pd.read_parquet(tree / STAGE0, columns=["match_id", "player_a_id", "player_b_id"])
    s0t = s0t.assign(match_id=s0t["match_id"].astype(str)).set_index("match_id").reindex(frame["match_id"])
    pa, pb = pid[ctx.A[pos]], pid[ctx.Bi[pos]]
    checks: dict = {"frame_sides_equal_tree_stage0": bool((pa == s0t["player_a_id"].astype(str).to_numpy()).all()
                                                          and (pb == s0t["player_b_id"].astype(str).to_numpy()).all())}
    if not checks["frame_sides_equal_tree_stage0"]:
        raise RuntimeError("the pool's A and B rows are not the tree's Stage 0 sides")
    tf = frame["tour"].to_numpy()
    kf = np.where(tf == "atp", K3["atp"], K3["wta"])

    def cols_at(ua: np.ndarray, ub: np.ndarray, kk: np.ndarray) -> dict:
        a_, b_ = sw[ua], sw[ub]
        ra, rb = a_ / (a_ + kk), b_ / (b_ + kk)
        return {"sw_a": a_, "sw_b": b_, "r_a": ra, "r_b": rb, "r_diff": ra - rb}
    fcols = cols_at(ia, ib, kf)
    tab = pd.DataFrame({"match_id": frame["match_id"].to_numpy(), "tour": tf, "season": frame["season"].to_numpy(),
                        "player_a_id": pa, "player_b_id": pb, **fcols})
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_parquet(OUT / f"{a.instance}.parquet", index=False)
    log(f"wrote {a.instance}.parquet: {len(tab):,} matches")

    # (b) the denominator, and an independent recount
    checks["b_denominator"] = check_denominator(ctx, frame, pos, S, K3u)
    log(f"(b) denominator: {checks['b_denominator']}")
    frame_u = np.unique(np.r_[ia, ib])
    checks["b_recount"] = check_recount(ctx, LL, cfg, sw, frame_u, a.sample, rng)
    log(f"(b) recount: max relative gap {checks['b_recount']['max_relative_gap']:.2e}")

    # level mix and the layer's part
    K = LL._box_keys(ctx, cfg)
    bucket = np.asarray(K["bucket"]).astype(str)
    S_main = step3(LL, AP, ctx, chosen, STAT, CHANNEL, (), keep=np.isin(bucket, MAIN_LEVELS))[:, 0]
    S_itf = step3(LL, AP, ctx, chosen, STAT, CHANNEL, (), keep=np.isin(bucket, ITF_LEVELS))[:, 0]
    S_nl = step3(LL, AP, ctx, chosen, STAT, CHANNEL, (), layer=False)[:, 0]
    S_plain = step3(LL, AP, ctx, chosen, STAT, CHANNEL, ())[:, 0]
    checks["sw_without_z_equals_sw"] = bool(np.array_equal(S_plain, sw))
    checks["women_untouched_by_the_layer"] = bool(np.array_equal(S_nl[tour_u == "wta"], sw[tour_u == "wta"]))
    extra = {"main_a": S_main[ia], "main_b": S_main[ib], "itf_a": S_itf[ia], "itf_b": S_itf[ib],
             "low_a": sw[ia] - S_main[ia] - S_itf[ia], "low_b": sw[ib] - S_main[ib] - S_itf[ib],
             "nl_a": S_nl[ia], "nl_b": S_nl[ib]}
    checks["e_by_tour_season"] = coverage_table(frame, {**fcols, **extra})
    checks["e_summary"] = {t: {c: summary(np.r_[fcols[f"{c}_a"][tf == t], fcols[f"{c}_b"][tf == t]]) for c in ("sw", "r")}
                           for t in TOURS}
    checks["e_summary"]["r_diff"] = summary(fcols["r_diff"])
    log("(e) coverage and level mix done")

    # (c) the time rule
    units, ok = ctx.step3_units(STAT, CHANNEL)
    rw = LL.weights(cfg, STAT, K["tour"], K["bucket"], K["season"], "box", valid=ok)
    own_w_u = np.zeros(len(ctx.U))
    own_w_u[ctx.u_pos_box] = np.where(ok, rw, 0.0)
    checks["c_probe"] = cut_probe(LL, AP, ctx, chosen, S_plain, own_w_u, a.probe_cuts, rng)

    # the 17 forms' masks
    checks["masks"] = check_masks(LL, AP, ctx, chosen, sw, ia, ib, frame["season"].to_numpy(), tf)

    # (d) near copies on the instance's population (the model's inputs)
    frame_new = {**fcols, "sw_diff": fcols["sw_a"] - fcols["sw_b"]}

    # the store's population: the frozen model frame's matches (the store's rows), in the store's order when it exists
    if a.store:
        st_keys = pd.read_parquet(STORE_POPULATION, columns=["match_id", "tour", "season"])
        st_keys["match_id"] = st_keys["match_id"].astype(str)
        if STORE.exists():
            order = pd.read_parquet(STORE, columns=["match_id"])["match_id"].astype(str)
            if set(order) != set(st_keys["match_id"]) or len(order) != len(st_keys):
                raise RuntimeError("the store's rows are not the frozen model frame's matches")
            st_keys = st_keys.set_index("match_id").loc[order.to_numpy()].reset_index()
        sides = pd.read_parquet(STORE_SIDES, columns=["match_id", "player_a_id", "player_b_id"])
        sides = sides.assign(match_id=sides["match_id"].astype(str)).set_index("match_id").reindex(st_keys["match_id"])
        u_key = pd.MultiIndex.from_arrays([rows["match_id"].astype(str).to_numpy()[ctx.U], pid[ctx.U]])
        if u_key.duplicated().any():
            raise RuntimeError("a (match, player) appears twice in U")
        sa_ids, sb_ids = sides["player_a_id"].astype(str).to_numpy(), sides["player_b_id"].astype(str).to_numpy()
        ua = u_key.get_indexer(pd.MultiIndex.from_arrays([st_keys["match_id"].to_numpy(), sa_ids]))
        ub = u_key.get_indexer(pd.MultiIndex.from_arrays([st_keys["match_id"].to_numpy(), sb_ids]))
        found = (ua >= 0) & (ub >= 0)
        ks = np.where(st_keys["tour"].to_numpy() == "atp", K3["atp"], K3["wta"])
        uas, ubs = np.where(found, ua, 0), np.where(found, ub, 0)
        sc = {k_: np.where(found, v, np.nan) for k_, v in cols_at(uas, ubs, ks).items()}
        nl_st = {"nl_a": np.where(found, S_nl[uas], np.nan), "nl_b": np.where(found, S_nl[ubs], np.nan)}
        stab = pd.DataFrame({"match_id": st_keys["match_id"].to_numpy(), "tour": st_keys["tour"].to_numpy(),
                             "season": st_keys["season"].to_numpy(), "player_a_id": sa_ids, "player_b_id": sb_ids,
                             **sc, "instance": a.instance})
        in_pool = np.isin(st_keys["match_id"].to_numpy(), pool_ids)
        # where found, the store's side A is the tree's side A (Stage 0's player_a_id), or the sides are exchanged
        s0_tree = pd.read_parquet(tree / STAGE0, columns=["match_id", "player_a_id", "player_b_id"])
        s0_tree = s0_tree.assign(match_id=s0_tree["match_id"].astype(str)).set_index("match_id")
        t_a = s0_tree["player_a_id"].astype(str).reindex(st_keys["match_id"]).to_numpy()
        in_tree = s0_tree.index.isin(st_keys["match_id"]).sum()
        nf = ~found
        nf_in_tree = nf & pd.Index(st_keys["match_id"]).isin(s0_tree.index)
        checks["store_population"] = {
            "rows": int(len(stab)), "found_both_sides": int(found.sum()), "found_in_the_pool": int((found & in_pool).sum()),
            "found_side_a_is_the_tree_side_a": int((found & (t_a == sa_ids)).sum()),
            "found_sides_exchanged": int((found & (t_a == sb_ids)).sum()),
            "in_the_instance_frame": int(st_keys["match_id"].isin(frame["match_id"]).sum()),
            "store_matches_in_the_tree_stage0": int(in_tree),
            "not_found_same_match_id_other_players": int(nf_in_tree.sum()),
            "not_found_match_id_absent_from_the_tree": int((nf & ~nf_in_tree).sum()),
            "not_found_by_tour_season": {f"{t}|{s}": int(n) for (t, s), n in
                                         stab.loc[nf].groupby(["tour", "season"]).size().items()},
            "not_found": stab.loc[nf, "match_id"].tolist(),
            "store_population_sha256": sha256(STORE_POPULATION), "store_sides_sha256": sha256(STORE_SIDES)}
        stab.to_parquet(OUT / "store_columns.parquet", index=False)
        log(f"wrote store_columns.parquet: {int(found.sum()):,} of {len(stab):,} found; "
            f"{ {k: v for k, v in checks['store_population'].items() if k != 'not_found'} }")
    if a.store and STORE.exists():
        # (a) against the 7 Oct build, and (d) near copies, on the store's population
        names = [c for c in pq.read_schema(STORE).names if "__" in c]
        store = pd.read_parquet(STORE, columns=["match_id", "tour", "season"] + names)
        store["match_id"] = store["match_id"].astype(str)
        if not (store["match_id"].to_numpy() == stab["match_id"].to_numpy()).all():
            raise RuntimeError("the store's row order moved")
        checks["a_old_build"] = check_old(pd.DataFrame({**sc, **nl_st, "player_a_id": stab["player_a_id"],
                                                        "player_b_id": stab["player_b_id"]}), store)
        box_ok = pd.DataFrame({"match_id": rows["match_id"].astype(str).to_numpy()[ctx.box_idx][ok],
                               "player_id": pid[ctx.box_idx][ok]})
        checks["a_tables_explained"] = explain_tables(checks["a_old_build"]["largest_tables_part"], rows, box_ok)
        log(f"(a) corr with the 7 Oct s0: {checks['a_old_build']['corr_sw_s0']['all']}")
        st_new = {**sc, "sw_diff": sc["sw_a"] - sc["sw_b"]}
        checks["d_near_copies"] = near_copies(st_new, store, names, frame, frame_new)
    else:
        X = frame[[c for c in frame.columns if c.startswith("in_")]]
        r, n = cross_corr(np.column_stack(list(frame_new.values())), X.to_numpy(dtype="float64"))
        checks["d_near_copies"] = {"model_inputs": {c: top_abs(list(X.columns), r[i], n[i])
                                                    for i, c in enumerate(frame_new)}}
    log("(d) near copies done")

    write_json(OUT / f"{a.instance}_checks.json", {
        "what": "U-126 refreshed (14 Oct 2026): each player's decayed count of earlier box-score matches behind the "
                "two-week form, as the current best model weighs it (sw), and the form's shrinkage share r = sw / (sw "
                "+ K3); no result read, nothing fitted",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "statistic": f"{CHANNEL}_{STAT}", "k3": K3, "half_life_weeks": {t: AP.constants_for(chosen, STAT, CHANNEL, t)["h3"]
                                                                       for t in TOURS},
        "sources": sources, "outputs": {"instance": str(OUT / f"{a.instance}.parquet"),
                                        "instance_sha256": sha256(OUT / f"{a.instance}.parquet"),
                                        **({"store": str(OUT / "store_columns.parquet"),
                                            "store_sha256": sha256(OUT / "store_columns.parquet")} if a.store else {})},
        "checks": checks, "seconds": round(time.time() - T0, 1)})
    log(f"wrote {a.instance}_checks.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
