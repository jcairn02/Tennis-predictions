"""Stage 3 of the predictability diagnostic, part 1: serve and return ratings, updated match by match.

A match's serve-point share is explained by the server's serve rating and the returner's return rating:

    P(server wins a serve point) = 1 / (1 + exp(-(mu + S_server - R_returner)))

with mu the tour's average serve-point share on the match's surface (on the log-odds scale, 2010-2018,
frozen). Every player has a serve rating S and a return rating R, each with an uncertainty (a variance).
After a match, each rating moves by the serve points won above expectation times a step that is large when
the ratings are uncertain and small when they are well known (a one-step Bayesian update of a Gaussian
rating on a binomial result, as Glickman's Glicko does for wins). Time away widens a rating's variance
again (drift), up to a newcomer's. It is Elo on serve points with a step size that adapts.

Two observations per match: A serving to B, and B serving to A. Only completed matches with a box score
move ratings; every match gets pre-match values. History is every singles level from 2010 (ITF and team
events included), as the Brief sets for ratings.

The time rule is Stage 1's (stage1_baselines.elo_pass): a rating used for a match holds the player's earlier
events and the same event's earlier rounds, never another match of the same round (a round robin) or
another event of the same week. What a round adds waits for the event's next round; what an event adds
reaches the player's other events after the week.

The four constants (a newcomer's starting serve rating, the variances of a newcomer's serve and return
ratings, and the drift per week) are tuned on a grid by the log loss of serve points over the
evaluation-level matches of 2013-2018 (2010-2012 warm up), and frozen; later seasons are out of sample. A
newcomer's return rating starts at 0: the ratings' common level is free (only serve minus return enters a
prediction), and this fixes it.

Writes, in data/studies/predictability_diagnostic/:
    stage3_ratings.parquet          one row per match (all 872,704): A's and B's pre-match serve and return
                                    ratings, their standard deviations and the serve and return points they
                                    rest on, the surface's mu, and each player's expected serve-point share
                                    against this opponent; whether the match moved the ratings
    stage3_rating_tuning.csv        the grid: log loss per serve point 2013-2018, per tour and setting
    stage3_ratings_summary.json     the constants, the tuning detail, the probe, the rating spreads and the
                                    highest-rated players (a sanity check)

Run: ./python.sh src/eda/predictability_diagnostic/stage3_ratings.py   (about 2 minutes)
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.lower_level_evidence import level_layer as _LLE  # noqa: E402  level layer (LLE_LAYER)

RATINGS = C.OUT / "stage3_ratings.parquet"
TUNING = C.OUT / "stage3_rating_tuning.csv"
SUMMARY = C.OUT / "stage3_ratings_summary.json"

SURFACES = ("Hard", "Clay", "Grass", "Carpet")
MU_YEARS = range(2010, 2019)              # the surface averages: 2010-2018, frozen
TUNE_YEARS = range(2013, 2019)            # tuning targets (2010-2012 warm up)
# A first grid (variances from 0.01 and 0.005, drift to 2e-4, every newcomer at 0) chose its corner for both
# tours; a second (variances to 0.02 and 0.01, drift to 8e-4, newcomers' serve and return starts from 0 to
# -0.3) put the serve variance at its top. A newcomer, mostly a qualifier or a junior, serves worse against
# the pool than an average player. Only a newcomer's serve start minus return start matters: adding one
# constant to every serve and every return rating changes no prediction (the tests show it), so the return
# start is fixed at 0 and the serve start carries the difference.
GRID = {"var_serve": [0.005, 0.01, 0.02, 0.04, 0.08], "var_return": [0.0025, 0.005, 0.01],
        "drift": [5e-5, 1e-4, 2e-4, 4e-4], "start_serve": [0.0, -0.1, -0.2, -0.3]}
START_RETURN = 0.0
VAR_FLOOR = 1e-5                          # a variance never falls below this
SEED = 20261001
EPS = 1e-12
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The rating pass

def rating_pass(week, event, rnd, a, b, mu, upd, n_a, w_a, n_b, w_b, n_players: int, var_serve: float,
                var_return: float, drift: float, start_serve: float = 0.0, start_return: float = 0.0) -> np.ndarray:
    """One chronological pass over a tour's matches, in the table's order.

    Inputs are sequences: week (the tournament date in days), event (a code unique within its week), rnd
    (round order), a and b (player codes 0..n_players-1), mu (the log-odds intercept of the match's
    surface), upd (whether the match moves ratings), and the box score: n_a and w_a, A's serve points and
    serve points won; n_b and w_b, B's. A newcomer starts at ``start_serve`` and ``start_return`` with
    variances ``var_serve`` and ``var_return``.

    Returns one row per match with the pre-match values: serve rating, return rating, their variances and
    the serve and return points rated so far, for A (columns 0, 2, 4, 6, 8, 10) and B (1, 3, 5, 7, 9, 11).

    The update. A serving to B: eta = mu + S_A - R_B, p = 1 / (1 + exp(-eta)); g = w - n p (points above
    expectation) and h = n p (1 - p) (their information). With V = var(S_A) + var(R_B):
        S_A += var(S_A) g / (1 + V h),  R_B -= var(R_B) g / (1 + V h),
        var(S_A) -= var(S_A)^2 h / (1 + V h),  var(R_B) -= var(R_B)^2 h / (1 + V h),
    one Newton step of the Gaussian posterior (the ratings' correlation is dropped, as Glicko drops it).
    B serving to A likewise. Both use the values the match was predicted with.

    Drift. When a player is first seen in a week, both variances grow by ``drift`` per week since their
    last week, capped at a newcomer's (``var_serve``, ``var_return``).

    The time rule is stage1_baselines.elo_pass's: a round's updates wait for the event's next round, an
    event's reach the player's other events once the week is over.
    """
    S = [float(start_serve)] * n_players
    R = [float(start_return)] * n_players
    VS = [var_serve] * n_players
    VR = [var_return] * n_players
    NS = [0.0] * n_players
    NR = [0.0] * n_players
    LW = [None] * n_players
    out = np.full((len(week), 12), np.nan)
    # per (player, event) within the current week: deltas of earlier rounds [S, R, VS, VR, NS, NR], the round
    # of the pending entry, and the pending deltas of that round [S, R, VS, VR, NS, NR]
    lo: dict = {}
    cur = None
    exp = math.exp
    for i in range(len(week)):
        wk = week[i]
        if wk != cur:
            for p, st in [(k[0], v) for k, v in lo.items()]:
                S[p] += st[0] + st[7]
                R[p] += st[1] + st[8]
                VS[p] = max(VS[p] + st[2] + st[9], VAR_FLOOR)
                VR[p] = max(VR[p] + st[3] + st[10], VAR_FLOOR)
                NS[p] += st[4] + st[11]
                NR[p] += st[5] + st[12]
            lo.clear()
            cur = wk
        e, r = event[i], rnd[i]
        sts = []
        for p in (a[i], b[i]):
            last = LW[p]
            if last != wk:
                if last is not None and drift > 0.0:
                    grow = drift * (wk - last) / 7.0
                    VS[p] = min(VS[p] + grow, var_serve)
                    VR[p] = min(VR[p] + grow, var_return)
                LW[p] = wk
            st = lo.get((p, e))
            if st is None:
                st = lo[(p, e)] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, r, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            elif st[6] < r:
                for j in range(6):
                    st[j] += st[7 + j]
                    st[7 + j] = 0.0
                st[6] = r
            sts.append(st)
        pa, pb = a[i], b[i]
        xa, xb = sts
        sa, ra = S[pa] + xa[0], R[pa] + xa[1]
        sb, rb = S[pb] + xb[0], R[pb] + xb[1]
        vsa, vra = max(VS[pa] + xa[2], VAR_FLOOR), max(VR[pa] + xa[3], VAR_FLOOR)
        vsb, vrb = max(VS[pb] + xb[2], VAR_FLOOR), max(VR[pb] + xb[3], VAR_FLOOR)
        o = out[i]
        o[0], o[1], o[2], o[3] = sa, sb, ra, rb
        o[4], o[5], o[6], o[7] = vsa, vsb, vra, vrb
        o[8], o[9], o[10], o[11] = NS[pa] + xa[4], NS[pb] + xb[4], NR[pa] + xa[5], NR[pb] + xb[5]
        if upd[i]:
            m = mu[i]
            for n, w, s_srv, v_srv, r_ret, v_ret, x_srv, x_ret in (
                    (n_a[i], w_a[i], sa, vsa, rb, vrb, xa, xb), (n_b[i], w_b[i], sb, vsb, ra, vra, xb, xa)):
                if n <= 0:
                    continue
                p = 1.0 / (1.0 + exp(-(m + s_srv - r_ret)))
                g = w - n * p
                h = n * p * (1.0 - p)
                den = 1.0 + (v_srv + v_ret) * h
                x_srv[7] += v_srv * g / den
                x_srv[9] -= v_srv * v_srv * h / den
                x_srv[11] += n
                x_ret[8] -= v_ret * g / den
                x_ret[10] -= v_ret * v_ret * h / den
                x_ret[12] += n
    return out


def expected_serve(out: np.ndarray, mu: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each player's expected serve-point share against this opponent: A's from S_A - R_B, B's from S_B - R_A."""
    pa = 1.0 / (1.0 + np.exp(-(mu + out[:, 0] - out[:, 3])))
    pb = 1.0 / (1.0 + np.exp(-(mu + out[:, 1] - out[:, 2])))
    return pa, pb


def serve_logloss(pa, pb, n_a, w_a, n_b, w_b) -> tuple[float, float]:
    """Log loss per serve point of the expected shares (both servers), and the number of serve points."""
    pa = np.clip(pa, EPS, 1 - EPS)
    pb = np.clip(pb, EPS, 1 - EPS)
    ll = -(w_a * np.log(pa) + (n_a - w_a) * np.log(1 - pa) + w_b * np.log(pb) + (n_b - w_b) * np.log(1 - pb))
    pts = float(np.sum(n_a + n_b))
    return float(np.sum(ll) / pts), pts


# ------------------------------------------------------------------------------------------------
# Inputs

def load_history() -> pd.DataFrame:
    """Every match in the table's order, with A's and B's serve points and serve points won."""
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "status", "format",
                        "surface", "has_box", "tournament_id", "tournament_date", "round_order", "player_a_id",
                        "player_b_id"])
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "spw_n", "spw_d"])
    a = mp[mp["side"].eq("A")].set_index("match_id")
    b = mp[mp["side"].eq("B")].set_index("match_id")
    m["n_a"], m["w_a"] = m["match_id"].map(a["spw_d"]).to_numpy(), m["match_id"].map(a["spw_n"]).to_numpy()
    m["n_b"], m["w_b"] = m["match_id"].map(b["spw_d"]).to_numpy(), m["match_id"].map(b["spw_n"]).to_numpy()
    box = m[["n_a", "w_a", "n_b", "w_b"]].notna().all(axis=1) & (m["n_a"] > 0) & (m["n_b"] > 0)
    m["updates"] = m["status"].eq("completed") & m["has_box"] & box
    for c in ("n_a", "w_a", "n_b", "w_b"):
        m[c] = m[c].where(m["updates"], 0.0).astype("float64")
    return m


def surface_means(m: pd.DataFrame) -> dict:
    """Per tour and surface: the log-odds of the pooled serve-point share over the rating matches of 2010-2018
    (both servers); a surface with under 100 such matches takes the tour's. Key (tour, surface or None)."""
    g = m[m["updates"] & m["year"].isin(list(MU_YEARS))]
    out = {}
    for tour in C.TOURS:
        t = g[g["tour"].eq(tour)]
        share = (t["w_a"].sum() + t["w_b"].sum()) / (t["n_a"].sum() + t["n_b"].sum())
        out[(tour, None)] = {"share": float(share), "mu": float(math.log(share / (1 - share))), "matches": int(len(t))}
        for s in SURFACES:
            ts = t[t["surface"].eq(s)]
            if len(ts) >= 100:
                sh = (ts["w_a"].sum() + ts["w_b"].sum()) / (ts["n_a"].sum() + ts["n_b"].sum())
                out[(tour, s)] = {"share": float(sh), "mu": float(math.log(sh / (1 - sh))), "matches": int(len(ts))}
            else:
                out[(tour, s)] = {**out[(tour, None)], "matches": int(len(ts)), "uses_tour_mean": True}
    return out


def mu_of(m: pd.DataFrame, means: dict) -> np.ndarray:
    """Each match's intercept: its tour and surface's, or the tour's when the surface is unknown."""
    return np.array([means[(t, s if s in SURFACES else None)]["mu"] for t, s in zip(m["tour"], m["surface"])],
                    dtype="float64")


def arrays(m: pd.DataFrame, mu: np.ndarray) -> dict:
    """The inputs of rating_pass() for one tour's matches, already in the table's order."""
    players, codes = np.unique(np.concatenate([m["player_a_id"].to_numpy(), m["player_b_id"].to_numpy()]),
                               return_inverse=True)
    return {"week": (m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")).tolist(),
            "event": pd.factorize(m["tournament_date"].astype(str) + "|" + m["tournament_id"])[0].tolist(),
            "rnd": m["round_order"].astype(int).tolist(),
            "a": codes[:len(m)].tolist(), "b": codes[len(m):].tolist(), "mu": mu.tolist(),
            "upd": m["updates"].astype(bool).tolist(),
            "n_a": m["n_a"].tolist(), "w_a": m["w_a"].tolist(), "n_b": m["n_b"].tolist(), "w_b": m["w_b"].tolist(),
            "n_players": int(len(players)), "players": players}


def run(h: dict, k: dict) -> np.ndarray:
    return rating_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["mu"], h["upd"], h["n_a"], h["w_a"],
                       h["n_b"], h["w_b"], h["n_players"], k["var_serve"], k["var_return"], k["drift"],
                       k.get("start_serve", 0.0), k.get("start_return", START_RETURN))


# ------------------------------------------------------------------------------------------------
# Tuning on 2013-2018 and the black-box probe

def tune(m: pd.DataFrame, mu: np.ndarray) -> tuple[dict, pd.DataFrame]:
    """Per tour: the grid setting with the lowest log loss per serve point on the evaluation-level rating matches
    of 2013-2018. Only rating matches of 2010-2018 enter these passes; a match that moves no rating changes
    nothing, so leaving the others out gives the same values."""
    rows, chosen = [], {}
    for tour in C.TOURS:
        sel = (m["tour"].eq(tour) & m["updates"] & m["year"].le(TUNE_YEARS[-1])).to_numpy()
        t = m[sel].reset_index(drop=True)
        h = arrays(t, mu[sel])
        target = (t["level"].isin(C.EVAL_LEVELS) & t["year"].isin(list(TUNE_YEARS))).to_numpy()
        na, wa, nb, wb = (t[c].to_numpy()[target] for c in ("n_a", "w_a", "n_b", "w_b"))
        mut = mu[sel][target]
        for values in itertools.product(*GRID.values()):
            k = dict(zip(GRID, values))
            out = run(h, k)[target]
            pa, pb = expected_serve(out, mut)
            ll, pts = serve_logloss(pa, pb, na, wa, nb, wb)
            rows.append({"tour": tour, **k, "logloss_per_serve_point": ll, "serve_points": pts, "matches": int(target.sum())})
        g = pd.DataFrame([r for r in rows if r["tour"] == tour])
        best = g.loc[g["logloss_per_serve_point"].idxmin()]
        chosen[tour] = {**{c: float(best[c]) for c in GRID}, "start_return": START_RETURN}
        log(f"{tour}: chosen {chosen[tour]} (log loss {best['logloss_per_serve_point']:.5f} per serve point)")
    return chosen, pd.DataFrame(rows)


def probe_by_round(h: dict, k: dict, n_cuts: int = 4, seed: int = SEED, from_quantile: float = 0.85) -> dict:
    """Black-box check of the time rule on a real history, cut by date, event and round (as stage1_baselines'
    probe, but on serve points). At each cut match, the serve points won of every match the rule does not let
    the cut see (its own round and later rounds of its event, the week's other events, later weeks) are
    redrawn at random, and the pass re-run. The pre-match values of every match of earlier weeks, and of the
    cut event's rounds up to the cut's, must not move."""
    rng = np.random.default_rng(seed)
    base = run(h, k)
    week, event, rnd = np.asarray(h["week"]), np.asarray(h["event"]), np.asarray(h["rnd"])
    na, nb = np.asarray(h["n_a"]), np.asarray(h["n_b"])
    cand = np.flatnonzero(np.asarray(h["upd"]) & (week >= np.quantile(week, from_quantile)))
    changed_protected = protected = changed_open = 0
    for c in rng.choice(cand, size=min(n_cuts, len(cand)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((event != event[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (event == event[c]) & (rnd <= rnd[c]))
        wa = np.where(later, np.floor(rng.random(len(week)) * (na + 1)), np.asarray(h["w_a"]))
        wb = np.where(later, np.floor(rng.random(len(week)) * (nb + 1)), np.asarray(h["w_b"]))
        got = run({**h, "w_a": wa.tolist(), "w_b": wb.tolist()}, k)
        diff = ~np.all(np.isclose(got, base, equal_nan=True, rtol=0, atol=0), axis=1)
        protected += int(keep.sum())
        changed_protected += int((diff & keep).sum())
        changed_open += int((diff & ~keep).sum())
    return {"cuts": int(min(n_cuts, len(cand))), "protected_matches_checked": protected,
            "protected_matches_changed": changed_protected, "later_matches_changed": changed_open}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    m = load_history()
    log(f"matches: {len(m):,}; moving ratings: {int(m['updates'].sum()):,}")
    means = surface_means(m)
    mu = mu_of(m, means)
    chosen, grid = tune(m, mu)
    grid.to_csv(TUNING, index=False)

    cols = ["serve_a", "serve_b", "return_a", "return_b", "var_serve_a", "var_serve_b", "var_return_a",
            "var_return_b", "serve_pts_a", "serve_pts_b", "return_pts_a", "return_pts_b"]
    block = np.full((len(m), 12), np.nan)
    probes = {}
    for tour in C.TOURS:
        idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
        t = m.iloc[idx].reset_index(drop=True)
        h = arrays(t, mu[idx])
        h = _LLE.ratings_arrays(t, h)   # level layer (LLE_LAYER)
        block[idx] = run(h, chosen[tour])
        log(f"{tour}: full pass done")
        probes[tour] = probe_by_round(h, chosen[tour])
        log(f"{tour}: probe {probes[tour]}")
    out = m[["match_id", "tour", "year", "updates"]].copy()
    for j, c in enumerate(cols):
        if c.startswith("var_"):
            out[c.replace("var_", "sd_")] = np.sqrt(block[:, j]).astype("float32")
        else:
            out[c] = block[:, j].astype("float32")
    out["mu_logit"] = mu.astype("float32")
    pa, pb = expected_serve(block, mu)
    out["p_serve_a"], out["p_serve_b"] = pa, pb
    out.to_parquet(RATINGS, index=False, compression="zstd")
    log(f"wrote {RATINGS.name}")

    # summaries: tuning detail, out-of-sample log loss, the spread of ratings, and the highest-rated players
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "mu_years": [MU_YEARS[0], MU_YEARS[-1]], "tune_years": [TUNE_YEARS[0], TUNE_YEARS[-1]], "grid": GRID,
               "var_floor": VAR_FLOOR, "surface_means": [{"tour": t, "surface": s or "all", **v} for (t, s), v in means.items()],
               "chosen": chosen, "probe_by_round": probes,
               "matches": {t: int(m["tour"].eq(t).sum()) for t in C.TOURS},
               "rating_matches": {t: int((m["tour"].eq(t) & m["updates"]).sum()) for t in C.TOURS}}
    detail = []
    for tour in C.TOURS:
        g = grid[grid["tour"].eq(tour)].sort_values("logloss_per_serve_point")
        k = chosen[tour]
        edge = {c: bool(k[c] in (min(GRID[c]), max(GRID[c]))) for c in GRID}
        ev = (m["tour"].eq(tour) & m["updates"] & m["level"].isin(C.EVAL_LEVELS)).to_numpy()
        rows = []
        for name, yrs in (("2013-2018", range(2013, 2019)), ("2019-2026", range(2019, 2027)), ("2022-2026", range(2022, 2027))):
            sel = ev & m["year"].isin(list(yrs)).to_numpy()
            ll, pts = serve_logloss(pa[sel], pb[sel], *(m[c].to_numpy()[sel] for c in ("n_a", "w_a", "n_b", "w_b")))
            # the same serve points scored with the surface average alone (no player information)
            p0 = 1.0 / (1.0 + np.exp(-mu[sel]))
            ll0, _ = serve_logloss(p0, p0, *(m[c].to_numpy()[sel] for c in ("n_a", "w_a", "n_b", "w_b")))
            rows.append({"window": name, "matches": int(sel.sum()), "serve_points": pts, "logloss": ll,
                         "logloss_surface_mean": ll0, "better_milli_per_point": 1000 * (ll0 - ll)})
        detail.append({"tour": tour, "best": float(g["logloss_per_serve_point"].iloc[0]),
                       "worst": float(g["logloss_per_serve_point"].iloc[-1]), "on_grid_edge": edge,
                       "within_0_1_milli_of_best": int((g["logloss_per_serve_point"] <= g["logloss_per_serve_point"].iloc[0] + 1e-4).sum()),
                       "grid_points": int(len(g)), "scored": rows})
    summary["tuning_detail"] = detail
    # each player's pre-match values, one row per player and match
    long = pd.concat([pd.DataFrame({"order": np.arange(len(m)), "tour": m["tour"].to_numpy(), "year": m["year"].to_numpy(),
                                    "evaluation": m["evaluation"].to_numpy(), "player": m[f"player_{x}_id"].to_numpy(),
                                    "serve": out[f"serve_{x}"].to_numpy(), "return": out[f"return_{x}"].to_numpy(),
                                    "serve_pts": out[f"serve_pts_{x}"].to_numpy(), "return_pts": out[f"return_pts_{x}"].to_numpy()})
                      for x in ("a", "b")], ignore_index=True)
    names = (pd.read_parquet(C.MATCH_PLAYERS, columns=["player_id", "player_name"])
             .drop_duplicates("player_id", keep="last").set_index("player_id")["player_name"])
    spread, top = [], []
    for tour in C.TOURS:
        # the spread of ratings among established players (2,000+ rated serve points) in 2022-2026 evaluation matches
        est = long[long["tour"].eq(tour) & long["evaluation"] & long["year"].ge(2022) & long["serve_pts"].ge(2000)]
        spread.append({"tour": tour, "player_matches": int(len(est)), "sd_serve": float(est["serve"].std()),
                       "sd_return": float(est["return"].std()),
                       "corr_serve_return": float(np.corrcoef(est["serve"], est["return"])[0, 1])})
        # the latest pre-match values of each established player who played in 2026 (a sanity check)
        last = long[long["tour"].eq(tour)].sort_values("order").groupby("player").tail(1)
        last = last[last["year"].eq(2026) & last["serve_pts"].ge(2000) & last["return_pts"].ge(2000)]
        for kind in ("serve", "return"):
            for _, r in last.sort_values(kind, ascending=False).head(8).iterrows():
                top.append({"tour": tour, "kind": kind, "player": r["player"], "name": names.get(r["player"], r["player"]),
                            "rating": round(float(r[kind]), 4), "serve_points_rated": float(r["serve_pts"]),
                            "return_points_rated": float(r["return_pts"])})
    summary["spread_2022_2026"] = spread
    summary["highest_2026"] = top
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"wrote {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
