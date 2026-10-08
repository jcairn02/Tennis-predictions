"""R4 red team (auditor): my own leak probes on the BUILT code (panel.py's EditionOffsets; features.py's histories,
snapshot_gammas and side_values), with my own cuts, perturbations, comparisons and leaky controls. Values only.

Probe A (own history, Stage 0 order). Sample: 20,000 frame sides 2014-2026 (8,000 of them 2024-26). For each cut c (30
cuts at the order of a sampled timed side; 12 in 2024-26) every panel row with order >= c gets y + 30 km/h. The filter
input and the registered windows take the perturbed panel directly (no y_override hook); the snapshots stay at the
clean build (the order cut is not a clock cut: C7). Checks:
    clean      no side value (f_hat, f_sd, L_hat, x_raw) of a target with order < c or = c moves (tolerance 1e-12)
    power      targets with order > c whose history holds a perturbed row move (the perturbation propagates)
    leaky L1   the target's own row appended to its history: some target AT the cut moves
    leaky L2   the player's NEXT own row appended to its history: some target BEFORE the cut whose next row is
               perturbed moves
Probe B (clock). 30 cut days inside events (a Slam's second-week Wednesday, a big tour event's Thursday), 2019-26,
17 in 2024-26. Every panel row with es > D gets y + 30 km/h (and, on 5 days, U(100, 250) noise instead) in BOTH the
filter input and the snapshot input; EditionOffsets is rebuilt on the perturbed panel. Checks:
    clean      no value (f_hat, f_sd, L_hat, x_raw, the summed gammas used) of ANY frame side with lf <= D moves
    gamma      gamma(D'), D' in {D, D - 1, D - 3, D - 7}: identical (every edition)
    power      sides with es > D (a 3,000 sample) move
    leaky L1   rows released at their tournament date instead of lf + 1 (lf := tdate - 1 in the DATA, not the
               module's release option): some side with lf <= D moves
    leaky L2   the player's next own row appended: some side with lf <= D whose next row has es > D moves

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_r4_probes.py
Writes data/studies/serve_speed_tabpfn/design/auditor_r4_probes.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design" / "auditor_r4_probes.json"
VALS_A = ["f_hat", "f_sd", "L_hat", "x_raw"]
VALS_B = ["f_hat", "f_sd", "L_hat", "x_raw", "g_sum", "g_abs"]
SHIFT = 30.0
TOL = 1e-12
RNG = np.random.default_rng(4242)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def moved(a: pd.DataFrame, b: pd.DataFrame, cols: list[str]) -> np.ndarray:
    m = np.zeros(len(a), bool)
    for c in cols:
        x, y = a[c].to_numpy(float), b[c].to_numpy(float)
        m |= ~(np.isclose(x, y, rtol=0.0, atol=TOL) | (np.isnan(x) & np.isnan(y)))
    return m


def own_and_next(p: pd.DataFrame, t: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per target side: the position in p of its own row (the frame match's rebuilt id and the player), and of the
    player's next row in own order (-1 where none)."""
    key = pd.Series(np.arange(len(p)), index=pd.MultiIndex.from_arrays([p["match_id"].astype(str),
                                                                         p["player_id"].astype(str)]))
    key = key[~key.index.duplicated()]
    own = key.reindex(pd.MultiIndex.from_arrays([t["rebuilt_id"].astype(str), t["player_id"].astype(str)])) \
        .fillna(-1).astype(np.int64).to_numpy()
    # p is in own order per player (prepare_panel): the next row is the next position with the same player
    same_next = np.r_[p["player_id"].to_numpy()[1:] == p["player_id"].to_numpy()[:-1], False]
    nxt = np.where(own >= 0, np.where(same_next[np.maximum(own, 0)], own + 1, -1), -1)
    return own, nxt


def probe_a(B: dict) -> dict:
    p, t, offsets = B["p"], B["t"], B["offsets"]
    p_order = F.stage0_order(p["match_id"]).to_numpy(float)
    t_order = F.stage0_order(t["rebuilt_id"]).to_numpy(float)
    own, nxt = own_and_next(p, t)
    ok = np.isfinite(t_order) & t["es"].notna().to_numpy() & t["season"].ge(2014).to_numpy()
    late = np.flatnonzero(ok & t["season"].between(2024, 2026).to_numpy())
    early = np.flatnonzero(ok & ~t["season"].between(2024, 2026).to_numpy())
    pick = np.sort(np.concatenate([RNG.choice(late, 8000, replace=False), RNG.choice(early, 12000, replace=False)]))
    S = t.iloc[pick].reset_index(drop=True)
    So, Sown, Snext = t_order[pick], own[pick], nxt[pick]
    Snext_order = np.where(Snext >= 0, p_order[np.maximum(Snext, 0)], np.nan)
    h0 = F.histories(p, S)
    G0 = F.snapshot_gammas(p, S, h0["idx"], offsets)
    base = F.side_values(p, S, offsets, hist=h0, G=G0)
    hL1 = F.histories(p, S, extra_own=Sown)
    GL1 = F.snapshot_gammas(p, S, hL1["idx"], offsets)
    baseL1 = F.side_values(p, S, offsets, hist=hL1, G=GL1)
    hL2 = F.histories(p, S, extra_own=Snext)
    GL2 = F.snapshot_gammas(p, S, hL2["idx"], offsets)
    baseL2 = F.side_values(p, S, offsets, hist=hL2, G=GL2)
    timed = Sown >= 0
    late_c = np.unique(So[timed & S["season"].between(2024, 2026).to_numpy()])
    early_c = np.unique(So[timed & ~S["season"].between(2024, 2026).to_numpy()])
    cuts = np.sort(np.concatenate([RNG.choice(late_c, 12, replace=False), RNG.choice(early_c, 18, replace=False)]))
    recs = []
    for c in cuts:
        q = p.copy()
        q.loc[p_order >= c, "y"] = q.loc[p_order >= c, "y"] + SHIFT
        hq = F.histories(q, S)                         # the same rows; the registered windows read q's y
        got = F.side_values(q, S, offsets, hist=hq, G=G0)
        mv = moved(base, got, VALS_A)
        before, at, after = So < c, So == c, So > c
        gotL1 = F.side_values(q, S, offsets, hist=F.histories(q, S, extra_own=Sown), G=GL1)
        gotL2 = F.side_values(q, S, offsets, hist=F.histories(q, S, extra_own=Snext), G=GL2)
        # the robust filter clips an innovation at c SDs: a +30 shift is invisible when the leaked row is already a
        # clipped high outlier, so the leaky control also tries -30
        q2 = p.copy()
        q2.loc[p_order >= c, "y"] = q2.loc[p_order >= c, "y"] - SHIFT
        gotL1m = F.side_values(q2, S, offsets, hist=F.histories(q2, S, extra_own=Sown), G=GL1)
        mL1 = moved(baseL1, gotL1, ["f_hat"]) | moved(baseL1, gotL1m, ["f_hat"])
        mL2 = moved(baseL2, gotL2, ["f_hat"])
        l2_pool = before & (Snext_order >= c)
        r = {"cut_order": float(c), "season": int(S.loc[at, "season"].iloc[0]),
             "before": int(before.sum()), "at": int(at.sum()), "moved_before": int((mv & before).sum()),
             "moved_at": int((mv & at).sum()), "power_moved_after": int((mv & after).sum()),
             "leaky_L1_moved_at": int((mL1 & at & timed).sum()),
             "leaky_L2_pool": int(l2_pool.sum()), "leaky_L2_moved_before": int((mL2 & l2_pool).sum())}
        r["pass"] = (r["moved_before"] == 0 and r["moved_at"] == 0 and r["power_moved_after"] > 0
                     and r["leaky_L1_moved_at"] > 0 and (r["leaky_L2_moved_before"] > 0 or r["leaky_L2_pool"] == 0))
        recs.append(r)
        log(f"A cut {c:.0f} ({r['season']}): before {r['moved_before']}/{r['before']}, at {r['moved_at']}/{r['at']}, "
            f"power {r['power_moved_after']}, L1 {r['leaky_L1_moved_at']}, L2 {r['leaky_L2_moved_before']}/"
            f"{r['leaky_L2_pool']} -> {'ok' if r['pass'] else 'FAIL'}")
    return {"sides": int(len(S)), "sides_2024_26": int(S["season"].between(2024, 2026).sum()), "cuts": len(cuts),
            "cuts_2024_26": int(sum(r["season"] >= 2024 for r in recs)),
            "moved_before_total": int(sum(r["moved_before"] for r in recs)),
            "moved_at_total": int(sum(r["moved_at"] for r in recs)),
            "leaky_L1_fired": int(sum(r["leaky_L1_moved_at"] > 0 for r in recs)),
            "leaky_L2_fired": int(sum(r["leaky_L2_moved_before"] > 0 for r in recs)),
            "leaky_L2_with_pool": int(sum(r["leaky_L2_pool"] > 0 for r in recs)),
            "pass": all(r["pass"] for r in recs), "per_cut": recs}


def cut_days(keys: pd.DataFrame, p: pd.DataFrame) -> list[tuple[float, str]]:
    """Inside-event days: each Slam main draw of 2021-2026 in the frame at tournament date + 9 (its second week), and
    the two non-Slam events with most frame matches in each of 2023-2026 at tournament date + 3."""
    k = keys[["season", "level", "tdate", "tournament_id"]]
    out = []
    sl = k[k["level"].eq("GS") & k["season"].between(2021, 2026)].drop_duplicates("tournament_id")
    for _, r in sl.iterrows():
        out.append((float(r["tdate"] + 9), f"slam {r['tournament_id']}"))
    ns = k[~k["level"].eq("GS") & k["season"].between(2023, 2026)]
    top = ns.groupby(["season", "tournament_id", "tdate"]).size().reset_index(name="n")
    for s, g in top.groupby("season"):
        for _, r in g.sort_values("n", ascending=False).head(2).iterrows():
            out.append((float(r["tdate"] + 3), f"tour {r['tournament_id']}"))
    return sorted(set(out))


def probe_b(B: dict) -> dict:
    p, t, keys, offsets = B["p"], B["t"], B["keys"], B["offsets"]
    base_all = B["sv"]
    own, nxt = own_and_next(p, t)
    es_p = p["es"].to_numpy(float)
    t_lf, t_es = t["lf"].to_numpy(float), t["es"].to_numpy(float)
    nxt_es = np.where(nxt >= 0, es_p[np.maximum(nxt, 0)], np.nan)
    days = cut_days(keys, p)
    noise_days = set(d for d, _ in days[::6])
    recs = []
    p_leak = p.copy()
    p_leak["lf"] = p_leak["tdate"] - 1                 # released at the tournament date: a leak built in the data
    for D, label in days:
        late = es_p > D
        q = p.copy()
        if D in noise_days:
            q.loc[late, "y"] = RNG.uniform(100.0, 250.0, int(late.sum()))
        else:
            q.loc[late, "y"] = q.loc[late, "y"] + SHIFT
        off_q = {tour: P.EditionOffsets(q, tour, cache=False) for tour in ("atp", "wta")}
        chk = np.flatnonzero(t_lf <= D)
        got = F.side_values(q, t.iloc[chk], off_q)
        mv = moved(base_all.iloc[chk], got, VALS_B)
        # gamma at D and before
        gdiff = 0.0
        for tour in ("atp", "wta"):
            for dd in (D, D - 1, D - 3, D - 7):
                a = offsets[tour].at(int(dd)).to_numpy()
                b = off_q[tour].at(int(dd)).to_numpy()
                gdiff = max(gdiff, float(np.max(np.abs(a - b))))
        # power: sides with es > D (sample)
        after = np.flatnonzero(t_es > D)
        smp = RNG.choice(after, min(3000, len(after)), replace=False) if len(after) else after
        gp = F.side_values(q, t.iloc[smp], off_q)
        power = int(moved(base_all.iloc[smp], gp, VALS_B).sum()) if len(smp) else 0
        # leaky L1: released at the tournament date (in the data)
        near = np.flatnonzero((t_lf <= D) & (t_es >= D - 28.0))
        q_leak = q.copy()
        q_leak["lf"] = q_leak["tdate"] - 1
        TN = t.iloc[near]
        l0 = F.side_values(p_leak, TN, {tr: P.EditionOffsets(p_leak, tr, cache=False) for tr in ("atp", "wta")})
        l1 = F.side_values(q_leak, TN, {tr: P.EditionOffsets(q_leak, tr, cache=False) for tr in ("atp", "wta")})
        L1 = int(moved(l0, l1, ["f_hat", "g_sum"]).sum())
        # leaky L2: the next own row appended (sides with lf <= D whose next row starts after D)
        pool = np.flatnonzero((t_lf <= D) & (nxt_es > D))
        if len(pool) > 4000:
            pool = RNG.choice(pool, 4000, replace=False)
        T2 = t.iloc[pool]
        h_c = F.histories(p, T2, extra_own=nxt[pool])
        h_q = F.histories(q, T2, extra_own=nxt[pool])
        a2 = F.side_values(p, T2, offsets, hist=h_c, G=F.snapshot_gammas(p, T2, h_c["idx"], offsets))
        b2 = F.side_values(q, T2, off_q, hist=h_q, G=F.snapshot_gammas(q, T2, h_q["idx"], off_q))
        L2 = int(moved(a2, b2, ["f_hat"]).sum())
        r = {"day": D, "date": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=D))[:10], "event": label,
             "perturbation": "noise" if D in noise_days else "shift +30", "sides_checked": int(len(chk)),
             "moved": int(mv.sum()), "gamma_max_abs_diff": gdiff, "power_moved": power,
             "power_sample": int(len(smp)), "leaky_L1_moved": L1, "leaky_L1_sides": int(len(near)),
             "leaky_L2_moved": L2, "leaky_L2_pool": int(len(pool))}
        # gamma: the clean snapshots come from panel.py's disk cache (fitted in the panel file's row order), the refit
        # from features.py's row order, so equal inputs agree to floating-point summation order, not bit for bit
        r["pass"] = (r["moved"] == 0 and gdiff <= TOL and power > 0 and L1 > 0 and L2 > 0)
        recs.append(r)
        log(f"B {r['date']} {label}: checked {r['sides_checked']}, moved {r['moved']}, gamma diff {gdiff:.1e}, "
            f"power {power}/{len(smp)}, L1 {L1}/{len(near)}, L2 {L2}/{len(pool)} -> {'ok' if r['pass'] else 'FAIL'}")
    return {"days": len(recs), "days_2024_26": int(sum(r["date"] >= "2024" for r in recs)),
            "moved_total": int(sum(r["moved"] for r in recs)),
            "gamma_max_abs_diff": float(max(r["gamma_max_abs_diff"] for r in recs)),
            "leaky_L1_fired": int(sum(r["leaky_L1_moved"] > 0 for r in recs)),
            "leaky_L2_fired": int(sum(r["leaky_L2_moved"] > 0 for r in recs)),
            "pass": all(r["pass"] for r in recs), "per_day": recs}


def main() -> None:
    log("clean build through features.build (the production path)")
    B = F.build(P)
    stored = pd.read_parquet(F.FEATURES, columns=["match_id", "spd_f", "spd_f_all", "spd_raw"])
    same = B["m"][["match_id", "spd_f", "spd_f_all", "spd_raw"]].merge(stored, on="match_id", suffixes=("", "_s"))
    res = {"reads_results": False,
           "rebuild_equals_stored_file": bool(np.allclose(same["spd_f"], same["spd_f_s"], atol=0, rtol=0)
                                              and np.allclose(same["spd_f_all"], same["spd_f_all_s"], atol=0, rtol=0)
                                              and np.allclose(same["spd_raw"], same["spd_raw_s"], atol=0, rtol=0,
                                                              equal_nan=True))}
    log(f"the production rebuild equals the stored file: {res['rebuild_equals_stored_file']}")
    res["probe_a"] = probe_a(B)
    log(f"probe A pass {res['probe_a']['pass']}")
    res["probe_b"] = probe_b(B)
    log(f"probe B pass {res['probe_b']['pass']}")
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
