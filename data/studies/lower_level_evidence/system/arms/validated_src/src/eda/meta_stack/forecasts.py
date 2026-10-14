"""Assemble the out-of-sample forecasts this study scores.

    walkforward.parquet    one row per main-tour match with odds, 2014-2026: the closing line (p_mkt) and, for both
                           models (base: with the odds; noodds: without), each seed's symmetrised P(A wins) and the
                           four-seed mean, every match forecast by the window trained on 2013 to the season before.
                           2014-2018 from this study's fits; 2019-2026 from the surface-IOS study's, each checked
                           against the fingerprint in its manifest
    holdout.parquet        the no-odds fits trained on 2013..T and queried on later seasons (the hold-out design):
                           train_to, seed, match_id, year, p (symmetrised)
    reproducibility.json   this study's fits that repeat a surface-IOS window (T = 2018 and 2019, on their first
                           season), compared match by match

Run: ./python.sh src/eda/meta_stack/forecasts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.meta_stack import common as C  # noqa: E402
from src.eda.meta_stack import run_local as R  # noqa: E402
from src.eda.surface_ios import common as SC  # noqa: E402  (jdump)
from src.eda.tabpfn_thinking import common as T  # noqa: E402

META = ["match_id", "tour", "year", "tournament_date", "a_won", "group", "surface_code", "p_mkt"]


def sios_long() -> pd.DataFrame:
    """The surface-IOS fits of base and base_noodds (2019-2026): match_id, arm, seed, p (symmetrised)."""
    manifest = json.loads((C.SIOS / "uploads" / "manifest.json").read_text(encoding="utf-8"))
    names = {v: k for k, v in C.SIOS_ARM.items()}
    parts = []
    for slot, spec in manifest["slots"].items():
        if spec["arm"] not in names:
            continue
        ids = pd.read_parquet(C.SIOS / "uploads" / slot / "query_ids.parquet")
        with np.load(C.SIOS / "local" / f"{slot}.npz", allow_pickle=False) as z:
            if str(z["input_fingerprint"]) != spec["input_fingerprint"]:
                raise RuntimeError(f"{slot}: saved forecasts belong to another upload")
            p = z["p_a"]
        n = len(ids) // 2
        mid = ids["match_id"].to_numpy()
        if len(p) != 2 * n or not (np.array_equal(mid[:n], mid[n:]) and (ids["orientation"].to_numpy()[:n] == 0).all()):
            raise RuntimeError(f"{slot}: query rows are not the season's matches, as stored then swapped")
        parts.append(pd.DataFrame({"match_id": mid[:n], "arm": names[spec["arm"]], "seed": spec["seed"],
                                   "year_fit": spec["year"], "p": T.symmetrize(p[:n], p[n:])}))
    return pd.concat(parts, ignore_index=True)


def own_long() -> pd.DataFrame:
    """This study's fits: match_id, arm, seed, train_to, p (symmetrised), for every queried season."""
    parts = []
    for slot, spec in R.slots().items():
        if not (C.LOCAL / f"{slot}.npz").exists():
            raise FileNotFoundError(f"{slot}: run run_local.py first")
        ids, p, _ = R.load(slot)
        n = len(ids)
        parts.append(pd.DataFrame({"match_id": ids, "arm": spec["arm"], "seed": spec["seed"],
                                   "train_to": spec["train_to"], "p": T.symmetrize(p[:n], p[n:])}))
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    base = pd.read_parquet(C.SIOS / "base_frame.parquet", columns=META)
    year = base.set_index("match_id")["year"]
    sios = sios_long()
    own = own_long()
    own["year"] = own["match_id"].map(year).to_numpy()
    # walk-forward: the window trained on 2013 to the season before the match's season
    wf_own = own[(own["year"] == own["train_to"] + 1) & own["year"].isin(C.PRE)]
    wf = pd.concat([wf_own[["match_id", "arm", "seed", "p"]], sios[["match_id", "arm", "seed", "p"]]],
                   ignore_index=True)
    if wf.duplicated(["match_id", "arm", "seed"]).any():
        raise RuntimeError("a match has two walk-forward forecasts from the same model and seed")
    wide = wf.assign(col=lambda d: "p_" + d["arm"] + "_s" + d["seed"].astype(str)).pivot(
        index="match_id", columns="col", values="p")
    out = base[base["year"].between(min(C.PRE), max(C.TEST))].merge(wide, left_on="match_id", right_index=True,
                                                                     how="left", validate="one_to_one")
    for arm in C.SIOS_ARM:
        cols = [f"p_{arm}_s{k}" for k in C.SEEDS]
        missing = out[cols].isna().any(axis=1)
        if missing.any():
            raise RuntimeError(f"{arm}: {int(missing.sum())} matches lack a walk-forward forecast")
        out[f"p_{arm}"] = out[cols].mean(axis=1)
    out.to_parquet(C.OUT / "walkforward.parquet", index=False)
    C.log(f"walkforward.parquet: {len(out):,} matches, {out['year'].min()}-{out['year'].max()}")

    hold = own[own["arm"] == "noodds"][["train_to", "seed", "match_id", "year", "p"]].reset_index(drop=True)
    hold.to_parquet(C.OUT / "holdout.parquet", index=False)
    C.log(f"holdout.parquet: {len(hold):,} forecasts")

    # this study's fits that repeat a surface-IOS window, on that window's season
    y = base.set_index("match_id")["a_won"]
    rep = {}
    for t in (2018, 2019):
        for k in C.SEEDS:
            mine = own[(own["arm"] == "noodds") & (own["train_to"] == t) & (own["seed"] == k) & (own["year"] == t + 1)]
            theirs = sios[(sios["arm"] == "noodds") & (sios["seed"] == k) & (sios["year_fit"] == t + 1)]
            m = mine.merge(theirs, on="match_id", suffixes=("_mine", "_sios"), validate="one_to_one")
            yy = y.reindex(m["match_id"]).to_numpy()
            rep[f"noodds trained 2013-{t}, seed {k}, season {t + 1}"] = {
                "matches": int(len(m)), "of_season": int(len(theirs)),
                "max_abs_diff_probability": float((m["p_mine"] - m["p_sios"]).abs().max()),
                "rows_differing_1e-7": int(((m["p_mine"] - m["p_sios"]).abs() > 1e-7).sum()),
                "log_loss_diff_milli": float(1000 * (T.ll(m["p_mine"].to_numpy(), yy).mean()
                                                     - T.ll(m["p_sios"].to_numpy(), yy).mean()))}
    SC.jdump(rep, C.OUT / "reproducibility.json")
    worst = max(abs(v["log_loss_diff_milli"]) for v in rep.values())
    C.log(f"reproducibility: largest log-loss difference {worst:.4f} milli over {len(rep)} repeated windows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
