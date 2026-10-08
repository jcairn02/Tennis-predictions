"""Tests for Stage A of "ideas borrowed from UFC-predictions" (src/eda/ufc_ideas/stageA_ratings.py).

    * the BT solver (sparse damped Newton with conjugate gradient) against a dense reference solve, plain and surface;
    * the sparse Hessian's layout against a dense X' diag(h) X, across epoch rebuilds;
    * the surface BT's block preconditioner against a dense inverse;
    * the time rule on hand-made histories: a round robin's matches never see each other, two events of one week
      never see each other, an earlier round of the same event is seen; and every pre-match value of a random history
      against a row-by-row reference (a dense solve per date from earlier dates only, then the earlier rounds of the
      same event applied round by round in plain Python);
    * MESR's snapshot against a dense least squares, and its pass against the same row-by-row reading;
    * with no decay and a huge lambda every rating stays at its anchor;
    * the probe cut by date, event and round passes the real pass and catches a leaky one.

Run: ./python.sh -m pytest test/ufc_ideas/test_stageA.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.ufc_ideas import stageA_ratings as A  # noqa: E402


# ------------------------------------------------------------------------------------------------
# Helpers

def table(rows) -> pd.DataFrame:
    """A hand-made match table in the study's order: rows of (date, event, round_order, A, B, a_won[, surface[,
    status[, p_avg_a]]])."""
    recs = []
    for r in rows:
        date, ev, rnd, pa, pb, won = r[:6]
        surf = r[6] if len(r) > 6 else "Hard"
        status = r[7] if len(r) > 7 else "completed"
        pmk = r[8] if len(r) > 8 else np.nan
        recs.append({"tournament_date": pd.Timestamp(date), "tournament_id": ev, "round_order": rnd,
                     "player_a_id": pa, "player_b_id": pb, "a_won": bool(won), "surface": surf, "status": status,
                     "p_avg_a": pmk})
    t = pd.DataFrame(recs).sort_values(["tournament_date", "round_order"], kind="mergesort").reset_index(drop=True)
    t["match_id"] = [f"m{i}" for i in range(len(t))]
    t["games_share"] = np.nan
    t["evaluation"] = True
    t["year"] = t["tournament_date"].dt.year
    return t


def dense_bt(edges, n, lam, mvec, lam_u=None, n_surf=A.N_SURF):
    """The BT MAP by dense Newton to machine precision. edges: (a, b, y, w, surface or -1). With lam_u, variables are
    s (n) then u (n x surfaces)."""
    nv = n * (1 + n_surf) if lam_u is not None else n
    X = np.zeros((len(edges), nv))
    for k, (a, b, _, _, s) in enumerate(edges):
        X[k, a], X[k, b] = 1, -1
        if lam_u is not None and s >= 0:
            X[k, n + n_surf * a + s], X[k, n + n_surf * b + s] = 1, -1
    y = np.array([e[2] for e in edges], dtype=float)
    w = np.array([e[3] for e in edges], dtype=float)
    ridge = np.full(nv, lam)
    if lam_u is not None:
        ridge[n:] = lam_u
    m = np.zeros(nv)
    m[:n] = mvec
    x = m.copy()
    for _ in range(100):
        p = expit(X @ x)
        g = X.T @ (w * (p - y)) + ridge * (x - m)
        H = X.T @ ((w * p * (1 - p))[:, None] * X) + np.diag(ridge)
        d = np.linalg.solve(H, -g)
        x = x + d
        if np.abs(d).max() < 1e-13:
            break
    p = expit(X @ x)
    info = (X ** 2).T @ (w * p * (1 - p))
    return x, info


def reference_pass(t: pd.DataFrame, cfg: dict, kind: str = "bt") -> np.ndarray:
    """A row-by-row reading of the time rule: for each date a dense solve from the edges of earlier dates only
    (ages from the date), then each event's rounds in order, every player's rating the snapshot plus the one-step
    updates of their earlier rounds of that event (a round's updates applied only after the round)."""
    h = A.history(t, 1.0)
    n = h["n_players"]
    out = np.full((len(t), 2), np.nan)
    week, ev, rnd = h["week"], np.asarray(h["event"]), np.asarray(h["rnd"])
    y_all = np.asarray(h["a_won"], dtype=float)
    lam, anchor = float(cfg["lam"]), float(cfg["anchor"])
    lam_u = cfg.get("lam_u")
    for D in np.unique(week):
        before = np.flatnonzero((week < D) & (h["odds_ok"] if kind == "mesr" else h["upd"]))
        age = (D - week[before]).astype(float)
        cnt = np.bincount(h["a"][before], minlength=n) + np.bincount(h["b"][before], minlength=n)
        if kind == "mesr":
            w = np.exp2(-age / (365.25 * cfg["half_life"]))
            mvec = np.where(cnt <= 1, anchor, 0.0)
            X = np.zeros((len(before), n))
            X[np.arange(len(before)), h["a"][before]] = 1
            X[np.arange(len(before)), h["b"][before]] = -1
            Aa = np.vstack([np.sqrt(w)[:, None] * X, np.sqrt(lam) * np.eye(n)])
            bb = np.concatenate([np.sqrt(w) * h["d"][before], np.sqrt(lam) * mvec])
            x = np.linalg.lstsq(Aa, bb, rcond=None)[0]
            info = (X ** 2).T @ w + lam
        else:
            dec = np.ones(len(before)) if cfg["half_life"] is None else np.exp2(-age / (365.25 * cfg["half_life"]))
            rw = np.where(h["ret"][before], cfg["ret_w"], 1.0)
            w = rw * dec
            if cfg["half_life"] is not None:
                keep = dec >= A.MIN_W
                before, w = before[keep], w[keep]
                cnt = np.bincount(h["a"][before], minlength=n) + np.bincount(h["b"][before], minlength=n)
            mvec = anchor * np.maximum(0.0, 1 - cnt / A.K_DECAY)
            edges = [(h["a"][k], h["b"][k], y_all[k], wk, h["surf"][k]) for k, wk in zip(before, w)]
            if edges:
                x, info_raw = dense_bt(edges, n, lam, mvec, lam_u)
            else:
                nv = n * (1 + A.N_SURF) if lam_u is not None else n
                x, info_raw = np.zeros(nv), np.zeros(nv)
                x[:n] = mvec
            info = info_raw
        today = np.flatnonzero(week == D)
        for e in np.unique(ev[today]):
            rows_e = today[ev[today] == e]
            delta, J, seen = {}, {}, {}
            for r in sorted(set(rnd[rows_e])):
                rows_r = rows_e[rnd[rows_e] == r]
                pre = {}
                for k in rows_r:
                    pa, pb, s = h["a"][k], h["b"][k], h["surf"][k]

                    def base(p):
                        v = x[p]
                        if kind == "bt" and lam_u is not None and s >= 0:
                            v += x[n + A.N_SURF * p + s]
                        return v

                    def eff(p):
                        if kind == "mesr":
                            return info[p]
                        hs = info[p] + lam
                        if lam_u is not None and s >= 0:
                            iu = info[n + A.N_SURF * p + s]
                            hu = iu + lam_u
                            return (hs * hu - iu ** 2) / (hs + hu - 2 * iu)
                        return hs
                    ra, rb = base(pa) + delta.get(pa, 0.0), base(pb) + delta.get(pb, 0.0)
                    if kind == "mesr":
                        ra = ra if (cnt[pa] + seen.get(pa, 0)) > 0 else np.nan
                        rb = rb if (cnt[pb] + seen.get(pb, 0)) > 0 else np.nan
                    out[k] = ra, rb
                    pre[k] = (base(pa) + delta.get(pa, 0.0), base(pb) + delta.get(pb, 0.0), eff(pa), eff(pb))
                nd, nJ, ns = {}, {}, {}
                for k in rows_r:
                    pa, pb = h["a"][k], h["b"][k]
                    ra, rb, ea, eb = pre[k]
                    if kind == "mesr":
                        if not h["odds_ok"][k]:
                            continue
                        res = h["d"][k] - (ra - rb)
                        nd[pa] = nd.get(pa, 0.0) + res / (1.0 + ea + J.get(pa, 0.0))
                        nd[pb] = nd.get(pb, 0.0) - res / (1.0 + eb + J.get(pb, 0.0))
                        hk = 1.0
                    else:
                        if not h["upd"][k]:
                            continue
                        wk = cfg["ret_w"] if h["ret"][k] else 1.0
                        p = expit(ra - rb)
                        hk = wk * p * (1 - p)
                        r_ = wk * (y_all[k] - p)
                        nd[pa] = nd.get(pa, 0.0) + r_ / (hk + ea + J.get(pa, 0.0))
                        nd[pb] = nd.get(pb, 0.0) - r_ / (hk + eb + J.get(pb, 0.0))
                    nJ[pa] = nJ.get(pa, 0.0) + hk
                    nJ[pb] = nJ.get(pb, 0.0) + hk
                    ns[pa] = ns.get(pa, 0) + 1
                    ns[pb] = ns.get(pb, 0) + 1
                for d_, tgt in ((nd, delta), (nJ, J), (ns, seen)):
                    for p, v in d_.items():
                        tgt[p] = tgt.get(p, 0) + v
    return out


def random_history(seed: int, n_players: int = 14, weeks: int = 9, with_odds: bool = False) -> pd.DataFrame:
    """Random weeks with one or two events each (knockout rounds, some round robins), a few retirements and
    walkovers, players reused across events of the same week, mixed surfaces, odds on some matches."""
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2020-01-06")
    surfaces = ["Hard", "Clay", "Grass", None]
    for wk in range(weeks):
        date = start + pd.Timedelta(days=7 * wk)
        for e in range(rng.integers(1, 3)):
            ev = f"E{wk}-{e}"
            surf = surfaces[rng.integers(0, 4)]
            players = list(rng.choice(n_players, size=6, replace=False))
            if rng.random() < 0.4:                                    # a round robin then a final
                for i in range(4):
                    for j in range(i + 1, 4):
                        rows.append((date, ev, 10, f"p{players[i]}", f"p{players[j]}", rng.random() < 0.5, surf))
                rows.append((date, ev, 17, f"p{players[0]}", f"p{players[1]}", rng.random() < 0.5, surf))
            else:                                                     # qualifying, then a knockout
                rows.append((date, ev, 1, f"p{players[4]}", f"p{players[5]}", True, surf))
                rows.append((date, ev, 13, f"p{players[0]}", f"p{players[1]}", rng.random() < 0.5, surf))
                rows.append((date, ev, 13, f"p{players[2]}", f"p{players[4]}", rng.random() < 0.5, surf))
                rows.append((date, ev, 16, f"p{players[0]}", f"p{players[2]}", rng.random() < 0.5, surf))
                rows.append((date, ev, 17, f"p{players[0]}", f"p{players[3]}", rng.random() < 0.5, surf))
    out = []
    for r in rows:
        status = rng.choice(["completed", "retired", "walkover"], p=[0.85, 0.1, 0.05])
        p = float(rng.uniform(0.1, 0.9)) if (with_odds and rng.random() < 0.8) else np.nan
        out.append((*r[:6], r[6] if r[6] is not None else "Hard", status, p))
    t = table(out)
    unknown = rng.random(len(t)) < 0.1
    t.loc[unknown, "surface"] = None                                  # some matches with an unknown surface
    return t


# ------------------------------------------------------------------------------------------------
# Solvers

@pytest.mark.parametrize("surface", [False, True])
def test_bt_solver_matches_dense_reference(surface):
    rng = np.random.default_rng(1)
    n, m = 9, 40
    a = rng.integers(0, n, m)
    b = (a + rng.integers(1, n, m)) % n
    y = (rng.random(m) < 0.6).astype(float)
    w = rng.uniform(0.2, 1.0, m)
    s = rng.integers(-1, 3, m)
    lam, lam_u = 0.35, 3.0
    mvec = -0.5 * np.maximum(0, 1 - (np.bincount(a, minlength=n) + np.bincount(b, minlength=n)) / A.K_DECAY)
    h = {"a": a, "b": b, "surf": s, "n_players": n}
    dsg = A.bt_design(h, np.arange(m), surface)
    ridge = np.full(dsg.n_var, lam)
    full_m = np.zeros(dsg.n_var)
    full_m[:n] = mvec
    if surface:
        ridge[n:] = lam_u
    x, info, _, _ = A.newton_bt(full_m.copy(), dsg, 0, m, y, w, ridge, full_m, tol=1e-12)
    xd, infod = dense_bt(list(zip(a, b, y, w, s)), n, lam, mvec, lam_u if surface else None)
    assert np.allclose(x, xd, atol=1e-9)
    assert np.allclose(info, infod, atol=1e-9)


@pytest.mark.parametrize("surface", [False, True])
def test_hessian_layout_matches_dense_across_epochs(surface, monkeypatch):
    monkeypatch.setattr(A.Design, "EPOCH", 7)
    rng = np.random.default_rng(2)
    n, m = 8, 60
    a = rng.integers(0, n, m)
    b = (a + rng.integers(1, n, m)) % n
    s = rng.integers(-1, 4, m)
    dsg = A.bt_design({"a": a, "b": b, "surf": s, "n_players": n}, np.arange(m), surface)
    X = np.zeros((m, dsg.n_var))
    for k in range(m):
        for c, sg in zip(dsg.cols[k], dsg.signs[k]):
            X[k, c] += sg
    ridge = rng.uniform(0.1, 2.0, dsg.n_var)
    for lo, hi in [(0, 5), (0, 20), (3, 33), (10, 60), (0, 4)]:          # forward, then a restart from the start
        hh = rng.uniform(0, 0.25, hi - lo)
        H, dd = dsg.hessian(hh, lo, hi, ridge)
        dense = X[lo:hi].T @ (hh[:, None] * X[lo:hi]) + np.diag(ridge)
        assert np.allclose(H.toarray(), dense, atol=1e-12)
        assert np.allclose(dd, np.diag(dense) - ridge, atol=1e-12)


def test_block_preconditioner_is_the_block_inverse():
    rng = np.random.default_rng(3)
    N = 5
    dd = rng.uniform(0, 3, N * (1 + A.N_SURF))
    dd[:N] += dd[N:].reshape(N, A.N_SURF).sum(axis=1)               # a player's total covers each surface's
    ridge = np.concatenate([np.full(N, 0.35), np.full(N * A.N_SURF, 3.0)])
    apply = A.jacobi(dd, ridge, N)
    v = rng.normal(size=N * (1 + A.N_SURF))
    got = apply(v)
    for i in range(N):
        idx = [i] + [N + A.N_SURF * i + k for k in range(A.N_SURF)]
        Hb = np.diag((dd + ridge)[idx])
        for k in range(A.N_SURF):
            Hb[0, k + 1] = Hb[k + 1, 0] = dd[N + A.N_SURF * i + k]
        assert np.allclose(got[idx], np.linalg.solve(Hb, v[idx]), atol=1e-12)


def test_mesr_snapshot_matches_dense_least_squares():
    rng = np.random.default_rng(4)
    n, m = 10, 35
    a = rng.integers(0, n, m)
    b = (a + rng.integers(1, n, m)) % n
    d = rng.normal(0, 1.2, m)
    w = rng.uniform(0.1, 1.0, m)
    lam = 1.0
    cnt = np.bincount(a, minlength=n) + np.bincount(b, minlength=n)
    mvec = np.where(cnt <= 1, -0.5, 0.0)
    dsg = A.Design(np.column_stack([a, b]), np.column_stack([np.ones(m), -np.ones(m)]), n)
    x, dd, _ = A.solve_ls(np.zeros(n), dsg, 0, m, d, w, lam, mvec)
    X = np.zeros((m, n))
    X[np.arange(m), a], X[np.arange(m), b] = 1, -1
    Aa = np.vstack([np.sqrt(w)[:, None] * X, np.sqrt(lam) * np.eye(n)])
    bb = np.concatenate([np.sqrt(w) * d, np.sqrt(lam) * mvec])
    assert np.allclose(x, np.linalg.lstsq(Aa, bb, rcond=None)[0], atol=1e-8)
    assert np.allclose(dd, (X ** 2).T @ w)


# ------------------------------------------------------------------------------------------------
# The time rule

CFG = {"half_life": 1.5, "lam": 0.35, "anchor": -0.5, "ret_w": 0.5}


def test_round_robin_same_week_events_and_earlier_rounds():
    rows = [("2020-01-06", "W1", 13, "p0", "p1", True), ("2020-01-06", "W1", 13, "p2", "p3", False),
            ("2020-01-06", "W1", 16, "p0", "p3", True)]                       # week 1: a small knockout
    rows += [("2020-01-13", "RR", 10, x, y_, w) for x, y_, w in
             [("p0", "p1", True), ("p2", "p3", True), ("p0", "p2", False), ("p1", "p3", True),
              ("p0", "p3", True), ("p1", "p2", False)]]                         # week 2: a round robin
    rows += [("2020-01-13", "RR", 17, "p0", "p2", True),                        # its final
             ("2020-01-13", "OTHER", 13, "p4", "p5", True),                     # another event of the same week
             ("2020-01-13", "OTHER", 14, "p4", "p6", True)]                     # its next round
    rows += [("2020-01-13", "LATE", 13, "p5", "p1", False)]                     # p5 again, a third event that week
    t = table(rows)
    h = A.history(t, 1.0)
    out = A.bt_pass(h, CFG)
    rr = np.flatnonzero((t["tournament_id"] == "RR") & (t["round_order"] == 10))
    # the round robin's matches see nothing of each other: each player's rating is the same in all three of theirs
    for p in ["p0", "p1", "p2", "p3"]:
        vals = [out[k, 0] if t.loc[k, "player_a_id"] == p else out[k, 1] for k in rr
                if p in (t.loc[k, "player_a_id"], t.loc[k, "player_b_id"])]
        assert len(vals) == 3 and np.ptp(vals) == 0
        assert all(out[k, 4 if t.loc[k, "player_a_id"] == p else 5] == 0 for k in rr
                   if p in (t.loc[k, "player_a_id"], t.loc[k, "player_b_id"]))
    # the final sees the round robin (an earlier round of the same event)
    fin = int(np.flatnonzero((t["tournament_id"] == "RR") & (t["round_order"] == 17))[0])
    p0_rr = out[rr[0], 0]
    assert out[fin, 0] != p0_rr and out[fin, 4] == 3
    # another event of the same week: p5's rating in LATE is the week's snapshot, untouched by OTHER's result
    late = int(np.flatnonzero(t["tournament_id"] == "LATE")[0])
    oth = int(np.flatnonzero((t["tournament_id"] == "OTHER") & (t["round_order"] == 13))[0])
    assert out[late, 0] == out[oth, 1] and out[late, 4] == 0
    # within OTHER, the next round sees the first: p4's rating moves after its win
    oth2 = int(np.flatnonzero((t["tournament_id"] == "OTHER") & (t["round_order"] == 14))[0])
    assert out[oth2, 0] > out[oth, 0] and out[oth2, 4] == 1
    # week 2's snapshot holds week 1's three matches (counts), not week 2's
    assert out[rr[0], 2] == 2 and out[fin, 2] == 2


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("cfg", [CFG, {"half_life": None, "lam": 1.0, "anchor": -1.0, "ret_w": 1.0},
                                 {**CFG, "lam_u": 3.0}])
def test_bt_pass_equals_row_by_row_reading(seed, cfg):
    t = random_history(seed)
    h = A.history(t, 1.0)
    got = A.bt_pass(h, cfg)
    ref = reference_pass(t, cfg)
    assert np.allclose(got[:, :2], ref, atol=1e-6)


@pytest.mark.parametrize("seed", [0, 3])
def test_mesr_pass_equals_row_by_row_reading(seed):
    t = random_history(seed, with_odds=True)
    h = A.history(t, 1.0)
    cfg = {"half_life": 1.0, "lam": 1.0, "anchor": -0.5}
    got = A.mesr_pass(h, cfg)
    ref = reference_pass(t, cfg, kind="mesr")
    assert np.array_equal(np.isnan(got[:, :2]), np.isnan(ref))
    assert np.allclose(got[:, :2], ref, atol=1e-6, equal_nan=True)


def test_huge_lambda_without_decay_keeps_every_rating_at_its_anchor():
    t = random_history(5)
    h = A.history(t, 1.0)
    cfg = {"half_life": None, "lam": 1e9, "anchor": -0.7, "ret_w": 1.0}
    out = A.bt_pass(h, cfg)
    anchors_a = -0.7 * np.maximum(0, 1 - out[:, 2] / A.K_DECAY)
    anchors_b = -0.7 * np.maximum(0, 1 - out[:, 3] / A.K_DECAY)
    assert np.allclose(out[:, 0], anchors_a, atol=1e-7) and np.allclose(out[:, 1], anchors_b, atol=1e-7)
    out_s = A.bt_pass(h, {**cfg, "lam_u": 1e9})
    assert np.allclose(out_s[:, 0], anchors_a, atol=1e-7)


def test_comparison_helpers():
    from src.eda.ufc_ideas import stageA_rundown as RD
    rng = np.random.default_rng(9)
    p = rng.uniform(0.05, 0.95, 200_000)
    y = rng.random(len(p)) < p
    assert abs(RD.calibration(p, y)["slope"] - 1) < 0.03                      # calibrated: slope 1
    bold = expit(2 * np.log(p / (1 - p)))
    assert abs(RD.calibration(bold, y)["slope"] - 0.5) < 0.02                  # twice too confident: slope 1/2
    L = {"elo": np.array([0.7, 0.6]), "bt": np.array([0.65, 0.55]), "market": np.array([0.6, 0.5])}
    b = RD.block(L, np.array([True, True]), ["bt", "elo", "market"], True)
    assert np.isclose(b["gap_closed"]["bt"], 0.5) and np.isclose(b["elo_minus_bt"]["milli"], 50.0)


def test_probe_passes_the_pass_and_catches_a_leaky_one():
    t = random_history(7, weeks=12)
    h = A.history(t, 1.0)

    def good(hh):
        return A.bt_pass({**h, "a_won": np.asarray(hh["a_won"], dtype=bool)}, CFG)

    def leaky(hh):
        return A.bt_pass({**h, "a_won": np.asarray(hh["a_won"], dtype=bool)}, CFG, leaky=True)
    ok = B.probe_by_round(h, good, n_cuts=8, seed=3, from_quantile=0.3)
    bad = B.probe_by_round(h, leaky, n_cuts=8, seed=3, from_quantile=0.3)
    assert ok["protected_matches_changed"] == 0 and ok["later_matches_changed"] > 0
    assert bad["protected_matches_changed"] > 0
    for what, cfg in [("mesr", {"half_life": 1.0, "lam": 1.0, "anchor": -0.5}), ("bt_games", {**CFG, "games": True}),
                      ("bt_surface", {**CFG, "lam_u": 3.0})]:
        hh = A.history(random_history(8, weeks=12, with_odds=True), 1.0)
        res = A.probe_generic(hh, what, cfg, n_cuts=6, seed=4, from_quantile=0.3)
        assert res["protected_matches_changed"] == 0 and res["later_matches_changed"] > 0
