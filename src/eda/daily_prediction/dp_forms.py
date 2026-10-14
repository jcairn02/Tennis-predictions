"""Stage B's 17 two-week forms with saved per-match z (PLAN.md section 3.3, "forms/z.parquet").

The decided computation (ufc_ideas/stageB_adjperf.py with the level layer's forms_z and forms_step3): every box-score
player-match gets a z for each of the 17 statistic-channel pairs, from its opponent's earlier box-score matches (the
pair moments); each player's form is a decayed, shrunk average of their earlier z (step 3); the input is A's form
minus B's. The z of a box row of a tournament week before the checkpoint day reads only matches of earlier weeks (and
its event's earlier rounds), so it is final: the checkpoint keeps those z (float64, keyed by match id and side), taken
from the decided forms_z itself. A daily update then needs the z of the box rows from the checkpoint's week on
(targeted pair moments, the prototype's z_for) and step 3 over the day's players' rows (the prototype's step3_for):
both proved bit for bit against the decided functions by the plan's prototype (prediction_pipeline/forms_state.py,
imported unchanged).

The slice: per box row before the checkpoint's week, its keys (match, side, player, day, event, round, Stage 0's
order) and every per-row array the z formula reads, for each pair: the translated norm value, its validity, units and
weight, the row's own value and its own-value shift; with the pinned constants, typical units and population MADs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dp_hash import hash_arrays, hash_value


def _mods():
    from src.eda.lower_level_evidence import level_layer as LL
    from src.eda.ufc_ideas import stageB_adjperf as AP
    import forms_state as FS                       # the prototype (prediction_pipeline), unchanged
    return LL, AP, FS


def context(rows: pd.DataFrame):
    """Stage B's context on Stage 4's rows (stageB_adjperf.main: Ctx(rows, surface_means()))."""
    _, AP, _ = _mods()
    from src.eda.ufc_ideas import stageB_common as B
    return AP.Ctx(rows, B.surface_means())


def box_keys(ctx) -> pd.DataFrame:
    rows = ctx.rows
    bi = ctx.box_idx
    return pd.DataFrame({"match_id": rows["match_id"].to_numpy()[bi].astype(str),
                         "side": rows["side"].to_numpy()[bi].astype(str)})


def specs_of(ctx, chosen: dict) -> dict:
    _, _, FS = _mods()
    return FS.layer_specs(ctx, chosen)


def slice_hash(ctx, specs: dict, chosen: dict, d0: int) -> str:
    """The arrays the z of the box rows before d0's week read."""
    LL, _, _ = _mods()
    rows = ctx.rows
    bi = ctx.box_idx
    day = rows["day"].to_numpy()[bi]
    old = day < d0
    k = bi[old]
    named = {"match_id": rows["match_id"].to_numpy()[k].astype(str), "side": rows["side"].to_numpy()[k].astype(str),
             "player_id": rows["player_id"].to_numpy()[k].astype(str), "day": day[old],
             "event": (rows["tournament_id"].astype(str).to_numpy()[k] + "|"
                       + rows["tournament_date"].astype(str).to_numpy()[k]),
             "round_order": rows["round_order"].to_numpy()[k], "order": rows["order"].to_numpy()[k],
             "tour": np.asarray(ctx.tour_box)[old].astype(str)}
    inv = np.empty(ctx.P.n, dtype=np.int64)
    inv[ctx.P.order] = np.arange(ctx.P.n)
    for (s, ch), sp in specs.items():
        a2, ok, units, rw = (np.asarray(x)[inv] for x in sp["sorted"])      # back to box order
        named[f"{s}|{ch}|a"] = np.asarray(a2, dtype="float64")[old]
        named[f"{s}|{ch}|ok"] = np.asarray(ok, dtype=bool)[old]
        named[f"{s}|{ch}|units"] = np.asarray(units, dtype="float64")[old]
        named[f"{s}|{ch}|rw"] = np.asarray(rw, dtype="float64")[old]
        named[f"{s}|{ch}|own"] = np.asarray(sp["own"], dtype="float64")[k]
        named[f"{s}|c"] = np.asarray(ctx.sa[s]["c"], dtype="float64")[k]
        named[f"{s}|okrow"] = np.asarray(ctx.sa[s]["ok"], dtype=bool)[k]
    consts = {"chosen": {f"{t}|{s}": v for (t, s), v in sorted(chosen.items())},
              "typ": {f"{s}|{t}": v for (s, t), v in sorted(ctx.typ.items())},
              "madpop": {"|".join(map(str, key)): v for key, v in sorted(ctx.madpop.items())}}
    named["constants"] = np.asarray([hash_value(consts)])
    return hash_arrays(named, tag="dp/forms/v1")


def decided_z(ctx, chosen: dict) -> dict:
    """The decided forms_z for every box row (the level layer's, as stageB_adjperf.build runs it)."""
    LL, _, _ = _mods()
    dummy = {k: np.full(len(ctx.box_idx), np.nan) for k in LL.FORM_SPECS}
    return LL.forms_z(ctx, chosen, dummy)


def save_z(path: Path, ctx, Z: dict, d0: int) -> dict:
    """The z of the box rows before d0's week, float64, keyed by match id and side."""
    LL, _, _ = _mods()
    rows = ctx.rows
    day = rows["day"].to_numpy()[ctx.box_idx]
    old = day < d0
    t = box_keys(ctx)[old].reset_index(drop=True)
    for s, ch in LL.FORM_SPECS:
        t[f"{s}|{ch}"] = np.asarray(Z[(s, ch)], dtype="float64")[old]
    path.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(path, index=False)
    return {"box_rows": int(len(t)), "bytes": int(path.stat().st_size)}


def load_z(path: Path, ctx, d0: int) -> tuple[dict, np.ndarray]:
    """Saved z onto today's box rows (before d0's week): {pair: z over today's box rows, NaN where not saved}, and the
    mask of today's box rows the saved z cover. Every one of today's old box rows must be in the file."""
    LL, _, _ = _mods()
    t = pd.read_parquet(path)
    keys = box_keys(ctx)
    day = ctx.rows["day"].to_numpy()[ctx.box_idx]
    old = day < d0
    idx = pd.MultiIndex.from_frame(t[["match_id", "side"]].astype(str))
    want = pd.MultiIndex.from_frame(keys[old].astype(str))
    pos = idx.get_indexer(want)
    if (pos < 0).any():
        raise ValueError(f"{int((pos < 0).sum())} of today's box rows before the checkpoint are not in its z")
    out = {}
    for s, ch in LL.FORM_SPECS:
        z = np.full(len(keys), np.nan)
        z[old] = t[f"{s}|{ch}"].to_numpy(dtype="float64")[pos]
        out[(s, ch)] = z
    return out, old


def new_z(ctx, specs: dict, box_pos: np.ndarray) -> dict:
    _, _, FS = _mods()
    return FS.z_for(ctx, specs, np.asarray(box_pos, dtype=np.int64))


def inputs_for(ctx, specs: dict, chosen: dict, Z: dict, pool_pos: np.ndarray) -> dict:
    """The 17 inputs of the chosen pool matches (positions in ctx.A), float64 as computed (stored float32 by the
    builder: apply the cast at assembly)."""
    _, _, FS = _mods()
    return FS.step3_for(ctx, specs, chosen, Z, np.asarray(pool_pos, dtype=np.int64))


def decided_inputs(ctx, chosen: dict, Z: dict) -> dict:
    """The decided step 3 for every pool match (verify_forms_state.py's reference R): {column: values over ctx.A}."""
    LL, AP, _ = _mods()
    feats = {}
    tour_pool = ctx.rows["tour"].to_numpy()[ctx.A]
    for s, ch in LL.FORM_SPECS:
        units, ok = ctx.step3_units(s, ch)
        col = f"{ch}_{s}|decayed"
        feats[col] = np.full(len(ctx.A), np.nan)
        for t in ("atp", "wta"):
            c = AP.constants_for(chosen, s, ch, t)
            sums = LL.forms_step3(ctx, s, ch, [Z[(s, ch)]], units, ok & (ctx.tour_box == t), c["tau"], (c["h3"],))
            kref = ctx.pool_kref(s, c["K3"], c["tau"])
            v, _ = ctx.pool_values(sums, AP.form_key("decayed", c["h3"]), 0, kref, exists_key="career")
            mt = tour_pool == t
            feats[col][mt] = v[mt]
    return feats


# the frame's names of the 17 inputs (tabpfn_thinking/common.FEATURES) -> Stage B's columns
FRAME_NAMES = {"adjperf_tpw_2w": "adjperf_tpw|decayed",
               **{f"form_{s}": f"adjperf_{s}|decayed" for s in ("ace", "df", "first_in", "first_won", "second_won",
                                                               "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
                                                               "rpw_first", "rpw_second")},
               **{f"formdef_{s}": f"adjdef_{s}|decayed" for s in ("ace", "df", "first_in", "bp_faced_pg")}}
