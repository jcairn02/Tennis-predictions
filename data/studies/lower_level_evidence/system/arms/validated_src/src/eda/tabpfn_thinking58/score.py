"""Score the one TabPFN-3.5-Thinking fit on the 58 inputs against the non-thinking model, calibrated, with and without
the serve-speed offset, and compute the return at the BetOnline and Pinnacle closes. Written and run on the free
forecasts before the paid call; a forecast that does not exist yet is skipped.

Base forecasts on the 23,819 test matches of 2022-2026 (P(A wins), symmetrised: the mean of P(A | x) and
1 - P(A | swapped)):

    thinking   the paid TabPFN-3.5-Thinking fit (one fit on 2013-2021, seed 0), RAW: not calibrated
    twin       its non-thinking twin (local_twin.py: the same rows and settings without thinking), seed 0, CALIBRATED
    twin4      the twin's seeds 0-3 mean, calibrated
    twin_raw   the twin's seed 0, not calibrated
    market     the closing odds recalibrated per tour on 2013-2021 (the leak-proof refit's p_market)

The decided calibration: per tour, one slope on the log-odds, no intercept, fitted on the walk-forward local model's
out-of-sample forecasts of 2019 .. Y - 1 (seeds 0-3 mean, debut seasons out; serve_speed_tabpfn.score.Scorer.slopes),
applied to season Y. The twin has no out-of-sample season before 2022 (it is trained on 2013-2021), so it takes these
slopes: the same model, inputs and settings. Checks: each forecast's own walk-forward slope inside the test seasons
(2022 .. Y - 1, debut seasons out), scored on 2023-2026: for the twin, and for Thinking (does it need one?).

The serve-speed offset (docs/decisions/2026-10-07-speed-nudge.md, amended 8 Oct 2026; adaptive/adjust.py): not an
input, a second stage on the forecast's log-odds, part of the current best model's final forecast. Always the 28-day
memory (spd_L_B: the speeds in hand with today's weekly feed) and the weekly feed's coefficients (coefficients.json
L_weekly), which exist for 2024-2026; 0 for every woman. Final forecasts (the base forecast where no coefficient exists,
i.e. 2022-2023):

    best             the current best model: the local 58-input model walk-forward (season Y trained on 2013 .. Y - 1),
                     the 16-seed mean; logit q = s_tour,Y eta + b_Y spd_L (adjust.apply)
    twin_final       the twin under the same two-stage rule: s_tour,Y eta_twin + b_Y spd_L
    thinking_final   Thinking with the speed offset and no slope (not calibrated): eta_thinking + b_Y spd_L

Comparisons: milli-log-loss, positive = the second-named forecast is better (Thinking is second wherever it appears);
paired 95% intervals over four-week blocks of tournament dates (calendar weeks alongside); a range spanning 0 is a tie.
    primary     twin -> thinking, 2022-2026, both tours; then per tour, per season
    final       twin_final -> thinking_final and best -> thinking_final, 2024-2026 (where the offset exists) and
                2022-2026 (the base forecasts in 2022-2023)
    secondary   twin4, best, twin_raw -> thinking; every forecast against the recalibrated close; what the offset adds
                to each; the own walk-forward calibration checks; seed noise (twin seed 0 against 1-3); at Polymarket's
                price 24 hours out (2025-2026, the rating race's population: every match with both Polymarket prices,
                debut seasons out) the same pairs and the price itself (raw, and recalibrated by a leave-one-block-out
                fit), every forecast fed that price

The return, at each book's close (books.py: Pinnacle 2022 - mid-January 2026, BetOnline 2024-2026), on every test match
with a coherent price at that book: a forecast backs the side whose expected return p d - 1 at that price is the larger
and exceeds the threshold (0 primary; 0.02 and 0.05 sensitivities; and the owner's "top 50% of bets": each forecast's
median edge among its bets, from the same matches' edges, or for a season from the earlier seasons' bets only),
staking common.stake(d) (the owner's rule). The
final forecasts are primary; the market average's close (mkt: de-vigged, as the model's input; market: recalibrated) is
bet the same way as a control: what the price input alone earns. Completed matches only (a retirement voids the bet); retirements settled on the player who
advanced, and flat 1-unit stakes, as checks. ROI = profit / staked; 95% intervals from 2,000 draws of four-week blocks
(the same draws for every forecast at a book, so each forecast's difference from Thinking's is paired).

Writes data/studies/tabpfn_thinking58/results.json, results.csv, roi.csv (aggregates only), predictions.parquet and
predictions_early.parquet (gitignored).
Run: ./python.sh src/eda/tabpfn_thinking58/score.py
"""
from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import score as SS  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import adjust as ADJ  # noqa: E402
from src.eda.surface_elo_pieces.early_price_score import crossfit_stack  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking58 import common as C  # noqa: E402
from src.eda.tabpfn_thinking58 import guard as G  # noqa: E402

BEST_SEEDS = tuple(range(16))
SPEED_FROM = min(ADJ.FIT_SEASONS)              # the offset's coefficients start in 2024
DRAWS = 2000
RNG_SEED = 20261008
BOOKS = {"pinnacle": ("ps_a", "ps_b", "ok_ps"), "betonline": ("bol_a", "bol_b", "ok_bol")}
# each forecast's return is compared with Thinking's in the same form (final with final, base with base); the two price
# controls (the market average's close, raw de-vigged and recalibrated) show what the price input alone earns
ROI_REFERENCE = {"thinking_final": None, "twin_final": "thinking_final", "best": "thinking_final",
                 "thinking": None, "twin": "thinking", "twin_raw": "thinking", "best_stage1": "thinking",
                 "mkt": None, "market": None}
# what the speed offset (the second stage) does to each forecast's return: final against its own base forecast
SPEED_BASE = {"thinking_final": "thinking", "twin_final": "twin", "best": "best_stage1"}
KEY = ("milli-log-loss; positive = the second-named forecast has the lower log loss (better); paired 95% intervals over "
       "four-week blocks; spanning 0 = tie")


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), T.EPS, 1 - T.EPS))


# ------------------------------------------------------------------------------------------------
# Forecasts

def load_frame() -> pd.DataFrame:
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "a_won", "p_mkt",
                                                 "tabpfn_split", "debut_season"])
    f = f[f["tabpfn_split"] == "test"].drop(columns="tabpfn_split").reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    f["debut"] = f["debut_season"].astype(bool)
    mk = pd.read_parquet(C.LEAKPROOF / "test_predictions.parquet", columns=["match_id", "p_market"])
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "all_early", "p_early_a", "p_close_a"])
    bo = pd.read_parquet(C.OUT / "book_odds.parquet").drop(columns=["tour", "season"])
    sp = pd.read_parquet(ADJ.columns_path(SC.DEFAULT), columns=["match_id", "spd_L_B"])
    for extra in (mk, ep, bo, sp):
        extra["match_id"] = extra["match_id"].astype(str)
        f = f.merge(extra, on="match_id", how="left", validate="one_to_one")
    for c in ("has_early", "all_early"):
        f[c] = f[c].fillna(False).astype(bool)
    if f["p_market"].isna().any() or f["status"].isna().any():
        raise RuntimeError("the recalibrated close or the status is missing for a test match")
    men_late = ((f["tour"] == "atp") & (f["season"] >= SPEED_FROM)).to_numpy()
    if not np.isfinite(f["spd_L_B"].to_numpy(float)[men_late]).all():
        raise RuntimeError("the speed column is missing for a man in 2024-2026")
    f["spd"] = np.where(f["tour"] == "atp", f["spd_L_B"].fillna(0.0), 0.0)
    return f


def decided_slopes() -> tuple[dict, SS.Bank]:
    """{season: {tour: slope}} of the decided calibration for 2022-2026, and the serve-speed study's forecast bank."""
    P = SC.DEFAULT
    bank = SS.Bank(P, SS.frame_index(P))
    sc = SS.Scorer(bank, SS.population(P), SS.labels(P))
    return {Y: sc.slopes("model", Y) for Y in C.TEST_YEARS}, bank


def calibrate(p, g: pd.DataFrame, slopes: dict) -> np.ndarray:
    s = np.array([slopes[int(y)][t] for t, y in zip(g["tour"], g["season"])])
    return expit(s * lg(p))


def with_speed(p_raw, p_base, g: pd.DataFrame, slope: bool) -> np.ndarray:
    """The final forecast: in 2024-2026 the speed offset on the raw forecast's log-odds, with the decided slope s_tour,Y
    (slope=True: adjust.apply) or none (slope=False: eta + b_Y spd); elsewhere the base forecast p_base."""
    out = np.asarray(p_base, dtype=float).copy()
    late = (g["season"] >= SPEED_FROM).to_numpy()
    if not late.any():
        return out
    eta, tour, season, z = lg(p_raw)[late], g["tour"].to_numpy()[late], g["season"].to_numpy()[late], \
        g["spd"].to_numpy(float)[late]
    coef = ADJ.load_coefficients(SC.DEFAULT)
    if slope:
        out[late] = ADJ.apply(eta, tour, season, mode="L", col_l=z, coef=coef, feed="weekly")
    else:
        b = np.array([ADJ.l_set(coef, "weekly")[str(int(y))]["b_shrunk"] for y in season])
        out[late] = expit(eta + b * np.where(tour == "wta", 0.0, z))
    return out


def walk_forward_own(f: pd.DataFrame, col: str) -> np.ndarray:
    """The forecast recalibrated by its own slope per tour, fitted on its seasons 2022 .. Y - 1 (debut seasons out);
    NaN in 2022."""
    out = np.full(len(f), np.nan)
    z, y = lg(f[col]), f["a_won"].to_numpy(float)
    for t in C.TOURS:
        for Y in C.TEST_YEARS[1:]:
            fit = ((f["tour"] == t) & (f["season"] < Y) & ~f["debut"]).to_numpy()
            tgt = ((f["tour"] == t) & (f["season"] == Y)).to_numpy()
            beta, _ = T.fit_logistic(z[fit][:, None], y[fit])
            out[tgt] = expit(beta[0] * z[tgt])
    return out


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The test frame with every forecast (td block), the early-price frame, and the facts about them."""
    f = load_frame()
    _, _, X_query, ids, manifest = C.load_upload()
    slopes, bank = decided_slopes()
    facts = {"decided_slopes": {str(Y): v for Y, v in slopes.items()},
             "speed_coefficients": {Y: v for Y, v in ADJ.l_set(ADJ.load_coefficients(SC.DEFAULT), "weekly").items()}}
    early = f[f["has_early"]].reset_index(drop=True)

    def put(name: str, by_block: dict):
        f[f"p_{name}"] = by_block["td"].reindex(f["match_id"]).to_numpy(float)
        early[f"p_{name}"] = by_block["early"].reindex(early["match_id"]).to_numpy(float)

    path = C.THINKING / "predictions.npz"
    facts["thinking_present"] = path.exists()
    if path.exists():
        _, p_a, meta, binding = G.load_predictions(path, None, len(X_query))
        if binding["input_sha256"] != manifest["input_fingerprint"]:
            raise RuntimeError("the saved Thinking predictions belong to another upload")
        put("thinking", C.symmetrised(p_a, ids))
        facts["thinking_metadata"] = meta
    seeds = [k for k in C.TWIN_SEEDS if (C.LOCAL / f"seed{k}.npz").exists()]
    if 0 not in seeds:
        raise RuntimeError("the twin's seed 0 is needed")
    facts["twin_seeds"] = seeds
    for k in seeds:
        put(f"twin_s{k}_raw", C.symmetrised(C.load_twin_seed(k, manifest["input_fingerprint"], len(X_query)), ids))
    eta, eta_e = bank.eta("model", BEST_SEEDS, C.TEST_YEARS, "td"), bank.eta("model", BEST_SEEDS, C.PRICE_SEASONS, "early")
    f["p_best_stage1_raw"] = expit(eta.reindex(f["match_id"]).to_numpy(float))
    early["p_best_stage1_raw"] = expit(eta_e.reindex(early["match_id"]).to_numpy(float))

    for g in (f, early):
        g["p_twin_raw"] = g["p_twin_s0_raw"]
        if len(seeds) == len(C.TWIN_SEEDS):
            g["p_twin4_raw"] = g[[f"p_twin_s{k}_raw" for k in seeds]].mean(axis=1)
        for c in [c for c in g.columns if c.startswith("p_twin") and c.endswith("_raw") and c != "p_twin_raw"]:
            g[c[:-4]] = calibrate(g[c], g, slopes)                  # p_twin_s<k>, p_twin4
        g["p_twin"] = g["p_twin_s0"]
        g["p_best_stage1"] = calibrate(g["p_best_stage1_raw"], g, slopes)
        g["p_best"] = with_speed(g["p_best_stage1_raw"], g["p_best_stage1"], g, slope=True)
        g["p_twin_final"] = with_speed(g["p_twin_raw"], g["p_twin"], g, slope=True)
        if "p_thinking" in g:
            g["p_thinking_final"] = with_speed(g["p_thinking"], g["p_thinking"], g, slope=False)
    if f["p_best_stage1_raw"].isna().any() or early["p_best_stage1_raw"].isna().any():
        raise RuntimeError("the current best model's forecast is missing for some matches")

    f["p_twin_wf"] = walk_forward_own(f, "p_twin_raw")
    if "p_thinking" in f:
        f["p_thinking_wf"] = walk_forward_own(f, "p_thinking")
    # the early population: the rating race's (every match with both Polymarket prices, debut seasons out)
    e = early[early["all_early"] & ~early["debut"] & np.isfinite(early["p_early_a"]) &
              np.isfinite(early["p_close_a"])].reset_index(drop=True)
    e["p_price_early"] = e["p_early_a"]
    e["p_price_early_recal"] = crossfit_stack(lg(e["p_early_a"])[:, None], e["a_won"].to_numpy(bool),
                                              T.blocks(e["tournament_date"].to_numpy(), 28))
    facts["early_population"] = int(len(e))
    return f, e, facts


# ------------------------------------------------------------------------------------------------
# Comparisons

def compare(g: pd.DataFrame, base: str, model: str) -> dict | None:
    pb, pm = f"p_{base}", f"p_{model}"
    if pb not in g or pm not in g:
        return None
    ok = np.isfinite(g[pb].to_numpy(float)) & np.isfinite(g[pm].to_numpy(float))
    h = g[ok]
    if len(h) < 50:
        return None
    y = h["a_won"].to_numpy(bool)
    lb, lm = T.ll(h[pb].to_numpy(), y), T.ll(h[pm].to_numpy(), y)
    c = T.compare(lb, lm, h["tournament_date"].to_numpy())
    verdict = "tie" if c["lo"] <= 0 <= c["hi"] else (model if c["lo"] > 0 else base)
    return {"base": base, "model": model, "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
            "week_lo": c["week_lo"], "week_hi": c["week_hi"], "blocks": c["blocks"], "verdict": verdict,
            "ll_base": float(lb.mean()), "ll_model": float(lm.mean())}


def tours(g: pd.DataFrame):
    yield "both", g
    for t in C.TOURS:
        yield t, g[g["tour"] == t]


BASE_PAIRS = [("twin", "thinking"), ("twin4", "thinking"), ("best_stage1", "thinking"), ("twin_raw", "thinking"),
              ("market", "thinking"), ("market", "twin"), ("market", "twin4"), ("market", "best_stage1"),
              ("market", "twin_raw"), ("twin_raw", "twin"), ("twin", "twin4"), ("twin", "best_stage1")]
FINAL_PAIRS = [("twin_final", "thinking_final"), ("best", "thinking_final"), ("market", "thinking_final"),
               ("market", "twin_final"), ("market", "best"), ("thinking", "thinking_final"), ("twin", "twin_final"),
               ("best_stage1", "best"), ("twin_final", "best")]
OWN_CAL_PAIRS = [("thinking", "thinking_wf"), ("twin_raw", "twin_wf"), ("twin_wf", "thinking"),
                 ("twin_wf", "thinking_wf"), ("twin", "twin_wf")]
EARLY_PAIRS = [("twin", "thinking"), ("twin4", "thinking"), ("best_stage1", "thinking"), ("twin_raw", "thinking"),
               ("twin_final", "thinking_final"), ("best", "thinking_final"),
               ("price_early", "thinking"), ("price_early_recal", "thinking"), ("price_early_recal", "thinking_final"),
               ("price_early", "twin"), ("price_early_recal", "twin"), ("price_early_recal", "twin_final"),
               ("price_early", "best"), ("price_early_recal", "best")]


def comparisons(f: pd.DataFrame, e: pd.DataFrame) -> list[dict]:
    rows = []

    def add(g, pairs, label):
        for tour, h in tours(g):
            for b, m in pairs:
                r = compare(h, b, m)
                if r:
                    rows.append({**label, "tour": tour, **r})

    add(f, BASE_PAIRS, {"setting": "close, base forecasts", "window": "2022-2026"})
    add(f[f["season"] >= SPEED_FROM], FINAL_PAIRS, {"setting": "close, with the speed offset", "window": "2024-2026"})
    add(f, FINAL_PAIRS, {"setting": "close, with the speed offset from 2024", "window": "2022-2026"})
    for Y in C.TEST_YEARS:
        add(f[f["season"] == Y], [("twin", "thinking"), ("twin_final", "thinking_final"), ("best", "thinking_final"),
                                  ("market", "thinking"), ("market", "twin")],
            {"setting": "close, by season", "window": str(Y)})
    add(f[f["season"] >= 2023], OWN_CAL_PAIRS, {"setting": "close, own walk-forward calibration", "window": "2023-2026"})
    seeds = [c for c in f.columns if c.startswith("p_twin_s") and not c.endswith("_raw") and c != "p_twin_s0"]
    add(f, [("twin_s0", c[2:]) for c in seeds], {"setting": "close, twin seed noise", "window": "2022-2026"})
    add(e, EARLY_PAIRS, {"setting": "Polymarket price 24 h out", "window": "2025-2026"})
    return rows


def slope_diagnostics(f: pd.DataFrame) -> dict:
    """In-sample slopes on 2022-2026 per tour (diagnosis only; 1 = calibrated, below 1 over-confident), and how far
    each forecast departs from the raw close (SD of its log-odds minus the close's)."""
    out = {}
    for col in ("thinking", "thinking_final", "twin_raw", "twin4_raw", "twin", "twin_final", "best_stage1_raw", "best"):
        if f"p_{col}" not in f:
            continue
        out[col] = {}
        for t in C.TOURS:
            g = f[f["tour"] == t]
            beta, se = T.fit_logistic(lg(g[f"p_{col}"])[:, None], g["a_won"].to_numpy(float))
            sd = float(np.std(lg(g[f"p_{col}"]) - lg(g["p_mkt"])))
            out[col][t] = {"slope": float(beta[0]), "se": float(se[0]), "sd_vs_close": sd}
    return out


def agreement(f: pd.DataFrame, a: str, b: str) -> dict:
    la, lb = lg(f[f"p_{a}"]), lg(f[f"p_{b}"])
    d = np.abs(f[f"p_{a}"].to_numpy() - f[f"p_{b}"].to_numpy())
    return {"pair": [a, b], "log_odds_correlation": float(np.corrcoef(la, lb)[0, 1]), "mean_abs_prob_diff": float(d.mean()),
            "p90_abs_prob_diff": float(np.quantile(d, 0.9)),
            "favourite_changes": int(((f[f"p_{a}"] > 0.5) != (f[f"p_{b}"] > 0.5)).sum())}


# ------------------------------------------------------------------------------------------------
# The return

def bets(p, d_a, d_b, threshold: float, flat: bool = False) -> pd.DataFrame:
    """Per match: whether a bet is made, on A or B, at what odds and stake, and the expected return it was made for."""
    p, d_a, d_b = (np.asarray(v, dtype=float) for v in (p, d_a, d_b))
    ev_a, ev_b = p * d_a - 1.0, (1.0 - p) * d_b - 1.0
    on_a = (ev_a > threshold) & (ev_a >= ev_b)
    on_b = (ev_b > threshold) & ~on_a
    bet = on_a | on_b
    odds = np.where(on_a, d_a, np.where(on_b, d_b, np.nan))
    stake = np.zeros(len(p))
    stake[bet] = 1.0 if flat else C.stake(odds[bet])
    return pd.DataFrame({"bet": bet, "on_a": on_a, "odds": odds, "stake": stake,
                         "ev": np.where(on_a, ev_a, np.where(on_b, ev_b, np.nan))})


def settle(b: pd.DataFrame, a_won) -> tuple[np.ndarray, np.ndarray]:
    """(profit, won) per match: a winning bet returns stake (odds - 1), a losing one loses the stake, no bet is 0."""
    a_won = np.asarray(a_won, dtype=bool)
    won = np.where(b["on_a"], a_won, ~a_won) & b["bet"].to_numpy()
    profit = np.where(b["bet"], np.where(won, b["stake"] * (b["odds"] - 1.0), -b["stake"]), 0.0)
    return profit, won


FIXED_RULES = [("owner", "edge > 0", 0.0), ("owner", "edge > 2%", 0.02), ("owner", "edge > 5%", 0.05),
               ("owner", "top 50% by edge", "median"), ("flat", "edge > 0", 0.0)]
PRIMARY_RULES = [("owner", "edge > 0", 0.0), ("owner", "top 50% by edge", "median")]


LUCK_DRAWS = 1000
LUCK_FORECASTS = ("thinking_final", "best", "twin_final", "market")


def luck_range(b: pd.DataFrame, qa: np.ndarray, rng) -> dict:
    """If the book's own margin-free price were the truth: the bets' expected ROI, and the 95% range of the ROI that
    luck alone gives them (each bet's outcome drawn from that price, 1,000 times; matches independent). A return
    outside the range is more than luck against that book's price."""
    k = b["bet"].to_numpy()
    if not k.any():
        return {}
    q = np.where(b["on_a"], qa, 1.0 - qa)[k]
    d, s = b["odds"].to_numpy()[k], b["stake"].to_numpy()[k]
    sims = (rng.random((LUCK_DRAWS, len(q))) < q) @ (s * d) / s.sum() - 1.0
    return {"roi_if_book_right": float((s * (q * d - 1.0)).sum() / s.sum()),
            "luck_lo": float(np.quantile(sims, 0.025)), "luck_hi": float(np.quantile(sims, 0.975))}


def median_edge(g: pd.DataFrame, fc: str, ca: str, cb: str) -> float:
    """The median expected return of the bets a forecast makes at threshold 0 on g: the threshold that keeps the top
    half of them by edge. It reads the edges only, never a result."""
    b = bets(g[f"p_{fc}"], g[ca], g[cb], 0.0)
    return float(np.median(b.loc[b["bet"], "ev"])) if b["bet"].any() else np.inf


def summarise(g: pd.DataFrame, forecasts: list[str], ca: str, cb: str, rules, label: dict) -> list[dict]:
    """Every forecast's return on the matches g under each (staking, rule, threshold): ROI with a 95% interval from block
    draws shared by every forecast and rule on g, and each forecast's paired difference from its reference. A threshold
    is a number, "median" (each forecast's median edge on g: its top half of bets), or {forecast: number}. The draws
    are seeded by the label, so a subset's interval does not depend on which other subsets are scored."""
    labels, ix = np.unique(T.blocks(g["tournament_date"].to_numpy(), 28), return_inverse=True)
    key = zlib.crc32(json.dumps(label, sort_keys=True).encode())
    rng = np.random.default_rng([RNG_SEED, key])
    W = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=DRAWS).astype(float)
    luck_rng = np.random.default_rng([RNG_SEED, key, 1])          # separate, so the block draws above never move
    margin = 1.0 / g[ca].to_numpy() + 1.0 / g[cb].to_numpy() - 1.0
    qa = (1.0 / g[ca].to_numpy()) / (1.0 / g[ca].to_numpy() + 1.0 / g[cb].to_numpy())   # the book's own chance for A
    rows = []
    for staking, rule, spec in rules:
        draws, block, sides, profits = {}, [], {}, {}
        for fc in forecasts:
            th = median_edge(g, fc, ca, cb) if spec == "median" else (spec[fc] if isinstance(spec, dict) else spec)
            b = bets(g[f"p_{fc}"], g[ca], g[cb], th, flat=staking == "flat")
            profit, won = settle(b, g["a_won"])
            stake = b["stake"].to_numpy()
            nb = int(b["bet"].sum())
            roi_draws = (W @ np.bincount(ix, weights=profit, minlength=len(labels))) / \
                np.maximum(W @ np.bincount(ix, weights=stake, minlength=len(labels)), 1e-12)
            draws[fc] = roi_draws
            sides[fc], profits[fc] = np.where(b["bet"], np.where(b["on_a"], 1, -1), 0), profit
            block.append({**label, "staking": staking, "rule": rule, "threshold": th, "forecast": fc,
                          "matches": int(len(g)),
                          "first_day": str(g["tournament_date"].min().date()),
                          "last_day": str(g["tournament_date"].max().date()), "bets": nb,
                          "bets_on_favourite": int((b["bet"] & (b["odds"] < 2.0)).sum()),
                          "staked": float(stake.sum()), "profit": float(profit.sum()),
                          "roi": float(profit.sum() / stake.sum()) if nb else np.nan,
                          "roi_lo": float(np.quantile(roi_draws, 0.025)) if nb else np.nan,
                          "roi_hi": float(np.quantile(roi_draws, 0.975)) if nb else np.nan,
                          "win_rate": float(won.sum() / nb) if nb else np.nan,
                          "mean_odds": float(np.nanmean(b["odds"])) if nb else np.nan,
                          "max_stake": float(stake.max()) if nb else np.nan,
                          "mean_ev_claimed": float(np.nanmean(b["ev"])) if nb else np.nan,
                          "book_margin_mean": float(margin.mean()), "blocks": int(len(labels)),
                          **(luck_range(b, qa, luck_rng) if fc in LUCK_FORECASTS and staking == "owner"
                             and label.get("population") == "completed" else {})})
        for r in block:
            ref = ROI_REFERENCE[r["forecast"]]
            if ref in draws:
                d = draws[r["forecast"]] - draws[ref]
                r.update({"versus": ref, "roi_minus_versus": r["roi"] - next(x["roi"] for x in block
                                                                               if x["forecast"] == ref),
                          "diff_lo": float(np.quantile(d, 0.025)), "diff_hi": float(np.quantile(d, 0.975))})
            base = SPEED_BASE.get(r["forecast"])
            if base in draws:                                 # the speed offset's effect, paired, and the bets it moved
                d = draws[r["forecast"]] - draws[base]
                moved = sides[r["forecast"]] != sides[base]
                r.update({"speed_base": base, "speed_effect": r["roi"] - next(x["roi"] for x in block
                                                                              if x["forecast"] == base),
                          "speed_lo": float(np.quantile(d, 0.025)), "speed_hi": float(np.quantile(d, 0.975)),
                          "bets_moved_by_speed": int(moved.sum()),
                          "profit_change_on_moved": float((profits[r["forecast"]] - profits[base])[moved].sum())})
        rows += block
    return rows


def season_rules(g: pd.DataFrame, Y: int, forecasts: list[str], ca: str, cb: str) -> list:
    """The primary rules for season Y of g, plus the top-half rule with its threshold from g's earlier seasons only."""
    rules = list(PRIMARY_RULES)
    earlier = g[g["season"] < Y]
    if len(earlier) >= 500:
        rules.append(("owner", "top 50% by edge, threshold from earlier seasons",
                      {fc: median_edge(earlier, fc, ca, cb) for fc in forecasts}))
    return rules


def roi_rows(f: pd.DataFrame) -> list[dict]:
    """The return at each book: the whole population under every rule, then breakdowns: men and women separately under
    every rule (the owner's request of 8 Oct 2026), before and after the speed offset's first season, by season (with
    the top-half rule's threshold also taken from the earlier seasons' bets only: BetOnline's 2026 and the top 50% of
    bets, the owner's request of the same day), and for BetOnline by how long before the listed start its last line was
    stamped. Per tour, a season's earlier-seasons threshold comes from the same tour's bets."""
    rows = []
    forecasts = [c for c in ROI_REFERENCE if f"p_{c}" in f]
    for book, (ca, cb, ok) in BOOKS.items():
        for population in ("completed", "with_retirements"):
            m = f[ok].to_numpy(bool).copy()
            if population == "completed":
                m &= (f["status"] == "completed").to_numpy()
            g = f[m].reset_index(drop=True)
            rules = FIXED_RULES if population == "completed" else [r for r in FIXED_RULES if r[0] == "owner"]
            rows += summarise(g, forecasts, ca, cb, rules, {"book": book, "population": population,
                                                                 "subset": "all"})
            subsets = [(f"tour={t}", g["tour"] == t, rules) for t in C.TOURS]
            if population == "completed":
                subsets += [(f"before {SPEED_FROM} (no speed offset)", g["season"] < SPEED_FROM, PRIMARY_RULES),
                            (f"{SPEED_FROM} on (speed offset active)", g["season"] >= SPEED_FROM, PRIMARY_RULES)]
                subsets += [(f"{SPEED_FROM} on, tour={t}", (g["season"] >= SPEED_FROM) & (g["tour"] == t),
                             PRIMARY_RULES) for t in C.TOURS]
                seasons = sorted(g["season"].unique())
                for Y in seasons:
                    subsets.append((f"season={Y}", g["season"] == Y, season_rules(g, Y, forecasts, ca, cb)))
                for Y in seasons:
                    for t in C.TOURS:
                        gt = g[g["tour"] == t]
                        subsets.append((f"season={Y}, tour={t}", (g["season"] == Y) & (g["tour"] == t),
                                        season_rules(gt, Y, forecasts, ca, cb)))
            if book == "betonline":
                subsets += [("last line within 60 min of the listed start", g["bol_close_min"] >= -60, PRIMARY_RULES),
                            ("last line over 60 min before the listed start", g["bol_close_min"] < -60, PRIMARY_RULES)]
            for name, k, rules_k in subsets:
                h = g[k.to_numpy(bool)].reset_index(drop=True)
                if len(h) >= 100:
                    rows += summarise(h, forecasts, ca, cb, rules_k, {"book": book, "population": population,
                                                                           "subset": name})
    return rows


def main() -> int:
    f, e, facts = build()
    R = pd.DataFrame(comparisons(f, e))
    roi = pd.DataFrame(roi_rows(f))
    facts.update({"slopes_in_sample_2022_2026": slope_diagnostics(f),
                  "agreement": [agreement(f, a, b) for a, b in (("thinking", "twin_raw"), ("thinking", "twin"),
                                                               ("thinking", "best_stage1"), ("twin", "best_stage1"),
                                                               ("thinking_final", "best"))
                                if f"p_{a}" in f and f"p_{b}" in f],
                  "matches": {"test": int(len(f)), "completed": int((f["status"] == "completed").sum()),
                              "early_population": facts["early_population"]}})
    C.write_json(C.OUT / "results.json", {"key": KEY, "facts": facts, "comparisons": R.to_dict("records"),
                                          "roi": roi.to_dict("records")})
    R.to_csv(C.OUT / "results.csv", index=False)
    roi.to_csv(C.OUT / "roi.csv", index=False)
    keep = ["match_id", "tour", "season", "tournament_date", "a_won", "status", "debut", "spd"] + \
        [c for c in f.columns if c.startswith("p_")]
    f[keep].to_parquet(C.OUT / "predictions.parquet", index=False)
    e[["match_id", "tour", "season", "tournament_date", "a_won", "spd"] + [c for c in e.columns if c.startswith("p_")]] \
        .to_parquet(C.OUT / "predictions_early.parquet", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        show = R[R["window"].isin(["2022-2026", "2024-2026", "2023-2026", "2025-2026"])]
        print(show[["setting", "window", "tour", "base", "model", "matches", "gain", "lo", "hi", "verdict"]]
              .round(2).to_string(index=False))
        top = roi[roi["subset"] == "all"]
        cols = ["book", "population", "staking", "rule", "forecast", "bets", "staked", "profit", "roi", "roi_lo",
                "roi_hi"] + [c for c in ("roi_minus_versus", "diff_lo", "diff_hi") if c in top]
        print(top[cols].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
