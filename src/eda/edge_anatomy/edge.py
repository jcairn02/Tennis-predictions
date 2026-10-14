"""Part A and C3 of the edge-anatomy study: the current instance's edge over its own price, and where it sits.

Reads data/studies/edge_anatomy/analysis.parquet and seeds.parquet (data.py). Log loss: lower is better; every gain is
1000 x mean(LL(base) - LL(model)) in mLL per match, + = the second named (the model) better; 95% intervals over
four-week blocks (t on blocks - 1) plus, where the model's 16 seeds enter, their variance. Debut seasons out.

    A   the model (both stages) against its recalibrated price, by window (2025 - 28 Jul 2026; 2020-2024; each season)
        and tour; stage 1 alone; what stage 2 adds (men); what the recalibration of the price alone is worth; the
        realisation of the model's disagreement (1 = right-sized) and its spread.
    C3  the 2025-26 gain by segment (tour, level, surface, the favourite's price band, which way the model leans, the
        size of its disagreement, the odds input's source, best of five, round, indoor, half-year), each segment's share
        of the window's total gain; the same on 2020-2024 for comparison.
    R   the return in 2025-26 at Pinnacle's close (to 7 Sep 2025) and BetOnline's last line, the owner's staking, edge
        above 0, completed matches, both tours: overall, by tour, by the side backed (favourite or underdog at the book)
        and by the model's lean.

Writes data/studies/edge_anatomy/edge_A.csv, edge_segments.csv, edge_roi.csv and edge_summary.json.
Run: ./python.sh src/eda/edge_anatomy/edge.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402
from src.eda.tabpfn_thinking58.score import bets, settle  # noqa: E402

STAGE1_REF = R.REF / "frozen" / "tables" / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
WINDOWS = {"2025-26": (2025, 2026), "2020-24": (2020, 2021, 2022, 2023, 2024)}


def load() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_parquet(E.OUT / "analysis.parquet").set_index("match_id")
    seeds = pd.read_parquet(E.OUT / "seeds.parquet").set_index("match_id").reindex(df.index)
    facts = json.loads((E.OUT / "data_facts.json").read_text(encoding="utf-8"))
    par = {int(k): v for k, v in facts["coefficients_both_stages"].items()}
    df = df[df["season"] >= 2020].copy()
    seeds = seeds.loc[df.index]
    s = np.array([par[int(Y)][0] if t == "atp" else par[int(Y)][1] for Y, t in zip(df["season"], df["tour"])])
    b = np.array([par[int(Y)][2] for Y in df["season"]])
    z = np.where(df["tour"].to_numpy() == "wta", 0.0, df["spd"].to_numpy(float))
    qk = expit(s[:, None] * S.lg(seeds.to_numpy(float)) + (b * z)[:, None])      # per-seed final forecasts
    check = expit(s * S.lg(seeds.to_numpy(float).mean(axis=1)) + b * z)
    if np.abs(check - df["q_full"].to_numpy()).max() > 1e-9:
        raise RuntimeError("the per-seed recipe does not reproduce the stored final forecast")
    st = pd.read_parquet(STAGE1_REF, columns=["match_id", "status"]).astype({"match_id": str}).set_index("match_id")
    df["status"] = st["status"].reindex(df.index).to_numpy()
    df["d"] = S.lg(df["q_full"]) - S.lg(df["q_close"])                      # the model's disagreement, log-odds
    df["fav_p"] = np.maximum(df["q_close"], 1 - df["q_close"])
    df["lean"] = np.where(np.sign(df["d"]) == np.sign(S.lg(df["q_close"])), "toward the favourite",
                          "toward the underdog")
    df["half"] = df["tournament_date"].dt.year.astype(str) + np.where(df["tournament_date"].dt.month <= 6, " H1", " H2")
    return df, qk


def mask(df: pd.DataFrame, window, tour: str) -> np.ndarray:
    m = df["season"].isin(window).to_numpy() & ~df["debut"].to_numpy()
    if tour != "both":
        m &= (df["tour"] == tour).to_numpy()
    return m


def part_a(df: pd.DataFrame, qk: np.ndarray) -> list[dict]:
    rows = []
    windows = dict(WINDOWS)
    windows.update({str(Y): (Y,) for Y in range(2020, 2027)})
    for wname, window in windows.items():
        for tour in ("both", "atp", "wta"):
            m = mask(df, window, tour)
            if m.sum() < 200:
                continue
            g = df[m]
            y, blk = g["y"].to_numpy(), g["block"].to_numpy()
            st = S.seed_term(None, qk[m], y)
            comps = {
                "model (both stages) vs its recalibrated price": S.gain(g["q_close"], g["q_full"], y, blk, st),
                "model, stage 1 alone vs its recalibrated price": S.gain(g["q_close"], g["q_full_s1"], y, blk),
                "stage 2 (speed) adds, both stages vs stage 1": S.gain(g["q_full_s1"], g["q_full"], y, blk),
                "recalibrated price vs the raw margin-free price": S.gain(g["p_mkt"], g["q_close"], y, blk),
                "model (both stages) vs the raw margin-free price": S.gain(g["p_mkt"], g["q_full"], y, blk, st),
                "model (both stages) vs the books' average close, recalibrated":
                    S.gain(g["q_avg_close"], g["q_full"], y, blk, st),
            }
            rea = S.realisation(g["q_close"].to_numpy(), g["q_full"].to_numpy(), y, blk)
            for k, v in comps.items():
                rows.append({"window": wname, "tour": tour, "comparison": k, **v, "verdict": S.verdict(v)})
            rows.append({"window": wname, "tour": tour, "comparison": "realisation of the disagreement (1 = right-sized)",
                         "est": rea["r"], "se": rea["se"], "lo": rea["r"] - 1.96 * rea["se"],
                         "hi": rea["r"] + 1.96 * rea["se"], "n": int(m.sum()), "spread": rea["spread"],
                         "verdict": ""})
            rows.append({"window": wname, "tour": tour, "comparison": "log loss of the model / of the recalibrated price",
                         "est": float(S.ll(g["q_full"], y).mean()), "se": float(S.ll(g["q_close"], y).mean()),
                         "n": int(m.sum()), "verdict": ""})
    return rows


SEGMENTS = {
    "tour": lambda g: g["tour"].map({"atp": "men", "wta": "women"}),
    "level": lambda g: g["level"],
    "surface": lambda g: g["surface_name"],
    "favourite's price (recalibrated)": lambda g: pd.cut(g["fav_p"], [0.5, 0.6, 0.7, 0.8, 0.9, 1.0001], right=False,
                                                          labels=["50-60%", "60-70%", "70-80%", "80-90%", "90%+"]),
    "the model leans": lambda g: g["lean"],
    "size of the disagreement (quintile of |d|)": lambda g: pd.qcut(g["d"].abs(), 5, labels=["Q1 smallest", "Q2", "Q3",
                                                                                              "Q4", "Q5 largest"]),
    "the odds input's source": lambda g: g["odds_input"],
    "best of": lambda g: g["in_best_of"].map({3.0: "best of 3", 5.0: "best of 5"}),
    "round": lambda g: g["round_name"].map({"R128": "R128-R32", "R64": "R128-R32", "R32": "R128-R32",
                                             "R16": "R16-QF", "QF": "R16-QF", "SF": "SF-F, RR", "F": "SF-F, RR",
                                             "RR": "SF-F, RR"}),
    "indoor": lambda g: g["in_indoor"].map({0.0: "outdoor", 1.0: "indoor"}),
    "half-year": lambda g: g["half"],
    "tour x level": lambda g: g["tour"].map({"atp": "men", "wta": "women"}) + " " + g["level"].astype(str),
}


def part_c3(df: pd.DataFrame, qk: np.ndarray) -> list[dict]:
    rows = []
    for wname, window in WINDOWS.items():
        m = mask(df, window, "both")
        g = df[m]
        qkm = qk[m]
        per = 1000 * (S.ll(g["q_close"], g["y"]) - S.ll(g["q_full"], g["y"]))
        total = float(per.sum())
        for seg, fn in SEGMENTS.items():
            lab = fn(g).astype(str).to_numpy()
            for level in sorted(set(lab)):
                k = lab == level
                if k.sum() < 100:
                    continue
                h = g[k]
                st = S.seed_term(None, qkm[k], h["y"].to_numpy())
                v = S.gain(h["q_close"], h["q_full"], h["y"].to_numpy(), h["block"].to_numpy(), st)
                rea = S.realisation(h["q_close"].to_numpy(), h["q_full"].to_numpy(), h["y"].to_numpy(),
                                    h["block"].to_numpy())
                rows.append({"window": wname, "segment_type": seg, "segment": level, "n": int(k.sum()),
                             "share_of_matches": float(k.mean()), **{f"gain_{a}": v[a] for a in
                                                                     ("est", "lo", "hi", "p_better")},
                             "verdict": S.verdict(v), "share_of_total_gain": float(per[k].sum() / total),
                             "realisation": rea["r"], "realisation_se": rea["se"], "spread": rea["spread"]})
    return rows


def part_roi(df: pd.DataFrame) -> list[dict]:
    rows = []
    books = {"pinnacle": ("pin_a", "pin_b"), "betonline": ("bol_a", "bol_b")}
    for wname, window in WINDOWS.items():
        m = df["season"].isin(window).to_numpy() & (df["status"] == "completed").to_numpy()
        for book, (ca, cb) in books.items():
            g = df[m & df[ca].notna().to_numpy() & df[cb].notna().to_numpy()].reset_index()
            if len(g) < 300:
                continue
            for fc, col in (("model", "q_full"), ("control: the recalibrated price", "q_close")):
                b = bets(g[col], g[ca], g[cb], 0.0)
                profit, _ = settle(b, g["y"].astype(bool))
                fav_side = np.where(b["on_a"], g[ca] < g[cb], g[cb] < g[ca])
                groups = {"all": np.ones(len(g), bool), "men": (g["tour"] == "atp").to_numpy(),
                          "women": (g["tour"] == "wta").to_numpy(),
                          "backing the book's favourite": fav_side, "backing the book's underdog": ~fav_side,
                          "model leans toward the favourite": (g["lean"] == "toward the favourite").to_numpy(),
                          "model leans toward the underdog": (g["lean"] == "toward the underdog").to_numpy()}
                for gname, gm in groups.items():
                    k = gm & b["bet"].to_numpy()
                    if k.sum() < 30:
                        continue
                    stake, prof = b["stake"].to_numpy()[k], profit[k]
                    lo, hi = block_ci(prof, stake, g["block"].to_numpy()[k])
                    rows.append({"window": wname, "book": book, "forecast": fc, "group": gname,
                                 "first_day": str(g["tournament_date"].min().date()),
                                 "last_day": str(g["tournament_date"].max().date()), "bets": int(k.sum()),
                                 "staked": float(stake.sum()), "profit": float(prof.sum()),
                                 "roi": float(prof.sum() / stake.sum()), "roi_lo": lo, "roi_hi": hi,
                                 "mean_edge_claimed": float(np.nanmean(b["ev"].to_numpy()[k]))})
    return rows


def block_ci(profit: np.ndarray, stake: np.ndarray, blk: np.ndarray, draws: int = 2000, seed: int = 20261012):
    labels, ix = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=draws).astype(float)
    d = (W @ np.bincount(ix, weights=profit, minlength=len(labels))) / \
        np.maximum(W @ np.bincount(ix, weights=stake, minlength=len(labels)), 1e-12)
    return float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def main() -> int:
    df, qk = load()
    a = pd.DataFrame(part_a(df, qk))
    seg = pd.DataFrame(part_c3(df, qk))
    roi = pd.DataFrame(part_roi(df))
    a.to_csv(E.OUT / "edge_A.csv", index=False)
    seg.to_csv(E.OUT / "edge_segments.csv", index=False)
    roi.to_csv(E.OUT / "edge_roi.csv", index=False)
    head = a[(a["comparison"] == "model (both stages) vs its recalibrated price")]
    E.write_json(E.OUT / "edge_summary.json", {"headline": head.to_dict("records")})
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(a[a["window"].isin(["2025-26", "2020-24"])][["window", "tour", "comparison", "est", "lo", "hi", "p_better",
                                                       "verdict", "n"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
