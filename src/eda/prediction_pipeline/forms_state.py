"""Stage B's 17 one-step forms (adjperf / adjdef, two-week half-life) from saved per-match z values.

The decided builder (src/eda/ufc_ideas/stageB_adjperf.py, with the level layer's forms_z and forms_step3 for men)
computes, for every box-score player-match, a per-match z: the player's value against the opponent's norm, the norm a
shrunk, decayed average over the opponent's earlier box-score matches (step 1, the pair moments). Then each player's
form is a decayed, shrunk average of their earlier z (step 3, the as-of sums), and the input is A's form minus B's.

What a daily update needs (and why it is exact):
    z of an earlier match never changes: it reads only the opponent's matches before it (the time rule), the frozen
    constants (pinned under the layer), the 2010-2018 priors and the layer's per-row terms. So the z of every match up to
    the checkpoint is the state, kept in float64 (the builder stores z as float32: not enough).
    A new match's z needs the pair moments of its opponent's row only: this module generates the decided pairs, in the
    decided order, for chosen target rows (moments_for), so each target's sums are the decided ones bit for bit.
    Step 3 is a per-player as-of sum (pandas' grouped sums, with their compensated summation, per player): recomputed on
    the target players' rows alone it equals the whole table's, row for row (step3_for).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _mods():
    from src.eda.lower_level_evidence import level_layer as LL
    from src.eda.ufc_ideas import stageB_adjperf as AP
    from src.eda.ufc_ideas import stageB_common as B
    return LL, AP, B


def pinned_constants() -> dict:
    """Stage B's constants as the layer pins them (the reference build's): {(tour, core stat): {h1, K1, tau, h3, K3}}."""
    LL, _, _ = _mods()
    cfg = LL.config()
    ref = LL.pinned(cfg, "stageB_adjperf")
    out = {}
    for c in ref["chosen"]:
        d = {k: v for k, v in c.items() if k not in ("tour", "stat")}
        for k in ("h1", "K1", "h3", "K3"):
            d[k] = float(d[k])
        d["tau"] = int(d["tau"])
        out[(c["tour"], c["stat"])] = d
    return out


def context():
    """The builder's context on the tree's tables, as stageB_adjperf.main builds it."""
    _, AP, B = _mods()
    rows, _ = B.load_rows()
    means = B.surface_means()
    return AP.Ctx(rows, means)


def inv_order(ctx) -> np.ndarray:
    inv = np.empty(ctx.P.n, dtype=np.int64)
    inv[ctx.P.order] = np.arange(ctx.P.n)
    return inv


def layer_specs(ctx, chosen: dict):
    """forms_z's inputs for the 17 pairs: per pair, the norm values, validity, units and row weights (each in the pair
    index's sorted order), the per-tour constants and the own-value shift. Row-wise arrays: any row's are its own."""
    LL, AP, _ = _mods()
    cfg = LL.active("forms")
    if cfg is None:
        raise RuntimeError("the level layer's forms family is off: set LLE_LAYER")
    K = LL._box_keys(ctx, cfg)
    bucket, tour, season = K["bucket"], K["tour"], K["season"]
    strength = LL.opponent_strength(cfg, K["mids"], K["side"]) if cfg["translate"] else None
    rows = ctx.rows
    r_bucket = LL.buckets_of(rows["match_id"].to_numpy(), cfg)
    r_tour = rows["tour"].to_numpy().astype(str)
    r_season = rows["year"].to_numpy()
    out = {}
    for s, ch in LL.FORM_SPECS:
        name = LL.input_name(s, ch)
        views = LL.form_views(s, ch)
        a, ok, units = ctx.spec(s, ch)
        nstat, nsign = views["norm"]
        T_norm = LL.translation(cfg, name, nstat, tour, bucket, season, strength, nsign, valid=ok)
        a2 = np.where(ok, np.asarray(a, dtype="float64") - T_norm, a)
        w_row = LL.weights(cfg, nstat, tour, bucket, season, "box", valid=ok)
        rw = w_row if cfg["forms_norm_weight"] else np.ones(len(w_row))
        per_tour = {t: AP.constants_for(chosen, s, ch, t) for t in LL.TOURS}
        own = np.zeros(len(rows))
        if cfg["translate"] and cfg["forms_own_delta"]:
            ostat, osign = views["own"]
            own = LL.translation(cfg, name, ostat, r_tour, r_bucket, r_season, None, osign, gamma_term=False,
                                 valid=ctx.sa[s]["ok"])
        step3_rw = LL.weights(cfg, views["step3"][0], tour, bucket, season, "box", valid=None)
        out[(s, ch)] = {"sorted": (ctx.P.to_sorted(a2), ctx.P.to_sorted(ok), ctx.P.to_sorted(units),
                                   ctx.P.to_sorted(rw)), "per_tour": per_tour, "own": own, "step3_view": views["step3"][0]}
    return out


def pairs_for(P, targets: np.ndarray):
    """The decided pairs (target, source, days apart) for chosen sorted target positions, target by target in
    ascending order, each target's sources in the decided order (earlier weeks' run, then the event's earlier rounds)."""
    t = np.asarray(targets, dtype=np.int64)
    L, L1 = P.L[t], P.L1[t]
    tot = int(L.sum())
    tgt = np.repeat(np.arange(len(t), dtype=np.int64), L)          # compact target index
    off = np.repeat(np.cumsum(L) - L, L)
    within = np.arange(tot, dtype=np.int64) - off
    l1 = np.repeat(L1, L)
    src = np.where(within < l1, np.repeat(P.p_start[t], L) + within, np.repeat(P.ev_start[t], L) + (within - l1))
    dt = (P.day_sorted[t][tgt] - P.day_sorted[src]).astype("float64")
    return tgt, src, dt


def moments_for(P, sorted_specs: tuple, targets: np.ndarray, h: float, tau: int):
    """level_layer.pair_moments_w's (S0, S1, M) for the chosen sorted targets only (compact order)."""
    _, _, B = _mods()
    a, valid, units, rw = sorted_specs
    valid = np.asarray(valid, dtype=bool)
    av = np.where(valid, np.nan_to_num(np.asarray(a, dtype="float64")), 0.0)
    un = np.asarray(units, dtype="float64")
    uv = np.where(valid, un ** tau if tau != 0 else 1.0, 0.0) * np.asarray(rw, dtype="float64")
    tgt, src, dt = pairs_for(P, targets)
    m = len(targets)
    w = B.decay(dt, h) * uv[src]
    aa = av[src]
    s0 = np.bincount(tgt, weights=w, minlength=m)
    s1 = np.bincount(tgt, weights=w * aa, minlength=m)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(s0 > 0, s1 / np.where(s0 > 0, s0, 1.0), 0.0)
    M = np.bincount(tgt, weights=w * np.abs(aa - mean[tgt]), minlength=m)
    # the decided sums start at zero and add one chunk's bincount: 0.0 + s is s
    return np.zeros(m) + s0, np.zeros(m) + s1, np.zeros(m) + M


def z_for(ctx, specs: dict, box_pos: np.ndarray, MAD_FLOOR: float | None = None, CLIP: float | None = None) -> dict:
    """The 17 pairs' z at the chosen box positions, as forms_z computes them (the builder's z formula on the layer's
    moments and shifted own values)."""
    _, AP, _ = _mods()
    floor = AP.MAD_FLOOR if MAD_FLOOR is None else MAD_FLOOR
    clip = AP.CLIP if CLIP is None else CLIP
    k = np.asarray(box_pos, dtype=np.int64)
    j = ctx.opp_box[k]                                   # the opponent's row: its moments are the norm
    inv = inv_order(ctx)
    tq = inv[j]                                          # sorted positions of the moments' targets
    tour_k = ctx.tour_box[k]
    out = {}
    for (s, ch), sp in specs.items():
        a = ctx.sa[s]
        c_shift = a["c"] - sp["own"]
        z = np.full(len(k), np.nan)
        for t in ("atp", "wta"):
            sel = tour_k == t
            if not sel.any():
                continue
            c = sp["per_tour"][t]
            S0, S1, M = moments_for(ctx.P, sp["sorted"], tq[sel], c["h1"], c["tau"])
            jj = j[sel]
            kr = np.where(ctx.tour_box[jj] == "atp", c["K1"] * ctx.typ[(s, "atp")] ** c["tau"],
                          c["K1"] * ctx.typ[(s, "wta")] ** c["tau"])
            mp = np.where(ctx.tour_box[jj] == "atp", ctx.madpop[(s, ch, "atp", c["tau"])],
                          ctx.madpop[(s, ch, "wta", c["tau"])])
            E = S1 / (S0 + kr)
            MAD = (M + kr * mp) / (S0 + kr)
            den = np.maximum(MAD, floor)
            mine, theirs = ctx.box_idx[k[sel]], ctx.box_idx[k[sel]] ^ 1
            if ch == "adjperf":
                zz = (c_shift[mine] - E) / den
                ok = a["ok"][mine]
            else:
                zz = (E - c_shift[theirs]) / den
                ok = a["ok"][theirs]
            z[sel] = np.where(ok, np.clip(zz, -clip, clip), np.nan)
        out[(s, ch)] = z
    return out


def step3_for(ctx, specs: dict, chosen: dict, Z: dict, pool_pos: np.ndarray) -> dict:
    """The 17 inputs (A's decayed form minus B's) of the chosen pool matches (positions in ctx.A), from the per-box-row
    z in Z (every box row of the matches' players must be filled), recomputing the as-of sums on those players' rows
    only."""
    LL, AP, B = _mods()
    cfg = LL.active("forms")
    K = LL._box_keys(ctx, cfg)
    pp = np.asarray(pool_pos, dtype=np.int64)
    rows = ctx.rows
    pcode = rows["pcode"].to_numpy()
    players = np.unique(np.r_[pcode[ctx.A[pp]], pcode[ctx.Bi[pp]]])
    u_rows = ctx.U                                         # row indices of the U set (sorted)
    keep_u = np.isin(pcode[u_rows], players)
    u_sel = np.flatnonzero(keep_u)                         # positions in U kept
    frame = ctx.frame.iloc[u_sel].reset_index(drop=True)
    sub_pos = np.full(len(u_rows), -1, dtype=np.int64)
    sub_pos[u_sel] = np.arange(len(u_sel))
    box_in = sub_pos[ctx.u_pos_box]                        # each box row's position in the subset (-1: not kept)
    kb = box_in >= 0
    ia = sub_pos[ctx.ia[pp]]
    ib = sub_pos[ctx.ib[pp]]
    if (ia < 0).any() or (ib < 0).any():
        raise RuntimeError("a pool row is missing from the subset")
    tour_pool = rows["tour"].to_numpy()[ctx.A[pp]]
    feats = {}
    for (s, ch), sp in specs.items():
        units, ok = ctx.step3_units(s, ch)
        rw = LL.weights(cfg, sp["step3_view"], K["tour"], K["bucket"], K["season"], "box", valid=ok)
        z = Z[(s, ch)]
        col = f"{ch}_{s}|decayed"
        v_out = np.full(len(pp), np.nan)
        for t in ("atp", "wta"):
            c = sp["per_tour"][t]
            okt = ok & (ctx.tour_box == t)
            w = np.where(okt, units ** c["tau"] if c["tau"] else 1.0, 0.0) * rw
            V = np.zeros((len(u_sel), 3))
            V[box_in[kb], 0] = np.where(okt, w * np.nan_to_num(z), 0.0)[kb]
            V[box_in[kb], 1] = w[kb]
            V[box_in[kb], 2] = (np.asarray(okt, bool) & (rw > 0)).astype("float64")[kb]
            sums = B.windowed_sums(frame, V, [h for h in (c["h3"],) if np.isfinite(h)])
            fk = AP.form_key("decayed", c["h3"])
            kref_a = np.where(tour_pool == "atp", c["K3"] * ctx.typ[(s, "atp")] ** c["tau"],
                              c["K3"] * ctx.typ[(s, "wta")] ** c["tau"])
            S_, ex = sums[fk], sums["career"][:, 2]
            val_a = S_[ia, 0] / (S_[ia, 1] + kref_a)
            val_b = S_[ib, 0] / (S_[ib, 1] + kref_a)
            e = (ex[ia] > 0.5) & (ex[ib] > 0.5)
            v = np.where(e, val_a - val_b, np.nan)
            mt = tour_pool == t
            v_out[mt] = v[mt]
        feats[col] = v_out
    return feats
