"""Backtest of the Pinnacle-first current best model for men, season by season: log loss and the return at Pinnacle's
and BetOnline's closes.

The owner's request of 9 Oct 2026, after deciding the Pinnacle-first odds input
(docs/decisions/2026-10-09-pinnacle-first-odds-input.md): "find wherever we are at with the plan for the best tabpfn3.5
offline model and repeat the backtest we've done before to see how we do in log loss and ROI for mens only, year to
year." The backtest repeated is the Thinking-58 study's return at the closes (src/eda/tabpfn_thinking58/score.py).

The models, both stages, the decided recipe as current_best_model/compare.py runs it (per-tour calibration slopes and
the speed stage's b fitted walk-forward on 2019 .. Y - 1, debut seasons out, b shrunk with tau 0.05):
    new     the Pinnacle-first instance (data/studies/current_best_model/pinnacle_first_2026-10-09/: the frozen
            reference's frame with the new odds input), fed its own construction at the close. Its forecast averages
            seeds 0-15; the slopes and b are fitted on seeds 0-3 (the decision's rule)
    new4    the same forecast from seeds 0-3, for the paired comparison with old
    new_stage1  the new model without the serve-speed offset: its calibration slopes alone, fitted walk-forward the same
            way (the owner's question of 9 Oct 2026: "does this include the serve speed offset? this roi?"; it does,
            and this shows what the offset adds)
    old     the frozen reference of 8 Oct 2026 (the books' average as its odds input), fed the average close; seeds
            0-3, all it has
Stage 2's speed column is the template's current one (with the ATP backfill: data/studies/infosys_atp_backfill/
speed_columns_augmented.parquet), the same for every model. The 40 matches of June 2026 whose ids changed at the 7 Oct
rebuild have no value in it and are left out.

The matches: men (atp), 2020-2026; 2026 only up to 28 Jul 2026, where the earlier backtest ended. Events from 29 Jul 2026
are the proposed sealed holdout (docs/studies/clean_holdout_rebuild/): their results are never read here.
    log loss    debut seasons out, as the decided comparisons. Each model's log loss; its input price recalibrated the
                decided way (one slope per tour on 2019 .. Y - 1) and the model's gain over it; new4 against old, paired.
                mLL, + = the model (second named) better; 95% intervals over four-week blocks
    the return  the earlier backtest's rules: completed matches with a coherent price at the book; back the side whose
                expected return p d - 1 is the larger and above the threshold (0 primary; 2%; 5%; the top half by edge,
                its threshold the forecast's median edge among its bets at the same book in earlier seasons); the
                owner's staking (tabpfn_thinking58.common.stake); ROI = profit / staked, 95% intervals from 2,000 draws
                of four-week blocks shared by every forecast in a cell (so new - old is paired). The books: Pinnacle's
                close as the new model's input takes it (tennis-data's to July 2025, OddsTrader's to 7 Sep 2025) and
                BetOnline's last line (OddsTrader; lines stamped over 30 minutes after the listed start left out). The
                control bets the new model's input price, recalibrated: what the price alone earns.

Writes data/studies/pinnacle_first/backtest.json and backtest_tables.md.
Run: ./python.sh src/eda/pinnacle_first/backtest.py
"""
from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.tabpfn_thinking58 import common as TC  # noqa: E402
from src.eda.tabpfn_thinking58.score import bets, settle  # noqa: E402

C = CMP.C
NEW = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09"
SPEED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
STAGE1_REF = R.REF / "frozen" / "tables" / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
OUT = ROOT / "data" / "studies" / "pinnacle_first"
SEALED_FROM = pd.Timestamp("2026-07-29")
FIT_FROM = 2019
SEASONS = tuple(range(2020, 2027))
SEEDS16, SEEDS4 = tuple(range(16)), (0, 1, 2, 3)
DRAWS, RNG_SEED = 2000, 20261009
BOOKS = {"pinnacle": ("pin_a", "pin_b"), "betonline": ("bol_a", "bol_b")}
FORECASTS = {"new": "Pinnacle-first model (16 seeds)", "new_stage1": "The same without the speed offset",
             "old": "Earlier model, books' average (4 seeds)", "control": "Control: the price input alone, recalibrated"}
RULES = (("edge > 0", 0.0), ("edge > 2%", 0.02), ("edge > 5%", 0.05), ("top 50% by edge", "earlier"))


# ------------------------------------------------------------------------------------------------
# Data and forecasts

def outcomes(P: C.Paths) -> pd.Series:
    """a_won of matches before SEALED_FROM only: later rows are filtered out before the column is read."""
    f = pd.read_parquet(P.model_frame, columns=["match_id", "tournament_date", "a_won"],
                        filters=[("tournament_date", "<", SEALED_FROM)])
    if len(f) and f["tournament_date"].max() >= SEALED_FROM:
        raise RuntimeError("a result from the sealed holdout was read")
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def speed() -> pd.Series:
    s = pd.read_parquet(SPEED, columns=["match_id", "spd_L_B"])
    return s.astype({"match_id": str}).set_index("match_id")["spd_L_B"]


def load() -> tuple[pd.DataFrame, dict]:
    """Every model's final forecast and every price on the matches of 2019 .. 28 Jul 2026 both frames hold."""
    _, P_new, _ = CMP.candidate(str(NEW))
    P_ref = R.paths("reference")
    new, ref = CMP.inputs_frame(P_new), CMP.inputs_frame(P_ref)
    y_new, y_ref = outcomes(P_new), outcomes(P_ref)
    z = speed()
    ids = new.index.intersection(ref.index)
    season = new.loc[ids, "season"].to_numpy()
    keep = (season >= FIT_FROM) & (season <= max(SEASONS)) & (new.loc[ids, "tournament_date"] < SEALED_FROM).to_numpy()
    ids = ids[keep]
    no_speed = ids[~np.isfinite(z.reindex(ids).to_numpy(float))]
    ids = ids.difference(no_speed, sort=False)
    y = y_new.reindex(ids)
    if y.isna().any() or not np.array_equal(y.to_numpy(), y_ref.reindex(ids).to_numpy()):
        raise RuntimeError("the two frames disagree on a result, or lack one")
    info = new.loc[ids, ["tour", "season", "tournament_date", "debut_season", "odds_input"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.to_numpy(float)
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    info["p_new_price"] = new.loc[ids, "p_mkt"].to_numpy(float)
    info["p_old_price"] = ref.loc[ids, "p_mkt"].to_numpy(float)
    seasons = tuple(range(FIT_FROM, max(SEASONS) + 1))
    p16, _ = F.seed_table("model", seasons, SEEDS16, F.FrameIndex(new.reset_index()[["match_id", "season"]]), P_new,
                          "td", require_checks=True)
    p_old = CMP.seed_table(P_ref, ref, seasons)
    p16, p_old = p16.reindex(info.index), p_old.reindex(info.index)
    if p16.isna().any().any() or p_old.isna().any().any():
        raise RuntimeError("forecasts are missing for some matches")
    eta = lambda p: pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=p.index)  # noqa: E731
    par_new = CMP.walk_forward(eta(p16[list(SEEDS4)]), info, z, SEASONS)       # fitted on 2019 .. Y - 1
    par_new1 = CMP.walk_forward(eta(p16[list(SEEDS4)]), info, None, SEASONS)   # the slopes alone: no speed offset
    par_old = CMP.walk_forward(eta(p_old), info, z, SEASONS)
    test = info.index[info["season"].isin(SEASONS).to_numpy()]
    q = {"q_new": CMP.forecasts(p16, info, par_new, z, test)[0],
         "q_new_stage1": CMP.forecasts(p16, info, par_new1, None, test)[0],
         "q_new4": CMP.forecasts(p16[list(SEEDS4)], info, par_new, z, test)[0],
         "q_old": CMP.forecasts(p_old, info, par_old, z, test)[0],
         "q_control": CMP.close_forecast(info, "p_new_price", SEASONS, test)[0],
         "q_old_control": CMP.close_forecast(info, "p_old_price", SEASONS, test)[0]}
    info = info.loc[test].copy()
    for k, v in q.items():
        info[k] = v
    books = pd.read_parquet(NEW / "book_prices.parquet").astype({"match_id": str}).set_index("match_id")
    for c in ("pin_a", "pin_b", "bol_a", "bol_b"):
        info[c] = books[c].reindex(info.index).to_numpy(float)
    s1 = pd.read_parquet(STAGE1_REF, columns=["match_id", "status"]).astype({"match_id": str}).set_index("match_id")
    info["status"] = s1["status"].reindex(info.index).to_numpy()
    facts = {"matches": int(len(info)), "left_out_without_speed_value": int(len(no_speed)),
             "coefficients": {"new": {str(k): v for k, v in par_new.items()},
                              "old": {str(k): v for k, v in par_old.items()}}}
    return info, facts


# ------------------------------------------------------------------------------------------------
# Log loss

def ll_rows(info: pd.DataFrame) -> list[dict]:
    """Men, debut seasons out: per season and pooled, each model's log loss, its gain over its own recalibrated price,
    and new4 against old (mLL, + = the second named better)."""
    g0 = info[(info["tour"] == "atp") & ~info["debut"]]
    rows = []
    for label, g in [(str(Y), g0[g0["season"] == Y]) for Y in SEASONS] + [("2020-2026", g0), ("2020-2024",
                                                                                         g0[g0["season"] <= 2024])]:
        y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
        L = {k: C.ll(g[f"q_{k}"].to_numpy(float), y) for k in ("new", "new4", "new_stage1", "old", "control",
                                                                  "old_control")}
        rows.append({"season": label, "matches": int(len(g)),
                     "ll_new": float(L["new"].mean()), "ll_price": float(L["control"].mean()),
                     "ll_old": float(L["old"].mean()), "ll_old_price": float(L["old_control"].mean()),
                     "new_over_its_price": mean_ci(L["control"] - L["new"], blk),
                     "old_over_its_price": mean_ci(L["old_control"] - L["old"], blk),
                     "new4_over_old": mean_ci(L["old"] - L["new4"], blk),
                     "new_over_old_price": mean_ci(L["old_control"] - L["new"], blk),
                     "speed_offset_adds": mean_ci(L["new_stage1"] - L["new"], blk)})
    return rows


def mean_ci(v, clusters, scale: float = 1000.0) -> dict:
    """Mean with a cluster-sandwich interval over four-week blocks (t on blocks - 1), times scale; P(better) the t CDF."""
    from scipy.stats import t as student_t
    v = np.asarray(v, float)
    labels, ix = np.unique(clusters, return_inverse=True)
    G, n, m = len(labels), len(v), float(v.mean())
    infl = np.bincount(ix, weights=v - m)
    se = float(np.sqrt(G / (G - 1) * infl @ infl) / n) if G > 1 else np.nan
    r = student_t.ppf(0.975, G - 1) * se if G > 1 else np.nan
    return {"est": scale * m, "lo": scale * (m - r), "hi": scale * (m + r), "p_better": float(student_t.cdf(m / se, G - 1))
            if se > 0 else np.nan, "blocks": int(G)}


# ------------------------------------------------------------------------------------------------
# The return

def median_edge(g: pd.DataFrame, fc: str, ca: str, cb: str) -> float:
    b = bets(g[f"q_{fc}"], g[ca], g[cb], 0.0)
    return float(np.median(b.loc[b["bet"], "ev"])) if b["bet"].any() else np.inf


def cell(g: pd.DataFrame, ca: str, cb: str, thresholds: dict, label: dict) -> list[dict]:
    """Every forecast's return on g at threshold thresholds[fc], with block-draw intervals shared by the forecasts."""
    labels, ix = np.unique(g["block"].to_numpy(), return_inverse=True)
    rng = np.random.default_rng([RNG_SEED, zlib.crc32(json.dumps(label, sort_keys=True).encode())])
    W = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=DRAWS).astype(float)
    rows, draws = [], {}
    for fc in FORECASTS:
        b = bets(g[f"q_{fc}"], g[ca], g[cb], thresholds[fc])
        profit, won = settle(b, g["y"].astype(bool))
        stake = b["stake"].to_numpy()
        nb = int(b["bet"].sum())
        d = (W @ np.bincount(ix, weights=profit, minlength=len(labels))) / \
            np.maximum(W @ np.bincount(ix, weights=stake, minlength=len(labels)), 1e-12)
        draws[fc] = d
        rows.append({**label, "forecast": fc, "threshold": thresholds[fc], "matches": int(len(g)), "bets": nb,
                     "staked": float(stake.sum()), "profit": float(profit.sum()),
                     "roi": float(profit.sum() / stake.sum()) if nb else np.nan,
                     "roi_lo": float(np.quantile(d, 0.025)) if nb else np.nan,
                     "roi_hi": float(np.quantile(d, 0.975)) if nb else np.nan,
                     "mean_edge_claimed": float(np.nanmean(b["ev"])) if nb else np.nan, "blocks": int(len(labels))})
    by = {r["forecast"]: r for r in rows}
    for r in rows:
        if r["forecast"] != "old" and r["bets"] and by["old"]["bets"]:
            d = draws[r["forecast"]] - draws["old"]
            r.update({"minus_old": r["roi"] - by["old"]["roi"],
                      "minus_old_lo": float(np.quantile(d, 0.025)), "minus_old_hi": float(np.quantile(d, 0.975))})
    if by["new"]["bets"] and by["new_stage1"]["bets"]:             # what the speed offset adds, paired
        d = draws["new"] - draws["new_stage1"]
        by["new"].update({"speed_adds": by["new"]["roi"] - by["new_stage1"]["roi"],
                          "speed_adds_lo": float(np.quantile(d, 0.025)), "speed_adds_hi": float(np.quantile(d, 0.975))})
    return rows


def roi_rows(info: pd.DataFrame) -> list[dict]:
    """Men, completed matches with a coherent price at the book: per season and pooled, every rule."""
    rows = []
    for book, (ca, cb) in BOOKS.items():
        ok = (info["tour"] == "atp") & (info["status"] == "completed") & info[ca].notna() & info[cb].notna()
        g0 = info[ok.to_numpy()]
        if len(g0) < 100:
            continue
        seasons = [Y for Y in SEASONS if (g0["season"] == Y).sum() >= 100]
        for rule, spec in RULES:
            for Y in seasons + ["all"]:
                g = g0 if Y == "all" else g0[g0["season"] == Y]
                if spec == "earlier":
                    if Y == "all":
                        th = {fc: median_edge(g0, fc, ca, cb) for fc in FORECASTS}
                    else:
                        earlier = g0[g0["season"] < Y]
                        if len(earlier) < 500:
                            continue
                        th = {fc: median_edge(earlier, fc, ca, cb) for fc in FORECASTS}
                else:
                    th = {fc: spec for fc in FORECASTS}
                rows += cell(g.reset_index(drop=True), ca, cb, th,
                             {"book": book, "rule": rule, "season": str(Y),
                              "first_day": str(g["tournament_date"].min().date()),
                              "last_day": str(g["tournament_date"].max().date())})
    return rows


SPEED_DECIDED_FROM = 2024     # the speed stage's own evidence (2024-26) and the earlier backtest's offset start


def offset_views(info: pd.DataFrame) -> dict:
    """What the serve-speed offset adds for men (the owner's question of 9 Oct 2026, "does this include the serve speed
    offset? this roi?"): log loss by window (debut seasons out; + = with the offset better), and the pooled return at
    edge above 0 with the offset from 2020 (this backtest), never, and from 2024 only (the earlier backtest's start)."""
    men = info[info["tour"] == "atp"].copy()
    men["q_from_2024"] = np.where(men["season"] >= SPEED_DECIDED_FROM, men["q_new"], men["q_new_stage1"])
    out = {"log_loss": {}, "roi": {}}
    for label, lo, hi in (("2020-2023", 2020, SPEED_DECIDED_FROM - 1), ("2024-2026", SPEED_DECIDED_FROM, 2026),
                          ("2020-2026", 2020, 2026)):
        g = men[~men["debut"] & men["season"].between(lo, hi)]
        y = g["y"].to_numpy(float)
        out["log_loss"][label] = mean_ci(C.ll(g["q_new_stage1"].to_numpy(float), y) - C.ll(g["q_new"].to_numpy(float), y),
                                         g["block"].to_numpy())
    for book, (ca, cb) in BOOKS.items():
        ok = (men["status"] == "completed") & men[ca].notna() & men[cb].notna()
        h = men[ok.to_numpy()].reset_index(drop=True)
        for label, sub in (("2020 on", h), ("2024 on", h[h["season"] >= SPEED_DECIDED_FROM])):
            row = {}
            for name, col in (("offset from 2020", "q_new"), ("no offset", "q_new_stage1"),
                              ("offset from 2024", "q_from_2024")):
                b = bets(sub[col], sub[ca], sub[cb], 0.0)
                profit, _ = settle(b, sub["y"].astype(bool))
                row[name] = {"roi": float(profit.sum() / b["stake"].sum()), "bets": int(b["bet"].sum()),
                             "profit": float(profit.sum())}
            out["roi"][f"{book}, {label}"] = row
    return out


CURVE = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10)
BANDS = (0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, np.inf)


def block_ci(profit: np.ndarray, stake: np.ndarray, blk: np.ndarray, seed: int) -> tuple[float, float]:
    labels, ix = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=DRAWS).astype(float)
    d = (W @ np.bincount(ix, weights=profit, minlength=len(labels))) / \
        np.maximum(W @ np.bincount(ix, weights=stake, minlength=len(labels)), 1e-12)
    return float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def edge_views(info: pd.DataFrame) -> dict:
    """The owner's questions of 9 Oct 2026 on the predicted edge (= the bet's expected ROI, p d - 1): men, completed,
    2020 on, the new model. The curve: every threshold's bets (a floor: each includes the higher edges). The bands:
    disjoint ranges of predicted ROI, each band's stake-weighted mean prediction against its realised ROI, and what the
    same bets would earn if the book's own margin-free price were right (no skill: about minus the margin)."""
    men = info[(info["tour"] == "atp") & (info["status"] == "completed")]
    out = {"curve": [], "bands": []}
    for book, (ca, cb) in BOOKS.items():
        g = men[men[ca].notna() & men[cb].notna()].reset_index(drop=True)
        years = (g["tournament_date"].max() - g["tournament_date"].min()).days / 365.25
        for th in CURVE:
            b = bets(g["q_new"], g[ca], g[cb], th)
            profit, _ = settle(b, g["y"].astype(bool))
            stake = b["stake"].to_numpy()
            lo, hi = block_ci(profit, stake, g["block"].to_numpy(), 7)
            nb = int(b["bet"].sum())
            out["curve"].append({"book": book, "threshold": th, "matches": int(len(g)), "bets": nb,
                                 "share_of_matches": nb / len(g), "bets_per_year": nb / years,
                                 "roi": float(profit.sum() / stake.sum()), "roi_lo": lo, "roi_hi": hi,
                                 "profit": float(profit.sum()), "staked": float(stake.sum()),
                                 "mean_predicted": float(np.nanmean(b["ev"]))})
        b = bets(g["q_new"], g[ca], g[cb], 0.0)
        profit, _ = settle(b, g["y"].astype(bool))
        qa = (1 / g[ca]) / (1 / g[ca] + 1 / g[cb])
        k = pd.DataFrame({"ev": b["ev"], "stake": b["stake"], "profit": profit, "block": g["block"],
                          "ev_book": np.where(b["on_a"], qa, 1 - qa) * b["odds"] - 1})[b["bet"].to_numpy()]
        k["band"] = pd.cut(k["ev"], BANDS, right=False)
        for band, h in k.groupby("band", observed=True):
            s, p = h["stake"].to_numpy(), h["profit"].to_numpy()
            lo, hi = block_ci(p, s, h["block"].to_numpy(), 11)
            out["bands"].append({"book": book, "from": float(band.left), "to": float(band.right), "bets": int(len(h)),
                                 "mean_predicted": float((s * h["ev"]).sum() / s.sum()),
                                 "roi": float(p.sum() / s.sum()), "roi_lo": lo, "roi_hi": hi,
                                 "roi_if_book_right": float((s * h["ev_book"]).sum() / s.sum())})
    return out


# ------------------------------------------------------------------------------------------------
# Tables

def ci(d: dict | None, scale: float = 1.0, digits: int = 2, pct: bool = False) -> str:
    if not d or d.get("est") is None or not np.isfinite(d["est"]):
        return "—"
    u = "%" if pct else ""
    return f"{scale * d['est']:+.{digits}f}{u} [{scale * d['lo']:+.{digits}f}, {scale * d['hi']:+.{digits}f}]"


def verdict(d: dict) -> str:
    if d["lo"] > 0:
        return "better"
    if d["hi"] < 0:
        return "worse"
    return f"unresolved (P {d['p_better']:.2f})"


def tables(res: dict) -> str:
    L = ["# Pinnacle-first model, men, season by season (generated by src/eda/pinnacle_first/backtest.py)", "",
         "Log loss: lower is better; gains in mLL, + = the model better; 95% intervals over four-week blocks. ROI = profit "
         "per unit staked, the owner's staking, completed matches; intervals from 2,000 four-week block draws.", "",
         "## Log loss (debut seasons out)", "",
         "| Season | Matches | Model | Its price, recalibrated | Model's gain over its price | Earlier model's gain over "
         "its price (the average) | Pinnacle-first (4 seeds) − earlier model | What the speed offset adds |",
         "|---|---:|---:|---:|---|---|---|---|"]
    for r in res["log_loss"]:
        L.append(f"| {r['season']} | {r['matches']:,} | {r['ll_new']:.4f} | {r['ll_price']:.4f} | "
                 f"{ci(r['new_over_its_price'])}, {verdict(r['new_over_its_price'])} | "
                 f"{ci(r['old_over_its_price'])}, {verdict(r['old_over_its_price'])} | "
                 f"{ci(r['new4_over_old'])}, {verdict(r['new4_over_old'])} | "
                 f"{ci(r['speed_offset_adds'])}, {verdict(r['speed_offset_adds'])} |")
    so = res.get("speed_offset")
    if so:
        L += ["", "## What the serve-speed offset adds (men)", "",
              "| Log loss, window | With the offset − without, mLL (+ = with better) |", "|---|---|"]
        L += [f"| {k} | {ci(v)}, {verdict(v)} |" for k, v in so["log_loss"].items()]
        L += ["", "| Return, edge above 0 | Offset from 2020 (this backtest) | No offset | Offset from 2024 only |",
              "|---|---|---|---|"]
        for k, row in so["roi"].items():
            L.append(f"| {k} | " + " | ".join(f"{100 * v['roi']:+.2f}% ({v['bets']:,} bets)" for v in row.values()) + " |")
    ev = res.get("edge")
    if ev:
        L += ["", "## The predicted edge (men, 2020 on): thresholds and bands", "",
              "The edge is the bet's predicted ROI, p d − 1. A threshold is a floor (its bets include every higher edge); "
              "a band holds only its own range.", "",
              "| Book | Predicted ROI over | Bets | Share of matches | Bets a year | Mean predicted | ROI | Profit (units) |",
              "|---|---|---:|---:|---:|---:|---|---:|"]
        for r in ev["curve"]:
            L.append(f"| {r['book']} | {100 * r['threshold']:g}% | {r['bets']:,} | {100 * r['share_of_matches']:.1f}% | "
                     f"{r['bets_per_year']:.0f} | {100 * r['mean_predicted']:.1f}% | {100 * r['roi']:+.2f}% "
                     f"[{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}] | {r['profit']:+.0f} |")
        L += ["", "| Book | Predicted ROI band | Bets | Mean predicted | Realised ROI | If the book's own price were right |",
              "|---|---|---:|---:|---|---:|"]
        for r in ev["bands"]:
            band = f"{100 * r['from']:g}% to {100 * r['to']:g}%" if np.isfinite(r["to"]) else f"{100 * r['from']:g}% and over"
            L.append(f"| {r['book']} | {band} | {r['bets']:,} | {100 * r['mean_predicted']:.2f}% | {100 * r['roi']:+.2f}% "
                     f"[{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}] | {100 * r['roi_if_book_right']:+.2f}% |")
    roi = pd.DataFrame(res["roi"])
    for book in BOOKS:
        L += ["", f"## Return at {book.capitalize()}'s close", ""]
        for rule, _ in RULES:
            sub = roi[(roi["book"] == book) & (roi["rule"] == rule)]
            if sub.empty:
                continue
            L += [f"**{rule}**", "", "| Season | Matches | " + " | ".join(FORECASTS.values()) +
                  " | Pinnacle-first − earlier, points | Speed offset adds, points |",
                  "|---|---:|" + "---|" * (len(FORECASTS) + 2)]
            for season, g in sub.groupby("season", sort=False):
                cells = []
                for fc in FORECASTS:
                    r = g[g["forecast"] == fc].iloc[0]
                    cells.append("—" if not r["bets"] else
                                 f"{100 * r['roi']:+.2f}% [{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}]; "
                                 f"{int(r['bets']):,} bets, {r['profit']:+.0f} u")
                n = g[g["forecast"] == "new"].iloc[0]
                diff = "—" if pd.isna(n.get("minus_old")) else \
                    f"{100 * n['minus_old']:+.2f} [{100 * n['minus_old_lo']:+.1f}, {100 * n['minus_old_hi']:+.1f}]"
                spd = "—" if pd.isna(n.get("speed_adds")) else \
                    f"{100 * n['speed_adds']:+.2f} [{100 * n['speed_adds_lo']:+.1f}, {100 * n['speed_adds_hi']:+.1f}]"
                L.append(f"| {season} | {int(g['matches'].iloc[0]):,} | " + " | ".join(cells) + f" | {diff} | {spd} |")
            L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    info, facts = load()
    res = {"facts": facts, "log_loss": ll_rows(info), "roi": roi_rows(info), "speed_offset": offset_views(info),
           "edge": edge_views(info),
           "odds_input_by_season_men": {f"{s}|{k}": int(v) for (s, k), v in
                                        info[info["tour"] == "atp"].groupby(["season", "odds_input"]).size().items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "backtest.json", res)
    (OUT / "backtest_tables.md").write_text(tables(res), encoding="utf-8")
    C.log(f"backtest.json, backtest_tables.md: {facts['matches']:,} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
