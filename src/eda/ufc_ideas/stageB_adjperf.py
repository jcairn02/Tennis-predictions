"""Stage B, part 1: opponent-adjusted performance (adjperf) and defence (adjdef) for the tennis box-score statistics,
the UFC pipeline's layer-2 machinery (features/v4/layer2.py) rebuilt for tennis, its priors tuned, its features built.

For each statistic s (serve side: spw, first_won, second_won, ace, df, first_in, hold, bp_saved, bp_faced_pg; return
side: rpw, brk, bp_conv, rpw_first, rpw_second; whole match: tpw), each match's value is read on the log-odds scale (the
log scale for break points faced per service game, a count per game) as (x + 1/2) / (d + 1), and centred on the tour's
average on the match's surface (Stage 3's surface averages, 2010-2018, as Stage 4 used them):

    step 1  the opponent's norm. For the match's opponent o, over o's earlier box-score matches (the time rule: earlier
            weeks and earlier rounds of the same event), the mean of what o's opponents produced against o on s (adjperf:
            o's "allowed"), or of what o produced (adjdef: o's own), weighted by 2^(-age / h1) x units^tau, shrunk toward
            the surface average with K1 reference matches: E = sum w a / (sum w + K1 u_typ^tau); and the weighted mean
            absolute deviation around o's weighted mean, shrunk toward the population's (player-seasons of 2010-2018,
            each around its own mean) with the same K1: MAD = (sum w |a - mean| + K1 u_typ^tau MAD_pop) / (sum w + K1 ...)
    step 2  the per-match z. adjperf: (the player's value - o's allowed norm) / max(MAD, 0.05); adjdef: (o's own norm -
            o's value in this match) / max(MAD, 0.05), how far the player held o below o's norm; both clipped to +-4
    step 3  the player's average of z over earlier box-score matches, sum w z / (sum w + K3 u_typ^tau), w =
            2^(-age / h3) x units^tau (adjperf: the player's units; adjdef: the opponent's), in three forms: the last
            52 weeks (no decay), decayed (half-life h3) and career (no decay)

K1 and K3 are in matches: a reference match weighs u_typ^tau, u_typ the statistic's mean units per box-score match on
the tour in 2010-2018 (so with tau = 0 a match weighs 1, with tau = 1 its units, and K is K typical matches either way).

Tuning (the Brief: 2013-2018 only, 2010-2012 warm up; then frozen), per tour, for adjperf on spw, rpw and tpw, by the
in-sample log-loss improvement of a logistic regression on [logit p_elo, A - B of the decayed feature] over logit p_elo
alone (both fitted and scored on the evaluation-level pool matches of 2013-2018 where the feature exists):
    step A  h1 in {26, 52, 104, inf} weeks x K1 in {2, 5, 10, 20, 40} x tau in {0, 1}, step 3 at h3 = 52 weeks, K3 = 5
    step B  with step A's choice: h3 in {1, 2, 4, 8, 13, 26, 52, 104, 208, inf} x K3 in {0.5, 1, 2, 5, 10, 20, 40, 80, 160}
    every setting of the grid (3,600 per tour and statistic) is also scored for the three statistics (the sensitivity
    picture). The Brief's grid (K1 from 5, h3 from 26 weeks, K3 2 to 40: 800 settings) was extended twice after runs chose
    its shortest h3 for every tour and statistic; its own two-step choice is reported beside (in_brief_grid in the CSV)
The chosen constants follow the skill a row measures: serve skill (adjperf on a serve-side statistic, adjdef on a
return-side one) takes spw's, return skill (adjperf on return-side, adjdef on serve-side) rpw's, the whole match tpw's.
adjdef on a statistic whose mirror is in the list (spw/rpw, first_won/rpw_first, second_won/rpw_second, hold/brk,
bp_saved/bp_conv, tpw/tpw) is then algebraically adjperf on the mirror for the same player; both are built through their
own code paths and the overlap is measured (stageB_adj_summary.json, "mirror").

Probe: on a slice of 2023-2026, the features rebuilt with what was played in every match a cut cannot see redrawn
(4 cuts in 2026); a leaky control (the career form counting the match's own z) must move.

Writes, in data/studies/ufc_ideas/:
    stageB_adj.parquet            per box-score player-match: the per-match z of every statistic, adjperf and adjdef
                                  (float32), at the frozen constants
    stageB_adj_features.parquet   per pool match: adjperf_<s>|<form> and adjdef_<s>|<form>, A - B (float32)
    stageB_adj_tuning.csv         every tuning setting scored: tour, statistic, step, h1, K1, tau, h3, K3, improvement
    stageB_adj_summary.json       the constants chosen, the priors, the grids' flatness, the mirror overlap, the probe,
                                  timings

Run: ./python.sh src/eda/ufc_ideas/stageB_adjperf.py   (about 23 minutes: one process with two BLAS threads,
     measured beside the other stages' runs; the tuning 14 minutes, the features 4, the probe 5)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")       # Stage B's share of the machine: at most 5 processes or threads at once

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as H  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402

ADJ_PARQUET = B.OUT / "stageB_adj.parquet"
ADJ_FEATURES = B.OUT / "stageB_adj_features.parquet"
ADJ_TUNING = B.OUT / "stageB_adj_tuning.csv"
ADJ_SUMMARY = B.OUT / "stageB_adj_summary.json"

H1 = (26.0, 52.0, 104.0, np.inf)
# The Brief's grid is K1 in {5, 10, 20, 40}, h3 in {26, 52, 104, 208, inf}, K3 in {2, 5, 10, 20, 40}. A first run chose
# h3 = 26 weeks (the grid's shortest) for every tour and statistic, with a steep gain toward it, and K1 = 5 and K3 = 2 (the
# grid's smallest) for most; a second, extended to K1 = 2, h3 = 4, 8, 13 weeks and K3 = 0.5, 1, chose h3 = 4 weeks for
# every tour and statistic (still rising steeply) and K3 = 40 for return points; so the grid now reaches h3 = 1 week and
# K3 = 160 (disclosed). Rows of the Brief's own grid are flagged in_brief_grid in stageB_adj_tuning.csv, and its own
# choice is reported beside.
K1S = (2.0, 5.0, 10.0, 20.0, 40.0)
H3 = (1.0, 2.0, 4.0, 8.0, 13.0, 26.0, 52.0, 104.0, 208.0, np.inf)
K3S = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0)
BRIEF_GRID = {"K1": (5.0, 10.0, 20.0, 40.0), "h3": (26.0, 52.0, 104.0, 208.0, np.inf), "K3": (2.0, 5.0, 10.0, 20.0, 40.0)}
TAUS = (0, 1)
DEFAULT3 = {"h3": 52.0, "K3": 5.0}
MAD_FLOOR = 0.05                    # on the log-odds (log) scale
CLIP = 4.0
MIN_WINDOW = 3                      # a player-season enters the population MAD with 3+ matches
CORE = ("spw", "rpw", "tpw")
CHANNELS = ("adjperf", "adjdef")
FORMS = ("52 weeks", "decayed", "career")
PROBE_FROM = "2023-01-01"
PROBE_CUTS = 4
PROBE_ATOL = 1e-9


def skill_of(stat: str, channel: str) -> str:
    """Which core statistic's constants a row takes: the skill it measures."""
    side = B.side_of(stat)
    if side == "match":
        return "tpw"
    if channel == "adjperf":
        return "spw" if side == "serve" else "rpw"
    return "rpw" if side == "serve" else "spw"


def hl_name(h: float) -> str:
    return "inf" if not np.isfinite(h) else f"{h:g}"


# ------------------------------------------------------------------------------------------------
# The context: rows, the statistics' values, the box rows, the pair index

class Ctx:
    def __init__(self, rows: pd.DataFrame, means: dict, typ: dict | None = None, madpop: dict | None = None,
                 stats=B.STATS):
        self.rows = rows
        self.stats = tuple(stats)
        self.sa = B.stat_arrays(rows, means, self.stats)
        box = np.zeros(len(rows), dtype=bool)
        for s in self.stats:
            box |= self.sa[s]["ok"]
        self.box_idx = np.flatnonzero(box)
        self.pos = np.full(len(rows), -1, dtype=np.int64)
        self.pos[self.box_idx] = np.arange(len(self.box_idx))
        self.opp_box = self.pos[self.box_idx ^ 1]          # the opponent's box position (the same match)
        assert (self.opp_box >= 0).all()
        self.P = B.PairIndex(rows, self.box_idx)
        self.tour_box = rows["tour"].to_numpy()[self.box_idx]
        self.typ = typ if typ is not None else B.typical_units(rows, self.sa)
        self.A, self.Bi = B.pool_rows(rows)
        self.U = np.union1d(self.box_idx, np.concatenate([self.A, self.Bi]))
        self.u_pos_box = np.searchsorted(self.U, self.box_idx)
        self.ia, self.ib = np.searchsorted(self.U, self.A), np.searchsorted(self.U, self.Bi)
        self.frame = B.asof_frame(rows, self.U)
        self.madpop = madpop if madpop is not None else self.population_mad()

    # step-1 history of a channel on a statistic, per box row (box order): the value, whether it exists, its units
    def spec(self, s: str, channel: str):
        r = (self.box_idx ^ 1) if channel == "adjperf" else self.box_idx
        a = self.sa[s]
        return a["c"][r], a["ok"][r], a["d"][r]

    def population_mad(self) -> dict:
        """Per (statistic, channel, tour, tau): the mean absolute deviation of a step-1 history value around its
        player-season's own weighted mean, pooled over the player-seasons of 2010-2018 with 3+ matches."""
        out = {}
        rows = self.rows
        pc = rows["pcode"].to_numpy()[self.box_idx].astype("int64")
        yr = rows["year"].to_numpy()[self.box_idx]
        for s in self.stats:
            for ch in CHANNELS:
                a, ok, d = self.spec(s, ch)
                sel = ok & np.isin(yr, list(B.SHRINK_YEARS))
                for t in C.TOURS:
                    m = sel & (self.tour_box == t)
                    key = pd.factorize(pd.Series(pc[m] * 100 + (yr[m] - 2000)))[0]
                    for tau in TAUS:
                        w = d[m] ** tau if tau else np.ones(int(m.sum()))
                        sw = np.bincount(key, weights=w)
                        mean = np.bincount(key, weights=w * a[m]) / sw
                        dev = np.bincount(key, weights=w * np.abs(a[m] - mean[key]))
                        cnt = np.bincount(key)
                        big = cnt >= MIN_WINDOW
                        out[(s, ch, t, tau)] = float(dev[big].sum() / sw[big].sum())
        return out

    def per_row(self, s: str, values: dict) -> np.ndarray:
        """A per-tour constant spread over the box rows."""
        return np.where(self.tour_box == "atp", values["atp"], values["wta"])

    def k_ref(self, s: str, K: float, tau: int) -> np.ndarray:
        """K reference matches in weight units, per box row: K x u_typ^tau."""
        return np.where(self.tour_box == "atp", K * self.typ[(s, "atp")] ** tau, K * self.typ[(s, "wta")] ** tau)

    def moments(self, wanted: list[tuple[str, str, float, int]]) -> dict:
        """Step-1 sums for (statistic, channel, h1, tau), back in box order: {(statistic, channel, h1, tau): (S0, S1, M)}."""
        sp = {}
        for s, ch, _, _ in wanted:
            if (s, ch) not in sp:
                a, ok, d = self.spec(s, ch)
                sp[(s, ch)] = (self.P.to_sorted(a), self.P.to_sorted(ok), self.P.to_sorted(d))
        mom = B.pair_moments(self.P, sp, [((s, ch), h, t) for s, ch, h, t in wanted])
        return {(k[0][0], k[0][1], k[1], k[2]): tuple(self.P.from_sorted(x) for x in v) for k, v in mom.items()}

    def z(self, s: str, ch: str, mom: tuple, K1: float, tau: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Step 1's shrinkage and step 2: the per-match z of every box row (box order; NaN where it does not exist),
        whether it exists, and the opponent's MAD before the floor (for the diagnostics)."""
        S0, S1, M = mom
        kr = self.k_ref(s, K1, tau)
        mp = np.where(self.tour_box == "atp", self.madpop[(s, ch, "atp", tau)], self.madpop[(s, ch, "wta", tau)])
        E = S1 / (S0 + kr)
        MAD = (M + kr * mp) / (S0 + kr)
        j = self.opp_box
        a = self.sa[s]
        mine, theirs = self.box_idx, self.box_idx ^ 1
        den = np.maximum(MAD[j], MAD_FLOOR)
        if ch == "adjperf":
            z = (a["c"][mine] - E[j]) / den
            ok = a["ok"][mine]
        else:
            z = (E[j] - a["c"][theirs]) / den
            ok = a["ok"][theirs]
        return np.where(ok, np.clip(z, -CLIP, CLIP), np.nan), ok, MAD[j]

    def step3_units(self, s: str, ch: str) -> tuple[np.ndarray, np.ndarray]:
        """The weight base of each box row's z in step 3: the player's units (adjperf) or the opponent's (adjdef)."""
        a = self.sa[s]
        r = self.box_idx if ch == "adjperf" else self.box_idx ^ 1
        return a["d"][r], a["ok"][r]

    def step3(self, zs: list[np.ndarray], units: np.ndarray, ok: np.ndarray, tau: int, half_lives) -> dict:
        """Step-3 sums at every row of U for several z arrays sharing their weights: columns [w z_1 .. w z_k, w, n]."""
        k = len(zs)
        V = np.zeros((len(self.U), k + 2))
        w = np.where(ok, units ** tau if tau else 1.0, 0.0)
        for j, z in enumerate(zs):
            V[self.u_pos_box, j] = np.where(ok, w * np.nan_to_num(z), 0.0)
        V[self.u_pos_box, k] = w
        V[self.u_pos_box, k + 1] = ok.astype("float64")
        return B.windowed_sums(self.frame, V, [h for h in half_lives if np.isfinite(h)])

    def pool_values(self, sums: dict, form_key, j: int, kref_rows: np.ndarray, exists_key=None) -> tuple:
        """The step-3 average at the pool's A and B rows for column j: (A - B, exists for both)."""
        s = sums[form_key]
        k = s.shape[1] - 2
        ex = sums[exists_key or form_key][:, k + 1]
        ia, ib = self.ia, self.ib
        val_a = s[ia, j] / (s[ia, k] + kref_rows[0])
        val_b = s[ib, j] / (s[ib, k] + kref_rows[1])
        e = (ex[ia] > 0.5) & (ex[ib] > 0.5)
        return np.where(e, val_a - val_b, np.nan), e

    def pool_kref(self, s: str, K3: float, tau: int) -> tuple[np.ndarray, np.ndarray]:
        tour = self.rows["tour"].to_numpy()
        kk = {t: K3 * self.typ[(s, t)] ** tau for t in C.TOURS}
        return (np.where(tour[self.A] == "atp", kk["atp"], kk["wta"]), np.where(tour[self.Bi] == "atp", kk["atp"], kk["wta"]))


def form_key(form: str, h3: float):
    if form == "decayed":
        return "career" if not np.isfinite(h3) else h3
    return form


# ------------------------------------------------------------------------------------------------
# Tuning

def tune(ctx: Ctx) -> tuple[pd.DataFrame, dict]:
    """Steps A and B (and the full grid) for adjperf on spw, rpw and tpw, per tour."""
    rows = ctx.rows
    year = rows["year"].to_numpy()[ctx.A]
    ev = rows["evaluation"].to_numpy()[ctx.A]
    tour = rows["tour"].to_numpy()[ctx.A]
    pel = rows["p_elo_a"].to_numpy()[ctx.A]
    y = rows["won"].to_numpy()[ctx.A].astype(bool)
    tune_m = ev & np.isin(year, list(B.TUNE_YEARS)) & np.isfinite(pel)
    base = logit(np.clip(np.nan_to_num(pel, nan=0.5), 1e-9, 1 - 1e-9))
    recs, chosen = [], {}
    for s in CORE:
        t0 = time.time()
        mom = ctx.moments([(s, "adjperf", h, t) for h in H1 for t in TAUS])
        units, ok = ctx.step3_units(s, "adjperf")
        # every (h1, K1, tau) z, and for each tau the step-3 sums of all its z's at every h3
        zsets = {}
        for h1 in H1:
            for tau in TAUS:
                for K1 in K1S:
                    zsets[(h1, K1, tau)] = ctx.z(s, "adjperf", mom[(s, "adjperf", h1, tau)], K1, tau)[0]
        del mom
        sums = {}
        keys_by_tau = {tau: [k for k in zsets if k[2] == tau] for tau in TAUS}
        for tau in TAUS:
            sums[tau] = ctx.step3([zsets[k] for k in keys_by_tau[tau]], units, ok, tau, H3)
        B.log(f"  tuning {s}: moments, z and step-3 sums in {time.time() - t0:.0f}s")
        for t in C.TOURS:
            for tau in TAUS:
                keys = keys_by_tau[tau]
                for h3 in H3:
                    fk = form_key("decayed", h3)
                    for K3 in K3S:
                        kref = ctx.pool_kref(s, K3, tau)
                        X, ex = [], None
                        for j, k in enumerate(keys):
                            v, e = ctx.pool_values(sums[tau], fk, j, kref, exists_key="career")
                            X.append(v)
                            ex = e
                        m = tune_m & (tour == t) & ex
                        imp = B.lr_improvement(base[m], np.column_stack([x[m] for x in X]), y[m])
                        for (h1, K1, _), v in zip(keys, imp):
                            recs.append({"tour": t, "stat": s, "channel": "adjperf", "h1": h1, "K1": K1, "tau": tau,
                                         "h3": h3, "K3": K3, "form": "decayed", "improvement": float(v),
                                         "matches": int(m.sum())})
        del sums, zsets
        B.log(f"  tuning {s}: {len(H1) * len(K1S) * len(TAUS) * len(H3) * len(K3S)} settings scored per tour")
    grid = pd.DataFrame(recs)
    grid["in_brief_grid"] = (grid["K1"].isin(BRIEF_GRID["K1"]) & grid["h3"].isin(BRIEF_GRID["h3"])
                             & grid["K3"].isin(BRIEF_GRID["K3"]))

    def two_step(g):
        a = g[(g["h3"] == DEFAULT3["h3"]) & (g["K3"] == DEFAULT3["K3"])]
        ba = a.loc[a["improvement"].idxmax()]
        b = g[(g["h1"] == ba["h1"]) & (g["K1"] == ba["K1"]) & (g["tau"] == ba["tau"])]
        bb = b.loc[b["improvement"].idxmax()]
        best = g.loc[g["improvement"].idxmax()]
        return {"h1": float(ba["h1"]), "K1": float(ba["K1"]), "tau": int(ba["tau"]), "h3": float(bb["h3"]),
                "K3": float(bb["K3"]), "improvement": float(bb["improvement"]),
                "step_A_improvement": float(ba["improvement"]), "matches": int(bb["matches"]),
                "grid_best": {k: (float(best[k]) if k != "tau" else int(best[k])) for k in ("h1", "K1", "tau", "h3", "K3", "improvement")},
                "rank_in_grid": int((g["improvement"] > bb["improvement"] + 1e-12).sum()) + 1, "settings": int(len(g))}
    brief = {}
    for t in C.TOURS:
        for s in CORE:
            g = grid[(grid["tour"] == t) & (grid["stat"] == s)]
            chosen[(t, s)] = two_step(g)
            brief[(t, s)] = two_step(g[g["in_brief_grid"]])
    grid["step_A"] = (grid["h3"] == DEFAULT3["h3"]) & (grid["K3"] == DEFAULT3["K3"])
    grid["step_B"] = False
    grid["chosen"] = False
    grid["chosen_in_brief_grid"] = False
    for (t, s), c in chosen.items():
        m = (grid["tour"] == t) & (grid["stat"] == s)
        mb = m & (grid["h1"] == c["h1"]) & (grid["K1"] == c["K1"]) & (grid["tau"] == c["tau"])
        grid.loc[mb, "step_B"] = True
        grid.loc[mb & (grid["h3"] == c["h3"]) & (grid["K3"] == c["K3"]), "chosen"] = True
        cb = brief[(t, s)]
        grid.loc[m & (grid["h1"] == cb["h1"]) & (grid["K1"] == cb["K1"]) & (grid["tau"] == cb["tau"])
                 & (grid["h3"] == cb["h3"]) & (grid["K3"] == cb["K3"]), "chosen_in_brief_grid"] = True
    return grid, chosen, brief


def flatness(grid: pd.DataFrame, label: str = "extended") -> list[dict]:
    """How flat each grid is: the best, the worst, the settings within 0.1 and 0.5 milli-log-loss of the best, and each
    constant's marginal (the best improvement at each value, the others free)."""
    out = []
    for (t, s), g in grid.groupby(["tour", "stat"]):
        best = g["improvement"].max()
        rec = {"grid": label, "tour": t, "stat": s, "settings": int(len(g)), "best": float(best),
               "worst": float(g["improvement"].min()),
               "within_0_1": int((g["improvement"] >= best - 0.1).sum()),
               "within_0_5": int((g["improvement"] >= best - 0.5).sum()), "marginal": {}}
        for k in ("h1", "K1", "tau", "h3", "K3"):
            rec["marginal"][k] = {hl_name(v) if k in ("h1", "h3") else f"{v:g}": float(x)
                                  for v, x in g.groupby(k)["improvement"].max().items()}
        out.append(rec)
    return out


# ------------------------------------------------------------------------------------------------
# The features at the frozen constants

def constants_for(chosen: dict, stat: str, channel: str, tour: str) -> dict:
    return chosen[(tour, skill_of(stat, channel))]


def load_frozen(path: Path = ADJ_SUMMARY) -> tuple[dict, dict, dict]:
    """The frozen constants, typical units and population MADs from stageB_adj_summary.json (for stageB_split.py and
    the probes): (chosen {(tour, core stat): constants}, typ {(stat, tour): units}, madpop {(stat, channel, tour, tau):
    MAD})."""
    import json
    summ = json.loads(Path(path).read_text(encoding="utf-8"))
    chosen = {(c["tour"], c["stat"]): {k: (float(c[k]) if k != "tau" else int(c[k])) for k in ("h1", "K1", "tau", "h3", "K3")}
              for c in summ["chosen"]}
    typ = {(r["stat"], r["tour"]): float(r["units"]) for r in summ["typical_units"]}
    madpop = {(r["stat"], r["channel"], r["tour"], int(r["tau"])): float(r["mad"]) for r in summ["population_mad"]}
    return chosen, typ, madpop


def build(ctx: Ctx, chosen: dict, stats=None, leaky_control: bool = False) -> dict:
    """Every adjperf and adjdef z (box rows) and feature (pool matches) at the frozen constants. Constants are per tour:
    each tour's z is computed with its own and the two tours' rows never mix (players do not cross tours)."""
    stats = tuple(stats or ctx.stats)
    specs = [(s, ch) for s in stats for ch in CHANNELS]
    wanted = sorted({(s, ch, constants_for(chosen, s, ch, t)["h1"], constants_for(chosen, s, ch, t)["tau"])
                     for s, ch in specs for t in C.TOURS}, key=str)
    mom = ctx.moments(wanted)
    Z, info = {}, {}
    for s, ch in specs:
        z = np.full(len(ctx.box_idx), np.nan)
        info[f"{ch}_{s}"] = {}
        for t in C.TOURS:
            c = constants_for(chosen, s, ch, t)
            zt, ok, mad = ctx.z(s, ch, mom[(s, ch, c["h1"], c["tau"])], c["K1"], c["tau"])
            m = ctx.tour_box == t
            z[m] = zt[m]
            raw = np.abs(zt[m & ok])
            info[f"{ch}_{s}"][t] = {"z_rows": int((m & ok).sum()), "floor_binding": int((m & ok & (mad < MAD_FLOOR)).sum()),
                                   "at_clip": int((raw >= CLIP).sum()),
                                   "z_mean": float(zt[m & ok].mean()) if (m & ok).any() else None,
                                   "z_sd": float(zt[m & ok].std()) if (m & ok).any() else None}
        Z[(s, ch)] = z
    del mom
    feats = {}
    tour_pool = ctx.rows["tour"].to_numpy()[ctx.A]
    for s, ch in specs:
        units, ok = ctx.step3_units(s, ch)
        for t in C.TOURS:
            c = constants_for(chosen, s, ch, t)
            sums = ctx.step3([Z[(s, ch)]], units, ok & (ctx.tour_box == t), c["tau"], (c["h3"],))
            kref = ctx.pool_kref(s, c["K3"], c["tau"])
            mt = tour_pool == t
            for form in FORMS:
                fk = form_key(form, c["h3"]) if form == "decayed" else form
                v, _ = ctx.pool_values(sums, fk, 0, kref, exists_key=("career" if form != "52 weeks" else "52 weeks"))
                col = f"{ch}_{s}|{form}"
                feats.setdefault(col, np.full(len(ctx.A), np.nan))
                feats[col][mt] = v[mt]
            if leaky_control and s == "tpw" and ch == "adjperf":
                # a positive control for the probe: the career form counting the match's own z (a leak)
                own = np.zeros(len(ctx.U))
                own_w = np.zeros(len(ctx.U))
                zz = np.where(ok, np.nan_to_num(Z[(s, ch)]), 0.0)
                own[ctx.u_pos_box] = zz * (units ** c["tau"] if c["tau"] else 1.0)
                own_w[ctx.u_pos_box] = np.where(ok, units ** c["tau"] if c["tau"] else 1.0, 0.0)
                car = sums["career"]
                ia, ib = np.searchsorted(ctx.U, ctx.A), np.searchsorted(ctx.U, ctx.Bi)
                va = (car[ia, 0] + own[ia]) / (car[ia, 1] + own_w[ia] + kref[0])
                vb = (car[ib, 0] + own[ib]) / (car[ib, 1] + own_w[ib] + kref[1])
                feats.setdefault("leak_control|inclusive", np.full(len(ctx.A), np.nan))
                feats["leak_control|inclusive"][mt] = (va - vb)[mt]
    return {"z": Z, "features": feats, "info": info}


# ------------------------------------------------------------------------------------------------
# The mirror: adjdef on s against adjperf on s's mirror

def mirror_overlap(ctx: Ctx, built: dict) -> list[dict]:
    out = []
    for s in ctx.stats:
        m = B.MIRROR.get(s)
        if m is None:
            continue
        zd, zp = built["z"][(s, "adjdef")], built["z"][(m, "adjperf")]
        both = np.isfinite(zd) & np.isfinite(zp)
        rec = {"adjdef": s, "adjperf": m, "z_rows": int(both.sum()),
               "z_corr": float(np.corrcoef(zd[both], zp[both])[0, 1]),
               "z_max_abs_diff": float(np.abs(zd[both] - zp[both]).max()),
               "z_only_one_exists": int((np.isfinite(zd) ^ np.isfinite(zp)).sum()), "forms": {}}
        for form in FORMS:
            a, b = built["features"][f"adjdef_{s}|{form}"], built["features"][f"adjperf_{m}|{form}"]
            e = np.isfinite(a) & np.isfinite(b)
            rec["forms"][form] = {"matches": int(e.sum()), "corr": float(np.corrcoef(a[e], b[e])[0, 1]),
                                  "max_abs_diff": float(np.abs(a[e] - b[e]).max())}
        out.append(rec)
    return out


# ------------------------------------------------------------------------------------------------
# The probe cut by date, event and round

def probe(rows: pd.DataFrame, means: dict, typ: dict, madpop: dict, chosen: dict, n_cuts: int = PROBE_CUTS) -> dict:
    """On the slice from PROBE_FROM (both tours, history inside the slice only), at each of n_cuts matches of the last
    season: the box-score counts and results of every match the cut may not see (its own round and later rounds of its
    event, the week's other events, later weeks) are redrawn and the features rebuilt with the frozen constants and
    priors. The features of the protected matches (earlier weeks, and the cut event's rounds up to the cut's) must not
    move; a leaky control (the career form counting the match's own z) must."""
    sl = rows["tournament_date"].ge(pd.Timestamp(PROBE_FROM)).to_numpy()
    base_rows = B.F.prepare(rows[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))
    rng = np.random.default_rng(B.SEED)
    ctx0 = Ctx(base_rows, means, typ=typ, madpop=madpop)
    b0 = build(ctx0, chosen, leaky_control=True)["features"]
    names = sorted(b0)
    real = np.array([k != "leak_control|inclusive" for k in names])
    A = ctx0.A
    week, ev, rnd = (base_rows[c].to_numpy()[A] for c in ("day", "ev", "round_order"))
    yr = base_rows["year"].to_numpy()[A]
    cand = np.flatnonzero(yr == yr.max())
    res = {"slice_from": PROBE_FROM, "cuts": 0, "protected_checked": 0, "protected_changed": 0, "later_changed": 0,
           "control_protected_changed": 0, "largest_protected_difference": 0.0, "columns": int(real.sum())}
    counts = [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
    for c in rng.choice(cand, size=min(n_cuts, len(cand)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((ev != ev[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (ev == ev[c]) & (rnd <= rnd[c]))
        # the rows of every match the cut may not see (pool or not)
        wk_all, ev_all, rn_all = (base_rows[c_].to_numpy() for c_ in ("day", "ev", "round_order"))
        lat_all = (wk_all > week[c]) | ((wk_all == week[c]) & ((ev_all != ev[c]) | (rn_all >= rnd[c])))
        pert = base_rows.copy()
        for col in counts:
            v = pert[col].to_numpy(dtype="float64").copy()
            if col.endswith("_n"):
                dcol = pert[col[:-2] + "_d"].to_numpy(dtype="float64")
                draw = np.floor(rng.random(len(v)) * (np.nan_to_num(dcol) + 1))
                v = np.where(lat_all & np.isfinite(v), np.minimum(draw, np.nan_to_num(dcol)), v)
            pert[col] = v
        won = pert["won"].to_numpy().copy()
        flip = np.repeat(rng.random(len(won) // 2) < 0.5, 2) & lat_all
        pert["won"] = np.where(flip, ~won, won)
        pert = B.F.prepare(pert)
        ctx1 = Ctx(pert, means, typ=typ, madpop=madpop)
        b1 = build(ctx1, chosen, leaky_control=True)["features"]
        G = np.column_stack([b1[k] for k in names])
        B0 = np.column_stack([b0[k] for k in names])
        diff = ~np.isclose(G, B0, equal_nan=True, rtol=0, atol=PROBE_ATOL)
        gap = np.where(np.isfinite(G) & np.isfinite(B0) & keep[:, None], np.abs(G - B0), 0.0)
        res["cuts"] += 1
        res["protected_checked"] += int(keep.sum())
        res["protected_changed"] += int((diff[:, real].any(axis=1) & keep).sum())
        res["later_changed"] += int((diff[:, real].any(axis=1) & later & ~keep).sum())
        res["control_protected_changed"] += int((diff[:, ~real].any(axis=1) & keep).sum())
        res["largest_protected_difference"] = max(res["largest_protected_difference"], float(gap[:, real].max()))
        B.log(f"  probe cut {res['cuts']}: protected changed {res['protected_changed']}, later changed "
              f"{res['later_changed']}, control caught at {res['control_protected_changed']}")
    return res


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t_start = time.time()
    timings = {}
    rows, _ = B.load_rows()
    means = B.surface_means()
    ctx = Ctx(rows, means)
    pool = H.load_pool()
    assert (pool["match_id"].to_numpy() == rows["match_id"].to_numpy()[ctx.A]).all()
    timings["setup"] = round(time.time() - t_start, 1)
    B.log(f"box rows {len(ctx.box_idx):,}; step-1 pairs {ctx.P.n_pairs:,}; pool matches {len(ctx.A):,}")

    t0 = time.time()
    grid, chosen, brief = tune(ctx)
    grid.to_csv(ADJ_TUNING, index=False)
    timings["tuning"] = round(time.time() - t0, 1)
    for (t, s), c in chosen.items():
        cb = brief[(t, s)]
        B.log(f"  chosen {t} {s}: h1 {hl_name(c['h1'])}, K1 {c['K1']:g}, tau {c['tau']}, h3 {hl_name(c['h3'])}, "
              f"K3 {c['K3']:g}: {c['improvement']:.3f} milli (rank {c['rank_in_grid']} of {c['settings']}); the Brief's "
              f"grid: h3 {hl_name(cb['h3'])}, K3 {cb['K3']:g}: {cb['improvement']:.3f}")

    t0 = time.time()
    built = build(ctx, chosen)
    timings["features"] = round(time.time() - t0, 1)
    mirror = mirror_overlap(ctx, built)
    for m in mirror:
        B.log(f"  mirror adjdef_{m['adjdef']} vs adjperf_{m['adjperf']}: z corr {m['z_corr']:.6f}, "
              f"max diff {m['z_max_abs_diff']:.2e}")

    # outputs
    keys = ctx.rows.iloc[ctx.box_idx]
    adj = pd.DataFrame({"row": ctx.box_idx.astype("int64"), "match_id": keys["match_id"].to_numpy(),
                        "player_id": keys["player_id"].to_numpy(), "side": keys["side"].to_numpy(),
                        "tour": keys["tour"].to_numpy(), "year": keys["year"].to_numpy()})
    for (s, ch), z in built["z"].items():
        adj[f"z_{ch}_{s}"] = z.astype("float32")
    adj.to_parquet(ADJ_PARQUET, index=False, compression="zstd")
    feat = pd.DataFrame({"match_id": pool["match_id"].to_numpy()})
    for k, v in built["features"].items():
        feat[k] = np.asarray(v, dtype="float32")
    feat.to_parquet(ADJ_FEATURES, index=False, compression="zstd")
    B.log(f"wrote {ADJ_PARQUET.name} ({len(adj):,} rows) and {ADJ_FEATURES.name} ({feat.shape[1] - 1} columns)")

    t0 = time.time()
    pr = probe(rows, means, ctx.typ, ctx.madpop, chosen)
    timings["probe"] = round(time.time() - t0, 1)
    timings["total"] = round(time.time() - t_start, 1)

    used = {f"{ch}_{s}": {t: {"from": skill_of(s, ch), **{k: constants_for(chosen, s, ch, t)[k]
                                                         for k in ("h1", "K1", "tau", "h3", "K3")}} for t in C.TOURS}
            for s in ctx.stats for ch in CHANNELS}
    exists = {col: {t: int(np.isfinite(v[(pool["tour"].to_numpy() == t) & pool["evaluation"].to_numpy()]).sum())
                    for t in C.TOURS} for col, v in built["features"].items()}
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "settings": {"h1": [hl_name(h) for h in H1], "K1": list(K1S), "h3": [hl_name(h) for h in H3], "K3": list(K3S),
                     "tau": list(TAUS), "default_step3": {"h3": DEFAULT3["h3"], "K3": DEFAULT3["K3"]},
                     "mad_floor": MAD_FLOOR, "clip": CLIP, "min_window_matches": MIN_WINDOW,
                     "tune_years": [B.TUNE_YEARS[0], B.TUNE_YEARS[-1]], "prior_years": [B.SHRINK_YEARS[0], B.SHRINK_YEARS[-1]],
                     "forms": list(FORMS)},
        "counts": {"box_rows": int(len(ctx.box_idx)), "step1_pairs": int(ctx.P.n_pairs), "pool_matches": int(len(ctx.A))},
        "chosen": [{"tour": t, "stat": s, **c} for (t, s), c in chosen.items()],
        "brief_grid_choice": [{"tour": t, "stat": s, **c} for (t, s), c in brief.items()],
        "brief_grid": {"K1": list(BRIEF_GRID["K1"]), "h3": [hl_name(h) for h in BRIEF_GRID["h3"]], "K3": list(BRIEF_GRID["K3"])},
        "used": used,
        "typical_units": [{"stat": s, "tour": t, "units": v} for (s, t), v in ctx.typ.items()],
        "population_mad": [{"stat": s, "channel": ch, "tour": t, "tau": tau, "mad": v} for (s, ch, t, tau), v in ctx.madpop.items()],
        "flatness": flatness(grid) + flatness(grid[grid["in_brief_grid"]], "brief"),
        "z_info": built["info"],
        "mirror": mirror,
        "exists_evaluation_matches": exists,
        "probe": pr,
        "seconds": timings,
    }
    B.jdump(summary, ADJ_SUMMARY)
    B.log(f"wrote {ADJ_TUNING.name}, {ADJ_SUMMARY.name}; total {timings['total']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
