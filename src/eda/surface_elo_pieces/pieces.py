"""Build the surface pieces for every match (all 872,704, every level, 2010-2026): Elo's parts and the surface-switch
quantities, each for player A and player B.

Elo (one pass per tour and variant, Stage 1's constants and its time rule: a rating used for a match includes earlier
events and earlier rounds of the same event, never other matches of the same round or other events of the same week;
retirements counted, walkovers and "other" never move ratings):

    stage1     Stage 1's pass, reproduced exactly (checked against stage1_baselines.parquet): the overall rating R, its
               rated-match count N, the surface rating S (moved only by matches on that surface, starting at 1500) and
               its count NS.
    anchored   the same, except that a player's surface rating starts at their overall rating at their first match on
               that surface instead of at 1500 (Stage 1's K schedule on the surface count).
    offset     a surface offset D that starts at 0 and is moved only by matches on that surface, by the surprise of the
               combined forecast expected(R_A + D_A, R_B + D_B), with its own K(n) = kd0 / (n + kd_off) ** kd_shape on
               the surface count. The overall rating is Stage 1's, unchanged. kd0 is tuned per tour on the log loss of
               the evaluation matches of 2013-2018 (constants frozen before anything later is scored).
    surface-blind offset (DG, a control from the audit): the same offset with every known surface mapped to one code,
               so it moves on every match; tuned the same way. If the offset's gain were a general correction of the
               overall rating rather than surface structure, this control would match it.

Surface switches (per player, this match's surface; history = every level; played = completed or retired):

    season_n        earlier played matches on the surface this calendar season (Stage 4's surface_first counts this and
                    flags fewer than 3), under the time rule
    days_since      days from the player's last earlier played match on the surface to this match, on the match-timing
                    study's best-estimate days (obs); missing if none since 2010
    prev_n          played matches on the surface last calendar season
    prev_res        last season's surface form: the sum over those matches of (won - P(won) from overall Elo), the wins
                    above what the player's overall rating expected on that surface

Writes data/studies/surface_elo_pieces/pieces.parquet (one row per match, Stage 0's order) and pieces_meta.json
(constants, tuning grid, reproduction check, leak probe).
Run: ./python.sh src/eda/surface_elo_pieces/pieces.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PC  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.predictability_diagnostic.stage4_features import prev_visible  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.lower_level_evidence import level_layer as _LLE  # noqa: E402  level layer (LLE_LAYER)

START = B.START
# A first grid (kd_off 2 and 10, kd_shape 0.4 and 0.6) put the best at its corner for both tours; this one reaches
# past it so that the best lies inside (the surface is a flat valley: a larger kd0 trades against a larger shape)
KD_GRID = {"kd0": [20.0, 40.0, 60.0, 80.0, 120.0, 160.0, 240.0, 320.0], "kd_off": [2.0, 10.0, 20.0, 40.0],
           "kd_shape": [0.4, 0.6, 0.8]}
STAGE0_COLS = ["match_id", "tour", "year", "level", "qualifying", "evaluation", "status", "surface", "tournament_id",
               "tournament_date", "round_order", "player_a_id", "player_b_id", "a_won", "order"]


# ------------------------------------------------------------------------------------------------
# Elo with three surface variants under Stage 1's time rule

def elo_pass_ext(week, event, rnd, a, b, a_won, surf, upd, n_players: int, k0: float, offset: float, shape: float,
                 mode: str = "stage1", kd0: float = 0.0, kd_off: float = 1.0, kd_shape: float = 0.5) -> np.ndarray:
    """Stage 1's elo_pass with a second surface state X. Returns one row per match:
    R_A, R_B, N_A, N_B, S_A, S_B, NS_A, NS_B (exactly Stage 1's), X_A, X_B, where X is

        mode "stage1"    a copy of S (no second state)
        mode "anchored"  the surface rating started at the player's overall rating at their first match on the surface
        mode "offset"    the surface offset D (starts at 0, K(n) = kd0 / (n + kd_off) ** kd_shape on the surface count,
                         moved by the surprise of expected(R_A + D_A, R_B + D_B))

    Pending updates follow Stage 1 exactly: an event's earlier rounds reach its later rounds, an event's results reach
    the player's other events only once the tournament week is over."""
    R = [START] * n_players
    N = [0] * n_players
    RS = [[START] * n_players for _ in C.SURFACES]
    NS = [[0] * n_players for _ in C.SURFACES]
    X = [[0.0 if mode == "offset" else START] * n_players for _ in C.SURFACES]
    INIT = [[False] * n_players for _ in C.SURFACES]
    out = np.full((len(week), 10), np.nan)
    lo: dict = {}
    ls: dict = {}
    lx: dict = {}
    cur = None

    def entry(d, key, r):
        x = d.get(key)
        if x is None:
            x = d[key] = [0.0, 0, r, 0.0, 0]
        elif x[2] < r:
            x[0] += x[3]; x[1] += x[4]; x[2] = r; x[3] = 0.0; x[4] = 0
        return x

    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R[p] += st[0] + st[3]
                N[p] += st[1] + st[4]
            for (p, _, s), st in ls.items():
                RS[s][p] += st[0] + st[3]
                NS[s][p] += st[1] + st[4]
            for (p, _, s), st in lx.items():
                X[s][p] += st[0] + st[3]
            lo.clear(); ls.clear(); lx.clear()
            cur = week[i]
        e, r, s, pa, pb = event[i], rnd[i], surf[i], a[i], b[i]
        xa, xb = entry(lo, (pa, e), r), entry(lo, (pb, e), r)
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra, rb, na, nb
        do_s = s >= 0
        if do_s:
            ya, yb = entry(ls, (pa, e, s), r), entry(ls, (pb, e, s), r)
            sa, sb, nsa, nsb = RS[s][pa] + ya[0], RS[s][pb] + yb[0], NS[s][pa] + ya[1], NS[s][pb] + yb[1]
            out[i, 4], out[i, 5], out[i, 6], out[i, 7] = sa, sb, nsa, nsb
            if mode == "anchored":
                # a player's first surface rating is their overall rating as used for this match (earlier events and
                # this event's earlier rounds only); same value for every match of the round, so no round-robin leak
                for p, rr in ((pa, ra), (pb, rb)):
                    if not INIT[s][p]:
                        X[s][p] = rr
                        INIT[s][p] = True
            za, zb = entry(lx, (pa, e, s), r), entry(lx, (pb, e, s), r)
            xa_s, xb_s = X[s][pa] + za[0], X[s][pb] + zb[0]
            out[i, 8], out[i, 9] = (sa, sb) if mode == "stage1" else (xa_s, xb_s)
        if upd[i]:
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            xa[3] += upd[i] * k0 / (na + offset) ** shape * surprise   # level layer (LLE_LAYER): upd[i] True or w
            xb[3] -= upd[i] * k0 / (nb + offset) ** shape * surprise
            xa[4] += upd[i]
            xb[4] += upd[i]
            if do_s:
                surprise_s = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                ya[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_s
                yb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_s
                ya[4] += upd[i]
                yb[4] += upd[i]
                if mode == "anchored":
                    surprise_x = res - 1.0 / (1.0 + 10.0 ** ((xb_s - xa_s) / 400.0))
                    za[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_x
                    zb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_x
                elif mode == "offset":
                    surprise_c = res - 1.0 / (1.0 + 10.0 ** (((rb + xb_s) - (ra + xa_s)) / 400.0))
                    za[3] += upd[i] * kd0 / (nsa + kd_off) ** kd_shape * surprise_c
                    zb[3] -= upd[i] * kd0 / (nsb + kd_off) ** kd_shape * surprise_c
    return out


def run(h: dict, upd: list, k: dict, mode: str, kd: dict | None = None) -> np.ndarray:
    kd = kd or {}
    return elo_pass_ext(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"],
                        k["k0"], k["offset"], k["shape"], mode=mode, **kd)


def tune_offset(t: pd.DataFrame, h: dict, upd: list, k: dict) -> tuple[dict, list]:
    """kd0, kd_off, kd_shape with the lowest log loss of expected(R_A + D_A, R_B + D_B) on the tour's evaluation
    matches of 2013-2018, the pass run on the history up to the end of 2018 only."""
    last = int(np.flatnonzero(t["year"].le(C.TUNE_YEARS[1]).to_numpy()).max())
    he = {kk: (v[:last + 1] if isinstance(v, list) else v) for kk, v in h.items()}
    rows = (t["evaluation"].to_numpy()[:last + 1] & t["year"].between(*C.TUNE_YEARS).to_numpy()[:last + 1]
            & t["status"].isin(["completed", "retired"]).to_numpy()[:last + 1] & (np.asarray(h["surf"][:last + 1]) >= 0))
    y = t["a_won"].to_numpy(bool)[:last + 1][rows]
    grid, best = [], None
    for kd0 in KD_GRID["kd0"]:
        for kd_off in KD_GRID["kd_off"]:
            for kd_shape in KD_GRID["kd_shape"]:
                kd = {"kd0": kd0, "kd_off": kd_off, "kd_shape": kd_shape}
                o = run(he, upd[:last + 1], k, "offset", kd)
                p = B.expected(o[rows, 0] + o[rows, 8], o[rows, 1] + o[rows, 9])
                v = C.mean_ll(p, y)
                grid.append({**kd, "log_loss_2013_2018": v, "matches": int(rows.sum())})
                if best is None or v < best[0]:
                    best = (v, kd)
    o0 = run(he, upd[:last + 1], k, "stage1")
    p0 = B.expected(o0[rows, 0], o0[rows, 1])
    grid.append({"kd0": 0.0, "kd_off": np.nan, "kd_shape": np.nan, "log_loss_2013_2018": C.mean_ll(p0, y),
                 "matches": int(rows.sum()), "note": "overall Elo alone"})
    return best[1], grid


# ------------------------------------------------------------------------------------------------
# Surface-switch quantities

def player_rows(m: pd.DataFrame, obs: np.ndarray, p_overall: np.ndarray) -> pd.DataFrame:
    """Two rows per match (A then B) in Stage 0's order."""
    n = len(m)
    rows = pd.DataFrame({
        "match_id": np.repeat(m["match_id"].to_numpy(), 2),
        "player_id": np.column_stack([m["player_a_id"].to_numpy(), m["player_b_id"].to_numpy()]).reshape(-1),
        "tour": np.repeat(m["tour"].to_numpy(), 2), "year": np.repeat(m["year"].to_numpy(), 2),
        "surf": np.repeat(m["surface"].map({s: i for i, s in enumerate(C.SURFACES)}).fillna(-1).astype(int).to_numpy(), 2),
        "tournament_date": np.repeat(m["tournament_date"].to_numpy(), 2),
        "tournament_id": np.repeat(m["tournament_id"].to_numpy(), 2),
        "round_order": np.repeat(m["round_order"].to_numpy(), 2),
        "order": np.repeat(m["order"].to_numpy(), 2),
        "played": np.repeat(m["status"].isin(["completed", "retired"]).to_numpy(), 2),
        "won": np.column_stack([m["a_won"].to_numpy(bool), ~m["a_won"].to_numpy(bool)]).reshape(-1),
        "obs": np.repeat(obs, 2),
        "p_own": np.column_stack([p_overall, 1 - p_overall]).reshape(-1),
    })
    rows["day"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    rows["ev"] = pd.factorize(rows["tournament_id"].astype(str) + "|" + rows["tournament_date"].astype(str))[0]
    rows["pcode"] = pd.factorize(rows["tour"] + "|" + rows["player_id"])[0]
    assert len(rows) == 2 * n
    return rows


def surface_switch(rows: pd.DataFrame) -> pd.DataFrame:
    """season_n, days_since, prev_n, prev_res for every player row (missing where the surface is unknown)."""
    surf = rows["surf"].to_numpy()
    known = surf >= 0
    pcode = rows["pcode"].to_numpy().astype("int64")
    year = rows["year"].to_numpy().astype("int64")
    played = rows["played"].to_numpy(bool)
    # this season's earlier played matches on the surface (Stage 4's season_surface_played, same rule)
    tmp = rows[["tournament_date", "tournament_id", "round_order"]].copy()
    tmp["_k"] = (pcode * 30 + (year - 2009)) * 8 + np.where(known, surf, 7)
    tmp["_v"] = played.astype("float64")
    season_n = PC.asof_sums(tmp, ["_v"], player="_k")["_v"].to_numpy()
    # the previous visible played match on the same surface (any season)
    key = pcode * 8 + np.where(known, surf, 7)
    prev = prev_visible(rows, played & known, key)
    obs = rows["obs"].to_numpy(dtype="float64")
    days_since = np.where(prev >= 0, np.maximum(obs - obs[np.maximum(prev, 0)], 0.0), np.nan)
    # last season on the surface: count and wins above overall Elo's expectation
    res = np.where(played & known, rows["won"].to_numpy(float) - rows["p_own"].to_numpy(float), 0.0)
    g = pd.DataFrame({"k": (pcode * 30 + (year - 2009)) * 8 + np.where(known, surf, 7),
                      "n": (played & known).astype("float64"), "res": res}).groupby("k")[["n", "res"]].sum()
    look = (pcode * 30 + (year - 1 - 2009)) * 8 + np.where(known, surf, 7)
    prev_n = g["n"].reindex(look).fillna(0.0).to_numpy()
    prev_res = g["res"].reindex(look).fillna(0.0).to_numpy()
    nan = np.where(known, 1.0, np.nan)
    return pd.DataFrame({"season_n": season_n * nan, "days_since": days_since * nan, "prev_n": prev_n * nan,
                         "prev_res": prev_res * nan}, index=rows.index)


def leak_probe(m: pd.DataFrame, obs: np.ndarray, p_overall: np.ndarray, n_cuts: int = 6, seed: int = 20261006) -> dict:
    """Two black-box probes of the surface-switch values, at random cuts (by Stage 0's order, which follows tournament
    dates). The values of every match of an earlier tournament week must not move when

        flip       every result at or after the cut is flipped (with its overall-Elo forecast): moves prev_res if it
                   read a later result
        truncate   every match from the cut's week on is deleted: moves season_n, days_since, prev_n or prev_res if
                   any of them read a later match at all (the audit's G1: dates and statuses alone cannot be flipped)
    """
    rng = np.random.default_rng(seed)
    base = surface_switch(player_rows(m, obs, p_overall)).to_numpy()
    week_m = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    week = np.repeat(week_m, 2)
    order = m["order"].to_numpy()
    cand = order[order >= np.quantile(order, 0.6)]
    out = []
    for c in rng.choice(cand, size=n_cuts, replace=False):
        cut_week = int(week_m[np.flatnonzero(order == c)[0]])
        protected = week < cut_week
        late = order >= c
        mm = m.copy()
        mm.loc[late, "a_won"] = ~mm.loc[late, "a_won"].to_numpy(bool)
        pp = np.where(late, 1 - p_overall, p_overall)            # the overall forecast is a pre-match input
        got = surface_switch(player_rows(mm, obs, pp)).to_numpy()
        moved = ~np.all(np.isclose(got, base, equal_nan=True), axis=1)
        keep = week_m < cut_week
        tr = surface_switch(player_rows(m[keep].reset_index(drop=True), obs[keep], p_overall[keep])).to_numpy()
        moved_tr = ~np.all(np.isclose(tr, base[np.repeat(keep, 2)], equal_nan=True), axis=1)
        out.append({"cut_order": int(c), "protected_rows": int(protected.sum()),
                    "flip_protected_moved": int((moved & protected).sum()),
                    "flip_later_moved": int((moved & ~protected).sum()),
                    "truncate_rows_checked": int(len(tr)), "truncate_moved": int(moved_tr.sum())})
    total = sum(o["flip_protected_moved"] + o["truncate_moved"] for o in out)
    return {"cuts": out, "protected_moved_total": int(total)}


def elo_probes(h: dict, upd: list, k: dict, kd: dict, kd_gen: dict, h_gen: dict) -> dict:
    """Stage 1's date-and-round probe (stage1_baselines.probe_by_round) on the anchored, offset and surface-blind offset
    passes: results flipped at random from a cut on (the cut's round, the week's other events, every later week) must
    not move any match of an earlier week or of the cut event's rounds up to the cut's (the audit's G1)."""
    out = {}
    for name, mode, kk, hh in (("anchored", "anchored", {}, h), ("offset", "offset", kd, h),
                               ("offset_surface_blind", "offset", kd_gen, h_gen)):
        def ratings(x, mode=mode, kk=kk):
            return run(x, upd, k, mode, kk)
        out[name] = B.probe_by_round(hh, ratings, n_cuts=4, from_quantile=0.85)
    return out


# ------------------------------------------------------------------------------------------------

def main() -> int:
    C.OUT.mkdir(parents=True, exist_ok=True)
    m = pd.read_parquet(C.STAGE0, columns=STAGE0_COLS)
    assert (np.diff(m["order"].to_numpy()) > 0).all(), "Stage 0 must be in its chronological order"
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "obs"]).set_index("match_id").reindex(m["match_id"])
    obs = tm["obs"].to_numpy(dtype="float64")
    assert np.isfinite(obs).all()
    s1 = pd.read_parquet(C.STAGE1).set_index("match_id").reindex(m["match_id"])
    chosen = {(c["tour"], c["rule"]): c for c in json.loads(C.STAGE1_SUMMARY.read_text())["chosen"]}
    cols = ["R_a", "R_b", "N_a", "N_b", "S_a", "S_b", "NS_a", "NS_b"]
    out = pd.DataFrame({"match_id": m["match_id"].to_numpy(), "tour": m["tour"].to_numpy(), "year": m["year"].to_numpy()})
    meta = {"kd_grid": KD_GRID, "stage1_constants": {}, "offset_constants": {}, "tuning": [], "reproduction": {},
            "offset_surface_blind_constants": {}, "tuning_surface_blind": [], "elo_probes": {}}
    for c in cols + ["XA_a", "XA_b", "D_a", "D_b", "DG_a", "DG_b"]:
        out[c] = np.nan
    for tour in C.TOURS:
        sel = m["tour"].eq(tour).to_numpy()
        t = m[sel].reset_index(drop=True)
        h = B.history_arrays(t)
        upd = t["status"].isin(B.UPDATES["ret"]).tolist()
        upd0, upd = upd, _LLE.elo_weights(t, upd)   # level layer (LLE_LAYER): the passes read upd, the tuning upd0
        k = {kk: float(chosen[(tour, "ret")][kk]) for kk in ("k0", "offset", "shape")}
        meta["stage1_constants"][tour] = {**k, "w": chosen[(tour, "ret")]["w"]}
        o1 = run(h, upd, k, "stage1")
        st = s1[sel]
        ref = st[["elo_a_ret", "elo_b_ret", "n_a_ret", "n_b_ret", "elo_surf_a_ret", "elo_surf_b_ret",
                  "n_surf_a_ret", "n_surf_b_ret"]].to_numpy(dtype="float64")
        err = np.nanmax(np.abs(o1[:, :8].astype("float32").astype("float64") - ref))
        same_nan = bool((np.isnan(o1[:, :8]) == np.isnan(ref)).all())
        meta["reproduction"][tour] = {"max_abs_diff_vs_stage1_float32": float(err), "same_missing": same_nan}
        if not (same_nan and err < 1e-3):
            raise RuntimeError(f"{tour}: the pass does not reproduce Stage 1 (max diff {err})")
        C.log(f"{tour}: Stage 1 reproduced (max diff {err:.2e})")
        oa = run(h, upd, k, "anchored")
        assert np.allclose(oa[:, :8], o1[:, :8], equal_nan=True)
        kd, grid = tune_offset(t, h, upd0, k)   # level layer (LLE_LAYER)
        meta["offset_constants"][tour] = kd
        meta["tuning"] += [{"tour": tour, **g} for g in grid]
        C.log(f"{tour}: offset constants {kd}")
        od = run(h, upd, k, "offset", kd)
        assert np.allclose(od[:, :8], o1[:, :8], equal_nan=True)
        # the audit's control: the same offset with every known surface mapped to one code, so that it moves on every
        # match (a second, general correction of the overall rating); tuned on the same rows and grid
        h_gen = {**h, "surf": [0 if s >= 0 else -1 for s in h["surf"]]}
        kd_gen, grid_gen = tune_offset(t, h_gen, upd0, k)   # level layer (LLE_LAYER)
        meta["offset_surface_blind_constants"][tour] = kd_gen
        meta["tuning_surface_blind"] += [{"tour": tour, **g} for g in grid_gen]
        og = run(h_gen, upd, k, "offset", kd_gen)
        C.log(f"{tour}: surface-blind offset constants {kd_gen}")
        meta["elo_probes"][tour] = elo_probes(h, upd, k, kd, kd_gen, h_gen)
        C.log(f"{tour}: Elo probes {meta['elo_probes'][tour]}")
        if any(v["protected_matches_changed"] for v in meta["elo_probes"][tour].values()):
            raise RuntimeError(f"{tour}: an Elo pass moved a protected match when later results changed")
        for j, c in enumerate(cols):
            out.loc[sel, c] = o1[:, j]
        out.loc[sel, "XA_a"], out.loc[sel, "XA_b"] = oa[:, 8], oa[:, 9]
        out.loc[sel, "D_a"], out.loc[sel, "D_b"] = od[:, 8], od[:, 9]
        out.loc[sel, "DG_a"], out.loc[sel, "DG_b"] = og[:, 8], og[:, 9]
    p_overall = B.expected(out["R_a"].to_numpy(), out["R_b"].to_numpy())
    rows = player_rows(m, obs, p_overall)
    sw = surface_switch(rows)
    for c in sw.columns:
        v = sw[c].to_numpy()
        out[f"{c}_a"], out[f"{c}_b"] = v[0::2], v[1::2]
    meta["leak_probe_surface_switch"] = leak_probe(m, obs, p_overall)
    C.log(f"leak probe: {meta['leak_probe_surface_switch']['protected_moved_total']} protected rows moved")
    if meta["leak_probe_surface_switch"]["protected_moved_total"]:
        raise RuntimeError("a surface-switch value moved when only later results changed")
    out.to_parquet(C.PIECES, index=False, compression="zstd")
    meta["rows"] = int(len(out))
    meta["generated_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    C.write_json(C.OUT / "pieces_meta.json", meta)
    C.log(f"wrote {C.PIECES.name}: {len(out):,} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
