"""Tests for Stage B of "ideas borrowed from UFC-predictions" (src/eda/ufc_ideas/stageB_*.py): hand-made histories against
a row-by-row reading of each rule.

    * the step-1 pair index against the time rule (a round robin's matches never see each other; two events of one week
      never see each other; an earlier round of the same event is seen), and its weighted moments against loops;
    * adjperf / adjdef steps 1-3 (the opponent's shrunk norm and MAD, the clipped z, the player's three forms) against a
      row-by-row computation, and the mirror identity (adjdef on rpw is adjperf on spw);
    * the IOS ridge solve against a dense least squares on a toy problem, its incremental step against the coordinate
      minimiser, and its time rule (another event of the same week is never in the incremental step);
    * the opponent-strength split (strong / weak averages, the contrast, the slope, wins above Elo, the interaction) on a
      hand-made history against loops.

Run: ./python.sh -m pytest test/ufc_ideas/test_stageB.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import stageB_adjperf as AP  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402
from src.eda.ufc_ideas import stageB_ios as IO  # noqa: E402
from src.eda.ufc_ideas import stageB_split as SP  # noqa: E402

D0 = pd.Timestamp("2016-01-04")      # a Monday


# ------------------------------------------------------------------------------------------------
# A hand-made history

# (week offset in days, event, round order, player A, player B, A's serve points won / played, B's)
MATCHES = [
    (0, "E1", 13, "P1", "P2", (40, 60), (30, 55)),
    (0, "E1", 13, "P3", "P4", (45, 70), (35, 66)),
    (0, "E2", 13, "P5", "P2", (38, 62), (41, 64)),     # P2 plays two events in the same week: never seen across
    (0, "E1", 14, "P1", "P3", (50, 75), (44, 72)),     # the next round of E1 sees round 13
    (7, "E3", 10, "P1", "P4", (36, 58), (33, 61)),     # a round robin: its three matches never see each other
    (7, "E3", 10, "P1", "P5", (42, 66), (39, 63)),
    (7, "E3", 10, "P4", "P5", (35, 57), (37, 60)),
    (14, "E4", 13, "P2", "P3", (47, 70), (40, 69)),
    (14, "E4", 14, "P1", "P2", (52, 80), (49, 78)),
    (70, "E5", 13, "P4", "P2", (31, 52), (38, 59)),
    (420, "E6", 13, "P1", "P3", (55, 81), (39, 70)),    # more than 52 weeks after the first weeks
    (420, "E6", 14, "P1", "P4", (48, 70), (30, 50)),
    (427, "E7", 13, "P2", "P5", (44, 68), (43, 67)),
]


def make_rows(matches=MATCHES, elo=None, won_a=None) -> pd.DataFrame:
    """Two rows per match (A, B) with every column Stage B reads; serve points as given, return and total points as
    their mirror, every other statistic missing."""
    recs = []
    for i, (dd, ev, rnd, a, b, (xa, na), (xb, nb)) in enumerate(matches):
        date = D0 + pd.Timedelta(days=dd)
        wa = True if won_a is None else bool(won_a[i])
        for side, p, o, x, n, xo, no, w in (("A", a, b, xa, na, xb, nb, wa), ("B", b, a, xb, nb, xa, na, not wa)):
            r = {"match_id": f"m{i}", "player_id": p, "opponent_id": o, "side": side, "order": i,
                 "tournament_date": date, "tournament_id": ev, "round_order": rnd, "tour": "atp", "year": date.year,
                 "level": "T250", "qualifying": False, "evaluation": True, "status": "completed", "format": "standard",
                 "surface": "Hard", "won": w, "tournament_name": ev, "best_of": 3, "minutes": 90.0}
            for s in C.RATES:
                r[f"{s}_n"], r[f"{s}_d"] = np.nan, np.nan
            r["spw_n"], r["spw_d"] = float(x), float(n)
            r["rpw_n"], r["rpw_d"] = float(no - xo), float(no)
            r["tpw_n"], r["tpw_d"] = float(x + no - xo), float(n + no)
            r["sets_won_n"], r["sets_won_d"] = (2.0 if w else 0.0), 2.0
            recs.append(r)
    rows = pd.DataFrame(recs)
    rows["elo_surf_own"] = (np.asarray(elo, dtype="float64") if elo is not None else 2000.0 + 10 * np.arange(len(rows)))
    pa = 0.5 + 0.02 * (np.arange(len(rows)) // 2 % 7) - 0.06
    rows["p_elo_a"] = pa
    return B.F.prepare(rows)


MEANS = {s: {(t, sf): mu for t in C.TOURS for sf in ("all", "Hard", "Clay", "Grass", "Carpet")}
         for s, mu in (("spw", 0.62), ("rpw", 0.38), ("tpw", 0.5))}


def visible(rows: pd.DataFrame, i: int, j: int) -> bool:
    """The Brief's time rule, row by row: j is an earlier event, or an earlier round of the same event."""
    di, dj = rows["day"].iloc[i], rows["day"].iloc[j]
    if dj < di:
        return True
    return bool(dj == di and rows["ev"].iloc[i] == rows["ev"].iloc[j]
                and rows["round_order"].iloc[j] < rows["round_order"].iloc[i])


# ------------------------------------------------------------------------------------------------
# The pair index and its moments

def test_pair_index_time_rule():
    rows = make_rows()
    box = np.arange(len(rows))
    P = B.PairIndex(rows, box, chunk_pairs=5)               # small chunks: the chunking is exercised too
    got = set()
    for tgt, src, dt in P.chunks():
        for a, b, d in zip(tgt, src, dt):
            i, j = box[P.order[a]], box[P.order[b]]
            got.add((i, j))
            assert d == rows["day"].iloc[i] - rows["day"].iloc[j]
    want = {(i, j) for i in range(len(rows)) for j in range(len(rows))
            if i != j and rows["pcode"].iloc[i] == rows["pcode"].iloc[j] and visible(rows, i, j)}
    assert got == want
    pid = rows["player_id"].to_numpy()
    rr = rows["round_order"].to_numpy()
    tid = rows["tournament_id"].to_numpy()
    # the round robin: P1's two E3 matches never see each other; P2's E2 match never sees its E1 match of the week
    e3 = np.flatnonzero((pid == "P1") & (tid == "E3"))
    assert (e3[0], e3[1]) not in got and (e3[1], e3[0]) not in got
    p2_e1 = int(np.flatnonzero((pid == "P2") & (tid == "E1"))[0])
    p2_e2 = int(np.flatnonzero((pid == "P2") & (tid == "E2"))[0])
    assert (p2_e2, p2_e1) not in got and (p2_e1, p2_e2) not in got
    # an earlier round of the same event is seen
    p1_r14 = int(np.flatnonzero((pid == "P1") & (tid == "E1") & (rr == 14))[0])
    p1_r13 = int(np.flatnonzero((pid == "P1") & (tid == "E1") & (rr == 13))[0])
    assert (p1_r14, p1_r13) in got


def test_pair_moments_against_loops():
    rows = make_rows()
    rng = np.random.default_rng(3)
    n = len(rows)
    box = np.arange(n)
    P = B.PairIndex(rows, box, chunk_pairs=7)
    a = rng.normal(size=n)
    valid = rng.random(n) > 0.2
    units = rng.integers(40, 90, n).astype(float)
    wanted = [("x", 26.0, 0), ("x", np.inf, 1), ("x", 52.0, 1)]
    mom = B.pair_moments(P, {"x": (P.to_sorted(a), P.to_sorted(valid), P.to_sorted(units))}, wanted)
    day = rows["day"].to_numpy()
    for key in wanted:
        S0, S1, M = (P.from_sorted(v) for v in mom[key])
        _, h, tau = key
        for i in range(n):
            js = [j for j in range(n) if j != i and rows["pcode"].iloc[j] == rows["pcode"].iloc[i]
                  and visible(rows, i, j) and valid[j]]
            w = np.array([(2 ** (-(day[i] - day[j]) / (7 * h)) if np.isfinite(h) else 1.0) * units[j] ** tau for j in js])
            v = a[js]
            s0, s1 = w.sum(), (w * v).sum()
            m = (w * np.abs(v - s1 / s0)).sum() if s0 > 0 else 0.0
            assert S0[i] == pytest.approx(s0, abs=1e-12)
            assert S1[i] == pytest.approx(s1, abs=1e-12)
            assert M[i] == pytest.approx(m, abs=1e-12)


# ------------------------------------------------------------------------------------------------
# adjperf / adjdef, steps 1-3

def frozen():
    chosen = {(t, s): {"h1": 52.0, "K1": 5.0, "tau": 1 if s == "spw" else 0, "h3": 26.0, "K3": 2.0}
              for t in C.TOURS for s in AP.CORE}
    chosen[("atp", "rpw")] = {"h1": np.inf, "K1": 10.0, "tau": 0, "h3": 13.0, "K3": 1.0}
    typ = {(s, t): u for s, u in (("spw", 66.0), ("rpw", 66.0), ("tpw", 132.0)) for t in C.TOURS}
    madpop = {(s, ch, t, tau): 0.3 + 0.01 * tau for s in ("spw", "rpw", "tpw") for ch in AP.CHANNELS
              for t in C.TOURS for tau in (0, 1)}
    return chosen, typ, madpop


def rowwise_z(rows, s, ch, c, typ, madpop, means=MEANS):
    """Steps 1-2 by loops: per row, the z of the row's player in that match."""
    n = len(rows)
    xd = {"spw": (rows["spw_n"], rows["spw_d"]), "rpw": (rows["rpw_n"], rows["rpw_d"]), "tpw": (rows["tpw_n"], rows["tpw_d"])}
    x, d = (np.asarray(v, dtype=float) for v in xd[s])
    mu = means[s][("atp", "Hard")]
    cv = logit((x + 0.5) / (d + 1)) - logit(mu)
    day = rows["day"].to_numpy()
    pc = rows["pcode"].to_numpy()
    kref = c["K1"] * typ[(s, "atp")] ** c["tau"]
    mp = madpop[(s, ch, "atp", c["tau"])]
    z = np.full(n, np.nan)
    for i in range(n):
        o = i ^ 1                                          # the opponent's row in this match
        hs = [h for h in range(n) if h != o and pc[h] == pc[o] and visible(rows, o, h)]
        vals, ws = [], []
        for h in hs:
            r = (h ^ 1) if ch == "adjperf" else h          # what the opponent allowed, or produced
            w = (2 ** (-(day[o] - day[h]) / (7 * c["h1"])) if np.isfinite(c["h1"]) else 1.0) * d[r] ** c["tau"]
            vals.append(cv[r])
            ws.append(w)
        ws, vals = np.array(ws), np.array(vals)
        s0 = ws.sum()
        E = (ws * vals).sum() / (s0 + kref)
        M = (ws * np.abs(vals - (ws * vals).sum() / s0)).sum() if s0 > 0 else 0.0
        MAD = (M + kref * mp) / (s0 + kref)
        den = max(MAD, AP.MAD_FLOOR)
        raw = (cv[i] - E) / den if ch == "adjperf" else (E - cv[o]) / den
        z[i] = np.clip(raw, -AP.CLIP, AP.CLIP)
    return z


def test_adjperf_adjdef_rowwise():
    rows = make_rows()
    chosen, typ, madpop = frozen()
    ctx = AP.Ctx(rows, MEANS, typ=typ, madpop=madpop, stats=("spw", "rpw", "tpw"))
    built = AP.build(ctx, chosen, stats=("spw", "rpw", "tpw"))
    day = rows["day"].to_numpy()
    pc = rows["pcode"].to_numpy()
    for s in ("spw", "rpw", "tpw"):
        for ch in AP.CHANNELS:
            c = AP.constants_for(chosen, s, ch, "atp")
            z_ref = rowwise_z(rows, s, ch, c, typ, madpop)
            z = np.full(len(rows), np.nan)
            z[ctx.box_idx] = built["z"][(s, ch)]
            np.testing.assert_allclose(z, z_ref, rtol=0, atol=1e-10)
            # step 3: the three forms at the pool rows, A minus B
            units = rows[f"{s}_d"].to_numpy(dtype=float)
            u = units if ch == "adjperf" else units[np.arange(len(rows)) ^ 1]
            kref = c["K3"] * typ[(s, "atp")] ** c["tau"]
            for form in AP.FORMS:
                ref = np.full(len(rows) // 2, np.nan)
                for m in range(len(rows) // 2):
                    vals = []
                    for i in (2 * m, 2 * m + 1):
                        js = [j for j in range(len(rows)) if j != i and pc[j] == pc[i] and visible(rows, i, j)]
                        if form == "52 weeks":
                            js = [j for j in js if day[j] >= day[i] - B.WEEK52]
                        if not js:
                            vals = None
                            break
                        w = np.array([u[j] ** c["tau"] * ((2 ** (-(day[i] - day[j]) / (7 * c["h3"])))
                                                          if form == "decayed" else 1.0) for j in js])
                        vals.append((w * z_ref[js]).sum() / (w.sum() + kref))
                    if vals is not None:
                        ref[m] = vals[0] - vals[1]
                got = built["features"][f"{ch}_{s}|{form}"]
                np.testing.assert_allclose(got, ref, rtol=0, atol=1e-10, err_msg=f"{ch} {s} {form}")
    # features exist exactly where an earlier visible match exists
    f = built["features"]["adjperf_spw|career"]
    assert np.isnan(f[0]) and np.isnan(f[1]) and np.isnan(f[2])     # the first week's first round: no history yet
    assert np.isfinite(f[3])                                          # E1's second round sees both players' first round
    assert np.isnan(built["features"]["adjperf_spw|52 weeks"][10])    # P1 v P3 in week 60: nothing in the last year


def test_mirror_identity():
    """adjdef on rpw is adjperf on spw for the same player, when both take the same (serve-skill) constants."""
    rows = make_rows()
    chosen, typ, madpop = frozen()
    madpop.update({("rpw", "adjdef", t, tau): madpop[("spw", "adjperf", t, tau)] for t in C.TOURS for tau in (0, 1)})
    ctx = AP.Ctx(rows, MEANS, typ=typ, madpop=madpop, stats=("spw", "rpw", "tpw"))
    built = AP.build(ctx, chosen, stats=("spw", "rpw", "tpw"))
    assert AP.skill_of("rpw", "adjdef") == AP.skill_of("spw", "adjperf") == "spw"
    np.testing.assert_allclose(built["z"][("rpw", "adjdef")], built["z"][("spw", "adjperf")], rtol=0, atol=1e-12)
    for form in AP.FORMS:
        np.testing.assert_allclose(built["features"][f"adjdef_rpw|{form}"], built["features"][f"adjperf_spw|{form}"],
                                   rtol=0, atol=1e-12)


# ------------------------------------------------------------------------------------------------
# IOS

def toy_td(seed=1, n_players=6, weeks=8, per_week=5):
    """A toy history: per week one event of two rounds; each match gives two serve observations."""
    rng = np.random.default_rng(seed)
    recs = []
    for w in range(weeks):
        for r in (13, 14):
            for k in range(per_week if r == 13 else 2):
                a, b = rng.choice(n_players, 2, replace=False)
                for p, o in ((a, b), (b, a)):
                    d = float(rng.integers(40, 90))
                    recs.append({"pid": p, "day": 7 * w, "ev": w, "round": r, "d": d, "x": float(rng.binomial(int(d), 0.6))})
    # another event in week 5, same day as event 5: a player plays both
    for p, o in ((0, 1), (1, 0)):
        recs.append({"pid": p, "day": 35, "ev": 99, "round": 13, "d": 60.0, "x": 37.0})
    t = pd.DataFrame(recs)
    y = logit((t["x"] + 0.5) / (t["d"] + 1)) - logit(0.6)
    return {"tour": "atp", "pid": t["pid"].to_numpy().astype(np.int64), "n_players": n_players,
            "day": t["day"].to_numpy().astype(np.int64),
            "tournament_date": (pd.Timestamp("2015-01-05") + pd.to_timedelta(t["day"], unit="D")).to_numpy(),
            "tournament_id": t["ev"].astype(str).to_numpy().astype(object), "round_order": t["round"].to_numpy().astype(np.int64),
            "year": np.full(len(t), 2015), "evaluation": np.ones(len(t), dtype=bool), "ev": t["ev"].to_numpy(),
            "stats": {"spw": {"ok": np.ones(len(t), dtype=bool), "x": t["x"].to_numpy(), "d": t["d"].to_numpy(),
                              "y": y.to_numpy(), "mu": np.full(len(t), logit(0.6)), "typ": 65.0}}}


def dense_solve(td, S, h, kappa, tau):
    st = td["stats"]["spw"]
    n = td["n_players"]
    k = np.flatnonzero(st["ok"] & (td["day"] < S))
    X = np.zeros((len(k), 2 * n))
    X[np.arange(len(k)), td["pid"][k]] = 1.0
    X[np.arange(len(k)), n + td["pid"][k ^ 1]] = -1.0
    w = (st["d"][k] / st["typ"]) ** tau * ((2.0 ** (-(S - td["day"][k]) / (7 * h))) if np.isfinite(h) else 1.0)
    A = np.vstack([X * np.sqrt(w)[:, None], np.sqrt(kappa) * np.eye(2 * n)])
    b = np.concatenate([st["y"][k] * np.sqrt(w), np.zeros(2 * n)])
    beta = np.linalg.lstsq(A, b, rcond=None)[0]
    return beta[:n], beta[n:], X, w, k


@pytest.mark.parametrize("h,kappa,tau", [(26.0, 3.0, 0), (np.inf, 1.0, 1), (104.0, 30.0, 1)])
def test_ios_solve_against_dense(h, kappa, tau):
    td = toy_td()
    sysm = IO.System(td, "spw")
    snaps = np.unique(td["day"])
    for gi, O, D, P, Q, it, conv in IO.snapshot_path(sysm, snaps, h, kappa, tau):
        assert conv
        O_ref, D_ref, X, w, _ = dense_solve(td, snaps[gi], h, kappa, tau)
        np.testing.assert_allclose(O, O_ref, rtol=0, atol=1e-7)
        np.testing.assert_allclose(D, D_ref, rtol=0, atol=1e-7)
        np.testing.assert_allclose(P, (X[:, :td["n_players"]] ** 2 * w[:, None]).sum(axis=0), rtol=1e-10, atol=1e-10)


def test_ios_incremental_step_and_time_rule():
    td = toy_td()
    h, kappa, tau = 52.0, 3.0, 0
    res = IO.run(td, "spw", h, kappa, tau, mode="weekly")
    st = td["stats"]["spw"]
    day, pid, ev, rnd = td["day"], td["pid"], td["ev"], td["round_order"]
    n = td["n_players"]
    for i in range(len(day)):
        S = day[i]
        O, D, X, w, k = dense_solve(td, S, h, kappa, tau)
        p = pid[i]
        # the coordinate minimiser of the player's own O (everyone else at the snapshot), with the gap observations: the
        # player's serve observations at the same event's earlier rounds (never another event of the week)
        srv = k[pid[k] == p]
        num = sum(w[list(k).index(j)] * (st["y"][j] + D[pid[j ^ 1]]) for j in srv)
        den = sum(w[list(k).index(j)] for j in srv) + kappa
        gap = [j for j in range(len(day)) if pid[j] == p and day[j] == S and ev[j] == ev[i] and rnd[j] < rnd[i]]
        num += sum(st["y"][j] + D[pid[j ^ 1]] for j in gap)
        den += len(gap)
        assert res["O"][i] == pytest.approx(num / den, abs=1e-7)
        # D likewise, from the observations where the player returned
        ret = k[pid[k ^ 1] == p]
        num = sum(w[list(k).index(j)] * (O[pid[j]] - st["y"][j]) for j in ret)
        den = sum(w[list(k).index(j)] for j in ret) + kappa
        gapr = [j ^ 1 for j in gap]
        num += sum(O[pid[j]] - st["y"][j] for j in gapr)
        den += len(gapr)
        assert res["D"][i] == pytest.approx(num / den, abs=1e-7)
        assert res["O_snap"][i] == pytest.approx(O[p], abs=1e-7)
    # the event of week 5 played by players 0 and 1 beside the main event: its rows take no gap from the main event
    side = np.flatnonzero(ev == 99)
    np.testing.assert_allclose(res["O"][side], res["O_snap"][side], rtol=0, atol=1e-12)


def test_earlier_weeks_variant_rowwise():
    """The decayed form with the same event's earlier rounds left out, on the matches where the full form exists."""
    rows = make_rows()
    rng = np.random.default_rng(11)
    n = len(rows)
    Z = {s: rng.normal(0, 1, n) for s in SP.SPLIT_STATS}
    used_full = {f"adjperf_{s}": {t: {"h3": 4.0, "K3": 3.0, "tau": 0} for t in C.TOURS} for s in SP.SPLIT_STATS}
    typ = {(s, t): 66.0 for s in SP.SPLIT_STATS for t in C.TOURS}
    sa = B.stat_arrays(rows, MEANS, SP.SPLIT_STATS)
    out = SP.earlier_weeks_variant(rows, np.arange(n), Z, used_full, typ, sa)
    day, pc = rows["day"].to_numpy(), rows["pcode"].to_numpy()
    for m in range(n // 2):
        vals = []
        for i in (2 * m, 2 * m + 1):
            full = [j for j in range(n) if j != i and pc[j] == pc[i] and visible(rows, i, j)]
            if not full:
                vals = None
                break
            js = [j for j in full if day[j] < day[i]]
            w = np.array([2 ** (-(day[i] - day[j]) / (7 * 4.0)) for j in js])
            vals.append((w * Z["tpw"][js]).sum() / (w.sum() + 3.0) if js else 0.0)
        got = out["adjperf_tpw|decayed, earlier weeks"][m]
        if vals is None:
            assert np.isnan(got)
        else:
            assert got == pytest.approx(vals[0] - vals[1], abs=1e-10)


# ------------------------------------------------------------------------------------------------
# The opponent-strength split

def test_split_rowwise():
    rng = np.random.default_rng(5)
    rows0 = make_rows()
    elo = 2050.0 + rng.normal(0, 60, len(rows0))
    rows = make_rows(elo=elo, won_a=rng.random(len(MATCHES)) < 0.5)
    lines = {t: {"median": 2050.0, "q33": 2020.0, "q67": 2080.0} for t in C.TOURS}
    slope_pop = {t: {"b0": -0.1, "var_e_within": 0.4} for t in C.TOURS}
    used = {s: {t: {"K3": 2.0, "tau": 0} for t in C.TOURS} for s in SP.SPLIT_STATS}
    typ = {(s, t): 66.0 for s in SP.SPLIT_STATS for t in C.TOURS}
    sa = B.stat_arrays(rows, MEANS, SP.SPLIT_STATS)
    box_idx = np.arange(len(rows))
    Z = {s: rng.normal(0, 1, len(rows)) for s in SP.SPLIT_STATS}
    feats = SP.split_features(rows, box_idx, Z, used, typ, lines, slope_pop, sa)
    n = len(rows)
    day, pc = rows["day"].to_numpy(), rows["pcode"].to_numpy()
    e_opp = elo[np.arange(n) ^ 1]
    strong, weak = e_opp > 2050.0, e_opp <= 2050.0
    K = 2.0
    for form in SP.FORMS:
        for m in range(n // 2):
            vals = {}
            for i in (2 * m, 2 * m + 1):
                js = [j for j in range(n) if j != i and pc[j] == pc[i] and visible(rows, i, j)]
                if form == "52 weeks":
                    js = [j for j in js if day[j] >= day[i] - B.WEEK52]
                if not js:
                    vals = None
                    break
                z = Z["tpw"]
                zs, zw = [z[j] for j in js if strong[j]], [z[j] for j in js if weak[j]]
                vs, vw = sum(zs) / (len(zs) + K), sum(zw) / (len(zw) + K)
                if zs and zw:
                    ne = len(zs) * len(zw) / (len(zs) + len(zw))
                    gap = (np.mean(zs) - np.mean(zw)) * ne / (ne + K)
                else:
                    gap = 0.0
                e = (e_opp[js] - 2050.0) / 100.0
                zz = z[js]
                cov = ((e - e.mean()) * (zz - zz.mean())).sum()
                var = ((e - e.mean()) ** 2).sum()
                lam = K * 0.4
                slope = (cov + lam * (-0.1)) / (var + lam)
                won = rows["won"].to_numpy().astype(float)
                p_own = np.where(rows["side"].to_numpy() == "A", rows["p_elo_a"].to_numpy(), 1 - rows["p_elo_a"].to_numpy())
                rs = [won[j] - p_own[j] for j in js if strong[j]]
                rw = [won[j] - p_own[j] for j in js if weak[j]]
                vals[i] = {"vs_strong": vs, "vs_weak": vw, "gap": gap, "slope": slope,
                           "ws": sum(rs) / (len(rs) + K), "ww": sum(rw) / (len(rw) + K)}
            got = {k: feats[f"{k}|{form}"][m] for k in ("vs_strong_tpw", "vs_weak_tpw", "strong_minus_weak_tpw", "slope_tpw",
                                                        "wins_over_strong", "wins_over_weak", "strong_gap_x_strong_opp")}
            if vals is None:
                assert np.isnan(got["vs_strong_tpw"]) and np.isnan(got["strong_minus_weak_tpw"])
                continue
            a, b = vals[2 * m], vals[2 * m + 1]
            assert got["vs_strong_tpw"] == pytest.approx(a["vs_strong"] - b["vs_strong"], abs=1e-10)
            assert got["vs_weak_tpw"] == pytest.approx(a["vs_weak"] - b["vs_weak"], abs=1e-10)
            assert got["strong_minus_weak_tpw"] == pytest.approx(a["gap"] - b["gap"], abs=1e-10)
            assert got["slope_tpw"] == pytest.approx(a["slope"] - b["slope"], abs=1e-9)
            assert got["wins_over_strong"] == pytest.approx(a["ws"] - b["ws"], abs=1e-10)
            assert got["wins_over_weak"] == pytest.approx(a["ww"] - b["ww"], abs=1e-10)
            a_strong, b_strong = elo[2 * m] > 2050.0, elo[2 * m + 1] > 2050.0
            assert got["strong_gap_x_strong_opp"] == pytest.approx(a["gap"] * b_strong - b["gap"] * a_strong, abs=1e-10)
