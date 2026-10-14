"""Stage A of "rating systems against Elo": Glicko-2 (weekly rating periods, and match by match), Glicko-1 (each with the
volatility held fixed) and TrueSkill, tuned on 2013-2018 and frozen; every match's pre-match values; checks; probes.

The systems (ratings.py has the formulas and the time rule)
    glicko2     Glicko-2 as Glickman specifies it, with a tournament date (the time rule's week) as the rating period: a
                player's games of a week are scored together against the opponents' ratings at the start of the week
    glicko1     the same with the volatility fixed at sigma0 (Glicko-1, sigma0 in the part of c)
    glicko2m    Glicko-2 match by match: each round is a rating period, and the drift is by elapsed time
    glicko1m    the same with the volatility fixed
    trueskill   two-player TrueSkill without draws, with a per-match drift tau and a per-year drift gamma
    glicko_cs   correlated surface skills with Glicko's (Kalman) update: a skill per surface, newcomers' surfaces
                correlated rho, match by match, drift by elapsed time (ratings.correlated_pass, link "logit"); the
                literature's most consistent extension (surface), in Bayesian form; no separate surface blend
    trueskill_cs  the same with TrueSkill's update (link "probit")
    ttt         TrueSkill Through Time run causally: each finished week joins the model as a batch, then one backward and
                one forward expectation-propagation sweep over the trailing ``window`` weeks re-scores every game in it
                against the current estimates (ratings.TTT); within a week, TrueSkill's update round by round; the
                surface blended as for the others. The literature's best results-only rating for tennis (Landfried and
                Mocskos 2025; Maystre et al. 2019), there measured against a constant-K Elo only

Tuning (per system and tour; then frozen), as Stage 1 tuned Elo
    1. The constants on the log loss of the OVERALL rating's forecast over the evaluation matches of 2013-2018 (2010-2012
       warm up; the history read stops at the end of 2018), on GRIDS. When a best value lies on an edge of its grid (other
       than a natural bound: TrueSkill's tau or gamma at 0), the grid is widened past it, geometrically, and the new
       settings run; up to MAX_WIDEN rounds. Every setting is recorded with the round that added it.
    2. The surface weight w (0 to 1 in 0.05) on the same matches with the constants fixed: P(A wins) from the means
       blended (1 - w) overall + w surface (ratings.blend).
Then the full passes over 2010-2026 with the frozen constants.

Checks and probes
    * The tuning pass equals the full pass's first rows (to the last bit: each pass is causal).
    * The probe cut by date, event and round (stage1_baselines.probe_by_round, as Stages 1 and the UFC-ideas Stage A ran
      it) on the matches from PROBE_FROM (history inside the slice), PROBE_CUTS cuts per system and tour: every result
      the rule does not let the cut see is flipped at random and the pass re-run; the pre-match values of the matches
      the cut may see must not move. A leaky control (every row its own round of one event per week, so it sees its
      week's earlier rows) must move them.

Writes, in data/studies/rating_systems/:
    stageA_ratings.parquet          one row per match of Stage 0's table (872,704): for every system p_<system> (the
                                    frozen surface blend) and p_<system>_overall; for glicko2m, glicko2 and trueskill each
                                    side's overall and surface mean and uncertainty (phi or the variance), the overall
                                    rated-match counts and (Glicko-2) the volatility, float32
    stageA_tuning.csv               every setting tried: system, tour, grid round, constants, log loss 2013-2018, seconds
    stageA_surface_weights.csv      the surface-weight grid per system and tour
    stageA_summary.json             the grids and their widening, the chosen constants, flatness, edges, the checks, the
                                    probes, timings, the ten highest-rated players per tour at the end of the table

Run: ./python.sh src/eda/rating_systems/stageA_ratings.py      (5 worker processes)
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.rating_systems import ratings as R  # noqa: E402

OUT = RC.OUT
RATINGS = OUT / "stageA_ratings.parquet"
TUNING = OUT / "stageA_tuning.csv"
WEIGHTS = OUT / "stageA_surface_weights.csv"
SUMMARY = OUT / "stageA_summary.json"

WORKERS = 5
SYSTEMS = ("glicko2", "glicko1", "glicko2m", "glicko1m", "trueskill", "glicko_cs", "trueskill_cs", "ttt")
CORRELATED = ("glicko_cs", "trueskill_cs")       # surface inside the model: no blend weight
# Centred on a first exploration of the tuning years (the weekly Glicko's best lay at RD0 550-700 and sigma 0.07, the
# match-by-match one's at RD0 600, sigma 0.07, TrueSkill's at sigma0 2-3, tau 0, gamma 0.5); widened by the rule below.
GRIDS = {
    "glicko2": {"rd0": [350.0, 450.0, 550.0, 700.0, 900.0], "sigma0": [0.04, 0.055, 0.07, 0.085, 0.1], "tau": [0.2, 0.6, 1.0]},
    "glicko1": {"rd0": [350.0, 450.0, 550.0, 700.0, 900.0], "sigma0": [0.04, 0.055, 0.07, 0.085, 0.1]},
    "glicko2m": {"rd0": [400.0, 500.0, 600.0, 700.0, 800.0], "sigma0": [0.05, 0.06, 0.07, 0.08, 0.09], "tau": [0.2, 0.6, 1.0]},
    "glicko1m": {"rd0": [400.0, 500.0, 600.0, 700.0, 800.0], "sigma0": [0.05, 0.06, 0.07, 0.08, 0.09]},
    "trueskill": {"sigma0": [1.5, 2.0, 2.5, 3.0, 3.5], "tau": [0.0, 0.005, 0.01, 0.02], "gamma": [0.3, 0.4, 0.5, 0.6, 0.7]},
    # a first exploration put the best correlation near 0.985 for both links, and a drift with its own correlation
    # no better than one sharing rho, so the drift shares rho
    "glicko_cs": {"rd0": [500.0, 600.0, 700.0], "sigma0": [0.06, 0.07, 0.08], "rho": [0.97, 0.98, 0.985, 0.99, 0.995]},
    "trueskill_cs": {"sigma0": [1.5, 2.0, 2.5], "gamma": [0.4, 0.5, 0.6], "rho": [0.97, 0.98, 0.985, 0.99, 0.995]},
    # TrueSkill's own best constants (sigma0 2-3, gamma 0.4) and two smoothing windows; a first run with a 26-week window
    # beat TrueSkill on the same constants by 1.4 milli-log-loss (men, 2013-2018), an 8-week one by 0.4
    "ttt": {"sigma0": [1.5, 2.0, 2.5], "gamma": [0.3, 0.4, 0.5], "window": [26.0, 52.0]},
}
NATURAL_LOWER = {("trueskill", "tau"): 0.0, ("trueskill", "gamma"): 0.0}
CORRELATION = "rho"                              # widened in log(1 - rho), so it never reaches 1
MAX_WIDEN = 3
SURFACE_WEIGHTS = [round(x, 2) for x in np.arange(0.0, 1.0001, 0.05)]
KEEP_COMPONENTS = ("glicko2m", "trueskill", "glicko_cs")   # systems whose overall per-side values are stored
PROBE_FROM = "2024-01-01"
PROBE_CUTS = 6
SEED = 20261002
LAST_YEAR = None
T0 = time.time()

# A reduced run to check the script end to end (history to 2014, tiny grids, outputs to STAGEA_SMOKE_DIR).
SMOKE = os.environ.get("STAGEA_SMOKE_DIR")
if SMOKE:
    OUT = Path(SMOKE)
    RATINGS, TUNING, WEIGHTS, SUMMARY = (OUT / "stageA_ratings.parquet", OUT / "stageA_tuning.csv",
                                         OUT / "stageA_surface_weights.csv", OUT / "stageA_summary.json")
    GRIDS = {"glicko2": {"rd0": [350.0, 500.0], "sigma0": [0.06], "tau": [0.5]},
             "glicko1": {"rd0": [350.0], "sigma0": [0.06]},
             "glicko2m": {"rd0": [500.0], "sigma0": [0.06, 0.08], "tau": [0.5]},
             "glicko1m": {"rd0": [500.0], "sigma0": [0.07]},
             "trueskill": {"sigma0": [2.0], "tau": [0.0], "gamma": [0.4, 0.6]},
             "glicko_cs": {"rd0": [600.0], "sigma0": [0.07], "rho": [0.98, 0.99]},
             "trueskill_cs": {"sigma0": [2.0], "gamma": [0.5], "rho": [0.98]},
             "ttt": {"sigma0": [2.0], "gamma": [0.4], "window": [8.0]}}
    MAX_WIDEN = 1
    RC.TUNE_YEARS = range(2013, 2014)
    LAST_YEAR = 2014
    PROBE_FROM, PROBE_CUTS = "2014-06-01", 2


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Workers

_W: dict = {}


def init_worker() -> None:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    if SMOKE:
        RC.TUNE_YEARS = range(2013, 2014)
    m = RC.load_table(LAST_YEAR)
    for tour in C.TOURS:
        t = m[m["tour"].eq(tour)].reset_index(drop=True)
        _W[(tour, "full")] = RC.history(t)
        _W[(tour, "full", "week_date")] = t["tournament_date"].to_numpy()
        last = int(np.flatnonzero(t["year"].le(RC.TUNE_YEARS[-1]).to_numpy()).max())
        _W[(tour, "tune")] = RC.history(t.iloc[:last + 1].reset_index(drop=True))


def _hist(tour: str, span: str) -> dict:
    if not _W:
        init_worker()
    return _W[(tour, span)]


def grid_job(spec: dict) -> dict:
    """One tuning pass: the overall component on the tuning history, scored on 2013-2018."""
    t0 = time.time()
    h = _hist(spec["tour"], "tune")
    res = R.run(h, spec["system"], {**spec["cfg"], "surface": False})
    mask = RC.tune_mask(h)
    p = R.blend(spec["system"], res, 0.0)
    return {"system": spec["system"], "tour": spec["tour"], "round": spec["round"], **spec["cfg"],
            "log_loss_2013_2018": RC.log_loss(p[mask], h["y"][mask]), "matches": int(mask.sum()),
            "seconds": round(time.time() - t0, 2)}


def weight_job(spec: dict) -> dict:
    """Both components on the tuning history at the chosen constants: the log loss at every surface weight, and the
    rows themselves (for the check against the full pass)."""
    t0 = time.time()
    h = _hist(spec["tour"], "tune")
    res = R.run(h, spec["system"], spec["cfg"])
    mask = RC.tune_mask(h)
    rows = [{"system": spec["system"], "tour": spec["tour"], "w": w,
             "log_loss_2013_2018": RC.log_loss(R.blend(spec["system"], res, w)[mask], h["y"][mask]),
             "matches": int(mask.sum())} for w in SURFACE_WEIGHTS]
    return {"system": spec["system"], "tour": spec["tour"], "rows": rows, "res": res,
            "seconds": round(time.time() - t0, 2)}


def full_job(spec: dict) -> dict:
    t0 = time.time()
    h = _hist(spec["tour"], "full")
    res = R.run(h, spec["system"], spec["cfg"])
    return {"system": spec["system"], "tour": spec["tour"], "res": res, "seconds": round(time.time() - t0, 2)}


def probe_job(spec: dict) -> dict:
    """The probe cut by date, event and round on the matches from PROBE_FROM (history inside the slice)."""
    t0 = time.time()
    h_full = _hist(spec["tour"], "full")
    dates = _W[(spec["tour"], "full", "week_date")]
    rows = np.flatnonzero(dates >= np.datetime64(PROBE_FROM))
    lo = int(rows[0])
    h = {k: (v[lo:] if isinstance(v, (list, np.ndarray)) and len(v) == len(h_full["week"]) else v)
         for k, v in h_full.items()}
    system, cfg = spec["system"], spec["cfg"]

    def ratings(hh):
        res = R.run(hh, system, cfg)
        return np.concatenate([res[c] for c in ("overall", "surface") if c in res], axis=1)

    def leaky(hh):
        """A control that breaks the rule: each week's matches run in reverse order, each its own round of one event,
        so a match sees the later rounds of its week."""
        n = len(hh["week"])
        order = np.lexsort((-np.arange(n), np.asarray(hh["week"])))
        inv = np.empty(n, dtype="int64")
        inv[order] = np.arange(n)
        h2 = {k: ([v[j] for j in order] if isinstance(v, list) and len(v) == n else
                  v[order] if isinstance(v, np.ndarray) and len(v) == n else v) for k, v in hh.items()}
        h2["event"], h2["rnd"] = [0] * n, list(range(n))
        return ratings(h2)[inv]
    fn = leaky if spec.get("leaky") else ratings
    res = B.probe_by_round(h, fn, n_cuts=PROBE_CUTS, seed=SEED, from_quantile=0.5)
    return {"system": system, "tour": spec["tour"], "leaky": bool(spec.get("leaky")), **res,
            "slice_matches": int(len(h["week"])), "slice_from": PROBE_FROM, "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------
# Grids and their widening

def cfg_key(system: str, cfg: dict) -> tuple:
    return (system,) + tuple(round(float(cfg[p]), 9) for p in GRIDS[system])


def grid_values(system: str, extra: dict) -> dict:
    """The grid of a system with the values added by widening."""
    return {p: sorted(set(GRIDS[system][p]) | set(extra.get((system, p), []))) for p in GRIDS[system]}


def widen(system: str, tour: str, g: pd.DataFrame, values: dict) -> dict:
    """For each constant whose best value lies on an edge of the values tried (not a natural bound), one value past
    it, geometrically (the ratio of the edge to its neighbour)."""
    best = g.loc[g["log_loss_2013_2018"].idxmin()]
    add = {}
    for p, vals in values.items():
        v = float(best[p])
        if len(vals) < 2:
            continue
        if p == CORRELATION:                              # geometric in 1 - rho
            if v == vals[0]:
                add[p] = round(1 - (1 - vals[0]) ** 2 / (1 - vals[1]), 6)
            elif v == vals[-1]:
                add[p] = round(1 - (1 - vals[-1]) ** 2 / (1 - vals[-2]), 6)
            continue
        if v == vals[0]:
            lb = NATURAL_LOWER.get((system, p))
            if lb is not None and v <= lb:
                continue
            new = v * (vals[0] / vals[1]) if vals[1] > 0 and vals[0] > 0 else None
            if new is not None:
                add[p] = round(new, 6)
        elif v == vals[-1]:
            new = v * (vals[-1] / vals[-2]) if vals[-2] > 0 else v + (vals[-1] - vals[-2])
            add[p] = round(new, 6)
    return add


def edge_report(system: str, cfg: dict, values: dict) -> dict:
    out = {}
    for p, vals in values.items():
        v = float(cfg[p])
        out[p] = {"value": v, "lowest_tried": bool(v <= min(vals)), "highest_tried": bool(v >= max(vals)),
                  "natural_bound": bool(NATURAL_LOWER.get((system, p)) is not None and v <= NATURAL_LOWER[(system, p)])}
    return out


def flatness(g: pd.DataFrame, params: list[str]) -> dict:
    best = float(g["log_loss_2013_2018"].min())
    out = {"best": best, "worst": float(g["log_loss_2013_2018"].max()), "settings": int(len(g)),
           "within_0_1_milli": int((g["log_loss_2013_2018"] <= best + 0.0001).sum()),
           "within_0_5_milli": int((g["log_loss_2013_2018"] <= best + 0.0005).sum()),
           "within_1_milli": int((g["log_loss_2013_2018"] <= best + 0.001).sum()), "best_by_value": {}}
    for p in params:
        out["best_by_value"][p] = {str(k): round(1000 * (float(v) - best), 4)
                                   for k, v in g.groupby(p)["log_loss_2013_2018"].min().items()}
    return out


def read_grid() -> dict:
    """--reuse-grid: the settings an earlier run wrote to stageA_tuning.csv, keyed as run_grids keys them (a pass is
    deterministic, so a setting's log loss does not change between runs)."""
    if not TUNING.exists():
        return {}
    out = {}
    for r in pd.read_csv(TUNING).to_dict("records"):
        s = r["system"]
        if s not in GRIDS or any(pd.isna(r.get(p)) for p in GRIDS[s]):
            continue
        out[(r["tour"],) + cfg_key(s, r)] = {k: v for k, v in r.items() if not (isinstance(v, float) and np.isnan(v))}
    return out


def run_grids(ex, reuse: bool = False) -> tuple[pd.DataFrame, dict, dict]:
    """Every grid with up to MAX_WIDEN widening rounds. Returns all rows, the chosen constants and the widening log.
    With ``reuse`` the settings already in stageA_tuning.csv are read back instead of run."""
    extra: dict = {}
    done: dict = read_grid() if reuse else {}
    log(f"grid settings read back: {len(done)}")
    widening = {s: {t: [] for t in C.TOURS} for s in SYSTEMS}
    pending_round = {(s, t): 0 for s in SYSTEMS for t in C.TOURS}
    active = set(pending_round)
    rnd = 0
    while active:
        specs = []
        for system, tour in sorted(active):
            vals = grid_values(system, {(system, p): extra.get((system, p, tour), []) for p in GRIDS[system]})
            for combo in itertools.product(*vals.values()):
                cfg = dict(zip(vals.keys(), combo))
                key = (tour,) + cfg_key(system, cfg)
                if key not in done:
                    done[key] = None
                    specs.append({"system": system, "tour": tour, "cfg": cfg,
                                  "round": "grid" if rnd == 0 else f"widened {rnd}"})
        specs.sort(key=lambda s: (s["system"] not in ("glicko2", "glicko2m"), s["tour"]))
        log(f"grid round {rnd}: {len(specs)} passes")
        for r in ex.map(grid_job, specs, chunksize=1):
            done[(r["tour"],) + cfg_key(r["system"], r)] = r
        rows = pd.DataFrame([v for v in done.values() if v is not None])
        cols = ["system", "tour", "round", "rd0", "sigma0", "tau", "gamma", "rho", "window", "log_loss_2013_2018",
                "matches", "seconds"]
        rows.reindex(columns=cols).sort_values(["system", "tour", "log_loss_2013_2018"]).to_csv(TUNING, index=False)
        log(f"grid round {rnd} done; {len(rows)} settings saved (a rerun with --reuse-grid resumes from here)")
        nxt = set()
        if rnd < MAX_WIDEN:
            for system, tour in sorted(active):
                g = rows[rows["system"].eq(system) & rows["tour"].eq(tour)]
                vals = {p: sorted(float(v) for v in g[p].unique()) for p in GRIDS[system]}   # every value tried
                add = widen(system, tour, g, vals)
                if add:
                    for p, v in add.items():
                        extra.setdefault((system, p, tour), []).append(v)
                    widening[system][tour].append({"round": rnd + 1, "added": add})
                    nxt.add((system, tour))
        active = nxt
        rnd += 1
    rows = pd.DataFrame([v for v in done.values() if v is not None])
    chosen = {}
    for system in SYSTEMS:
        for tour in C.TOURS:
            g = rows[rows["system"].eq(system) & rows["tour"].eq(tour)]
            best = g.loc[g["log_loss_2013_2018"].idxmin()]
            chosen[(system, tour)] = {p: float(best[p]) for p in GRIDS[system]}
    return rows, chosen, {"rounds": widening, "values_added": {f"{s}|{p}|{t}": v for (s, p, t), v in extra.items()}}


# ------------------------------------------------------------------------------------------------
# Outputs

def player_names() -> pd.Series:
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "player_name"])
    mo = C.load_matches(["match_id", "order"]).set_index("match_id")["order"]
    mp["order"] = mp["match_id"].map(mo)
    return mp.sort_values("order").groupby("player_id")["player_name"].last()


MIN_TOP_MATCHES = 30     # the sanity list leaves out players with fewer rated matches (an uncertain mean can be high)


def top_players(m: pd.DataFrame, out: pd.DataFrame, system: str, k: int = 10) -> dict:
    """The k highest overall means per tour among players with a match in the table's last season and at least
    MIN_TOP_MATCHES rated matches before it, each read at the player's last match (the pre-match value: a sanity check
    of the scale, not a ranking). Without the floor the list is led by new player ids with a few wins and a wide
    uncertainty, among them the 2026 split identities (Stage 1's problem 1)."""
    names = player_names()
    res = {}
    last_year = int(m["year"].max())
    for tour in C.TOURS:
        t = m["tour"].eq(tour).to_numpy() & m["year"].eq(last_year).to_numpy()
        long = pd.concat([pd.DataFrame({"pid": m.loc[t, "player_a_id"].to_numpy(), "mu": out.loc[t, f"{system}_mu_a"].to_numpy(),
                                        "n": out.loc[t, "n_a"].to_numpy(), "order": m.loc[t, "order"].to_numpy()}),
                          pd.DataFrame({"pid": m.loc[t, "player_b_id"].to_numpy(), "mu": out.loc[t, f"{system}_mu_b"].to_numpy(),
                                        "n": out.loc[t, "n_b"].to_numpy(), "order": m.loc[t, "order"].to_numpy()})])
        lastv = long.sort_values("order").groupby("pid").last()
        lastv = lastv[lastv["n"] >= MIN_TOP_MATCHES].sort_values("mu", ascending=False).head(k)
        res[tour] = [{"rank": i + 1, "player_id": str(pid), "name": str(names.get(pid, "")), "mu": round(float(r["mu"]), 4),
                      "rated_matches_before": int(r["n"])} for i, (pid, r) in enumerate(lastv.iterrows())]
    return res


def top_only() -> int:
    """--top-only: recompute the sanity list from stageA_ratings.parquet and rewrite it in stageA_summary.json."""
    m = RC.load_table(LAST_YEAR)
    out = pd.read_parquet(RATINGS)
    assert (out["match_id"].to_numpy() == m["match_id"].to_numpy()).all()
    mm = m.assign(order=np.arange(len(m)))
    S = json.loads(SUMMARY.read_text(encoding="utf-8"))
    S["top10_end"] = {s: top_players(mm, out, s) for s in KEEP_COMPONENTS}
    S["top10_rule"] = f"at least {MIN_TOP_MATCHES} rated matches before the player's last match of the last season"
    SUMMARY.write_text(json.dumps(S, indent=2, default=float), encoding="utf-8")
    for s, v in S["top10_end"].items():
        for tour in C.TOURS:
            log(f"top {s} {tour}: " + ", ".join(x["name"] for x in v[tour]))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    OUT.mkdir(parents=True, exist_ok=True)
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    timings = {}
    m = RC.load_table(LAST_YEAR)
    log(f"matches: {len(m):,}")
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker) as ex:
        # ---- 1. the grids, widened where a best value is on an edge
        t1 = time.time()
        grid, chosen, widening = run_grids(ex, reuse="--reuse-grid" in argv)
        timings["grids_seconds"] = round(time.time() - t1, 1)
        timings["grid_settings_read_back"] = "--reuse-grid" in argv
        timings["grid_pass_seconds_total"] = round(float(grid["seconds"].sum()), 1)
        cols = ["system", "tour", "round", "rd0", "sigma0", "tau", "gamma", "rho", "window", "log_loss_2013_2018", "matches",
                "seconds"]
        grid.reindex(columns=cols).sort_values(["system", "tour", "log_loss_2013_2018"]).to_csv(TUNING, index=False)
        for (system, tour), cfg in chosen.items():
            log(f"chosen {system} {tour}: {cfg}")

        # ---- 2. the surface weight on the tuning years
        t2 = time.time()
        wspecs = [{"system": s, "tour": t, "cfg": chosen[(s, t)]} for s in SYSTEMS for t in C.TOURS]
        wres = list(ex.map(weight_job, wspecs, chunksize=1))
        wall = pd.DataFrame([r for x in wres for r in x["rows"]])
        wrows = wall[~wall["system"].isin(CORRELATED)].reset_index(drop=True)   # the correlated systems: no blend
        wrows.to_csv(WEIGHTS, index=False)
        wchosen = {(s, t): 0.0 for s in CORRELATED for t in C.TOURS}
        for (system, tour), g in wrows.groupby(["system", "tour"]):
            wchosen[(system, tour)] = float(g.loc[g["log_loss_2013_2018"].idxmin(), "w"])
        tune_res = {(x["system"], x["tour"]): x["res"] for x in wres}
        timings["surface_weights_seconds"] = round(time.time() - t2, 1)
        log(f"surface weights: {wchosen}")

        # ---- 3. the full passes and the probes
        t3 = time.time()
        fspecs = [{"system": s, "tour": t, "cfg": chosen[(s, t)]} for s in SYSTEMS for t in C.TOURS]
        pspecs = [{"system": s, "tour": t, "cfg": chosen[(s, t)]} for s in SYSTEMS for t in C.TOURS]
        pspecs += [{"system": s, "tour": t, "cfg": chosen[(s, t)], "leaky": True}
                   for s in ("glicko2m", "trueskill", "glicko_cs") for t in C.TOURS]
        ff = [ex.submit(full_job, s) for s in fspecs]
        fp = [ex.submit(probe_job, s) for s in pspecs]
        full = {}
        for f in ff:
            r = f.result()
            full[(r["system"], r["tour"])] = r
        probes = [f.result() for f in fp]
        timings["full_passes_and_probes_seconds"] = round(time.time() - t3, 1)
        for p in probes:
            log(f"probe {p['system']} {p['tour']}{' (leaky control)' if p['leaky'] else ''}: "
                f"{p['protected_matches_changed']} of {p['protected_matches_checked']} protected changed; "
                f"{p['later_matches_changed']} later changed")

    # ---- checks: the tuning pass is the full pass's prefix
    checks = {}
    for (system, tour), r in full.items():
        tr = tune_res[(system, tour)]
        worst = 0.0
        for comp in tr:
            a, b = tr[comp], r["res"][comp][:len(tr[comp])]
            same_nan = np.array_equal(np.isnan(a), np.isnan(b))
            d = np.nanmax(np.abs(a - b)) if np.isfinite(a).any() else 0.0
            worst = max(worst, float(d) if same_nan else np.inf)
        checks[f"{system}|{tour}"] = {"tuning_pass_vs_full_prefix_max_abs": worst, "rows": int(len(tr["overall"]))}
        assert worst == 0.0, (system, tour, worst)
    log("checks: every tuning pass equals its full pass's prefix exactly")

    # ---- outputs
    out = m[["match_id", "tour", "year"]].copy()
    blocks = {}
    for system in SYSTEMS:
        p = np.full(len(m), np.nan)
        po = np.full(len(m), np.nan)
        comp = {c: np.full((len(m), len(R.OUT_COLS)), np.nan) for c in full[(system, C.TOURS[0])]["res"]}
        for tour in C.TOURS:
            idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
            res = full[(system, tour)]["res"]
            assert len(res["overall"]) == len(idx)
            p[idx] = R.blend(system, res, wchosen[(system, tour)])
            po[idx] = R.blend(system, res, 0.0)
            for c in comp:
                comp[c][idx] = res[c]
        out[f"p_{system}"] = p
        if system not in CORRELATED:
            out[f"p_{system}_overall"] = po
        blocks[system] = comp
    for system in KEEP_COMPONENTS:
        o = blocks[system]["overall"]          # for glicko_cs: the match surface's mean and deviation
        out[f"{system}_mu_a"], out[f"{system}_mu_b"] = o[:, 0].astype("float32"), o[:, 1].astype("float32")
        out[f"{system}_u_a"], out[f"{system}_u_b"] = o[:, 2].astype("float32"), o[:, 3].astype("float32")
        if system == "glicko2m":
            out["n_a"], out["n_b"] = o[:, 6].astype("int32"), o[:, 7].astype("int32")
            out[f"{system}_vol_a"], out[f"{system}_vol_b"] = o[:, 4].astype("float32"), o[:, 5].astype("float32")
    RC.write_parquet(out, RATINGS)
    log(f"wrote {RATINGS.name} ({RATINGS.stat().st_size / 1e6:.1f} MB)")

    mm = m.assign(order=np.arange(len(m)))
    top = {s: top_players(mm, out, s) for s in KEEP_COMPONENTS}
    for s, v in top.items():
        for tour in C.TOURS:
            log(f"top {s} {tour}: " + ", ".join(x["name"] for x in v[tour]))

    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "design": {"systems": {"glicko2": "Glicko-2, a tournament date as the rating period",
                               "glicko1": "Glicko-2's weekly pass with the volatility fixed at sigma0 (Glicko-1)",
                               "glicko2m": "Glicko-2 match by match: each round a rating period, drift by elapsed time",
                               "glicko1m": "the match-by-match pass with the volatility fixed (Glicko-1)",
                               "trueskill": "two-player TrueSkill, no draws, beta = 1, per-match drift tau, per-year drift gamma",
                               "glicko_cs": "correlated surface skills, Glicko's (Kalman) update match by match; RD0 and the weekly "
                                            "drift sigma as Glicko's; surfaces correlated rho (prior and drift); no blend",
                               "trueskill_cs": "correlated surface skills with TrueSkill's update; sigma0, gamma per year, rho",
                               "ttt": "TrueSkill Through Time, causal: weekly batches, one backward-forward EP sweep over the "
                                      "trailing window (weeks) after each week; TrueSkill round by round within the week"},
                   "period_days": 7.0, "updates": list(RC.UPDATES), "tuning_years": [RC.TUNE_YEARS[0], RC.TUNE_YEARS[-1]],
                   "newcomer": "mean 0 (1500 for Glicko), deviation RD0 / 173.7178 (Glicko) or sigma0 (TrueSkill)",
                   "surface": "one rating per player and surface (hard, clay, grass, carpet), the same constants; means blended "
                              "(1 - w) overall + w surface, the uncertainty on the variance scale",
                   "tuning": "constants on the overall forecast's log loss, then w with the constants fixed (Stage 1's order)",
                   "widening": f"a best value on a grid edge (not a natural bound) adds one value past it, geometrically; up to {MAX_WIDEN} rounds"},
        "grids": GRIDS, "widening": widening,
        "settings_by_round": {f"{s}|{t}": grid[grid["system"].eq(s) & grid["tour"].eq(t)]["round"].value_counts().to_dict()
                              for s in SYSTEMS for t in C.TOURS},
        "chosen": {f"{s}|{t}": {**chosen[(s, t)], "w": wchosen[(s, t)]} for s in SYSTEMS for t in C.TOURS},
        "edges": {f"{s}|{t}": edge_report(s, chosen[(s, t)],
                                          {p: sorted(grid[grid["system"].eq(s) & grid["tour"].eq(t)][p].unique())
                                           for p in GRIDS[s]}) for s in SYSTEMS for t in C.TOURS},
        "flatness": {f"{s}|{t}": flatness(grid[grid["system"].eq(s) & grid["tour"].eq(t)], list(GRIDS[s]))
                     for s in SYSTEMS for t in C.TOURS},
        "surface_weight": {f"{s}|{t}": {"w": wchosen[(s, t)], "blend": s not in CORRELATED,
                                        "log_loss_w0": float(wall[(wall["system"] == s) & (wall["tour"] == t) & (wall["w"] == 0.0)]["log_loss_2013_2018"].iloc[0]),
                                        "log_loss_best": float(wall[(wall["system"] == s) & (wall["tour"] == t)]["log_loss_2013_2018"].min())}
                           for s in SYSTEMS for t in C.TOURS},
        "shared_code": RC.dependency_hashes(),
        "checks": checks, "probes": probes, "top10_end": top,
        "top10_rule": f"at least {MIN_TOP_MATCHES} rated matches before the player's last match of the last season",
        "full_pass_seconds": {f"{s}|{t}": full[(s, t)]["seconds"] for s in SYSTEMS for t in C.TOURS},
        "timings": timings, "workers": WORKERS, "table_rows": int(len(out)),
    }
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}; total {summary['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(top_only() if "--top-only" in sys.argv[1:] else main())
