"""Residual screen of women's pressure pace (and, reported only, tempo level) against the model and the close.

The registration is data/studies/point_sequence/pace_screen_prereg.md; its SHA-256 was recorded in
pace_screen_prereg.sha256 before this script was written, and the script refuses to run if the file has changed.

Pre-match value per player: the weighted mean X/D over her logged matches of the 364 days before the match's
best-estimate day (`obs`), or at earlier rounds of the same event, with at least 5 such matches; the same history rule
as tempo_run.py's R^2 step. x = A - B, divided by its discovery-window standard deviation.
Benchmarks: meta-stack walk-forward forecasts of the 54-input model and the close, recalibrated prequentially (one
slope per tour on logit, earlier seasons only). beta in logistic(a_won) = offset(logit benchmark) + beta * x.
Positive beta = the player whose value is higher (for pressure pace: slows down more on pressure points than on others)
wins more often than the benchmark says.

    ./python.sh src/eda/point_sequence/pace_screen.py
Writes data/studies/point_sequence/pace_screen_results.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import diag_edge_split as S  # noqa: E402
from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = TC.OUT
PREREG, HASH = OUT / "pace_screen_prereg.md", OUT / "pace_screen_prereg.sha256"
JUNE_2019 = int(np.datetime64("2019-06-01", "D").astype("int64"))
WINDOWS = {"discovery": ("2020-01-01", "2021-12-31"), "replication": ("2022-01-01", "2024-12-31")}
STATS = {"pressure_pace": ("X_P", "D_P"), "tempo_level": ("X_T", "D_T")}


def history() -> pd.DataFrame:
    """Per logged player-match: player, day, event, round order and the X/D sums of every world kept."""
    pop = pd.read_parquet(OUT / "trait_population.parquet")
    tp = pop[pop["tour"].eq("wta") & pop["source"].eq("wta") & (pop["obs"] >= JUNE_2019) & pop["year"].le(2024)]
    tp = tp.reset_index(drop=True)
    tp["tcode"] = np.arange(len(tp))
    tpm = pd.read_parquet(OUT / "tempo_player_matches.parquet")
    tpm = tpm[tpm["world"].isin(["primary|real", "spec|real"])]
    h = tpm.merge(tp[["tcode", "match_id", "player_a_id", "player_b_id", "obs", "tournament_id", "round_order"]],
                  on="tcode", how="left", validate="many_to_one")
    if h["match_id"].isna().any():
        raise RuntimeError("tempo codes do not map back to the population (order changed?)")
    h["player"] = np.where(h["side"] == 1, h["player_a_id"], h["player_b_id"])
    return h.drop(columns=["player_a_id", "player_b_id"])


def pre_match(h: pd.DataFrame, frame: pd.DataFrame, world: str, xcol: str, dcol: str) -> pd.DataFrame:
    hw = h[(h["world"] == world) & (h[dcol] > 0)][["player", "obs", "tournament_id", "round_order", xcol, dcol]]
    out = {}
    for sd in ("a", "b"):
        q = frame[["match_id", f"player_{sd}_id", "obs", "tournament_id", "round_order"]].rename(
            columns={f"player_{sd}_id": "player", "obs": "obs_t", "tournament_id": "tid_t", "round_order": "ro_t"})
        j = q.merge(hw, on="player", how="inner")
        ok = ((j["obs"] < j["obs_t"]) & (j["obs"] >= j["obs_t"] - 364)) | \
             ((j["tournament_id"] == j["tid_t"]) & (j["round_order"] < j["ro_t"]) & (j["obs"] <= j["obs_t"]))
        g = j[ok].groupby("match_id").agg(X=(xcol, "sum"), D=(dcol, "sum"), k=(xcol, "size"))
        g = g[g["k"] >= 5]
        out[sd] = (g["X"] / g["D"]).reindex(frame["match_id"]).to_numpy()
    return pd.DataFrame({"match_id": frame["match_id"].to_numpy(), "va": out["a"], "vb": out["b"]})


def offset_fit(y: np.ndarray, off: np.ndarray, x: np.ndarray) -> float:
    beta = 0.0
    for _ in range(60):
        p = expit(off + beta * x)
        h = np.sum(x * x * p * (1 - p))
        if h <= 0:
            break
        step = np.sum(x * (y - p)) / h
        beta += step
        if abs(step) < 1e-11:
            break
    return float(beta)


def summary(g: pd.DataFrame, bench: str, rng: np.random.Generator, beta_disc: float | None) -> dict:
    y = g["a_won"].astype(int).to_numpy()
    off = logit(np.clip(g[bench].to_numpy(), T.EPS, 1 - T.EPS))
    x = g["x"].to_numpy(dtype=float)
    beta = offset_fit(y, off, x)
    p = expit(off + beta * x)
    se = float(1 / np.sqrt(np.sum(x * x * p * (1 - p))))
    blk = T.blocks(g["tournament_date"].to_numpy(), 28)
    ub = np.unique(blk)
    idx = {b: np.flatnonzero(blk == b) for b in ub}
    boots = [offset_fit(y[ii], off[ii], x[ii]) for ii in
             (np.concatenate([idx[b] for b in rng.choice(ub, len(ub), replace=True)]) for _ in range(1000))]
    res = {"matches": int(len(g)), "beta": beta, "lo": beta - 1.96 * se, "hi": beta + 1.96 * se,
           "block_lo": float(np.percentile(boots, 2.5)), "block_hi": float(np.percentile(boots, 97.5))}
    if beta_disc is not None:   # discovery's beta applied out of sample: gain in mLL, positive = feature better
        base = T.ll(expit(off), y)
        with_x = T.ll(expit(off + beta_disc * x), y)
        c = T.compare(base, with_x, g["tournament_date"].to_numpy())
        res["gain_mll_with_discovery_beta"] = {"gain": c["gain"], "lo": c["lo"], "hi": c["hi"]}
    return res


def main() -> int:
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if digest != HASH.read_text(encoding="utf-8").split()[0]:
        raise SystemExit("pace_screen_prereg.md changed after its hash was recorded: refusing to run")
    wf = pd.read_parquet(S.WF, columns=["match_id", "tour", "year", "tournament_date", "a_won", "p_mkt", "p_base"])
    wf = wf[wf["p_mkt"].notna() & wf["p_base"].notna()].reset_index(drop=True)
    wf["p_model"] = S.prequential(wf, "p_base")
    wf["p_market"] = S.prequential(wf, "p_mkt")
    f = wf[(wf["tour"] == "wta") & wf["p_model"].notna() & wf["p_market"].notna()].copy()
    s0 = pd.read_parquet(TC.S0 / "stage0_matches.parquet",
                         columns=["match_id", "player_a_id", "player_b_id", "tournament_id", "round_order"])
    tim = pd.read_parquet(TC.TIMING, columns=["match_id", "obs"])
    f = f.merge(s0, on="match_id", how="left").merge(tim, on="match_id", how="left")
    f["day"] = pd.to_datetime(f["obs"], unit="D")
    f = f[(f["day"] >= WINDOWS["discovery"][0]) & (f["day"] <= WINDOWS["replication"][1])].reset_index(drop=True)
    h = history()
    rng = np.random.default_rng(20261006)
    res = {"prereg_sha256": digest,
           "key": "beta = log-odds per SD of (A - B), given the benchmark as an offset; positive = the player with the "
                  "higher value wins more often than the benchmark says; Wald 95% (block bootstrap as a check); "
                  "gain in mLL, positive = feature better; spanning 0 = tie",
           "results": {}}
    for stat, (xc, dc) in STATS.items():
        for world in ("primary|real", "spec|real"):
            pm = pre_match(h, f, world, xc, dc)
            g0 = f.merge(pm, on="match_id", how="left")
            g0 = g0[np.isfinite(g0["va"]) & np.isfinite(g0["vb"])].copy()
            g0["raw"] = g0["va"] - g0["vb"]
            disc = (g0["day"] >= WINDOWS["discovery"][0]) & (g0["day"] <= WINDOWS["discovery"][1])
            sd = float(g0.loc[disc, "raw"].std())
            g0["x"] = g0["raw"] / sd
            key = f"{stat} | {world}"
            res["results"][key] = {"sd_discovery_s": sd}
            for bench in ("p_model", "p_market"):
                gd = g0[disc]
                rd = summary(gd, bench, rng, None)
                gr = g0[(g0["day"] >= WINDOWS["replication"][0]) & (g0["day"] <= WINDOWS["replication"][1])]
                rr = summary(gr, bench, rng, rd["beta"])
                res["results"][key][bench] = {"discovery": rd, "replication": rr}
    prim = res["results"]["pressure_pace | primary|real"]["p_model"]
    d, r = prim["discovery"], prim["replication"]
    passed = (d["lo"] > 0 or d["hi"] < 0) and np.sign(r["beta"]) == np.sign(d["beta"]) and (r["lo"] > 0 or r["hi"] < 0)
    res["decision"] = {"rule": "discovery interval excludes 0 against the model, and replication beta has the same sign "
                               "with its interval excluding 0", "pass": bool(passed)}
    (OUT / "pace_screen_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for k, v in res["results"].items():
        for bench in ("p_model", "p_market"):
            for w in ("discovery", "replication"):
                e = v[bench][w]
                gain = e.get("gain_mll_with_discovery_beta", {})
                print(f"{k:32s} {bench:8s} {w:11s} n={e['matches']:5d} beta={e['beta']:+.3f} "
                      f"[{e['lo']:+.3f}, {e['hi']:+.3f}] block [{e['block_lo']:+.3f}, {e['block_hi']:+.3f}]"
                      + (f"  gain {gain['gain']:+.2f} [{gain['lo']:+.2f}, {gain['hi']:+.2f}] mLL" if gain else ""))
    print("decision:", res["decision"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
