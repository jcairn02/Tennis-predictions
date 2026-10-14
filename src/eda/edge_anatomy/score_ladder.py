"""Scores the family-ablation refits (fits.py): what each input family adds to the current model's edge over its price.

Every arm goes through the decided recipe on its own forecasts, as data.py does for the full model: the seed mean of
seeds 0-3; the per-tour calibration slopes and the men's serve-speed coefficient b fitted walk-forward on 2019 .. Y - 1
(compare.walk_forward; debut seasons out; b shrunk); both stages (and stage 1 alone). The full model is the instance's
stored fits, seeds 0-3 (seeds.parquet), so every comparison has four matched seeds on each side.

Readings (mLL; + = the second named better; four-week-block intervals plus the seed term, paired by seed between two
arms, unpaired against the price), on 2025 - 28 Jul 2026 and on 2020-2024, both tours, men, women, debut seasons out:
    arm vs price      each arm against the recalibrated price
    ladder step       L(k) against L(k - 1): what adding the family to the arm below it gives (L0 = the price)
    unique part       drop_<family> against the full model: what the family adds that the others cannot replace
    realisation       of each arm's disagreement with the price (1 = right-sized)
Only arms with every fit on disk are scored.

Writes data/studies/edge_anatomy/ladder_scores.csv.
Run: ./python.sh src/eda/edge_anatomy/score_ladder.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

SEASONS = tuple(range(2020, 2027))
WINDOWS = {"2025-26": (2025, 2026), "2020-24": (2020, 2021, 2022, 2023, 2024), "2025": (2025,), "2026": (2026,)}
LADDER_ARMS = ("L1", "L2", "L3", "L4", "L5", "full")
STEP_NAMES = {"L1": "the price alone, re-drawn by TabPFN", "L2": "+ context", "L3": "+ ratings",
              "L4": "+ schedule and body", "L5": "+ box-score form", "full": "+ IOS profile (= the full model)"}
DROPS = ("drop_context", "drop_ratings", "drop_schedule", "drop_form", "drop_ios")


def arm_table(arm: str, ids_by_season: dict[int, np.ndarray]) -> pd.DataFrame | None:
    parts = []
    for s in range(2019, 2027):
        per = {}
        for k in E.SEEDS:
            path = E.fit_path(arm, s, k)
            if not path.exists():
                return None
            with np.load(path, allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"].astype(str)
                meta = json.loads(str(z["meta"]))
            if meta["columns"] != E.arms()[arm]:
                raise RuntimeError(f"{path.name}: columns differ from the arm's")
            if not np.array_equal(ids, ids_by_season[s]):
                raise RuntimeError(f"{path.name}: ids are not the season's frame matches in order")
            per[k] = pd.Series(E.sym(p, len(ids)), index=ids)
        parts.append(pd.DataFrame(per))
    return pd.concat(parts)


def run() -> pd.DataFrame:
    info = pd.read_parquet(E.OUT / "analysis.parquet").set_index("match_id")
    frame = pd.read_parquet(E.INSTANCE / "model_frame.parquet", columns=["match_id", "season"])
    frame["match_id"] = frame["match_id"].astype(str)
    ids_by_season = {int(s): g["match_id"].to_numpy() for s, g in frame.groupby("season", sort=True)}
    z = info["spd"]
    seeds = pd.read_parquet(E.OUT / "seeds.parquet").set_index("match_id")
    tables = {"full": seeds[[f"s{k}" for k in E.SEEDS]].set_axis(list(E.SEEDS), axis=1)}
    for arm in ("L1", "L2", "L3", "L4", "L5") + DROPS:
        t = arm_table(arm, ids_by_season)
        if t is not None:
            tables[arm] = t
    E.log(f"arms with every fit: {sorted(tables)}")
    test = info.index[info["season"].isin(SEASONS).to_numpy()]
    fc = {}
    for arm, t in tables.items():
        t = t.reindex(info.index)
        if t.isna().any().any():
            raise RuntimeError(f"{arm}: forecasts missing")
        eta = pd.Series(S.lg(t.mean(axis=1).to_numpy()), index=t.index)
        par2 = CMP.walk_forward(eta, info, z, SEASONS)
        par1 = CMP.walk_forward(eta, info, None, SEASONS)
        q2, q2k = CMP.forecasts(t, info, par2, z, test)
        q1, q1k = CMP.forecasts(t, info, par1, None, test)
        fc[arm] = {"both": (pd.Series(q2, index=test), q2k), "s1": (pd.Series(q1, index=test), q1k)}
    full_check = np.abs(fc["full"]["both"][0].to_numpy() - info.loc[test, "q_full"].to_numpy())
    E.log(f"full (seeds 0-3) against the 16-seed final forecast: mean |diff| {full_check.mean():.4f}")
    rows = []
    for wname, window in WINDOWS.items():
        for tour in ("both", "atp", "wta"):
            m = info.loc[test, "season"].isin(window).to_numpy() & ~info.loc[test, "debut"].to_numpy()
            if tour != "both":
                m &= (info.loc[test, "tour"] == tour).to_numpy()
            ids = test[m]
            y, blk = info.loc[ids, "y"].to_numpy(), info.loc[ids, "block"].to_numpy()
            qc = info.loc[ids, "q_close"].to_numpy()
            for stage in ("both", "s1"):
                def get(arm):
                    q, qk = fc[arm][stage]
                    return q.loc[ids].to_numpy(), qk[m]
                for arm in fc:
                    q, qk = get(arm)
                    v = S.gain(qc, q, y, blk, S.seed_term(None, qk, y))
                    rea = S.realisation(qc, q, y, blk)
                    rows.append({"window": wname, "tour": tour, "stage": stage, "reading": "arm vs price", "arm": arm,
                                 **v, "verdict": S.verdict(v), "realisation": rea["r"], "realisation_se": rea["se"],
                                 "spread": rea["spread"]})
                prev = None
                for arm in LADDER_ARMS:
                    if arm not in fc:
                        break
                    q, qk = get(arm)
                    if prev is None:
                        v = S.gain(qc, q, y, blk, S.seed_term(None, qk, y))
                    else:
                        v = S.gain(prev[0], q, y, blk, S.seed_term(prev[1], qk, y))
                    rows.append({"window": wname, "tour": tour, "stage": stage, "reading": "ladder step", "arm": arm,
                                 "step": STEP_NAMES[arm], **v, "verdict": S.verdict(v)})
                    prev = (q, qk)
                qf, qfk = get("full")
                for arm in DROPS:
                    if arm not in fc:
                        continue
                    q, qk = get(arm)
                    v = S.gain(q, qf, y, blk, S.seed_term(qk, qfk, y))
                    rows.append({"window": wname, "tour": tour, "stage": stage, "reading": "unique part", "arm": arm,
                                 "step": f"what {arm[5:]} adds that the others cannot replace", **v,
                                 "verdict": S.verdict(v)})
    return pd.DataFrame(rows)


def main() -> int:
    out = run()
    out.to_csv(E.OUT / "ladder_scores.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    sub = out[(out["stage"] == "both") & out["window"].isin(["2025-26", "2020-24"])]
    print(sub[["window", "tour", "reading", "arm", "est", "lo", "hi", "p_better", "verdict"]].round(2)
          .to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
