"""Bet timing, step 5: the current best model retrained on the books it would bet at (local TabPFN-3.5 on the GPU).

The owner's follow-up of 8 Oct 2026: "So ideally if we were betting at pinnacle and betonline we train on both of their
closing lines averaged then bet whenever we want to bet and use the combination of their lines at the time we decide to
bet as input for this feature space?"

The arm "pb": the 58 inputs and settings of the current best model, season Y trained on 2013 .. Y - 1, but its odds input
in training is the mean margin-free log-odds of Pinnacle's close (Stage 1's PSW/PSL) and BetOnline's last line (frame.py).
Before 2018, and wherever BetOnline has no clean last line, Pinnacle's close alone; where Pinnacle has none, the books'
average close (the current input). Season Y's matches are queried, stored and then swapped:

    own          every match, with the arm's own training construction (its calibration history)
    cons_close   the consensus of Pinnacle's close and BetOnline's last line (consensus.py)
    ps_close     Pinnacle's close alone
    bol_close    BetOnline's last line alone
    bol_open     BetOnline's opening line

Seasons 2019-2025 (2019 only for the calibration; Pinnacle stops in January 2026), seeds 0-3. Started as fits.py is
(run_when_free.sh); saved to data/studies/bet_timing/local_cons_trained/, never refitted.

    bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits_cons_trained.py --run [--arm bo]

--arm bo trains on BetOnline's last line wherever it has one (2018 on) and Pinnacle's close before that, instead of the
average of the two: the construction that needs no Pinnacle price after January 2026.

--arm pf ("Pinnacle first", 9 Oct 2026, the odds-sources study: docs/studies/odds_sources/) trains on Pinnacle's close
from its two recordings (tennis-data's to July 2025, OddsTrader's timed last line; the other books deciding where they
differ), BetOnline's last line where Pinnacle has none, the books' average where neither does: p_pf of
data/studies/odds_sources/pools.parquet. Fitted on the data the walk-forward weights pointed to (about all on Pinnacle).
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

LOCAL = C.OUT / "local_cons_trained"
SEASONS = tuple(range(2019, 2026))
QUERY_BLOCKS = ("cons_close", "ps_close", "bol_close", "bol_open")
# The arms' training constructions (the owner's follow-up of 8 Oct 2026, "Can I just use betonline in this scenario for
# training?"): "pb" averages Pinnacle and BetOnline; "bo" takes BetOnline's last line wherever it has one (2018 on) and
# Pinnacle's close before that, the free choice from 2026 on (Pinnacle's closes in tennis-data stop in January 2026);
# "pf" takes a faithful Pinnacle close first, then BetOnline (the odds-sources study, 9 Oct 2026)
ARMS = ("pb", "bo", "pf")
PF_INPUT = ROOT / "data" / "studies" / "odds_sources" / "pools.parquet"     # odds_sources/pools.py (gitignored)


def fit_path(season: int, seed: int, arm: str = "pb") -> Path:
    return LOCAL / f"{arm}__{season}__seed{seed}.npz"


def inputs(frame: pd.DataFrame, arm: str = "pb") -> pd.DataFrame:
    """match_id -> p_own (the arm's training construction) and the query prices, for every frame match."""
    s1 = pd.read_parquet(C.STAGE1, columns=["match_id", "ps_a", "ps_b", "ps_coherent"])
    s1["match_id"] = s1["match_id"].astype(str)
    f = frame[["match_id", "in_odds_logit"]].merge(s1, on="match_id", how="left", validate="one_to_one")
    ok = f["ps_coherent"].fillna(False).astype(bool).to_numpy()
    p_ps = np.where(ok, C.devig(f["ps_a"], f["ps_b"]), np.nan)
    pr = pd.read_parquet(C.FRAME, columns=["match_id", "p_bol_close", "p_bol_open"])
    pr["match_id"] = pr["match_id"].astype(str)
    cf = pd.read_parquet(C.CONSENSUS_FRAME, columns=["match_id", "p_cons_close", "p_ps_close"])
    cf["match_id"] = cf["match_id"].astype(str)
    f = f.merge(pr, on="match_id", how="left").merge(cf, on="match_id", how="left")
    p_bol = f["p_bol_close"].to_numpy(float)
    both = np.isfinite(p_ps) & np.isfinite(p_bol)
    p_avg = C.ex(f["in_odds_logit"].to_numpy(float))
    if arm == "pb":
        own = np.where(both, C.ex(0.5 * (C.lg(np.where(both, p_ps, 0.5)) + C.lg(np.where(both, p_bol, 0.5)))),
                       np.where(np.isfinite(p_ps), p_ps, p_avg))
        kind = np.where(both, "pinnacle+betonline", np.where(np.isfinite(p_ps), "pinnacle", "average"))
    elif arm == "bo":
        own = np.where(np.isfinite(p_bol), p_bol, np.where(np.isfinite(p_ps), p_ps, p_avg))
        kind = np.where(np.isfinite(p_bol), "betonline", np.where(np.isfinite(p_ps), "pinnacle", "average"))
    elif arm == "pf":
        pf = pd.read_parquet(PF_INPUT, columns=["match_id", "p_pin", "p_pin_first", "p_pf"])
        pf = pf.set_index(pf["match_id"].astype(str)).reindex(f["match_id"].to_numpy())
        p_pin, p_first, p_pf = (pf[c].to_numpy(float) for c in ("p_pin", "p_pin_first", "p_pf"))
        own = np.where(np.isfinite(p_pf), p_pf, p_avg)               # a frame match the study's table lacks: average
        kind = np.where(np.isfinite(p_pin), "pinnacle", np.where(np.isfinite(p_first), "betonline", "average"))
    else:
        raise ValueError(f"arm must be one of {ARMS}")
    out = pd.DataFrame({"match_id": f["match_id"].to_numpy(), "p_own": own, "own_kind": kind,
                        "p_cons_close": f["p_cons_close"].to_numpy(float), "p_ps_close": f["p_ps_close"].to_numpy(float),
                        "p_bol_close": p_bol, "p_bol_open": f["p_bol_open"].to_numpy(float)})
    if arm == "pb":   # the consensus frame's p_cons_close must be this construction where both books price the match
        k = both & np.isfinite(out["p_cons_close"].to_numpy())
        if not np.allclose(out.loc[k, "p_cons_close"], out.loc[k, "p_own"], atol=1e-12):
            raise RuntimeError("the training construction differs from consensus.py's p_cons_close")
    return out.set_index("match_id")


def run(seasons, seeds, arm: str = "pb") -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    P = SC.DEFAULT
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    inp = inputs(frame, arm)
    kinds = inp["own_kind"].reindex(frame["match_id"]).to_numpy()
    C.write_json(C.OUT / ("cons_trained_inputs.json" if arm == "pb" else f"cons_trained_inputs_{arm}.json"),
                 {"arm": arm, "by_season_and_kind": {f"{s}|{k}": int(n) for (s, k), n in
                                                     pd.Series(kinds).groupby([frame["season"].to_numpy(), kinds])
                                                     .size().items()}})
    LOCAL.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        todo = [k for k in seeds if not fit_path(season, k, arm).exists()]
        if not todo:
            continue
        X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
        tr_ids = frame.loc[frame["season"].between(C.TRAIN_FROM, season - 1).to_numpy(), "match_id"].to_numpy()
        X_train = X_train.copy()
        X_train["odds_logit"] = C.lg(inp.loc[tr_ids, "p_own"].to_numpy(float))
        ids = ids.astype(str)
        f = inp.reindex(ids)
        qs = {}
        for name, col in (("own", "p_own"),) + tuple((b, f"p_{b}") for b in QUERY_BLOCKS):
            p = f[col].to_numpy(float)
            ok = np.isfinite(p)
            if not ok.any():
                continue
            Xq = X_test[ok].reset_index(drop=True).copy()
            Xq["odds_logit"] = C.lg(p[ok])
            qs[name] = (pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), ids[ok])
        names = list(qs)
        X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
        for seed in todo:
            path = fit_path(season, seed, arm)
            free_gb = wait_for_card(need_gb=12.0, patience_s=12 * 3600, processes=False)
            clf = runtime.classifier(**C.CONFIG, random_state=seed)
            torch.cuda.reset_peak_memory_stats()
            t0 = time.monotonic()
            clf.fit(X_train, y_train)
            proba = clf.predict_proba(X_query)
            secs = time.monotonic() - t0
            if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
                raise RuntimeError(f"{path.name}: invalid probabilities")
            p = proba[:, 1]
            payload, start = {}, 0
            for n in names:
                k = len(qs[n][0])
                payload[f"p_{n}"] = p[start:start + k]
                payload[f"ids_{n}"] = qs[n][1].astype(str)
                start += k
            meta = {"arm": arm, "season": season, "seed": seed, "config": {**C.CONFIG, "random_state": seed},
                    "train_shape": list(X_train.shape), "train_seasons": [C.TRAIN_FROM, season - 1],
                    "query_rows": {n: int(len(qs[n][0])) for n in names}, "seconds": round(secs, 1),
                    "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            C.log(f"{path.name}: {secs:.0f} s, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    if "--run" in sys.argv:
        arm = sys.argv[sys.argv.index("--arm") + 1] if "--arm" in sys.argv else "pb"
        sys.exit(run(SEASONS[::-1], C.SEEDS, arm))
    print(__doc__)
    sys.exit(2)
